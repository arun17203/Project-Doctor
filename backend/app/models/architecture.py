from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class ArchitectureAnalysis(Base):
    __tablename__ = "architecture_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(String(36), ForeignKey("project_scans.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(30), default="COMPLETED")  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    cycle_count = Column(Integer, default=0)

    metrics = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="architecture_analyses")
    scan = relationship("ProjectScan")
    nodes = relationship("ArchitectureNode", back_populates="analysis", cascade="all, delete-orphan")
    edges = relationship("ArchitectureEdge", back_populates="analysis", cascade="all, delete-orphan")


class ArchitectureNode(Base):
    __tablename__ = "architecture_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("architecture_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    file_path = Column(String(500), nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    language = Column(String(50), default="Unknown", index=True)
    layer = Column(String(50), default="Unknown", index=True)
    node_type = Column(String(50), default="file", index=True)
    directory = Column(String(255), default="", index=True)

    metrics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    analysis = relationship("ArchitectureAnalysis", back_populates="nodes")
    project = relationship("Project")


class ArchitectureEdge(Base):
    __tablename__ = "architecture_edges"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("architecture_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    source_node_id = Column(String(36), ForeignKey("architecture_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(String(36), ForeignKey("architecture_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    relationship_type = Column(String(50), default="imports", index=True)
    raw_import = Column(String(255), nullable=True)
    is_circular = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    analysis = relationship("ArchitectureAnalysis", back_populates="edges")
    project = relationship("Project")
    source_node = relationship("ArchitectureNode", foreign_keys=[source_node_id])
    target_node = relationship("ArchitectureNode", foreign_keys=[target_node_id])
