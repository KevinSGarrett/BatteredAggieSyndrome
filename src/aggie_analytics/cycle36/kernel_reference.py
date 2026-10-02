"""Independent reconstruction of the prior-event kernel, and PIT containment.

MR35R-08: 13,280 kernel rows, 796 whose game is in no declared raw source,
12,203 rows whose stored features disagree with an independent recompute,
and 36 rows the producer labelled ``PROVEN_PIT_TRAINING_ROW`` with no
receipt on any of them.

Two questions are kept apart here, because conflating them is what made the
producer's labels look supported:

* **Is the arithmetic reconstructible?**  Given the declared raw sources and
  a declared prior-selection policy, can the stored feature value be
  reproduced exactly? This is answerable locally and is answered here for
  every row and every field.
* **Was the value provably available before the contest?**  That needs a
  contemporaneous publication receipt for each admitted prior. No amount of
  recomputation supplies one. A row whose arithmetic reproduces perfectly is
  still ``RETROSPECTIVE_ONLY`` until receipts exist.

The prior-selection policy is declared rather than inferred:

* a prior is a completed game strictly before the target game's start
  instant, involving the team;
* the target game itself is excluded by canonical id, not by date;
* a same-day prior is admitted only when its start instant is strictly
  earlier -- equal instants are excluded, because two games starting
  together cannot inform each other;
* ties count as games played and are excluded from win rate, matching the
  kernel's declared ``EXCLUDE_TIES_FROM_BINARY_ESTIMAND``;
* no target outcome, label or future observation is read.

The *source universe* is a parameter, not a constant, because the stored
kernel and the Cycle #35 reference disagreed about it and neither said so.
Reconstructing under several declared universes and reporting which one
reproduces the stored value is how the disagreement is explained instead of
adjudicated.
"""

from __future__ import annotations

import bisect
import collections
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

# MF36-03. `classify_pit` treated any truthy object as a publication receipt
# and `admit_to_pit_consumer` read its verdict out of a caller-supplied
# mapping. Both now go through typed validation that derives admission from
# evidence instead of reading a conclusion.
from aggie_analytics.cycle37.admission_domains import (
    DOMAIN_VERSION,
    attested_prior_ids,
    valid_publication_receipt,
)

KERNEL_REFERENCE_VERSION = "BAS-KERNEL-INDEPENDENT-REFERENCE-v36.1"

#: Declared source universes. Each names the raw files it admits, so a
#: reconstruction always says which games it counted.
UNIVERSE_ALL = "ALL_DECLARED_GAME_SOURCES"
UNIVERSE_FBS_ROUTE = "FBS_ROUTE_SOURCES_ONLY"
UNIVERSE_COMPLETED_WITH_SCORES = "ALL_SOURCES_COMPLETED_WITH_BOTH_SCORES"

RECONSTRUCTED_EXACT = "RECONSTRUCTED_EXACT_MATCH"
RECONSTRUCTED_DIFFERENT = "RECONSTRUCTED_VALUE_DIFFERS"
TARGET_GAME_ABSENT = "TARGET_GAME_NOT_IN_ANY_DECLARED_SOURCE"

PIT_RETROSPECTIVE_ONLY = "RETROSPECTIVE_ONLY_NO_PUBLICATION_RECEIPT"
PIT_PROVEN = "PIT_PROVEN_BY_PER_PRIOR_RECEIPTS"
PIT_SUPERSEDED = "SUPERSEDED_PRODUCER_LABEL_WITHOUT_RECEIPTS"


def parse_instant(value: Any) -> datetime | None:
    """A timezone-aware instant, or ``None`` when the source gives none."""

    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class GameObservation:
    """One completed contest as a declared raw source states it."""

    canonical_game_id: str
    source_file: str
    season: int | None
    start: datetime | None
    home_team: str
    away_team: str
    home_points: int | None
    away_points: int | None
    completed: bool
    home_classification: str | None
    away_classification: str | None

    def side_for(self, team_id: str) -> str | None:
        if team_id == self.home_team:
            return "home"
        if team_id == self.away_team:
            return "away"
        return None

    def outcome_for(self, team_id: str) -> tuple[int, int] | None:
        """``(points_for, points_against)`` or ``None`` when unscored."""

        if self.home_points is None or self.away_points is None:
            return None
        if team_id == self.home_team:
            return (int(self.home_points), int(self.away_points))
        if team_id == self.away_team:
            return (int(self.away_points), int(self.home_points))
        return None


