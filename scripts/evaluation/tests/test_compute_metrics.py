"""
DevTwin Phase 14 — Unit tests for compute_metrics.py.

Hermetic: no live PostgreSQL connection and no live GitHub call required.
Follows the same mocking convention as backend/tests/test_capability.py
(AsyncMock for the SQLAlchemy session, MagicMock for query results) so
these tests are consistent with the rest of the codebase's test style.

Placed under scripts/evaluation/tests/ (not backend/tests/) because
compute_metrics.py is a standalone evaluation script, not part of the
`app` package shipped with the backend service — it imports `app.*`
models for convenience but is not itself part of that package's test
surface or CI gate.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure backend/ is importable (same mechanism compute_metrics.py uses).
BACKEND_ROOT = Path(__file__).resolve().parents[3] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Backend test suite's conftest sets hermetic env vars before `app.*` import;
# replicate the minimal subset needed here so this module is importable
# standalone (e.g. `pytest scripts/evaluation/tests`).
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service")
os.environ.setdefault("SECRET_KEY", "secret")
os.environ.setdefault("GITHUB_APP_ID", "123")
os.environ.setdefault("GITHUB_APP_SLUG", "app")
os.environ.setdefault("GITHUB_CLIENT_ID", "client")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "secret")
os.environ.setdefault("GITHUB_PRIVATE_KEY", "pem")
os.environ.setdefault("GITHUB_REDIRECT_URL", "http://localhost/cb")
os.environ.setdefault("GITHUB_STATE_ENCRYPTION_KEY", "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compute_metrics import (  # noqa: E402
    GroundTruth,
    extraction_precision_recall,
    parse_ground_truth,
    provenance_traceability,
)
from run_evaluation import parse_dataset  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scalars_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _scalar_one_result(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


# ---------------------------------------------------------------------------
# dataset.md parsing
# ---------------------------------------------------------------------------


def test_parse_dataset_skips_pending_selection_rows(tmp_path):
    content = """
| # | Repo (owner/name) | Size class | Ground truth defined? |
|---|---|---|---|
| 1 | `acme/widgets` | Mid | Yes |
| 2 | `<PENDING SELECTION>` | Small | No |
| 3 | `acme/another` | Small | Yes |
"""
    path = tmp_path / "dataset.md"
    path.write_text(content, encoding="utf-8")

    slugs = parse_dataset(path)

    assert slugs == ["acme/widgets", "acme/another"]


def test_parse_ground_truth_extracts_expected_hits_only(tmp_path):
    content = """
### Ground Truth — Repo 1: acme/widgets

### Expected languages (`repository_languages` / `CANONICAL_LANGUAGES`)

| Language | Expected to be detected? | Notes |
|---|---|---|
| Python | Yes | core |
| COBOL | No | not present |

### Expected dependencies (`repository_dependencies` / `CANONICAL_DEPENDENCIES`)

In taxonomy (expected HIT):
- `fastapi`
- `pytest`

