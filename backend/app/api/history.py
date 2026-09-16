import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.schemas.history import (
    SnapshotSummaryResponse,
    SnapshotDetailResponse,
    HistoryListResponse,
    VersionComparisonResponse,
    CreateSnapshotRequest,
)
from backend.app.services.snapshot_service import SnapshotService

history_router = APIRouter(prefix="/projects", tags=["Analysis History & Trends"])


def get_user_project(project_id: str, current_user: User, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized",
        )
    return project


@history_router.get("/{project_id}/history", response_model=HistoryListResponse)
def get_project_history(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve paginated historical analysis snapshots for a project, ordered newest first."""
    project = get_user_project(project_id, current_user, db)

    snapshots, total = SnapshotService.get_history(project.id, db, page=page, page_size=page_size)

    items = []
    for s in snapshots:
        tot_issues = s.critical_count + s.high_count + s.medium_count + s.low_count
        items.append(
            SnapshotSummaryResponse(
                id=s.id,
                project_id=s.project_id,
                version_number=s.version_number,
                status=s.status,
                overall_score=s.overall_score,
                quality_score=s.quality_score,
                security_score=s.security_score,
                dependency_score=s.dependency_score,
                architecture_score=s.architecture_score,
                maintainability_score=s.maintainability_score,
                testing_score=s.testing_score,
                technical_debt_hours=s.technical_debt_hours,
                critical_count=s.critical_count,
                high_count=s.high_count,
                medium_count=s.medium_count,
                low_count=s.low_count,
                total_issues=tot_issues,
                total_files=s.total_files,
                total_lines=s.total_lines,
                created_at=s.created_at,
                summary=s.summary,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return HistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@history_router.get("/{project_id}/history/compare", response_model=VersionComparisonResponse)
def compare_analysis_versions(
    project_id: str,
    from_version: int = Query(..., alias="from", ge=1),
    to_version: int = Query(..., alias="to", ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Compare two historical analysis snapshots and calculate score, issue, debt, and file deltas."""
    project = get_user_project(project_id, current_user, db)

    from_snap = SnapshotService.get_snapshot_by_version(project.id, from_version, db)
    if not from_snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis version #{from_version} not found for this project.",
        )

    to_snap = SnapshotService.get_snapshot_by_version(project.id, to_version, db)
    if not to_snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis version #{to_version} not found for this project.",
        )

    return SnapshotService.compare_snapshots(from_snap, to_snap)


