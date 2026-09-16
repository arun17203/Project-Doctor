from typing import Dict, Any, List


def generate_score_explanations(
    overall_score: float,
    status: str,
    quality_score: float,
    security_score: float,
    dependency_score: float,
    architecture_score: float,
    maintainability_score: float,
    testing_score: float,
    quality_counts: Dict[str, int],
    security_counts: Dict[str, int],
    dependency_counts: Dict[str, int],
    circular_cycles_count: int,
) -> Dict[str, Any]:
    """Generate deterministic diagnostic explanations for the calculated scores.
    Zero AI used.
    """
    why_items: List[str] = []
    category_drivers: Dict[str, List[str]] = {
        "security": [],
        "quality": [],
        "dependencies": [],
        "architecture": [],
        "maintainability": [],
        "testing": [],
    }

    # 1. Security Drivers
    sec_crit = security_counts.get("critical", 0)
    sec_high = security_counts.get("high", 0)
    sec_med = security_counts.get("medium", 0)
    sec_low = security_counts.get("low", 0)

    if sec_crit > 0 or sec_high > 0:
        pts_lost = (sec_crit * 25) + (sec_high * 15)
        msg = f"Security score reduced by {pts_lost} points due to {sec_crit} critical and {sec_high} high severity vulnerability findings."
        why_items.append(msg)
        category_drivers["security"].append(msg)
    elif sec_med > 0 or sec_low > 0:
        pts_lost = (sec_med * 7) + (sec_low * 2)
        msg = f"Security score reduced slightly by {pts_lost} points across {sec_med + sec_low} medium/low severity security items."
        category_drivers["security"].append(msg)
    else:
        msg = "Security remained at 100 points: zero hardcoded secrets, SQL injection, or command injection vulnerabilities detected."
        category_drivers["security"].append(msg)

    # 2. Quality Drivers
    qual_crit = quality_counts.get("critical", 0)
    qual_high = quality_counts.get("high", 0)
    qual_med = quality_counts.get("medium", 0)
    qual_low = quality_counts.get("low", 0)

    if qual_crit > 0 or qual_high > 0:
        pts_lost = (qual_crit * 12) + (qual_high * 7)
        msg = f"Code quality reduced by {pts_lost} points due to {qual_crit} critical and {qual_high} high complexity/duplication issues."
        why_items.append(msg)
        category_drivers["quality"].append(msg)
    elif qual_med > 0 or qual_low > 0:
        pts_lost = (qual_med * 3) + (qual_low * 1)
        msg = f"Code quality reduced slightly by {pts_lost} points across minor formatting and complexity findings."
        category_drivers["quality"].append(msg)
    else:
        msg = "Code quality remained at 100 points: clean control flow, no duplicate blocks, and compliant function lengths."
        category_drivers["quality"].append(msg)

    # 3. Dependency Drivers
    vuln_count = dependency_counts.get("vulnerable", 0)
    outdated_count = dependency_counts.get("outdated", 0)
    unknown_count = dependency_counts.get("unknown", 0)

    if vuln_count > 0:
        pts_lost = vuln_count * 15
        msg = f"Dependencies reduced by {pts_lost} points due to {vuln_count} confirmed vulnerable packages from Google OSV advisories."
        why_items.append(msg)
        category_drivers["dependencies"].append(msg)
    elif outdated_count > 0:
        msg = f"Dependencies score at {dependency_score}/100: {outdated_count} packages have newer versions available in upstream package registries."
        category_drivers["dependencies"].append(msg)
    else:
        msg = "Dependencies remained at 100 points: all declared direct packages are current with zero known CVE advisories."
        category_drivers["dependencies"].append(msg)

    # 4. Architecture Drivers
    if circular_cycles_count > 0:
        pts_lost = circular_cycles_count * 10
        msg = f"Architecture score reduced by {pts_lost} points due to {circular_cycles_count} circular dependency loop(s)."
        why_items.append(msg)
        category_drivers["architecture"].append(msg)
    else:
        msg = "Architecture remained at 100 points: clean directional module imports with zero circular dependency loops."
        category_drivers["architecture"].append(msg)

    # 5. Maintainability Drivers
    if maintainability_score >= 90:
        category_drivers["maintainability"].append("High maintainability: low cyclomatic complexity and well-proportioned function sizes.")
    elif maintainability_score >= 70:
        category_drivers["maintainability"].append("Fair maintainability: code is generally readable but contains localized functions with higher complexity.")
    else:
        msg = f"Maintainability reduced to {maintainability_score}/100 due to elevated average cyclomatic complexity and large functions."
        why_items.append(msg)
        category_drivers["maintainability"].append(msg)

    # 6. Testing Drivers
    if testing_score >= 80:
        category_drivers["testing"].append(f"Strong testing health ({testing_score}/100): comprehensive test file suite detected relative to source modules.")
    elif testing_score > 0:
        category_drivers["testing"].append(f"Moderate testing health ({testing_score}/100): automated tests exist but test-to-source file ratio can be improved.")
    else:
        category_drivers["testing"].append("Testing score at 0/100: no automated unit or integration test files were detected in the repository.")

    # If no major negative drivers were added to why_items, provide positive summary
    if not why_items:
        why_items.append(f"Project achieved a {status} score of {overall_score}/100 across all diagnostic dimensions with minimal structural issues.")

    return {
        "summary": f"Overall Health Score is {overall_score}/100 ({status}).",
        "why_breakdown": why_items,
        "category_drivers": category_drivers,
    }
