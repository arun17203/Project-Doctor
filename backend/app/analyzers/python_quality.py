"""
Python AST Code Quality Analyzer.
Performs purely static analysis using Python's built-in `ast` module.
Never executes analyzed code.
"""

import ast
from typing import List, Dict, Any, Optional, Tuple


class PythonASTQualityVisitor(ast.NodeVisitor):
    """AST visitor that computes:
    - Cyclomatic complexity per function/method
    - Function lengths
    - Maximum control-flow nesting depth
    - Classes and functions inventory
    """

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_lines = source_code.splitlines()
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.current_function_stack: List[str] = []
        self.current_class_stack: List[str] = []

    def _get_node_name(self, node: ast.AST) -> str:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return node.name
        return "<unknown>"

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append({
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
        })
        self.current_class_stack.append(node.name)
        self.generic_visit(node)
        self.current_class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._analyze_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._analyze_function(node)

    def _analyze_function(self, node: ast.AST):
        func_name = getattr(node, "name", "<anonymous>")
        if self.current_class_stack:
            full_name = f"{self.current_class_stack[-1]}.{func_name}"
        else:
            full_name = func_name

        lineno = getattr(node, "lineno", 1)
        end_lineno = getattr(node, "end_lineno", lineno)
        line_count = max(1, end_lineno - lineno + 1)

        # Calculate Cyclomatic Complexity
        complexity = self._calculate_cyclomatic_complexity(node)

        # Calculate Max Nesting Depth
        max_depth, deep_line = self._calculate_max_nesting(node)

        self.functions.append({
            "name": full_name,
            "lineno": lineno,
            "end_lineno": end_lineno,
            "line_count": line_count,
            "complexity": complexity,
            "max_nesting_depth": max_depth,
            "deepest_nesting_line": deep_line or lineno,
        })

        self.current_function_stack.append(full_name)
        self.generic_visit(node)
        self.current_function_stack.pop()

    def _calculate_cyclomatic_complexity(self, func_node: ast.AST) -> int:
        """Calculates McCabe cyclomatic complexity:
        Base = 1
        +1 for each branch/decision point:
        if, elif (in Python AST is an If in orelse), for, while,
        and, or, except handler, assert, with, comprehension ifs,
        ternary IfExp, match_case.
        """
        complexity = 1

        for child in ast.walk(func_node):
            if child is func_node:
                continue

            # Don't recurse into inner nested functions here to attribute complexity cleanly
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With) or isinstance(child, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.IfExp):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # e.g. a and b and c -> 2 decision points (len(values) - 1)
                complexity += max(1, len(child.values) - 1)
            elif isinstance(child, ast.comprehension):
                complexity += len(child.ifs)
            elif hasattr(ast, "match_case") and isinstance(child, ast.match_case):
                complexity += 1

        return complexity

    def _calculate_max_nesting(self, func_node: ast.AST) -> Tuple[int, Optional[int]]:
        """Calculates maximum block nesting depth inside a function.
        Blocks considered: If, For, While, Try, With, Match.
        Returns (max_depth, line_where_max_depth_reached).
        """
        control_blocks = (
            ast.If, ast.For, ast.AsyncFor, ast.While,
            ast.Try, ast.With, ast.AsyncWith
        )
        if hasattr(ast, "Match"):
            control_blocks = control_blocks + (ast.Match,)

        max_depth = 0
        deepest_line = None

        def recurse(node: ast.AST, current_depth: int):
            nonlocal max_depth, deepest_line
            # Skip nested functions
            if node is not func_node and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return

            if isinstance(node, control_blocks):
                current_depth += 1
                if current_depth > max_depth:
                    max_depth = current_depth
                    deepest_line = getattr(node, "lineno", None)

            for child in ast.iter_child_nodes(node):
                recurse(child, current_depth)

        recurse(func_node, 0)
        return max_depth, deepest_line


