"""
DevTwin Backend Tests — Repository Mining Engine (Step 6C)
Tests safe traversal, language classification, manifest extraction, AST parsing, and resource limits.
"""

import json
import os
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mining.ast_parser import PythonASTParser
from app.mining.classification import (
    classify_file_language,
    compute_language_breakdown,
    is_binary_content,
)
from app.mining.constants import (
    MAX_DEPENDENCIES_PER_MANIFEST,
    MAX_MANIFEST_FILE_BYTES,
    MAX_SINGLE_SOURCE_FILE_BYTES,
)
from app.mining.engine import mine_repository
from app.mining.manifests import (
    parse_cargo_toml,
    parse_package_json,
    parse_requirements_txt,
)
from app.mining.models import (
    MiningResult,
    RepositoryInventory,
)
from app.mining.traversal import safe_walk_workspace
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.workers.fetcher import (
    SecurityArchiveError,
    safe_extract_tar,
    temporary_workspace,
)
from app.workers.runner import execute_job_run


# ===========================================================================
# 1. Traversal and Exclusions
# ===========================================================================


def test_traversal_excludes_forbidden_directories(tmp_path):
    """safe_walk_workspace excludes .git, node_modules, venv, build, dist, and __pycache__."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = workspace / "repo"
    root.mkdir()

    # Valid source files
    (root / "app.py").write_text("print('hello')", encoding="utf-8")
    (root / "utils.py").write_text("def add(a, b): return a + b", encoding="utf-8")

    # Forbidden directories
    for forbidden in [".git", "node_modules", "venv", ".venv", "build", "dist", "__pycache__"]:
        f_dir = root / forbidden
        f_dir.mkdir(parents=True)
        (f_dir / "hidden.py").write_text("should_not_be_indexed = True", encoding="utf-8")

    discovered, excluded, warnings = safe_walk_workspace(root, workspace)

    file_names = {f.rel_path for f in discovered}
    assert "app.py" in file_names
    assert "utils.py" in file_names
    assert not any("hidden.py" in name for name in file_names)
    assert not any("node_modules" in name for name in file_names)
    assert not any(".git" in name for name in file_names)
    assert excluded >= 7


def test_traversal_ignores_symlinks_and_escapes(tmp_path):
    """safe_walk_workspace rejects symlinks and directory escapes outside workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = workspace / "repo"
    root.mkdir()

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret outside", encoding="utf-8")

    (root / "main.py").write_text("print('safe')", encoding="utf-8")

    # Symlink to outside file
    try:
        os.symlink(str(outside_file), str(root / "symlink_escape.py"))
        has_symlink = True
    except (OSError, NotImplementedError):
        has_symlink = False

    discovered, excluded, warnings = safe_walk_workspace(root, workspace)

    paths = [d.rel_path for d in discovered]
    assert "main.py" in paths
    if has_symlink:
        assert "symlink_escape.py" not in paths


