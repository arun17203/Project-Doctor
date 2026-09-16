import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


async def get_auth_token(client: AsyncClient, email: str, name: str) -> str:
    """Helper to register and login a test user."""
    await client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "Password123!"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    return res.json()["access_token"]


def create_sample_zip() -> bytes:
    """Helper to generate a valid in-memory ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("src/main.py", "def hello():\n    print('Hello World')\n")
        zf.writestr("src/utils.js", "function add(a, b) { return a + b; }\n")
        zf.writestr("README.md", "# Test Sample Project\n")
        # Include an ignored path to verify it gets filtered out
        zf.writestr("node_modules/dummy/index.js", "console.log('ignore me');\n")
    return buf.getvalue()


def create_malicious_zip() -> bytes:
    """Helper to generate a ZIP with path traversal (Zip Slip)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../../evil_traversal.py", "import os; os.system('echo hacked')\n")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_create_project():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "alice@test.dev", "Alice Developer")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": "Microservice API",
            "description": "Core payment and invoice processing microservice",
            "source_type": "zip"
        }
        res = await client.post("/api/projects", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Microservice API"
        assert data["description"] == "Core payment and invoice processing microservice"
        assert data["source_type"] == "zip"
        assert data["status"] == "CREATED"
        assert "storage_path" not in data  # Ensure internal path not exposed


@pytest.mark.asyncio
async def test_create_project_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/projects", json={"name": "No Auth", "source_type": "zip"})
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_projects_user_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await get_auth_token(client, "user_a@test.dev", "User A")
        token_b = await get_auth_token(client, "user_b@test.dev", "User B")

        # User A creates a project
        await client.post("/api/projects", json={"name": "Project A", "source_type": "zip"}, headers={"Authorization": f"Bearer {token_a}"})

        # User B creates a project
        await client.post("/api/projects", json={"name": "Project B", "source_type": "github"}, headers={"Authorization": f"Bearer {token_b}"})

        # User A lists projects
        res_a = await client.get("/api/projects", headers={"Authorization": f"Bearer {token_a}"})
        assert res_a.status_code == 200
        projects_a = res_a.json()
        assert len(projects_a) == 1
        assert projects_a[0]["name"] == "Project A"

        # User B lists projects
        res_b = await client.get("/api/projects", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b.status_code == 200
        projects_b = res_b.json()
        assert len(projects_b) == 1
        assert projects_b[0]["name"] == "Project B"


@pytest.mark.asyncio
async def test_get_project_unauthorized_other_user():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await get_auth_token(client, "owner@test.dev", "Owner")
        token_b = await get_auth_token(client, "intruder@test.dev", "Intruder")

        # Owner creates project
        create_res = await client.post("/api/projects", json={"name": "Confidential", "source_type": "zip"}, headers={"Authorization": f"Bearer {token_a}"})
        project_id = create_res.json()["id"]

        # Intruder attempts to fetch project
        res = await client.get(f"/api/projects/{project_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_upload_valid_zip():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "uploader@test.dev", "Uploader")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project
        create_res = await client.post("/api/projects", json={"name": "Zip Project", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        # 2. Upload zip
        zip_bytes = create_sample_zip()
        files = {"file": ("codebase.zip", zip_bytes, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert upload_res.status_code == 200
        data = upload_res.json()
        assert data["status"] == "READY"
        assert data["original_filename"] == "codebase.zip"
        assert data["source_type"] == "zip"


@pytest.mark.asyncio
async def test_upload_invalid_file_extension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "badfile@test.dev", "Bad File")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={"name": "Invalid File Project", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        files = {"file": ("evil.exe", b"not-a-zip", "application/octet-stream")}
        res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert res.status_code == 400
        assert "only .zip" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_empty_zip():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "emptyzip@test.dev", "Empty Zip")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={"name": "Empty Project", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        files = {"file": ("empty.zip", b"", "application/zip")}
        res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_zip_slip_protection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zipslip@test.dev", "Zip Slip")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={"name": "Zip Slip Project", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        malicious_zip = create_malicious_zip()
        files = {"file": ("malicious.zip", malicious_zip, "application/zip")}
        res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert res.status_code == 400
        assert "path traversal" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_github_import_url_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "ghval@test.dev", "GitHub Val")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={"name": "GH Val Project", "source_type": "github"}, headers=headers)
        project_id = create_res.json()["id"]

        # Invalid URL format (GitLab)
        bad_res = await client.post(
            f"/api/projects/{project_id}/github",
            json={"github_url": "https://gitlab.com/user/project"},
            headers=headers
        )
        assert bad_res.status_code == 422 or bad_res.status_code == 400


@pytest.mark.asyncio
async def test_delete_project():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "deleter@test.dev", "Deleter")
        headers = {"Authorization": f"Bearer {token}"}

        # Create and upload zip
        create_res = await client.post("/api/projects", json={"name": "To Delete", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        files = {"file": ("code.zip", create_sample_zip(), "application/zip")}
        await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)

        # Delete project
        del_res = await client.delete(f"/api/projects/{project_id}", headers=headers)
        assert del_res.status_code == 200

        # Verify project is gone
        get_res = await client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_res.status_code == 404
