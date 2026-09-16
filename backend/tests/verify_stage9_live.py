"""End-to-end live verification script for Stage 9: Health & Technical Debt Engine.
Tests live against http://127.0.0.1:8000:
1. User registration & login (JWT auth)
2. Project creation & ZIP upload containing realistic multi-tier project:
   - Python & JS/TS files with code quality issues (complexity, duplicates)
   - Security findings (hardcoded secret, eval)
   - Manifest with dependencies (requirements.txt with known CVE package)
   - Module imports connecting architecture layers
3. Prerequisites enforcement check:
   - Run Scan (Stage 4)
   - Call POST /analyze/health -> Verify HTTP 400 with prerequisites message
4. Execute Stages 5, 6, 7, 8 in sequence
5. Trigger Stage 9 Health Analysis (POST /api/projects/{id}/analyze/health)
6. Verify Health Analysis (GET /api/projects/{id}/health):
   - Overall score clamped [0.0, 100.0]
   - 6 dimension scores (quality, security, dependency, architecture, maintainability, testing)
   - Status categorization (Excellent, Good, Fair, Needs Attention, Critical)
   - Technical debt hours & category breakdown
   - Fix First prioritized action list
   - Deterministic explanations ("Why [Score]?")
   - Weights record
7. Multi-run history check (POST /analyze/health again -> GET /health/history has >= 2 records)
"""

import io
import sys
import time
import zipfile
import requests

BASE_URL = "http://127.0.0.1:8000/api"


def create_test_project_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Requirements manifest (known vulnerable flask version)
        zf.writestr(
            "requirements.txt",
            "flask==0.12.0\nrequests==2.25.1\nurllib3==1.26.4\npytest==7.4.0\n",
        )

        # Database / Data layer
        zf.writestr(
            "database.py",
            "class DB:\n    def connect(self):\n        pass\n",
        )

        # User model with security issue (hardcoded secret)
        zf.writestr(
            "models/user.py",
            "from database import DB\n\n"
            "JWT_SECRET = 'super_secret_master_key_12345'\n"
            "class User:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n",
        )

        # Service layer with high cyclomatic complexity and eval() security issue
        zf.writestr(
            "services/user_service.py",
            "from models.user import User\n"
            "from services.auth_service import verify_token\n\n"
            "def calculate_user_discount(tier, points, is_vip, coupon, has_referral, days_active):\n"
            "    discount = 0\n"
            "    if tier == 'platinum':\n"
            "        if points > 1000:\n"
            "            discount = 30\n"
            "        elif points > 500:\n"
            "            discount = 25\n"
            "        else:\n"
            "            discount = 20\n"
            "    elif tier == 'gold':\n"
            "        if is_vip:\n"
            "            discount = 20\n"
            "        elif coupon:\n"
            "            discount = 15\n"
            "        else:\n"
            "            discount = 10\n"
            "    elif tier == 'silver':\n"
            "        discount = 5 if days_active > 30 else 2\n"
            "    if has_referral and discount < 40:\n"
            "        discount += 5\n"
            "    return discount\n\n"
            "def dangerous_exec(user_code):\n"
            "    return eval(user_code)\n",
        )

        # Service layer - auth service (forms circular dependency with user_service)
        zf.writestr(
            "services/auth_service.py",
            "from services.user_service import calculate_user_discount\n\n"
            "def verify_token(token):\n"
            "    if token == 'valid':\n"
            "        return {'status': 'ok'}\n"
            "    return None\n",
        )

        # API Routes
        zf.writestr(
            "api/routes.py",
            "from services.user_service import calculate_user_discount\n"
            "from services.auth_service import verify_token\n\n"
            "def login_endpoint(token):\n"
            "    return verify_token(token)\n",
        )

        # Frontend Presentation component
        zf.writestr(
            "frontend/src/App.tsx",
            "import React from 'react';\n\n"
            "export const App = () => {\n"
            "    return <div>Project Doctor Live Test</div>;\n"
            "};\n",
        )

    return buf.getvalue()


