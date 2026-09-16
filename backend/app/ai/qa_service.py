import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.ai.client import gemini_client, GeminiClient, AIUnavailableError, AIExplanationError
from backend.app.ai.retrieval import CodebaseRetriever
from backend.app.ai.prompts import build_qa_prompt
from backend.app.ai.schemas import SourceCitation, CodebaseQAResponse, CodebaseQAOutput

logger = logging.getLogger(__name__)


class CodebaseQAService:
    def __init__(self, db: Session, client: Optional[GeminiClient] = None):
        self.db = db
        self.gemini_client = client or gemini_client

    def answer_question(
        self,
        project_id: str,
        user_id: str,
        question: str,
        conversation: Optional[List[Dict[str, str]]] = None,
    ) -> CodebaseQAResponse:
        # 1. Project ownership verification
        project = (
            self.db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or unauthorized.",
            )

        # 2. Verify repository scan completed
        scan = (
            self.db.query(ProjectScan)
            .filter(ProjectScan.project_id == project.id, ProjectScan.status == "COMPLETED")
            .first()
        )
        if not scan:
            return CodebaseQAResponse(
                answer="This repository has not been scanned yet. Please run the Repository Scanner (Stage 4) first so I can inspect your codebase files.",
                sources=[],
                project_id=project.id,
                provider="google-gemini",
                model=self.gemini_client.model,
                available=True,
            )

        # 3. Retrieve grounded codebase context
        retriever = CodebaseRetriever(project, self.db)
        context = retriever.retrieve(question)

        # 4. Build grounded prompt
        prompt = build_qa_prompt(context, question, conversation)

        # 5. Invoke Gemini with structured schema
        try:
            qa_output: CodebaseQAOutput = self.gemini_client.generate_qa_answer(prompt)
        except AIUnavailableError as aue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(aue),
            )
        except AIExplanationError as aee:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(aee),
            )

        # 6. Strict Citation Verification:
        # Only allow citations that correspond to real files in this user's project
        verified_sources: List[SourceCitation] = []
        seen_paths = set()

        for src in qa_output.sources:
            norm_path = src.file_path.replace("\\", "/").strip().lstrip("./")
            matched_real_path = None

            for real_path in context.all_project_files:
                if real_path == norm_path or real_path.endswith(f"/{norm_path}") or norm_path.endswith(f"/{real_path}"):
                    matched_real_path = real_path
                    break

            if matched_real_path and matched_real_path not in seen_paths:
                seen_paths.add(matched_real_path)
                verified_sources.append(
                    SourceCitation(
                        file_path=matched_real_path,
                        line_start=src.line_start,
                        line_end=src.line_end,
                        reason=src.reason or "Referenced in answer",
                    )
                )

        # If model did not cite files but we retrieved highly relevant snippets, attach them as grounding references
        if not verified_sources and context.code_snippets and "couldn't find enough evidence" not in qa_output.answer.lower():
            for s in context.code_snippets[:3]:
                if s.file_path not in seen_paths:
                    seen_paths.add(s.file_path)
                    verified_sources.append(
                        SourceCitation(
                            file_path=s.file_path,
                            line_start=s.line_start,
                            line_end=s.line_end,
                            reason=s.reason,
                        )
                    )

        return CodebaseQAResponse(
            answer=qa_output.answer,
            sources=verified_sources,
            project_id=project.id,
            provider="google-gemini",
            model=self.gemini_client.model,
            available=True,
        )
