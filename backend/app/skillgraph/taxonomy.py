"""
DevTwin SkillGraph — Deterministic Taxonomy Resolution & Normalization

Provides curated, deterministic taxonomic mapping from languages, dependencies,
and AST symbols to canonical Technologies, Concepts, and Skills.
Prevents ungrounded or hallucinated capability claims.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TaxonomyLanguageMapping:
    technology_name: str
    technology_type: str
    skills: List[Tuple[str, str]]  # (skill_name, domain)
    concepts: List[str]


@dataclass(frozen=True)
class TaxonomyDependencyMapping:
    technology_name: str
    technology_type: str
    skills: List[Tuple[str, str]]
    concepts: List[str]


# ---------------------------------------------------------------------------
# Canonical Language Taxonomy
# ---------------------------------------------------------------------------

CANONICAL_LANGUAGES: Dict[str, TaxonomyLanguageMapping] = {
    "python": TaxonomyLanguageMapping(
        technology_name="Python",
        technology_type="language",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["Object-Oriented Programming", "Dynamic Typing", "Scripting"],
    ),
    "javascript": TaxonomyLanguageMapping(
        technology_name="JavaScript",
        technology_type="language",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Web Development", "Event-Driven Programming", "Dynamic Typing"],
    ),
    "typescript": TaxonomyLanguageMapping(
        technology_name="TypeScript",
        technology_type="language",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Static Typing", "Web Development", "Object-Oriented Programming"],
    ),
    "rust": TaxonomyLanguageMapping(
        technology_name="Rust",
        technology_type="language",
        skills=[("Systems Programming", "Systems Engineering")],
        concepts=["Memory Safety", "Systems Architecture", "Static Typing"],
    ),
    "go": TaxonomyLanguageMapping(
        technology_name="Go",
        technology_type="language",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["Concurrency", "Microservices", "Static Typing"],
    ),
    "html": TaxonomyLanguageMapping(
        technology_name="HTML",
        technology_type="language",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Web Markup", "Document Object Model"],
    ),
    "css": TaxonomyLanguageMapping(
        technology_name="CSS",
        technology_type="language",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Web Styling", "Responsive Layouts"],
    ),
    "sql": TaxonomyLanguageMapping(
        technology_name="SQL",
        technology_type="language",
        skills=[("Database Administration", "Data Engineering")],
        concepts=["Relational Databases", "Declarative Querying"],
    ),
    "shell": TaxonomyLanguageMapping(
        technology_name="Shell",
        technology_type="language",
        skills=[("DevOps", "Operations & Infrastructure")],
        concepts=["Scripting", "Automation"],
    ),
    "dockerfile": TaxonomyLanguageMapping(
        technology_name="Docker",
        technology_type="tool",
        skills=[("DevOps", "Operations & Infrastructure")],
        concepts=["Containerization", "Infrastructure as Code"],
    ),
}


# ---------------------------------------------------------------------------
# Canonical Dependency Taxonomy (Well-known packages)
# ---------------------------------------------------------------------------

CANONICAL_DEPENDENCIES: Dict[str, TaxonomyDependencyMapping] = {
    # Python (pip)
    "fastapi": TaxonomyDependencyMapping(
        technology_name="FastAPI",
        technology_type="framework",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["REST API", "Asynchronous Programming", "API Routing"],
    ),
    "flask": TaxonomyDependencyMapping(
        technology_name="Flask",
        technology_type="framework",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["REST API", "Web Development"],
    ),
    "django": TaxonomyDependencyMapping(
        technology_name="Django",
        technology_type="framework",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["MVC Architecture", "Object-Relational Mapping", "Web Development"],
    ),
    "sqlalchemy": TaxonomyDependencyMapping(
        technology_name="SQLAlchemy",
        technology_type="library",
        skills=[("Backend Development", "Software Engineering"), ("Database Administration", "Data Engineering")],
        concepts=["Object-Relational Mapping", "Database Access", "Relational Databases"],
    ),
    "pydantic": TaxonomyDependencyMapping(
        technology_name="Pydantic",
        technology_type="library",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["Data Validation", "Type Safety"],
    ),
    "pytest": TaxonomyDependencyMapping(
        technology_name="pytest",
        technology_type="tool",
        skills=[("Testing & Quality Assurance", "Software Engineering")],
        concepts=["Automated Testing", "Unit Testing", "Test Fixtures"],
    ),
    "httpx": TaxonomyDependencyMapping(
        technology_name="HTTPX",
        technology_type="library",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["HTTP Communication", "Asynchronous Programming"],
    ),
    "requests": TaxonomyDependencyMapping(
        technology_name="Requests",
        technology_type="library",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["HTTP Communication"],
    ),
    "celery": TaxonomyDependencyMapping(
        technology_name="Celery",
        technology_type="framework",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["Distributed Task Queues", "Asynchronous Processing"],
    ),
    "redis": TaxonomyDependencyMapping(
        technology_name="Redis",
        technology_type="tool",
        skills=[("Database Administration", "Data Engineering")],
        concepts=["In-Memory Caching", "Key-Value Storage"],
    ),

    # JavaScript / TypeScript (npm)
    "react": TaxonomyDependencyMapping(
        technology_name="React",
        technology_type="framework",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Component-Based UI", "Virtual DOM", "Declarative UI"],
    ),
    "next": TaxonomyDependencyMapping(
        technology_name="Next.js",
        technology_type="framework",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Server-Side Rendering", "Fullstack Web", "Routing"],
    ),
    "express": TaxonomyDependencyMapping(
        technology_name="Express",
        technology_type="framework",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["REST API", "Middleware", "Web Development"],
    ),
    "axios": TaxonomyDependencyMapping(
        technology_name="Axios",
        technology_type="library",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["HTTP Communication", "Promise-Based Architecture"],
    ),
    "jest": TaxonomyDependencyMapping(
        technology_name="Jest",
        technology_type="tool",
        skills=[("Testing & Quality Assurance", "Software Engineering")],
        concepts=["Automated Testing", "Unit Testing", "Mocking"],
    ),
    "tailwindcss": TaxonomyDependencyMapping(
        technology_name="Tailwind CSS",
        technology_type="framework",
        skills=[("Frontend Development", "Software Engineering")],
        concepts=["Utility-First CSS", "Web Styling", "Responsive Layouts"],
    ),

    # Rust (cargo)
    "tokio": TaxonomyDependencyMapping(
        technology_name="Tokio",
        technology_type="runtime",
        skills=[("Systems Programming", "Systems Engineering")],
        concepts=["Asynchronous Programming", "Event Loop", "Concurrency"],
    ),
    "serde": TaxonomyDependencyMapping(
        technology_name="Serde",
        technology_type="library",
        skills=[("Systems Programming", "Systems Engineering")],
        concepts=["Data Serialization", "Type Safety"],
    ),
    "actix-web": TaxonomyDependencyMapping(
        technology_name="Actix-web",
        technology_type="framework",
        skills=[("Backend Development", "Software Engineering")],
        concepts=["REST API", "Asynchronous Programming", "High Performance"],
    ),
}


# ---------------------------------------------------------------------------
# Pre-seeded Skill Relationships (Curated global edges)
# ---------------------------------------------------------------------------

CANONICAL_SKILL_RELATIONSHIPS: List[Tuple[str, str, str]] = [
    ("Backend Development", "Database Administration", "REQUIRES"),
    ("Backend Development", "Testing & Quality Assurance", "REQUIRES"),
    ("Frontend Development", "Testing & Quality Assurance", "RELATED_TO"),
    ("Systems Programming", "Backend Development", "RELATED_TO"),
    ("DevOps", "Backend Development", "RELATED_TO"),
]


# ---------------------------------------------------------------------------
# Resolution Helpers
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Returns lowercased, stripped, canonical key."""
    return name.strip().lower()


def resolve_language_taxonomy(language_name: str) -> Optional[TaxonomyLanguageMapping]:
    """Resolves language name to curated taxonomy mapping if available."""
    key = normalize_name(language_name)
    return CANONICAL_LANGUAGES.get(key)


def resolve_dependency_taxonomy(package_name: str) -> Optional[TaxonomyDependencyMapping]:
    """Resolves package name to curated taxonomy mapping if available."""
    key = normalize_name(package_name)
    return CANONICAL_DEPENDENCIES.get(key)
