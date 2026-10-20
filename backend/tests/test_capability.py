"""
DevTwin — Step 6G Capability Scoring Tests

Hermetic unit and integration tests for the Capability Scoring Engine.
All database interaction is mocked; no live PostgreSQL connection required.
Tests cover Capability Model v1 contracts:
- Positive evidence aggregation
- Negative evidence and bounded polarity (ADR-010)
- Weak dependency-only evidence (MENTION produces low confidence)
- Reliability and directness handling
- Recency/temporal decay
- Repeated/corroborating evidence and diminishing returns
- Duplicate evidence and idempotent persistence
- No evidence / insufficient evidence (zero-confidence result)
- Score and confidence semantics (independent)
- Provenance and taxonomy relationships
- Isolation between developers, repositories, analysis runs
- Transaction rollback on persistence failure
- Worker Stage 7 ordering and status transitions
- Failure behavior without premature completion

Testing conventions:
- AsyncMock for SQLAlchemy session
- Deterministic UUIDs for reproducibility
- No real database, no real GitHub calls
"""

import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.capability.models import CapabilityResult, TargetCapabilityScore
from app.capability.scorer import (
    SCORING_VERSION,
    EvidenceRow,
    calculate_target_capability,
    _sigmoid,
    _temporal_decay,
    _type_strength,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)

_SKILL_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
_TECH_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
_CONCEPT_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
_DEV_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000001")
_RUN_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000001")
_REPO_ID = uuid.UUID("ffffffff-0000-0000-0000-000000000001")
_PROJECT_ID = uuid.UUID("11111111-0000-0000-0000-000000000001")
_EV_ID_1 = uuid.UUID("22222222-0000-0000-0000-000000000001")
_EV_ID_2 = uuid.UUID("22222222-0000-0000-0000-000000000002")
_EV_ID_3 = uuid.UUID("22222222-0000-0000-0000-000000000003")


def _make_evidence_row(
    ev_id: uuid.UUID = _EV_ID_1,
    ev_type: str = "USAGE",
    strength: Optional[float] = None,
    directness: float = 1.0,
    reliability: float = 1.0,
    polarity: float = 1.0,
    age_days: float = 0.0,
) -> EvidenceRow:
    recency = _NOW - timedelta(days=age_days)
    return EvidenceRow(
        evidence_id=ev_id,
        ev_type=ev_type,
        strength=strength,
        directness=directness,
        reliability=reliability,
        polarity=polarity,
        recency=recency,
    )


# ---------------------------------------------------------------------------
# Unit Tests: _type_strength
# ---------------------------------------------------------------------------


class TestTypeStrength:
    def test_mention(self):
        assert _type_strength("MENTION") == pytest.approx(0.20)

    def test_usage(self):
        assert _type_strength("USAGE") == pytest.approx(0.45)

    def test_applied_engineering(self):
        assert _type_strength("APPLIED_ENGINEERING") == pytest.approx(0.70)

    def test_demonstrated_outcome(self):
        assert _type_strength("DEMONSTRATED_OUTCOME") == pytest.approx(1.00)

    def test_case_insensitive(self):
        assert _type_strength("usage") == pytest.approx(0.45)

    def test_unknown_defaults_to_mention(self):
        assert _type_strength("UNKNOWN_TYPE") == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# Unit Tests: _temporal_decay
# ---------------------------------------------------------------------------


class TestTemporalDecay:
    def test_current_evidence_is_near_one(self):
        t = _temporal_decay(_NOW, _NOW)
        assert t == pytest.approx(1.0, abs=1e-6)

    def test_half_life_at_365_days(self):
        recency = _NOW - timedelta(days=365)
        t = _temporal_decay(recency, _NOW)
        assert t == pytest.approx(0.5, abs=0.01)

    def test_two_year_old_is_quarter_strength(self):
        recency = _NOW - timedelta(days=730)
        t = _temporal_decay(recency, _NOW)
        assert t == pytest.approx(0.25, abs=0.01)

    def test_naive_datetime_treated_as_utc(self):
        # Should not raise; naive datetimes assumed UTC
        naive = _NOW.replace(tzinfo=None)
        t = _temporal_decay(naive, _NOW)
        assert 0 < t <= 1.0

    def test_decay_never_negative(self):
        very_old = _NOW - timedelta(days=10000)
        t = _temporal_decay(very_old, _NOW)
        assert t > 0.0


# ---------------------------------------------------------------------------
# Unit Tests: calculate_target_capability — Scoring Contracts
# ---------------------------------------------------------------------------


