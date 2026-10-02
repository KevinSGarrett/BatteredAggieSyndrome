r"""Cycle #37 — Attempt #3 — byte-verified receipt authority for scoring and PIT admission (MF37A02-02/03).

The Attempt #2 manager showed that the installed scoring and PIT gates admitted *claims about* evidence:

* ``admit_for_scoring`` returned ``ADMITTED_FOR_SCORING`` for two invented 64-character digests with no
  receipt or packet bytes behind them, and model/input binding happened only when a caller chose to pass
  ``receipt_model_identity``;
* ``classify_pit`` returned ``PIT_PROVEN_BY_PER_PRIOR_RECEIPTS`` for a self-asserted receipt naming
  ``UNRELATED-PRIOR`` and admitted a row whose features consumed ``REQUIRED-PRIOR``.

A digest is an identity for bytes, not evidence that the bytes exist; a receipt dictionary handed in by a
caller is a claim, not a receipt. This module is the one place a gate turns a digest into verified bytes:

* a :class:`ReceiptAuthority` is a declared, content-addressed store: ``receipts/<sha256>.json`` holds a
  receipt's exact bytes and ``payloads/<sha256>.bin`` the bytes the receipt attests (a frozen packet, an
  official final's raw source, a prior's publication);
* :meth:`ReceiptAuthority.resolve` re-hashes both files, refuses a digest whose bytes are absent, altered or
  of the wrong receipt kind, and refuses a receipt from a source the authority does not trust;
* every authority carries its **class**. ``TEST_ONLY_FIXTURE_AUTHORITY`` exists so a locally created fixture
  can exercise the admitted path; constructing one needs an explicit acknowledgement and a matching marker
  file in its root, it may not live inside the canonical data root, and every admission it supports is
  labelled with that class. ``DURABLE_RECEIPT_STORE`` is the only class whose admissions count as real
  eligibility, and no durable store is declared (:data:`DECLARED_DURABLE_STORES` is empty): constructing one
  refuses. Real eligible forecasts and real proven PIT rows therefore stay zero until a durable store with
  real receipts is separately declared -- by construction, not by convention.

Nothing here creates a receipt, a timestamp or a forecast.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from aggie_analytics.cycle37.admission_domains import DomainVerdict, valid_digest

__all__ = [
    "AUTHORITY_VERSION",
    "DECLARED_DURABLE_STORES",
    "DURABLE",
    "FINAL_RECEIPT",
    "FORECAST_RECEIPT",
    "PRIOR_RECEIPT",
    "ReceiptAuthority",
    "ReceiptAuthorityError",
    "TEST_ONLY",
    "VerifiedReceipt",
    "create_test_only_store",
    "write_fixture_receipt",
]

AUTHORITY_VERSION = "BAS-RECEIPT-AUTHORITY-v37.3"
TEST_ONLY = "TEST_ONLY_FIXTURE_AUTHORITY"
DURABLE = "DURABLE_RECEIPT_STORE"
TEST_ONLY_MARKER = "TEST_ONLY_AUTHORITY.json"

FORECAST_RECEIPT = "BAS_FORECAST_FREEZE_RECEIPT_V1"
FINAL_RECEIPT = "BAS_OFFICIAL_FINAL_RECEIPT_V1"
PRIOR_RECEIPT = "BAS_PRIOR_PUBLICATION_RECEIPT_V1"
RECEIPT_KINDS = frozenset({FORECAST_RECEIPT, FINAL_RECEIPT, PRIOR_RECEIPT})

#: Roots a ``DURABLE_RECEIPT_STORE`` may be constructed over. Empty: no durable forecast/final/prior receipt
#: store has been declared (the ORIGINAL-OBL-OBL_FORECAST_RECEIPT_STORE obligation remains owned backlog).
#: Adding one is a reviewed source change, not a runtime argument.
DECLARED_DURABLE_STORES: tuple[str, ...] = ()

#: The canonical data root. A test-only authority inside it would put fixtures beside real evidence.
_CANONICAL_DATA_ROOT = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or r"C:\BatteredAggieSyndrome.data"


class ReceiptAuthorityError(ValueError):
    """Raised when an authority cannot be constructed as declared."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class VerifiedReceipt:
    """A receipt whose bytes and attested payload bytes were re-hashed by an authority."""

    digest: str
    kind: str
    content: Mapping[str, Any]
    payload_digest: str
    authority_id: str
    authority_class: str
    trusted_source: str
    extra: Mapping[str, Any] = field(default_factory=dict)

    def evidence(self) -> dict[str, Any]:
        return {"receipt_digest": self.digest, "receipt_kind": self.kind, "payload_digest": self.payload_digest,
                "authority_id": self.authority_id, "authority_class": self.authority_class,
                "source_id": self.trusted_source}


