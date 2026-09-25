r"""Typed value and evidence domains for every admission gate.

MF36-03 and MF36-04 repair. Both findings are the same shape: a gate that
checked *presence* where it needed to check *kind*.

* ``classify_pit`` did ``if receipt:``, so ``{"unrelated": True}`` was a
  point-in-time publication receipt. ``admit_to_pit_consumer`` then read
  ``admissible_to_a_pit_consumer`` straight out of whatever mapping it was
  handed, so a caller could simply state the conclusion.
* ``admit_for_scoring`` checked contest identity, freeze order, orientation
  and duplication -- carefully -- and never checked that the probability was
  a probability. ``1.8``, ``-0.5``, ``NaN``, ``Infinity`` and ``True`` all
  reached ``ADMITTED_FOR_SCORING`` and produced a Brier component.
  ``packet_eligibility`` accepted any non-empty value in each required
  field, so ``"yes"`` was a digest.

The rules here are deliberately boring and total. Each returns a verdict
naming the invariant rather than raising, so a gate can report which domain
failed instead of collapsing everything into one rejection.

``bool`` is rejected everywhere a number is required. In Python ``True`` is
an ``int`` and ``isinstance(True, (int, float))`` is true, which is exactly
how a boolean became a probability of 1.0 and a score of 1.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Mapping

__all__ = [
    "DOMAIN_VERSION",
    "DomainVerdict",
    "attested_prior_ids",
    "valid_digest",
    "valid_instant",
    "valid_probability",
    "valid_publication_receipt",
    "valid_score",
]

DOMAIN_VERSION = "BAS-ADMISSION-DOMAIN-v37.1"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class DomainVerdict:
    """A value's admissibility plus the reason, never a bare boolean."""

    __slots__ = ("ok", "code", "detail", "value")

    def __init__(self, ok: bool, code: str, detail: str, value: Any = None) -> None:
        self.ok = ok
        self.code = code
        self.detail = detail
        self.value = value

    def __bool__(self) -> bool:
        return self.ok

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain_version": DOMAIN_VERSION,
            "ok": self.ok,
            "code": self.code,
            "detail": self.detail,
        }

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"DomainVerdict(ok={self.ok!r}, code={self.code!r})"


def valid_probability(value: Any, *, label: str = "probability") -> DomainVerdict:
    """A real number in ``[0, 1]``. Not a bool, not NaN, not infinite."""

    if isinstance(value, bool):
        return DomainVerdict(
            False,
            "REFUSED_PROBABILITY_IS_BOOLEAN",
            f"{label} is a boolean; True would silently score as 1.0",
        )
    if not isinstance(value, (int, float)):
        return DomainVerdict(
            False,
            "REFUSED_PROBABILITY_IS_NOT_A_NUMBER",
            f"{label} is {type(value).__name__}, not a real number",
        )
    number = float(value)
    if math.isnan(number):
        return DomainVerdict(
            False, "REFUSED_PROBABILITY_IS_NAN", f"{label} is NaN"
        )
    if math.isinf(number):
        return DomainVerdict(
            False, "REFUSED_PROBABILITY_IS_INFINITE", f"{label} is infinite"
        )
    if not 0.0 <= number <= 1.0:
        return DomainVerdict(
            False,
            "REFUSED_PROBABILITY_OUT_OF_RANGE",
            f"{label} is {number}, outside [0, 1]",
        )
    return DomainVerdict(True, "PROBABILITY_IN_DOMAIN", f"{label} is in [0, 1]", number)


def valid_score(value: Any, *, label: str = "score") -> DomainVerdict:
    """A non-negative whole number of points. Not a bool, not a float."""

    if isinstance(value, bool):
        return DomainVerdict(
            False,
            "REFUSED_SCORE_IS_BOOLEAN",
            f"{label} is a boolean; True would silently score as 1 point",
        )
    if isinstance(value, float):
        if not float(value).is_integer() or math.isnan(value) or math.isinf(value):
            return DomainVerdict(
                False,
                "REFUSED_SCORE_IS_NOT_A_WHOLE_NUMBER",
                f"{label} is {value!r}, not a whole number of points",
            )
        value = int(value)
    if not isinstance(value, int):
        return DomainVerdict(
            False,
            "REFUSED_SCORE_IS_NOT_A_NUMBER",
            f"{label} is {type(value).__name__}, not a number of points",
        )
    if value < 0:
        return DomainVerdict(
            False,
            "REFUSED_SCORE_IS_NEGATIVE",
            f"{label} is {value}; a contest score cannot be negative",
        )
    return DomainVerdict(True, "SCORE_IN_DOMAIN", f"{label} is a valid score", value)


