import logging
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.dependencies.auth import (
    AuthenticatedUser,
    get_current_developer,
    get_current_user,
)
from app.db.connection import get_db_session
from app.models.analysis_run import AnalysisRun
from app.models.capability import CapabilityHistory, DeveloperCapability
from app.models.developer import Developer
from app.models.evidence import (
    Evidence,
    EvidenceConcept,
    EvidenceSkill,
    EvidenceTechnology,
)
from app.models.observation import Observation
from app.models.project import Project
from app.models.repository import Repository
from app.models.taxonomy import Concept, Skill, Technology
from app.schemas.capability import (
    CapabilityHistoryItemResponse,
    CapabilityHistoryListResponse,
    CapabilityTargetResponse,
    DeveloperCapabilityListResponse,
    DeveloperCapabilityResponse,
)
from app.schemas.developer import DeveloperResponse
from app.schemas.evidence import (
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceSourceProvenance,
    EvidenceTaxonomyRef,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/developers", tags=["Developers"])


def _format_target(
    skill: Optional[Skill],
    tech: Optional[Technology],
    concept: Optional[Concept],
    skill_id: Optional[uuid.UUID] = None,
    tech_id: Optional[uuid.UUID] = None,
    concept_id: Optional[uuid.UUID] = None,
) -> CapabilityTargetResponse:
    if skill_id and skill:
        return CapabilityTargetResponse(
            target_type="skill",
            target_id=skill.id,
            target_name=skill.name,
            domain_or_category=skill.domain,
        )
    elif tech_id and tech:
        return CapabilityTargetResponse(
            target_type="technology",
            target_id=tech.id,
            target_name=tech.name,
            domain_or_category=tech.type,
        )
    elif concept_id and concept:
        return CapabilityTargetResponse(
            target_type="concept",
            target_id=concept.id,
            target_name=concept.name,
            domain_or_category=None,
        )
    else:
        t_type = "skill" if skill_id else ("technology" if tech_id else "concept")
        t_id = skill_id or tech_id or concept_id or uuid.uuid4()
        return CapabilityTargetResponse(
            target_type=t_type,
            target_id=t_id,
            target_name=str(t_id),
            domain_or_category=None,
        )


async def _fetch_capabilities_for_developer(
    session: AsyncSession,
    developer_id: uuid.UUID,
    target_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
) -> DeveloperCapabilityListResponse:
    base_where = [DeveloperCapability.developer_id == developer_id]
    if target_type == "skill":
        base_where.append(DeveloperCapability.skill_id.is_not(None))
    elif target_type == "technology":
        base_where.append(DeveloperCapability.technology_id.is_not(None))
    elif target_type == "concept":
        base_where.append(DeveloperCapability.concept_id.is_not(None))

    if min_confidence is not None:
        base_where.append(DeveloperCapability.confidence >= min_confidence)

    count_stmt = select(func.count(DeveloperCapability.id)).where(*base_where)
    count_res = await session.execute(count_stmt)
    total = count_res.scalar_one()

    stmt = (
        select(DeveloperCapability)
        .options(
            joinedload(DeveloperCapability.skill),
            joinedload(DeveloperCapability.technology),
            joinedload(DeveloperCapability.concept),
        )
        .where(*base_where)
        .order_by(DeveloperCapability.score.desc(), DeveloperCapability.id.asc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    caps = res.scalars().all()

    items = [
        DeveloperCapabilityResponse(
            id=cap.id,
            developer_id=cap.developer_id,
            target=_format_target(
                cap.skill, cap.technology, cap.concept,
                cap.skill_id, cap.technology_id, cap.concept_id
            ),
            score=float(cap.score),
            confidence=float(cap.confidence),
            scoring_version=cap.scoring_version,
            updated_at=cap.updated_at,
        )
        for cap in caps
    ]
    return DeveloperCapabilityListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/me", response_model=DeveloperResponse)
async def create_developer_me(
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    Creates or returns the Developer record for the currently authenticated user.

    Identity mapping:
      The verified JWT `sub` is converted to a UUID and mapped to `auth_user_id`.

    Idempotency:
      If the record already exists, returns 200 OK and the existing record.
      If it does not exist, attempts to create it, returning 201 Created.
      A unique constraint race condition is handled securely.
    """
    try:
        auth_user_uuid = uuid.UUID(current_user.sub)
    except ValueError:
        logger.warning("Verified JWT sub is not a valid UUID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )

    # 1. Query existing record
    result = await session.execute(
        select(Developer).where(Developer.auth_user_id == auth_user_uuid)
    )
    existing_developer = result.scalar_one_or_none()

    if existing_developer:
        response.status_code = status.HTTP_200_OK
        return existing_developer

    # 2. Not found, attempt creation
    new_developer = Developer(auth_user_id=auth_user_uuid)
    session.add(new_developer)

    try:
        await session.commit()
        await session.refresh(new_developer)
        response.status_code = status.HTTP_201_CREATED
        return new_developer
    except IntegrityError:
        # 3. Race condition: Another request created the record concurrently.
        await session.rollback()
        
        # Re-query the now-existing record
        result = await session.execute(
            select(Developer).where(Developer.auth_user_id == auth_user_uuid)
        )
        existing_developer = result.scalar_one_or_none()
        
        if not existing_developer:
            logger.error("Failed to re-query developer after IntegrityError (auth_user_id=%s)", auth_user_uuid)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while provisioning developer identity."
            )

        response.status_code = status.HTTP_200_OK
        return existing_developer


@router.get("/me", response_model=DeveloperResponse)
async def get_developer_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Developer:
    """
    Retrieve developer profile for the authenticated user.
    Returns 404 if the profile does not exist yet.
    """
    try:
        auth_user_uuid = uuid.UUID(current_user.sub)
    except ValueError:
        logger.warning("Verified JWT sub is not a valid UUID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )

    result = await session.execute(
        select(Developer).where(Developer.auth_user_id == auth_user_uuid)
    )
    developer = result.scalar_one_or_none()

    if not developer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer profile not found. Please initialize via POST /developers/me.",
        )

    return developer


@router.get("/me/capabilities", response_model=DeveloperCapabilityListResponse)
async def get_current_developer_capabilities(
    target_type: Optional[str] = Query(None, pattern="^(skill|technology|concept)$", description="Filter by target type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> DeveloperCapabilityListResponse:
    """
    Retrieve capability scores and confidence intervals for the authenticated developer.
    """
    return await _fetch_capabilities_for_developer(
        session=session,
        developer_id=developer.id,
        target_type=target_type,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )


@router.get("/{developer_id}/capabilities", response_model=DeveloperCapabilityListResponse)
async def get_developer_capabilities_by_id(
    developer_id: uuid.UUID,
    target_type: Optional[str] = Query(None, pattern="^(skill|technology|concept)$", description="Filter by target type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> DeveloperCapabilityListResponse:
    """
    Retrieve capability scores for a developer by ID.
    Enforces authorization: callers cannot query other developers' capabilities.
    """
    if developer.id != developer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer not found.",
        )

    return await _fetch_capabilities_for_developer(
        session=session,
        developer_id=developer.id,
        target_type=target_type,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )


@router.get("/me/capabilities/history", response_model=CapabilityHistoryListResponse)
async def get_developer_capability_history(
    target_id: Optional[uuid.UUID] = Query(None, description="Filter history by target taxonomy UUID"),
    target_type: Optional[str] = Query(None, pattern="^(skill|technology|concept)$", description="Filter by target type"),
    capability_id: Optional[uuid.UUID] = Query(None, description="Filter by developer_capabilities ID"),
    analysis_run_id: Optional[uuid.UUID] = Query(None, description="Filter by analysis_runs ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> CapabilityHistoryListResponse:
    """
    Retrieve append-only history of capability states for trend tracking.
    """
    base_where = [DeveloperCapability.developer_id == developer.id]

    if capability_id is not None:
        base_where.append(CapabilityHistory.capability_id == capability_id)

    if analysis_run_id is not None:
        base_where.append(CapabilityHistory.analysis_run_id == analysis_run_id)

    if target_type == "skill":
        base_where.append(DeveloperCapability.skill_id.is_not(None))
    elif target_type == "technology":
        base_where.append(DeveloperCapability.technology_id.is_not(None))
    elif target_type == "concept":
        base_where.append(DeveloperCapability.concept_id.is_not(None))

    if target_id is not None:
        base_where.append(
            or_(
                DeveloperCapability.skill_id == target_id,
                DeveloperCapability.technology_id == target_id,
                DeveloperCapability.concept_id == target_id,
            )
        )

    count_stmt = (
        select(func.count(CapabilityHistory.id))
        .join(DeveloperCapability, CapabilityHistory.capability_id == DeveloperCapability.id)
        .where(*base_where)
    )
    count_res = await session.execute(count_stmt)
    total = count_res.scalar_one()

    stmt = (
        select(CapabilityHistory)
        .join(DeveloperCapability, CapabilityHistory.capability_id == DeveloperCapability.id)
        .options(
            joinedload(CapabilityHistory.capability).joinedload(DeveloperCapability.skill),
            joinedload(CapabilityHistory.capability).joinedload(DeveloperCapability.technology),
            joinedload(CapabilityHistory.capability).joinedload(DeveloperCapability.concept),
        )
        .where(*base_where)
        .order_by(CapabilityHistory.recorded_at.desc(), CapabilityHistory.id.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()

    items = []
    for row in rows:
        cap = row.capability
        target = _format_target(
            cap.skill, cap.technology, cap.concept,
            cap.skill_id, cap.technology_id, cap.concept_id
        ) if cap else CapabilityTargetResponse(
            target_type="unknown",
            target_id=uuid.uuid4(),
            target_name="Unknown",
            domain_or_category=None,
        )
        items.append(
            CapabilityHistoryItemResponse(
                id=row.id,
                capability_id=row.capability_id,
                analysis_run_id=row.analysis_run_id,
                target=target,
                score=float(row.score),
                confidence=float(row.confidence),
                scoring_version=row.scoring_version,
                recorded_at=row.recorded_at,
            )
        )

    return CapabilityHistoryListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/me/evidence", response_model=EvidenceListResponse)
async def get_developer_evidence(
    repository_id: Optional[uuid.UUID] = Query(None, description="Filter evidence by repository ID"),
    analysis_run_id: Optional[uuid.UUID] = Query(None, description="Filter evidence by analysis run ID"),
    evidence_type: Optional[str] = Query(None, pattern="^(MENTION|USAGE|APPLIED_ENGINEERING|DEMONSTRATED_OUTCOME)$"),
    polarity: Optional[str] = Query(None, pattern="^(positive|negative)$"),
    target_id: Optional[uuid.UUID] = Query(None, description="Filter evidence supporting a specific skill, technology, or concept"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceListResponse:
    """
    Retrieve contextualized evidence records with source provenance for the authenticated developer.
    """
    base_where = [
        Project.developer_id == developer.id,
    ]

    if repository_id is not None:
        base_where.append(Repository.id == repository_id)

    if analysis_run_id is not None:
        base_where.append(AnalysisRun.id == analysis_run_id)

    if evidence_type is not None:
        base_where.append(Evidence.type == evidence_type)

    if polarity == "positive":
        base_where.append(Evidence.polarity > 0)
    elif polarity == "negative":
        base_where.append(Evidence.polarity < 0)

    if target_id is not None:
        target_subquery = (
            select(Evidence.id)
            .outerjoin(EvidenceSkill, Evidence.id == EvidenceSkill.evidence_id)
            .outerjoin(EvidenceTechnology, Evidence.id == EvidenceTechnology.evidence_id)
            .outerjoin(EvidenceConcept, Evidence.id == EvidenceConcept.evidence_id)
            .where(
                or_(
                    EvidenceSkill.skill_id == target_id,
                    EvidenceTechnology.technology_id == target_id,
                    EvidenceConcept.concept_id == target_id,
                )
            )
        )
        base_where.append(Evidence.id.in_(target_subquery))

    count_stmt = (
        select(func.count(func.distinct(Evidence.id)))
        .join(Observation, Evidence.observation_id == Observation.id)
        .join(AnalysisRun, Observation.analysis_run_id == AnalysisRun.id)
        .join(Repository, AnalysisRun.repository_id == Repository.id)
        .join(Project, Repository.project_id == Project.id)
        .where(*base_where)
    )
    count_res = await session.execute(count_stmt)
    total = count_res.scalar_one()

    stmt = (
        select(Evidence)
        .join(Observation, Evidence.observation_id == Observation.id)
        .join(AnalysisRun, Observation.analysis_run_id == AnalysisRun.id)
        .join(Repository, AnalysisRun.repository_id == Repository.id)
        .join(Project, Repository.project_id == Project.id)
        .options(
            selectinload(Evidence.skills),
            selectinload(Evidence.technologies),
            selectinload(Evidence.concepts),
            joinedload(Evidence.observation),
        )
        .where(*base_where)
        .order_by(Evidence.recency.desc(), Evidence.id.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    rows = res.scalars().unique().all()

    items = []
    for ev in rows:
        provenance = None
        if ev.observation:
            src_ref = ev.observation.source_reference or {}
            provenance = EvidenceSourceProvenance(
                observation_id=ev.observation.id,
                source_tool=ev.observation.source_tool,
                observation_type=ev.observation.type,
                file_path=src_ref.get("file_path") or src_ref.get("file"),
                line_start=src_ref.get("line_start") or src_ref.get("line"),
                line_end=src_ref.get("line_end"),
                rule_id=src_ref.get("rule_id"),
            )

        items.append(
            EvidenceResponse(
                id=ev.id,
                type=ev.type,
                strength=float(ev.strength),
                directness=float(ev.directness),
                reliability=float(ev.reliability),
                polarity=float(ev.polarity),
                recency=ev.recency,
                created_at=ev.created_at,
                skills=[
                    EvidenceTaxonomyRef(id=s.id, name=s.name, type="skill")
                    for s in ev.skills
                ],
                technologies=[
                    EvidenceTaxonomyRef(id=t.id, name=t.name, type="technology")
                    for t in ev.technologies
                ],
                concepts=[
                    EvidenceTaxonomyRef(id=c.id, name=c.name, type="concept")
                    for c in ev.concepts
                ],
                provenance=provenance,
            )
        )

    return EvidenceListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
