# DevTwin Domain Model

This document outlines the core business entities for DevTwin. It focuses on the conceptual domain, ownership, lifecycle, and relationships. For the physical PostgreSQL database schema, see `11_DATABASE_SCHEMA.md`.

## Core Entities

### 1. Developer
*   **Purpose**: The central human actor whose capabilities are being tracked.
*   **Ownership**: Self-owned.
*   **Lifecycle**: Created upon signup. Exists indefinitely.
*   **Relationships**: Has many GitHub Accounts, Projects, Capabilities, and Skill Gaps.
*   **Important Attributes**: Internal UUID, created timestamp.
*   **Source of Truth**: DevTwin Platform.
*   **State**: Current state (historical states tracked in other entities).

### 2. GitHub Account
*   **Purpose**: Represents an external GitHub identity linked to a Developer.
*   **Ownership**: Owned by Developer.
*   **Lifecycle**: Created when a developer links their GitHub.
*   **Relationships**: Belongs to Developer.
*   **Important Attributes**: External GitHub User ID, username.
*   **Source of Truth**: GitHub (mirrored in DevTwin).
*   **State**: Current state.

### 3. Project
*   **Purpose**: A logical grouping of repositories or work associated with a developer.
*   **Ownership**: Owned by Developer.
*   **Lifecycle**: Created by Developer.
*   **Relationships**: Contains Repositories.
*   **Important Attributes**: Name, description.
*   **Source of Truth**: DevTwin Platform.
*   **State**: Current state.

### 4. Repository
*   **Purpose**: Represents a tracked codebase containing evidence of engineering work.
*   **Ownership**: Owned by Project/Developer (for private repos) or tracked publicly.
*   **Lifecycle**: Tracked when added to DevTwin.
*   **Relationships**: Belongs to Project. Undergoes many Analysis Runs. Contains Commits, PRs.
*   **Important Attributes**: GitHub Repo ID, full name, URL, visibility, default branch.
*   **Source of Truth**: GitHub (mirrored/synced).
*   **State**: Current metadata (analysis data separated).

### 5. Repository Language
*   **Purpose**: Statistics about languages used in a repository.
*   **Ownership**: Owned by Repository.
*   **Lifecycle**: Replaced/updated during Analysis Runs.
*   **Relationships**: Belongs to Repository.
*   **Important Attributes**: Language name, bytes.
*   **Source of Truth**: Analysis Run (Linguist/Enry).
*   **State**: Current state per repository.

### 6. Repository Dependency
*   **Purpose**: Tracked software dependencies (e.g., npm packages, pip packages).
*   **Ownership**: Owned by Repository.
*   **Lifecycle**: Updated during Analysis Runs.
*   **Relationships**: Belongs to Repository. Maps to Technologies in SkillGraph.
*   **Important Attributes**: Ecosystem, package name, version constraint.
*   **Source of Truth**: Analysis Run (Dependency manifest parsing).
*   **State**: Current state per repository.

### 7. Commit
*   **Purpose**: A unit of version-controlled work.
*   **Ownership**: Owned by Repository. Attributed to Author (Developer).
*   **Lifecycle**: Immutable once extracted from Git.
*   **Relationships**: Belongs to Repository. May trigger Risk Findings or Evidence.
*   **Important Attributes**: SHA, author email, timestamp, message.
*   **Source of Truth**: Git History.
*   **State**: Historical/Immutable.

### 8. Pull Request
*   **Purpose**: A unit of collaboration and peer review.
*   **Ownership**: Owned by Repository.
*   **Lifecycle**: Open -> Merged/Closed.
*   **Relationships**: Belongs to Repository.
*   **Important Attributes**: PR number, state, timestamps.
*   **Source of Truth**: GitHub.
*   **State**: Current state (syncs over time).

### 9. Analysis Job
*   **Purpose**: Represents the queueing and scheduling request for an analysis.
*   **Ownership**: System-owned.
*   **Lifecycle**: QUEUED -> IN_PROGRESS -> COMPLETED/FAILED.
*   **Relationships**: Triggers Analysis Run.
*   **Important Attributes**: Priority, queued timestamp.
*   **Source of Truth**: DevTwin Queue.
*   **State**: Ephemeral/Current.

### 10. Analysis Run
*   **Purpose**: Represents a specific, bounded execution of the analysis pipeline on a repository.
*   **Ownership**: System-owned (linked to Repository).
*   **Lifecycle**: Created upon job execution. Finalizes upon completion/failure.
*   **Relationships**: Belongs to Repository. Generates Observations, Risk Findings.
*   **Important Attributes**: Status, analyzer version, schema version, error info, timestamps.
*   **Source of Truth**: DevTwin Analysis Engine.
*   **State**: Historical/Immutable once completed.

### 11. Observation
*   **Purpose**: A directly detected, factual finding from an Analysis Run.
*   **Ownership**: Owned by Analysis Run.
*   **Lifecycle**: Created during an Analysis Run. Immutable.
*   **Relationships**: Belongs to Analysis Run. Translates into Evidence or Risk Findings.
*   **Important Attributes**: Source tool, source reference (file/line), raw data.
*   **Source of Truth**: DevTwin Analysis Engine.
*   **State**: Historical/Immutable.

