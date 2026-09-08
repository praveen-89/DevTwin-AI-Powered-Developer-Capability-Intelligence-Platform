---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: PRD.md
---

# Product Requirements Document (PRD)

## Product Identity
*   **Product Name**: DevTwin
*   **Formal Title**: AI-Powered Developer Capability Intelligence Platform
*   **One-line Definition**: An intelligence platform that maintains an evolving representation of a developer's technical capabilities, engineering behaviors, and skill gaps based on verifiable repository evidence.
*   **Product Vision**: To create a continuously evolving "Developer Twin" that connects what a developer knows with how they build, enabling evidence-backed capability tracking and personalized growth.
*   **Product Mission**: To eliminate the guesswork in developer capability assessment by replacing static resumes and generic test scores with continuous, evidence-backed engineering intelligence.

## Problem
Current methods for evaluating developer capability rely on static resumes, generic GitHub dashboards, or isolated LeetCode-style assessments. These fail to capture the true, evolving nature of a developer's technical knowledge and practical application. There is a massive gap between claiming knowledge and demonstrating safe, maintainable engineering behavior. Current tools fail to map codebase risks directly back to developer growth opportunities.

## Target Users
*   **Developers**: To track their true, evidence-backed capability progression, identify hidden skill gaps, and understand how their code choices reflect their engineering maturity.

## Product Goals
1.  Ingest heterogeneous repository evidence and deterministically extract observations.
2.  Maintain a relational SkillGraph mapping technologies to underlying concepts.
3.  Calculate an evidence-backed Capability score and Confidence metric for any target skill.
4.  Provide an explainable UI where every capability inference can trace back to source code provenance.

## Non-Goals
DevTwin is explicitly **NOT**:
*   A generic chatbot or ChatGPT clone.
*   A generic Learning Management System (LMS).
*   A resume parser or text analyzer.
*   A generic GitHub statistics dashboard (counting stars or lines of code).
*   A generic code reviewer or pull request summarizer.
*   A simple skill assessment platform using multiple-choice questions.
*   A generic RAG application.
*   An autonomous coding agent that writes code on behalf of the user.

## Core Product Loop
`Know -> Build -> Detect -> Learn -> Improve -> Re-evaluate`

## Core Intelligence Loop
`Capability -> Engineering Behavior -> Risk -> Skill Gap -> Learning Intervention -> Outcome -> Updated Capability`

## Minor Scope (Developer Capability Intelligence Foundation)
The Minor MVP focuses exclusively on establishing the foundational assessment engine:
`GitHub -> Repository Discovery -> Repository Mining -> SkillGraph + CodeRisk -> Evidence -> Capability Model -> Skill Gap -> Dashboard`

## Major Scope (Future)
Future functionality includes **StudyTwin**, which closes the loop:
*   StudyTwin / Personalized learning
*   Knowledge tracing
*   Intervention tracking
*   Outcome measurement
*   Capability prediction
*   Future simulation

## Functional Requirements
*   **FR-001**: System must ingest GitHub repositories via URL or integration.
*   **FR-002**: System must execute asynchronous analysis runs without blocking the UI.
*   **FR-003**: System must extract dependencies and languages from repositories.
*   **FR-004**: System must execute CodeRisk static analysis heuristics.
*   **FR-005**: System must map observations to the SkillGraph taxonomy.
*   **FR-006**: System must generate Evidence from Observations, assigning strength and polarity.
*   **FR-007**: System must calculate Capability scores and Confidence metrics.
*   **FR-008**: System must log historical capability states immutably.
*   **FR-009**: System must calculate Skill Gaps based on target thresholds.
*   **FR-010**: Dashboard must display capability states with click-through provenance to Evidence.

## Non-Functional Requirements
*   **Explainability**: Every capability score must trace back to raw observations.
*   **Security**: Minimal OAuth scopes, external secrets management, strict RLS database boundaries.
*   **Privacy**: Developer A cannot access Developer B's private repository data or capability scores.
*   **Reliability**: Failed analysis jobs must not corrupt existing capability history.
*   **Performance**: The dashboard must load developer capabilities in < 500ms; analysis runs may take minutes asynchronously.

## Acceptance Criteria
1.  A developer can connect a repository, and within 5 minutes, see an updated SkillGraph.
2.  The UI explicitly distinguishes between a "Low Capability Score" and "Low Confidence."
3.  A risk finding (e.g., hardcoded secret) reduces the relevant capability score (e.g., Security) and is logged as negative evidence.

## Future Scope
*   GitLab/Bitbucket integrations.
*   Organizational/Team intelligence aggregations.
*   Production incident prediction mapping.
