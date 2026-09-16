import os
import shutil
import zipfile
from typing import Tuple, Set

# Ignored directory names (case-insensitive)
IGNORED_DIRS: Set[str] = {
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
}

# Ignored file extensions
IGNORED_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".DS_Store",
}


def is_ignored_path(relative_path: str) -> bool:
    """Determine if a relative path inside the zip archive should be ignored."""
    normalized = relative_path.replace("\\", "/").strip("/")
    parts = normalized.split("/")

    # Check if any folder matches ignored directories
    for part in parts:
        if part.lower() in IGNORED_DIRS:
            return True

    # Check file extension
    _, ext = os.path.splitext(parts[-1])
    if ext.lower() in IGNORED_EXTENSIONS:
        return True

    return False


def safe_extract_zip(zip_bytes: bytes, target_dir: str) -> Tuple[int, str]:
    """Safely extract ZIP bytes into target_dir with strict Zip Slip protection and file filtering.
    
    Returns:
        Tuple[int, str]: (extracted_files_count, target_dir)
    """
    target_dir = os.path.abspath(target_dir)

    # Clean existing destination if any
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir, exist_ok=True)

    import io
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise ValueError("Invalid or corrupted ZIP archive") from e

    members = archive.infolist()
    if not members:
        raise ValueError("ZIP archive is completely empty")

    extracted_count = 0

    for member in members:
        # Normalize filename
        filename = member.filename.replace("\\", "/")

        # 1. Path traversal / Zip Slip security checks
        if filename.startswith("/") or filename.startswith("\\"):
            raise ValueError(f"Path traversal detected: absolute path in ZIP entry '{member.filename}'")

        parts = filename.split("/")
        if ".." in parts:
            raise ValueError(f"Path traversal detected: '..' component in ZIP entry '{member.filename}'")

        # 2. Skip ignored directories and files
        if is_ignored_path(filename):
            continue

        # 3. Canonical destination validation
        dest_path = os.path.abspath(os.path.join(target_dir, filename))
        if os.path.commonpath([target_dir, dest_path]) != target_dir:
            raise ValueError(f"Path traversal detected: '{member.filename}' escapes target directory")

        # 4. Extract
        if member.is_dir():
            os.makedirs(dest_path, exist_ok=True)
        else:
            parent_dir = os.path.dirname(dest_path)
            os.makedirs(parent_dir, exist_ok=True)

            # Write file content safely without executing
            with archive.open(member) as source_file, open(dest_path, "wb") as target_file:
                shutil.copyfileobj(source_file, target_file)
            extracted_count += 1

    if extracted_count == 0:
        raise ValueError("No valid source files found in ZIP archive after filtering")

    return extracted_count, target_dir
