"""
DevTwin Evidence — Persistence Service
Generates contextualized evidence records from grounded observations and
persists them into the database within session transaction boundaries.
"""

from collections import Counter
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.mapper import map_observations_to_evidence
from app.evidence.models import EvidenceItemData, EvidenceResult
from app.models.analysis_run import AnalysisRun
from app.models.evidence import (
    Evidence,
    EvidenceConcept,
    EvidenceSkill,
    EvidenceTechnology,
)
from app.models.observation import Observation
from app.models.taxonomy import Concept, Skill, Technology

logger = logging.getLogger(__name__)


async def persist_evidence(
    session: AsyncSession,
    run: AnalysisRun,
    observations: Optional[List[Observation]] = None,
) -> EvidenceResult:
    """
    Transforms observations for the given analysis run into evidence records,
    resolves taxonomy junction entities, and atomically persists them.
    Ensures run-level idempotency by cleaning up any pre-existing evidence for this run.
    """
    logger.info("Generating and persisting evidence for analysis run %s...", run.id)

    # 1. Fetch observations for this run if not explicitly provided
    if observations is None:
        stmt = (
            select(Observation)
            .where(Observation.analysis_run_id == run.id)
            .order_by(Observation.observed_at, Observation.id)
        )
        try:
            res = await session.execute(stmt)
            scalars = res.scalars() if hasattr(res, "scalars") and callable(res.scalars) else []
            if hasattr(scalars, "all") and callable(scalars.all):
                obs_list = list(scalars.all())
            elif isinstance(scalars, (list, tuple, set)):
                obs_list = list(scalars)
            else:
                try:
                    obs_list = list(scalars)
                except (TypeError, Exception):
                    obs_list = []
        except Exception:
            obs_list = []
    else:
        obs_list = observations

    # 2. Idempotent cleanup: Delete any pre-existing evidence for this run's observations.
    # Note: Foreign key CASCADE will automatically delete evidence_skills,
    # evidence_technologies, and evidence_concepts.
    obs_ids_stmt = select(Observation.id).where(Observation.analysis_run_id == run.id)
    await session.execute(
        delete(Evidence).where(Evidence.observation_id.in_(obs_ids_stmt))
    )

    # 3. Deterministically map observations into evidence items
    items = map_observations_to_evidence(obs_list)

    # 4. Resolve Taxonomy Entities (Skills, Technologies, Concepts)
    # 4a. Skills
    skill_ids: Dict[str, uuid.UUID] = {}
    all_skills = sorted({s for item in items for s in item.skills})
    if all_skills:
        existing_skills: List[Skill] = []
        try:
            skill_res = await session.execute(select(Skill).where(Skill.name.in_(all_skills)))
            scalars = skill_res.scalars() if hasattr(skill_res, "scalars") and callable(skill_res.scalars) else []
            if hasattr(scalars, "all") and callable(scalars.all):
                existing_skills = list(scalars.all())
            elif isinstance(scalars, (list, tuple, set)):
                existing_skills = list(scalars)
            else:
                existing_skills = list(scalars)
        except (TypeError, Exception):
            existing_skills = []

        for s in existing_skills:
            if hasattr(s, "name") and hasattr(s, "id"):
                skill_ids[s.name] = s.id
        for s_name in all_skills:
            if s_name not in skill_ids:
                new_skill_id = uuid.uuid4()
                session.add(Skill(id=new_skill_id, name=s_name, domain="General"))
                skill_ids[s_name] = new_skill_id

    # 4b. Technologies
    tech_ids: Dict[str, uuid.UUID] = {}
    all_techs = sorted({t for item in items for t in item.technologies})
    if all_techs:
        existing_techs: List[Technology] = []
        try:
            tech_res = await session.execute(select(Technology).where(Technology.name.in_(all_techs)))
            scalars = tech_res.scalars() if hasattr(tech_res, "scalars") and callable(tech_res.scalars) else []
            if hasattr(scalars, "all") and callable(scalars.all):
                existing_techs = list(scalars.all())
            elif isinstance(scalars, (list, tuple, set)):
                existing_techs = list(scalars)
            else:
                existing_techs = list(scalars)
        except (TypeError, Exception):
            existing_techs = []

        for t in existing_techs:
            if hasattr(t, "name") and hasattr(t, "id"):
                tech_ids[t.name] = t.id
        for t_name in all_techs:
            if t_name not in tech_ids:
                new_tech_id = uuid.uuid4()
                session.add(Technology(id=new_tech_id, name=t_name, type="library"))
                tech_ids[t_name] = new_tech_id

    # 4c. Concepts
    concept_ids: Dict[str, uuid.UUID] = {}
    all_concepts = sorted({c for item in items for c in item.concepts})
    if all_concepts:
        existing_concepts: List[Concept] = []
        try:
            concept_res = await session.execute(select(Concept).where(Concept.name.in_(all_concepts)))
            scalars = concept_res.scalars() if hasattr(concept_res, "scalars") and callable(concept_res.scalars) else []
            if hasattr(scalars, "all") and callable(scalars.all):
                existing_concepts = list(scalars.all())
            elif isinstance(scalars, (list, tuple, set)):
                existing_concepts = list(scalars)
            else:
                existing_concepts = list(scalars)
        except (TypeError, Exception):
            existing_concepts = []

        for c in existing_concepts:
            if hasattr(c, "name") and hasattr(c, "id"):
                concept_ids[c.name] = c.id
        for c_name in all_concepts:
            if c_name not in concept_ids:
                new_concept_id = uuid.uuid4()
                session.add(Concept(id=new_concept_id, name=c_name))
                concept_ids[c_name] = new_concept_id

    # 5. Persist Evidence and Junction Rows
    for item in items:
        ev_id = uuid.uuid4()
        session.add(
            Evidence(
                id=ev_id,
                observation_id=item.observation_id,
                type=item.type,
                strength=item.strength,
                directness=item.directness,
                reliability=item.reliability,
                polarity=item.polarity,
                recency=item.recency,
            )
        )

        for s_name in item.skills:
            if s_name in skill_ids:
                session.add(EvidenceSkill(evidence_id=ev_id, skill_id=skill_ids[s_name]))

        for t_name in item.technologies:
            if t_name in tech_ids:
                session.add(EvidenceTechnology(evidence_id=ev_id, technology_id=tech_ids[t_name]))

        for c_name in item.concepts:
            if c_name in concept_ids:
                session.add(EvidenceConcept(evidence_id=ev_id, concept_id=concept_ids[c_name]))

    await session.flush()

    by_type = Counter(item.type for item in items)
    pos_count = sum(1 for item in items if item.polarity > 0)
    neg_count = sum(1 for item in items if item.polarity < 0)
    now_iso = datetime.now(timezone.utc).isoformat()

    result = EvidenceResult(
        schema_version="1.0.0",
        evidence_version="1.0.0",
        total_evidence=len(items),
        evidence_by_type=dict(by_type),
        evidence_by_polarity={"positive": pos_count, "negative": neg_count},
        skills_count=len(skill_ids),
        technologies_count=len(tech_ids),
        concepts_count=len(concept_ids),
        items=items,
        completed_at=now_iso,
    )

    logger.info(
        "Evidence persistence completed for run %s: %d evidence items (%d positive, %d negative).",
        run.id,
        result.total_evidence,
        pos_count,
        neg_count,
    )
    return result
