"""
DevTwin Mining Engine — Structured Result Contracts and Models
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class RepositoryInventory:
    total_files: int
    source_files: int
    binary_files: int
    excluded_files: int
    total_bytes: int
    source_bytes: int


@dataclass(frozen=True)
class LanguageBreakdown:
    language: str
    files_count: int
    bytes_count: int
    percentage: float


@dataclass(frozen=True)
class ManifestDependency:
    name: str
    version_spec: Optional[str]
    dependency_type: str  # "runtime", "dev", "peer"


@dataclass(frozen=True)
class ManifestSummary:
    file_path: str
    manifest_type: str  # "npm", "pip", "cargo"
    project_name: Optional[str]
    project_version: Optional[str]
    dependencies_count: int
    dependencies: List[ManifestDependency] = field(default_factory=list)


@dataclass(frozen=True)
class ASTFunctionSummary:
    name: str
    line_number: int
    is_async: bool
    args_count: int
    has_docstring: bool


@dataclass(frozen=True)
class ASTClassSummary:
    name: str
    line_number: int
    base_classes: List[str]
    methods_count: int
    has_docstring: bool


@dataclass(frozen=True)
class ASTImportSummary:
    module: Optional[str]
    names: List[str]
    is_from: bool
    line_number: int


@dataclass(frozen=True)
class ASTFileSummary:
    file_path: str
    language: str
    functions_count: int
    classes_count: int
    imports_count: int
    functions: List[ASTFunctionSummary] = field(default_factory=list)
    classes: List[ASTClassSummary] = field(default_factory=list)
    imports: List[ASTImportSummary] = field(default_factory=list)
    parse_error: Optional[str] = None


@dataclass(frozen=True)
class MiningWarning:
    file_path: Optional[str]
    warning_code: str
    message: str


@dataclass(frozen=True)
class MiningResult:
    schema_version: str
    mining_version: str
    inventory: RepositoryInventory
    languages: List[LanguageBreakdown]
    manifests: List[ManifestSummary]
    ast_summaries: List[ASTFileSummary]
    warnings: List[MiningWarning]
    completed_at: str
