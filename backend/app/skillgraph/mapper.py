"""
DevTwin SkillGraph — Deterministic Mapper
Transforms an in-memory MiningResult into normalized domain entities,
taxonomic nodes, edges, and provenance-backed observations.
"""

import uuid
from typing import Dict, List, Set, Tuple

from app.mining.models import MiningResult
from app.skillgraph.models import (
    ConceptData,
    ObservationData,
    RepositoryDependencyData,
    RepositoryLanguageData,
    SkillData,
    SkillGraphMapping,
    TechnologyData,
)
from app.skillgraph.taxonomy import (
    CANONICAL_SKILL_RELATIONSHIPS,
    resolve_dependency_taxonomy,
    resolve_language_taxonomy,
)


def map_mining_result_to_graph(
    mining_result: MiningResult,
    repository_id: uuid.UUID,
    analysis_run_id: uuid.UUID,
) -> SkillGraphMapping:
    """
    Performs pure, deterministic mapping from MiningResult to SkillGraph entities and relationships.
    Does NOT execute repository code or perform I/O.
    """
    languages_dict: Dict[str, RepositoryLanguageData] = {}
    dependencies_dict: Dict[Tuple[str, str], RepositoryDependencyData] = {}
    observations: List[ObservationData] = []

    technologies_dict: Dict[str, TechnologyData] = {}
    skills_dict: Dict[str, SkillData] = {}
    concepts_dict: Dict[str, ConceptData] = {}

    skill_technologies_set: Set[Tuple[str, str]] = set()
    skill_concepts_set: Set[Tuple[str, str]] = set()
    technology_concepts_set: Set[Tuple[str, str]] = set()
    skill_relationships_set: Set[Tuple[str, str, str]] = set()

    # -----------------------------------------------------------------------
    # 1. Map Languages
    # -----------------------------------------------------------------------
    for lb in mining_result.languages:
        # Repository Language
        languages_dict[lb.language] = RepositoryLanguageData(
            language=lb.language,
            bytes=lb.bytes_count,
        )

        # Factual Observation
        observations.append(
            ObservationData(
                type="LANGUAGE_DETECTED",
                source_tool="mining-classifier",
                source_reference={
                    "language": lb.language,
                    "bytes": lb.bytes_count,
                    "files": lb.files_count,
                    "percentage": lb.percentage,
                },
                confidence=1.0,
            )
        )

        # Taxonomic Resolution
        lang_tax = resolve_language_taxonomy(lb.language)
        if lang_tax:
            tech_name = lang_tax.technology_name
            technologies_dict[tech_name] = TechnologyData(
                name=tech_name,
                type=lang_tax.technology_type,
            )
            for skill_name, skill_domain in lang_tax.skills:
                skills_dict[skill_name] = SkillData(name=skill_name, domain=skill_domain)
                skill_technologies_set.add((skill_name, tech_name))

            for concept_name in lang_tax.concepts:
                concepts_dict[concept_name] = ConceptData(name=concept_name)
                technology_concepts_set.add((tech_name, concept_name))
        else:
            # Unmapped language: create canonical technology entry safely without hallucinating skills
            cleaned_tech_name = lb.language.strip()
            technologies_dict[cleaned_tech_name] = TechnologyData(
                name=cleaned_tech_name,
                type="language",
            )

    # -----------------------------------------------------------------------
    # 2. Map Manifest Dependencies
    # -----------------------------------------------------------------------
    for manifest in mining_result.manifests:
        for dep in manifest.dependencies:
            dep_key = (manifest.manifest_type, dep.name)
            dependencies_dict[dep_key] = RepositoryDependencyData(
                ecosystem=manifest.manifest_type,
                package_name=dep.name,
                version_constraint=dep.version_spec,
            )

            observations.append(
                ObservationData(
                    type="DEPENDENCY_FOUND",
                    source_tool="manifest-parser",
                    source_reference={
                        "manifest": manifest.file_path,
                        "ecosystem": manifest.manifest_type,
                        "package": dep.name,
                        "version": dep.version_spec,
                        "dependency_type": dep.dependency_type,
                    },
                    confidence=1.0,
                )
            )

            dep_tax = resolve_dependency_taxonomy(dep.name)
            if dep_tax:
                tech_name = dep_tax.technology_name
                technologies_dict[tech_name] = TechnologyData(
                    name=tech_name,
                    type=dep_tax.technology_type,
                )
                for skill_name, skill_domain in dep_tax.skills:
                    skills_dict[skill_name] = SkillData(name=skill_name, domain=skill_domain)
                    skill_technologies_set.add((skill_name, tech_name))

                for concept_name in dep_tax.concepts:
                    concepts_dict[concept_name] = ConceptData(name=concept_name)
                    technology_concepts_set.add((tech_name, concept_name))
            else:
                # Unmapped package: safe library entry with no ungrounded claims
                clean_name = dep.name.strip().lower()
                technologies_dict[clean_name] = TechnologyData(
                    name=clean_name,
                    type="library",
                )

    # -----------------------------------------------------------------------
    # 3. Map AST Summaries (Python in Step 6C/6D)
    # -----------------------------------------------------------------------
    for ast_file in mining_result.ast_summaries:
        if ast_file.parse_error:
            observations.append(
                ObservationData(
                    type="SYNTAX_ERROR_OBSERVED",
                    source_tool="ast-parser",
                    source_reference={
                        "file": ast_file.file_path,
                        "error": ast_file.parse_error,
                    },
                    confidence=1.0,
                )
            )

        for cls in ast_file.classes:
            observations.append(
                ObservationData(
                    type="CLASS_DEFINED",
                    source_tool="ast-parser",
                    source_reference={
                        "file": ast_file.file_path,
                        "class": cls.name,
                        "line": cls.line_number,
                        "bases": cls.base_classes,
                        "methods_count": cls.methods_count,
                        "has_docstring": cls.has_docstring,
                    },
                    confidence=1.0,
                )
            )
            concepts_dict["Object-Oriented Programming"] = ConceptData(name="Object-Oriented Programming")

        for fn in ast_file.functions:
            observations.append(
                ObservationData(
                    type="FUNCTION_DEFINED",
                    source_tool="ast-parser",
                    source_reference={
                        "file": ast_file.file_path,
                        "function": fn.name,
                        "line": fn.line_number,
                        "is_async": fn.is_async,
                        "args_count": fn.args_count,
                        "has_docstring": fn.has_docstring,
                    },
                    confidence=1.0,
                )
            )
            if fn.is_async:
                concepts_dict["Asynchronous Programming"] = ConceptData(name="Asynchronous Programming")
            if fn.has_docstring:
                concepts_dict["Code Documentation"] = ConceptData(name="Code Documentation")

        for imp in ast_file.imports:
            observations.append(
                ObservationData(
                    type="MODULE_IMPORTED",
                    source_tool="ast-parser",
                    source_reference={
                        "file": ast_file.file_path,
                        "module": imp.module,
                        "names": imp.names,
                        "is_from": imp.is_from,
                        "line": imp.line_number,
                    },
                    confidence=1.0,
                )
            )

    # -----------------------------------------------------------------------
    # 4. Map Warnings
    # -----------------------------------------------------------------------
    for warn in mining_result.warnings:
        observations.append(
            ObservationData(
                type="MINING_WARNING",
                source_tool="mining-coordinator",
                source_reference={
                    "file": warn.file_path,
                    "warning_code": warn.warning_code,
                    "message": warn.message,
                },
                confidence=1.0,
            )
        )

    # -----------------------------------------------------------------------
    # 5. Canonical Skill Relationships (Edges between active skills)
    # -----------------------------------------------------------------------
    for src_skill, tgt_skill, rel_type in CANONICAL_SKILL_RELATIONSHIPS:
        if src_skill in skills_dict and tgt_skill in skills_dict:
            skill_relationships_set.add((src_skill, tgt_skill, rel_type))

    # -----------------------------------------------------------------------
    # 6. Deterministic Sorting & Assembly
    # -----------------------------------------------------------------------
    sorted_languages = sorted(languages_dict.values(), key=lambda l: l.language)
    sorted_dependencies = sorted(dependencies_dict.values(), key=lambda d: (d.ecosystem, d.package_name))
    sorted_technologies = sorted(technologies_dict.values(), key=lambda t: t.name)
    sorted_skills = sorted(skills_dict.values(), key=lambda s: s.name)
    sorted_concepts = sorted(concepts_dict.values(), key=lambda c: c.name)

    sorted_skill_tech = sorted(list(skill_technologies_set), key=lambda x: (x[0], x[1]))
    sorted_skill_concepts = sorted(list(skill_concepts_set), key=lambda x: (x[0], x[1]))
    sorted_tech_concepts = sorted(list(technology_concepts_set), key=lambda x: (x[0], x[1]))
    sorted_skill_rels = sorted(list(skill_relationships_set), key=lambda x: (x[0], x[1], x[2]))

    return SkillGraphMapping(
        languages=sorted_languages,
        dependencies=sorted_dependencies,
        observations=observations,
        technologies=sorted_technologies,
        skills=sorted_skills,
        concepts=sorted_concepts,
        skill_technologies=sorted_skill_tech,
        skill_concepts=sorted_skill_concepts,
        technology_concepts=sorted_tech_concepts,
        skill_relationships=sorted_skill_rels,
    )
