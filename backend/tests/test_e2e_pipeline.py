import io
import zipfile
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.ai.client import GeminiClient
from backend.app.ai.schemas import AIExplanationOutput, CodebaseQAOutput, SourceCitation


def create_e2e_sample_repo() -> bytes:
    """Creates a sample multi-language repository archive for end-to-end testing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Python file with security, complexity, and styling issues
        zf.writestr(
            "backend/auth_service.py",
            "import os\n"
            "import sys\n"
            "import base64\n"
            "\n"
            "# Critical hardcoded credential\n"
            "AWS_SECRET_KEY = 'AKIA1234567890EXAMPLE'\n"
            "\n"
            "def authenticate_and_process(user, role, perm, flag_a, flag_b, flag_c):\n"
            "    # Deliberately complex function to trigger complexity finding\n"
            "    score = 0\n"
            "    if flag_a:\n"
            "        if flag_b:\n"
            "            score += 10\n"
            "        elif flag_c:\n"
            "            score += 5\n"
            "    for i in range(10):\n"
            "        if i % 2 == 0:\n"
            "            score += i\n"
            "        elif i % 3 == 0:\n"
            "            score -= i\n"
            "    while score > 100:\n"
            "        score -= 10\n"
            "    # Insecure eval\n"
            "    return eval(str(score))\n",
        )

        # 2. Service layer importing utility
        zf.writestr(
            "backend/user_service.py",
            "from backend.auth_service import authenticate_and_process\n"
            "\n"
            "class UserService:\n"
            "    def get_user(self, user_id):\n"
            "        return {'id': user_id, 'name': 'Test User'}\n",
        )

        # 3. Requirements with pinned dependencies
        zf.writestr(
            "requirements.txt",
            "flask==0.12.0\n"
            "requests==2.18.4\n",
        )

        # 4. Frontend component
        zf.writestr(
            "frontend/src/App.tsx",
            "import React from 'react';\n"
            "import { useState } from 'react';\n"
            "\n"
            "export function App() {\n"
            "    const [count, setCount] = useState(0);\n"
            "    return <div>Project Doctor Test App: {count}</div>;\n"
            "}\n",
        )

        # 5. Documentation
        zf.writestr(
            "README.md",
            "# Sample E2E Test Codebase\n"
            "This is a demonstration repository for end-to-end integration testing.\n",
        )

    buf.seek(0)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_complete_end_to_end_pipeline():
    """Validates the entire Project Doctor pipeline:
    1. Register & authenticate User A
    2. Create a project
    3. Upload multi-language ZIP archive
    4. Run repository scan (Stage 4)
    5. Run code quality analysis (Stage 5)
    6. Run security audit (Stage 6)
    7. Run dependency analyzer (Stage 7)
    8. Run architecture graph analysis (Stage 8)
    9. Run health & technical debt engine (Stage 9)
    10. Run AI problem explainer with mock Gemini (Stage 10)
    11. Ask codebase Q&A with mock Gemini (Stage 11)
    12. Create & compare analysis snapshots in history (Stage 12)
    13. Verify multi-user isolation with User B
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ==========================================
        # STEP 1: Register & Authenticate User A
        # ==========================================
        reg_a = await client.post(
            "/api/auth/register",
            json={"name": "Alice Developer", "email": "alice.e2e@doctor.io", "password": "SecurePassword123!"},
        )
        assert reg_a.status_code in (200, 201), reg_a.text

        login_a = await client.post(
            "/api/auth/login",
            json={"email": "alice.e2e@doctor.io", "password": "SecurePassword123!"},
        )
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        me_res = await client.get("/api/auth/me", headers=headers_a)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "alice.e2e@doctor.io"

        # ==========================================
        # STEP 2: Create Project
        # ==========================================
        p_res = await client.post(
            "/api/projects",
            json={
                "name": "E2E Masterpiece Service",
                "description": "Full end-to-end integration test project",
                "source_type": "zip",
            },
            headers=headers_a,
        )
        assert p_res.status_code == 201
        project_data = p_res.json()
        project_id = project_data["id"]
        assert project_data["status"] == "CREATED"

        # ==========================================
        # STEP 3: Upload ZIP Archive
        # ==========================================
        zip_bytes = create_e2e_sample_repo()
        up_res = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("e2e_repo.zip", zip_bytes, "application/zip")},
            headers=headers_a,
        )
        assert up_res.status_code == 200
        assert up_res.json()["status"] == "READY"

        # ==========================================
        # STEP 4: Repository Scanner (Stage 4)
        # ==========================================
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers_a)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["status"] == "COMPLETED"
        assert scan_data["total_files"] >= 4
        assert scan_data["total_lines"] > 0
        assert "Python" in scan_data["languages_summary"] or "python" in [k.lower() for k in scan_data["languages_summary"]]

        # ==========================================
        # STEP 5: Code Quality Analysis (Stage 5)
        # ==========================================
        q_res = await client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers_a)
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert q_data["status"] == "COMPLETED"
        assert "metrics" in q_data
        assert q_data["total_issues"] >= 1

        # Verify quality issues listed
        q_issues_res = await client.get(f"/api/projects/{project_id}/quality/issues", headers=headers_a)
        assert q_issues_res.status_code == 200
        q_issues = q_issues_res.json()
        assert len(q_issues) >= 1

        # ==========================================
        # STEP 6: Security Audit (Stage 6)
        # ==========================================
        s_res = await client.post(f"/api/projects/{project_id}/analyze/security", headers=headers_a)
        assert s_res.status_code == 200
        s_data = s_res.json()
        assert s_data["status"] == "COMPLETED"
        assert s_data["total_issues"] >= 1

        s_issues_res = await client.get(f"/api/projects/{project_id}/security/issues", headers=headers_a)
        assert s_issues_res.status_code == 200
        s_issues = s_issues_res.json()
        assert len(s_issues) >= 1
        # Pick one security issue for AI explainer later
        target_issue_id = s_issues[0]["id"]

        # ==========================================
        # STEP 7: Dependency Analysis (Stage 7)
        # ==========================================
        d_res = await client.post(f"/api/projects/{project_id}/analyze/dependencies", headers=headers_a)
        assert d_res.status_code == 200
        d_data = d_res.json()
        assert d_data["status"] == "COMPLETED"
        assert d_data["total_dependencies"] >= 2

        # ==========================================
        # STEP 8: Architecture Graph (Stage 8)
        # ==========================================
        arch_res = await client.post(f"/api/projects/{project_id}/analyze/architecture", headers=headers_a)
        assert arch_res.status_code == 200
        arch_data = arch_res.json()
        assert arch_data["status"] == "COMPLETED"
        assert arch_data["node_count"] >= 2

        # Check graph retrieval
        graph_res = await client.get(f"/api/projects/{project_id}/architecture/graph", headers=headers_a)
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert len(graph_data["nodes"]) >= 2

        # ==========================================
        # STEP 9: Health Engine (Stage 9)
        # ==========================================
        h_res = await client.post(f"/api/projects/{project_id}/analyze/health", headers=headers_a)
        assert h_res.status_code == 200
        h_data = h_res.json()
        assert "overall_score" in h_data
        assert "technical_debt_hours" in h_data
        assert "debt_breakdown" in h_data
        assert "explanations" in h_data
        assert "fix_first" in h_data

        # ==========================================
        # STEP 10: AI Problem Explainer (Stage 10)
        # ==========================================
        mock_explanation = AIExplanationOutput(
            summary="Hardcoded AWS secret key detected in backend/auth_service.py.",
            why_it_matters="Sensitive AWS access token was committed in plaintext.",
            potential_impact="High risk of unauthorized infrastructure access and cloud credential compromise.",
            recommendation="Move credentials to environment variables and rotate the compromised key.",
            priority="Immediate",
            developer_action="import os\nAWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')",
        )

        with patch.object(GeminiClient, "is_available", return_value=True):
            with patch.object(GeminiClient, "generate_explanation", return_value=mock_explanation):
                ai_exp_res = await client.post(
                    f"/api/issues/{target_issue_id}/explain",
                    headers=headers_a,
                )
                assert ai_exp_res.status_code == 200
                ai_exp_data = ai_exp_res.json()
                assert ai_exp_data["summary"] == mock_explanation.summary
                assert ai_exp_data["provider"] == "google-gemini"

                # Verify cached retrieval
                cached_res = await client.get(
                    f"/api/issues/{target_issue_id}/explanation",
                    headers=headers_a,
                )
                assert cached_res.status_code == 200
                assert cached_res.json()["summary"] == mock_explanation.summary

        # ==========================================
        # STEP 11: Ask My Codebase Q&A (Stage 11)
        # ==========================================
        mock_qa = CodebaseQAOutput(
            answer="The application entry point and main React component is located in `frontend/src/App.tsx`.",
            sources=[
                SourceCitation(file_path="frontend/src/App.tsx", line_start=1, line_end=9, reason="App component definition"),
            ],
        )

        with patch.object(GeminiClient, "is_available", return_value=True):
            with patch.object(GeminiClient, "generate_qa_answer", return_value=mock_qa):
                qa_res = await client.post(
                    f"/api/projects/{project_id}/ask",
                    json={
                        "question": "Where is the frontend user interface defined?",
                        "conversation": [],
                    },
                    headers=headers_a,
                )
                assert qa_res.status_code == 200
                qa_data = qa_res.json()
                assert "frontend/src/App.tsx" in qa_data["answer"]
                assert len(qa_data["sources"]) == 1
                assert qa_data["sources"][0]["file_path"] == "frontend/src/App.tsx"

        # ==========================================
        # STEP 12: Analysis History & Comparison (Stage 12)
        # ==========================================
        # 1. Fetch historical snapshots
        hist_res = await client.get(f"/api/projects/{project_id}/history", headers=headers_a)
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert hist_data["total"] >= 1
        v1_number = hist_data["items"][-1]["version_number"]

        # 2. Create a second snapshot to demonstrate progression
        snap_v2_res = await client.post(
            f"/api/projects/{project_id}/snapshots",
            json={"summary": "Post-remediation security and quality verification snapshot"},
            headers=headers_a,
        )
        assert snap_v2_res.status_code == 200
        v2_data = snap_v2_res.json()
        v2_number = v2_data["version_number"]
        assert v2_number > v1_number

        # 3. Compare Version 1 and Version 2
        comp_res = await client.get(
            f"/api/projects/{project_id}/history/compare",
            params={"from": v1_number, "to": v2_number},
            headers=headers_a,
        )
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert comp_data["from_version"] == v1_number
        assert comp_data["to_version"] == v2_number
        assert "health_delta" in comp_data
        assert "technical_debt_delta" in comp_data
        assert "file_diff" in comp_data
        assert "summary_headline" in comp_data

        # ==========================================
        # STEP 13: Multi-User Isolation Verification
        # ==========================================
        reg_b = await client.post(
            "/api/auth/register",
            json={"name": "Bob Observer", "email": "bob.e2e@doctor.io", "password": "BobPassword123!"},
        )
        assert reg_b.status_code in (200, 201)
        login_b = await client.post(
            "/api/auth/login",
            json={"email": "bob.e2e@doctor.io", "password": "BobPassword123!"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Bob cannot access Alice's project
        unauth_p = await client.get(f"/api/projects/{project_id}", headers=headers_b)
        assert unauth_p.status_code in (403, 404)

        # Bob cannot scan Alice's project
        unauth_scan = await client.post(f"/api/projects/{project_id}/scan", headers=headers_b)
        assert unauth_scan.status_code in (403, 404)

        # Bob cannot see Alice's project history
        unauth_hist = await client.get(f"/api/projects/{project_id}/history", headers=headers_b)
        assert unauth_hist.status_code in (403, 404)

        # Bob cannot explain Alice's issues
        unauth_exp = await client.post(f"/api/issues/{target_issue_id}/explain", headers=headers_b)
        assert unauth_exp.status_code in (403, 404)
