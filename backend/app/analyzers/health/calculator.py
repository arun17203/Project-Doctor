from typing import Dict, Any


DEFAULT_WEIGHTS: Dict[str, float] = {
    "security": 0.30,
    "quality": 0.25,
    "maintainability": 0.20,
    "dependencies": 0.15,
    "architecture": 0.10,
}


def calculate_quality_score(critical: int, high: int, medium: int, low: int) -> float:
    """Calculate Code Quality Score (0-100) based on Stage 5 quality findings.
    Baseline: 100 points
    Penalties:
      - Critical: -12 pts
      - High: -7 pts
      - Medium: -3 pts
      - Low: -1 pt
    Clamped to [0.0, 100.0].
    """
    penalty = (critical * 12.0) + (high * 7.0) + (medium * 3.0) + (low * 1.0)
    score = 100.0 - penalty
    return max(0.0, min(100.0, round(score, 1)))


def calculate_security_score(critical: int, high: int, medium: int, low: int) -> float:
    """Calculate Security Score (0-100) based on Stage 6 static security findings.
    Baseline: 100 points
    Penalties:
      - Critical: -25 pts (SQLi, command injection, leaked credentials)
      - High: -15 pts (eval/exec, dangerous dynamic code)
      - Medium: -7 pts (insecure config, weak crypto)
      - Low: -2 pts
    Clamped to [0.0, 100.0].
    """
    penalty = (critical * 25.0) + (high * 15.0) + (medium * 7.0) + (low * 2.0)
    score = 100.0 - penalty
    return max(0.0, min(100.0, round(score, 1)))


def calculate_dependency_score(vulnerable_count: int, outdated_count: int, unknown_count: int) -> float:
    """Calculate Dependency Score (0-100) based on Stage 7 dependency audit.
    Baseline: 100 points
    Penalties:
      - Vulnerable dependency: -15 pts each
      - Outdated dependency: -3 pts each
      - Unknown dependency: -1 pt each
    Clamped to [0.0, 100.0]. Up-to-date dependencies have 0 penalty.
    """
    penalty = (vulnerable_count * 15.0) + (outdated_count * 3.0) + (unknown_count * 1.0)
    score = 100.0 - penalty
    return max(0.0, min(100.0, round(score, 1)))


def calculate_architecture_score(circular_cycles_count: int) -> float:
    """Calculate Architecture Score (0-100) based on Stage 8 architecture graph.
    Baseline: 100 points
    Penalties:
      - Circular dependency loop: -10 pts each
    Clamped to [0.0, 100.0].
    """
    penalty = circular_cycles_count * 10.0
    score = 100.0 - penalty
    return max(0.0, min(100.0, round(score, 1)))


def calculate_maintainability_score(
    quality_metrics: Dict[str, Any],
    total_code_lines: int,
    total_files: int,
) -> float:
    """Calculate Maintainability Score (0-100) based on Stage 4 and Stage 5 structural metrics.
    Factors:
      - Average cyclomatic complexity
      - High complexity finding count
      - Average function length
      - Large functions count (>50 lines)
      - Duplicate code blocks
      - TODO/FIXME markers
    Clamped to [0.0, 100.0].
    """
    total_penalty = 0.0

    # 1. Average Cyclomatic Complexity
    avg_complexity = float(quality_metrics.get("avg_cyclomatic_complexity", 1.0))
    if avg_complexity > 15.0:
        total_penalty += 30.0
    elif avg_complexity > 10.0:
        total_penalty += 20.0
    elif avg_complexity > 5.0:
        total_penalty += 10.0

    # High complexity functions finding count
    high_complexity_count = int(quality_metrics.get("high_complexity_count", 0))
    total_penalty += min(25.0, high_complexity_count * 5.0)

    # 2. Function Length
    avg_func_len = float(quality_metrics.get("avg_function_length", 15.0))
    if avg_func_len > 60.0:
        total_penalty += 20.0
    elif avg_func_len > 30.0:
        total_penalty += 10.0

    large_functions_count = int(quality_metrics.get("large_functions_count", 0))
    total_penalty += min(20.0, large_functions_count * 3.0)

    # 3. Code Duplication
    duplicate_blocks = int(quality_metrics.get("duplicate_blocks_count", 0))
    total_penalty += min(20.0, duplicate_blocks * 4.0)

    # 4. Technical Debt comments (TODO / FIXME)
    todos_count = int(quality_metrics.get("todos_count", 0))
    total_penalty += min(10.0, todos_count * 1.0)

    score = 100.0 - total_penalty
    return max(0.0, min(100.0, round(score, 1)))


def calculate_testing_score(
    test_files_count: int,
    total_files: int,
    config_files_count: int = 0,
    doc_files_count: int = 0,
) -> float:
    """Estimate Testing Health Score (0-100) based on repository scan data.
    Clearly labeled 'Testing Health' (not code coverage).
    """
    if test_files_count <= 0:
        return 0.0

    source_files = max(1, total_files - config_files_count - doc_files_count - test_files_count)
    ratio = test_files_count / source_files

    if ratio >= 0.5:  # 1 test file for every 2 source files is considered excellent
        return 100.0

    # Scale linearly between 10.0 and 100.0
    score = (ratio / 0.5) * 100.0
    return max(10.0, min(100.0, round(score, 1)))


def calculate_overall_health_score(
    security_score: float,
    quality_score: float,
    maintainability_score: float,
    dependency_score: float,
    architecture_score: float,
    weights: Dict[str, float] = None,
) -> float:
    """Calculate weighted Overall Project Health Score (0-100).
    Weights:
      Security: 30%
      Quality: 25%
      Maintainability: 20%
      Dependencies: 15%
      Architecture: 10%
    """
    w = weights or DEFAULT_WEIGHTS
    overall = (
        (security_score * w.get("security", 0.30))
        + (quality_score * w.get("quality", 0.25))
        + (maintainability_score * w.get("maintainability", 0.20))
        + (dependency_score * w.get("dependencies", 0.15))
        + (architecture_score * w.get("architecture", 0.10))
    )
    return max(0.0, min(100.0, round(overall, 1)))


def interpret_health_status(overall_score: float) -> str:
    """Map numeric score (0-100) to qualitative diagnostic status."""
    if overall_score >= 90.0:
        return "Excellent"
    elif overall_score >= 80.0:
        return "Good"
    elif overall_score >= 70.0:
        return "Fair"
    elif overall_score >= 50.0:
        return "Needs Attention"
    else:
        return "Critical"
