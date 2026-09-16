from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class ProjectAnalysisSnapshot(Base):
    __tablename__ = "project_analysis_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="COMPLETED")  # COMPLETED, PARTIAL, FAILED

    # Foreign Keys to underlying analyzer runs
    repository_scan_id = Column(String(36), ForeignKey("project_scans.id", ondelete="CASCADE"), nullable=True, index=True)
    quality_analysis_id = Column(String(36), ForeignKey("quality_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    security_analysis_id = Column(String(36), ForeignKey("security_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    dependency_analysis_id = Column(String(36), ForeignKey("dependency_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    architecture_analysis_id = Column(String(36), ForeignKey("architecture_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    health_analysis_id = Column(String(36), ForeignKey("health_analyses.id", ondelete="SET NULL"), nullable=True, index=True)

    # Repository size metrics
    total_files = Column(Integer, nullable=False, default=0)
    total_lines = Column(Integer, nullable=False, default=0)

    # Core health & dimensional scores (0 - 100)
    overall_score = Column(Float, nullable=False, default=100.0)
    quality_score = Column(Float, nullable=False, default=100.0)
    security_score = Column(Float, nullable=False, default=100.0)
    dependency_score = Column(Float, nullable=False, default=100.0)
    architecture_score = Column(Float, nullable=False, default=100.0)
    maintainability_score = Column(Float, nullable=False, default=100.0)
    testing_score = Column(Float, nullable=False, default=0.0)

    # Technical Debt (estimated remediation hours)
    technical_debt_hours = Column(Float, nullable=False, default=0.0)

    # Total issue tallies by severity
    critical_count = Column(Integer, nullable=False, default=0)
    high_count = Column(Integer, nullable=False, default=0)
    medium_count = Column(Integer, nullable=False, default=0)
    low_count = Column(Integer, nullable=False, default=0)

    # Granular trend telemetry
    critical_security_count = Column(Integer, nullable=False, default=0)
    high_security_count = Column(Integer, nullable=False, default=0)
    high_complexity_count = Column(Integer, nullable=False, default=0)
    long_functions_count = Column(Integer, nullable=False, default=0)
    duplicate_blocks_count = Column(Integer, nullable=False, default=0)
    total_dependencies = Column(Integer, nullable=False, default=0)
    vulnerable_dependencies_count = Column(Integer, nullable=False, default=0)
    outdated_dependencies_count = Column(Integer, nullable=False, default=0)
    architecture_nodes_count = Column(Integer, nullable=False, default=0)
    architecture_edges_count = Column(Integer, nullable=False, default=0)
    architecture_cycles_count = Column(Integer, nullable=False, default=0)

    # File manifest for reliable file diffing between versions
    file_manifest = Column(JSON, default=list)  # [{"path": "auth/jwt.py", "lines": 45}, ...]
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    project = relationship("Project", back_populates="snapshots")
    scan = relationship("ProjectScan")
    quality_analysis = relationship("QualityAnalysis")
    security_analysis = relationship("SecurityAnalysis")
    dependency_analysis = relationship("DependencyAnalysis")
    architecture_analysis = relationship("ArchitectureAnalysis")
    health_analysis = relationship("HealthAnalysis")
