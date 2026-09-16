import ast
import re
from typing import List, Optional, Any
from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding


SQL_KEYWORDS = re.compile(
    r'(?i)\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+TABLE|ALTER\s+TABLE|UNION\s+SELECT|WHERE)\b'
)

# JavaScript / TypeScript query patterns: db.query(`SELECT ... ${...}`), etc.
JS_SQL_TEMPLATE_REGEX = re.compile(
    r'(?:db|connection|pool|client)\.(?:query|execute)\s*\(\s*`[^`]*\$\{[^}]+\}[^`]*`',
    re.IGNORECASE,
)
JS_SQL_CONCAT_REGEX = re.compile(
    r'(?:db|connection|pool|client)\.(?:query|execute)\s*\(\s*["\'][^"\']*(?:SELECT|UPDATE|INSERT|DELETE)[^"\']*["\']\s*\+',
    re.IGNORECASE,
)

# JS child_process command execution
JS_EXEC_REGEX = re.compile(
    r'\b(?:child_process\.)?(?:exec|execSync)\s*\(\s*(?!["\'][^"\']*["\']\s*[,)])',
    re.IGNORECASE,
)


class SQLInjectionRule(BaseSecurityRule):
    rule_id = "SEC-SQLI-001"
    category = "INJECTION"
    cwe_id = "CWE-89"
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

            # Identify if the call looks like database execution
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name not in {"execute", "executemany", "raw", "raw_query"}:
                continue

            if not node.args:
                continue

            first_arg = node.args[0]
            is_vulnerable = False
            vuln_type = ""

            # Check 1: f-string used as query: f"SELECT ... {val}"
            if isinstance(first_arg, ast.JoinedStr):
                # Verify if f-string contains SQL keywords
                raw_fragments = [
                    part.value for part in first_arg.values if isinstance(part, ast.Constant) and isinstance(part.value, str)
                ]
                combined = " ".join(raw_fragments)
                if SQL_KEYWORDS.search(combined):
                    is_vulnerable = True
                    vuln_type = "formatted string (f-string)"

            # Check 2: String concatenation: "SELECT ... " + var
            elif isinstance(first_arg, ast.BinOp):
                if isinstance(first_arg.op, ast.Add):
                    is_vulnerable = True
                    vuln_type = "string concatenation (+)"
                elif isinstance(first_arg.op, ast.Mod):
                    # % operator: "SELECT ... %s" % var (unsafe if not parameterized via driver)
                    is_vulnerable = True
                    vuln_type = "string formatting (% operator)"

            # Check 3: .format() call: "SELECT ... {}".format(var)
            elif isinstance(first_arg, ast.Call):
                if (
                    isinstance(first_arg.func, ast.Attribute)
                    and first_arg.func.attr == "format"
                    and isinstance(first_arg.func.value, ast.Constant)
                    and isinstance(first_arg.func.value.value, str)
                    and SQL_KEYWORDS.search(first_arg.func.value.value)
                ):
                    is_vulnerable = True
                    vuln_type = ".format() string substitution"

            if is_vulnerable:
                line_no = getattr(node, "lineno", 1)
                evidence = lines[line_no - 1].strip() if 1 <= line_no <= len(lines) else ""
                findings.append(
                    SecurityFinding(
                        issue_type="sql_injection",
                        severity="CRITICAL",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=line_no,
                        category=self.category,
                        message=f"Potential SQL injection via dynamic {vuln_type}",
                        description=(
                            f"Dynamic SQL query construction detected in '{func_name}()' call. "
                            "Constructing SQL queries by concatenating or formatting variables directly allows attackers "
                            "to alter query logic, bypass authentication, and access or destroy unauthorized database records."
                        ),
                        evidence=evidence,
                        recommendation=(
                            "Use parameterized queries (e.g. `cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))` "
                            "or ORM parameter binding). Never concatenate untrusted strings into SQL statements."
                        ),
                        cwe_id=self.cwe_id,
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

            if JS_SQL_TEMPLATE_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="sql_injection",
                        severity="CRITICAL",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Potential SQL injection via template literal",
                        description=(
                            "Dynamic SQL query constructed using JavaScript template literals (`${...}`). "
                            "User inputs embedded directly in query strings can lead to complete database compromise."
                        ),
                        evidence=stripped,
                        recommendation="Use parameterized statements with database driver placeholder arrays (e.g., `client.query('SELECT * FROM users WHERE id = $1', [userId])`).",
                        cwe_id=self.cwe_id,
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )
            elif JS_SQL_CONCAT_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="sql_injection",
                        severity="CRITICAL",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Potential SQL injection via string concatenation",
                        description="SQL query combined with variable expressions using '+' operator.",
                        evidence=stripped,
                        recommendation="Use parameterized queries instead of string concatenation.",
                        cwe_id=self.cwe_id,
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )

        return findings


