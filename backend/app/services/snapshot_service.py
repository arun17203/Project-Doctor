import os
import logging
from typing import List, Optional, Tuple, Dict, Any, Set
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan, ProjectFile
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.models.dependency import DependencyAnalysis, ProjectDependency, DependencyIssue
from backend.app.models.architecture import ArchitectureAnalysis, ArchitectureNode, ArchitectureEdge
from backend.app.models.health import HealthAnalysis
from backend.app.models.snapshot import ProjectAnalysisSnapshot
from backend.app.schemas.history import (
    MetricDelta,
    FileDiffSummary,
    VersionComparisonResponse,
)
from backend.app.models.base import utc_now

logger = logging.getLogger(__name__)


def calc_metric_delta(
    metric_name: str,
    from_val: float,
    to_val: float,
    lower_is_better: bool = False,
    unit: str = "points",
) -> MetricDelta:
    """Calculates numeric difference and evaluates improvement direction."""
    diff = round(to_val - from_val, 2)
    if abs(diff) < 0.001:
        direction = "UNCHANGED"
    elif lower_is_better:
        direction = "IMPROVED" if diff < 0 else "WORSENED"
    else:
        direction = "IMPROVED" if diff > 0 else "WORSENED"

    return MetricDelta(
        metric_name=metric_name,
        from_value=round(from_val, 2),
        to_value=round(to_val, 2),
        difference=diff,
        direction=direction,
        unit=unit,
    )


