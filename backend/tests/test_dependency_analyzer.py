import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.analyzers.dependency.manifest_parser import (
    parse_requirements_txt,
    parse_pyproject_toml,
    parse_pipfile,
    parse_package_json,
    parse_package_lock_json,
    parse_pom_xml,
)
from backend.app.analyzers.dependency.vulnerability_service import VulnerabilityService
from backend.app.analyzers.dependency.version_checker import VersionChecker
from backend.app.analyzers.dependency.engine import DependencyAuditEngine


async def get_auth_token(client: AsyncClient, email: str, name: str) -> str:
    """Helper to register and login a test user."""
    await client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "DepAuditPass123!"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "DepAuditPass123!"
    })
    return res.json()["access_token"]


def create_manifests_test_zip() -> bytes:
    """Creates a zip archive containing multiple manifests across Python, Node.js, and Java."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. requirements.txt
        zf.writestr(
            "requirements.txt",
            "# Production dependencies\n"
            "requests==2.28.1\n"
            "flask>=2.0.0; python_version >= '3.8'\n"
            "cryptography==3.4.7 # vulnerable\n"
            "# comments and empty lines\n\n"
            "-r other-reqs.txt\n"
        )

        # 2. package.json & package-lock.json
        pkg_json = """{
  "name": "my-sample-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2",
    "lodash": "4.17.15"
  },
  "devDependencies": {
    "jest": "^29.5.0"
  }
}"""
        zf.writestr("package.json", pkg_json)

        pkg_lock = """{
  "name": "my-sample-app",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "packages": {
    "": {
      "dependencies": {
        "express": "^4.18.2",
        "lodash": "4.17.15"
      },
      "devDependencies": {
        "jest": "^29.5.0"
      }
    },
    "node_modules/express": {
      "version": "4.18.2"
    },
    "node_modules/lodash": {
      "version": "4.17.15"
    },
    "node_modules/accepts": {
      "version": "1.3.8"
    }
  }
}"""
        zf.writestr("package-lock.json", pkg_lock)

        # 3. pom.xml
        pom_xml = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>sample-service</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
      <version>3.0.0</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>"""
        zf.writestr("pom.xml", pom_xml)

    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Unit Tests for Manifest Parsers
# ---------------------------------------------------------------------------

def test_requirements_txt_parser():
    content = """
    # Core requirements
    fastapi==0.100.0
    uvicorn>=0.20.0,<0.30.0
    sqlalchemy~=2.0.0; sys_platform == 'win32'
    # invalid lines
    --extra-index-url https://example.com
    invalid@#$line
    requests
    """
    deps = parse_requirements_txt(content, "requirements.txt")
    names = {d.name: d for d in deps}

    assert "fastapi" in names
    assert names["fastapi"].declared_version == "==0.100.0"
    assert names["fastapi"].resolved_version == "0.100.0"
    assert names["fastapi"].dependency_type == "direct"
    assert names["fastapi"].ecosystem == "PyPI"

    assert "uvicorn" in names
    assert names["uvicorn"].declared_version == ">=0.20.0,<0.30.0"
    assert names["uvicorn"].resolved_version is None

    assert "sqlalchemy" in names
    assert "requests" in names
    assert names["requests"].declared_version is None


def test_pyproject_toml_parser():
    # PEP 621
    pep621_content = """
    [project]
    name = "pep621-app"
    dependencies = [
        "httpx>=0.24.0",
        "pydantic==2.5.0",
    ]
    [project.optional-dependencies]
    dev = [
        "pytest>=7.0.0"
    ]
    """
    deps = parse_pyproject_toml(pep621_content, "pyproject.toml")
    dep_map = {d.name: d for d in deps}
    assert "httpx" in dep_map
    assert "pydantic" in dep_map
    assert dep_map["pydantic"].resolved_version == "2.5.0"
    assert "pytest" in dep_map
    assert dep_map["pytest"].dependency_type == "dev"

    # Poetry
    poetry_content = """
    [tool.poetry.dependencies]
    python = "^3.10"
    fastapi = "^0.104.0"
    celery = { version = "5.3.0", optional = true }

    [tool.poetry.group.dev.dependencies]
    flake8 = "^6.0.0"
    """
    p_deps = parse_pyproject_toml(poetry_content, "pyproject.toml")
    p_map = {d.name: d for d in p_deps}
    assert "python" not in p_map  # Python interpreter omitted
    assert "fastapi" in p_map
    assert "celery" in p_map
    assert "flake8" in p_map
    assert p_map["flake8"].dependency_type == "dev"


def test_pipfile_parser():
    content = """
    [packages]
    requests = "==2.28.1"
    flask = "*"

    [dev-packages]
    pytest = ">=7.0.0"
    """
    deps = parse_pipfile(content, "Pipfile")
    dep_map = {d.name: d for d in deps}
    assert "requests" in dep_map
    assert dep_map["requests"].resolved_version == "2.28.1"
    assert "flask" in dep_map
    assert "pytest" in dep_map
    assert dep_map["pytest"].dependency_type == "dev"