class ReceiptAuthority:
    """A declared, content-addressed receipt store that resolves digests only to re-verified bytes."""

    def __init__(self, root: Path | str, *, authority_class: str, authority_id: str,
                 trusted_source_ids: frozenset[str] | set[str] | tuple[str, ...],
                 acknowledge_test_only: bool = False) -> None:
        self.root = Path(root).resolve()
        self.authority_class = authority_class
        self.authority_id = str(authority_id)
        self.trusted_source_ids = frozenset(str(s) for s in trusted_source_ids)
        if not self.root.is_dir():
            raise ReceiptAuthorityError(f"authority root {self.root} does not exist")
        if not self.trusted_source_ids:
            raise ReceiptAuthorityError("an authority must name the sources it trusts")
        if authority_class == TEST_ONLY:
            if not acknowledge_test_only:
                raise ReceiptAuthorityError("a test-only authority must be acknowledged explicitly; its admissions "
                                            "are fixtures, never real eligibility")
            if _inside(self.root, Path(_CANONICAL_DATA_ROOT)):
                raise ReceiptAuthorityError("a test-only authority may not live inside the canonical data root")
            marker = self.root / TEST_ONLY_MARKER
            try:
                declared = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ReceiptAuthorityError(f"a test-only authority root needs a readable {TEST_ONLY_MARKER}") from error
            if declared.get("authority_class") != TEST_ONLY or declared.get("authority_id") != self.authority_id:
                raise ReceiptAuthorityError("the authority's marker file does not declare this test-only authority")
        elif authority_class == DURABLE:
            if os.path.normcase(str(self.root)) not in {os.path.normcase(str(Path(p).resolve()))
                                                         for p in DECLARED_DURABLE_STORES}:
                raise ReceiptAuthorityError(
                    "no durable receipt store is declared at this root; DECLARED_DURABLE_STORES is "
                    f"{list(DECLARED_DURABLE_STORES)}, so real eligibility cannot be asserted here")
        else:
            raise ReceiptAuthorityError(f"unknown authority class {authority_class!r}")

    @property
    def counts_as_real_evidence(self) -> bool:
        return self.authority_class == DURABLE

    def describe(self) -> dict[str, Any]:
        return {"authority_version": AUTHORITY_VERSION, "authority_id": self.authority_id,
                "authority_class": self.authority_class, "root": str(self.root),
                "trusted_source_ids": sorted(self.trusted_source_ids),
                "counts_as_real_evidence": self.counts_as_real_evidence}

    def _read(self, relative: str) -> bytes | None:
        path = (self.root / relative).resolve()
        if not _inside(path, self.root) or not path.is_file():
            return None
        return path.read_bytes()

    def resolve(self, digest: Any, *, expected_kind: str) -> DomainVerdict:
        """Re-verify a receipt and the payload it attests. ``value`` is a :class:`VerifiedReceipt` on success."""

        shape = valid_digest(digest, label="receipt digest")
        if not shape:
            return shape
        data = self._read(f"receipts/{digest}.json")
        if data is None:
            return DomainVerdict(False, "REFUSED_RECEIPT_BYTES_ABSENT",
                                 f"no receipt bytes for {digest[:16]}... in authority {self.authority_id}; a digest "
                                 f"with nothing behind it is not a receipt")
        if _sha256(data) != digest:
            return DomainVerdict(False, "REFUSED_RECEIPT_BYTES_DO_NOT_MATCH_THE_DIGEST",
                                 f"the stored receipt re-hashes to {_sha256(data)[:16]}..., not {digest[:16]}...")
        try:
            content = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return DomainVerdict(False, "REFUSED_RECEIPT_IS_NOT_JSON", "the receipt bytes are not a JSON document")
        if not isinstance(content, dict):
            return DomainVerdict(False, "REFUSED_RECEIPT_IS_NOT_AN_OBJECT", "the receipt is not a JSON object")
        if content.get("receipt_kind") != expected_kind:
            return DomainVerdict(False, "REFUSED_RECEIPT_KIND_MISMATCH",
                                 f"receipt kind {content.get('receipt_kind')!r}, expected {expected_kind!r}")
        source = str(content.get("source_id") or "")
        if source not in self.trusted_source_ids:
            return DomainVerdict(False, "REFUSED_RECEIPT_SOURCE_NOT_TRUSTED",
                                 f"source {source!r} is not trusted by authority {self.authority_id}")
        payload = content.get("payload_sha256")
        payload_shape = valid_digest(payload, label="receipt payload_sha256")
        if not payload_shape:
            return payload_shape
        payload_bytes = self._read(f"payloads/{payload}.bin")
        if payload_bytes is None:
            return DomainVerdict(False, "REFUSED_PAYLOAD_BYTES_ABSENT",
                                 f"the receipt attests payload {payload[:16]}... but the authority holds no such bytes")
        if _sha256(payload_bytes) != payload:
            return DomainVerdict(False, "REFUSED_PAYLOAD_BYTES_DO_NOT_MATCH_THE_DIGEST",
                                 f"the attested payload re-hashes to {_sha256(payload_bytes)[:16]}..., not {payload[:16]}...")
        receipt = VerifiedReceipt(digest=digest, kind=expected_kind, content=MappingProxyType(dict(content)),
                                  payload_digest=payload, authority_id=self.authority_id,
                                  authority_class=self.authority_class, trusted_source=source)
        return DomainVerdict(True, "RECEIPT_BYTES_AND_PAYLOAD_VERIFIED",
                             f"receipt {digest[:16]}... and payload {payload[:16]}... re-hash in {self.authority_id} "
                             f"({self.authority_class})", receipt)

    def payload(self, receipt: VerifiedReceipt) -> bytes:
        data = self._read(f"payloads/{receipt.payload_digest}.bin")
        if data is None or _sha256(data) != receipt.payload_digest:
            raise ReceiptAuthorityError("the payload changed after it was verified")
        return data


