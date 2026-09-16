"""
Stage 5 Code Quality Analyzer Live End-to-End Verification Script
Tests the running FastAPI instance (http://127.0.0.1:8000) through HTTP requests:
1. User registration & JWT authentication
2. Project creation with ZIP upload containing intentional quality test fixtures
3. Stage 4 Repository Scan execution
4. Stage 5 Code Quality Analysis trigger (POST /api/projects/{id}/analyze/quality)
5. Real issue tallies: total, critical, high, medium, low
6. Maintainability metrics verification (complexity, lengths, duplicates, TODOs, unused imports)
7. Querying issues with severity filtering
8. Code snippet retrieval with credential masking
9. Access control validation (unauthorized user blocked)
10. Cleanup
"""

import io
import time
import zipfile
import requests

BASE_URL = "http://127.0.0.1:8000"


def create_verification_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Complex Python file (AST analysis)
        complex_py = (
            "import os\n"
            "import unused_telemetry_pkg\n"
            "\n"
            "# TODO: refactor order validation logic\n"
            "def validate_order(user, cart, promo, shipping, flags, retry, debug, mode):\n"
            "    score = 0\n"
            "    if user and cart and promo:\n"
            "        score += 1\n"
            "    elif user or cart or promo:\n"
            "        score -= 1\n"
            "    if shipping:\n"
            "        for item in cart:\n"
            "            if item.price > 100:\n"
            "                score += 5\n"
            "            elif item.price > 50:\n"
            "                score += 2\n"
            "    while retry > 0:\n"
            "        retry -= 1\n"
            "        if flags and debug:\n"
            "            score += 1\n"
            "    try:\n"
            "        if mode:\n"
            "            assert score != 0\n"
            "    except Exception:\n"
            "        pass\n"
            "    return score if score > 0 else (1 if mode == 'fast' else 0)\n"
            "\n"
            "def nested_calculator(n):\n"
            "    if n > 0:\n"
            "        for i in range(10):\n"
            "            if i % 2 == 0:\n"
            "                while n > 5:\n"
            "                    n -= 1\n"
            "    return n\n"
        )
        zf.writestr("src/orders/validator.py", complex_py)

        # 2. Long Python function (>50 lines)
        long_lines = [
            "# FIXME: optimize database transaction duration",
            "def batch_process_records():",
            "    accumulator = 0",
        ]
        for idx in range(55):
            long_lines.append(f"    accumulator += {idx}  # compute step {idx}")
        long_lines.append("    return accumulator")
        zf.writestr("src/jobs/batch.py", "\n".join(long_lines))

        # 3. Duplicate code across two modules (12 lines)
        shared_algorithm = (
            "def compute_discount_rate(customer_tier, order_volume, season):\n"
            "    base_discount = customer_tier * 0.02\n"
            "    if order_volume > 1000:\n"
            "        volume_bonus = 0.05\n"
            "    elif order_volume > 500:\n"
            "        volume_bonus = 0.03\n"
            "    else:\n"
            "        volume_bonus = 0.01\n"
            "    seasonal_factor = 1.1 if season == 'holiday' else 1.0\n"
            "    net_rate = min(0.30, (base_discount + volume_bonus) * seasonal_factor)\n"
            "    return round(net_rate, 4)\n"
        )
        zf.writestr("src/discounts/standard.py", f"# Standard pricing\n{shared_algorithm}\n")
        zf.writestr("src/discounts/promotional.py", f"# Promo pricing\n{shared_algorithm}\n")

        # 4. JavaScript nested function
        js_code = (
            "// High nesting JS function\n"
            "// TODO: convert to async stream\n"
            "function processEvents(events, ctx) {\n"
            "    if (events && ctx) {\n"
            "        for (let i = 0; i < events.length; i++) {\n"
            "            if (events[i].active) {\n"
            "                while (ctx.limit > 0) {\n"
            "                    ctx.limit--;\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return true;\n"
            "}\n"
        )
        zf.writestr("frontend/src/events.js", js_code)

        # 5. Broken syntax file to test fault-tolerance
        zf.writestr("src/invalid_file.py", "def syntax_failure(\n    unmatched bracket (\n")

        # 6. File with dummy credential to test read-only snippet masking
        zf.writestr("config/settings.py", "api_key = \"super_secret_token_12345\"\nDEBUG = False\n")

    return buf.getvalue()


