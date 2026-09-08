# 06. Capability Model

*Source of Truth Context: Domain-level specification of capability semantics.*

## Core Distinction: Skill ≠ Capability
**A Skill is a named competency. A Capability is a developer-specific, evidence-backed, scored measure of how well they demonstrate that competency.**

*   **Skill** (or Technology, Concept): A specific tool, language, or concept in the SkillGraph taxonomy (e.g., "Python", "Docker", "REST API"). Shared globally.
*   **Capability**: The demonstrated ability of a *specific developer* to effectively utilize a skill, inferred from verifiable repository evidence. Developer-specific.

## Capability Model Principle: Risk ≠ Competence
**Risk signals are evidence about engineering behavior, not direct proof of incompetence.** When a CodeRisk finding is attributable to a developer, it acts as a negative evidence signal in the Capability Engine — its weight depends on severity, directness, and recency. It does not unilaterally override other positive evidence.

## Capability State Object
A capability state for a specific developer and target contains:
- `score` (0.0 - 1.0): The inferred level of demonstrated capability.
- `confidence` (0.0 - 1.0): The system's certainty in the score (based on evidence volume, diversity, and consistency). **Score and Confidence are separate dimensions.**
- `evidence_ids`: A linked list of `evidence` records supporting the score.
- `scoring_version`: The model version used to produce this score.
- `historical_state`: Stored immutably in `capability_history`.

## Capability Evidence States
The UI must clearly distinguish between:
*   **Observed**: Evidence directly extracted from the developer's code.
*   **Inferred**: Score derived from related skills in the SkillGraph traversal.
*   **Uncertain**: Insufficient evidence to make a confident claim.

## Conceptual Flow
`Knowledge Evidence + Application Evidence + Engineering Behavior Evidence + Risk Evidence (negative) → Aggregated Weighted Score → Capability + Confidence`
