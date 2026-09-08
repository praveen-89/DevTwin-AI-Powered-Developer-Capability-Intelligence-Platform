# 10. Scoring Model

*Source of Truth Context: Scoring methodology for the Capability Engine.*

## Design Philosophy
DevTwin explicitly **rejects** arbitrary fixed weights (e.g., Knowledge = 20%, Application = 30%). Capability is treated as a latent state inferred from heterogeneous evidence. The model must be interpretable, reproducible, and version-tracked.

**This model is NOT scientifically validated. It is a calibration starting point. The architecture ensures it can be tuned or replaced without breaking the system.**

## Evidence Weight Calculation
The weight of a single piece of evidence ($w_i$) is calculated dynamically:

$$w_i = S_i \times D_i \times R_i \times T_i \times P_i$$

Where:
-   **S (Strength)**: Based on evidence hierarchy (MENTION=0.2, USAGE=0.5, APPLIED\_ENGINEERING=0.8, DEMONSTRATED\_OUTCOME=1.0).
-   **D (Directness)**: How closely the evidence links to the specific capability being scored.
-   **R (Reliability)**: The trustworthiness of the source tool.
-   **T (Temporal/Recency)**: A decay factor based on how old the evidence is (recent evidence has higher weight).
-   **P (Polarity)**: +1 for positive engineering signals, negative for risks/anti-patterns. **Negative polarity evidence does NOT eliminate positive evidence — it reduces the aggregate weight.**

## Capability Scoring Function (Minor v1)
An interpretable normalized scoring function aggregates evidence into a capability score ($C$) for a developer ($d$) and target ($s$):

$$C(d,s) = \sigma\left(\frac{\sum w_i}{Z}\right)$$

Where:
-   $\sigma$ is the sigmoid function to bound the score between 0 and 1.
-   $Z$ is a normalization constant (to be calibrated once real evidence data is available).
-   `scoring_version` must be stored alongside every score for reproducibility.

## Confidence Score (Independent of Capability Score)
Confidence is calculated independently. **A developer can have High Score + Low Confidence, or Moderate Score + High Confidence.**

$$Confidence = f(\text{evidence quantity}, \text{evidence diversity}, \text{recency}, \text{consistency})$$

## Temporal Updates
When new evidence arrives after a new analysis run, the existing capability is re-evaluated:
*   Updated score is stored in `developer_capabilities`.
*   The previous state is appended immutably to `capability_history`.

## Skill Gap
$$Gap(d,s) = Target(s) - Capability(d,s)$$

A low Gap score must be qualified by confidence. **A low-confidence gap must be visually distinguishable from a high-confidence gap in the UI.**
