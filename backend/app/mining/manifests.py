"""
DevTwin Mining Engine — Defensive Manifest Extraction
Extracts declared dependencies from package.json, requirements.txt, and Cargo.toml.
"""

import json
import logging
import re
import tomllib
from pathlib import Path
from typing import List, Optional, Tuple

from app.mining.constants import MAX_DEPENDENCIES_PER_MANIFEST, MAX_MANIFEST_FILE_BYTES
from app.mining.models import ManifestDependency, ManifestSummary, MiningWarning

logger = logging.getLogger(__name__)

# Basic pip requirement specifier regex: package_name followed optionally by version spec
PIP_REQ_REGEX = re.compile(
    r"^([A-Za-z0-9_.\-]+)\s*([~=<>!].*)?$",
    re.IGNORECASE,
)


def parse_package_json(
    content: str,
    rel_path: str,
) -> Tuple[Optional[ManifestSummary], List[MiningWarning]]:
    """
    Parses package.json to extract declared dependencies and metadata.
    """
    warnings: List[MiningWarning] = []
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            warnings.append(
                MiningWarning(
                    file_path=rel_path,
                    warning_code="MANIFEST_INVALID_JSON",
                    message="package.json root is not a JSON object.",
                )
            )
            return None, warnings

        project_name = data.get("name")
        if not isinstance(project_name, str):
            project_name = None

        project_version = data.get("version")
        if not isinstance(project_version, str):
            project_version = None

        deps: List[ManifestDependency] = []

        def extract_deps(dep_dict: dict, dep_type: str):
            if not isinstance(dep_dict, dict):
                return
            for name, ver in dep_dict.items():
                if len(deps) >= MAX_DEPENDENCIES_PER_MANIFEST:
                    break
                if isinstance(name, str):
                    ver_str = str(ver) if ver is not None else None
                    deps.append(
                        ManifestDependency(
                            name=name.strip(),
                            version_spec=ver_str,
                            dependency_type=dep_type,
                        )
                    )

        extract_deps(data.get("dependencies", {}), "runtime")
        extract_deps(data.get("devDependencies", {}), "dev")
        extract_deps(data.get("peerDependencies", {}), "peer")

        deps.sort(key=lambda d: (d.name, d.dependency_type))

        summary = ManifestSummary(
            file_path=rel_path,
            manifest_type="npm",
            project_name=project_name,
            project_version=project_version,
            dependencies_count=len(deps),
            dependencies=deps,
        )
        return summary, warnings

    except json.JSONDecodeError as exc:
        warnings.append(
            MiningWarning(
                file_path=rel_path,
                warning_code="MANIFEST_SYNTAX_ERROR",
                message=f"JSON decode error in package.json at line {exc.lineno}.",
            )
        )
        return None, warnings
    except Exception as exc:
        warnings.append(
            MiningWarning(
                file_path=rel_path,
                warning_code="MANIFEST_PARSE_ERROR",
                message=f"Unexpected error parsing package.json: {type(exc).__name__}.",
            )
        )
        return None, warnings


def parse_requirements_txt(
    content: str,
    rel_path: str,
) -> Tuple[Optional[ManifestSummary], List[MiningWarning]]:
    """
    Parses requirements.txt to extract declared python dependencies.
    """
    warnings: List[MiningWarning] = []
    deps: List[ManifestDependency] = []

    try:
        lines = content.splitlines()
        for line in lines:
            if len(deps) >= MAX_DEPENDENCIES_PER_MANIFEST:
                break
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Strip inline comments
            if " #" in stripped:
                stripped = stripped.split(" #", 1)[0].strip()

            # Ignore pip flags (-r, -e, -f, -i, etc.)
            if stripped.startswith("-") or stripped.startswith("--"):
                continue

            # Match package name and version
            match = PIP_REQ_REGEX.match(stripped)
            if match:
                pkg_name = match.group(1).strip()
                ver_spec = match.group(2).strip() if match.group(2) else None
                deps.append(
                    ManifestDependency(
                        name=pkg_name,
                        version_spec=ver_spec,
                        dependency_type="runtime",
                    )
                )
            else:
                # Malformed line: record warning if non-trivial
                if len(stripped) > 0 and not stripped.startswith("."):
                    warnings.append(
                        MiningWarning(
                            file_path=rel_path,
                            warning_code="MANIFEST_LINE_SKIPPED",
                            message=f"Skipped unparseable requirements line: {stripped[:50]}.",
                        )
                    )

        deps.sort(key=lambda d: d.name)

        summary = ManifestSummary(
            file_path=rel_path,
            manifest_type="pip",
            project_name=None,
            project_version=None,
            dependencies_count=len(deps),
            dependencies=deps,
        )
        return summary, warnings

    except Exception as exc:
        warnings.append(
            MiningWarning(
                file_path=rel_path,
                warning_code="MANIFEST_PARSE_ERROR",
                message=f"Unexpected error parsing requirements.txt: {type(exc).__name__}.",
            )
        )
        return None, warnings


