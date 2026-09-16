import os
import shutil
import git
from typing import Tuple
from backend.app.schemas.project import GITHUB_URL_REGEX
from backend.app.services.extractor import IGNORED_DIRS


def clone_github_repo(github_url: str, target_dir: str) -> Tuple[int, str]:
    """Safely clone a public GitHub repository using shallow clone and post-clone sanitation.
    
    Returns:
        Tuple[int, str]: (source_files_count, target_dir)
    """
    github_url = github_url.strip()
    if not GITHUB_URL_REGEX.match(github_url):
        raise ValueError("Invalid GitHub repository URL format. Expected: https://github.com/owner/repo")

    target_dir = os.path.abspath(target_dir)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir, exist_ok=True)

    # Disable interactive terminal prompts to fail quickly on private repos
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
    }

    try:
        git.Repo.clone_from(
            github_url,
            target_dir,
            depth=1,
            env=env,
            multi_options=["--single-branch"],
        )
    except git.exc.GitCommandError as e:
        # Clean up failed clone directory
        shutil.rmtree(target_dir, ignore_errors=True)
        err_msg = str(e).lower()
        if "authentication failed" in err_msg or "could not read username" in err_msg or "not found" in err_msg:
            raise ValueError("Repository not found or is private. Only public GitHub repositories are supported.") from e
        elif "could not resolve host" in err_msg or "unable to access" in err_msg:
            raise ValueError("Network error: Unable to reach GitHub. Please check network connectivity.") from e
        else:
            raise ValueError(f"Failed to clone repository: {e.stderr or str(e)}") from e
    except Exception as e:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise ValueError(f"Unexpected error during GitHub clone: {str(e)}") from e

    # Post-clone sanitization:
    # 1. Remove .git directory to eliminate git hooks and save disk space
    git_dir = os.path.join(target_dir, ".git")
    if os.path.exists(git_dir):
        shutil.rmtree(git_dir, ignore_errors=True)

    # 2. Clean out any ignored folders present in repo
    for root, dirs, _ in os.walk(target_dir, topdown=True):
        for d in list(dirs):
            if d.lower() in IGNORED_DIRS:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)

    # 3. Count remaining valid files
    source_files_count = 0
    for _, _, files in os.walk(target_dir):
        source_files_count += len(files)

    if source_files_count == 0:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise ValueError("GitHub repository contains no valid files")

    return source_files_count, target_dir
