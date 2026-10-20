"""
DevTwin Capability — Scoring Engine (Capability Model v1)

Implements the mathematical scoring formulas defined in docs/10_SCORING_MODEL.md
and frozen in DECISIONS.md (ADR-004, ADR-005, ADR-010, ADR-011).

Formula summary:
    evidence_weight_i = S_i * D_i * R_i * T_i * P_i
    effective_weight_k = evidence_weight_k / sqrt(k)   (diminishing returns, k=1-based rank)
    score = clamp(sigmoid(sum(effective_weights) / Z), 0.01, 0.99)
    confidence = clamp(q * d * c * R_mean, 0.05, 0.98)

Where:
    S_i  = type strength: MENTION=0.20, USAGE=0.45, APPLIED_ENGINEERING=0.70, DEMONSTRATED_OUTCOME=1.00
    D_i  = directness (stored on evidence row, 0.0-1.0)
    R_i  = reliability (stored on evidence row, 0.0-1.0)
    T_i  = temporal decay = exp(-ln2 * age_days / 365.0)
    P_i  = polarity (-1.0 to +1.0; negative for risk findings, ADR-010)
    Z    = 3.0 (logistic calibration constant)
    q    = 1 - exp(-0.35 * N)          (quantity factor)
    d    = 0.60/0.85/1.00 for 1/2/3+ evidence types (diversity factor)
    c    = max(0.50, 1.0 - 0.25 * N_neg/N)  (consistency factor)
    R_mean = mean reliability across all evidence items

Design decisions:
- Polarity is bounded to [-1.0, +1.0] per DB CHECK; risk finding polarity is negative (ADR-010).
- A declared dependency alone (MENTION, polarity=+1) produces low confidence (~0.14),
  preventing inflation without independent corroboration.
- Score and confidence are independently computed; a high score with low confidence
  is semantically distinct from a high score with high confidence.
- Diminishing returns prevent 50 identical imports from dominating a score.
"""

import math
from datetime import datetime, timezone
from typing import List, NamedTuple, Optional, Tuple
import uuid

from app.capability.models import TargetCapabilityScore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORING_VERSION = "1.0.0"

# Calibration constant — logistic sigmoid denominator
_Z = 3.0

# Type-strength mapping (Capability Model v1, docs/10_SCORING_MODEL.md)
_TYPE_STRENGTH: dict = {
    "MENTION": 0.20,
    "USAGE": 0.45,
    "APPLIED_ENGINEERING": 0.70,
    "DEMONSTRATED_OUTCOME": 1.00,
}

# Temporal half-life (365 days => T=0.5 at one year)
_HALF_LIFE_DAYS = 365.0


# ---------------------------------------------------------------------------
# Internal evidence descriptor
# ---------------------------------------------------------------------------


class _EvidenceRow(NamedTuple):
    """Flattened, type-safe descriptor used inside the scorer."""

    evidence_id: uuid.UUID
    ev_type: str
    strength: Optional[float]
    directness: float
    reliability: float
    polarity: float
    recency: datetime


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _type_strength(ev_type: str) -> float:
    """Return the fixed type-strength coefficient for a given evidence type."""
    return _TYPE_STRENGTH.get(ev_type.upper(), 0.20)


def _temporal_decay(recency: datetime, now: datetime) -> float:
    """
    Exponential temporal decay factor T_i = exp(-ln2 * age_days / half_life).

    Returns 1.0 for evidence timestamped now; ~0.5 for one-year-old evidence.
    Never returns a negative value; clamps to a minimum of 1e-4 for very old evidence.
    """
    age_seconds = (now - recency.replace(tzinfo=timezone.utc) if recency.tzinfo is None
                   else (now - recency)).total_seconds()
    age_days = max(0.0, age_seconds / 86400.0)
    return max(1e-4, math.exp(-math.log(2) * age_days / _HALF_LIFE_DAYS))


def _sigmoid(x: float) -> float:
    """Logistic sigmoid: 1 / (1 + exp(-x))."""
    # Guard against overflow
    if x > 700:
        return 1.0
    if x < -700:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------


