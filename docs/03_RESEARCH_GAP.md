# 03. Research Gap

## Introduction
While significant research and commercial effort have been directed toward assessing developer productivity, analyzing source code for vulnerabilities, and recommending learning content, there remains a substantial gap in the synthesis of these domains into a holistic, evolving model of the developer themselves.

## Identified Gaps

### 1. Disconnect Between Code Quality and Developer Capability
Extensive research exists on static analysis, software metrics, and defect prediction (e.g., SonarQube, CodeQL). However, these tools analyze the *repository* as the primary subject. There is a research gap in mapping the specific findings, risks, and architectural patterns found in code directly back to a structured capability model of the *authoring developer*. Code analysis is rarely treated as dynamic evidence for updating a latent capability state.

### 2. Lack of Explainable Evidence Hierarchies in Capability Inference
Many modern HR-tech systems and generic LLM-based profile analyzers attempt to extract skills from text (resumes, commit messages). However, they lack a formalized "evidence hierarchy." They often weight a mention in a bio the same as complex usage in a repository. There is a lack of models that explicitly model the *strength, directness, reliability, and recency* of evidence when inferring capability.

### 3. Static Skill Ontologies vs. Dynamic Capability Graphs
Traditional skill mapping relies on static taxonomies. While some research has explored knowledge graphs for software engineering, there is limited work on interconnected models that link a developer, the concepts they use, the technologies they apply, the specific evidence they generate, and the resulting capability estimate in a unified, queryable structure (the SkillGraph concept).

### 4. Conflating Knowledge with Engineering Behavior
Educational technology and Developer LMS platforms (e.g., Pluralsight, Udemy) excel at mapping what a developer *knows* (via multiple-choice assessments or guided labs). However, they cannot verify if that knowledge translates into safe, maintainable *engineering behavior* in the wild. The gap lies in the continuous integration of practical engineering signals (CodeRisk) into the capability profile.

## Conclusion
The fundamental research gap DevTwin addresses is the lack of a formal, computational model that transforms heterogeneous repository artifacts into an explainable, probabilistic capability state, where every inference is explicitly tied to observable engineering evidence.