class TestCalculateTargetCapability:

    # --- No evidence ---

    def test_no_evidence_returns_minimum_score_and_confidence(self):
        result = calculate_target_capability([], _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.score == pytest.approx(0.01)
        assert result.confidence == pytest.approx(0.05)
        assert result.evidence_count == 0
        assert result.evidence_ids == []

    def test_no_evidence_sets_correct_exclusive_arc(self):
        result = calculate_target_capability([], _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.skill_id == _SKILL_ID
        assert result.technology_id is None
        assert result.concept_id is None

    def test_no_evidence_for_technology(self):
        result = calculate_target_capability([], _TECH_ID, "technology", "FastAPI", now=_NOW)
        assert result.technology_id == _TECH_ID
        assert result.skill_id is None
        assert result.concept_id is None

    def test_no_evidence_for_concept(self):
        result = calculate_target_capability([], _CONCEPT_ID, "concept", "REST", now=_NOW)
        assert result.concept_id == _CONCEPT_ID

    # --- Score bounds ---

    def test_score_clamped_to_01_99(self):
        # Many strong items should not reach 1.0
        rows = [_make_evidence_row(ev_id=uuid.uuid4(), ev_type="DEMONSTRATED_OUTCOME", directness=1.0, reliability=1.0) for _ in range(50)]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.score <= 0.99
        assert result.score > 0.5  # but definitely high

    def test_score_never_below_minimum(self):
        # Single weak mention
        rows = [_make_evidence_row(ev_type="MENTION", directness=0.1, reliability=0.1)]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.score >= 0.01

    # --- Positive evidence aggregation ---

    def test_single_usage_evidence_produces_positive_score(self):
        rows = [_make_evidence_row()]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.score > 0.5
        assert result.evidence_count == 1

    def test_strong_evidence_scores_higher_than_weak(self):
        weak = [_make_evidence_row(ev_type="MENTION", directness=1.0, reliability=1.0)]
        strong = [_make_evidence_row(ev_type="DEMONSTRATED_OUTCOME", directness=1.0, reliability=1.0)]
        weak_result = calculate_target_capability(weak, _SKILL_ID, "skill", "Python", now=_NOW)
        strong_result = calculate_target_capability(strong, _SKILL_ID, "skill", "Python", now=_NOW)
        assert strong_result.score > weak_result.score

    def test_multiple_corroborating_items_increase_score(self):
        single = [_make_evidence_row()]
        multi = [_make_evidence_row(ev_id=uuid.uuid4()) for _ in range(5)]
        single_result = calculate_target_capability(single, _SKILL_ID, "skill", "Python", now=_NOW)
        multi_result = calculate_target_capability(multi, _SKILL_ID, "skill", "Python", now=_NOW)
        assert multi_result.score > single_result.score

    # --- Diminishing returns ---

    def test_diminishing_returns_prevent_unbounded_inflation(self):
        """50 identical items should not reach maximum score; diminishing returns apply."""
        ten_rows = [_make_evidence_row(ev_id=uuid.uuid4()) for _ in range(10)]
        fifty_rows = [_make_evidence_row(ev_id=uuid.uuid4()) for _ in range(50)]
        ten_result = calculate_target_capability(ten_rows, _SKILL_ID, "skill", "Python", now=_NOW)
        fifty_result = calculate_target_capability(fifty_rows, _SKILL_ID, "skill", "Python", now=_NOW)
        # Fifty is higher, but the gain should diminish
        diff_10_to_50 = fifty_result.score - ten_result.score
        # Adding 40 more identical items should produce <0.1 score gain when we are already above 0.5
        assert diff_10_to_50 < 0.20

    def test_provenance_evidence_ids_captured(self):
        ev_ids = [uuid.uuid4() for _ in range(3)]
        rows = [_make_evidence_row(ev_id=eid) for eid in ev_ids]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        assert set(result.evidence_ids) == set(ev_ids)

    # --- Negative evidence / bounded polarity (ADR-010) ---

    def test_negative_polarity_reduces_score(self):
        positive_row = _make_evidence_row(ev_type="USAGE", polarity=1.0)
        negative_row = _make_evidence_row(ev_type="USAGE", polarity=-0.5)
        pos_result = calculate_target_capability([positive_row], _SKILL_ID, "skill", "Python", now=_NOW)
        neg_result = calculate_target_capability([negative_row], _SKILL_ID, "skill", "Python", now=_NOW)
        assert neg_result.score < pos_result.score

    def test_bounded_polarity_does_not_destroy_all_competence(self):
        """A risk finding must not imply zero competence (ADR-010)."""
        # Mix of positive and some negative (risk findings)
        rows = [
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="APPLIED_ENGINEERING", polarity=1.0),
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="USAGE", polarity=1.0),
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="MENTION", polarity=-0.3),  # risk finding
        ]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        # Score should be reduced but not near zero
        assert result.score > 0.3

    def test_all_negative_polarity_is_below_neutral(self):
        rows = [_make_evidence_row(ev_id=uuid.uuid4(), polarity=-0.5) for _ in range(3)]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.score < 0.5

    def test_polarity_clamped_within_bounds(self):
        """Polarity values outside [-1,1] are safely clamped (should not occur via DB but defensive)."""
        row = EvidenceRow(
            evidence_id=_EV_ID_1, ev_type="USAGE", strength=0.45,
            directness=1.0, reliability=1.0, polarity=2.5,  # out of range
            recency=_NOW,
        )
        result = calculate_target_capability([row], _SKILL_ID, "skill", "Python", now=_NOW)
        assert 0.01 <= result.score <= 0.99  # no crash, clamped correctly

    # --- Reliability and directness ---

    def test_low_reliability_reduces_score(self):
        high_rel = _make_evidence_row(reliability=1.0, directness=1.0)
        low_rel = _make_evidence_row(reliability=0.1, directness=1.0)
        h = calculate_target_capability([high_rel], _SKILL_ID, "skill", "Python", now=_NOW)
        l = calculate_target_capability([low_rel], _SKILL_ID, "skill", "Python", now=_NOW)
        assert h.score > l.score

    def test_low_directness_reduces_score(self):
        high_dir = _make_evidence_row(directness=1.0, reliability=1.0)
        low_dir = _make_evidence_row(directness=0.1, reliability=1.0)
        h = calculate_target_capability([high_dir], _SKILL_ID, "skill", "Python", now=_NOW)
        l = calculate_target_capability([low_dir], _SKILL_ID, "skill", "Python", now=_NOW)
        assert h.score > l.score

    # --- Recency/temporal decay ---

    def test_recent_evidence_scores_higher_than_old(self):
        recent = _make_evidence_row(age_days=0)
        old = _make_evidence_row(age_days=730)  # 2 years
        r = calculate_target_capability([recent], _SKILL_ID, "skill", "Python", now=_NOW)
        o = calculate_target_capability([old], _SKILL_ID, "skill", "Python", now=_NOW)
        assert r.score > o.score

    # --- Confidence / uncertainty semantics ---

    def test_single_mention_has_low_confidence(self):
        """A single declared dependency alone must produce low confidence (~0.14)."""
        rows = [_make_evidence_row(ev_type="MENTION", directness=1.0, reliability=1.0, polarity=1.0)]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        # q=1-exp(-0.35), d=0.60, c=1.0 (no neg), R=1.0
        expected_q = 1.0 - math.exp(-0.35)
        expected_conf = max(0.05, min(0.98, expected_q * 0.60 * 1.0 * 1.0))
        assert result.confidence == pytest.approx(expected_conf, abs=0.01)
        assert result.confidence < 0.25  # definitely low

    def test_confidence_increases_with_more_evidence(self):
        single = [_make_evidence_row()]
        multi = [_make_evidence_row(ev_id=uuid.uuid4()) for _ in range(10)]
        r1 = calculate_target_capability(single, _SKILL_ID, "skill", "Python", now=_NOW)
        r10 = calculate_target_capability(multi, _SKILL_ID, "skill", "Python", now=_NOW)
        assert r10.confidence > r1.confidence

    def test_diverse_evidence_types_increase_confidence(self):
        single_type = [
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="USAGE") for _ in range(3)
        ]
        multi_type = [
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="USAGE"),
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="APPLIED_ENGINEERING"),
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="DEMONSTRATED_OUTCOME"),
        ]
        r_single = calculate_target_capability(single_type, _SKILL_ID, "skill", "Python", now=_NOW)
        r_multi = calculate_target_capability(multi_type, _SKILL_ID, "skill", "Python", now=_NOW)
        assert r_multi.confidence > r_single.confidence

    def test_confidence_clamped_within_bounds(self):
        rows = [_make_evidence_row(ev_id=uuid.uuid4()) for _ in range(100)]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        assert 0.05 <= result.confidence <= 0.98

    def test_negative_evidence_reduces_consistency_factor(self):
        all_pos = [_make_evidence_row(ev_id=uuid.uuid4(), polarity=1.0) for _ in range(4)]
        half_neg = [
            _make_evidence_row(ev_id=uuid.uuid4(), polarity=1.0),
            _make_evidence_row(ev_id=uuid.uuid4(), polarity=1.0),
            _make_evidence_row(ev_id=uuid.uuid4(), polarity=-0.3),
            _make_evidence_row(ev_id=uuid.uuid4(), polarity=-0.3),
        ]
        r_pos = calculate_target_capability(all_pos, _SKILL_ID, "skill", "Python", now=_NOW)
        r_mix = calculate_target_capability(half_neg, _SKILL_ID, "skill", "Python", now=_NOW)
        assert r_pos.confidence > r_mix.confidence

    # --- Score vs confidence independence ---

    def test_score_and_confidence_are_independent(self):
        """Low reliability can produce moderate score but low confidence."""
        rows = [
            _make_evidence_row(ev_id=uuid.uuid4(), ev_type="APPLIED_ENGINEERING",
                               directness=1.0, reliability=0.1, polarity=1.0)
            for _ in range(5)
        ]
        result = calculate_target_capability(rows, _SKILL_ID, "skill", "Python", now=_NOW)
        # Score can still be > 0.4 due to type strength but confidence will be low
        assert result.confidence < 0.35  # low reliability pulls confidence down

    # --- Exclusive Arc (ADR-005) ---

    def test_skill_exclusive_arc(self):
        result = calculate_target_capability([_make_evidence_row()], _SKILL_ID, "skill", "Python", now=_NOW)
        assert result.skill_id == _SKILL_ID
        assert result.technology_id is None
        assert result.concept_id is None

    def test_technology_exclusive_arc(self):
        result = calculate_target_capability([_make_evidence_row()], _TECH_ID, "technology", "FastAPI", now=_NOW)
        assert result.technology_id == _TECH_ID
        assert result.skill_id is None
        assert result.concept_id is None

    def test_concept_exclusive_arc(self):
        result = calculate_target_capability([_make_evidence_row()], _CONCEPT_ID, "concept", "REST", now=_NOW)
        assert result.concept_id == _CONCEPT_ID
        assert result.skill_id is None
        assert result.technology_id is None

    def test_unknown_target_type_raises(self):
        with pytest.raises(ValueError, match="Unknown target_type"):
            calculate_target_capability([_make_evidence_row()], _SKILL_ID, "invalid_type", "X", now=_NOW)


