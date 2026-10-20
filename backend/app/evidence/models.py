"""
DevTwin Evidence — Models & Schemas
Data classes for Evidence Generation results and evidence item transfer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class EvidenceItemData:
    """In-memory representation of an individual evidence item derived from an observation."""

    observation_id: uuid.UUID
    type: str  # 'MENTION' | 'USAGE' | 'APPLIED_ENGINEERING' | 'DEMONSTRATED_OUTCOME'
    strength: float  # 0.0 .. 1.0
    directness: float  # 0.0 .. 1.0
    reliability: float  # 0.0 .. 1.0
    polarity: float  # -1.0 .. 1.0 (negative for code risks)
    recency: datetime
    skills: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    source_tool: str = ""
    source_reference: Optional[Dict[str, Any]] = None


@dataclass
class EvidenceResult:
    """Summary contract returned by Stage 6 Evidence Generation."""

    schema_version: str = "1.0.0"
    evidence_version: str = "1.0.0"
    total_evidence: int = 0
    evidence_by_type: Dict[str, int] = field(default_factory=dict)
    evidence_by_polarity: Dict[str, int] = field(default_factory=dict)
    skills_count: int = 0
    technologies_count: int = 0
    concepts_count: int = 0
    items: List[EvidenceItemData] = field(default_factory=list)
    completed_at: str = ""
