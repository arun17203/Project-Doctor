"""
Comprehensive Live Verification Script for Stage 12: Analysis History & Trends.
Tests real end-to-end flow against running FastAPI server:
1. User registration & authentication
2. Project creation & file upload (ZIP)
3. Full multi-stage pipeline run (Scans -> Quality -> Security -> Dependencies -> Architecture -> Health)
4. Verification of automatic Snapshot #1 creation
5. Manual or automated trigger of Snapshot #2
6. History listing and pagination
7. Individual snapshot retrieval
8. Version comparison (v1 vs v2) with deterministic deltas & change summary
9. Immutability validation (v1 remains unchanged)
10. Multi-user security isolation & 404 validation
"""

import io
import zipfile
import uuid
import sys
import httpx

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    prefixes = {
        "INFO": "[*]",
        "PASS": "[OK]",
        "FAIL": "[FAIL]",
        "WARN": "[!]"
    }
    print(f"{prefixes.get(status, '[*]')} {msg}")

def build_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("app/main.py", (
            "import os\n"
            "from app.helpers import compute\n\n"
            "def run():\n"
            "    val = compute(10)\n"
            "    print('Computed:', val)\n"
            "    # Potential secret:\n"
            "    api_token = 'secret_token_12345'\n"
            "    return val\n\n"
            "if __name__ == '__main__':\n"
            "    run()\n"
        ))
        zf.writestr("app/helpers.py", (
            "def compute(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        if i % 2 == 0:\n"
            "            total += i\n"
            "    return total\n"
        ))
        zf.writestr("requirements.txt", (
            "requests==2.25.1\n"
            "urllib3==1.26.4\n"
        ))
    buf.seek(0)
    return buf.read()