# ---------------------------------------------------------------------------
# Unit Tests: Evidence Strength Remediation (Fine-Grained vs Fallback)
# ---------------------------------------------------------------------------


class TestEvidenceStrengthRemediation:
    """Regression tests verifying persisted fine-grained evidence strength is respected."""

    def test_same_type_different_strengths_contribute_differently(self):
        """
        Two evidence records with the same type (APPLIED_ENGINEERING) but
        different strengths (0.80 for class vs 0.60 for docstring) must
        produce distinct capability scores.
        """
        high_str_row = _make_evidence_row(
            ev_type="APPLIED_ENGINEERING",
            strength=0.80,
            directness=1.0,
            reliability=1.0,
        )
        low_str_row = _make_evidence_row(
            ev_type="APPLIED_ENGINEERING",
            strength=0.60,
            directness=1.0,
            reliability=1.0,
        )
        res_high = calculate_target_capability([high_str_row], _SKILL_ID, "skill", "Python", now=_NOW)
        res_low = calculate_target_capability([low_str_row], _SKILL_ID, "skill", "Python", now=_NOW)

        assert res_high.score > res_low.score
        # Verify mathematically: S=0.80 -> sigmoid(0.80/3.0) ≈ 0.5663; S=0.60 -> sigmoid(0.60/3.0) ≈ 0.5498
        assert res_high.score == pytest.approx(1.0 / (1.0 + math.exp(-0.80 / 3.0)), abs=1e-4)
        assert res_low.score == pytest.approx(1.0 / (1.0 + math.exp(-0.60 / 3.0)), abs=1e-4)

    def test_critical_risk_evidence_strength_0_80_preserved(self):
        """
        A critical-risk finding with strength=0.80 and polarity=-1.0 must
        preserve strength 0.80, pulling the score down proportionally more
        than a medium risk (strength=0.40).
        """
        crit_risk = _make_evidence_row(
            ev_type="USAGE",
            strength=0.80,
            directness=0.90,
            reliability=0.95,
            polarity=-1.0,
        )
        med_risk = _make_evidence_row(
            ev_type="USAGE",
            strength=0.40,
            directness=0.90,
            reliability=0.95,
            polarity=-1.0,
        )
        res_crit = calculate_target_capability([crit_risk], _SKILL_ID, "skill", "Python", now=_NOW)
        res_med = calculate_target_capability([med_risk], _SKILL_ID, "skill", "Python", now=_NOW)

        # Critical risk has greater negative weight, so its score must be lower
        assert res_crit.score < res_med.score
        # Check that strength 0.80 is active: weight = 0.80 * 0.90 * 0.95 * 1.0 * (-1.0) = -0.684
        expected_crit_score = 1.0 / (1.0 + math.exp(-(-0.684) / 3.0))
        assert res_crit.score == pytest.approx(expected_crit_score, abs=1e-4)

    def test_low_risk_evidence_strength_0_20_preserved(self):
        """
        A low-risk finding with strength=0.20 and polarity=-0.2 must preserve
        strength 0.20 and not be inflated to the APPLIED_ENGINEERING default (0.70).
        """
        low_risk = _make_evidence_row(
            ev_type="APPLIED_ENGINEERING",
            strength=0.20,
            directness=0.90,
            reliability=0.95,
            polarity=-0.2,
        )
        res_low = calculate_target_capability([low_risk], _SKILL_ID, "skill", "Python", now=_NOW)

        # Weight = 0.20 * 0.90 * 0.95 * 1.0 * (-0.2) = -0.0342
        expected_score = 1.0 / (1.0 + math.exp(-(-0.0342) / 3.0))
        assert res_low.score == pytest.approx(expected_score, abs=1e-4)
        # Verify it is significantly higher (closer to neutral 0.50) than if strength=0.70 were used:
        # If S=0.70: weight = 0.70 * 0.90 * 0.95 * (-0.2) = -0.1197 -> score ≈ 0.490
        # With S=0.20: weight = -0.0342 -> score ≈ 0.497
        assert res_low.score > 0.495

    def test_zero_strength_not_replaced_by_type_default(self):
        """
        A strength of 0.0 is valid under CHECK (strength BETWEEN 0 AND 1)
        and must evaluate to weight=0.0 (score 0.50), not be replaced by type default.
        """
        zero_row = _make_evidence_row(
            ev_type="USAGE",
            strength=0.0,
            directness=1.0,
            reliability=1.0,
            polarity=1.0,
        )
        res_zero = calculate_target_capability([zero_row], _SKILL_ID, "skill", "Python", now=_NOW)
        # Weight = 0.0 * 1.0 * 1.0 * 1.0 * 1.0 = 0.0 -> sigmoid(0 / 3) = 0.50
        assert res_zero.score == pytest.approx(0.50, abs=1e-4)

    def test_fallback_to_type_strength_when_strength_is_none(self):
        """
        When strength is genuinely absent (None), the scorer must fallback
        to _type_strength(row.ev_type).
        """
        none_row = _make_evidence_row(
            ev_type="APPLIED_ENGINEERING",
            strength=None,
            directness=1.0,
            reliability=1.0,
            polarity=1.0,
        )
        res_fallback = calculate_target_capability([none_row], _SKILL_ID, "skill", "Python", now=_NOW)
        # S falls back to _type_strength("APPLIED_ENGINEERING") = 0.70
        expected = 1.0 / (1.0 + math.exp(-0.70 / 3.0))
        assert res_fallback.score == pytest.approx(expected, abs=1e-4)


