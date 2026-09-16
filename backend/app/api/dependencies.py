import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.models.dependency import (
    DependencyAnalysis,
    ProjectDependency,
    DependencyIssue,
)
from backend.app.schemas.dependency import (
    DependencyAnalysisResponse,
    ProjectDependencyResponse,
    DependencyIssueResponse,
    DependencySummaryResponse,
)
from backend.app.analyzers.dependency.engine import run_dependency_analysis
from backend.app.models.base import utc_now

dependencies_router = APIRouter(prefix="/projects", tags=["Dependency Analyzer"])


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


@dependencies_router.post("/{project_id}/analyze/dependencies", response_model=DependencyAnalysisResponse)
def trigger_dependency_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Trigger static dependency health and vulnerability audit on an already-scanned project.
    Zero code execution. Real vulnerability data only.
    """
    project = get_user_project(project_id, current_user, db)

    # 1. Verify project status is READY
    if project.status != "READY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project is not ready for analysis. Current status is '{project.status}'.",
        )

    # 2. Verify completed repository scan exists
    scan = (
        db.query(ProjectScan)
        .filter(ProjectScan.project_id == project.id, ProjectScan.status == "COMPLETED")
        .order_by(ProjectScan.scanned_at.desc())
        .first()
    )
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A completed Stage 4 repository scan is required before running dependency analysis.",
        )

    # 3. Create initial pending analysis record
    analysis = DependencyAnalysis(
        project_id=project.id,
        scan_id=scan.id,
        status="IN_PROGRESS",
        started_at=utc_now(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # 4. Run static dependency audit engine
        results = run_dependency_analysis(project, scan, db)

        # 5. Update analysis record with counts & metrics
        analysis.status = "COMPLETED"
        analysis.completed_at = utc_now()
        analysis.total_dependencies = results["total_dependencies"]
        analysis.direct_dependencies = results["direct_dependencies"]
        analysis.transitive_dependencies = results["transitive_dependencies"]
        analysis.current_count = results["current_count"]
        analysis.outdated_count = results["outdated_count"]
        analysis.vulnerable_count = results["vulnerable_count"]
        analysis.unknown_count = results["unknown_count"]
        analysis.metrics = results.get("metrics", {})

        # 6. Bulk insert dependencies
        dep_models = []
        dep_id_map = {}  # Map (name, manifest_file) to created ProjectDependency
        for d in results["dependencies"]:
            dep_obj = ProjectDependency(
                analysis_id=analysis.id,
                project_id=project.id,
                manifest_file=d["manifest_file"],
                ecosystem=d["ecosystem"],
                name=d["name"],
                declared_version=d.get("declared_version"),
                resolved_version=d.get("resolved_version"),
                dependency_type=d.get("dependency_type", "direct"),
                latest_version=d.get("latest_version"),
                status=d.get("status", "UNKNOWN"),
                vulnerability_count=d.get("vulnerability_count", 0),
                advisories=d.get("advisories", []),
            )
            dep_models.append(dep_obj)

        if dep_models:
            db.add_all(dep_models)
            db.flush()  # Populates IDs
            for dep_obj in dep_models:
                dep_id_map[(dep_obj.name, dep_obj.manifest_file)] = dep_obj.id

        # 7. Bulk insert issues linked to dependencies where applicable
        issue_models = []
        for iss in results["issues"]:
            matched_dep_id = dep_id_map.get((iss["package_name"], iss["manifest_file"]))
            issue_obj = DependencyIssue(
                analysis_id=analysis.id,
                project_id=project.id,
                dependency_id=matched_dep_id,
                category=iss.get("category", "dependency"),
                issue_type=iss["issue_type"],
                severity=iss["severity"],
                package_name=iss["package_name"],
                manifest_file=iss["manifest_file"],
                version=iss["version"],
                vulnerability_id=iss.get("vulnerability_id"),
                description=iss["description"],
                recommendation=iss.get("recommendation"),
            )
            issue_models.append(issue_obj)

        if issue_models:
            db.add_all(issue_models)

        db.commit()
        db.refresh(analysis)
        return analysis

    except Exception as e:
        db.rollback()
        analysis.status = "FAILED"
        analysis.error_message = str(e)
        analysis.completed_at = utc_now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dependency analysis failed: {str(e)}",
        ) from e


@dependencies_router.get("/{project_id}/dependency-analysis", response_model=DependencyAnalysisResponse)
def get_latest_dependency_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the latest dependency analysis record for a project."""
    project = get_user_project(project_id, current_user, db)
    analysis = (
        db.query(DependencyAnalysis)
        .filter(DependencyAnalysis.project_id == project.id)
        .order_by(DependencyAnalysis.started_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No dependency analysis found for this project. Please run dependency audit first.",
        )
    return analysis


@dependencies_router.get("/{project_id}/dependencies/summary", response_model=DependencySummaryResponse)
def get_dependency_summary(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get high-level summary metrics for dependencies of the project."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(DependencyAnalysis)
            .filter(DependencyAnalysis.project_id == project.id)
            .order_by(DependencyAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No dependency analysis found for this project.",
            )
        analysis = latest
    else:
        analysis = (
            db.query(DependencyAnalysis)
            .filter(DependencyAnalysis.id == target_analysis_id, DependencyAnalysis.project_id == project.id)
            .first()
        )
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specified dependency analysis not found.",
            )

    metrics = analysis.metrics or {}
    return DependencySummaryResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        total_dependencies=analysis.total_dependencies,
        direct_dependencies=analysis.direct_dependencies,
        transitive_dependencies=analysis.transitive_dependencies,
        current_count=analysis.current_count,
        outdated_count=analysis.outdated_count,
        vulnerable_count=analysis.vulnerable_count,
        unknown_count=analysis.unknown_count,
        manifests=metrics.get("manifests_scanned", []),
        by_ecosystem=metrics.get("by_ecosystem", {}),
        network_warning=metrics.get("network_warning", False),
        completed_at=analysis.completed_at,
    )


