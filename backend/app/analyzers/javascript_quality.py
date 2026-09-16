"""
JavaScript and TypeScript Code Quality Analyzer.
Performs deterministic static lexical and structural analysis without code execution.
"""

import re
from typing import List, Dict, Any, Tuple


# Regex patterns to detect function declarations in JS/TS
FUNC_PATTERNS = [
    # regular function: function foo(...) { or async function foo(...) {
    re.compile(r'(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\('),
    # arrow / assigned function: const foo = (...) => { or let foo = function(...) {
    re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>\s*\{'),
    re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s+)?function\s*\('),
    # class method: foo(...) { or async foo(...) {
    re.compile(r'^\s*(?:async\s+)?(?:public\s+|private\s+|protected\s+)?(?:static\s+)?([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*(?::\s*[^\{]+)?\s*\{'),
]

CLASS_PATTERN = re.compile(r'class\s+([a-zA-Z0-9_$]+)')

# Branching keywords for cyclomatic complexity approximation
BRANCH_PATTERN = re.compile(r'\b(if|else\s+if|for|while|catch|case)\b|&&|\|\||\?')
NESTING_START_PATTERN = re.compile(r'\b(if|for|while|switch|try)\b.*\{')


def analyze_javascript_source(file_path: str, source_code: str) -> Dict[str, Any]:
    """Statically analyzes JS/TS source code for complexity, function length, and nesting."""
    lines = source_code.splitlines()
    total_lines = len(lines)

    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

    # 1. Identify classes
    for idx, line in enumerate(lines, start=1):
        m = CLASS_PATTERN.search(line)
        if m:
            classes.append({"name": m.group(1), "lineno": idx})

    # 2. Extract functions by scanning line-by-line and tracking brace balance
    i = 0
    while i < total_lines:
        line = lines[i]
        line_num = i + 1

        func_name = None
        for pattern in FUNC_PATTERNS:
            match = pattern.search(line)
            if match:
                func_name = match.group(1)
                break

        if func_name and "{" in line:
            # Find function closing brace
            start_line = line_num
            brace_count = line.count("{") - line.count("}")
            func_lines = [line]
            current_idx = i + 1

            while current_idx < total_lines and brace_count > 0:
                cur_line = lines[current_idx]
                func_lines.append(cur_line)
                brace_count += cur_line.count("{") - cur_line.count("}")
                current_idx += 1

            end_line = current_idx
            func_body = "\n".join(func_lines)
            line_count = end_line - start_line + 1

            # Compute Cyclomatic Complexity
            # Base 1 + number of branch tokens
            branch_matches = len(BRANCH_PATTERN.findall(func_body))
            complexity = 1 + branch_matches

            # Compute max nesting depth inside function
            max_nesting = 0
            curr_nesting = 0
            deepest_line = start_line

            for f_idx, f_line in enumerate(func_lines, start=start_line):
                # Count block starters
                if NESTING_START_PATTERN.search(f_line):
                    curr_nesting += 1
                    if curr_nesting > max_nesting:
                        max_nesting = curr_nesting
                        deepest_line = f_idx
                if "}" in f_line and curr_nesting > 0:
                    curr_nesting -= f_line.count("}")

            functions.append({
                "name": func_name,
                "lineno": start_line,
                "end_lineno": end_line,
                "line_count": line_count,
                "complexity": complexity,
                "max_nesting_depth": max_nesting,
                "deepest_nesting_line": deepest_line,
            })

            # Check thresholds:
            # High Complexity
            if complexity >= 6:
                if complexity >= 16:
                    sev = "CRITICAL"
                elif complexity >= 11:
                    sev = "HIGH"
                else:
                    sev = "MEDIUM"

                issues.append({
                    "issue_type": "high_complexity",
                    "severity": sev,
                    "file_path": file_path,
                    "line_number": start_line,
                    "end_line": end_line,
                    "symbol_name": func_name,
                    "message": f"Function '{func_name}' has high cyclomatic complexity ({complexity}).",
                    "description": (
                        f"Function '{func_name}' has {complexity} branch decision paths. "
                        "High complexity makes code difficult to review, test, and refactor."
                    ),
                    "evidence": f"Complexity: {complexity} (Threshold: 5)",
                    "recommendation": (
                        "Decompose the function into smaller modular handlers or reduce nested conditionals."
                    )
                })

            # Long Function
            if line_count > 50:
                if line_count >= 151:
                    len_sev = "CRITICAL"
                elif line_count >= 101:
                    len_sev = "HIGH"
                else:
                    len_sev = "MEDIUM"

                issues.append({
                    "issue_type": "long_function",
                    "severity": len_sev,
                    "file_path": file_path,
                    "line_number": start_line,
                    "end_line": end_line,
                    "symbol_name": func_name,
                    "message": f"Function '{func_name}' is unusually long ({line_count} lines).",
                    "description": (
                        f"Function spans {line_count} lines, exceeding the 50-line maintainability standard."
                    ),
                    "evidence": f"Line count: {line_count} (lines {start_line}–{end_line})",
                    "recommendation": "Extract distinct sub-routines or responsibilities into separate functions."
                })

            # Deep Nesting
            if max_nesting >= 4:
                if max_nesting >= 6:
                    nest_sev = "CRITICAL"
                elif max_nesting == 5:
                    nest_sev = "HIGH"
                else:
                    nest_sev = "MEDIUM"

                issues.append({
                    "issue_type": "deep_nesting",
                    "severity": nest_sev,
                    "file_path": file_path,
                    "line_number": deepest_line,
                    "end_line": end_line,
                    "symbol_name": func_name,
                    "message": f"Deeply nested control flow in '{func_name}' (depth {max_nesting}).",
                    "description": (
                        f"Code inside '{func_name}' reaches a nesting depth of {max_nesting}."
                    ),
                    "evidence": f"Nesting depth: {max_nesting} (Threshold: 3)",
                    "recommendation": "Use early returns / guard statements to flatten indentation."
                })

            i = max(i + 1, current_idx - 1)
        i += 1

    complexities = [f["complexity"] for f in functions]
    lengths = [f["line_count"] for f in functions]

    avg_complexity = round(sum(complexities) / len(complexities), 1) if complexities else 0.0
    max_complexity = max(complexities) if complexities else 0
    avg_length = round(sum(lengths) / len(lengths), 1) if lengths else 0.0
    max_length = max(lengths) if lengths else 0

    return {
        "success": True,
        "error": None,
        "functions": functions,
        "classes": classes,
        "issues": issues,
        "stats": {
            "total_functions": len(functions),
            "total_classes": len(classes),
            "avg_complexity": avg_complexity,
            "max_complexity": max_complexity,
            "avg_function_length": avg_length,
            "max_function_length": max_length,
        }
    }