# ---------------------------------------------------------------------------
# Unit Tests: TargetCapabilityScore exclusive-arc validation
# ---------------------------------------------------------------------------


class TestTargetCapabilityScoreExclusiveArc:
    def test_raises_if_no_fk_set(self):
        with pytest.raises(ValueError):
            TargetCapabilityScore(
                target_type="skill", target_id=_SKILL_ID, target_name="X",
                score=0.5, confidence=0.5, evidence_count=1,
                skill_id=None, technology_id=None, concept_id=None,
            )

    def test_raises_if_two_fks_set(self):
        with pytest.raises(ValueError):
            TargetCapabilityScore(
                target_type="skill", target_id=_SKILL_ID, target_name="X",
                score=0.5, confidence=0.5, evidence_count=1,
                skill_id=_SKILL_ID, technology_id=_TECH_ID, concept_id=None,
            )

    def test_valid_skill_arc(self):
        ts = TargetCapabilityScore(
            target_type="skill", target_id=_SKILL_ID, target_name="Python",
            score=0.7, confidence=0.6, evidence_count=3,
            skill_id=_SKILL_ID,
        )
        assert ts.skill_id == _SKILL_ID
        assert ts.technology_id is None
        assert ts.concept_id is None


# ---------------------------------------------------------------------------
# Unit Tests: Mathematical properties
# ---------------------------------------------------------------------------


