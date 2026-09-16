from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(20), nullable=False)  # "zip" or "github"
    source_url = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    storage_path = Column(String(500), nullable=True)  # Path to sandboxed extracted code
    status = Column(String(30), default="CREATED")  # CREATED, UPLOADING, CLONING, PROCESSING, READY, FAILED
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    owner = relationship("User", back_populates="projects")
    scans = relationship("ProjectScan", back_populates="project", cascade="all, delete-orphan", order_by="desc(ProjectScan.scanned_at)")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    quality_analyses = relationship("QualityAnalysis", back_populates="project", cascade="all, delete-orphan", order_by="desc(QualityAnalysis.started_at)")
    security_analyses = relationship("SecurityAnalysis", back_populates="project", cascade="all, delete-orphan", order_by="desc(SecurityAnalysis.started_at)")
    dependency_analyses = relationship("DependencyAnalysis", back_populates="project", cascade="all, delete-orphan", order_by="desc(DependencyAnalysis.started_at)")
    architecture_analyses = relationship("ArchitectureAnalysis", back_populates="project", cascade="all, delete-orphan", order_by="desc(ArchitectureAnalysis.started_at)")
    health_analyses = relationship("HealthAnalysis", back_populates="project", cascade="all, delete-orphan", order_by="desc(HealthAnalysis.created_at)")
    ai_explanations = relationship("AIExplanation", back_populates="project", cascade="all, delete-orphan", order_by="desc(AIExplanation.created_at)")
    analyses = relationship("Analysis", back_populates="project", cascade="all, delete-orphan", order_by="desc(Analysis.created_at)")
    ai_conversations = relationship("AIConversation", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("ProjectAnalysisSnapshot", back_populates="project", cascade="all, delete-orphan", order_by="desc(ProjectAnalysisSnapshot.version_number)")
