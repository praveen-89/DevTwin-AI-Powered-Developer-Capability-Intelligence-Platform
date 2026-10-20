"""
DevTwin Backend — SkillGraph API Schemas (Step 6J)
"""

from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SkillGraphLanguageResponse(BaseModel):
    """Mined repository language entry."""
    language: str
    bytes: int

    model_config = ConfigDict(from_attributes=True)


class SkillGraphDependencyResponse(BaseModel):
    """Mined repository package dependency entry."""
    ecosystem: str
    package_name: str
    version_constraint: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SkillGraphNodeResponse(BaseModel):
    """Node in the developer or repository SkillGraph."""
    id: uuid.UUID
    name: str
    type: str = Field(..., description="skill, technology, or concept")
    domain_or_category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SkillGraphEdgeResponse(BaseModel):
    """Directed relationship edge in the SkillGraph."""
    source_id: uuid.UUID
    target_id: uuid.UUID
    source_name: str
    target_name: str
    relation_type: str = Field(..., description="REQUIRES, RELATED_TO, PART_OF, USES, APPLIES")

    model_config = ConfigDict(from_attributes=True)


class SkillGraphResponse(BaseModel):
    """Complete SkillGraph view for a repository."""
    repository_id: uuid.UUID
    analysis_run_id: Optional[uuid.UUID] = Field(None, description="Analysis run ID for this snapshot")
    languages: List[SkillGraphLanguageResponse] = Field(default_factory=list)
    dependencies: List[SkillGraphDependencyResponse] = Field(default_factory=list)
    nodes: List[SkillGraphNodeResponse] = Field(default_factory=list)
    edges: List[SkillGraphEdgeResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
