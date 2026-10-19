"""
DevTwin Mining Engine — Safe File-Tree Traversal
Safely walks an isolated workspace, enforcing directory exclusions and resource limits.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List

from app.mining.classification import is_binary_content
from app.mining.constants import (
    EXCLUDED_DIRECTORIES,
    MAX_FILES_INSPECTED,
    MAX_TOTAL_SOURCE_BYTES,
)
from app.mining.models import MiningWarning


@dataclass(frozen=True)
class DiscoveredFile:
    abs_path: Path
    rel_path: str
    size_bytes: int
    is_binary: bool


def safe_walk_workspace(
    root_dir: Path,
    workspace_dir: Path,
) -> tuple[List[DiscoveredFile], int, List[MiningWarning]]:
    """
    Safely walks the extracted repository file tree within the isolated workspace.

    Guarantees:
    - Never follows symlinks.
    - Never traverses outside the workspace_dir.
    - Excludes build, dependency, virtual environment, and cache directories.
    - Detects and categorizes binary files.
    - Enforces file count and total byte budgets.

    Returns:
    - List of valid DiscoveredFile records.
    - Count of excluded/skipped files.
    - List of sanitized MiningWarning objects.
    """
    resolved_workspace = workspace_dir.resolve()
    resolved_root = root_dir.resolve()

    discovered: List[DiscoveredFile] = []
    excluded_count = 0
    warnings: List[MiningWarning] = []
    total_source_bytes = 0

    # Ensure root_dir is strictly contained inside workspace_dir
    try:
        if resolved_workspace not in resolved_root.parents and resolved_root != resolved_workspace:
            warnings.append(
                MiningWarning(
                    file_path=None,
                    warning_code="WORKSPACE_ESCAPE_DETECTED",
                    message="Repository root directory escapes workspace boundary.",
                )
            )
            return [], 0, warnings
    except Exception:
        return [], 0, warnings

    for dirpath, dirnames, filenames in os.walk(str(resolved_root), followlinks=False):
        current_dir = Path(dirpath).resolve()

        # Check directory confinement
        try:
            if resolved_workspace not in current_dir.parents and current_dir != resolved_workspace:
                warnings.append(
                    MiningWarning(
                        file_path=str(current_dir),
                        warning_code="WORKSPACE_ESCAPE_DETECTED",
                        message="Directory path traversal outside workspace ignored.",
                    )
                )
                dirnames.clear()
                continue
        except Exception:
            dirnames.clear()
            continue

        # Prune excluded directories in-place to prevent descending into them
        pruned_dirs = []
        for d in list(dirnames):
            d_lower = d.lower()
            d_path = current_dir / d
            if d_path.is_symlink():
                dirnames.remove(d)
                excluded_count += 1
            elif d_lower in EXCLUDED_DIRECTORIES:
                dirnames.remove(d)
                excluded_count += 1
            else:
                pruned_dirs.append(d)

        for fname in sorted(filenames):
            if len(discovered) >= MAX_FILES_INSPECTED:
                warnings.append(
                    MiningWarning(
                        file_path=None,
                        warning_code="FILE_BUDGET_EXCEEDED",
                        message=f"Reached maximum file inspection budget ({MAX_FILES_INSPECTED}).",
                    )
                )
                return discovered, excluded_count, warnings

            file_path = current_dir / fname

            # Skip symlinks
            if file_path.is_symlink():
                excluded_count += 1
                continue

            # Verify file confinement
            try:
                resolved_file = file_path.resolve()
                if resolved_workspace not in resolved_file.parents and resolved_file != resolved_workspace:
                    excluded_count += 1
                    continue
            except Exception:
                excluded_count += 1
                continue

            try:
                st = file_path.stat()
                size = st.st_size

                # Check if total source bytes budget exceeded
                if total_source_bytes + size > MAX_TOTAL_SOURCE_BYTES:
                    warnings.append(
                        MiningWarning(
                            file_path=None,
                            warning_code="BYTE_BUDGET_EXCEEDED",
                            message=f"Reached maximum source bytes budget ({MAX_TOTAL_SOURCE_BYTES} bytes).",
                        )
                    )
                    return discovered, excluded_count, warnings

                # Read header to detect binary
                is_binary = False
                if size > 0:
                    try:
                        with open(file_path, "rb") as f:
                            header = f.read(8192)
                            is_binary = is_binary_content(header)
                    except Exception:
                        is_binary = True

                rel_to_root = str(file_path.relative_to(resolved_root)).replace("\\", "/")

                discovered.append(
                    DiscoveredFile(
                        abs_path=file_path,
                        rel_path=rel_to_root,
                        size_bytes=size,
                        is_binary=is_binary,
                    )
                )
                if not is_binary:
                    total_source_bytes += size

            except (PermissionError, FileNotFoundError, OSError):
                excluded_count += 1
                continue

    return discovered, excluded_count, warnings
