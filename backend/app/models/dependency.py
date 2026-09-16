from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import generate_uuid, utc_now


# Legacy model preserved for backwards compatibility with Stage 1 analyses table
class Dependency(Base):
    __tablename__ = "dependencies"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(150), nullable=False)
    version = Column(String(50), nullable=True)
    ecosystem = Column(String(30), nullable=False)  # "python", "npm", "maven", etc.
    source_file = Column(String(255), nullable=False)  # requirements.txt, package.json
    
    is_outdated = Column(Boolean, default=False)
    latest_version = Column(String(50), nullable=True)
    is_vulnerable = Column(Boolean, default=False)
    advisory_info = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationship
    analysis = relationship("Analysis", back_populates="dependencies")


# Stage 7 Dedicated Dependency Models
class DependencyAnalysis(Base):
    __tablename__ = "dependency_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(String(36), ForeignKey("project_scans.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(30), default="COMPLETED")  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    total_dependencies = Column(Integer, default=0)
    direct_dependencies = Column(Integer, default=0)
    transitive_dependencies = Column(Integer, default=0)

    current_count = Column(Integer, default=0)
    outdated_count = Column(Integer, default=0)
    vulnerable_count = Column(Integer, default=0)
    unknown_count = Column(Integer, default=0)

    metrics = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="dependency_analyses")
    scan = relationship("ProjectScan")
    dependencies = relationship("ProjectDependency", back_populates="analysis", cascade="all, delete-orphan")
    issues = relationship("DependencyIssue", back_populates="analysis", cascade="all, delete-orphan")


class ProjectDependency(Base):
    __tablename__ = "project_dependencies"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("dependency_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    manifest_file = Column(String(500), nullable=False, index=True)
    ecosystem = Column(String(50), nullable=False, index=True)  # "PyPI", "npm", "Maven"
    name = Column(String(150), nullable=False, index=True)

    declared_version = Column(String(100), nullable=True)
    resolved_version = Column(String(100), nullable=True)
    dependency_type = Column(String(50), default="direct", index=True)  # "direct", "dev", "transitive", "peer"

    latest_version = Column(String(100), nullable=True)
    status = Column(String(30), default="UNKNOWN", index=True)  # "CURRENT", "OUTDATED", "VULNERABLE", "UNKNOWN"
    vulnerability_count = Column(Integer, default=0)

    advisories = Column(JSON, default=list)  # List of {id, severity, affected_versions, fixed_version, summary, reference_url}
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    analysis = relationship("DependencyAnalysis", back_populates="dependencies")
    project = relationship("Project")


class DependencyIssue(Base):
    __tablename__ = "dependency_issues"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("dependency_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_id = Column(String(36), ForeignKey("project_dependencies.id", ondelete="CASCADE"), nullable=True, index=True)

    category = Column(String(50), default="dependency", index=True)
    issue_type = Column(String(50), nullable=False, index=True)  # "vulnerable_dependency", "outdated_dependency"
    severity = Column(String(20), nullable=False, index=True)  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"

    package_name = Column(String(150), nullable=False)
    manifest_file = Column(String(500), nullable=False)
    version = Column(String(100), nullable=False)
    vulnerability_id = Column(String(100), nullable=True)

    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    analysis = relationship("DependencyAnalysis", back_populates="issues")
    project = relationship("Project")
    dependency = relationship("ProjectDependency")
