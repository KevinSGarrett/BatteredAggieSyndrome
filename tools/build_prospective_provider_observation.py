r"""Build the explicit prospective provider-observation capsule (BAT-723, Cycle #51 TP51-A01).

``python -B tools/build_prospective_provider_observation.py
--contract configs/prospective_provider_observation_20261011_contract.json
--raw <retained provider-response.json> --receipt <retained provider-receipt.json>
--expected <manager-frozen EXPECTED_COHORT.json>
--output-root <data>/canonical/prospective_provider_observation_20261011
--manifest-root <data>/manifests/prospective_provider_observation_20261011``

The builder refuses unless the contract bytes are exactly the committed contract the reader pins
(:data:`aggie_analytics.national_source_time.prospective.CONTRACT_SHA256`); the reader's own derivation then requires
the raw response, receipt and cohort to hash to that contract's pins and the derived membership to equal its frozen
event keys and participant tuples. No network access: the inputs are retained local bytes.

Materialization is create-only and content addressed: every member of the capsule directory (``capsule.json`` and
the four byte-identical bundle members) is written into a fresh staging directory under ``<output-root>/.staging``,
re-read and compared, and the staging directory is then renamed in one operation to
``<output-root>/sha256/<capsule identity>``. An existing identity directory must hold exactly the same members and
bytes (``ALREADY_PRESENT_IDENTICAL``, nothing is written) or the build refuses. An interrupted build
(``--stop-after-members``) leaves no directory at the identity path, so the reader cannot mistake it for a complete
capsule; a resumed build yields identical bytes. ``--processing-order`` and ``--chunk-size`` prove that processing
order and read chunking never change a byte. The materialized capsule is then opened through the reader's complete
verification, and the run manifest is written once to ``<manifest-root>/sha256/<identity>/run_manifest.json``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from aggie_analytics.national_source_time import prospective  # noqa: E402

PRODUCER = "prospective_provider_observation/1.0.0"
MANIFEST_SCHEMA = "BAS-PROSPECTIVE-PROVIDER-OBSERVATION-RUN-MANIFEST-1"
INTERRUPTED_EXIT = 3


class BuildRefused(RuntimeError):
    """A refused build; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class BuildInterrupted(RuntimeError):
    """A deliberately interrupted build (``--stop-after-members``); nothing was published."""


def read_chunked(path: Path, chunk_size: int) -> bytes:
    """The exact bytes of ``path`` read in ``chunk_size`` blocks (a chunking variant never changes the result)."""
    parts = []
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(max(1, chunk_size)), b""):
            parts.append(block)
    return b"".join(parts)


def directory_members(directory: Path) -> dict[str, bytes]:
    out = {}
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        out[path.relative_to(directory).as_posix()] = path.read_bytes()
    return out


def materialize(output_root: Path, identity: str, files: dict[str, bytes], *,
                stop_after_members: int | None = None) -> str:
    """Publish the capsule directory create-only; returns MATERIALIZED or ALREADY_PRESENT_IDENTICAL."""
    final = Path(output_root) / "sha256" / identity
    if final.exists():
        if directory_members(final) != files:
            raise BuildRefused("EXISTING_IDENTITY_DIFFERS", f"{final} exists with different members or bytes")
        return "ALREADY_PRESENT_IDENTICAL"
    staging = Path(output_root) / ".staging" / f"{identity}-{os.getpid()}-{time.time_ns()}"
    staging.mkdir(parents=True, exist_ok=False)
    for written, (name, data) in enumerate(sorted(files.items()), start=1):
        target = staging / Path(*name.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if stop_after_members is not None and written >= stop_after_members:
            raise BuildInterrupted(f"interrupted after {written} of {len(files)} members in {staging}")
    if directory_members(staging) != files:
        raise BuildRefused("STAGING_READBACK_DIFFERS", f"{staging} does not read back exactly")
    final.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(staging, final)
    except FileExistsError:
        if directory_members(final) != files:
            raise BuildRefused("EXISTING_IDENTITY_DIFFERS", f"{final} appeared with different members or bytes")
        return "ALREADY_PRESENT_IDENTICAL"
    return "MATERIALIZED"


def build(args: argparse.Namespace) -> dict[str, Any]:
    chunk = int(args.chunk_size)
    contract = read_chunked(args.contract, chunk)
    contract_sha = hashlib.sha256(contract).hexdigest()
    authority = getattr(args, "contract_authority", None) or prospective.CONTRACT_SHA256
    if contract_sha != authority:
        raise BuildRefused("CONTRACT_NOT_COMMITTED_AUTHORITY", f"{args.contract} hashes to {contract_sha}, the reader "
                                                               f"pins {authority}")
    raw, receipt, expected = (read_chunked(p, chunk) for p in (args.raw, args.receipt, args.expected))
    try:
        identity, files, iddoc = prospective.build_capsule(raw, receipt, expected, contract, contract_sha256=authority,
                                                           order=args.processing_order, chunk_size=chunk)
    except prospective.ProspectiveEvidenceError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    state = materialize(Path(args.output_root), identity, files, stop_after_members=args.stop_after_members)
    capsule = Path(args.output_root) / "sha256" / identity / prospective.CAPSULE_FILE
    verified = prospective.verify_capsule(capsule, contract_sha256=authority)
    if verified["capsule_identity"] != identity:
        raise BuildRefused("READER_VERIFICATION_DIFFERS", "the reader's identity differs from the build's")
    document = verified["document"]
    manifest_path = Path(args.manifest_root) / "sha256" / identity / "run_manifest.json"
    manifest_state = "ALREADY_PRESENT"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("identity") != identity or existing.get("identity_document") != iddoc:
            raise BuildRefused("EXISTING_MANIFEST_DIFFERS", f"{manifest_path} names another capsule")
    else:
        manifest = {"schema": MANIFEST_SCHEMA, "producer": PRODUCER, "population": prospective.POPULATION,
                    "identity": identity, "identity_document": iddoc,
                    "contract": {"id": prospective.CONTRACT_ID, "sha256": contract_sha},
                    "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                                for name, data in sorted(files.items())},
                    "counts": document["counts"], "observation": document["observation"],
                    "labels": document["labels"],
                    "build": {"tool": "tools/build_prospective_provider_observation.py",
                              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              "reader_sha256": hashlib.sha256(Path(prospective.__file__).read_bytes()).hexdigest(),
                              "processing_order": args.processing_order or "natural", "chunk_size": chunk,
                              "capsule_state": state,
                              "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                              "built_at_role": "BUILD_CLOCK_ONLY_NOT_OBSERVATION_TIME"},
                    "network_requests": 0}
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "capsule": str(capsule), "capsule_state": state, "manifest": str(manifest_path),
            "manifest_state": manifest_state, "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "identity_document": iddoc, "counts": document["counts"], "contract_sha256": contract_sha,
            "members": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "network_requests": 0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_prospective_provider_observation", allow_abbrev=False,
                                     description="Create-only build of the BAT-723 prospective provider-observation "
                                                 "capsule from retained local bytes (no network).")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--processing-order", default=None, help="natural, reversed or shuffled:<seed>")
    parser.add_argument("--chunk-size", default=str(1 << 20))
    parser.add_argument("--stop-after-members", type=int, default=None,
                        help="interrupt after writing this many staged members (resume proof; publishes nothing)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build(args)
    except BuildInterrupted as exc:
        print(json.dumps({"interrupted": True, "detail": str(exc)}), file=sys.stderr)
        return INTERRUPTED_EXIT
    except BuildRefused as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
