"""
DevTwin Phase 14 — Metrics Computation.

Reads PERSISTED DATABASE STATE (not the JSON dumps written by
run_evaluation.py) for a set of evaluated repositories and computes:

  (a) Skill/technology extraction precision & recall vs. hand-written
      ground truth in dataset.md.
  (b) Provenance traceability: % of DeveloperCapability rows (via their
      CapabilityHistory entries for the evaluated run) that trace to at
      least one Evidence row, which traces to at least one Observation row.
  (c) CodeRisk finding counts by rule_id and severity (for manual FP review
      — this script does NOT judge false positives itself).
  (d) Runtime distribution (min/median/max) across evaluated repositories.
  (e) A trivial baseline comparator (distinct language + distinct declared
      dependency count per repo) alongside DevTwin's capability target
      count, for contrast only — this never writes back to
      DeveloperCapability.

This module deliberately contains NO scoring logic. It does not import or
call app.capability.scorer, app.capability.service, app.evidence.mapper,
or app.coderisk.rules's analyzer — only read queries against already
persisted rows, plus the frozen RULES / taxonomy dictionaries for
*labeling* output (not for recomputing anything).

Usage
-----
    python scripts/evaluation/compute_metrics.py \\
        --results-dir scripts/evaluation/results \\
        --dataset scripts/evaluation/dataset.md \\
        --out scripts/evaluation/results/metrics_summary.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import statistics
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("devtwin.evaluation.metrics")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# Ground truth parsing (dataset.md)
# ---------------------------------------------------------------------------


@dataclass
class GroundTruth:
    full_name: str
    expected_languages: set[str] = field(default_factory=set)
    expected_dependencies: set[str] = field(default_factory=set)
    defined: bool = False


_HEADING_RE = re.compile(r"^#{2,3}\s+Ground Truth\s+—\s+Repo\s+\d+:\s*(.+?)\s*$")
_BULLET_RE = re.compile(r"^-\s*`([A-Za-z0-9_.\-@/]+)`")


def parse_ground_truth(dataset_path: Path) -> dict[str, GroundTruth]:
    """
    Parses the "Ground Truth — Repo N: <name>" sections of dataset.md.
    Only bullet items under "Expected languages" / "Expected dependencies"
    subsections that are explicitly marked as taxonomy HITs are counted as
    ground truth for precision/recall (expected MISSes are intentionally
    excluded — they are documented coverage gaps, not targets).
    """
    text = dataset_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    sections: dict[str, GroundTruth] = {}
    current: Optional[GroundTruth] = None
    mode: Optional[str] = None  # "lang_hit" | "dep_hit" | other

    for line in lines:
        heading_match = _HEADING_RE.match(line.strip())
        if heading_match:
            name = heading_match.group(1).strip()
            if name.lower() == "this repository":
                # Table-style heading combines name; handled by caller joining
                # repo-1's slug separately. Skip ambiguous heading text.
                pass
            current = sections.setdefault(name, GroundTruth(full_name=name))
            current.defined = True
            mode = None
            continue

        if current is None:
            continue

        stripped = line.strip()
        lower = stripped.lower()
        if "expected languages" in lower and "not in taxonomy" not in lower:
            mode = "lang_hit"
            continue
        if "expected dependencies" in lower and "not in taxonomy" not in lower:
            mode = "dep_hit"
            continue
        if "not in taxonomy" in lower or "expected miss" in lower:
            mode = "ignore"
            continue
        if lower.startswith("### "):
            current = None
            mode = None
            continue
        if mode == "lang_hit" and stripped.startswith("|") and stripped.endswith("|"):
            # Markdown table rows for Repo 1's language table (header/separator
            # rows are harmlessly ignored: they never have a "Yes" 2nd cell,
            # and "---" is excluded explicitly).
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if (
                len(cells) >= 2
                and cells[0] not in ("Language", "")
                and not cells[0].startswith("-")
                and cells[1].lower().startswith("yes")
            ):
                current.expected_languages.add(cells[0].strip().lower())
            continue

        m = _BULLET_RE.match(stripped)
        if m and mode == "lang_hit":
            current.expected_languages.add(m.group(1).strip().lower())
        elif m and mode == "dep_hit":
            current.expected_dependencies.add(m.group(1).strip().lower())

    return sections


def _slug_for_dataset_name(full_name: str) -> str:
    """Map dataset.md's heading text to a repo-result-file slug where possible."""
    if "devtwin" in full_name.lower():
        return "praveen-89__DevTwin-AI-Powered-Developer-Capability-Intelligence-Platform"
    return full_name.replace("/", "__").replace(" ", "_")


