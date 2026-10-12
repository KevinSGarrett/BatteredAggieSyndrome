"""Synthetic fixtures for the BAT-725 UNTRUSTED_SHADOW snapshot (no real provider bytes, no real anchor).

A shadow world builds a synthetic BAT-724 preview (the BAT-724 fixture's synthetic capsule and preview contract,
through the accepted preview builder) and derives a shadow contract from the committed shadow contract with the fixture
preview's own pins; its SHA-256 is the fixture authority tests pass explicitly. Anchor receipts here are FIXTURE-ONLY
Jira-shaped JSON documents (a fixture author, the fixture comment id and a chosen created time) and the profile that
pins them is passed explicitly to the reader: neither can ever enter the packaged profile, which only names the real
anchor (the committed contract SHA-256 and the packaged profile remain the only defaults).
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
from argparse import Namespace
from pathlib import Path
from typing import Any, Callable

import provider_record_baseline_preview_fixture as pfx

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "configs" / "provider_record_shadow_20261017_contract.json"
#: The fixture anchor's service-created time: after the fixture observation end (2026-10-11T18:15:55.744674Z) and
#: before every fixture provider-reported start (the earliest is 2026-10-17T16:00:00Z).
FIXTURE_CREATED = "2026-10-12T01:30:00.000-0500"
FIXTURE_COMMENT_ID = "700001"
EXT = "\\\\?\\"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ext(path: Path | str) -> str:
    """The extended-length spelling (nested snapshot members exceed the classic path limit on Windows)."""
    text = os.path.abspath(path)
    return EXT + text if os.name == "nt" and not text.startswith(EXT) else text


def read_tree(directory: Path | str) -> dict[str, bytes]:
    root = ext(directory)
    out: dict[str, bytes] = {}
    for base, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names):
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                out[os.path.relpath(full, root).replace(os.sep, "/")] = handle.read()
    return out


def write_tree(directory: Path | str, files: dict[str, bytes]) -> None:
    root = ext(directory)
    for name, data in files.items():
        target = os.path.join(root, *name.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "xb") as handle:
            handle.write(data)


def service_time(moment: dt.datetime, offset_hours: int = -5) -> str:
    """A Jira-style service time (milliseconds, +hhmm/-hhmm) for a UTC instant."""
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    local = moment.astimezone(tz)
    sign = "-" if offset_hours < 0 else "+"
    return local.strftime("%Y-%m-%dT%H:%M:%S.") + f"{local.microsecond // 1000:03d}" + \
        f"{sign}{abs(offset_hours):02d}00"


def adf(text: str) -> dict[str, Any]:
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": line}]}
                        for line in text.splitlines() if line.strip()]}


class ShadowWorld:
    """One synthetic preview plus the shadow contract that pins it."""

    def __init__(self, root: Path, events: list[dict[str, Any]] | None = None, *,
                 raw_doc: dict[str, Any] | None = None) -> None:
        from aggie_analytics.retrospective_baseline import preview  # noqa: PLC0415
        from tools import build_provider_record_baseline_preview as preview_builder  # noqa: PLC0415

        self.root = Path(root)
        self.preview_world = pfx.PreviewWorld(self.root / "pw", events, raw_doc=raw_doc)
        built = preview_builder.build(self.preview_world.build_args(self.root / "pb"))
        self.preview = Path(built["preview"])
        verified = preview.verify_preview(self.preview, contract_sha256=self.preview_world.authority)
        doc = verified["document"]
        self.preview_identity = verified["preview_identity"]
        self.capsule_identity = doc["input"]["capsule_identity"]
        cohort = f"{preview.CAPSULE_ROOT}/{self.capsule_identity}/inputs/EXPECTED_COHORT.json"
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["input"].update(
            preview_identity=self.preview_identity, preview_sha256=verified["preview_sha256"],
            preview_contract_sha256=self.preview_world.authority, capsule_identity=self.capsule_identity,
            capsule_sha256=doc["input"]["capsule_sha256"],
            capsule_contract_sha256=doc["input"]["capsule_contract_sha256"],
            source_body_sha256=doc["input"]["source_body_sha256"], receipt_sha256=doc["input"]["receipt_sha256"],
            expected_cohort_sha256=doc["bundle"][cohort]["sha256"], expected_events=len(doc["games"]),
            expected_participants=len(doc["features"]), expected_predictions=len(doc["estimates"]),
            observation_interval=[doc["input"]["observation"]["request_start_utc"],
                                  doc["input"]["observation"]["request_end_utc"]])
        self.contract = (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        self.authority = sha256(self.contract)
        self.contract_path = self.root / "shadow-contract.json"
        self.contract_path.write_bytes(self.contract)
        self.games = doc["games"]

    # ---- builder arguments
    def payload_args(self, out: Path, **overrides: Any) -> Namespace:
        values = {"stage": "payload", "contract": self.contract_path, "preview": self.preview,
                  "output_root": Path(out) / "c", "manifest_root": Path(out) / "m", "processing_order": None,
                  "chunk_size": str(1 << 20), "stop_after_members": None, "successor_of": None,
                  "contract_authority": self.authority}
        values.update(overrides)
        return Namespace(**values)

    def snapshot_args(self, out: Path, payload: Path, receipt: Path, **overrides: Any) -> Namespace:
        values = {"stage": "snapshot", "contract": self.contract_path, "preview": self.preview,
                  "payload": Path(payload), "anchor_receipt": Path(receipt), "output_root": Path(out) / "c",
                  "manifest_root": Path(out) / "m", "processing_order": None, "chunk_size": str(1 << 20),
                  "stop_after_members": None, "successor_of": None, "contract_authority": self.authority}
        values.update(overrides)
        return Namespace(**values)

    # ---- fixture-only anchor receipts
    def receipt_bytes(self, payload_path: Path, *, created: str = FIXTURE_CREATED, updated: str | None = None,
                      comment_id: Any = FIXTURE_COMMENT_ID, issue_id: str = "25892",
                      text: Callable[[str], str] | None = None) -> bytes:
        from aggie_analytics.retrospective_baseline import shadow  # noqa: PLC0415

        data = Path(ext(payload_path)).read_bytes()
        body = shadow.anchor_body(json.loads(data.decode("utf-8")), sha256(data), len(data))
        if text is not None:
            body = text(body)
        doc = {"self": f"{shadow.ANCHOR_SPEC['tenant']}/rest/api/3/issue/{issue_id}/comment/{comment_id}",
               "id": comment_id, "author": {"accountId": "fixture-account", "displayName": "FIXTURE ONLY"},
               "body": adf(body), "updateAuthor": {"accountId": "fixture-account", "displayName": "FIXTURE ONLY"},
               "created": created, "updated": created if updated is None else updated, "jsdPublic": True}
        return json.dumps(doc).encode("utf-8")

    def write_receipt(self, payload_path: Path, out: Path, **kwargs: Any) -> Path:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.receipt_bytes(payload_path, **kwargs))
        return path

    def build(self, out: Path, **receipt_kwargs: Any) -> dict[str, Any]:
        """Payload, a fixture receipt and the snapshot under ``out``; returns paths, results and the fixture
        profile."""
        from tools import build_provider_record_shadow as builder  # noqa: PLC0415

        payload = builder.build(self.payload_args(out))
        receipt = self.write_receipt(Path(payload["payload"]), Path(out) / "receipt.json", **receipt_kwargs)
        snapshot = builder.build(self.snapshot_args(out, Path(payload["payload"]), receipt))
        return {"payload": payload, "receipt": receipt, "snapshot": snapshot,
                "path": Path(snapshot["snapshot"]), "profile": snapshot["profile"]}


def forge(snapshot_path: Path, work: Path, *, payload_edit: Callable[[dict], None] | None = None,
          receipt_edit: Callable[[dict], None] | None = None, snapshot_edit: Callable[[dict], None] | None = None,
          rerender_body: bool = True, file_edit: Callable[[dict[str, bytes]], None] | None = None) -> Path:
    """A coordinated forgery of a genuine snapshot copy: the payload, the receipt and/or the snapshot document are
    edited; the receipt body is re-rendered for the edited payload; the snapshot's payload binding, anchor record,
    timing, counts and bundle are recomputed; and the directory is renamed to the recomputed identity -- every outer
    hash is consistent, so only a semantic rule can refuse it."""
    from aggie_analytics.retrospective_baseline import shadow  # noqa: PLC0415

    files = read_tree(snapshot_path.parent)
    snap = json.loads(files.pop(shadow.SNAPSHOT_FILE).decode("utf-8"))
    payload = json.loads(files[shadow.PAYLOAD_FILE].decode("utf-8"))
    if payload_edit is not None:
        payload_edit(payload)
        files[shadow.PAYLOAD_FILE] = shadow.file_bytes(payload)
    data = files[shadow.PAYLOAD_FILE]
    receipt = json.loads(files[shadow.ANCHOR_MEMBER].decode("utf-8"))
    if rerender_body:
        receipt["body"] = adf(shadow.anchor_body(payload, sha256(data), len(data)))
    if receipt_edit is not None:
        receipt_edit(receipt)
    files[shadow.ANCHOR_MEMBER] = json.dumps(receipt).encode("utf-8")
    raw = files[shadow.ANCHOR_MEMBER]
    snap["payload"].update(sha256=sha256(data), bytes=len(data), counts=payload.get("counts"))
    anchor = snap["anchor"]
    anchor.update(comment_id=receipt.get("id"), created=receipt.get("created"), updated=receipt.get("updated"),
                  body_text_sha256=sha256(shadow.adf_text(receipt.get("body")).encode("utf-8")),
                  receipt_sha256=sha256(raw), receipt_bytes=len(raw))
    try:
        anchor["created_utc"] = shadow.iso_micro(shadow.parse_service_time(receipt.get("created")))
        timing = shadow.timing_rows(payload, anchor["created_utc"])
        snap["timing"]["events"] = timing
        anchored = {t["event_key"] for t in timing if t["decision"] == shadow.ANCHORED}
        predictions = payload.get("predictions") or []
        snap["counts"].update(anchored_events=len(anchored), ineligible_events=len(timing) - len(anchored),
                              anchored_predictions=sum(x.get("event_key") in anchored for x in predictions),
                              ineligible_predictions=sum(x.get("event_key") not in anchored for x in predictions))
    except (shadow.ShadowError, KeyError, TypeError):
        pass  # an invalid time stays as edited; the receipt rule refuses it first
    if snapshot_edit is not None:
        snapshot_edit(snap)
    if file_edit is not None:
        file_edit(files)
    snap["bundle"] = {name: {"sha256": sha256(files[name]), "bytes": len(files[name])} for name in sorted(files)}
    identity = shadow.snapshot_identity(snap)
    target = Path(work) / identity
    write_tree(target, {**files, shadow.SNAPSHOT_FILE: shadow.file_bytes(snap)})
    return target / shadow.SNAPSHOT_FILE


def rehouse(snapshot_path: Path, target_parent: Path) -> Path:
    """A byte copy of the whole snapshot directory under another parent (same identity directory name)."""
    target = Path(target_parent) / snapshot_path.parent.name
    write_tree(target, read_tree(snapshot_path.parent))
    return target / snapshot_path.name


def copy_events(mutator: Callable[[list[dict[str, Any]]], None]) -> list[dict[str, Any]]:
    """The three synthetic events with one mutation applied."""
    return pfx.events_with(mutator)


def deep(value: Any) -> Any:
    return copy.deepcopy(value)