def observations_from_rows(
    rows: Iterable[Mapping[str, Any]],
    source_file: str,
    team_namespace: str = "SRC-002:TEAM:",
    game_namespace: str = "SRC-002:GAME:",
) -> list[GameObservation]:
    found: list[GameObservation] = []
    for row in rows:
        if row.get("id") is None:
            continue
        found.append(
            GameObservation(
                canonical_game_id=f"{game_namespace}{row['id']}",
                source_file=source_file,
                season=int(row["season"]) if row.get("season") is not None else None,
                start=parse_instant(row.get("startDate")),
                home_team=f"{team_namespace}{row.get('homeId')}",
                away_team=f"{team_namespace}{row.get('awayId')}",
                home_points=row.get("homePoints"),
                away_points=row.get("awayPoints"),
                completed=bool(row.get("completed")),
                home_classification=row.get("homeClassification"),
                away_classification=row.get("awayClassification"),
            )
        )
    return found


@dataclass(frozen=True)
class TeamObservation:
    """One team's result in one contest, from whichever source states it.

    The public game feeds state a contest with two sides; the private
    BAT-523 lane states one row per team. Both reduce to this shape, which
    is what lets a reconstruction declare a universe spanning them without
    pretending they share a record structure.
    """

    team_id: str
    canonical_game_id: str
    start: datetime
    season: int | None
    points_for: int
    points_against: int
    source_file: str

    @property
    def tie(self) -> bool:
        return self.points_for == self.points_against

    @property
    def won(self) -> bool:
        return self.points_for > self.points_against


def team_observations(game: GameObservation) -> list[TeamObservation]:
    """Split a two-sided contest into the two rows it states."""

    if game.start is None:
        return []
    rows: list[TeamObservation] = []
    for team_id in (game.home_team, game.away_team):
        outcome = game.outcome_for(team_id)
        if outcome is None:
            continue
        rows.append(
            TeamObservation(
                team_id=team_id,
                canonical_game_id=game.canonical_game_id,
                start=game.start,
                season=game.season,
                points_for=outcome[0],
                points_against=outcome[1],
                source_file=game.source_file,
            )
        )
    return rows


@dataclass
class TeamHistory:
    """One team's completed contests, in chronological order."""

    team_id: str
    starts: list[datetime] = field(default_factory=list)
    games: list[TeamObservation] = field(default_factory=list)

    def priors_before(
        self,
        instant: datetime,
        exclude_game_id: str,
        same_instant: str = "EXCLUDE_EQUAL_INSTANT",
    ) -> list[TeamObservation]:
        """Contests earlier than ``instant``, target always excluded by id.

        ``same_instant`` is a declared policy, not an implementation detail.
        Two contests kicking off at the same instant cannot inform each other,
        which is why ``EXCLUDE_EQUAL_INSTANT`` is the default. A producer that
        compared dates rather than instants effectively used
        ``INCLUDE_EQUAL_INSTANT``, and reconstructing under both is how that
        difference is shown rather than argued about. The target contest is
        excluded by canonical id under either policy, so including equal
        instants never leaks the target's own outcome.
        """

        cut = (
            bisect.bisect_right(self.starts, instant)
            if same_instant == "INCLUDE_EQUAL_INSTANT"
            else bisect.bisect_left(self.starts, instant)
        )
        return [
            game
            for game in self.games[:cut]
            if game.canonical_game_id != exclude_game_id
        ]


