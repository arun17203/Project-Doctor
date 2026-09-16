import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.models.dependency import DependencyAnalysis, DependencyIssue
from backend.app.models.health import HealthAnalysis
from backend.app.core.security import hash_password, create_access_token

client = TestClient(app)


@pytest.fixture
def test_users(db_session):
    u1 = User(
        email="doctor_user@example.com",
        name="Doctor User",
        password_hash=hash_password("DoctorSecret123!"),
        is_active=True,
    )
    u2 = User(
        email="other_user@example.com",
        name="Other User",
        password_hash=hash_password("OtherSecret123!"),
        is_active=True,
    )
    db_session.add_all([u1, u2])
    db_session.commit()
    db_session.refresh(u1)
    db_session.refresh(u2)
    return u1, u2


@pytest.fixture
def auth_headers(test_users):
    u1, _ = test_users
    token = create_access_token({"sub": u1.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(test_users):
    _, u2 = test_users
    token = create_access_token({"sub": u2.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_with_issues(db_session, test_users):
    u1, _ = test_users
    project = Project(
        user_id=u1.id,
        name="MedClinicApp",
        source_type="zip",
        status="READY",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # Add Security Analysis & Issue
    sec_analysis = SecurityAnalysis(
        project_id=project.id,
        scan_id="scan-123",
        status="COMPLETED",
        total_issues=1,
        critical_count=1,
    )
    db_session.add(sec_analysis)
    db_session.commit()

    sec_issue = SecurityIssue(
        analysis_id=sec_analysis.id,
        project_id=project.id,
        category="security",
        issue_type="hardcoded_secret",
        severity="CRITICAL",
        confidence="HIGH",
        file_path="app/config.py",
        line_number=14,
        symbol_name="STRIPE_KEY",
        message="Hardcoded Stripe API key detected in source code",
        description="Plaintext secret committed to repository",
        evidence="sk_live_***REDACTED***",
    )
    db_session.add(sec_issue)

    # Add Quality Analysis & Issue
    qual_analysis = QualityAnalysis(
        project_id=project.id,
        scan_id="scan-123",
        status="COMPLETED",
        total_issues=1,
        high_count=1,
    )
    db_session.add(qual_analysis)
    db_session.commit()

    qual_issue = QualityIssue(
        analysis_id=qual_analysis.id,
        project_id=project.id,
        issue_type="high_complexity",
        severity="HIGH",
        file_path="app/processor.py",
        line_number=45,
        symbol_name="process_transactions",
        message="Cyclomatic complexity exceeds threshold (18 > 10)",
        description="Function has excessive conditional branches",
        recommendation="Refactor into smaller helper functions",
    )
    db_session.add(qual_issue)

    # Add Dependency Analysis & Issue
    dep_analysis = DependencyAnalysis(
        project_id=project.id,
        scan_id="scan-123",
        status="COMPLETED",
        total_dependencies=5,
        vulnerable_count=1,
    )
    db_session.add(dep_analysis)
    db_session.commit()

    dep_issue = DependencyIssue(
        analysis_id=dep_analysis.id,
        project_id=project.id,
        package_name="requests",
        manifest_file="requirements.txt",
        version="2.20.0",
        vulnerability_id="CVE-2018-18074",
        issue_type="vulnerable_dependency",
        severity="HIGH",
        description="CVE-2018-18074 session fixation in requests",
        recommendation="Upgrade requests to 2.31.0",
    )
    db_session.add(dep_issue)

    # Add Health Analysis
    health = HealthAnalysis(
        project_id=project.id,
        repository_scan_id="scan-123",
        overall_score=62.5,
        technical_debt_hours=18.0,
        status="Needs Attention",
    )
    db_session.add(health)

    db_session.commit()
    return project


def test_get_project_prescription(auth_headers, project_with_issues):
    response = client.get(
        f"/api/projects/{project_with_issues.id}/remediation",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_with_issues.id
    assert data["project_name"] == "MedClinicApp"
    assert data["current_health_score"] == 62.5
    assert data["projected_health_score"] > 62.5
    assert data["total_prescriptions"] >= 3
    assert data["critical_count"] == 1
    assert "unified_diff" in data
    assert "--- a/app/config.py" in data["unified_diff"]
    assert "--- a/requirements.txt" in data["unified_diff"]
    assert data["patch_filename"].endswith(".patch")


def test_download_prescription_patch(auth_headers, project_with_issues):
    response = client.get(
        f"/api/projects/{project_with_issues.id}/remediation/download",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert ".patch" in response.headers["Content-Disposition"]
    content = response.text
    assert "--- a/app/config.py" in content
    assert "+++ b/app/config.py" in content


def test_remediation_access_isolation(other_auth_headers, project_with_issues):
    # Other user should be forbidden
    response = client.get(
        f"/api/projects/{project_with_issues.id}/remediation",
        headers=other_auth_headers,
    )
    assert response.status_code == 403
    assert "access" in response.json()["detail"].lower()


def test_remediation_not_found(auth_headers):
    response = client.get(
        "/api/projects/non-existent-uuid/remediation",
        headers=auth_headers,
    )
    assert response.status_code == 404
