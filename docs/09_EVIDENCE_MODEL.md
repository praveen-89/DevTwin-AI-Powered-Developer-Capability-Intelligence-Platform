# 9. Evidence Model

## Overview
The Evidence Model sits between raw Observations and the final Capability Score. It translates immutable facts into contextualized signals.

## Risk as Evidence
**Risk is evidence about engineering behavior, not direct proof of developer incompetence.**
When a `risk_finding` is attributed to a developer, it acts as a negative observation. The Evidence Engine interprets it as negative polarity evidence, which slightly pulls down the capability score and affects confidence, depending on the severity and recency.

## The Evidence Hierarchy
1.  **MENTION** (Lowest Strength): E.g., The developer mentions "React" in a README.
2.  **USAGE**: E.g., The developer imports `React` in a file.
3.  **APPLIED_ENGINEERING**: E.g., The developer implements a complex custom React Hook.
4.  **DEMONSTRATED_OUTCOME** (Highest Strength): E.g., The developer's PR fixing a critical React rendering bug is merged.

## Attributes
*   **Type**: MENTION | USAGE | APPLIED_ENGINEERING | DEMONSTRATED_OUTCOME
*   **Strength** (0-1): The base weight of the evidence type.
*   **Directness** (0-1): How directly the evidence applies to the target concept.
*   **Reliability** (0-1): Trust in the source tool extracting the observation.
*   **Recency** (0-1): Decays over time (e.g., code written 3 years ago is less relevant today).
*   **Polarity** (-1 to 1): Positive for good engineering, negative for risks/anti-patterns.
