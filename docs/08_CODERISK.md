# 08. CodeRisk

## Overview
CodeRisk is the engineering-risk intelligence layer. It analyzes repository, code, and change signals to generate explainable risk signals. Importantly, CodeRisk does not directly penalize a developer's competence; instead, it generates evidence that feeds into the capability model regarding engineering behavior.

`CodeRisk -> Risk Signal -> Evidence -> Capability Model`

## Risk Categories (Minor Project)
The initial CodeRisk engine focuses on the following categories:

1.  **Security**: Hardcoded secrets, unsafe input handling, common injection patterns, weak authentication/authorization patterns.
2.  **Testing**: Absence of tests, missing critical test coverage, lack of CI testing configurations.
3.  **Maintainability**: High cyclomatic complexity, large files/functions, code duplication, dead code, deep nesting.
4.  **Dependency**: Vulnerable dependencies, outdated dependencies, unused/duplicate dependencies, unpinned versions.
5.  **Reliability**: Selected error handling issues, missing validation, missing fallback/retry patterns where relevant.
6.  **Architecture**: Circular dependencies, excessive coupling, basic layer violations, "god" modules, poor separation of concerns.

## Risk Structure
A detected risk is structured as a `RiskSignal`:

```json
{
    "id": "uuid",
    "repository_id": "uuid",
    "observation_id": "uuid",
    "category": "MAINTAINABILITY",
    "type": "HIGH_COMPLEXITY",
    "severity": "MEDIUM",
    "confidence": "HIGH",
    "location": "src/utils/parser.ts:45",
    "description": "Function parseData exceeds cyclomatic complexity threshold of 15 (actual: 22).",
    "evidence": "AST analysis snippet...",
    "detected_at": "timestamp"
}
```

## Severity vs. Confidence
A critical distinction in CodeRisk is the separation of severity and confidence.
-   **Severity**: The potential impact of the risk (LOW, MEDIUM, HIGH, CRITICAL).
-   **Confidence**: The system's certainty that the finding is accurate (LOW, MEDIUM, HIGH).

For example, a finding can be HIGH severity but LOW confidence (e.g., a heuristic guess at a potential SQL injection), or MEDIUM severity with HIGH confidence (e.g., a firmly detected unused dependency).

## Exclusions
The Minor MVP does **not** implement automatic developer blame (e.g., assigning a risk entirely to the author of a specific line without broader context), as this requires complex temporal commit analysis planned for later stages.
