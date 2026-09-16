import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.analyzers.security.secrets import HardcodedSecretRule, mask_line, mask_value
from backend.app.analyzers.security.injection import SQLInjectionRule, CommandInjectionRule
from backend.app.analyzers.security.dangerous_calls import DangerousCallsRule
from backend.app.analyzers.security.configuration import InsecureConfigurationRule
from backend.app.analyzers.security.crypto import WeakCryptographyRule
from backend.app.analyzers.security.password import InsecurePasswordRule
import ast


async def get_auth_token(client: AsyncClient, email: str, name: str) -> str:
    """Helper to register and login a test user."""
    await client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "SecurityPass123!"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurityPass123!"
    })
    return res.json()["access_token"]


def create_security_test_zip() -> bytes:
    """Creates a zip archive with intentional security vulnerabilities across categories:
    1. auth_service.py:
       - Hardcoded AWS key: AKIAIOSFODNN7EXAMPLE
       - Insecure password assignment: user.password = request.data['password']
       - Weak crypto: hashlib.md5(password.encode())
    2. db_service.py:
       - Unsafe SQL injection: cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")
       - Safe parameterized query: cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    3. runner.py:
       - Command injection: os.system("ping " + host)
       - Subprocess with shell=True: subprocess.run(cmd, shell=True)
    4. calc.py:
       - Dangerous eval: eval(formula)
    5. config.py:
       - Insecure config: DEBUG = True
       - Disabled SSL: requests.get(url, verify=False)
    6. broken.py:
       - Syntax error file to verify fault tolerance.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        auth_code = (
            "import hashlib\n"
            "AWS_KEY = \"AKIAIOSFODNN7EXAMPLE\"\n"
            "def register(request):\n"
            "    user = {}\n"
            "    user.password = request.data['password']\n"
            "    hashed = hashlib.md5(user.password.encode()).hexdigest()\n"
            "    return hashed\n"
        )
        zf.writestr("src/auth_service.py", auth_code)

        db_code = (
            "def query_user(cursor, user_input, user_id):\n"
            "    # Unsafe query\n"
            "    cursor.execute(f\"SELECT * FROM users WHERE username = '{user_input}'\")\n"
            "    # Safe parameterized query - must NOT be flagged\n"
            "    cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))\n"
        )
        zf.writestr("src/db_service.py", db_code)

        runner_code = (
            "import os\n"
            "import subprocess\n"
            "def execute_task(host, cmd):\n"
            "    os.system(\"ping \" + host)\n"
            "    subprocess.run(cmd, shell=True)\n"
            "    # Safe subprocess - should NOT be flagged\n"
            "    subprocess.run([\"ls\", \"-la\"], shell=False)\n"
        )
        zf.writestr("src/runner.py", runner_code)

        calc_code = (
            "def evaluate(formula):\n"
            "    return eval(formula)\n"
        )
        zf.writestr("src/calc.py", calc_code)

        config_code = (
            "import requests\n"
            "DEBUG = True\n"
            "def fetch_data(url):\n"
            "    return requests.get(url, verify=False)\n"
        )
        zf.writestr("src/config.py", config_code)

        broken_code = "def broken( : invalid syntax here {"
        zf.writestr("src/broken.py", broken_code)

    return buf.getvalue()


# ==========================================
# 1. UNIT TESTS FOR RULES
# ==========================================

def test_secret_masking_helper():
    assert mask_value("AKIAIOSFODNN7EXAMPLE") == "AKIA**************LE"
    assert "AKIA" in mask_value("AKIAIOSFODNN7EXAMPLE")
    assert "FODNN7" not in mask_value("AKIAIOSFODNN7EXAMPLE")
    assert mask_value("short") == "********"

    line = 'api_key = "sk-test-998877665544332211"'
    masked = mask_line(line)
    assert "998877" not in masked
    assert "********" in masked or "sk-t" in masked


def test_hardcoded_secret_rule():
    rule = HardcodedSecretRule()
    content = (
        'AWS_ACCESS_KEY = "AKIA1111111111EXAMPL"\n'
        'STRIPE_KEY = "' + "sk_" + 'test_1234567890abcdef12345678"\n'
        'PLACEHOLDER_KEY = "your_api_key_here"\n'
        'TEST_KEY = "test_key"\n'
    )
    findings = rule.run("config.py", content, ".py")
    # Should detect AWS and Stripe keys, but filter out placeholders
    assert len(findings) >= 2
    for f in findings:
        assert f.issue_type == "hardcoded_secret"
        assert f.evidence is not None
        assert "1111111111" not in f.evidence
        assert "1234567890" not in f.evidence


def test_sql_injection_rule_distinguishes_parameterized_queries():
    rule = SQLInjectionRule()
    content = (
        "def test_queries(cursor, val):\n"
        "    cursor.execute(f'SELECT * FROM users WHERE id = {val}')\n"
        "    cursor.execute('SELECT * FROM users WHERE id = ' + val)\n"
        "    cursor.execute('SELECT * FROM users WHERE id = %s', (val,))\n"
    )
    tree = ast.parse(content)
    findings = rule.run("db.py", content, ".py", ast_tree=tree)
    # Line 2 and 3 should be flagged, line 4 (safe parameterized) MUST NOT be flagged
    flagged_lines = [f.line_number for f in findings]
    assert 2 in flagged_lines
    assert 3 in flagged_lines
    assert 4 not in flagged_lines
    assert all(f.severity == "CRITICAL" for f in findings)


def test_command_injection_rule():
    rule = CommandInjectionRule()
    content = (
        "import os\n"
        "import subprocess\n"
        "def run_cmd(user_arg):\n"
        "    os.system('ping ' + user_arg)\n"
        "    subprocess.run(user_arg, shell=True)\n"
        "    subprocess.run(['ls', '-l'], shell=False)\n"
    )
    tree = ast.parse(content)
    findings = rule.run("exec.py", content, ".py", ast_tree=tree)
    flagged_lines = [f.line_number for f in findings]
    assert 4 in flagged_lines
    assert 5 in flagged_lines
    assert 6 not in flagged_lines


def test_dangerous_calls_rule():
    rule = DangerousCallsRule()
    content = (
        "def compute(user_code):\n"
        "    return eval(user_code)\n"
    )
    tree = ast.parse(content)
    findings = rule.run("eval.py", content, ".py", ast_tree=tree)
    assert len(findings) == 1
    assert findings[0].issue_type == "dangerous_eval"
    assert findings[0].severity == "CRITICAL"


def test_configuration_rule():
    rule = InsecureConfigurationRule()
    content = (
        "DEBUG = True\n"
        "requests.get('https://example.com', verify=False)\n"
    )
    findings = rule.run("settings.py", content, ".py")
    assert len(findings) == 2
    types = [f.issue_type for f in findings]
    assert "insecure_config" in types


def test_weak_crypto_rule():
    rule = WeakCryptographyRule()
    content = (
        "import hashlib\n"
        "def hash_password(password):\n"
        "    return hashlib.md5(password.encode()).hexdigest()\n"
    )
    findings = rule.run("crypto.py", content, ".py")
    assert len(findings) == 1
    assert findings[0].issue_type == "weak_crypto"
    assert findings[0].severity == "HIGH"


def test_insecure_password_rule():
    rule = InsecurePasswordRule()
    content = (
        "def save(request):\n"
        "    user.password = request.data['password']\n"
    )
    findings = rule.run("auth.py", content, ".py")
    assert len(findings) == 1
    assert findings[0].issue_type == "insecure_password"


# ==========================================
# 2. INTEGRATION TESTS (END-TO-END API)
# ==========================================

@pytest.mark.asyncio
async def test_full_security_audit_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "security_tester@test.com", "Security Tester")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project
        create_res = await client.post(
            "/api/projects",
            json={"name": "Security Audit Test Project", "description": "Testing Stage 6", "source_type": "zip"},
            headers=headers,
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Upload zip
        zip_bytes = create_security_test_zip()
        upload_res = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("security_project.zip", zip_bytes, "application/zip")},
            headers=headers,
        )
        assert upload_res.status_code == 200

        # 3. Must fail if scanned before repository scan
        audit_res_early = await client.post(
            f"/api/projects/{project_id}/analyze/security",
            headers=headers,
        )
        assert audit_res_early.status_code == 400
        assert "repository scan is required" in audit_res_early.json()["detail"]

        # 4. Perform Stage 4 repository scan
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200
        assert scan_res.json()["status"] == "COMPLETED"

        # 5. Trigger Stage 6 Security Audit
        audit_res = await client.post(
            f"/api/projects/{project_id}/analyze/security",
            headers=headers,
        )
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        assert audit_data["status"] == "COMPLETED"
        assert audit_data["total_issues"] > 0
        assert audit_data["critical_count"] > 0
        assert audit_data["high_count"] > 0
        assert audit_data["medium_count"] > 0

        # Verify metrics breakdown
        metrics = audit_data["metrics"]
        assert metrics["files_audited"] >= 5
        assert "by_category" in metrics
        assert "SECRETS" in metrics["by_category"]
        assert "INJECTION" in metrics["by_category"]

        # 6. Retrieve latest security analysis via GET
        get_res = await client.get(f"/api/projects/{project_id}/security", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == audit_data["id"]

        # 7. Retrieve security issues with severity filter
        crit_issues_res = await client.get(
            f"/api/projects/{project_id}/security/issues?severity=CRITICAL",
            headers=headers,
        )
        assert crit_issues_res.status_code == 200
        crit_issues = crit_issues_res.json()
        assert len(crit_issues) == audit_data["critical_count"]
        assert all(i["severity"] == "CRITICAL" for i in crit_issues)

        # 8. Check strict secret masking in all returned issues
        all_issues_res = await client.get(
            f"/api/projects/{project_id}/security/issues",
            headers=headers,
        )
        assert all_issues_res.status_code == 200
        all_issues = all_issues_res.json()
        for iss in all_issues:
            if iss["issue_type"] == "hardcoded_secret":
                assert iss["evidence"] is not None
                assert "AKIAIOSFODNN7EXAMPLE" not in iss["evidence"]
                assert "AKIA" in iss["evidence"] or "********" in iss["evidence"]

        # 9. Test masked code snippet endpoint
        secret_issue = next(i for i in all_issues if i["issue_type"] == "hardcoded_secret")
        snippet_res = await client.get(
            f"/api/projects/{project_id}/security/snippet?file_path={secret_issue['file_path']}&line_number={secret_issue['line_number']}&window=2",
            headers=headers,
        )
        assert snippet_res.status_code == 200
        snippet_data = snippet_res.json()
        assert snippet_data["target_line"] == secret_issue["line_number"]
        # Confirm that snippet also masks the secret
        raw_snippet_text = "\n".join(l["content"] for l in snippet_data["lines"])
        assert "AKIAIOSFODNN7EXAMPLE" not in raw_snippet_text

        # 10. Test directory traversal rejection in snippet
        traversal_res = await client.get(
            f"/api/projects/{project_id}/security/snippet?file_path=../../secret.txt&line_number=1",
            headers=headers,
        )
        assert traversal_res.status_code in {400, 403}

        # 11. Test unauthorized project access
        other_token = await get_auth_token(client, "other_user@test.com", "Other User")
        unauth_res = await client.get(
            f"/api/projects/{project_id}/security",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert unauth_res.status_code == 404
