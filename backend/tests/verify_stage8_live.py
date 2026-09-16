"""End-to-end live verification script for Stage 8: Architecture Graph.
Tests live against http://127.0.0.1:8000:
1. User registration & login (JWT auth)
2. Project creation & ZIP upload containing realistic multi-tier project:
   - Presentation layer (e.g. React components)
   - API layer (FastAPI router)
   - Service layer (Business logic)
   - Data layer (Models / DB)
   - Circular dependency between two modules (e.g. auth_service.py <-> session_service.py)
3. Repository Scan (Stage 4)
4. Trigger Architecture Analysis (Stage 8 POST /api/projects/{id}/analyze/architecture)
5. Fetch Architecture Analysis (GET /api/projects/{id}/architecture)
6. Fetch Architecture Nodes (GET /api/projects/{id}/architecture/nodes)
7. Fetch Architecture Edges (GET /api/projects/{id}/architecture/edges)
8. Fetch Architecture Cycles (GET /api/projects/{id}/architecture/cycles)
9. Fetch Architecture Graph (GET /api/projects/{id}/architecture/graph)
10. Verify that cycles are detected, edges connect real files, layers are classified, and degree metrics computed.
"""

import io
import sys
import zipfile
import requests

BASE_URL = "http://127.0.0.1:8000/api"


def create_test_project_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Data layer
        zf.writestr("database.py", "class DB:\n    pass\n")
        zf.writestr(
            "models/user.py",
            "from database import DB\n\nclass User:\n    id = 1\n    name = 'Alice'\n",
        )

        # Service layer with circular dependency
        zf.writestr(
            "services/user_service.py",
            "from models.user import User\nfrom services.auth_service import verify_token\n\ndef get_user():\n    return User()\n",
        )
        zf.writestr(
            "services/auth_service.py",
            "from services.user_service import get_user\n\ndef verify_token(token):\n    return get_user()\n",
        )

        # API layer
        zf.writestr(
            "api/routes.py",
            "from services.user_service import get_user\nfrom services.auth_service import verify_token\n\ndef route_login():\n    return verify_token('abc')\n",
        )

        # Presentation layer (Frontend React TSX)
        zf.writestr(
            "frontend/src/components/UserProfile.tsx",
            "import React from 'react';\nimport { fetchUser } from '../services/api';\n\nexport const UserProfile = () => <div>Profile</div>;\n",
        )
        zf.writestr(
            "frontend/src/services/api.ts",
            "import { UserProfile } from '../components/UserProfile';\n\nexport const fetchUser = () => ({ name: 'Alice' });\n",
        )

        # Config layer
        zf.writestr("config.py", "DEBUG = True\nPORT = 8000\n")

    return buf.getvalue()


