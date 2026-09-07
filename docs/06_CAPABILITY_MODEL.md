# 06. Capability Model

## Skill vs. Capability
The fundamental premise of DevTwin's capability model is the explicit distinction between Skill and Capability.

*   **Skill (or Technology):** A specific tool, language, or concept (e.g., "Python", "Docker", "REST API").
*   **Capability:** The demonstrated ability to effectively utilize a skill in real software projects.

## Components of a Capability State
A developer's capability is not a single number, but a multi-dimensional state. The model considers the following dimensions:

1.  **Technical Knowledge:** Evidence that the developer understands the syntax, APIs, and basic concepts of a technology.
2.  **Practical Application:** Evidence of the technology being used to build functional software components.
3.  **Engineering Capability:** The quality, safety, and maintainability of the application (informed by CodeRisk).
4.  **Project Experience:** The context in which the technology was used (e.g., a simple script vs. a production-grade microservice).
5.  **Engineering Behavior:** Consistent patterns of work, such as writing tests, managing dependencies, and structuring code.

## The Capability State Object
A capability state for a specific developer and skill contains:
- `capability_score`: The inferred level of capability (e.g., 0.0 to 1.0).
- `confidence`: The system's confidence in the score (based on evidence volume and diversity).
- `evidence`: A linked list of `EvidenceItem` objects supporting the score.
- `recency`: When the capability was last demonstrated.
- `trend`: The trajectory of the capability over time (e.g., improving, decaying).
- `historical_state`: A timeline of past capability states.

## Conceptual Flow
The process of determining a capability state:
`Knowledge + Practical Application + Engineering Behavior + Project Experience + Consistency/Recency + Outcomes -> Developer Capability`