### 12. Evidence
*   **Purpose**: Contextualized support for a capability or technical inference, derived from Observations.
*   **Ownership**: Developer-associated.
*   **Lifecycle**: Created based on Observations.
*   **Relationships**: Supported by Observations. Maps to Skills/Technologies/Concepts. Supports Capabilities.
*   **Important Attributes**: Type (MENTION, USAGE, etc.), strength, directness, reliability, recency, polarity.
*   **Source of Truth**: DevTwin Evidence Engine.
*   **State**: Historical/Immutable.

### 13. Skill
*   **Purpose**: Broad competency area (e.g., "Backend Development").
*   **Ownership**: System-owned (Taxonomy).
*   **Lifecycle**: Managed globally by DevTwin.
*   **Relationships**: Related to other Skills. Includes Technologies and Concepts.
*   **Important Attributes**: Name, domain.
*   **Source of Truth**: DevTwin Taxonomy.
*   **State**: Current state.

### 14. Technology
*   **Purpose**: Concrete implementation tool/framework (e.g., "FastAPI").
*   **Ownership**: System-owned (Taxonomy).
*   **Lifecycle**: Managed globally.
*   **Relationships**: Part of Skills. Involves Concepts.
*   **Important Attributes**: Name, type.
*   **Source of Truth**: DevTwin Taxonomy.
*   **State**: Current state.

### 15. Concept
*   **Purpose**: Underlying technical theory (e.g., "REST API").
*   **Ownership**: System-owned (Taxonomy).
*   **Lifecycle**: Managed globally.
*   **Relationships**: Part of Skills. Involved in Technologies.
*   **Important Attributes**: Name.
*   **Source of Truth**: DevTwin Taxonomy.
*   **State**: Current state.

### 16. Skill Relationship
*   **Purpose**: Represents directed edges between nodes in the SkillGraph (e.g., React REQUIRES JavaScript).
*   **Ownership**: System-owned (Taxonomy).
*   **Lifecycle**: Managed globally.
*   **Relationships**: Connects Taxonomy nodes.
*   **Important Attributes**: Relation type (REQUIRES, RELATED_TO, PART_OF).
*   **Source of Truth**: DevTwin Taxonomy.
*   **State**: Current state.

### 17. Developer Capability
*   **Purpose**: The calculated, current inferred capability of a developer for a specific target.
*   **Ownership**: Owned by Developer.
*   **Lifecycle**: Continuously updated as new Evidence arrives.
*   **Relationships**: Belongs to Developer. Targets exactly one Skill, Tech, or Concept. Supported by Evidence.
*   **Important Attributes**: Score, confidence, model version.
*   **Source of Truth**: DevTwin Capability Engine.
*   **State**: Current state (Latest calculation).

### 18. Capability History
*   **Purpose**: Temporal, immutable log of previous Capability states.
*   **Ownership**: Owned by Developer Capability.
*   **Lifecycle**: Appended whenever a Capability updates.
*   **Relationships**: Belongs to Developer Capability. Linked to Analysis Run.
*   **Important Attributes**: Historical score, historical confidence, timestamp, model version.
*   **Source of Truth**: DevTwin Capability Engine.
*   **State**: Historical/Immutable.

### 19. Skill Gap
*   **Purpose**: The delta between a required capability target and the developer's current capability.
*   **Ownership**: Owned by Developer.
*   **Lifecycle**: Recalculated dynamically or periodically.
*   **Relationships**: Belongs to Developer. Targets exactly one Skill, Tech, or Concept.
*   **Important Attributes**: Target score, current score, gap value, confidence.
*   **Source of Truth**: DevTwin Capability Engine.
*   **State**: Current state.

### 20. Risk Finding
*   **Purpose**: A CodeRisk signal detected in a repository.
*   **Ownership**: Owned by Repository. (Optionally attributed to a commit/developer).
*   **Lifecycle**: Generated during Analysis Runs.
*   **Relationships**: Belongs to Repository, Analysis Run, Observation. Optionally linked to Commit.
*   **Important Attributes**: Category (SECURITY, MAINTAINABILITY, etc.), severity, confidence, risk type.
*   **Source of Truth**: CodeRisk Engine.
*   **State**: Current and Historical (tied to runs).

## Crucial Conceptual Distinctions

**OBSERVATION vs. EVIDENCE vs. INFERENCE vs. CAPABILITY**
1. **Observation**: "File `server.py` contains `from fastapi import FastAPI`." (A raw, undeniable fact).
2. **Evidence**: "Developer used FastAPI in a backend context." (Observation contextualized with type `USAGE`, strength `0.6`).
3. **Inference**: "Because Developer used FastAPI, they likely understand REST API concepts." (SkillGraph traversal).
4. **Capability**: "Developer's overall ability in Backend Development is 0.72 with 0.8 confidence." (The aggregated mathematical result).
