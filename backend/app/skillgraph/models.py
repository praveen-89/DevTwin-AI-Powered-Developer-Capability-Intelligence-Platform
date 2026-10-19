"""
DevTwin SkillGraph — Data Models and Mapping Contracts
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class RepositoryLanguageData:
    language: str
    bytes: int


@dataclass(frozen=True)
class RepositoryDependencyData:
    ecosystem: str
    package_name: str
    version_constraint: Optional[str] = None


@dataclass(frozen=True)
class ObservationData:
    type: str
    source_tool: str
    source_reference: Dict[str, Any]
    confidence: float = 1.0


@dataclass(frozen=True)
class TechnologyData:
    name: str
    type: str  # 'language', 'framework', 'library', 'tool', 'runtime'


@dataclass(frozen=True)
class SkillData:
    name: str
    domain: Optional[str] = None


@dataclass(frozen=True)
class ConceptData:
    name: str


@dataclass(frozen=True)
class SkillGraphMapping:
    """
    Pure in-memory mapping of mining results to database domain entities and taxonomy relationships.
    """
    languages: List[RepositoryLanguageData] = field(default_factory=list)
    dependencies: List[RepositoryDependencyData] = field(default_factory=list)
    observations: List[ObservationData] = field(default_factory=list)
    technologies: List[TechnologyData] = field(default_factory=list)
    skills: List[SkillData] = field(default_factory=list)
    concepts: List[ConceptData] = field(default_factory=list)
    skill_technologies: List[Tuple[str, str]] = field(default_factory=list)  # (skill_name, tech_name)
    skill_concepts: List[Tuple[str, str]] = field(default_factory=list)  # (skill_name, concept_name)
    technology_concepts: List[Tuple[str, str]] = field(default_factory=list)  # (tech_name, concept_name)
    skill_relationships: List[Tuple[str, str, str]] = field(default_factory=list)  # (src_skill, tgt_skill, relation_type)


@dataclass(frozen=True)
class SkillGraphResult:
    """
    Summary of persisted SkillGraph entities and edges produced by an analysis run.
    """
    schema_version: str
    observations_count: int
    languages_count: int
    dependencies_count: int
    technologies_count: int
    skills_count: int
    concepts_count: int
    edges_count: int
    completed_at: str
