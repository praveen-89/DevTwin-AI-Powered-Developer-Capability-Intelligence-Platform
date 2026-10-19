"""
DevTwin CodeRisk — Dataclasses & Contracts
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CodeRiskFinding:
    """
    Structured CodeRisk finding adhering strictly to the schema constraints of `risk_findings`.
    """
    rule_id: str
    category: str  # 'SECURITY', 'RELIABILITY', 'TESTING', 'MAINTAINABILITY', 'DEPENDENCY', 'ARCHITECTURE'
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    confidence: float  # 0.0 to 1.0
    title: str
    explanation: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    evidence_snippet: Optional[str] = None


@dataclass(frozen=True)
class CodeRiskResult:
    """
    Summary of findings discovered and persisted by the CodeRisk engine for an analysis run.
    """
    schema_version: str
    analyzer_version: str
    total_findings: int
    findings_by_category: Dict[str, int]
    findings_by_severity: Dict[str, int]
    findings: List[CodeRiskFinding] = field(default_factory=list)
    completed_at: str = ""
