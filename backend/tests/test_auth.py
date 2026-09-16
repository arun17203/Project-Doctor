import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_registration_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "Dr. Alan Turing",
            "email": "alan.turing@doctor.dev",
            "password": "SuperSecretPassword123!"
        }
        res = await client.post("/api/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Dr. Alan Turing"
        assert data["email"] == "alan.turing@doctor.dev"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data


@pytest.mark.asyncio
async def test_registration_duplicate_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register first user
        payload1 = {
            "name": "Dr. Alan Turing",
            "email": "alan.turing@doctor.dev",
            "password": "SuperSecretPassword123!"
        }
        res1 = await client.post("/api/auth/register", json=payload1)
        assert res1.status_code == 201

        # Attempt to register with the same email
        payload2 = {
            "name": "Duplicate Turing",
            "email": "alan.turing@doctor.dev",
            "password": "AnotherPassword123!"
        }
        res2 = await client.post("/api/auth/register", json=payload2)
        assert res2.status_code == 400
        data = res2.json()
        assert "detail" in data
        assert "already registered" in data["detail"].lower()


@pytest.mark.asyncio
async def test_registration_validation_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid email and short password
        payload = {
            "name": "",
            "email": "not-an-email",
            "password": "123"
        }
        res = await client.post("/api/auth/register", json=payload)
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user first
        reg_payload = {
            "name": "Grace Hopper",
            "email": "grace.hopper@doctor.dev",
            "password": "CompilerQueen123!"
        }
        reg_res = await client.post("/api/auth/register", json=reg_payload)
        assert reg_res.status_code == 201

        # Perform login
        login_payload = {
            "email": "grace.hopper@doctor.dev",
            "password": "CompilerQueen123!"
        }
        res = await client.post("/api/auth/login", json=login_payload)
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "grace.hopper@doctor.dev"
        assert data["user"]["name"] == "Grace Hopper"
        assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_login_incorrect_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user first
        reg_payload = {
            "name": "Ada Lovelace",
            "email": "ada.lovelace@doctor.dev",
            "password": "FirstProgrammer123!"
        }
        await client.post("/api/auth/register", json=reg_payload)

        # Login with incorrect password
        payload = {
            "email": "ada.lovelace@doctor.dev",
            "password": "WrongPassword999!"
        }
        res = await client.post("/api/auth/login", json=payload)
        assert res.status_code == 401
        data = res.json()
        assert "detail" in data
        assert "invalid email or password" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": "nonexistent@doctor.dev",
            "password": "SomePassword123!"
        }
        res = await client.post("/api/auth/login", json=payload)
        assert res.status_code == 401
        data = res.json()
        assert "detail" in data
        assert "invalid email or password" in data["detail"].lower()


@pytest.mark.asyncio
async def test_jwt_protected_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register and Login to get token
        reg_payload = {
            "name": "Linus Torvalds",
            "email": "linus@doctor.dev",
            "password": "LinuxKernelPass123!"
        }
        await client.post("/api/auth/register", json=reg_payload)

        login_res = await client.post("/api/auth/login", json={
            "email": "linus@doctor.dev",
            "password": "LinuxKernelPass123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # 2. Access protected endpoint with Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_res = await client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        user_data = me_res.json()
        assert user_data["email"] == "linus@doctor.dev"
        assert user_data["name"] == "Linus Torvalds"
        assert "password_hash" not in user_data

        # 3. Access without token should fail with 401
        unauth_res = await client.get("/api/auth/me")
        assert unauth_res.status_code == 401

        # 4. Access with forged/invalid token should fail with 401
        invalid_res = await client.get("/api/auth/me", headers={"Authorization": "Bearer forged.invalid.token"})
        assert invalid_res.status_code == 401

        # 5. Logout endpoint
        logout_res = await client.post("/api/auth/logout", headers=headers)
        assert logout_res.status_code == 200