def test_package_json_parser():
    content = """{
      "dependencies": {
        "react": "^18.2.0",
        "axios": "~1.4.0"
      },
      "devDependencies": {
        "typescript": "^5.0.0"
      },
      "peerDependencies": {
        "react-dom": "^18.2.0"
      }
    }"""
    deps = parse_package_json(content, "frontend/package.json")
    dep_map = {d.name: d for d in deps}

    assert "react" in dep_map
    assert dep_map["react"].dependency_type == "direct"
    assert dep_map["react"].ecosystem == "npm"

    assert "typescript" in dep_map
    assert dep_map["typescript"].dependency_type == "dev"

    assert "react-dom" in dep_map
    assert dep_map["react-dom"].dependency_type == "peer"


def test_package_lock_json_parser():
    content = """{
      "name": "sample",
      "lockfileVersion": 3,
      "packages": {
        "node_modules/react": {
          "version": "18.2.0"
        },
        "node_modules/loose-envify": {
          "version": "1.4.0"
        }
      }
    }"""
    # direct names passed in
    deps = parse_package_lock_json(content, "package-lock.json", direct_names={"react"})
    dep_map = {d.name: d for d in deps}

    assert "react" in dep_map
    assert dep_map["react"].dependency_type == "direct"
    assert dep_map["react"].resolved_version == "18.2.0"

    assert "loose-envify" in dep_map
    assert dep_map["loose-envify"].dependency_type == "transitive"
    assert dep_map["loose-envify"].resolved_version == "1.4.0"


def test_pom_xml_parser():
    content = """<project>
      <dependencies>
        <dependency>
          <groupId>org.apache.commons</groupId>
          <artifactId>commons-lang3</artifactId>
          <version>3.12.0</version>
        </dependency>
        <dependency>
          <groupId>org.mockito</groupId>
          <artifactId>mockito-core</artifactId>
          <version>5.2.0</version>
          <scope>test</scope>
        </dependency>
      </dependencies>
    </project>"""
    deps = parse_pom_xml(content, "pom.xml")
    dep_map = {d.name: d for d in deps}

    assert "org.apache.commons:commons-lang3" in dep_map
    assert dep_map["org.apache.commons:commons-lang3"].resolved_version == "3.12.0"
    assert dep_map["org.apache.commons:commons-lang3"].dependency_type == "direct"
    assert dep_map["org.apache.commons:commons-lang3"].ecosystem == "Maven"

    assert "org.mockito:mockito-core" in dep_map
    assert dep_map["org.mockito:mockito-core"].dependency_type == "dev"


def test_malformed_and_empty_manifests():
    """Manifest parsers should gracefully return empty lists on malformed or empty content."""
    assert parse_requirements_txt("", "requirements.txt") == []
    assert parse_package_json("{ broken json", "package.json") == []
    assert parse_package_lock_json("not a json", "package-lock.json") == []
    assert parse_pyproject_toml("[tool.poetry\nbroken", "pyproject.toml") == []
    assert parse_pipfile("broken pipfile ]]", "Pipfile") == []
    assert parse_pom_xml("<project><broken></project>", "pom.xml") == []


# ---------------------------------------------------------------------------
# Unit Tests for Vulnerability Service & Version Checker
# ---------------------------------------------------------------------------

def test_version_checker_status():
    checker = VersionChecker()
    checker.set_mock_latest("requests", "pypi", "2.31.0")

    # Current
    st_curr = checker.determine_status(
        current_version="2.31.0",
        latest_version="2.31.0",
        vulnerability_count=0,
        was_network_error=False,
    )
    assert st_curr == "CURRENT"

    # Outdated
    st_out = checker.determine_status(
        current_version="2.28.1",
        latest_version="2.31.0",
        vulnerability_count=0,
        was_network_error=False,
    )
    assert st_out == "OUTDATED"

    # Vulnerability takes precedence over outdated
    st_vuln = checker.determine_status(
        current_version="2.28.1",
        latest_version="2.31.0",
        vulnerability_count=2,
        was_network_error=False,
    )
    assert st_vuln == "VULNERABLE"

    # Network error / unknown
    st_unk = checker.determine_status(
        current_version="2.28.1",
        latest_version=None,
        vulnerability_count=0,
        was_network_error=True,
    )
    assert st_unk == "UNKNOWN"


