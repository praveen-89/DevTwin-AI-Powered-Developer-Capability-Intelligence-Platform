# DevTwin Domain Model

*Source of Truth Context: This document defines what the system's concepts and relationships mean.*

## Core Entities

### 1. Developer
*   **Purpose**: The central human actor whose capabilities are being tracked.
*   **Ownership**: Self-owned.
*   **Lifecycle**: Created upon signup. Exists indefinitely.
*   **Relationships**: Maps to an external auth identity (`auth_user_id`). Has many GitHub Accounts, Projects, Capabilities, and Skill Gaps.
*   **Source of Truth**: DevTwin Platform.

### 2. GitHub Account
*   **Purpose**: Represents an external GitHub identity linked to a Developer.
*   **Ownership**: Owned by Developer.
*   **Lifecycle**: Created when a developer links their GitHub via OAuth.
*   **Relationships**: Belongs to Developer.
*   **Important Attributes**: External GitHub User ID, username. Plaintext tokens are NEVER stored here.
*   **Source of Truth**: GitHub (mirrored in DevTwin).

### 3. Project
*   **Purpose**: A logical grouping of repositories or work associated with a developer.
*   **Ownership**: Owned by Developer.
*   **Relationships**: Contains Repositories.

### 4. Repository
*   **Purpose**: Represents a tracked codebase containing evidence of engineering work.
*   **Ownership**: Owned by Project/Developer (for private repos) or tracked publicly.
*   **Relationships**: Belongs to Project. Undergoes many Analysis Jobs. Contains Commits, PRs.
*   **Important Attributes**: GitHub Repo ID, full name, URL, visibility, default branch.

### 5. Repository Language
*   **Purpose**: Statistics about languages used in a repository.
*   **Source of Truth**: Analysis Run (Linguist/Enry).

### 6. Repository Dependency
*   **Purpose**: Tracked software dependencies (e.g., npm packages, pip packages).
*   **Source of Truth**: Analysis Run (Dependency manifest parsing).

### 7. Commit
*   **Purpose**: A unit of version-controlled work. Essential for accurate CodeRisk attribution.
*   **Important Attributes**: SHA, author email, timestamp, message.
*   **Source of Truth**: Git History.

### 8. Pull Request
*   **Purpose**: A unit of collaboration and peer review. Used as evidence of communication/code review capabilities.
*   **Important Attributes**: PR number, author, state, timestamps, GitHub PR ID.
*   **Source of Truth**: GitHub.

### 9. Analysis Job
*   **Purpose**: Represents the user/system request to analyze a repository.
*   **Lifecycle**: QUEUED -> PROCESSING -> COMPLETED/FAILED.
*   **Relationships**: Contains one or more Analysis Runs (attempts).
*   **Important Attributes**: Status, requested_at, attempt_count.

### 10. Analysis Run
*   **Purpose**: Represents a specific, bounded execution attempt of an Analysis Job on a repository.
*   **Lifecycle**: QUEUED -> FETCHING -> MINING -> SKILL_GRAPH -> CODE_RISK -> CAPABILITY -> COMPLETED (or FAILED).
*   **Relationships**: Belongs to an Analysis Job. Generates Observations, Risk Findings.
*   **Important Attributes**: Status, analyzer version, schema version, error info, timestamps.

### 11. Observation
*   **Purpose**: A directly detected, factual finding from an Analysis Run (e.g., "Dependency React found").
*   **Source of Truth**: DevTwin Analysis Engine.

### 12. Evidence
*   **Purpose**: Contextualized interpretation of an Observation, supporting a capability inference.
*   **Relationships**: Supported by Observations. Maps to Taxonomy. Supports Capabilities.

### 13. Skill (Taxonomy)
*   **Purpose**: Broad competency area (e.g., "Backend Development").

### 14. Technology (Taxonomy)
*   **Purpose**: Concrete implementation tool/framework (e.g., "FastAPI").

### 15. Concept (Taxonomy)
*   **Purpose**: Underlying technical theory (e.g., "REST API").

### 16. Skill Relationship
*   **Purpose**: Represents relational mapping between taxonomy nodes (e.g., React REQUIRES JavaScript). Note: This is an internal taxonomy relationship, separate from developer evidence edges.

### 17. Developer Capability
*   **Purpose**: The calculated, current inferred capability of a developer for a specific target.
*   **Relationships**: Targets EXACTLY ONE Skill, Tech, or Concept (Exclusive Arc). Supported by Evidence.

### 18. Capability History
*   **Purpose**: Temporal, immutable, append-only log of previous Capability states. Do NOT overwrite.

### 19. Skill Gap
*   **Purpose**: The delta between a required capability target and the developer's current capability.

### 20. Risk Finding
*   **Purpose**: A CodeRisk signal detected in a repository.
*   **Crucial Rule**: **Risk ≠ Competence**. A risk finding is *evidence* about engineering behavior. If attributed to a specific developer via Git history, it acts as a signal in the capability model. It does not automatically label the developer incompetent.

## Crucial Conceptual Distinctions

**OBSERVATION vs. EVIDENCE vs. INFERENCE vs. CAPABILITY**
1. **Observation**: "File `server.py` contains `from fastapi import FastAPI`." (A raw, undeniable fact).
2. **Evidence**: "Developer used FastAPI in a backend context." (Observation contextualized with type `USAGE`, strength `0.6`).
3. **Inference**: "Because Developer used FastAPI, they likely understand REST API concepts." (SkillGraph traversal).
4. **Capability**: "Developer's overall ability in Backend Development is 0.72 with 0.8 confidence." (The aggregated mathematical result).
