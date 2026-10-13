r"""Build the immutable official schedule evidence sidecar for the frozen October 17 shadow (BAT-726, Cycle #54 TP54-A01).

``python -B tools/build_official_shadow_schedule.py build --contract configs/official_shadow_schedule_20261017_contract.json
--shadow <data>/canonical/provider_record_shadow_20261017/sha256/<shadow identity>/snapshot.json
--acquisition <capture directory holding journal-NN.jsonl and bodies/<sha256>.gz>
--output-root <data>/canonical/official_shadow_schedule_20261017
--manifest-root <data>/manifests/official_shadow_schedule_20261017``

The builder refuses unless the contract bytes are exactly the committed contract the reader pins
(:data:`aggie_analytics.retrospective_baseline.schedule.CONTRACT_SHA256`). The shadow is verified completely by the
accepted BAT-725 reader; the capture directory is read only (its journal segments are copied byte for byte, its bodies
re-encoded as canonical ``gzip.compress(body, mtime=0)``); nothing is requested from the network and nothing is fetched
again.

Materialization is create-only and content addressed: the sidecar directory (schedule.json, the contract, every journal
segment and every raw body) under ``<output-root>/sha256/<identity>`` is written into a fresh staging directory under
``<output-root>/.staging``, re-read and compared, then renamed in one operation. An existing identity directory must
hold exactly the same members and bytes (``ALREADY_PRESENT_IDENTICAL``) or the build refuses; a second, different
sidecar in the same root refuses (``SIDECAR_ALREADY_FROZEN``) unless ``--successor-of`` names the frozen predecessor (a
deliberate corrected successor; the predecessor is never touched). An interrupted build (``--stop-after-members``)
leaves no directory at the identity path. ``--processing-order`` and ``--chunk-size`` prove that processing order and
read chunking never change a byte. The materialized sidecar is re-opened through the reader's complete verification
(before the gate is packaged the actual-sidecar pin is reported, not required), and the run manifest (which alone
records the build clock) is written once.

``build-expansion`` (BAT-727, Cycle #55 TP55-A01) builds the explicit successor profile the same create-only way:
``--contract configs/official_shadow_schedule_expansion_20261017_contract.json --shadow <...snapshot.json>
--predecessor <data>/canonical/official_shadow_schedule_20261017/sha256/<V1 identity>/schedule.json
--output-root <data>/canonical/official_shadow_schedule_expansion_20261017
--manifest-root <data>/manifests/official_shadow_schedule_expansion_20261017``. The contract must be the committed
successor contract (:data:`aggie_analytics.retrospective_baseline.schedule_expansion.CONTRACT_SHA256`); the named
V1 sidecar is verified by the accepted BAT-726 reader and copied byte for byte under ``predecessor/<V1 identity>/``
(never edited, never requested again); the successor document is derived from those retained bytes under the
frozen successor policy and re-opened through the successor reader. ``build`` and its V1 output are unchanged.
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

from aggie_analytics.retrospective_baseline import preview as pv  # noqa: E402
from aggie_analytics.retrospective_baseline import schedule  # noqa: E402

PRODUCER = "official_shadow_schedule/1.0.0"
MANIFEST_SCHEMA = "BAS-OFFICIAL-SHADOW-SCHEDULE-RUN-MANIFEST-1"
EXPANSION_PRODUCER = "official_shadow_schedule_expansion/2.0.0"
EXPANSION_MANIFEST_SCHEMA = "BAS-OFFICIAL-SHADOW-SCHEDULE-EXPANSION-RUN-MANIFEST-1"
INTERRUPTED_EXIT = 3
_DEFAULT = object()


class BuildRefused(RuntimeError):
    """A refused build; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class BuildInterrupted(RuntimeError):
    """A deliberately interrupted build (``--stop-after-members``); nothing was published."""


def _io(path: Path | str) -> Path:
    return Path(pv.io_path(os.path.abspath(path)))