Known to be used but NOT in `CANONICAL_DEPENDENCIES` (expected MISS):
- `some-unlisted-package`
"""
    path = tmp_path / "dataset.md"
    path.write_text(content, encoding="utf-8")

    sections = parse_ground_truth(path)

    assert "acme/widgets" in sections
    truth = sections["acme/widgets"]
    assert truth.defined is True
    assert "python" in truth.expected_languages
    assert "cobol" not in truth.expected_languages
    assert truth.expected_dependencies == {"fastapi", "pytest"}
    assert "some-unlisted-package" not in truth.expected_dependencies


# ---------------------------------------------------------------------------
# Precision / recall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extraction_precision_recall_missing_ground_truth_flagged():
    session = AsyncMock()
    truth = GroundTruth(full_name="acme/widgets")  # defined=False by default

    result = await extraction_precision_recall(session, uuid.uuid4(), truth)

    assert result == {"ground_truth_missing": True}
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_extraction_precision_recall_perfect_match():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _scalars_result(["Python", "TypeScript"]),
            _scalars_result(["fastapi", "pytest"]),
        ]
    )
    truth = GroundTruth(
        full_name="acme/widgets",
        expected_languages={"python", "typescript"},
        expected_dependencies={"fastapi", "pytest"},
        defined=True,
    )

    result = await extraction_precision_recall(session, uuid.uuid4(), truth)

    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["false_positives"] == []
    assert result["false_negatives"] == []


@pytest.mark.asyncio
async def test_extraction_precision_recall_partial_match_no_division_by_zero():
    session = AsyncMock()
    # Detected nothing at all (e.g. empty repo) — must not raise ZeroDivisionError.
    session.execute = AsyncMock(
        side_effect=[
            _scalars_result([]),
            _scalars_result([]),
        ]
    )
    truth = GroundTruth(
        full_name="acme/widgets",
        expected_languages={"python"},
        expected_dependencies=set(),
        defined=True,
    )

    result = await extraction_precision_recall(session, uuid.uuid4(), truth)

    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["detected_count"] == 0


@pytest.mark.asyncio
async def test_extraction_precision_recall_false_positive_and_negative():
    session = AsyncMock()
    # Detected "rust" (unexpected -> false positive) but missed "python" (false negative).
    session.execute = AsyncMock(
        side_effect=[
            _scalars_result(["Rust"]),
            _scalars_result([]),
        ]
    )
    truth = GroundTruth(
        full_name="acme/widgets",
        expected_languages={"python"},
        expected_dependencies=set(),
        defined=True,
    )

    result = await extraction_precision_recall(session, uuid.uuid4(), truth)

    assert result["false_positives"] == ["rust"]
    assert result["false_negatives"] == ["python"]
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0


# ---------------------------------------------------------------------------
# Provenance traceability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provenance_traceability_no_capability_history_rows():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_scalars_result([])])

    result = await provenance_traceability(session, uuid.uuid4(), uuid.uuid4())

    assert result["capability_rows_checked"] == 0
    assert result["traceable_count"] == 0
    assert result["traceable_percentage"] is None


@pytest.mark.asyncio
async def test_provenance_traceability_mixed_traceable_and_untraceable():
    history_row_1 = MagicMock(id=uuid.uuid4(), capability_id=uuid.uuid4())
    history_row_2 = MagicMock(id=uuid.uuid4(), capability_id=uuid.uuid4())

    cap_1 = MagicMock(id=history_row_1.capability_id, skill_id=uuid.uuid4(), technology_id=None, concept_id=None)
    cap_2 = MagicMock(id=history_row_2.capability_id, skill_id=None, technology_id=uuid.uuid4(), concept_id=None)

    evidence_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _scalars_result([history_row_1, history_row_2]),  # CapabilityHistory rows
            _scalar_one_result(cap_1),                          # DeveloperCapability for row 1
            _scalars_result([evidence_id]),                     # EvidenceSkill.evidence_id for cap_1
            _scalar_one_result(evidence_id),                    # Evidence JOIN Observation exists -> traceable
            _scalar_one_result(cap_2),                          # DeveloperCapability for row 2
            _scalars_result([]),                                 # EvidenceTechnology.evidence_id for cap_2 -> none
        ]
    )

    result = await provenance_traceability(session, uuid.uuid4(), uuid.uuid4())

    assert result["capability_rows_checked"] == 2
    assert result["traceable_count"] == 1
    assert result["traceable_percentage"] == 50.0
    assert str(history_row_2.id) in result["untraceable_capability_history_ids"]


@pytest.mark.asyncio
async def test_provenance_traceability_evidence_without_observation_is_untraceable():
    """Evidence exists but its observation_id FK was SET NULL (observation deleted) -> untraceable."""
    history_row = MagicMock(id=uuid.uuid4(), capability_id=uuid.uuid4())
    cap = MagicMock(id=history_row.capability_id, skill_id=uuid.uuid4(), technology_id=None, concept_id=None)
    evidence_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _scalars_result([history_row]),
            _scalar_one_result(cap),
            _scalars_result([evidence_id]),
            _scalar_one_result(None),  # JOIN Observation finds nothing -> untraceable
        ]
    )

    result = await provenance_traceability(session, uuid.uuid4(), uuid.uuid4())

    assert result["traceable_count"] == 0
    assert result["traceable_percentage"] == 0.0
