import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


async def get_auth_token(client: AsyncClient, email: str, name: str) -> str:
    """Helper to register and login a test user."""
    await client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "QualityPass123!"
    })
    res = await client.post("/api/auth/login", json={
        "email": email,
        "password": "QualityPass123!"
    })
    return res.json()["access_token"]


def create_quality_test_zip() -> bytes:
    """Creates a zip archive with intentional code quality issues:
    1. complex_module.py:
       - 1 function with complexity 17 (16+ = CRITICAL high_complexity)
       - 1 function with deep nesting (depth 4 = MEDIUM deep_nesting)
       - 1 unused import (`import unused_math_module`)
       - 1 TODO comment (`# TODO: optimize this algorithm`)
    2. long_module.py:
       - 1 function with 65 lines (>50 = MEDIUM long_function)
       - 1 FIXME comment (`# FIXME: handle edge case properly`)
    3. duplicate_a.py & duplicate_b.py:
       - 14 lines of identical normalized logic to test duplicate_code detection.
    4. broken_syntax.py:
       - Intentional invalid syntax (`def broken( `) to verify graceful recovery.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. complex_module.py
        complex_code = (
            "import os\n"
            "import unused_math_module\n"
            "\n"
            "# TODO: optimize this algorithm\n"
            "def highly_complex_function(a, b, c, d, e, f, g, h):\n"
            "    res = 0\n"
            "    if a > 0 and b > 0 and c > 0:\n"
            "        res += 1\n"
            "    elif a < 0 or b < 0 or c < 0:\n"
            "        res -= 1\n"
            "    if c:\n"
            "        for i in range(10):\n"
            "            if d:\n"
            "                res += i\n"
            "            elif e:\n"
            "                res -= i\n"
            "    while f > 0:\n"
            "        f -= 1\n"
            "        if g:\n"
            "            res += 2\n"
            "    try:\n"
            "        if h:\n"
            "            assert res != 0\n"
            "    except Exception:\n"
            "        pass\n"
            "    return res if a == 1 else (1 if b == 2 else 0)\n"
            "\n"
            "def deeply_nested_function(x):\n"
            "    if x > 0:\n"
            "        for i in range(5):\n"
            "            if i % 2 == 0:\n"
            "                while x > 10:\n"
            "                    x -= 1\n"
            "    return x\n"
            "\n"
            "highly_complex_function(1, 2, True, True, False, 5, True, False)\n"
            "deeply_nested_function(20)\n"
        )
        zf.writestr("src/complex_module.py", complex_code)

        # 2. long_module.py (65 lines function)
        long_func_lines = ["# FIXME: handle edge case properly", "def very_long_function():", "    val = 0"]
        for k in range(60):
            long_func_lines.append(f"    val += {k}  # statement {k}")
        long_func_lines.append("    return val")
        long_func_lines.append("")
        long_func_lines.append("very_long_function()")
        zf.writestr("src/long_module.py", "\n".join(long_func_lines))

        # 3. duplicate_a.py & duplicate_b.py (14 duplicate lines)
        shared_block = (
            "def calculate_tax_metrics(gross_income, tax_bracket, deductions):\n"
            "    adjusted_income = gross_income - deductions\n"
            "    if adjusted_income <= 0:\n"
            "        return 0.0\n"
            "    base_rate = tax_bracket * 0.01\n"
            "    surcharge = 0.05 if adjusted_income > 100000 else 0.0\n"
            "    preliminary_tax = adjusted_income * (base_rate + surcharge)\n"
            "    final_liability = round(preliminary_tax, 2)\n"
            "    rebate = min(final_liability, 500.0)\n"
            "    net_payable = final_liability - rebate\n"
            "    print(f'Net tax payable: {net_payable}')\n"
            "    return net_payable\n"
        )
        code_a = f"# Module A billing\n{shared_block}\nprint('Module A ready')\n"
        code_b = f"# Module B invoices\n{shared_block}\nprint('Module B ready')\n"
        zf.writestr("src/billing/duplicate_a.py", code_a)
        zf.writestr("src/invoices/duplicate_b.py", code_b)

        # 4. broken_syntax.py
        zf.writestr("src/broken_syntax.py", "def broken_code_syntax(\n  this is invalid syntax !!!\n")

        # 5. dummy package.json
        zf.writestr("package.json", '{"name": "quality-fixture"}\n')

    return buf.getvalue()


@pytest.mark.asyncio
async def test_quality_analysis_full_flow():
    """Verify complete flow:
    Register -> Project -> ZIP Upload -> Scan (Stage 4) -> Quality Analysis (Stage 5)
    -> Verify detected issues:
       - high_complexity (CRITICAL)
       - long_function (MEDIUM)
       - deep_nesting (MEDIUM)
       - unused_import (LOW)
       - todo_comment (LOW & MEDIUM)
       - duplicate_code (MEDIUM)
       - syntax error handled gracefully
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "quality_lead@doctor.io", "Quality Lead")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create project
        create_res = await client.post("/api/projects", json={
            "name": "Quality Audit Project",
            "description": "Project with intentional code quality issues",
            "source_type": "zip"
        }, headers=headers)
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Attempt Quality Analysis before scan (must fail with 400)
        premature_res = await client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
        assert premature_res.status_code == 400
        assert "not ready" in premature_res.json()["detail"].lower()

        # 3. Upload ZIP
        zip_bytes = create_quality_test_zip()
        upload_res = await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("quality.zip", zip_bytes, "application/zip")},
            headers=headers
        )
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "READY"

        # 4. Attempt Quality Analysis before Stage 4 Scan (must fail with 400)
        pre_scan_res = await client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
        assert pre_scan_res.status_code == 400
        assert "repository scan is required" in pre_scan_res.json()["detail"].lower()

        # 5. Run Stage 4 Scan
        scan_res = await client.post(f"/api/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200
        assert scan_res.json()["status"] == "COMPLETED"

        # 6. Run Stage 5 Quality Analysis
        qa_res = await client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
        assert qa_res.status_code == 200
        qa_data = qa_res.json()

        assert qa_data["status"] == "COMPLETED"
        assert qa_data["total_issues"] > 0
        assert qa_data["critical_count"] >= 1  # From high_complexity >= 16
        assert qa_data["medium_count"] >= 1   # From deep_nesting, long_function, duplicate_code
        assert qa_data["low_count"] >= 1      # From unused_import, TODO

        # Verify maintainability metrics
        metrics = qa_data["metrics"]
        assert metrics["total_functions"] >= 4
        assert metrics["max_complexity"] >= 16
        assert metrics["max_function_length"] >= 50
        assert metrics["unparseable_files"] == 1  # broken_syntax.py

        # 7. Query Latest Quality Analysis
        latest_res = await client.get(f"/api/projects/{project_id}/quality", headers=headers)
        assert latest_res.status_code == 200
        assert latest_res.json()["id"] == qa_data["id"]

        # 8. Query Issues List
        issues_res = await client.get(f"/api/projects/{project_id}/quality/issues", headers=headers)
        assert issues_res.status_code == 200
        issues = issues_res.json()
        assert len(issues) == qa_data["total_issues"]

        issue_types = {iss["issue_type"] for iss in issues}
        assert "high_complexity" in issue_types
        assert "long_function" in issue_types
        assert "deep_nesting" in issue_types
        assert "unused_import" in issue_types
        assert "todo_comment" in issue_types
        assert "duplicate_code" in issue_types

        # Verify specific critical complexity issue
        critical_complex = next(i for i in issues if i["issue_type"] == "high_complexity" and i["severity"] == "CRITICAL")
        assert "highly_complex_function" in critical_complex["symbol_name"]
        assert "Complexity: " in critical_complex["evidence"]

        # Verify duplicate code issue
        dup_issue = next(i for i in issues if i["issue_type"] == "duplicate_code")
        assert "duplicate" in dup_issue["file_path"]
        assert "Matches " in dup_issue["evidence"]

        # 9. Test Severity Filter (CRITICAL only)
        crit_res = await client.get(f"/api/projects/{project_id}/quality/issues?severity=CRITICAL", headers=headers)
        assert crit_res.status_code == 200
        for i in crit_res.json():
            assert i["severity"] == "CRITICAL"

        # 10. Test Read-Only Code Snippet Endpoint
        snippet_res = await client.get(
            f"/api/projects/{project_id}/quality/snippet?file_path={critical_complex['file_path']}&line_number={critical_complex['line_number']}&window=3",
            headers=headers
        )
        assert snippet_res.status_code == 200
        snippet_data = snippet_res.json()
        assert snippet_data["target_line"] == critical_complex["line_number"]
        assert len(snippet_data["lines"]) > 0
        highlighted = [l for l in snippet_data["lines"] if l["is_highlighted"]]
        assert len(highlighted) == 1
        assert "def highly_complex_function" in highlighted[0]["content"]

        # 11. Unauthorized access test: User B cannot access User A's quality data
        token_b = await get_auth_token(client, "user_b@doctor.io", "User B")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        unauth_get = await client.get(f"/api/projects/{project_id}/quality", headers=headers_b)
        assert unauth_get.status_code == 404

        unauth_issues = await client.get(f"/api/projects/{project_id}/quality/issues", headers=headers_b)
        assert unauth_issues.status_code == 404

        unauth_snippet = await client.get(
            f"/api/projects/{project_id}/quality/snippet?file_path=src/complex_module.py&line_number=5",
            headers=headers_b
        )
        assert unauth_snippet.status_code == 404


@pytest.mark.asyncio
async def test_javascript_quality_analysis():
    """Verify that JavaScript/TypeScript files are analyzed for complexity, function length, and nesting."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_auth_token(client, "js_lead@doctor.io", "JS Lead")
        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        create_res = await client.post("/api/projects", json={
            "name": "JS Quality Project",
            "source_type": "zip"
        }, headers=headers)
        project_id = create_res.json()["id"]

        # Create zip with JS fixture
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            js_code = (
                "// Complex and nested JS function\n"
                "// TODO: refactor to modular actions\n"
                "function processOrder(order, user, discount) {\n"
                "    let total = 0;\n"
                "    if (order && user) {\n"
                "        for (let i = 0; i < order.items.length; i++) {\n"
                "            if (order.items[i].price > 0) {\n"
                "                while (discount > 0) {\n"
                "                    total += order.items[i].price * 0.9;\n"
                "                    discount--;\n"
                "                }\n"
                "            }\n"
                "        }\n"
                "    } else if (order || user) {\n"
                "        total = 10;\n"
                "    }\n"
                "    return total;\n"
                "}\n"
            )
            zf.writestr("src/orders.js", js_code)
            zf.writestr("package.json", '{"name": "orders-app"}\n')

        await client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("js_proj.zip", buf.getvalue(), "application/zip")},
            headers=headers
        )
        await client.post(f"/api/projects/{project_id}/scan", headers=headers)

        # Run quality analysis
        qa_res = await client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
        assert qa_res.status_code == 200
        qa_data = qa_res.json()
        assert qa_data["total_issues"] >= 2  # deep_nesting + todo_comment

        issues_res = await client.get(f"/api/projects/{project_id}/quality/issues", headers=headers)
        issues = issues_res.json()
        types = [i["issue_type"] for i in issues]
        assert "deep_nesting" in types
        assert "todo_comment" in types
