import ast
import os
from typing import List, Dict, Any, Optional

from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding
from backend.app.analyzers.security.secrets import HardcodedSecretRule, mask_line
from backend.app.analyzers.security.injection import SQLInjectionRule, CommandInjectionRule
from backend.app.analyzers.security.dangerous_calls import DangerousCallsRule
from backend.app.analyzers.security.configuration import InsecureConfigurationRule
from backend.app.analyzers.security.crypto import WeakCryptographyRule
from backend.app.analyzers.security.password import InsecurePasswordRule

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    "vendor",
}

IGNORED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
}

MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB


class SecurityAuditEngine:
    def __init__(self):
        self.rules: List[BaseSecurityRule] = [
            HardcodedSecretRule(),
            SQLInjectionRule(),
            CommandInjectionRule(),
            DangerousCallsRule(),
            InsecureConfigurationRule(),
            WeakCryptographyRule(),
            InsecurePasswordRule(),
        ]

    def audit_project(self, project_path: str) -> Dict[str, Any]:
        """Perform static security audit on all qualifying files in the project.
        Zero code execution. Strict secret masking.
        """
        all_findings: List[SecurityFinding] = []
        files_audited = 0
        files_skipped = 0

        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project storage path does not exist: {project_path}")

        for root, dirs, files in os.walk(project_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for filename in files:
                if filename in IGNORED_FILES:
                    files_skipped += 1
                    continue

                abs_file_path = os.path.join(root, filename)
                rel_file_path = os.path.relpath(abs_file_path, project_path).replace("\\", "/")

                # Check file size
                try:
                    size = os.path.getsize(abs_file_path)
                    if size > MAX_FILE_SIZE_BYTES:
                        files_skipped += 1
                        continue
                except OSError:
                    files_skipped += 1
                    continue

                _, ext = os.path.splitext(filename)
                ext = ext.lower()

                # Read file content safely
                try:
                    with open(abs_file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    files_skipped += 1
                    continue

                # Pre-parse Python AST if applicable
                ast_tree: Optional[ast.AST] = None
                if ext == ".py":
                    try:
                        ast_tree = ast.parse(content, filename=filename)
                    except SyntaxError:
                        ast_tree = None

                # Execute all registered security rules
                for rule in self.rules:
                    try:
                        findings = rule.run(
                            file_path=rel_file_path,
                            content=content,
                            ext=ext,
                            ast_tree=ast_tree,
                        )
                        for finding in findings:
                            # Enforce global secret masking on evidence
                            if finding.evidence:
                                finding.evidence = mask_line(finding.evidence)
                            all_findings.append(finding)
                    except Exception:
                        # Fault tolerant: single rule error on a file does not crash the audit
                        pass

                files_audited += 1

        # Aggregate counts
        critical_count = sum(1 for f in all_findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in all_findings if f.severity == "HIGH")
        medium_count = sum(1 for f in all_findings if f.severity == "MEDIUM")
        low_count = sum(1 for f in all_findings if f.severity == "LOW")
        total_issues = len(all_findings)

        # Categorized metrics
        by_category: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for f in all_findings:
            by_category[f.category] = by_category.get(f.category, 0) + 1
            by_type[f.issue_type] = by_type.get(f.issue_type, 0) + 1

        metrics = {
            "files_audited": files_audited,
            "files_skipped": files_skipped,
            "by_category": by_category,
            "by_type": by_type,
            "by_severity": {
                "CRITICAL": critical_count,
                "HIGH": high_count,
                "MEDIUM": medium_count,
                "LOW": low_count,
            },
        }

        # Format issues into dictionaries ready for ORM or API
        serialized_issues = []
        for f in all_findings:
            serialized_issues.append({
                "category": f.category,
                "issue_type": f.issue_type,
                "severity": f.severity,
                "confidence": f.confidence,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "end_line": f.end_line,
                "symbol_name": f.symbol_name,
                "message": f.message,
                "description": f.description,
                "evidence": f.evidence,
                "recommendation": f.recommendation,
            })

        return {
            "total_issues": total_issues,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "metrics": metrics,
            "issues": serialized_issues,
        }


def run_security_analysis(project, scan, db) -> Dict[str, Any]:
    """Helper entrypoint for running security audit on a project."""
    engine = SecurityAuditEngine()
    storage_path = project.storage_path
    if not storage_path or not os.path.exists(storage_path):
        raise ValueError(f"Project storage path not found: {storage_path}")

    return engine.audit_project(storage_path)
