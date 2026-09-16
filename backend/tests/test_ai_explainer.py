import io
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.ai.client import GeminiClient, AIUnavailableError, AIExplanationError
from backend.app.ai.schemas import AIExplanationOutput
from backend.app.ai.sanitizer import extract_relevant_snippet, mask_sensitive_snippet


def test_gemini_client_availability():
    client_empty = GeminiClient(api_key=None)
    assert not client_empty.is_available()

    client_placeholder = GeminiClient(api_key="your_gemini_api_key_here")
    assert not client_placeholder.is_available()

    client_valid = GeminiClient(api_key="AIzaSyRealApiKeyExample123")
    assert client_valid.is_available()


def test_sanitizer_snippet_and_masking(tmp_path):
    # Test directory traversal defense
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("secret = 'danger'")

    assert extract_relevant_snippet(str(project_dir), "../outside.py", 1) is None

    # Test .env file blocked
    env_file = project_dir / ".env"
    env_file.write_text("SECRET=12345")
    assert extract_relevant_snippet(str(project_dir), ".env", 1) is None

    # Test valid source file snippet extraction & masking
    code_file = project_dir / "service.py"
    code_file.write_text(
        "import os\n"
        "def run():\n"
        "    password = 'supersecretpassword123'\n"
        "    header = 'Authorization: Bearer abcdef123456'\n"
        "    return 42\n"
    )

    snippet = extract_relevant_snippet(str(project_dir), "service.py", 3, radius=2)
    assert snippet is not None
    assert "supersecretpassword123" not in snippet
    assert "***REDACTED***" in snippet
    assert "Bearer ***REDACTED_TOKEN***" in snippet
    assert " >    3 |" in snippet  # Line indicator


