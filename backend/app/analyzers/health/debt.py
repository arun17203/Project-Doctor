from typing import List, Dict, Any


HOURS_PER_SEVERITY = {
    "CRITICAL": 8.0,
    "HIGH": 4.0,
    "MEDIUM": 2.0,
    "LOW": 1.0,
    "INFO": 0.5,
}

HOURS_VULNERABLE_DEP = 4.0
HOURS_OUTDATED_DEP = 1.0
HOURS_CIRCULAR_CYCLE = 4.0


def calculate_technical_debt(
    quality_issues: List[Any],
    security_issues: List[Any],
    vulnerable_deps_count: int,
    outdated_deps_count: int,
    circular_cycles_count: int,
) -> Dict[str, float]:
    """Calculate technical debt in estimated remediation hours based on actual findings.
    Zero double counting.
    Returns:
      {
        "quality_hours": float,
        "security_hours": float,
        "dependency_hours": float,
        "architecture_hours": float,
        "total_hours": float
      }
    """
    # 1. Quality Debt
    quality_hours = 0.0
    for issue in quality_issues:
        sev = getattr(issue, "severity", "LOW").upper()
        quality_hours += HOURS_PER_SEVERITY.get(sev, 1.0)

    # 2. Security Debt
    security_hours = 0.0
    for issue in security_issues:
        sev = getattr(issue, "severity", "LOW").upper()
        security_hours += HOURS_PER_SEVERITY.get(sev, 1.0)

    # 3. Dependency Debt
    dep_hours = (vulnerable_deps_count * HOURS_VULNERABLE_DEP) + (outdated_deps_count * HOURS_OUTDATED_DEP)

    # 4. Architecture Debt
    arch_hours = circular_cycles_count * HOURS_CIRCULAR_CYCLE

    total_hours = quality_hours + security_hours + dep_hours + arch_hours

    return {
        "quality_hours": round(quality_hours, 1),
        "security_hours": round(security_hours, 1),
        "dependency_hours": round(dep_hours, 1),
        "architecture_hours": round(arch_hours, 1),
        "total_hours": round(total_hours, 1),
    }
