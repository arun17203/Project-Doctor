import ast
import re
from typing import List, Optional, Any
from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding

JS_DANGEROUS_REGEX = [
    (
        re.compile(r'\beval\s*\('),
        "dangerous_eval",
        "CRITICAL",
        "JavaScript eval() detected",
        "Using `eval()` executes arbitrary code in the caller's privilege context, leading to Remote Code Execution or XSS.",
        "Refactor to use standard JSON parsing (`JSON.parse`) or safe lookup maps instead of eval.",
        "CWE-95",
    ),
    (
        re.compile(r'\bnew\s+Function\s*\('),
        "dangerous_eval",
        "HIGH",
        "JavaScript new Function(...) constructor detected",
        "The Function constructor compiles and runs arbitrary code strings at runtime, similar to eval.",
        "Avoid dynamic code generation. Use predefined functions or closures.",
        "CWE-95",
    ),
    (
        re.compile(r'dangerouslySetInnerHTML\s*=\s*\{'),
        "dangerous_eval",
        "HIGH",
        "React dangerouslySetInnerHTML detected",
        "Setting HTML directly bypasses React's built-in XSS protections and exposes the application to DOM-based Cross-Site Scripting.",
        "Sanitize HTML content using DOMPurify or render trusted JSX elements directly.",
        "CWE-79",
    ),
]


class DangerousCallsRule(BaseSecurityRule):
    rule_id = "SEC-DANG-001"
    category = "DANGEROUS_CALLS"
    cwe_id = "CWE-95"
    owasp_category = "A03:2021-Injection"

    def run(
        self,
        file_path: str,
        content: str,
        ext: str,
        ast_tree: Optional[Any] = None,
    ) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []

        if ext == ".py" and ast_tree:
            findings.extend(self._analyze_python_ast(file_path, content, ast_tree))
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            findings.extend(self._analyze_js_regex(file_path, content))

        return findings

    def _analyze_python_ast(
        self, file_path: str, content: str, tree: ast.AST
    ) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        lines = content.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            callee = ""
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                callee = node.func.id
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"eval", "exec"}
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"builtins", "__builtins__"}
            ):
                callee = node.func.attr

            if callee:
                line_no = getattr(node, "lineno", 1)
                evidence = lines[line_no - 1].strip() if 1 <= line_no <= len(lines) else ""
                arg_is_dynamic = node.args and not isinstance(node.args[0], ast.Constant)

                findings.append(
                    SecurityFinding(
                        issue_type="dangerous_eval",
                        severity="CRITICAL" if arg_is_dynamic else "HIGH",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=line_no,
                        category=self.category,
                        message=f"Use of dangerous dynamic execution function `{callee}()`",
                        description=(
                            f"`{callee}()` dynamically evaluates arbitrary code strings. "
                            "If untrusted data or user input reaches this call, attackers can execute arbitrary commands or access memory."
                        ),
                        evidence=evidence,
                        recommendation=(
                            "Replace `eval()` with `ast.literal_eval()` for safely evaluating literal data structures, "
                            "or redesign the logic to use dictionaries/dispatch tables instead of arbitrary code execution."
                        ),
                        cwe_id="CWE-95",
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )

        return findings

    def _analyze_js_regex(self, file_path: str, content: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            for pattern, issue_type, severity, msg, desc, rec, cwe in JS_DANGEROUS_REGEX:
                if pattern.search(stripped):
                    findings.append(
                        SecurityFinding(
                            issue_type=issue_type,
                            severity=severity,
                            confidence="HIGH",
                            file_path=file_path,
                            line_number=idx,
                            category=self.category,
                            message=msg,
                            description=desc,
                            evidence=stripped,
                            recommendation=rec,
                            cwe_id=cwe,
                            owasp_category=self.owasp_category,
                            rule_id=self.rule_id,
                        )
                    )

        return findings
