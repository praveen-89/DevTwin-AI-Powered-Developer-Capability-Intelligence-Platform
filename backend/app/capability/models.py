"""
DevTwin Capability — Data Models
Data contracts for the Capability Scoring Engine (Step 6G).
These are in-memory transfer objects; the ORM models live in app.models.capability.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid


@dataclass
class TargetCapabilityScore:
    """
    Result of scoring a single (developer, target) pair.

    The target is identified by exactly one of skill_id, technology_id, or concept_id
    (the Exclusive Arc, ADR-005). The name is informational only.

    score       — logistic-sigmoid aggregate [0.01, 0.99] (Capability Model v1).
    confidence  — independent uncertainty estimate [0.05, 0.98].
                  Low confidence != low score; a declared-dependency-only evidence item
                  yields confidence ~0.14 even if score is moderate.
    evidence_count — total evidence items that contributed.
    evidence_ids   — provenance references back to persisted evidence rows.
    target_type    — one of 'skill', 'technology', 'concept'.
    """

    target_type: str  # 'skill' | 'technology' | 'concept'
    target_id: uuid.UUID
    target_name: str
    score: float
    confidence: float
    evidence_count: int
    evidence_ids: List[uuid.UUID] = field(default_factory=list)

    # Optional FK slot -- exactly one is set, matching target_type
    skill_id: Optional[uuid.UUID] = None
    technology_id: Optional[uuid.UUID] = None
    concept_id: Optional[uuid.UUID] = None

    def __post_init__(self) -> None:
        # Enforce exclusive arc invariant at Python level
        set_count = sum(
            1 for v in (self.skill_id, self.technology_id, self.concept_id)
            if v is not None
        )
        if set_count != 1:
            raise ValueError(
                f"TargetCapabilityScore must have exactly one target FK set "
                f"(got skill_id={self.skill_id}, technology_id={self.technology_id}, "
                f"concept_id={self.concept_id})."
            )


@dataclass
class CapabilityResult:
    """
    Summary contract returned by Stage 7 Capability Scoring (persist_capabilities).
    Mirrors the pattern of EvidenceResult for pipeline consistency.
    """

    schema_version: str = "1.0.0"
    scoring_version: str = "1.0.0"
    developer_id: Optional[uuid.UUID] = None
    total_targets: int = 0
    targets_by_type: Dict[str, int] = field(default_factory=dict)
    # Distribution of score buckets: 'low' (<0.33), 'moderate' (0.33-0.66), 'high' (>0.66)
    score_distribution: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    history_entries_appended: int = 0
    completed_at: str = ""
    scores: List[TargetCapabilityScore] = field(default_factory=list)