def materialize(parent: Path, identity: str, files: dict[str, bytes], staging_root: Path, *,
                stop_after_members: int | None = None, successor_of: str | None = None) -> str:
    """Publish one identity directory create-only; returns MATERIALIZED or ALREADY_PRESENT_IDENTICAL."""
    final = parent / identity
    if final.exists():
        if pv.directory_files(str(final)) != files:
            raise BuildRefused("EXISTING_IDENTITY_DIFFERS", f"{final} exists with different members or bytes")
        return "ALREADY_PRESENT_IDENTICAL"
    others = sorted(p.name for p in parent.iterdir()) if parent.is_dir() else []
    if others and others != [successor_of]:
        raise BuildRefused("SIDECAR_ALREADY_FROZEN", f"{parent} already holds {others}; a corrected successor must name "
                                                     "its frozen predecessor with --successor-of")
    if successor_of is not None and successor_of not in others:
        raise BuildRefused("SUCCESSOR_PREDECESSOR_MISSING", f"--successor-of {successor_of} is not present in {parent}")
    staging = staging_root / f"{time.time_ns()}-{os.getpid()}"
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
    if pv.directory_files(str(staging)) != files:
        raise BuildRefused("STAGING_READBACK_DIFFERS", f"{staging} does not read back exactly")
    parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(staging, final)
    except FileExistsError:
        if pv.directory_files(str(final)) != files:
            raise BuildRefused("EXISTING_IDENTITY_DIFFERS", f"{final} appeared with different members or bytes")
        return "ALREADY_PRESENT_IDENTICAL"
    return "MATERIALIZED"


def _write_manifest(manifest_root: Path, identity: str, document: dict[str, Any]) -> tuple[str, str, str]:
    """The run manifest, written once (an existing manifest must name the same identity)."""
    report = Path(manifest_root) / "sha256" / identity / "run_manifest.json"
    path = _io(manifest_root) / "sha256" / identity / "run_manifest.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("identity") != identity or existing.get("identity_document") != document.get(
                "identity_document"):
            raise BuildRefused("EXISTING_MANIFEST_DIFFERS", f"{path} names another identity")
        state = "ALREADY_PRESENT"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
        state = "WRITTEN"
    return str(report), state, hashlib.sha256(path.read_bytes()).hexdigest()


