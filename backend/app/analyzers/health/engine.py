from typing import Tuple, List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.models.dependency import DependencyAnalysis, DependencyIssue
from backend.app.models.architecture import ArchitectureAnalysis
from backend.app.models.health import HealthAnalysis

from backend.app.analyzers.health.calculator import (
    calculate_quality_score,
    calculate_security_score,
    calculate_dependency_score,
    calculate_architecture_score,
    calculate_maintainability_score,
    calculate_testing_score,
    calculate_overall_health_score,
    interpret_health_status,
    DEFAULT_WEIGHTS,
)
from backend.app.analyzers.health.debt import calculate_technical_debt
from backend.app.analyzers.health.priorities import generate_fix_first_list
from backend.app.analyzers.health.explainer import generate_score_explanations


class HealthEngine:
    """Core Health and Technical Debt Diagnostic Engine for Project Doctor.
    Takes real results from Stages 4, 5, 6, 7, and 8 to calculate deterministic
    overall project health scores, dimensions, technical debt, and priority actions.
    """

    def __init__(self, db: Session):
        self.db = db

    def check_prerequisites(self, project: Project) -> Tuple[bool, Optional[str]]:
        """Verify that all required upstream analysis stages (Stages 4-8) exist and are completed."""
        # 1. Stage 4: Repository Scan
        scan = self.db.query(ProjectScan).filter(
            ProjectScan.project_id == project.id,
            ProjectScan.status == "COMPLETED"
        ).order_by(ProjectScan.scanned_at.desc()).first()
        if not scan:
            return False, "Repository Scan (Stage 4) must be completed before Health Analysis can run."

        # 2. Stage 5: Quality Analysis
        quality = self.db.query(QualityAnalysis).filter(
            QualityAnalysis.project_id == project.id,
            QualityAnalysis.status == "COMPLETED"
        ).order_by(QualityAnalysis.started_at.desc()).first()
        if not quality:
            return False, "Code Quality Analysis (Stage 5) must be completed before Health Analysis can run."

        # 3. Stage 6: Security Audit
        security = self.db.query(SecurityAnalysis).filter(
            SecurityAnalysis.project_id == project.id,
            SecurityAnalysis.status == "COMPLETED"
        ).order_by(SecurityAnalysis.started_at.desc()).first()
        if not security:
            return False, "Security Audit (Stage 6) must be completed before Health Analysis can run."

        # 4. Stage 7: Dependency Analysis
        dependency = self.db.query(DependencyAnalysis).filter(
            DependencyAnalysis.project_id == project.id,
            DependencyAnalysis.status == "COMPLETED"
        ).order_by(DependencyAnalysis.started_at.desc()).first()
        if not dependency:
            return False, "Dependency Analysis (Stage 7) must be completed before Health Analysis can run."

        # 5. Stage 8: Architecture Analysis
        architecture = self.db.query(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.project_id == project.id,
            ArchitectureAnalysis.status == "COMPLETED"
        ).order_by(ArchitectureAnalysis.started_at.desc()).first()
        if not architecture:
            return False, "Architecture Analysis (Stage 8) must be completed before Health Analysis can run."

        return True, None

    def analyze_project_health(self, project: Project) -> HealthAnalysis:
        """Execute full health diagnosis across stored results and persist record."""
        # Retrieve latest completed stages
        scan = self.db.query(ProjectScan).filter(
            ProjectScan.project_id == project.id,
            ProjectScan.status == "COMPLETED"
        ).order_by(ProjectScan.scanned_at.desc()).first()

        quality = self.db.query(QualityAnalysis).filter(
            QualityAnalysis.project_id == project.id,
            QualityAnalysis.status == "COMPLETED"
        ).order_by(QualityAnalysis.started_at.desc()).first()

        security = self.db.query(SecurityAnalysis).filter(
            SecurityAnalysis.project_id == project.id,
            SecurityAnalysis.status == "COMPLETED"
        ).order_by(SecurityAnalysis.started_at.desc()).first()

        dependency = self.db.query(DependencyAnalysis).filter(
            DependencyAnalysis.project_id == project.id,
            DependencyAnalysis.status == "COMPLETED"
        ).order_by(DependencyAnalysis.started_at.desc()).first()

        architecture = self.db.query(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.project_id == project.id,
            ArchitectureAnalysis.status == "COMPLETED"
        ).order_by(ArchitectureAnalysis.started_at.desc()).first()

        if not (scan and quality and security and dependency and architecture):
            raise ValueError("All Stage 4-8 analyses must be completed before running health analysis.")

        # Ingest issues
        quality_issues = self.db.query(QualityIssue).filter(QualityIssue.analysis_id == quality.id).all()
        security_issues = self.db.query(SecurityIssue).filter(SecurityIssue.analysis_id == security.id).all()
        dependency_issues = self.db.query(DependencyIssue).filter(DependencyIssue.analysis_id == dependency.id).all()
        circular_cycles = architecture.metrics.get("cycles", []) if architecture.metrics else []

        # 1. Quality Score
        quality_score = calculate_quality_score(
            critical=quality.critical_count,
            high=quality.high_count,
            medium=quality.medium_count,
            low=quality.low_count,
        )

        # 2. Security Score
        security_score = calculate_security_score(
            critical=security.critical_count,
            high=security.high_count,
            medium=security.medium_count,
            low=security.low_count,
        )

        # 3. Dependency Score
        dependency_score = calculate_dependency_score(
            vulnerable_count=dependency.vulnerable_count,
            outdated_count=dependency.outdated_count,
            unknown_count=dependency.unknown_count,
        )

        # 4. Architecture Score
        architecture_score = calculate_architecture_score(
            circular_cycles_count=architecture.cycle_count,
        )

        # 5. Maintainability Score
        maintainability_score = calculate_maintainability_score(
            quality_metrics=quality.metrics or {},
            total_code_lines=scan.total_code_lines or 0,
            total_files=scan.total_files or 0,
        )

        # 6. Testing Health Score
        testing_score = calculate_testing_score(
            test_files_count=scan.test_files_count or 0,
            total_files=scan.total_files or 0,
            config_files_count=scan.config_files_count or 0,
            doc_files_count=scan.doc_files_count or 0,
        )

        # 7. Overall Health Score & Qualitative Status
        overall_score = calculate_overall_health_score(
            security_score=security_score,
            quality_score=quality_score,
            maintainability_score=maintainability_score,
            dependency_score=dependency_score,
            architecture_score=architecture_score,
            weights=DEFAULT_WEIGHTS,
        )
        status = interpret_health_status(overall_score)

        # 8. Technical Debt Hours
        debt_breakdown = calculate_technical_debt(
            quality_issues=quality_issues,
            security_issues=security_issues,
            vulnerable_deps_count=dependency.vulnerable_count,
            outdated_deps_count=dependency.outdated_count,
            circular_cycles_count=architecture.cycle_count,
        )

        # 9. Priority "Fix First" Action List
        fix_first = generate_fix_first_list(
            security_issues=security_issues,
            quality_issues=quality_issues,
            dependency_issues=dependency_issues,
            circular_cycles=circular_cycles,
            limit=10,
        )

        # 10. Diagnostic Explanations ("Why [Score]?")
        explanations = generate_score_explanations(
            overall_score=overall_score,
            status=status,
            quality_score=quality_score,
            security_score=security_score,
            dependency_score=dependency_score,
            architecture_score=architecture_score,
            maintainability_score=maintainability_score,
            testing_score=testing_score,
            quality_counts={
                "critical": quality.critical_count,
                "high": quality.high_count,
                "medium": quality.medium_count,
                "low": quality.low_count,
            },
            security_counts={
                "critical": security.critical_count,
                "high": security.high_count,
                "medium": security.medium_count,
                "low": security.low_count,
            },
            dependency_counts={
                "vulnerable": dependency.vulnerable_count,
                "outdated": dependency.outdated_count,
                "unknown": dependency.unknown_count,
            },
            circular_cycles_count=architecture.cycle_count,
        )

        # Issue Severity Totals
        critical_count = quality.critical_count + security.critical_count
        high_count = quality.high_count + security.high_count
        medium_count = quality.medium_count + security.medium_count
        low_count = quality.low_count + security.low_count

        # Persist new HealthAnalysis record (preserving history)
        health_record = HealthAnalysis(
            project_id=project.id,
            repository_scan_id=scan.id,
            quality_analysis_id=quality.id,
            security_analysis_id=security.id,
            dependency_analysis_id=dependency.id,
            architecture_analysis_id=architecture.id,
            overall_score=overall_score,
            quality_score=quality_score,
            security_score=security_score,
            dependency_score=dependency_score,
            architecture_score=architecture_score,
            maintainability_score=maintainability_score,
            testing_score=testing_score,
            technical_debt_hours=debt_breakdown["total_hours"],
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            status=status,
            explanations=explanations,
            debt_breakdown=debt_breakdown,
            fix_first=fix_first,
            weights_used=DEFAULT_WEIGHTS,
        )

        self.db.add(health_record)
        self.db.commit()
        self.db.refresh(health_record)

        return health_record
