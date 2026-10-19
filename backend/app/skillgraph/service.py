"""
DevTwin SkillGraph — Persistence Service
Persists mapped SkillGraph entities, observations, repository metadata,
and taxonomic relationships to the database within session transaction boundaries.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mining.models import MiningResult
from app.models.analysis_run import AnalysisRun
from app.models.observation import Observation
from app.models.repository_dependency import RepositoryDependency
from app.models.repository_language import RepositoryLanguage
from app.models.taxonomy import (
    Concept,
    Skill,
    SkillConcept,
    SkillRelationship,
    SkillTechnology,
    Technology,
    TechnologyConcept,
)
from app.skillgraph.mapper import map_mining_result_to_graph
from app.skillgraph.models import SkillGraphResult

logger = logging.getLogger(__name__)


async def persist_skillgraph(
    session: AsyncSession,
    run: AnalysisRun,
    repository_id: uuid.UUID,
    mining_result: MiningResult,
) -> SkillGraphResult:
    """
    Persists SkillGraph nodes, edges, repository languages, dependencies,
    and factual observations into the database.
    """
    logger.info("Mapping and persisting SkillGraph for run %s (repo %s)...", run.id, repository_id)

    mapping = map_mining_result_to_graph(
        mining_result=mining_result,
        repository_id=repository_id,
        analysis_run_id=run.id,
    )

    # -----------------------------------------------------------------------
    # 1. Persist Repository Languages (Snapshot replacement for this repo)
    # -----------------------------------------------------------------------
    await session.execute(
        delete(RepositoryLanguage).where(RepositoryLanguage.repository_id == repository_id)
    )
    for lang in mapping.languages:
        session.add(
            RepositoryLanguage(
                id=uuid.uuid4(),
                repository_id=repository_id,
                language=lang.language,
                bytes=lang.bytes,
            )
        )

    # -----------------------------------------------------------------------
    # 2. Persist Repository Dependencies (Snapshot replacement for this repo)
    # -----------------------------------------------------------------------
    await session.execute(
        delete(RepositoryDependency).where(RepositoryDependency.repository_id == repository_id)
    )
    for dep in mapping.dependencies:
        session.add(
            RepositoryDependency(
                id=uuid.uuid4(),
                repository_id=repository_id,
                ecosystem=dep.ecosystem,
                package_name=dep.package_name,
                version_constraint=dep.version_constraint,
            )
        )

    # -----------------------------------------------------------------------
    # 3. Persist Observations (Linked to this analysis_run)
    # -----------------------------------------------------------------------
    for obs in mapping.observations:
        session.add(
            Observation(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                type=obs.type,
                source_tool=obs.source_tool,
                source_reference=obs.source_reference,
                confidence=obs.confidence,
            )
        )

    # -----------------------------------------------------------------------
    # 4. Resolve & Persist Global Taxonomy Nodes
    # -----------------------------------------------------------------------
    # 4a. Skills
    skill_ids: Dict[str, uuid.UUID] = {}
    if mapping.skills:
        skill_names = [s.name for s in mapping.skills]
        res = await session.execute(select(Skill).where(Skill.name.in_(skill_names)))
        for existing_skill in res.scalars():
            skill_ids[existing_skill.name] = existing_skill.id

        for s_data in mapping.skills:
            if s_data.name not in skill_ids:
                new_id = uuid.uuid4()
                session.add(Skill(id=new_id, name=s_data.name, domain=s_data.domain))
                skill_ids[s_data.name] = new_id

    # 4b. Technologies
    tech_ids: Dict[str, uuid.UUID] = {}
    if mapping.technologies:
        tech_names = [t.name for t in mapping.technologies]
        res = await session.execute(select(Technology).where(Technology.name.in_(tech_names)))
        for existing_tech in res.scalars():
            tech_ids[existing_tech.name] = existing_tech.id

        for t_data in mapping.technologies:
            if t_data.name not in tech_ids:
                new_id = uuid.uuid4()
                session.add(Technology(id=new_id, name=t_data.name, type=t_data.type))
                tech_ids[t_data.name] = new_id

    # 4c. Concepts
    concept_ids: Dict[str, uuid.UUID] = {}
    if mapping.concepts:
        concept_names = [c.name for c in mapping.concepts]
        res = await session.execute(select(Concept).where(Concept.name.in_(concept_names)))
        for existing_concept in res.scalars():
            concept_ids[existing_concept.name] = existing_concept.id

        for c_data in mapping.concepts:
            if c_data.name not in concept_ids:
                new_id = uuid.uuid4()
                session.add(Concept(id=new_id, name=c_data.name))
                concept_ids[c_data.name] = new_id

    # Flush pending node inserts so FKs exist for junctions if flushed
    await session.flush()

    # -----------------------------------------------------------------------
    # 5. Persist Taxonomy Junctions (Edges)
    # -----------------------------------------------------------------------
    edges_persisted_count = 0

    # 5a. Skill ↔ Technology
    if mapping.skill_technologies and skill_ids and tech_ids:
        active_skill_ids = [skill_ids[s] for s, _ in mapping.skill_technologies if s in skill_ids]
        active_tech_ids = [tech_ids[t] for _, t in mapping.skill_technologies if t in tech_ids]
        existing_st: Set[Tuple[uuid.UUID, uuid.UUID]] = set()
        if active_skill_ids and active_tech_ids:
            res = await session.execute(
                select(SkillTechnology.skill_id, SkillTechnology.technology_id).where(
                    SkillTechnology.skill_id.in_(active_skill_ids),
                    SkillTechnology.technology_id.in_(active_tech_ids),
                )
            )
            existing_st = {(row[0], row[1]) for row in res.all()}

        for s_name, t_name in mapping.skill_technologies:
            if s_name in skill_ids and t_name in tech_ids:
                pair = (skill_ids[s_name], tech_ids[t_name])
                if pair not in existing_st:
                    session.add(SkillTechnology(skill_id=pair[0], technology_id=pair[1]))
                    existing_st.add(pair)
                    edges_persisted_count += 1

    # 5b. Technology ↔ Concept
    if mapping.technology_concepts and tech_ids and concept_ids:
        active_tech_ids = [tech_ids[t] for t, _ in mapping.technology_concepts if t in tech_ids]
        active_concept_ids = [concept_ids[c] for _, c in mapping.technology_concepts if c in concept_ids]
        existing_tc: Set[Tuple[uuid.UUID, uuid.UUID]] = set()
        if active_tech_ids and active_concept_ids:
            res = await session.execute(
                select(TechnologyConcept.technology_id, TechnologyConcept.concept_id).where(
                    TechnologyConcept.technology_id.in_(active_tech_ids),
                    TechnologyConcept.concept_id.in_(active_concept_ids),
                )
            )
            existing_tc = {(row[0], row[1]) for row in res.all()}

        for t_name, c_name in mapping.technology_concepts:
            if t_name in tech_ids and c_name in concept_ids:
                pair = (tech_ids[t_name], concept_ids[c_name])
                if pair not in existing_tc:
                    session.add(TechnologyConcept(technology_id=pair[0], concept_id=pair[1]))
                    existing_tc.add(pair)
                    edges_persisted_count += 1

    # 5c. Skill Relationships
    if mapping.skill_relationships and skill_ids:
        active_src_ids = [skill_ids[s] for s, _, _ in mapping.skill_relationships if s in skill_ids]
        active_tgt_ids = [skill_ids[t] for _, t, _ in mapping.skill_relationships if t in skill_ids]
        existing_sr: Set[Tuple[uuid.UUID, uuid.UUID, str]] = set()
        if active_src_ids and active_tgt_ids:
            res = await session.execute(
                select(
                    SkillRelationship.source_id,
                    SkillRelationship.target_id,
                    SkillRelationship.relation_type,
                ).where(
                    SkillRelationship.source_id.in_(active_src_ids),
                    SkillRelationship.target_id.in_(active_tgt_ids),
                )
            )
            existing_sr = {(row[0], row[1], row[2]) for row in res.all()}

        for s_name, t_name, rel_type in mapping.skill_relationships:
            if s_name in skill_ids and t_name in skill_ids:
                triplet = (skill_ids[s_name], skill_ids[t_name], rel_type)
                if triplet not in existing_sr:
                    session.add(
                        SkillRelationship(
                            source_id=triplet[0],
                            target_id=triplet[1],
                            relation_type=triplet[2],
                        )
                    )
                    existing_sr.add(triplet)
                    edges_persisted_count += 1

    now_iso = datetime.now(timezone.utc).isoformat()
    result = SkillGraphResult(
        schema_version="1.0.0",
        observations_count=len(mapping.observations),
        languages_count=len(mapping.languages),
        dependencies_count=len(mapping.dependencies),
        technologies_count=len(mapping.technologies),
        skills_count=len(mapping.skills),
        concepts_count=len(mapping.concepts),
        edges_count=edges_persisted_count,
        completed_at=now_iso,
    )

    logger.info(
        "SkillGraph persisted successfully for run %s: %d observations, %d languages, %d dependencies, %d tech, %d skills, %d concepts, %d edges.",
        run.id,
        result.observations_count,
        result.languages_count,
        result.dependencies_count,
        result.technologies_count,
        result.skills_count,
        result.concepts_count,
        result.edges_count,
    )

    return result
