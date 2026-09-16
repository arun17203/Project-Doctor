import hashlib
from typing import Optional, Tuple, Any, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.quality import QualityIssue
from backend.app.models.security import SecurityIssue
from backend.app.models.dependency import DependencyIssue, ProjectDependency
from backend.app.models.architecture import ArchitectureEdge, ArchitectureNode
from backend.app.models.ai import AIExplanation
from backend.app.ai.client import GeminiClient, gemini_client, AIUnavailableError, AIExplanationError
from backend.app.ai.prompts import build_explanation_prompt
from backend.app.ai.sanitizer import extract_relevant_snippet


class AIExplainerService:
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or gemini_client

    def resolve_issue(self, db: Session, issue_id: str) -> Tuple[str, Any, Project]:
        """Resolves issue_id across all supported static-analysis issue models.
        Returns:
            (category, issue_model_instance, project)
        """
        # 1. Check Quality Issues
        qual = db.query(QualityIssue).filter(QualityIssue.id == issue_id).first()
        if qual:
            proj = db.query(Project).filter(Project.id == qual.project_id).first()
            if not proj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found.")
            return "quality", qual, proj

        # 2. Check Security Issues
        sec = db.query(SecurityIssue).filter(SecurityIssue.id == issue_id).first()
        if sec:
            proj = db.query(Project).filter(Project.id == sec.project_id).first()
            if not proj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found.")
            return "security", sec, proj

        # 3. Check Dependency Issues
        dep_issue = db.query(DependencyIssue).filter(DependencyIssue.id == issue_id).first()
        if dep_issue:
            proj = db.query(Project).filter(Project.id == dep_issue.project_id).first()
            if not proj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found.")
            return "dependency", dep_issue, proj

        # 4. Check ProjectDependency directly
        proj_dep = db.query(ProjectDependency).filter(ProjectDependency.id == issue_id).first()
        if proj_dep:
            proj = db.query(Project).filter(Project.id == proj_dep.project_id).first()
            if not proj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found.")
            return "dependency", proj_dep, proj

        # 5. Check Architecture Edge
        arch_edge = db.query(ArchitectureEdge).filter(ArchitectureEdge.id == issue_id).first()
        if arch_edge:
            proj = db.query(Project).filter(Project.id == arch_edge.project_id).first()
            if not proj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found.")
            return "architecture", arch_edge, proj

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID '{issue_id}' not found in any static analysis categories.",
        )

    def verify_ownership(self, project: Project, user: User) -> None:
        """Enforces that only the project owner can request or view AI explanations."""
        if project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access issues for this project.",
            )

    def extract_evidence_and_prompt(
        self,
        category: str,
        issue: Any,
        project: Project,
        db: Session,
    ) -> Tuple[str, str, str]:
        """Extracts sanitized evidence, snippet, and builds structured prompt for Gemini.
        Returns:
            (issue_type, evidence_hash, prompt_text)
        """
        file_path = None
        line_number = None
        symbol_name = None
        deterministic_message = None
        deterministic_description = None
        measured_metric = None
        evidence = None
        extra_context: Dict[str, Any] = {}

        if category == "quality":
            issue_type = issue.issue_type
            severity = issue.severity
            file_path = issue.file_path
            line_number = issue.line_number
            symbol_name = getattr(issue, "symbol_name", None)
            deterministic_message = issue.message
            deterministic_description = issue.description
            measured_metric = getattr(issue, "evidence", None)
            if issue.recommendation:
                extra_context["analyzer_recommendation"] = issue.recommendation

        elif category == "security":
            issue_type = issue.issue_type
            severity = issue.severity
            file_path = issue.file_path
            line_number = issue.line_number
            symbol_name = issue.symbol_name
            deterministic_message = issue.message
            deterministic_description = issue.description
            # Strictly use masked evidence from Stage 6
            evidence = issue.evidence or getattr(issue, "masked_evidence", None)
            if getattr(issue, "rule_id", None):
                extra_context["security_rule_id"] = issue.rule_id
            if getattr(issue, "cwe_id", None):
                extra_context["cwe_reference"] = issue.cwe_id

        elif category == "dependency":
            if isinstance(issue, DependencyIssue):
                issue_type = issue.issue_type
                severity = issue.severity
                file_path = issue.manifest_file
                deterministic_message = f"Dependency Finding: {issue.package_name} ({issue.version})"
                deterministic_description = issue.description
                if issue.vulnerability_id:
                    extra_context["vulnerability_advisory_id"] = issue.vulnerability_id
                if issue.recommendation:
                    extra_context["remediation_advice"] = issue.recommendation
            else:
                # ProjectDependency
                is_vuln = getattr(issue, "status", "") == "VULNERABLE" or (getattr(issue, "vulnerability_count", 0) or 0) > 0
                issue_type = "vulnerable_dependency" if is_vuln else "outdated_dependency"
                severity = issue.status
                file_path = issue.manifest_file
                deterministic_message = f"Package {issue.name} declared: {issue.declared_version}, resolved: {issue.resolved_version}"
                deterministic_description = f"Status: {issue.status}. Latest available: {issue.latest_version or 'N/A'}"
                if issue.advisories:
                    extra_context["known_advisories_count"] = len(issue.advisories)
                    extra_context["advisories_sample"] = str(issue.advisories[:2])

        elif category == "architecture":
            issue_type = "circular_dependency" if issue.is_circular else "architecture_coupling"
            severity = "HIGH" if issue.is_circular else "MEDIUM"
            source_node = db.query(ArchitectureNode).filter(ArchitectureNode.id == issue.source_node_id).first()
            target_node = db.query(ArchitectureNode).filter(ArchitectureNode.id == issue.target_node_id).first()
            file_path = source_node.file_path if source_node else None
            deterministic_message = f"Architecture import edge: {source_node.name if source_node else 'A'} -> {target_node.name if target_node else 'B'}"
            deterministic_description = "Edge participates in circular dependency cycle." if issue.is_circular else "Cross-module import coupling."
            if issue.raw_import:
                extra_context["import_statement"] = issue.raw_import
            if source_node and target_node:
                extra_context["source_layer"] = source_node.layer
                extra_context["target_layer"] = target_node.layer

        else:
            issue_type = "general_finding"
            severity = "MEDIUM"

        # Extract source code snippet if on disk and not disallowed
        source_snippet = None
        if file_path and project.storage_path:
            source_snippet = extract_relevant_snippet(
                project_root=project.storage_path,
                relative_path=file_path,
                line_number=line_number,
                radius=5,
                max_chars=600,
            )

        # Compute evidence hash to detect changes
        hash_seed = f"{category}:{issue_type}:{severity}:{file_path}:{line_number}:{deterministic_message}:{evidence}"
        evidence_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()

        prompt = build_explanation_prompt(
            category=category,
            issue_type=issue_type,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            symbol_name=symbol_name,
            deterministic_message=deterministic_message,
            deterministic_description=deterministic_description,
            measured_metric=measured_metric,
            evidence=evidence,
            source_snippet=source_snippet,
            extra_context=extra_context,
        )

        return issue_type, evidence_hash, prompt

    def explain_issue(
        self,
        db: Session,
        issue_id: str,
        user: User,
        force_regenerate: bool = False,
    ) -> AIExplanation:
        """Main method to explain an issue. Uses caching unless force_regenerate is True."""
        category, issue, project = self.resolve_issue(db, issue_id)
        self.verify_ownership(project, user)

        # Check existing cached explanation
        existing = db.query(AIExplanation).filter(AIExplanation.issue_id == issue_id).first()
        if existing and not force_regenerate:
            return existing

        # Extract evidence and build prompt
        issue_type, evidence_hash, prompt = self.extract_evidence_and_prompt(category, issue, project, db)

        # Generate structured explanation via Gemini
        try:
            ai_out = self.client.generate_explanation(prompt)
        except AIUnavailableError as ue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(ue),
            )
        except AIExplanationError as ee:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(ee),
            )

        # Persist or update in PostgreSQL / SQLite
        if existing:
            existing.summary = ai_out.summary
            existing.why_it_matters = ai_out.why_it_matters
            existing.potential_impact = ai_out.potential_impact
            existing.recommendation = ai_out.recommendation
            existing.priority = ai_out.priority
            existing.developer_action = ai_out.developer_action
            existing.evidence_hash = evidence_hash
            existing.model = self.client.model
            db.commit()
            db.refresh(existing)
            return existing

        new_explanation = AIExplanation(
            issue_id=issue_id,
            project_id=project.id,
            issue_category=category,
            issue_type=issue_type,
            provider="google-gemini",
            model=self.client.model,
            summary=ai_out.summary,
            why_it_matters=ai_out.why_it_matters,
            potential_impact=ai_out.potential_impact,
            recommendation=ai_out.recommendation,
            priority=ai_out.priority,
            developer_action=ai_out.developer_action,
            evidence_hash=evidence_hash,
        )
        db.add(new_explanation)
        db.commit()
        db.refresh(new_explanation)
        return new_explanation

    def get_existing_explanation(
        self,
        db: Session,
        issue_id: str,
        user: User,
    ) -> Optional[AIExplanation]:
        """Retrieves existing explanation if one has already been created."""
        category, issue, project = self.resolve_issue(db, issue_id)
        self.verify_ownership(project, user)

        explanation = db.query(AIExplanation).filter(AIExplanation.issue_id == issue_id).first()
        return explanation


ai_explainer_service = AIExplainerService()