class PythonImportCollector(ast.NodeVisitor):
    """Collects all imports and tracks variable name references to identify unused imports."""

    def __init__(self):
        # imported_names maps alias_name -> (original_name, line_number)
        self.imported_names: Dict[str, Tuple[str, int]] = {}
        # set of all identifier names read in the file
        self.used_names: set = set()
        self.has_star_import = False
        self.all_attribute = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            # For dotted import without alias like 'import os.path', base name 'os' is accessed
            base_name = name.split(".")[0]
            self.imported_names[base_name] = (alias.name, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            if alias.name == "*":
                self.has_star_import = True
                continue
            name = alias.asname or alias.name
            self.imported_names[name] = (alias.name, node.lineno)

    def visit_Name(self, node: ast.Name):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self.used_names.add(node.attr)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Check if __all__ is assigned
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            self.used_names.add(elt.value)
        self.generic_visit(node)


def analyze_python_source(file_path: str, source_code: str) -> Dict[str, Any]:
    """Statically parses and analyzes a single Python source file.
    Returns:
    {
        "success": bool,
        "error": Optional[str],
        "functions": List[Dict],
        "classes": List[Dict],
        "issues": List[Dict],
        "stats": Dict
    }
    """
    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}",
            "functions": [],
            "classes": [],
            "issues": [],
            "stats": {
                "total_functions": 0,
                "total_classes": 0,
                "avg_complexity": 0.0,
                "max_complexity": 0,
                "avg_function_length": 0.0,
                "max_function_length": 0,
            }
        }

    visitor = PythonASTQualityVisitor(file_path, source_code)
    visitor.visit(tree)

    issues: List[Dict[str, Any]] = []

    # 1. Evaluate Complexity & Length & Nesting per function
    for func in visitor.functions:
        complexity = func["complexity"]
        line_count = func["line_count"]
        nesting = func["max_nesting_depth"]
        func_name = func["name"]
        line = func["lineno"]
        end_line = func["end_lineno"]

        # High Complexity Rule:
        # 1-5 = Normal, 6-10 = Medium, 11-15 = High, 16+ = Critical
        if complexity >= 6:
            if complexity >= 16:
                severity = "CRITICAL"
            elif complexity >= 11:
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            issues.append({
                "issue_type": "high_complexity",
                "severity": severity,
                "file_path": file_path,
                "line_number": line,
                "end_line": end_line,
                "symbol_name": func_name,
                "message": f"Function '{func_name}' has high cyclomatic complexity ({complexity}).",
                "description": (
                    f"This function has {complexity} independent decision paths. "
                    "Functions with high cyclomatic complexity are difficult to understand, test, "
                    "and maintain, and have a significantly higher risk of defect introduction."
                ),
                "evidence": f"Complexity: {complexity} (Threshold: 5)",
                "recommendation": (
                    "Split the function into smaller, single-purpose helper functions or "
                    "replace complex nested conditional logic with polymorphism or dictionary lookups."
                )
            })

        # Long Function Rule:
        # <= 50 = Normal, 51-100 = Medium, 101-150 = High, 151+ = Critical
        if line_count > 50:
            if line_count >= 151:
                len_severity = "CRITICAL"
            elif line_count >= 101:
                len_severity = "HIGH"
            else:
                len_severity = "MEDIUM"

            issues.append({
                "issue_type": "long_function",
                "severity": len_severity,
                "file_path": file_path,
                "line_number": line,
                "end_line": end_line,
                "symbol_name": func_name,
                "message": f"Function '{func_name}' is unusually long ({line_count} lines).",
                "description": (
                    f"Function '{func_name}' spans {line_count} lines of code. "
                    "Long functions typically violate the Single Responsibility Principle, "
                    "making them error-prone and arduous to test."
                ),
                "evidence": f"Line count: {line_count} (lines {line}–{end_line})",
                "recommendation": (
                    "Decompose this function using the Extract Method refactoring pattern "
                    "to isolate distinct logical steps into cohesive helper functions."
                )
            })

        # Deep Nesting Rule:
        # 1-3 = Normal, 4 = Medium, 5 = High, 6+ = Critical
        if nesting >= 4:
            if nesting >= 6:
                nest_severity = "CRITICAL"
            elif nesting == 5:
                nest_severity = "HIGH"
            else:
                nest_severity = "MEDIUM"

            issues.append({
                "issue_type": "deep_nesting",
                "severity": nest_severity,
                "file_path": file_path,
                "line_number": func["deepest_nesting_line"] or line,
                "end_line": end_line,
                "symbol_name": func_name,
                "message": f"Deeply nested control structures in '{func_name}' (depth {nesting}).",
                "description": (
                    f"Code inside function '{func_name}' reaches a nesting depth of {nesting}. "
                    "Deeply nested blocks create high cognitive burden and complicate debugging."
                ),
                "evidence": f"Nesting depth: {nesting} (Threshold: 3)",
                "recommendation": (
                    "Refactor with guard clauses (early returns) or extract inner loops/blocks "
                    "into separate functions to flatten control flow."
                )
            })

    # 2. Evaluate Unused Imports
    # Skip __init__.py because it frequently re-exports symbols
    is_init_file = file_path.endswith("__init__.py")
    if not is_init_file:
        import_collector = PythonImportCollector()
        import_collector.visit(tree)

        if not import_collector.has_star_import:
            for imported_alias, (orig_name, import_line) in import_collector.imported_names.items():
                # If imported_alias is not in used_names (and wasn't part of the import node itself)
                # Note: PythonImportCollector collects names in AST. We need to ensure imported_alias
                # is actually used outside the import statements.
                # Since Name visitor visited the entire tree including function bodies:
                # We can count how many times it appeared, or check if it was loaded.
                # A clean check: count occurrences in used_names:
                if imported_alias not in import_collector.used_names:
                    issues.append({
                        "issue_type": "unused_import",
                        "severity": "LOW",
                        "file_path": file_path,
                        "line_number": import_line,
                        "end_line": import_line,
                        "symbol_name": orig_name,
                        "message": f"Unused import '{orig_name}'.",
                        "description": (
                            f"Module '{orig_name}' (imported as '{imported_alias}') is never referenced "
                            "in this file."
                        ),
                        "evidence": f"Import: {orig_name}",
                        "recommendation": "Remove this unused import to keep the namespace clean and improve load time."
                    })

    # 3. Calculate summary metrics
    complexities = [f["complexity"] for f in visitor.functions]
    lengths = [f["line_count"] for f in visitor.functions]

    avg_complexity = round(sum(complexities) / len(complexities), 1) if complexities else 0.0
    max_complexity = max(complexities) if complexities else 0
    avg_length = round(sum(lengths) / len(lengths), 1) if lengths else 0.0
    max_length = max(lengths) if lengths else 0

    return {
        "success": True,
        "error": None,
        "functions": visitor.functions,
        "classes": visitor.classes,
        "issues": issues,
        "stats": {
            "total_functions": len(visitor.functions),
            "total_classes": len(visitor.classes),
            "avg_complexity": avg_complexity,
            "max_complexity": max_complexity,
            "avg_function_length": avg_length,
            "max_function_length": max_length,
        }
    }
