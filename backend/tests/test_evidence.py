"""
DevTwin Backend Tests — Evidence Generation Engine (Step 6F)
Hermetic tests covering observation-to-evidence mapping, provenance tracking,
confidence/reliability weighting, risk polarity handling, taxonomy junction linking,
run-level idempotency, and worker runner integration.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.evidence.mapper import map_observation_to_evidence, map_observations_to_evidence
from app.evidence.models import EvidenceItemData, EvidenceResult
from app.evidence.service import persist_evidence
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.models.evidence import (
    Evidence,
    EvidenceConcept,
    EvidenceSkill,
    EvidenceTechnology,
)
from app.models.observation import Observation
from app.models.taxonomy import Concept, Skill, Technology
from app.workers.fetcher import FetchResult
from app.workers.runner import execute_job_run


# ===========================================================================
# 1. Deterministic Observation-to-Evidence Mapping Tests
# ===========================================================================


def test_map_dependency_found_produces_mention_evidence():
    """DEPENDENCY_FOUND is mapped to MENTION evidence (strength 0.2) and links known taxonomy."""
    obs_id = uuid.uuid4()
    obs = Observation(
        id=obs_id,
        analysis_run_id=uuid.uuid4(),
        type="DEPENDENCY_FOUND",
        source_tool="manifest-parser",
        source_reference={
            "manifest": "package.json",
            "ecosystem": "npm",
            "package": "fastapi",
            "version": "^0.110.0",
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )

    ev = map_observation_to_evidence(obs)
    assert ev is not None
    assert ev.observation_id == obs_id
    assert ev.type == "MENTION"
    assert ev.strength == 0.20
    assert ev.directness == 0.80
    assert ev.reliability == 0.90
    assert ev.polarity == 1.0
    assert "FastAPI" in ev.technologies
    assert "Backend Development" in ev.skills
    assert "REST API" in ev.concepts


def test_map_unknown_dependency_produces_safe_mention():
    """Unmapped dependencies produce MENTION evidence with a safe library technology node and no hallucinated skills."""
    obs_id = uuid.uuid4()
    obs = Observation(
        id=obs_id,
        analysis_run_id=uuid.uuid4(),
        type="DEPENDENCY_FOUND",
        source_tool="manifest-parser",
        source_reference={
            "manifest": "requirements.txt",
            "package": "unheard-of-lib",
            "version": "1.0.0",
        },
        confidence=0.8,
        observed_at=datetime.now(timezone.utc),
    )

    ev = map_observation_to_evidence(obs)
    assert ev is not None
    assert ev.type == "MENTION"
    assert ev.technologies == ["unheard-of-lib"]
    assert ev.skills == []
    assert ev.concepts == []


def test_map_module_imported_produces_usage_evidence():
    """MODULE_IMPORTED is mapped to USAGE evidence (strength 0.5) with directness 1.0."""
    obs_id = uuid.uuid4()
    obs = Observation(
        id=obs_id,
        analysis_run_id=uuid.uuid4(),
        type="MODULE_IMPORTED",
        source_tool="ast-parser",
        source_reference={
            "file": "app/main.py",
            "module": "fastapi",
            "names": ["FastAPI", "Depends"],
            "line": 1,
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )

    ev = map_observation_to_evidence(obs)
    assert ev is not None
    assert ev.observation_id == obs_id
    assert ev.type == "USAGE"
    assert ev.strength == 0.50
    assert ev.directness == 1.0
    assert ev.reliability == 0.95
    assert ev.polarity == 1.0
    assert "FastAPI" in ev.technologies


def test_map_submodule_imported_resolves_base_technology():
    """Submodule imports (e.g. pydantic.dataclasses) resolve canonical base technology."""
    obs_id = uuid.uuid4()
    obs = Observation(
        id=obs_id,
        analysis_run_id=uuid.uuid4(),
        type="MODULE_IMPORTED",
        source_tool="ast-parser",
        source_reference={
            "file": "app/schemas.py",
            "module": "pydantic.dataclasses",
            "names": ["dataclass"],
            "line": 5,
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )

    ev = map_observation_to_evidence(obs)
    assert ev is not None
    assert ev.type == "USAGE"
    assert "Pydantic" in ev.technologies
    assert "Data Validation" in ev.concepts


def test_map_language_detected_substantive_vs_incidental():
    """Substantive language detection (>=5% or >=2 files) produces USAGE; incidental produces MENTION."""
    run_id = uuid.uuid4()

    # Substantive
    obs_sub = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="LANGUAGE_DETECTED",
        source_tool="mining-classifier",
        source_reference={"language": "Python", "percentage": 85.0, "files": 12},
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    ev_sub = map_observation_to_evidence(obs_sub)
    assert ev_sub is not None
    assert ev_sub.type == "USAGE"
    assert ev_sub.strength == 0.40
    assert "Python" in ev_sub.technologies

    # Incidental (<5% and 1 file)
    obs_inc = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="LANGUAGE_DETECTED",
        source_tool="mining-classifier",
        source_reference={"language": "HTML", "percentage": 1.2, "files": 1},
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    ev_inc = map_observation_to_evidence(obs_inc)
    assert ev_inc is not None
    assert ev_inc.type == "MENTION"
    assert ev_inc.strength == 0.20
    assert "HTML" in ev_inc.technologies


def test_map_class_defined_produces_applied_engineering():
    """CLASS_DEFINED is mapped to APPLIED_ENGINEERING (strength 0.8) and Object-Oriented Programming concept."""
    obs_id = uuid.uuid4()
    obs = Observation(
        id=obs_id,
        analysis_run_id=uuid.uuid4(),
        type="CLASS_DEFINED",
        source_tool="ast-parser",
        source_reference={
            "file": "app/services.py",
            "class": "AnalysisCoordinator",
            "line": 15,
            "bases": ["BaseService"],
            "methods_count": 4,
            "has_docstring": True,
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )

    ev = map_observation_to_evidence(obs)
    assert ev is not None
    assert ev.type == "APPLIED_ENGINEERING"
    assert ev.strength == 0.80
    assert ev.directness == 0.90
    assert ev.polarity == 1.0
    assert "Object-Oriented Programming" in ev.concepts
    assert "Python" in ev.technologies


def test_map_function_defined_async_vs_docstring_vs_simple():
    """Async functions map to Asynchronous Programming; documented functions map to Code Documentation."""
    run_id = uuid.uuid4()

    # Async function
    obs_async = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="FUNCTION_DEFINED",
        source_tool="ast-parser",
        source_reference={
            "file": "app/worker.py",
            "function": "process_job",
            "line": 40,
            "is_async": True,
            "has_docstring": True,
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    ev_async = map_observation_to_evidence(obs_async)
    assert ev_async is not None
    assert ev_async.type == "APPLIED_ENGINEERING"
    assert ev_async.strength == 0.70
    assert "Asynchronous Programming" in ev_async.concepts
    assert "Code Documentation" in ev_async.concepts

    # Sync function with docstring
    obs_doc = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="FUNCTION_DEFINED",
        source_tool="ast-parser",
        source_reference={
            "file": "app/util.py",
            "function": "format_date",
            "line": 10,
            "is_async": False,
            "has_docstring": True,
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    ev_doc = map_observation_to_evidence(obs_doc)
    assert ev_doc is not None
    assert ev_doc.type == "APPLIED_ENGINEERING"
    assert ev_doc.strength == 0.60
    assert "Code Documentation" in ev_doc.concepts

    # Simple function
    obs_simple = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="FUNCTION_DEFINED",
        source_tool="ast-parser",
        source_reference={
            "file": "app/util.py",
            "function": "add",
            "line": 20,
            "is_async": False,
            "has_docstring": False,
        },
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    ev_simple = map_observation_to_evidence(obs_simple)
    assert ev_simple is not None
    assert ev_simple.type == "USAGE"
    assert ev_simple.strength == 0.40


def test_map_risk_observed_produces_negative_polarity():
    """RISK_OBSERVED findings produce negative polarity evidence with severity-weighted strength."""
    run_id = uuid.uuid4()

    # SEC-001 (Hardcoded secret -> HIGH severity)
    obs_sec = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="RISK_OBSERVED",
        source_tool="coderisk-v1",
        source_reference={
            "rule_id": "SEC-001",
            "title": "Hardcoded Secret Literal",
            "file_path": "app/config.py",
            "line_start": 12,
            "evidence_snippet": "api_key = '***REDACTED***'",
        },
        confidence=0.85,
        observed_at=datetime.now(timezone.utc),
    )
    ev_sec = map_observation_to_evidence(obs_sec)
    assert ev_sec is not None
    assert ev_sec.polarity == -0.8
    assert ev_sec.strength == 0.60
    assert ev_sec.type == "USAGE"
    assert "Secure Coding" in ev_sec.concepts

    # TEST-001 (Missing test suite -> LOW severity, TESTING category)
    obs_test = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="RISK_OBSERVED",
        source_tool="coderisk-v1",
        source_reference={
            "rule_id": "TEST-001",
            "title": "Missing Test Suite",
            "file_path": None,
        },
        confidence=0.75,
        observed_at=datetime.now(timezone.utc),
    )
    ev_test = map_observation_to_evidence(obs_test)
    assert ev_test is not None
    assert ev_test.polarity == -0.2
    assert ev_test.strength == 0.20
    assert "Automated Testing" in ev_test.concepts
    assert "Testing & Quality Assurance" in ev_test.skills

    # REL-001 (Bare except -> MEDIUM severity, RELIABILITY category)
    obs_rel = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="RISK_OBSERVED",
        source_tool="coderisk-v1",
        source_reference={
            "rule_id": "REL-001",
            "title": "Bare Except Clause",
            "file_path": "app.py",
        },
        confidence=0.95,
        observed_at=datetime.now(timezone.utc),
    )
    ev_rel = map_observation_to_evidence(obs_rel)
    assert ev_rel is not None
    assert ev_rel.polarity == -0.5
    assert ev_rel.strength == 0.40
    assert "Error Handling" in ev_rel.concepts


def test_map_diagnostic_observations_return_none():
    """Diagnostic coordinator and parser warnings do NOT generate capability evidence."""
    run_id = uuid.uuid4()
    obs_warn = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="MINING_WARNING",
        source_tool="mining-coordinator",
        source_reference={"file": "foo.bin", "warning_code": "FILE_SKIPPED"},
    )
    obs_syntax = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="SYNTAX_ERROR_OBSERVED",
        source_tool="ast-parser",
        source_reference={"file": "bad.py", "error": "SyntaxError: invalid syntax"},
    )

    assert map_observation_to_evidence(obs_warn) is None
    assert map_observation_to_evidence(obs_syntax) is None


# ===========================================================================
# 2. Persistence & Idempotency Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_persist_evidence_success():
    """persist_evidence generates Evidence and junction records, flushing to database."""
    run_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    run = AnalysisRun(
        id=run_id,
        analysis_job_id=uuid.uuid4(),
        repository_id=repo_id,
        status="CODE_RISK",
        analyzer_version="1.0.0",
        schema_version="1.0.0",
    )

    obs1 = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="DEPENDENCY_FOUND",
        source_tool="manifest-parser",
        source_reference={"package": "fastapi"},
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    obs2 = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="RISK_OBSERVED",
        source_tool="coderisk-v1",
        source_reference={"rule_id": "REL-001"},
        confidence=0.95,
        observed_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await persist_evidence(
        session=mock_session,
        run=run,
        observations=[obs1, obs2],
    )

    assert isinstance(result, EvidenceResult)
    assert result.total_evidence == 2
    assert result.evidence_by_polarity["positive"] == 1
    assert result.evidence_by_polarity["negative"] == 1
    assert mock_session.flush.await_count == 1
    # Check that delete was executed for idempotency
    assert mock_session.execute.await_count >= 1


@pytest.mark.asyncio
async def test_persist_evidence_repeated_execution_idempotency():
    """Repeated execution on the same analysis run deletes pre-existing evidence and is idempotent."""
    run_id = uuid.uuid4()
    run = AnalysisRun(
        id=run_id,
        analysis_job_id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        status="CODE_RISK",
        analyzer_version="1.0.0",
        schema_version="1.0.0",
    )

    obs = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run_id,
        type="CLASS_DEFINED",
        source_tool="ast-parser",
        source_reference={"file": "app.py", "class": "App"},
        confidence=1.0,
        observed_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    # First call
    res1 = await persist_evidence(mock_session, run, [obs])
    assert res1.total_evidence == 1

    # Second call (idempotent rerun)
    res2 = await persist_evidence(mock_session, run, [obs])
    assert res2.total_evidence == 1


@pytest.mark.asyncio
async def test_persist_evidence_failure_rollback():
    """Database flush failure propagates exception for caller transaction rollback."""
    run = AnalysisRun(
        id=uuid.uuid4(),
        analysis_job_id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        status="CODE_RISK",
        analyzer_version="1.0.0",
        schema_version="1.0.0",
    )
    obs = Observation(
        id=uuid.uuid4(),
        analysis_run_id=run.id,
        type="MODULE_IMPORTED",
        source_tool="ast-parser",
        source_reference={"module": "fastapi"},
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush.side_effect = RuntimeError("Database deadlock")

    with pytest.raises(RuntimeError, match="Database deadlock"):
        await persist_evidence(mock_session, run, [obs])


# ===========================================================================
# 3. Worker Runner Pipeline Integration Test
# ===========================================================================


@pytest.mark.asyncio
async def test_execute_job_run_executes_stage_6_evidence(tmp_path):
    """execute_job_run runs through Stage 6 Evidence Generation, leaving run in CODE_RISK and job in PROCESSING."""
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
    (repo_dir / "main.py").write_text(
        "import os\n\ndef test_fn():\n    '''Docstring'''\n    pass\n",
        encoding="utf-8",
    )

    mock_fetch_result = FetchResult(
        workspace_dir=tmp_path,
        root_dir=repo_dir,
        file_count=1,
    )

    with patch(
        "app.workers.runner.fetch_repository_for_job",
        new=AsyncMock(return_value=mock_fetch_result),
    ), patch(
        "app.workers.runner.persist_capabilities",
        new=AsyncMock(return_value=__import__('app.capability.models', fromlist=['CapabilityResult']).CapabilityResult(total_targets=0)),
    ):
        with patch("app.workers.runner.temporary_workspace") as mock_ws:
            import contextlib

            @contextlib.asynccontextmanager
            async def dummy_ws():
                yield tmp_path

            mock_ws.side_effect = dummy_ws
            run = await execute_job_run(job, mock_session)

    # Step 6G: run.status reaches CAPABILITY (Stage 7 complete), awaiting Stage 8
    assert run.status == "CAPABILITY"
    assert run.completed_at is None
    assert job.status == "PROCESSING"
    assert job.completed_at is None

    # Transient results bound
    assert hasattr(run, "_mining_result")
    assert run._mining_result is not None
    assert hasattr(run, "_skillgraph_result")
    assert run._skillgraph_result is not None
    assert hasattr(run, "_coderisk_result")
    assert run._coderisk_result is not None
    assert hasattr(run, "_evidence_result")
    assert run._evidence_result is not None
    assert isinstance(run._evidence_result, EvidenceResult)
    assert run._evidence_result.total_evidence >= 0
    assert hasattr(run, "_capability_result")
    assert run._capability_result is not None
