import re
from typing import List, Optional, Any
from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding

PLAINTEXT_ASSIGN_REGEX = re.compile(
    r'(?i)\b(?:user|account|record)\.(?:password|passwd|pwd)\s*=\s*(?:request\.|req\.body|form|data|input|params|args|password)\b'
)

PLAINTEXT_EQUALITY_REGEX = re.compile(
    r'(?i)\b(?:user|account)\.password\s*==\s*[a-zA-Z0-9_]+'
)


class InsecurePasswordRule(BaseSecurityRule):
    rule_id = "SEC-AUTH-001"
    category = "AUTHENTICATION"
    cwe_id = "CWE-312"
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
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            if PLAINTEXT_ASSIGN_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="insecure_password",
                        severity="HIGH",
                        confidence="MEDIUM",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Direct plaintext password assignment detected",
                        description=(
                            "User password appears to be assigned directly from request or variable without cryptographic hashing. "
                            "Storing passwords in plaintext or unhashed form violates compliance requirements and allows immediate account compromise upon database breaches."
                        ),
                        evidence=stripped,
                        recommendation="Hash passwords before storage using an adaptive algorithm such as bcrypt (`passlib.hash.bcrypt.hash(password)`) or argon2id.",
                        cwe_id=self.cwe_id,
                        owasp_category=self.owasp_category,
                        rule_id=self.rule_id,
                    )
                )
            elif PLAINTEXT_EQUALITY_REGEX.search(stripped):
                findings.append(
                    SecurityFinding(
                        issue_type="insecure_password",
                        severity="MEDIUM",
                        confidence="MEDIUM",
                        file_path=file_path,
                        line_number=idx,
                        category=self.category,
                        message="Direct password equality comparison without constant-time hash check",
                        description=(
                            "Direct string comparison (`==`) for passwords suggests plaintext storage and is vulnerable to timing attacks. "
                            "Passwords should always be stored as hashes and validated using constant-time hash verification functions."
                        ),
                        evidence=stripped,
                        recommendation="Use a constant-time password verification function like `bcrypt.checkpw(entered_bytes, hashed_bytes)`.",
                        cwe_id="CWE-208",
                        owasp_category=self.owasp_category,
                        rule_id="SEC-AUTH-002",
                    )
                )

        return findings
