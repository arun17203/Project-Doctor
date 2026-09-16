import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.models.dependency import DependencyAnalysis, DependencyIssue
from backend.app.models.architecture import ArchitectureAnalysis
from backend.app.models.health import HealthAnalysis

from backend.app.analyzers.health.calculator import (
    calculate_quality_score,
    calculate_security_score,
    calculate_dependency_score,
    calculate_architecture_score,
    calculate_maintainability_score,
    calculate_testing_score,
    calculate_overall_health_score,
    interpret_health_status,
    DEFAULT_WEIGHTS,
)
from backend.app.analyzers.health.debt import calculate_technical_debt
from backend.app.analyzers.health.priorities import generate_fix_first_list
from backend.app.analyzers.health.explainer import generate_score_explanations
from backend.app.analyzers.health.engine import HealthEngine


# ---------------------------------------------------------------------------
# Unit Tests for Calculator Formulas
# ---------------------------------------------------------------------------

def test_perfect_scores():
    assert calculate_quality_score(0, 0, 0, 0) == 100.0
    assert calculate_security_score(0, 0, 0, 0) == 100.0
    assert calculate_dependency_score(0, 0, 0) == 100.0
    assert calculate_architecture_score(0) == 100.0
    assert calculate_maintainability_score({"avg_cyclomatic_complexity": 2.0, "avg_function_length": 12.0}, 500, 10) == 100.0
    assert calculate_testing_score(5, 10) == 100.0  # 5/5 = 1.0 >= 0.5

    overall = calculate_overall_health_score(100.0, 100.0, 100.0, 100.0, 100.0)
    assert overall == 100.0
    assert interpret_health_status(overall) == "Excellent"


def test_quality_score_penalties_and_clamping():
    # 1 critical (-12), 2 high (-14), 1 medium (-3), 2 low (-2) = -31 -> 69.0
    score = calculate_quality_score(critical=1, high=2, medium=1, low=2)
    assert score == 69.0

    # Clamping: 10 critical (-120) -> 0.0
    score_clamped = calculate_quality_score(critical=10, high=0, medium=0, low=0)
    assert score_clamped == 0.0


def test_security_score_penalties_and_clamping():
    # 1 critical (-25), 1 high (-15), 1 medium (-7), 1 low (-2) = -49 -> 51.0
    score = calculate_security_score(critical=1, high=1, medium=1, low=1)
    assert score == 51.0

    # Clamping: 5 critical (-125) -> 0.0
    score_clamped = calculate_security_score(critical=5, high=0, medium=0, low=0)
    assert score_clamped == 0.0


def test_dependency_score_penalties():
    # 1 vulnerable (-15), 3 outdated (-9), 2 unknown (-2) = -26 -> 74.0
    score = calculate_dependency_score(vulnerable_count=1, outdated_count=3, unknown_count=2)
    assert score == 74.0

    # 10 vulnerable (-150) -> clamped to 0.0
    assert calculate_dependency_score(vulnerable_count=10, outdated_count=0, unknown_count=0) == 0.0


def test_architecture_score_penalties():
    # 2 circular cycles (-20) -> 80.0
    score = calculate_architecture_score(circular_cycles_count=2)
    assert score == 80.0

    # 12 cycles (-120) -> clamped to 0.0
    assert calculate_architecture_score(circular_cycles_count=12) == 0.0


def test_maintainability_score():
    # Elevated complexity (>15 -> -30), large functions (>60 -> -20), 2 duplicate blocks (-8), 3 todos (-3) -> 100 - 61 = 39.0
    metrics = {
        "avg_cyclomatic_complexity": 18.0,
        "avg_function_length": 75.0,
        "duplicate_blocks_count": 2,
        "todos_count": 3,
        "high_complexity_count": 0,
        "large_functions_count": 0,
    }
    score = calculate_maintainability_score(metrics, total_code_lines=1500, total_files=20)
    assert score == 39.0


def test_testing_health_score():
    # 0 test files -> 0.0
    assert calculate_testing_score(test_files_count=0, total_files=10) == 0.0

    # 1 test file for 4 source files -> ratio = 0.25 -> (0.25 / 0.5) * 100 = 50.0
    assert calculate_testing_score(test_files_count=1, total_files=5, config_files_count=0, doc_files_count=0) == 50.0