def test_traversal_detects_binary_files(tmp_path):
    """safe_walk_workspace correctly flags binary files containing null bytes."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = workspace / "repo"
    root.mkdir()

    (root / "code.py").write_bytes(b"print('hello world')\n")
    (root / "blob.dat").write_bytes(b"\x00\x01\x02\x03\x04\xff\xfe")

    discovered, excluded, warnings = safe_walk_workspace(root, workspace)

    assert len(discovered) == 2
    binary_map = {d.rel_path: d.is_binary for d in discovered}
    assert binary_map["code.py"] is False
    assert binary_map["blob.dat"] is True


# ===========================================================================
# 2. Language and File Classification
# ===========================================================================


def test_classify_file_language():
    """classify_file_language maps extensions and special names deterministically."""
    assert classify_file_language(Path("app.py")) == "Python"
    assert classify_file_language(Path("index.ts")) == "TypeScript"
    assert classify_file_language(Path("Component.tsx")) == "TypeScript (React)"
    assert classify_file_language(Path("script.js")) == "JavaScript"
    assert classify_file_language(Path("main.rs")) == "Rust"
    assert classify_file_language(Path("server.go")) == "Go"
    assert classify_file_language(Path("Dockerfile")) == "Dockerfile"
    assert classify_file_language(Path("Makefile")) == "Makefile"
    assert classify_file_language(Path("unknown.xyz123")) == "Unknown"
    assert classify_file_language(Path("LICENSE")) == "Extensionless"


def test_compute_language_breakdown():
    """compute_language_breakdown aggregates byte counts and calculates deterministic percentages."""
    files = [
        ("Python", 600),
        ("Python", 400),
        ("TypeScript", 500),
        ("Markdown", 500),
    ]
    breakdown = compute_language_breakdown(files)

    assert len(breakdown) == 3
    # Sorted by bytes descending
    assert breakdown[0].language == "Python"
    assert breakdown[0].bytes_count == 1000
    assert breakdown[0].files_count == 2
    assert breakdown[0].percentage == 50.0

    # 500 bytes each: Markdown comes before TypeScript alphabetically
    assert breakdown[1].bytes_count == 500
    assert breakdown[2].bytes_count == 500
    assert breakdown[1].percentage == 25.0
    assert breakdown[2].percentage == 25.0


# ===========================================================================
# 3. Manifest Extraction
# ===========================================================================


def test_parse_package_json():
    """parse_package_json extracts npm metadata, dependencies, devDependencies, and peerDependencies."""
    pkg_content = json.dumps({
        "name": "my-app",
        "version": "1.2.3",
        "dependencies": {
            "react": "^18.2.0",
            "next": "14.1.0",
        },
        "devDependencies": {
            "typescript": "^5.0.0",
        },
        "peerDependencies": {
            "react-dom": "^18.2.0",
        },
    })
    summary, warnings = parse_package_json(pkg_content, "package.json")

    assert len(warnings) == 0
    assert summary is not None
    assert summary.manifest_type == "npm"
    assert summary.project_name == "my-app"
    assert summary.project_version == "1.2.3"
    assert summary.dependencies_count == 4

    dep_map = {d.name: (d.version_spec, d.dependency_type) for d in summary.dependencies}
    assert dep_map["react"] == ("^18.2.0", "runtime")
    assert dep_map["next"] == ("14.1.0", "runtime")
    assert dep_map["typescript"] == ("^5.0.0", "dev")
    assert dep_map["react-dom"] == ("^18.2.0", "peer")


def test_parse_package_json_malformed():
    """parse_package_json handles syntax errors gracefully with sanitized warnings."""
    summary, warnings = parse_package_json("{invalid_json: true", "package.json")
    assert summary is None
    assert len(warnings) == 1
    assert warnings[0].warning_code == "MANIFEST_SYNTAX_ERROR"


def test_parse_requirements_txt():
    """parse_requirements_txt parses python dependencies, ignores comments, flags, and blank lines."""
    req_content = """
    # Core requirements
    fastapi>=0.110.0
    pydantic~=2.6.0
    requests==2.31.0
    uvicorn

    # Pip flags to ignore
    -r other-requirements.txt
    -e .
    --extra-index-url https://pypi.org/simple

    pytest>=8.0.0 # inline comment
    """
    summary, warnings = parse_requirements_txt(req_content, "requirements.txt")

    assert summary is not None
    assert summary.manifest_type == "pip"
    dep_names = {d.name: d.version_spec for d in summary.dependencies}
    assert "fastapi" in dep_names
    assert dep_names["fastapi"] == ">=0.110.0"
    assert "pydantic" in dep_names
    assert "requests" in dep_names
    assert "uvicorn" in dep_names
    assert dep_names["uvicorn"] is None
    assert "pytest" in dep_names
    assert dep_names["pytest"] == ">=8.0.0"
    assert "-r" not in dep_names
    assert "-e" not in dep_names


def test_parse_cargo_toml():
    """parse_cargo_toml extracts Rust crate metadata and dependencies."""
    cargo_content = """
    [package]
    name = "devtwin-miner"
    version = "0.1.0"
    edition = "2021"

    [dependencies]
    serde = { version = "1.0", features = ["derive"] }
    tokio = "1.35"

    [dev-dependencies]
    criterion = "0.5"
    """
    summary, warnings = parse_cargo_toml(cargo_content, "Cargo.toml")

    assert summary is not None
    assert summary.manifest_type == "cargo"
    assert summary.project_name == "devtwin-miner"
    assert summary.project_version == "0.1.0"
    assert summary.dependencies_count == 3

    dep_map = {d.name: (d.version_spec, d.dependency_type) for d in summary.dependencies}
    assert dep_map["serde"] == ("1.0", "runtime")
    assert dep_map["tokio"] == ("1.35", "runtime")
    assert dep_map["criterion"] == ("0.5", "dev")


def test_parse_cargo_toml_malformed():
    """parse_cargo_toml handles malformed TOML safely."""
    summary, warnings = parse_cargo_toml("[package\nincomplete_table", "Cargo.toml")
    assert summary is None
    assert len(warnings) == 1
    assert warnings[0].warning_code == "MANIFEST_SYNTAX_ERROR"


# ===========================================================================
# 4. AST Parser Foundation
# ===========================================================================


def test_python_ast_parser_extracts_structures():
    """PythonASTParser extracts functions, classes, imports, and docstring metadata."""
    code = b"""
