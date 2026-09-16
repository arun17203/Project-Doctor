from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.ai.service import ai_explainer_service
from backend.app.ai.schemas import AIExplanationResponse, ExplainIssueRequest

router = APIRouter(prefix="/issues", tags=["AI Explainer"])


@router.post("/{issue_id}/explain", response_model=AIExplanationResponse)
def explain_issue(
    issue_id: str,
    payload: Optional[ExplainIssueRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explains a static-analysis finding using Google Gemini.
    Uses cached explanation if already generated, unless force_regenerate=True.
    """
    force_regenerate = payload.force_regenerate if payload else False
    explanation = ai_explainer_service.explain_issue(
        db=db,
        issue_id=issue_id,
        user=current_user,
        force_regenerate=force_regenerate,
    )
    return explanation


@router.get("/{issue_id}/explanation", response_model=AIExplanationResponse)
def get_issue_explanation(
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves existing AI explanation for an issue if already generated."""
    explanation = ai_explainer_service.get_existing_explanation(
        db=db,
        issue_id=issue_id,
        user=current_user,
    )
    if not explanation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI explanation has been generated yet for issue '{issue_id}'.",
        )
    return explanation


@router.post("/{issue_id}/explanation/regenerate", response_model=AIExplanationResponse)
def regenerate_issue_explanation(
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explicitly re-runs Google Gemini to generate a fresh explanation for the issue."""
    explanation = ai_explainer_service.explain_issue(
        db=db,
        issue_id=issue_id,
        user=current_user,
        force_regenerate=True,
    )
    return explanation
