from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict


class QualityIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    project_id: str
    issue_type: str
    severity: str
    file_path: str
    line_number: int
    end_line: Optional[int] = None
    symbol_name: Optional[str] = None
    message: str
    description: str
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: datetime


class QualityAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scan_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    metrics: Dict[str, Any]
    error_message: Optional[str] = None


class SnippetLine(BaseModel):
    line_number: int
    content: str
    is_highlighted: bool


class CodeSnippetResponse(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    target_line: int
    lines: List[SnippetLine]
