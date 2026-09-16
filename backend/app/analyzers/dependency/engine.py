import os
from typing import List, Dict, Any, Optional, Set

from backend.app.analyzers.dependency.manifest_parser import (
    ParsedDependency,
    parse_requirements_txt,
    parse_pyproject_toml,
    parse_pipfile,
    parse_package_json,
    parse_package_lock_json,
    parse_pom_xml,
)
from backend.app.analyzers.dependency.vulnerability_service import VulnerabilityService
from backend.app.analyzers.dependency.version_checker import VersionChecker

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
    "dist",
    "build",
    "vendor",
}


class DependencyAuditEngine:
    def __init__(
        self,
        vulnerability_service: Optional[VulnerabilityService] = None,
        version_checker: Optional[VersionChecker] = None,
    ):
        self.vuln_service = vulnerability_service or VulnerabilityService()
        self.version_checker = version_checker or VersionChecker()

    def audit_project(self, project_path: str) -> Dict[str, Any]:
        """Perform full static dependency audit across all manifests in the project repository.
        Zero code execution. Real vulnerability data only.
        """
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        # 1. Discover all manifest files
        manifests: Dict[str, List[str]] = {
            "requirements": [],
            "pyproject": [],
            "pipfile": [],
            "package_json": [],
            "package_lock": [],
            "pom_xml": [],
        }

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for filename in files:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, project_path).replace("\\", "/")
                lower_name = filename.lower()

                if lower_name == "package.json":
                    manifests["package_json"].append((abs_path, rel_path))
                elif lower_name in {"package-lock.json", "npm-shrinkwrap.json"}:
                    manifests["package_lock"].append((abs_path, rel_path))
                elif lower_name.endswith(".txt") and ("requirement" in lower_name or lower_name == "requirements.txt"):
                    manifests["requirements"].append((abs_path, rel_path))
                elif lower_name == "pyproject.toml":
                    manifests["pyproject"].append((abs_path, rel_path))
                elif lower_name == "pipfile":
                    manifests["pipfile"].append((abs_path, rel_path))
                elif lower_name == "pom.xml":
                    manifests["pom_xml"].append((abs_path, rel_path))

        all_parsed_deps: List[ParsedDependency] = []
        manifests_scanned: List[str] = []

        # 2. Parse package.json files
        npm_direct_names_by_dir: Dict[str, Set[str]] = {}
        for abs_path, rel_path in manifests["package_json"]:
            manifests_scanned.append(rel_path)
            content = self._read_file(abs_path)
            if content:
                deps = parse_package_json(content, rel_path)
                all_parsed_deps.extend(deps)
                dir_key = os.path.dirname(abs_path)
                npm_direct_names_by_dir[dir_key] = {d.name for d in deps}

        # 3. Parse package-lock.json files (correlating with package.json in same dir)
        for abs_path, rel_path in manifests["package_lock"]:
            manifests_scanned.append(rel_path)
            content = self._read_file(abs_path)
            if content:
                dir_key = os.path.dirname(abs_path)
                direct_names = npm_direct_names_by_dir.get(dir_key, set())
                lock_deps = parse_package_lock_json(content, rel_path, direct_names=direct_names)

                # If package.json was already parsed, update resolved versions for direct deps
                # and append transitive deps
                direct_map = {
                    (d.name, os.path.dirname(d.manifest_file)): d
                    for d in all_parsed_deps
                    if d.ecosystem == "npm"
                }

                for ld in lock_deps:
                    key = (ld.name, os.path.dirname(rel_path))
                    if key in direct_map:
                        if not direct_map[key].resolved_version and ld.resolved_version:
                            direct_map[key].resolved_version = ld.resolved_version
                    else:
                        # Append transitive dependency
                        all_parsed_deps.append(ld)

        # 4. Parse Python requirements
        for abs_path, rel_path in manifests["requirements"]:
            manifests_scanned.append(rel_path)
            content = self._read_file(abs_path)
            if content:
                all_parsed_deps.extend(parse_requirements_txt(content, rel_path))

        # 5. Parse pyproject.toml
        for abs_path, rel_path in manifests["pyproject"]:
            manifests_scanned.append(rel_path)
            content = self._read_file(abs_path)
            if content:
                all_parsed_deps.extend(parse_pyproject_toml(content, rel_path))

        # 6. Parse Pipfile
        for abs_path, rel_path in manifests["pipfile"]:
            manifests_scanned.append(rel_path)
            content = self._read_file(abs_path)
            if content:
                all_parsed_deps.extend(parse_pipfile(content, rel_path))

        # 7. Parse pom.xml
        for abs_path, rel_path in manifests["pom_xml"]:
            manifests_scanned.append(rel_path)
            content = self._read_file(abs_path)
            if content:
                all_parsed_deps.extend(parse_pom_xml(content, rel_path))

        # 8. Deduplicate identical package entries within the same manifest file
        unique_deps: List[ParsedDependency] = []
        seen = set()
        for d in all_parsed_deps:
            key = (d.name.lower(), d.ecosystem, d.manifest_file)
            if key not in seen:
                seen.add(key)
                unique_deps.append(d)

        # 9. Verify Vulnerabilities & Latest Versions for each dependency
        evaluated_deps: List[Dict[str, Any]] = []
        generated_issues: List[Dict[str, Any]] = []

        vulnerable_count = 0
        outdated_count = 0
        current_count = 0
        unknown_count = 0

        direct_count = sum(1 for d in unique_deps if d.dependency_type in {"direct", "dev", "peer"})
        transitive_count = sum(1 for d in unique_deps if d.dependency_type == "transitive")

        for d in unique_deps:
            # Determine candidate version for query
            query_version = d.resolved_version
            if not query_version and d.declared_version:
                if d.declared_version.startswith("=="):
                    query_version = d.declared_version[2:]
                elif d.declared_version[0].isdigit():
                    query_version = d.declared_version

            # Check OSV vulnerabilities
            advisories, was_net_err = self.vuln_service.check_vulnerabilities(
                d.name, d.ecosystem, query_version
            )
            vuln_count = len(advisories) if advisories else 0

            # Check latest version
            latest_version = self.version_checker.get_latest_version(d.name, d.ecosystem)

            # Determine status
            status = self.version_checker.determine_status(
                current_version=query_version or d.declared_version,
                latest_version=latest_version,
                vulnerability_count=vuln_count,
                was_network_error=was_net_err,
            )

            if status == "VULNERABLE":
                vulnerable_count += 1
            elif status == "OUTDATED":
                outdated_count += 1
            elif status == "CURRENT":
                current_count += 1
            else:
                unknown_count += 1

            dep_record = {
                "manifest_file": d.manifest_file,
                "ecosystem": d.ecosystem,
                "name": d.name,
                "declared_version": d.declared_version,
                "resolved_version": d.resolved_version,
                "dependency_type": d.dependency_type,
                "latest_version": latest_version,
                "status": status,
                "vulnerability_count": vuln_count,
                "advisories": advisories or [],
            }
            evaluated_deps.append(dep_record)

            # Generate issues for confirmed problems
            if status == "VULNERABLE" and advisories:
                for adv in advisories:
                    generated_issues.append({
                        "category": "dependency",
                        "issue_type": "vulnerable_dependency",
                        "severity": adv.get("severity", "HIGH"),
                        "package_name": d.name,
                        "manifest_file": d.manifest_file,
                        "version": query_version or d.declared_version or "unknown",
                        "vulnerability_id": adv.get("id"),
                        "description": f"Vulnerability {adv.get('id')} detected in {d.name}: {adv.get('summary')}",
                        "recommendation": (
                            f"Upgrade {d.name} to version {adv.get('fixed_version')} or higher to resolve advisory."
                            if adv.get("fixed_version")
                            else f"Upgrade {d.name} to a secure patched release."
                        ),
                    })
            elif status == "OUTDATED" and latest_version:
                generated_issues.append({
                    "category": "dependency",
                    "issue_type": "outdated_dependency",
                    "severity": "LOW",
                    "package_name": d.name,
                    "manifest_file": d.manifest_file,
                    "version": query_version or d.declared_version or "unknown",
                    "vulnerability_id": None,
                    "description": f"Package '{d.name}' is outdated (installed: {query_version or d.declared_version}, latest: {latest_version}).",
                    "recommendation": f"Update '{d.name}' to {latest_version} and test for breaking changes.",
                })

        # By ecosystem counts
        by_ecosystem: Dict[str, int] = {}
        for d in unique_deps:
            by_ecosystem[d.ecosystem] = by_ecosystem.get(d.ecosystem, 0) + 1

        metrics = {
            "manifests_scanned": manifests_scanned,
            "by_ecosystem": by_ecosystem,
            "network_warning": self.vuln_service.network_error_occurred,
        }

        return {
            "total_dependencies": len(unique_deps),
            "direct_dependencies": direct_count,
            "transitive_dependencies": transitive_count,
            "current_count": current_count,
            "outdated_count": outdated_count,
            "vulnerable_count": vulnerable_count,
            "unknown_count": unknown_count,
            "metrics": metrics,
            "dependencies": evaluated_deps,
            "issues": generated_issues,
        }

    def _read_file(self, abs_path: str) -> Optional[str]:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None


def run_dependency_analysis(
    project,
    scan,
    db,
    vuln_service: Optional[VulnerabilityService] = None,
    version_checker: Optional[VersionChecker] = None,
) -> Dict[str, Any]:
    """Helper entrypoint for running dependency audit on a project."""
    engine = DependencyAuditEngine(
        vulnerability_service=vuln_service,
        version_checker=version_checker,
    )
    storage_path = project.storage_path
    if not storage_path or not os.path.exists(storage_path):
        raise ValueError(f"Project storage path not found: {storage_path}")

    return engine.audit_project(storage_path)
