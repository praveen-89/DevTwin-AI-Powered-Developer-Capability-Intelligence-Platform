# 07. SkillGraph

## Overview
SkillGraph is the relational intelligence layer that maps the connections between developers, their skills, underlying concepts, and supporting evidence. It answers the question: "What technical knowledge and technologies are represented in the developer's evidence, and how are they related?"

## Core Nodes
- **Developer**: The user being analyzed.
- **Skill**: A specific, applicable ability (e.g., "Frontend Development", "Database Administration").
- **Concept**: Theoretical or structural knowledge (e.g., "Containerization", "REST").
- **Technology**: A specific tool, language, or framework (e.g., "React", "PostgreSQL", "Docker").
- **Project**: A logical grouping of work.
- **Repository**: The physical code repository.
- **Evidence**: A specific extracted data point.
- **Capability**: The inferred state linking a developer to a skill/technology.

## Core Relationships
- `(Developer)-[HAS_SKILL]->(Capability)`
- `(Developer)-[HAS_REPOSITORY]->(Repository)`
- `(Developer)-[HAS_PROJECT]->(Project)`
- `(Repository)-[USES_TECHNOLOGY]->(Technology)`
- `(Technology)-[INVOLVES_CONCEPT]->(Concept)`
- `(Evidence)-[SUPPORTS_CAPABILITY]->(Capability)`
- `(Technology)-[RELATED_TO]->(Technology)`
- `(Technology)-[REQUIRES]->(Concept/Technology)`
- `(Skill)-[PART_OF]->(Domain)`

## Example Path
`Docker (Technology) -> Containerization (Concept) -> DevOps (Skill)`

If evidence points to a concrete Docker implementation in a repository, the graph infers support for the broader Containerization concept and DevOps skill.

## Database Implementation (Minor Project)
For the Minor MVP, the SkillGraph is implemented using a relational database (PostgreSQL/Supabase) designed to support graph-like queries via junction tables. A dedicated graph database (like Neo4j) is deferred unless performance or complex traversal requirements justify its inclusion in the Major roadmap.
