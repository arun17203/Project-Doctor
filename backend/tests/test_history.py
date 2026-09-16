import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan, ProjectFile
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.models.dependency import DependencyAnalysis
from backend.app.models.architecture import ArchitectureAnalysis
from backend.app.models.health import HealthAnalysis
from backend.app.models.snapshot import ProjectAnalysisSnapshot
from backend.app.services.snapshot_service import SnapshotService, calc_metric_delta


@pytest.mark.asyncio
async def test_metric_delta_calculations():
    """Verify numeric differences, units, and improvement/worsening logic."""
    # Higher is better: Health score
    delta_up = calc_metric_delta("Health", from_val=61.0, to_val=82.0, lower_is_better=False)
    assert delta_up.difference == 21.0
    assert delta_up.direction == "IMPROVED"

    delta_down = calc_metric_delta("Health", from_val=80.0, to_val=65.0, lower_is_better=False)
    assert delta_down.difference == -15.0
    assert delta_down.direction == "WORSENED"

    delta_same = calc_metric_delta("Health", from_val=75.0, to_val=75.0, lower_is_better=False)
    assert delta_same.difference == 0.0
    assert delta_same.direction == "UNCHANGED"

    # Lower is better: Technical debt hours
    debt_improved = calc_metric_delta("Tech Debt", from_val=42.0, to_val=17.0, lower_is_better=True, unit="hours")
    assert debt_improved.difference == -25.0
    assert debt_improved.direction == "IMPROVED"

    debt_worsened = calc_metric_delta("Tech Debt", from_val=17.0, to_val=30.0, lower_is_better=True, unit="hours")
    assert debt_worsened.difference == 13.0
    assert debt_worsened.direction == "WORSENED"

    # Lower is better: Critical issues
    issues_improved = calc_metric_delta("Critical Issues", from_val=5.0, to_val=1.0, lower_is_better=True, unit="issues")
    assert issues_improved.difference == -4.0
    assert issues_improved.direction == "IMPROVED"