@dependencies_router.get("/{project_id}/dependencies", response_model=List[ProjectDependencyResponse])
def get_project_dependencies(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: CURRENT, OUTDATED, VULNERABLE, UNKNOWN"),
    ecosystem: Optional[str] = Query(None, description="Filter by ecosystem: PyPI, npm, Maven"),
    dependency_type: Optional[str] = Query(None, description="Filter by type: direct, dev, transitive, peer"),
    manifest_file: Optional[str] = Query(None, description="Filter by manifest file"),
    search: Optional[str] = Query(None, description="Search package name (substring match)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List dependencies discovered in the repository with optional filtering."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(DependencyAnalysis)
            .filter(DependencyAnalysis.project_id == project.id)
            .order_by(DependencyAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        target_analysis_id = latest.id

    query = db.query(ProjectDependency).filter(
        ProjectDependency.analysis_id == target_analysis_id,
        ProjectDependency.project_id == project.id,
    )

    if status_filter:
        query = query.filter(ProjectDependency.status == status_filter.upper())
    if ecosystem:
        query = query.filter(ProjectDependency.ecosystem.ilike(ecosystem))
    if dependency_type:
        query = query.filter(ProjectDependency.dependency_type == dependency_type.lower())
    if manifest_file:
        query = query.filter(ProjectDependency.manifest_file == manifest_file)
    if search:
        query = query.filter(ProjectDependency.name.ilike(f"%{search.strip()}%"))

    # Order: VULNERABLE first, then OUTDATED, then name asc
    # We can order by status (VULNERABLE desc) or name
    return (
        query.order_by(
            ProjectDependency.vulnerability_count.desc(),
            ProjectDependency.name.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@dependencies_router.get("/{project_id}/dependencies/issues", response_model=List[DependencyIssueResponse])
def get_dependency_issues(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    issue_type: Optional[str] = Query(None, description="Filter by issue_type: vulnerable_dependency, outdated_dependency"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List issues created for vulnerable or outdated dependencies."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(DependencyAnalysis)
            .filter(DependencyAnalysis.project_id == project.id)
            .order_by(DependencyAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        target_analysis_id = latest.id

    query = db.query(DependencyIssue).filter(
        DependencyIssue.analysis_id == target_analysis_id,
        DependencyIssue.project_id == project.id,
    )

    if severity:
        query = query.filter(DependencyIssue.severity == severity.upper())
    if issue_type:
        query = query.filter(DependencyIssue.issue_type == issue_type)

    return query.order_by(DependencyIssue.created_at.asc()).offset(offset).limit(limit).all()


@dependencies_router.get("/{project_id}/dependencies/{dependency_id}", response_model=ProjectDependencyResponse)
def get_project_dependency_detail(
    project_id: str,
    dependency_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed information and advisories for a single dependency."""
    project = get_user_project(project_id, current_user, db)

    dep = (
        db.query(ProjectDependency)
        .filter(
            ProjectDependency.id == dependency_id,
            ProjectDependency.project_id == project.id,
        )
        .first()
    )
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found",
        )
    return dep