class CommandInjectionRule(BaseSecurityRule):
    rule_id = "SEC-CMD-001"
    category = "INJECTION"
    cwe_id = "CWE-78"
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

            # Detect os.system / os.popen
            is_os_call = False
            callee_name = ""
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    if node.func.attr in {"system", "popen"}:
                        is_os_call = True
                        callee_name = f"os.{node.func.attr}"

            if is_os_call:
                line_no = getattr(node, "lineno", 1)
                evidence = lines[line_no - 1].strip() if 1 <= line_no <= len(lines) else ""
                # Check if argument is a constant or dynamic
                arg_is_dynamic = node.args and not isinstance(node.args[0], ast.Constant)
                findings.append(
                    SecurityFinding(
                        issue_type="command_injection",
                        severity="CRITICAL" if arg_is_dynamic else "HIGH",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=line_no,
                        category=self.category,
                        message=f"Insecure system command execution via {callee_name}()",
                        description=(
                            f"Call to '{callee_name}()' executes shell commands. "
                            "If untrusted or unsanitized input is passed, an attacker can execute arbitrary operating system commands."
                        ),
                        evidence=evidence,
                        recommendation="Use `subprocess.run([...], shell=False)` with arguments passed as a list, avoiding system shell invocation.",
                        cwe_id=self.cwe_id,
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )

            # Detect subprocess.*(..., shell=True)
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                    if node.func.attr in {"run", "Popen", "call", "check_output", "check_call"}:
                        has_shell_true = False
                        for kw in node.keywords:
                            if kw.arg == "shell":
                                if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                    has_shell_true = True

                        if has_shell_true:
                            line_no = getattr(node, "lineno", 1)
                            evidence = lines[line_no - 1].strip() if 1 <= line_no <= len(lines) else ""
                            arg_is_dynamic = node.args and not isinstance(node.args[0], ast.Constant)
                            findings.append(
                                SecurityFinding(
                                    issue_type="command_injection",
                                    severity="CRITICAL" if arg_is_dynamic else "HIGH",
                                    confidence="HIGH",
                                    file_path=file_path,
                                    line_number=line_no,
                                    category=self.category,
                                    message=f"Subprocess invoked with shell=True (`subprocess.{node.func.attr}`)",
                                    description=(
                                        f"`subprocess.{node.func.attr}(..., shell=True)` invokes the system shell. "
                                        "Passing dynamic strings through the shell enables command injection via shell metacharacters (`|`, `&`, `;`, `$`)."
                                    ),
                                    evidence=evidence,
                                    recommendation="Set `shell=False` and pass arguments as a list: `subprocess.run(['command', 'arg1', 'arg2'], shell=False)`.",
                                    cwe_id=self.cwe_id,
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

            if JS_EXEC_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="command_injection",
                        severity="HIGH",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Potential OS command injection via child_process.exec()",
                        description="`child_process.exec()` invokes a system shell. Untrusted input concatenated into the command string can execute arbitrary shell commands.",
                        evidence=stripped,
                        recommendation="Use `child_process.execFile()` or `child_process.spawn()` with explicit arguments array instead of shell execution.",
                        cwe_id=self.cwe_id,
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )

        return findings
