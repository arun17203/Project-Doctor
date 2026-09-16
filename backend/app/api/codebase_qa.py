from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.ai.schemas import CodebaseQARequest, CodebaseQAResponse
from backend.app.ai.qa_service import CodebaseQAService

qa_router = APIRouter(prefix="/projects", tags=["Codebase Q&A"])


@qa_router.post("/{project_id}/ask", response_model=CodebaseQAResponse)
def ask_codebase(
    project_id: str,
    request: CodebaseQARequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Ask a question about an imported codebase.
    Returns a grounded answer supported strictly by repository evidence and verified source citations.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    service = CodebaseQAService(db)
    conv_dicts = [m.model_dump() for m in request.conversation] if request.conversation else []

    return service.answer_question(
        project_id=project_id,
        user_id=current_user.id,
        question=question,
        conversation=conv_dicts,
    )
