from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


class ProjectScan(Base):
    __tablename__ = "project_scans"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Counts & Metrics
    total_files = Column(Integer, default=0)
    total_directories = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    total_code_lines = Column(Integer, default=0)
    total_blank_lines = Column(Integer, default=0)
    total_comment_lines = Column(Integer, default=0)
    
    # Categorization tallies
    test_files_count = Column(Integer, default=0)
    config_files_count = Column(Integer, default=0)
    doc_files_count = Column(Integer, default=0)

    # Summaries (Stored as JSON)
    languages_summary = Column(JSON, default=dict)
    # e.g.: {"Python": {"files": 4, "lines": 420, "code_lines": 350, "blank_lines": 40, "comment_lines": 30, "percentage": 85.0}}
    categories_summary = Column(JSON, default=dict)
    # e.g.: {"Source Code": 6, "Tests": 2, "Configuration": 3, "Documentation": 1, "Assets": 0, "Other": 0}

    # Full hierarchical directory tree structure
    directory_tree = Column(JSON, default=dict)

    status = Column(String(30), default="COMPLETED")  # COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    scanned_at = Column(DateTime, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="scans")
    files = relationship("ProjectFile", back_populates="scan", cascade="all, delete-orphan")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    scan_id = Column(String(36), ForeignKey("project_scans.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    file_path = Column(String(500), nullable=False)  # Relative to project root, e.g. "src/main.py"
    file_name = Column(String(255), nullable=False)
    extension = Column(String(50), nullable=False)
    language = Column(String(50), default="Other")
    category = Column(String(50), default="Other")  # Source Code, Tests, Configuration, Documentation, Assets, Other

    size_bytes = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    code_lines = Column(Integer, default=0)
    blank_lines = Column(Integer, default=0)
    comment_lines = Column(Integer, default=0)

    is_binary = Column(Boolean, default=False)
    is_test = Column(Boolean, default=False)
    is_config = Column(Boolean, default=False)
    is_doc = Column(Boolean, default=False)
    is_skipped = Column(Boolean, default=False)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    scan = relationship("ProjectScan", back_populates="files")
    project = relationship("Project", back_populates="files")
