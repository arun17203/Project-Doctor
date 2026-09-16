"""Live End-to-End Authentication Verification Script.

Tests against live running server:
1. Register
2. Attempt Duplicate Register (Expect 400)
3. Login (Expect JWT Token)
4. Login with Wrong Password (Expect 401)
5. Access Protected Endpoint /api/auth/me with Bearer Token (Expect 200)
6. Access Protected Endpoint without Token (Expect 401)
7. Access Protected Endpoint with Invalid Token (Expect 401)
8. Call /api/auth/logout (Expect 200)
"""
import sys
import httpx

BASE_URL = "http://127.0.0.1:8000/api"

def run_verification():
    print(f"[*] Connecting to live server at {BASE_URL}...")
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 0. Health check
    h = client.get("/health")
    assert h.status_code == 200, f"Health check failed: {h.text}"
    print(f"[+] Health check OK: {h.json()['status']} (db: {h.json()['database']})")

    # 1. Registration
    email = "live.user@projectdoctor.dev"
    password = "SecurePassword456!"
    name = "Dr. Margaret Hamilton"

    reg_payload = {"name": name, "email": email, "password": password}
    # Clean up test user if exists from prior run
    reg_res = client.post("/auth/register", json=reg_payload)
    if reg_res.status_code == 400 and "already registered" in reg_res.text.lower():
        print(f"[*] User {email} already registered from earlier test. Continuing with login verification.")
    else:
        assert reg_res.status_code == 201, f"Registration failed ({reg_res.status_code}): {reg_res.text}"
        reg_data = reg_res.json()
        assert reg_data["name"] == name
        assert reg_data["email"] == email
        assert "password_hash" not in reg_data
        print(f"[+] 1. Registration SUCCESS: User ID {reg_data['id']}, Name: {reg_data['name']}")

    # 2. Duplicate Registration Test
    dup_res = client.post("/auth/register", json=reg_payload)
    assert dup_res.status_code == 400, f"Expected 400 for duplicate, got {dup_res.status_code}"
    print(f"[+] 2. Duplicate registration correctly rejected: {dup_res.json()['detail']}")

    # 3. Login with Correct Credentials
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, f"Login failed ({login_res.status_code}): {login_res.text}"
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert "password_hash" not in login_data["user"]
    token = login_data["access_token"]
    print(f"[+] 3. Login SUCCESS: Received JWT token ({token[:20]}...)")

    # 4. Login with Incorrect Password
    wrong_res = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert wrong_res.status_code == 401, f"Expected 401, got {wrong_res.status_code}"
    print(f"[+] 4. Incorrect password rejected with 401: {wrong_res.json()['detail']}")

    # 5. Access Protected Endpoint (/api/auth/me) with JWT
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200, f"Protected endpoint failed ({me_res.status_code}): {me_res.text}"
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["name"] == name
    assert "password_hash" not in me_data
    print(f"[+] 5. Protected endpoint access SUCCESS: Hello {me_data['name']} ({me_data['email']})")

    # 6. Access Protected Endpoint WITHOUT Token
    unauth_res = client.get("/auth/me")
    assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
    print(f"[+] 6. Protected endpoint correctly rejected without token: 401 Unauthorized")

    # 7. Access Protected Endpoint WITH Forged Token
    forged_res = client.get("/auth/me", headers={"Authorization": "Bearer forged.token.here"})
    assert forged_res.status_code == 401, f"Expected 401, got {forged_res.status_code}"
    print(f"[+] 7. Protected endpoint correctly rejected with invalid token: 401 Unauthorized")

    # 8. Logout
    logout_res = client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    print(f"[+] 8. Logout endpoint SUCCESS: {logout_res.json()['message']}")

    # 9. Test Frontend Proxy connection to /api/auth
    print("[*] Testing frontend Vite dev server proxy (http://127.0.0.1:5173/api/auth/me)...")
    proxy_client = httpx.Client(base_url="http://127.0.0.1:5173/api", timeout=10.0)
    proxy_res = proxy_client.get("/auth/me", headers=headers)
    assert proxy_res.status_code == 200
    assert proxy_res.json()["email"] == email
    print(f"[+] 9. Frontend Vite Reverse-Proxy to Backend Auth SUCCESS!")

    print("\n=======================================================")
    print("ALL 9 STAGE 2 AUTHENTICATION CHECKS PASSED LIVE!")
    print("=======================================================")


if __name__ == "__main__":
    run_verification()
