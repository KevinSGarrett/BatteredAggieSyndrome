"""Actual-edge DAG cycle and transitive-impact reconstruction."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable, Mapping, Sequence


def _edge_pair(edge: Mapping[str, object] | Sequence[object]) -> tuple[str, str] | None:
    if isinstance(edge, Mapping):
        source = str(edge.get("from") or edge.get("source") or "").strip()
        target = str(edge.get("to") or edge.get("target") or "").strip()
    else:
        if len(edge) < 2:
            return None
        source = str(edge[0]).strip()
        target = str(edge[1]).strip()
    if not source or not target:
        return None
    return source, target


def directed_cycles(edges: Iterable[Mapping[str, object] | Sequence[object]]) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for edge in edges:
        pair = _edge_pair(edge)
        if pair is None:
            continue
        source, target = pair
        graph[source].append(target)
        nodes.add(source)
        nodes.add(target)
    cycles: list[list[str]] = []
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for successor in graph.get(node, []):
            if successor not in indices:
                strongconnect(successor)
                lowlink[node] = min(lowlink[node], lowlink[successor])
            elif successor in on_stack:
                lowlink[node] = min(lowlink[node], indices[successor])
        if lowlink[node] == indices[node]:
            component: list[str] = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1 or node in graph.get(node, []):
                cycles.append(sorted(component))

    for node in sorted(nodes):
        if node not in indices:
            strongconnect(node)
    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for cycle in cycles:
        key = tuple(cycle)
        if key not in seen:
            seen.add(key)
            unique.append(cycle)
    return unique


def transitive_affected(
    edges: Iterable[Mapping[str, object] | Sequence[object]],
    start: str,
) -> set[str]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        pair = _edge_pair(edge)
        if pair is None:
            continue
        graph[pair[0]].append(pair[1])
    reached: set[str] = set()
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for successor in graph.get(node, []):
            if successor not in reached:
                reached.add(successor)
                queue.append(successor)
    return reached


def circular_authority_from_edges(
    edges: Iterable[Mapping[str, object] | Sequence[object]],
) -> bool:
    return bool(directed_cycles(edges))