def test_overall_health_weighted_calculation():
    # Security: 50 * 0.30 = 15.0
    # Quality: 80 * 0.25 = 20.0
    # Maintainability: 70 * 0.20 = 14.0
    # Dependencies: 90 * 0.15 = 13.5
    # Architecture: 100 * 0.10 = 10.0
    # Total = 15.0 + 20.0 + 14.0 + 13.5 + 10.0 = 72.5
    overall = calculate_overall_health_score(
        security_score=50.0,
        quality_score=80.0,
        maintainability_score=70.0,
        dependency_score=90.0,
        architecture_score=100.0,
    )
    assert overall == 72.5
    assert interpret_health_status(overall) == "Fair"


def test_technical_debt_calculation():
    class DummyIssue:
        def __init__(self, severity):
            self.severity = severity

    q_issues = [DummyIssue("CRITICAL"), DummyIssue("HIGH"), DummyIssue("MEDIUM")]  # 8 + 4 + 2 = 14h
    s_issues = [DummyIssue("CRITICAL"), DummyIssue("LOW")]  # 8 + 1 = 9h
    # Vulnerable: 2 * 4 = 8h, Outdated: 3 * 1 = 3h, Circular: 1 * 4 = 4h
    debt = calculate_technical_debt(
        quality_issues=q_issues,
        security_issues=s_issues,
        vulnerable_deps_count=2,
        outdated_deps_count=3,
        circular_cycles_count=1,
    )

    assert debt["quality_hours"] == 14.0
    assert debt["security_hours"] == 9.0
    assert debt["dependency_hours"] == 11.0
    assert debt["architecture_hours"] == 4.0
    assert debt["total_hours"] == 38.0


def test_fix_first_priority_ordering():
    class DummySec:
        severity = "CRITICAL"
        message = "SQL Injection in login"
        file_path = "api/auth.py"
        line_number = 45
        description = "Unparameterized query"
        recommendation = "Use bind parameters"

    class DummySecHigh:
        severity = "HIGH"
        message = "Command injection"
        file_path = "utils/cmd.py"
        line_number = 12
        description = "subprocess shell=True"
        recommendation = "Use list args"

    class DummyQual:
        severity = "HIGH"
        message = "Complexity 24"
        file_path = "services/user.py"
        line_number = 100
        description = "Cyclomatic complexity too high"
        recommendation = "Refactor into smaller methods"

    class DummyDep:
        severity = "CRITICAL"
        package_name = "requests"
        manifest_file = "requirements.txt"
        description = "Known CVE vulnerability"
        recommendation = "Upgrade to requests 2.32.0"

    items = generate_fix_first_list(
        security_issues=[DummySec(), DummySecHigh()],
        quality_issues=[DummyQual()],
        dependency_issues=[DummyDep()],
        circular_cycles=[["a.py", "b.py", "a.py"]],
        limit=5,
    )

    # Highest weight should be rank 1 (Critical Security)
    assert items[0]["title"] == "SQL Injection in login"
    assert items[0]["category"] == "Security"
    assert items[0]["severity"] == "CRITICAL"

    # Next should be High Security
    assert items[1]["title"] == "Command injection"

    # Next should be High Quality
    assert items[2]["title"] == "Complexity 24"

    # Next should be Vulnerable Dependency
    assert "requests" in items[3]["title"]

    # Next should be Circular Architecture
    assert items[4]["category"] == "Architecture"


# ---------------------------------------------------------------------------
# Integration Tests with Full Flow
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health_analysis_missing_prerequisites_rejected():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Register user
        reg_resp = await ac.post(
            "/api/auth/register",
            json={"name": "Prereq User", "email": "prereq@test.com", "password": "Password123!"},
        )
        token = reg_resp.json()["access_token"] if "access_token" in reg_resp.json() else None
        if not token:
            log_resp = await ac.post(
                "/api/auth/login",
                json={"email": "prereq@test.com", "password": "Password123!"},
            )
            token = log_resp.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        proj_resp = await ac.post(
            "/api/projects",
            json={"name": "Missing Prereqs Project", "source_type": "zip"},
            headers=headers,
        )
        project_id = proj_resp.json()["id"]

        # Trigger health analysis without Stage 4 scan
        health_resp = await ac.post(
            f"/api/projects/{project_id}/analyze/health",
            headers=headers,
        )
        assert health_resp.status_code == 400
        assert "Repository Scan (Stage 4) must be completed" in health_resp.json()["detail"]


import io
import zipfile


def create_health_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("requirements.txt", "requests==2.25.1\nurllib3==1.26.5\n")
        zf.writestr(
            "backend/db.py",
            "class Database:\n    pass\n"
        )
        zf.writestr(
            "backend/models.py",
            "from backend.db import Database\nclass User:\n    pass\n"
        )
        zf.writestr(
            "backend/auth.py",
            "import os\nfrom backend.models import User\n"
            "def login(user, pw):\n"
            "    # TODO: Add rate limiting\n"
            "    if user == 'admin':\n"
            "        return True\n"
            "    return False\n"
        )
        zf.writestr(
            "tests/test_auth.py",
            "from backend.auth import login\ndef test_login():\n    assert login('admin', '123') is True\n"
        )
    return buf.getvalue()


