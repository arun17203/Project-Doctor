import os
import sys
import json
import argparse
from typing import Dict, Any, List

from backend.app.analyzers.scanner import scan_repository
from backend.app.analyzers.security.engine import SecurityAuditEngine
from backend.app.analyzers.dependency.engine import DependencyAuditEngine
from backend.app.analyzers.python_quality import analyze_python_source
from backend.app.analyzers.javascript_quality import analyze_javascript_source
from backend.app.analyzers.health.calculator import (
    calculate_quality_score,
    calculate_security_score,
    calculate_dependency_score,
    calculate_overall_health_score,
)

VERSION = "1.0.0"

# Reconfigure stdout to UTF-8 on Windows consoles to prevent charmap errors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ANSI Color codes for clean terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def compute_letter_grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def scan_directory_cli(target_dir: str) -> Dict[str, Any]:
    """Runs zero-code-execution deterministic static analysis across target directory."""
    abs_path = os.path.abspath(target_dir)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Target directory does not exist: {abs_path}")

    # 1. Structure scan
    scan_meta = scan_repository(abs_path)
    total_files = scan_meta.get("total_files", 0)
    total_lines = scan_meta.get("total_lines", 0)
    languages = scan_meta.get("language_distribution", {})

    # 2. Security Audit
    sec_engine = SecurityAuditEngine()
    sec_results = sec_engine.audit_project(abs_path)
    sec_crit = sec_results.get("critical_count", 0)
    sec_high = sec_results.get("high_count", 0)
    sec_med = sec_results.get("medium_count", 0)
    sec_low = sec_results.get("low_count", 0)
    sec_score = calculate_security_score(sec_crit, sec_high, sec_med, sec_low)

    # 3. Dependency Audit
    dep_engine = DependencyAuditEngine()
    dep_results = dep_engine.audit_project(abs_path)
    dep_vuln = dep_results.get("vulnerable_count", 0)
    dep_outdated = dep_results.get("outdated_count", 0)
    dep_unknown = dep_results.get("unknown_count", 0)
    dep_score = calculate_dependency_score(dep_vuln, dep_outdated, dep_unknown)

    # 4. Quality Audit (Python + JS files)
    qual_crit = 0
    qual_high = 0
    qual_med = 0
    qual_low = 0
    quality_issues: List[Dict[str, Any]] = []

    for root, _, files in os.walk(abs_path):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, abs_path).replace("\\", "/")
            if "node_modules" in rel or ".venv" in rel or "venv" in rel or ".git" in rel:
                continue
            if f.endswith((".py", ".pyw")):
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as src_f:
                        code = src_f.read()
                    res = analyze_python_source(code, rel)
                    for iss in res.get("issues", []):
                        quality_issues.append(iss)
                        sev = iss.get("severity", "LOW")
                        if sev == "CRITICAL":
                            qual_crit += 1
                        elif sev == "HIGH":
                            qual_high += 1
                        elif sev == "MEDIUM":
                            qual_med += 1
                        else:
                            qual_low += 1
                except Exception:
                    pass
            elif f.endswith((".js", ".jsx", ".ts", ".tsx")):
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as src_f:
                        code = src_f.read()
                    res = analyze_javascript_source(code, rel)
                    for iss in res.get("issues", []):
                        quality_issues.append(iss)
                        sev = iss.get("severity", "LOW")
                        if sev == "CRITICAL":
                            qual_crit += 1
                        elif sev == "HIGH":
                            qual_high += 1
                        elif sev == "MEDIUM":
                            qual_med += 1
                        else:
                            qual_low += 1
                except Exception:
                    pass

    qual_score = calculate_quality_score(qual_crit, qual_high, qual_med, qual_low)
    maint_score = qual_score
    arch_score = 100.0

    overall_score = calculate_overall_health_score(
        qual_score,
        sec_score,
        dep_score,
        arch_score,
        maint_score,
    )

    grade = compute_letter_grade(overall_score)

    return {
        "target_directory": abs_path,
        "total_files": total_files,
        "total_lines": total_lines,
        "primary_languages": list(languages.keys())[:3],
        "health_score": round(overall_score, 1),
        "letter_grade": grade,
        "vitals": {
            "security_score": round(sec_score, 1),
            "quality_score": round(qual_score, 1),
            "dependency_score": round(dep_score, 1),
            "maintainability_score": round(maint_score, 1),
        },
        "issues_summary": {
            "security": {
                "critical": sec_crit,
                "high": sec_high,
                "medium": sec_med,
                "low": sec_low,
                "total": sec_results.get("total_issues", 0),
            },
            "quality": {
                "critical": qual_crit,
                "high": qual_high,
                "medium": qual_med,
                "low": qual_low,
                "total": len(quality_issues),
            },
            "dependencies": {
                "vulnerable": dep_vuln,
                "outdated": dep_outdated,
                "total": dep_results.get("total_dependencies", 0),
            },
        },
        "critical_findings": [
            {
                "category": "security",
                "message": f.message,
                "file_path": f.file_path,
                "line": f.line_number,
            }
            for f in sec_results.get("findings", [])[:5]
            if f.severity in ("CRITICAL", "HIGH")
        ],
    }