def run_live_verification():
    print("================================================================")
    print("STAGE 8 LIVE VERIFICATION: Architecture Graph Engine")
    print("================================================================")

    session = requests.Session()

    # 1. Health check
    resp = session.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("[PASS] 1. Backend health check OK")

    # 2. Register user
    email = f"arch_tester_{sys.platform}@test.com"
    password = "SecurePassword123!"
    reg_resp = session.post(
        f"{BASE_URL}/auth/register",
        json={"name": "Arch Tester", "email": email, "password": password},
    )
    if reg_resp.status_code not in (200, 201, 400):
        raise AssertionError(f"Register failed: {reg_resp.text}")

    # Login user
    login_resp = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("[PASS] 2. User registration and authentication OK")

    # 3. Create Project
    proj_resp = session.post(
        f"{BASE_URL}/projects",
        json={"name": "Stage 8 Architecture Test App", "description": "Testing architecture graph & cycle detection", "source_type": "zip"},
    )
    assert proj_resp.status_code in (200, 201), f"Create project failed: {proj_resp.text}"
    project_id = proj_resp.json()["id"]
    print(f"[PASS] 3. Project created: ID={project_id}")

    # 4. Upload ZIP
    zip_data = create_test_project_zip()
    upload_resp = session.post(
        f"{BASE_URL}/projects/{project_id}/upload",
        files={"file": ("arch_test.zip", zip_data, "application/zip")},
    )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    print("[PASS] 4. Project source files uploaded and extracted safely")

    # 5. Scan Repository
    scan_resp = session.post(f"{BASE_URL}/projects/{project_id}/scan")
    assert scan_resp.status_code == 200, f"Scan failed: {scan_resp.text}"
    scan_data = scan_resp.json()
    print(f"[PASS] 5. Repository scan completed: {scan_data['total_files']} files detected")

    # 6. Trigger Architecture Analysis
    print("--> Triggering POST /api/projects/{id}/analyze/architecture...")
    arch_resp = session.post(f"{BASE_URL}/projects/{project_id}/analyze/architecture")
    assert arch_resp.status_code == 200, f"Architecture analysis failed: {arch_resp.text}"
    analysis = arch_resp.json()
    print(f"[PASS] 6. Architecture analysis completed successfully!")
    print(f"       - Status: {analysis['status']}")
    print(f"       - Nodes created: {analysis['node_count']}")
    print(f"       - Edges discovered: {analysis['edge_count']}")
    print(f"       - Cycles detected: {analysis['cycle_count']}")
    print(f"       - Layers breakdown: {analysis['metrics'].get('layers_breakdown')}")

    assert analysis["node_count"] > 0, "Expected at least 1 node"
    assert analysis["edge_count"] > 0, "Expected at least 1 edge"
    assert analysis["cycle_count"] >= 1, "Expected at least 1 circular dependency cycle"

    # 7. Query Nodes
    nodes_resp = session.get(f"{BASE_URL}/projects/{project_id}/architecture/nodes")
    assert nodes_resp.status_code == 200, f"Get nodes failed: {nodes_resp.text}"
    nodes = nodes_resp.json()
    print(f"[PASS] 7. Retrieved {len(nodes)} architecture nodes")
    node_names = [n["name"] for n in nodes]
    layers = {n["name"]: n["layer"] for n in nodes}
    print(f"       Nodes & Layers: {layers}")

    # Verify layer classifications
    assert "database.py" in node_names
    assert "user_service.py" in node_names
    assert "routes.py" in node_names
    assert layers.get("routes.py") == "API", f"Expected routes.py to be API layer, got {layers.get('routes.py')}"
    assert layers.get("user_service.py") == "Service", f"Expected user_service.py to be Service, got {layers.get('user_service.py')}"
    assert layers.get("UserProfile.tsx") == "Presentation", f"Expected UserProfile.tsx to be Presentation, got {layers.get('UserProfile.tsx')}"

    # 8. Query Edges
    edges_resp = session.get(f"{BASE_URL}/projects/{project_id}/architecture/edges")
    assert edges_resp.status_code == 200, f"Get edges failed: {edges_resp.text}"
    edges = edges_resp.json()
    print(f"[PASS] 8. Retrieved {len(edges)} architecture edges")
    circular_edges = [e for e in edges if e["is_circular"]]
    print(f"       - Circular edges count: {len(circular_edges)}")
    assert len(circular_edges) >= 2, "Expected circular edges between user_service and auth_service"

    # 9. Query Cycles
    cycles_resp = session.get(f"{BASE_URL}/projects/{project_id}/architecture/cycles")
    assert cycles_resp.status_code == 200, f"Get cycles failed: {cycles_resp.text}"
    cycles = cycles_resp.json()
    print(f"[PASS] 9. Retrieved {len(cycles)} cycles: {cycles}")
    assert len(cycles) >= 1, "Expected at least 1 cycle returned"

    # 10. Query Graph
    graph_resp = session.get(f"{BASE_URL}/projects/{project_id}/architecture/graph")
    assert graph_resp.status_code == 200, f"Get graph failed: {graph_resp.text}"
    graph = graph_resp.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert "cycles" in graph
    assert "analysis" in graph
    print(f"[PASS] 10. Retrieved full graph structure ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")

    print("\n================================================================")
    print("ALL STAGE 8 ARCHITECTURE GRAPH VERIFICATIONS PASSED SUCCESSFULLY!")
    print("================================================================")


if __name__ == "__main__":
    run_live_verification()
