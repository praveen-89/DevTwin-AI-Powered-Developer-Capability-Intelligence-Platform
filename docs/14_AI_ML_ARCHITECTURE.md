# 14. AI and ML Architecture

## Philosophy
**AI is an intelligence layer, NOT the entire product.** 
DevTwin rejects the approach of dumping repository data into an LLM to generate an opaque capability score. The system must remain explainable and grounded in evidence.

`Repository -> Structured Evidence Extraction -> Features -> Capability Model -> Capability Estimate -> LLM -> Human-readable explanation`

## Usage in the Minor MVP
For the Minor Project, AI/ML usage is strictly bounded:
-   **Semantic Mapping**: LLMs (via API) may be used to map obscure dependencies to known concepts in the SkillGraph (e.g., mapping a custom library to "Authentication").
-   **Explanation Generation**: Once the deterministic Capability Model calculates a score based on evidence weights, an LLM may be used to generate a natural-language summary explaining *why* the score is what it is, citing the specific evidence.
-   **Concept Extraction**: Extracting structural concepts from commit messages or PR descriptions.

## Exclusions (Minor MVP)
The following are explicitly excluded from the current phase:
-   LLM agents acting autonomously on code.
-   End-to-end neural networks predicting capability directly from raw code.
-   Reinforcement learning.

## Future ML Architecture (Major Roadmap)
Future versions will incorporate more advanced ML:
-   **Temporal Prediction**: Time-series models to predict capability decay or growth.
-   **Knowledge Tracing**: Bayesian Knowledge Tracing (BKT) or Deep Knowledge Tracing (DKT) applied to engineering tasks.
-   **Graph Learning**: Graph Neural Networks (GNNs) operating on the SkillGraph to infer unobserved capabilities based on topological similarity.