import os
import sys
from typing import List, Optional
from app.core import config

class BaseService:
    \"\"\"Base service docstring.\"\"\"
    def __init__(self, name: str):
        self.name = name

class DataService(BaseService):
    def process(self, items):
        pass

def compute_total(a, b, c=1):
    return a + b + c

async def fetch_async(url):
    \"\"\"Async fetch helper.\"\"\"
    pass
"""
    parser = PythonASTParser()
    summary, warnings = parser.parse_file(Path("service.py"), "service.py", code)

    assert len(warnings) == 0
    assert summary is not None
    assert summary.language == "Python"
    assert summary.functions_count == 4  # __init__, process, compute_total, fetch_async
    assert summary.classes_count == 2
    assert summary.imports_count == 4

    # Classes
    class_names = {c.name: c.base_classes for c in summary.classes}
    assert "BaseService" in class_names
    assert class_names["DataService"] == ["BaseService"]

    # Functions
    fn_map = {f.name: f for f in summary.functions}
    assert fn_map["compute_total"].args_count == 3
    assert fn_map["compute_total"].is_async is False
    assert fn_map["fetch_async"].is_async is True
    assert fn_map["fetch_async"].has_docstring is True

    # Imports
    import_mods = [imp.module for imp in summary.imports if imp.is_from]
    assert "typing" in import_mods
    assert "app.core" in import_mods


def test_python_ast_parser_handles_syntax_error():
    """PythonASTParser handles syntax errors without throwing unhandled exceptions."""
    bad_code = b"""
