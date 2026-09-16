import re
from typing import List, Optional, Any, Tuple
from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding

# Regex patterns for specific high-fidelity secrets
SPECIFIC_PATTERNS: List[Tuple[str, re.Pattern, str, str]] = [
    (
        "AWS Access Key ID",
        re.compile(r'\b(AKIA[0-9A-Z]{16})\b'),
        "CRITICAL",
        "AWS Access Key ID detected. If exposed, this allows unauthorized access to cloud infrastructure.",
    ),
    (
        "GitHub Personal Access Token",
        re.compile(r'\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{30,80})\b'),
        "CRITICAL",
        "GitHub Personal Access Token detected. This allows direct repository and organization access.",
    ),
    (
        "Stripe API Key",
        re.compile(r'\b([sr]k_(?:live|test)_[0-9a-zA-Z]{24,})\b'),
        "CRITICAL",
        "Stripe API secret key detected. Exposing payment gateway keys risks financial compromise.",
    ),
    (
        "OpenAI / Anthropic Secret Key",
        re.compile(r'\b(sk-[a-zA-Z0-9]{20,50}|sk-ant-[a-zA-Z0-9_-]{20,60})\b'),
        "HIGH",
        "AI provider API secret key detected. This can lead to unauthorized API usage and billing abuse.",
    ),
    (
        "Private Cryptographic Key",
        re.compile(r'(-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)'),
        "CRITICAL",
        "Private cryptographic key header detected directly in source code.",
    ),
    (
        "Database Connection String with Password",
        re.compile(r'(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):\/\/[a-zA-Z0-9_.-]+:([^@\s:/?#]{4,})@[a-zA-Z0-9_.-]+'),
        "HIGH",
        "Database connection URI containing hardcoded database credentials.",
    ),
]

# Generic assignment regex: variable = "secret_string"
GENERIC_ASSIGNMENT_REGEX = re.compile(
    r'(?i)\b(api_key|secret_key|client_secret|auth_token|access_token|db_password|password|private_key|jwt_secret)\b\s*[:=]\s*(["\'])(.*?)\2'
)

# Obvious placeholder / dummy values that should never trigger alerts
PLACEHOLDER_SUBSTRINGS = {
    "your_api_key_here",
    "your_key",
    "your_secret",
    "your_token",
    "your-api-key",
    "api_key_here",
    "test_key",
    "dummy_key",
    "dummy",
    "example",
    "changeme",
    "placeholder",
    "123456",
    "12345678",
    "admin",
    "password",
    "root",
    "none",
    "null",
    "default",
    "undefined",
    "secret",
    "mysecret",
    "sample",
    "fake",
}


def mask_value(raw: str) -> str:
    """Mask sensitive string, showing at most first 4 and last 2 characters."""
    if not raw:
        return "********"
    if len(raw) <= 8:
        return "********"
    prefix = raw[:4]
    suffix = raw[-2:]
    return f"{prefix}{'*' * (len(raw) - 6)}{suffix}"


def mask_line(line: str) -> str:
    """Mask credentials in a single line of code."""
    # Mask specific patterns
    for name, pattern, _, _ in SPECIFIC_PATTERNS:
        matches = pattern.finditer(line)
        for m in matches:
            secret = m.group(1)
            line = line.replace(secret, mask_value(secret))

    # Mask generic assignments
    def _mask_generic(m):
        var_name = m.group(1)
        quote = m.group(2)
        val = m.group(3)
        return f'{var_name} = {quote}{mask_value(val)}{quote}'

    line = GENERIC_ASSIGNMENT_REGEX.sub(_mask_generic, line)
    return line


class HardcodedSecretRule(BaseSecurityRule):
    rule_id = "SEC-SECRET-001"
    category = "SECRETS"
    cwe_id = "CWE-798"
    owasp_category = "A07:2021-Identification and Authentication Failures"

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
            if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                # Skip pure comments unless they hold a private key header
                if "-----BEGIN " not in stripped:
                    continue

            # 1. Check specific patterns
            found_specific = False
            for name, pattern, severity, desc in SPECIFIC_PATTERNS:
                match = pattern.search(line)
                if match:
                    secret_val = match.group(1)
                    # Filter out trivial dummy repetitions (e.g. all Xs or all 0s)
                    body_to_check = secret_val[4:] if len(secret_val) > 4 else secret_val
                    if len(set(body_to_check)) <= 1:
                        continue
                    if secret_val in {"AKIA0000000000000000", "AKIAXXXXXXXXXXXXXXXX"}:
                        continue

                    masked_evidence = mask_line(stripped)
                    findings.append(
                        SecurityFinding(
                            issue_type="hardcoded_secret",
                            severity=severity,
                            confidence="HIGH",
                            file_path=file_path,
                            line_number=idx,
                            category=self.category,
                            message=f"Hardcoded {name} detected",
                            description=f"{desc} Hardcoded credentials in source code can be extracted and abused.",
                            evidence=masked_evidence,
                            recommendation="Move sensitive credentials out of source code into environment variables or a secure secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault).",
                            cwe_id=self.cwe_id,
                            owasp_category=self.owasp_category,
                            rule_id=self.rule_id,
                        )
                    )
                    found_specific = True
                    break

            if found_specific:
                continue

            # 2. Check generic variable assignment
            assign_match = GENERIC_ASSIGNMENT_REGEX.search(line)
            if assign_match:
                var_name = assign_match.group(1)
                val = assign_match.group(3).strip()

                # Filter placeholders
                lower_val = val.lower()
                if len(val) < 6:
                    continue
                if any(ph == lower_val or f"<{lower_val}>" == lower_val for ph in PLACEHOLDER_SUBSTRINGS):
                    continue
                if lower_val.startswith(("${", "process.env", "os.getenv", "os.environ", "config(", "env(")):
                    continue
                if all(c == val[0] for c in val):
                    # Trivial repetitive strings like "xxxxxx" or "000000"
                    continue

                masked_evidence = mask_line(stripped)
                findings.append(
                    SecurityFinding(
                        issue_type="hardcoded_secret",
                        severity="HIGH",
                        confidence="HIGH" if len(val) > 12 else "MEDIUM",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message=f"Hardcoded credential assigned to '{var_name}'",
                        description=f"Variable '{var_name}' appears to hold a hardcoded secret or token. Plaintext secrets in version control can be compromised by unauthorized repository access.",
                        evidence=masked_evidence,
                        recommendation="Load secrets dynamically from environment variables (e.g., `os.environ.get(...)` or `process.env`) or secret storage systems.",
                        cwe_id=self.cwe_id,
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )

        return findings
