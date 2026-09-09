"""Validate Cycle #30 gates.

Containment and science are separate modes. Empty producer/reference
directories cannot pass science. Missing external row files cannot PASS.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.claims import (  # noqa: E402
    CONTAINMENT,
    SCIENCE,
    reject_empty_science_pass,
    reject_vacuous_row_count,
)
from aggie_analytics.cycle30.ci_rows import open_and_rehash, reject_pass_without_opening  # noqa: E402

ART_REL = Path("artifacts") / "scientific_integrity" / "cycle30"
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
REQUIRED = (
    "PIT_KERNEL_TRUST_GATE.json",
    "CYCLE30_FINDING_SUCCESSOR_LEDGER.json",
    "BAS_DOMAIN_CATALOG_CROSSWALK.json",
    "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
    "COACHING_MODEL_ADMISSION_GATE.json",
    "CYCLE30_CLAIM_INVENTORY.json",
    "CYCLE30_PREFLIGHT_AND_PRESERVATION.json",
    "PIT_KERNEL_POPULATION_MANIFEST.json",
    "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
    "PIT_KERNEL_FULL_CHAIN_RECONSTRUCTION.json",
    "CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION.json",
)
C28_P0_IDS = tuple(f"C28-P0-{index:02d}" for index in range(1, 13))
PRODUCER_ROOT = "aggie_analytics.cycle30"
REFERENCE_ROOT = "aggie_analytics.scientific_reference.cycle30"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _producer_reference_disjoint(src_root: Path) -> bool:
    producer_dir = src_root / "aggie_analytics" / "cycle30"
    reference_dir = src_root / "aggie_analytics" / "scientific_reference" / "cycle30"
    if not any(producer_dir.rglob("*.py")) or not any(reference_dir.rglob("*.py")):
        return False
    producer_imports: set[str] = set()
    reference_imports: set[str] = set()
    for path in producer_dir.rglob("*.py"):
        producer_imports.update(_imported_modules(path))
    for path in reference_dir.rglob("*.py"):
        reference_imports.update(_imported_modules(path))
    if any(
        name == REFERENCE_ROOT or name.startswith(REFERENCE_ROOT + ".")
        for name in producer_imports
    ):
        return False
    if any(
        name == PRODUCER_ROOT or name.startswith(PRODUCER_ROOT + ".")
        for name in reference_imports
    ):
        return False
    return True


def _containment(root: Path) -> int:
    art = root / ART_REL
    missing = [name for name in REQUIRED if not (art / name).is_file()]
    if missing:
        print("FAIL missing", missing)
        return 1
    if not _producer_reference_disjoint(root / "src"):
        print("FAIL dependency graph")
        return 1
    preflight = json.loads(
        (art / "CYCLE30_PREFLIGHT_AND_PRESERVATION.json").read_text(encoding="utf-8")
    )
    if preflight.get("operator_hold") != "ACTIVE":
        print("FAIL hold must remain ACTIVE")
        return 1
    if preflight.get("review_state") == "MANAGER_VERIFIED":
        print("FAIL Cursor cannot mark MANAGER_VERIFIED")
        return 1
    xwalk = json.loads(
        (art / "BAS_DOMAIN_CATALOG_CROSSWALK.json").read_text(encoding="utf-8")
    )
    if xwalk.get("unmapped_term_count") != 0:
        print("FAIL domain crosswalk")
        return 1
    if xwalk.get("ambiguous_unresolved_mapping_count") == 0:
        print("FAIL ambiguous mapping cannot be literal zero")
        return 1
    findings = json.loads(
        (art / "CYCLE30_FINDING_SUCCESSOR_LEDGER.json").read_text(encoding="utf-8")
    )
    ids = {row["finding_id"] for row in findings["rows"]}
    if any(item not in ids for item in C28_P0_IDS):
        print("FAIL missing C28-P0 identifiers")
        return 1
    trust = json.loads((art / "PIT_KERNEL_TRUST_GATE.json").read_text(encoding="utf-8"))
    for key in (
        "current_fitted_forecast_trust_recovered",
        "project_wide_scientific_trust_recovered",
        "scientific_trust_recovered",
    ):
        if trust.get(key) is not False:
            print("FAIL", key, "must remain false")
            return 1
    coaching = json.loads(
        (art / "COACHING_MODEL_ADMISSION_GATE.json").read_text(encoding="utf-8")
    )
    if coaching.get("coaching_enters_model") is not False:
        print("FAIL coaching modeled")
        return 1
    attestation = json.loads(
        (art / "CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION.json").read_text(
            encoding="utf-8"
        )
    )
    if attestation.get("scientific_review_gate") in {None, "PASS", "APPROVED"}:
        print("FAIL no-API attestation is not scientific review")
        return 1
    inventory = json.loads(
        (art / "CYCLE30_CLAIM_INVENTORY.json").read_text(encoding="utf-8")
    )
    if inventory.get("unmapped_count") not in {0, None}:
        print("FAIL claim inventory unmapped_count")
        return 1
    if not inventory.get("declared_count"):
        print("FAIL claim inventory empty")
        return 1
    print("PASS cycle30 containment")
    return 0


def _science(root: Path) -> int:
    art = root / ART_REL
    producer = list((root / "src" / "aggie_analytics" / "cycle30").glob("*.py"))
    reference = list(
        (root / "src" / "aggie_analytics" / "scientific_reference" / "cycle30").glob(
            "*.py"
        )
    )
    rows_path = EXT / "PIT_KERNEL_ROWS.jsonl"
    manifest = json.loads(
        (art / "PIT_KERNEL_POPULATION_MANIFEST.json").read_text(encoding="utf-8")
    )
    claimed = int(
        manifest.get("game_grain_count")
        or manifest.get("retrospective_candidate_rows")
        or 0
    )
    try:
        reject_empty_science_pass(
            mode=SCIENCE,
            producer_modules=producer,
            reference_modules=reference,
            bound_row_files=[rows_path],
            claimed_row_count=claimed,
        )
        opened = reject_vacuous_row_count(rows_path, claimed)
        rehash = open_and_rehash(
            rows_path,
            expected_sha256=str(manifest.get("external_rows_sha256") or ""),
            expected_rows=claimed,
            payload_available=rows_path.is_file(),
        )
        reject_pass_without_opening(True, int(rehash["rows_opened"]), claimed)
    except Exception as exc:
        print("FAIL science", exc)
        return 1
    reconstruction = json.loads(
        (art / "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json").read_text(encoding="utf-8")
    )
    if reconstruction.get("matched") is not True:
        print("FAIL independent reconstruction")
        return 1
    if claimed and opened == 0:
        print("FAIL empty scientific rows")
        return 1
    pair = json.loads(
        (art / "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json").read_text(
            encoding="utf-8"
        )
    )
    labeled = pair.get("pair_counts_home_to_away") or {}
    if pair.get("normalized_game_count") != labeled.get("row_count"):
        print("FAIL pair counts not derived from rows")
        return 1
    print("PASS cycle30 science", "rows", opened)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument(
        "--mode",
        choices=(CONTAINMENT, SCIENCE, "BOTH"),
        default="BOTH",
    )
    args = parser.parse_args()
    root = Path(args.repo_root)
    if args.mode in {CONTAINMENT, "BOTH"}:
        code = _containment(root)
        if code:
            return code
    if args.mode in {SCIENCE, "BOTH"}:
        return _science(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