def build_sidecar(args: argparse.Namespace, *, contract_authority: str | None = None,
                  shadow_profile: Any = _DEFAULT) -> dict[str, Any]:
    chunk = int(args.chunk_size)
    contract = pv.read_chunked(args.contract, chunk)
    authority = contract_authority or schedule.CONTRACT_SHA256
    contract_sha = hashlib.sha256(contract).hexdigest()
    if contract_sha != authority:
        raise BuildRefused("CONTRACT_NOT_COMMITTED_AUTHORITY", f"{args.contract} hashes to {contract_sha}, the reader "
                                                               f"pins {authority}")
    acquisition = _io(args.acquisition)
    if not acquisition.is_dir():
        raise BuildRefused("ACQUISITION_MISSING", f"no capture directory at {args.acquisition}")
    segments, raw_members = schedule.read_acquisition(acquisition)
    profile = {} if shadow_profile is _DEFAULT else {"shadow_profile": shadow_profile}
    try:
        identity, files, iddoc, document = schedule.sidecar_files(contract, args.shadow, segments, raw_members,
                                                                  contract_sha256=authority,
                                                                  order=args.processing_order, chunk_size=chunk,
                                                                  **profile)
    except schedule.ScheduleError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    root = _io(args.output_root)
    state = materialize(root / "sha256", identity, files, root / ".staging",
                        stop_after_members=args.stop_after_members, successor_of=args.successor_of)
    target = Path(args.output_root) / "sha256" / identity / schedule.SCHEDULE_FILE
    try:
        verified = schedule.verify_sidecar(target, args.shadow, contract_sha256=authority,
                                           require_pinned_profile=False, **profile)
    except schedule.ScheduleError as exc:
        raise BuildRefused(f"READER_VERIFICATION_{exc.code}", str(exc)) from exc
    if verified["schedule_identity"] != identity:
        raise BuildRefused("READER_VERIFICATION_DIFFERS", "the reader's identity differs from the build's")
    build_block = {"tool": "tools/build_official_shadow_schedule.py",
                   "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "reader_sha256": hashlib.sha256(Path(schedule.__file__).read_bytes()).hexdigest(),
                   "processing_order": args.processing_order or "natural", "chunk_size": chunk, "state": state,
                   "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                   "built_at_role": "BUILD_CLOCK_ONLY_NOT_OBSERVATION_OR_AVAILABILITY_TIME_NOT_CONTENT"}
    manifest = {"schema": MANIFEST_SCHEMA, "producer": PRODUCER, "population": schedule.POPULATION,
                "identity": identity, "identity_document": iddoc,
                "contract": {"id": schedule.CONTRACT_ID, "sha256": authority},
                "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                            for name, data in sorted(files.items())},
                "shadow": document["shadow"], "acquisition": document["acquisition"],
                "summary": document["summary"], "counts": document["counts"], "labels": document["labels"],
                "profile": verified["profile"], "build": build_block, "network_requests": 0}
    report, manifest_state, manifest_sha = _write_manifest(Path(args.manifest_root), identity, manifest)
    return {"identity": identity, "schedule": str(target), "state": state, "manifest": report,
            "manifest_state": manifest_state, "manifest_sha256": manifest_sha, "identity_document": iddoc,
            "acquisition": document["acquisition"], "counts": document["counts"], "summary": document["summary"],
            "profile": verified["profile"], "profile_pinned": verified["profile_pinned"], "contract_sha256": authority,
            "members": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "network_requests": 0}


def build_expansion(args: argparse.Namespace, *, contract_authority: str | None = None,
                    predecessor_profile: Any = _DEFAULT, shadow_profile: Any = _DEFAULT) -> dict[str, Any]:
    """The BAT-727 successor sidecar from the verified V1 sidecar's retained bytes (no network, create-only)."""
    from aggie_analytics.retrospective_baseline import schedule_expansion as sx  # noqa: PLC0415

    chunk = int(args.chunk_size)
    contract = pv.read_chunked(args.contract, chunk)
    authority = contract_authority or sx.CONTRACT_SHA256
    contract_sha = hashlib.sha256(contract).hexdigest()
    if contract_sha != authority:
        raise BuildRefused("CONTRACT_NOT_COMMITTED_AUTHORITY", f"{args.contract} hashes to {contract_sha}, the "
                                                               f"successor reader pins {authority}")
    authorities: dict[str, Any] = {}
    if predecessor_profile is not _DEFAULT:
        authorities["predecessor_profile"] = predecessor_profile
    if shadow_profile is not _DEFAULT:
        authorities["shadow_profile"] = shadow_profile
    try:
        identity, files, iddoc, document = sx.expansion_files(contract, args.shadow, args.predecessor,
                                                              contract_sha256=authority,
                                                              order=args.processing_order, chunk_size=chunk,
                                                              **authorities)
    except sx.ScheduleError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    root = _io(args.output_root)
    state = materialize(root / "sha256", identity, files, root / ".staging",
                        stop_after_members=args.stop_after_members, successor_of=args.successor_of)
    target = Path(args.output_root) / "sha256" / identity / sx.SCHEDULE_FILE
    try:
        verified = sx.verify_expansion(target, args.shadow, contract_sha256=authority, require_pinned_profile=False,
                                       **authorities)
    except sx.ScheduleError as exc:
        raise BuildRefused(f"READER_VERIFICATION_{exc.code}", str(exc)) from exc
    if verified["schedule_identity"] != identity:
        raise BuildRefused("READER_VERIFICATION_DIFFERS", "the reader's identity differs from the build's")
    build_block = {"tool": "tools/build_official_shadow_schedule.py build-expansion",
                   "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "reader_sha256": hashlib.sha256(Path(sx.__file__).read_bytes()).hexdigest(),
                   "predecessor_reader_sha256": hashlib.sha256(Path(schedule.__file__).read_bytes()).hexdigest(),
                   "processing_order": args.processing_order or "natural", "chunk_size": chunk, "state": state,
                   "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                   "built_at_role": "BUILD_CLOCK_ONLY_NOT_OBSERVATION_POLICY_OR_AVAILABILITY_TIME_NOT_CONTENT"}
    manifest = {"schema": EXPANSION_MANIFEST_SCHEMA, "producer": EXPANSION_PRODUCER, "population": sx.POPULATION,
                "identity": identity, "identity_document": iddoc,
                "contract": {"id": sx.CONTRACT_ID, "sha256": authority},
                "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                            for name, data in sorted(files.items())},
                "predecessor": document["predecessor"], "shadow": document["shadow"],
                "acquisition": document["acquisition"], "policy": document["policy"],
                "availability": document["availability"], "summary": document["summary"],
                "counts": document["counts"], "labels": document["labels"], "profile": verified["profile"],
                "build": build_block, "network_requests": 0}
    report, manifest_state, manifest_sha = _write_manifest(Path(args.manifest_root), identity, manifest)
    return {"identity": identity, "schedule": str(target), "state": state, "manifest": report,
            "manifest_state": manifest_state, "manifest_sha256": manifest_sha, "identity_document": iddoc,
            "predecessor": document["predecessor"], "availability": document["availability"],
            "counts": document["counts"], "summary": document["summary"], "profile": verified["profile"],
            "profile_pinned": verified["profile_pinned"], "contract_sha256": authority,
            "members": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "network_requests": 0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_official_shadow_schedule", allow_abbrev=False,
                                     description="Create-only build of the BAT-726 official schedule evidence sidecar "
                                                 "from a retained local capture (no network).")
    sub = parser.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("build", allow_abbrev=False)
    p.add_argument("--contract", required=True, type=Path)
    p.add_argument("--shadow", required=True, type=Path)
    p.add_argument("--acquisition", required=True, type=Path)
    p.add_argument("--output-root", required=True, type=Path)
    p.add_argument("--manifest-root", required=True, type=Path)
    p.add_argument("--chunk-size", default=str(1 << 20))
    p.add_argument("--processing-order", default=None, help="natural, reversed or shuffled:<seed>")
    p.add_argument("--stop-after-members", type=int, default=None,
                   help="interrupt after writing this many staged members (resume proof; publishes nothing)")
    p.add_argument("--successor-of", dest="successor_of", default=None,
                   help="the frozen predecessor identity a deliberate corrected successor replaces as current")
    e = sub.add_parser("build-expansion", allow_abbrev=False,
                       help="the BAT-727 successor from a verified V1 sidecar's retained bytes (no network)")
    e.add_argument("--contract", required=True, type=Path)
    e.add_argument("--shadow", required=True, type=Path)
    e.add_argument("--predecessor", required=True, type=Path,
                   help="the accepted V1 sidecar's schedule.json (verified, copied byte for byte, never edited)")
    e.add_argument("--output-root", required=True, type=Path)
    e.add_argument("--manifest-root", required=True, type=Path)
    e.add_argument("--chunk-size", default=str(1 << 20))
    e.add_argument("--processing-order", default=None, help="natural, reversed or shuffled:<seed>")
    e.add_argument("--stop-after-members", type=int, default=None,
                   help="interrupt after writing this many staged members (resume proof; publishes nothing)")
    e.add_argument("--successor-of", dest="successor_of", default=None,
                   help="the frozen predecessor identity a deliberate corrected successor replaces as current")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_expansion(args) if args.stage == "build-expansion" else build_sidecar(args)
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
