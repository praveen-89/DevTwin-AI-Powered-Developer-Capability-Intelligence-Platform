# 11. Database Schema

## Overview
For the Minor MVP, DevTwin uses a relational database (PostgreSQL) optimized to handle the requirements of the SkillGraph and Evidence Model via junction tables.

## Core Entities

### 1. Identity & Projects
-   **Developer**: `id, username, github_id, created_at`
-   **Repository**: `id, developer_id, url, name, description, last_analyzed_at`

### 2. SkillGraph Taxonomy
-   **Domain**: `id, name` (e.g., "Frontend", "DevOps")
-   **Skill**: `id, domain_id, name`
-   **Concept**: `id, name`
-   **Technology**: `id, name, type` (e.g., "React", "PostgreSQL")

### 3. SkillGraph Relationships (Junction Tables)
-   **Tech_Concept**: `tech_id, concept_id`
-   **Skill_Tech**: `skill_id, tech_id`
-   **Tech_Related**: `tech_id_1, tech_id_2, relation_type`

### 4. Analysis & Evidence
-   **AnalysisJob**: `id, repository_id, status (QUEUED, MINING, COMPLETED, FAILED), started_at, completed_at`
-   **Observation**: `id, job_id, type, raw_data, location, detected_at`
-   **RiskSignal**: `id, repository_id, observation_id, category, type, severity, confidence, description`
-   **EvidenceItem**: `id, observation_id, target_entity_id, target_entity_type, type, strength, directness, reliability, recency, polarity`

### 5. Capability State
-   **CapabilityState**: `id, developer_id, target_entity_id (Skill/Tech), target_entity_type, score, confidence, trend, last_updated_at`
-   **Capability_Evidence**: `capability_id, evidence_id` (Linking scores directly to evidence for provenance)
-   **CapabilityHistory**: Time-series log of CapabilityState changes for trend analysis.

## Note on Graph Databases
While a property graph (like Neo4j) is conceptually aligned with the SkillGraph, PostgreSQL provides sufficient capability (via recursive CTEs and junction tables) for the Minor MVP without introducing premature infrastructure complexity.