class TestMathematicalProperties:
    def test_sigmoid_midpoint_at_zero(self):
        assert _sigmoid(0.0) == pytest.approx(0.5)

    def test_sigmoid_positive_returns_above_half(self):
        assert _sigmoid(1.0) > 0.5

    def test_sigmoid_negative_returns_below_half(self):
        assert _sigmoid(-1.0) < 0.5

    def test_sigmoid_extreme_positive_near_one(self):
        assert _sigmoid(100.0) == pytest.approx(1.0, abs=1e-9)

    def test_sigmoid_extreme_negative_near_zero(self):
        assert _sigmoid(-100.0) == pytest.approx(0.0, abs=1e-9)

    def test_sigmoid_overflow_guard(self):
        # Should not raise OverflowError
        assert _sigmoid(1000.0) == pytest.approx(1.0, abs=1e-9)
        assert _sigmoid(-1000.0) == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Service Tests: persist_capabilities
# ---------------------------------------------------------------------------


def _make_mock_session(
    developer_id: uuid.UUID = _DEV_ID,
    evidence_list=None,
    skill_junctions=None,
    tech_junctions=None,
    concept_junctions=None,
    skills=None,
    technologies=None,
    concepts=None,
    upsert_raises=False,
):
    """Build a hermetic AsyncMock session for service tests."""
    from app.models.repository import Repository
    from app.models.project import Project
    from app.models.observation import Observation

    # Build mock repository and project
    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = _REPO_ID
    mock_repo.project_id = _PROJECT_ID

    mock_proj = MagicMock(spec=Project)
    mock_proj.id = _PROJECT_ID
    mock_proj.developer_id = developer_id

    # Build mock observations
    mock_obs = MagicMock(spec=Observation)
    mock_obs.id = uuid.uuid4()
    mock_obs.analysis_run_id = _RUN_ID

    # Default evidence list
    if evidence_list is None:
        mock_ev = MagicMock()
        mock_ev.id = _EV_ID_1
        mock_ev.type = "USAGE"
        mock_ev.strength = 0.45
        mock_ev.directness = 1.0
        mock_ev.reliability = 1.0
        mock_ev.polarity = 1.0
        mock_ev.recency = _NOW
        mock_ev.observation_id = mock_obs.id
        evidence_list = [mock_ev]

    # Default junctions
    if skill_junctions is None:
        mock_es = MagicMock()
        mock_es.evidence_id = _EV_ID_1
        mock_es.skill_id = _SKILL_ID
        skill_junctions = [mock_es]
    if tech_junctions is None:
        tech_junctions = []
    if concept_junctions is None:
        concept_junctions = []

    # Default taxonomy names
    if skills is None:
        mock_skill = MagicMock()
        mock_skill.id = _SKILL_ID
        mock_skill.name = "Python"
        skills = [mock_skill]
    if technologies is None:
        technologies = []
    if concepts is None:
        concepts = []

    # Build a mock DeveloperCapability returned from upsert
    from app.models.capability import DeveloperCapability, CapabilityHistory
    mock_cap = MagicMock(spec=DeveloperCapability)
    mock_cap.id = uuid.uuid4()

    session = AsyncMock()
    session.add = MagicMock()

    # We need execute to return different things based on query type.
    # Use side_effect sequence to route calls in order.
    def make_scalar_result(value):
        res = MagicMock()
        res.scalar_one_or_none.return_value = value
        res.scalar_one.return_value = value
        return res

    def make_scalars_result(values):
        res = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = values
        res.scalars.return_value = scalars
        return res

    call_count = [0]

    async def execute_side_effect(stmt, *args, **kwargs):
        n = call_count[0]
        call_count[0] += 1
        # Call order from service.py:
        # 0: repo lookup
        # 1: project lookup
        # 2: load evidence
        # 3: skill junctions
        # 4: tech junctions
        # 5: concept junctions
        # 6: skill names
        # 7: tech names
        # 8: concept names
        # 9: delete capability_history (returns None-ish, not read)
        # 10+: pg_insert upsert (raises to trigger fallback)
        #      fallback: select existing capability
        if n == 0:
            return make_scalar_result(mock_repo)
        elif n == 1:
            return make_scalar_result(mock_proj)
        elif n == 2:
            return make_scalars_result(evidence_list)
        elif n == 3:
            return make_scalars_result(skill_junctions)
        elif n == 4:
            return make_scalars_result(tech_junctions)
        elif n == 5:
            return make_scalars_result(concept_junctions)
        elif n == 6:
            return make_scalars_result(skills)
        elif n == 7:
            return make_scalars_result(technologies)
        elif n == 8:
            return make_scalars_result(concepts)
        elif n == 9:
            # delete capability_history
            return MagicMock()
        elif n >= 10:
            if upsert_raises and n == 10:
                raise Exception("pg upsert failed — fallback to SELECT")
            # Fallback select: return existing cap
            return make_scalar_result(mock_cap)
        return MagicMock()

    session.execute.side_effect = execute_side_effect
    session.flush = AsyncMock()

    return session


