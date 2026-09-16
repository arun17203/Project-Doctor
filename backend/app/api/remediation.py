from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.services.remediation_service import remediation_service

remediation_router = APIRouter(prefix="/projects/{project_id}/remediation", tags=["Remediation"])


def _get_user_project(project_id: str, current_user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project.",
        )
    return project


@remediation_router.get("")
def get_project_prescription(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the doctor's prescription, prioritized triage orders, and unified git diff for auto-fixing issues."""
    project = _get_user_project(project_id, current_user, db)
    prescription = remediation_service.generate_prescription(db, project)
    return prescription


@remediation_router.get("/download")
def download_prescription_patch(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Download the generated Unified Git Diff (.patch file) to apply via 'git apply'."""
    project = _get_user_project(project_id, current_user, db)
    prescription = remediation_service.generate_prescription(db, project)
    
    diff_content = prescription.get("unified_diff", "")
    filename = prescription.get("patch_filename", "project_doctor_prescription.patch")
    
    return Response(
        content=diff_content,
        media_type="text/x-diff",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
