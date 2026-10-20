"""
DevTwin Backend Tests — Core Intelligence Read APIs (Step 6J)

Hermetic tests covering:
- GET /developers/me
- GET /developers/me/capabilities and GET /developers/{id}/capabilities
- GET /developers/me/capabilities/history
- GET /developers/me/evidence
- GET /repositories/{id}/risks
- GET /repositories/{id}/skillgraph
"""

from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import AuthenticatedUser, get_current_developer, get_current_user
from app.db.connection import get_db_session
from app.main import create_app
from app.models.analysis_run import AnalysisRun
from app.models.capability import CapabilityHistory, DeveloperCapability
from app.models.developer import Developer
from app.models.evidence import Evidence
from app.models.observation import Observation
from app.models.project import Project
from app.models.repository import Repository
from app.models.repository_dependency import RepositoryDependency
from app.models.repository_language import RepositoryLanguage
from app.models.risk_finding import RiskFinding
from app.models.taxonomy import Concept, Skill, Technology


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def mock_developer():
    now = datetime.now(timezone.utc)
    dev = Developer(
        id=uuid.uuid4(),
        auth_user_id=uuid.uuid4(),
    )
    dev.created_at = now
    dev.updated_at = now
    return dev


@pytest.fixture
def mock_user(mock_developer):
    return AuthenticatedUser(sub=str(mock_developer.auth_user_id))


# ===========================================================================
# 1. Developer Profile Tests (GET /developers/me)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_developer_me_unauthenticated(app):
    """GET /developers/me without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_developer_me_not_found(app, mock_user):
    """GET /developers/me returns 404 if profile row does not exist."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: mock_user
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me")

    assert res.status_code == 404
    assert "Developer profile not found" in res.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_developer_me_success(app, mock_developer, mock_user):
    """GET /developers/me returns Developer profile."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_developer
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: mock_user
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me")

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(mock_developer.id)
    assert data["auth_user_id"] == str(mock_developer.auth_user_id)
    app.dependency_overrides.clear()


# ===========================================================================
# 2. Developer Capabilities Tests (GET /developers/me/capabilities)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_capabilities_unauthenticated(app):
    """GET /developers/me/capabilities without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/capabilities")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_capabilities_empty(app, mock_developer):
    """GET /developers/me/capabilities returns empty items when no capabilities scored."""
    mock_session = AsyncMock()
    count_res = MagicMock()
    count_res.scalar_one.return_value = 0
    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [count_res, items_res]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/capabilities")

    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_capabilities_with_items(app, mock_developer):
    """GET /developers/me/capabilities returns formatted target metadata and score bounds."""
    skill = Skill(id=uuid.uuid4(), name="Backend Development", domain="Software Engineering")
    tech = Technology(id=uuid.uuid4(), name="FastAPI", type="framework")
    now = datetime.now(timezone.utc)

    cap1 = DeveloperCapability(
        id=uuid.uuid4(),
        developer_id=mock_developer.id,
        skill_id=skill.id,
        score=0.85,
        confidence=0.92,
        scoring_version="1.0.0",
        updated_at=now,
    )
    cap1.skill = skill
    cap1.technology = None
    cap1.concept = None

    cap2 = DeveloperCapability(
        id=uuid.uuid4(),
        developer_id=mock_developer.id,
        technology_id=tech.id,
        score=0.78,
        confidence=0.80,
        scoring_version="1.0.0",
        updated_at=now,
    )
    cap2.skill = None
    cap2.technology = tech
    cap2.concept = None

    mock_session = AsyncMock()
    count_res = MagicMock()
    count_res.scalar_one.return_value = 2
    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = [cap1, cap2]
    mock_session.execute.side_effect = [count_res, items_res]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/capabilities")

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    item0 = data["items"][0]
    assert item0["target"]["target_type"] == "skill"
    assert item0["target"]["target_name"] == "Backend Development"
    assert item0["score"] == 0.85
    assert item0["confidence"] == 0.92

    item1 = data["items"][1]
    assert item1["target"]["target_type"] == "technology"
    assert item1["target"]["target_name"] == "FastAPI"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_capabilities_by_id_owner(app, mock_developer):
    """GET /developers/{id}/capabilities succeeds when requested by owning developer."""
    mock_session = AsyncMock()
    count_res = MagicMock()
    count_res.scalar_one.return_value = 0
    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [count_res, items_res]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/developers/{mock_developer.id}/capabilities")

    assert res.status_code == 200
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_capabilities_by_id_cross_developer_isolation(app, mock_developer):
    """GET /developers/{id}/capabilities returns 404 when querying another developer's id."""
    other_dev_id = uuid.uuid4()
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/developers/{other_dev_id}/capabilities")

    assert res.status_code == 404
    assert "Developer not found" in res.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_capabilities_invalid_filter(app, mock_developer):
    """GET /developers/me/capabilities with invalid target_type returns 422."""
    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/capabilities?target_type=unsupported")
    assert res.status_code == 422
    app.dependency_overrides.clear()


