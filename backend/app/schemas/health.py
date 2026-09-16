from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict


class FixFirstItem(BaseModel):
    rank: int
    category: str
    severity: str
    title: str
    location: str
    file_path: str
    line_number: Optional[int] = None
    description: str
    recommendation: str


class TechnicalDebtBreakdown(BaseModel):
    quality_hours: float
    security_hours: float
    dependency_hours: float
    architecture_hours: float
    total_hours: float


class HealthExplanations(BaseModel):
    summary: str
    why_breakdown: List[str]
    category_drivers: Dict[str, List[str]]


class HealthAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    repository_scan_id: str

    quality_analysis_id: Optional[str] = None
    security_analysis_id: Optional[str] = None
    dependency_analysis_id: Optional[str] = None
    architecture_analysis_id: Optional[str] = None

    overall_score: float
    quality_score: float
    security_score: float
    dependency_score: float
    architecture_score: float
    maintainability_score: float
    testing_score: float

    technical_debt_hours: float

    critical_count: int
    high_count: int
    medium_count: int
    low_count: int

    status: str

    explanations: Dict[str, Any] = {}
    debt_breakdown: Dict[str, Any] = {}
    fix_first: List[Dict[str, Any]] = []
    weights_used: Dict[str, float] = {}

    created_at: datetime
    updated_at: datetime
