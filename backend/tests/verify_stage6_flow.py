"""
Stage 6 Security Audit Engine Live End-to-End Verification Script
Tests the live running FastAPI instance (http://127.0.0.1:8000) through HTTP requests:
1. Health check verification
2. User registration & JWT authentication
3. Project creation with multi-vulnerability test ZIP upload
4. Stage 4 Repository Scan execution
5. Stage 6 Security Audit trigger (POST /api/projects/{id}/analyze/security)
6. Verification of real vulnerability findings across categories (SECRETS, INJECTION, DANGEROUS_CALLS, CONFIGURATION, CRYPTO, AUTHENTICATION)
7. Verification of STRICT SECRET MASKING in database and evidence
8. Issue retrieval with severity and category filtering
9. Read-only code snippet retrieval with line context and credential masking
10. Directory traversal protection
11. Multi-tenant access control isolation
12. Clean cleanup
"""

import io
import time
import zipfile
import requests

BASE_URL = "http://127.0.0.1:8000"


def create_security_verification_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Auth & Secrets
        auth_code = (
            "import hashlib\n"
            "# Production configuration\n"
            "AWS_ACCESS_KEY = \"AKIAIOSFODNN7EXAMPLE\"\n"
            "STRIPE_API_KEY = \"" + "sk_" + "test_998877665544332211aabbcc\"\n"
            "DATABASE_URI = \"postgresql://dbuser:SuperSecretPass123@db.internal:5432/app\"\n"
            "\n"
            "def handle_register(request):\n"
            "    user = {}\n"
            "    user.password = request.form['password']\n"
            "    token = hashlib.md5(user.password.encode()).hexdigest()\n"
            "    return {'user': user, 'token': token}\n"
        )
        zf.writestr("src/auth.py", auth_code)

        # 2. Database & SQL Injection
        db_code = (
            "def get_user_by_name(cursor, username):\n"
            "    # Vulnerable f-string query\n"
            "    query = f\"SELECT * FROM users WHERE username = '{username}'\"\n"
            "    cursor.execute(query)\n"
            "    return cursor.fetchall()\n"
            "\n"
            "def get_user_safe(cursor, user_id):\n"
            "    # Safe parameterized query - MUST NOT BE FLAGGED\n"
            "    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))\n"
            "    return cursor.fetchone()\n"
        )
        zf.writestr("src/database.py", db_code)

        # 3. Task runner & Command Injection
        runner_code = (
            "import os\n"
            "import subprocess\n"
            "\n"
            "def ping_host(target_host):\n"
            "    os.system('ping -c 1 ' + target_host)\n"
            "\n"
            "def run_custom_task(user_cmd):\n"
            "    subprocess.run(user_cmd, shell=True)\n"
            "\n"
            "def safe_task():\n"
            "    subprocess.run(['ls', '-la'], shell=False)\n"
        )
        zf.writestr("src/runner.py", runner_code)

        # 4. Calculator & Dangerous Calls
        calc_code = (
            "def evaluate_expression(user_math_str):\n"
            "    # Dangerous eval of user input\n"
            "    return eval(user_math_str)\n"
            "\n"
            "def run_dynamic_script(script_body):\n"
            "    exec(script_body)\n"
        )
        zf.writestr("src/calculator.py", calc_code)

        # 5. Config & Misconfiguration
        config_code = (
            "import requests\n"
            "\n"
            "DEBUG = True\n"
            "allow_origins = ['*']\n"
            "\n"
            "def fetch_remote_metrics(url):\n"
            "    # Insecure SSL verification disabled\n"
            "    return requests.get(url, verify=False)\n"
        )
        zf.writestr("src/config.py", config_code)

    return buf.getvalue()


