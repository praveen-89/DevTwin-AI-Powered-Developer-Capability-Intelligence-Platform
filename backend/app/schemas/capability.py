"""
DevTwin Backend — Capability API Schemas (Step 6J)
"""

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class CapabilityTargetResponse(BaseModel):
    """Identifies the resolved taxonomy target of a capability."""
    target_type: str = Field(..., description="Taxonomy type: skill, technology, or concept")
    target_id: uuid.UUID = Field(..., description="Taxonomy entity UUID")
    target_name: str = Field(..., description="Canonical entity name")
    domain_or_category: Optional[str] = Field(None, description="Domain (skills) or type (technologies)")

    model_config = ConfigDict(from_attributes=True)


class DeveloperCapabilityResponse(BaseModel):
    """Current inferred capability state per developer per target."""
    id: uuid.UUID
    developer_id: uuid.UUID
    target: CapabilityTargetResponse
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score [0.0, 1.0]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Uncertainty-aware confidence [0.0, 1.0]")
    scoring_version: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeveloperCapabilityListResponse(BaseModel):
    """Paginated collection of developer capabilities."""
    items: List[DeveloperCapabilityResponse]
    total: int
    limit: int
    offset: int


class CapabilityHistoryItemResponse(BaseModel):
    """Immutable log entry of a capability score snapshot."""
    id: uuid.UUID
    capability_id: uuid.UUID
    analysis_run_id: Optional[uuid.UUID] = None
    target: CapabilityTargetResponse
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    scoring_version: str
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CapabilityHistoryListResponse(BaseModel):
    """Paginated collection of historical capability snapshots."""
    items: List[CapabilityHistoryItemResponse]
    total: int
    limit: int
    offset: int
