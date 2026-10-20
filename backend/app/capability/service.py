"""
DevTwin Capability — Persistence Service (Step 6G)

Aggregates persisted Evidence records for an analysis run into DeveloperCapability
and CapabilityHistory records according to Capability Model v1.

Idempotency contract (ADR-004):
- capability_history rows for this analysis_run_id are deleted before re-inserting.
- DeveloperCapability rows are upserted (insert-or-update) based on the
  (developer_id, skill_id, technology_id, concept_id) UNIQUE NULLS NOT DISTINCT constraint.
- This makes repeated processing of the same run safe.

Ownership chain:
  analysis_run -> repository -> project -> developer
  developer_id is resolved via this chain, not passed in directly.
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.capability.models import CapabilityResult, TargetCapabilityScore
from app.capability.scorer import EvidenceRow, SCORING_VERSION, calculate_target_capability
from app.models.analysis_run import AnalysisRun
from app.models.capability import CapabilityHistory, DeveloperCapability
from app.models.evidence import Evidence, EvidenceConcept, EvidenceSkill, EvidenceTechnology
from app.models.observation import Observation
from app.models.project import Project
from app.models.repository import Repository
from app.models.taxonomy import Concept, Skill, Technology

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Developer resolution
# ---------------------------------------------------------------------------


async def _resolve_developer_id(
    session: AsyncSession,
    run: AnalysisRun,
) -> Optional[uuid.UUID]:
    """
    Resolve developer_id via the ownership chain:
        analysis_run -> repository -> project -> developer_id.

    Returns None if the repository has no associated project (orphan repository),
    which is a valid configuration for public repositories analysed without a project.
    """
    repo_stmt = select(Repository).where(Repository.id == run.repository_id)
    repo_res = await session.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()
    if repo is None or repo.project_id is None:
        return None

    proj_stmt = select(Project).where(Project.id == repo.project_id)
    proj_res = await session.execute(proj_stmt)
    proj = proj_res.scalar_one_or_none()
    if proj is None:
        return None

    return proj.developer_id


# ---------------------------------------------------------------------------
# Evidence loading
# ---------------------------------------------------------------------------


async def _load_evidence_for_run(
    session: AsyncSession,
    run: AnalysisRun,
) -> List[Evidence]:
    """
    Load all Evidence rows linked to observations from this analysis run,
    with eager loading of their taxonomy junction rows.
    """
    # Get observation IDs for this run
    obs_stmt = select(Observation.id).where(Observation.analysis_run_id == run.id)

    # Load evidence rows that reference these observations
    ev_stmt = (
        select(Evidence)
        .where(Evidence.observation_id.in_(obs_stmt))
        .order_by(Evidence.recency.desc(), Evidence.id)
    )
    ev_res = await session.execute(ev_stmt)
    evidence_rows = list(ev_res.scalars().all())
    return evidence_rows


async def _load_junction_rows(
    session: AsyncSession,
    evidence_ids: List[uuid.UUID],
) -> Tuple[
    Dict[uuid.UUID, List[uuid.UUID]],  # evidence_id -> [skill_ids]
    Dict[uuid.UUID, List[uuid.UUID]],  # evidence_id -> [technology_ids]
    Dict[uuid.UUID, List[uuid.UUID]],  # evidence_id -> [concept_ids]
]:
    """Load evidence_skills, evidence_technologies, evidence_concepts for the given evidence IDs."""
    if not evidence_ids:
        return {}, {}, {}

    # Skills
    sk_stmt = select(EvidenceSkill).where(EvidenceSkill.evidence_id.in_(evidence_ids))
    sk_res = await session.execute(sk_stmt)
    skill_junctions = list(sk_res.scalars().all())

    # Technologies
    tech_stmt = select(EvidenceTechnology).where(EvidenceTechnology.evidence_id.in_(evidence_ids))
    tech_res = await session.execute(tech_stmt)
    tech_junctions = list(tech_res.scalars().all())

    # Concepts
    con_stmt = select(EvidenceConcept).where(EvidenceConcept.evidence_id.in_(evidence_ids))
    con_res = await session.execute(con_stmt)
    concept_junctions = list(con_res.scalars().all())

    ev_to_skills: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    for j in skill_junctions:
        ev_to_skills[j.evidence_id].append(j.skill_id)

    ev_to_techs: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    for j in tech_junctions:
        ev_to_techs[j.evidence_id].append(j.technology_id)

    ev_to_concepts: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    for j in concept_junctions:
        ev_to_concepts[j.evidence_id].append(j.concept_id)

    return dict(ev_to_skills), dict(ev_to_techs), dict(ev_to_concepts)


async def _load_target_names(
    session: AsyncSession,
    skill_ids: List[uuid.UUID],
    tech_ids: List[uuid.UUID],
    concept_ids: List[uuid.UUID],
) -> Tuple[Dict[uuid.UUID, str], Dict[uuid.UUID, str], Dict[uuid.UUID, str]]:
    """Load human-readable names for all referenced taxonomy entities."""
    skill_names: Dict[uuid.UUID, str] = {}
    tech_names: Dict[uuid.UUID, str] = {}
    concept_names: Dict[uuid.UUID, str] = {}

    if skill_ids:
        res = await session.execute(select(Skill).where(Skill.id.in_(skill_ids)))
        for s in res.scalars().all():
            skill_names[s.id] = s.name

    if tech_ids:
        res = await session.execute(select(Technology).where(Technology.id.in_(tech_ids)))
        for t in res.scalars().all():
            tech_names[t.id] = t.name

    if concept_ids:
        res = await session.execute(select(Concept).where(Concept.id.in_(concept_ids)))
        for c in res.scalars().all():
            concept_names[c.id] = c.name

    return skill_names, tech_names, concept_names


# ---------------------------------------------------------------------------
# Grouping evidence by (target_type, target_id)
# ---------------------------------------------------------------------------


def _group_evidence_by_target(
    evidence_list: List[Evidence],
    ev_to_skills: Dict[uuid.UUID, List[uuid.UUID]],
    ev_to_techs: Dict[uuid.UUID, List[uuid.UUID]],
    ev_to_concepts: Dict[uuid.UUID, List[uuid.UUID]],
) -> Dict[Tuple[str, uuid.UUID], List[EvidenceRow]]:
    """
    Build a mapping of (target_type, target_id) -> [EvidenceRow, ...].

    A single evidence item may link to multiple taxonomy targets.
    Each (target_type, target_id) pair accumulates all evidence items that reference it.
    """
    groups: Dict[Tuple[str, uuid.UUID], List[EvidenceRow]] = defaultdict(list)

    for ev in evidence_list:
        row = EvidenceRow(
            evidence_id=ev.id,
            ev_type=ev.type,
            strength=float(ev.strength) if ev.strength is not None else None,
            directness=float(ev.directness),
            reliability=float(ev.reliability),
            polarity=float(ev.polarity),
            recency=ev.recency,
        )
        for sid in ev_to_skills.get(ev.id, []):
            groups[("skill", sid)].append(row)
        for tid in ev_to_techs.get(ev.id, []):
            groups[("technology", tid)].append(row)
        for cid in ev_to_concepts.get(ev.id, []):
            groups[("concept", cid)].append(row)

    return dict(groups)


# ---------------------------------------------------------------------------
# Upsert DeveloperCapability & append CapabilityHistory
# ---------------------------------------------------------------------------


async def _upsert_capability(
    session: AsyncSession,
    developer_id: uuid.UUID,
    score_result: TargetCapabilityScore,
) -> DeveloperCapability:
    """
    Insert or update a DeveloperCapability row using PostgreSQL ON CONFLICT DO UPDATE.
    The unique index is on (developer_id, skill_id, technology_id, concept_id)
    with NULLS NOT DISTINCT semantics (per 001_initial_schema.sql).
    Falls back to a pure Python SELECT-then-UPDATE for non-PostgreSQL test environments.
    """
    now = datetime.now(timezone.utc)

    try:
        # PostgreSQL path: upsert via ON CONFLICT
        stmt = pg_insert(DeveloperCapability).values(
            id=uuid.uuid4(),
            developer_id=developer_id,
            skill_id=score_result.skill_id,
            technology_id=score_result.technology_id,
            concept_id=score_result.concept_id,
            score=score_result.score,
            confidence=score_result.confidence,
            scoring_version=SCORING_VERSION,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="capability_unique_target",
            set_=dict(
                score=stmt.excluded.score,
                confidence=stmt.excluded.confidence,
                scoring_version=stmt.excluded.scoring_version,
                updated_at=stmt.excluded.updated_at,
            ),
        ).returning(DeveloperCapability)
        result = await session.execute(stmt)
        cap = result.scalar_one()
        return cap

    except Exception:
        # Fallback: SELECT + UPDATE (for SQLite test databases)
        existing_stmt = select(DeveloperCapability).where(
            DeveloperCapability.developer_id == developer_id,
            DeveloperCapability.skill_id == score_result.skill_id,
            DeveloperCapability.technology_id == score_result.technology_id,
            DeveloperCapability.concept_id == score_result.concept_id,
        )
        existing_res = await session.execute(existing_stmt)
        existing = existing_res.scalar_one_or_none()

        if existing is not None:
            existing.score = score_result.score
            existing.confidence = score_result.confidence
            existing.scoring_version = SCORING_VERSION
            existing.updated_at = now
            session.add(existing)
            await session.flush([existing])
            return existing
        else:
            cap = DeveloperCapability(
                id=uuid.uuid4(),
                developer_id=developer_id,
                skill_id=score_result.skill_id,
                technology_id=score_result.technology_id,
                concept_id=score_result.concept_id,
                score=score_result.score,
                confidence=score_result.confidence,
                scoring_version=SCORING_VERSION,
                updated_at=now,
            )
            session.add(cap)
            await session.flush([cap])
            return cap


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def persist_capabilities(
    session: AsyncSession,
    run: AnalysisRun,
) -> CapabilityResult:
    """
    Stage 7: Aggregate persisted evidence for the given analysis run into
    DeveloperCapability and CapabilityHistory records.

    Idempotency: CapabilityHistory rows for this run.id are deleted first.
    DeveloperCapability rows are upserted (never duplicated).

    Parameters
    ----------
    session : AsyncSession
        Active SQLAlchemy async session within a caller-managed transaction.
    run : AnalysisRun
        The analysis run whose evidence should be scored.

    Returns
    -------
    CapabilityResult
        Summary of what was scored and persisted.
    """
    logger.info("Starting Capability Scoring for analysis run %s...", run.id)

    # 1. Resolve developer ownership
    developer_id = await _resolve_developer_id(session, run)
    if developer_id is None:
        logger.warning(
            "No developer owner found for run %s (repository has no linked project). "
            "Capability scoring skipped — no DeveloperCapability rows written.",
            run.id,
        )
        return CapabilityResult(
            developer_id=None,
            total_targets=0,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    # 2. Load evidence for this run
    evidence_list = await _load_evidence_for_run(session, run)
    if not evidence_list:
        logger.info(
            "No evidence found for run %s. Returning zero-evidence CapabilityResult.",
            run.id,
        )
        return CapabilityResult(
            developer_id=developer_id,
            total_targets=0,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    evidence_ids = [ev.id for ev in evidence_list]

    # 3. Load junction rows (evidence -> taxonomy targets)
    ev_to_skills, ev_to_techs, ev_to_concepts = await _load_junction_rows(session, evidence_ids)

    # 4. Collect all target IDs for name loading
    all_skill_ids = list({sid for ids in ev_to_skills.values() for sid in ids})
    all_tech_ids = list({tid for ids in ev_to_techs.values() for tid in ids})
    all_concept_ids = list({cid for ids in ev_to_concepts.values() for cid in ids})

    skill_names, tech_names, concept_names = await _load_target_names(
        session, all_skill_ids, all_tech_ids, all_concept_ids
    )

    # 5. Group evidence by (target_type, target_id)
    groups = _group_evidence_by_target(
        evidence_list, ev_to_skills, ev_to_techs, ev_to_concepts
    )

    if not groups:
        logger.info(
            "Evidence exists for run %s but no taxonomy targets found (no junction rows). "
            "Returning zero-target CapabilityResult.",
            run.id,
        )
        return CapabilityResult(
            developer_id=developer_id,
            total_targets=0,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    # 6. Idempotency: delete capability_history rows for this run
    await session.execute(
        delete(CapabilityHistory).where(
            CapabilityHistory.analysis_run_id == run.id
        )
    )
    logger.debug("Cleaned up existing CapabilityHistory for run %s.", run.id)

    # 7. Score each target and persist
    now = datetime.now(timezone.utc)
    scored: List[TargetCapabilityScore] = []
    history_count = 0

    for (target_type, target_id), rows in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        # Resolve human-readable name
        if target_type == "skill":
            target_name = skill_names.get(target_id, str(target_id))
        elif target_type == "technology":
            target_name = tech_names.get(target_id, str(target_id))
        else:
            target_name = concept_names.get(target_id, str(target_id))

        # Score
        score_result = calculate_target_capability(
            evidence_rows=rows,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            now=now,
        )
        scored.append(score_result)

        # Upsert DeveloperCapability
        cap = await _upsert_capability(session, developer_id, score_result)

        # Append CapabilityHistory (append-only, ADR-004)
        history_row = CapabilityHistory(
            id=uuid.uuid4(),
            capability_id=cap.id,
            analysis_run_id=run.id,
            score=score_result.score,
            confidence=score_result.confidence,
            scoring_version=SCORING_VERSION,
            recorded_at=now,
        )
        session.add(history_row)
        history_count += 1

    await session.flush()

    # 8. Build result summary
    targets_by_type: Dict[str, int] = defaultdict(int)
    score_dist: Dict[str, int] = {"low": 0, "moderate": 0, "high": 0}
    confidences: List[float] = []

    for s in scored:
        targets_by_type[s.target_type] += 1
        confidences.append(s.confidence)
        if s.score < 0.33:
            score_dist["low"] += 1
        elif s.score <= 0.66:
            score_dist["moderate"] += 1
        else:
            score_dist["high"] += 1

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    result = CapabilityResult(
        schema_version="1.0.0",
        scoring_version=SCORING_VERSION,
        developer_id=developer_id,
        total_targets=len(scored),
        targets_by_type=dict(targets_by_type),
        score_distribution=score_dist,
        avg_confidence=avg_conf,
        history_entries_appended=history_count,
        completed_at=now.isoformat(),
        scores=scored,
    )

    logger.info(
        "Capability Scoring completed for run %s: %d targets scored "
        "(%d skills, %d technologies, %d concepts), avg_confidence=%.3f, "
        "%d history entries appended.",
        run.id,
        result.total_targets,
        result.targets_by_type.get("skill", 0),
        result.targets_by_type.get("technology", 0),
        result.targets_by_type.get("concept", 0),
        result.avg_confidence,
        result.history_entries_appended,
    )
    return result
