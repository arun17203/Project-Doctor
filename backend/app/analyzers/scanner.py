import os
from typing import Dict, List, Any, Tuple, Optional, Set

# Ignored directory names (case-insensitive)
SCANNER_IGNORED_DIRS: Set[str] = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".next",
    ".turbo",
    ".parcel-cache",
}

# Known Binary / Asset extensions
BINARY_EXTENSIONS: Set[str] = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
    # Audio / Video
    ".mp3", ".wav", ".ogg", ".mp4", ".avi", ".mov", ".mkv", ".webm",
    # Archives / Binaries
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".exe", ".dll", ".so",
    ".dylib", ".class", ".jar", ".war", ".pyc", ".pyo", ".pyd", ".bin",
    # Documents / Fonts
    ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".db", ".sqlite", ".sqlite3"
}

# Language Extension Mapping
LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyw": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".hxx": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".php": "PHP",
    ".phtml": "PHP",
    ".rb": "Ruby",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".less": "SCSS",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sh": "Shell",
    ".bash": "Shell",
    ".rs": "Rust",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".xml": "XML",
}

# Config file exact names or suffixes
KNOWN_CONFIG_FILENAMES: Set[str] = {
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "pyproject.toml",
    "pipfile",
    "pom.xml",
    "build.gradle",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "tsconfig.json",
    "alembic.ini",
    ".gitignore",
    "pytest.ini",
    "webpack.config.js",
    "vite.config.ts",
    "vite.config.js",
    "tailwind.config.js",
    "tailwind.config.ts",
}

# Max file size to read for line counting (2 MB)
MAX_LINE_COUNT_FILE_SIZE = 2 * 1024 * 1024


def is_binary_file(filepath: str) -> bool:
    """Check if file is binary by extension or null-byte sampling."""
    _, ext = os.path.splitext(filepath)
    if ext.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


def detect_language(ext: str) -> str:
    """Map file extension to programming language name."""
    return LANGUAGE_MAP.get(ext.lower(), "Other")


def categorize_file(rel_path: str, filename: str, ext: str, language: str) -> Tuple[str, bool, bool, bool]:
    """Categorize file into Source Code, Tests, Configuration, Documentation, Assets, or Other.
    
    Returns:
        Tuple[str, bool, bool, bool]: (category, is_test, is_config, is_doc)
    """
    rel_lower = rel_path.lower().replace("\\", "/")
    parts = rel_lower.split("/")
    fname_lower = filename.lower()

    # 1. Tests
    is_in_test_folder = any(p in ("tests", "test", "__tests__", "spec", "specs") for p in parts[:-1])
    is_test_filename = (
        fname_lower.startswith("test_")
        or fname_lower.endswith("_test.py")
        or fname_lower.endswith(".test.js")
        or fname_lower.endswith(".spec.js")
        or fname_lower.endswith(".test.ts")
        or fname_lower.endswith(".spec.ts")
        or fname_lower.endswith(".test.jsx")
        or fname_lower.endswith(".spec.jsx")
        or fname_lower.endswith(".test.tsx")
        or fname_lower.endswith(".spec.tsx")
        or fname_lower.endswith("test.java")
        or fname_lower.endswith("tests.java")
        or fname_lower.endswith("_test.go")
    )
    if is_in_test_folder or is_test_filename:
        return "Tests", True, False, False

    # 2. Configuration
    is_config = (
        fname_lower in KNOWN_CONFIG_FILENAMES
        or fname_lower.startswith(".env")
        or fname_lower.startswith("requirements")
        or fname_lower.endswith(".config.js")
        or fname_lower.endswith(".config.ts")
        or fname_lower.endswith(".conf")
        or fname_lower.endswith(".ini")
        or fname_lower.endswith(".cfg")
    )
    if is_config:
        return "Configuration", False, True, False

    # 3. Documentation
    is_in_doc_folder = any(p in ("doc", "docs", "documentation") for p in parts[:-1])
    is_doc = (
        is_in_doc_folder
        or fname_lower.startswith("readme")
        or fname_lower.startswith("changelog")
        or fname_lower.startswith("license")
        or fname_lower.startswith("contributing")
        or ext.lower() in (".md", ".markdown", ".rst", ".txt")
    )
    if is_doc:
        return "Documentation", False, False, True

    # 4. Assets
    if ext.lower() in BINARY_EXTENSIONS:
        return "Assets", False, False, False

    # 5. Source Code
    if language != "Other":
        return "Source Code", False, False, False

    return "Other", False, False, False


