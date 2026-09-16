import ast
import re
from typing import List, Optional, Any
from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding

DEBUG_TRUE_ASSIGN_REGEX = re.compile(
    r'(?i)\bDEBUG\s*=\s*True\b'
)
DEBUG_RUN_REGEX = re.compile(
    r'(?i)\b(?:app|server)\.run\s*\([^)]*debug\s*=\s*True[^)]*\)'
)
SSL_VERIFY_FALSE_REGEX = re.compile(
    r'(?i)\bverify\s*=\s*False\b'
)
NODE_REJECT_UNAUTH_REGEX = re.compile(
    r'(?i)\b(?:rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\'"]?0[\'"]?)'
)
CORS_WILDCARD_REGEX = re.compile(
    r'(?i)allow_origins\s*=\s*\[\s*["\']\*["\']\s*\]'
)


class InsecureConfigurationRule(BaseSecurityRule):
    rule_id = "SEC-CONF-001"
    category = "CONFIGURATION"
    cwe_id = "CWE-209"
    owasp_category = "A05:2021-Security Misconfiguration"

    def run(
        self,
        file_path: str,
        content: str,
        ext: str,
        ast_tree: Optional[Any] = None,
    ) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # 1. SSL verification disabled
            if SSL_VERIFY_FALSE_REGEX.search(stripped) or NODE_REJECT_UNAUTH_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="insecure_config",
                        severity="HIGH",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Disabled TLS/SSL certificate verification",
                        description=(
                            "TLS/SSL certificate validation is explicitly disabled (`verify=False` or `rejectUnauthorized: false`). "
                            "This exposes network communications to Man-in-the-Middle (MitM) attacks where an attacker can intercept or alter encrypted traffic."
                        ),
                        evidence=stripped,
                        recommendation="Enable standard TLS verification (`verify=True`). If using custom internal certificates, provide the path to the trusted CA bundle instead of disabling verification.",
                        cwe_id="CWE-295",
                        owasp_category="A02:2021-Cryptographic Failures",
                        rule_id="SEC-CONF-002",
                    )
                )

            # 2. DEBUG mode enabled
            elif DEBUG_TRUE_ASSIGN_REGEX.search(stripped) or DEBUG_RUN_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="insecure_config",
                        severity="MEDIUM",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Debug mode explicitly enabled (`DEBUG = True`)",
                        description=(
                            "Debug mode is explicitly enabled. In production environments, debug mode reveals interactive tracebacks, "
                            "environment variables, configuration files, and internal paths to attackers upon errors."
                        ),
                        evidence=stripped,
                        recommendation="Ensure debug mode is disabled in production environments by loading debug flags from environment variables (e.g. `DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'`).",
                        cwe_id="CWE-209",
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )

            # 3. Wildcard CORS
            elif CORS_WILDCARD_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="insecure_config",
                        severity="MEDIUM",
                        confidence="HIGH",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Permissive wildcard CORS policy (`allow_origins=['*']`)",
                        description=(
                            "Wildcard CORS allows any external domain to make requests to the API. If sensitive endpoints or cookies are involved, "
                            "this can allow malicious third-party websites to extract data from authenticated users."
                        ),
                        evidence=stripped,
                        recommendation="Specify explicit allowed origins rather than wildcard '*' when serving authenticated API endpoints.",
                        cwe_id="CWE-942",
                        owasp_category=self.owasp_category,
                        rule_id="SEC-CONF-003",
                    )
                )

        return findings
