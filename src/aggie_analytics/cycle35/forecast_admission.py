"""R35-06: one forecast admission contract shared by inventory and scoring.

The Cycle #34 boundary failed for a structural reason, not a missing edge
case: it asked "do these bytes hash to this value?" and treated the answer as
a statement about *when* the forecast was committed and *what* it was about.
Hash equality proves byte identity. It proves nothing about time, issuer or
participants. Cycle #34 therefore accepted (a) a receipt written seconds ago
declaring a freeze two hours after kickoff, (b) a forecast about entirely
different teams than the game it scored, and (c) a self-rehashed packet dated
2099 whose "probability" was the Boolean `True`.

This module replaces that with an explicit, typed admission contract:

1.  **Trusted issuance, not discovery.** A receipt is authority only when it
    appears in a declared `TrustedReceiptStore` -- an allowlist naming the
    issuer and the commitment time. Scanning archive roots for any JSON file
    whose bytes happen to hash correctly is *discovery*, and discovery lets
    anything writable become evidence (that is precisely how a file written
    into a manager-review directory became forecast authority). Bytes found
    on disk are corroboration of content; the allowlist is the authority.

2.  **Commitment before cutoff, established independently of the claimant.**
    The commitment time comes from the trusted store, never from the packet
    or the caller. It must be at or before the contest's cutoff (derived from
    the authoritative schedule version's kickoff and the checkpoint offset),
    and it must not be in the future relative to an explicitly injected
    `as_of_utc`.

3.  **Ordered participants are part of the key.** `(home, away)` is ordered;
    a reversed pair is a different claim about the world, not the same one.

4.  **Strict types.** `True` is not a probability. `1` is not a probability
    either when it arrives as a Boolean. Timestamps must be timezone-aware
    ISO-8601.

Every rejection returns an exact predicate name. `admit()` never raises for
ordinary bad input -- an unprovable forecast is a normal, expected, *recorded*
outcome, not an exception -- so zero eligible forecasts is representable and
is the correct answer when no valid receipt exists.

Nothing in this module can create authority. A receipt minted today can never
repair an old freeze: `commitment_time_utc` is compared against the contest's
cutoff, so a late commitment is late no matter when its bytes were written.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "BAS-FORECAST-ADMISSION-CONTRACT-v35.1"
SHADOW = "UNTRUSTED_SHADOW"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"

_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

#: Checkpoint identifier -> how long before kickoff the commitment must exist.
#: A checkpoint is a *promise about lead time*; without this mapping "frozen"
#: is untethered from the contest it claims to precede.
CHECKPOINT_LEAD: dict[str, timedelta] = {
    "T24": timedelta(hours=24),
    "T24H": timedelta(hours=24),
    "T90M": timedelta(minutes=90),
    "T90": timedelta(minutes=90),
    "T0": timedelta(0),
    "KICKOFF": timedelta(0),
}


class ForecastAdmissionError(ValueError):
    """Raised only for malformed *contract inputs*, never for a rejected row.

    A forecast that fails admission is data, so it is returned as a verdict.
    This exception means the caller handed the contract something it cannot
    even evaluate (e.g. a store that is not a store).
    """


def parse_utc(value: Any) -> datetime | None:
    """A genuine timezone-aware ISO-8601 instant, or None. Never a guess."""

    if not isinstance(value, str) or not _ISO8601_RE.match(value.strip()):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def strict_probability(value: Any) -> float | None:
    """A finite real in [0, 1]. Booleans are rejected before numeric coercion.

    `isinstance(True, int)` is True in Python, so `float(True) == 1.0` sails
    through a naive range check -- that is exactly how `probability_home:
    true` read ELIGIBLE. The Boolean test must come first.
    """

    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        return None
    return number


def ordered_participants(row: Mapping[str, Any]) -> tuple[str, str] | None:
    """Canonical `(home, away)` ids. Order is meaning, not presentation."""

    home = str(row.get("home_canonical_team_id") or "").strip()
    away = str(row.get("away_canonical_team_id") or "").strip()
    if not home or not away or home == away:
        return None
    return (home, away)


def forecast_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Contest/candidate/cohort/checkpoint. Deliberately identical in shape to
    the Cycle #33 key so inventory, scoring and the successor agree on grain."""

    return (
        str(
            row.get("ncaa_contest_id")
            or row.get("canonical_contest_id")
            or row.get("contest_id")
            or ""
        ),
        str(row.get("candidate_id") or row.get("candidate") or ""),
        str(row.get("cohort") or row.get("forecast_cohort") or ""),
        str(row.get("checkpoint") or row.get("checkpoint_id") or ""),
    )


