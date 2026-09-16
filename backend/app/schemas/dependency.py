from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict


class VulnerabilityAdvisorySchema(BaseModel):
    id: str
    severity: str
    affected_versions: Optional[str] = None
    fixed_version: Optional[str] = None
    summary: Optional[str] = None
    reference_url: Optional[str] = None


class ProjectDependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    project_id: str
    manifest_file: str
    ecosystem: str
    name: str
    declared_version: Optional[str] = None
    resolved_version: Optional[str] = None
    dependency_type: str
    latest_version: Optional[str] = None
    status: str
    vulnerability_count: int
    advisories: List[Dict[str, Any]] = []
    created_at: datetime


class DependencyIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    project_id: str
    dependency_id: Optional[str] = None
    category: str
    issue_type: str
    severity: str
    package_name: str
    manifest_file: str
    version: str
    vulnerability_id: Optional[str] = None
    description: str
    recommendation: Optional[str] = None
    created_at: datetime


class DependencyAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scan_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_dependencies: int
    direct_dependencies: int
    transitive_dependencies: int
    current_count: int
    outdated_count: int
    vulnerable_count: int
    unknown_count: int
    metrics: Dict[str, Any] = {}
    error_message: Optional[str] = None


class DependencySummaryResponse(BaseModel):
    analysis_id: str
    status: str
    total_dependencies: int
    direct_dependencies: int
    transitive_dependencies: int
    current_count: int
    outdated_count: int
    vulnerable_count: int
    unknown_count: int
    manifests: List[str] = []
    by_ecosystem: Dict[str, int] = {}
    network_warning: bool = False
    completed_at: Optional[datetime] = None