def run_verification():
    print("=" * 70)
    print("STAGE 5: CODE QUALITY ANALYZER LIVE E2E VERIFICATION")
    print("=" * 70)

    session = requests.Session()
    ts = int(time.time())
    email = f"quality_user_{ts}@doctor.io"
    password = "QualityPass123!"

    # 1. Health check
    print("\n[Step 1] Checking backend health...")
    r = session.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health_data = r.json()
    print(f"  --> Status: {health_data['status']}, Database: {health_data['database']}")

    # 2. Register user
    print(f"\n[Step 2] Registering user {email}...")
    r = session.post(f"{BASE_URL}/api/auth/register", json={
        "name": f"Quality Lead {ts}",
        "email": email,
        "password": password
    })
    assert r.status_code in (200, 201), f"Registration failed: {r.text}"
    token = r.json().get("access_token")
    if not token:
        r_login = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  --> Authenticated successfully!")

    # 3. Create project
    print("\n[Step 3] Creating project...")
    r = session.post(
        f"{BASE_URL}/api/projects",
        json={
            "name": f"Quality Live Test {ts}",
            "description": "Multi-language project with intentional quality issues",
            "source_type": "zip"
        },
        headers=headers
    )
    assert r.status_code in (200, 201), f"Project creation failed: {r.text}"
    proj = r.json()
    project_id = proj["id"]
    print(f"  --> Project created with ID: {project_id}")

    # 4. Upload ZIP
    print("\n[Step 4] Uploading structured ZIP archive...")
    zip_bytes = create_verification_zip()
    r = session.post(
        f"{BASE_URL}/api/projects/{project_id}/upload",
        files={"file": ("quality_project.zip", zip_bytes, "application/zip")},
        headers=headers
    )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    proj = r.json()
    assert proj["status"] == "READY"
    print("  --> Project uploaded and ready!")

    # 5. Verify Quality Analysis fails without Stage 4 scan
    print("\n[Step 5] Verifying quality analysis blocked before repository scan...")
    r = session.post(f"{BASE_URL}/api/projects/{project_id}/analyze/quality", headers=headers)
    assert r.status_code == 400, f"Expected 400 before scan, got {r.status_code}"
    print("  --> Correctly rejected with 400 (Stage 4 scan required)")

    # 6. Execute Stage 4 Repository Scan
    print("\n[Step 6] Running Stage 4 Repository Scan...")
    r = session.post(f"{BASE_URL}/api/projects/{project_id}/scan", headers=headers)
    assert r.status_code == 200, f"Scan failed: {r.text}"
    scan_data = r.json()
    assert scan_data["status"] == "COMPLETED"
    print(f"  --> Scan completed: {scan_data['total_files']} files, {scan_data['total_code_lines']} LOC")

    # 7. Execute Stage 5 Code Quality Analysis
    print("\n[Step 7] Running Stage 5 Code Quality Analysis (POST /api/projects/{id}/analyze/quality)...")
    r = session.post(f"{BASE_URL}/api/projects/{project_id}/analyze/quality", headers=headers)
    assert r.status_code == 200, f"Quality analysis failed: {r.text}"
    qa = r.json()
    print("  --> Code Quality Analysis completed successfully!")
    print(f"      Status: {qa['status']}")
    print(f"      Total Issues Detected: {qa['total_issues']}")
    print(f"      - Critical: {qa['critical_count']}")
    print(f"      - High:     {qa['high_count']}")
    print(f"      - Medium:   {qa['medium_count']}")
    print(f"      - Low:      {qa['low_count']}")

    assert qa["status"] == "COMPLETED"
    assert qa["total_issues"] > 0
    assert qa["critical_count"] >= 1, "Expected at least 1 critical complexity issue"
    assert qa["medium_count"] >= 1, "Expected medium issues (long function, deep nesting, duplicate)"
    assert qa["low_count"] >= 1, "Expected low issues (unused import, TODO)"

    metrics = qa["metrics"]
    print("\n      Maintainability Metrics:")
    print(f"      - Avg Complexity:       {metrics['avg_complexity']}")
    print(f"      - Max Complexity:       {metrics['max_complexity']}")
    print(f"      - Avg Function Length:  {metrics['avg_function_length']} lines")
    print(f"      - Max Function Length:  {metrics['max_function_length']} lines")
    print(f"      - Total Functions:      {metrics['total_functions']}")
    print(f"      - Duplicate Blocks:     {metrics['duplicate_blocks_count']}")
    print(f"      - Unused Imports:       {metrics['unused_imports_count']}")
    print(f"      - Technical Debt Tags:  {metrics['todo_comments_count']}")
    print(f"      - Files Analyzed:       {metrics['files_analyzed']}")
    print(f"      - Unparseable Files:    {metrics['unparseable_files']}")

    assert metrics["max_complexity"] >= 16
    assert metrics["max_function_length"] >= 50
    assert metrics["duplicate_blocks_count"] >= 1
    assert metrics["unparseable_files"] == 1  # invalid_file.py handled gracefully

    # 8. Query Latest Analysis via GET /quality
    print("\n[Step 8] Querying latest analysis (GET /api/projects/{id}/quality)...")
    r = session.get(f"{BASE_URL}/api/projects/{project_id}/quality", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == qa["id"]
    print("  --> Confirmed persistence in database!")

    # 9. Query Issues with Severity Filtering
    print("\n[Step 9] Querying Issues list and filtering by severity...")
    r = session.get(f"{BASE_URL}/api/projects/{project_id}/quality/issues?severity=CRITICAL", headers=headers)
    assert r.status_code == 200
    crit_issues = r.json()
    assert len(crit_issues) == qa["critical_count"]
    print(f"  --> Filtered CRITICAL issues count: {len(crit_issues)}")
    for c in crit_issues:
        print(f"      * [{c['severity']}] {c['issue_type']}: {c['file_path']}:{c['line_number']} -> {c['evidence']}")

    # 10. Query Read-Only Code Snippet with Credential Masking
    print("\n[Step 10] Testing read-only code snippet endpoint with credential masking...")
    r = session.get(
        f"{BASE_URL}/api/projects/{project_id}/quality/snippet?file_path=config/settings.py&line_number=1&window=2",
        headers=headers
    )
    assert r.status_code == 200
    snippet_data = r.json()
    print("  --> Snippet lines:")
    for l in snippet_data["lines"]:
        print(f"      {l['line_number']:2d} | {l['content']}")
        if "api_key" in l["content"]:
            assert "********" in l["content"], "Secret was not masked in snippet!"
            assert "super_secret_token" not in l["content"], "Plaintext secret leaked!"
    print("  --> Credential safely masked as '********'!")

    # 11. Test Security & Access Control
    print("\n[Step 11] Testing security isolation...")
    unauth_headers = {"Authorization": "Bearer invalid_bearer_token"}
    r = session.get(f"{BASE_URL}/api/projects/{project_id}/quality", headers=unauth_headers)
    assert r.status_code == 401
    print("  --> Invalid authentication properly blocked with 401")

    # 12. Cleanup
    print("\n[Step 12] Cleaning up test project...")
    r = session.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
    assert r.status_code in (200, 204)
    print("  --> Test project deleted cleanly!")

    print("\n" + "=" * 70)
    print(">>> ALL STAGE 5 QUALITY ANALYZER CHECKS PASSED LIVE! <<<")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
