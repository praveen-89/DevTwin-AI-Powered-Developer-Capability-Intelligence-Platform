"""
DevTwin CodeRisk — Rule Definitions & Constants

Defines grounded, reproducible static analysis rules adhering strictly
to `001_initial_schema.sql` CHECK constraints for category and severity.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    title: str
    category: str
    severity: str
    confidence: float
    description: str


RULES: Dict[str, RuleDefinition] = {
    # -----------------------------------------------------------------------
    # SECURITY
    # -----------------------------------------------------------------------
    "SEC-001": RuleDefinition(
        rule_id="SEC-001",
        title="Hardcoded Secret or Credential Literal",
        category="SECURITY",
        severity="HIGH",
        confidence=0.85,
        description="Potential hardcoded secret or API key assignment detected in source code or configuration.",
    ),
    "SEC-002": RuleDefinition(
        rule_id="SEC-002",
        title="Arbitrary Code Execution Construct",
        category="SECURITY",
        severity="HIGH",
        confidence=0.95,
        description="Usage of dynamic evaluation or system execution constructs (eval, exec, os.system, subprocess with shell=True) detected.",
    ),
    "SEC-003": RuleDefinition(
        rule_id="SEC-003",
        title="Insecure Object Deserialization",
        category="SECURITY",
        severity="MEDIUM",
        confidence=0.90,
        description="Usage of unsafe deserialization constructs (pickle.load / pickle.loads) detected.",
    ),

    # -----------------------------------------------------------------------
    # RELIABILITY
    # -----------------------------------------------------------------------
    "REL-001": RuleDefinition(
        rule_id="REL-001",
        title="Bare Except Clause",
        category="RELIABILITY",
        severity="MEDIUM",
        confidence=0.95,
        description="Bare 'except:' clause catches BaseException, potentially masking SystemExit or KeyboardInterrupt.",
    ),
    "REL-002": RuleDefinition(
        rule_id="REL-002",
        title="Silent Exception Swallowing",
        category="RELIABILITY",
        severity="MEDIUM",
        confidence=0.90,
        description="Empty exception handler ('except ...: pass') silently suppresses errors without logging or handling.",
    ),

    # -----------------------------------------------------------------------
    # MAINTAINABILITY
    # -----------------------------------------------------------------------
    "MAINT-001": RuleDefinition(
        rule_id="MAINT-001",
        title="Excessive Function Parameter Count",
        category="MAINTAINABILITY",
        severity="LOW",
        confidence=0.90,
        description="Function defines more than 7 parameters, suggesting a candidate for refactoring into a parameter object.",
    ),
    "MAINT-002": RuleDefinition(
        rule_id="MAINT-002",
        title="Syntax Parse Failure in Source File",
        category="MAINTAINABILITY",
        severity="LOW",
        confidence=1.0,
        description="Source file contains invalid syntax or could not be parsed by AST, preventing static verification.",
    ),

    # -----------------------------------------------------------------------
    # TESTING
    # -----------------------------------------------------------------------
    "TEST-001": RuleDefinition(
        rule_id="TEST-001",
        title="Missing Test Suite",
        category="TESTING",
        severity="LOW",
        confidence=0.75,
        description="Repository contains significant source code but lacks test directories, test manifests, or test files.",
    ),
}