def test_mock_osv_vulnerability_advisory():
    vuln_service = VulnerabilityService()
    vuln_service.set_mock_vulnerabilities(
        package_name="lodash",
        ecosystem="npm",
        version="4.17.15",
        advisories=[
            {
                "id": "GHSA-p6mc-m468-83gw",
                "severity": "HIGH",
                "affected_versions": "< 4.17.19",
                "fixed_version": "4.17.19",
                "summary": "Prototype Pollution in lodash",
                "reference_url": "https://osv.dev/vulnerability/GHSA-p6mc-m468-83gw",
            }
        ],
    )

    advisories, net_err = vuln_service.check_vulnerabilities("lodash", "npm", "4.17.15")
    assert net_err is False
    assert len(advisories) == 1
    assert advisories[0]["id"] == "GHSA-p6mc-m468-83gw"
    assert advisories[0]["severity"] == "HIGH"
    assert advisories[0]["fixed_version"] == "4.17.19"


# ---------------------------------------------------------------------------
# Integration Tests (API Endpoints, Ownership & Full Lifecycle)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_dependency_analysis_flow():
    """Full test of dependency audit from project creation to query endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "dep_user1@example.com", "Dep User 1")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project and upload ZIP with manifests
        create_proj_res = await client.post(
            "/api/projects",
            json={"name": "Manifests Project", "description": "Testing Stage 7", "source_type": "zip"},
            headers=headers,
        )
        assert create_proj_res.status_code == 201, create_proj_res.text
        project_id = create_proj_res.json()["id"]

        zip_bytes = create_manifests_test_zip()
        files = {"file": ("manifests_project.zip", zip_bytes, "application/zip")}
        upload_res = await client.post(f"/api/projects/{project_id}/upload", headers=headers, files=files)
        assert upload_res.status_code == 200, upload_res.text

        # 2. Run repository scanner
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200, scan_res.text

        # 3. Trigger dependency audit
        audit_res = await client.post(f"/api/projects/{project_id}/analyze/dependencies", headers=headers)
        assert audit_res.status_code == 200, audit_res.text
        audit_data = audit_res.json()

        assert audit_data["status"] == "COMPLETED"
        assert audit_data["total_dependencies"] > 0
        assert audit_data["direct_dependencies"] > 0

        # 4. Get dependency summary
        summary_res = await client.get(f"/api/projects/{project_id}/dependencies/summary", headers=headers)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["total_dependencies"] == audit_data["total_dependencies"]
        assert len(summary_data["manifests"]) >= 3
        assert "PyPI" in summary_data["by_ecosystem"]
        assert "npm" in summary_data["by_ecosystem"]
        assert "Maven" in summary_data["by_ecosystem"]

        # 5. List dependencies with filters
        deps_res = await client.get(f"/api/projects/{project_id}/dependencies", headers=headers)
        assert deps_res.status_code == 200
        all_deps = deps_res.json()
        assert len(all_deps) > 0

        # Filter by ecosystem
        npm_res = await client.get(f"/api/projects/{project_id}/dependencies?ecosystem=npm", headers=headers)
        assert npm_res.status_code == 200
        npm_deps = npm_res.json()
        assert len(npm_deps) > 0
        assert all(d["ecosystem"] == "npm" for d in npm_deps)

        # Filter by search
        search_res = await client.get(f"/api/projects/{project_id}/dependencies?search=requests", headers=headers)
        assert search_res.status_code == 200
        search_deps = search_res.json()
        assert any("requests" in d["name"] for d in search_deps)

        # 6. Get single dependency detail
        target_dep = all_deps[0]
        single_res = await client.get(f"/api/projects/{project_id}/dependencies/{target_dep['id']}", headers=headers)
        assert single_res.status_code == 200
        assert single_res.json()["name"] == target_dep["name"]

        # 7. List dependency issues
        issues_res = await client.get(f"/api/projects/{project_id}/dependencies/issues", headers=headers)
        assert issues_res.status_code == 200
        issues = issues_res.json()
        assert isinstance(issues, list)


@pytest.mark.anyio
async def test_dependency_analysis_access_control():
    """Non-owners cannot trigger analysis or view dependency information."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await get_auth_token(client, "owner_dep@example.com", "Owner Dep")
        other_token = await get_auth_token(client, "other_dep@example.com", "Other Dep")

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Owner creates project
        create_res = await client.post(
            "/api/projects",
            json={"name": "Owner Project", "source_type": "zip"},
            headers=owner_headers,
        )
        assert create_res.status_code == 201
        proj_id = create_res.json()["id"]

        zip_bytes = create_manifests_test_zip()
        files = {"file": ("project.zip", zip_bytes, "application/zip")}
        upload_res = await client.post(f"/api/projects/{proj_id}/upload", headers=owner_headers, files=files)
        assert upload_res.status_code == 200

        # Other user tries to trigger analysis -> 404
        bad_trigger = await client.post(f"/api/projects/{proj_id}/analyze/dependencies", headers=other_headers)
        assert bad_trigger.status_code == 404

        # Other user tries to get summary -> 404
        bad_get = await client.get(f"/api/projects/{proj_id}/dependencies/summary", headers=other_headers)
        assert bad_get.status_code == 404
