import os
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
import git
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


@pytest.mark.asyncio
async def test_github_import_valid_url_mocked():
    """Test importing a valid GitHub repository with mocked Git clone."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "gh_valid@test.dev", "GH Valid")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project
        create_res = await client.post(
            "/api/projects",
            json={
                "name": "Cloned Project",
                "source_type": "github",
                "source_url": "https://github.com/octocat/Hello-World"
            },
            headers=headers
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # Mock git.Repo.clone_from to simulate a successful clone by writing a file into target_dir
        def fake_clone_from(url, target_dir, **kwargs):
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, "main.py"), "w") as f:
                f.write("print('Hello from clone')\n")
            with open(os.path.join(target_dir, "README.md"), "w") as f:
                f.write("# Hello-World\n")
            # Create a .git dir to verify post-clone sanitization strips it
            git_dir = os.path.join(target_dir, ".git")
            os.makedirs(git_dir, exist_ok=True)
            with open(os.path.join(git_dir, "config"), "w") as f:
                f.write("[core]\n")

        with patch("git.Repo.clone_from", side_effect=fake_clone_from):
            import_res = await client.post(
                f"/api/projects/{project_id}/github",
                json={"github_url": "https://github.com/octocat/Hello-World"},
                headers=headers
            )
            assert import_res.status_code == 200
            data = import_res.json()
            assert data["status"] == "READY"
            assert data["source_type"] == "github"
            assert data["source_url"] == "https://github.com/octocat/Hello-World"


@pytest.mark.asyncio
async def test_github_import_invalid_url():
    """Test invalid GitHub URLs (wrong domain, malformed structure)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "gh_invalid@test.dev", "GH Invalid")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Bad URL Project", "source_type": "github"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # GitLab URL instead of GitHub
        res_gitlab = await client.post(
            f"/api/projects/{project_id}/github",
            json={"github_url": "https://gitlab.com/owner/repo"},
            headers=headers
        )
        assert res_gitlab.status_code == 400 or res_gitlab.status_code == 422

        # Malformed path
        res_malformed = await client.post(
            f"/api/projects/{project_id}/github",
            json={"github_url": "https://github.com/invalid_repo_only"},
            headers=headers
        )
        assert res_malformed.status_code == 400 or res_malformed.status_code == 422


@pytest.mark.asyncio
async def test_github_import_repo_not_found():
    """Test handling when repository is not found or private."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "gh_404@test.dev", "GH 404")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Not Found Project", "source_type": "github"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # Mock GitCommandError with 'not found'
        error = git.exc.GitCommandError(
            command=["git", "clone"],
            status=128,
            stderr="fatal: repository 'https://github.com/nonexistent/repo' not found"
        )
        with patch("git.Repo.clone_from", side_effect=error):
            res = await client.post(
                f"/api/projects/{project_id}/github",
                json={"github_url": "https://github.com/nonexistent/repo"},
                headers=headers
            )
            assert res.status_code == 400
            assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_github_import_network_failure():
    """Test handling when network fails during clone."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "gh_net@test.dev", "GH Net")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Network Fail Project", "source_type": "github"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        error = git.exc.GitCommandError(
            command=["git", "clone"],
            status=128,
            stderr="fatal: unable to access 'https://github.com/owner/repo/': Could not resolve host: github.com"
        )
        with patch("git.Repo.clone_from", side_effect=error):
            res = await client.post(
                f"/api/projects/{project_id}/github",
                json={"github_url": "https://github.com/owner/repo"},
                headers=headers
            )
            assert res.status_code == 400
            assert "network error" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_github_import_empty_repository():
    """Test handling when cloned repository contains no files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "gh_empty@test.dev", "GH Empty")
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/projects",
            json={"name": "Empty Repo Project", "source_type": "github"},
            headers=headers
        )
        project_id = create_res.json()["id"]

        # Fake clone creates an empty directory
        def fake_clone_empty(url, target_dir, **kwargs):
            os.makedirs(target_dir, exist_ok=True)

        with patch("git.Repo.clone_from", side_effect=fake_clone_empty):
            res = await client.post(
                f"/api/projects/{project_id}/github",
                json={"github_url": "https://github.com/owner/empty-repo"},
                headers=headers
            )
            assert res.status_code == 400
            assert "no valid files" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_github_import_user_isolation():
    """Test that User B cannot trigger a GitHub import on User A's project."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await get_auth_token(client, "user_a_gh@test.dev", "User A")
        token_b = await get_auth_token(client, "user_b_gh@test.dev", "User B")

        create_res = await client.post(
            "/api/projects",
            json={"name": "A's Repo", "source_type": "github"},
            headers={"Authorization": f"Bearer {token_a}"}
        )
        project_id = create_res.json()["id"]

        # User B tries to trigger import
        res = await client.post(
            f"/api/projects/{project_id}/github",
            json={"github_url": "https://github.com/owner/repo"},
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res.status_code == 404
