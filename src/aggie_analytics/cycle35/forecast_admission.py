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
    issuer, the commitment time, AND the specific committed payload bytes.
    Scanning archive roots for any JSON file whose bytes happen to hash
    correctly is *discovery*; the allowlist plus its bound payload is the
    authority.

2.  **Commitment before cutoff, established independently of the claimant.**
    The commitment time comes from the trusted store, never from the packet
    or the caller. It must be at or before the contest's cutoff (derived from
    the authoritative schedule version's kickoff and the checkpoint offset),
    and it must not be in the future relative to an explicitly injected
    `as_of_utc`.

3.  **Ordered participants are part of the key**, and so is the CONTEST'S OWN
    declared identity -- `(home, away)` is ordered, and a reversed pair is a
    different claim about the world, not the same one. The `contest` mapping
    handed to `admit()` must itself declare the same canonical id the
    forecast claims; nothing about matching participants or schedule version
    alone is treated as proof it is the same game (MF35-01).

4.  **The admitted content is the verified payload's content, not the
    caller's claim.** A receipt binds to a specific payload file at
    authoring time (`payload_path` in the allowlist row). `admit()` resolves
    that path, verifies its bytes hash to `receipt_sha256`, parses it, and
    uses ITS OWN declared probability/contest/participants as the ground
    truth. A forecast row that disagrees with the verified payload is
    rejected outright, and a forecast with no verifiable payload behind its
    receipt is never admitted merely because its metadata matches (MF35-01).

5.  **Strict types.** `True` is not a probability. `1` is not a probability
    either when it arrives as a Boolean. Timestamps must be timezone-aware
    ISO-8601.

6.  **An empty trusted-issuer allowlist trusts nothing.** `trusted_issuers=()`
    is a store with no authority, not a store with unrestricted authority --
    every row is rejected with `NO_TRUSTED_ISSUERS_CONFIGURED` (MF35-02).

7.  **A receipt ID that has ever conflicted stays poisoned for the entire
    load.** Sequence A / conflicting-B / A must not resurrect A: once an ID
    is flagged as carrying inconsistent content, it is permanently excluded
    from that store, regardless of what a later row with the same ID and
    even the same content claims (MF35-02).

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

CONTRACT_VERSION = "BAS-FORECAST-ADMISSION-CONTRACT-v35.2"
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


def contest_own_id(row: Mapping[str, Any]) -> str:
    """The identity a CONTEST mapping declares about itself.

    MF35-01 repair: `admit()` previously never read this. A caller could pass
    a `contest` mapping for an entirely different game -- sharing participants
    and schedule_version by coincidence or construction -- and admission would
    not notice, because nothing compared the contest's own declared id to what
    the forecast/receipt claim. Deliberately the SAME field set `forecast_key`
    reads, so a contest and a forecast describing the same game agree by the
    same rule.
    """

    return str(
        row.get("ncaa_contest_id")
        or row.get("canonical_contest_id")
        or row.get("contest_id")
        or ""
    )


