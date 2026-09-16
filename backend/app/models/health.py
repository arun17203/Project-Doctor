from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class HealthAnalysis(Base):
    __tablename__ = "health_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    repository_scan_id = Column(String(36), ForeignKey("project_scans.id", ondelete="CASCADE"), nullable=False, index=True)

    quality_analysis_id = Column(String(36), ForeignKey("quality_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    security_analysis_id = Column(String(36), ForeignKey("security_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    dependency_analysis_id = Column(String(36), ForeignKey("dependency_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    architecture_analysis_id = Column(String(36), ForeignKey("architecture_analyses.id", ondelete="SET NULL"), nullable=True, index=True)

    # Health & Dimension Scores (0 - 100)
    overall_score = Column(Float, nullable=False, default=100.0)
    quality_score = Column(Float, nullable=False, default=100.0)
    security_score = Column(Float, nullable=False, default=100.0)
    dependency_score = Column(Float, nullable=False, default=100.0)
    architecture_score = Column(Float, nullable=False, default=100.0)
    maintainability_score = Column(Float, nullable=False, default=100.0)
    testing_score = Column(Float, nullable=False, default=0.0)

    # Technical Debt (Estimated remediation effort in hours)
    technical_debt_hours = Column(Float, nullable=False, default=0.0)

    # Issue Severity Tallies
    critical_count = Column(Integer, nullable=False, default=0)
    high_count = Column(Integer, nullable=False, default=0)
    medium_count = Column(Integer, nullable=False, default=0)
    low_count = Column(Integer, nullable=False, default=0)

    # Qualitative Status (Excellent, Good, Fair, Needs Attention, Critical)
    status = Column(String(30), nullable=False, default="Good")

    # Diagnostic Payloads (Stored as JSON)
    explanations = Column(JSON, default=dict)  # {"why": [...], "quality": [...], "security": [...], ...}
    debt_breakdown = Column(JSON, default=dict)  # {"quality_hours": 12, "security_hours": 8, "dependency_hours": 5, "architecture_hours": 4, "total_hours": 29}
    fix_first = Column(JSON, default=list)  # Top 5-10 prioritized actionable issues
    weights_used = Column(JSON, default=dict)  # {"security": 0.30, "quality": 0.25, "maintainability": 0.20, "dependencies": 0.15, "architecture": 0.10}

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="health_analyses")
    scan = relationship("ProjectScan")
    quality_analysis = relationship("QualityAnalysis")
    security_analysis = relationship("SecurityAnalysis")
    dependency_analysis = relationship("DependencyAnalysis")
    architecture_analysis = relationship("ArchitectureAnalysis")
