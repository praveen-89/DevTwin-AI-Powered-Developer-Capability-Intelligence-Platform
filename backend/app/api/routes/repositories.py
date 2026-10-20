"""
DevTwin Backend — Repositories Routes
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.analysis_run import AnalysisRun
from app.models.developer import Developer
from app.models.evidence import Evidence
from app.models.github_account import GitHubAccount
from app.models.observation import Observation
from app.models.project import Project
from app.models.repository import Repository
from app.models.repository_dependency import RepositoryDependency
from app.models.repository_language import RepositoryLanguage
from app.models.risk_finding import RiskFinding
from app.models.taxonomy import (
    Concept,
    Skill,
    SkillConcept,
    SkillRelationship,
    SkillTechnology,
    Technology,
    TechnologyConcept,
)
from app.schemas.coderisk import RiskFindingListResponse, RiskFindingResponse
from app.schemas.skillgraph import (
    SkillGraphDependencyResponse,
    SkillGraphEdgeResponse,
    SkillGraphLanguageResponse,
    SkillGraphNodeResponse,
    SkillGraphResponse,
)
from app.services.github.client import GitHubClient
from app.services.github.auth import generate_app_jwt
from app.services.github.exceptions import GitHubHTTPError, GitHubResponseError, GitHubIntegrationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["repositories"])

class RepositoryCreateRequest(BaseModel):
    project_id: uuid.UUID
    github_repo_id: int

class RepositoryResponse(BaseModel):
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    github_repo_id: Optional[int]
    owner_login: str
    name: str
    full_name: str
    url: str
    default_branch: str
    visibility: str
    synced_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    request: RepositoryCreateRequest,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Register a GitHub repository to a project.
    """
    # 1. Verify project ownership
    query = select(Project).where(
        Project.id == request.project_id,
        Project.developer_id == developer.id
    )
    project_result = await session.execute(query)
    project = project_result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {request.project_id} not found or not owned by developer {developer.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by developer."
        )

    # 2. Query GitHubAccount
    gh_query = select(GitHubAccount).where(GitHubAccount.developer_id == developer.id)
    gh_result = await session.execute(gh_query)
    github_account = gh_result.scalar_one_or_none()

    if not github_account:
        logger.warning(f"Developer {developer.id} has no GitHubAccount.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GitHub account linked."
        )

    if github_account.disconnected_at is not None:
        logger.warning(f"Developer {developer.id} GitHubAccount is disconnected.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account is disconnected."
        )

    if github_account.installation_id is None:
        logger.warning(f"Developer {developer.id} has no personal installation.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No personal GitHub App installation found."
        )

    # 3. GitHub API interaction
    client = GitHubClient()
    
    try:
        app_jwt = generate_app_jwt()
        # Ephemeral token
        installation_token = await client.create_installation_access_token(
            github_account.installation_id, app_jwt
        )
    except GitHubIntegrationError as e:
        logger.error(f"Failed to generate installation token: {e.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to authenticate with GitHub."
        )

    try:
        repo_data = await client.get_installation_repository(request.github_repo_id, installation_token)
    except GitHubHTTPError as e:
        logger.warning(f"Failed to fetch repository from GitHub: HTTP {e.status_code}")
        if e.status_code in (403, 404):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Repository not found or inaccessible by your personal installation."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify repository with GitHub."
        )
    except GitHubIntegrationError as e:
        logger.error(f"GitHub integration error fetching repo: {e.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify repository with GitHub."
        )
    
    # 4. Construct Repository Model
    owner_login = repo_data.get("owner", {}).get("login")
    name = repo_data.get("name")
    full_name = repo_data.get("full_name")
    html_url = repo_data.get("html_url")
    default_branch = repo_data.get("default_branch")
    visibility = repo_data.get("visibility")
    
    if (
        not all([owner_login, name, full_name, html_url, default_branch, visibility])
        or not isinstance(default_branch, str)
        or not default_branch.strip()
    ):
        logger.error("GitHub repository response missing required metadata fields.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid repository metadata received from GitHub."
        )

    new_repo = Repository(
        project_id=project.id,
        github_repo_id=request.github_repo_id,
        owner_login=owner_login,
        name=name,
        full_name=full_name,
        url=html_url,
        default_branch=default_branch,
        visibility=visibility
    )

    session.add(new_repo)

    try:
        await session.commit()
        await session.refresh(new_repo)
    except IntegrityError as e:
        await session.rollback()
        orig = getattr(e, "orig", None)
        sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
        
        if sqlstate == "23505" or "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            logger.warning(f"Duplicate repository registration attempt for github_repo_id {request.github_repo_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Repository already registered."
            )
            
        logger.error(f"IntegrityError saving repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save repository."
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to save repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save repository."
        )

    return new_repo


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    project_id: Optional[uuid.UUID] = Query(default=None),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
) -> List[Repository]:
    """
    List all repositories belonging to projects owned by the authenticated developer,
    optionally filtered by project_id.
    """
    if project_id is not None:
        proj_query = select(Project).where(
            Project.id == project_id,
            Project.developer_id == developer.id
        )
        project_result = await session.execute(proj_query)
        project = project_result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or not owned by developer."
            )

    query = (
        select(Repository)
        .join(Project, Repository.project_id == Project.id)
        .where(Project.developer_id == developer.id)
    )

    if project_id is not None:
        query = query.where(Repository.project_id == project_id)

    query = query.order_by(Repository.created_at.asc())

    try:
        result = await session.execute(query)
        repositories = result.scalars().all()
        return list(repositories)
    except Exception as e:
        logger.error(f"Failed to list repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch repositories."
        )


