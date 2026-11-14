---
Status: Active
Version: 1.1
Last Updated: 2026-11-14
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

## Page Explainability Pattern
*   **PageExplainer**: Every authenticated dashboard page (`Overview`, `Repositories`, `Capabilities`, `CodeRisk`, `SkillGraph`, `Evidence`) has a collapsible panel directly below its hero banner (`frontend/src/components/dashboard/page-explainer.tsx`) stating in plain language what the page shows and defining every technical term/column visible on it (e.g. Strength, Directness, Polarity, Severity, Confidence). Expand/collapse state persists per page via `localStorage` (a per-viewer convenience, not synced state).
*   **Summary Chart Below Hero**: Every dashboard page also shows a small chart immediately below its hero banner, computed client-side from data the page already fetches (no new API calls): a severity/type/visibility breakdown bar chart (`frontend/src/components/dashboard/breakdown-chart.tsx`, `BreakdownChart`), a composition pie chart for SkillGraph's language breakdown (`CompositionPieChart`, same file), or — on Capabilities — the existing score-history line chart, which already satisfies this.

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
*   **Color Palette**: Dual-theme — Light mode: `#f8fafc` app background, `#ffffff` container background, `slate-100` borders, `#0f172a` body text. Dark mode: `#090D16` app background, `#0f172a` container background, `#162036` elevated cards. Accent colors: cyan (`#06b6d4`) and emerald (`#10b981`). Theme switching via `next-themes` (`system`/`light`/`dark`) with `attribute="class"` on `<html>`.
*   **Typography**: Geist Sans for interface elements, Geist Mono for code, hashes, and scores.
*   **Components Implemented (Step 7A–7C)**:
    *   `Shell`, `Sidebar`, `Header`, `PageContainer`, `PageHeading` (App shell layout — dual-theme aware as of v1.1)
    *   `Card`, `CardHeader`, `CardTitle`, `CardBody`, `CardFooter` (Container primitives — dual-theme aware)
    *   `Badge`, `SeverityBadge`, `ConfidenceBadge`, `StatusBadge` (Categorical tags)
    *   `Button` (Interactive variants with loading states)
    *   `ScoreGauge`, `ScorePill` (Capability and confidence visualization)
    *   `StageStepper` (Analysis pipeline stage tracker)
    *   `SkillGraphCanvas` (Interactive Cytoscape taxonomy graph canvas with zoom/pan/fit/layout controls)
    *   `SkillGraphDetail` (Inspector panel for node metadata and directed edge provenance)
    *   `CapabilityHistoryChart` (Recharts temporal time series with snapshot history table)
    *   `Skeleton`, `CardSkeleton` (Loading states)
    *   `EmptyState`, `InlineError` (Error and zero-data states)
*   **Components Implemented (Step 7D — Theme & Hero Banners)**:
    *   `PageHeroBanner` (`src/components/layout/page-hero-banner.tsx`) — Reusable unified hero section card. Follows the ordered layout: 1) Top badge chip/tablet, 2) Full-width generated technical banner illustration, 3) Primary title and description, 4) CTA action buttons and metric stat chips. Everything is enclosed in one cohesive hero card with theme-aware styling (`light`/`dark`/`system`).
    *   `page-banner-illustrations.tsx` — 9 inline SVG `motion/react`-animated technical illustration components, one per page, optimized for zero rasterization blur (no filter drop-shadow artifacts) and high contrast in light mode:
        *   `OverviewBannerVisual` — Pulse radar with twin node and 4 metric nodes
        *   `RepositoriesBannerVisual` — Git branch topology with commit nodes and language badges
        *   `CapabilitiesBannerVisual` — Sigmoid curve mathematical chart with formula annotation
        *   `CodeRiskBannerVisual` — Shield matrix with 4 category quadrants (SEC/REL/MAINT/TEST)
        *   `SkillGraphBannerVisual` — Node/edge taxonomy graph (Skill=cyan ellipse, Tech=emerald rect, Concept=purple diamond)
        *   `EvidenceBannerVisual` — Layered evidence cards with provenance and strength readouts
        *   `PipelineBannerVisual` — 8-stage pipeline stepper track
        *   `AboutBannerVisual` — Comparison matrix (Resume vs DevTwin)
        *   `LandingBannerVisual` — Intelligence loop hexagon with 6 stage nodes
    *   `ThemeToggle` (`src/components/theme/theme-toggle.tsx`) — Light/Dark/System dropdown toggle rendered in the app `Header` next to auth controls.
    *   Static SVG banners in `public/banners/` — CSS `prefers-color-scheme`-based companion banners for all 9 pages (used as `<img>` fallbacks via `bannerSvgSrc` prop).
*   **Run-Scoped Capability Display Constraint**: Capabilities are single-repository run-scoped in the Minor MVP. An amber warning banner is explicitly displayed across all capability views to disclaim cross-repository aggregation.
*   **SkillGraph Visual Taxonomy**:
    *   `Skill`: Cyan ellipse (`#06b6d4`, border `#0891b2`)
    *   `Technology`: Emerald rectangle (`#10b981`, border `#059669`)
    *   `Concept`: Purple diamond (`#a855f7`, border `#7e22ce`)
    *   `Directed Edge`: Slate bezier arrow (`#475569`), highlighted with cyan (`#38bdf8`) on selection
    *   `Accessibility Fallback`: Accessible tabular view provided for keyboard and screen reader exploration.