@dataclass
class GameUniverse:
    """The declared set of contests a reconstruction is allowed to count."""

    name: str
    by_game: dict[str, GameObservation]
    histories: dict[str, TeamHistory]
    admitted: int
    rejected: dict[str, int]
    same_instant_policy: str = "EXCLUDE_EQUAL_INSTANT"

    def features_for(
        self, team_id: str, instant: datetime, target_game_id: str, season: int | None
    ) -> dict[str, Any]:
        history = self.histories.get(team_id)
        if history is None:
            return {
                "pit_prior_games_played": 0,
                "pit_prior_margin_mean": None,
                "pit_prior_points_against_mean": None,
                "pit_prior_points_for_mean": None,
                "pit_prior_season_win_rate": None,
                "pit_prior_win_rate": None,
                "pit_season_to_date_games": 0,
                "pit_season_to_date_win_rate": None,
                "admitted_prior_game_ids": [],
            }
        priors = history.priors_before(
            instant, target_game_id, self.same_instant_policy
        )
        points_for: list[int] = []
        points_against: list[int] = []
        wins = 0
        decided = 0
        season_wins = 0
        season_decided = 0
        season_games = 0
        for game in priors:
            scored_for, scored_against = game.points_for, game.points_against
            points_for.append(scored_for)
            points_against.append(scored_against)
            if scored_for != scored_against:
                decided += 1
                if scored_for > scored_against:
                    wins += 1
            if season is not None and game.season == season:
                season_games += 1
                if scored_for != scored_against:
                    season_decided += 1
                    if scored_for > scored_against:
                        season_wins += 1
        played = len(points_for)
        return {
            "pit_prior_games_played": played,
            "pit_prior_points_for_mean": (
                sum(points_for) / played if played else None
            ),
            "pit_prior_points_against_mean": (
                sum(points_against) / played if played else None
            ),
            "pit_prior_margin_mean": (
                (sum(points_for) - sum(points_against)) / played if played else None
            ),
            "pit_prior_win_rate": (wins / decided if decided else None),
            "pit_season_to_date_games": season_games,
            "pit_season_to_date_win_rate": (
                season_wins / season_decided if season_decided else None
            ),
            "pit_prior_season_win_rate": (
                season_wins / season_decided if season_decided else None
            ),
            "admitted_prior_game_ids": [
                game.canonical_game_id for game in priors
            ],
        }


def build_universe(
    name: str,
    observations: Sequence[GameObservation],
    require_completed: bool = True,
    require_scores: bool = True,
    allowed_source_files: Sequence[str] | None = None,
    extra_team_observations: Sequence[TeamObservation] = (),
    dedupe_by: str = "SOURCE_GAME_ID",
    same_instant_policy: str = "EXCLUDE_EQUAL_INSTANT",
) -> GameUniverse:
    """A declared, explained source universe with its exclusions counted.

    ``extra_team_observations`` admits a source that states one row per team
    rather than one row per contest -- the private BAT-523 lane. Its contests
    become locatable targets, and rows already present in a public source are
    counted as such rather than double-counted.

    ``dedupe_by`` decides what "already present" means:

    * ``SOURCE_GAME_ID`` -- two rows are the same contest only when both
      sources use the same identifier. The public feeds and the private lane
      do NOT: the same 2015 contest carries a CFBD id in one and a different
      ``source_game_id`` in the other, so a union under this rule counts it
      twice and inflates every later prior count.
    * ``CONTEST_IDENTITY`` -- two rows are the same contest when the same team
      played at the same instant with the same score. That is a property of
      the contest rather than of whoever catalogued it, so it deduplicates
      across namespaces without needing a crosswalk between their id spaces.
    """

    by_game: dict[str, GameObservation] = {}
    rejected: collections.Counter = collections.Counter()
    for observation in observations:
        if allowed_source_files is not None and (
            observation.source_file not in allowed_source_files
        ):
            rejected["SOURCE_FILE_NOT_IN_THIS_UNIVERSE"] += 1
            continue
        if require_completed and not observation.completed:
            rejected["NOT_COMPLETED"] += 1
            continue
        if require_scores and (
            observation.home_points is None or observation.away_points is None
        ):
            rejected["NO_SCORE_ON_BOTH_SIDES"] += 1
            continue
        if observation.start is None:
            rejected["NO_START_INSTANT"] += 1
            continue
        existing = by_game.get(observation.canonical_game_id)
        if existing is not None:
            rejected["DUPLICATE_GAME_ID"] += 1
            continue
        by_game[observation.canonical_game_id] = observation

    rows: list[TeamObservation] = []
    for observation in by_game.values():
        rows.extend(team_observations(observation))

    def identity(row: "TeamObservation") -> tuple:
        if dedupe_by == "CONTEST_IDENTITY":
            return (row.team_id, row.start, row.points_for, row.points_against)
        return (row.team_id, row.canonical_game_id)

    seen_pairs = {identity(row) for row in rows}
    for extra in extra_team_observations:
        key = identity(extra)
        if key in seen_pairs:
            rejected["PRIVATE_ROW_ALREADY_PRESENT_IN_A_PUBLIC_SOURCE"] += 1
            continue
        seen_pairs.add(key)
        rows.append(extra)
        by_game.setdefault(
            extra.canonical_game_id,
            GameObservation(
                canonical_game_id=extra.canonical_game_id,
                source_file=extra.source_file,
                season=extra.season,
                start=extra.start,
                home_team=extra.team_id,
                away_team="",
                home_points=extra.points_for,
                away_points=extra.points_against,
                completed=True,
                home_classification=None,
                away_classification=None,
            ),
        )

    histories: dict[str, TeamHistory] = {}
    for row in rows:
        histories.setdefault(row.team_id, TeamHistory(row.team_id)).games.append(row)
    for history in histories.values():
        history.games.sort(key=lambda game: (game.start, game.canonical_game_id))
        history.starts = [game.start for game in history.games]
    return GameUniverse(
        name=name,
        by_game=by_game,
        histories=histories,
        admitted=len(by_game),
        rejected=dict(rejected),
        same_instant_policy=same_instant_policy,
    )


