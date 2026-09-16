"""
Duplicate Code Detector.
Identifies repeated blocks of source code across files or within the same file.
Normalizes source lines by removing comments, blank lines, and whitespace variance.
"""

import re
import hashlib
from typing import List, Dict, Tuple, Any, Set
from difflib import SequenceMatcher

MIN_BLOCK_SIZE = 10  # Minimum consecutive normalized lines to consider a duplicate


def _normalize_line(line: str) -> str:
    """Strip comments, extra spaces, and trailing whitespace."""
    # Remove inline Python/Shell comments (#) and C-style comments (//)
    line = re.sub(r'(#|//).*$', '', line)
    # Collapse multiple whitespaces
    line = re.sub(r'\s+', ' ', line).strip()
    return line


def detect_duplicate_blocks(
    files_content: List[Tuple[str, str]]
) -> List[Dict[str, Any]]:
    """Detects duplicate blocks of 10+ consecutive normalized lines across files.
    Args:
        files_content: List of (file_path, source_text)
    Returns:
        List of duplicate issue dictionaries
    """
    # 1. Preprocess and normalize files
    # file_data[file_path] = list of (normalized_text, orig_lineno)
    file_data: Dict[str, List[Tuple[str, int]]] = {}

    for file_path, content in files_content:
        norm_lines = []
        for line_idx, raw_line in enumerate(content.splitlines(), start=1):
            norm = _normalize_line(raw_line)
            # Skip empty lines or trivial single bracket lines
            if norm and norm not in ("{", "}", "(", ")", "pass", ";"):
                norm_lines.append((norm, line_idx))
        file_data[file_path] = norm_lines

    # 2. Index sliding windows of size MIN_BLOCK_SIZE
    # window_hash -> list of (file_path, start_norm_idx, start_orig_line)
    window_map: Dict[str, List[Tuple[str, int, int]]] = {}

    for file_path, lines in file_data.items():
        if len(lines) < MIN_BLOCK_SIZE:
            continue
        for i in range(len(lines) - MIN_BLOCK_SIZE + 1):
            window = tuple(lines[i + k][0] for k in range(MIN_BLOCK_SIZE))
            window_str = "\n".join(window)
            h = hashlib.md5(window_str.encode("utf-8")).hexdigest()
            if h not in window_map:
                window_map[h] = []
            window_map[h].append((file_path, i, lines[i][1]))

    # 3. Find matches and extend blocks
    issues: List[Dict[str, Any]] = []
    # Track pairs already covered to prevent sub-window spam: (file_a, start_orig_a, file_b, start_orig_b)
    reported_matches: Set[Tuple[str, int, str, int]] = set()

    for h, occurrences in window_map.items():
        if len(occurrences) < 2:
            continue

        for idx_a in range(len(occurrences)):
            for idx_b in range(idx_a + 1, len(occurrences)):
                file_a, norm_idx_a, orig_line_a = occurrences[idx_a]
                file_b, norm_idx_b, orig_line_b = occurrences[idx_b]

                # If same file, ensure non-overlapping
                if file_a == file_b and abs(norm_idx_a - norm_idx_b) < MIN_BLOCK_SIZE:
                    continue

                # Extend matching forward
                lines_a = file_data[file_a]
                lines_b = file_data[file_b]

                length = MIN_BLOCK_SIZE
                while (
                    norm_idx_a + length < len(lines_a)
                    and norm_idx_b + length < len(lines_b)
                    and lines_a[norm_idx_a + length][0] == lines_b[norm_idx_b + length][0]
                ):
                    length += 1

                orig_end_a = lines_a[norm_idx_a + length - 1][1]
                orig_end_b = lines_b[norm_idx_b + length - 1][1]

                # Check if this occurrence is already covered by a previous longer report
                already_covered = False
                for (prev_fa, prev_sa, prev_fb, prev_sb) in reported_matches:
                    if prev_fa == file_a and prev_fb == file_b:
                        if abs(prev_sa - orig_line_a) < 5 and abs(prev_sb - orig_line_b) < 5:
                            already_covered = True
                            break
                if already_covered:
                    continue

                reported_matches.add((file_a, orig_line_a, file_b, orig_line_b))

                # Calculate approximate similarity
                text_a = "\n".join(lines_a[norm_idx_a + k][0] for k in range(length))
                text_b = "\n".join(lines_b[norm_idx_b + k][0] for k in range(length))
                similarity = round(SequenceMatcher(None, text_a, text_b).ratio() * 100, 1)

                severity = "HIGH" if length >= 25 else "MEDIUM"

                issues.append({
                    "issue_type": "duplicate_code",
                    "severity": severity,
                    "file_path": file_a,
                    "line_number": orig_line_a,
                    "end_line": orig_end_a,
                    "symbol_name": None,
                    "message": f"Duplicate code block (~{length} lines) matching {file_b}:{orig_line_b}.",
                    "description": (
                        f"Detected approximately {length} consecutive lines of identical or near-identical code "
                        f"in '{file_a}' (lines {orig_line_a}–{orig_end_a}) that matches '{file_b}' (lines {orig_line_b}–{orig_end_b})."
                    ),
                    "evidence": f"Matches {file_b}:{orig_line_b}–{orig_end_b} (~{length} lines, {similarity}% similarity)",
                    "recommendation": (
                        "Extract the duplicated logic into a shared helper function, class, or utility module "
                        "to follow the DRY (Don't Repeat Yourself) principle."
                    )
                })

    return issues
