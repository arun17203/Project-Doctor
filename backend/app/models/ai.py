from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class AIExplanation(Base):
    __tablename__ = "ai_explanations"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    issue_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    issue_category = Column(String(50), nullable=False, index=True)  # "quality", "security", "dependency", "architecture"
    issue_type = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), default="google-gemini")
    model = Column(String(50), default="gemini-2.5-flash")

    summary = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=False)
    potential_impact = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    priority = Column(String(30), nullable=False)
    developer_action = Column(Text, nullable=False)

    evidence_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="ai_explanations")
