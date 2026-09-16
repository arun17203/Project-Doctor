"""
Stage 4 Repository Scanner Live End-to-End Verification Script
Tests the running FastAPI instance (http://127.0.0.1:8000) through HTTP requests:
1. User registration & JWT authentication
2. Project creation with ZIP upload
3. Verification of ignored folders (node_modules, .git)
4. Repository Scan execution (POST /api/projects/{id}/scan)
5. Metric checks: LOC, comments, blank lines, languages, categories
6. Directory tree retrieval (GET /api/projects/{id}/tree)
7. File explorer query (GET /api/projects/{id}/files)
8. Scan statistics query (GET /api/projects/{id}/statistics)
9. Security & Access control (unauthorized user blocked)
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
        # 1. Python source
        py_app = (
            '"""Main API Module."""\n'
            '# Fast API server\n'
            'import os\n'
            '\n'
            'def run():\n'
            '    print("Running...")\n'
            '    return 42\n'
        )
        zf.writestr("src/backend/app.py", py_app)

        # 2. Python test
        py_test = (
            '# Unit tests\n'
            'from src.backend.app import run\n'
            '\n'
            'def test_run():\n'
            '    assert run() == 42\n'
        )
        zf.writestr("tests/test_app.py", py_test)

        # 3. TypeScript source
        ts_code = (
            '// Frontend main\n'
            'interface Config {\n'
            '    port: number;\n'
            '}\n'
            'export const serverConfig: Config = { port: 3000 };\n'
        )
        zf.writestr("src/frontend/index.ts", ts_code)

        # 4. Config file
        json_cfg = '{\n  "name": "stage4-demo",\n  "private": true\n}\n'
        zf.writestr("package.json", json_cfg)

        # 5. Documentation
        doc = '# Project Doctor Stage 4\n\nLive verification repository.\n'
        zf.writestr("README.md", doc)

        # 6. Binary file
        zf.writestr("assets/icon.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00")

        # 7. Ignored directories (must be filtered out by scanner!)
        zf.writestr("node_modules/dummy_pkg/index.js", "console.log('should be ignored');\n")
        zf.writestr(".git/objects/00/dummy", b"git-object-data")

    return buf.getvalue()


def run_verification():
    print("=" * 70)
    print("STAGE 4: REPOSITORY SCANNER LIVE E2E VERIFICATION")
    print("=" * 70)

    session = requests.Session()
    ts = int(time.time())
    email = f"scanner_user_{ts}@doctor.io"
    password = "ScannerPass123!"

    # 1. Health check
    print("\n[Step 1] Checking backend health...")
    r = session.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health_data = r.json()
    print(f"  --> Status: {health_data['status']}, Database: {health_data['database']}")

    # 2. Register user
    print(f"\n[Step 2] Registering user {email}...")
    r = session.post(f"{BASE_URL}/api/auth/register", json={
        "name": f"Scanner Tester {ts}",
        "email": email,
        "password": password
    })
    assert r.status_code in (200, 201), f"Registration failed: {r.text}"
    token = r.json().get("access_token")
    if not token:
        r_login = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  --> User authenticated successfully!")

    # 3. Create project
    print("\n[Step 3] Creating project...")
    r = session.post(
        f"{BASE_URL}/api/projects",
        json={
            "name": f"Live Scanner Test {ts}",
            "description": "Multi-language project for Stage 4 scanner verification",
            "source_type": "zip"
        },
        headers=headers
    )
    assert r.status_code in (200, 201), f"Project creation failed: {r.text}"
    proj = r.json()
    project_id = proj["id"]
    print(f"  --> Project created with ID: {project_id} (status: {proj['status']})")

    # 4. Upload ZIP
    print("\n[Step 4] Uploading structured ZIP archive...")
    zip_bytes = create_verification_zip()
    r = session.post(
        f"{BASE_URL}/api/projects/{project_id}/upload",
        files={"file": ("scanner_project.zip", zip_bytes, "application/zip")},
        headers=headers
    )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    proj = r.json()
    print(f"  --> Project upload complete, status: {proj['status']}")
    assert proj["status"] == "READY", f"Expected READY but got {proj['status']}"

    # 5. Unauthorized access check
    print("\n[Step 5] Checking access control...")
    unauth_headers = {"Authorization": "Bearer invalid_token_xyz"}
    r = session.post(f"{BASE_URL}/api/projects/{project_id}/scan", headers=unauth_headers)
    assert r.status_code == 401, f"Expected 401 for invalid token, got {r.status_code}"
    print("  --> Unauthorized access correctly rejected with 401")

    # 6. Execute Scan
    print("\n[Step 6] Triggering Repository Scan (POST /api/projects/{id}/scan)...")
    r = session.post(f"{BASE_URL}/api/projects/{project_id}/scan", headers=headers)
    assert r.status_code == 200, f"Scan request failed: {r.text}"
    scan_data = r.json()
    print("  --> Scan completed successfully!")
    print(f"      Status: {scan_data['status']}")
    print(f"      Files Discovered: {scan_data['total_files']}")
    print(f"      Total Lines: {scan_data['total_lines']}")
    print(f"      Code Lines: {scan_data['total_code_lines']}")
    print(f"      Comment Lines: {scan_data['total_comment_lines']}")
    print(f"      Blank Lines: {scan_data['total_blank_lines']}")

    # Verify metrics
    assert scan_data["status"] == "COMPLETED"
    assert scan_data["total_files"] == 6, f"Expected 6 files (ignoring node_modules and .git), got {scan_data['total_files']}"
    assert scan_data["total_lines"] > 0
    assert scan_data["total_code_lines"] > 0

    print("\n      Languages Breakdown:")
    for lang, stat in scan_data["languages_summary"].items():
        print(f"        - {lang:12}: {stat['lines']} lines ({stat['percentage']}%), {stat['files']} files")
    assert "Python" in scan_data["languages_summary"]
    assert "TypeScript" in scan_data["languages_summary"]

    print("\n      File Categories:")
    for cat, count in scan_data["categories_summary"].items():
        print(f"        - {cat:15}: {count} files")
    assert scan_data["categories_summary"].get("Source Code", 0) >= 2
    assert scan_data["categories_summary"].get("Tests", 0) >= 1
    assert scan_data["categories_summary"].get("Configuration", 0) >= 1
    assert scan_data["categories_summary"].get("Documentation", 0) >= 1
    assert scan_data["categories_summary"].get("Assets", 0) >= 1

    # 7. Check Tree structure
    print("\n[Step 7] Querying Directory Tree (GET /api/projects/{id}/tree)...")
    r = session.get(f"{BASE_URL}/api/projects/{project_id}/tree", headers=headers)
    assert r.status_code == 200, f"Tree retrieval failed: {r.text}"
    tree = r.json()
    assert tree["type"] == "directory"
    child_names = [c["name"] for c in tree.get("children", [])]
    print(f"  --> Root tree items: {child_names}")
    assert "node_modules" not in child_names, "node_modules should have been excluded!"
    assert ".git" not in child_names, ".git should have been excluded!"
    assert "package.json" in child_names
    assert "README.md" in child_names

    # 8. Check Files list
    print("\n[Step 8] Querying Discovered Files (GET /api/projects/{id}/files)...")
    r = session.get(f"{BASE_URL}/api/projects/{project_id}/files", headers=headers)
    assert r.status_code == 200, f"Files query failed: {r.text}"
    files = r.json()
    assert len(files) == 6
    file_paths = [f["file_path"] for f in files]
    print(f"  --> Scanned file paths: {file_paths}")
    for p in file_paths:
        assert not p.startswith("node_modules"), f"node_modules file included: {p}"
        assert not p.startswith(".git"), f".git file included: {p}"

    # 9. Check Statistics
    print("\n[Step 9] Querying Scan Statistics (GET /api/projects/{id}/statistics)...")
    r = session.get(f"{BASE_URL}/api/projects/{project_id}/statistics", headers=headers)
    assert r.status_code == 200, f"Statistics query failed: {r.text}"
    stats = r.json()
    assert stats["total_files"] == 6
    assert stats["total_code_lines"] > 0
    print(f"  --> Statistics verified: total_files={stats['total_files']}, code_lines={stats['total_code_lines']}")

    # 10. Cleanup
    print("\n[Step 10] Cleaning up test project...")
    r = session.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
    assert r.status_code in (200, 204), f"Cleanup failed: {r.text}"
    print("  --> Project deleted successfully!")

    print("\n" + "=" * 70)
    print(">>> ALL STAGE 4 VERIFICATION CHECKS PASSED PERFECTLY! <<<")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
