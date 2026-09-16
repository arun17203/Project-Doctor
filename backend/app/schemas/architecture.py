from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict


class ArchitectureNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    project_id: str
    file_path: str
    name: str
    language: str
    layer: str
    node_type: str
    directory: str
    metrics: Dict[str, Any] = {}
    created_at: datetime


class ArchitectureEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    project_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    raw_import: Optional[str] = None
    is_circular: bool = False
    created_at: datetime


class ArchitectureAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scan_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    node_count: int
    edge_count: int
    cycle_count: int
    metrics: Dict[str, Any] = {}
    error_message: Optional[str] = None


class ArchitectureCycleResponse(BaseModel):
    cycle: List[str]
    length: int


class ArchitectureGraphResponse(BaseModel):
    analysis: ArchitectureAnalysisResponse
    nodes: List[ArchitectureNodeResponse]
    edges: List[ArchitectureEdgeResponse]
    cycles: List[List[str]] = []