@dataclass(frozen=True)
class TrustedReceipt:
    """One allowlisted commitment. The store is the authority, not the file."""

    receipt_id: str
    issuer: str
    receipt_sha256: str
    commitment_time_utc: datetime
    contest_id: str
    candidate_id: str
    cohort: str
    checkpoint: str
    participants: tuple[str, str]
    schedule_version: str
    model_code_identity: str
    model_data_identity: str

    def key(self) -> tuple[str, str, str, str]:
        return (self.contest_id, self.candidate_id, self.cohort, self.checkpoint)


@dataclass(frozen=True)
class AdmissionVerdict:
    """Why a forecast is or is not admissible. Reasons are exact, not a bool."""

    admitted: bool
    key: tuple[str, str, str, str]
    failed_predicates: tuple[str, ...] = ()
    receipt_id: str | None = None
    issuer: str | None = None
    commitment_time_utc: str | None = None
    cutoff_utc: str | None = None
    participants: tuple[str, str] | None = None
    probability_home: float | None = None
    evidence_bytes_confirmed: bool = False
    contract_version: str = CONTRACT_VERSION
    pit_admitted: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "key": list(self.key),
            "failed_predicates": list(self.failed_predicates),
            "receipt_id": self.receipt_id,
            "issuer": self.issuer,
            "commitment_time_utc": self.commitment_time_utc,
            "cutoff_utc": self.cutoff_utc,
            "participants": list(self.participants) if self.participants else None,
            "probability_home": self.probability_home,
            "evidence_bytes_confirmed": self.evidence_bytes_confirmed,
            "contract_version": self.contract_version,
            "pit_admitted": self.pit_admitted,
        }


class TrustedReceiptStore:
    """An explicit allowlist of commitments, with issuer and commitment time.

    Construct from a declared allowlist artifact (`from_file`) or from rows.
    Absence is a first-class answer: an unknown receipt id resolves to None,
    which the contract reports as `RECEIPT_NOT_IN_TRUSTED_STORE` rather than
    falling back to a filesystem search.
    """

    def __init__(
        self,
        receipts: Iterable[Mapping[str, Any]] = (),
        *,
        trusted_issuers: Sequence[str] = (),
        source_identity: str = "INLINE",
    ) -> None:
        self.trusted_issuers = tuple(trusted_issuers)
        self.source_identity = source_identity
        self._by_id: dict[str, TrustedReceipt] = {}
        self.rejected_rows: list[dict[str, Any]] = []
        for row in receipts:
            parsed = self._parse(row)
            if parsed is None:
                continue
            if parsed.receipt_id in self._by_id:
                # A duplicate receipt id with differing content is a store
                # defect, not a tiebreak: drop both rather than pick one.
                existing = self._by_id[parsed.receipt_id]
                if existing != parsed:
                    del self._by_id[parsed.receipt_id]
                    self.rejected_rows.append(
                        {
                            "receipt_id": parsed.receipt_id,
                            "reason": "DUPLICATE_RECEIPT_ID_CONFLICTING_CONTENT",
                        }
                    )
                continue
            self._by_id[parsed.receipt_id] = parsed

    def _parse(self, row: Mapping[str, Any]) -> TrustedReceipt | None:
        receipt_id = str(row.get("receipt_id") or "").strip()
        issuer = str(row.get("issuer") or "").strip()
        digest = str(row.get("receipt_sha256") or "").strip().casefold()
        commitment = parse_utc(row.get("commitment_time_utc"))
        participants = ordered_participants(row)
        reasons: list[str] = []
        if not receipt_id:
            reasons.append("MISSING_RECEIPT_ID")
        if not issuer:
            reasons.append("MISSING_ISSUER")
        elif self.trusted_issuers and issuer not in self.trusted_issuers:
            reasons.append("ISSUER_NOT_TRUSTED")
        if not _SHA256_RE.match(digest):
            reasons.append("RECEIPT_SHA256_NOT_WELL_FORMED")
        if commitment is None:
            reasons.append("COMMITMENT_TIME_NOT_PARSEABLE")
        if participants is None:
            reasons.append("MISSING_OR_DEGENERATE_ORDERED_PARTICIPANTS")
        for required in ("contest_id", "candidate_id", "cohort", "checkpoint",
                         "schedule_version", "model_code_identity",
                         "model_data_identity"):
            if not str(row.get(required) or "").strip():
                reasons.append("MISSING_" + required.upper())
        if reasons:
            self.rejected_rows.append(
                {"receipt_id": receipt_id or None, "reasons": reasons}
            )
            return None
        assert commitment is not None and participants is not None
        return TrustedReceipt(
            receipt_id=receipt_id,
            issuer=issuer,
            receipt_sha256=digest,
            commitment_time_utc=commitment,
            contest_id=str(row["contest_id"]).strip(),
            candidate_id=str(row["candidate_id"]).strip(),
            cohort=str(row["cohort"]).strip(),
            checkpoint=str(row["checkpoint"]).strip(),
            participants=participants,
            schedule_version=str(row["schedule_version"]).strip(),
            model_code_identity=str(row["model_code_identity"]).strip(),
            model_data_identity=str(row["model_data_identity"]).strip(),
        )

    @classmethod
    def from_file(cls, path: Path) -> "TrustedReceiptStore":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ForecastAdmissionError("trusted receipt allowlist must be an object")
        return cls(
            payload.get("receipts") or [],
            trusted_issuers=tuple(payload.get("trusted_issuers") or ()),
            source_identity=str(path),
        )

    def get(self, receipt_id: str) -> TrustedReceipt | None:
        return self._by_id.get(str(receipt_id or "").strip())

    def __len__(self) -> int:
        return len(self._by_id)

    def identities(self) -> dict[str, Any]:
        return {
            "source_identity": self.source_identity,
            "trusted_issuers": list(self.trusted_issuers),
            "receipt_count": len(self._by_id),
            "rejected_store_rows": len(self.rejected_rows),
        }


