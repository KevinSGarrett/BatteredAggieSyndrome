"""Validate Cycle #29 gates from materialized artifacts and import graphs.

Does not import producer scientific helpers. Independent reconstruction only.
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
C28_P0_IDS = tuple(f"C28-P0-{index:02d}" for index in range(1, 13))
PRODUCER_ROOT = "aggie_analytics.cycle29"
REFERENCE_ROOT = "aggie_analytics.scientific_reference.cycle29"


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
    producer_dir = src_root / "aggie_analytics" / "cycle29"
    reference_dir = src_root / "aggie_analytics" / "scientific_reference" / "cycle29"
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


INVENTORY_CLAIM_FIELDS = (
    "claim_id",
    "artifact_path",
    "field",
    "formula",
    "numerator",
    "denominator",
    "population",
    "source_identities",
    "temporal_authority",
    "producer",
    "validator",
    "independent_reference",
    "dependencies",
    "trust_class",
)
INVENTORY_SKIP = {
    "CYCLE29_CLAIM_INVENTORY.json",
    "CYCLE29_MATERIALIZATION_MANIFEST.json",
    "CYCLE29_PREFLIGHT_AND_PRESERVATION.json",
}


def _numeric_fields(payload: object, found: set[str]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                found.add(str(key))
            _numeric_fields(value, found)
    elif isinstance(payload, list):
        for item in payload:
            _numeric_fields(item, found)


def claim_inventory_findings(art: Path) -> list[str]:
    """Independently read the claim inventory instead of trusting its presence."""

    inventory = json.loads((art / "CYCLE29_CLAIM_INVENTORY.json").read_text(encoding="utf-8"))
    claims = inventory.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["claim inventory has no claims"]
    findings = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            findings.append(f"claim {index} is not an object")
            continue
        missing = [field for field in INVENTORY_CLAIM_FIELDS if field not in claim]
        if missing:
            findings.append(f"claim {claim.get('claim_id', index)} missing {missing}")
    unmapped = inventory.get("unmapped_count")
    if isinstance(unmapped, bool) or not isinstance(unmapped, int) or unmapped != 0:
        findings.append(f"unmapped_count is {unmapped!r}, not 0")
    discovered = inventory.get("discovered_count")
    if isinstance(discovered, bool) or not isinstance(discovered, int) or discovered < 1:
        findings.append(f"discovered_count is {discovered!r}")
    declared_fields = {str(claim.get("field")) for claim in claims if isinstance(claim, dict)}
    undeclared: set[tuple[str, str]] = set()
    for path in sorted(art.glob("*.json")):
        if path.name in INVENTORY_SKIP:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            findings.append(f"unreadable artifact {path.name}")
            continue
        fields: set[str] = set()
        _numeric_fields(payload, fields)
        undeclared.update((path.name, field) for field in fields if field not in declared_fields)
    if undeclared:
        sample = sorted(undeclared)[:5]
        findings.append(f"{len(undeclared)} numeric claims absent from the inventory, e.g. {sample}")
    return findings


# Cycle #37 Attempt #3 (W37R-71, R37A03-06): an explicitly selected, versioned
# successor inventory. The committed inventory stays the default and keeps
# failing on its own; the successor is only consulted when named on the
# command line. This reads bytes directly and imports no producer tool.

SUCCESSOR_TYPE = "CYCLE29_CLAIM_INVENTORY_SUCCESSOR"
SUPPORTED_SUCCESSOR_VERSIONS = ("BAS-C29-CLAIM-INVENTORY-SUCCESSOR-v1",)
SUCCESSOR_CLASSES = ("EVIDENCE_BACKED", "RECONSTRUCTED", "UNSUPPORTED", "CONTRADICTED")
MANIFEST = "CYCLE29_MATERIALIZATION_MANIFEST.json"


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _numeric_pointers(payload: object, pointer: str = "") -> list[tuple[str, str | None, object]]:
    """Every JSON number with its RFC 6901 pointer and the key holding it."""

    found: list[tuple[str, str | None, object]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{pointer}/{_pointer_token(str(key))}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                found.append((child, str(key), value))
            else:
                found.extend(_numeric_pointers(value, child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            child = f"{pointer}/{index}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                found.append((child, None, value))
            else:
                found.extend(_numeric_pointers(value, child))
    return found


def _same_number(left: object, right: object) -> bool:
    return (type(left) is type(right) and not isinstance(left, bool) and left == right)


def claim_inventory_successor_findings(art: Path, successor_path: Path) -> list[str]:
    """Check an explicitly selected successor against the committed artifacts.

    It fails when the successor or the original inventory was altered, when a
    claimed pointer no longer holds its recorded value, when a scanned
    artifact holds a number neither inventory accounts for (a renamed field
    or a missing claim), when an artifact appears that neither the manifest
    nor the successor declares, and when any claim is contradicted.
    """

    findings: list[str] = []
    try:
        successor = json.loads(successor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"successor unreadable: {type(exc).__name__}: {exc}"]
    if successor.get("artifact_type") != SUCCESSOR_TYPE:
        return [f"successor artifact_type is {successor.get('artifact_type')!r}"]
    if successor.get("successor_version") not in SUPPORTED_SUCCESSOR_VERSIONS:
        return [f"successor_version {successor.get('successor_version')!r} is not supported"]
    body = {key: value for key, value in successor.items() if key != "body_sha256"}
    if _sha256(json.dumps(body, sort_keys=True).encode("utf-8")) != successor.get("body_sha256"):
        findings.append("successor body does not match its body_sha256 (altered after it was written)")

    inventory_bytes = (art / "CYCLE29_CLAIM_INVENTORY.json").read_bytes()
    if _sha256(inventory_bytes) != successor.get("predecessor_inventory", {}).get("sha256"):
        findings.append("the committed claim inventory differs from the one the successor was built over")
    inventory = json.loads(inventory_bytes.decode("utf-8"))
    original_pairs = {(row.get("artifact_path"), row.get("field")) for row in inventory.get("claims", [])
                      if isinstance(row, dict)}

    manifest_bytes = (art / MANIFEST).read_bytes()
    declared_set = successor.get("declared_artifact_set", {})
    if _sha256(manifest_bytes) != declared_set.get("manifest_sha256"):
        findings.append("the materialization manifest differs from the one the successor was built over")
    allowed = set(json.loads(manifest_bytes.decode("utf-8")).get("file_hashes", {}))
    allowed.update(declared_set.get("present_in_the_artifact_directory_but_not_declared", []))
    allowed.add(MANIFEST)
    unexpected = sorted(path.name for path in art.iterdir() if path.is_file() and path.name not in allowed)
    if unexpected:
        findings.append(f"artifacts neither the manifest nor the successor declares: {unexpected}")

    claims = successor.get("claims")
    if not isinstance(claims, list) or not claims:
        return findings + ["successor has no claims"]
    if successor.get("claim_count") != len(claims):
        findings.append(f"claim_count {successor.get('claim_count')!r} but {len(claims)} claims")
    identities = [row.get("claim_id") for row in claims if isinstance(row, dict)]
    if len(identities) != len(set(identities)) or len(identities) != len(claims):
        findings.append("successor claim identities are missing or duplicated")
    counted = {name: 0 for name in SUCCESSOR_CLASSES}
    claimed: dict[tuple[str, str], set[str]] = {}
    documents: dict[str, object] = {}
    for row in claims:
        if not isinstance(row, dict):
            findings.append("a successor claim is not an object")
            continue
        label = row.get("claim_id")
        classification = row.get("classification")
        if classification not in SUCCESSOR_CLASSES:
            findings.append(f"{label}: classification {classification!r} is not in the vocabulary")
            continue
        counted[classification] += 1
        if classification == "CONTRADICTED":
            findings.append(f"{label}: its recomputation contradicts the recorded value")
        if not str(row.get("meaning") or "").strip() or not isinstance(row.get("evidence"), dict):
            findings.append(f"{label}: missing meaning or evidence")
        artifact, field = row.get("artifact"), row.get("field")
        path = art / str(artifact)
        if not path.is_file():
            findings.append(f"{label}: artifact {artifact} is absent")
            continue
        data = path.read_bytes()
        if _sha256(data) != row.get("artifact_sha256"):
            findings.append(f"{label}: {artifact} bytes differ from the successor's recorded digest")
        document = documents.setdefault(str(artifact), json.loads(data.decode("utf-8")))
        by_pointer = {pointer: value for pointer, _, value in _numeric_pointers(document)}
        pointers = row.get("pointers") or []
        if not pointers:
            findings.append(f"{label}: no pointers")
        for entry in pointers:
            pointer = entry.get("pointer")
            if pointer not in by_pointer:
                findings.append(f"{label}: {artifact}{pointer} no longer holds a number")
            elif not _same_number(by_pointer[pointer], entry.get("value")):
                findings.append(f"{label}: {artifact}{pointer} holds {by_pointer[pointer]!r}, "
                                f"the successor records {entry.get('value')!r}")
            if classification in ("EVIDENCE_BACKED", "RECONSTRUCTED") and (
                    entry.get("matches") is not True or not _same_number(entry.get("recomputed_value"),
                                                                         entry.get("value"))):
                findings.append(f"{label}: {pointer} is classified {classification} without a matching "
                                "recomputation")
            claimed.setdefault((str(artifact), str(field)), set()).add(str(pointer))
    if successor.get("classification_counts") != counted:
        findings.append(f"classification_counts {successor.get('classification_counts')!r} but claims give {counted}")

    array_numbers = {(row.get("artifact"), row.get("pointer")) for row in successor.get("array_element_numbers", [])
                     if isinstance(row, dict)}
    uncovered: list[tuple[str, str]] = []
    for path in sorted(art.glob("*.json")):
        if path.name in INVENTORY_SKIP:
            continue
        document = documents.get(path.name)
        if document is None:
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                findings.append(f"unreadable artifact {path.name}")
                continue
        present: dict[str, set[str]] = {}
        for pointer, key, _ in _numeric_pointers(document):
            if key is None:
                if (path.name, pointer) not in array_numbers:
                    uncovered.append((path.name, pointer))
                continue
            present.setdefault(key, set()).add(pointer)
        for key, pointers in present.items():
            if (path.name, key) in original_pairs:
                continue
            wanted = claimed.get((path.name, key))
            if wanted is None:
                uncovered.extend((path.name, pointer) for pointer in sorted(pointers))
            elif wanted != pointers:
                findings.append(f"{path.name}/{key}: successor pointers {sorted(wanted)} but the artifact "
                                f"holds {sorted(pointers)}")
    for (artifact, key), pointers in claimed.items():
        if (art / artifact).is_file() and artifact not in INVENTORY_SKIP:
            held = {pointer for pointer, name, _ in _numeric_pointers(documents.get(artifact, {})) if name == key}
            if not held:
                findings.append(f"{artifact}/{key}: claimed by the successor but no longer present")
    if uncovered:
        findings.append(f"{len(uncovered)} numeric values absent from the inventory and its successor, "
                        f"e.g. {uncovered[:5]}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument(
        "--claim-inventory-successor",
        help="Explicitly select a versioned Cycle 29 claim-inventory successor. Without "
        "it the committed inventory is checked alone, as it always was.",
    )
    args = parser.parse_args()
    root = Path(args.repo_root)
    art = root / "artifacts" / "scientific_integrity" / "cycle29"
    missing = [name for name in REQUIRED if not (art / name).is_file()]
    if missing:
        print("FAIL missing", missing)
        return 1
    if not _producer_reference_disjoint(root / "src"):
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
    findings = json.loads(
        (art / "CYCLE29_FINDING_SUCCESSOR_LEDGER.json").read_text(encoding="utf-8")
    )
    ids = {row["finding_id"] for row in findings["rows"]}
    if any(item not in ids for item in C28_P0_IDS):
        print("FAIL missing C28-P0 identifiers")
        return 1
    if args.claim_inventory_successor:
        successor_path = Path(args.claim_inventory_successor)
        inventory_findings = claim_inventory_successor_findings(art, successor_path)
        if inventory_findings:
            print("FAIL claim inventory successor", inventory_findings)
            return 1
        print(
            "NOTE claim inventory successor selected explicitly:",
            successor_path.name,
            "- the committed inventory alone still reports",
            claim_inventory_findings(art),
        )
    else:
        inventory_findings = claim_inventory_findings(art)
        if inventory_findings:
            print("FAIL claim inventory", inventory_findings)
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
    if trust.get("cycle29_kernel_trust_usable") is not False:
        print("FAIL kernel trust usable must remain false")
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
