from typing import List, Dict, Any


def generate_fix_first_list(
    security_issues: List[Any],
    quality_issues: List[Any],
    dependency_issues: List[Any],
    circular_cycles: List[List[str]],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Generate deterministic 'Fix First' priority action list.
    Prioritization order:
      1. Critical Security findings
      2. Critical Quality findings
      3. High Security findings
      4. High Quality findings
      5. Vulnerable Dependencies
      6. Circular Dependencies
      7. Medium Security findings
      8. Medium Quality findings
      9. Outdated Dependencies
      10. Low issues
    """
    candidates: List[Dict[str, Any]] = []

    # 1. Security Issues
    for sec in security_issues:
        sev = getattr(sec, "severity", "LOW").upper()
        weight = 10
        if sev == "CRITICAL":
            weight = 100
        elif sev == "HIGH":
            weight = 80
        elif sev == "MEDIUM":
            weight = 40

        file_p = getattr(sec, "file_path", "")
        line_no = getattr(sec, "line_number", 1)
        candidates.append(
            {
                "weight": weight,
                "category": "Security",
                "severity": sev,
                "title": getattr(sec, "message", getattr(sec, "issue_type", "Security Finding")),
                "location": f"{file_p}:{line_no}" if file_p else "Project Code",
                "file_path": file_p,
                "line_number": line_no,
                "description": getattr(sec, "description", ""),
                "recommendation": getattr(sec, "recommendation", "Review and remediate security vulnerability."),
            }
        )

    # 2. Quality Issues
    for qual in quality_issues:
        sev = getattr(qual, "severity", "LOW").upper()
        weight = 10
        if sev == "CRITICAL":
            weight = 90
        elif sev == "HIGH":
            weight = 70
        elif sev == "MEDIUM":
            weight = 30

        file_p = getattr(qual, "file_path", "")
        line_no = getattr(qual, "line_number", 1)
        candidates.append(
            {
                "weight": weight,
                "category": "Code Quality",
                "severity": sev,
                "title": getattr(qual, "message", getattr(qual, "issue_type", "Code Quality Finding")),
                "location": f"{file_p}:{line_no}" if file_p else "Project Code",
                "file_path": file_p,
                "line_number": line_no,
                "description": getattr(qual, "description", ""),
                "recommendation": getattr(qual, "recommendation", "Refactor module or simplify complex structure."),
            }
        )

    # 3. Dependency Issues
    for dep in dependency_issues:
        sev = getattr(dep, "severity", "LOW").upper()
        weight = 20
        if sev == "CRITICAL":
            weight = 65
        elif sev == "HIGH":
            weight = 60
        elif sev == "MEDIUM":
            weight = 35

        pkg = getattr(dep, "package_name", "package")
        manifest = getattr(dep, "manifest_file", "")
        candidates.append(
            {
                "weight": weight,
                "category": "Dependencies",
                "severity": sev,
                "title": f"Vulnerable Dependency: {pkg}" if sev in ("CRITICAL", "HIGH") else f"Outdated Dependency: {pkg}",
                "location": manifest or pkg,
                "file_path": manifest,
                "line_number": 1,
                "description": getattr(dep, "description", ""),
                "recommendation": getattr(dep, "recommendation", f"Update {pkg} to the fixed or latest version."),
            }
        )

    # 4. Circular Architecture Dependencies
    for idx, cycle in enumerate(circular_cycles):
        cycle_str = " -> ".join([c.split("/")[-1] for c in cycle])
        candidates.append(
            {
                "weight": 50,
                "category": "Architecture",
                "severity": "HIGH",
                "title": f"Circular Dependency Loop #{idx + 1}",
                "location": cycle_str,
                "file_path": cycle[0] if cycle else "",
                "line_number": 1,
                "description": f"Circular dependency cycle between modules: {' -> '.join(cycle)}",
                "recommendation": "Decouple modules using dependency injection, interface abstraction, or extract shared functionality.",
            }
        )

    # Sort deterministically: highest weight first, then alphabetically by location
    candidates.sort(key=lambda x: (-x["weight"], x["location"], x["title"]))

    # Assign ranks and slice top items
    result = []
    for rank, item in enumerate(candidates[:limit], start=1):
        item_copy = dict(item)
        item_copy["rank"] = rank
        del item_copy["weight"]
        result.append(item_copy)

    return result
