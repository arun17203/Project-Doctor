import json
import re
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Any

# Regex for Python requirements line (PEP 508 / pip requirements format)
# Matches: name[extras] (==|>=|<=|~=|!=|>|<) version
PYTHON_REQ_REGEX = re.compile(
    r'^\s*([a-zA-Z0-9_\-\.]+)(?:\[[^\]]*\])?\s*([=><~^!]+)?\s*([a-zA-Z0-9_\-\.\*]+)?'
)


@dataclass
class ParsedDependency:
    name: str
    ecosystem: str  # "PyPI", "npm", "Maven"
    declared_version: Optional[str]
    resolved_version: Optional[str]
    dependency_type: str  # "direct", "dev", "transitive", "peer"
    manifest_file: str


def parse_requirements_txt(content: str, file_path: str) -> List[ParsedDependency]:
    """Parse pip requirements.txt or requirements-dev.txt file."""
    dependencies: List[ParsedDependency] = []
    is_dev = "dev" in file_path.lower() or "test" in file_path.lower()
    dep_type = "dev" if is_dev else "direct"

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r", "-i", "-f", "--", "-c")):
            continue

        # Strip inline comments and environment markers
        line = line.split("#")[0].strip()
        line = line.split(";")[0].strip()
        if not line:
            continue

        # Match package name, optional extras, and the rest as version specifier
        m = re.match(r'^\s*([a-zA-Z0-9_\-\.]+)(?:\[[^\]]*\])?\s*(.*)$', line)
        if m:
            pkg_name = m.group(1).strip()
            spec = m.group(2).strip()
            declared = spec if spec else None
            resolved = None

            if declared:
                if declared.startswith("=="):
                    v_match = re.match(r'^==\s*([a-zA-Z0-9_\-\.\+]+)', declared)
                    if v_match:
                        resolved = v_match.group(1)

            dependencies.append(
                ParsedDependency(
                    name=pkg_name,
                    ecosystem="PyPI",
                    declared_version=declared,
                    resolved_version=resolved,
                    dependency_type=dep_type,
                    manifest_file=file_path,
                )
            )

    return dependencies