def valid_digest(value: Any, *, label: str = "digest") -> DomainVerdict:
    """A lowercase 64-character SHA-256. Not merely a non-empty string."""

    if not isinstance(value, str):
        return DomainVerdict(
            False,
            "REFUSED_DIGEST_IS_NOT_A_STRING",
            f"{label} is {type(value).__name__}, not a digest",
        )
    if not _HEX64.match(value):
        return DomainVerdict(
            False,
            "REFUSED_DIGEST_IS_NOT_SHA256",
            f"{label}={value[:24]!r} is not a 64-character lowercase SHA-256",
        )
    return DomainVerdict(True, "DIGEST_IN_DOMAIN", f"{label} is a SHA-256", value)


def valid_instant(
    value: Any, *, label: str = "instant", now: datetime | None = None
) -> DomainVerdict:
    """A timezone-aware instant that is not in the future.

    A naive datetime is refused rather than assumed UTC: "no timezone" and
    "UTC" are different facts, and the difference is hours of point-in-time
    validity.
    """

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return DomainVerdict(
                False,
                "REFUSED_INSTANT_IS_UNPARSEABLE",
                f"{label}={value[:32]!r} is not an ISO-8601 instant",
            )
    if not isinstance(value, datetime):
        return DomainVerdict(
            False,
            "REFUSED_INSTANT_IS_NOT_A_DATETIME",
            f"{label} is {type(value).__name__}, not an instant",
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return DomainVerdict(
            False,
            "REFUSED_INSTANT_IS_NAIVE",
            f"{label} carries no timezone; it cannot be compared to a cutoff",
        )
    reference = now or datetime.now(timezone.utc)
    if value > reference:
        return DomainVerdict(
            False,
            "REFUSED_INSTANT_IS_IN_THE_FUTURE",
            f"{label}={value.isoformat()} is after {reference.isoformat()}",
        )
    return DomainVerdict(True, "INSTANT_IN_DOMAIN", f"{label} is a past instant", value)


#: What a per-prior point-in-time publication receipt must actually carry.
#: Each field answers a question that ``if receipt:`` never asked: which
#: source, which parent contest, which bytes, and known at what time.
#:
#: Accepted spellings. The existing kernel receipt fixture writes
#: ``source_known_at_utc`` and carries the prior as one of
#: ``prior_observation_ids``; the scoring side writes ``known_at_utc`` and
#: ``prior_game_id``. Those are the same facts under two names, so both are
#: read rather than one producer being declared wrong -- but a receipt that
#: names no source, no bytes and no prior is still not a receipt, whichever
#: spelling it uses.
_FIELD_ALIASES: Mapping[str, tuple[str, ...]] = {
    "source_id": ("source_id", "source", "source_namespace"),
    "payload_sha256": ("payload_sha256", "payload_digest", "raw_sha256", "receipt_sha256"),
    "published_at_utc": ("published_at_utc", "publication_utc", "source_published_at_utc"),
    "known_at_utc": ("known_at_utc", "source_known_at_utc", "availability_utc"),
}
REQUIRED_RECEIPT_FIELDS = tuple(_FIELD_ALIASES)


def _field(receipt: Mapping[str, Any], canonical: str) -> Any:
    for name in _FIELD_ALIASES[canonical]:
        value = receipt.get(name)
        if value:
            return value
    return None


def _names_the_prior(receipt: Mapping[str, Any], prior_game_id: str) -> tuple[bool, str]:
    """Whether the receipt states which priors it covers.

    Two shapes are in use and they mean different things, so both are read
    rather than one being forced into the other:

    * ``prior_game_id`` -- this receipt is *for that one prior*, and it must
      be the prior it is offered for;
    * ``prior_observation_ids`` -- the kernel shape, where the receipt is
      keyed by the row being classified and lists the priors whose
      publication it attests. Here the row's own id is deliberately NOT in
      the list, so requiring it would reject every real receipt of this kind.
      What must hold is that the list is non-empty: a receipt that names no
      prior attests nothing.
    """

    single = receipt.get("prior_game_id") or receipt.get("prior_observation_id")
    if single:
        return str(single) == str(prior_game_id), f"prior_game_id={single!r}"
    listed = receipt.get("prior_observation_ids") or receipt.get("prior_game_ids")
    if isinstance(listed, (list, tuple)) and listed:
        values = [str(item) for item in listed]
        return True, f"prior_observation_ids={values[:5]!r}"
    return False, "no prior identity"


def attested_prior_ids(receipt: Any) -> list[str] | None:
    """The prior identities a receipt attests, in either shape; ``None`` when it names none.

    MF37A02-03. A list of prior ids identifies *priors*, not the contest the receipt is keyed by, and says
    nothing about whether those priors are the ones a row consumed. That comparison belongs to the consumer
    that knows the row (``kernel_reference.classify_pit``); this only reads what the receipt claims.
    """

    if not isinstance(receipt, Mapping):
        return None
    single = receipt.get("prior_game_id") or receipt.get("prior_observation_id")
    if single:
        return [str(single)]
    listed = receipt.get("prior_observation_ids") or receipt.get("prior_game_ids")
    if isinstance(listed, (list, tuple)) and listed:
        return [str(item) for item in listed]
    return None


def valid_publication_receipt(
    receipt: Any,
    *,
    prior_game_id: str,
    cutoff_utc: datetime | None,
    now: datetime | None = None,
) -> DomainVerdict:
    """Whether a receipt actually proves this prior was knowable before the cutoff.

    The checks, in order, are the ones ``if receipt:`` skipped:

    1. it is a mapping with every required field;
    2. its ``prior_game_id`` is the prior it is offered for, not another;
    3. its ``payload_sha256`` is a real digest;
    4. its instants are timezone-aware and not in the future;
    5. its ``known_at_utc`` is strictly before the contest's cutoff.

    A receipt that fails any of these is not a weaker receipt. It is not a
    receipt for this prior.
    """

    if not isinstance(receipt, Mapping):
        return DomainVerdict(
            False,
            "REFUSED_RECEIPT_IS_NOT_A_MAPPING",
            f"receipt is {type(receipt).__name__}; a truthy object is not evidence",
        )
    missing = [field for field in REQUIRED_RECEIPT_FIELDS if _field(receipt, field) is None]
    if missing:
        return DomainVerdict(
            False,
            "REFUSED_RECEIPT_MISSING_REQUIRED_FIELDS",
            f"receipt lacks {missing} under any accepted spelling; presence of "
            f"some keys is not evidence",
        )
    names_prior, how = _names_the_prior(receipt, prior_game_id)
    if not names_prior:
        return DomainVerdict(
            False,
            "REFUSED_RECEIPT_NAMES_A_DIFFERENT_PRIOR",
            f"receipt binds {how}, offered for {str(prior_game_id)!r}",
        )
    digest = valid_digest(_field(receipt, "payload_sha256"), label="receipt payload digest")
    if not digest:
        return digest
    published = valid_instant(
        _field(receipt, "published_at_utc"), label="published_at_utc", now=now
    )
    if not published:
        return published
    known = valid_instant(
        _field(receipt, "known_at_utc"), label="known_at_utc", now=now
    )
    if not known:
        return known
    # MF37A03-03 (Cycle #37 - Attempt #4). A receipt may carry the cutoff it
    # was issued against; that is another decision's clock, not this
    # contest's. It used to be substituted when the caller supplied none, so
    # two receipts carrying different cutoffs "proved" a target whose own
    # decision time was never stated. The contest's cutoff is required.
    if cutoff_utc is None:
        return DomainVerdict(
            False,
            "REFUSED_RECEIPT_HAS_NO_CUTOFF_TO_COMPARE",
            "no target contest cutoff was supplied; a cutoff carried by the "
            "receipt is not the target's decision time and is never substituted, "
            "so nothing can be shown to precede it",
        )
    if cutoff_utc.tzinfo is None:
        return DomainVerdict(
            False,
            "REFUSED_CUTOFF_IS_NAIVE",
            "the contest cutoff carries no timezone",
        )
    if known.value >= cutoff_utc:
        return DomainVerdict(
            False,
            "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF",
            f"known_at {known.value.isoformat()} is not strictly before cutoff "
            f"{cutoff_utc.isoformat()}; a prior that merely started earlier is "
            f"not a prior whose outcome was knowable",
        )
    if published.value > known.value:
        return DomainVerdict(
            False,
            "REFUSED_RECEIPT_PUBLISHED_AFTER_IT_WAS_KNOWN",
            f"published_at {published.value.isoformat()} is after known_at "
            f"{known.value.isoformat()}; these are different clocks and this "
            f"ordering is impossible",
        )
    attested = attested_prior_ids(receipt) or []
    return DomainVerdict(
        True,
        "RECEIPT_BINDS_THIS_PRIOR_BEFORE_THE_CUTOFF",
        # MF37A02-03: name the priors the receipt attests, not the id it was offered under. For the
        # kernel shape those differ, and printing the offered id made an unrelated prior read as bound.
        f"receipt ({how}) attests prior(s) {attested[:5]!r} known at "
        f"{known.value.isoformat()}, before cutoff {cutoff_utc.isoformat()}; whether these are the priors "
        f"a row consumed is decided by the consumer",
        {
            "source_id": str(_field(receipt, "source_id")),
            "prior_game_id": str(prior_game_id),
            "attested_prior_ids": attested,
            "prior_named_by": how,
            "payload_sha256": digest.value,
            "published_at_utc": published.value,
            "known_at_utc": known.value,
            "cutoff_utc": cutoff_utc,
        },
    )
