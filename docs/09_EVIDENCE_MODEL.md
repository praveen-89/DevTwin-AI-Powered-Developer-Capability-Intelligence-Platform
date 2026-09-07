# 09. Evidence Model

## Overview
The foundational rule of DevTwin is: **Every capability estimate must be supported by evidence.**

## Observation vs. Evidence
The system distinguishes between an raw observation and contextualized evidence:
-   **Observation**: A directly detected fact (e.g., "A file named Dockerfile exists in Repo A").
-   **Evidence**: A contextualized interpretation of an observation related to a capability (e.g., "Developer demonstrates usage of Docker technology").

*Pipeline:*
`RAW EVIDENCE -> OBSERVATION -> FEATURE -> CAPABILITY ESTIMATE -> CONFIDENCE -> EXPLANATION`

## Evidence Hierarchy
Not all evidence is equal. The system weights evidence based on its depth and context:
1.  **Mention (Weakest)**: A skill is listed in a README or a bio.
2.  **Usage (Stronger)**: A technology is present in a `package.json` or imported in a file.
3.  **Applied Engineering (Strong)**: Complex usage, custom configurations, architectural patterns (e.g., writing a custom Webpack config, not just running `create-react-app`).
4.  **Demonstrated Outcome (Strongest)**: The code runs in production, passes CI/CD, receives positive peer reviews, or resolves complex issues.

## Evidence Object Structure
```json
{
    "id": "uuid",
    "source": "REPOSITORY_MINING", // e.g., GitHub profile, source code, commits, issues
    "type": "APPLIED_ENGINEERING",
    "strength": 0.8, // Base weight based on hierarchy
    "directness": 0.9, // How directly it relates to the target capability
    "reliability": 0.95, // Confidence in the source of the observation
    "recency": "timestamp", // Used for temporal weighting
    "corroboration": ["evidence_id_1", "evidence_id_2"], // Links to supporting evidence
    "polarity": 1.0, // Positive (demonstrates capability) or Negative (CodeRisk finding)
    "target": "technology_docker_id"
}
```

## Provenance
Evidence must maintain provenance wherever possible. A capability score shown on the dashboard must be clickable, tracing back through the `EvidenceItem` to the original `Observation` and ideally the specific file or commit in the repository.