def run_live_verification():
    print("================================================================")
    print("STAGE 9 LIVE VERIFICATION: Health & Technical Debt Engine")
    print("================================================================")

    session = requests.Session()

    # 1. Health check
    resp = session.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("[PASS] 1. Backend health check OK")

    # 2. Register & Login user
    email = f"health_tester_{int(time.time())}@test.com"
    password = "SecurePassword123!"
    reg_resp = session.post(
        f"{BASE_URL}/auth/register",
        json={"name": "Health Diagnostics Tester", "email": email, "password": password},
    )
    if reg_resp.status_code not in (200, 201, 400):
        raise AssertionError(f"Register failed: {reg_resp.text}")

    login_resp = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print(f"[PASS] 2. User registration and authentication OK (User: {email})")

    # 3. Create Project & Upload ZIP
    proj_resp = session.post(
        f"{BASE_URL}/projects",
        json={"name": "Health Diagnostic Test Repository", "description": "Multi-tier repository for testing Stage 9 diagnostic engine", "source_type": "zip"},
    )
    assert proj_resp.status_code in (200, 201), f"Create project failed: {proj_resp.text}"
    project_id = proj_resp.json()["id"]

    zip_bytes = create_test_project_zip()
    upload_resp = session.post(
        f"{BASE_URL}/projects/{project_id}/upload",
        files={"file": ("health_test_repo.zip", zip_bytes, "application/zip")},
    )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    print(f"[PASS] 3. Project created and ZIP uploaded OK (Project ID: {project_id})")

    # 4. Run Stage 4 Scan
    scan_resp = session.post(f"{BASE_URL}/projects/{project_id}/scan")
    assert scan_resp.status_code == 200, f"Scan failed: {scan_resp.text}"
    scan_data = scan_resp.json()
    print(f"[PASS] 4. Stage 4 Scan completed ({scan_data['total_files']} files, {scan_data['total_code_lines']} LOC)")

    # 5. Verify Prerequisites Enforcement: Call /analyze/health before stages 5-8
    print("Testing Stage 9 prerequisites enforcement (should fail with 400)...")
    pre_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/health")
    assert pre_resp.status_code == 400, f"Expected 400 when prerequisites missing, got {pre_resp.status_code}: {pre_resp.text}"
    err_detail = pre_resp.json().get("detail", "")
    assert "must be completed before Health Analysis can run" in err_detail or "Stage 5" in err_detail, f"Expected prerequisite message, got: {err_detail}"
    print(f"[PASS] 5. Prerequisites correctly enforced: {err_detail}")

    # 6. Execute Stages 5 through 8
    print("Running Stages 5 through 8 in sequence...")
    q_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/quality")
    assert q_resp.status_code in (200, 201), f"Quality analysis failed: {q_resp.text}"
    print(f"[PASS]    Stage 5 (Quality): {q_resp.json()['total_issues']} issues detected")

    s_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/security")
    assert s_resp.status_code in (200, 201), f"Security analysis failed: {s_resp.text}"
    print(f"[PASS]    Stage 6 (Security): {s_resp.json()['total_issues']} issues detected")

    d_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/dependencies")
    assert d_resp.status_code in (200, 201), f"Dependency analysis failed: {d_resp.text}"
    print(f"[PASS]    Stage 7 (Dependencies): {d_resp.json()['total_dependencies']} dependencies parsed")

    a_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/architecture")
    assert a_resp.status_code in (200, 201), f"Architecture analysis failed: {a_resp.text}"
    print(f"[PASS]    Stage 8 (Architecture): {a_resp.json()['node_count']} nodes, {a_resp.json()['cycle_count']} cycles detected")

    # 7. Execute Stage 9 Health Diagnostic
    print("Executing Stage 9 Master Health Diagnostic...")
    h_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/health")
    assert h_resp.status_code in (200, 201), f"Health analysis failed: {h_resp.text}"
    health = h_resp.json()
    print("[PASS] 7. Stage 9 Health Diagnostic executed successfully!")

    # 8. Verify all Health Metrics and Deterministic Calculations
    print("\n--- Diagnostic Scorecard ---")
    print(f"Overall Health Score:  {health['overall_score']:.1f}/100 ({health['status']})")
    print(f"Code Quality Score:    {health['quality_score']:.1f}/100")
    print(f"Security Score:        {health['security_score']:.1f}/100")
    print(f"Dependency Score:      {health['dependency_score']:.1f}/100")
    print(f"Architecture Score:    {health['architecture_score']:.1f}/100")
    print(f"Maintainability Score: {health['maintainability_score']:.1f}/100")
    print(f"Testing Score:         {health['testing_score']:.1f}/100")
    print(f"Technical Debt:        {health['technical_debt_hours']:.1f} hours")
    print(f"Severity Breakdown:    Critical={health['critical_count']}, High={health['high_count']}, Medium={health['medium_count']}, Low={health['low_count']}")

    assert 0.0 <= health["overall_score"] <= 100.0, f"Invalid overall score: {health['overall_score']}"
    assert 0.0 <= health["quality_score"] <= 100.0, f"Invalid quality score: {health['quality_score']}"
    assert 0.0 <= health["security_score"] <= 100.0, f"Invalid security score: {health['security_score']}"
    assert 0.0 <= health["dependency_score"] <= 100.0, f"Invalid dependency score: {health['dependency_score']}"
    assert 0.0 <= health["architecture_score"] <= 100.0, f"Invalid architecture score: {health['architecture_score']}"
    assert 0.0 <= health["maintainability_score"] <= 100.0, f"Invalid maintainability score: {health['maintainability_score']}"
    assert 0.0 <= health["testing_score"] <= 100.0, f"Invalid testing score: {health['testing_score']}"
    assert health["status"] in ["Excellent", "Good", "Fair", "Needs Attention", "Critical"], f"Invalid status: {health['status']}"
    assert health["technical_debt_hours"] > 0, "Technical debt hours should be > 0 given issues exist"
    assert isinstance(health["debt_breakdown"], dict), "debt_breakdown must be a dict"
    assert "quality_hours" in health["debt_breakdown"], "quality_hours missing in debt_breakdown"
    assert "security_hours" in health["debt_breakdown"], "security_hours missing in debt_breakdown"
    assert "dependency_hours" in health["debt_breakdown"], "dependency_hours missing in debt_breakdown"
    assert "architecture_hours" in health["debt_breakdown"], "architecture_hours missing in debt_breakdown"

    print("\n--- Technical Debt Breakdown ---")
    print(f"Quality Debt:       {health['debt_breakdown']['quality_hours']:.1f}h")
    print(f"Security Debt:      {health['debt_breakdown']['security_hours']:.1f}h")
    print(f"Dependency Debt:    {health['debt_breakdown']['dependency_hours']:.1f}h")
    print(f"Architecture Debt:  {health['debt_breakdown']['architecture_hours']:.1f}h")
    print(f"Total Debt:         {health['debt_breakdown']['total_hours']:.1f}h")

    # Fix First queue
    assert isinstance(health["fix_first"], list) and len(health["fix_first"]) > 0, "fix_first priority list must be non-empty"
    print(f"\n--- Top {min(5, len(health['fix_first']))} 'Fix First' Priorities ---")
    for idx, item in enumerate(health["fix_first"][:5], 1):
        print(f"  #{idx} [{item['category'].upper()}] ({item['severity'].upper()}) {item['title']} - {item['location']}")

    # Explanations
    assert isinstance(health["explanations"], dict), "explanations must be a dict"
    assert "summary" in health["explanations"], "summary missing in explanations"
    assert "why_breakdown" in health["explanations"], "why_breakdown missing in explanations"
    assert "category_drivers" in health["explanations"], "category_drivers missing in explanations"
    print(f"\nDiagnostic Summary Explanation:\n\"{health['explanations']['summary']}\"")
    for reason in health['explanations']['why_breakdown']:
        print(f"  - {reason}")
    print("[PASS] 8. Diagnostic scorecard, technical debt, and priority queue verified!")

    # 9. GET /projects/{id}/health
    get_resp = session.get(f"{BASE_URL}/projects/{project_id}/health")
    assert get_resp.status_code == 200, f"GET /health failed: {get_resp.text}"
    latest_health = get_resp.json()
    assert latest_health["id"] == health["id"], "GET /health returned wrong record"
    print("[PASS] 9. GET /api/projects/{id}/health returned latest analysis record")

    # 10. Re-run analysis & verify History Preservation
    print("Re-running health analysis to test history preservation...")
    h2_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/health")
    assert h2_resp.status_code in (200, 201), f"Second health run failed: {h2_resp.text}"
    h2_data = h2_resp.json()
    assert h2_data["id"] != health["id"], "Subsequent analysis must generate a new record ID"

    history_resp = session.get(f"{BASE_URL}/projects/{project_id}/health/history")
    assert history_resp.status_code == 200, f"GET /health/history failed: {history_resp.text}"
    history_list = history_resp.json()
    assert len(history_list) >= 2, f"Expected at least 2 history records, got {len(history_list)}"
    print(f"[PASS] 10. History preservation verified ({len(history_list)} records preserved in database)")

    print("================================================================")
    print("STAGE 9 LIVE VERIFICATION COMPLETE - ALL 10 TESTS PASSED!")
    print("================================================================")


if __name__ == "__main__":
    run_live_verification()