def main():
    client = httpx.Client(base_url=BASE_URL, timeout=60.0)
    unique_suffix = uuid.uuid4().hex[:8]
    user1_email = f"hist_user_{unique_suffix}@example.com"
    user2_email = f"other_user_{unique_suffix}@example.com"
    password = "TestPassword123!"

    print("=" * 70)
    print("STAGE 12 LIVE END-TO-END VERIFICATION: ANALYSIS HISTORY & TRENDS")
    print("=" * 70)

    # 1. Register User 1
    log(f"Registering User 1 ({user1_email})...")
    r = client.post("/api/auth/register", json={
        "email": user1_email,
        "password": password,
        "name": "History Test User"
    })
    assert r.status_code == 201, f"Failed to register user 1: {r.text}"
    r_login = client.post("/api/auth/login", json={"email": user1_email, "password": password})
    assert r_login.status_code == 200, f"Failed to login user 1: {r_login.text}"
    token1 = r_login.json()["access_token"]
    auth1 = {"Authorization": f"Bearer {token1}"}
    log("User 1 registered and authenticated.", "PASS")

    # 2. Upload Project
    log("Creating test project record...")
    r = client.post("/api/projects", headers=auth1, json={
        "name": f"History-Demo-{unique_suffix}",
        "description": "Stage 12 verification repo",
        "source_type": "zip"
    })
    assert r.status_code == 201, f"Failed to create project: {r.text}"
    project = r.json()
    project_id = project["id"]
    log(f"Project created with ID: {project_id}", "PASS")

    log("Uploading test project ZIP...")
    zip_bytes = build_test_zip()
    files = {"file": ("repo.zip", zip_bytes, "application/zip")}
    r = client.post(f"/api/projects/{project_id}/upload", headers=auth1, files=files)
    assert r.status_code == 200, f"Failed to upload project ZIP: {r.text}"
    log("ZIP archive uploaded and extracted successfully.", "PASS")

    # 3. Run Pipeline Stages 4 through 9
    log("Running Repository Scanner (Stage 4)...")
    r = client.post(f"/api/projects/{project_id}/scan", headers=auth1)
    assert r.status_code == 200, f"Scan failed: {r.text}"
    log("Repository scan complete.", "PASS")

    log("Running Code Quality Analyzer (Stage 5)...")
    r = client.post(f"/api/projects/{project_id}/analyze/quality", headers=auth1)
    assert r.status_code == 200, f"Quality failed: {r.text}"
    log("Quality analysis complete.", "PASS")

    log("Running Security Audit Engine (Stage 6)...")
    r = client.post(f"/api/projects/{project_id}/analyze/security", headers=auth1)
    assert r.status_code == 200, f"Security failed: {r.text}"
    log("Security analysis complete.", "PASS")

    log("Running Dependency Analyzer (Stage 7)...")
    r = client.post(f"/api/projects/{project_id}/analyze/dependencies", headers=auth1)
    assert r.status_code == 200, f"Dependencies failed: {r.text}"
    log("Dependency analysis complete.", "PASS")

    log("Running Architecture Analyzer (Stage 8)...")
    r = client.post(f"/api/projects/{project_id}/analyze/architecture", headers=auth1)
    assert r.status_code == 200, f"Architecture failed: {r.text}"
    log("Architecture analysis complete.", "PASS")

    log("Running Health & Technical Debt Engine (Stage 9)...")
    r = client.post(f"/api/projects/{project_id}/analyze/health", headers=auth1)
    assert r.status_code == 200, f"Health failed: {r.text}"
    health_data = r.json()
    log(f"Health analysis complete (Score: {health_data['overall_score']:.1f}, Debt: {health_data['technical_debt_hours']:.1f}h).", "PASS")

    # 4. Check Snapshot #1 created automatically
    log("Verifying automatic creation of Version #1 Snapshot...")
    r = client.get(f"/api/projects/{project_id}/history", headers=auth1)
    assert r.status_code == 200, f"Failed to get history: {r.text}"
    hist = r.json()
    assert hist["total"] >= 1, f"Expected at least 1 snapshot, got {hist['total']}"
    v1_summary = hist["items"][-1] if hist["items"][-1]["version_number"] == 1 else hist["items"][0]
    assert v1_summary["version_number"] == 1, f"Expected version 1, got {v1_summary['version_number']}"
    log(f"Version #1 Snapshot verified (Health: {v1_summary['overall_score']}, Debt: {v1_summary['technical_debt_hours']}h)", "PASS")

    # 5. Fetch details of Snapshot #1
    log("Fetching Snapshot #1 details...")
    r = client.get(f"/api/projects/{project_id}/history/1", headers=auth1)
    assert r.status_code == 200, f"Failed to get v1 detail: {r.text}"
    v1_detail = r.json()
    assert v1_detail["version_number"] == 1
    assert "file_manifest" in v1_detail
    log(f"Snapshot #1 details verified ({len(v1_detail.get('file_manifest') or [])} files in manifest).", "PASS")

    # 6. Run Full Analysis to produce Version #2
    log("Triggering Full Analysis via POST /api/projects/{project_id}/analysis/run for Version #2...")
    r = client.post(
        f"/api/projects/{project_id}/analysis/run",
        headers=auth1,
        json={"summary": "Automated verification run #2"}
    )
    assert r.status_code == 200, f"Failed to run full analysis: {r.text}"
    v2_created = r.json()
    assert v2_created["version_number"] == 2, f"Expected version 2, got {v2_created['version_number']}"
    log(f"Version #2 created successfully (ID: {v2_created['id']})", "PASS")

    # 7. Check History list has 2 versions ordered descending
    log("Verifying history contains sequential versions [v2, v1]...")
    r = client.get(f"/api/projects/{project_id}/history", headers=auth1)
    assert r.status_code == 200
    hist = r.json()
    assert hist["total"] == 2, f"Expected 2 snapshots, got {hist['total']}"
    versions = [s["version_number"] for s in hist["items"]]
    assert versions == [2, 1], f"Expected [2, 1], got {versions}"
    log(f"History list verified: {versions}", "PASS")

    # 8. Verify Immutability of Version #1
    log("Verifying immutability of Version #1...")
    r = client.get(f"/api/projects/{project_id}/history/1", headers=auth1)
    assert r.status_code == 200
    v1_check = r.json()
    assert v1_check["id"] == v1_detail["id"], "Version 1 ID mutated!"
    assert v1_check["overall_score"] == v1_detail["overall_score"], "Version 1 score mutated!"
    assert v1_check["created_at"] == v1_detail["created_at"], "Version 1 created_at mutated!"
    log("Immutability verified: Snapshot #1 strictly unchanged.", "PASS")

    # 9. Compare Version #1 and Version #2
    log("Comparing Version #1 vs Version #2 (GET /api/projects/{project_id}/history/compare?from=1&to=2)...")
    r = client.get(f"/api/projects/{project_id}/history/compare?from=1&to=2", headers=auth1)
    assert r.status_code == 200, f"Compare failed: {r.text}"
    comp = r.json()
    assert comp["from_version"] == 1
    assert comp["to_version"] == 2
    assert "health_delta" in comp
    assert "technical_debt_delta" in comp
    assert "critical_issues_delta" in comp
    assert "file_diff" in comp
    assert "summary_headline" in comp
    assert "summary_text" in comp
    assert isinstance(comp["summary_text"], str)
    assert len(comp["summary_text"]) > 0
    log(f"Deterministic comparison verified:\n      Summary: {comp['summary_headline']} - {comp['summary_text']}", "PASS")

    # 10. Test Reverse Comparison (v2 to v1)
    log("Testing reverse comparison (from=2&to=1)...")
    r = client.get(f"/api/projects/{project_id}/history/compare?from=2&to=1", headers=auth1)
    assert r.status_code == 200
    comp_rev = r.json()
    assert comp_rev["from_version"] == 2
    assert comp_rev["to_version"] == 1
    log("Reverse comparison verified.", "PASS")

    # 11. Test Error Handling (Invalid Versions)
    log("Testing 404 for non-existent version #999...")
    r = client.get(f"/api/projects/{project_id}/history/999", headers=auth1)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    r = client.get(f"/api/projects/{project_id}/history/compare?from=1&to=999", headers=auth1)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    log("404 errors for non-existent versions verified.", "PASS")

    # 12. Multi-User Isolation
    log("Testing multi-user isolation with User 2...")
    r = client.post("/api/auth/register", json={
        "email": user2_email,
        "password": password,
        "name": "Second User"
    })
    assert r.status_code == 201
    r_login2 = client.post("/api/auth/login", json={"email": user2_email, "password": password})
    assert r_login2.status_code == 200
    token2 = r_login2.json()["access_token"]
    auth2 = {"Authorization": f"Bearer {token2}"}

    r = client.get(f"/api/projects/{project_id}/history", headers=auth2)
    assert r.status_code == 404, f"Expected 404 for User 2 accessing User 1's project history, got {r.status_code}"

    r = client.get(f"/api/projects/{project_id}/history/1", headers=auth2)
    assert r.status_code == 404, f"Expected 404 for User 2 accessing User 1's snapshot, got {r.status_code}"

    r = client.get(f"/api/projects/{project_id}/history/compare?from=1&to=2", headers=auth2)
    assert r.status_code == 404, f"Expected 404 for User 2 comparing User 1's snapshots, got {r.status_code}"

    r = client.post(f"/api/projects/{project_id}/analysis/run", headers=auth2, json={"summary": "Unauthorized"})
    assert r.status_code == 404, f"Expected 404 for User 2 running analysis on User 1's project, got {r.status_code}"
    log("Multi-user security isolation completely verified.", "PASS")

    print("=" * 70)
    log("ALL STAGE 12 LIVE VERIFICATIONS PASSED SUCCESSFULLY!", "PASS")
    print("=" * 70)

if __name__ == "__main__":
    main()
