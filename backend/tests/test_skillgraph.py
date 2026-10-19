"""
DevTwin Backend Tests — SkillGraph Entity & Relationship Mapping (Step 6D)
Tests taxonomy normalization, entity/relationship mapping, observation provenance,
deduplication, empty repositories, error handling, and worker pipeline integration.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mining.models import (
    ASTClassSummary,
    ASTFileSummary,
    ASTFunctionSummary,
    ASTImportSummary,
    LanguageBreakdown,
    ManifestDependency,
    ManifestSummary,
    MiningResult,
    MiningWarning,
    RepositoryInventory,
)
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.skillgraph.mapper import map_mining_result_to_graph
from app.skillgraph.models import SkillGraphMapping, SkillGraphResult
from app.skillgraph.service import persist_skillgraph
from app.skillgraph.taxonomy import (
    CANONICAL_DEPENDENCIES,
    CANONICAL_LANGUAGES,
    CANONICAL_SKILL_RELATIONSHIPS,
    normalize_name,
    resolve_dependency_taxonomy,
    resolve_language_taxonomy,
)
from app.workers.fetcher import FetchResult
from app.workers.runner import execute_job_run


def create_sample_mining_result(
    languages=None,
    manifests=None,
    ast_summaries=None,
    warnings=None,
) -> MiningResult:
    """Helper to assemble a hermetic MiningResult for unit tests."""
    inv = RepositoryInventory(
        total_files=10,
        source_files=8,
        binary_files=2,
        excluded_files=5,
        total_bytes=50000,
        source_bytes=45000,
    )
    return MiningResult(
        schema_version="1.0.0",
        mining_version="1.0.0",
        inventory=inv,
        languages=languages or [],
        manifests=manifests or [],
        ast_summaries=ast_summaries or [],
        warnings=warnings or [],
        completed_at=datetime.now(timezone.utc).isoformat(),
    )


# ===========================================================================
# 1. Deterministic Taxonomy Normalization Tests
# ===========================================================================


def test_normalize_name():
    """normalize_name lowercases and trims tokens."""
    assert normalize_name("  FastAPI  ") == "fastapi"
    assert normalize_name("PYTHON") == "python"
    assert normalize_name("React") == "react"


def test_canonical_taxonomy_seeds_valid():
    """Verify pre-seeded taxonomy items adhere to required constraints."""
    for key, item in CANONICAL_LANGUAGES.items():
        assert item.technology_type in ("language", "tool")
        assert len(item.technology_name) > 0
        for skill_name, domain in item.skills:
            assert len(skill_name) > 0
            assert len(domain) > 0

    for key, item in CANONICAL_DEPENDENCIES.items():
        assert item.technology_type in ("framework", "library", "tool", "runtime")
        assert len(item.technology_name) > 0

    for src, tgt, rel in CANONICAL_SKILL_RELATIONSHIPS:
        assert rel in ("REQUIRES", "RELATED_TO", "PART_OF")


# ===========================================================================
# 2. Language and Technology Mapping Tests
# ===========================================================================


def test_map_canonical_languages():
    """Canonical languages generate repository language, observation, tech, skills, and concepts."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        languages=[
            LanguageBreakdown(language="Python", files_count=5, bytes_count=30000, percentage=60.0),
            LanguageBreakdown(language="TypeScript", files_count=3, bytes_count=20000, percentage=40.0),
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)

    # Repository languages
    assert len(mapping.languages) == 2
    assert mapping.languages[0].language == "Python"
    assert mapping.languages[0].bytes == 30000
    assert mapping.languages[1].language == "TypeScript"
    assert mapping.languages[1].bytes == 20000

    # Factual observations
    lang_obs = [o for o in mapping.observations if o.type == "LANGUAGE_DETECTED"]
    assert len(lang_obs) == 2
    assert lang_obs[0].source_tool == "mining-classifier"
    assert lang_obs[0].source_reference["language"] == "Python"
    assert lang_obs[0].confidence == 1.0

    # Technologies resolved
    tech_names = {t.name for t in mapping.technologies}
    assert "Python" in tech_names
    assert "TypeScript" in tech_names

    # Skills resolved
    skill_names = {s.name for s in mapping.skills}
    assert "Backend Development" in skill_names
    assert "Frontend Development" in skill_names

    # Edges: skill -> technology
    assert ("Backend Development", "Python") in mapping.skill_technologies
    assert ("Frontend Development", "TypeScript") in mapping.skill_technologies

    # Edges: technology -> concept
    tech_concepts_map = {tc[0]: tc[1] for tc in mapping.technology_concepts}
    assert ("Python", "Object-Oriented Programming") in mapping.technology_concepts
    assert ("TypeScript", "Static Typing") in mapping.technology_concepts


