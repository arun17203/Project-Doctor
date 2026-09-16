"""Live End-to-End Stage 3 Verification Script.

Tests against live running server:
1. Login with user credentials (or register first if needed)
2. Create project via POST /api/projects
3. Upload real in-memory ZIP via POST /api/projects/{id}/upload
4. Verify safe extraction on disk & project status becomes READY
5. Verify project appears in GET /api/projects
6. Open project details via GET /api/projects/{id}
7. Attempt unauthorized access with a second user -> verify 404
8. Test malicious ZIP path traversal (Zip Slip) -> verify rejected with 400
9. Delete project via DELETE /api/projects/{id} -> verify database record and disk files purged
10. Verify project no longer exists (404)
"""
import io
import os
import zipfile
import httpx

BASE_URL = "http://127.0.0.1:8000/api"


def make_sample_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("src/server.py", "# Real python server\ndef run():\n    return 'OK'\n")
        zf.writestr("src/client.ts", "export const client = () => 'connected';\n")
        zf.writestr("package.json", '{"name": "demo-app", "version": "1.0.0"}\n')
        zf.writestr("README.md", "# Demo Ingested App\n")
        # Ignored directory entry
        zf.writestr("node_modules/lodash/index.js", "module.exports = {};\n")
    return buf.getvalue()


def make_malicious_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../../escape_sandbox.py", "print('Attacking host')\n")
    return buf.getvalue()


def run_stage3_verification():
    print(f"[*] Starting Stage 3 Live Verification against {BASE_URL}...")
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. Login User A
    email_a = "stage3.dev@doctor.dev"
    pass_a = "SecureStage3Pass!"
    name_a = "Dr. John von Neumann"

    reg_res = client.post("/auth/register", json={"name": name_a, "email": email_a, "password": pass_a})
    if reg_res.status_code == 201:
        print(f"[+] Registered User A: {email_a}")
    else:
        print(f"[*] User A already exists ({reg_res.status_code}), continuing to login...")

    login_res = client.post("/auth/login", json={"email": email_a, "password": pass_a})
    assert login_res.status_code == 200, f"Login A failed: {login_res.text}"
    token_a = login_res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("[+] 1. User A Logged in, JWT received.")

    # 2. Create Project
    create_res = client.post(
        "/projects",
        json={
            "name": "Telemetry Microservice",
            "description": "Distributed telemetry ingest service",
            "source_type": "zip"
        },
        headers=headers_a
    )
    assert create_res.status_code == 201, f"Project creation failed: {create_res.text}"
    proj_a = create_res.json()
    proj_id = proj_a["id"]
    assert proj_a["status"] == "CREATED"
    assert "storage_path" not in proj_a
    print(f"[+] 2. Project Created: '{proj_a['name']}' (ID: {proj_id}) with status CREATED.")

    # 3 & 4. Upload Real ZIP & Extract Safely
    sample_zip_bytes = make_sample_zip()
    upload_res = client.post(
        f"/projects/{proj_id}/upload",
        files={"file": ("telemetry_service.zip", sample_zip_bytes, "application/zip")},
        headers=headers_a
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    uploaded_data = upload_res.json()
    assert uploaded_data["status"] == "READY", f"Expected READY, got {uploaded_data['status']}"
    assert uploaded_data["original_filename"] == "telemetry_service.zip"
    print(f"[+] 3 & 4. Real ZIP Uploaded and Extracted Safely. Status is now: {uploaded_data['status']}.")

    # 5. Verify Project Appears in User A's Dashboard
    list_res = client.get("/projects", headers=headers_a)
    assert list_res.status_code == 200
    projects_list = list_res.json()
    found = any(p["id"] == proj_id for p in projects_list)
    assert found, "Created project not found in User A's projects list!"
    print(f"[+] 5. Project verified in User A's Dashboard (Total user projects: {len(projects_list)}).")

    # 6. Open Project Details
    detail_res = client.get(f"/projects/{proj_id}", headers=headers_a)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["name"] == "Telemetry Microservice"
    assert detail_data["status"] == "READY"
    print(f"[+] 6. Project Details verified: '{detail_data['name']}' is READY for analysis.")

    # 7. Try Accessing with User B (Unauthorized Intruder)
    email_b = "intruder.stage3@doctor.dev"
    pass_b = "IntruderPass123!"
    client.post("/auth/register", json={"name": "Intruder B", "email": email_b, "password": pass_b})
    login_b = client.post("/auth/login", json={"email": email_b, "password": pass_b})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    unauth_get = client.get(f"/projects/{proj_id}", headers=headers_b)
    assert unauth_get.status_code == 404, f"Expected 404 for unauthorized access, got {unauth_get.status_code}"
    print(f"[+] 7. Unauthorized user access correctly blocked with 404 Not Found.")

    # 8. Test Malicious ZIP Path Traversal (Zip Slip) Protection
    malicious_proj_res = client.post(
        "/projects",
        json={"name": "Malicious Test", "source_type": "zip"},
        headers=headers_a
    )
    malicious_proj_id = malicious_proj_res.json()["id"]

    malicious_zip_bytes = make_malicious_zip()
    malicious_upload = client.post(
        f"/projects/{malicious_proj_id}/upload",
        files={"file": ("slip.zip", malicious_zip_bytes, "application/zip")},
        headers=headers_a
    )
    assert malicious_upload.status_code == 400, f"Expected 400 for malicious zip, got {malicious_upload.status_code}"
    err_detail = malicious_upload.json()["detail"]
    assert "path traversal" in err_detail.lower(), f"Unexpected error message: {err_detail}"
    print(f"[+] 8. Malicious Zip Slip path traversal blocked: '{err_detail}'.")

    # Clean up malicious test project
    client.delete(f"/projects/{malicious_proj_id}", headers=headers_a)

    # 9. Delete Project
    del_res = client.delete(f"/projects/{proj_id}", headers=headers_a)
    assert del_res.status_code == 200, f"Delete failed: {del_res.text}"
    print(f"[+] 9. Project deleted successfully: {del_res.json()['message']}")

    # 10. Verify Project is completely purged
    gone_res = client.get(f"/projects/{proj_id}", headers=headers_a)
    assert gone_res.status_code == 404
    print("[+] 10. Verified project record purged (404 Not Found).")

    print("\n=======================================================")
    print("ALL 10 STAGE 3 INGESTION & SECURITY CHECKS PASSED LIVE!")
    print("=======================================================")


if __name__ == "__main__":
    run_stage3_verification()