class SnapshotService:
    """Service to create, retrieve, compare, and version historical project analysis snapshots."""

    @staticmethod
    def get_next_version_number(project_id: str, db: Session) -> int:
        """Atomically determine the next sequential version number for a project."""
        max_version = (
            db.query(func.max(ProjectAnalysisSnapshot.version_number))
            .filter(ProjectAnalysisSnapshot.project_id == project_id)
            .scalar()
        )
        return (max_version or 0) + 1

    @classmethod
    def create_snapshot(
        cls,
        project: Project,
        db: Session,
        summary: Optional[str] = None,
    ) -> ProjectAnalysisSnapshot:
        """Create a new historical snapshot record from the latest completed analysis stages."""
        # 1. Fetch latest completed scan
        scan = (
            db.query(ProjectScan)
            .filter(ProjectScan.project_id == project.id, ProjectScan.status == "COMPLETED")
            .order_by(ProjectScan.scanned_at.desc())
            .first()
        )
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create snapshot: Repository scan (Stage 4) has not been completed.",
            )

        # 2. Fetch latest analyses
        quality = (
            db.query(QualityAnalysis)
            .filter(QualityAnalysis.project_id == project.id, QualityAnalysis.status == "COMPLETED")
            .order_by(QualityAnalysis.started_at.desc())
            .first()
        )
        security = (
            db.query(SecurityAnalysis)
            .filter(SecurityAnalysis.project_id == project.id, SecurityAnalysis.status == "COMPLETED")
            .order_by(SecurityAnalysis.started_at.desc())
            .first()
        )
        dependency = (
            db.query(DependencyAnalysis)
            .filter(DependencyAnalysis.project_id == project.id, DependencyAnalysis.status == "COMPLETED")
            .order_by(DependencyAnalysis.started_at.desc())
            .first()
        )
        architecture = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.project_id == project.id, ArchitectureAnalysis.status == "COMPLETED")
            .order_by(ArchitectureAnalysis.started_at.desc())
            .first()
        )
        health = (
            db.query(HealthAnalysis)
            .filter(HealthAnalysis.project_id == project.id)
            .order_by(HealthAnalysis.created_at.desc())
            .first()
        )

        # Determine version number
        version_number = cls.get_next_version_number(project.id, db)

        # Extract telemetry
        total_files = scan.total_files or 0
        total_lines = scan.total_lines or 0

        # Scores default to health or 100
        overall_score = health.overall_score if health else 100.0
        quality_score = health.quality_score if health else (100.0 if not quality else max(0.0, 100.0 - quality.total_issues * 2.5))
        security_score = health.security_score if health else (100.0 if not security else max(0.0, 100.0 - security.total_issues * 5.0))
        dependency_score = health.dependency_score if health else 100.0
        architecture_score = health.architecture_score if health else 100.0
        maintainability_score = health.maintainability_score if health else 100.0
        testing_score = health.testing_score if health else 0.0
        technical_debt_hours = health.technical_debt_hours if health else 0.0

        critical_count = health.critical_count if health else 0
        high_count = health.high_count if health else 0
        medium_count = health.medium_count if health else 0
        low_count = health.low_count if health else 0

        # Granular trend metrics
        crit_sec = 0
        high_sec = 0
        if security:
            crit_sec = db.query(SecurityIssue).filter(SecurityIssue.analysis_id == security.id, SecurityIssue.severity == "CRITICAL").count()
            high_sec = db.query(SecurityIssue).filter(SecurityIssue.analysis_id == security.id, SecurityIssue.severity == "HIGH").count()

        comp_count = 0
        long_func_count = 0
        dup_count = 0
        if quality and quality.metrics:
            m = quality.metrics
            comp_count = db.query(QualityIssue).filter(QualityIssue.analysis_id == quality.id, QualityIssue.issue_type == "high_complexity").count()
            long_func_count = db.query(QualityIssue).filter(QualityIssue.analysis_id == quality.id, QualityIssue.issue_type == "long_function").count()
            dup_count = m.get("duplicate_blocks_count", 0) if isinstance(m, dict) else getattr(m, "duplicate_blocks_count", 0)

        tot_deps = dependency.total_dependencies if dependency else 0
        vuln_deps = dependency.vulnerable_count if dependency else 0
        outdated_deps = dependency.outdated_count if dependency else 0

        arch_nodes = architecture.node_count if architecture else 0
        arch_edges = architecture.edge_count if architecture else 0
        arch_cycles = architecture.cycle_count if architecture else 0

        # File manifest for reliable file diffing
        files = db.query(ProjectFile).filter(ProjectFile.scan_id == scan.id).all()
        file_manifest = [{"path": f.file_path, "lines": f.total_lines or 0} for f in files[:1500]]

        status_str = "COMPLETED" if health else "PARTIAL"

        snapshot = ProjectAnalysisSnapshot(
            project_id=project.id,
            version_number=version_number,
            status=status_str,
            repository_scan_id=scan.id,
            quality_analysis_id=quality.id if quality else None,
            security_analysis_id=security.id if security else None,
            dependency_analysis_id=dependency.id if dependency else None,
            architecture_analysis_id=architecture.id if architecture else None,
            health_analysis_id=health.id if health else None,
            total_files=total_files,
            total_lines=total_lines,
            overall_score=round(overall_score, 1),
            quality_score=round(quality_score, 1),
            security_score=round(security_score, 1),
            dependency_score=round(dependency_score, 1),
            architecture_score=round(architecture_score, 1),
            maintainability_score=round(maintainability_score, 1),
            testing_score=round(testing_score, 1),
            technical_debt_hours=round(technical_debt_hours, 1),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            critical_security_count=crit_sec,
            high_security_count=high_sec,
            high_complexity_count=comp_count,
            long_functions_count=long_func_count,
            duplicate_blocks_count=dup_count,
            total_dependencies=tot_deps,
            vulnerable_dependencies_count=vuln_deps,
            outdated_dependencies_count=outdated_deps,
            architecture_nodes_count=arch_nodes,
            architecture_edges_count=arch_edges,
            architecture_cycles_count=arch_cycles,
            file_manifest=file_manifest,
            summary=summary,
            created_at=utc_now(),
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def get_history(
        project_id: str,
        db: Session,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ProjectAnalysisSnapshot], int]:
        """Fetch paginated snapshots for a project ordered newest first."""
        query = db.query(ProjectAnalysisSnapshot).filter(
            ProjectAnalysisSnapshot.project_id == project_id
        )
        total = query.count()
        snapshots = (
            query.order_by(ProjectAnalysisSnapshot.version_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return snapshots, total

    @staticmethod
    def get_snapshot_by_version(
        project_id: str,
        version_number: int,
        db: Session,
    ) -> Optional[ProjectAnalysisSnapshot]:
        """Fetch specific version snapshot for a project."""
        return (
            db.query(ProjectAnalysisSnapshot)
            .filter(
                ProjectAnalysisSnapshot.project_id == project_id,
                ProjectAnalysisSnapshot.version_number == version_number,
            )
            .first()
        )

    @classmethod
    def compare_snapshots(
        cls,
        from_snapshot: ProjectAnalysisSnapshot,
        to_snapshot: ProjectAnalysisSnapshot,
    ) -> VersionComparisonResponse:
        """Deterministic comparison of two historical snapshot versions."""
        health_delta = calc_metric_delta("Overall Health", from_snapshot.overall_score, to_snapshot.overall_score, lower_is_better=False, unit="points")
        security_delta = calc_metric_delta("Security Score", from_snapshot.security_score, to_snapshot.security_score, lower_is_better=False, unit="points")
        quality_delta = calc_metric_delta("Code Quality Score", from_snapshot.quality_score, to_snapshot.quality_score, lower_is_better=False, unit="points")
        dep_delta = calc_metric_delta("Dependencies Score", from_snapshot.dependency_score, to_snapshot.dependency_score, lower_is_better=False, unit="points")
        arch_delta = calc_metric_delta("Architecture Score", from_snapshot.architecture_score, to_snapshot.architecture_score, lower_is_better=False, unit="points")
        maint_delta = calc_metric_delta("Maintainability Score", from_snapshot.maintainability_score, to_snapshot.maintainability_score, lower_is_better=False, unit="points")
        test_delta = calc_metric_delta("Testing Score", from_snapshot.testing_score, to_snapshot.testing_score, lower_is_better=False, unit="points")

        debt_delta = calc_metric_delta("Technical Debt", from_snapshot.technical_debt_hours, to_snapshot.technical_debt_hours, lower_is_better=True, unit="hours")

        crit_delta = calc_metric_delta("Critical Issues", from_snapshot.critical_count, to_snapshot.critical_count, lower_is_better=True, unit="issues")
        high_delta = calc_metric_delta("High Issues", from_snapshot.high_count, to_snapshot.high_count, lower_is_better=True, unit="issues")
        med_delta = calc_metric_delta("Medium Issues", from_snapshot.medium_count, to_snapshot.medium_count, lower_is_better=True, unit="issues")
        low_delta = calc_metric_delta("Low Issues", from_snapshot.low_count, to_snapshot.low_count, lower_is_better=True, unit="issues")

        from_tot_issues = from_snapshot.critical_count + from_snapshot.high_count + from_snapshot.medium_count + from_snapshot.low_count
        to_tot_issues = to_snapshot.critical_count + to_snapshot.high_count + to_snapshot.medium_count + to_snapshot.low_count
        tot_issues_delta = calc_metric_delta("Total Issues", from_tot_issues, to_tot_issues, lower_is_better=True, unit="issues")

        vuln_delta = calc_metric_delta("Vulnerable Dependencies", from_snapshot.vulnerable_dependencies_count, to_snapshot.vulnerable_dependencies_count, lower_is_better=True, unit="issues")
        outdated_delta = calc_metric_delta("Outdated Dependencies", from_snapshot.outdated_dependencies_count, to_snapshot.outdated_dependencies_count, lower_is_better=True, unit="issues")
        comp_delta = calc_metric_delta("High Complexity Functions", from_snapshot.high_complexity_count, to_snapshot.high_complexity_count, lower_is_better=True, unit="issues")
        cycles_delta = calc_metric_delta("Architecture Cycles", from_snapshot.architecture_cycles_count, to_snapshot.architecture_cycles_count, lower_is_better=True, unit="cycles")

        # Compare File Manifests
        files_from: Dict[str, int] = {f["path"]: f.get("lines", 0) for f in (from_snapshot.file_manifest or [])}
        files_to: Dict[str, int] = {f["path"]: f.get("lines", 0) for f in (to_snapshot.file_manifest or [])}

        set_from = set(files_from.keys())
        set_to = set(files_to.keys())

        added = sorted(list(set_to - set_from))
        removed = sorted(list(set_from - set_to))
        common = set_from & set_to
        modified = [p for p in common if files_from[p] != files_to[p]]

        file_diff = FileDiffSummary(
            files_added=len(added),
            files_removed=len(removed),
            files_modified=len(modified),
            total_files_before=len(files_from),
            total_files_after=len(files_to),
            sample_added=added[:5],
            sample_removed=removed[:5],
        )

        # Generate Deterministic Change Summary
        summary_paragraphs = []
        headline = "PROJECT HEALTH STABLE"

        if health_delta.difference > 0:
            headline = f"PROJECT IMPROVED (+{health_delta.difference:.0f} pts)"
            summary_paragraphs.append(f"Overall project health improved by {health_delta.difference:.0f} points (from {from_snapshot.overall_score:.0f} to {to_snapshot.overall_score:.0f}).")
        elif health_delta.difference < 0:
            headline = f"PROJECT REGRESSED ({health_delta.difference:.0f} pts)"
            summary_paragraphs.append(f"Overall project health declined by {abs(health_delta.difference):.0f} points (from {from_snapshot.overall_score:.0f} to {to_snapshot.overall_score:.0f}).")
        else:
            summary_paragraphs.append(f"Overall project health remained steady at {to_snapshot.overall_score:.0f} points.")

        # Security
        if security_delta.difference != 0:
            word = "improved" if security_delta.difference > 0 else "declined"
            summary_paragraphs.append(f"Security score {word} by {abs(security_delta.difference):.0f} points ({from_snapshot.security_score:.0f} → {to_snapshot.security_score:.0f}).")

        # Critical issues
        if crit_delta.difference != 0:
            word = "decreased" if crit_delta.difference < 0 else "increased"
            summary_paragraphs.append(f"Critical issues {word} from {from_snapshot.critical_count} to {to_snapshot.critical_count} ({int(crit_delta.difference):+d}).")

        # Tech debt
        if debt_delta.difference != 0:
            word = "decreased" if debt_delta.difference < 0 else "increased"
            summary_paragraphs.append(f"Estimated technical debt remediation effort {word} by {abs(debt_delta.difference):.1f} hours ({from_snapshot.technical_debt_hours:.1f}h → {to_snapshot.technical_debt_hours:.1f}h).")

        # Files
        if len(added) > 0 or len(removed) > 0:
            summary_paragraphs.append(f"Repository file changes: {len(added)} added, {len(removed)} removed, {len(modified)} modified.")

        return VersionComparisonResponse(
            project_id=to_snapshot.project_id,
            from_version=from_snapshot.version_number,
            to_version=to_snapshot.version_number,
            from_created_at=from_snapshot.created_at,
            to_created_at=to_snapshot.created_at,
            health_delta=health_delta,
            security_delta=security_delta,
            quality_delta=quality_delta,
            dependency_delta=dep_delta,
            architecture_delta=arch_delta,
            maintainability_delta=maint_delta,
            testing_delta=test_delta,
            technical_debt_delta=debt_delta,
            critical_issues_delta=crit_delta,
            high_issues_delta=high_delta,
            medium_issues_delta=med_delta,
            low_issues_delta=low_delta,
            total_issues_delta=tot_issues_delta,
            vulnerable_deps_delta=vuln_delta,
            outdated_deps_delta=outdated_delta,
            complexity_delta=comp_delta,
            cycles_delta=cycles_delta,
            file_diff=file_diff,
            summary_headline=headline,
            summary_text=" ".join(summary_paragraphs),
        )

    @classmethod
    def run_full_analysis(
        cls,
        project: Project,
        db: Session,
        summary: Optional[str] = None,
    ) -> ProjectAnalysisSnapshot:
        """Triggers all analysis pipeline stages (Stages 4 through 9) and records a new historical snapshot version."""
        if project.status != "READY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project is not ready for analysis. Current status is '{project.status}'.",
            )

        if not project.storage_path or not os.path.exists(project.storage_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository storage path is missing or inaccessible on disk.",
            )

        # 1. Repository Scan
        from backend.app.analyzers.scanner import scan_repository
        scan_data = scan_repository(project.storage_path)

        scan = ProjectScan(
            project_id=project.id,
            total_files=scan_data["total_files"],
            total_directories=scan_data.get("total_directories", 0),
            total_lines=scan_data["total_lines"],
            total_code_lines=scan_data.get("total_code_lines", 0),
            total_blank_lines=scan_data.get("total_blank_lines", 0),
            total_comment_lines=scan_data.get("total_comment_lines", 0),
            test_files_count=scan_data.get("test_files_count", 0),
            config_files_count=scan_data.get("config_files_count", 0),
            doc_files_count=scan_data.get("doc_files_count", 0),
            languages_summary=scan_data.get("languages_summary", {}),
            categories_summary=scan_data.get("categories_summary", {}),
            directory_tree=scan_data.get("directory_tree", {}),
            status="COMPLETED",
            scanned_at=utc_now(),
        )
        db.add(scan)
        db.flush()

        file_entities = []
        for f in scan_data.get("files", []):
            file_entities.append(
                ProjectFile(
                    scan_id=scan.id,
                    project_id=project.id,
                    file_path=f["file_path"],
                    file_name=f["file_name"],
                    extension=f["extension"],
                    language=f["language"],
                    category=f["category"],
                    size_bytes=f["size_bytes"],
                    total_lines=f["total_lines"],
                    code_lines=f["code_lines"],
                    blank_lines=f["blank_lines"],
                    comment_lines=f["comment_lines"],
                    is_binary=f.get("is_binary", False),
                    is_test=f.get("is_test", False),
                    is_config=f.get("is_config", False),
                    is_doc=f.get("is_doc", False),
                    is_skipped=f.get("is_skipped", False),
                )
            )
        if file_entities:
            db.add_all(file_entities)
        db.flush()

        # 2. Quality Analysis
        from backend.app.analyzers.quality_engine import run_code_quality_analysis
        quality_analysis = QualityAnalysis(
            project_id=project.id,
            scan_id=scan.id,
            status="IN_PROGRESS",
            started_at=utc_now(),
        )
        db.add(quality_analysis)
        db.flush()
        quality_results = run_code_quality_analysis(project, scan, db)
        quality_analysis.status = "COMPLETED"
        quality_analysis.completed_at = utc_now()
        quality_analysis.total_issues = quality_results["total_issues"]
        quality_analysis.critical_count = quality_results["critical_count"]
        quality_analysis.high_count = quality_results["high_count"]
        quality_analysis.medium_count = quality_results["medium_count"]
        quality_analysis.low_count = quality_results["low_count"]
        quality_analysis.metrics = quality_results["metrics"]

        quality_issues_to_create = []
        for iss in quality_results.get("issues", []):
            quality_issues_to_create.append(
                QualityIssue(
                    analysis_id=quality_analysis.id,
                    project_id=project.id,
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    file_path=iss["file_path"],
                    line_number=iss["line_number"],
                    end_line=iss.get("end_line"),
                    symbol_name=iss.get("symbol_name"),
                    message=iss["message"],
                    description=iss["description"],
                    evidence=iss.get("evidence"),
                    recommendation=iss.get("recommendation"),
                )
            )
        if quality_issues_to_create:
            db.add_all(quality_issues_to_create)
        db.flush()

        # 3. Security Audit
        from backend.app.analyzers.security.engine import run_security_analysis
        security_analysis = SecurityAnalysis(
            project_id=project.id,
            scan_id=scan.id,
            status="IN_PROGRESS",
            started_at=utc_now(),
        )
        db.add(security_analysis)
        db.flush()
        sec_results = run_security_analysis(project, scan, db)
        security_analysis.status = "COMPLETED"
        security_analysis.completed_at = utc_now()
        security_analysis.total_issues = sec_results["total_issues"]
        security_analysis.critical_count = sec_results["critical_count"]
        security_analysis.high_count = sec_results["high_count"]
        security_analysis.medium_count = sec_results["medium_count"]
        security_analysis.low_count = sec_results["low_count"]
        security_analysis.rules_applied = sec_results.get("rules_applied", 0)
        security_analysis.metrics = sec_results.get("metrics", {})

        sec_issues_to_create = []
        for iss in sec_results.get("issues", []):
            sec_issues_to_create.append(
                SecurityIssue(
                    analysis_id=security_analysis.id,
                    project_id=project.id,
                    category=iss.get("category", "security"),
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    confidence=iss.get("confidence", "HIGH"),
                    file_path=iss["file_path"],
                    line_number=iss["line_number"],
                    end_line=iss.get("end_line"),
                    symbol_name=iss.get("symbol_name"),
                    message=iss["message"],
                    description=iss["description"],
                    evidence=iss.get("evidence"),
                    recommendation=iss.get("recommendation"),
                )
            )
        if sec_issues_to_create:
            db.add_all(sec_issues_to_create)
        db.flush()

        # 4. Dependency Analysis
        from backend.app.analyzers.dependency.engine import run_dependency_analysis
        dep_analysis = DependencyAnalysis(
            project_id=project.id,
            scan_id=scan.id,
            status="IN_PROGRESS",
            started_at=utc_now(),
        )
        db.add(dep_analysis)
        db.flush()
        dep_results = run_dependency_analysis(project, scan, db)
        dep_analysis.status = "COMPLETED"
        dep_analysis.completed_at = utc_now()
        dep_analysis.total_dependencies = dep_results.get("total_dependencies", 0)
        dep_analysis.direct_dependencies = dep_results.get("direct_dependencies", 0)
        dep_analysis.transitive_dependencies = dep_results.get("transitive_dependencies", 0)
        dep_analysis.current_count = dep_results.get("current_count", 0)
        dep_analysis.outdated_count = dep_results.get("outdated_count", 0)
        dep_analysis.vulnerable_count = dep_results.get("vulnerable_count", 0)
        dep_analysis.unknown_count = dep_results.get("unknown_count", 0)
        dep_analysis.metrics = dep_results.get("metrics", {})

        dep_models = []
        dep_id_map = {}
        for d in dep_results.get("dependencies", []):
            dep_obj = ProjectDependency(
                analysis_id=dep_analysis.id,
                project_id=project.id,
                manifest_file=d["manifest_file"],
                ecosystem=d["ecosystem"],
                name=d["name"],
                declared_version=d.get("declared_version"),
                resolved_version=d.get("resolved_version"),
                dependency_type=d.get("dependency_type", "direct"),
                latest_version=d.get("latest_version"),
                status=d.get("status", "UNKNOWN"),
                vulnerability_count=d.get("vulnerability_count", 0),
                advisories=d.get("advisories", []),
            )
            dep_models.append(dep_obj)

        if dep_models:
            db.add_all(dep_models)
            db.flush()
            for dep_obj in dep_models:
                dep_id_map[(dep_obj.name, dep_obj.manifest_file)] = dep_obj.id

        dep_issues = []
        for iss in dep_results.get("issues", []):
            matched_dep_id = dep_id_map.get((iss["package_name"], iss["manifest_file"]))
            dep_issues.append(
                DependencyIssue(
                    analysis_id=dep_analysis.id,
                    project_id=project.id,
                    dependency_id=matched_dep_id,
                    category=iss.get("category", "dependency"),
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    package_name=iss["package_name"],
                    manifest_file=iss["manifest_file"],
                    version=iss["version"],
                    vulnerability_id=iss.get("vulnerability_id"),
                    description=iss.get("description", ""),
                    recommendation=iss.get("recommendation"),
                )
            )
        if dep_issues:
            db.add_all(dep_issues)
        db.flush()

        # 5. Architecture Analysis
        from backend.app.analyzers.architecture.engine import run_architecture_analysis
        arch_analysis = ArchitectureAnalysis(
            project_id=project.id,
            scan_id=scan.id,
            status="IN_PROGRESS",
            started_at=utc_now(),
        )
        db.add(arch_analysis)
        db.flush()
        arch_results = run_architecture_analysis(project, scan, db)
        arch_analysis.status = "COMPLETED"
        arch_analysis.completed_at = utc_now()
        arch_analysis.node_count = arch_results.get("node_count", 0)
        arch_analysis.edge_count = arch_results.get("edge_count", 0)
        arch_analysis.cycle_count = arch_results.get("cycle_count", 0)
        arch_analysis.metrics = arch_results.get("metrics", {})

        node_models = []
        path_to_node_id = {}
        for n in arch_results.get("nodes", []):
            node_obj = ArchitectureNode(
                analysis_id=arch_analysis.id,
                project_id=project.id,
                file_path=n["file_path"],
                name=n["name"],
                language=n["language"],
                layer=n["layer"],
                node_type=n.get("node_type", "file"),
                directory=n.get("directory", ""),
                metrics=n.get("metrics", {}),
            )
            node_models.append(node_obj)
        if node_models:
            db.add_all(node_models)
            db.flush()
            for node_obj in node_models:
                path_to_node_id[node_obj.file_path] = node_obj.id

        edge_models = []
        for e in arch_results.get("edges", []):
            src_id = path_to_node_id.get(e["source"])
            tgt_id = path_to_node_id.get(e["target"])
            if src_id and tgt_id:
                edge_models.append(
                    ArchitectureEdge(
                        analysis_id=arch_analysis.id,
                        project_id=project.id,
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        relationship_type=e.get("relationship_type", "imports"),
                        raw_import=e.get("raw_import"),
                        is_circular=e.get("is_circular", False),
                    )
                )
        if edge_models:
            db.add_all(edge_models)
        db.flush()

        # 6. Health Analysis
        from backend.app.analyzers.health.engine import HealthEngine
        health_engine = HealthEngine(db)
        health_engine.analyze_project_health(project)

        db.commit()

        # 7. Create and return the new snapshot version
        snapshot = cls.create_snapshot(project, db, summary=summary)
        return snapshot
