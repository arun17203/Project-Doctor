import io
import zipfile
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.ai.client import GeminiClient
from backend.app.ai.schemas import CodebaseQAOutput, SourceCitation
from backend.app.ai.sanitizer import is_file_disallowed, mask_sensitive_snippet


async def get_auth_token(client: AsyncClient, email: str, name: str) -> str:
    """Helper to register and login a test user."""
    await client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "QAPassword123!"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "QAPassword123!"
    })
    return res.json()["access_token"]


def create_qa_sample_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "backend/auth.py",
            "import jwt\n\nSECRET = 'sk-test-1234567890abcdef1234567890'\n\ndef authenticate_user(username, password):\n    # Authenticate user\n    if username == 'admin':\n        return jwt.encode({'user': username}, 'key')\n    return None\n"
        )
        zf.writestr(
            "backend/database.py",
            "import sqlite3\n\ndef get_db_connection():\n    return sqlite3.connect('app.db')\n"
        )
        zf.writestr(
            "frontend/src/Login.jsx",
            "import React from 'react';\n\nexport function Login() {\n    return <div>Login Form</div>;\n}\n"
        )
        zf.writestr(
            ".env",
            "DATABASE_URL=postgres://admin:supersecret@localhost:5432/db\nAPI_KEY=supersecretsecret\n"
        )
    buf.seek(0)
    return buf.getvalue()


def test_retriever_blocks_sensitive_files():
    assert is_file_disallowed(".env") is True
    assert is_file_disallowed("config/.env.production") is True
    assert is_file_disallowed("certs/server.pem") is True
    assert is_file_disallowed("backend/auth.py") is False

    masked = mask_sensitive_snippet("API_KEY = 'sk-test-1234567890abcdef'")
    assert "sk-test-1234567890abcdef" not in masked
    assert "REDACTED" in masked


@pytest.mark.asyncio
async def test_full_qa_flow_with_mock_gemini():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "qa_lead@doctor.io", "QA Lead Developer")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project
        create_res = await client.post("/api/projects", json={
            "name": "QA Grounded Repo",
            "description": "Repo for testing codebase assistant",
            "source_type": "zip"
        }, headers=headers)
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Upload sample zip
        zip_bytes = create_qa_sample_zip()
        upload_res = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("qa_repo.zip", zip_bytes, "application/zip")},
            headers=headers
        )
        assert upload_res.status_code == 200

        # 3. Run scan
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200

        # 4. Ask with mocked Gemini
        mock_output = CodebaseQAOutput(
            answer="Authentication is implemented in `backend/auth.py` where `authenticate_user` handles JWT token generation.",
            sources=[
                SourceCitation(file_path="backend/auth.py", line_start=5, line_end=10, reason="Defines authenticate_user"),
                SourceCitation(file_path="nonexistent/hallucinated_file.py", line_start=1, line_end=5, reason="Fake citation")
            ]
        )

        with patch.object(GeminiClient, "is_available", return_value=True):
            with patch.object(GeminiClient, "generate_qa_answer", return_value=mock_output) as mock_method:
                qa_res = await client.post(
                    f"/api/projects/{project_id}/ask",
                    json={
                        "question": "Where is authentication implemented?",
                        "conversation": [{"role": "user", "content": "Initial inquiry"}]
                    },
                    headers=headers
                )
                assert qa_res.status_code == 200
                data = qa_res.json()
                assert "backend/auth.py" in data["answer"]
                assert data["project_id"] == project_id
                assert data["provider"] == "google-gemini"

                # Citation validation test: Real file preserved, fake file stripped!
                source_paths = [s["file_path"] for s in data["sources"]]
                assert "backend/auth.py" in source_paths
                assert "nonexistent/hallucinated_file.py" not in source_paths
                mock_method.assert_called_once()


@pytest.mark.asyncio
async def test_qa_unscanned_project_returns_guidance():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "unscanned_qa@doctor.io", "Unscanned Tester")
        headers = {"Authorization": f"Bearer {token}"}

        # Create project without scan
        create_res = await client.post("/api/projects", json={
            "name": "Unscanned App",
            "description": "Not scanned yet",
            "source_type": "zip"
        }, headers=headers)
        project_id = create_res.json()["id"]

        qa_res = await client.post(
            f"/api/projects/{project_id}/ask",
            json={"question": "What does this code do?"},
            headers=headers
        )
        assert qa_res.status_code == 200
        data = qa_res.json()
        assert "not been scanned yet" in data["answer"].lower()
        assert len(data["sources"]) == 0


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_ask():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_alice = await get_auth_token(client, "alice_qa@doctor.io", "Alice QA")
        token_bob = await get_auth_token(client, "bob_qa@doctor.io", "Bob QA")

        # Alice creates project
        create_res = await client.post("/api/projects", json={
            "name": "Alice Secret Project",
            "description": "Private project",
            "source_type": "zip"
        }, headers={"Authorization": f"Bearer {token_alice}"})
        project_id = create_res.json()["id"]

        # Bob attempts to ask question about Alice's project
        bob_res = await client.post(
            f"/api/projects/{project_id}/ask",
            json={"question": "What is in this project?"},
            headers={"Authorization": f"Bearer {token_bob}"}
        )
        assert bob_res.status_code == 404


@pytest.mark.asyncio
async def test_empty_question_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "empty_q_user@doctor.io", "Empty Tester")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={
            "name": "Empty Question App",
            "source_type": "zip"
        }, headers=headers)
        project_id = create_res.json()["id"]

        res = await client.post(
            f"/api/projects/{project_id}/ask",
            json={"question": "   "},
            headers=headers
        )
        assert res.status_code == 400
        assert "cannot be empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_missing_gemini_key_returns_503():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "no_key_user@doctor.io", "No Key Tester")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={
            "name": "No Key Project",
            "source_type": "zip"
        }, headers=headers)
        project_id = create_res.json()["id"]

        # Upload & scan so it passes scan check
        zip_bytes = create_qa_sample_zip()
        await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("code.zip", zip_bytes, "application/zip")},
            headers=headers
        )
        await client.post(f"/api/projects/{project_id}/scan", headers=headers)

        with patch.object(GeminiClient, "is_available", return_value=False):
            res = await client.post(
                f"/api/projects/{project_id}/ask",
                json={"question": "Where is authentication?"},
                headers=headers
            )
            assert res.status_code == 503
            assert "unavailable" in res.json()["detail"].lower()
