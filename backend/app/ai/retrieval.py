import os
import re
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan, ProjectFile
from backend.app.models.quality import QualityAnalysis, QualityIssue
from backend.app.models.security import SecurityAnalysis, SecurityIssue
from backend.app.models.dependency import DependencyAnalysis, ProjectDependency
from backend.app.models.architecture import ArchitectureAnalysis, ArchitectureNode, ArchitectureEdge
from backend.app.models.health import HealthAnalysis
from backend.app.ai.sanitizer import is_file_disallowed, mask_sensitive_snippet


STOP_WORDS = {
    "what", "where", "which", "how", "why", "who", "when", "is", "are", "the",
    "a", "an", "in", "on", "at", "of", "for", "to", "from", "by", "with",
    "this", "that", "these", "those", "my", "our", "your", "show", "me", "tell",
    "explain", "does", "do", "did", "can", "could", "would", "should", "any",
    "about", "project", "codebase", "file", "files", "here", "there"
}

SYNONYMS = {
    "auth": ["auth", "login", "jwt", "token", "user", "session", "password"],
    "authentication": ["auth", "login", "jwt", "token", "user", "session", "password"],
    "database": ["db", "database", "models", "schema", "repository", "sql", "sqlite", "postgres"],
    "db": ["db", "database", "models", "schema", "sql"],
    "api": ["api", "router", "route", "routes", "endpoint", "endpoints", "views", "controllers"],
    "service": ["service", "services", "handler", "manager"],
    "config": ["config", "settings", "env", "configuration"],
    "test": ["test", "tests", "spec"],
    "security": ["security", "secret", "vulnerability", "injection", "eval", "crypto"],
    "quality": ["quality", "complexity", "duplicate", "function", "todo"],
    "dependency": ["dependency", "dependencies", "package", "requirements", "package.json"],
    "architecture": ["architecture", "layer", "cycle", "circular", "import", "graph"]
}


class RetrievedSnippet:
    def __init__(self, file_path: str, line_start: int, line_end: int, content: str, reason: str):
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.content = content
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "content": self.content,
            "reason": self.reason
        }


class RetrievedContext:
    def __init__(
        self,
        project_name: str,
        scan_overview: str,
        deterministic_evidence: List[str],
        code_snippets: List[RetrievedSnippet],
        all_project_files: Set[str]
    ):
        self.project_name = project_name
        self.scan_overview = scan_overview
        self.deterministic_evidence = deterministic_evidence
        self.code_snippets = code_snippets
        self.all_project_files = all_project_files