@pytest.mark.asyncio
async def test_snapshot_creation_sequential_versions_and_immutability(db_session: Session):
    """Test that versions are 1, 2, 3 sequentially, and previous snapshots remain unchanged."""
    # 1. Setup User and Project
    user = User(email="hist_user@example.com", password_hash="hashed_pw", name="Hist User", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        user_id=user.id,
        name="History Test Project",
        source_type="zip",
        status="READY",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # 2. Add Scan 1
    scan1 = ProjectScan(project_id=project.id, total_files=10, total_lines=500, status="COMPLETED")
    db_session.add(scan1)
    db_session.commit()
    db_session.refresh(scan1)

    file1 = ProjectFile(
        scan_id=scan1.id,
        project_id=project.id,
        file_path="main.py",
        file_name="main.py",
        extension=".py",
        language="Python",
        category="source",
        total_lines=100,
    )
    db_session.add(file1)

    # Add Health 1 (Baseline: score 60, debt 40)
    health1 = HealthAnalysis(
        project_id=project.id,
        repository_scan_id=scan1.id,
        overall_score=60.0,
        quality_score=65.0,
        security_score=50.0,
        dependency_score=70.0,
        architecture_score=75.0,
        technical_debt_hours=40.0,
        critical_count=4,
        high_count=6,
        medium_count=8,
        low_count=10,
    )
    db_session.add(health1)
    db_session.commit()

    # Create Snapshot #1
    snap1 = SnapshotService.create_snapshot(project, db_session, summary="Initial baseline analysis")
    assert snap1.version_number == 1
    assert snap1.overall_score == 60.0
    assert snap1.technical_debt_hours == 40.0
    assert snap1.critical_count == 4
    snap1_id = snap1.id

    # Add Health 2 (Improved: score 80, debt 15, critical 1)
    health2 = HealthAnalysis(
        project_id=project.id,
        repository_scan_id=scan1.id,
        overall_score=80.0,
        quality_score=85.0,
        security_score=82.0,
        dependency_score=85.0,
        architecture_score=90.0,
        technical_debt_hours=15.0,
        critical_count=1,
        high_count=2,
        medium_count=3,
        low_count=4,
    )
    db_session.add(health2)
    db_session.commit()

    # Create Snapshot #2
    snap2 = SnapshotService.create_snapshot(project, db_session, summary="Refactored security and debt")
    assert snap2.version_number == 2
    assert snap2.overall_score == 80.0
    assert snap2.technical_debt_hours == 15.0
    assert snap2.critical_count == 1

    # Verify Snapshot #1 remains completely unmodified (immutability)
    db_session.expire_all()
    verified_snap1 = db_session.query(ProjectAnalysisSnapshot).filter(ProjectAnalysisSnapshot.id == snap1_id).first()
    assert verified_snap1.version_number == 1
    assert verified_snap1.overall_score == 60.0
    assert verified_snap1.technical_debt_hours == 40.0
    assert verified_snap1.critical_count == 4


@pytest.mark.asyncio
async def test_comparison_between_versions(db_session: Session):
    """Test comparing version 1 and version 2 returns accurate deltas and deterministic text summary."""
    user = User(email="compare_user@example.com", password_hash="pw", name="Comp User", is_active=True)
    db_session.add(user)
    db_session.commit()

    project = Project(user_id=user.id, name="Comparison Project", source_type="zip", status="READY")
    db_session.add(project)
    db_session.commit()

    snap1 = ProjectAnalysisSnapshot(
        project_id=project.id,
        version_number=1,
        status="COMPLETED",
        total_files=5,
        total_lines=200,
        overall_score=61.0,
        security_score=48.0,
        quality_score=72.0,
        dependency_score=65.0,
        architecture_score=70.0,
        maintainability_score=68.0,
        testing_score=0.0,
        technical_debt_hours=42.0,
        critical_count=5,
        high_count=8,
        medium_count=10,
        low_count=6,
        vulnerable_dependencies_count=3,
        architecture_cycles_count=2,
        file_manifest=[{"path": "old.py", "lines": 50}, {"path": "main.py", "lines": 100}],
    )
    snap2 = ProjectAnalysisSnapshot(
        project_id=project.id,
        version_number=2,
        status="COMPLETED",
        total_files=6,
        total_lines=250,
        overall_score=82.0,
        security_score=79.0,
        quality_score=81.0,
        dependency_score=85.0,
        architecture_score=90.0,
        maintainability_score=84.0,
        testing_score=50.0,
        technical_debt_hours=17.0,
        critical_count=1,
        high_count=3,
        medium_count=5,
        low_count=4,
        vulnerable_dependencies_count=0,
        architecture_cycles_count=0,
        file_manifest=[{"path": "new.py", "lines": 60}, {"path": "main.py", "lines": 120}],
    )
    db_session.add_all([snap1, snap2])
    db_session.commit()

    comparison = SnapshotService.compare_snapshots(snap1, snap2)

    # Assert Scores
    assert comparison.health_delta.difference == 21.0
    assert comparison.health_delta.direction == "IMPROVED"

    assert comparison.security_delta.difference == 31.0
    assert comparison.security_delta.direction == "IMPROVED"

    assert comparison.quality_delta.difference == 9.0
    assert comparison.quality_delta.direction == "IMPROVED"

    # Assert Technical Debt
    assert comparison.technical_debt_delta.difference == -25.0
    assert comparison.technical_debt_delta.direction == "IMPROVED"

    # Assert Issues
    assert comparison.critical_issues_delta.difference == -4.0
    assert comparison.critical_issues_delta.direction == "IMPROVED"

    assert comparison.vulnerable_deps_delta.difference == -3.0
    assert comparison.vulnerable_deps_delta.direction == "IMPROVED"

    assert comparison.cycles_delta.difference == -2.0
    assert comparison.cycles_delta.direction == "IMPROVED"

    # Assert Files
    assert comparison.file_diff.files_added == 1
    assert "new.py" in comparison.file_diff.sample_added
    assert comparison.file_diff.files_removed == 1
    assert "old.py" in comparison.file_diff.sample_removed
    assert comparison.file_diff.files_modified == 1  # main.py changed from 100 to 120 lines

    # Assert Deterministic Headline & Text
    assert "PROJECT IMPROVED" in comparison.summary_headline
    assert "Overall project health improved by 21 points" in comparison.summary_text
    assert "Security score improved by 31 points" in comparison.summary_text
    assert "Critical issues decreased from 5 to 1" in comparison.summary_text
    assert "Estimated technical debt remediation effort decreased by 25.0 hours" in comparison.summary_text


@pytest.mark.asyncio
async def test_history_api_endpoints_and_access_control(db_session: Session):
    """Test full HTTP API endpoints: history listing, pagination, version details, and 401/404 handling."""
    from backend.app.core.security import create_access_token

    # Create Owner User
    owner = User(email="owner@example.com", password_hash="pw", name="Owner", is_active=True)
    db_session.add(owner)
    db_session.commit()
    owner_token = create_access_token(data={"sub": owner.id})
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Create Other User
    other = User(email="other@example.com", password_hash="pw", name="Other", is_active=True)
    db_session.add(other)
    db_session.commit()
    other_token = create_access_token(data={"sub": other.id})
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Create Project
    project = Project(user_id=owner.id, name="Secure History Project", source_type="zip", status="READY")
    db_session.add(project)
    db_session.commit()

    # Add 3 historical snapshots
    for v in range(1, 4):
        snap = ProjectAnalysisSnapshot(
            project_id=project.id,
            version_number=v,
            status="COMPLETED",
            overall_score=60.0 + v * 10,
            technical_debt_hours=50.0 - v * 10,
            critical_count=5 - v,
            total_files=10,
            total_lines=500,
        )
        db_session.add(snap)
    db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res = await client.get(f"/api/projects/{project.id}/history")
        assert res.status_code == 401

        # 2. Non-owner request -> 404
        res = await client.get(f"/api/projects/{project.id}/history", headers=other_headers)
        assert res.status_code == 404

        # 3. Owner request -> 200 with 3 items ordered newest first
        res = await client.get(f"/api/projects/{project.id}/history", headers=owner_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["items"][0]["version_number"] == 3
        assert data["items"][1]["version_number"] == 2
        assert data["items"][2]["version_number"] == 1

        # 4. Pagination test (page=1, page_size=2)
        res_page = await client.get(f"/api/projects/{project.id}/history?page=1&page_size=2", headers=owner_headers)
        assert res_page.status_code == 200
        data_page = res_page.json()
        assert len(data_page["items"]) == 2
        assert data_page["total_pages"] == 2

        # 5. Specific version details
        res_v2 = await client.get(f"/api/projects/{project.id}/history/2", headers=owner_headers)
        assert res_v2.status_code == 200
        snap_v2 = res_v2.json()
        assert snap_v2["version_number"] == 2
        assert snap_v2["overall_score"] == 80.0
        assert snap_v2["critical_count"] == 3

        # 6. Invalid version -> 404
        res_inv = await client.get(f"/api/projects/{project.id}/history/999", headers=owner_headers)
        assert res_inv.status_code == 404

        # 7. Comparison endpoint
        res_comp = await client.get(f"/api/projects/{project.id}/history/compare?from=1&to=3", headers=owner_headers)
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        assert comp_data["from_version"] == 1
        assert comp_data["to_version"] == 3
        assert comp_data["health_delta"]["difference"] == 20.0
        assert comp_data["technical_debt_delta"]["difference"] == -20.0
        assert comp_data["critical_issues_delta"]["difference"] == -2.0


@pytest.mark.asyncio
async def test_snapshot_prerequisite_validation_and_failure_handling(db_session: Session):
    """Test that projects without completed scans cannot create snapshots."""
    from fastapi import HTTPException

    user = User(email="fail_user@example.com", password_hash="pw", name="Fail User", is_active=True)
    db_session.add(user)
    db_session.commit()

    # Project without scan
    project = Project(user_id=user.id, name="Unscanned Project", source_type="zip", status="READY")
    db_session.add(project)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        SnapshotService.create_snapshot(project, db_session)
    assert exc.value.status_code == 400
    assert "Repository scan" in exc.value.detail


@pytest.mark.asyncio
async def test_multiple_users_separate_project_isolation(db_session: Session):
    """Verify that User A cannot see User B's historical analysis snapshots or comparisons."""
    from backend.app.core.security import create_access_token

    user_a = User(email="user_a@example.com", password_hash="pw", name="User A", is_active=True)
    user_b = User(email="user_b@example.com", password_hash="pw", name="User B", is_active=True)
    db_session.add_all([user_a, user_b])
    db_session.commit()

    proj_a = Project(user_id=user_a.id, name="Project A", source_type="zip", status="READY")
    proj_b = Project(user_id=user_b.id, name="Project B", source_type="zip", status="READY")
    db_session.add_all([proj_a, proj_b])
    db_session.commit()

    snap_b = ProjectAnalysisSnapshot(
        project_id=proj_b.id,
        version_number=1,
        status="COMPLETED",
        overall_score=95.0,
        technical_debt_hours=2.0,
        critical_count=0,
        total_files=5,
        total_lines=150,
    )
    db_session.add(snap_b)
    db_session.commit()

    token_a = create_access_token(data={"sub": user_a.id})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A attempts to view User B's project history -> 404
        res = await client.get(f"/api/projects/{proj_b.id}/history", headers=headers_a)
        assert res.status_code == 404

        # User A attempts to compare User B's versions -> 404
        res_comp = await client.get(f"/api/projects/{proj_b.id}/history/compare?from=1&to=1", headers=headers_a)
        assert res_comp.status_code == 404

        # User A attempts to get User B's snapshot details -> 404
        res_det = await client.get(f"/api/projects/{proj_b.id}/history/1", headers=headers_a)
        assert res_det.status_code == 404

