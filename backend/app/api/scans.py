import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan, ProjectFile
from backend.app.schemas.scan import ScanResponse, DiscoveredFileResponse, ScanStatisticsResponse
from backend.app.analyzers.scanner import scan_repository

scans_router = APIRouter(prefix="/projects", tags=["Repository Scanner"])


def get_user_project(project_id: str, current_user: User, db: Session) -> Project:
    """Helper to verify and retrieve a project owned by the current user."""
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


@scans_router.post("/{project_id}/scan", response_model=ScanResponse)
def trigger_repository_scan(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Trigger a repository scan on an unpacked READY project."""
    project = get_user_project(project_id, current_user, db)

    # Must be in READY state
    if project.status != "READY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project is not ready for scanning. Current status is '{project.status}'.",
        )

    if not project.storage_path or not os.path.exists(project.storage_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository storage path is missing or inaccessible on disk.",
        )

    try:
        scan_data = scan_repository(project.storage_path)

        # Clear any previous scan files for this project to maintain freshness
        previous_scans = db.query(ProjectScan).filter(ProjectScan.project_id == project.id).all()
        for prev in previous_scans:
            db.delete(prev)
        db.flush()

        # Create new ProjectScan record
        new_scan = ProjectScan(
            project_id=project.id,
            total_files=scan_data["total_files"],
            total_directories=scan_data["total_directories"],
            total_lines=scan_data["total_lines"],
            total_code_lines=scan_data["total_code_lines"],
            total_blank_lines=scan_data["total_blank_lines"],
            total_comment_lines=scan_data["total_comment_lines"],
            test_files_count=scan_data["test_files_count"],
            config_files_count=scan_data["config_files_count"],
            doc_files_count=scan_data["doc_files_count"],
            languages_summary=scan_data["languages_summary"],
            categories_summary=scan_data["categories_summary"],
            directory_tree=scan_data["directory_tree"],
            status="COMPLETED",
        )
        db.add(new_scan)
        db.flush()

        # Create ProjectFile records
        file_entities = []
        for f in scan_data["files"]:
            file_entities.append(
                ProjectFile(
                    scan_id=new_scan.id,
                    project_id=project.id,
                    file_path=f["file_path"],
                    file_name=f["file_name"],
                    extension=f["extension"],
                    language=f["language"],
                    category=f["category"],
                    size_bytes=f["size_bytes"],
                    total_lines=f["total_lines"],
                    code_lines=f["code_lines"],
                    blank_lines=f["blank_lines"],
                    comment_lines=f["comment_lines"],
                    is_binary=f["is_binary"],
                    is_test=f["is_test"],
                    is_config=f["is_config"],
                    is_doc=f["is_doc"],
                    is_skipped=f["is_skipped"],
                )
            )
        db.add_all(file_entities)
        db.commit()
        db.refresh(new_scan)

        return new_scan

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository scan failed: {str(e)}",
        ) from e


@scans_router.get("/{project_id}/scan", response_model=ScanResponse)
def get_latest_project_scan(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the latest repository scan result for a project."""
    project = get_user_project(project_id, current_user, db)
    scan = (
        db.query(ProjectScan)
        .filter(ProjectScan.project_id == project.id)
        .order_by(ProjectScan.scanned_at.desc())
        .first()
    )
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scan has been performed on this project yet.",
        )
    return scan


@scans_router.get("/{project_id}/tree")
def get_project_directory_tree(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the hierarchical directory tree from the latest scan."""
    project = get_user_project(project_id, current_user, db)
    scan = (
        db.query(ProjectScan)
        .filter(ProjectScan.project_id == project.id)
        .order_by(ProjectScan.scanned_at.desc())
        .first()
    )
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scan found. Please scan the repository first.",
        )
    return scan.directory_tree


@scans_router.get("/{project_id}/files", response_model=List[DiscoveredFileResponse])
def get_project_files(
    project_id: str,
    category: Optional[str] = Query(None, description="Filter by category (Source Code, Tests, Configuration, Documentation, Assets, Other)"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List discovered files with metadata from the latest scan."""
    project = get_user_project(project_id, current_user, db)
    scan = (
        db.query(ProjectScan)
        .filter(ProjectScan.project_id == project.id)
        .order_by(ProjectScan.scanned_at.desc())
        .first()
    )
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scan found. Please scan the repository first.",
        )

    query = db.query(ProjectFile).filter(ProjectFile.scan_id == scan.id)
    if category:
        query = query.filter(ProjectFile.category == category)
    if language:
        query = query.filter(ProjectFile.language == language)

    return query.order_by(ProjectFile.file_path.asc()).all()


@scans_router.get("/{project_id}/statistics", response_model=ScanStatisticsResponse)
def get_project_statistics(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve high-level code metrics and language statistics for a project."""
    project = get_user_project(project_id, current_user, db)
    scan = (
        db.query(ProjectScan)
        .filter(ProjectScan.project_id == project.id)
        .order_by(ProjectScan.scanned_at.desc())
        .first()
    )
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scan found. Please scan the repository first.",
        )

    return ScanStatisticsResponse(
        project_id=project.id,
        total_files=scan.total_files,
        total_directories=scan.total_directories,
        total_lines=scan.total_lines,
        total_code_lines=scan.total_code_lines,
        total_blank_lines=scan.total_blank_lines,
        total_comment_lines=scan.total_comment_lines,
        test_files_count=scan.test_files_count,
        config_files_count=scan.config_files_count,
        doc_files_count=scan.doc_files_count,
        languages=scan.languages_summary,
        categories=scan.categories_summary,
        scanned_at=scan.scanned_at,
    )
