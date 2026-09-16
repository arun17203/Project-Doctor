import re
from typing import List, Optional, Any
from backend.app.analyzers.security.base import BaseSecurityRule, SecurityFinding

WEAK_HASH_PATTERNS = [
    (
        re.compile(r'(?i)\b(?:hashlib\.)?md5\s*\('),
        "MD5",
        "MD5 is a cryptographically broken hash algorithm vulnerable to collision attacks.",
    ),
    (
        re.compile(r'(?i)\bcrypto\.createHash\s*\(\s*["\']md5["\']\s*\)'),
        "MD5",
        "MD5 is a cryptographically broken hash algorithm vulnerable to collision attacks.",
    ),
    (
        re.compile(r'(?i)\b(?:hashlib\.)?sha1\s*\('),
        "SHA-1",
        "SHA-1 is deprecated and vulnerable to practical collision generation.",
    ),
    (
        re.compile(r'(?i)\bcrypto\.createHash\s*\(\s*["\']sha1["\']\s*\)'),
        "SHA-1",
        "SHA-1 is deprecated and vulnerable to practical collision generation.",
    ),
]

AUTH_OR_PASSWORD_CONTEXT = re.compile(
    r'(?i)\b(password|passwd|token|auth|secret|credential|key)\b'
)


class WeakCryptographyRule(BaseSecurityRule):
    rule_id = "SEC-CRYPTO-001"
    category = "CRYPTO"
    cwe_id = "CWE-328"
    owasp_category = "A02:2021-Cryptographic Failures"

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

            for pattern, alg_name, explanation in WEAK_HASH_PATTERNS:
                if pattern.search(stripped):
                    # Check if line or adjacent context relates to passwords/auth
                    is_auth_context = bool(AUTH_OR_PASSWORD_CONTEXT.search(stripped))
                    severity = "HIGH" if is_auth_context else "MEDIUM"

                    findings.append(
                        SecurityFinding(
                            issue_type="weak_crypto",
                            severity=severity,
                            confidence="HIGH",
                            file_path=file_path,
                            line_number=idx,
                            category=self.category,
                            message=f"Weak cryptographic hash algorithm `{alg_name}` in use",
                            description=(
                                f"{explanation} When used for passwords, digital signatures, or integrity checks, "
                                "attackers can forge signatures or pre-compute rainbow tables to reverse hashes."
                            ),
                            evidence=stripped,
                            recommendation=(
                                "For password storage, use modern adaptive key derivation functions: `argon2id`, `bcrypt`, or `PBKDF2`. "
                                "For general data integrity or hashing, use `SHA-256` or `SHA-3` (`hashlib.sha256()`)."
                            ),
                            cwe_id=self.cwe_id,
                            owasp_category=self.owasp_category,
                            rule_id=self.rule_id,
                        )
                    )
                    break

        return findings
