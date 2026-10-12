"""Synthetic fixtures for the BAT-724 provider-record baseline preview (no real provider bytes).

A preview world materializes a synthetic BAT-723 capsule (the BAT-723 fixture's scoreboard-shaped response, receipt,
cohort and fixture contract, built by the accepted capsule builder) and derives a preview contract from the committed
preview contract with the fixture capsule's own pins. Its SHA-256 is the fixture authority that tests pass explicitly to
the builder and the query (the committed contract SHA-256 remains the only default authority).
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from argparse import Namespace
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

import prospective_provider_observation_fixture as pfx

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "configs" / "provider_record_baseline_preview_20261011_contract.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PreviewWorld:
    """One synthetic capsule directory under ``root`` plus the preview contract that pins it."""

    def __init__(self, root: Path, events: list[dict[str, Any]] | None = None, *,
                 raw_doc: dict[str, Any] | None = None) -> None:
        from aggie_analytics.national_source_time import prospective  # noqa: PLC0415

        self.world = pfx.World(events, raw_doc=raw_doc)
        identity, files, _ = prospective.build_capsule(self.world.raw, self.world.receipt, self.world.expected,
                                                       self.world.contract, contract_sha256=self.world.authority)
        directory = Path(root) / "cap" / identity
        for name, data in files.items():
            path = directory / Path(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.capsule_identity = identity
        self.capsule = directory / prospective.CAPSULE_FILE
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cohort = json.loads(self.world.expected.decode("utf-8"))
        contract["input"].update(capsule_identity=identity, capsule_sha256=sha256(files[prospective.CAPSULE_FILE]),
                                 capsule_contract_sha256=self.world.authority,
                                 source_body_sha256=sha256(self.world.raw), receipt_sha256=sha256(self.world.receipt),
                                 expected_cohort_sha256=sha256(self.world.expected),
                                 expected_events=cohort["expected_events"],
                                 expected_participants=cohort["expected_participants"])
        self.contract = (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        self.authority = sha256(self.contract)
        self.contract_path = Path(root) / "preview-contract.json"
        self.contract_path.write_bytes(self.contract)

    def build_args(self, root: Path, **overrides: Any) -> Namespace:
        values = {"contract": self.contract_path, "capsule": self.capsule, "output_root": Path(root) / "canonical",
                  "manifest_root": Path(root) / "manifests", "processing_order": None, "chunk_size": str(1 << 20),
                  "stop_after_members": None, "contract_authority": self.authority}
        values.update(overrides)
        return Namespace(**values)


def events_with(mutator: Callable[[list[dict[str, Any]]], None]) -> list[dict[str, Any]]:
    """The three genuine synthetic events with one mutation applied."""
    events = pfx.genuine_events()
    mutator(events)
    return events


def competitor_of(events: list[dict[str, Any]], event_id: str, side: str) -> dict[str, Any]:
    event = next(e for e in events if e["id"] == event_id)
    return next(c for c in event["competitions"][0]["competitors"] if c["homeAway"] == side)


def oracle_q(wins: int, losses: int, ties: int) -> Fraction:
    """The smoothed record strength written independently of the product: (W + T/2 + 1) / (W + L + T + 2)."""
    return (Fraction(wins) + Fraction(ties, 2) + 1) / (wins + losses + ties + 2)


def oracle_p(q_home: Fraction, q_away: Fraction) -> Fraction:
    top = q_home * (1 - q_away)
    return top / (top + q_away * (1 - q_home))


def half_even(value: Fraction, places: int = 12) -> str:
    """Exact half-even rounding written independently of the product (via decimal-free integer steps)."""
    scale = 10 ** places
    floor = (value.numerator * scale) // value.denominator
    remainder = value * scale - floor
    if remainder > Fraction(1, 2) or (remainder == Fraction(1, 2) and floor % 2 == 1):
        floor += 1
    text = str(floor).rjust(places + 1, "0")
    return f"{text[:-places]}.{text[-places:]}"


def forge(preview_path: Path, edit: Callable[[dict[str, Any]], None], work: Path) -> Path:
    """A coordinated forgery: preview.json is edited, re-serialized canonically and housed in a directory named by the
    recomputed identity of the edited document, with the genuine bundle members copied beside it."""
    from aggie_analytics.retrospective_baseline import preview  # noqa: PLC0415

    doc = json.loads(preview_path.read_bytes().decode("utf-8"))
    forged = copy.deepcopy(doc)
    edit(forged)
    if preview.preview_file_bytes(forged) == preview.preview_file_bytes(doc):
        raise AssertionError("the forgery edit changed nothing (a no-op is not a forgery)")
    target = Path(work) / preview.preview_identity(forged)
    shutil.copytree(preview_path.parent, target)
    (target / preview.PREVIEW_FILE).write_bytes(preview.preview_file_bytes(forged))
    return target / preview.PREVIEW_FILE


def rehouse(preview_path: Path, target_parent: Path) -> Path:
    """A byte copy of the whole preview directory under another parent (same identity directory name)."""
    target = Path(target_parent) / preview_path.parent.name
    shutil.copytree(preview_path.parent, target)
    return target / preview_path.name