def test_map_unrecognized_language():
    """Unrecognized language maps safely to a Technology without hallucinating skills."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        languages=[
            LanguageBreakdown(language="Elixir", files_count=2, bytes_count=1500, percentage=100.0)
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)

    assert len(mapping.languages) == 1
    assert mapping.languages[0].language == "Elixir"
    assert len(mapping.technologies) == 1
    assert mapping.technologies[0].name == "Elixir"
    assert mapping.technologies[0].type == "language"
    assert len(mapping.skills) == 0  # No hallucinated skills
    assert len(mapping.concepts) == 0  # No hallucinated concepts


# ===========================================================================
# 3. Dependency Mapping Tests
# ===========================================================================


def test_map_known_dependencies():
    """Known dependencies map to canonical technologies, concepts, and skills."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        manifests=[
            ManifestSummary(
                file_path="requirements.txt",
                manifest_type="pip",
                project_name=None,
                project_version=None,
                dependencies_count=2,
                dependencies=[
                    ManifestDependency(name="fastapi", version_spec=">=0.100.0", dependency_type="runtime"),
                    ManifestDependency(name="pytest", version_spec="^8.0.0", dependency_type="dev"),
                ],
            )
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)

    # Repository dependencies
    assert len(mapping.dependencies) == 2
    assert mapping.dependencies[0].package_name == "fastapi"
    assert mapping.dependencies[0].ecosystem == "pip"
    assert mapping.dependencies[0].version_constraint == ">=0.100.0"

    # Observations
    dep_obs = [o for o in mapping.observations if o.type == "DEPENDENCY_FOUND"]
    assert len(dep_obs) == 2
    assert dep_obs[0].source_reference["package"] == "fastapi"
    assert dep_obs[0].source_reference["manifest"] == "requirements.txt"

    # Resolved Technologies
    tech_names = {t.name for t in mapping.technologies}
    assert "FastAPI" in tech_names
    assert "pytest" in tech_names

    # Resolved Concepts
    concept_names = {c.name for c in mapping.concepts}
    assert "REST API" in concept_names
    assert "Automated Testing" in concept_names

    # Relationships
    assert ("Backend Development", "FastAPI") in mapping.skill_technologies
    assert ("FastAPI", "REST API") in mapping.technology_concepts


