import os
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.schemas.quality import (
    QualityAnalysisResponse,
    QualityIssueResponse,
    CodeSnippetResponse,
    SnippetLine,
)
from backend.app.analyzers.quality_engine import run_code_quality_analysis
from backend.app.models.base import utc_now

quality_router = APIRouter(prefix="/projects", tags=["Code Quality Analyzer"])

# Regex for basic masking of credentials in read-only snippet view
MASK_REGEX = re.compile(
    r'(?i)((?:password|secret|api_key|token|access_key|auth_token|jwt|apikey)\s*[:=]\s*)(["\'])(.*?)(["\'])'
)


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


@quality_router.post("/{project_id}/analyze/quality", response_model=QualityAnalysisResponse)
def trigger_quality_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Trigger static code quality analysis on an already-scanned project."""
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
            detail="A completed Stage 4 repository scan is required before running code quality analysis.",
        )

    # 3. Create initial pending analysis record
    analysis = QualityAnalysis(
        project_id=project.id,
        scan_id=scan.id,
        status="IN_PROGRESS",
        started_at=utc_now(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # 4. Run static quality analysis
        results = run_code_quality_analysis(project, scan, db)

        # 5. Update analysis record with metrics
        analysis.status = "COMPLETED"
        analysis.completed_at = utc_now()
        analysis.total_issues = results["total_issues"]
        analysis.critical_count = results["critical_count"]
        analysis.high_count = results["high_count"]
        analysis.medium_count = results["medium_count"]
        analysis.low_count = results["low_count"]
        analysis.metrics = results["metrics"]

        # 6. Bulk insert issues
        issues_to_create = []
        for iss in results["issues"]:
            issues_to_create.append(
                QualityIssue(
                    analysis_id=analysis.id,
                    project_id=project.id,
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    file_path=iss["file_path"],
                    line_number=iss["line_number"],
                    end_line=iss.get("end_line"),
                    symbol_name=iss.get("symbol_name"),
                    message=iss["message"],
                    description=iss["description"],
                    evidence=iss.get("evidence"),
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
            detail=f"Code quality analysis failed: {str(e)}",
        ) from e


@quality_router.get("/{project_id}/quality", response_model=QualityAnalysisResponse)
def get_latest_quality_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the latest quality analysis for a project."""
    project = get_user_project(project_id, current_user, db)
    analysis = (
        db.query(QualityAnalysis)
        .filter(QualityAnalysis.project_id == project.id)
        .order_by(QualityAnalysis.started_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quality analysis found for this project. Please run analysis first.",
        )
    return analysis


@quality_router.get("/{project_id}/quality/issues", response_model=List[QualityIssueResponse])
def get_quality_issues(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    issue_type: Optional[str] = Query(None, description="Filter by issue_type"),
    file_path: Optional[str] = Query(None, description="Filter by relative file path"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List detected quality issues with optional filtering."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(QualityAnalysis)
            .filter(QualityAnalysis.project_id == project.id)
            .order_by(QualityAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        target_analysis_id = latest.id

    query = db.query(QualityIssue).filter(
        QualityIssue.analysis_id == target_analysis_id,
        QualityIssue.project_id == project.id,
    )

    if severity:
        query = query.filter(QualityIssue.severity == severity.upper())
    if issue_type:
        query = query.filter(QualityIssue.issue_type == issue_type)
    if file_path:
        query = query.filter(QualityIssue.file_path == file_path)

    # Order by severity priority then line number
    return query.order_by(QualityIssue.line_number.asc()).offset(offset).limit(limit).all()


@quality_router.get("/{project_id}/quality/snippet", response_model=CodeSnippetResponse)
def get_code_snippet(
    project_id: str,
    file_path: str = Query(..., description="Relative file path"),
    line_number: int = Query(..., ge=1, description="Target line number"),
    window: int = Query(5, ge=1, le=20, description="Lines of context before and after"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Read a small, read-only code snippet around an issue line with credential masking.
    Zero code execution.
    """
    project = get_user_project(project_id, current_user, db)

    if not project.storage_path or not os.path.exists(project.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project storage not found",
        )

    # Prevent path traversal
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
        # Mask credentials
        masked_text = MASK_REGEX.sub(r'\1\2********\4', raw_text)
        snippet_lines.append(
            SnippetLine(
                line_number=cur_num,
                content=masked_text,
                is_highlighted=(cur_num == line_number),
            )
        )

    return CodeSnippetResponse(
        file_path=normalized_rel,
        start_line=start_line,
        end_line=end_line,
        target_line=line_number,
        lines=snippet_lines,
    )