def parse_cargo_toml(
    content: str,
    rel_path: str,
) -> Tuple[Optional[ManifestSummary], List[MiningWarning]]:
    """
    Parses Cargo.toml to extract Rust crate dependencies and package metadata.
    """
    warnings: List[MiningWarning] = []
    try:
        data = tomllib.loads(content)
        package_info = data.get("package", {})
        project_name = package_info.get("name") if isinstance(package_info, dict) else None
        project_version = package_info.get("version") if isinstance(package_info, dict) else None

        deps: List[ManifestDependency] = []

        def extract_cargo_deps(dep_dict: dict, dep_type: str):
            if not isinstance(dep_dict, dict):
                return
            for name, val in dep_dict.items():
                if len(deps) >= MAX_DEPENDENCIES_PER_MANIFEST:
                    break
                if not isinstance(name, str):
                    continue

                ver_str: Optional[str] = None
                if isinstance(val, str):
                    ver_str = val
                elif isinstance(val, dict):
                    if "version" in val and isinstance(val["version"], str):
                        ver_str = val["version"]
                    elif "path" in val:
                        ver_str = f"path:{val['path']}"
                    elif "git" in val:
                        ver_str = "git"

                deps.append(
                    ManifestDependency(
                        name=name.strip(),
                        version_spec=ver_str,
                        dependency_type=dep_type,
                    )
                )

        extract_cargo_deps(data.get("dependencies", {}), "runtime")
        extract_cargo_deps(data.get("dev-dependencies", {}), "dev")
        extract_cargo_deps(data.get("build-dependencies", {}), "dev")

        deps.sort(key=lambda d: (d.name, d.dependency_type))

        summary = ManifestSummary(
            file_path=rel_path,
            manifest_type="cargo",
            project_name=project_name,
            project_version=project_version,
            dependencies_count=len(deps),
            dependencies=deps,
        )
        return summary, warnings

    except tomllib.TOMLDecodeError as exc:
        warnings.append(
            MiningWarning(
                file_path=rel_path,
                warning_code="MANIFEST_SYNTAX_ERROR",
                message=f"TOML decode error in Cargo.toml: {exc}.",
            )
        )
        return None, warnings
    except Exception as exc:
        warnings.append(
            MiningWarning(
                file_path=rel_path,
                warning_code="MANIFEST_PARSE_ERROR",
                message=f"Unexpected error parsing Cargo.toml: {type(exc).__name__}.",
            )
        )
        return None, warnings


def extract_manifest_if_applicable(
    file_path: Path,
    rel_path: str,
) -> Tuple[Optional[ManifestSummary], List[MiningWarning]]:
    """
    Inspects file name; if recognized as a supported manifest, extracts dependencies.
    Enforces maximum file size budget before reading.
    """
    file_name = file_path.name.lower()
    is_manifest = (
        file_name == "package.json"
        or file_name == "cargo.toml"
        or file_name == "requirements.txt"
        or (file_name.startswith("requirements") and file_name.endswith(".txt"))
    )

    if not is_manifest:
        return None, []

    try:
        size = file_path.stat().st_size
        if size > MAX_MANIFEST_FILE_BYTES:
            return None, [
                MiningWarning(
                    file_path=rel_path,
                    warning_code="MANIFEST_OVERSIZED",
                    message=f"Manifest exceeds size limit ({size} > {MAX_MANIFEST_FILE_BYTES} bytes).",
                )
            ]

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if file_name == "package.json":
            return parse_package_json(content, rel_path)
        elif file_name == "cargo.toml":
            return parse_cargo_toml(content, rel_path)
        else:
            return parse_requirements_txt(content, rel_path)

    except Exception as exc:
        return None, [
            MiningWarning(
                file_path=rel_path,
                warning_code="MANIFEST_READ_ERROR",
                message=f"Could not read manifest {rel_path}: {type(exc).__name__}.",
            )
        ]
