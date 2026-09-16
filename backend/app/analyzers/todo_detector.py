"""
TODO and Technical Debt Comment Detector.
Scans source files for unresolved task markers such as TODO, FIXME, HACK, BUG, and XXX.
"""

import re
from typing import List, Dict, Any, Tuple

TODO_PATTERN = re.compile(
    r'(?:#|//|/\*|<!--)\s*(TODO|FIXME|HACK|BUG|XXX)(?:\(([^)]+)\))?\s*[:\s-]\s*(.+?)(?:\*/|-->)?$',
    re.IGNORECASE
)


def scan_todo_comments(file_path: str, source_code: str) -> List[Dict[str, Any]]:
    """Scans lines for TODO, FIXME, and HACK comment markers."""
    issues: List[Dict[str, Any]] = []

    for line_num, line in enumerate(source_code.splitlines(), start=1):
        match = TODO_PATTERN.search(line)
        if match:
            tag = match.group(1).upper()
            author = match.group(2)
            comment_body = match.group(3).strip()

            full_comment = f"{tag}: {comment_body}"
            if author:
                full_comment = f"{tag}({author}): {comment_body}"

            # Severity: FIXME and BUG indicate defects/broken functionality -> MEDIUM
            # TODO, HACK, XXX -> LOW
            if tag in ("FIXME", "BUG"):
                severity = "MEDIUM"
            else:
                severity = "LOW"

            issues.append({
                "issue_type": "todo_comment",
                "severity": severity,
                "file_path": file_path,
                "line_number": line_num,
                "end_line": line_num,
                "symbol_name": None,
                "message": f"Unresolved technical debt marker ({tag}).",
                "description": (
                    f"Found an unresolved debt or action marker in source code comment: '{full_comment}'."
                ),
                "evidence": full_comment,
                "recommendation": (
                    "Resolve the noted task or log it in your project's issue tracking system, "
                    "then remove the comment from the codebase."
                )
            })

    return issues
