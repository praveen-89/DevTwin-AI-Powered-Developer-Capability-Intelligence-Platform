# 8. CodeRisk Model

## Core Principle: Risk ≠ Competence
A critical distinction in DevTwin is that **CodeRisk is an engineering risk signal, not an automatic proof of incompetence**. 

If a CodeRisk heuristic triggers (e.g., "Hardcoded AWS Secret found"):
1. It is logged as a `risk_findings` record.
2. It generates a negative `evidence` record (e.g., negative polarity for the "Security" skill).
3. The Capability Engine weighs this negative evidence against other positive evidence.

**We do NOT hard-reset a capability score to zero because of a risk finding.** Developers make mistakes; our goal is to measure their overall demonstrated capability and provide learning interventions, not to build a punitive blame-machine.

## Attribution Rules
DevTwin must not create misleading developer blame. A repository-wide risk must not be automatically blamed on all contributors.
*   **Commit-level Risk**: If a CodeRisk rule flags a specific line of code, and Git history proves Developer A authored that exact line, the risk is attributed to Developer A.
*   **Repository-level Risk**: If a risk applies to the whole repository (e.g., "Missing CI/CD pipeline"), it is logged against the repository but *not* attributed as negative evidence to an individual developer unless they are the sole owner.

## Categories
*   **SECURITY**: Vulnerabilities, hardcoded secrets.
*   **RELIABILITY**: Lack of error handling, race conditions.
*   **TESTING**: Missing tests, low coverage.
*   **MAINTAINABILITY**: High cyclomatic complexity, duplicated code.
*   **DEPENDENCY**: Outdated or vulnerable dependencies.
*   **ARCHITECTURE**: Architectural anti-patterns.

## Risk State Mapping
```text
CodeRisk
   ↓
Engineering Risk Signal
   ↓
Observation
   ↓
Evidence
   ↓
Capability Model
```