def contest_cutoff(
    contest: Mapping[str, Any], checkpoint: str
) -> tuple[datetime | None, str | None]:
    """The instant by which a commitment must already exist.

    An explicit `cutoff_utc` on the contest wins. Otherwise the cutoff is
    derived from the authoritative schedule version's kickoff minus the
    checkpoint's declared lead time. An unknown checkpoint has no derivable
    cutoff -- that is reported, never defaulted to kickoff (which would
    silently admit a commitment made 23 hours after a "T24" promise).
    """

    explicit = parse_utc(contest.get("cutoff_utc"))
    if explicit is not None:
        return explicit, None
    kickoff = parse_utc(contest.get("kickoff_utc"))
    if kickoff is None:
        return None, "MISSING_OR_UNPARSEABLE_KICKOFF"
    lead = CHECKPOINT_LEAD.get(str(checkpoint or "").strip().upper())
    if lead is None:
        return None, "UNKNOWN_CHECKPOINT_NO_DERIVABLE_CUTOFF"
    return kickoff - lead, None


def confirm_receipt_bytes(receipt: TrustedReceipt, payload_path: Path | None) -> bool:
    """Corroborate the allowlisted digest against actual bytes, when present.

    This is deliberately *not* how authority is established -- it only
    confirms that a file the caller already identified matches what the store
    says. A False result means the bytes disagree with the allowlist; a
    missing file means unconfirmed, which the caller records rather than
    treating as proof either way.
    """

    if payload_path is None or not Path(payload_path).is_file():
        return False
    try:
        raw = Path(payload_path).read_bytes()
    except OSError:
        return False
    return hashlib.sha256(raw).hexdigest() == receipt.receipt_sha256


