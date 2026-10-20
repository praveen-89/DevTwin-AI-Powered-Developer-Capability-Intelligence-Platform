"""
DevTwin Backend — Evidence API Schemas (Step 6J)
"""

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class EvidenceTaxonomyRef(BaseModel):
    """Reference to a taxonomy entity supported by evidence."""
    id: uuid.UUID
    name: str
    type: str = Field(..., description="Taxonomy type: skill, technology, or concept")

    model_config = ConfigDict(from_attributes=True)


class EvidenceSourceProvenance(BaseModel):
    """Source code provenance and contextual grounding for an evidence item."""
    observation_id: Optional[uuid.UUID] = None
    source_tool: Optional[str] = None
    observation_type: Optional[str] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    rule_id: Optional[str] = None


class EvidenceResponse(BaseModel):
    """Contextualized evidence item supporting developer capabilities."""
    id: uuid.UUID
    type: str = Field(..., description="MENTION, USAGE, APPLIED_ENGINEERING, DEMONSTRATED_OUTCOME")
    strength: float = Field(..., ge=0.0, le=1.0)
    directness: float = Field(..., ge=0.0, le=1.0)
    reliability: float = Field(..., ge=0.0, le=1.0)
    polarity: float = Field(..., ge=-1.0, le=1.0, description="Positive (+1.0) or negative (-1.0 for risk findings)")
    recency: datetime
    created_at: datetime
    skills: List[EvidenceTaxonomyRef] = Field(default_factory=list)
    technologies: List[EvidenceTaxonomyRef] = Field(default_factory=list)
    concepts: List[EvidenceTaxonomyRef] = Field(default_factory=list)
    provenance: Optional[EvidenceSourceProvenance] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceListResponse(BaseModel):
    """Paginated collection of evidence records."""
    items: List[EvidenceResponse]
    total: int
    limit: int
    offset: int
