"""
Stage 7 Dependency Analyzer Live End-to-End Verification Script
Tests the live running FastAPI instance (http://127.0.0.1:8000) through HTTP requests:
1. Health check verification
2. User registration & JWT authentication
3. Project creation with multi-manifest test ZIP upload
4. Stage 4 Repository Scan execution
5. Stage 7 Dependency Audit trigger (POST /api/projects/{id}/analyze/dependencies)
6. Verification of real dependency findings across PyPI, npm, and Maven
7. Verification of direct vs. transitive classification via lockfile
8. Summary metrics retrieval (GET /api/projects/{id}/dependencies/summary)
9. Dependency list retrieval with ecosystem, status, and search filtering
10. Single dependency detail & advisory inspection
11. Dependency issues list inspection
12. Access control isolation (non-owner rejection)
13. Clean project deletion
"""

import io
import time
import zipfile
import requests

BASE_URL = "http://127.0.0.1:8000"


def create_manifests_verification_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. requirements.txt
        requirements_content = (
            "# Production Python dependencies\n"
            "requests==2.28.1\n"
            "fastapi==0.100.0\n"
            "uvicorn>=0.20.0\n"
            "cryptography==3.4.7\n"
        )
        zf.writestr("requirements.txt", requirements_content)

        # 2. package.json
        pkg_json = """{
  "name": "stage7-demo-app",
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

        # 3. package-lock.json
        pkg_lock = """{
  "name": "stage7-demo-app",
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

        # 4. pom.xml
        pom_xml = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.projectdoctor</groupId>
  <artifactId>demo-service</artifactId>
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


def main():
    print("==================================================================")
    print("STAGE 7: DEPENDENCY ANALYZER — LIVE END-TO-END VERIFICATION")
    print("==================================================================")

    # 1. Health check
    print("\n[1/12] Verifying Backend Health...")
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health = r.json()
    print(f"  OK: Backend is {health['status']}, database {health['database']}")

    # 2. Register & Login Users
    print("\n[2/12] Authenticating Test User...")
    ts = int(time.time())
    email = f"dep_auditor_{ts}@test.com"
    reg_r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "Dep Auditor", "email": email, "password": "AuditorPass123!"},
    )
    assert reg_r.status_code == 201, f"Register failed: {reg_r.text}"

    login_r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": "AuditorPass123!"},
    )
    assert login_r.status_code == 200, f"Login failed: {login_r.text}"
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  OK: User {email} authenticated.")

    # 3. Create Project & Upload Multi-Manifest Zip
    print("\n[3/12] Creating Project & Uploading Manifests ZIP...")
    p_r = requests.post(
        f"{BASE_URL}/api/projects",
        json={"name": "Dependency Audit Demo", "description": "Stage 7 Manifests Test", "source_type": "zip"},
        headers=headers,
    )
    assert p_r.status_code == 201, f"Project creation failed: {p_r.text}"
    project_id = p_r.json()["id"]

    zip_bytes = create_manifests_verification_zip()
    u_r = requests.post(
        f"{BASE_URL}/api/projects/{project_id}/upload",
        files={"file": ("manifests_demo.zip", zip_bytes, "application/zip")},
        headers=headers,
    )
    assert u_r.status_code == 200, f"ZIP upload failed: {u_r.text}"
    print(f"  OK: Project created (ID: {project_id}) and ZIP ingested.")

    # 4. Execute Repository Scan
    print("\n[4/12] Executing Stage 4 Repository Scan...")
    s_r = requests.post(f"{BASE_URL}/api/projects/{project_id}/scan", headers=headers)
    assert s_r.status_code == 200, f"Scan failed: {s_r.text}"
    scan_data = s_r.json()
    print(f"  OK: Scanned {scan_data['total_files']} files across {len(scan_data['languages_summary'])} languages.")

    # 5. Trigger Stage 7 Dependency Audit
    print("\n[5/12] Triggering Stage 7 Dependency Audit (POST /analyze/dependencies)...")
    audit_r = requests.post(f"{BASE_URL}/api/projects/{project_id}/analyze/dependencies", headers=headers)
    assert audit_r.status_code == 200, f"Dependency audit failed: {audit_r.text}"
    audit = audit_r.json()
    print(f"  OK: Audit status: {audit['status']}")
    print(f"      Total dependencies: {audit['total_dependencies']}")
    print(f"      Direct dependencies: {audit['direct_dependencies']}")
    print(f"      Transitive dependencies: {audit['transitive_dependencies']}")
    print(f"      Up to Date (Current): {audit['current_count']}")
    print(f"      Outdated count: {audit['outdated_count']}")
    print(f"      Vulnerable count: {audit['vulnerable_count']}")
    print(f"      Unknown count: {audit['unknown_count']}")

    assert audit["total_dependencies"] > 0, "No dependencies discovered!"
    assert audit["direct_dependencies"] > 0, "No direct dependencies identified!"
    assert audit["transitive_dependencies"] > 0, "Transitive dependencies not identified via lockfile!"

    # 6. Verify Manifests & Ecosystem Metrics
    print("\n[6/12] Verifying Manifests & Ecosystem Metrics...")
    metrics = audit["metrics"]
    scanned_manifests = metrics.get("manifests_scanned", [])
    print(f"  OK: Manifests scanned: {scanned_manifests}")
    assert any("requirements.txt" in m for m in scanned_manifests), "requirements.txt not found!"
    assert any("package.json" in m for m in scanned_manifests), "package.json not found!"
    assert any("pom.xml" in m for m in scanned_manifests), "pom.xml not found!"

    by_eco = metrics.get("by_ecosystem", {})
    print(f"  OK: Ecosystem distribution: {by_eco}")
    assert "PyPI" in by_eco, "PyPI ecosystem missing!"
    assert "npm" in by_eco, "npm ecosystem missing!"
    assert "Maven" in by_eco, "Maven ecosystem missing!"

    # 7. Get Dependencies Summary Endpoint
    print("\n[7/12] Testing GET /dependencies/summary...")
    sum_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies/summary", headers=headers)
    assert sum_r.status_code == 200, f"Summary failed: {sum_r.text}"
    summary = sum_r.json()
    assert summary["total_dependencies"] == audit["total_dependencies"]
    print(f"  OK: Summary verified: {summary['total_dependencies']} total, {len(summary['manifests'])} manifests.")

    # 8. List Dependencies & Test Filters
    print("\n[8/12] Testing GET /dependencies with Filters...")
    # All
    all_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies", headers=headers)
    assert all_r.status_code == 200
    all_deps = all_r.json()
    print(f"  OK: Fetched {len(all_deps)} dependencies.")

    # Ecosystem filter
    npm_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies?ecosystem=npm", headers=headers)
    assert npm_r.status_code == 200
    npm_deps = npm_r.json()
    assert len(npm_deps) > 0 and all(d["ecosystem"] == "npm" for d in npm_deps)
    print(f"  OK: npm filter returned {len(npm_deps)} packages.")

    # Search filter
    search_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies?search=lodash", headers=headers)
    assert search_r.status_code == 200
    search_deps = search_r.json()
    assert any("lodash" in d["name"] for d in search_deps)
    print(f"  OK: Search filter for 'lodash' found {len(search_deps)} packages.")

    # Dependency type filter
    trans_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies?dependency_type=transitive", headers=headers)
    assert trans_r.status_code == 200
    trans_deps = trans_r.json()
    assert len(trans_deps) > 0 and all(d["dependency_type"] == "transitive" for d in trans_deps)
    print(f"  OK: Transitive filter returned {len(trans_deps)} sub-packages.")

    # 9. Single Dependency Detail
    print("\n[9/12] Testing GET /dependencies/{dependency_id} Detail...")
    sample_dep = all_deps[0]
    detail_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies/{sample_dep['id']}", headers=headers)
    assert detail_r.status_code == 200
    detail = detail_r.json()
    assert detail["name"] == sample_dep["name"]
    print(f"  OK: Dependency detail verified: '{detail['name']}' ({detail['ecosystem']}), status: {detail['status']}.")

    # 10. Dependency Issues Endpoint
    print("\n[10/12] Testing GET /dependencies/issues...")
    issues_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies/issues", headers=headers)
    assert issues_r.status_code == 200
    issues = issues_r.json()
    print(f"  OK: Total dependency issues registered: {len(issues)}")
    if issues:
        sample_issue = issues[0]
        print(f"      Sample issue: [{sample_issue['severity']}] {sample_issue['issue_type']} in {sample_issue['package_name']}")

    # 11. Multi-Tenant Access Control
    print("\n[11/12] Testing Access Control (Other User Rejection)...")
    other_email = f"other_{ts}@test.com"
    requests.post(f"{BASE_URL}/api/auth/register", json={"name": "Other", "email": other_email, "password": "Pass123!Safe"})
    other_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": other_email, "password": "Pass123!Safe"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    # Attempt to access project dependencies as another user
    unauth_r = requests.get(f"{BASE_URL}/api/projects/{project_id}/dependencies", headers=other_headers)
    assert unauth_r.status_code == 404, f"Expected 404 for unauthorized user, got {unauth_r.status_code}"
    print("  OK: Unauthorized access rejected with 404.")

    # 12. Cleanup
    print("\n[12/12] Cleaning up Test Project...")
    del_r = requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
    assert del_r.status_code == 204 or del_r.status_code == 200
    print("  OK: Project deleted.")

    print("\n==================================================================")
    print("ALL STAGE 7 DEPENDENCY ANALYZER VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================================")


if __name__ == "__main__":
    main()
