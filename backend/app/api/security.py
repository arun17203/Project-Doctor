import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.schemas.security import (
    SecurityAnalysisResponse,
    SecurityIssueResponse,
    SecuritySnippetResponse,
    SecuritySnippetLine,
)
from backend.app.analyzers.security.engine import run_security_analysis
from backend.app.analyzers.security.secrets import mask_line
from backend.app.models.base import utc_now

security_router = APIRouter(prefix="/projects", tags=["Security Audit Engine"])


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


@security_router.post("/{project_id}/analyze/security", response_model=SecurityAnalysisResponse)
def trigger_security_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Trigger static security audit analysis on an already-scanned project.
    Zero code execution. Strict secret masking.
    """
    project = get_user_project(project_id, current_user, db)

    # 1. Verify project is READY
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
            detail="A completed Stage 4 repository scan is required before running security analysis.",
        )

    # 3. Create initial pending analysis record
    analysis = SecurityAnalysis(
        project_id=project.id,
        scan_id=scan.id,
        status="IN_PROGRESS",
        started_at=utc_now(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # 4. Run static security analysis
        results = run_security_analysis(project, scan, db)

        # 5. Update analysis record with metrics
        analysis.status = "COMPLETED"
        analysis.completed_at = utc_now()
        analysis.total_issues = results["total_issues"]
        analysis.critical_count = results["critical_count"]
        analysis.high_count = results["high_count"]
        analysis.medium_count = results["medium_count"]
        analysis.low_count = results["low_count"]
        analysis.metrics = results["metrics"]

        # 6. Bulk insert security issues
        issues_to_create = []
        for iss in results["issues"]:
            issues_to_create.append(
                SecurityIssue(
                    analysis_id=analysis.id,
                    project_id=project.id,
                    category=iss.get("category", "security"),
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    confidence=iss.get("confidence", "HIGH"),
                    file_path=iss["file_path"],
                    line_number=iss["line_number"],
                    end_line=iss.get("end_line"),
                    symbol_name=iss.get("symbol_name"),
                    message=iss["message"],
                    description=iss["description"],
                    evidence=iss.get("evidence"),  # Strictly masked
                    recommendation=iss.get("recommendation"),
                )
            )

        if issues_to_create:
            db.add_all(issues_to_create)

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
            detail=f"Security audit analysis failed: {str(e)}",
        ) from e


@security_router.get("/{project_id}/security", response_model=SecurityAnalysisResponse)
def get_latest_security_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the latest security audit analysis for a project."""
    project = get_user_project(project_id, current_user, db)
    analysis = (
        db.query(SecurityAnalysis)
        .filter(SecurityAnalysis.project_id == project.id)
        .order_by(SecurityAnalysis.started_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No security analysis found for this project. Please run security audit first.",
        )
    return analysis


@security_router.get("/{project_id}/security/issues", response_model=List[SecurityIssueResponse])
def get_security_issues(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    category: Optional[str] = Query(None, description="Filter by category: SECRETS, INJECTION, etc."),
    issue_type: Optional[str] = Query(None, description="Filter by issue_type"),
    file_path: Optional[str] = Query(None, description="Filter by relative file path"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List detected security issues with optional filtering."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(SecurityAnalysis)
            .filter(SecurityAnalysis.project_id == project.id)
            .order_by(SecurityAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        target_analysis_id = latest.id

    query = db.query(SecurityIssue).filter(
        SecurityIssue.analysis_id == target_analysis_id,
        SecurityIssue.project_id == project.id,
    )

    if severity:
        query = query.filter(SecurityIssue.severity == severity.upper())
    if category:
        query = query.filter(SecurityIssue.category == category.upper())
    if issue_type:
        query = query.filter(SecurityIssue.issue_type == issue_type)
    if file_path:
        query = query.filter(SecurityIssue.file_path == file_path)

    # Order by severity priority (CRITICAL -> HIGH -> MEDIUM -> LOW) then line number
    return query.order_by(SecurityIssue.line_number.asc()).offset(offset).limit(limit).all()


@security_router.get("/{project_id}/security/snippet", response_model=SecuritySnippetResponse)
def get_security_code_snippet(
    project_id: str,
    file_path: str = Query(..., description="Relative file path"),
    line_number: int = Query(..., ge=1, description="Target line number"),
    window: int = Query(5, ge=1, le=20, description="Lines of context before and after"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Read a small, read-only code snippet around a security issue line with guaranteed credential masking.
    Zero code execution.
    """
    project = get_user_project(project_id, current_user, db)

    if not project.storage_path or not os.path.exists(project.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project storage not found",
        )

    # Prevent directory traversal
    normalized_rel = os.path.normpath(file_path).lstrip("/\\")
    if ".." in normalized_rel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path",
        )

    abs_path = os.path.abspath(os.path.join(project.storage_path, normalized_rel))
    if not abs_path.startswith(os.path.abspath(project.storage_path)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access outside project directory forbidden",
        )

    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in project",
        )

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read source file: {str(e)}",
        ) from e

    total_lines = len(all_lines)
    start_line = max(1, line_number - window)
    end_line = min(total_lines, line_number + window)

    snippet_lines = []
    for cur_num in range(start_line, end_line + 1):
        raw_text = all_lines[cur_num - 1].rstrip("\r\n")
        # Strictly mask credentials
        masked_text = mask_line(raw_text)
        snippet_lines.append(
            SecuritySnippetLine(
                line_number=cur_num,
                content=masked_text,
                is_highlighted=(cur_num == line_number),
            )
        )

    return SecuritySnippetResponse(
        file_path=normalized_rel,
        start_line=start_line,
        end_line=end_line,
        target_line=line_number,
        lines=snippet_lines,
    )
