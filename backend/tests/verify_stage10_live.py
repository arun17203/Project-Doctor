import sys
import os
import io
import zipfile
import httpx

BASE_URL = "http://127.0.0.1:8000"


def create_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        content = """
import os

API_KEY = "sk-test-abcdef1234567890abcdef1234567890"

def evaluate_risk(data):
    score = 0
    if data:
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k == "risk":
                        if v > 10:
                            score += 10
                        elif v > 5:
                            score += 5
                        else:
                            score += 1
    return score
"""
        z.writestr("analytics.py", content)
    buf.seek(0)
    return buf.getvalue()


def run_live_verification():
    print("=" * 60)
    print("STAGE 10 LIVE VERIFICATION: AI PROBLEM EXPLAINER")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Backend API is healthy.")

    import time
    ts = int(time.time())
    email = f"ai_tester_{ts}@example.com"
    password = "Password123!"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "AI Explainer Tester"},
    )
    assert reg_res.status_code in (200, 201), f"Registration failed: {reg_res.text}"
    
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] User registered and authenticated: {email}")

    proj_res = client.post(
        "/api/projects",
        json={
            "name": f"AI Diagnostic Target {ts}",
            "description": "Stage 10 test",
            "source_type": "zip"
        },
        headers=headers,
    )
    assert proj_res.status_code == 201, f"Create project failed: {proj_res.text}"
    project_id = proj_res.json()["id"]
    print(f"[PASS] Project created: {project_id}")

    zip_bytes = create_test_zip()
    upload_res = client.post(
        f"/api/projects/{project_id}/upload",
        files={"file": ("code.zip", zip_bytes, "application/zip")},
        headers=headers,
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    print("[PASS] ZIP codebase uploaded and extracted.")

    scan_res = client.post(f"/api/projects/{project_id}/scan", headers=headers)
    assert scan_res.status_code == 200, f"Scan failed: {scan_res.text}"
    print("[PASS] Repository scan completed.")

    qual_res = client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
    assert qual_res.status_code == 200, f"Quality analysis failed: {qual_res.text}"
    print(f"[PASS] Quality analysis completed. Issues found: {qual_res.json()['total_issues']}")

    sec_res = client.post(f"/api/projects/{project_id}/analyze/security", headers=headers)
    assert sec_res.status_code == 200, f"Security audit failed: {sec_res.text}"
    print(f"[PASS] Security audit completed. Issues found: {sec_res.json()['total_issues']}")

    issues_res = client.get(f"/api/projects/{project_id}/quality/issues", headers=headers)
    assert issues_res.status_code == 200
    quality_issues = issues_res.json()
    assert len(quality_issues) > 0, "Expected at least 1 quality issue"
    test_issue_id = quality_issues[0]["id"]
    print(f"[PASS] Selected Quality Issue for explanation testing: {test_issue_id}")

    exp_get = client.get(f"/api/issues/{test_issue_id}/explanation", headers=headers)
    assert exp_get.status_code == 404, f"Expected 404 before explanation, got {exp_get.status_code}"
    print("[PASS] GET /api/issues/{issue_id}/explanation returned 404 as expected for ungenerated explanation.")

    exp_post = client.post(f"/api/issues/{test_issue_id}/explain", headers=headers)
    print(f"Explanation API status code: {exp_post.status_code}")
    if exp_post.status_code == 200:
        data = exp_post.json()
        print("[PASS] Real Gemini explanation returned:")
        print(f"  Summary: {data['summary']}")
        print(f"  Why it matters: {data['why_it_matters'][:80]}...")
        print(f"  Action plan steps: {len(data['developer_action'])}")
    elif exp_post.status_code == 503:
        data = exp_post.json()
        print(f"[PASS] Graceful degradation verified (HTTP 503): {data['detail']}")
    else:
        raise AssertionError(f"Unexpected response code {exp_post.status_code}: {exp_post.text}")

    unauth_res = client.post(f"/api/issues/{test_issue_id}/explain")
    assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
    print("[PASS] Access control verified: Unauthenticated request rejected with 401.")

    print("\n" + "=" * 60)
    print("ALL STAGE 10 LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_live_verification()