def count_lines(filepath: str, language: str) -> Tuple[int, int, int, int]:
    """Count total, code, blank, and comment lines in a source file.
    
    Returns:
        Tuple[int, int, int, int]: (total_lines, code_lines, blank_lines, comment_lines)
    """
    total_lines = 0
    blank_lines = 0
    comment_lines = 0

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            in_block_comment = False
            block_comment_end = ""

            for line in f:
                total_lines += 1
                stripped = line.strip()

                if not stripped:
                    blank_lines += 1
                    continue

                # Check if currently inside block comment
                if in_block_comment:
                    comment_lines += 1
                    if block_comment_end and block_comment_end in stripped:
                        in_block_comment = False
                        block_comment_end = ""
                    continue

                # Python block comments (docstrings at start of line)
                if language == "Python":
                    if stripped.startswith('"""'):
                        comment_lines += 1
                        if stripped.count('"""') == 1:
                            in_block_comment = True
                            block_comment_end = '"""'
                        continue
                    elif stripped.startswith("'''"):
                        comment_lines += 1
                        if stripped.count("'''") == 1:
                            in_block_comment = True
                            block_comment_end = "'''"
                        continue
                    elif stripped.startswith("#"):
                        comment_lines += 1
                        continue

                # C-style comments (JS, TS, Java, C, C++, C#, Go, Rust, PHP, CSS)
                if language in ("JavaScript", "TypeScript", "Java", "C", "C++", "C#", "Go", "Rust", "PHP", "CSS", "SCSS", "Swift"):
                    if stripped.startswith("/*"):
                        comment_lines += 1
                        if "*/" not in stripped:
                            in_block_comment = True
                            block_comment_end = "*/"
                        continue
                    elif stripped.startswith("//"):
                        comment_lines += 1
                        continue

                # HTML / XML comments
                if language in ("HTML", "XML"):
                    if stripped.startswith("<!--"):
                        comment_lines += 1
                        if "-->" not in stripped:
                            in_block_comment = True
                            block_comment_end = "-->"
                        continue

                # SQL comments
                if language == "SQL":
                    if stripped.startswith("--"):
                        comment_lines += 1
                        continue
                    elif stripped.startswith("/*"):
                        comment_lines += 1
                        if "*/" not in stripped:
                            in_block_comment = True
                            block_comment_end = "*/"
                        continue

                # Shell / Ruby comments
                if language in ("Shell", "Ruby", "YAML") and stripped.startswith("#"):
                    comment_lines += 1
                    continue

    except Exception:
        # If unreadable, return zeroes safely
        return 0, 0, 0, 0

    code_lines = max(0, total_lines - blank_lines - comment_lines)
    return total_lines, code_lines, blank_lines, comment_lines