def write_fixture_receipt(root: Path | str, content: Mapping[str, Any], payload: bytes) -> tuple[str, str]:
    """Write one receipt and its payload into a test-only fixture store; return (receipt, payload) digests.

    For tests and the attempt's own fixture probes only. The receipt's ``payload_sha256`` is computed from the
    payload bytes given, so a fixture can never attest bytes it does not hold.
    """

    root = Path(root)
    (root / "receipts").mkdir(parents=True, exist_ok=True)
    (root / "payloads").mkdir(parents=True, exist_ok=True)
    payload_digest = _sha256(payload)
    (root / "payloads" / f"{payload_digest}.bin").write_bytes(payload)
    document = dict(content, payload_sha256=payload_digest)
    data = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt_digest = _sha256(data)
    (root / "receipts" / f"{receipt_digest}.json").write_bytes(data)
    return receipt_digest, payload_digest


def create_test_only_store(root: Path | str, authority_id: str) -> Path:
    """Create an empty, marked test-only fixture store (the marker is what makes it constructible)."""

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / TEST_ONLY_MARKER).write_text(json.dumps({"authority_class": TEST_ONLY, "authority_id": authority_id,
                                                     "purpose": "fixture receipts only; never real eligibility"},
                                                    sort_keys=True), encoding="utf-8")
    return root
