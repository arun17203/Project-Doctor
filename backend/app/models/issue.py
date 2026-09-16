from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class Issue(Base):
    __tablename__ = "issues"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Classification
    type = Column(String(30), nullable=False)  # "code_quality", "security", "dependency", "architecture", "maintainability"
    category = Column(String(60), nullable=False)  # "Complexity", "Hardcoded Secret", "Vulnerability", "Duplicate Code", etc.
    severity = Column(String(20), nullable=False, index=True)  # "critical", "high", "medium", "low"
    rule_id = Column(String(80), nullable=False)  # e.g., "SEC-001", "QUAL-002"

    # Context & Location
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer, nullable=True)
    end_line_number = Column(Integer, nullable=True)
    function_name = Column(String(120), nullable=True)

    # Details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)  # Code snippet with secrets safely masked
    suggested_fix = Column(Text, nullable=True)
    
    # Pre-computed or Cached AI Explanation
    ai_explanation = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationship
    analysis = relationship("Analysis", back_populates="issues")