NUMERIC_FIELDS = (
    "pit_prior_games_played",
    "pit_prior_margin_mean",
    "pit_prior_points_against_mean",
    "pit_prior_points_for_mean",
    "pit_prior_season_win_rate",
    "pit_prior_win_rate",
    "pit_season_to_date_games",
    "pit_season_to_date_win_rate",
)


def compare_value(stored: Any, reference: Any, tolerance: float = 1e-9) -> bool:
    if stored is None or reference is None:
        return stored is None and reference is None
    try:
        return abs(float(stored) - float(reference)) <= tolerance
    except (TypeError, ValueError):
        return stored == reference


def reconstruct_row(
    row: Mapping[str, Any], universe: GameUniverse
) -> dict[str, Any]:
    """One kernel row recomputed independently, field by field."""

    game_id = str(row.get("canonical_game_id") or "")
    target = universe.by_game.get(game_id)
    record: dict[str, Any] = {
        "canonical_game_id": game_id,
        "season": row.get("season"),
        "universe": universe.name,
        "reference_version": KERNEL_REFERENCE_VERSION,
    }
    if target is None or target.start is None:
        record.update(
            state=TARGET_GAME_ABSENT,
            detail=(
                "The kernel's target game is in no contest admitted by this "
                "declared universe, so no prior can be selected against its "
                "start instant. This is a source-membership fact, not a "
                "missing crosswalk to guess at."
            ),
        )
        return record

    sides = {
        "home": str(row.get("home_canonical_team_id") or ""),
        "away": str(row.get("away_canonical_team_id") or ""),
    }
    comparisons: list[dict[str, Any]] = []
    exact_fields = 0
    total_fields = 0
    for side, team_id in sides.items():
        stored_features = row.get(f"{side}_features") or {}
        reference = universe.features_for(
            team_id, target.start, game_id, row.get("season")
        )
        for name in NUMERIC_FIELDS:
            stored = stored_features.get(name)
            value = reference.get(name)
            same = compare_value(stored, value)
            total_fields += 1
            exact_fields += int(same)
            if not same:
                comparisons.append(
                    {
                        "side": side,
                        "team_id": team_id,
                        "field": name,
                        "stored": stored,
                        "independent_reference": value,
                    }
                )
        record[f"{side}_admitted_prior_count"] = len(
            reference["admitted_prior_game_ids"]
        )
    record.update(
        state=RECONSTRUCTED_EXACT if not comparisons else RECONSTRUCTED_DIFFERENT,
        fields_compared=total_fields,
        fields_matching=exact_fields,
        differences=comparisons[:16],
        difference_count=len(comparisons),
        target_game_excluded_by_id=True,
        target_outcome_read=False,
    )
    return record


#: MF37A02-03 (Cycle #37 - Attempt #3). The gate every PIT consumer calls. Bumped because its admission set
#: changed: a receipt must now be resolved to verified bytes by a declared authority, and the priors it
#: attests must be exactly the dependencies the row declares it consumed.
#: v37.4 (MF37A03-03): one explicit, aware target cutoff is required before any offered prior is verified; a
#: receipt's own decision time is never substituted for it.
PIT_CONSUMER_GATE_VERSION = "BAS-PIT-CONSUMER-GATE-v37.4"
PREDECESSOR_PIT_CONSUMER_GATE_VERSION = "BAS-PIT-CONSUMER-GATE-v37.3"

