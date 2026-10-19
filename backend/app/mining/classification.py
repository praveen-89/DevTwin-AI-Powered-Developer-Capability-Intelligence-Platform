"""
DevTwin Mining Engine — Language and File Classification
"""

from pathlib import Path
from typing import Dict, List, Tuple

from app.mining.constants import EXTENSION_TO_LANGUAGE, SPECIAL_FILENAMES
from app.mining.models import LanguageBreakdown


def is_binary_content(header: bytes) -> bool:
    """
    Detects binary content by inspecting the first chunk of a file for null bytes.
    Standard heuristic used by Git and file classifiers.
    """
    return b"\x00" in header


def classify_file_language(file_path: Path) -> str:
    """
    Deterministically maps a file to a canonical language name based on extension or special filename.
    Returns 'Unknown' if the extension is unmapped, or 'Extensionless' if no suffix exists.
    """
    filename_lower = file_path.name.lower()
    if filename_lower in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[filename_lower]

    suffix = file_path.suffix.lower()
    if not suffix:
        return "Extensionless"

    return EXTENSION_TO_LANGUAGE.get(suffix, "Unknown")


def compute_language_breakdown(
    classified_files: List[Tuple[str, int]],
) -> List[LanguageBreakdown]:
    """
    Aggregates classified files (language, byte_count) into LanguageBreakdown metrics.
    Calculates percentage relative to total classified bytes.
    Sorts deterministically: byte count descending, then language name ascending.
    """
    language_stats: Dict[str, Dict[str, int]] = {}
    total_bytes = 0

    for lang, size in classified_files:
        if lang not in language_stats:
            language_stats[lang] = {"files": 0, "bytes": 0}
        language_stats[lang]["files"] += 1
        language_stats[lang]["bytes"] += size
        total_bytes += size

    breakdown = []
    for lang, stats in language_stats.items():
        pct = round((stats["bytes"] / total_bytes * 100.0), 2) if total_bytes > 0 else 0.0
        breakdown.append(
            LanguageBreakdown(
                language=lang,
                files_count=stats["files"],
                bytes_count=stats["bytes"],
                percentage=pct,
            )
        )

    # Sort deterministically: bytes descending, then name ascending
    breakdown.sort(key=lambda item: (-item.bytes_count, item.language))
    return breakdown