# ===========================================================================
# 3. Capability History Tests (GET /developers/me/capabilities/history)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_capability_history_unauthenticated(app):
    """GET /developers/me/capabilities/history without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/capabilities/history")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_capability_history_populated(app, mock_developer):
    """GET /developers/me/capabilities/history returns historical entries with target."""
    skill = Skill(id=uuid.uuid4(), name="Distributed Systems", domain="Architecture")
    cap = DeveloperCapability(
        id=uuid.uuid4(),
        developer_id=mock_developer.id,
        skill_id=skill.id,
        score=0.8,
        confidence=0.75,
        scoring_version="1.0.0",
        updated_at=datetime.now(timezone.utc),
    )
    cap.skill = skill
    cap.technology = None
    cap.concept = None

    hist = CapabilityHistory(
        id=uuid.uuid4(),
        capability_id=cap.id,
        analysis_run_id=uuid.uuid4(),
        score=0.75,
        confidence=0.70,
        scoring_version="1.0.0",
        recorded_at=datetime.now(timezone.utc),
    )
    hist.capability = cap

    mock_session = AsyncMock()
    count_res = MagicMock()
    count_res.scalar_one.return_value = 1
    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = [hist]
    mock_session.execute.side_effect = [count_res, items_res]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/capabilities/history")

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["capability_id"] == str(cap.id)
    assert item["target"]["target_name"] == "Distributed Systems"
    assert item["score"] == 0.75
    app.dependency_overrides.clear()


# ===========================================================================
# 4. Evidence Tests (GET /developers/me/evidence)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_evidence_unauthenticated(app):
    """GET /developers/me/evidence without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/evidence")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_evidence_with_provenance_scrubs_secrets(app, mock_developer):
    """GET /developers/me/evidence returns safe file/line provenance without raw secret code."""
    now = datetime.now(timezone.utc)
    obs = Observation(
        id=uuid.uuid4(),
        analysis_run_id=uuid.uuid4(),
        type="CLASS_DEFINED",
        source_tool="ast-parser-v1",
        source_reference={
            "file_path": "src/services/auth.py",
            "line_start": 42,
            "line_end": 85,
            "secret_code": "SUPER_SECRET_TOKEN_SHOULD_NEVER_BE_RETURNED",
        },
        confidence=0.95,
        observed_at=now,
    )

    concept = Concept(id=uuid.uuid4(), name="Object-Oriented Programming")
    ev = Evidence(
        id=uuid.uuid4(),
        observation_id=obs.id,
        type="APPLIED_ENGINEERING",
        strength=0.80,
        directness=0.90,
        reliability=0.95,
        polarity=1.0,
        recency=now,
        created_at=now,
    )
    ev.observation = obs
    ev.skills = []
    ev.technologies = []
    ev.concepts = [concept]

    mock_session = AsyncMock()
    count_res = MagicMock()
    count_res.scalar_one.return_value = 1
    items_res = MagicMock()
    items_res.scalars.return_value.unique.return_value.all.return_value = [ev]
    mock_session.execute.side_effect = [count_res, items_res]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/developers/me/evidence")

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["type"] == "APPLIED_ENGINEERING"
    assert item["polarity"] == 1.0
    assert len(item["concepts"]) == 1
    assert item["concepts"][0]["name"] == "Object-Oriented Programming"

    prov = item["provenance"]
    assert prov is not None
    assert prov["file_path"] == "src/services/auth.py"
    assert prov["line_start"] == 42
    assert prov["line_end"] == 85
    # Verify raw secret was scrubbed from response schema
    assert "SUPER_SECRET_TOKEN" not in str(item)
    app.dependency_overrides.clear()


