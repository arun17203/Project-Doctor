import io
import os
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings


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


def make_zip(files_dict: dict) -> bytes:
    """Helper to build an in-memory zip archive with arbitrary files and paths."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files_dict.items():
            zf.writestr(path, content)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_zip_valid_multi_language_extraction():
    """Test extracting a valid zip archive with multiple programming languages and doc files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zip_valid@test.dev", "Zip Valid")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "MultiLang Project", "source_type": "zip"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        zip_data = make_zip({
            "src/backend/server.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "src/frontend/app.tsx": "export default function App() { return <div>App</div>; }\n",
            "src/frontend/styles.css": "body { margin: 0; }\n",
            "docs/architecture.md": "# Architecture Overview\n",
            "tests/test_server.py": "def test_root(): assert True\n",
        })

        files = {"file": ("codebase.zip", zip_data, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert upload_res.status_code == 200
        data = upload_res.json()
        assert data["status"] == "READY"
        assert data["original_filename"] == "codebase.zip"


@pytest.mark.asyncio
async def test_zip_slip_path_traversal_blocked():
    """Test that path traversal attempts (Zip Slip) are strictly caught and rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zip_slip@test.dev", "Zip Slip")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Zip Slip Trap", "source_type": "zip"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # Attack payload: file attempting to escape target storage directory
        malicious_zip = make_zip({
            "../../malicious.txt": "evil payload attempting to escape sandbox",
            "../../../etc/passwd": "root:x:0:0:root:/root:/bin/bash",
            "normal.py": "print('normal')\n"
        })

        files = {"file": ("exploit.zip", malicious_zip, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert upload_res.status_code == 400
        assert "path traversal" in upload_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_zip_nested_hierarchy_and_binary_files():
    """Test deeply nested folder structures and binary files (images/icons) handled safely."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zip_nested@test.dev", "Zip Nested")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Deep Nested Project", "source_type": "zip"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # Binary content simulation (PNG header bytes)
        fake_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        zip_data = make_zip({
            "level1/level2/level3/level4/deep_module.py": "def deep(): return 42\n",
            "assets/logo.png": fake_png_bytes,
            "assets/binary_data.dat": b"\x00\x01\x02\x03\xff\xfe\xfd",
            "package.json": '{"name": "deep-app", "version": "1.0.0"}\n'
        })

        files = {"file": ("deep_app.zip", zip_data, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "READY"


@pytest.mark.asyncio
async def test_zip_ignored_directories_filtered_out():
    """Test that unwanted folders (node_modules, .git, __pycache__, dist) are stripped."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zip_ignored@test.dev", "Zip Ignored")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Ignored Filter Project", "source_type": "zip"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        zip_data = make_zip({
            "src/index.ts": "console.log('valid source');\n",
            "node_modules/express/index.js": "module.exports = {};\n",
            ".git/config": "[core]\n",
            "__pycache__/app.cpython-311.pyc": b"bytecode",
            "dist/bundle.js": "var bundle = true;\n",
            ".venv/bin/activate": "# virtualenv\n"
        })

        files = {"file": ("with_junk.zip", zip_data, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "READY"

        # Scan the project to verify that only the valid file (src/index.ts) is recognized
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["total_files"] == 1


@pytest.mark.asyncio
async def test_zip_empty_or_corrupt():
    """Test rejection of empty zip and corrupt byte stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zip_corrupt@test.dev", "Zip Corrupt")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Corrupt Test", "source_type": "zip"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # 1. 0-byte zip
        res_empty = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("empty.zip", b"", "application/zip")},
            headers=headers
        )
        assert res_empty.status_code == 400

        # 2. Corrupt zip header
        res_corrupt = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("corrupt.zip", b"not-a-valid-zip-content-here", "application/zip")},
            headers=headers
        )
        assert res_corrupt.status_code == 400


@pytest.mark.asyncio
async def test_uploaded_source_code_never_executed():
    """Verification that uploaded files are strictly stored as passive data without execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "zip_passive@test.dev", "Zip Passive")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Passive Code Project", "source_type": "zip"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # Code containing dangerous calls: should NOT be executed during extraction or scanning
        marker_file = "C:/tmp_hacked_marker.txt"
        zip_data = make_zip({
            "exploit.py": f"import os; os.system('touch {marker_file}')\nprint('danger')\n",
            "setup.py": "raise RuntimeError('Should not execute!')\n"
        })

        files = {"file": ("dangerous.zip", zip_data, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", files=files, headers=headers)
        assert upload_res.status_code == 200

        # Verify marker file was never created
        assert not os.path.exists(marker_file)
