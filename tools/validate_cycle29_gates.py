"""Validate Cycle #29 gates from materialized artifacts and import graphs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Tool scripts must import the local package after PATH setup.
# ruff: noqa: E402

from aggie_analytics.cycle29.dependency import static_import_graph
from aggie_analytics.cycle29.domains import crosswalk
from aggie_analytics.cycle29.findings import C28_P0_IDS

ART = ROOT / "artifacts" / "scientific_integrity" / "cycle29"
REQUIRED = (
    "PIT_KERNEL_TRUST_GATE.json",
    "CYCLE29_FINDING_SUCCESSOR_LEDGER.json",
    "BAS_DOMAIN_CATALOG_CROSSWALK.json",
    "WEEK1_2026_PROGRAM_SLICE.json",
    "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json",
    "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
    "COACHING_MODEL_ADMISSION_GATE.json",
    "CYCLE29_CLAIM_INVENTORY.json",
    "CYCLE29_PREFLIGHT_AND_PRESERVATION.json",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.repo_root)
    art = root / "artifacts" / "scientific_integrity" / "cycle29"
    missing = [name for name in REQUIRED if not (art / name).is_file()]
    if missing:
        print("FAIL missing", missing)
        return 1
    graph = static_import_graph(root / "src")
    if not graph["disjoint"]:
        print("FAIL dependency graph")
        return 1
    xwalk = json.loads(
        (art / "BAS_DOMAIN_CATALOG_CROSSWALK.json").read_text(encoding="utf-8")
    )
    if (
        xwalk.get("unmapped_term_count") != 0
        or xwalk.get("ambiguous_unresolved_mapping_count") != 0
    ):
        print("FAIL domain crosswalk")
        return 1
    live = crosswalk()
    if live["unmapped_term_count"] != 0:
        print("FAIL live crosswalk")
        return 1
    findings = json.loads(
        (art / "CYCLE29_FINDING_SUCCESSOR_LEDGER.json").read_text(encoding="utf-8")
    )
    ids = {row["finding_id"] for row in findings["rows"]}
    if any(item not in ids for item in C28_P0_IDS):
        print("FAIL missing C28-P0 identifiers")
        return 1
    trust = json.loads((art / "PIT_KERNEL_TRUST_GATE.json").read_text(encoding="utf-8"))
    if trust.get("current_fitted_forecast_trust_recovered") is not False:
        print("FAIL fitted trust must remain false")
        return 1
    if trust.get("project_wide_scientific_trust_recovered") is not False:
        print("FAIL project-wide trust must remain false")
        return 1
    if trust.get("scientific_trust_recovered") is not False:
        print("FAIL compatibility scientific_trust_recovered must remain false")
        return 1
    entity = json.loads(
        (art / "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json").read_text(
            encoding="utf-8"
        )
    )
    if entity.get("predecessor_unresolved_participant_row_count") != 8:
        print("FAIL predecessor unresolved count")
        return 1
    if entity.get("successor_unresolved_participant_row_count") != 0:
        print("FAIL successor unresolved count")
        return 1
    games = json.loads(
        (art / "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json").read_text(
            encoding="utf-8"
        )
    )
    if games.get("fcs_to_fcs_count") != 0:
        print("FAIL predecessor FCS-v-FCS fact")
        return 1
    if (
        games.get("classification")
        != "FBS_CENTRIC_NOT_COMPLETE_FBS_FCS_COMPETITION_GRAPH"
    ):
        print("FAIL FBS-centric classification")
        return 1
    coaching = json.loads(
        (art / "COACHING_MODEL_ADMISSION_GATE.json").read_text(encoding="utf-8")
    )
    if coaching.get("coaching_enters_model") is not False:
        print("FAIL coaching modeled")
        return 1
    print("PASS cycle29 gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
