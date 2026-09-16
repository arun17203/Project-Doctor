import os
from typing import Dict, List, Any, Set, Tuple, Optional

from backend.app.analyzers.architecture.parser import extract_file_imports, RawImport
from backend.app.analyzers.architecture.resolver import ImportResolver
from backend.app.analyzers.architecture.classifier import classify_layer
from backend.app.analyzers.architecture.cycles import detect_cycles

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "vendor",
    "target",
    ".next",
    ".turbo",
}

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}


class ArchitectureEngine:
    def __init__(self, max_nodes: int = 500):
        self.max_nodes = max_nodes

    def analyze_project(self, storage_path: str) -> Dict[str, Any]:
        """Perform static architecture dependency and cycle analysis across source files.
        Zero code execution.
        """
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"Project storage path does not exist: {storage_path}")

        # 1. Discover all candidate source files
        source_files: Dict[str, Dict[str, Any]] = {}
        all_relative_paths: Set[str] = set()

        for root, dirs, files in os.walk(storage_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for filename in files:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, storage_path).replace("\\", "/")
                all_relative_paths.add(rel_path)

                _, ext = os.path.splitext(filename.lower())
                if ext in SUPPORTED_EXTENSIONS:
                    lang = SUPPORTED_EXTENSIONS[ext]
                    source_files[rel_path] = {
                        "abs_path": abs_path,
                        "rel_path": rel_path,
                        "name": filename,
                        "language": lang,
                        "directory": os.path.dirname(rel_path) or "root",
                    }

        # 2. Build local import resolver
        resolver = ImportResolver(all_relative_paths)

        # 3. Parse imports and resolve edges
        node_file_paths = list(source_files.keys())
        # Cap if excessive to keep graph responsive
        if len(node_file_paths) > self.max_nodes:
            node_file_paths = node_file_paths[:self.max_nodes]

        edges_raw: List[Dict[str, Any]] = []
        file_imports_count: Dict[str, int] = {f: 0 for f in node_file_paths}
        file_imported_by_count: Dict[str, int] = {f: 0 for f in node_file_paths}
        seen_edges: Set[Tuple[str, str]] = set()

        for rel_path in node_file_paths:
            file_meta = source_files[rel_path]
            content = self._read_file(file_meta["abs_path"])
            if not content:
                continue

            raw_imports = extract_file_imports(content, rel_path, file_meta["language"])
            for imp in raw_imports:
                target_file = resolver.resolve(imp, file_meta["language"])
                if target_file and target_file in source_files and target_file != rel_path:
                    edge_key = (rel_path, target_file)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges_raw.append({
                            "source": rel_path,
                            "target": target_file,
                            "relationship_type": "imports",
                            "raw_import": imp.imported_module,
                            "line_number": imp.line_number,
                            "is_circular": False,
                        })
                        file_imports_count[rel_path] = file_imports_count.get(rel_path, 0) + 1
                        file_imported_by_count[target_file] = file_imported_by_count.get(target_file, 0) + 1

        # 4. Detect circular dependencies
        graph_edge_tuples = [(e["source"], e["target"]) for e in edges_raw]
        detected_cycles = detect_cycles(node_file_paths, graph_edge_tuples, max_cycles=50)

        # Flag circular edges and nodes
        circular_node_set: Set[str] = set()
        circular_edge_pairs: Set[Tuple[str, str]] = set()

        for cycle in detected_cycles:
            for i in range(len(cycle) - 1):
                u = cycle[i]
                v = cycle[i + 1]
                circular_node_set.add(u)
                circular_node_set.add(v)
                circular_edge_pairs.add((u, v))

        for edge in edges_raw:
            if (edge["source"], edge["target"]) in circular_edge_pairs:
                edge["is_circular"] = True

        # 5. Build Node objects with heuristic layer classification & metrics
        nodes_result: List[Dict[str, Any]] = []
        by_layer: Dict[str, int] = {}
        by_language: Dict[str, int] = {}
        modules_set: Set[str] = set()

        for rel_path in node_file_paths:
            file_meta = source_files[rel_path]
            layer = classify_layer(rel_path)
            by_layer[layer] = by_layer.get(layer, 0) + 1
            by_language[file_meta["language"]] = by_language.get(file_meta["language"], 0) + 1

            dir_part = file_meta["directory"]
            if dir_part != "root":
                # First 2 directory segments represent primary module
                primary_module = "/".join(dir_part.split("/")[:2])
                modules_set.add(primary_module)
            else:
                modules_set.add("root")

            node_data = {
                "file_path": rel_path,
                "name": file_meta["name"],
                "language": file_meta["language"],
                "layer": layer,
                "node_type": "file",
                "directory": file_meta["directory"],
                "metrics": {
                    "in_degree": file_imported_by_count.get(rel_path, 0),
                    "out_degree": file_imports_count.get(rel_path, 0),
                    "is_in_cycle": rel_path in circular_node_set,
                },
            }
            nodes_result.append(node_data)

        # 6. Generate Issues for Circular Dependencies
        generated_issues: List[Dict[str, Any]] = []
        for idx, cycle in enumerate(detected_cycles, start=1):
            chain_str = " -> ".join(cycle)
            root_file = cycle[0]
            generated_issues.append({
                "category": "architecture",
                "issue_type": "circular_dependency",
                "severity": "HIGH",
                "file_path": root_file,
                "message": f"Circular dependency detected: {chain_str}",
                "description": (
                    f"A cyclic dependency loop was discovered in the module graph: {chain_str}. "
                    "Circular imports cause tight coupling, unexpected initialization order side effects, and make testing difficult."
                ),
                "recommendation": (
                    "Break the cycle by applying the Dependency Inversion Principle (DIP): "
                    "extract shared types or helper functions into an independent module, or use dependency injection."
                ),
            })

        # 7. Aggregate Summary Metrics
        metrics = {
            "by_layer": by_layer,
            "by_language": by_language,
            "modules_count": len(modules_set),
            "modules_list": sorted(list(modules_set)),
            "cycles_summary": [" -> ".join(c) for c in detected_cycles],
            "total_files_analyzed": len(source_files),
        }

        return {
            "node_count": len(nodes_result),
            "edge_count": len(edges_raw),
            "cycle_count": len(detected_cycles),
            "metrics": metrics,
            "nodes": nodes_result,
            "edges": edges_raw,
            "cycles": detected_cycles,
            "issues": generated_issues,
        }

    def _read_file(self, abs_path: str) -> Optional[str]:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None


def run_architecture_analysis(project, scan, db) -> Dict[str, Any]:
    """Helper entrypoint for running static architecture analysis on a project."""
    engine = ArchitectureEngine()
    storage_path = project.storage_path
    if not storage_path or not os.path.exists(storage_path):
        raise ValueError(f"Project storage path not found: {storage_path}")

    return engine.analyze_project(storage_path)
