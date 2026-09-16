from typing import List, Dict, Set, Tuple


def canonicalize_cycle(cycle: List[str]) -> Tuple[str, ...]:
    """Rotate cycle list so the lexicographically smallest element is first.
    E.g. ['b', 'c', 'a', 'b'] -> ('a', 'b', 'c', 'a')
    """
    if len(cycle) < 2:
        return tuple(cycle)
    # The last element is identical to the first in a closed cycle
    nodes = cycle[:-1]
    min_idx = min(range(len(nodes)), key=lambda i: nodes[i])
    rotated = nodes[min_idx:] + nodes[:min_idx]
    return tuple(rotated + [rotated[0]])


def detect_cycles(nodes: List[str], edges: List[Tuple[str, str]], max_cycles: int = 50) -> List[List[str]]:
    """Detect simple cycles in a directed graph using depth-first search.
    Args:
        nodes: list of node identifiers (file paths)
        edges: list of (source, target) tuples
        max_cycles: limit to prevent explosion in dense/complex graphs
    Returns:
        List of cycle paths e.g. [['a.py', 'b.py', 'a.py'], ...]
    """
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    for u, v in edges:
        if u in adj and v in adj:
            adj[u].append(v)

    visited: Set[str] = set()
    rec_stack: List[str] = []
    in_stack: Set[str] = set()
    found_cycles_set: Set[Tuple[str, ...]] = set()
    detected_cycles: List[List[str]] = []

    def dfs(node: str):
        if len(detected_cycles) >= max_cycles:
            return

        visited.add(node)
        rec_stack.append(node)
        in_stack.add(node)

        for neighbor in adj.get(node, []):
            if neighbor in in_stack:
                # Cycle found! Extract sub-path from neighbor to current
                idx = rec_stack.index(neighbor)
                cycle_path = rec_stack[idx:] + [neighbor]
                canonical = canonicalize_cycle(cycle_path)
                if canonical not in found_cycles_set:
                    found_cycles_set.add(canonical)
                    detected_cycles.append(list(canonical))
                    if len(detected_cycles) >= max_cycles:
                        break
            elif neighbor not in visited:
                dfs(neighbor)

        rec_stack.pop()
        in_stack.remove(node)

    for n in sorted(nodes):
        if n not in visited:
            dfs(n)
        if len(detected_cycles) >= max_cycles:
            break

    return detected_cycles