def parse_pyproject_toml(content: str, file_path: str) -> List[ParsedDependency]:
    """Parse PEP 621 / Poetry dependencies in pyproject.toml."""
    dependencies: List[ParsedDependency] = []
    try:
        data = tomllib.loads(content)
    except Exception:
        return []

    # 1. PEP 621 project.dependencies
    project_deps = data.get("project", {}).get("dependencies", [])
    if isinstance(project_deps, list):
        for item in project_deps:
            if isinstance(item, str):
                item_clean = item.split(";")[0].strip()
                m = PYTHON_REQ_REGEX.match(item_clean)
                if m:
                    name = m.group(1).strip()
                    op = m.group(2)
                    ver = m.group(3)
                    declared = f"{op}{ver}" if op and ver else None
                    resolved = ver if op == "==" else None
                    dependencies.append(
                        ParsedDependency(
                            name=name,
                            ecosystem="PyPI",
                            declared_version=declared,
                            resolved_version=resolved,
                            dependency_type="direct",
                            manifest_file=file_path,
                        )
                    )

    # 2. PEP 621 project.optional-dependencies (e.g. dev, test)
    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    if isinstance(opt_deps, dict):
        for group_name, group_list in opt_deps.items():
            if isinstance(group_list, list):
                for item in group_list:
                    if isinstance(item, str):
                        item_clean = item.split(";")[0].strip()
                        m = PYTHON_REQ_REGEX.match(item_clean)
                        if m:
                            name = m.group(1).strip()
                            op = m.group(2)
                            ver = m.group(3)
                            declared = f"{op}{ver}" if op and ver else None
                            resolved = ver if op == "==" else None
                            dependencies.append(
                                ParsedDependency(
                                    name=name,
                                    ecosystem="PyPI",
                                    declared_version=declared,
                                    resolved_version=resolved,
                                    dependency_type="dev",
                                    manifest_file=file_path,
                                )
                            )

    # 3. Poetry tool.poetry.dependencies
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if isinstance(poetry_deps, dict):
        for pkg, spec in poetry_deps.items():
            if pkg.lower() == "python":
                continue
            declared = None
            resolved = None
            if isinstance(spec, str):
                declared = spec
                if spec.startswith("=="):
                    resolved = spec[2:]
                elif not spec.startswith(("^", "~", ">", "<", "!")):
                    resolved = spec
            elif isinstance(spec, dict):
                declared = spec.get("version")

            dependencies.append(
                ParsedDependency(
                    name=pkg,
                    ecosystem="PyPI",
                    declared_version=declared,
                    resolved_version=resolved,
                    dependency_type="direct",
                    manifest_file=file_path,
                )
            )

    # 4. Poetry legacy dev-dependencies
    poetry_dev = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
    if isinstance(poetry_dev, dict):
        for pkg, spec in poetry_dev.items():
            declared = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
            dependencies.append(
                ParsedDependency(
                    name=pkg,
                    ecosystem="PyPI",
                    declared_version=declared,
                    resolved_version=None,
                    dependency_type="dev",
                    manifest_file=file_path,
                )
            )

    # 5. Poetry groups: tool.poetry.group.<group_name>.dependencies
    poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
    if isinstance(poetry_groups, dict):
        for grp_name, grp_data in poetry_groups.items():
            if isinstance(grp_data, dict):
                grp_deps = grp_data.get("dependencies", {})
                is_dev = "dev" in grp_name.lower() or "test" in grp_name.lower()
                dep_type = "dev" if is_dev else "direct"
                if isinstance(grp_deps, dict):
                    for pkg, spec in grp_deps.items():
                        if pkg.lower() == "python":
                            continue
                        declared = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
                        dependencies.append(
                            ParsedDependency(
                                name=pkg,
                                ecosystem="PyPI",
                                declared_version=declared,
                                resolved_version=None,
                                dependency_type=dep_type,
                                manifest_file=file_path,
                            )
                        )

    return dependencies


def parse_pipfile(content: str, file_path: str) -> List[ParsedDependency]:
    """Parse Pipfile dependencies."""
    dependencies: List[ParsedDependency] = []
    try:
        data = tomllib.loads(content)
    except Exception:
        return []

    for section, dep_type in [("packages", "direct"), ("dev-packages", "dev")]:
        pkgs = data.get(section, {})
        if isinstance(pkgs, dict):
            for name, spec in pkgs.items():
                declared = spec if isinstance(spec, str) and spec != "*" else None
                resolved = None
                if declared and declared.startswith("=="):
                    resolved = declared[2:]
                dependencies.append(
                    ParsedDependency(
                        name=name,
                        ecosystem="PyPI",
                        declared_version=declared,
                        resolved_version=resolved,
                        dependency_type=dep_type,
                        manifest_file=file_path,
                    )
                )

    return dependencies


def parse_package_json(content: str, file_path: str) -> List[ParsedDependency]:
    """Parse Node.js package.json."""
    dependencies: List[ParsedDependency] = []
    try:
        data = json.loads(content)
    except Exception:
        return []

    sections = [
        ("dependencies", "direct"),
        ("devDependencies", "dev"),
        ("peerDependencies", "peer"),
    ]

    for section_name, dep_type in sections:
        section = data.get(section_name, {})
        if isinstance(section, dict):
            for name, version_spec in section.items():
                if not isinstance(version_spec, str):
                    continue
                # Clean version spec
                clean_spec = version_spec.strip()
                # Check if exact version
                resolved = None
                if re.match(r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9_\.]+)?$', clean_spec):
                    resolved = clean_spec

                dependencies.append(
                    ParsedDependency(
                        name=name,
                        ecosystem="npm",
                        declared_version=clean_spec,
                        resolved_version=resolved,
                        dependency_type=dep_type,
                        manifest_file=file_path,
                    )
                )

    return dependencies