def admit(
    forecast: Mapping[str, Any],
    contest: Mapping[str, Any],
    *,
    store: TrustedReceiptStore,
    as_of_utc: datetime,
    payload_path: Path | None = None,
) -> AdmissionVerdict:
    """The single admission decision used by both inventory and scoring."""

    if not isinstance(store, TrustedReceiptStore):
        raise ForecastAdmissionError("store must be a TrustedReceiptStore")
    if as_of_utc.tzinfo is None:
        raise ForecastAdmissionError("as_of_utc must be timezone-aware")

    key = forecast_key(forecast)
    failed: list[str] = []
    if any(part == "" for part in key):
        failed.append("INCOMPLETE_FORECAST_KEY")

    # The caller may not supply the commitment time. Only the store may.
    declared_receipt = forecast.get("freeze_receipt")
    receipt_id = ""
    if isinstance(declared_receipt, Mapping):
        receipt_id = str(declared_receipt.get("receipt_id") or "").strip()
    elif isinstance(declared_receipt, str):
        receipt_id = declared_receipt.strip()
    if not receipt_id:
        failed.append("MISSING_RECEIPT_ID")

    receipt = store.get(receipt_id) if receipt_id else None
    if receipt_id and receipt is None:
        failed.append("RECEIPT_NOT_IN_TRUSTED_STORE")

    probability = strict_probability(forecast.get("probability_home"))
    if probability is None:
        failed.append("PROBABILITY_NOT_STRICT_FINITE_UNIT_INTERVAL")

    forecast_participants = ordered_participants(forecast)
    if forecast_participants is None:
        failed.append("FORECAST_MISSING_ORDERED_PARTICIPANTS")
    contest_participants = ordered_participants(contest)
    if contest_participants is None:
        failed.append("CONTEST_MISSING_ORDERED_PARTICIPANTS")

    cutoff: datetime | None = None
    if receipt is not None:
        if receipt.key() != key:
            failed.append("RECEIPT_KEY_DOES_NOT_MATCH_FORECAST")
        if (
            contest_participants is not None
            and receipt.participants != contest_participants
        ):
            failed.append("RECEIPT_PARTICIPANTS_DO_NOT_MATCH_CONTEST")
        if (
            forecast_participants is not None
            and receipt.participants != forecast_participants
        ):
            failed.append("RECEIPT_PARTICIPANTS_DO_NOT_MATCH_FORECAST")
        schedule_version = str(contest.get("schedule_version") or "").strip()
        if not schedule_version:
            failed.append("CONTEST_MISSING_SCHEDULE_VERSION")
        elif schedule_version != receipt.schedule_version:
            failed.append("SCHEDULE_VERSION_MISMATCH")

        cutoff, cutoff_reason = contest_cutoff(contest, key[3])
        if cutoff_reason:
            failed.append(cutoff_reason)
        elif cutoff is not None and receipt.commitment_time_utc > cutoff:
            failed.append("COMMITMENT_AFTER_CUTOFF")
        if receipt.commitment_time_utc > as_of_utc:
            failed.append("COMMITMENT_IN_THE_FUTURE")

    if (
        forecast_participants is not None
        and contest_participants is not None
        and forecast_participants != contest_participants
    ):
        failed.append("FORECAST_PARTICIPANTS_DO_NOT_MATCH_CONTEST")

    unique_failed = tuple(dict.fromkeys(failed))
    bytes_confirmed = (
        confirm_receipt_bytes(receipt, payload_path) if receipt is not None else False
    )
    return AdmissionVerdict(
        admitted=not unique_failed and receipt is not None,
        key=key,
        failed_predicates=unique_failed,
        receipt_id=receipt.receipt_id if receipt else (receipt_id or None),
        issuer=receipt.issuer if receipt else None,
        commitment_time_utc=(
            receipt.commitment_time_utc.isoformat() if receipt else None
        ),
        cutoff_utc=cutoff.isoformat() if cutoff else None,
        participants=receipt.participants if receipt else forecast_participants,
        probability_home=probability,
        evidence_bytes_confirmed=bytes_confirmed,
    )


def admit_many(
    forecasts: Sequence[Mapping[str, Any]],
    contests_by_id: Mapping[str, Mapping[str, Any]],
    *,
    store: TrustedReceiptStore,
    as_of_utc: datetime,
) -> dict[str, Any]:
    """Admit a batch, quarantining conflicting duplicates by exact key.

    Two rows sharing a key but disagreeing on probability are a contradiction
    in the evidence. Neither arrival order nor a content sort may pick a
    winner: the whole key is quarantined and reported.
    """

    by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str, str, str]] = []
    verdicts: list[dict[str, Any]] = []
    for row in forecasts:
        key = forecast_key(row)
        contest = contests_by_id.get(key[0]) or {}
        verdict = admit(row, contest, store=store, as_of_utc=as_of_utc)
        verdicts.append(verdict.as_dict())
        if not verdict.admitted:
            continue
        if key not in by_key:
            by_key[key] = []
            order.append(key)
        by_key[key].append(
            {"row": row, "probability_home": verdict.probability_home,
             "verdict": verdict}
        )

    admitted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for key in order:
        group = by_key[key]
        distinct = {round(float(item["probability_home"]), 12) for item in group}
        if len(distinct) > 1:
            quarantined.append(
                {"key": list(key), "distinct_probabilities": sorted(distinct),
                 "reason": "CONFLICTING_DUPLICATE_FORECASTS_FOR_KEY"}
            )
            continue
        admitted.append(
            {"key": list(key), "probability_home": group[0]["probability_home"],
             "verdict": group[0]["verdict"].as_dict(), "duplicate_count": len(group)}
        )
    return {
        "contract_version": CONTRACT_VERSION,
        "as_of_utc": as_of_utc.isoformat(),
        "store": store.identities(),
        "input_row_count": len(forecasts),
        "admitted": admitted,
        "admitted_count": len(admitted),
        "quarantined_conflicting_keys": quarantined,
        "verdicts": verdicts,
        "rejected_count": sum(1 for v in verdicts if not v["admitted"]),
        "zero_admitted_is_valid_evidence_state": True,
        "trust_classification": SHADOW,
        "operator_hold": HOLD,
        "pit_admitted": False,
    }
