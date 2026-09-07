# 10. Scoring Model

## Design Philosophy
DevTwin explicitly **rejects** arbitrary fixed weights (e.g., Knowledge = 20%, Application = 30%). Capability is treated as a latent state inferred from heterogeneous evidence.

## Initial Evidence Contribution
The weight of a single piece of evidence ($w_i$) is calculated dynamically based on the properties of the `EvidenceItem`:

$$w_i = S_i \times D_i \times R_i \times T_i \times P_i$$

Where:
-   **S (Strength)**: Based on the evidence hierarchy (Mention vs. Usage vs. Outcome).
-   **D (Directness)**: How closely the evidence links to the specific capability being scored.
-   **R (Reliability)**: The trustworthiness of the source.
-   **T (Temporal/Recency)**: A decay factor based on how old the evidence is.
-   **P (Polarity)**: Positive (supporting capability) or negative (highlighting a gap/risk).

## Capability Scoring Function (Minor v1)
For the Minor MVP, an interpretable normalized scoring function is used to aggregate evidence into a capability score ($C$) for a developer ($d$) and skill ($s$):

$$C(d,s) = \sigma\left(\frac{\sum w_i}{Z}\right)$$

Where:
-   $\sigma$ is the sigmoid function to bound the score between 0 and 1.
-   $Z$ is a normalization constant (which can be calibrated later).

*Note: This is a calibration starting point, NOT a scientifically proven universal formula. The system architecture ensures this model can be tuned or replaced later.*

## Confidence Score
Confidence is calculated independently of the capability score. It represents the system's certainty:

$$Confidence = f(\text{quality, diversity, consistency, recency, evidence quantity})$$

## Temporal Capability Updates
Capability is not static. When new evidence ($E(t+1)$) arrives, the state is updated:

$$C(t+1) = Update(C(t), E(t+1))$$

The trend can be calculated as:

$$Trend = C(t) - C(t-k)$$

## Skill Gap Identification
The skill gap is conceptually modeled as:

$$Gap(d,s) = Target(s) - Capability(d,s)$$

**Crucial Caveat:** A low capability score does *not* automatically mean the developer lacks the skill. It may simply mean a lack of evidence. The UI must clearly distinguish between:
-   **Observed** (Evidence exists to support a score)
-   **Inferred** (Score derived from related skills in the SkillGraph)
-   **Uncertain** (Insufficient evidence to make a claim)