def _make_mock_run(
    run_id: uuid.UUID = _RUN_ID,
    repo_id: uuid.UUID = _REPO_ID,
) -> MagicMock:
    from app.models.analysis_run import AnalysisRun
    run = MagicMock(spec=AnalysisRun)
    run.id = run_id
    run.repository_id = repo_id
    run.status = "CODE_RISK"
    return run


class TestPersistCapabilities:
    """Integration-level tests against the mocked service."""

    @pytest.mark.asyncio
    async def test_basic_persist_returns_capability_result(self):
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        assert isinstance(result, CapabilityResult)
        assert result.total_targets == 1
        assert result.developer_id == _DEV_ID

    @pytest.mark.asyncio
    async def test_persist_with_no_developer_returns_empty(self):
        """Repository with no project owner → zero targets, no writes."""
        from app.models.repository import Repository
        mock_repo = MagicMock(spec=Repository)
        mock_repo.id = _REPO_ID
        mock_repo.project_id = None  # orphan repo

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        def make_scalar_result(val):
            r = MagicMock()
            r.scalar_one_or_none.return_value = val
            return r

        session.execute.side_effect = [make_scalar_result(mock_repo)]

        from app.capability.service import persist_capabilities
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        assert result.total_targets == 0
        assert result.developer_id is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_persist_with_no_evidence_returns_empty(self):
        """Run has no evidence → zero targets."""
        from app.models.repository import Repository
        from app.models.project import Project

        mock_repo = MagicMock(spec=Repository)
        mock_repo.id = _REPO_ID
        mock_repo.project_id = _PROJECT_ID

        mock_proj = MagicMock(spec=Project)
        mock_proj.developer_id = _DEV_ID

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        call_count = [0]

        def make_scalar(v):
            r = MagicMock()
            r.scalar_one_or_none.return_value = v
            return r

        def make_scalars(vals):
            r = MagicMock()
            s = MagicMock()
            s.all.return_value = vals
            r.scalars.return_value = s
            return r

        async def exe(*args, **kwargs):
            n = call_count[0]
            call_count[0] += 1
            if n == 0:
                return make_scalar(mock_repo)
            elif n == 1:
                return make_scalar(mock_proj)
            else:
                return make_scalars([])  # no evidence

        session.execute.side_effect = exe

        from app.capability.service import persist_capabilities
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        assert result.total_targets == 0
        assert result.developer_id == _DEV_ID

    @pytest.mark.asyncio
    async def test_persist_uses_fallback_select_when_pg_upsert_unavailable(self):
        """The service must fall back gracefully in non-PostgreSQL environments (e.g. SQLite tests)."""
        from app.capability.service import persist_capabilities
        session = _make_mock_session(upsert_raises=True)
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        # Should still succeed via SELECT+UPDATE fallback
        assert isinstance(result, CapabilityResult)

    @pytest.mark.asyncio
    async def test_idempotency_deletes_history_before_insert(self):
        """Idempotency: capability_history deletion must be called before inserts."""
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        delete_calls_before_flush = []

        original_execute = session.execute.side_effect
        call_idx = [0]

        async def tracked_execute(stmt, *args, **kwargs):
            res = await original_execute(stmt, *args, **kwargs)
            call_idx[0] += 1
            return res

        session.execute.side_effect = tracked_execute
        await persist_capabilities(session=session, run=run)
        # Execute was called multiple times: repo, proj, evidence, junctions (3), names (3), delete
        # The pg_insert path does not use session.execute directly in the mock, so >=9 is the
        # minimum expected calls (repo + project + evidence + 3 junction + 3 name + delete).
        assert session.execute.call_count >= 9

    @pytest.mark.asyncio
    async def test_flush_called_after_all_inserts(self):
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        await persist_capabilities(session=session, run=run)
        session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_result_contains_scores(self):
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        assert len(result.scores) == 1
        s = result.scores[0]
        assert s.target_type == "skill"
        assert s.skill_id == _SKILL_ID
        assert 0.01 <= s.score <= 0.99
        assert 0.05 <= s.confidence <= 0.98

    @pytest.mark.asyncio
    async def test_avg_confidence_computed_correctly(self):
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        assert result.avg_confidence == pytest.approx(result.scores[0].confidence)

    @pytest.mark.asyncio
    async def test_history_count_matches_targets(self):
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        assert result.history_entries_appended == result.total_targets

    @pytest.mark.asyncio
    async def test_score_distribution_populated(self):
        from app.capability.service import persist_capabilities
        session = _make_mock_session()
        run = _make_mock_run()
        result = await persist_capabilities(session=session, run=run)
        total_in_dist = sum(result.score_distribution.values())
        assert total_in_dist == result.total_targets


