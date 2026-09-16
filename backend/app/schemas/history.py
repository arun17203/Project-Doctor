from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class SnapshotSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    version_number: int
    status: str
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
    total_issues: int = 0
    total_files: int
    total_lines: int
    created_at: datetime
    summary: Optional[str] = None


class SnapshotDetailResponse(SnapshotSummaryResponse):
    repository_scan_id: Optional[str] = None
    quality_analysis_id: Optional[str] = None
    security_analysis_id: Optional[str] = None
    dependency_analysis_id: Optional[str] = None
    architecture_analysis_id: Optional[str] = None
    health_analysis_id: Optional[str] = None

    critical_security_count: int = 0
    high_security_count: int = 0
    high_complexity_count: int = 0
    long_functions_count: int = 0
    duplicate_blocks_count: int = 0
    total_dependencies: int = 0
    vulnerable_dependencies_count: int = 0
    outdated_dependencies_count: int = 0
    architecture_nodes_count: int = 0
    architecture_edges_count: int = 0
    architecture_cycles_count: int = 0

    file_manifest: List[Dict[str, Any]] = []


class HistoryListResponse(BaseModel):
    items: List[SnapshotSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MetricDelta(BaseModel):
    metric_name: str
    from_value: float
    to_value: float
    difference: float
    direction: str  # "IMPROVED", "WORSENED", "UNCHANGED"
    unit: str = "points"


class FileDiffSummary(BaseModel):
    files_added: int = 0
    files_removed: int = 0
    files_modified: int = 0
    total_files_before: int = 0
    total_files_after: int = 0
    sample_added: List[str] = []
    sample_removed: List[str] = []


class VersionComparisonResponse(BaseModel):
    project_id: str
    from_version: int
    to_version: int
    from_created_at: datetime
    to_created_at: datetime

    # Scores
    health_delta: MetricDelta
    security_delta: MetricDelta
    quality_delta: MetricDelta
    dependency_delta: MetricDelta
    architecture_delta: MetricDelta
    maintainability_delta: MetricDelta
    testing_delta: MetricDelta

    # Technical Debt
    technical_debt_delta: MetricDelta

    # Issues
    critical_issues_delta: MetricDelta
    high_issues_delta: MetricDelta
    medium_issues_delta: MetricDelta
    low_issues_delta: MetricDelta
    total_issues_delta: MetricDelta

    # Deep sub-metrics
    vulnerable_deps_delta: MetricDelta
    outdated_deps_delta: MetricDelta
    complexity_delta: MetricDelta
    cycles_delta: MetricDelta

    # Repository File Changes
    file_diff: FileDiffSummary

    # Deterministic change summaries
    summary_headline: str
    summary_text: str


class CreateSnapshotRequest(BaseModel):
    summary: Optional[str] = Field(None, max_length=500, description="Optional note or version description")