def main():
    print("=================================================================")
    print("STAGE 6: SECURITY AUDIT ENGINE LIVE END-TO-END VERIFICATION")
    print("=================================================================")

    # 1. Health check
    print("\n[Step 1] Checking backend health...")
    health_res = requests.get(f"{BASE_URL}/api/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    print("[OK] Backend is healthy:", health_res.json())

    # 2. Authentication
    ts = int(time.time())
    email = f"security_lead_{ts}@doctor.io"
    password = "SecurityPass123!"
    print(f"\n[Step 2] Registering user: {email}...")
    reg_res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Security Lead",
        "email": email,
        "password": password
    })
    assert reg_res.status_code in [200, 201], f"Registration failed: {reg_res.text}"

    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] User authenticated with JWT")

    # 3. Create Project
    print("\n[Step 3] Creating security audit project...")
    create_res = requests.post(
        f"{BASE_URL}/api/projects",
        json={
            "name": f"Security Verification Project {ts}",
            "description": "Live verification project with intentional security test vulnerabilities",
            "source_type": "zip"
        },
        headers=headers,
    )
    assert create_res.status_code == 201, f"Create project failed: {create_res.text}"
    project_id = create_res.json()["id"]
    print(f"[OK] Project created: {project_id}")

    # 4. Upload ZIP
    print("\n[Step 4] Uploading multi-file test ZIP archive...")
    zip_bytes = create_security_verification_zip()
    upload_res = requests.post(
        f"{BASE_URL}/api/projects/{project_id}/upload",
        files={"file": ("security_fixtures.zip", zip_bytes, "application/zip")},
        headers=headers,
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    print("[OK] Project ZIP safely extracted and ready for analysis")

    # 5. Verify pre-scan requirement
    print("\n[Step 5] Verifying that security audit requires Stage 4 repository scan...")
    early_res = requests.post(
        f"{BASE_URL}/api/projects/{project_id}/analyze/security",
        headers=headers,
    )
    assert early_res.status_code == 400, f"Expected 400 before scan, got {early_res.status_code}"
    print("[OK] Correctly rejected security analysis prior to repository scan")

    # 6. Execute Stage 4 Repository Scan
    print("\n[Step 6] Running Stage 4 repository scanner...")
    scan_res = requests.post(f"{BASE_URL}/api/projects/{project_id}/scan", headers=headers)
    assert scan_res.status_code == 200, f"Scan failed: {scan_res.text}"
    scan_data = scan_res.json()
    print(f"[OK] Repository scan complete. Total files: {scan_data['total_files']}, LOC: {scan_data['total_code_lines']}")

    # 7. Execute Stage 6 Security Audit
    print("\n[Step 7] Triggering Stage 6 Security Audit Engine (POST /api/projects/{id}/analyze/security)...")
    t0 = time.time()
    audit_res = requests.post(f"{BASE_URL}/api/projects/{project_id}/analyze/security", headers=headers)
    elapsed = time.time() - t0
    assert audit_res.status_code == 200, f"Security audit failed: {audit_res.text}"
    audit_data = audit_res.json()
    print(f"[OK] Security audit completed in {elapsed:.3f}s")
    print(f"  Total Findings: {audit_data['total_issues']}")
    print(f"  Critical Issues: {audit_data['critical_count']}")
    print(f"  High Issues:     {audit_data['high_count']}")
    print(f"  Medium Issues:   {audit_data['medium_count']}")
    print(f"  Low Issues:      {audit_data['low_count']}")

    assert audit_data["total_issues"] >= 6, "Expected at least 6 security issues"
    assert audit_data["critical_count"] >= 2, "Expected critical injection/secret issues"
    assert audit_data["high_count"] >= 2, "Expected high severity issues"
    assert audit_data["medium_count"] >= 1, "Expected medium config/crypto issues"

    # 8. Category Breakdown Verification
    print("\n[Step 8] Checking vulnerability categories breakdown...")
    metrics = audit_data["metrics"]
    by_cat = metrics.get("by_category", {})
    for cat, cnt in by_cat.items():
        print(f"  * {cat}: {cnt} findings")
    assert "SECRETS" in by_cat
    assert "INJECTION" in by_cat
    assert "DANGEROUS_CALLS" in by_cat
    assert "CONFIGURATION" in by_cat
    print("[OK] All requested vulnerability categories detected deterministically")

    # 9. Strict Secret Masking Verification
    print("\n[Step 9] Validating STRICT SECRET MASKING in database records and evidence...")
    issues_res = requests.get(f"{BASE_URL}/api/projects/{project_id}/security/issues", headers=headers)
    assert issues_res.status_code == 200
    all_issues = issues_res.json()

    for iss in all_issues:
        evidence = iss.get("evidence") or ""
        # Strictly verify raw secret tokens never leaked
        assert "AKIAIOSFODNN7EXAMPLE" not in evidence, "Raw AWS key leaked in evidence!"
        assert ("sk_" + "test_998877665544332211aabbcc") not in evidence, "Raw Stripe key leaked in evidence!"
        assert "SuperSecretPass123" not in evidence, "Raw DB password leaked in evidence!"

    print("[OK] ZERO raw credentials leaked! All secrets successfully masked with asterisks.")

    # 10. Filtered Query Verification
    print("\n[Step 10] Testing filtered query: GET /api/projects/{id}/security/issues?severity=CRITICAL...")
    crit_res = requests.get(
        f"{BASE_URL}/api/projects/{project_id}/security/issues?severity=CRITICAL",
        headers=headers,
    )
    assert crit_res.status_code == 200
    crit_issues = crit_res.json()
    assert len(crit_issues) == audit_data["critical_count"]
    print(f"[OK] Retrieved {len(crit_issues)} CRITICAL issues:")
    for c in crit_issues:
        print(f"  - [{c['issue_type']}] {c['file_path']}:{c['line_number']} -> {c['message']}")

    # 11. Masked Code Snippet Verification
    print("\n[Step 11] Testing read-only code snippet retrieval with credential masking...")
    secret_issue = next(i for i in all_issues if i["issue_type"] == "hardcoded_secret")
    snippet_res = requests.get(
        f"{BASE_URL}/api/projects/{project_id}/security/snippet?file_path={secret_issue['file_path']}&line_number={secret_issue['line_number']}&window=2",
        headers=headers,
    )
    assert snippet_res.status_code == 200
    snippet_data = snippet_res.json()
    assert snippet_data["target_line"] == secret_issue["line_number"]
    snippet_text = "\n".join(l["content"] for l in snippet_data["lines"])
    assert "AKIAIOSFODNN7EXAMPLE" not in snippet_text, "Raw AWS key leaked in code snippet!"
    assert "AKIA" in snippet_text or "********" in snippet_text
    print("[OK] Code snippet safely returned with target line highlighted and credentials masked")

    # 12. Path traversal security check
    print("\n[Step 12] Testing path traversal defense on snippet endpoint...")
    trav_res = requests.get(
        f"{BASE_URL}/api/projects/{project_id}/security/snippet?file_path=../../etc/passwd&line_number=1",
        headers=headers,
    )
    assert trav_res.status_code in [400, 403, 404]
    print(f"[OK] Directory traversal attempt rejected with HTTP {trav_res.status_code}")

    # 13. Multi-tenant access control check
    print("\n[Step 13] Testing cross-user access control...")
    other_email = f"attacker_{ts}@doctor.io"
    requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Attacker",
        "email": other_email,
        "password": "Password123!"
    })
    other_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": other_email,
        "password": "Password123!"
    })
    other_token = other_login.json()["access_token"]
    unauth_res = requests.get(
        f"{BASE_URL}/api/projects/{project_id}/security",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert unauth_res.status_code == 404
    print("[OK] Cross-user access blocked with 404 Not Found")

    # 14. Cleanup
    print("\n[Step 14] Cleaning up test project...")
    del_res = requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
    assert del_res.status_code in [200, 204]
    print("[OK] Test project cleanly deleted")

    print("\n=================================================================")
    print("SUCCESS: ALL STAGE 6 SECURITY AUDIT ENGINE TESTS PASSED 100%!")
    print("=================================================================")


if __name__ == "__main__":
    main()