def calculate_target_capability(
    evidence_rows: List[_EvidenceRow],
    target_id: uuid.UUID,
    target_type: str,
    target_name: str,
    now: datetime | None = None,
) -> TargetCapabilityScore:
    """
    Calculate score and confidence for a single (developer, target) pair.

    Parameters
    ----------
    evidence_rows : List[_EvidenceRow]
        All evidence items linked to this (target_type, target_id).
    target_id : uuid.UUID
        The taxonomy entity UUID (skill/technology/concept).
    target_type : str
        One of 'skill', 'technology', 'concept'.
    target_name : str
        Human-readable name for the target (informational).
    now : datetime | None
        Reference time for recency decay. Defaults to UTC now.

    Returns
    -------
    TargetCapabilityScore
        Scored capability result with exclusive arc FK set.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # --- No evidence case ---
    if not evidence_rows:
        # Represent as a zero-score, minimum-confidence result rather than None.
        # This makes it explicit that insufficient evidence exists (ADR-004).
        return _make_score(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            raw_score=0.01,
            confidence=0.05,
            evidence_count=0,
            evidence_ids=[],
        )

    # --- Compute per-evidence raw weights ---
    raw_weights = []
    for row in evidence_rows:
        S = (
            max(0.0, min(1.0, row.strength))
            if row.strength is not None
            else _type_strength(row.ev_type)
        )
        D = max(0.0, min(1.0, row.directness))
        R = max(0.0, min(1.0, row.reliability))
        T = _temporal_decay(row.recency, now)
        P = max(-1.0, min(1.0, row.polarity))
        raw_weights.append(S * D * R * T * P)

    # --- Diminishing returns: rank evidence by |weight| descending ---
    # Separate positive and negative contributions, apply sqrt(k) discount per direction.
    # Rank 1-based within each polarity direction.
    pos_items = sorted(
        [(w, ev.evidence_id) for w, ev in zip(raw_weights, evidence_rows) if w > 0],
        key=lambda x: -x[0],
    )
    neg_items = sorted(
        [(w, ev.evidence_id) for w, ev in zip(raw_weights, evidence_rows) if w <= 0],
        key=lambda x: x[0],  # most negative first
    )

    effective_sum = 0.0
    for k, (w, _) in enumerate(pos_items, start=1):
        effective_sum += w / math.sqrt(k)
    for k, (w, _) in enumerate(neg_items, start=1):
        effective_sum += w / math.sqrt(k)

    # --- Score: sigmoid with calibration constant Z ---
    raw_score_val = _sigmoid(effective_sum / _Z)
    # Clamp to [0.01, 0.99] (never claim perfect or zero capability)
    final_score = max(0.01, min(0.99, raw_score_val))

    # --- Confidence: independent of score ---
    N = len(evidence_rows)
    N_neg = sum(1 for w in raw_weights if w < 0)
    R_values = [max(0.0, min(1.0, row.reliability)) for row in evidence_rows]
    R_mean = sum(R_values) / N if N > 0 else 0.0

    # Quantity factor: saturates toward 1.0 as N grows
    q = 1.0 - math.exp(-0.35 * N)

    # Diversity factor: how many distinct evidence types are represented
    distinct_types = len({row.ev_type for row in evidence_rows})
    if distinct_types >= 3:
        d = 1.00
    elif distinct_types == 2:
        d = 0.85
    else:
        d = 0.60

    # Consistency factor: penalised by negative-evidence proportion
    c = max(0.50, 1.0 - 0.25 * (N_neg / N))

    confidence = max(0.05, min(0.98, q * d * c * R_mean))

    return _make_score(
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        raw_score=final_score,
        confidence=confidence,
        evidence_count=N,
        evidence_ids=[row.evidence_id for row in evidence_rows],
    )


def _make_score(
    *,
    target_type: str,
    target_id: uuid.UUID,
    target_name: str,
    raw_score: float,
    confidence: float,
    evidence_count: int,
    evidence_ids: list,
) -> TargetCapabilityScore:
    """Build a TargetCapabilityScore with the correct exclusive-arc FK set."""
    skill_id = technology_id = concept_id = None
    if target_type == "skill":
        skill_id = target_id
    elif target_type == "technology":
        technology_id = target_id
    elif target_type == "concept":
        concept_id = target_id
    else:
        raise ValueError(f"Unknown target_type: {target_type!r}. Expected 'skill', 'technology', or 'concept'.")

    return TargetCapabilityScore(
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        score=raw_score,
        confidence=confidence,
        evidence_count=evidence_count,
        evidence_ids=evidence_ids,
        skill_id=skill_id,
        technology_id=technology_id,
        concept_id=concept_id,
    )


# Re-export for service use
EvidenceRow = _EvidenceRow