#: Row fields that declare what a row's features consumed. A list of prior ids identifies *priors*; it is
#: compared with what receipts attest, never with the row's own contest id.
CONSUMED_DEPENDENCY_FIELDS = (
    "consumed_prior_ids",
    "prior_observation_ids",
    "admitted_prior_game_ids",
    "home_admitted_prior_game_ids",
    "away_admitted_prior_game_ids",
    "feature_dependency_ids",
)

REFUSED_DEPENDENCIES_UNDECLARED = "REFUSED_CONSUMED_DEPENDENCIES_ARE_NOT_DECLARED"
REFUSED_NOTHING_TO_PROVE = "REFUSED_NO_CONSUMED_DEPENDENCY_TO_PROVE"
REFUSED_PRIOR_NOT_ATTESTED = "REFUSED_CONSUMED_PRIOR_IS_NOT_ATTESTED"
REFUSED_PRIOR_NOT_CONSUMED = "REFUSED_RECEIPT_ATTESTS_A_PRIOR_THE_ROW_DID_NOT_CONSUME"
REFUSED_CONFLICTING = "REFUSED_CONFLICTING_RECEIPTS_FOR_ONE_PRIOR"
REFUSED_NO_AUTHORITY = "REFUSED_NO_TRUSTED_RECEIPT_AUTHORITY"
REFUSED_NO_BYTES_IDENTITY = "REFUSED_RECEIPT_HAS_NO_BYTES_IDENTITY"
REFUSED_CLAIM_DIFFERS = "REFUSED_OFFERED_RECEIPT_DIFFERS_FROM_ITS_VERIFIED_BYTES"
REFUSED_STANDALONE = "REFUSED_A_CLASSIFICATION_WITHOUT_ITS_ROW_CANNOT_BIND_WHAT_THE_ROW_CONSUMED"
#: MF37A03-03 additions: the target's own decision time, required before any prior is verified.
REFUSED_NO_TARGET_CUTOFF = "REFUSED_TARGET_HAS_NO_CUTOFF"
REFUSED_TARGET_CUTOFF_UNUSABLE = "REFUSED_TARGET_CUTOFF_IS_NOT_A_USABLE_AWARE_INSTANT"
REFUSED_TARGET_CUTOFF_CONFLICT = "REFUSED_TARGET_CUTOFFS_CONFLICT"
#: Where a target cutoff may be stated: the caller's argument, then the row's own fields.
TARGET_CUTOFF_FIELDS = ("cutoff_utc", "decision_cutoff_utc")


def target_cutoff(row: Mapping[str, Any], cutoff_utc: Any = None) -> tuple[datetime | None, str | None, str]:
    """(cutoff, refusal code, detail) for one target row: the single decision time its priors must precede.

    Every statement of the target's cutoff -- the caller's argument and each of the row's cutoff fields -- must
    be a timezone-aware instant, and all statements present must name the same instant. None present is a
    refusal, not a default: a receipt carries the decision time *it* was issued against, which is another
    contest's clock, and ``now`` is not a decision time at all.
    """

    stated: list[tuple[str, Any]] = []
    if cutoff_utc is not None:
        stated.append(("argument cutoff_utc", cutoff_utc))
    for name in TARGET_CUTOFF_FIELDS:
        if row.get(name) is not None:
            stated.append((f"row {name}", row.get(name)))
    if not stated:
        return None, REFUSED_NO_TARGET_CUTOFF, ("the target row states no cutoff and none was supplied; no prior "
                                                "can be shown to precede a decision time that is not stated")
    instants: list[tuple[str, datetime]] = []
    for source, value in stated:
        # A target cutoff may lie in the future (an upcoming contest); it must still be an aware instant.
        parsed = value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None, REFUSED_TARGET_CUTOFF_UNUSABLE, f"{source} {value[:40]!r} is not an ISO-8601 instant"
        if not isinstance(parsed, datetime):
            return None, REFUSED_TARGET_CUTOFF_UNUSABLE, f"{source} is {type(value).__name__}, not an instant"
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None, REFUSED_TARGET_CUTOFF_UNUSABLE, (f"{source} {parsed.isoformat()} carries no timezone; a "
                                                          f"naive time is not a decision instant")
        instants.append((source, parsed))
    distinct = {instant for _source, instant in instants}
    if len(distinct) > 1:
        return None, REFUSED_TARGET_CUTOFF_CONFLICT, (
            "the target's cutoff is stated as different instants: "
            + ", ".join(f"{source}={instant.isoformat()}" for source, instant in instants))
    return instants[0][1], None, "; ".join(source for source, _instant in instants)


