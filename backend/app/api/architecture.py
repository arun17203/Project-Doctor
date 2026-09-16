from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.models.architecture import (
    ArchitectureAnalysis,
    ArchitectureNode,
    ArchitectureEdge,
)
from backend.app.schemas.architecture import (
    ArchitectureAnalysisResponse,
    ArchitectureNodeResponse,
    ArchitectureEdgeResponse,
    ArchitectureCycleResponse,
    ArchitectureGraphResponse,
)
from backend.app.analyzers.architecture.engine import run_architecture_analysis
from backend.app.models.base import utc_now

architecture_router = APIRouter(prefix="/projects", tags=["Architecture Graph"])


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


@architecture_router.post("/{project_id}/analyze/architecture", response_model=ArchitectureAnalysisResponse)
def trigger_architecture_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Trigger static architecture import and circular dependency analysis on an already-scanned project.
    Zero code execution. Real repository imports only.
    """
    project = get_user_project(project_id, current_user, db)

    # 1. Verify project status is READY
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
            detail="A completed Stage 4 repository scan is required before running architecture analysis.",
        )

    # 3. Create initial pending record
    analysis = ArchitectureAnalysis(
        project_id=project.id,
        scan_id=scan.id,
        status="IN_PROGRESS",
        started_at=utc_now(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # 4. Execute architecture engine
        results = run_architecture_analysis(project, scan, db)

        # 5. Update analysis record with metrics
        analysis.status = "COMPLETED"
        analysis.completed_at = utc_now()
        analysis.node_count = results["node_count"]
        analysis.edge_count = results["edge_count"]
        analysis.cycle_count = results["cycle_count"]
        analysis.metrics = results.get("metrics", {})

        # 6. Bulk insert architecture nodes
        node_models = []
        path_to_node_id = {}

        for n in results["nodes"]:
            node_obj = ArchitectureNode(
                analysis_id=analysis.id,
                project_id=project.id,
                file_path=n["file_path"],
                name=n["name"],
                language=n["language"],
                layer=n["layer"],
                node_type=n.get("node_type", "file"),
                directory=n.get("directory", ""),
                metrics=n.get("metrics", {}),
            )
            node_models.append(node_obj)

        if node_models:
            db.add_all(node_models)
            db.flush()  # Populates node IDs
            for node_obj in node_models:
                path_to_node_id[node_obj.file_path] = node_obj.id

        # 7. Bulk insert architecture edges
        edge_models = []
        for e in results["edges"]:
            src_id = path_to_node_id.get(e["source"])
            tgt_id = path_to_node_id.get(e["target"])
            if src_id and tgt_id:
                edge_obj = ArchitectureEdge(
                    analysis_id=analysis.id,
                    project_id=project.id,
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    relationship_type=e.get("relationship_type", "imports"),
                    raw_import=e.get("raw_import"),
                    is_circular=e.get("is_circular", False),
                )
                edge_models.append(edge_obj)

        if edge_models:
            db.add_all(edge_models)

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
            detail=f"Architecture analysis failed: {str(e)}",
        ) from e


@architecture_router.get("/{project_id}/architecture", response_model=ArchitectureAnalysisResponse)
def get_latest_architecture_analysis(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the latest architecture analysis record for a project."""
    project = get_user_project(project_id, current_user, db)
    analysis = (
        db.query(ArchitectureAnalysis)
        .filter(ArchitectureAnalysis.project_id == project.id)
        .order_by(ArchitectureAnalysis.started_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No architecture analysis found for this project. Please run architecture analysis first.",
        )
    return analysis


@architecture_router.get("/{project_id}/architecture/nodes", response_model=List[ArchitectureNodeResponse])
def get_architecture_nodes(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    layer: Optional[str] = Query(None, description="Filter by layer: Presentation, API, Service, Data, Utility, etc."),
    directory: Optional[str] = Query(None, description="Filter by directory prefix"),
    search: Optional[str] = Query(None, description="Search node name or file path"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve architecture nodes with optional filtering."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.project_id == project.id)
            .order_by(ArchitectureAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        target_analysis_id = latest.id

    query = db.query(ArchitectureNode).filter(
        ArchitectureNode.analysis_id == target_analysis_id,
        ArchitectureNode.project_id == project.id,
    )

    if layer:
        query = query.filter(ArchitectureNode.layer.ilike(layer))
    if directory:
        query = query.filter(ArchitectureNode.directory.ilike(f"{directory}%"))
    if search:
        query = query.filter(
            (ArchitectureNode.name.ilike(f"%{search.strip()}%")) |
            (ArchitectureNode.file_path.ilike(f"%{search.strip()}%"))
        )

    return query.order_by(ArchitectureNode.file_path.asc()).offset(offset).limit(limit).all()


@architecture_router.get("/{project_id}/architecture/edges", response_model=List[ArchitectureEdgeResponse])
def get_architecture_edges(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    is_circular: Optional[bool] = Query(None, description="Filter circular edges"),
    limit: int = Query(1000, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve architecture edges representing import relationships."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.project_id == project.id)
            .order_by(ArchitectureAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        target_analysis_id = latest.id

    query = db.query(ArchitectureEdge).filter(
        ArchitectureEdge.analysis_id == target_analysis_id,
        ArchitectureEdge.project_id == project.id,
    )

    if is_circular is not None:
        query = query.filter(ArchitectureEdge.is_circular == is_circular)

    return query.offset(offset).limit(limit).all()


@architecture_router.get("/{project_id}/architecture/cycles", response_model=List[ArchitectureCycleResponse])
def get_architecture_cycles(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve all detected circular dependency chains."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.project_id == project.id)
            .order_by(ArchitectureAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            return []
        analysis = latest
    else:
        analysis = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.id == target_analysis_id, ArchitectureAnalysis.project_id == project.id)
            .first()
        )
        if not analysis:
            raise HTTPException(status_code=404, detail="Architecture analysis not found")

    cycles_summary = (analysis.metrics or {}).get("cycles_summary", [])
    result = []
    for c_str in cycles_summary:
        parts = [p.strip() for p in c_str.split(" -> ") if p.strip()]
        result.append(ArchitectureCycleResponse(cycle=parts, length=max(0, len(parts) - 1)))
    return result


@architecture_router.get("/{project_id}/architecture/graph", response_model=ArchitectureGraphResponse)
def get_architecture_graph(
    project_id: str,
    analysis_id: Optional[str] = Query(None, description="Optional specific analysis ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve complete graph data (analysis, nodes, edges, cycles) for the frontend canvas."""
    project = get_user_project(project_id, current_user, db)

    target_analysis_id = analysis_id
    if not target_analysis_id:
        latest = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.project_id == project.id)
            .order_by(ArchitectureAnalysis.started_at.desc())
            .first()
        )
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No architecture analysis found for this project.",
            )
        analysis = latest
    else:
        analysis = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.id == target_analysis_id, ArchitectureAnalysis.project_id == project.id)
            .first()
        )
        if not analysis:
            raise HTTPException(status_code=404, detail="Architecture analysis not found")

    nodes = (
        db.query(ArchitectureNode)
        .filter(ArchitectureNode.analysis_id == analysis.id)
        .all()
    )
    edges = (
        db.query(ArchitectureEdge)
        .filter(ArchitectureEdge.analysis_id == analysis.id)
        .all()
    )

    cycles_summary = (analysis.metrics or {}).get("cycles_summary", [])
    raw_cycles = [
        [p.strip() for p in c_str.split(" -> ") if p.strip()]
        for c_str in cycles_summary
    ]

    return ArchitectureGraphResponse(
        analysis=analysis,
        nodes=nodes,
        edges=edges,
        cycles=raw_cycles,
    )
