from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AIExplanationOutput(BaseModel):
    """Structured output expected directly from Google Gemini."""
    summary: str = Field(
        ...,
        description="Concise, clear explanation of the specific static-analysis finding.",
    )
    why_it_matters: str = Field(
        ...,
        description="Technical explanation of why this issue is problematic in production or maintenance.",
    )
    potential_impact: str = Field(
        ...,
        description="Downstream consequences on software security, maintainability, or system reliability.",
    )
    recommendation: str = Field(
        ...,
        description="Concrete, actionable engineering approach to resolve or refactor this finding.",
    )
    priority: str = Field(
        ...,
        description="Recommended remediation urgency (Immediate, High, Medium, Low) respecting analyzer severity.",
    )
    developer_action: str = Field(
        ...,
        description="Step-by-step instructions for a software developer to fix the issue.",
    )


class ExplainIssueRequest(BaseModel):
    force_regenerate: bool = False


class AIExplanationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    issue_id: str
    project_id: str
    issue_category: str
    issue_type: str
    provider: str
    model: str
    summary: str
    why_it_matters: str
    potential_impact: str
    recommendation: str
    priority: str
    developer_action: str
    created_at: datetime
    updated_at: datetime
    available: bool = True
    error_message: Optional[str] = None


class SourceCitation(BaseModel):
    file_path: str = Field(..., description="Relative path of the referenced file in the repository")
    line_start: Optional[int] = Field(None, description="Starting line number of the reference")
    line_end: Optional[int] = Field(None, description="Ending line number of the reference")
    reason: Optional[str] = Field(None, description="Brief explanation of why this file/snippet is relevant")


class CodebaseQAOutput(BaseModel):
    answer: str = Field(..., description="Detailed, technical, grounded answer to the developer's question")
    sources: list[SourceCitation] = Field(default_factory=list, description="Verified source citations actually retrieved from the repository")


class ChatMessageInput(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Text content of the message")


class CodebaseQARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Question about the imported codebase")
    conversation: list[ChatMessageInput] = Field(default_factory=list, description="Recent conversation history turns")


class CodebaseQAResponse(BaseModel):
    answer: str
    sources: list[SourceCitation] = Field(default_factory=list)
    project_id: str
    provider: str = "google-gemini"
    model: str = "gemini-2.5-flash"
    available: bool = True
    error_message: Optional[str] = None