@history_router.get("/{project_id}/history/{version}", response_model=SnapshotDetailResponse)
def get_version_details(
    project_id: str,
    version: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed telemetry and audit references for a specific historical snapshot version."""
    project = get_user_project(project_id, current_user, db)

    snap = SnapshotService.get_snapshot_by_version(project.id, version, db)
    if not snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis version #{version} not found for this project.",
        )

    tot_issues = snap.critical_count + snap.high_count + snap.medium_count + snap.low_count

    return SnapshotDetailResponse(
        id=snap.id,
        project_id=snap.project_id,
        version_number=snap.version_number,
        status=snap.status,
        overall_score=snap.overall_score,
        quality_score=snap.quality_score,
        security_score=snap.security_score,
        dependency_score=snap.dependency_score,
        architecture_score=snap.architecture_score,
        maintainability_score=snap.maintainability_score,
        testing_score=snap.testing_score,
        technical_debt_hours=snap.technical_debt_hours,
        critical_count=snap.critical_count,
        high_count=snap.high_count,
        medium_count=snap.medium_count,
        low_count=snap.low_count,
        total_issues=tot_issues,
        total_files=snap.total_files,
        total_lines=snap.total_lines,
        created_at=snap.created_at,
        summary=snap.summary,
        repository_scan_id=snap.repository_scan_id,
        quality_analysis_id=snap.quality_analysis_id,
        security_analysis_id=snap.security_analysis_id,
        dependency_analysis_id=snap.dependency_analysis_id,
        architecture_analysis_id=snap.architecture_analysis_id,
        health_analysis_id=snap.health_analysis_id,
        critical_security_count=snap.critical_security_count,
        high_security_count=snap.high_security_count,
        high_complexity_count=snap.high_complexity_count,
        long_functions_count=snap.long_functions_count,
        duplicate_blocks_count=snap.duplicate_blocks_count,
        total_dependencies=snap.total_dependencies,
        vulnerable_dependencies_count=snap.vulnerable_dependencies_count,
        outdated_dependencies_count=snap.outdated_dependencies_count,
        architecture_nodes_count=snap.architecture_nodes_count,
        architecture_edges_count=snap.architecture_edges_count,
        architecture_cycles_count=snap.architecture_cycles_count,
        file_manifest=snap.file_manifest or [],
    )


@history_router.post("/{project_id}/analysis/run", response_model=SnapshotDetailResponse)
def trigger_analysis_run(
    project_id: str,
    payload: Optional[CreateSnapshotRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run complete multi-stage analysis pipeline and record a new sequential historical snapshot."""
    project = get_user_project(project_id, current_user, db)

    summary = payload.summary if payload else None
    snapshot = SnapshotService.run_full_analysis(project, db, summary=summary)

    tot_issues = snapshot.critical_count + snapshot.high_count + snapshot.medium_count + snapshot.low_count

    return SnapshotDetailResponse(
        id=snapshot.id,
        project_id=snapshot.project_id,
        version_number=snapshot.version_number,
        status=snapshot.status,
        overall_score=snapshot.overall_score,
        quality_score=snapshot.quality_score,
        security_score=snapshot.security_score,
        dependency_score=snapshot.dependency_score,
        architecture_score=snapshot.architecture_score,
        maintainability_score=snapshot.maintainability_score,
        testing_score=snapshot.testing_score,
        technical_debt_hours=snapshot.technical_debt_hours,
        critical_count=snapshot.critical_count,
        high_count=snapshot.high_count,
        medium_count=snapshot.medium_count,
        low_count=snapshot.low_count,
        total_issues=tot_issues,
        total_files=snapshot.total_files,
        total_lines=snapshot.total_lines,
        created_at=snapshot.created_at,
        summary=snapshot.summary,
        repository_scan_id=snapshot.repository_scan_id,
        quality_analysis_id=snapshot.quality_analysis_id,
        security_analysis_id=snapshot.security_analysis_id,
        dependency_analysis_id=snapshot.dependency_analysis_id,
        architecture_analysis_id=snapshot.architecture_analysis_id,
        health_analysis_id=snapshot.health_analysis_id,
        critical_security_count=snapshot.critical_security_count,
        high_security_count=snapshot.high_security_count,
        high_complexity_count=snapshot.high_complexity_count,
        long_functions_count=snapshot.long_functions_count,
        duplicate_blocks_count=snapshot.duplicate_blocks_count,
        total_dependencies=snapshot.total_dependencies,
        vulnerable_dependencies_count=snapshot.vulnerable_dependencies_count,
        outdated_dependencies_count=snapshot.outdated_dependencies_count,
        architecture_nodes_count=snapshot.architecture_nodes_count,
        architecture_edges_count=snapshot.architecture_edges_count,
        architecture_cycles_count=snapshot.architecture_cycles_count,
        file_manifest=snapshot.file_manifest or [],
    )


@history_router.post("/{project_id}/snapshots", response_model=SnapshotDetailResponse)
def create_project_snapshot(
    project_id: str,
    payload: Optional[CreateSnapshotRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new version snapshot from current completed analysis results."""
    project = get_user_project(project_id, current_user, db)

    summary = payload.summary if payload else None
    snapshot = SnapshotService.create_snapshot(project, db, summary=summary)

    tot_issues = snapshot.critical_count + snapshot.high_count + snapshot.medium_count + snapshot.low_count

    return SnapshotDetailResponse(
        id=snapshot.id,
        project_id=snapshot.project_id,
        version_number=snapshot.version_number,
        status=snapshot.status,
        overall_score=snapshot.overall_score,
        quality_score=snapshot.quality_score,
        security_score=snapshot.security_score,
        dependency_score=snapshot.dependency_score,
        architecture_score=snapshot.architecture_score,
        maintainability_score=snapshot.maintainability_score,
        testing_score=snapshot.testing_score,
        technical_debt_hours=snapshot.technical_debt_hours,
        critical_count=snapshot.critical_count,
        high_count=snapshot.high_count,
        medium_count=snapshot.medium_count,
        low_count=snapshot.low_count,
        total_issues=tot_issues,
        total_files=snapshot.total_files,
        total_lines=snapshot.total_lines,
        created_at=snapshot.created_at,
        summary=snapshot.summary,
        repository_scan_id=snapshot.repository_scan_id,
        quality_analysis_id=snapshot.quality_analysis_id,
        security_analysis_id=snapshot.security_analysis_id,
        dependency_analysis_id=snapshot.dependency_analysis_id,
        architecture_analysis_id=snapshot.architecture_analysis_id,
        health_analysis_id=snapshot.health_analysis_id,
        critical_security_count=snapshot.critical_security_count,
        high_security_count=snapshot.high_security_count,
        high_complexity_count=snapshot.high_complexity_count,
        long_functions_count=snapshot.long_functions_count,
        duplicate_blocks_count=snapshot.duplicate_blocks_count,
        total_dependencies=snapshot.total_dependencies,
        vulnerable_dependencies_count=snapshot.vulnerable_dependencies_count,
        outdated_dependencies_count=snapshot.outdated_dependencies_count,
        architecture_nodes_count=snapshot.architecture_nodes_count,
        architecture_edges_count=snapshot.architecture_edges_count,
        architecture_cycles_count=snapshot.architecture_cycles_count,
        file_manifest=snapshot.file_manifest or [],
    )