def test_map_unknown_dependency():
    """Unknown dependency maps to Technology type='library' without ungrounded claims."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        manifests=[
            ManifestSummary(
                file_path="package.json",
                manifest_type="npm",
                project_name="my-app",
                project_version="1.0.0",
                dependencies_count=1,
                dependencies=[
                    ManifestDependency(name="some-niche-parser", version_spec="1.2.3", dependency_type="runtime")
                ],
            )
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)

    assert len(mapping.dependencies) == 1
    assert mapping.dependencies[0].package_name == "some-niche-parser"
    assert len(mapping.technologies) == 1
    assert mapping.technologies[0].name == "some-niche-parser"
    assert mapping.technologies[0].type == "library"
    assert len(mapping.skills) == 0
    assert len(mapping.concepts) == 0


# ===========================================================================
# 4. AST Symbol & Concept Mapping Tests
# ===========================================================================


def test_map_ast_structures():
    """Classes, async functions, docstrings, and imports are mapped to observations and concepts."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        ast_summaries=[
            ASTFileSummary(
                file_path="app/server.py",
                language="Python",
                functions_count=1,
                classes_count=1,
                imports_count=1,
                functions=[
                    ASTFunctionSummary(
                        name="handle_request",
                        line_number=20,
                        is_async=True,
                        args_count=2,
                        has_docstring=True,
                    )
                ],
                classes=[
                    ASTClassSummary(
                        name="ServerApp",
                        line_number=10,
                        base_classes=["BaseServer"],
                        methods_count=3,
                        has_docstring=True,
                    )
                ],
                imports=[
                    ASTImportSummary(
                        module="asyncio",
                        names=["gather"],
                        is_from=True,
                        line_number=1,
                    )
                ],
            )
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)

    obs_types = {o.type for o in mapping.observations}
    assert "CLASS_DEFINED" in obs_types
    assert "FUNCTION_DEFINED" in obs_types
    assert "MODULE_IMPORTED" in obs_types

    # Concepts derived from AST evidence
    concept_names = {c.name for c in mapping.concepts}
    assert "Object-Oriented Programming" in concept_names
    assert "Asynchronous Programming" in concept_names
    assert "Code Documentation" in concept_names


def test_map_ast_parse_errors():
    """Syntax errors in AST files are preserved as factual observations."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        ast_summaries=[
            ASTFileSummary(
                file_path="bad_file.py",
                language="Python",
                functions_count=0,
                classes_count=0,
                imports_count=0,
                parse_error="SyntaxError: invalid syntax (line 4)",
            )
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)
    error_obs = [o for o in mapping.observations if o.type == "SYNTAX_ERROR_OBSERVED"]
    assert len(error_obs) == 1
    assert "SyntaxError" in error_obs[0].source_reference["error"]


def test_map_warnings_to_observations():
    """Mining warnings become MINING_WARNING observations."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        warnings=[
            MiningWarning(
                file_path="huge.json",
                warning_code="MANIFEST_OVERSIZED",
                message="File exceeded size budget.",
            )
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)
    warn_obs = [o for o in mapping.observations if o.type == "MINING_WARNING"]
    assert len(warn_obs) == 1
    assert warn_obs[0].source_reference["warning_code"] == "MANIFEST_OVERSIZED"


# ===========================================================================
# 5. Empty Repositories and Deduplication Tests
# ===========================================================================


def test_empty_repository():
    """Empty repository yields zero mappings without error."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result()
    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)

    assert len(mapping.languages) == 0
    assert len(mapping.dependencies) == 0
    assert len(mapping.observations) == 0
    assert len(mapping.technologies) == 0
    assert len(mapping.skills) == 0
    assert len(mapping.concepts) == 0


def test_duplicate_entities_deduplicated():
    """Duplicate packages or languages across files are deduplicated."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mining_res = create_sample_mining_result(
        manifests=[
            ManifestSummary(
                file_path="req1.txt",
                manifest_type="pip",
                project_name=None,
                project_version=None,
                dependencies_count=1,
                dependencies=[ManifestDependency(name="requests", version_spec="2.0", dependency_type="runtime")],
            ),
            ManifestSummary(
                file_path="req2.txt",
                manifest_type="pip",
                project_name=None,
                project_version=None,
                dependencies_count=1,
                dependencies=[ManifestDependency(name="requests", version_spec="2.0", dependency_type="runtime")],
            ),
        ]
    )

    mapping = map_mining_result_to_graph(mining_res, repo_id, run_id)
    # Distinct dependency key (pip, requests)
    assert len(mapping.dependencies) == 1
    # Both occurrences recorded as factual observations
    assert len(mapping.observations) == 2


