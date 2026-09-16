import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.analyzers.architecture.parser import (
    parse_python_imports,
    parse_js_ts_imports,
)
from backend.app.analyzers.architecture.resolver import ImportResolver, RawImport
from backend.app.analyzers.architecture.classifier import (
    classify_layer,
    LAYER_PRESENTATION,
    LAYER_API,
    LAYER_SERVICE,
    LAYER_DATA,
    LAYER_UTILITY,
    LAYER_CONFIGURATION,
    LAYER_TEST,
    LAYER_UNKNOWN,
)
from backend.app.analyzers.architecture.cycles import detect_cycles, canonicalize_cycle
from backend.app.analyzers.architecture.engine import ArchitectureEngine


async def get_auth_token(client: AsyncClient, email: str, name: str) -> str:
    """Helper to register and login a test user."""
    await client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "ArchPass123!Secure"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "ArchPass123!Secure"
    })
    return res.json()["access_token"]


def create_architecture_test_zip() -> bytes:
    """Creates a zip archive containing interrelated Python and TypeScript files
    with an intentional circular dependency:
      - routes/auth_controller.py -> services/auth_service.py
      - services/auth_service.py -> services/user_service.py
      - services/user_service.py -> services/auth_service.py (CYCLE!)
      - services/user_service.py -> models/user_model.py
      - models/user_model.py -> database/db.py
      - utils/hasher.py (Utility)
      - frontend/pages/Login.tsx -> frontend/services/api.ts
      - frontend/services/api.ts -> frontend/utils/storage.ts
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Backend files
        zf.writestr(
            "backend/database/db.py",
            "import os\nclass Database:\n    pass\n"
        )
        zf.writestr(
            "backend/models/user_model.py",
            "from backend.database.db import Database\nclass User:\n    pass\n"
        )
        zf.writestr(
            "backend/services/user_service.py",
            "from backend.models.user_model import User\n"
            "from backend.services.auth_service import AuthService\n"
            "class UserService:\n    pass\n"
        )
        zf.writestr(
            "backend/services/auth_service.py",
            "from backend.services.user_service import UserService\n"
            "class AuthService:\n    pass\n"
        )
        zf.writestr(
            "backend/routes/auth_controller.py",
            "from backend.services.auth_service import AuthService\n"
            "def login():\n    pass\n"
        )
        zf.writestr(
            "backend/utils/hasher.py",
            "import hashlib\ndef hash_pw():\n    pass\n"
        )

        # Frontend files
        zf.writestr(
            "frontend/utils/storage.ts",
            "export const getToken = () => localStorage.getItem('t');\n"
        )
        zf.writestr(
            "frontend/services/api.ts",
            "import { getToken } from '../utils/storage';\n"
            "export const api = {};\n"
        )
        zf.writestr(
            "frontend/pages/Login.tsx",
            "import React from 'react';\n"
            "import { api } from '../services/api';\n"
            "export default function Login() { return null; }\n"
        )

    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Unit Tests for Parsers, Resolver, Classifier & Cycles
# ---------------------------------------------------------------------------

def test_python_import_parser():
    content = """
import os
import sys
import database
from services.user import UserService, get_user
from ..utils.helpers import format_date
from . import db
import invalid syntax !!!
"""
    imports = parse_python_imports(content, "src/main.py")
    modules = [imp.imported_module for imp in imports]

    assert "os" in modules
    assert "sys" in modules
    assert "database" in modules
    assert "services.user" in modules
    assert "utils.helpers" in modules


def test_js_ts_import_parser():
    content = """
