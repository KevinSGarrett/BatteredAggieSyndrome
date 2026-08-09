from __future__ import annotations

import argparse
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path


def _cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = stack.index(node)
            return stack[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for dep in graph[node]:
            found = visit(dep)
            if found:
                return found
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in graph:
        found = visit(node)
        if found:
            return found
    return None


def validate_registry(registry: dict) -> list[str]:
    findings: list[str] = []
    components = registry.get("components", [])
    ids = [c.get("id") for c in components]
    if len(ids) != len(set(ids)):
        findings.append("duplicate component IDs")
    known = set(ids)
    graph: dict[str, list[str]] = {}
    by_id = {c["id"]: c for c in components}
    for component in components:
        cid = component["id"]
        imports = list(component.get("imports", []))
        graph[cid] = imports
        unknown = sorted(set(imports) - known)
        if unknown:
            findings.append(f"{cid} imports unknown components: {unknown}")

    found_cycle = _cycle(graph) if graph and all(set(v) <= known for v in graph.values()) else None
    if found_cycle:
        findings.append("component import cycle: " + " -> ".join(found_cycle))

    rules = registry.get("protected_dependency_rules", {})
    prohibited_planes = set(rules.get("production_may_not_import_planes", []))
    for component in components:
        if component.get("production_forecast_path"):
            if component.get("llm_policy") == "REQUIRED":
                findings.append(f"{component['id']} requires LLM on production forecast path")
            for dep in component.get("imports", []):
                dep_plane = by_id[dep].get("plane")
                if dep_plane in prohibited_planes:
                    findings.append(
                        f"{component['id']} production path imports prohibited plane {dep_plane} via {dep}"
                    )

    serving_forbidden = set(rules.get("serving_may_not_import_components", []))
    for component in components:
        if component.get("plane") == "serving" and component.get("name") == "read_only_serving":
            bad = sorted(set(component.get("imports", [])) & serving_forbidden)
            if bad:
                findings.append(f"read-only serving imports forbidden components: {bad}")

    zones = registry.get("data_zones", [])
    zone_ids = [z.get("id") for z in zones]
    zone_orders = [z.get("order") for z in zones]
    if len(zone_ids) != len(set(zone_ids)):
        findings.append("duplicate data-zone IDs")
    if zone_orders != sorted(zone_orders):
        findings.append("data zones are not ordered")
    if any(z.get("mutable") is not False for z in zones):
        findings.append("W03 canonical data-zone contract requires immutable/versioned artifacts")

    interfaces = registry.get("interfaces", [])
    interface_ids = [i.get("id") for i in interfaces]
    if len(interface_ids) != len(set(interface_ids)):
        findings.append("duplicate interface IDs")
    for interface in interfaces:
        if interface.get("owner") not in known:
            findings.append(f"{interface.get('id')} has unknown owner {interface.get('owner')}")

    if rules.get("required_pit_gateway_component") not in known:
        findings.append("required PIT gateway component missing")
    if rules.get("llm_required_on_production_path") is not False:
        findings.append("architecture must state that LLM is not required on production path")
    if rules.get("future_live_may_not_feed_pregame") is not True:
        findings.append("future-live isolation rule missing")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the W03 logical architecture registry.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("configs/architecture_registry.json"),
    )
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    findings = validate_registry(registry)
    if findings:
        print(f"FAIL: {len(findings)} architecture finding(s)")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(
        f"PASS: architecture {registry['architecture_version']} "
        f"({len(registry['components'])} components, "
        f"{len(registry['interfaces'])} interfaces, "
        f"{len(registry['data_zones'])} data zones)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