# ===========================================================================
# 6. Database Persistence Service Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_persist_skillgraph_mocked_session():
    """persist_skillgraph performs clean database deletes, adds, and flushes."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()

    run = AnalysisRun(
        id=run_id,
        analysis_job_id=job_id,
        repository_id=repo_id,
        status="SKILL_GRAPH",
        analyzer_version="0.1.0",
        schema_version="1.0.0",
    )

    mining_res = create_sample_mining_result(
        languages=[
            LanguageBreakdown(language="Python", files_count=2, bytes_count=1000, percentage=100.0)
        ],
        manifests=[
            ManifestSummary(
                file_path="requirements.txt",
                manifest_type="pip",
                project_name=None,
                project_version=None,
                dependencies_count=1,
                dependencies=[ManifestDependency(name="fastapi", version_spec=None, dependency_type="runtime")],
            )
        ],
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # Mock execute results for existing query checks (return empty)
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await persist_skillgraph(
        session=mock_session,
        run=run,
        repository_id=repo_id,
        mining_result=mining_res,
    )

    assert isinstance(result, SkillGraphResult)
    assert result.languages_count == 1
    assert result.dependencies_count == 1
    assert result.observations_count == 2
    assert result.technologies_count >= 2
    assert result.skills_count >= 1
    assert mock_session.add.call_count > 0
    assert mock_session.flush.await_count == 1


# ===========================================================================
# 7. Pipeline Worker Runner Integration Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_execute_job_run_transitions_to_skill_graph(tmp_path):
    """execute_job_run successfully executes mining, advances to SKILL_GRAPH, and keeps job in PROCESSING."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    job = AnalysisJob(id=job_id, repository_id=repo_id, status="PROCESSING", attempt_count=1)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("class MyService:\n    async def run(self):\n        pass\n", encoding="utf-8")

    mock_fetch_result = FetchResult(
        workspace_dir=tmp_path,
        root_dir=repo_dir,
        file_count=1,
    )

    with patch(
        "app.workers.runner.fetch_repository_for_job",
        new=AsyncMock(return_value=mock_fetch_result),
    ):
        with patch("app.workers.runner.temporary_workspace") as mock_ws:
            import contextlib

            @contextlib.asynccontextmanager
            async def dummy_ws():
                yield tmp_path

            mock_ws.side_effect = dummy_ws
            run = await execute_job_run(job, mock_session)

    # In Step 6E:
    # run.status reaches CODE_RISK, run.completed_at is None
    # job.status remains PROCESSING, job.completed_at is None
    assert run.status == "CODE_RISK"
    assert run.completed_at is None
    assert job.status == "PROCESSING"
    assert job.completed_at is None

    assert hasattr(run, "_mining_result")
    assert run._mining_result is not None
    assert hasattr(run, "_skillgraph_result")
    assert run._skillgraph_result is not None
    assert run._skillgraph_result.observations_count >= 1
    assert hasattr(run, "_coderisk_result")
    assert run._coderisk_result is not None


@pytest.mark.asyncio
async def test_execute_job_run_failure_during_skillgraph(tmp_path):
    """If persist_skillgraph raises an exception, the run and job transition cleanly to FAILED."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    job = AnalysisJob(id=job_id, repository_id=repo_id, status="PROCESSING", attempt_count=1)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("print('hello')", encoding="utf-8")

    mock_fetch_result = FetchResult(
        workspace_dir=tmp_path,
        root_dir=repo_dir,
        file_count=1,
    )

    with patch(
        "app.workers.runner.fetch_repository_for_job",
        new=AsyncMock(return_value=mock_fetch_result),
    ):
        with patch("app.workers.runner.temporary_workspace") as mock_ws:
            import contextlib

            @contextlib.asynccontextmanager
            async def dummy_ws():
                yield tmp_path

            mock_ws.side_effect = dummy_ws
            with patch(
                "app.workers.runner.persist_skillgraph",
                side_effect=RuntimeError("Database write error"),
            ):
                run = await execute_job_run(job, mock_session)

    assert run.status == "FAILED"
    assert run.completed_at is not None
    assert job.status == "FAILED"
    assert job.completed_at is not None
    assert run.error_code == "INTERNAL_ERROR"
    assert mock_session.rollback.await_count >= 1
