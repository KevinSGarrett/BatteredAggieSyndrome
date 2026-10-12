r"""Build the immutable UNTRUSTED_SHADOW provider-record snapshot in two stages (BAT-725, Cycle #53 TP53-A01).

Stage one (before the anchor exists):

``python -B tools/build_provider_record_shadow.py payload --contract configs/provider_record_shadow_20261017_contract.json
--preview <data>/canonical/provider_record_baseline_preview_20261011/sha256/<preview identity>/preview.json
--output-root <data>/canonical/provider_record_shadow_20261017 --manifest-root <data>/manifests/provider_record_shadow_20261017``

``python -B tools/build_provider_record_shadow.py anchor-body --contract ... --preview ... --payload <payload.json>
--out <body.txt>`` renders the deterministic hash-only C53-A01-M2 comment body of that exact payload (the comment itself
is posted by the separately granted platform operation, never by this tool).

Stage two (after the real comment exists and its raw readback is retained):

``python -B tools/build_provider_record_shadow.py snapshot --contract ... --preview ... --payload <payload.json>
--anchor-receipt <raw readback.json> --output-root ... --manifest-root ...``

The builder refuses unless the contract bytes are exactly the committed contract the reader pins
(:data:`aggie_analytics.retrospective_baseline.shadow.CONTRACT_SHA256`). The preview is verified completely by the
accepted BAT-724 reader against the pinned identity and contract; nothing else is read and no network is used.

Materialization is create-only and content addressed: the payload under ``<output-root>/payload/sha256/<payload
sha256>/payload.json`` and the snapshot directory (snapshot.json, payload.json, the anchor receipt, the contract and a
byte copy of the preview directory) under ``<output-root>/sha256/<snapshot identity>``. Each is written into a fresh
staging directory under ``<output-root>/.staging``, re-read and compared, then renamed in one operation. An existing
identity directory must hold exactly the same members and bytes (``ALREADY_PRESENT_IDENTICAL``) or the build refuses; a
second, different payload or snapshot in the same root refuses (``PAYLOAD_ALREADY_FROZEN``/``SNAPSHOT_ALREADY_FROZEN``)
unless ``--successor-of`` names the frozen predecessor (a deliberate corrected successor; the predecessor is never
touched). An interrupted build (``--stop-after-members``) leaves no directory at the identity path. ``--processing-order``
and ``--chunk-size`` prove that processing order and read chunking never change a byte. The materialized snapshot is
re-opened through the reader's complete verification (before the gate is packaged the actual-anchor pin is reported,
not required), and the run manifest (which alone records the build clock) is written once.
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
from aggie_analytics.retrospective_baseline import shadow  # noqa: E402

PRODUCER = "provider_record_shadow/1.0.0"
MANIFEST_SCHEMA = "BAS-PROVIDER-RECORD-SHADOW-RUN-MANIFEST-1"
INTERRUPTED_EXIT = 3


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
                stop_after_members: int | None = None, successor_of: str | None = None,
                frozen_code: str = "SNAPSHOT_ALREADY_FROZEN") -> str:
    """Publish one identity directory create-only; returns MATERIALIZED or ALREADY_PRESENT_IDENTICAL."""
    final = parent / identity
    if final.exists():
        if pv.directory_files(str(final)) != files:
            raise BuildRefused("EXISTING_IDENTITY_DIFFERS", f"{final} exists with different members or bytes")
        return "ALREADY_PRESENT_IDENTICAL"
    others = sorted(p.name for p in parent.iterdir()) if parent.is_dir() else []
    if others and others != [successor_of]:
        raise BuildRefused(frozen_code, f"{parent} already holds {others}; a corrected successor must name its frozen "
                                        "predecessor with --successor-of")
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


def _contract(args: argparse.Namespace) -> tuple[bytes, str]:
    contract = pv.read_chunked(args.contract, int(args.chunk_size))
    contract_sha = hashlib.sha256(contract).hexdigest()
    authority = getattr(args, "contract_authority", None) or shadow.CONTRACT_SHA256
    if contract_sha != authority:
        raise BuildRefused("CONTRACT_NOT_COMMITTED_AUTHORITY", f"{args.contract} hashes to {contract_sha}, the reader "
                                                               f"pins {authority}")
    return contract, authority


def _write_manifest(manifest_root: Path, rel: str, identity: str, document: dict[str, Any]) -> tuple[str, str, str]:
    """The run manifest, written once (an existing manifest must name the same identity)."""
    report = Path(manifest_root) / rel / identity / "run_manifest.json"
    path = _io(manifest_root) / rel / identity / "run_manifest.json"
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


def _build_block(args: argparse.Namespace, state: str, chunk: int) -> dict[str, Any]:
    return {"tool": "tools/build_provider_record_shadow.py",
            "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "reader_sha256": hashlib.sha256(Path(shadow.__file__).read_bytes()).hexdigest(),
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "state": state,
            "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "built_at_role": "BUILD_CLOCK_ONLY_NOT_ANCHOR_OBSERVATION_OR_FORECAST_TIME_NOT_CONTENT"}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    chunk = int(args.chunk_size)
    contract, authority = _contract(args)
    try:
        _spec, data, document = shadow.payload_files(contract, args.preview, contract_sha256=authority,
                                                     order=args.processing_order, chunk_size=chunk)
    except shadow.ShadowError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    digest = hashlib.sha256(data).hexdigest()
    root = _io(args.output_root)
    state = materialize(root / "payload" / "sha256", digest, {shadow.PAYLOAD_FILE: data}, root / ".staging",
                        stop_after_members=args.stop_after_members, successor_of=args.successor_of,
                        frozen_code="PAYLOAD_ALREADY_FROZEN")
    target = Path(args.output_root) / "payload" / "sha256" / digest / shadow.PAYLOAD_FILE
    if hashlib.sha256((_io(args.output_root) / "payload" / "sha256" / digest / shadow.PAYLOAD_FILE).read_bytes()
                      ).hexdigest() != digest:
        raise BuildRefused("PAYLOAD_READBACK_DIFFERS", "the materialized payload does not read back exactly")
    manifest = {"schema": MANIFEST_SCHEMA, "producer": PRODUCER, "population": shadow.POPULATION, "stage": "PAYLOAD",
                "identity": digest, "identity_document": {"payload_sha256": digest, "payload_bytes": len(data)},
                "contract": {"id": shadow.CONTRACT_ID, "sha256": authority},
                "source": document["source"], "counts": document["counts"], "summary": document["summary"],
                "labels": document["labels"], "models": {m: document["models"][m]["sha256"] for m in shadow.MODEL_IDS},
                "build": _build_block(args, state, chunk), "network_requests": 0}
    report, manifest_state, manifest_sha = _write_manifest(Path(args.manifest_root), "payload/sha256", digest,
                                                           manifest)
    return {"stage": "PAYLOAD", "payload_sha256": digest, "payload_bytes": len(data), "payload": str(target),
            "payload_state": state, "manifest": report, "manifest_state": manifest_state,
            "manifest_sha256": manifest_sha, "counts": document["counts"], "contract_sha256": authority,
            "preview_identity": document["source"]["preview_identity"],
            "capsule_identity": document["source"]["capsule_identity"],
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "network_requests": 0}


def anchor_body(args: argparse.Namespace) -> dict[str, Any]:
    chunk = int(args.chunk_size)
    contract, authority = _contract(args)
    try:
        _spec, expected, document = shadow.payload_files(contract, args.preview, contract_sha256=authority,
                                                         chunk_size=chunk)
    except shadow.ShadowError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    data = pv.read_chunked(_io(args.payload), chunk)
    if data != expected:
        raise BuildRefused("PAYLOAD_NOT_REDERIVED", "the payload file is not the re-derived payload")
    digest = hashlib.sha256(data).hexdigest()
    text = shadow.anchor_body(document, digest, len(data))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return {"stage": "ANCHOR_BODY", "payload_sha256": digest, "payload_bytes": len(data), "body": str(out),
            "body_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "lines": len(text.splitlines()),
            "network_requests": 0}


def build_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    chunk = int(args.chunk_size)
    contract, authority = _contract(args)
    payload = pv.read_chunked(_io(args.payload), chunk)
    receipt = pv.read_chunked(_io(args.anchor_receipt), chunk)
    try:
        identity, files, iddoc, document = shadow.snapshot_files(contract, args.preview, payload, receipt,
                                                                 contract_sha256=authority,
                                                                 order=args.processing_order, chunk_size=chunk)
    except shadow.ShadowError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    root = _io(args.output_root)
    state = materialize(root / "sha256", identity, files, root / ".staging",
                        stop_after_members=args.stop_after_members, successor_of=args.successor_of)
    target = Path(args.output_root) / "sha256" / identity / shadow.SNAPSHOT_FILE
    try:
        verified = shadow.verify_snapshot(target, contract_sha256=authority, require_pinned_profile=False)
    except shadow.ShadowError as exc:
        raise BuildRefused(f"READER_VERIFICATION_{exc.code}", str(exc)) from exc
    if verified["snapshot_identity"] != identity:
        raise BuildRefused("READER_VERIFICATION_DIFFERS", "the reader's identity differs from the build's")
    manifest = {"schema": MANIFEST_SCHEMA, "producer": PRODUCER, "population": shadow.POPULATION, "stage": "SNAPSHOT",
                "identity": identity, "identity_document": iddoc,
                "contract": {"id": shadow.CONTRACT_ID, "sha256": authority},
                "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                            for name, data in sorted(files.items())},
                "payload": document["payload"], "anchor": document["anchor"], "timing": document["timing"],
                "counts": document["counts"], "labels": document["labels"], "profile": verified["profile"],
                "build": _build_block(args, state, chunk), "network_requests": 0}
    report, manifest_state, manifest_sha = _write_manifest(Path(args.manifest_root), "sha256", identity, manifest)
    return {"stage": "SNAPSHOT", "identity": identity, "snapshot": str(target), "snapshot_state": state,
            "manifest": report, "manifest_state": manifest_state, "manifest_sha256": manifest_sha,
            "identity_document": iddoc, "payload": document["payload"], "anchor": document["anchor"],
            "timing_decisions": {t["event_key"]: t["decision"] for t in document["timing"]["events"]},
            "counts": document["counts"], "profile": verified["profile"],
            "profile_pinned": verified["profile_pinned"], "contract_sha256": authority,
            "members": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "network_requests": 0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_provider_record_shadow", allow_abbrev=False,
                                     description="Create-only two-stage build of the BAT-725 UNTRUSTED_SHADOW "
                                                 "provider-record snapshot from the accepted local preview (no "
                                                 "network; the anchor comment is a separate granted operation).")
    sub = parser.add_subparsers(dest="stage", required=True)
    for name in ("payload", "anchor-body", "snapshot"):
        p = sub.add_parser(name, allow_abbrev=False)
        p.add_argument("--contract", required=True, type=Path)
        p.add_argument("--preview", required=True, type=Path)
        p.add_argument("--chunk-size", default=str(1 << 20))
        if name in ("anchor-body", "snapshot"):
            p.add_argument("--payload", required=True, type=Path)
        if name == "anchor-body":
            p.add_argument("--out", required=True, type=Path)
            continue
        if name == "snapshot":
            p.add_argument("--anchor-receipt", dest="anchor_receipt", required=True, type=Path)
        p.add_argument("--output-root", required=True, type=Path)
        p.add_argument("--manifest-root", required=True, type=Path)
        p.add_argument("--processing-order", default=None, help="natural, reversed or shuffled:<seed>")
        p.add_argument("--stop-after-members", type=int, default=None,
                       help="interrupt after writing this many staged members (resume proof; publishes nothing)")
        p.add_argument("--successor-of", dest="successor_of", default=None,
                       help="the frozen predecessor identity a deliberate corrected successor replaces as current")
    return parser


def build(args: argparse.Namespace) -> dict[str, Any]:
    if args.stage == "payload":
        return build_payload(args)
    if args.stage == "anchor-body":
        return anchor_body(args)
    return build_snapshot(args)


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
