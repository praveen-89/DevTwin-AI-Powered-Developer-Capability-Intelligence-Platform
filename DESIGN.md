---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: DESIGN.md
---

# Design Specification (UI/UX)

## Design Philosophy
DevTwin should feel technical, intelligent, trustworthy, explainable, modern, and professional. It is an engineering intelligence tool, not a consumer social app. Avoid meaningless AI visual gimmicks (e.g., generic sparkling wand icons for basic tasks). The interface must prioritize data density, clarity, and provenance.

## Information Architecture
*   Landing
*   Authentication
*   Onboarding (GitHub Connect)
*   Dashboard
    *   Overview (High-level capabilities and recent risks)
    *   Capabilities (Detailed breakdown with confidence intervals)
    *   SkillGraph (Interactive taxonomy visualization)
    *   CodeRisk (Repository-level findings)
    *   Evidence (The raw observation explorer)
    *   Settings

## User Flows
1.  **Onboarding**: Developer signs up -> Authenticates with GitHub -> Selects Repositories to track -> Analysis Jobs queued -> Redirect to Overview.
2.  **Capability Drill-down**: Developer clicks "Backend Development" capability -> Sees temporal trend graph -> Sees list of supporting Evidence -> Clicks Evidence to see source CodeRisk or Commit observation.

## Dashboard Design
*   **Overview**: Provides a snapshot. Must clearly separate "What we know" (High Confidence) from "What we infer" (Low Confidence).
*   **Capabilities**: A radar chart or bar layout.

## Capability Visualization
*   **Capability**: Represented as a normalized score (0.0 - 1.0) via progress bars or radial charts.
*   **Confidence**: Represented visually (e.g., opacity, error bars, or a distinct secondary indicator like "High/Med/Low" badges).
*   **Trend**: Sparklines showing `capability_history` over the last N analysis runs.
*   **History**: A timeline component.
*   **Skill Gaps**: A visual delta overlay comparing Current Score vs. Target Score.

## SkillGraph Visualization
*   **Nodes**: Skills (large), Technologies (medium), Concepts (small).
*   **Relationships**: Directed edges showing `REQUIRES`, `RELATED_TO`.
*   **Interactions**: Clicking a node filters the Evidence view to show only evidence supporting that node.

## CodeRisk Visualization
*   **Severity**: Distinct color coding (Critical=Red, High=Orange, Medium=Yellow, Low=Blue).
*   **Confidence**: Explicitly shown next to severity (e.g., "Critical Severity | 40% Confidence").
*   **Location**: File path and line numbers displayed as monospaced code blocks.
*   **Evidence**: A link to the generated negative Evidence item that impacted the capability.

## UX Principles
*   **Explainability**: Every score must be clickable to reveal its provenance.
*   **Evidence-First Design**: The UI must reflect that data is based on facts, not black-box LLM guessing.
*   **Progressive Disclosure**: Show high-level scores first; allow drilling down into raw JSON/AST observations for advanced users.
*   **No Misleading Scores**: If confidence is too low, the UI should state "Insufficient Data" rather than displaying a misleading 0.2 score.
*   **Uncertainty Visibility**: Always show when the system is guessing vs. knowing.
*   **Accessible Interaction**: Standard contrast ratios, keyboard navigation.
*   **Responsive Design**: Mobile-friendly, though desktop-optimized for deep data exploration.

## Component Guidelines
*   Use a standardized component library based on Tailwind CSS v4 and Lucide React icons.
*   **Color Palette**: Dark-mode primary (`#090D16` app background, `#0f172a` container background, `#162036` elevated cards), with cyan (`#06b6d4`) and emerald (`#10b981`) accents.
*   **Typography**: Geist Sans for interface elements, Geist Mono for code, hashes, and scores.
*   **Components Implemented (Step 7A–7C)**:
    *   `Shell`, `Sidebar`, `Header`, `PageContainer`, `PageHeading` (App shell layout)
    *   `Card`, `CardHeader`, `CardTitle`, `CardBody`, `CardFooter` (Container primitives)
    *   `Badge`, `SeverityBadge`, `ConfidenceBadge`, `StatusBadge` (Categorical tags)
    *   `Button` (Interactive variants with loading states)
    *   `ScoreGauge`, `ScorePill` (Capability and confidence visualization)
    *   `StageStepper` (Analysis pipeline stage tracker)
    *   `SkillGraphCanvas` (Interactive Cytoscape taxonomy graph canvas with zoom/pan/fit/layout controls)
    *   `SkillGraphDetail` (Inspector panel for node metadata and directed edge provenance)
    *   `CapabilityHistoryChart` (Recharts temporal time series with snapshot history table)
    *   `Skeleton`, `CardSkeleton` (Loading states)
    *   `EmptyState`, `InlineError` (Error and zero-data states)
*   **Run-Scoped Capability Display Constraint**: Capabilities are single-repository run-scoped in the Minor MVP. An amber warning banner is explicitly displayed across all capability views to disclaim cross-repository aggregation.
*   **SkillGraph Visual Taxonomy**:
    *   `Skill`: Cyan ellipse (`#06b6d4`, border `#0891b2`)
    *   `Technology`: Emerald rectangle (`#10b981`, border `#059669`)
    *   `Concept`: Purple diamond (`#a855f7`, border `#7e22ce`)
    *   `Directed Edge`: Slate bezier arrow (`#475569`), highlighted with cyan (`#38bdf8`) on selection
    *   `Accessibility Fallback`: Accessible tabular view provided for keyboard and screen reader exploration.
