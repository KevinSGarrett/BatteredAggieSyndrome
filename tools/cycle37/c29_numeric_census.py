"""Cycle #37 — Attempt #3 — independent raw numeric census of the Cycle 29 artifacts.

W37R-71 / R37A03-06-A. The committed ``CYCLE29_CLAIM_INVENTORY.json`` says
``unmapped_count: 0``, but its discovery scan only recognised allow-listed
field suffixes and skipped undeclared artifacts; the repaired validator
finds 35 numeric (artifact, field) pairs the inventory never declared.

This census is written independently of both the Cycle 29 producer and the
validator: it imports neither, and it enumerates at a finer grain than the
validator does. It lists

* every artifact the Cycle 29 materialization manifest declares, every file
  present in the artifact directory, every file a Cycle 29 claim or artifact
  names (the inventory's ``artifact_path`` values and ``ops/cycle29_work/
  outputs/...`` references inside artifacts), with bytes, SHA-256, where it
  was found and whether the bytes match the manifest;
* every numeric value (JSON integer or number, never a boolean) in every
  readable artifact, addressed by an RFC 6901 JSON pointer (plus the line
  number for JSON Lines files), with its key, type and exact value.

It never writes into the artifact directory and never edits a byte of the
historical receipts it reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterator

CENSUS_VERSION = "BAS-C29-NUMERIC-CENSUS-v37.3"

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts" / "scientific_integrity" / "cycle29"
DEFAULT_EXTERNAL_DIR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\outputs")
MANIFEST_NAME = "CYCLE29_MATERIALIZATION_MANIFEST.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def escape(token: str) -> str:
    """RFC 6901 reference-token escaping."""

    return token.replace("~", "~0").replace("/", "~1")


def numeric_values(document: Any, pointer: str = "") -> Iterator[tuple[str, str | None, Any]]:
    """Yield ``(pointer, key, value)`` for every JSON number in ``document``.

    Booleans are JSON literals, not numbers, even though Python's ``bool`` is
    an ``int`` subclass; they are never yielded. ``key`` is the object member
    name holding the value, or ``None`` for an array element.
    """

    if isinstance(document, dict):
        for key, value in document.items():
            child = f"{pointer}/{escape(str(key))}"
            if _is_number(value):
                yield child, str(key), value
            else:
                yield from numeric_values(value, child)
    elif isinstance(document, list):
        for index, value in enumerate(document):
            child = f"{pointer}/{index}"
            if _is_number(value):
                yield child, None, value
            else:
                yield from numeric_values(value, child)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _value_type(value: Any) -> str:
    if isinstance(value, int):
        return "integer"
    if math.isfinite(value):
        return "number"
    return "non_finite_number"


def _documents(name: str, data: bytes) -> Iterator[tuple[int | None, Any]]:
    text = data.decode("utf-8")
    if name.endswith(".jsonl"):
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip():
                yield number, json.loads(line)
    else:
        yield None, json.loads(text)


INVENTORY_NAME = "CYCLE29_CLAIM_INVENTORY.json"
EXTERNAL_REFERENCE = re.compile(r"ops/cycle29_work/outputs/([A-Za-z0-9_.\-]+)")


def locate(name: str, artifact_dir: Path, external_dir: Path | None) -> tuple[Path | None, str]:
    candidate = artifact_dir / name
    if candidate.is_file():
        return candidate, "REPOSITORY_ARTIFACT_DIRECTORY"
    if external_dir is not None:
        candidate = external_dir / name
        if candidate.is_file():
            return candidate, "CYCLE29_EXTERNAL_OUTPUT_DIRECTORY"
    # A claim may name an artifact another cycle's directory holds; it is
    # found there by exact name, never by a looser match.
    siblings = sorted(path for path in artifact_dir.parent.glob(f"*/{name}") if path.is_file())
    if len(siblings) == 1:
        return siblings[0], "REPOSITORY_OTHER_ARTIFACT_DIRECTORY"
    if len(siblings) > 1:
        return None, "AMBIGUOUS_SEVERAL_REPOSITORY_DIRECTORIES"
    return None, "ABSENT"


def _strings(document: Any) -> Iterator[str]:
    if isinstance(document, dict):
        for value in document.values():
            yield from _strings(value)
    elif isinstance(document, list):
        for value in document:
            yield from _strings(value)
    elif isinstance(document, str):
        yield document


def references(artifact_dir: Path) -> dict[str, set[str]]:
    """Files named by the inventory's claims or by paths inside artifacts."""

    found: dict[str, set[str]] = {}
    inventory = artifact_dir / INVENTORY_NAME
    if inventory.is_file():
        for row in json.loads(inventory.read_text(encoding="utf-8")).get("claims", []):
            if isinstance(row, dict) and row.get("artifact_path"):
                found.setdefault(str(row["artifact_path"]), set()).add(f"{INVENTORY_NAME}:artifact_path")
    for path in sorted(artifact_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        for text in _strings(document):
            for match in EXTERNAL_REFERENCE.finditer(text):
                found.setdefault(match.group(1), set()).add(f"{path.name}:external_path_reference")
    return found


def census(artifact_dir: Path, external_dir: Path | None) -> dict[str, Any]:
    manifest_path = artifact_dir / MANIFEST_NAME
    manifest_bytes = manifest_path.read_bytes()
    declared: dict[str, str] = json.loads(manifest_bytes.decode("utf-8"))["file_hashes"]
    present = sorted(path.name for path in artifact_dir.iterdir() if path.is_file())
    referenced = references(artifact_dir)
    names = sorted(set(declared) | set(present) | set(referenced))
    artifacts: list[dict[str, Any]] = []
    numbers: list[dict[str, Any]] = []
    for name in names:
        path, location = locate(name, artifact_dir, external_dir)
        record: dict[str, Any] = {
            "artifact": name,
            "declared_in_manifest": name in declared,
            "present_in_artifact_directory": name in present,
            "referenced_by": sorted(referenced.get(name, ())),
            "location": location,
            "path": None if path is None else str(path),
            "manifest_sha256": declared.get(name),
        }
        if path is None:
            record.update(state="NAMED_BUT_ABSENT_FROM_EVERY_SEARCHED_LOCATION",
                          bytes=None, sha256=None, manifest_hash_matches=None,
                          numeric_value_count=None)
            artifacts.append(record)
            continue
        data = path.read_bytes()
        digest = sha256(data)
        record.update(bytes=len(data), sha256=digest,
                      manifest_hash_matches=None if name not in declared else digest == declared[name])
        if not name.endswith((".json", ".jsonl")):
            record.update(state="NOT_JSON_NOT_PARSED", numeric_value_count=None)
            artifacts.append(record)
            continue
        try:
            documents = list(_documents(name, data))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            record.update(state="UNPARSEABLE", error=f"{type(exc).__name__}: {exc}",
                          numeric_value_count=None)
            artifacts.append(record)
            continue
        count = 0
        for line, document in documents:
            for pointer, key, value in numeric_values(document):
                count += 1
                numbers.append({
                    "artifact": name,
                    "artifact_sha256": digest,
                    "line": line,
                    "pointer": pointer,
                    "key": key,
                    "value": value,
                    "value_type": _value_type(value),
                })
        record.update(state="PARSED", document_count=len(documents), numeric_value_count=count)
        artifacts.append(record)
    fields: dict[tuple[str, str], int] = {}
    for item in numbers:
        if item["key"] is not None:
            pair = (item["artifact"], item["key"])
            fields[pair] = fields.get(pair, 0) + 1
    body = {
        "census_version": CENSUS_VERSION,
        "artifact_directory": str(artifact_dir),
        "external_directory": None if external_dir is None else str(external_dir),
        "manifest": {"path": str(manifest_path), "sha256": sha256(manifest_bytes),
                     "declared_count": len(declared)},
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "numeric_value_count": len(numbers),
        "numeric_values": numbers,
        "numeric_field_pairs": [
            {"artifact": artifact, "field": field, "occurrences": count}
            for (artifact, field), count in sorted(fields.items())
        ],
        "array_element_numbers": sum(1 for item in numbers if item["key"] is None),
    }
    body["census_body_sha256"] = sha256(json.dumps(body, sort_keys=True).encode("utf-8"))
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--external-dir", default=str(DEFAULT_EXTERNAL_DIR))
    parser.add_argument("--no-external", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    artifact_dir = Path(args.artifact_dir).resolve()
    out = Path(args.out).resolve()
    if artifact_dir == out.parent or artifact_dir in out.parents:
        print("REFUSED: the census never writes into the artifact directory it reads", file=sys.stderr)
        return 2
    if out.exists():
        print(f"REFUSED: {out} exists; census receipts are never overwritten", file=sys.stderr)
        return 2
    body = census(artifact_dir, None if args.no_external else Path(args.external_dir))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "census_version": CENSUS_VERSION,
        "artifacts": body["artifact_count"],
        "numeric_values": body["numeric_value_count"],
        "numeric_field_pairs": len(body["numeric_field_pairs"]),
        "absent": [a["artifact"] for a in body["artifacts"] if a["path"] is None],
        "hash_mismatches": [a["artifact"] for a in body["artifacts"]
                            if a.get("manifest_hash_matches") is False],
        "out": str(out),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