class CodebaseRetriever:
    """Retrieves grounded repository evidence and targeted code snippets without loading the whole repo."""

    def __init__(self, project: Project, db: Session):
        self.project = project
        self.db = db

    def extract_keywords(self, question: str) -> Set[str]:
        tokens = re.findall(r"[a-zA-Z0-9_\-\.]+", question.lower())
        keywords: Set[str] = set()
        for t in tokens:
            if len(t) >= 2 and t not in STOP_WORDS:
                keywords.add(t)
                if t in SYNONYMS:
                    keywords.update(SYNONYMS[t])
        return keywords

    def retrieve(self, question: str, max_snippets: int = 5) -> RetrievedContext:
        keywords = self.extract_keywords(question)
        q_lower = question.lower()

        # 1. Project Scan overview & all file paths
        latest_scan = (
            self.db.query(ProjectScan)
            .filter(ProjectScan.project_id == self.project.id)
            .order_by(ProjectScan.scanned_at.desc())
            .first()
        )

        all_files_query = (
            self.db.query(ProjectFile.file_path)
            .filter(ProjectFile.project_id == self.project.id)
            .all()
        )
        all_project_files: Set[str] = {f[0].replace("\\", "/") for f in all_files_query}

        scan_overview_lines = [f"Project Name: {self.project.name}"]
        if latest_scan:
            scan_overview_lines.append(
                f"Repository Scan: {latest_scan.total_files} total files, {latest_scan.total_code_lines} lines of code, "
                f"{latest_scan.total_directories} directories."
            )
            if latest_scan.languages_summary:
                langs = [f"{lang} ({data.get('percentage', 0)}%)" for lang, data in latest_scan.languages_summary.items()]
                scan_overview_lines.append(f"Languages: {', '.join(langs)}")
        else:
            scan_overview_lines.append("Repository Scan: No scan completed yet.")

        # 2. Deterministic findings based on query intent
        deterministic_evidence: List[str] = []

        # (a) Security
        is_security_intent = any(k in keywords for k in ["security", "vulnerability", "vulnerabilities", "secret", "token", "password", "injection", "eval", "cve", "threat"])
        if is_security_intent or "issue" in q_lower or "problem" in q_lower:
            sec_issues = (
                self.db.query(SecurityIssue)
                .filter(SecurityIssue.project_id == self.project.id)
                .order_by(SecurityIssue.severity.asc())
                .limit(8)
                .all()
            )
            if sec_issues:
                deterministic_evidence.append(f"Security Findings ({len(sec_issues)} detected):")
                for s in sec_issues:
                    loc = f"{s.file_path}:{s.line_number}" if s.file_path else "Project-wide"
                    deterministic_evidence.append(f"  - [{s.severity}] {s.category} ({s.issue_type}): {s.message} at {loc}")

        # (b) Quality
        is_quality_intent = any(k in keywords for k in ["quality", "complexity", "cyclomatic", "nesting", "long", "duplicate", "todo", "function", "maintainability"])
        if is_quality_intent or "issue" in q_lower or "problem" in q_lower:
            qual_issues = (
                self.db.query(QualityIssue)
                .filter(QualityIssue.project_id == self.project.id)
                .order_by(QualityIssue.severity.asc())
                .limit(8)
                .all()
            )
            if qual_issues:
                deterministic_evidence.append(f"Code Quality Findings ({len(qual_issues)} detected):")
                for q in qual_issues:
                    loc = f"{q.file_path}:{q.line_number}" if q.file_path else "Project-wide"
                    sym = f" in '{q.symbol_name}'" if q.symbol_name else ""
                    deterministic_evidence.append(f"  - [{q.severity}] {q.issue_type}: {q.message}{sym} at {loc}")

        # (c) Dependencies
        is_dep_intent = any(k in keywords for k in ["dependency", "dependencies", "package", "packages", "library", "libraries", "osv", "outdated", "vulnerable", "npm", "pypi"])
        if is_dep_intent:
            deps = (
                self.db.query(ProjectDependency)
                .filter(ProjectDependency.project_id == self.project.id)
                .all()
            )
            vuln_deps = [d for d in deps if d.status == "VULNERABLE" or d.vulnerability_count > 0]
            outdated_deps = [d for d in deps if d.status == "OUTDATED"]
            deterministic_evidence.append(f"Dependency Analysis: {len(deps)} total dependencies ({len(vuln_deps)} vulnerable, {len(outdated_deps)} outdated).")
            if vuln_deps:
                deterministic_evidence.append("Vulnerable Packages:")
                for vd in vuln_deps[:6]:
                    adv_info = f"({vd.vulnerability_count} advisories)" if vd.vulnerability_count else ""
                    deterministic_evidence.append(f"  - {vd.name}@{vd.resolved_version or vd.declared_version} in {vd.manifest_file} {adv_info}")
            if outdated_deps:
                deterministic_evidence.append("Outdated Packages:")
                for od in outdated_deps[:5]:
                    deterministic_evidence.append(f"  - {od.name} (current: {od.resolved_version or od.declared_version}, latest: {od.latest_version})")

        # (d) Architecture
        is_arch_intent = any(k in keywords for k in ["architecture", "structure", "layer", "layers", "import", "imports", "circular", "cycle", "cycles", "depend", "graph"])
        if is_arch_intent:
            arch = (
                self.db.query(ArchitectureAnalysis)
                .filter(ArchitectureAnalysis.project_id == self.project.id)
                .order_by(ArchitectureAnalysis.analyzed_at.desc())
                .first()
            )
            if arch:
                deterministic_evidence.append(f"Architecture Topology: {arch.node_count} nodes, {arch.edge_count} dependency edges across layers: {', '.join(arch.layers_summary.keys())}.")
                if arch.cycle_count > 0 and arch.cycles:
                    deterministic_evidence.append(f"Circular Dependency Loops Detected ({arch.cycle_count}):")
                    for c_idx, loop in enumerate(arch.cycles[:3]):
                        deterministic_evidence.append(f"  - Loop #{c_idx + 1}: {' -> '.join([f.split('/')[-1] for f in loop])}")

            # Also check if user is asking about a specific file's dependencies
            for kw in keywords:
                matching_nodes = (
                    self.db.query(ArchitectureNode)
                    .filter(ArchitectureNode.project_id == self.project.id, ArchitectureNode.file_path.ilike(f"%{kw}%"))
                    .all()
                )
                for node in matching_nodes[:3]:
                    # Find outgoing and incoming edges
                    out_edges = self.db.query(ArchitectureEdge).filter(ArchitectureEdge.source_id == node.id).all()
                    in_edges = self.db.query(ArchitectureEdge).filter(ArchitectureEdge.target_id == node.id).all()
                    if out_edges:
                        imported_names = [e.target.file_path.split("/")[-1] for e in out_edges if e.target]
                        deterministic_evidence.append(f"File '{node.file_path}' directly imports: {', '.join(imported_names[:8])}")
                    if in_edges:
                        importer_names = [e.source.file_path.split("/")[-1] for e in in_edges if e.source]
                        deterministic_evidence.append(f"File '{node.file_path}' is imported by: {', '.join(importer_names[:8])}")

        # (e) Health
        is_health_intent = any(k in keywords for k in ["health", "score", "scores", "debt", "hours", "fix", "first", "priority"])
        if is_health_intent or "score" in q_lower:
            health = (
                self.db.query(HealthAnalysis)
                .filter(HealthAnalysis.project_id == self.project.id)
                .order_by(HealthAnalysis.created_at.desc())
                .first()
            )
            if health:
                deterministic_evidence.append(
                    f"Health Score: {Math_Round(health.overall_score)}/100 (Status: {health.status}). "
                    f"Security: {Math_Round(health.security_score)}, Quality: {Math_Round(health.quality_score)}, "
                    f"Dependencies: {Math_Round(health.dependency_score)}, Architecture: {Math_Round(health.architecture_score)}, "
                    f"Maintainability: {Math_Round(health.maintainability_score)}, Testing: {Math_Round(health.testing_score)}."
                )
                deterministic_evidence.append(f"Estimated Technical Debt: {health.technical_debt_hours} developer hours.")
                if health.fix_first:
                    deterministic_evidence.append("Prioritized 'Fix First' Actions:")
                    for ff in health.fix_first[:5]:
                        deterministic_evidence.append(f"  #{ff.get('rank')}: [{ff.get('category')}] {ff.get('title')} ({ff.get('location')})")

        # 3. Code Snippet Retrieval (Path / Keyword Matching)
        code_snippets: List[RetrievedSnippet] = []
        candidate_files: List[str] = []

        # Find files matching keywords
        for f_path in all_project_files:
            f_lower = f_path.lower()
            # If keyword matches filename or directory path
            match_score = 0
            for kw in keywords:
                if kw in f_lower:
                    match_score += 2
                    if f_lower.endswith(f"{kw}.py") or f_lower.endswith(f"{kw}.js") or f_lower.endswith(f"{kw}.ts"):
                        match_score += 5
            if match_score > 0:
                candidate_files.append((match_score, f_path))

        # Sort candidate files by match score
        candidate_files.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [cf[1] for cf in candidate_files[:max_snippets]]

        # If no candidates found by keyword, pick key entrypoints / files
        if not top_candidates:
            for priority_file in ["main.py", "app.py", "index.js", "App.tsx", "server.js", "auth.py", "database.py"]:
                matches = [f for f in all_project_files if f.lower().endswith(priority_file)]
                if matches and matches[0] not in top_candidates:
                    top_candidates.append(matches[0])
                    if len(top_candidates) >= 3:
                        break

        # Extract bounded snippets from candidates
        storage_path = self.project.storage_path
        if storage_path and os.path.isdir(storage_path):
            abs_storage = os.path.abspath(storage_path)
            for rel_path in top_candidates:
                if is_file_disallowed(rel_path):
                    continue
                full_path = os.path.abspath(os.path.join(abs_storage, rel_path))
                if not full_path.startswith(abs_storage) or not os.path.isfile(full_path):
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    if not lines:
                        continue

                    # Search for best match line in the file
                    best_line_idx = 0
                    for idx, line in enumerate(lines):
                        line_l = line.lower()
                        if any(kw in line_l for kw in keywords):
                            best_line_idx = idx
                            break

                    start_idx = max(0, best_line_idx - 10)
                    end_idx = min(len(lines), best_line_idx + 25)

                    snippet_lines = [f"{i+1:4d} | {lines[i].rstrip()}" for i in range(start_idx, end_idx)]
                    raw_content = "\n".join(snippet_lines)
                    masked_content = mask_sensitive_snippet(raw_content)

                    if len(masked_content) > 1200:
                        masked_content = masked_content[:1200] + "\n   ... [truncated]"

                    code_snippets.append(
                        RetrievedSnippet(
                            file_path=rel_path,
                            line_start=start_idx + 1,
                            line_end=end_idx,
                            content=masked_content,
                            reason=f"Matched keywords in file path or source content"
                        )
                    )
                except Exception:
                    continue

        return RetrievedContext(
            project_name=self.project.name,
            scan_overview="\n".join(scan_overview_lines),
            deterministic_evidence=deterministic_evidence,
            code_snippets=code_snippets,
            all_project_files=all_project_files
        )


def Math_Round(val: Optional[float]) -> int:
    return round(val) if val is not None else 0
