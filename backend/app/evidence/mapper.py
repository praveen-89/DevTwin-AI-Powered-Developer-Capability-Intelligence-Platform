"""
DevTwin Evidence — Deterministic Mapper
Transforms raw observations into contextualized evidence records with
strength, directness, reliability, polarity, and taxonomy links.
"""

import logging
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Dict, List, Optional, Set, Tuple
import uuid

from app.coderisk.rules import RULES
from app.evidence.models import EvidenceItemData
from app.models.observation import Observation
from app.skillgraph.taxonomy import (
    resolve_dependency_taxonomy,
    resolve_language_taxonomy,
)

logger = logging.getLogger(__name__)

# Map file extensions to language names
_EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
}


def _infer_language_technology(file_path: Optional[str]) -> List[str]:
    """Infers canonical language technology name from a file extension."""
    if not file_path:
        return []
    ext = PurePath(file_path).suffix.lower()
    lang = _EXTENSION_TO_LANGUAGE.get(ext)
    if lang:
        tax = resolve_language_taxonomy(lang)
        return [tax.technology_name if tax else lang]
    return []


def map_observation_to_evidence(obs: Observation) -> Optional[EvidenceItemData]:
    """
    Deterministically transforms a single Observation into an EvidenceItemData record.
    Returns None if the observation is purely diagnostic (e.g. MINING_WARNING).
    """
    ref = obs.source_reference or {}
    observed_time = obs.observed_at or datetime.now(timezone.utc)
    obs_confidence = float(obs.confidence) if obs.confidence is not None else 1.0

    # -----------------------------------------------------------------------
    # 1. DEPENDENCY_FOUND -> MENTION
    # -----------------------------------------------------------------------
    if obs.type == "DEPENDENCY_FOUND":
        package_name = ref.get("package", "").strip()
        if not package_name:
            return None

        tax = resolve_dependency_taxonomy(package_name)
        if tax:
            tech_name = tax.technology_name
            skills = [s[0] for s in tax.skills]
            concepts = list(tax.concepts)
        else:
            tech_name = package_name.lower()
            skills = []
            concepts = []

        return EvidenceItemData(
            observation_id=obs.id,
            type="MENTION",
            strength=0.20,
            directness=0.80,
            reliability=min(obs_confidence, 0.90),
            polarity=1.0,
            recency=observed_time,
            skills=skills,
            technologies=[tech_name],
            concepts=concepts,
            source_tool=obs.source_tool,
            source_reference=ref,
        )

    # -----------------------------------------------------------------------
    # 2. MODULE_IMPORTED -> USAGE
    # -----------------------------------------------------------------------
    if obs.type == "MODULE_IMPORTED":
        module_name = ref.get("module", "").strip()
        if not module_name:
            return None

        base_module = module_name.split(".")[0]
        tax = resolve_dependency_taxonomy(module_name) or resolve_dependency_taxonomy(base_module)
        if not tax:
            # Check if imported module is a language standard library or language itself
            lang_tax = resolve_language_taxonomy(base_module)
            if lang_tax:
                tech_name = lang_tax.technology_name
                skills = [s[0] for s in lang_tax.skills]
                concepts = list(lang_tax.concepts)
            else:
                tech_name = base_module.lower()
                skills = []
                concepts = []
        else:
            tech_name = tax.technology_name
            skills = [s[0] for s in tax.skills]
            concepts = list(tax.concepts)

        return EvidenceItemData(
            observation_id=obs.id,
            type="USAGE",
            strength=0.50,
            directness=1.0,
            reliability=min(obs_confidence, 0.95),
            polarity=1.0,
            recency=observed_time,
            skills=skills,
            technologies=[tech_name],
            concepts=concepts,
            source_tool=obs.source_tool,
            source_reference=ref,
        )

    # -----------------------------------------------------------------------
    # 3. LANGUAGE_DETECTED -> USAGE (if >= 5% or >= 2 files) or MENTION
    # -----------------------------------------------------------------------
    if obs.type == "LANGUAGE_DETECTED":
        lang = ref.get("language", "").strip()
        if not lang:
            return None

        percentage = float(ref.get("percentage", 0.0))
        files = int(ref.get("files", 0))

        tax = resolve_language_taxonomy(lang)
        if tax:
            tech_name = tax.technology_name
            skills = [s[0] for s in tax.skills]
            concepts = list(tax.concepts)
        else:
            tech_name = lang
            skills = []
            concepts = []

        is_substantive = percentage >= 5.0 or files >= 2
        evidence_type = "USAGE" if is_substantive else "MENTION"
        strength = 0.40 if is_substantive else 0.20

        return EvidenceItemData(
            observation_id=obs.id,
            type=evidence_type,
            strength=strength,
            directness=1.0,
            reliability=min(obs_confidence, 0.85),
            polarity=1.0,
            recency=observed_time,
            skills=skills,
            technologies=[tech_name],
            concepts=concepts,
            source_tool=obs.source_tool,
            source_reference=ref,
        )

    # -----------------------------------------------------------------------
    # 4. CLASS_DEFINED -> APPLIED_ENGINEERING
    # -----------------------------------------------------------------------
    if obs.type == "CLASS_DEFINED":
        file_path = ref.get("file")
        techs = _infer_language_technology(file_path)

        return EvidenceItemData(
            observation_id=obs.id,
            type="APPLIED_ENGINEERING",
            strength=0.80,
            directness=0.90,
            reliability=min(obs_confidence, 0.95),
            polarity=1.0,
            recency=observed_time,
            skills=[],
            technologies=techs,
            concepts=["Object-Oriented Programming"],
            source_tool=obs.source_tool,
            source_reference=ref,
        )

    # -----------------------------------------------------------------------
    # 5. FUNCTION_DEFINED -> APPLIED_ENGINEERING (async/docstring) or USAGE
    # -----------------------------------------------------------------------
    if obs.type == "FUNCTION_DEFINED":
        file_path = ref.get("file")
        techs = _infer_language_technology(file_path)

        is_async = bool(ref.get("is_async", False))
        has_docstring = bool(ref.get("has_docstring", False))

        concepts: List[str] = []
        if is_async:
            concepts.append("Asynchronous Programming")
        if has_docstring:
            concepts.append("Code Documentation")

        if is_async:
            ev_type = "APPLIED_ENGINEERING"
            strength = 0.70
            directness = 0.90
        elif has_docstring:
            ev_type = "APPLIED_ENGINEERING"
            strength = 0.60
            directness = 0.85
        else:
            ev_type = "USAGE"
            strength = 0.40
            directness = 0.80

        return EvidenceItemData(
            observation_id=obs.id,
            type=ev_type,
            strength=strength,
            directness=directness,
            reliability=min(obs_confidence, 0.95),
            polarity=1.0,
            recency=observed_time,
            skills=[],
            technologies=techs,
            concepts=concepts,
            source_tool=obs.source_tool,
            source_reference=ref,
        )

    # -----------------------------------------------------------------------
    # 6. RISK_OBSERVED -> Negative Polarity Evidence
    # -----------------------------------------------------------------------
    if obs.type == "RISK_OBSERVED":
        rule_id = ref.get("rule_id", "")
        rule = RULES.get(rule_id)

        category = rule.category if rule else "RELIABILITY"
        severity = rule.severity if rule else "MEDIUM"
        file_path = ref.get("file_path")

        # Map polarity (negative) and strength by severity
        if severity == "CRITICAL":
            polarity = -1.0
            strength = 0.80
        elif severity == "HIGH":
            polarity = -0.8
            strength = 0.60
        elif severity == "MEDIUM":
            polarity = -0.5
            strength = 0.40
        else:  # LOW
            polarity = -0.2
            strength = 0.20

        # Type: construct call vs structural pattern
        if rule_id in ("SEC-001", "SEC-002", "SEC-003", "REL-001"):
            ev_type = "USAGE"
        else:
            ev_type = "APPLIED_ENGINEERING"

        concepts = []
        skills = []
        if category == "SECURITY":
            concepts.append("Secure Coding")
        elif category == "RELIABILITY":
            concepts.append("Error Handling")
        elif category == "TESTING":
            concepts.append("Automated Testing")
            skills.append("Testing & Quality Assurance")
        elif category == "MAINTAINABILITY":
            concepts.append("Code Maintainability")
        elif category == "ARCHITECTURE":
            concepts.append("Software Architecture")
        elif category == "DEPENDENCY":
            concepts.append("Dependency Management")

        techs = _infer_language_technology(file_path)

        return EvidenceItemData(
            observation_id=obs.id,
            type=ev_type,
            strength=strength,
            directness=0.90,
            reliability=min(obs_confidence, 0.95),
            polarity=polarity,
            recency=observed_time,
            skills=skills,
            technologies=techs,
            concepts=concepts,
            source_tool=obs.source_tool,
            source_reference=ref,
        )

    # -----------------------------------------------------------------------
    # 7. Diagnostic Observations (MINING_WARNING, SYNTAX_ERROR_OBSERVED)
    # -----------------------------------------------------------------------
    # Per ADR-003 and DOMAIN_MODEL: Observation ≠ Evidence.
    # Diagnostic observations remain in the observations table but do not generate capability evidence.
    return None


def map_observations_to_evidence(observations: List[Observation]) -> List[EvidenceItemData]:
    """
    Transforms a sequence of Observations into grounded EvidenceItemData items.
    Maintains deterministic ordering.
    """
    evidence_items: List[EvidenceItemData] = []
    for obs in observations:
        item = map_observation_to_evidence(obs)
        if item is not None:
            evidence_items.append(item)

    # Deterministic sort by observation_id and type
    evidence_items.sort(key=lambda x: (str(x.observation_id), x.type))
    return evidence_items
