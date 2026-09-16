"""
Code Quality Analysis Engine Orchestrator.
Coordinates static analyzers across Python, JavaScript/TypeScript,
duplicate code detection, and TODO/debt scanning.
"""

import os
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.models.project import Project
from backend.app.models.scan import ProjectScan, ProjectFile
from backend.app.analyzers.python_quality import analyze_python_source
from backend.app.analyzers.javascript_quality import analyze_javascript_source
from backend.app.analyzers.duplicate_detector import detect_duplicate_blocks
from backend.app.analyzers.todo_detector import scan_todo_comments

MAX_ANALYSIS_FILE_SIZE = 2 * 1024 * 1024  # 2MB


def run_code_quality_analysis(project: Project, scan: ProjectScan, db: Session) -> Dict[str, Any]:
    """Executes deterministic static code quality analysis on the project files.
    Returns:
    {
        "total_issues": int,
        "critical_count": int,
        "high_count": int,
        "medium_count": int,
        "low_count": int,
        "metrics": Dict[str, Any],
        "issues": List[Dict[str, Any]],
        "files_analyzed": int,
        "files_skipped": int,
    }
    """
    storage_root = project.storage_path
    if not storage_root or not os.path.exists(storage_root):
        raise ValueError(f"Project storage path does not exist on disk: {storage_root}")

    # Fetch all project files from the scan
    files: List[ProjectFile] = (
        db.query(ProjectFile)
        .filter(ProjectFile.scan_id == scan.id)
        .all()
    )

    all_issues: List[Dict[str, Any]] = []
    all_complexities: List[int] = []
    all_lengths: List[int] = []
    total_functions = 0
    total_classes = 0
    unused_imports_count = 0
    todo_comments_count = 0
    unparseable_files = 0
    files_analyzed = 0
    files_skipped = 0

    # Collect source files for cross-file duplicate detection
    source_files_for_duplication: List[Tuple[str, str]] = []

    for file_record in files:
        # Check exclusion rules
        if file_record.is_binary or file_record.is_skipped or file_record.size_bytes > MAX_ANALYSIS_FILE_SIZE:
            files_skipped += 1
            continue

        abs_file_path = os.path.join(storage_root, file_record.file_path)
        if not os.path.exists(abs_file_path) or not os.path.isfile(abs_file_path):
            files_skipped += 1
            continue

        try:
            with open(abs_file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            files_skipped += 1
            continue

        files_analyzed += 1
        rel_path = file_record.file_path
        ext = file_record.extension.lower()

        # 1. TODO / Technical debt comment scanning (for all text source/config/doc files)
        todo_issues = scan_todo_comments(rel_path, content)
        todo_comments_count += len(todo_issues)
        all_issues.extend(todo_issues)

        # 2. Language-specific AST / Structural analysis
        if ext == ".py":
            py_res = analyze_python_source(rel_path, content)
            if not py_res["success"]:
                unparseable_files += 1
                # Record as an informative note issue rather than failing the scan
                all_issues.append({
                    "issue_type": "high_complexity",
                    "severity": "LOW",
                    "file_path": rel_path,
                    "line_number": 1,
                    "end_line": 1,
                    "symbol_name": None,
                    "message": f"Syntax error in '{rel_path}': parsing failed.",
                    "description": py_res.get("error", "Source file could not be parsed via Python AST."),
                    "evidence": py_res.get("error", "SyntaxError"),
                    "recommendation": "Check Python syntax compatibility and resolve syntax errors."
                })
            else:
                all_issues.extend(py_res["issues"])
                total_functions += py_res["stats"]["total_functions"]
                total_classes += py_res["stats"]["total_classes"]
                for func in py_res["functions"]:
                    all_complexities.append(func["complexity"])
                    all_lengths.append(func["line_count"])
                for iss in py_res["issues"]:
                    if iss["issue_type"] == "unused_import":
                        unused_imports_count += 1

            source_files_for_duplication.append((rel_path, content))

        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            js_res = analyze_javascript_source(rel_path, content)
            all_issues.extend(js_res["issues"])
            total_functions += js_res["stats"]["total_functions"]
            total_classes += js_res["stats"]["total_classes"]
            for func in js_res["functions"]:
                all_complexities.append(func["complexity"])
                all_lengths.append(func["line_count"])

            source_files_for_duplication.append((rel_path, content))

        elif ext in (".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php"):
            # Include in duplicate detection, but skip advanced AST
            source_files_for_duplication.append((rel_path, content))

    # 3. Duplicate Code Detection across collected source files
    duplicate_issues = detect_duplicate_blocks(source_files_for_duplication)
    duplicate_blocks_count = len(duplicate_issues)
    all_issues.extend(duplicate_issues)

    # 4. Maintainability Metrics Summary
    avg_complexity = round(sum(all_complexities) / len(all_complexities), 1) if all_complexities else 0.0
    max_complexity = max(all_complexities) if all_complexities else 0
    avg_length = round(sum(all_lengths) / len(all_lengths), 1) if all_lengths else 0.0
    max_length = max(all_lengths) if all_lengths else 0

    metrics = {
        "avg_complexity": avg_complexity,
        "max_complexity": max_complexity,
        "avg_function_length": avg_length,
        "max_function_length": max_length,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "duplicate_blocks_count": duplicate_blocks_count,
        "todo_comments_count": todo_comments_count,
        "unused_imports_count": unused_imports_count,
        "files_analyzed": files_analyzed,
        "files_skipped": files_skipped,
        "unparseable_files": unparseable_files,
    }

    # 5. Tally issue severities
    critical_count = sum(1 for i in all_issues if i["severity"] == "CRITICAL")
    high_count = sum(1 for i in all_issues if i["severity"] == "HIGH")
    medium_count = sum(1 for i in all_issues if i["severity"] == "MEDIUM")
    low_count = sum(1 for i in all_issues if i["severity"] == "LOW")
    total_issues = len(all_issues)

    return {
        "total_issues": total_issues,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "metrics": metrics,
        "issues": all_issues,
        "files_analyzed": files_analyzed,
        "files_skipped": files_skipped,
    }