import React, { useState } from 'react';
import { Button } from './components/Button';
import axios from 'axios';
const authService = require('../services/authService');
export * from './types';
import('./lazyModule');
// import commented from './commented';
"""
    imports = parse_js_ts_imports(content, "src/App.tsx")
    modules = [imp.imported_module for imp in imports]

    assert "react" in modules
    assert "./components/Button" in modules
    assert "axios" in modules
    assert "../services/authService" in modules
    assert "./types" in modules
    assert "./lazyModule" in modules
    assert "./commented" not in modules


def test_import_resolver():
    all_files = {
        "src/services/auth.py",
        "src/services/user.py",
        "src/database.py",
        "frontend/components/Button.tsx",
        "frontend/pages/Home.tsx",
    }
    resolver = ImportResolver(all_files)

    # Standard libraries discarded
    res_os = resolver.resolve(RawImport("src/services/auth.py", "os"), "Python")
    assert res_os is None

    # Relative Python import
    res_py_rel = resolver.resolve(
        RawImport("src/services/auth.py", "user", is_relative=True, level=1),
        "Python"
    )
    assert res_py_rel == "src/services/user.py"

    # Absolute Python import
    res_py_abs = resolver.resolve(
        RawImport("src/services/auth.py", "src.database"),
        "Python"
    )
    assert res_py_abs == "src/database.py"

    # Relative JS import with extension inference
    res_js = resolver.resolve(
        RawImport("frontend/pages/Home.tsx", "../components/Button", is_relative=True),
        "TypeScript"
    )
    assert res_js == "frontend/components/Button.tsx"


def test_layer_classifier():
    assert classify_layer("frontend/src/components/Header.tsx") == LAYER_PRESENTATION
    assert classify_layer("frontend/src/pages/Dashboard.jsx") == LAYER_PRESENTATION
    assert classify_layer("backend/routes/user.py") == LAYER_API
    assert classify_layer("backend/controllers/auth_controller.js") == LAYER_API
    assert classify_layer("backend/services/payment_service.py") == LAYER_SERVICE
    assert classify_layer("backend/models/user.py") == LAYER_DATA
    assert classify_layer("backend/db/database.py") == LAYER_DATA
    assert classify_layer("backend/utils/hasher.py") == LAYER_UTILITY
    assert classify_layer("backend/config/settings.py") == LAYER_CONFIGURATION
    assert classify_layer("backend/tests/test_auth.py") == LAYER_TEST
    assert classify_layer("backend/misc/unclassified.py") == LAYER_UNKNOWN


def test_cycle_detection():
    # 1. A -> B -> C (Acyclic)
    nodes_acyclic = ["a.py", "b.py", "c.py"]
    edges_acyclic = [("a.py", "b.py"), ("b.py", "c.py")]
    cycles_1 = detect_cycles(nodes_acyclic, edges_acyclic)
    assert len(cycles_1) == 0

    # 2. A -> B -> A (2-node cycle)
    nodes_cyclic = ["a.py", "b.py"]
    edges_cyclic = [("a.py", "b.py"), ("b.py", "a.py")]
    cycles_2 = detect_cycles(nodes_cyclic, edges_cyclic)
    assert len(cycles_2) == 1
    assert cycles_2[0] == ["a.py", "b.py", "a.py"]

    # 3. Canonicalize cycle rotation
    c1 = canonicalize_cycle(["b.py", "c.py", "a.py", "b.py"])
    c2 = canonicalize_cycle(["a.py", "b.py", "c.py", "a.py"])
    assert c1 == c2 == ("a.py", "b.py", "c.py", "a.py")


def test_empty_and_invalid_project():
    engine = ArchitectureEngine()
    assert engine._read_file("non_existent_file.py") is None


# ---------------------------------------------------------------------------
# Integration Tests (Full API Lifecycle & Access Control)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_full_architecture_analysis_flow():
    """Full end-to-end integration test of architecture analysis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "arch_user@example.com", "Arch User")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project
        create_proj_res = await client.post(
            "/api/projects",
            json={"name": "Architecture Demo Project", "description": "Testing Stage 8", "source_type": "zip"},
            headers=headers,
        )
        assert create_proj_res.status_code == 201
        project_id = create_proj_res.json()["id"]

        # 2. Upload test ZIP
        zip_bytes = create_architecture_test_zip()
        upload_res = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("arch_test.zip", zip_bytes, "application/zip")},
            headers=headers,
        )
        assert upload_res.status_code == 200

        # 3. Must fail if architecture analysis triggered before scan
        early_res = await client.post(f"/api/projects/{project_id}/analyze/architecture", headers=headers)
        assert early_res.status_code == 400

        # 4. Run Stage 4 repository scan
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200

        # 5. Trigger Stage 8 Architecture Analysis
        arch_res = await client.post(f"/api/projects/{project_id}/analyze/architecture", headers=headers)
        assert arch_res.status_code == 200, arch_res.text
        arch_data = arch_res.json()

        assert arch_data["status"] == "COMPLETED"
        assert arch_data["node_count"] >= 8
        assert arch_data["edge_count"] >= 5
        # Verify intentional circular dependency was detected between auth_service & user_service
        assert arch_data["cycle_count"] >= 1
        assert "by_layer" in arch_data["metrics"]
        assert "cycles_summary" in arch_data["metrics"]

        # 6. Fetch latest architecture analysis
        get_arch = await client.get(f"/api/projects/{project_id}/architecture", headers=headers)
        assert get_arch.status_code == 200
        assert get_arch.json()["id"] == arch_data["id"]

        # 7. Fetch nodes with filters
        nodes_res = await client.get(f"/api/projects/{project_id}/architecture/nodes", headers=headers)
        assert nodes_res.status_code == 200
        nodes = nodes_res.json()
        assert len(nodes) == arch_data["node_count"]

        # Filter nodes by layer
        pres_nodes_res = await client.get(
            f"/api/projects/{project_id}/architecture/nodes?layer=Presentation",
            headers=headers,
        )
        assert pres_nodes_res.status_code == 200
        pres_nodes = pres_nodes_res.json()
        assert len(pres_nodes) >= 1
        assert any("Login.tsx" in n["name"] for n in pres_nodes)

        # 8. Fetch edges
        edges_res = await client.get(f"/api/projects/{project_id}/architecture/edges", headers=headers)
        assert edges_res.status_code == 200
        edges = edges_res.json()
        assert len(edges) == arch_data["edge_count"]
        # Verify at least one edge has is_circular=True
        assert any(e["is_circular"] is True for e in edges)

        # 9. Fetch cycles endpoint
        cycles_res = await client.get(f"/api/projects/{project_id}/architecture/cycles", headers=headers)
        assert cycles_res.status_code == 200
        cycles = cycles_res.json()
        assert len(cycles) >= 1

        # 10. Fetch complete graph endpoint
        graph_res = await client.get(f"/api/projects/{project_id}/architecture/graph", headers=headers)
        assert graph_res.status_code == 200
        graph = graph_res.json()
        assert "analysis" in graph
        assert "nodes" in graph
        assert "edges" in graph
        assert "cycles" in graph


@pytest.mark.anyio
async def test_architecture_access_control():
    """Non-owners cannot trigger analysis or view architecture graphs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await get_auth_token(client, "owner_arch@example.com", "Owner Arch")
        other_token = await get_auth_token(client, "other_arch@example.com", "Other Arch")

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Owner creates project
        create_res = await client.post(
            "/api/projects",
            json={"name": "Owner Project", "source_type": "zip"},
            headers=owner_headers,
        )
        proj_id = create_res.json()["id"]

        # Other user tries to trigger analysis -> 404
        bad_trigger = await client.post(f"/api/projects/{proj_id}/analyze/architecture", headers=other_headers)
        assert bad_trigger.status_code == 404

        # Other user tries to get architecture -> 404
        bad_get = await client.get(f"/api/projects/{proj_id}/architecture", headers=other_headers)
        assert bad_get.status_code == 404