def build_directory_tree(file_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a nested hierarchical directory tree from discovered files."""
    root: Dict[str, Any] = {
        "name": "root",
        "path": "",
        "type": "directory",
        "children": {},
    }

    for file_info in file_list:
        parts = file_info["file_path"].replace("\\", "/").split("/")
        current = root

        # Traverse and create directory nodes
        for i, part in enumerate(parts[:-1]):
            sub_path = "/".join(parts[: i + 1])
            if part not in current["children"]:
                current["children"][part] = {
                    "name": part,
                    "path": sub_path,
                    "type": "directory",
                    "children": {},
                }
            current = current["children"][part]

        # Add file leaf node
        filename = parts[-1]
        current["children"][filename] = {
            "name": filename,
            "path": file_info["file_path"],
            "type": "file",
            "size_bytes": file_info["size_bytes"],
            "language": file_info["language"],
            "category": file_info["category"],
            "lines": file_info["total_lines"],
            "code_lines": file_info["code_lines"],
        }

    # Convert dictionary children to sorted lists
    def format_node(node: Dict[str, Any]) -> Dict[str, Any]:
        if node["type"] == "directory":
            children_list = list(node["children"].values())
            # Sort: directories first, then alphabetical by name
            children_list.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
            return {
                "name": node["name"],
                "path": node["path"],
                "type": "directory",
                "children": [format_node(child) for child in children_list],
            }
        return node

    return format_node(root)


def scan_repository(storage_path: str) -> Dict[str, Any]:
    """Perform comprehensive repository scanning on an unpacked codebase.
    
    Returns structured results:
        - total_files
        - total_directories
        - total_lines
        - total_code_lines
        - total_blank_lines
        - total_comment_lines
        - test_files_count
        - config_files_count
        - doc_files_count
        - languages_summary
        - categories_summary
        - directory_tree
        - files (list of file detail dictionaries)
    """
    storage_path = os.path.abspath(storage_path)
    if not os.path.exists(storage_path):
        raise ValueError(f"Repository storage path does not exist: {storage_path}")

    discovered_files: List[Dict[str, Any]] = []
    total_directories = 0

    languages_stats: Dict[str, Dict[str, int]] = {}
    categories_stats: Dict[str, int] = {
        "Source Code": 0,
        "Tests": 0,
        "Configuration": 0,
        "Documentation": 0,
        "Assets": 0,
        "Other": 0,
    }

    total_lines = 0
    total_code_lines = 0
    total_blank_lines = 0
    total_comment_lines = 0
    test_files_count = 0
    config_files_count = 0
    doc_files_count = 0

    for root, dirs, files in os.walk(storage_path, topdown=True):
        # Filter ignored directories in-place
        dirs[:] = [d for d in dirs if d.lower() not in SCANNER_IGNORED_DIRS]
        total_directories += len(dirs)

        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, storage_path).replace("\\", "/")
            _, ext = os.path.splitext(fname)

            # Basic metadata
            try:
                size_bytes = os.path.getsize(full_path)
            except Exception:
                size_bytes = 0

            is_binary = is_binary_file(full_path)
            language = "Other" if is_binary else detect_language(ext)
            category, is_test, is_config, is_doc = categorize_file(rel_path, fname, ext, language)

            # Tallies
            categories_stats[category] = categories_stats.get(category, 0) + 1
            if is_test:
                test_files_count += 1
            if is_config:
                config_files_count += 1
            if is_doc:
                doc_files_count += 1

            # Line counting
            is_skipped = size_bytes > MAX_LINE_COUNT_FILE_SIZE or is_binary
            f_lines, f_code, f_blank, f_comments = 0, 0, 0, 0

            if not is_skipped:
                f_lines, f_code, f_blank, f_comments = count_lines(full_path, language)
                total_lines += f_lines
                total_code_lines += f_code
                total_blank_lines += f_blank
                total_comment_lines += f_comments

                # Accumulate language lines
                if language != "Other" and f_lines > 0:
                    if language not in languages_stats:
                        languages_stats[language] = {
                            "files": 0,
                            "lines": 0,
                            "code_lines": 0,
                            "blank_lines": 0,
                            "comment_lines": 0,
                        }
                    languages_stats[language]["files"] += 1
                    languages_stats[language]["lines"] += f_lines
                    languages_stats[language]["code_lines"] += f_code
                    languages_stats[language]["blank_lines"] += f_blank
                    languages_stats[language]["comment_lines"] += f_comments

            discovered_files.append({
                "file_path": rel_path,
                "file_name": fname,
                "extension": ext.lower(),
                "language": language,
                "category": category,
                "size_bytes": size_bytes,
                "total_lines": f_lines,
                "code_lines": f_code,
                "blank_lines": f_blank,
                "comment_lines": f_comments,
                "is_binary": is_binary,
                "is_test": is_test,
                "is_config": is_config,
                "is_doc": is_doc,
                "is_skipped": is_skipped,
            })

    # Compute language percentages based on real line counts
    total_lang_lines = sum(stat["lines"] for stat in languages_stats.values())
    languages_summary: Dict[str, Any] = {}

    if len(languages_stats) == 1:
        # If single language, exactly 100%
        single_lang = list(languages_stats.keys())[0]
        data = languages_stats[single_lang]
        languages_summary[single_lang] = {**data, "percentage": 100.0}
    elif total_lang_lines > 0:
        for lang, stat in sorted(languages_stats.items(), key=lambda item: item[1]["lines"], reverse=True):
            pct = round((stat["lines"] / total_lang_lines) * 100, 1)
            languages_summary[lang] = {**stat, "percentage": pct}

    # Build hierarchical directory tree
    directory_tree = build_directory_tree(discovered_files)

    return {
        "total_files": len(discovered_files),
        "total_directories": total_directories,
        "total_lines": total_lines,
        "total_code_lines": total_code_lines,
        "total_blank_lines": total_blank_lines,
        "total_comment_lines": total_comment_lines,
        "test_files_count": test_files_count,
        "config_files_count": config_files_count,
        "doc_files_count": doc_files_count,
        "languages_summary": languages_summary,
        "categories_summary": categories_stats,
        "directory_tree": directory_tree,
        "files": discovered_files,
    }