def consumed_dependencies(row: Mapping[str, Any]) -> list[str] | None:
    """The sorted, distinct dependency ids a row declares it consumed; ``None`` when it declares none.

    A malformed declaration (not a list) is treated as undeclared: an unreadable dependency set cannot be
    shown to have been covered by anything.
    """

    declared = False
    found: list[str] = []
    for field_name in CONSUMED_DEPENDENCY_FIELDS:
        if field_name not in row or row[field_name] is None:
            continue
        value = row[field_name]
        if not isinstance(value, (list, tuple)):
            return None
        declared = True
        found.extend(str(item) for item in value)
    return sorted(set(found)) if declared else None


def _offered_receipts(receipts: Mapping[str, Any], game_id: str,
                      consumed: list[str] | None) -> list[tuple[str, Any]]:
    """(offered-under key, offered item) pairs: the row-keyed shape, then any per-prior entries."""

    offered: list[tuple[str, Any]] = []

    def add(key: str, value: Any) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                offered.append((key, item))
        elif value is not None:
            offered.append((key, value))

    if game_id in receipts:
        add(game_id, receipts[game_id])
    for prior in consumed or []:
        if prior != game_id and prior in receipts:
            add(prior, receipts[prior])
    return offered


def classify_pit(
    row: Mapping[str, Any],
    receipts_by_game: Mapping[str, Any] | None = None,
    *,
    cutoff_utc: datetime | None = None,
    now: datetime | None = None,
    authority: Any = None,
) -> dict[str, Any]:
    """Supersede a producer label with a receipt-backed classification.

    A producer's ``PROVEN_PIT_TRAINING_ROW`` is retained verbatim as the
    predecessor claim and replaced by a classification that fails closed
    unless per-prior publication receipts exist. Creating a timestamp or
    loosening the definition of a receipt would be the repair this refuses.

    MF36-03. This was ``if receipt:``, so ``{"unrelated": True}`` was a
    point-in-time publication receipt and any non-empty object promoted a
    row to ``PIT_PROVEN``. A receipt is validated: it must be a mapping
    carrying a source, the prior it binds, a real SHA-256, and publication
    and known-at instants that are timezone-aware, not in the future,
    correctly ordered, and strictly before this contest's cutoff.

    MF37A02-03. Those checks were all about the receipt and none about the
    row: a self-asserted receipt naming ``UNRELATED-PRIOR``, with an invented
    digest and no bytes, proved a row whose features consumed
    ``REQUIRED-PRIOR``. Now, in order:

    1. every offered receipt claim must pass the domain checks above
       (unchanged codes, so the missing-digest and late known-at refusals
       read as before);
    2. the row must declare the dependencies it consumed
       (:data:`CONSUMED_DEPENDENCY_FIELDS`), and the priors the offered
       receipts attest must be *exactly* that set -- none omitted, none
       extra;
    3. a declared receipt authority must resolve every offered receipt, by
       its digest, to re-hashed receipt and payload bytes from a trusted
       source, and each caller claim must equal those verified bytes;
    4. the verified contents are validated again against the cutoff, the
       exact-set rule is re-applied to what the bytes attest, and two
       verified receipts that disagree about one prior are refused.

    Without a cutoff nothing can be shown to have been knowable in time, so
    a row with no cutoff stays inadmissible rather than defaulting to now.
    An admission supported by a test-only authority says so and never counts
    as real point-in-time proof.

    MF37A03-03 (Cycle #37 - Attempt #4). That paragraph was not what the
    code did: with no target cutoff, ``effective_cutoff`` was None and
    ``valid_publication_receipt`` fell back to *each receipt's own*
    ``cutoff_utc``, so two receipts carrying 12:00 and 14:00 proved a row
    whose own decision time was never stated, and a prior known at 13:00
    became admissible by omitting the target cutoff. Now, as soon as any
    receipt is offered and before any is verified, :func:`target_cutoff`
    must resolve one aware instant from the caller's argument and the row's
    cutoff fields (missing, malformed, naive or conflicting statements
    refuse), and that one instant is used for every receipt check and
    reported with the classification.
    """

    receipts = dict(receipts_by_game or {})
    game_id = str(row.get("canonical_game_id") or "")
    producer_label = row.get("authority_class") or row.get("row_verdict")

    effective_cutoff, cutoff_refusal, cutoff_source = target_cutoff(row, cutoff_utc)

    consumed = consumed_dependencies(row)
    offered = _offered_receipts(receipts, game_id, consumed)
    superseded = str(producer_label or "").upper().startswith("PROVEN")
    cutoff_text = effective_cutoff.isoformat() if isinstance(effective_cutoff, datetime) else None

    def not_proven(verdict: dict[str, Any] | None) -> dict[str, Any]:
        detail = (
            "No per-prior publication receipt binds any admitted prior to a "
            "time before this contest's cutoff. The arithmetic may reproduce "
            "exactly and the row still cannot enter a point-in-time consumer."
        )
        if verdict is not None:
            detail = (
                f"A receipt was offered and rejected: {verdict['detail']}. An offered "
                f"receipt that fails validation is not weaker evidence; it is not "
                f"evidence for this prior."
            )
        return {
            "canonical_game_id": game_id,
            "producer_label": producer_label,
            "successor_state": PIT_SUPERSEDED if superseded else PIT_RETROSPECTIVE_ONLY,
            "receipt": None,
            "receipt_offered": bool(offered),
            "receipt_validation": verdict,
            "consumed_dependencies": consumed,
            "cutoff_utc": cutoff_text,
            "admissible_to_a_pit_consumer": False,
            "gate_version": PIT_CONSUMER_GATE_VERSION,
            "detail": detail,
        }

    def refused(code: str, detail: str) -> dict[str, Any]:
        return not_proven({"domain_version": DOMAIN_VERSION, "ok": False, "code": code, "detail": detail})

    if not offered:
        return not_proven(None)

    # 0. MF37A03-03: the target's own decision time, before any offered prior is looked at.
    if cutoff_refusal is not None:
        return refused(cutoff_refusal, cutoff_source)

    # 1. Domain checks on every claim a caller offered, with their original codes.
    for key, item in offered:
        if isinstance(item, Mapping) or not isinstance(item, str):
            verdict = valid_publication_receipt(item, prior_game_id=key, cutoff_utc=effective_cutoff, now=now)
            if not verdict.ok:
                return not_proven(verdict.as_dict())

    # 2. The consumed set, exactly, as far as the claims state it.
    if consumed is None:
        return refused(REFUSED_DEPENDENCIES_UNDECLARED,
                       "the row does not declare which priors or feature dependencies it consumed, so no receipt "
                       "can be shown to cover them; a receipt's prior list identifies priors, not this contest")
    if not consumed:
        return refused(REFUSED_NOTHING_TO_PROVE,
                       "the row declares an empty dependency set; a point-in-time claim with nothing to bind is "
                       "not proven by any receipt")

    def exact_set(attested: set[str], basis: str) -> dict[str, Any] | None:
        omitted = sorted(set(consumed) - attested)
        extra = sorted(attested - set(consumed))
        if omitted:
            return refused(REFUSED_PRIOR_NOT_ATTESTED,
                           f"{basis} attest {sorted(attested)[:5]} but the row consumed {consumed[:5]}; "
                           f"not attested: {omitted[:5]}")
        if extra:
            return refused(REFUSED_PRIOR_NOT_CONSUMED,
                           f"{basis} attest {extra[:5]}, which the row did not consume; the consumed set must be "
                           f"matched exactly")
        return None

    claims = [item for _key, item in offered if isinstance(item, Mapping)]
    if len(claims) == len(offered):
        claimed: set[str] = set()
        for item in claims:
            claimed.update(attested_prior_ids(item) or [])
        failure = exact_set(claimed, "the offered receipts")
        if failure is not None:
            return failure

    # 3. Bytes: every offered receipt must resolve, by digest, in a declared authority.
    if authority is None:
        return refused(REFUSED_NO_AUTHORITY,
                       "no receipt authority was supplied, so no offered receipt can be resolved to bytes; a "
                       "self-asserted receipt and a digest-shaped string are claims, not evidence")
    from aggie_analytics.cycle37.receipt_authority import PRIOR_RECEIPT  # noqa: PLC0415 - avoid an import cycle

    verified: list[tuple[str, Any, Any]] = []
    for key, item in offered:
        digest = item if isinstance(item, str) else (item.get("receipt_digest") if isinstance(item, Mapping) else None)
        if not digest:
            return refused(REFUSED_NO_BYTES_IDENTITY,
                           "an offered receipt carries no receipt_digest, so there are no bytes to verify it against")
        resolved = authority.resolve(digest, expected_kind=PRIOR_RECEIPT)
        if not resolved.ok:
            return not_proven(resolved.as_dict())
        content = resolved.value.content
        if isinstance(item, Mapping):
            differing = sorted(k for k, v in item.items() if k != "receipt_digest" and content.get(k) != v)
            if differing:
                return refused(REFUSED_CLAIM_DIFFERS,
                               f"the offered receipt states {differing} differently from its verified bytes")
        verdict = valid_publication_receipt(dict(content), prior_game_id=key, cutoff_utc=effective_cutoff, now=now)
        if not verdict.ok:
            return not_proven(verdict.as_dict())
        verified.append((key, resolved.value, verdict))

    # 4. The exact set again, over what the verified bytes attest; and no two receipts may disagree.
    attested: set[str] = set()
    by_prior: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for _key, receipt, verdict in verified:
        for prior in attested_prior_ids(dict(receipt.content)) or []:
            attested.add(prior)
            by_prior[prior].add((receipt.payload_digest, str(verdict.value["known_at_utc"])))
    failure = exact_set(attested, "the verified receipts")
    if failure is not None:
        return failure
    conflicting = sorted(prior for prior, statements in by_prior.items() if len(statements) > 1)
    if conflicting:
        return refused(REFUSED_CONFLICTING,
                       f"verified receipts disagree about the publication of {conflicting[:5]}")

    first = verified[0]
    return {
        "canonical_game_id": game_id,
        "producer_label": producer_label,
        "successor_state": PIT_PROVEN,
        "receipt": dict(first[1].content),
        "receipts": [receipt.evidence() for _key, receipt, _verdict in verified],
        "receipt_validation": first[2].as_dict(),
        "consumed_dependencies": consumed,
        "cutoff_utc": cutoff_text,
        "cutoff_source": cutoff_source,
        "admissible_to_a_pit_consumer": True,
        "authority": authority.describe(),
        "authority_class": authority.authority_class,
        "counts_as_real_pit_proof": authority.counts_as_real_evidence,
        "gate_version": PIT_CONSUMER_GATE_VERSION,
    }


