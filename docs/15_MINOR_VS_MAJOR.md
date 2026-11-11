# 15. Minor vs. Major Scope

---
Status: Active
Version: 2.0
Last Updated: 2026-11-12
---

## Overview
This document strictly delineates the boundaries between the current Minor Project (Foundation) and the future Major Project (Production/Startup).

## Minor Project: Developer Capability Intelligence Foundation
*Goal: Can heterogeneous evidence extracted from software repositories be transformed into an explainable, evidence-backed representation of a developer's capabilities?*

**Implemented & Verified in Minor MVP (v0.8 / Checkpoint 31):**
*   **GitHub Ingestion**: GitHub App OAuth installation, account linking, status, and repository listing via ephemeral installation tokens.
*   **Repository Ingestion & Fetching**: Safe streaming tarball downloads with Zip Slip / path traversal protection and isolated temporary workspaces.
*   **Repository Mining**: Language classification, manifest extraction (`package.json`, `requirements.txt`, `Cargo.toml`), and Python AST symbol extraction (classes, async functions, imports).
*   **SkillGraph Engine**: Grounded taxonomy mapping, entity deduplication, and relational persistence.
*   **CodeRisk Engine**: 8 static analysis heuristics across security, reliability, maintainability, and testing, with secret redaction (Risk ≠ Competence).
*   **Evidence Engine**: Deterministic translation of raw observations into contextualized evidence with strength, directness, reliability, and polarity (`-1.0` to `+1.0`).
*   **Capability Model v1**: Mathematical aggregation with sigmoid saturation, rank-ordered diminishing returns, half-life temporal decay (365 days), and uncertainty-aware confidence bounds (`[0.05, 0.98]`).
*   **Capability History**: Append-only logging for temporal capability trend analytics.
*   **Interactive Dashboard UI**: Next.js 16 (App Router, Tailwind CSS v4) with 6 core views (`/` Overview, `/repositories`, `/capabilities`, `/coderisk`, `/skillgraph`, `/evidence`).
*   **Interactive Visualizations**: Cytoscape interactive graph canvas with accessible tabular toggle, and Recharts temporal history charts.
*   **In-App Authentication**: Supabase Auth modal (Sign In / Sign Up) with graceful dev-token fallback.
*   **Testing Pyramid**: 385 backend tests, 64 frontend tests, and 47 Playwright tests. Verified live E2E run (`3bfc7727-8c19-46da-9490-5faf245e4940`).

**Explicitly Excluded from Minor:**
*   StudyTwin (Learning interventions)
*   Personalized learning system
*   Reinforcement learning / Federated learning
*   Organization/Team intelligence
*   Autonomous coding agents
*   Production incident prediction
*   Digital-twin counterfactual simulation
*   Public repository URL ingestion (deferred; Minor uses OAuth selection only)

---

## Major Project: Developer Twin
*Goal: Close the loop from capability assessment to learning intervention and verified outcome.*

**Future Capabilities:**
*   **StudyTwin Integration**: Recommending specific learning paths based on identified skill gaps.
*   **Knowledge Tracing**: Modeling the learning process over time (BKT / DKT).
*   **Outcome Measurement**: Verifying if a learning intervention actually resulted in improved engineering behavior in subsequent commits.
*   **What-if Simulation**: Simulating the impact of adding a specific skill to the developer's profile.
*   **Advanced ML**: Moving from interpretable weighted models to predictive models calibrated against ground-truth data.
