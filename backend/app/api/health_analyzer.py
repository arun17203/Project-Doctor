from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.health import HealthAnalysis
from backend.app.schemas.health import HealthAnalysisResponse
from backend.app.analyzers.health.engine import HealthEngine

health_router = APIRouter(prefix="/projects", tags=["Health & Technical Debt"])


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


@health_router.post("/{project_id}/analyze/health", response_model=HealthAnalysisResponse)
def trigger_health_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run Health and Technical Debt audit.
    Requires completed results from Stages 4, 5, 6, 7, and 8.
    Calculates deterministic health scores, technical debt hours, explanations, and fix-first items.
    """
    project = get_user_project(project_id, current_user, db)

    engine = HealthEngine(db)
    valid, error_message = engine.check_prerequisites(project)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    try:
        health_record = engine.analyze_project_health(project)
        try:
            from backend.app.services.snapshot_service import SnapshotService
            SnapshotService.create_snapshot(project, db)
        except Exception:
            pass
        return health_record
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health analysis failed: {str(e)}",
        )


@health_router.get("/{project_id}/health", response_model=HealthAnalysisResponse)
def get_latest_health_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the latest health and technical debt analysis for a project."""
    project = get_user_project(project_id, current_user, db)

    health_record = (
        db.query(HealthAnalysis)
        .filter(HealthAnalysis.project_id == project.id)
        .order_by(HealthAnalysis.created_at.desc())
        .first()
    )
    if not health_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No health analysis found for this project. Please run health analysis first.",
        )

    return health_record


@health_router.get("/{project_id}/health/history", response_model=List[HealthAnalysisResponse])
def get_health_history(
    project_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve chronological history of health analyses for trend comparisons (Stage 12 preparation)."""
    project = get_user_project(project_id, current_user, db)

    records = (
        db.query(HealthAnalysis)
        .filter(HealthAnalysis.project_id == project.id)
        .order_by(HealthAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
    return records