def admit_to_pit_consumer(
    classification: Mapping[str, Any],
    *,
    row: Mapping[str, Any] | None = None,
    receipts_by_game: Mapping[str, Any] | None = None,
    cutoff_utc: datetime | None = None,
    now: datetime | None = None,
    authority: Any = None,
) -> bool:
    """The single gate every PIT consumer must call. Fails closed.

    MF36-03. This read ``admissible_to_a_pit_consumer`` and
    ``successor_state`` straight out of whatever mapping it was handed, so a
    caller could state the conclusion and have it believed.

    MF37A02-03. The standalone path then re-validated the receipt a
    classification carried -- but a classification carries whatever priors
    its author chose, so it could never show that those were the priors the
    row consumed. Admission is now derived only from the originating ``row``,
    the offered receipts and the authority: the classification is re-derived
    here, and believed only when that fresh derivation proves the same
    contest. A classification handed in without its row is refused.
    """

    if not isinstance(classification, Mapping) or row is None:
        return False
    derived = classify_pit(row, receipts_by_game, cutoff_utc=cutoff_utc, now=now, authority=authority)
    if derived.get("successor_state") != PIT_PROVEN:
        return False
    if not derived.get("admissible_to_a_pit_consumer"):
        return False
    # MF37A03-03: the gate and the classification must have used the same one decision time.
    if not derived.get("cutoff_utc") or classification.get("cutoff_utc") != derived.get("cutoff_utc"):
        return False
    return str(classification.get("canonical_game_id") or "") == str(
        derived.get("canonical_game_id") or ""
    )