@pytest.mark.anyio
async def test_full_health_analysis_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Register & Login User 1
        reg_resp = await ac.post(
            "/api/auth/register",
            json={"name": "Health Tester", "email": "health_full@test.com", "password": "SecurePassword123!"},
        )
        token = reg_resp.json().get("access_token")
        if not token:
            log_resp = await ac.post(
                "/api/auth/login",
                json={"email": "health_full@test.com", "password": "SecurePassword123!"},
            )
            token = log_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Project
        proj_resp = await ac.post(
            "/api/projects",
            json={"name": "Health Full Demo", "source_type": "zip"},
            headers=headers,
        )
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # 3. Upload ZIP
        zip_bytes = create_health_test_zip()
        upload_resp = await ac.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("project.zip", zip_bytes, "application/zip")},
            headers=headers,
        )
        assert upload_resp.status_code == 200

        # 4. Run Stage 4 Scan
        scan_resp = await ac.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_resp.status_code == 200

        # 5. Run Stage 5 Quality Analysis
        qual_resp = await ac.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
        assert qual_resp.status_code == 200

        # 6. Run Stage 6 Security Audit
        sec_resp = await ac.post(f"/api/projects/{project_id}/analyze/security", headers=headers)
        assert sec_resp.status_code == 200

        # 7. Run Stage 7 Dependency Analysis
        dep_resp = await ac.post(f"/api/projects/{project_id}/analyze/dependencies", headers=headers)
        assert dep_resp.status_code == 200

        # 8. Run Stage 8 Architecture Analysis
        arch_resp = await ac.post(f"/api/projects/{project_id}/analyze/architecture", headers=headers)
        assert arch_resp.status_code == 200

        # 9. Trigger Stage 9 Health Analysis
        h_resp = await ac.post(
            f"/api/projects/{project_id}/analyze/health",
            headers=headers,
        )
        assert h_resp.status_code == 200, f"Health analysis failed: {h_resp.json()}"
        data = h_resp.json()

        assert 0.0 <= data["overall_score"] <= 100.0
        assert 0.0 <= data["quality_score"] <= 100.0
        assert 0.0 <= data["security_score"] <= 100.0
        assert 0.0 <= data["dependency_score"] <= 100.0
        assert 0.0 <= data["architecture_score"] <= 100.0
        assert 0.0 <= data["maintainability_score"] <= 100.0
        assert 0.0 <= data["testing_score"] <= 100.0
        assert data["status"] in ("Excellent", "Good", "Fair", "Needs Attention", "Critical")
        assert "technical_debt_hours" in data
        assert "debt_breakdown" in data
        assert "fix_first" in data
        assert "explanations" in data
        assert "weights_used" in data

        # 10. Fetch Latest Health Diagnosis
        latest_resp = await ac.get(
            f"/api/projects/{project_id}/health",
            headers=headers,
        )
        assert latest_resp.status_code == 200
        assert latest_resp.json()["id"] == data["id"]

        # 11. Re-run Health Analysis (History Preservation)
        rerun_resp = await ac.post(
            f"/api/projects/{project_id}/analyze/health",
            headers=headers,
        )
        assert rerun_resp.status_code == 200
        second_id = rerun_resp.json()["id"]
        assert second_id != data["id"]

        # 12. Fetch History (should contain both runs)
        hist_resp = await ac.get(
            f"/api/projects/{project_id}/health/history",
            headers=headers,
        )
        assert hist_resp.status_code == 200
        history_list = hist_resp.json()
        assert len(history_list) >= 2
        assert history_list[0]["id"] == second_id
        assert history_list[1]["id"] == data["id"]

        # 13. Unauthorized access from another user should be forbidden (404)
        reg_user2 = await ac.post(
            "/api/auth/register",
            json={"name": "Attacker", "email": "attacker@test.com", "password": "Password123!"},
        )
        token2 = reg_user2.json().get("access_token")
        if not token2:
            log_user2 = await ac.post(
                "/api/auth/login",
                json={"email": "attacker@test.com", "password": "Password123!"},
            )
            token2 = log_user2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        unauth_resp = await ac.get(
            f"/api/projects/{project_id}/health",
            headers=headers2,
        )
        assert unauth_resp.status_code == 404
