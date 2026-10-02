"""Fail-closed admission for scoring a frozen forecast against an official final.

TP36-07. Scoring is the point where a mistake becomes a published number, so
every join condition is checked explicitly and a failure names itself. The
six refusals R36-10 requires are each a separate reason code rather than one
generic rejection, because "the join failed" tells a reviewer nothing about
which invariant broke.

A forecast is eligible only when its bytes existed before the contest's
cutoff and a receipt says so. Recomputing a probability today produces a
retrospective number, never an eligible one, so ``freeze_known_at`` must come
from a receipt and is never defaulted to now.

MF37A02-02 (Cycle #37 - Attempt #3). The v37.2 guard checked that two digests
were *shaped* like SHA-256 and then admitted: invented digests with no receipt
or packet bytes behind them scored, model/input binding happened only when a
caller volunteered ``receipt_model_identity``, an absent final provenance and
the same team on both sides were admitted, and a naive freeze instant raised
``TypeError`` against an aware cutoff. v37.3 composes byte verification into
every scoring entry point: a declared :class:`ReceiptAuthority` must resolve
the forecast's receipt digest to re-hashed receipt bytes that bind the
contest, model, input, orientation, cutoff and freeze instant, and whose
attested payload *is* the frozen packet (its probability is read from those
bytes); the final must carry a receipt of its own that binds the score,
teams, lifecycle and observation time; every instant must be timezone-aware.
Without an authority nothing is admitted, and an admission supported by a
test-only authority says so and never counts as a real eligible forecast.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

# MF36-04. Every join condition here was checked except the one that decides
# whether the numbers are numbers: 1.8, -0.5, NaN, Infinity and True all
# reached ADMITTED_FOR_SCORING and produced a Brier component, and any
# non-empty string counted as a digest. The value and evidence domains live
# in one shared module so the scoring path and the PIT path cannot drift.
from aggie_analytics.cycle37.admission_domains import (  # noqa: E402
    DOMAIN_VERSION,
    valid_digest,
    valid_instant,
    valid_probability,
    valid_score,
)
from aggie_analytics.cycle37.receipt_authority import (  # noqa: E402
    FINAL_RECEIPT,
    FORECAST_RECEIPT,
    ReceiptAuthority,
)

#: Bumped because this guard's admission set genuinely changed: packets a
#: v37.2 receipt records as ADMITTED are refused here unless real bytes and a
#: declared authority stand behind them. A reviewer comparing two receipts
#: must be able to see that from the version alone.
#: v37.4 (MF37A03-02): a final observed at or before the forecast's cutoff is refused, and a supersession is
#: rebuilt from verified bytes instead of trusting the rows it is handed.
SCORING_GUARD_VERSION = "BAS-SCORING-JOIN-GUARD-v37.4"
PREDECESSOR_GUARD_VERSION = "BAS-SCORING-JOIN-GUARD-v37.3"
SUPERSESSION_VERSION = "BAS-SCORING-SUPERSESSION-v37.4"
#: R37-10 AC04. The declared tie and correction rules this guard applies.
SCORING_POLICY = {
    "version": "BAS-SCORING-POLICY-v37.1",
    "tie": "a terminal tie is outcome 0.5 for the designated home side and flagged tie=true",
    "correction": ("a scored row is immutable; a corrected final is admitted as a new row that supersedes the "
                   "original by reference (supersede_after_correction), and a final corrected after the observation "
                   "a claim used is refused rather than silently rescored"),
    "non_final": "pregame, in-progress, postponed and cancelled contests are never scored",
}

ADMITTED = "ADMITTED_FOR_SCORING"
INVALID_PROBABILITY = "REFUSED_PROBABILITY_IS_NOT_A_PROBABILITY"
INVALID_SCORE = "REFUSED_SCORE_IS_NOT_A_SCORE"
INVALID_DIGEST = "REFUSED_DIGEST_IS_NOT_A_SHA256"
INVALID_INSTANT = "REFUSED_INSTANT_IS_NOT_A_USABLE_INSTANT"
WRONG_CONTEST = "REFUSED_FORECAST_NAMES_A_DIFFERENT_CONTEST"
LATE_FREEZE = "REFUSED_FREEZE_IS_NOT_BEFORE_THE_CUTOFF"
NO_RECEIPT = "REFUSED_NO_DURABLE_FREEZE_RECEIPT"
SCORE_MISMATCH = "REFUSED_SUPPLIED_SCORE_DOES_NOT_MATCH_THE_OFFICIAL_FINAL"
FUTURE_CORRECTION = "REFUSED_FINAL_WAS_CORRECTED_AFTER_SCORING_WAS_CLAIMED"
ORIENTATION_INVERTED = "REFUSED_NEUTRAL_ORIENTATION_INVERTED"
DUPLICATE_ORIENTED_ROW = "REFUSED_DUPLICATE_ORIENTED_ROW_FOR_ONE_CONTEST"
NOT_FINAL = "REFUSED_OBSERVATION_IS_NOT_A_TERMINAL_FINAL"
MODEL_MISMATCH = "REFUSED_MODEL_OR_INPUT_IDENTITY_DOES_NOT_MATCH_THE_RECEIPT"
#: MF37A02-02 additions.
PARTICIPANTS_NOT_DISTINCT = "REFUSED_PARTICIPANTS_ARE_NOT_TWO_DISTINCT_TEAMS"
NO_AUTHORITY = "REFUSED_NO_TRUSTED_RECEIPT_AUTHORITY"
RECEIPT_NOT_VERIFIED = "REFUSED_RECEIPT_BYTES_NOT_VERIFIED"
PACKET_NOT_BOUND = "REFUSED_PACKET_BYTES_NOT_BOUND_TO_THE_RECEIPT"
RECEIPT_BINDING_MISMATCH = "REFUSED_RECEIPT_DOES_NOT_BIND_THIS_FORECAST"
FINAL_NO_PROVENANCE = "REFUSED_FINAL_HAS_NO_VERIFIED_SOURCE_PROVENANCE"
FINAL_PROVENANCE_MISMATCH = "REFUSED_FINAL_DOES_NOT_MATCH_ITS_SOURCE_RECEIPT"
#: MF37A03-02 addition: a contest cannot be final before the decision cutoff its forecast was frozen against.
FINAL_BEFORE_CUTOFF = "REFUSED_FINAL_OBSERVED_BEFORE_THE_FORECAST_CUTOFF"

#: The frozen packet's own fields that must agree with the forecast being scored.
PACKET_FIELDS = ("contest_id", "model_identity", "input_identity", "designated_home_team",
                 "designated_away_team", "home_win_probability")


@dataclass(frozen=True)
class FrozenForecast:
    """A forecast packet plus the receipt that makes it eligible."""

    contest_id: str
    model_identity: str
    input_identity: str
    designated_home_team: str
    designated_away_team: str
    home_win_probability: float
    freeze_known_at: datetime | None
    cutoff_utc: datetime | None
    receipt_digest: str | None
    packet_bytes_digest: str | None
    neutral_site: bool | None = None
    supplied_home_points: int | None = None
    supplied_away_points: int | None = None


@dataclass(frozen=True)
class OfficialFinal:
    """One terminal official result as a source states it."""

    contest_id: str
    home_team: str
    away_team: str
    home_points: int
    away_points: int
    lifecycle: str
    observed_at: datetime | None
    corrected_at: datetime | None = None
    neutral_site: bool | None = None
    #: MF37A02-02: the digest of the final's own source receipt. A final with no verified source is a claim
    #: about a score, not an official observation of one.
    source_receipt_digest: str | None = None


def _instant_text(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _same_instant(receipt_value: Any, value: datetime | None) -> bool:
    if value is None:
        return receipt_value is None
    verdict = valid_instant(receipt_value, label="receipt instant") if receipt_value is not None else None
    return bool(verdict) and verdict.value == value


def _verify_forecast_evidence(forecast: FrozenForecast, authority: ReceiptAuthority) -> tuple[str, str, Any]:
    """(state, detail, verified receipt) for the forecast's receipt and the packet bytes it attests."""

    verdict = authority.resolve(forecast.receipt_digest, expected_kind=FORECAST_RECEIPT)
    if not verdict:
        return RECEIPT_NOT_VERIFIED, f"{verdict.code}: {verdict.detail}", None
    receipt = verdict.value
    content = receipt.content
    if receipt.payload_digest != forecast.packet_bytes_digest:
        return PACKET_NOT_BOUND, (f"the receipt attests packet {receipt.payload_digest[:16]}..., the forecast names "
                                  f"{str(forecast.packet_bytes_digest)[:16]}..."), None
    for field_name in ("model_identity", "input_identity"):
        if content.get(field_name) != getattr(forecast, field_name):
            return MODEL_MISMATCH, (f"receipt binds {field_name} {content.get(field_name)!r}, packet claims "
                                    f"{getattr(forecast, field_name)!r}"), None
    mismatched = [name for name in ("contest_id", "designated_home_team", "designated_away_team")
                  if content.get(name) != getattr(forecast, name)]
    if "neutral_site" in content and content.get("neutral_site") != forecast.neutral_site:
        mismatched.append("neutral_site")
    if not _same_instant(content.get("cutoff_utc"), forecast.cutoff_utc):
        mismatched.append("cutoff_utc")
    if not _same_instant(content.get("freeze_known_at"), forecast.freeze_known_at):
        mismatched.append("freeze_known_at")
    if mismatched:
        return RECEIPT_BINDING_MISMATCH, f"the verified receipt does not bind this forecast's {mismatched}", None
    try:
        packet = json.loads(authority.payload(receipt).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return PACKET_NOT_BOUND, "the attested packet bytes are not a JSON document", None
    if not isinstance(packet, dict):
        return PACKET_NOT_BOUND, "the attested packet is not a JSON object", None
    disagreeing = []
    for name in PACKET_FIELDS:
        stated = packet.get(name)
        claimed = getattr(forecast, name)
        if name == "home_win_probability":
            same = (isinstance(stated, (int, float)) and not isinstance(stated, bool)
                    and math.isfinite(float(stated)) and float(stated) == float(claimed))
        else:
            same = stated == claimed
        if not same:
            disagreeing.append(name)
    if disagreeing:
        return PACKET_NOT_BOUND, f"the frozen packet bytes disagree with the forecast on {disagreeing}", None
    return ADMITTED, "forecast receipt and packet bytes verified", receipt


def _verify_final_evidence(final: OfficialFinal, authority: ReceiptAuthority) -> tuple[str, str, Any]:
    if not final.source_receipt_digest:
        return FINAL_NO_PROVENANCE, ("the final carries no source receipt; a score without a verified official "
                                     "source is not an official final"), None
    verdict = authority.resolve(final.source_receipt_digest, expected_kind=FINAL_RECEIPT)
    if not verdict:
        return FINAL_NO_PROVENANCE, f"{verdict.code}: {verdict.detail}", None
    content = verdict.value.content
    mismatched = [name for name in ("contest_id", "home_team", "away_team", "home_points", "away_points",
                                    "lifecycle") if content.get(name) != getattr(final, name)]
    if "neutral_site" in content and content.get("neutral_site") != final.neutral_site:
        mismatched.append("neutral_site")
    if not _same_instant(content.get("observed_at"), final.observed_at) or final.observed_at is None:
        mismatched.append("observed_at")
    if not _same_instant(content.get("corrected_at"), final.corrected_at):
        mismatched.append("corrected_at")
    if mismatched:
        return FINAL_PROVENANCE_MISMATCH, f"the final disagrees with its verified source receipt on {mismatched}", None
    return ADMITTED, "final source receipt verified", verdict.value


def admit_for_scoring(
    forecast: FrozenForecast,
    final: OfficialFinal,
    *,
    already_scored_contests: frozenset[str] = frozenset(),
    receipt_model_identity: str | None = None,
    receipt_input_identity: str | None = None,
    authority: ReceiptAuthority | None = None,
) -> dict[str, Any]:
    """Decide whether one forecast may be scored against one final.

    Every refusal names the exact invariant that failed. The order is
    deliberate: values first, then identity, then eligibility in time, then
    the evidence behind the claims, because a score comparison on the wrong
    contest is meaningless and a well-formed digest is not yet evidence.
    """

    def refuse(state: str, detail: str) -> dict[str, Any]:
        return {
            "guard_version": SCORING_GUARD_VERSION,
            "state": state,
            "admitted": False,
            "contest_id": forecast.contest_id,
            "detail": detail,
        }

    # Value domains come first. Identity checks on nonsense values still
    # produce a verdict, and that verdict was ADMITTED with a Brier
    # component computed from Infinity. A probability that is not a
    # probability is not a late-breaking detail of an otherwise valid join.
    probability = valid_probability(
        forecast.home_win_probability, label="home_win_probability"
    )
    if not probability:
        return refuse(INVALID_PROBABILITY, f"{probability.code}: {probability.detail}")
    for label, value in (
        ("final home_points", final.home_points),
        ("final away_points", final.away_points),
    ):
        score = valid_score(value, label=label)
        if not score:
            return refuse(INVALID_SCORE, f"{score.code}: {score.detail}")
    for label, value in (
        ("packet supplied_home_points", forecast.supplied_home_points),
        ("packet supplied_away_points", forecast.supplied_away_points),
    ):
        if value is None:
            continue
        score = valid_score(value, label=label)
        if not score:
            return refuse(INVALID_SCORE, f"{score.code}: {score.detail}")

    # MF37A02-02: a contest is two different teams. The same identifier on both sides was admitted.
    for label, home, away in (("forecast", forecast.designated_home_team, forecast.designated_away_team),
                              ("final", final.home_team, final.away_team)):
        if not home or not away or home == away:
            return refuse(PARTICIPANTS_NOT_DISTINCT,
                          f"the {label} names {home!r} and {away!r}; a scored contest needs two distinct teams")

    if forecast.contest_id != final.contest_id:
        return refuse(
            WRONG_CONTEST,
            f"forecast names {forecast.contest_id!r}, final names {final.contest_id!r}",
        )
    if final.lifecycle != "FINAL":
        return refuse(
            NOT_FINAL,
            f"observation lifecycle is {final.lifecycle!r}; only a terminal FINAL scores",
        )
    if forecast.contest_id in already_scored_contests:
        return refuse(
            DUPLICATE_ORIENTED_ROW,
            "this contest already has an oriented scored row; a second one "
            "would double-count the same result",
        )
    if not forecast.receipt_digest or not forecast.packet_bytes_digest:
        return refuse(
            NO_RECEIPT,
            "eligibility needs durable packet bytes and a receipt naming them; "
            "a recomputed probability is retrospective, not frozen",
        )
    # Truthiness was the whole of this check, so "yes" was a receipt digest.
    for label, value in (
        ("receipt_digest", forecast.receipt_digest),
        ("packet_bytes_digest", forecast.packet_bytes_digest),
    ):
        digest = valid_digest(value, label=label)
        if not digest:
            return refuse(INVALID_DIGEST, f"{digest.code}: {digest.detail}")
    if receipt_model_identity is not None and (
        receipt_model_identity != forecast.model_identity
    ):
        return refuse(
            MODEL_MISMATCH,
            f"receipt binds model {receipt_model_identity!r}, packet claims "
            f"{forecast.model_identity!r}",
        )
    if receipt_input_identity is not None and (
        receipt_input_identity != forecast.input_identity
    ):
        return refuse(
            MODEL_MISMATCH,
            f"receipt binds inputs {receipt_input_identity!r}, packet claims "
            f"{forecast.input_identity!r}",
        )
    if forecast.freeze_known_at is None or forecast.cutoff_utc is None:
        return refuse(
            LATE_FREEZE,
            "a missing freeze instant or cutoff cannot be treated as on time",
        )
    # MF37A02-02: a naive instant is not a time on the contest's clock, and comparing one with an aware
    # instant raised TypeError. Every instant this guard compares must be aware.
    for label, value in (("freeze_known_at", forecast.freeze_known_at), ("cutoff_utc", forecast.cutoff_utc),
                         ("final observed_at", final.observed_at), ("final corrected_at", final.corrected_at)):
        if value is None and label.startswith("final"):
            continue
        instant = valid_instant(value, label=label)
        if not instant:
            return refuse(INVALID_INSTANT, f"{instant.code}: {instant.detail}")
    if forecast.freeze_known_at >= forecast.cutoff_utc:
        return refuse(
            LATE_FREEZE,
            f"freeze {forecast.freeze_known_at.isoformat()} is not strictly "
            f"before cutoff {forecast.cutoff_utc.isoformat()}",
        )
    if (forecast.designated_home_team, forecast.designated_away_team) != (
        final.home_team,
        final.away_team,
    ):
        return refuse(
            ORIENTATION_INVERTED,
            "the forecast's designated home/away sides do not match the "
            "final's; a neutral-site contest still has a designated "
            "orientation and inverting it inverts the probability's meaning",
        )
    if forecast.supplied_home_points is not None or (
        forecast.supplied_away_points is not None
    ):
        if (
            forecast.supplied_home_points != final.home_points
            or forecast.supplied_away_points != final.away_points
        ):
            return refuse(
                SCORE_MISMATCH,
                f"packet supplied {forecast.supplied_home_points}-"
                f"{forecast.supplied_away_points}, official final is "
                f"{final.home_points}-{final.away_points}",
            )
    if final.corrected_at is not None and final.observed_at is not None and (
        final.corrected_at > final.observed_at
    ):
        return refuse(
            FUTURE_CORRECTION,
            f"the final was corrected at {final.corrected_at.isoformat()}, after "
            f"the observation at {final.observed_at.isoformat()}; the corrected "
            "result must be re-admitted rather than silently scored",
        )
    # MF37A03-02: a terminal result observed at or before the decision cutoff contradicts the forecast's own
    # clock. An absent observation time is left to the provenance check below, which refuses it by name.
    if final.observed_at is not None and final.observed_at <= forecast.cutoff_utc:
        return refuse(
            FINAL_BEFORE_CUTOFF,
            f"the final was observed at {final.observed_at.isoformat()}, not after the forecast's cutoff "
            f"{forecast.cutoff_utc.isoformat()}; a contest is not final before its decision time",
        )
    if forecast.neutral_site is not None and final.neutral_site is not None and (
        bool(forecast.neutral_site) != bool(final.neutral_site)
    ):
        return refuse(
            ORIENTATION_INVERTED,
            "forecast and final disagree about neutral-site status, so the "
            "orientation the probability was produced under is unclear",
        )

    # MF37A02-02: every claim above is now checked against verified bytes. A digest-shaped string is not
    # evidence; without a declared authority there is nothing to verify it against, so nothing scores.
    if authority is None:
        return refuse(
            NO_AUTHORITY,
            "no receipt authority was supplied, so the receipt and packet digests cannot be resolved to bytes; "
            "a well-formed digest with nothing behind it is not a durable freeze receipt",
        )
    state, detail, forecast_receipt = _verify_forecast_evidence(forecast, authority)
    if state != ADMITTED:
        return refuse(state, detail)
    state, detail, final_receipt = _verify_final_evidence(final, authority)
    if state != ADMITTED:
        return refuse(state, detail)

    home_won = final.home_points > final.away_points
    tie = final.home_points == final.away_points
    # R37-10 AC04: a tie is outcome 0.5 under the declared policy, not a
    # home loss. The v37.1 row scored a tie as 0 for the home side.
    outcome = 0.5 if tie else float(home_won)
    return {
        "guard_version": SCORING_GUARD_VERSION,
        "domain_version": DOMAIN_VERSION,
        "scoring_policy": SCORING_POLICY["version"],
        "state": ADMITTED,
        "admitted": True,
        "contest_id": forecast.contest_id,
        "home_win_probability": probability.value,
        "home_won": home_won,
        "tie": tie,
        "outcome_for_home": outcome,
        "brier_component": (probability.value - outcome) ** 2,
        "final_home_points": final.home_points,
        "final_away_points": final.away_points,
        "evidence": {
            "authority": authority.describe(),
            "forecast_receipt": forecast_receipt.evidence(),
            "final_receipt": final_receipt.evidence(),
        },
        "authority_class": authority.authority_class,
        "counts_as_real_eligible_forecast": authority.counts_as_real_evidence,
        "detail": (
            "The probability and both scores are in their declared domains, "
            "the packet's bytes are receipt-bound before the cutoff and were "
            "re-hashed by the authority, the contest, model, input and "
            "orientation match those bytes, and the official final is "
            "terminal and bound to its own verified source receipt."
        ),
    }


def _receipt_instant(value: Any) -> datetime | None:
    """A receipt's instant, parsed; anything unusable becomes None so the admission path refuses it by name."""

    if value is None:
        return None
    verdict = valid_instant(value, label="receipt instant")
    return verdict.value if verdict else None


def _rebuild_admitted_row(row: Any, authority: ReceiptAuthority, label: str) -> tuple[dict[str, Any], FrozenForecast,
                                                                                      OfficialFinal]:
    """Re-derive a scored row from nothing but the receipts it names, through the full admission path.

    MF37A03-02. The supplied mapping contributes two digests and nothing else. The forecast is rebuilt from
    its verified freeze receipt and the packet bytes that receipt attests; the final from its verified source
    receipt; both then pass :func:`admit_for_scoring` again, so every value domain, identity, orientation,
    chronology and provenance rule applies to the rebuilt row exactly as it did when the row was first scored.
    """

    if not isinstance(row, Mapping):
        raise ValueError(f"the {label} row is not a mapping")
    evidence = row.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError(f"the {label} row carries no admission evidence to rebuild it from")
    forecast_digest = (evidence.get("forecast_receipt") or {}).get("receipt_digest") \
        if isinstance(evidence.get("forecast_receipt"), Mapping) else None
    final_digest = (evidence.get("final_receipt") or {}).get("receipt_digest") \
        if isinstance(evidence.get("final_receipt"), Mapping) else None
    forecast_verdict = authority.resolve(forecast_digest, expected_kind=FORECAST_RECEIPT)
    if not forecast_verdict:
        raise ValueError(f"the {label} row's forecast receipt does not verify: {forecast_verdict.code}")
    final_verdict = authority.resolve(final_digest, expected_kind=FINAL_RECEIPT)
    if not final_verdict:
        raise ValueError(f"the {label} row's final receipt does not verify: {final_verdict.code}")
    try:
        packet = json.loads(authority.payload(forecast_verdict.value).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"the {label} row's frozen packet bytes are not a JSON document") from error
    if not isinstance(packet, dict):
        raise ValueError(f"the {label} row's frozen packet is not a JSON object")
    fc = forecast_verdict.value.content
    forecast = FrozenForecast(
        contest_id=fc.get("contest_id"), model_identity=fc.get("model_identity"),
        input_identity=fc.get("input_identity"), designated_home_team=fc.get("designated_home_team"),
        designated_away_team=fc.get("designated_away_team"), home_win_probability=packet.get("home_win_probability"),
        freeze_known_at=_receipt_instant(fc.get("freeze_known_at")), cutoff_utc=_receipt_instant(fc.get("cutoff_utc")),
        receipt_digest=forecast_digest, packet_bytes_digest=forecast_verdict.value.payload_digest,
        neutral_site=fc.get("neutral_site"), supplied_home_points=packet.get("supplied_home_points"),
        supplied_away_points=packet.get("supplied_away_points"))
    zc = final_verdict.value.content
    final = OfficialFinal(
        contest_id=zc.get("contest_id"), home_team=zc.get("home_team"), away_team=zc.get("away_team"),
        home_points=zc.get("home_points"), away_points=zc.get("away_points"), lifecycle=zc.get("lifecycle"),
        observed_at=_receipt_instant(zc.get("observed_at")), corrected_at=_receipt_instant(zc.get("corrected_at")),
        neutral_site=zc.get("neutral_site"), source_receipt_digest=final_digest)
    rebuilt = admit_for_scoring(forecast, final, authority=authority)
    if not rebuilt.get("admitted"):
        raise ValueError(f"the {label} row's own receipts do not admit it for scoring: {rebuilt['state']} "
                         f"({rebuilt.get('detail')})")
    missing = object()
    differing = sorted(key for key in set(row) | set(rebuilt) if row.get(key, missing) != rebuilt.get(key, missing))
    if differing:
        raise ValueError(f"the {label} row states {differing} differently from what its verified receipts admit; "
                         f"a scored row is re-derived from bytes, never taken as supplied")
    return rebuilt, forecast, final


def _row_digest(row: Mapping[str, Any]) -> str:
    import hashlib  # noqa: PLC0415 - only the supersession needs it

    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def supersede_after_correction(original: Mapping[str, Any], corrected: Mapping[str, Any],
                               *, correction_known_at: datetime,
                               authority: ReceiptAuthority | None = None) -> dict[str, Any]:
    """The row a corrected final produces: new, referencing the scored row it supersedes.

    A scored row is immutable (``SCORING_POLICY['correction']``). The
    corrected final is admitted through :func:`admit_for_scoring` like any
    other; this binds the two so the history shows both, and refuses a
    "correction" that states the same final or belongs to another contest.

    MF37A03-02 (Cycle #37 - Attempt #4). v37.3 re-resolved each row's two
    receipts and compared only the final score, then returned the corrected
    mapping as supplied: a contest id, probability, Brier component and
    authority class edited in both rows came back intact, and a correction
    "known" before the forecast was frozen was accepted. Now:

    * each row is rebuilt from the receipts it names through the whole
      admission path (:func:`_rebuild_admitted_row`) and every field it
      states must equal the rebuilt row -- no field is taken as supplied;
    * both rows must re-score the same frozen forecast receipt against two
      different final receipts of the same contest and orientation;
    * chronology: the corrected final may not be observed before the final
      it corrects, and the correction may not be known before the corrected
      final was observed, before the original final, nor before the
      forecast's freeze or cutoff;
    * the successor is constructed only from the rebuilt corrected row, and
      references the unchanged predecessor by the digest of its rebuilt
      content. Test-only authority stays test-only.
    """

    if authority is None:
        raise ValueError("a supersession needs the receipt authority that verified both rows")
    known = valid_instant(correction_known_at, label="correction_known_at")
    if not known:
        raise ValueError("the correction needs a usable, timezone-aware instant it became known")
    before_row, before_forecast, before_final = _rebuild_admitted_row(original, authority, "original")
    after_row, after_forecast, after_final = _rebuild_admitted_row(corrected, authority, "corrected")
    if before_row["contest_id"] != after_row["contest_id"]:
        raise ValueError("a correction supersedes a row of the same contest only")
    if before_forecast.receipt_digest != after_forecast.receipt_digest:
        raise ValueError("a correction re-scores the same frozen forecast; the two rows name different forecast "
                         "receipts")
    if before_final.source_receipt_digest == after_final.source_receipt_digest:
        raise ValueError("the corrected row names the same final receipt; there is nothing to supersede")
    before = (before_row["final_home_points"], before_row["final_away_points"])
    after = (after_row["final_home_points"], after_row["final_away_points"])
    if before == after:
        raise ValueError("the corrected final states the same score; there is nothing to supersede")
    if (before_final.home_team, before_final.away_team) != (after_final.home_team, after_final.away_team):
        raise ValueError("the corrected final names a different orientation of the contest")
    if after_final.observed_at < before_final.observed_at:
        raise ValueError(f"the corrected final was observed at {after_final.observed_at.isoformat()}, before the "
                         f"final it corrects ({before_final.observed_at.isoformat()})")
    floor = max(after_final.observed_at, before_final.observed_at, after_forecast.cutoff_utc,
                after_forecast.freeze_known_at)
    if known.value < floor:
        raise ValueError(f"the correction is stated as known at {known.value.isoformat()}, before "
                         f"{floor.isoformat()} (the corrected final's observation, the original final, or the "
                         f"forecast's freeze and cutoff); a correction cannot be known before what it corrects")
    successor = dict(after_row)
    successor.update({
        "supersession_version": SUPERSESSION_VERSION,
        "supersedes": {"contest_id": before_row["contest_id"], "final": list(before),
                       "brier_component": before_row["brier_component"],
                       "row_sha256": _row_digest(before_row),
                       "final_receipt_digest": before_final.source_receipt_digest,
                       "forecast_receipt_digest": before_forecast.receipt_digest},
        "correction_known_at": known.value.isoformat(),
        "original_row_kept": True,
    })
    return successor


def packet_eligibility(packet: Mapping[str, Any], *, authority: ReceiptAuthority | None = None) -> dict[str, Any]:
    """Whether a declared frozen packet is eligible at all, before any join.

    ``durable_bytes`` is not the same as "a file exists now": the packet must
    carry a digest of the bytes AND a receipt that binds those bytes to a
    time. Zero eligible packets across the whole inventory is an honest
    result and is never repaired by backfilling a checkpoint.

    MF37A02-02: the receipt and packet digests must also resolve, through a
    declared authority, to re-hashed bytes that bind this packet's contest,
    model, input, freeze instant and cutoff.
    """

    missing = [
        field
        for field in (
            "contest_id",
            "model_identity",
            "input_identity",
            "packet_bytes_digest",
            "receipt_digest",
            "freeze_known_at",
            "cutoff_utc",
        )
        if not packet.get(field)
    ]
    if missing:
        return {
            "guard_version": SCORING_GUARD_VERSION,
            "domain_version": DOMAIN_VERSION,
            "eligible": False,
            "state": "INELIGIBLE_MISSING_BINDING",
            "missing_fields": missing,
            "detail": (
                "Eligibility requires contest, model, input, packet bytes, a "
                "receipt and both instants. A missing field is never filled in."
            ),
        }

    # MF36-04: presence was the whole check, so "yes" was a digest and
    # "soon" was an instant. Each field is now checked against its kind.
    domain_failures: list[dict[str, Any]] = []
    for field in ("packet_bytes_digest", "receipt_digest"):
        verdict = valid_digest(packet.get(field), label=field)
        if not verdict:
            domain_failures.append({"field": field, **verdict.as_dict()})
    for field in ("freeze_known_at", "cutoff_utc"):
        verdict = valid_instant(packet.get(field), label=field)
        if not verdict:
            domain_failures.append({"field": field, **verdict.as_dict()})
    if domain_failures:
        return {
            "guard_version": SCORING_GUARD_VERSION,
            "domain_version": DOMAIN_VERSION,
            "eligible": False,
            "state": "INELIGIBLE_FIELD_OUT_OF_DOMAIN",
            "missing_fields": [],
            "domain_failures": domain_failures,
            "detail": (
                "Every required field was present and at least one was not of "
                "its declared kind. A non-empty value is not a binding."
            ),
        }

    freeze = valid_instant(packet.get("freeze_known_at"), label="freeze_known_at").value
    cutoff = valid_instant(packet.get("cutoff_utc"), label="cutoff_utc").value
    if freeze >= cutoff:
        return {
            "guard_version": SCORING_GUARD_VERSION,
            "domain_version": DOMAIN_VERSION,
            "eligible": False,
            "state": "INELIGIBLE_FREEZE_IS_NOT_BEFORE_THE_CUTOFF",
            "missing_fields": [],
            "detail": (
                f"freeze {freeze.isoformat()} is not strictly before cutoff "
                f"{cutoff.isoformat()}; a packet frozen at or after the cutoff "
                f"is retrospective"
            ),
        }
    if authority is None:
        return {
            "guard_version": SCORING_GUARD_VERSION,
            "domain_version": DOMAIN_VERSION,
            "eligible": False,
            "state": "INELIGIBLE_NO_TRUSTED_RECEIPT_AUTHORITY",
            "missing_fields": [],
            "detail": ("Every binding is present and well formed, but no receipt authority was supplied to resolve "
                       "the digests to bytes; a digest is not evidence that the bytes exist."),
        }
    verdict = authority.resolve(packet.get("receipt_digest"), expected_kind=FORECAST_RECEIPT)
    if not verdict:
        return {"guard_version": SCORING_GUARD_VERSION, "domain_version": DOMAIN_VERSION, "eligible": False,
                "state": "INELIGIBLE_RECEIPT_BYTES_NOT_VERIFIED", "missing_fields": [],
                "detail": f"{verdict.code}: {verdict.detail}"}
    receipt = verdict.value
    mismatched = [name for name in ("contest_id", "model_identity", "input_identity")
                  if receipt.content.get(name) != packet.get(name)]
    if receipt.payload_digest != packet.get("packet_bytes_digest"):
        mismatched.append("packet_bytes_digest")
    if not _same_instant(receipt.content.get("freeze_known_at"), freeze):
        mismatched.append("freeze_known_at")
    if not _same_instant(receipt.content.get("cutoff_utc"), cutoff):
        mismatched.append("cutoff_utc")
    if mismatched:
        return {"guard_version": SCORING_GUARD_VERSION, "domain_version": DOMAIN_VERSION, "eligible": False,
                "state": "INELIGIBLE_RECEIPT_DOES_NOT_BIND_THIS_PACKET", "missing_fields": [],
                "detail": f"the verified receipt does not bind this packet's {mismatched}"}
    return {
        "guard_version": SCORING_GUARD_VERSION,
        "domain_version": DOMAIN_VERSION,
        "eligible": True,
        "state": "ELIGIBLE_SUBJECT_TO_THE_JOIN_GUARDS",
        "missing_fields": [],
        "evidence": receipt.evidence(),
        "authority_class": authority.authority_class,
        "counts_as_real_eligible_forecast": authority.counts_as_real_evidence,
    }
