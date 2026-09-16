from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1)
    status = Column(String(40), default="pending")  
    # pending, scanning, analyzing_quality, checking_security, analyzing_deps, building_arch, completed, failed
    current_stage = Column(String(100), default="Queued")
    progress_percentage = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Health & Category Scores (0-100)
    health_score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    security_score = Column(Float, default=0.0)
    maintainability_score = Column(Float, default=0.0)
    architecture_score = Column(Float, default=0.0)
    testing_score = Column(Float, default=0.0)

    # Technical Debt
    technical_debt_hours = Column(Float, default=0.0)

    # Repository Scanner Metrics
    total_files = Column(Integer, default=0)
    total_lines_of_code = Column(Integer, default=0)
    total_code_lines = Column(Integer, default=0)
    total_comment_lines = Column(Integer, default=0)
    total_blank_lines = Column(Integer, default=0)
    total_dependencies = Column(Integer, default=0)
    total_test_files = Column(Integer, default=0)
    total_config_files = Column(Integer, default=0)
    languages_summary = Column(JSON, default=dict)  # {"Python": {"files": 12, "loc": 1400}, ...}

    # Issue Counts Summary
    critical_issues_count = Column(Integer, default=0)
    high_issues_count = Column(Integer, default=0)
    medium_issues_count = Column(Integer, default=0)
    low_issues_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="analyses")
    issues = relationship("Issue", back_populates="analysis", cascade="all, delete-orphan")
    dependencies = relationship("Dependency", back_populates="analysis", cascade="all, delete-orphan")
