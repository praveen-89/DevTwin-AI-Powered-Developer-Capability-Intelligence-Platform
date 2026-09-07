# 04. Novelty

## Novel Positioning of DevTwin

DevTwin introduces several novel approaches to developer capability modeling that distinguish it from existing generic AI chatbots, code reviewers, and skill assessment platforms.

### 1. The Evidence-Backed Capability Paradigm
Unlike black-box AI assessors that simply state "Developer is 83% Backend," DevTwin enforces a strict provenance model. Every capability score is explicitly linked to an underlying `EvidenceItem`. The system does not guess; it infers based on a weighted evidence hierarchy (Mention -> Usage -> Applied Engineering -> Demonstrated Outcome). If there is no evidence, there is no capability score.

### 2. Separation of Skill and Capability
DevTwin introduces a novel conceptual distinction:
*   **Skill/Technology**: e.g., "Python", "Docker"
*   **Capability**: The ability to effectively apply that technology in real software projects, considering engineering behavior, practical application, and project experience.
The system models capability as a latent state inferred from heterogeneous evidence, rather than a binary "has skill / lacks skill" toggle.

### 3. CodeRisk as a Capability Signal
DevTwin treats static analysis and software metrics not just as repository health indicators, but as *behavioral engineering signals*. The CodeRisk layer translates codebase findings (e.g., hardcoded secrets, deep nesting, lack of CI testing) into evidence that directly updates the developer's capability profile regarding maintainability, security, and architecture. 

### 4. Separation of Score and Confidence
DevTwin natively separates a capability *score* from the *confidence* of that score. Two developers might both receive an intermediate score in Next.js, but one might have a high confidence score due to a diverse, consistent, and recent set of engineering evidence, while the other has a low confidence score based on a single repository. 

### 5. The Tripartite Intelligence Architecture
DevTwin is novel in its architectural synthesis of three distinct intelligence layers:
1.  **SkillGraph**: The relational topology of knowledge.
2.  **CodeRisk**: The behavioral engineering analysis.
3.  **StudyTwin** (Future): The adaptive learning loop.
This structure allows the system to move beyond static assessment and toward a continuously evolving "Digital Twin" of the developer.
