"""
DevTwin Mining Engine — Coordinator
Executes bounded repository mining on an extracted workspace tree.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from app.mining.ast_parser import PythonASTParser
from app.mining.classification import (
    classify_file_language,
    compute_language_breakdown,
)
from app.mining.constants import MAX_AST_FILES_PARSED
from app.mining.manifests import extract_manifest_if_applicable
from app.mining.models import (
    ASTFileSummary,
    ManifestSummary,
    MiningResult,
    MiningWarning,
    RepositoryInventory,
)
from app.mining.traversal import safe_walk_workspace

logger = logging.getLogger(__name__)


def mine_repository(
    root_dir: Path,
    workspace_dir: Path,
) -> MiningResult:
    """
    Performs bounded, secure repository mining on a local file tree within an isolated workspace.

    Executes:
    1. Safe file-tree traversal with exclusion of dependencies, builds, and caches.
    2. Language & file classification.
    3. Defensive manifest extraction (package.json, requirements.txt, Cargo.toml).
    4. Python AST parsing for functions, classes, and imports.
    5. Assembly of deterministically sorted MiningResult.
    """
    logger.info("Beginning repository mining for: %s", root_dir)
    discovered_files, excluded_count, warnings = safe_walk_workspace(
        root_dir=root_dir,
        workspace_dir=workspace_dir,
    )

    total_files = len(discovered_files)
    source_files = 0
    binary_files = 0
    total_bytes = 0
    source_bytes = 0

    classified_files: List[Tuple[str, int]] = []
    manifests: List[ManifestSummary] = []
    ast_summaries: List[ASTFileSummary] = []

    python_parser = PythonASTParser()
    ast_files_count = 0

    for disc in discovered_files:
        total_bytes += disc.size_bytes
        if disc.is_binary:
            binary_files += 1
            classified_files.append(("Binary", disc.size_bytes))
            continue

        source_files += 1
        source_bytes += disc.size_bytes

        lang = classify_file_language(disc.abs_path)
        classified_files.append((lang, disc.size_bytes))

        # Check for manifests
        manifest, m_warnings = extract_manifest_if_applicable(
            file_path=disc.abs_path,
            rel_path=disc.rel_path,
        )
        if manifest:
            manifests.append(manifest)
        if m_warnings:
            warnings.extend(m_warnings)

        # Check for AST parsing (Python in Step 6C)
        if python_parser.can_parse(disc.abs_path):
            if ast_files_count < MAX_AST_FILES_PARSED:
                ast_files_count += 1
                try:
                    with open(disc.abs_path, "rb") as f:
                        source_bytes_content = f.read()
                    ast_summary, ast_warns = python_parser.parse_file(
                        file_path=disc.abs_path,
                        rel_path=disc.rel_path,
                        source_bytes=source_bytes_content,
                    )
                    if ast_summary:
                        ast_summaries.append(ast_summary)
                    if ast_warns:
                        warnings.extend(ast_warns)
                except Exception as exc:
                    warnings.append(
                        MiningWarning(
                            file_path=disc.rel_path,
                            warning_code="AST_READ_ERROR",
                            message=f"Failed to read file for AST: {type(exc).__name__}.",
                        )
                    )

    # Compute language breakdown
    language_breakdown = compute_language_breakdown(classified_files)

    # Deterministic sorting
    manifests.sort(key=lambda m: m.file_path)
    ast_summaries.sort(key=lambda a: a.file_path)
    warnings.sort(key=lambda w: (w.file_path or "", w.warning_code))

    inventory = RepositoryInventory(
        total_files=total_files,
        source_files=source_files,
        binary_files=binary_files,
        excluded_files=excluded_count,
        total_bytes=total_bytes,
        source_bytes=source_bytes,
    )

    completed_at = datetime.now(timezone.utc).isoformat()

    result = MiningResult(
        schema_version="1.0.0",
        mining_version="1.0.0",
        inventory=inventory,
        languages=language_breakdown,
        manifests=manifests,
        ast_summaries=ast_summaries,
        warnings=warnings,
        completed_at=completed_at,
    )

    logger.info(
        "Mining finished: %d files (%d source, %d binary, %d excluded), %d languages, %d manifests, %d AST files, %d warnings.",
        inventory.total_files,
        inventory.source_files,
        inventory.binary_files,
        inventory.excluded_files,
        len(result.languages),
        len(result.manifests),
        len(result.ast_summaries),
        len(result.warnings),
    )
    return result
