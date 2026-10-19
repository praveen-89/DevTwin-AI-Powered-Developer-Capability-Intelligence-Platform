"""
DevTwin Backend Tests — CodeRisk Engine & Static Analysis (Step 6E)
Tests static risk rules, AST inspection, secret detection, deduplication,
resource limits, database persistence, and worker runner integration.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.coderisk.analyzer import analyze_repository_risks
from app.coderisk.models import CodeRiskFinding, CodeRiskResult
from app.coderisk.rules import RULES
from app.coderisk.service import persist_coderisk
from app.mining.models import (
    ASTFileSummary,
    LanguageBreakdown,
    ManifestDependency,
    ManifestSummary,
    MiningResult,
    RepositoryInventory,
)
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.models.risk_finding import RiskFinding
from app.workers.fetcher import FetchResult
from app.workers.runner import execute_job_run


def create_sample_mining_result(
    source_files_count=1,
    ast_summaries=None,
    manifests=None,
) -> MiningResult:
    inv = RepositoryInventory(
        total_files=source_files_count,
        source_files=source_files_count,
        binary_files=0,
        excluded_files=0,
        total_bytes=1000 * source_files_count,
        source_bytes=1000 * source_files_count,
    )
    return MiningResult(
        schema_version="1.0.0",
        mining_version="1.0.0",
        inventory=inv,
        languages=[],
        manifests=manifests or [],
        ast_summaries=ast_summaries or [],
        warnings=[],
        completed_at=datetime.now(timezone.utc).isoformat(),
    )


# ===========================================================================
# 1. Rule Positive and Negative Tests
# ===========================================================================


def test_sec_001_hardcoded_secret_detected(tmp_path):
    """SEC-001 flags hardcoded high-entropy secrets and redacts secret in evidence."""
    code = 'AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
    (tmp_path / "config.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    sec_findings = [f for f in findings if f.rule_id == "SEC-001"]
    assert len(sec_findings) == 1
    f = sec_findings[0]
    assert f.category == "SECURITY"
    assert f.severity == "HIGH"
    assert f.line_start == 1
    # Secret must never be leaked in evidence snippet
    assert f.evidence_snippet is not None
    assert "wJalrXUtnFEMI" not in f.evidence_snippet
    assert "REDACTED" in f.evidence_snippet



def test_sec_001_placeholder_ignored(tmp_path):
    """SEC-001 ignores template placeholders and environment lookups."""
    code = (
        'api_key = "your-api-key-here"\n'
        'secret_key = "insert_secret_here"\n'
        'token = "xxxxxxxxxxxxxxxx"\n'
    )
    (tmp_path / "config.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    sec_findings = [f for f in findings if f.rule_id == "SEC-001"]
    assert len(sec_findings) == 0


def test_sec_002_arbitrary_code_execution_detected(tmp_path):
    """SEC-002 flags eval, exec, and os.system constructs."""
    code = (
        "import os\n"
        "eval('2 + 2')\n"
        "exec('print(1)')\n"
        "os.system('ls -la')\n"
    )
    (tmp_path / "dangerous.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    sec2_findings = [f for f in findings if f.rule_id == "SEC-002"]
    assert len(sec2_findings) == 3
    lines = [f.line_start for f in sec2_findings]
    assert 2 in lines
    assert 3 in lines
    assert 4 in lines


def test_sec_003_insecure_deserialization_detected(tmp_path):
    """SEC-003 flags pickle.load and pickle.loads."""
    code = (
        "import pickle\n"
        "data = pickle.loads(raw_data)\n"
    )
    (tmp_path / "loader.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    sec3_findings = [f for f in findings if f.rule_id == "SEC-003"]
    assert len(sec3_findings) == 1
    assert sec3_findings[0].category == "SECURITY"
    assert sec3_findings[0].severity == "MEDIUM"
    assert sec3_findings[0].line_start == 2


def test_rel_001_bare_except_detected(tmp_path):
    """REL-001 flags bare except: clauses."""
    code = (
        "try:\n"
        "    do_something()\n"
        "except:\n"
        "    logger.error('failed')\n"
    )
    (tmp_path / "handler.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    rel1_findings = [f for f in findings if f.rule_id == "REL-001"]
    assert len(rel1_findings) == 1
    assert rel1_findings[0].category == "RELIABILITY"
    assert rel1_findings[0].severity == "MEDIUM"
    assert rel1_findings[0].line_start == 3


def test_rel_002_silent_exception_swallowing_detected(tmp_path):
    """REL-002 flags empty pass in except blocks."""
    code = (
        "try:\n"
        "    risky_operation()\n"
        "except ValueError:\n"
        "    pass\n"
    )
    (tmp_path / "swallow.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    rel2_findings = [f for f in findings if f.rule_id == "REL-002"]
    assert len(rel2_findings) == 1
    assert rel2_findings[0].category == "RELIABILITY"
    assert rel2_findings[0].line_start == 3


def test_maint_001_excessive_parameter_count(tmp_path):
    """MAINT-001 flags functions with > 7 parameters."""
    code = "def complex_function(p1, p2, p3, p4, p5, p6, p7, p8):\n    return p1\n"
    (tmp_path / "funcs.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    maint1_findings = [f for f in findings if f.rule_id == "MAINT-001"]
    assert len(maint1_findings) == 1
    assert maint1_findings[0].category == "MAINTAINABILITY"
    assert maint1_findings[0].line_start == 1


def test_maint_002_syntax_error_observed():
    """MAINT-002 flags source files that failed AST syntax parsing during mining."""
    mining_res = create_sample_mining_result(
        source_files_count=1,
        ast_summaries=[
            ASTFileSummary(
                file_path="src/broken.py",
                language="Python",
                functions_count=0,
                classes_count=0,
                imports_count=0,
                parse_error="SyntaxError: invalid syntax (line 5)",
            )
        ],
    )
    findings = analyze_repository_risks(root_dir=None, mining_result=mining_res)

    maint2_findings = [f for f in findings if f.rule_id == "MAINT-002"]
    assert len(maint2_findings) == 1
    assert maint2_findings[0].category == "MAINTAINABILITY"
    assert maint2_findings[0].file_path == "src/broken.py"


def test_test_001_missing_test_suite():
    """TEST-001 flags repositories with >= 5 source files but zero test files or frameworks."""
    mining_res = create_sample_mining_result(
        source_files_count=6,
        ast_summaries=[
            ASTFileSummary(file_path=f"src/file_{i}.py", language="Python", functions_count=1, classes_count=0, imports_count=0)
            for i in range(6)
        ],
        manifests=[
            ManifestSummary(
                file_path="requirements.txt",
                manifest_type="pip",
                project_name=None,
                project_version=None,
                dependencies_count=1,
                dependencies=[ManifestDependency(name="flask", version_spec="2.0", dependency_type="runtime")],
            )
        ],
    )
    findings = analyze_repository_risks(root_dir=None, mining_result=mining_res)

    test_findings = [f for f in findings if f.rule_id == "TEST-001"]
    assert len(test_findings) == 1
    assert test_findings[0].category == "TESTING"
    assert test_findings[0].file_path is None  # Repository-level finding


def test_test_001_not_flagged_when_tests_exist():
    """TEST-001 does not flag if a test file or testing dependency exists."""
    mining_res = create_sample_mining_result(
        source_files_count=6,
        ast_summaries=[
            ASTFileSummary(file_path="tests/test_server.py", language="Python", functions_count=1, classes_count=0, imports_count=0)
        ],
    )
    findings = analyze_repository_risks(root_dir=None, mining_result=mining_res)
    test_findings = [f for f in findings if f.rule_id == "TEST-001"]
    assert len(test_findings) == 0


# ===========================================================================
# 2. Determinism, Ordering, and Edge Cases
# ===========================================================================


def test_findings_deterministic_ordering(tmp_path):
    """Findings are deterministically ordered by (file_path, line_start, rule_id)."""
    code = (
        "eval('1')\n"
        "AWS_SECRET_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE12345'\n"
        "pickle.loads(b'x')\n"
    )
    (tmp_path / "b_file.py").write_text(code, encoding="utf-8")
    (tmp_path / "a_file.py").write_text(code, encoding="utf-8")

    mining_res = create_sample_mining_result(source_files_count=2)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)

    assert len(findings) >= 4
    # a_file must come before b_file
    a_findings = [f for f in findings if f.file_path == "a_file.py"]
    b_findings = [f for f in findings if f.file_path == "b_file.py"]
    assert len(a_findings) > 0 and len(b_findings) > 0

    idx_a = findings.index(a_findings[0])
    idx_b = findings.index(b_findings[0])
    assert idx_a < idx_b


def test_empty_repository_handling():
    """Empty repository yields zero findings without error."""
    mining_res = create_sample_mining_result(source_files_count=0)
    findings = analyze_repository_risks(root_dir=None, mining_result=mining_res)
    assert len(findings) == 0


def test_binary_files_safely_ignored(tmp_path):
    """Binary files containing null bytes are safely skipped by text-based inspections."""
    binary_content = b"\x00\x01\x02AWS_SECRET_ACCESS_KEY='secret'\x00"
    (tmp_path / "blob.bin").write_bytes(binary_content)

    mining_res = create_sample_mining_result(source_files_count=1)
    findings = analyze_repository_risks(root_dir=tmp_path, mining_result=mining_res)
    assert len(findings) == 0


# ===========================================================================
# 3. Persistence Service Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_persist_coderisk_mocked_session(tmp_path):
    """persist_coderisk deletes old findings, inserts observations and risk_findings."""
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()

    run = AnalysisRun(
        id=run_id,
        analysis_job_id=job_id,
        repository_id=repo_id,
        status="CODE_RISK",
        analyzer_version="0.1.0",
        schema_version="1.0.0",
    )

    (tmp_path / "app.py").write_text("eval('1 + 1')\n", encoding="utf-8")
    mining_res = create_sample_mining_result(source_files_count=1)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    result = await persist_coderisk(
        session=mock_session,
        run=run,
        repository_id=repo_id,
        root_dir=tmp_path,
        mining_result=mining_res,
    )

    assert isinstance(result, CodeRiskResult)
    assert result.total_findings == 1
    assert result.findings_by_severity["HIGH"] == 1
    assert result.findings_by_category["SECURITY"] == 1

    # Verified 1 observation + 1 risk_finding added
    assert mock_session.add.call_count == 2
    assert mock_session.flush.await_count == 1
    assert mock_session.execute.await_count == 1  # delete previous findings


# ===========================================================================
# 4. Pipeline Integration & Status Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_execute_job_run_transitions_to_code_risk(tmp_path):
    """execute_job_run successfully executes mining, skillgraph, and coderisk, leaving job in PROCESSING."""
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
    (repo_dir / "main.py").write_text("def hello():\n    pass\n", encoding="utf-8")

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
    assert hasattr(run, "_coderisk_result")
    assert run._coderisk_result is not None


@pytest.mark.asyncio
async def test_execute_job_run_failure_during_coderisk(tmp_path):
    """If persist_coderisk raises an exception, the run and job transition cleanly to FAILED."""
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
                "app.workers.runner.persist_coderisk",
                side_effect=RuntimeError("Static analysis failure"),
            ):
                run = await execute_job_run(job, mock_session)

    assert run.status == "FAILED"
    assert run.completed_at is not None
    assert job.status == "FAILED"
    assert job.completed_at is not None
    assert run.error_code == "INTERNAL_ERROR"
    assert mock_session.rollback.await_count >= 1