def print_cli_report(data: Dict[str, Any], fail_under: float) -> int:
    """Prints a beautiful formatted ANSI medical chart report to stdout."""
    score = data["health_score"]
    grade = data["letter_grade"]
    passed = score >= fail_under

    score_color = GREEN if score >= 80 else (YELLOW if score >= 60 else RED)

    print()
    print(f"{BOLD}{CYAN}+===============================================================+{RESET}")
    print(f"{BOLD}{CYAN}|             [+]  PROJECT DOCTOR -- CODEBASE HEALTH            |{RESET}")
    print(f"{BOLD}{CYAN}+===============================================================+{RESET}")
    print(f" Target: {BOLD}{data['target_directory']}{RESET}")
    print(f" Files: {data['total_files']}  |  Lines of Code: {data['total_lines']}  |  Stack: {', '.join(data['primary_languages']) or 'General'}")
    print("-----------------------------------------------------------------")
    print(f" {BOLD}OVERALL HEALTH SCORE:{RESET}  {score_color}{BOLD}{score}/100  (Grade {grade}){RESET}")
    print("-----------------------------------------------------------------")
    print(f" {BOLD}DIAGNOSTIC VITALS:{RESET}")
    print(f"   * Security Audit:       {data['vitals']['security_score']:>5.1f} / 100  ({data['issues_summary']['security']['critical']} Critical, {data['issues_summary']['security']['high']} High)")
    print(f"   * Code Quality:         {data['vitals']['quality_score']:>5.1f} / 100  ({data['issues_summary']['quality']['critical']} Critical, {data['issues_summary']['quality']['high']} High)")
    print(f"   * Dependencies:         {data['vitals']['dependency_score']:>5.1f} / 100  ({data['issues_summary']['dependencies']['vulnerable']} Vulnerable CVEs)")
    print(f"   * Maintainability:      {data['vitals']['maintainability_score']:>5.1f} / 100")

    critical_items = data.get("critical_findings", [])
    if critical_items:
        print("-----------------------------------------------------------------")
        print(f" {BOLD}{RED}TOP URGENT FINDINGS:{RESET}")
        for item in critical_items:
            print(f"   [{item['category'].upper()}] {item['message']}")
            print(f"     -> {item['file_path']}:{item['line']}")

    print("=================================================================")
    if passed:
        print(f" {BOLD}{GREEN}[PASSED] QUALITY GATE PASSED{RESET}: Score {score:.1f} meets threshold ({fail_under:.1f})")
        print()
        return 0
    else:
        print(f" {BOLD}{RED}[FAILED] QUALITY GATE FAILED{RESET}: Score {score:.1f} is below threshold ({fail_under:.1f})")
        print(f" Run 'python -m backend.app.cli scan {data['target_directory']}' or launch Project Doctor web UI for prescriptions.")
        print()
        return 1


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="project-doctor",
        description="Project Doctor CLI: Standalone code health, security, and dependency diagnostics.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    scan_parser = subparsers.add_parser("scan", help="Scan a directory for health, security, and quality issues")
    scan_parser.add_argument("path", nargs="?", default=".", help="Directory to scan (defaults to current directory)")
    scan_parser.add_argument(
        "--fail-under",
        type=float,
        default=70.0,
        help="Minimum overall health score required to pass (default: 70.0)",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON diagnostic result instead of terminal chart",
    )

    args = parser.parse_args(argv)

    if not args.command or args.command == "scan":
        target = getattr(args, "path", ".")
        fail_under = getattr(args, "fail_under", 70.0)
        is_json = getattr(args, "json", False)

        try:
            report_data = scan_directory_cli(target)
            if is_json:
                print(json.dumps(report_data, indent=2))
                return 0 if report_data["health_score"] >= fail_under else 1
            return print_cli_report(report_data, fail_under)
        except Exception as err:
            print(f"{RED}Error during scan: {err}{RESET}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