@router.get("/{id}", response_model=RepositoryResponse)
async def get_repository(
    id: uuid.UUID,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
) -> Repository:
    """
    Retrieve details for a single repository owned by the authenticated developer.
    """
    query = (
        select(Repository)
        .join(Project, Repository.project_id == Project.id)
        .where(
            Repository.id == id,
            Project.developer_id == developer.id
        )
    )

    try:
        result = await session.execute(query)
        repository = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to fetch repository {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch repository."
        )

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    return repository


async def _verify_repository_ownership(
    session: AsyncSession,
    repository_id: uuid.UUID,
    developer_id: uuid.UUID,
) -> Repository:
    """Verifies that the repository belongs to an owned project of the developer."""
    query = (
        select(Repository)
        .join(Project, Repository.project_id == Project.id)
        .where(
            Repository.id == repository_id,
            Project.developer_id == developer_id,
        )
    )
    result = await session.execute(query)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or not owned by developer.",
        )
    return repo


@router.get("/{id}/risks", response_model=RiskFindingListResponse)
async def get_repository_risks(
    id: uuid.UUID,
    run_id: Optional[uuid.UUID] = Query(None, description="Specific analysis run ID; defaults to latest completed run"),
    severity: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$", description="Filter by risk severity"),
    category: Optional[str] = Query(None, description="Filter by category (SECURITY, RELIABILITY, etc.)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> RiskFindingListResponse:
    """
    Retrieve static CodeRisk findings for a repository.
    Defaults to the latest completed analysis run unless a specific run_id is requested.
    """
    await _verify_repository_ownership(session, id, developer.id)

    target_run_id = run_id
    if target_run_id is None:
        latest_run_stmt = (
            select(AnalysisRun.id)
            .where(AnalysisRun.repository_id == id, AnalysisRun.status == "COMPLETED")
            .order_by(AnalysisRun.completed_at.desc(), AnalysisRun.created_at.desc())
            .limit(1)
        )
        run_res = await session.execute(latest_run_stmt)
        target_run_id = run_res.scalar_one_or_none()

    if target_run_id is None:
        return RiskFindingListResponse(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
            analysis_run_id=None,
        )

    base_where = [
        RiskFinding.repository_id == id,
        RiskFinding.analysis_run_id == target_run_id,
    ]
    if severity is not None:
        base_where.append(RiskFinding.severity == severity)
    if category is not None:
        base_where.append(RiskFinding.category == category)

    count_stmt = select(func.count(RiskFinding.id)).where(*base_where)
    count_res = await session.execute(count_stmt)
    total = count_res.scalar_one()

    stmt = (
        select(RiskFinding)
        .where(*base_where)
        .order_by(RiskFinding.detected_at.desc(), RiskFinding.id.asc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    findings = res.scalars().all()

    items = [
        RiskFindingResponse(
            id=f.id,
            repository_id=f.repository_id,
            analysis_run_id=f.analysis_run_id,
            category=f.category,
            severity=f.severity,
            confidence=float(f.confidence),
            risk_type=f.risk_type,
            file_path=f.file_path,
            line_start=f.line_start,
            line_end=f.line_end,
            detected_at=f.detected_at,
        )
        for f in findings
    ]

    return RiskFindingListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        analysis_run_id=target_run_id,
    )


@router.get("/{id}/skillgraph", response_model=SkillGraphResponse)
async def get_repository_skillgraph(
    id: uuid.UUID,
    run_id: Optional[uuid.UUID] = Query(None, description="Specific analysis run ID; defaults to latest completed run"),
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> SkillGraphResponse:
    """
    Retrieve repository SkillGraph view including languages, dependencies, taxonomy nodes, and relationships.
    """
    await _verify_repository_ownership(session, id, developer.id)

    target_run_id = run_id
    if target_run_id is None:
        latest_run_stmt = (
            select(AnalysisRun.id)
            .where(AnalysisRun.repository_id == id, AnalysisRun.status == "COMPLETED")
            .order_by(AnalysisRun.completed_at.desc(), AnalysisRun.created_at.desc())
            .limit(1)
        )
        run_res = await session.execute(latest_run_stmt)
        target_run_id = run_res.scalar_one_or_none()

    # 1. Repository languages
    lang_stmt = (
        select(RepositoryLanguage)
        .where(RepositoryLanguage.repository_id == id)
        .order_by(RepositoryLanguage.bytes.desc())
    )
    lang_res = await session.execute(lang_stmt)
    languages = [
        SkillGraphLanguageResponse(language=l.language, bytes=l.bytes)
        for l in lang_res.scalars().all()
    ]

    # 2. Repository dependencies
    dep_stmt = (
        select(RepositoryDependency)
        .where(RepositoryDependency.repository_id == id)
        .order_by(RepositoryDependency.ecosystem.asc(), RepositoryDependency.package_name.asc())
    )
    dep_res = await session.execute(dep_stmt)
    dependencies = [
        SkillGraphDependencyResponse(
            ecosystem=d.ecosystem,
            package_name=d.package_name,
            version_constraint=d.version_constraint,
        )
        for d in dep_res.scalars().all()
    ]

    nodes: List[SkillGraphNodeResponse] = []
    edges: List[SkillGraphEdgeResponse] = []

    if target_run_id is not None:
        obs_subquery = (
            select(Observation.id)
            .where(Observation.analysis_run_id == target_run_id)
        )
        ev_stmt = (
            select(Evidence)
            .options(
                selectinload(Evidence.skills),
                selectinload(Evidence.technologies),
                selectinload(Evidence.concepts),
            )
            .where(Evidence.observation_id.in_(obs_subquery))
        )
        ev_res = await session.execute(ev_stmt)
        ev_rows = ev_res.scalars().unique().all()

        seen_skills = {}
        seen_techs = {}
        seen_concepts = {}

        for ev in ev_rows:
            for s in ev.skills:
                seen_skills[s.id] = s
            for t in ev.technologies:
                seen_techs[t.id] = t
            for c in ev.concepts:
                seen_concepts[c.id] = c

        for s in seen_skills.values():
            nodes.append(SkillGraphNodeResponse(id=s.id, name=s.name, type="skill", domain_or_category=s.domain))
        for t in seen_techs.values():
            nodes.append(SkillGraphNodeResponse(id=t.id, name=t.name, type="technology", domain_or_category=t.type))
        for c in seen_concepts.values():
            nodes.append(SkillGraphNodeResponse(id=c.id, name=c.name, type="concept", domain_or_category=None))

        if seen_skills and seen_techs:
            st_stmt = select(SkillTechnology).where(
                SkillTechnology.skill_id.in_(list(seen_skills.keys())),
                SkillTechnology.technology_id.in_(list(seen_techs.keys())),
            )
            st_res = await session.execute(st_stmt)
            for st in st_res.scalars().all():
                s = seen_skills.get(st.skill_id)
                t = seen_techs.get(st.technology_id)
                if s and t:
                    edges.append(
                        SkillGraphEdgeResponse(
                            source_id=s.id,
                            target_id=t.id,
                            source_name=s.name,
                            target_name=t.name,
                            relation_type="USES",
                        )
                    )

        if seen_skills and seen_concepts:
            sc_stmt = select(SkillConcept).where(
                SkillConcept.skill_id.in_(list(seen_skills.keys())),
                SkillConcept.concept_id.in_(list(seen_concepts.keys())),
            )
            sc_res = await session.execute(sc_stmt)
            for sc in sc_res.scalars().all():
                s = seen_skills.get(sc.skill_id)
                c = seen_concepts.get(sc.concept_id)
                if s and c:
                    edges.append(
                        SkillGraphEdgeResponse(
                            source_id=s.id,
                            target_id=c.id,
                            source_name=s.name,
                            target_name=c.name,
                            relation_type="APPLIES",
                        )
                    )

        if seen_techs and seen_concepts:
            tc_stmt = select(TechnologyConcept).where(
                TechnologyConcept.technology_id.in_(list(seen_techs.keys())),
                TechnologyConcept.concept_id.in_(list(seen_concepts.keys())),
            )
            tc_res = await session.execute(tc_stmt)
            for tc in tc_res.scalars().all():
                t = seen_techs.get(tc.technology_id)
                c = seen_concepts.get(tc.concept_id)
                if t and c:
                    edges.append(
                        SkillGraphEdgeResponse(
                            source_id=t.id,
                            target_id=c.id,
                            source_name=t.name,
                            target_name=c.name,
                            relation_type="APPLIES",
                        )
                    )

        if len(seen_skills) >= 2:
            sr_stmt = select(SkillRelationship).where(
                SkillRelationship.source_id.in_(list(seen_skills.keys())),
                SkillRelationship.target_id.in_(list(seen_skills.keys())),
            )
            sr_res = await session.execute(sr_stmt)
            for sr in sr_res.scalars().all():
                s = seen_skills.get(sr.source_id)
                t = seen_skills.get(sr.target_id)
                if s and t:
                    edges.append(
                        SkillGraphEdgeResponse(
                            source_id=s.id,
                            target_id=t.id,
                            source_name=s.name,
                            target_name=t.name,
                            relation_type=sr.relation_type,
                        )
                    )

    nodes.sort(key=lambda n: (n.type, n.name))
    edges.sort(key=lambda e: (e.source_name, e.target_name, e.relation_type))

    return SkillGraphResponse(
        repository_id=id,
        analysis_run_id=target_run_id,
        languages=languages,
        dependencies=dependencies,
        nodes=nodes,
        edges=edges,
    )