@pytest.mark.asyncio
async def test_ai_explainer_full_flow_with_mock():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register User A
        email_a = "ai_user_a@test.com"
        reg_a = await ac.post(
            "/api/auth/register",
            json={"name": "User A", "email": email_a, "password": "Password123!"},
        )
        assert reg_a.status_code in (200, 201)
        login_a = await ac.post("/api/auth/login", json={"email": email_a, "password": "Password123!"})
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Upload project with quality, security, and dependency issues
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "app.py",
                "import os\n"
                "import unused_module\n"
                "# TODO: fix this\n"
                "API_KEY = 'AKIA1234567890EXAMPLE'\n"
                "def complex_func(a, b, c, d, e, f):\n"
                "    res = 0\n"
                "    if a:\n"
                "        if b:\n"
                "            res += 1\n"
                "    elif c:\n"
                "        res += 2\n"
                "    for i in range(10):\n"
                "        if d:\n"
                "            res += i\n"
                "        elif e:\n"
                "            res -= i\n"
                "    while f > 0:\n"
                "        f -= 1\n"
                "    return eval(str(res))\n",
            )
            zf.writestr("requirements.txt", "flask==0.12.0\n")

        p_res = await ac.post(
            "/api/projects",
            json={"name": "AI Test App", "source_type": "zip"},
            headers=headers_a,
        )
        project_id = p_res.json()["id"]

        up_res = await ac.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("test.zip", buf.getvalue(), "application/zip")},
            headers=headers_a,
        )
        assert up_res.status_code == 200

        # Scan & analyze quality, security, dependencies
        await ac.post(f"/api/projects/{project_id}/scan", headers=headers_a)
        q_res = await ac.post(f"/api/projects/{project_id}/analyze/quality", headers=headers_a)
        s_res = await ac.post(f"/api/projects/{project_id}/analyze/security", headers=headers_a)
        d_res = await ac.post(f"/api/projects/{project_id}/analyze/dependencies", headers=headers_a)

        # Get quality issues
        q_issues_res = await ac.get(f"/api/projects/{project_id}/quality/issues", headers=headers_a)
        q_issues = q_issues_res.json()
        assert len(q_issues) > 0
        quality_issue_id = q_issues[0]["id"]

        # Get security issues
        s_issues_res = await ac.get(f"/api/projects/{project_id}/security/issues", headers=headers_a)
        s_issues = s_issues_res.json()
        assert len(s_issues) > 0
        security_issue_id = s_issues[0]["id"]

        # 3. Test Missing API Key -> Returns 503 Service Unavailable
        with patch.object(GeminiClient, "is_available", return_value=False):
            err_res = await ac.post(
                f"/api/issues/{quality_issue_id}/explain",
                headers=headers_a,
            )
            assert err_res.status_code == 503
            assert "AI explanation is currently unavailable" in err_res.json()["detail"]

        # 4. Test Successful Explanation with Mock Gemini
        mock_output = AIExplanationOutput(
            summary="Function complex_func exhibits elevated cyclomatic complexity.",
            why_it_matters="Nested conditional branches increase mental overhead and make testing difficult.",
            potential_impact="Future changes can introduce regression bugs due to untested branch combinations.",
            recommendation="Extract the inner conditional logic into a discrete helper function.",
            priority="High",
            developer_action="Refactor complex_func into smaller single-responsibility methods.",
        )

        with patch.object(GeminiClient, "generate_explanation", return_value=mock_output) as mock_gen:
            with patch.object(GeminiClient, "is_available", return_value=True):
                exp_res = await ac.post(
                    f"/api/issues/{quality_issue_id}/explain",
                    headers=headers_a,
                )
                assert exp_res.status_code == 200
                data = exp_res.json()
                assert data["summary"] == mock_output.summary
                assert data["why_it_matters"] == mock_output.why_it_matters
                assert data["recommendation"] == mock_output.recommendation
                assert data["priority"] == "High"
                assert data["issue_id"] == quality_issue_id
                assert data["provider"] == "google-gemini"
                mock_gen.assert_called_once()

        # 5. Test Caching: Calling explain again should NOT call Gemini again
        with patch.object(GeminiClient, "generate_explanation") as mock_gen_cached:
            cached_res = await ac.post(
                f"/api/issues/{quality_issue_id}/explain",
                headers=headers_a,
            )
            assert cached_res.status_code == 200
            assert cached_res.json()["id"] == data["id"]
            mock_gen_cached.assert_not_called()

        # 6. Test GET existing explanation endpoint
        get_res = await ac.get(f"/api/issues/{quality_issue_id}/explanation", headers=headers_a)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == data["id"]

        # 7. Test Explicit Regeneration
        mock_updated = AIExplanationOutput(
            summary="Updated summary after regeneration.",
            why_it_matters="Updated why it matters.",
            potential_impact="Updated potential impact.",
            recommendation="Updated recommendation.",
            priority="High",
            developer_action="Updated action plan.",
        )
        with patch.object(GeminiClient, "generate_explanation", return_value=mock_updated) as mock_regen:
            with patch.object(GeminiClient, "is_available", return_value=True):
                regen_res = await ac.post(
                    f"/api/issues/{quality_issue_id}/explanation/regenerate",
                    headers=headers_a,
                )
                assert regen_res.status_code == 200
                regen_data = regen_res.json()
                assert regen_data["summary"] == "Updated summary after regeneration."
                assert regen_data["id"] == data["id"]  # Preserves same record ID
                mock_regen.assert_called_once()

        # 8. Test Security Issue Explanation (Masked Evidence Passed)
        sec_mock_output = AIExplanationOutput(
            summary="Potential hardcoded credential detected.",
            why_it_matters="Committing credentials to repositories exposes infrastructure to unauthorized access.",
            potential_impact="Attackers with repository read access can compromise cloud services.",
            recommendation="Store credentials in environment variables and access via os.environ.",
            priority="Critical",
            developer_action="Revoke the exposed key immediately and migrate to secret management.",
        )
        with patch.object(GeminiClient, "generate_explanation", return_value=sec_mock_output) as mock_sec_gen:
            with patch.object(GeminiClient, "is_available", return_value=True):
                sec_exp_res = await ac.post(
                    f"/api/issues/{security_issue_id}/explain",
                    headers=headers_a,
                )
                assert sec_exp_res.status_code == 200
                sec_data = sec_exp_res.json()
                assert sec_data["priority"] == "Critical"
                mock_sec_gen.assert_called_once()

        # 9. Test Cross-User Isolation (User B cannot explain User A's issue)
        email_b = "ai_user_b@test.com"
        await ac.post(
            "/api/auth/register",
            json={"name": "User B", "email": email_b, "password": "Password123!"},
        )
        login_b = await ac.post("/api/auth/login", json={"email": email_b, "password": "Password123!"})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        unauth_res = await ac.post(
            f"/api/issues/{quality_issue_id}/explain",
            headers=headers_b,
        )
        assert unauth_res.status_code == 403

        # 10. Test Non-existent Issue returns 404
        non_res = await ac.post("/api/issues/non-existent-uuid-12345/explain", headers=headers_a)
        assert non_res.status_code == 404

        # 11. Test Gemini API Failure returns 502 Bad Gateway
        with patch.object(GeminiClient, "is_available", return_value=True):
            with patch.object(GeminiClient, "generate_explanation", side_effect=AIExplanationError("Provider timeout")):
                fail_res = await ac.post(
                    f"/api/issues/{security_issue_id}/explanation/regenerate",
                    headers=headers_a,
                )
                assert fail_res.status_code == 502
                assert "Provider timeout" in fail_res.json()["detail"]

        # 12. Test Explaining Dependency Issue
        deps_res = await ac.get(f"/api/projects/{project_id}/dependencies", headers=headers_a)
        deps_list = deps_res.json()
        assert len(deps_list) > 0
        dep_id = deps_list[0]["id"]

        dep_mock_output = AIExplanationOutput(
            summary="Vulnerable dependency detected in requirements.txt.",
            why_it_matters="Known vulnerabilities can be exploited by remote attackers.",
            potential_impact="Denial of service or remote code execution depending on CVE vector.",
            recommendation="Upgrade package to the patched release version.",
            priority="High",
            developer_action="Update requirements.txt to specify a secure version.",
        )
        with patch.object(GeminiClient, "generate_explanation", return_value=dep_mock_output):
            with patch.object(GeminiClient, "is_available", return_value=True):
                dep_exp_res = await ac.post(f"/api/issues/{dep_id}/explain", headers=headers_a)
                assert dep_exp_res.status_code == 200
                assert dep_exp_res.json()["issue_category"] == "dependency"