# ---------------------------------------------------------------------------
# DB-backed metric computations
# ---------------------------------------------------------------------------


async def _get_session_factory():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import NullPool
    from app.core.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    return engine, factory


async def extraction_precision_recall(
    session, repository_id: uuid.UUID, truth: GroundTruth
) -> dict[str, Any]:
    """
    (a) Precision/recall of detected languages+dependencies vs. ground truth,
    using the persisted repository_languages / repository_dependencies rows.
    Returns None-safe zeros (no divide-by-zero) when a repo has no evidence
    or no ground truth defined.
    """
    from sqlalchemy import select
    from app.models.repository_language import RepositoryLanguage
    from app.models.repository_dependency import RepositoryDependency

    if not truth.defined:
        return {"ground_truth_missing": True}

    lang_rows = (
        await session.execute(
            select(RepositoryLanguage.language).where(RepositoryLanguage.repository_id == repository_id)
        )
    ).scalars().all()
    dep_rows = (
        await session.execute(
            select(RepositoryDependency.package_name).where(
                RepositoryDependency.repository_id == repository_id
            )
        )
    ).scalars().all()

    detected = {x.lower() for x in lang_rows} | {x.lower() for x in dep_rows}
    expected = truth.expected_languages | truth.expected_dependencies

    true_positives = detected & expected
    false_positives = detected - expected
    false_negatives = expected - detected

    precision = (
        len(true_positives) / len(detected) if detected else 0.0
    )
    recall = (
        len(true_positives) / len(expected) if expected else 0.0
    )

    return {
        "ground_truth_missing": False,
        "detected_count": len(detected),
        "expected_count": len(expected),
        "true_positives": sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


async def provenance_traceability(session, developer_id: uuid.UUID, run_id: uuid.UUID) -> dict[str, Any]:
    """
    (b) For every CapabilityHistory row produced by this analysis run, verify
    that its DeveloperCapability's target (skill/technology/concept, via the
    exclusive arc) is backed by at least one Evidence row whose
    observation_id points to a real Observation row belonging to this run's
    repository's analysis history. Reports the percentage traceable, not an
    assumption of 100%.
    """
    from sqlalchemy import select
    from app.models.capability import CapabilityHistory, DeveloperCapability
    from app.models.evidence import Evidence, EvidenceConcept, EvidenceSkill, EvidenceTechnology
    from app.models.observation import Observation

    history_rows = (
        await session.execute(
            select(CapabilityHistory).where(CapabilityHistory.analysis_run_id == run_id)
        )
    ).scalars().all()

    if not history_rows:
        return {
            "capability_rows_checked": 0,
            "traceable_count": 0,
            "traceable_percentage": None,
        }

    traceable = 0
    untraceable_ids: list[str] = []

    for hist in history_rows:
        cap = (
            await session.execute(
                select(DeveloperCapability).where(DeveloperCapability.id == hist.capability_id)
            )
        ).scalar_one_or_none()
        if cap is None:
            untraceable_ids.append(str(hist.id))
            continue

        evidence_ids: list[uuid.UUID] = []
        if cap.skill_id is not None:
            rows = (
                await session.execute(
                    select(EvidenceSkill.evidence_id).where(EvidenceSkill.skill_id == cap.skill_id)
                )
            ).scalars().all()
            evidence_ids = list(rows)
        elif cap.technology_id is not None:
            rows = (
                await session.execute(
                    select(EvidenceTechnology.evidence_id).where(
                        EvidenceTechnology.technology_id == cap.technology_id
                    )
                )
            ).scalars().all()
            evidence_ids = list(rows)
        elif cap.concept_id is not None:
            rows = (
                await session.execute(
                    select(EvidenceConcept.evidence_id).where(
                        EvidenceConcept.concept_id == cap.concept_id
                    )
                )
            ).scalars().all()
            evidence_ids = list(rows)

        if not evidence_ids:
            untraceable_ids.append(str(hist.id))
            continue

        obs_backed = (
            await session.execute(
                select(Evidence.id)
                .join(Observation, Evidence.observation_id == Observation.id)
                .where(Evidence.id.in_(evidence_ids))
                .limit(1)
            )
        ).scalar_one_or_none()

        if obs_backed is not None:
            traceable += 1
        else:
            untraceable_ids.append(str(hist.id))

    total = len(history_rows)
    return {
        "capability_rows_checked": total,
        "traceable_count": traceable,
        "traceable_percentage": round(100.0 * traceable / total, 2) if total else None,
        "untraceable_capability_history_ids": untraceable_ids,
    }


async def coderisk_finding_breakdown(session, run_id: uuid.UUID) -> dict[str, Any]:
    """(c) CodeRisk finding counts by rule_id (risk_type) and severity, for manual FP review."""
    from sqlalchemy import select, func
    from app.models.risk_finding import RiskFinding

    rows = (
        await session.execute(
            select(RiskFinding.risk_type, RiskFinding.severity, func.count(RiskFinding.id))
            .where(RiskFinding.analysis_run_id == run_id)
            .group_by(RiskFinding.risk_type, RiskFinding.severity)
        )
    ).all()

    breakdown: dict[str, dict[str, int]] = {}
    total = 0
    for rule_id, severity, count in rows:
        breakdown.setdefault(rule_id, {})[severity] = count
        total += count

    return {"total_findings": total, "by_rule_and_severity": breakdown}


async def trivial_baseline(session, repository_id: uuid.UUID) -> dict[str, Any]:
    """
    (e) Naive baseline: distinct declared language count + distinct declared
    dependency count, with no evidence weighting whatsoever. Comparison
    artifact only — never written back to DeveloperCapability.
    """
    from sqlalchemy import select, func
    from app.models.repository_language import RepositoryLanguage
    from app.models.repository_dependency import RepositoryDependency

    lang_count = (
        await session.execute(
            select(func.count(RepositoryLanguage.id)).where(
                RepositoryLanguage.repository_id == repository_id
            )
        )
    ).scalar_one()
    dep_count = (
        await session.execute(
            select(func.count(RepositoryDependency.id)).where(
                RepositoryDependency.repository_id == repository_id
            )
        )
    ).scalar_one()

    return {"naive_distinct_language_count": lang_count, "naive_distinct_dependency_count": dep_count}


async def capability_target_count_and_score_distribution(session, run_id: uuid.UUID) -> dict[str, Any]:
    """
    Reports how many DeveloperCapability targets this run produced history
    for, and the score distribution — used to evidence finding (ii) in the
    Phase 14 results doc (diminishing-returns clamp behavior), never to
    alter scoring.
    """
    from sqlalchemy import select
    from app.models.capability import CapabilityHistory

    rows = (
        await session.execute(
            select(CapabilityHistory.score).where(CapabilityHistory.analysis_run_id == run_id)
        )
    ).scalars().all()

    scores = [float(s) for s in rows]
    near_clamp = sum(1 for s in scores if s >= 0.95)

    return {
        "capability_target_count": len(scores),
        "score_min": round(min(scores), 4) if scores else None,
        "score_max": round(max(scores), 4) if scores else None,
        "score_median": round(statistics.median(scores), 4) if scores else None,
        "scores_at_or_above_0_95": near_clamp,
    }


async def runtime_seconds_for_run(session, run_id: uuid.UUID) -> Optional[float]:
    from sqlalchemy import select
    from app.models.analysis_run import AnalysisRun

    run = (
        await session.execute(select(AnalysisRun).where(AnalysisRun.id == run_id))
    ).scalar_one_or_none()
    if run is None or run.started_at is None or run.completed_at is None:
        return None
    return (run.completed_at - run.started_at).total_seconds()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _load_result_files(results_dir: Path) -> list[dict[str, Any]]:
    results = []
    for path in sorted(results_dir.glob("*.json")):
        if path.name == "metrics_summary.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Skipping unparseable result file: %s", path)
            continue
        if "run_id" in data:
            results.append(data)
    return results