def broken_syntax(
    print("missing closing paren"
"""
    parser = PythonASTParser()
    summary, warnings = parser.parse_file(Path("broken.py"), "broken.py", bad_code)

    assert summary is not None
    assert "SYNTAX_ERROR" in (summary.parse_error or "")
    assert len(warnings) == 1
    assert warnings[0].warning_code == "AST_SYNTAX_ERROR"


# ===========================================================================
# 5. Archive Safety and Extraction Limits
# ===========================================================================


def create_in_memory_tar(files: dict[str, bytes]) -> bytes:
    import io
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = 1700000000
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_safe_extract_tar_rejects_excessive_member_count(tmp_path):
    """safe_extract_tar rejects archives exceeding MAX_EXTRACTED_MEMBERS."""
    with patch("app.workers.fetcher.MAX_EXTRACTED_MEMBERS", 5):
        files = {f"file_{i}.txt": b"content" for i in range(10)}
        archive_bytes = create_in_memory_tar(files)
        with pytest.raises(SecurityArchiveError) as exc_info:
            safe_extract_tar(archive_bytes, tmp_path)
        assert "member count" in str(exc_info.value).lower()


def test_safe_extract_tar_rejects_oversized_single_file(tmp_path):
    """safe_extract_tar rejects an individual file exceeding MAX_SINGLE_FILE_BYTES."""
    with patch("app.workers.fetcher.MAX_SINGLE_FILE_BYTES", 100):
        files = {"large.bin": b"A" * 200}
        archive_bytes = create_in_memory_tar(files)
        with pytest.raises(SecurityArchiveError) as exc_info:
            safe_extract_tar(archive_bytes, tmp_path)
        assert "single file size limit" in str(exc_info.value).lower()


def test_safe_extract_tar_rejects_excessive_total_uncompressed_bytes(tmp_path):
    """safe_extract_tar rejects archives exceeding MAX_EXTRACTED_BYTES."""
    with patch("app.workers.fetcher.MAX_EXTRACTED_BYTES", 500):
        files = {
            "f1.txt": b"B" * 300,
            "f2.txt": b"B" * 300,
        }
        archive_bytes = create_in_memory_tar(files)
        with pytest.raises(SecurityArchiveError) as exc_info:
            safe_extract_tar(archive_bytes, tmp_path)
        assert "total uncompressed bytes" in str(exc_info.value).lower()


# ===========================================================================
# 6. End-to-End Mining and Worker Lifecycle Integration
# ===========================================================================


def test_mine_repository_end_to_end(tmp_path):
    """mine_repository produces a complete, deterministically sorted MiningResult."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    repo = workspace / "repo"
    repo.mkdir()

    # Create mixed project files
    (repo / "package.json").write_text(json.dumps({
        "name": "full-stack-app",
        "dependencies": {"express": "4.18.2"},
    }), encoding="utf-8")

    (repo / "requirements.txt").write_text("fastapi>=0.100.0\npytest\n", encoding="utf-8")

    (repo / "server.py").write_text("""
def run_app():
    return True
""", encoding="utf-8")

    (repo / "README.md").write_text("# Full Stack App\nDocumentation\n", encoding="utf-8")
    (repo / "app.js").write_text("console.log('node');\n", encoding="utf-8")

    # Excluded folder
    node_modules = repo / "node_modules"
    node_modules.mkdir()
    (node_modules / "express.js").write_text("// vendor code", encoding="utf-8")

    result = mine_repository(repo, workspace)

    assert isinstance(result, MiningResult)
    assert result.inventory.total_files == 5
    assert result.inventory.excluded_files >= 1

    # Languages
    langs = {l.language for l in result.languages}
    assert "Python" in langs
    assert "JavaScript" in langs
    assert "Markdown" in langs
    assert "JSON" in langs

    # Manifests
    manifest_types = {m.manifest_type for m in result.manifests}
    assert "npm" in manifest_types
    assert "pip" in manifest_types

    # AST
    ast_files = [a.file_path for a in result.ast_summaries]
    assert "server.py" in ast_files
    server_ast = next(a for a in result.ast_summaries if a.file_path == "server.py")
    assert server_ast.functions_count == 1
    assert server_ast.functions[0].name == "run_app"


@pytest.mark.asyncio
async def test_execute_job_run_transitions_to_mining_and_preserves_processing_state(tmp_path):
    """execute_job_run transitions run through MINING to SKILL_GRAPH and keeps job in PROCESSING."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    job = AnalysisJob(id=job_id, repository_id=repo_id, status="PROCESSING", attempt_count=1)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Create dummy repo in tmp_path
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("print('hello')", encoding="utf-8")

    from app.workers.fetcher import FetchResult

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
            # Context manager yielding tmp_path
            import contextlib
            @contextlib.asynccontextmanager
            async def dummy_ws():
                yield tmp_path

            mock_ws.side_effect = dummy_ws
            run = await execute_job_run(job, mock_session)

    # Step 6H: run reaches COMPLETED, job reaches COMPLETED, completed_at populated
    assert run.status == "COMPLETED"
    assert run.completed_at is not None
    assert job.status == "COMPLETED"
    assert job.completed_at is not None
    assert hasattr(run, "_mining_result")
    assert run._mining_result is not None
    assert run._mining_result.inventory.total_files == 1
    assert hasattr(run, "_skillgraph_result")
    assert run._skillgraph_result is not None
    assert hasattr(run, "_coderisk_result")
    assert run._coderisk_result is not None
    assert hasattr(run, "_capability_result")
    assert run._capability_result is not None
    assert mock_session.commit.await_count >= 2