@dataclass(frozen=True)
class TrustedReceipt:
    """One allowlisted commitment. The store is the authority, not the file.

    `payload_path` is REQUIRED and is resolved against the store's
    `evidence_root`. A receipt with no bound payload cannot be confirmed and
    therefore cannot admit anything -- "trusted issuance" means the issuer
    committed specific bytes at authoring time, not merely a row of metadata
    that happens to match whatever is later presented for scoring.
    """

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
    payload_path: str

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
    """An explicit allowlist of commitments, with issuer, commitment time and
    a bound payload for each receipt.

    Construct from a declared allowlist artifact (`from_file`) or from rows.
    Absence is a first-class answer: an unknown receipt id resolves to None,
    which the contract reports as `RECEIPT_NOT_IN_TRUSTED_STORE` rather than
    falling back to a filesystem search.

    MF35-02 repair, two structural changes versus the prior version:

    * An empty `trusted_issuers` sequence trusts NO issuer. The prior
      condition (`if self.trusted_issuers and issuer not in ...`) short-
      circuited to "accept" when the allowlist was empty, which is the
      precise inversion of what an empty allowlist should mean.
    * Once a receipt ID is found carrying conflicting content, that ID is
      permanently poisoned for the life of this store. The prior version
      deleted the conflicting entry from `_by_id` but did not remember the
      ID was poisoned, so a THIRD row repeating the original content simply
      re-inserted it -- sequence A / conflicting-B / A resurrected A.
    """

    def __init__(
        self,
        receipts: Iterable[Mapping[str, Any]] = (),
        *,
        trusted_issuers: Sequence[str] = (),
        source_identity: str = "INLINE",
        evidence_root: Path | None = None,
    ) -> None:
        self.trusted_issuers = tuple(trusted_issuers)
        self.source_identity = source_identity
        self.evidence_root = evidence_root
        self._by_id: dict[str, TrustedReceipt] = {}
        self._poisoned_ids: set[str] = set()
        self.rejected_rows: list[dict[str, Any]] = []
        for row in receipts:
            parsed = self._parse(row)
            if parsed is None:
                continue
            if parsed.receipt_id in self._poisoned_ids:
                # MF35-02: a poisoned ID stays poisoned. A row that happens to
                # repeat the ORIGINAL content is not evidence the conflict
                # never happened -- it is evidence this ID is not reliably
                # single-sourced, which is disqualifying on its own.
                self.rejected_rows.append(
                    {
                        "receipt_id": parsed.receipt_id,
                        "reason": "RECEIPT_ID_PERMANENTLY_QUARANTINED_"
                        "CONFLICTING_CONTENT_SEEN_EARLIER_IN_LOAD",
                    }
                )
                continue
            if parsed.receipt_id in self._by_id:
                # A duplicate receipt id with differing content is a store
                # defect, not a tiebreak: drop both and poison the ID rather
                # than pick one.
                existing = self._by_id[parsed.receipt_id]
                if existing != parsed:
                    del self._by_id[parsed.receipt_id]
                    self._poisoned_ids.add(parsed.receipt_id)
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
        payload_path = str(row.get("payload_path") or "").strip()
        reasons: list[str] = []
        if not receipt_id:
            reasons.append("MISSING_RECEIPT_ID")
        if not issuer:
            reasons.append("MISSING_ISSUER")
        # MF35-02: fail closed on an empty allowlist rather than skipping the
        # issuer check entirely. This fires regardless of whether `issuer`
        # itself looks plausible -- an empty allowlist trusts nobody.
        if not self.trusted_issuers:
            reasons.append("NO_TRUSTED_ISSUERS_CONFIGURED")
        elif issuer and issuer not in self.trusted_issuers:
            reasons.append("ISSUER_NOT_TRUSTED")
        if not _SHA256_RE.match(digest):
            reasons.append("RECEIPT_SHA256_NOT_WELL_FORMED")
        if commitment is None:
            reasons.append("COMMITMENT_TIME_NOT_PARSEABLE")
        if participants is None:
            reasons.append("MISSING_OR_DEGENERATE_ORDERED_PARTICIPANTS")
        if not payload_path:
            # MF35-01: a receipt with no bound payload cannot be confirmed,
            # so it must never enter the store as if it could be trusted.
            reasons.append("MISSING_PAYLOAD_PATH")
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
            payload_path=payload_path,
        )

    @classmethod
    def from_file(cls, path: Path) -> "TrustedReceiptStore":
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ForecastAdmissionError("trusted receipt allowlist must be an object")
        return cls(
            payload.get("receipts") or [],
            trusted_issuers=tuple(payload.get("trusted_issuers") or ()),
            source_identity=str(path),
            evidence_root=path.parent,
        )

    def get(self, receipt_id: str) -> TrustedReceipt | None:
        return self._by_id.get(str(receipt_id or "").strip())

    def __len__(self) -> int:
        return len(self._by_id)

    def resolve_payload_path(self, receipt: TrustedReceipt) -> Path:
        candidate = Path(receipt.payload_path)
        if candidate.is_absolute():
            return candidate
        if self.evidence_root is not None:
            return self.evidence_root / candidate
        return candidate

    def identities(self) -> dict[str, Any]:
        return {
            "source_identity": self.source_identity,
            "trusted_issuers": list(self.trusted_issuers),
            "receipt_count": len(self._by_id),
            "rejected_store_rows": len(self.rejected_rows),
            "poisoned_receipt_ids": sorted(self._poisoned_ids),
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


def verify_and_load_payload(
    receipt: TrustedReceipt, resolved_path: Path
) -> tuple[dict[str, Any] | None, list[str]]:
    """Read the receipt's bound bytes, verify the hash, parse the content.

    Returns `(payload, [])` only when the bytes exist, hash-match the
    receipt's pinned `receipt_sha256`, and parse as a JSON object. Any other
    outcome returns `(None, [exact_reason, ...])` -- never a guess, never a
    partial read treated as confirmation.
    """

    if not resolved_path.is_file():
        return None, ["EVIDENCE_PAYLOAD_FILE_NOT_FOUND"]
    try:
        raw = resolved_path.read_bytes()
    except OSError:
        return None, ["EVIDENCE_PAYLOAD_FILE_UNREADABLE"]
    if hashlib.sha256(raw).hexdigest() != receipt.receipt_sha256:
        return None, ["EVIDENCE_BYTES_DO_NOT_MATCH_RECEIPT_SHA256"]
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, ["EVIDENCE_PAYLOAD_NOT_VALID_JSON"]
    if not isinstance(payload, dict):
        return None, ["EVIDENCE_PAYLOAD_NOT_A_JSON_OBJECT"]
    return payload, []


def confirm_receipt_bytes(receipt: TrustedReceipt, payload_path: Path | None) -> bool:
    """Byte-only confirmation, retained for callers that just want a bool.

    `admit()` itself does not use this narrow form -- it uses
    `verify_and_load_payload`, which also validates and cross-checks the
    parsed content. This wrapper exists for direct diagnostic use only.
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
) -> AdmissionVerdict:
    """The single admission decision used by both inventory and scoring.

    MF35-01 repair: admission now requires (a) the `contest` mapping to
    declare its OWN canonical id and for that id to equal the forecast's
    claimed contest identity, and (b) the receipt's bound payload to be
    read from disk, hash-verified against `receipt_sha256`, and its own
    declared probability/contest/participants to agree with what is being
    scored. `evidence_bytes_confirmed` is no longer informational -- a
    forecast cannot be admitted while it is false.
    """

    if not isinstance(store, TrustedReceiptStore):
        raise ForecastAdmissionError("store must be a TrustedReceiptStore")
    if as_of_utc.tzinfo is None:
        raise ForecastAdmissionError("as_of_utc must be timezone-aware")

    key = forecast_key(forecast)
    failed: list[str] = []
    if any(part == "" for part in key):
        failed.append("INCOMPLETE_FORECAST_KEY")

    # MF35-01: the contest passed in must declare itself as the SAME contest
    # the forecast claims. Matching participants/schedule_version alone is
    # not proof of identity -- those can coincide across different contests
    # (or be supplied for the wrong one by a calling error) while the
    # contest's own id silently differs.
    declared_contest_id = contest_own_id(contest)
    if not declared_contest_id:
        failed.append("CONTEST_MISSING_CANONICAL_ID")
    elif key[0] and declared_contest_id != key[0]:
        failed.append("CONTEST_IDENTITY_DOES_NOT_MATCH_FORECAST_KEY")

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

    forecast_declared_probability = strict_probability(
        forecast.get("probability_home")
    )
    if forecast_declared_probability is None:
        failed.append("PROBABILITY_NOT_STRICT_FINITE_UNIT_INTERVAL")

    forecast_participants = ordered_participants(forecast)
    if forecast_participants is None:
        failed.append("FORECAST_MISSING_ORDERED_PARTICIPANTS")
    contest_participants = ordered_participants(contest)
    if contest_participants is None:
        failed.append("CONTEST_MISSING_ORDERED_PARTICIPANTS")

    cutoff: datetime | None = None
    bytes_confirmed = False
    verified_probability: float | None = None
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

        # MF35-01: read the actual committed bytes. This is the predicate
        # that closes "admit without payload", "change probability under the
        # same receipt" and (together with the contest-identity check above)
        # "wrong contest, same participants" -- none of those can succeed
        # against bytes pinned to a fixed sha256 at allowlist-authoring time.
        resolved_path = store.resolve_payload_path(receipt)
        payload, payload_reasons = verify_and_load_payload(receipt, resolved_path)
        if payload_reasons:
            failed.extend(payload_reasons)
        else:
            bytes_confirmed = True
            payload_key = (
                str(
                    payload.get("contest_id")
                    or payload.get("ncaa_contest_id")
                    or payload.get("canonical_contest_id")
                    or ""
                ),
                str(payload.get("candidate_id") or ""),
                str(payload.get("cohort") or ""),
                str(payload.get("checkpoint") or ""),
            )
            if payload_key != key:
                failed.append("PAYLOAD_KEY_DOES_NOT_MATCH_RECEIPT")
            payload_participants = ordered_participants(payload)
            if payload_participants is None:
                failed.append("PAYLOAD_MISSING_ORDERED_PARTICIPANTS")
            elif payload_participants != receipt.participants:
                failed.append("PAYLOAD_PARTICIPANTS_DO_NOT_MATCH_RECEIPT")
            verified_probability = strict_probability(
                payload.get("probability_home")
            )
            if verified_probability is None:
                failed.append(
                    "PAYLOAD_PROBABILITY_NOT_STRICT_FINITE_UNIT_INTERVAL"
                )
            elif (
                forecast_declared_probability is not None
                and round(forecast_declared_probability, 12)
                != round(verified_probability, 12)
            ):
                # The forecast row being scored claims a probability that
                # disagrees with what the verified, hash-pinned payload
                # actually committed. Neither the caller nor the forecast
                # row itself may override committed content.
                failed.append(
                    "FORECAST_PROBABILITY_DISAGREES_WITH_VERIFIED_PAYLOAD"
                )

    if (
        forecast_participants is not None
        and contest_participants is not None
        and forecast_participants != contest_participants
    ):
        failed.append("FORECAST_PARTICIPANTS_DO_NOT_MATCH_CONTEST")

    unique_failed = tuple(dict.fromkeys(failed))
    admitted = not unique_failed and receipt is not None and bytes_confirmed
    return AdmissionVerdict(
        admitted=admitted,
        key=key,
        failed_predicates=unique_failed,
        receipt_id=receipt.receipt_id if receipt else (receipt_id or None),
        issuer=receipt.issuer if receipt else None,
        commitment_time_utc=(
            receipt.commitment_time_utc.isoformat() if receipt else None
        ),
        cutoff_utc=cutoff.isoformat() if cutoff else None,
        participants=receipt.participants if receipt else forecast_participants,
        # The ADMITTED probability is always the verified payload's own
        # committed value when bytes are confirmed -- never the caller's
        # claim. When bytes are not confirmed, nothing is admitted, so there
        # is no trustworthy probability to report.
        probability_home=verified_probability if bytes_confirmed else None,
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
