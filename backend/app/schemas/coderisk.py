"""
DevTwin Backend — CodeRisk API Schemas (Step 6J)
"""

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class RiskFindingResponse(BaseModel):
    """Static risk analysis finding for a repository."""
    id: uuid.UUID
    repository_id: uuid.UUID
    analysis_run_id: uuid.UUID
    category: str = Field(..., description="SECURITY, RELIABILITY, TESTING, MAINTAINABILITY, DEPENDENCY, ARCHITECTURE")
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_type: str = Field(..., description="Rule pattern ID, e.g. SEC-001")
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskFindingListResponse(BaseModel):
    """Paginated collection of CodeRisk findings."""
    items: List[RiskFindingResponse]
    total: int
    limit: int
    offset: int
    analysis_run_id: Optional[uuid.UUID] = Field(None, description="The analysis run these findings belong to")
