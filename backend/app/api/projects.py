import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectCreate, ProjectResponse, GitHubImportRequest
from backend.app.services.extractor import safe_extract_zip
from backend.app.services.git_service import clone_github_repo

projects_router = APIRouter(prefix="/projects", tags=["Projects"])


def get_project_storage_dir(project_id: str) -> str:
    """Generate sandboxed storage directory for a project."""
    base_storage = os.path.abspath(settings.STORAGE_DIR)
    project_dir = os.path.abspath(os.path.join(base_storage, "projects", project_id, "source"))
    # Verify sandbox constraint
    if not project_dir.startswith(base_storage):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage configuration error: Path traversal attempt detected.",
        )
    return project_dir


@projects_router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new software project metadata record belonging to the current user."""
    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        source_type=project_in.source_type,
        source_url=project_in.source_url,
        status="CREATED",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@projects_router.get("", response_model=List[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all projects belonging to the authenticated user."""
    return (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )


@projects_router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve details of a specific project owned by the authenticated user."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@projects_router.post("/{project_id}/upload", response_model=ProjectResponse)
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload and safely extract a ZIP archive into the project's sandboxed storage."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Validate file extension
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .zip archive files are accepted.",
        )

    # Read and enforce size limit
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded ZIP exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB size limit.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded ZIP file is empty.",
        )

    target_dir = get_project_storage_dir(project.id)

    try:
        project.status = "PROCESSING"
        db.commit()

        # Safely extract with path traversal prevention and file filters
        extracted_count, _ = safe_extract_zip(content, target_dir)

        project.storage_path = target_dir
        project.original_filename = filename
        project.source_type = "zip"
        project.status = "READY"
        db.commit()
        db.refresh(project)
        return project

    except ValueError as e:
        project.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        project.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the ZIP archive: {str(e)}",
        ) from e


@projects_router.post("/{project_id}/github", response_model=ProjectResponse)
def import_github_repo(
    project_id: str,
    github_in: GitHubImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Clone a public GitHub repository into the project's sandboxed storage."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    target_dir = get_project_storage_dir(project.id)

    try:
        project.status = "CLONING"
        project.source_url = github_in.github_url
        project.source_type = "github"
        db.commit()

        # Clone and sanitize
        clone_github_repo(github_in.github_url, target_dir)

        project.storage_path = target_dir
        project.status = "READY"
        db.commit()
        db.refresh(project)
        return project

    except ValueError as e:
        project.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        project.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while importing repository: {str(e)}",
        ) from e


@projects_router.delete("/{project_id}")
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a project record and all associated extracted files on disk."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Safely remove extracted files from disk if exists
    base_storage = os.path.abspath(settings.STORAGE_DIR)
    project_root = os.path.abspath(os.path.join(base_storage, "projects", project.id))
    if project_root.startswith(base_storage) and os.path.exists(project_root):
        shutil.rmtree(project_root, ignore_errors=True)

    db.delete(project)
    db.commit()
    return {"message": "Project successfully deleted"}