# ===========================================================================
# 5. CodeRisk Findings Tests (GET /repositories/{id}/risks)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_repository_risks_unauthenticated(app):
    """GET /repositories/{id}/risks without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/repositories/{uuid.uuid4()}/risks")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_repository_risks_unowned(app, mock_developer):
    """GET /repositories/{id}/risks returns 404 if repository does not belong to developer."""
    repo_id = uuid.uuid4()
    mock_session = AsyncMock()
    ownership_res = MagicMock()
    ownership_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = ownership_res

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/repositories/{repo_id}/risks")

    assert res.status_code == 404
    assert "Repository not found" in res.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repository_risks_latest_run(app, mock_developer):
    """GET /repositories/{id}/risks defaults to latest completed run and returns findings."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    repo = Repository(
        id=repo_id,
        project_id=uuid.uuid4(),
        owner_login="testdev",
        name="testrepo",
        full_name="testdev/testrepo",
        url="https://github.com/testdev/testrepo",
        default_branch="main",
        visibility="public",
    )

    finding = RiskFinding(
        id=uuid.uuid4(),
        repository_id=repo_id,
        analysis_run_id=run_id,
        observation_id=uuid.uuid4(),
        category="SECURITY",
        severity="HIGH",
        confidence=0.90,
        risk_type="SEC-002",
        file_path="app/exec.py",
        line_start=15,
        line_end=15,
        detected_at=now,
    )

    mock_session = AsyncMock()
    # 1. Ownership check
    res_repo = MagicMock()
    res_repo.scalar_one_or_none.return_value = repo
    # 2. Latest run query
    res_run = MagicMock()
    res_run.scalar_one_or_none.return_value = run_id
    # 3. Count query
    res_count = MagicMock()
    res_count.scalar_one.return_value = 1
    # 4. Items query
    res_items = MagicMock()
    res_items.scalars.return_value.all.return_value = [finding]

    mock_session.execute.side_effect = [res_repo, res_run, res_count, res_items]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/repositories/{repo_id}/risks")

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["analysis_run_id"] == str(run_id)
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["risk_type"] == "SEC-002"
    assert item["severity"] == "HIGH"
    assert item["file_path"] == "app/exec.py"
    app.dependency_overrides.clear()


# ===========================================================================
# 6. SkillGraph Tests (GET /repositories/{id}/skillgraph)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_repository_skillgraph_unauthenticated(app):
    """GET /repositories/{id}/skillgraph without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/repositories/{uuid.uuid4()}/skillgraph")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_repository_skillgraph_populated(app, mock_developer):
    """GET /repositories/{id}/skillgraph returns languages, dependencies, nodes, and edges."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    repo = Repository(
        id=repo_id,
        project_id=uuid.uuid4(),
        owner_login="testdev",
        name="testrepo",
        full_name="testdev/testrepo",
        url="https://github.com/testdev/testrepo",
        default_branch="main",
        visibility="public",
    )

    lang = RepositoryLanguage(id=uuid.uuid4(), repository_id=repo_id, language="Python", bytes=50000)
    dep = RepositoryDependency(id=uuid.uuid4(), repository_id=repo_id, ecosystem="pip", package_name="fastapi")

    skill = Skill(id=uuid.uuid4(), name="Web Frameworks", domain="Backend")
    tech = Technology(id=uuid.uuid4(), name="FastAPI", type="framework")

    ev = Evidence(
        id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        type="USAGE",
        strength=0.5,
        directness=1.0,
        reliability=1.0,
        polarity=1.0,
        recency=now,
        created_at=now,
    )
    ev.skills = [skill]
    ev.technologies = [tech]
    ev.concepts = []

    mock_session = AsyncMock()
    # 1. Ownership
    res_repo = MagicMock()
    res_repo.scalar_one_or_none.return_value = repo
    # 2. Latest run
    res_run = MagicMock()
    res_run.scalar_one_or_none.return_value = run_id
    # 3. Languages
    res_lang = MagicMock()
    res_lang.scalars.return_value.all.return_value = [lang]
    # 4. Dependencies
    res_dep = MagicMock()
    res_dep.scalars.return_value.all.return_value = [dep]
    # 5. Evidence for run
    res_ev = MagicMock()
    res_ev.scalars.return_value.unique.return_value.all.return_value = [ev]
    # 6. SkillTechnology query
    st_edge = MagicMock()
    st_edge.skill_id = skill.id
    st_edge.technology_id = tech.id
    res_st = MagicMock()
    res_st.scalars.return_value.all.return_value = [st_edge]

    mock_session.execute.side_effect = [res_repo, res_run, res_lang, res_dep, res_ev, res_st]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/repositories/{repo_id}/skillgraph")

    assert res.status_code == 200
    data = res.json()
    assert data["repository_id"] == str(repo_id)
    assert data["analysis_run_id"] == str(run_id)
    assert len(data["languages"]) == 1
    assert data["languages"][0]["language"] == "Python"
    assert len(data["dependencies"]) == 1
    assert data["dependencies"][0]["package_name"] == "fastapi"

    # Nodes
    assert len(data["nodes"]) == 2
    node_names = {n["name"] for n in data["nodes"]}
    assert "Web Frameworks" in node_names
    assert "FastAPI" in node_names

    # Edges
    assert len(data["edges"]) == 1
    edge = data["edges"][0]
    assert edge["source_name"] == "Web Frameworks"
    assert edge["target_name"] == "FastAPI"
    assert edge["relation_type"] == "USES"
    app.dependency_overrides.clear()
