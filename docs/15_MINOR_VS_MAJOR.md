# 15. Minor vs. Major Scope

## Overview
This document strictly delineates the boundaries between the current Minor Project (Foundation) and the future Major Project (Production/Startup).

## Minor Project: Developer Capability Intelligence Foundation
*Goal: Can heterogeneous evidence extracted from software repositories be transformed into an explainable, evidence-backed representation of a developer's capabilities?*

**Specified & Planned (Not Yet Implemented):**
*   GitHub ingestion (OAuth + Repository Selection)
*   Repository mining (AST, dependencies)
*   SkillGraph modeling (Relational structure)
*   CodeRisk analysis (Static analysis heuristics)
*   Evidence engine (Observation to Evidence translation)
*   Capability model (Interpretable weighted scoring)
*   Capability history logging
*   Basic skill-gap identification
*   Explainable dashboard UI
*   Evidence Explorer UI

**Explicitly Excluded from Minor:**
*   StudyTwin (Learning interventions)
*   Personalized learning system
*   Reinforcement learning / Federated learning
*   Organization/Team intelligence
*   Autonomous coding agents
*   Production incident prediction
*   Digital-twin counterfactual simulation
*   Public repository URL ingestion (deferred; Minor uses OAuth selection only)

## Major Project: Developer Twin
*Goal: Close the loop from capability assessment to learning intervention and verified outcome.*

**Future Capabilities:**
*   **StudyTwin Integration**: Recommending specific learning paths based on identified skill gaps.
*   **Knowledge Tracing**: Modeling the learning process over time.
*   **Outcome Measurement**: Verifying if a learning intervention actually resulted in improved engineering behavior in subsequent commits.
*   **What-if Simulation**: Simulating the impact of adding a specific skill to the developer's profile.
*   **Advanced ML**: Moving from interpretable weighted models to predictive models calibrated against ground-truth data.
