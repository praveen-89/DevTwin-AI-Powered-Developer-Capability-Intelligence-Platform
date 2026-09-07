# 16. Evaluation Plan

## Objective
The evaluation plan defines how DevTwin's Minor MVP will be assessed to prove the viability of the "Evidence-Backed Capability Paradigm."

## Evaluation Metrics

### 1. System Reliability & Performance
-   **Pipeline Throughput**: Time taken to fully process a standard repository (e.g., < 2 minutes for a medium-sized React app).
-   **Extraction Accuracy**: Percentage of correctly identified dependencies and architectural patterns compared to manual inspection.

### 2. Evidence Quality
-   **Provenance Traceability**: 100% of generated capability scores must be traceable back to at least one raw observation.
-   **False Positive Rate in CodeRisk**: Manual review of a sample of generated CodeRisk signals to ensure heuristics are not overly aggressive.

### 3. Capability Model Validity
-   **Heuristic Validation**: Do developers with known, demonstrated expertise in a technology receive higher capability scores (and confidence intervals) than novices within the system's test data?
-   **Explainability Rating**: User testing of the dashboard: Can a user clearly understand *why* the system assigned a specific score by using the Evidence Explorer?

## Evaluation Methodology
The evaluation will be conducted using a curated dataset of open-source repositories representing various skill levels (e.g., student projects, established open-source libraries).

*(Note: DevTwin does not rely on fabricated research claims or benchmarks. Evaluation will be based on verifiable test data processed by the implemented pipeline).*
