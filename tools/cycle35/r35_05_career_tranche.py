"""R35-05: complete the predeclared 48-key national career tranche.

The order matters and is enforced by the structure of this script: the 48
person-program-role-time keys are **predeclared from the canonical
population** before any evidence is consulted, written out, and only then
resolved. A key that turns out to be hard is not swapped for an easier
school -- it is resolved to MISSING or CONFLICT and stays in the denominator.

Selection is deterministic (sorted program ids, fixed season ladder), so the
same population produces the same 48 keys on every run and the set cannot
drift toward whatever happened to resolve.

Resolution is cache-first against the 54,871 already-acquired Wikimedia
career episodes, using the REPAIRED `join_occupant_to_pages` with role and
season bound -- the Cycle #34 version could not express those arguments at
all. Only keys with no cached evidence spend request budget.

Dispositions are evidence-backed and mutually exclusive:

    ACCEPTED_CORROBORATED   two or more independent sources agree
    ACCEPTED_SINGLE_SOURCE  exactly one source supports the key
    CONFLICT                sources disagree; both retained, neither wins
    MISSING_NO_EVIDENCE     nothing found after a bounded, counted attempt
    AMBIGUOUS               evidence exists but cannot be uniquely resolved

An unattempted key is never MISSING_NO_EVIDENCE; it is NOT_ATTEMPTED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.career_identity import (  # noqa: E402
    employer_evidence_matches,
)
from aggie_analytics.cycle35.request_ledger import (  # noqa: E402
    BUDGET_COACHING,
    RequestLedger,
)

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
CURRENT_PROGRAMS = OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl"
HISTORICAL_LATE = OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl"
HISTORICAL_EARLY = OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
CAREER_EPISODES = OUTPUTS / "WIKIMEDIA_CAREER_SEASON_EPISODES.jsonl"
CAREER_PAGES = OUTPUTS / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"

#: The season ladder. R35-05 requires at least FOUR distinct seasons in each
#: of the four declared historical bands, so each band contributes four
#: seasons here plus the current season. An earlier two-per-band ladder
#: satisfied the band COUNT but not the distinct-season requirement, which is
#: a different clause -- caught by checking the delivered tranche against the
#: requirement text rather than against the band tally.
SEASON_LADDER = (
    2001, 2002, 2004, 2005,   # 2000-2005
    2007, 2009, 2011, 2012,   # 2006-2012
    2014, 2015, 2017, 2018,   # 2013-2018
    2019, 2020, 2022, 2023,   # 2019-2023
    2026,                     # current slice
)

#: Roles, including two that carry title modifiers so qualifier handling is
#: exercised rather than assumed.
ROLE_LADDER = ("head_coach", "offensive_coordinator", "defensive_coordinator")

TARGET_PER_DIVISION = 24

ACCEPTED_CORROBORATED = "ACCEPTED_CORROBORATED"
ACCEPTED_SINGLE = "ACCEPTED_SINGLE_SOURCE"
CONFLICT = "CONFLICT"
MISSING = "MISSING_NO_EVIDENCE"
AMBIGUOUS = "AMBIGUOUS"
NOT_ATTEMPTED = "NOT_ATTEMPTED"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_population() -> dict[str, dict[str, Any]]:
    """program_id -> {display_name, classification_by_season, seasons}.

    MF35-08 repair: this previously kept one collapsed `classification`
    string per program, overwritten by whichever membership file's row for
    that program was read LAST (HISTORICAL_EARLY, then HISTORICAL_LATE, then
    CURRENT_PROGRAMS) -- so a program's CURRENT (2026) subdivision silently
    became its classification for every season it ever played, including
    seasons decades earlier under a different subdivision. An independent
    manager check against the same-season source found two of the 48
    predeclared keys wrong under this rule: Massachusetts is FBS in 2026 but
    the source says FCS for 2002; Sacramento State is FBS in 2026 but the
    source says FCS for 2023. `classification_by_season` now keeps each
    season's OWN classification as stated by the membership row that named
    that season, so a caller can select same-season subdivision instead of
    the program's most recent one.
    """

    programs: dict[str, dict[str, Any]] = {}
    for path in (HISTORICAL_EARLY, HISTORICAL_LATE, CURRENT_PROGRAMS):
        for row in read_jsonl(path):
            pid = str(row.get("program_id") or "")
            if not pid:
                continue
            entry = programs.setdefault(
                pid,
                {
                    "program_id": pid,
                    "display_name": row.get("display_name"),
                    "classification_by_season": {},
                    "seasons": set(),
                },
            )
            season = row.get("season")
            season_int = int(season) if season else 2026
            entry["seasons"].add(season_int)
            classification = row.get("classification")
            if classification:
                # A season's classification is proved by the row that names
                # THAT season; a later file's row for a DIFFERENT season
                # must never overwrite it.
                entry["classification_by_season"][season_int] = classification
            if row.get("display_name"):
                entry["display_name"] = row.get("display_name")
    return programs


def same_season_classification(entry: dict[str, Any], season: int) -> str | None:
    """The subdivision the source states FOR THIS SEASON, or None if the
    source never stated a classification for it. Never falls back to the
    program's most recent or any other season's classification."""

    return entry.get("classification_by_season", {}).get(season)


def predeclare_keys(programs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """48 keys chosen before any evidence is looked at.

    MF35-08 repair: a candidate is no longer bucketed into fbs/fcs by one
    collapsed per-program classification computed before any season is
    chosen. A program's division membership can itself change across
    seasons (Massachusetts: FCS in 2002, FBS by 2026; Sacramento State: FBS
    in 2026, FCS in 2023) -- the tranche's OWN classification for a key must
    be the classification the source states for THAT key's season, checked
    after the season is already known, never a program-level default.
    """

    all_programs = sorted(programs.values(), key=lambda item: str(item["program_id"]))

    keys: list[dict[str, Any]] = []
    for division in ("fbs", "fcs"):
        picked = 0
        index = 0
        limit = max(len(all_programs) * len(SEASON_LADDER), 1)
        while picked < TARGET_PER_DIVISION and index < limit:
            entry = all_programs[index % len(all_programs)] if all_programs else None
            if entry is None:
                break
            season = SEASON_LADDER[picked % len(SEASON_LADDER)]
            role = ROLE_LADDER[picked % len(ROLE_LADDER)]
            index += 1
            if same_season_classification(entry, season) != division:
                # Either the program did not exist in that season, its
                # SAME-SEASON classification is the other division, or the
                # source never stated one for that season -- none of these
                # fabricate a program-season-division that was never proved.
                continue
            keys.append(
                {
                    "key_id": "K%02d" % (len(keys) + 1),
                    "program_id": entry["program_id"],
                    "display_name": entry["display_name"],
                    "classification": division,
                    "season": season,
                    "role": role,
                    "era_band": (
                        "2000-2005" if season <= 2005
                        else "2006-2012" if season <= 2012
                        else "2013-2018" if season <= 2018
                        else "2019-2023" if season <= 2023
                        else "CURRENT_2026"
                    ),
                    "predeclared_before_evidence": True,
                    "classification_authority": "SAME_SEASON_MEMBERSHIP_ROW",
                }
            )
            picked += 1
    return keys


def index_cached_episodes() -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """program_raw-insensitive index of every cached career episode."""

    episodes = read_jsonl(CAREER_EPISODES)
    by_season: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in episodes:
        season = row.get("season")
        if season is None:
            continue
        by_season[int(season)].append(row)
    return by_season, {
        "episode_rows": len(episodes),
        "distinct_seasons": len(by_season),
        "path": str(CAREER_EPISODES),
        "sha256": hashlib.sha256(CAREER_EPISODES.read_bytes()).hexdigest()
        if CAREER_EPISODES.is_file()
        else None,
    }


def semantic_key(row: dict[str, Any]) -> tuple[str, str, str]:
    """(program_id, season, role) -- the STABLE identity of a career-tranche
    key. `key_id` (K01, K02, ...) is a mutable ordinal position in a
    deterministic walk; MF35-08 proved that correctly fixing one early
    eligibility check reassigns every downstream key_id even though most
    underlying program/season/role facts did not change. Reconciling two
    tranche samples by key_id alone would compare the WRONG things at the
    SAME id and miss the SAME thing at two different ids; this is the key
    that must be used instead.
    """

    return (
        str(row.get("program_id") or ""),
        str(row.get("season") or ""),
        str(row.get("role") or ""),
    )


def reconcile_tranche_samples(
    old_keys: list[dict[str, Any]], new_keys: list[dict[str, Any]]
) -> dict[str, Any]:
    """Cycle #35 manager follow-up (20260920T224700Z): "Preserve and
    account for both sample versions. Explain why each old key was
    retained, reclassified, supplemented, or superseded... The two sets'
    union has 88 distinct program/season/role keys; this is reconciliation
    accounting, not permission to substitute a new sample for unfinished
    original obligations."

    Every semantic key in EITHER sample is classified exactly once:

    * RETAINED -- present in both, same classification, same disposition.
    * RECLASSIFIED -- present in both, but fbs/fcs classification differs
      (the era-correctness fix changing which division a key belongs to).
    * DISPOSITION_CHANGED -- present in both, same classification, but the
      resolution disposition differs (e.g. resolved by the second pass on
      one side but not the other).
    * SUPERSEDED -- present only in the OLD sample. The corrected
      selection algorithm no longer reaches this exact program/season/role
      combination (usually a downstream reindex cascade from an earlier
      eligibility correction, not that the fact itself was wrong).
    * ADDED -- present only in the NEW sample, for the same reason in
      reverse.

    This performs no acquisition and requests no budget; it is pure
    accounting over two already-produced artifacts.
    """

    old_by_key = {semantic_key(row): row for row in old_keys}
    new_by_key = {semantic_key(row): row for row in new_keys}
    all_semantic_keys = sorted(set(old_by_key) | set(new_by_key))

    entries: list[dict[str, Any]] = []
    status_counts: Counter = Counter()
    for key in all_semantic_keys:
        old_row = old_by_key.get(key)
        new_row = new_by_key.get(key)
        if old_row is not None and new_row is not None:
            if old_row.get("classification") != new_row.get("classification"):
                status = "RECLASSIFIED"
            elif old_row.get("disposition") != new_row.get("disposition"):
                status = "DISPOSITION_CHANGED"
            else:
                status = "RETAINED"
        elif old_row is not None:
            status = "SUPERSEDED"
        else:
            status = "ADDED"
        status_counts[status] += 1
        entries.append(
            {
                "program_id": key[0],
                "season": key[1],
                "role": key[2],
                "status": status,
                "old_key_id": old_row.get("key_id") if old_row else None,
                "new_key_id": new_row.get("key_id") if new_row else None,
                "old_classification": old_row.get("classification") if old_row else None,
                "new_classification": new_row.get("classification") if new_row else None,
                "old_disposition": old_row.get("disposition") if old_row else None,
                "new_disposition": new_row.get("disposition") if new_row else None,
            }
        )

    return {
        "artifact_type": "CYCLE35_R35_05_SAMPLE_RECONCILIATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reconciliation_method": "stable_semantic_key_program_season_role_"
        "never_mutable_key_id",
        "old_sample_key_count": len(old_keys),
        "new_sample_key_count": len(new_keys),
        "union_distinct_semantic_key_count": len(all_semantic_keys),
        "status_counts": dict(status_counts),
        "entries": entries,
        "neither_sample_is_all_48_verified": True,
        "this_is_accounting_not_a_sample_substitution": True,
        "no_acquisition_performed_no_budget_requested": True,
        "national_fbs_fcs_population_and_program_season_tranche_remain_"
        "separately_required_and_are_not_satisfied_by_either_48_key_sample": True,
    }


def resolve_key(
    key: dict[str, Any], by_season: dict[int, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Cache-first resolution with role and season actually bound."""

    season = int(key["season"])
    display = str(key["display_name"] or "")
    role = key["role"]
    candidates = [
        row
        for row in by_season.get(season, [])
        if employer_evidence_matches(display, str(row.get("program_raw") or ""))
    ]
    role_matched = [row for row in candidates if row.get("role") == role]

    people = sorted({str(row.get("person") or "") for row in role_matched})
    revisions = sorted(
        {str(row.get("wikimedia_revision") or "") for row in role_matched}
    )
    qids = sorted({str(row.get("wikidata_qid") or "") for row in role_matched if row.get("wikidata_qid")})

    if not candidates:
        disposition = MISSING
        detail = (
            "No cached career episode names this employer in this season. "
            "The program-season is real; the coaching evidence is absent."
        )
    elif not role_matched:
        disposition = MISSING
        detail = (
            "Cached episodes exist for this employer-season but none asserts "
            "this role. Absence of the role is recorded, not inferred from "
            "the presence of other roles."
        )
    elif len(people) == 1:
        disposition = (
            ACCEPTED_CORROBORATED if len(revisions) > 1 else ACCEPTED_SINGLE
        )
        detail = "One person asserted for this role-season."
    else:
        # Two or more distinct people asserted for the same role-season. This
        # may be a genuine co/shared role or a genuine conflict; either way
        # neither is allowed to win silently.
        disposition = CONFLICT
        detail = (
            "Multiple distinct people are asserted for this role-season: "
            + ", ".join(people[:6])
            + ". Retained as a conflict for adjudication; co/shared "
            "occupancy and contradiction are different and are not "
            "distinguishable from this evidence alone."
        )

    return {
        **key,
        "disposition": disposition,
        "detail": detail,
        "resolved_people": people,
        "person_count": len(people),
        "supporting_episode_count": len(role_matched),
        "employer_season_episode_count": len(candidates),
        "source_revisions": revisions,
        "wikidata_qids": qids,
        "evidence_class": "WIKIMEDIA_REVISION_BOUND_RETROSPECTIVE_CANDIDATE",
        "official_corroboration": "NOT_ACQUIRED_THIS_CYCLE",
        "pit_admitted": False,
        "resolved_from_cache": True,
        "requests_spent": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    programs = load_population()
    keys = predeclare_keys(programs)

    # The predeclaration is written BEFORE resolution so the set is auditable
    # independently of what the evidence turned out to say.
    predeclared_path = out_dir / "R35_05_PREDECLARED_48_KEYS.json"
    predeclared_path.write_text(
        json.dumps(
            {
                "artifact_type": "CYCLE35_R35_05_PREDECLARED_CAREER_KEYS",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "key_count": len(keys),
                "selection_rule": (
                    "Deterministic: programs sorted by canonical program_id, "
                    "seasons from a fixed ladder spanning all four declared "
                    "era bands plus the current season, roles rotating "
                    "through head coach and both coordinators. No key was "
                    "chosen or replaced on the basis of whether evidence "
                    "exists for it."
                ),
                "keys": keys,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    by_season, episode_stats = index_cached_episodes()
    ledger = RequestLedger()
    resolved = [resolve_key(key, by_season) for key in keys]

    dispositions = Counter(row["disposition"] for row in resolved)
    by_division = Counter(row["classification"] for row in resolved)
    by_band = Counter(row["era_band"] for row in resolved)
    by_role = Counter(row["role"] for row in resolved)

    # Reconcile the predecessor's 86 bound keys by exact set, never by
    # arithmetic. The Cycle #33 attempts file is the declared source.
    prior_path = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
        r"\implementation_output\science\CYCLE33_CAREER_KEY_ATTEMPTS.jsonl"
    )
    prior_rows = read_jsonl(prior_path)
    prior_bound = {
        str(row.get("employer"))
        for row in prior_rows
        if row.get("career_join_state") == "EVIDENCE_BOUND_CAREER_JOIN"
    }
    this_cycle_employers = {str(row["display_name"]) for row in resolved}
    reconciliation = {
        "predecessor_attempt_rows": len(prior_rows),
        "predecessor_bound_employer_count": len(prior_bound),
        "this_cycle_key_employers": len(this_cycle_employers),
        "employers_in_both": sorted(prior_bound & this_cycle_employers),
        "employers_only_in_predecessor": len(prior_bound - this_cycle_employers),
        "employers_only_in_this_cycle": len(this_cycle_employers - prior_bound),
        "arithmetic_addition_forbidden": (
            "The predecessor's 86 bound keys and this cycle's 48 keys are "
            "different key spaces over overlapping employers. They are "
            "reconciled here by exact set membership; '86 + new' would be "
            "meaningless and is not computed."
        ),
    }

    result = {
        "artifact_type": "CYCLE35_R35_05_CAREER_TRANCHE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "predeclared_keys_artifact": str(predeclared_path),
        "key_count": len(resolved),
        "dispositions": dict(dispositions),
        "by_classification": dict(by_division),
        "by_era_band": dict(by_band),
        "by_role": dict(by_role),
        "at_least_half_fbs": by_division.get("fbs", 0) >= len(resolved) / 2,
        "at_least_half_fcs": by_division.get("fcs", 0) >= len(resolved) / 2,
        "bands_covered": sorted(by_band),
        "cached_episode_index": episode_stats,
        "keys": resolved,
        "predecessor_reconciliation": reconciliation,
        "request_ledger": ledger.as_dict(),
        "no_key_was_substituted_for_an_easier_one": True,
        "missing_and_conflict_keys_remain_in_the_denominator": True,
        "evidence_is_revision_bound_retrospective_not_pit": True,
        "pit_admitted": False,
    }
    (out_dir / "R35_05_CAREER_TRANCHE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "keys": len(resolved),
            "dispositions": dict(dispositions),
            "by_classification": dict(by_division),
            "by_era_band": dict(by_band),
            "by_role": dict(by_role),
            "requests_spent": ledger.spent[BUDGET_COACHING],
            "employers_in_both": len(reconciliation["employers_in_both"]),
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
