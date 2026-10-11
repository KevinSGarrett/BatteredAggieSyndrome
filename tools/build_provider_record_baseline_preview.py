r"""Build the explicit provider-record baseline preview (BAT-724, Cycle #52 TP52-A01).

``python -B tools/build_provider_record_baseline_preview.py
--contract configs/provider_record_baseline_preview_20261011_contract.json
--capsule <data>/canonical/prospective_provider_observation_20261011/sha256/<capsule identity>/capsule.json
--output-root <data>/canonical/provider_record_baseline_preview_20261011
--manifest-root <data>/manifests/provider_record_baseline_preview_20261011``

The builder refuses unless the contract bytes are exactly the committed contract the reader pins
(:data:`aggie_analytics.retrospective_baseline.preview.CONTRACT_SHA256`). The input capsule is verified completely by
the accepted BAT-723 reader against the capsule identity, file hash and observation contract the preview contract pins;
nothing else is read and no network is used.

Materialization is create-only and content addressed: ``preview.json``, the contract bytes and a byte copy of the
capsule directory are written into a fresh staging directory under ``<output-root>/.staging``, re-read and compared, and
the staging directory is then renamed in one operation to ``<output-root>/sha256/<preview identity>``. An existing
identity directory must hold exactly the same members and bytes (``ALREADY_PRESENT_IDENTICAL``, nothing is written) or
the build refuses. An interrupted build (``--stop-after-members``) leaves no directory at the identity path, so the
reader cannot mistake it for a complete preview; a resumed build yields identical bytes. ``--processing-order`` and
``--chunk-size`` prove that processing order and read chunking never change a byte. The materialized preview is then
opened through the reader's complete verification, and the run manifest (which alone records the build clock) is
written once to ``<manifest-root>/sha256/<identity>/run_manifest.json``.
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

from aggie_analytics.retrospective_baseline import preview  # noqa: E402

PRODUCER = "provider_record_baseline_preview/1.0.0"
MANIFEST_SCHEMA = "BAS-PROVIDER-RECORD-BASELINE-PREVIEW-RUN-MANIFEST-1"
INTERRUPTED_EXIT = 3


class BuildRefused(RuntimeError):
    """A refused build; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class BuildInterrupted(RuntimeError):
    """A deliberately interrupted build (``--stop-after-members``); nothing was published."""


def directory_members(directory: Path) -> dict[str, bytes]:
    return preview.directory_files(str(directory))


def materialize(output_root: Path, identity: str, files: dict[str, bytes], *,
                stop_after_members: int | None = None) -> str:
    """Publish the preview directory create-only; returns MATERIALIZED or ALREADY_PRESENT_IDENTICAL."""
    final = Path(output_root) / "sha256" / identity
    if final.exists():
        if directory_members(final) != files:
            raise BuildRefused("EXISTING_IDENTITY_DIFFERS", f"{final} exists with different members or bytes")
        return "ALREADY_PRESENT_IDENTICAL"
    # A short staging name: the nested capsule directory keeps every member below the classic path limit.
    staging = Path(output_root) / ".staging" / f"{time.time_ns()}-{os.getpid()}"
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
    contract = preview.read_chunked(args.contract, chunk)
    contract_sha = hashlib.sha256(contract).hexdigest()
    authority = getattr(args, "contract_authority", None) or preview.CONTRACT_SHA256
    if contract_sha != authority:
        raise BuildRefused("CONTRACT_NOT_COMMITTED_AUTHORITY", f"{args.contract} hashes to {contract_sha}, the reader "
                                                               f"pins {authority}")
    try:
        identity, files, iddoc, document = preview.build_preview(args.capsule, contract, contract_sha256=authority,
                                                                 order=args.processing_order, chunk_size=chunk)
    except preview.PreviewError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    # Every write and read below goes through the extended-length spelling on Windows (the nested capsule members of a
    # deep output root exceed the classic path limit); reported paths stay the caller's literal spelling.
    output_io = Path(preview.io_path(os.path.abspath(args.output_root)))
    state = materialize(output_io, identity, files, stop_after_members=args.stop_after_members)
    target = Path(args.output_root) / "sha256" / identity / preview.PREVIEW_FILE
    try:
        verified = preview.verify_preview(target, contract_sha256=authority)
    except preview.PreviewError as exc:
        raise BuildRefused(f"READER_VERIFICATION_{exc.code}", str(exc)) from exc
    if verified["preview_identity"] != identity:
        raise BuildRefused("READER_VERIFICATION_DIFFERS", "the reader's identity differs from the build's")
    manifest_report = Path(args.manifest_root) / "sha256" / identity / "run_manifest.json"
    manifest_path = Path(preview.io_path(os.path.abspath(args.manifest_root))) / "sha256" / identity / \
        "run_manifest.json"
    manifest_state = "ALREADY_PRESENT"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("identity") != identity or existing.get("identity_document") != iddoc:
            raise BuildRefused("EXISTING_MANIFEST_DIFFERS", f"{manifest_path} names another preview")
    else:
        manifest = {"schema": MANIFEST_SCHEMA, "producer": PRODUCER, "population": preview.POPULATION,
                    "identity": identity, "identity_document": iddoc,
                    "contract": {"id": preview.CONTRACT_ID, "sha256": contract_sha},
                    "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                                for name, data in sorted(files.items())},
                    "input": {k: document["input"][k] for k in ("capsule_identity", "capsule_sha256",
                                                                "capsule_contract_sha256", "source_body_sha256")},
                    "counts": document["counts"], "summary": document["summary"], "labels": document["labels"],
                    "models": {m: document["models"][m]["sha256"] for m in preview.MODEL_IDS},
                    "build": {"tool": "tools/build_provider_record_baseline_preview.py",
                              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              "reader_sha256": hashlib.sha256(Path(preview.__file__).read_bytes()).hexdigest(),
                              "processing_order": args.processing_order or "natural", "chunk_size": chunk,
                              "preview_state": state,
                              "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                              "built_at_role": "BUILD_CLOCK_ONLY_NOT_OBSERVATION_OR_FORECAST_TIME_NOT_CONTENT"},
                    "network_requests": 0}
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "preview": str(target), "preview_state": state, "manifest": str(manifest_report),
            "manifest_state": manifest_state, "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "identity_document": iddoc, "counts": document["counts"], "contract_sha256": contract_sha,
            "capsule_identity": document["input"]["capsule_identity"],
            "members": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
            "processing_order": args.processing_order or "natural", "chunk_size": chunk, "network_requests": 0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_provider_record_baseline_preview", allow_abbrev=False,
                                     description="Create-only build of the BAT-724 provider-record baseline preview "
                                                 "from the accepted local capsule (no network).")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--capsule", required=True, type=Path)
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
