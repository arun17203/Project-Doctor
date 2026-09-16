import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawImport:
    source_file: str
    imported_module: str
    imported_names: List[str] = field(default_factory=list)
    is_relative: bool = False
    level: int = 0
    line_number: int = 1


# Regex patterns for JavaScript / TypeScript imports and requires
# 1. import ... from 'module'
# 2. import 'module'
# 3. const/let/var x = require('module')
# 4. import('module')
# 5. export * from 'module'
# 6. export { x } from 'module'
JS_TS_IMPORT_REGEXES = [
    # import ... from '...' or export ... from '...'
    re.compile(r"""(?:import|export)\s+(?:(?:[\w*\s{},$]+)\s+from\s+)?['"]([^'"]+)['"]"""),
    # require('...')
    re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    # dynamic import('...')
    re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
]


def _extract_from_ast(tree: ast.AST, file_path: str) -> List[RawImport]:
    raw_imports: List[RawImport] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                raw_imports.append(
                    RawImport(
                        source_file=file_path,
                        imported_module=alias.name,
                        imported_names=[alias.name],
                        is_relative=False,
                        level=0,
                        line_number=getattr(node, "lineno", 1),
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            names = [alias.name for alias in node.names]
            raw_imports.append(
                RawImport(
                    source_file=file_path,
                    imported_module=module_name,
                    imported_names=names,
                    is_relative=(node.level > 0),
                    level=node.level,
                    line_number=getattr(node, "lineno", 1),
                )
            )
    return raw_imports


def _fallback_python_import_parser(content: str, file_path: str) -> List[RawImport]:
    raw_imports: List[RawImport] = []
    lines = content.splitlines()
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            try:
                sub_tree = ast.parse(stripped)
                for node in ast.walk(sub_tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            raw_imports.append(
                                RawImport(
                                    source_file=file_path,
                                    imported_module=alias.name,
                                    imported_names=[alias.name],
                                    is_relative=False,
                                    level=0,
                                    line_number=line_no,
                                )
                            )
                    elif isinstance(node, ast.ImportFrom):
                        raw_imports.append(
                            RawImport(
                                source_file=file_path,
                                imported_module=node.module or "",
                                imported_names=[alias.name for alias in node.names],
                                is_relative=(node.level > 0),
                                level=node.level,
                                line_number=line_no,
                            )
                        )
            except Exception:
                match_from = re.match(r"^from\s+([.\w]+)\s+import\s+(.+)$", stripped)
                if match_from:
                    mod = match_from.group(1).lstrip(".")
                    raw_imports.append(
                        RawImport(
                            source_file=file_path,
                            imported_module=mod,
                            is_relative=match_from.group(1).startswith("."),
                            level=len(match_from.group(1)) - len(match_from.group(1).lstrip(".")),
                            line_number=line_no,
                        )
                    )
                else:
                    match_imp = re.match(r"^import\s+([a-zA-Z0-9_.,\s]+)$", stripped)
                    if match_imp:
                        for part in match_imp.group(1).split(","):
                            clean_mod = part.strip().split()[0] if part.strip() else ""
                            if clean_mod and clean_mod.isidentifier():
                                raw_imports.append(
                                    RawImport(
                                        source_file=file_path,
                                        imported_module=clean_mod,
                                        imported_names=[clean_mod],
                                        line_number=line_no,
                                    )
                                )
    return raw_imports


def parse_python_imports(content: str, file_path: str) -> List[RawImport]:
    """Statically parse Python imports using ast.parse.
    Zero code execution. Falls back to line-by-line parsing if syntax errors exist.
    """
    try:
        tree = ast.parse(content, filename=file_path)
        return _extract_from_ast(tree, file_path)
    except (SyntaxError, ValueError, TypeError):
        return _fallback_python_import_parser(content, file_path)


def parse_js_ts_imports(content: str, file_path: str) -> List[RawImport]:
    """Statically parse JavaScript and TypeScript imports using regular expressions.
    Zero code execution.
    """
    raw_imports: List[RawImport] = []
    seen = set()

    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        for regex in JS_TS_IMPORT_REGEXES:
            for match in regex.finditer(line):
                mod = match.group(1).strip()
                if mod and mod not in seen:
                    seen.add(mod)
                    raw_imports.append(
                        RawImport(
                            source_file=file_path,
                            imported_module=mod,
                            is_relative=mod.startswith("."),
                            level=1 if mod.startswith("./") else (2 if mod.startswith("../") else 0),
                            line_number=line_no,
                        )
                    )

    return raw_imports


def extract_file_imports(content: str, file_path: str, language: str) -> List[RawImport]:
    """Extract raw import statements based on language."""
    lang_lower = language.lower()
    if lang_lower == "python":
        return parse_python_imports(content, file_path)
    elif lang_lower in {"javascript", "typescript", "jsx", "tsx"}:
        return parse_js_ts_imports(content, file_path)
    return []