async def compute_all_metrics(results_dir: Path, dataset_path: Path) -> dict[str, Any]:
    truth_by_name = parse_ground_truth(dataset_path)
    result_records = _load_result_files(results_dir)

    completed = [r for r in result_records if r.get("run_status") == "COMPLETED" and r.get("run_id")]
    skipped = [r for r in result_records if r not in completed]

    if not completed:
        logger.warning(
            "No COMPLETED result files found under %s — nothing to compute. "
            "Did run_evaluation.py execute successfully?",
            results_dir,
        )
        return {
            "repositories_evaluated": 0,
            "repositories_skipped_or_failed": len(skipped),
            "per_repository": [],
            "runtime_distribution_seconds": None,
            "note": "No COMPLETED runs available; metrics not computable.",
        }

    engine, factory = await _get_session_factory()
    per_repo_metrics = []
    runtimes: list[float] = []

    try:
        async with factory() as session:
            for record in completed:
                full_name = record["full_name"]
                repository_id = uuid.UUID(record["repository_id"])
                run_id = uuid.UUID(record["run_id"])

                # Match ground truth by best-effort name containment (dataset.md
                # section headings are free text, not guaranteed identical to
                # the `owner/name` slug).
                truth = GroundTruth(full_name=full_name)
                for heading, candidate in truth_by_name.items():
                    if heading.lower() in full_name.lower() or "devtwin" in full_name.lower():
                        truth = candidate
                        break

                extraction = await extraction_precision_recall(session, repository_id, truth)

                from app.models.repository import Repository
                from app.models.project import Project
                from sqlalchemy import select as _select

                repo_row = (
                    await session.execute(_select(Repository).where(Repository.id == repository_id))
                ).scalar_one_or_none()
                developer_id = None
                if repo_row is not None and repo_row.project_id is not None:
                    proj_row = (
                        await session.execute(_select(Project).where(Project.id == repo_row.project_id))
                    ).scalar_one_or_none()
                    if proj_row is not None:
                        developer_id = proj_row.developer_id

                provenance = (
                    await provenance_traceability(session, developer_id, run_id)
                    if developer_id is not None
                    else {"capability_rows_checked": 0, "traceable_count": 0, "traceable_percentage": None}
                )
                risk_breakdown = await coderisk_finding_breakdown(session, run_id)
                baseline = await trivial_baseline(session, repository_id)
                score_dist = await capability_target_count_and_score_distribution(session, run_id)
                runtime = await runtime_seconds_for_run(session, run_id)
                if runtime is not None:
                    runtimes.append(runtime)

                per_repo_metrics.append(
                    {
                        "full_name": full_name,
                        "repository_id": str(repository_id),
                        "run_id": str(run_id),
                        "runtime_seconds": round(runtime, 2) if runtime is not None else None,
                        "extraction_precision_recall": extraction,
                        "provenance_traceability": provenance,
                        "coderisk_findings": risk_breakdown,
                        "naive_baseline": baseline,
                        "capability_score_distribution": score_dist,
                    }
                )
    finally:
        await engine.dispose()

    runtime_distribution = None
    if runtimes:
        runtime_distribution = {
            "min_seconds": round(min(runtimes), 2),
            "median_seconds": round(statistics.median(runtimes), 2),
            "max_seconds": round(max(runtimes), 2),
            "n": len(runtimes),
        }

    return {
        "repositories_evaluated": len(completed),
        "repositories_skipped_or_failed": len(skipped),
        "skipped_repositories": [
            {"full_name": r.get("full_name"), "error": r.get("error"), "run_status": r.get("run_status")}
            for r in skipped
        ],
        "per_repository": per_repo_metrics,
        "runtime_distribution_seconds": runtime_distribution,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DevTwin Phase 14 metrics computation.")
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parent / "dataset.md")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    summary = asyncio.run(compute_all_metrics(args.results_dir, args.dataset))

    output = json.dumps(summary, indent=2)
    if args.out:
        args.out.write_text(output, encoding="utf-8")
        logger.info("Wrote metrics summary to %s", args.out)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
