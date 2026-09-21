"""R35-29 (Cycle #35 continuation, 20260921T055921Z), section 4.

"The inspected release has zero scheme and responsibility assertions. Before
treating these as source-unavailable, reconcile the declared predecessor
scheme/career/user-corpus caches and their ingest routes. Earlier cycles
produced scheme observations; check the actual artifacts rather than assuming
their existence proves correctness."

They did. `extract_cycle33_scheme_tenure.py` produced
CYCLE33_SCHEME_TENURE_CLAIMS.jsonl: 51,076 claims, of which 19,271 are
SCHEME and 9,111 carry text a source actually stated. The release reports
zero not because the evidence is missing but because nothing ever wrote to
the `scheme_assertion` table, which has existed since the schema was
written. That is an unwired route, not an evidence gap, and the two are
different dispositions with different fixes.

What this module will not do:

* It does not infer a scheme from a coach's reputation or from a
  coordinator's title. Only text a source stated is ingested.
* It does not promote anything above the layer its source warrants. Every
  cycle33 claim is WIKIPEDIA_ONLY_NOT_OFFICIAL and pit_admitted=false, so
  every row lands at the candidate layer and keeps that provenance.
* It does not resolve an ambiguous program. A claim whose Wikipedia page
  title matches no canonical program in that season, or matches more than
  one, is recorded unresolved with the reason -- never attached to the
  closest guess.
* It does not silence the three SCHEME_SOURCE_TEXT_CONFLICT claims. A
  conflict stays a conflict. They are counted over every stated claim AND
  over the resolved candidate rows, separately, because all three carry no
  stated season and so reach no candidate row -- a single count scoped to
  the resolved rows would report zero conflicts and read as though there
  were none.

AND YET NOTHING IS INGESTED HERE, because binding a claim to a canonical
program turns out to be the missing piece, not the ingest itself.

The claims key their program by Wikipedia page title ("2005 North Texas Mean
Green football team"). The canonical population keys by display name ("North
Texas"). No crosswalk between them exists in the cache, and the obvious
string rule -- strip the year and "football team", then require the
canonical name to be a unique token-prefix of what remains -- misattributes
across genuinely different schools:

    "Miami Hurricanes"          -> canonical "Miami"
    "Miami RedHawks"            -> canonical "Miami"     (a different school)
    "Texas A&M-Commerce Lions"  -> canonical "Texas"     (a different school)
    "Texas Longhorns"           -> canonical "Texas"

35 program-seasons collide that way. Worse, collision detection only catches
the pairs that happen to appear together: in a season carrying Texas
A&M-Commerce but not Texas, "Texas A&M-Commerce Lions" resolves to a single
canonical "Texas" and would be ingested SILENTLY WRONG. A rule whose failures
are invisible cannot be made safe by counting the visible ones.

So this module measures and refuses. It reports how much evidence exists,
how much a crosswalk would recover, and the exact collisions, and it emits
no scheme_assertion row. The remaining work is a real page-title-to-program
crosswalk; the acceptance predicate is that it resolves titles with zero
many-to-one bindings across distinct schools.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.career_identity import (  # noqa: E402
    employer_evidence_matches,
)

SCHEME_CLAIMS = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs")
    / "20260914T130736Z"
    / "implementation_output"
    / "science"
    / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"
)

#: The disposition the extractor gives a field the page left empty. An empty
#: infobox field is not a scheme; it is the absence of one.
BLANK = "BLANK_NOT_CAPTURED"
CONFLICT = "SCHEME_SOURCE_TEXT_CONFLICT"

SIDE_BY_FIELD = {"offensive_scheme": "OFFENSE", "defensive_scheme": "DEFENSE"}

RESOLVED = "RESOLVED_SINGLE_CANONICAL_PROGRAM"
UNRESOLVED_NONE = "UNRESOLVED_NO_CANONICAL_PROGRAM_IN_THAT_SEASON"
UNRESOLVED_MANY = "UNRESOLVED_MORE_THAN_ONE_CANONICAL_PROGRAM_MATCHES"


PAGE_TITLE = re.compile(r"^(?P<year>\d{4})\s+(?P<team>.+?)\s+football\s+team$", re.I)


def team_from_page_title(title: str) -> str | None:
    """"2005 North Texas Mean Green football team" -> "North Texas Mean Green"."""

    match = PAGE_TITLE.match(str(title or "").strip())
    return match.group("team") if match else None


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(t for t in re.split(r"\s+", str(value).strip().casefold()) if t)


def token_prefix(canonical: str, team: str) -> bool:
    """Whether a canonical name is a leading token run of a team name.

    This is the rule the measurement showed to be UNSAFE on its own -- it
    binds "Texas A&M-Commerce Lions" to "Texas". It is kept only so the
    reconciliation can quantify what a real crosswalk would recover, and its
    results are never ingested.
    """

    left, right = _tokens(canonical), _tokens(team)
    return bool(left) and right[: len(left)] == left


def read_claims(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def scheme_claims_with_content(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """SCHEME claims whose source actually stated something."""

    return [
        claim
        for claim in claims
        if claim.get("claim_kind") == "SCHEME"
        and claim.get("disposition") != BLANK
        and str(claim.get("source_text") or "").strip()
    ]


def resolve_program(
    claim: dict[str, Any], programs_by_season: dict[int, list[dict[str, Any]]]
) -> dict[str, Any]:
    """One canonical program, or an honest refusal.

    `program_raw` is a Wikipedia page title such as "2005 North Texas Mean
    Green football team". Matching is delegated to the career-identity
    matcher so scheme and career resolution cannot drift apart.
    """

    try:
        season = int(str(claim.get("season") or ""))
    except ValueError:
        return {"state": UNRESOLVED_NONE, "program_id": None, "season": None}

    raw = str(claim.get("program_raw") or "")
    team = team_from_page_title(raw)
    if team is None:
        return {"state": UNRESOLVED_NONE, "program_id": None, "season": season}
    # employer_evidence_matches expects an employer name, not a page title,
    # and correctly rejects "2005 North Texas Mean Green football team".
    # The page title is reduced to its team name first; the match is still
    # delegated so scheme and career resolution cannot drift apart.
    matches = [
        program
        for program in programs_by_season.get(season, [])
        if employer_evidence_matches(str(program.get("display_name") or ""), team)
        or token_prefix(str(program.get("display_name") or ""), team)
    ]
    distinct = sorted({str(p.get("program_id")) for p in matches})
    if len(distinct) == 1:
        return {"state": RESOLVED, "program_id": distinct[0], "season": season}
    if not distinct:
        return {"state": UNRESOLVED_NONE, "program_id": None, "season": season}
    return {
        "state": UNRESOLVED_MANY,
        "program_id": None,
        "season": season,
        "candidates": distinct[:8],
    }


def prepare(
    claims_path: Path, programs_by_season: dict[int, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Resolve every stated scheme claim without writing anything."""

    claims = read_claims(claims_path)
    stated = scheme_claims_with_content(claims)

    rows: list[dict[str, Any]] = []
    states: Counter = Counter()
    unresolved_examples: list[dict[str, Any]] = []
    for claim in stated:
        resolution = resolve_program(claim, programs_by_season)
        states[resolution["state"]] += 1
        if resolution["state"] != RESOLVED:
            if len(unresolved_examples) < 20:
                unresolved_examples.append(
                    {
                        "program_raw": claim.get("program_raw"),
                        "season": claim.get("season"),
                        "state": resolution["state"],
                        "candidates": resolution.get("candidates"),
                    }
                )
            continue
        normalized = claim.get("normalized")
        if isinstance(normalized, list):
            normalized = ";".join(str(item) for item in normalized) or None
        rows.append(
            {
                "program_id": resolution["program_id"],
                "season": str(resolution["season"]),
                "side": SIDE_BY_FIELD.get(str(claim.get("field")), "OFFENSE"),
                "exact_source_text": str(claim["source_text"]),
                "normalized_family": normalized,
                "normalization_version": str(
                    claim.get("normalization_version") or "UNVERSIONED"
                ),
                "is_source_text_conflict": claim.get("disposition") == CONFLICT,
                "page_title": claim.get("page_title"),
                "wikimedia_revision": claim.get("wikimedia_revision"),
                "official_corroboration": claim.get("official_corroboration"),
                "pit_admitted": claim.get("pit_admitted"),
            }
        )

    # Two DIFFERENT schools resolving to one canonical program is a
    # misattribution, not a duplicate. Detect it, and note that detection is
    # only possible when both collide in the same season.
    by_target: dict[tuple[str, str], set] = {}
    for row in rows:
        by_target.setdefault((row["season"], row["program_id"]), set()).add(
            team_from_page_title(str(row.get("page_title") or "")) or ""
        )
    collisions = [
        {
            "season": season,
            "program_id": program_id,
            "distinct_page_teams": sorted(teams),
        }
        for (season, program_id), teams in sorted(by_target.items())
        if len(teams) > 1
    ]

    return {
        "claims_total": len(claims),
        "scheme_claims": sum(1 for c in claims if c.get("claim_kind") == "SCHEME"),
        "scheme_claims_with_stated_text": len(stated),
        "resolution_states": dict(states),
        "candidate_rows": rows,
        "unresolved_examples": unresolved_examples,
        # Scoped to the rows that RESOLVED. Reported beside the count over
        # every stated claim, because on its own a 0 here reads as "there
        # were no conflicts" when it means "none of them resolved".
        "source_text_conflicts_in_candidate_rows": sum(
            1 for r in rows if r["is_source_text_conflict"]
        ),
        "source_text_conflicts_in_stated_claims": sum(
            1 for claim in claims if claim.get("disposition") == CONFLICT
        ),
        "source_text_conflicts_without_a_stated_season": sum(
            1
            for claim in claims
            if claim.get("disposition") == CONFLICT and not claim.get("season")
        ),
        "program_collisions": collisions,
    }


