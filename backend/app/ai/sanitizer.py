import os
import re
from typing import Optional

# Disallowed files that should NEVER have snippets extracted or sent to AI
DISALLOWED_PATTERNS = [
    re.compile(r"(^|[/\\])\.env", re.IGNORECASE),
    re.compile(r"(^|[/\\]).*\.(pem|key|pkcs12|pfx|cert|crt)$", re.IGNORECASE),
    re.compile(r"(^|[/\\])(credentials|secrets|id_rsa|id_dsa|id_ecdsa|id_ed25519)", re.IGNORECASE),
]

# Sensitive regex patterns to scrub from any extracted snippet before sending to AI
SENSITIVE_PATTERNS = [
    (re.compile(r"([a-z0-9_]*(?:password|passwd|pwd|secret|api_key|apikey|token)[a-z0-9_]*)\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE), r"\1 = '***REDACTED***'"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE), "Bearer ***REDACTED_TOKEN***"),
    (re.compile(r"ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "***REDACTED_JWT***"),
    (re.compile(r"-----BEGIN [A-Z ]+-----[^-]+-----END [A-Z ]+-----", re.DOTALL), "***REDACTED_PRIVATE_KEY***"),
]


def is_file_disallowed(file_path: str) -> bool:
    """Check if file is sensitive and should never have content read."""
    norm = file_path.replace("\\", "/")
    return any(p.search(norm) for p in DISALLOWED_PATTERNS)


def mask_sensitive_snippet(snippet: str) -> str:
    """Scrub potential credentials or secrets from source snippet."""
    if not snippet:
        return ""
    result = snippet
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def extract_relevant_snippet(
    project_root: str,
    relative_path: str,
    line_number: Optional[int],
    radius: int = 5,
    max_chars: int = 600,
) -> Optional[str]:
    """Safely extracts a tightly bounded source code snippet around the issue line.
    Enforces security:
      - Validates path is strictly inside project_root (Zip Slip / Traversal defense)
      - Blocks .env and credential files
      - Masks any residual sensitive patterns
      - Clamps total characters to max_chars
    """
    if not relative_path or not project_root:
        return None

    if is_file_disallowed(relative_path):
        return None

    try:
        abs_root = os.path.abspath(project_root)
        full_path = os.path.abspath(os.path.join(abs_root, relative_path))

        # Check directory traversal
        if not full_path.startswith(abs_root):
            return None

        if not os.path.isfile(full_path):
            return None

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if not lines:
            return None

        target_line = line_number or 1
        target_idx = max(0, target_line - 1)

        start_idx = max(0, target_idx - radius)
        end_idx = min(len(lines), target_idx + radius + 1)

        snippet_lines = []
        for i in range(start_idx, end_idx):
            line_num = i + 1
            marker = " > " if line_num == target_line else "   "
            snippet_lines.append(f"{marker}{line_num:4d} | {lines[i].rstrip()}")

        raw_snippet = "\n".join(snippet_lines)
        masked_snippet = mask_sensitive_snippet(raw_snippet)

        if len(masked_snippet) > max_chars:
            masked_snippet = masked_snippet[:max_chars] + "\n   ... [truncated]"

        return masked_snippet
    except Exception:
        return None