def parse_package_lock_json(
    content: str,
    file_path: str,
    direct_names: Optional[Set[str]] = None,
) -> List[ParsedDependency]:
    """Parse package-lock.json (v1, v2, and v3 supported).
    Distinguishes direct vs transitive dependencies.
    """
    dependencies: List[ParsedDependency] = []
    direct_names = direct_names or set()

    try:
        data = json.loads(content)
    except Exception:
        return []

    lockfile_version = data.get("lockfileVersion", 1)

    # v2 / v3 lockfiles have a "packages" dict where keys are "node_modules/name"
    if lockfile_version >= 2 and "packages" in data and isinstance(data["packages"], dict):
        for key, info in data["packages"].items():
            if not key or not key.startswith("node_modules/"):
                continue

            # Extract top-level or sub-package name
            # E.g. "node_modules/express" -> "express"
            # E.g. "node_modules/@types/node" -> "@types/node"
            # E.g. "node_modules/a/node_modules/b" -> "b" (transitive)
            parts = key.split("node_modules/")
            pkg_name = parts[-1].strip()
            if not pkg_name or not isinstance(info, dict):
                continue

            version = info.get("version")
            is_dev = bool(info.get("dev", False))
            is_transitive = len(parts) > 2 or pkg_name not in direct_names

            if pkg_name in direct_names:
                dep_type = "dev" if is_dev else "direct"
            else:
                dep_type = "transitive"

            dependencies.append(
                ParsedDependency(
                    name=pkg_name,
                    ecosystem="npm",
                    declared_version=None,
                    resolved_version=version,
                    dependency_type=dep_type,
                    manifest_file=file_path,
                )
            )

    # Fallback to v1 "dependencies" dict if packages not present
    elif "dependencies" in data and isinstance(data["dependencies"], dict):
        def _walk_v1(deps_dict: dict, depth: int = 0):
            for name, info in deps_dict.items():
                if not isinstance(info, dict):
                    continue
                version = info.get("version")
                is_dev = bool(info.get("dev", False))
                if depth == 0 and name in direct_names:
                    dep_type = "dev" if is_dev else "direct"
                else:
                    dep_type = "transitive"

                dependencies.append(
                    ParsedDependency(
                        name=name,
                        ecosystem="npm",
                        declared_version=None,
                        resolved_version=version,
                        dependency_type=dep_type,
                        manifest_file=file_path,
                    )
                )
                sub_deps = info.get("dependencies")
                if isinstance(sub_deps, dict):
                    _walk_v1(sub_deps, depth + 1)

        _walk_v1(data["dependencies"])

    return dependencies


def parse_pom_xml(content: str, file_path: str) -> List[ParsedDependency]:
    """Parse Java Maven pom.xml file."""
    dependencies: List[ParsedDependency] = []
    try:
        root = ET.fromstring(content)
    except Exception:
        return []

    # Helper to strip namespace from tags
    def strip_ns(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    # Find all dependencies
    for elem in root.iter():
        if strip_ns(elem.tag) == "dependency":
            group_id = ""
            artifact_id = ""
            version = None
            scope = "compile"

            for child in elem:
                c_tag = strip_ns(child.tag)
                text = (child.text or "").strip()
                if c_tag == "groupId":
                    group_id = text
                elif c_tag == "artifactId":
                    artifact_id = text
                elif c_tag == "version":
                    version = text
                elif c_tag == "scope":
                    scope = text.lower()

            if group_id and artifact_id:
                pkg_name = f"{group_id}:{artifact_id}"
                dep_type = "dev" if scope in {"test", "provided"} else "direct"
                # Check if version is a property placeholder like ${project.version}
                resolved_ver = version if version and not version.startswith("${") else None

                dependencies.append(
                    ParsedDependency(
                        name=pkg_name,
                        ecosystem="Maven",
                        declared_version=version,
                        resolved_version=resolved_ver,
                        dependency_type=dep_type,
                        manifest_file=file_path,
                    )
                )

    return dependencies
