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
        "password": "ScannerPass123!"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "ScannerPass123!"
    })
    return res.json()["access_token"]


def create_structured_sample_zip() -> bytes:
    """Creates a sample zip archive with known files, lines, and categories:
    - backend/main.py: 10 lines (7 code, 2 comment, 1 blank) [Python - Source]
    - backend/tests/test_main.py: 8 lines (6 code, 1 comment, 1 blank) [Python - Tests]
    - frontend/src/app.js: 6 lines (5 code, 0 comment, 1 blank) [JavaScript - Source]
    - frontend/src/style.css: 5 lines (4 code, 1 comment, 0 blank) [CSS - Source]
    - package.json: 5 lines [Configuration]
    - README.md: 3 lines [Documentation]
    - logo.png: binary mock bytes [Assets]
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # backend/main.py
        py_code = (
            '"""Main API entrypoint module."""\n'
            '# Author: Antigravity\n'
            'import os\n'
            '\n'
            'def start_app():\n'
            '    port = 8000\n'
            '    print(f"Starting server on port {port}")\n'
            '    return True\n'
            '\n'
            'start_app()\n'
        )
        zf.writestr("backend/main.py", py_code)

        # backend/tests/test_main.py
        test_code = (
            '# Test suite\n'
            'from backend.main import start_app\n'
            '\n'
            'def test_app():\n'
            '    res = start_app()\n'
            '    assert res is True\n'
            '\n'
            'test_app()\n'
        )
        zf.writestr("backend/tests/test_main.py", test_code)

        # frontend/src/app.js
        js_code = (
            'const message = "Hello from Doctor UI";\n'
            'function render() {\n'
            '    console.log(message);\n'
            '    return true;\n'
            '}\n'
            'render();\n'
        )
        zf.writestr("frontend/src/app.js", js_code)

        # frontend/src/style.css
        css_code = (
            '/* Primary styles */\n'
            'body { background: #000; }\n'
            '.card { border: 1px solid #333; }\n'
            'h1 { color: #fff; }\n'
            'p { margin: 0; }\n'
        )
        zf.writestr("frontend/src/style.css", css_code)

        # package.json
        pkg_json = '{\n  "name": "sample-project",\n  "version": "1.0.0"\n}\n'
        zf.writestr("package.json", pkg_json)

        # README.md
        readme = '# Sample Repository\n\nProject Doctor evaluation fixture.\n'
        zf.writestr("README.md", readme)

        # Mock binary image
        zf.writestr("logo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00")

    return buf.getvalue()


@pytest.mark.asyncio
async def test_scan_valid_project():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "scientist@scanner.dev", "Marie Curie")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Project
        create_res = await client.post("/api/projects", json={"name": "Multi-Lang Codebase", "source_type": "zip"}, headers=headers)
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Upload structured zip
        zip_bytes = create_structured_sample_zip()
        upload_res = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("structured.zip", zip_bytes, "application/zip")},
            headers=headers
        )
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "READY"

        # 3. Trigger Scan
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200
        data = scan_res.json()

        # Check total file count: 7 files (main.py, test_main.py, app.js, style.css, package.json, README.md, logo.png)
        assert data["total_files"] == 7
        assert data["total_lines"] > 0
        assert data["total_code_lines"] > 0
        assert data["test_files_count"] == 1
        assert data["config_files_count"] == 1
        assert data["doc_files_count"] == 1

        # Check languages detected
        langs = data["languages_summary"]
        assert "Python" in langs
        assert "JavaScript" in langs
        assert "CSS" in langs
        # Total percentages should sum to approximately 100%
        pct_sum = sum(l["percentage"] for l in langs.values())
        assert 98.0 <= pct_sum <= 102.0

        # Check file categories
        cats = data["categories_summary"]
        assert cats["Tests"] == 1
        assert cats["Configuration"] == 1
        assert cats["Documentation"] == 1
        assert cats["Assets"] == 1
        assert cats["Source Code"] == 3  # main.py, app.js, style.css

        # Check directory tree structure
        tree = data["directory_tree"]
        assert tree["type"] == "directory"
        assert len(tree["children"]) > 0


@pytest.mark.asyncio
async def test_scan_single_language_project_100_percent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "pydev@scanner.dev", "Guido van Rossum")
        headers = {"Authorization": f"Bearer {token}"}

        # Create zip with ONLY python files
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("app.py", "def run():\n    return 42\n")
            zf.writestr("calc.py", "def add(x, y):\n    return x + y\n")

        create_res = await client.post("/api/projects", json={"name": "Pure Python", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("pure_python.zip", buf.getvalue(), "application/zip")},
            headers=headers
        )

        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200
        data = scan_res.json()
        langs = data["languages_summary"]
        assert len(langs) == 1
        assert "Python" in langs
        assert langs["Python"]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_scan_non_ready_project():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "unready@scanner.dev", "Unready Dev")
        headers = {"Authorization": f"Bearer {token}"}

        # Project created but no files uploaded yet
        create_res = await client.post("/api/projects", json={"name": "Not Ready", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 400
        assert "not ready" in scan_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_scan_unauthorized_other_user():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await get_auth_token(client, "owner.scan@scanner.dev", "Owner")
        token_b = await get_auth_token(client, "intruder.scan@scanner.dev", "Intruder")

        create_res = await client.post("/api/projects", json={"name": "Protected Project", "source_type": "zip"}, headers={"Authorization": f"Bearer {token_a}"})
        project_id = create_res.json()["id"]

        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers={"Authorization": f"Bearer {token_b}"})
        assert scan_res.status_code == 404


@pytest.mark.asyncio
async def test_get_scan_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "inspector@scanner.dev", "Inspector")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post("/api/projects", json={"name": "Inspectable Codebase", "source_type": "zip"}, headers=headers)
        project_id = create_res.json()["id"]

        zip_bytes = create_structured_sample_zip()
        await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("structured.zip", zip_bytes, "application/zip")},
            headers=headers
        )

        # 1. Trigger scan
        await client.post(f"/api/projects/{project_id}/scan", headers=headers)

        # 2. GET /api/projects/{id}/scan
        get_scan = await client.get(f"/api/projects/{project_id}/scan", headers=headers)
        assert get_scan.status_code == 200
        assert get_scan.json()["total_files"] == 7

        # 3. GET /api/projects/{id}/tree
        get_tree = await client.get(f"/api/projects/{project_id}/tree", headers=headers)
        assert get_tree.status_code == 200
        assert get_tree.json()["type"] == "directory"

        # 4. GET /api/projects/{id}/files
        get_files = await client.get(f"/api/projects/{project_id}/files", headers=headers)
        assert get_files.status_code == 200
        assert len(get_files.json()) == 7

        # 5. GET /api/projects/{id}/files?category=Tests
        get_tests = await client.get(f"/api/projects/{project_id}/files?category=Tests", headers=headers)
        assert get_tests.status_code == 200
        test_files = get_tests.json()
        assert len(test_files) == 1
        assert "test_main.py" in test_files[0]["file_name"]

        # 6. GET /api/projects/{id}/statistics
        get_stats = await client.get(f"/api/projects/{project_id}/statistics", headers=headers)
        assert get_stats.status_code == 200
        stats = get_stats.json()
        assert stats["total_files"] == 7
        assert stats["test_files_count"] == 1