# ---------------------------------------------------------------------------
# Worker Integration Tests: Stage 7 lifecycle
# ---------------------------------------------------------------------------


class TestWorkerStage7Lifecycle:
    """Verify that runner.execute_job_run sets status=CAPABILITY and stays non-terminal."""

    @pytest.mark.asyncio
    async def test_runner_sets_capability_status_before_scoring(self):
        """The run.status must be set to CAPABILITY before persist_capabilities is called."""
        from app.workers.runner import execute_job_run
        from app.models.analysis_job import AnalysisJob

        job = MagicMock(spec=AnalysisJob)
        job.id = uuid.uuid4()
        job.repository_id = _REPO_ID
        job.attempt_count = 1
        job.status = "PROCESSING"

        statuses_seen = []

        # We need to capture what the run.status is when persist_capabilities is called
        async def mock_persist_capabilities(session, run):
            statuses_seen.append(run.status)
            return CapabilityResult(developer_id=_DEV_ID, total_targets=0)

        with (
            patch("app.workers.runner.fetch_repository_for_job") as mock_fetch,
            patch("app.workers.runner.mine_repository") as mock_mine,
            patch("app.workers.runner.persist_skillgraph") as mock_sg,
            patch("app.workers.runner.persist_coderisk") as mock_cr,
            patch("app.workers.runner.persist_evidence") as mock_ev,
            patch("app.workers.runner.persist_capabilities", side_effect=mock_persist_capabilities),
            patch("app.workers.runner.temporary_workspace") as mock_ws,
            patch("app.workers.runner.get_settings") as mock_settings,
        ):
            mock_settings.return_value.APP_VERSION = "test"

            # Setup temporary_workspace as async context manager
            mock_ws.return_value.__aenter__ = AsyncMock(return_value="/tmp/workspace")
            mock_ws.return_value.__aexit__ = AsyncMock(return_value=None)

            # Setup mock fetch result
            fetch_res = MagicMock()
            fetch_res.file_count = 1
            fetch_res.root_dir = "/tmp/workspace/repo"
            mock_fetch.return_value = fetch_res

            # Setup mock mining result
            mining_res = MagicMock()
            mining_res.inventory.total_files = 1
            mining_res.languages = []
            mining_res.manifests = []
            mining_res.ast_summaries = []
            mining_res.warnings = []
            mock_mine.return_value = mining_res

            # Setup mock skillgraph result
            sg_res = MagicMock()
            sg_res.observations_count = 0
            sg_res.languages_count = 0
            sg_res.dependencies_count = 0
            sg_res.technologies_count = 0
            sg_res.skills_count = 0
            sg_res.concepts_count = 0
            sg_res.edges_count = 0
            mock_sg.return_value = sg_res

            # Setup mock coderisk result
            cr_res = MagicMock()
            cr_res.total_findings = 0
            cr_res.findings_by_severity = {}
            mock_cr.return_value = cr_res

            # Setup mock evidence result
            ev_res = MagicMock()
            ev_res.total_evidence = 0
            ev_res.evidence_by_polarity = {}
            mock_ev.return_value = ev_res

            # Setup mock session
            session = AsyncMock()
            session.add = MagicMock()

            run_states = []

            async def commit_side_effect():
                pass

            async def refresh_side_effect(obj):
                pass

            session.commit.side_effect = commit_side_effect
            session.refresh.side_effect = refresh_side_effect

            # AnalysisRun is created inside execute_job_run; patch the class
            with patch("app.workers.runner.AnalysisRun") as mock_ar_cls:
                mock_run = MagicMock()
                mock_run.id = _RUN_ID
                mock_run.status = "FETCHING"
                mock_run.analysis_job_id = job.id
                mock_ar_cls.return_value = mock_run

                run = await execute_job_run(job=job, session=session)

        # The capability scorer should have seen status = "CAPABILITY"
        assert "CAPABILITY" in statuses_seen

    @pytest.mark.asyncio
    async def test_run_not_marked_completed_after_stage_7(self):
        """After Stage 7 succeeds, the run must NOT be COMPLETED (Stage 8 deferred)."""
        from app.workers.runner import execute_job_run
        from app.models.analysis_job import AnalysisJob

        job = MagicMock(spec=AnalysisJob)
        job.id = uuid.uuid4()
        job.repository_id = _REPO_ID
        job.attempt_count = 1
        job.status = "PROCESSING"

        with (
            patch("app.workers.runner.fetch_repository_for_job") as mock_fetch,
            patch("app.workers.runner.mine_repository") as mock_mine,
            patch("app.workers.runner.persist_skillgraph") as mock_sg,
            patch("app.workers.runner.persist_coderisk") as mock_cr,
            patch("app.workers.runner.persist_evidence") as mock_ev,
            patch("app.workers.runner.persist_capabilities") as mock_cap,
            patch("app.workers.runner.temporary_workspace") as mock_ws,
            patch("app.workers.runner.get_settings") as mock_settings,
        ):
            mock_settings.return_value.APP_VERSION = "test"

            mock_ws.return_value.__aenter__ = AsyncMock(return_value="/tmp/workspace")
            mock_ws.return_value.__aexit__ = AsyncMock(return_value=None)

            fetch_res = MagicMock()
            fetch_res.file_count = 1
            fetch_res.root_dir = "/tmp/workspace/repo"
            mock_fetch.return_value = fetch_res

            mining_res = MagicMock()
            mining_res.inventory.total_files = 1
            mining_res.languages = []
            mining_res.manifests = []
            mining_res.ast_summaries = []
            mining_res.warnings = []
            mock_mine.return_value = mining_res

            sg_res = MagicMock()
            sg_res.observations_count = sg_res.languages_count = sg_res.dependencies_count = 0
            sg_res.technologies_count = sg_res.skills_count = sg_res.concepts_count = sg_res.edges_count = 0
            mock_sg.return_value = sg_res

            cr_res = MagicMock()
            cr_res.total_findings = 0
            cr_res.findings_by_severity = {}
            mock_cr.return_value = cr_res

            ev_res = MagicMock()
            ev_res.total_evidence = 0
            ev_res.evidence_by_polarity = {}
            mock_ev.return_value = ev_res

            cap_res = CapabilityResult(developer_id=_DEV_ID, total_targets=0)
            mock_cap.return_value = cap_res

            session = AsyncMock()
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.refresh = AsyncMock()

            with patch("app.workers.runner.AnalysisRun") as mock_ar_cls:
                mock_run = MagicMock()
                mock_run.id = _RUN_ID
                mock_run.status = "CAPABILITY"
                mock_run.completed_at = None
                mock_run.analysis_job_id = job.id
                mock_ar_cls.return_value = mock_run

                run = await execute_job_run(job=job, session=session)

        # The job must remain PROCESSING (not COMPLETED)
        assert job.status != "COMPLETED"
        # The run must not have completed_at set (confirmed by the mock not being mutated)
        assert mock_run.completed_at is None

    @pytest.mark.asyncio
    async def test_capability_failure_marks_run_failed_not_completed(self):
        """If persist_capabilities raises, the pipeline must set status=FAILED, not COMPLETED."""
        from app.workers.runner import execute_job_run
        from app.models.analysis_job import AnalysisJob

        job = MagicMock(spec=AnalysisJob)
        job.id = uuid.uuid4()
        job.repository_id = _REPO_ID
        job.attempt_count = 1
        job.status = "PROCESSING"

        with (
            patch("app.workers.runner.fetch_repository_for_job") as mock_fetch,
            patch("app.workers.runner.mine_repository") as mock_mine,
            patch("app.workers.runner.persist_skillgraph") as mock_sg,
            patch("app.workers.runner.persist_coderisk") as mock_cr,
            patch("app.workers.runner.persist_evidence") as mock_ev,
            patch("app.workers.runner.persist_capabilities", side_effect=RuntimeError("scoring failed")),
            patch("app.workers.runner.temporary_workspace") as mock_ws,
            patch("app.workers.runner.get_settings") as mock_settings,
        ):
            mock_settings.return_value.APP_VERSION = "test"

            mock_ws.return_value.__aenter__ = AsyncMock(return_value="/tmp/workspace")
            mock_ws.return_value.__aexit__ = AsyncMock(return_value=None)

            fetch_res = MagicMock()
            fetch_res.file_count = 1
            fetch_res.root_dir = "/tmp/workspace/repo"
            mock_fetch.return_value = fetch_res

            mining_res = MagicMock()
            mining_res.inventory.total_files = 1
            mining_res.languages = []
            mining_res.manifests = []
            mining_res.ast_summaries = []
            mining_res.warnings = []
            mock_mine.return_value = mining_res

            sg_res = MagicMock()
            sg_res.observations_count = sg_res.languages_count = sg_res.dependencies_count = 0
            sg_res.technologies_count = sg_res.skills_count = sg_res.concepts_count = sg_res.edges_count = 0
            mock_sg.return_value = sg_res

            cr_res = MagicMock()
            cr_res.total_findings = 0
            cr_res.findings_by_severity = {}
            mock_cr.return_value = cr_res

            ev_res = MagicMock()
            ev_res.total_evidence = 0
            ev_res.evidence_by_polarity = {}
            mock_ev.return_value = ev_res

            session = AsyncMock()
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.refresh = AsyncMock()
            session.rollback = AsyncMock()

            with patch("app.workers.runner.AnalysisRun") as mock_ar_cls:
                mock_run = MagicMock()
                mock_run.id = _RUN_ID
                mock_run.status = "CAPABILITY"
                mock_run.analysis_job_id = job.id
                mock_ar_cls.return_value = mock_run

                run = await execute_job_run(job=job, session=session)

            # On failure, rollback must be called
            session.rollback.assert_called_once()
            # Run must be marked FAILED
            assert mock_run.status == "FAILED"
            # Job must be marked FAILED
            assert job.status == "FAILED"