def summary(prepared: dict[str, Any]) -> dict[str, Any]:
    rows = prepared["candidate_rows"]
    collisions = prepared["program_collisions"]
    return {
        "artifact_type": "CYCLE35_SCHEME_INGEST_RECONCILIATION",
        "rows_ingested": 0,
        "ingest_refused": True,
        "why_ingest_is_refused": (
            "Binding a claim to a canonical program is the missing piece, not "
            "the ingest. The claims key by Wikipedia page title and the "
            "canonical population keys by display name, with no crosswalk "
            "between them in the cache. The obvious string rule binds "
            f"'Texas A&M-Commerce Lions' to 'Texas' and both Miami schools to "
            f"one program; {len(collisions)} program-seasons collide that way. "
            "Collision detection only catches pairs that appear together, so "
            "a season carrying one of them alone would resolve silently "
            "wrong. A rule whose failures are invisible is not made safe by "
            "counting the visible ones."
        ),
        "program_collisions": collisions,
        "program_collision_count": len(collisions),
        "remaining_work": (
            "A page-title-to-canonical-program crosswalk. Acceptance "
            "predicate: every stated scheme claim resolves to at most one "
            "canonical program, and no two distinct page-title teams in a "
            "season resolve to the same one."
        ),
        "candidate_rows_if_a_crosswalk_existed": len(rows),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_claims": str(SCHEME_CLAIMS),
        "claims_total": prepared["claims_total"],
        "scheme_claims": prepared["scheme_claims"],
        "scheme_claims_with_stated_text": prepared["scheme_claims_with_stated_text"],
        "resolution_states": prepared["resolution_states"],
        "rows_by_side": dict(Counter(r["side"] for r in rows)),
        "distinct_programs": len({r["program_id"] for r in rows}),
        "season_span": (
            [min(r["season"] for r in rows), max(r["season"] for r in rows)]
            if rows
            else None
        ),
        "source_text_conflicts_in_stated_claims": prepared[
            "source_text_conflicts_in_stated_claims"
        ],
        "source_text_conflicts_in_candidate_rows": prepared[
            "source_text_conflicts_in_candidate_rows"
        ],
        "why_no_conflict_reaches_a_candidate_row": (
            "All "
            + str(prepared["source_text_conflicts_without_a_stated_season"])
            + " of the SCHEME_SOURCE_TEXT_CONFLICT claims carry no stated "
            "season, so they resolve to no program-season and cannot appear "
            "among the candidate rows. They are unresolved, not absent, and "
            "not silenced: a count scoped to the resolved rows alone would "
            "have reported zero conflicts and read as though there were none."
        ),
        "unresolved_examples": prepared["unresolved_examples"],
        "evidence_layer": "CANDIDATE_SINGLE_SOURCE",
        "why_candidate_only": (
            "Every cycle33 scheme claim is WIKIPEDIA_ONLY_NOT_OFFICIAL with "
            "pit_admitted=false, reported_not_observed_film=true and "
            "not_play_calling=true. Ingesting them changes what the release "
            "can be asked; it does not make any of them official, PIT, or a "
            "statement about who called plays."
        ),
        "zero_was_an_unwired_route_not_an_evidence_gap": (
            "The scheme_assertion table has existed since the schema was "
            "written and nothing wrote to it. The packet recorded the "
            "resulting zero as RETAINED_AS_EVIDENCE_GAP, which named the "
            "wrong cause and so pointed at the wrong fix."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheme ingest reconciliation.")
    parser.add_argument("--claims", type=Path, default=SCHEME_CLAIMS)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from r35_05_career_tranche import load_population  # noqa: E402

    programs = load_population()
    by_season: dict[int, list[dict[str, Any]]] = {}
    for program_id, entry in programs.items():
        for season in entry.get("seasons") or []:
            by_season.setdefault(int(season), []).append(
                {"program_id": program_id, "display_name": entry.get("display_name")}
            )

    prepared = prepare(args.claims, by_season)
    result = summary(prepared)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "CYCLE35_SCHEME_INGEST.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({k: v for k, v in result.items() if k != "unresolved_examples"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
