from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class QualityAnalysis(Base):
    __tablename__ = "quality_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(String(36), ForeignKey("project_scans.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(30), default="COMPLETED")  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    # Issue Counts
    total_issues = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)

    # Maintainability Metrics (Stored as JSON)
    metrics = Column(JSON, default=dict)

    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="quality_analyses")
    scan = relationship("ProjectScan")
    issues = relationship("QualityIssue", back_populates="analysis", cascade="all, delete-orphan")


class QualityIssue(Base):
    __tablename__ = "quality_issues"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("quality_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    issue_type = Column(String(50), nullable=False, index=True)
    # Types: "high_complexity", "long_function", "deep_nesting", "duplicate_code", "unused_import", "todo_comment"

    severity = Column(String(20), nullable=False, index=True)
    # Levels: "CRITICAL", "HIGH", "MEDIUM", "LOW"

    file_path = Column(String(500), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=True)
    symbol_name = Column(String(150), nullable=True)

    message = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    analysis = relationship("QualityAnalysis", back_populates="issues")
    project = relationship("Project")
