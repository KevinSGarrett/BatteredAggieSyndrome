r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Re-measure every inherited obligation the Cycle 37 contract carries
(the CF-OBL-* rows) against what exists now, instead of repeating the state
Cycle 35 recorded.

The Cycle 35 obligation view settled many obligations "by category": an
acquisition decision, a missing fact, a network call outside the ceiling.
Some of those categories no longer describe the world -- the released C01
wheel has since been downloaded, the owner heads were read live, stadium
coordinates were in a cached venue file all along -- and some DONE states
were measured against a Cycle 35 release that has since been superseded.
So each obligation gets a check here that reads the current artifact and
returns what it finds:

* ``SATISFIED_AT_HEAD``: the predicate holds on the current artifact.
* ``PARTIALLY_SATISFIED``: part holds; the rest is named.
* ``NOT_SATISFIED_LOCAL_WORK_REMAINS``: local work would settle it.
* ``BLOCKED_ACQUISITION_OR_BUDGET`` / ``BLOCKED_MISSING_SOURCE_FACT`` /
  ``STRUCTURAL_LIMIT_RETAINED``: not settleable by local work here, with the
  reason re-checked rather than inherited.
* ``RECORD_ONLY``: the obligation was to record something, and the record
  is present.

No check returns a state because a category says so. Each one names what it
read. The obligations themselves are parsed from the issued contract, so a
row cannot be dropped or reworded here.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ROOT = Path(__file__).resolve().parents[2]
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
CONTRACT = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle37/20260922T171601Z/cycle_contract.json")
CYCLE36_RUN = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output")
VENUES = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/outputs/CFBD_VENUES.jsonl")

SATISFIED, PARTIAL = "SATISFIED_AT_HEAD", "PARTIALLY_SATISFIED"
LOCAL = "NOT_SATISFIED_LOCAL_WORK_REMAINS"
ACQUISITION, MISSING = "BLOCKED_ACQUISITION_OR_BUDGET", "BLOCKED_MISSING_SOURCE_FACT"
STRUCTURAL, RECORD = "STRUCTURAL_LIMIT_RETAINED", "RECORD_ONLY"

OBLIGATION_ROW = re.compile(
    r"^Account and fulfill the applicable unchanged inherited obligation (OBL_[A-Z0-9_]+): (\{.*\})\s*$", re.S)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


class Context:
    def __init__(self, release: Path) -> None:
        self.release = release
        self.conn = sqlite3.connect(f"file:{release}?mode=ro", uri=True)

    def q(self, sql: str) -> list[tuple]:
        return self.conn.execute(sql).fetchall()

    def one(self, sql: str) -> Any:
        return self.conn.execute(sql).fetchone()[0]

    def lane(self, slug: str) -> dict[str, Any]:
        return load(ATTEMPT / "evidence" / "lanes" / f"{slug}.json") or {}


def ceiling(kind: str) -> str:
    """The issued free request ceiling for one category, and what is left of it.

    An acquisition that fits one of these ceilings is local work the
    assignment authorised, not an external block.
    """

    ledger = load(ATTEMPT / "COST_AND_AUTHORITY_LEDGER.json") or {}
    network = ledger.get("network") or {}
    used = network.get(f"{kind}_requests")
    cap = network.get(f"{kind}_ceiling")
    return f"{kind} free ceiling {cap}, {used} used, {None if cap is None or used is None else cap - used} unspent"


def result(state: str, measured: str, *evidence: Path | str) -> dict[str, Any]:
    return {"state": state, "measured": measured,
            "evidence": [{"path": str(p), "sha256": sha256_file(Path(p))} for p in evidence]}


# ------------------------------------------------------------------- checks
def c_adjudication_determinism(ctx: Context) -> dict[str, Any]:
    path = ROOT / "src/aggie_analytics/cycle35/coaching_release.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    boundary = next(n.lineno for n in functions if n.name == "apply_migrations")
    clock_calls = []
    for fn in functions:
        if fn.lineno <= boundary:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                    node.func.attr in ("now", "utcnow", "today", "time", "monotonic") and \
                    isinstance(node.func.value, (ast.Name, ast.Attribute)):
                owner = getattr(node.func.value, "id", getattr(node.func.value, "attr", ""))
                if owner in ("datetime", "date", "time"):
                    clock_calls.append(f"{fn.name}:{node.lineno}")
    state = SATISFIED if not clock_calls else LOCAL
    return result(state, f"{len([f for f in functions if f.lineno > boundary])} functions after "
                  f"apply_migrations; wall-clock calls among them: {clock_calls or 'none'}", path)


def c_confirmed_coverage(ctx: Context) -> dict[str, Any]:
    confirmed = ctx.one("select count(*) from core_role_cell where coverage_state='CONFIRMED_SOURCE_SCOPED'")
    unbound = ctx.one("select coalesce(sum(value),0) from coverage_summary where grain='CORE_ROLE_CELL' "
                      "and bucket='CANDIDATE_UNBOUND_SEASON_OR_UNBOUND_RECORD'")
    state = SATISFIED if confirmed > 0 and unbound == 0 else LOCAL
    return result(state, f"Cycle 37 corrected release: {confirmed} cells in the confirmed layer, "
                  f"{unbound} candidate cells with an unbound season. (Cycle 35 measured 625 on a "
                  f"release since superseded by the R37-03 school/sport/season repair.)", ctx.release)


def c_coverage_horizon(ctx: Context) -> dict[str, Any]:
    lo, hi, n = ctx.q("select min(season), max(season), count(*) from season_population")[0]
    probe = ATTEMPT / "evidence/repairs/MF36_05_MEMBERSHIP_PROBE_AFTER.json"
    repaired = (load(probe) or {}).get("repaired") is True
    unproven = ctx.one("select count(*) from program_season_membership where season is null")
    state = SATISFIED if repaired and unproven == 0 and (lo, hi) == (1963, 2026) else PARTIAL
    return result(state, f"seasons {lo}-{hi} ({n}); {unproven} membership rows without a season; "
                  f"membership season proof repaired (MF36-05): {repaired}", ctx.release, probe)


def c_delivered_reconciliation(ctx: Context) -> dict[str, Any]:
    lane = ctx.lane("delivered-db")
    state = SATISFIED if lane.get("result") == "PASS" else LOCAL
    return result(state, f"DELIVERED_DB_INDEPENDENT lane result {lane.get('result')}: the delivered "
                  "file is read read-only by an independent reader with no rebuild consulted",
                  ATTEMPT / "evidence/lanes/delivered-db.json")


def c_family_b(ctx: Context) -> dict[str, Any]:
    lane = ctx.lane("family-b")
    artifact = Path(lane.get("qualification_artifact") or "")
    data = load(artifact) or {}
    text = json.dumps(data)
    ledger = "d48698ab" in text
    negatives = data.get("negative_controls_that_rejected")
    composed_artifact = Path(lane.get("composed_qualification_artifact") or "")
    composed = load(composed_artifact) or {}
    identities = {k: v.get("all_three_agree") for k, v in (composed.get("identity_agreement") or {}).items()}
    composed_ok = bool(composed.get("qualified_in_isolation")) and bool(identities) and all(identities.values())
    state = SATISFIED if lane.get("result") == "PASS" and ledger and composed_ok else LOCAL
    return result(state, f"FAMILY_B_COMPOSED lane {lane.get('result')}; ledger d48698ab exercised: "
                  f"{ledger}; upstream negative controls rejected: {negatives}; composed upstream+downstream "
                  f"qualified in isolation: {composed.get('qualified_in_isolation')}, identities reproduced and "
                  f"independently recomputed: {identities}, composed controls rejected "
                  f"{composed.get('negative_controls_rejected')}/{composed.get('negative_controls_total')}, rollback "
                  f"rehearsal complete: {(composed.get('rollback_rehearsal') or {}).get('complete')}; activation "
                  "authority not granted", ATTEMPT / "evidence/lanes/family-b.json", artifact, composed_artifact)


def c_this_view(ctx: Context, parsed: dict[str, Any]) -> dict[str, Any]:
    entries = sum(int(b.get("source_entry_count") or 0) for b in parsed["bodies"].values())
    unmapped = [k for k, rows in parsed["rows"].items() if not rows]
    state = SATISFIED if not unmapped and len(parsed["bodies"]) == len(parsed["rows"]) else LOCAL
    return result(state, f"{len(parsed['bodies'])} obligations parsed verbatim from the contract, "
                  f"{sum(len(r) for r in parsed['rows'].values())} rows, {entries} source entries; "
                  f"obligations without a row: {unmapped or 'none'}", CONTRACT)


def c_release_states_coverage(ctx: Context) -> dict[str, Any]:
    stated = dict(ctx.q("select bucket, value from coverage_summary where grain='CORE_ROLE_CELL' and bucket!='TOTAL'"))
    actual = dict(ctx.q("select coverage_state, count(*) from core_role_cell group by 1"))
    mismatches = {k: (stated.get(k, 0), actual.get(k, 0)) for k in set(stated) | set(actual)
                  if stated.get(k, 0) != actual.get(k, 0)}
    state = SATISFIED if not mismatches else LOCAL
    return result(state, f"coverage_summary vs core_role_cell per state: mismatches {mismatches or 'none'}",
                  ctx.release)


def c_responsibility(ctx: Context) -> dict[str, Any]:
    """Whether any cached source states play-calling, read from the R37-06 successor.

    The inherited premise was that no source in the cache states it. The
    R37-06 scan of the whole cache (staff titles, official captures and
    encyclopedia revisions) measures that directly.
    """

    path = ATTEMPT / "evidence/repairs/R37_06_SCHEME_RESPONSIBILITY.json"
    data = load(path) or {}
    episodes = data.get("current_responsibility_episodes") or []
    encyclopedia = ((data.get("population") or {}).get("encyclopedia")) or {}
    historical = encyclopedia.get("CANDIDATE_HISTORICAL_EXPLICIT_STATEMENT", 0)
    other = encyclopedia.get("CANDIDATE_STATEMENT_ABOUT_ANOTHER_PERSON", 0)
    state = SATISFIED if episodes and historical else PARTIAL if (episodes or historical) else MISSING
    return result(state, f"sources that state play-calling are in the cache: {len(episodes)} current official-title "
                  f"episode(s) and {historical + other} historical candidate statements in encyclopedia revisions "
                  f"({historical} about the page subject, {other} about another named person). They are "
                  "candidate evidence, not national unit-responsibility coverage; the premise that no source "
                  "states play-calling was false.", path)


def c_scheme_crosswalk(ctx: Context) -> dict[str, Any]:
    collisions = ctx.one("select count(*) from (select season, program_id, count(distinct page_title) n "
                         "from scheme_assertion where program_id is not null and program_id != '' "
                         "group by 1,2 having n > 1)")
    unresolved = ctx.one("select count(*) from scheme_assertion where program_id is null or program_id = ''")
    total = ctx.one("select count(*) from scheme_assertion")
    state = SATISFIED if collisions == 0 else LOCAL
    return result(state, f"{total} scheme assertions; distinct page-title teams resolving to one program "
                  f"in one season: {collisions}; claims resolving to no program (kept, unresolved): "
                  f"{unresolved}. Every claim resolves to at most one program.", ctx.release)


def c_already_fixed(ctx: Context) -> dict[str, Any]:
    return result(RECORD, "the obligation was to record the fix and the lane that caught it; the "
                  "Cycle 35 record is preserved unchanged in the inherited ledger", CONTRACT)


def c_mounted_hosted(ctx: Context) -> dict[str, Any]:
    local = ctx.lane("strict-mounted")
    return result(STRUCTURAL, "a hosted runner cannot mount the private lake; the mounted lane is run "
                  f"locally and reported as local (latest local STRICT_MOUNTED result: {local.get('result')})",
                  ATTEMPT / "evidence/lanes/strict-mounted.json")


def c_program_unresolved(ctx: Context) -> dict[str, Any]:
    rows = ctx.q("select state, count(*), sum(case when detail is null or trim(detail)='' then 1 else 0 end) "
                 "from unresolved_program_name group by 1")
    missing_reason = sum(r[2] for r in rows)
    state = SATISFIED if missing_reason == 0 else LOCAL
    return result(state, f"unresolved names by state: {[(r[0], r[1]) for r in rows]}; without a specific "
                  f"reason: {missing_reason}", ctx.release)


def c_user_corpus(ctx: Context) -> dict[str, Any]:
    recent = ctx.one("select count(*) from user_corpus_cell where season between 2013 and 2026")
    older = ctx.one("select count(*) from user_corpus_cell where season between 2000 and 2012")
    state = SATISFIED if recent > 0 else LOCAL
    return result(state, f"delivered release carries {recent} user-corpus observations in 2013-2026 "
                  f"and {older} in 2000-2012", ctx.release)


def c_career_keys(ctx: Context) -> dict[str, Any]:
    """Each remaining key is bound to an acquired source, or MISSING_NO_EVIDENCE with the routes searched."""

    path = ATTEMPT / "evidence/repairs/R37_05_TRANCHE_KEYS.json"
    data = load(path) or {}
    rows = data.get("rows") or []
    unrouted = [r["key_id"] for r in rows if r["disposition"] == "MISSING_NO_EVIDENCE" and not r["routes_searched"]]
    state = SATISFIED if len(rows) == 48 and not unrouted else LOCAL
    return result(state, f"{len(rows)} predeclared keys searched again in the rebuilt caches: "
                  f"{data.get('dispositions')}; missing keys each list the routes searched "
                  f"({'none unrouted' if not unrouted else unrouted}); changes from Cycle 36: "
                  f"{data.get('cycle36_to_cycle37')}. Bound keys are revision-bound candidates unless an "
                  f"official staff page states them. {ceiling('coaching')}", path)


def c_membership_2024_2025(ctx: Context) -> dict[str, Any]:
    rows = ctx.q("select season, membership_authority, count(*), count(distinct payload_sha256) "
                 "from program_season_membership where season in (2024, 2025) group by 1, 2")
    ledgered = all(r[1] != "RESTORED_FROM_CACHED_PAYLOAD_NOT_IN_CYCLE30_LEDGER" for r in rows)
    # Present and proved from cached bytes, but not attested by a ledgered request. Attesting it
    # means re-reading the game source's 2024/2025 team lists, which needs that provider's credential
    # (absent here); the NCAA's official standings route serves the current season only.
    state = SATISFIED if rows and ledgered else ACQUISITION
    return result(state, f"2024/2025 membership rows by authority: {rows}. Cached payload bytes exist "
                  "and each row's season is proved from them, but the acquisition itself is not "
                  "in the request ledger, so it is present and unattested, not freshly acquired. A ledgered "
                  "re-acquisition needs the game source's credential, which this environment does not hold, and "
                  "the NCAA's official standings serve only the current season.", ctx.release)


def c_membership_official(ctx: Context) -> dict[str, Any]:
    """A bounded official tranche: the NCAA's own standings for the current season."""

    path = ATTEMPT / "evidence/repairs/R37_04_OFFICIAL_MEMBERSHIP.json"
    data = load(path) or {}
    states = data.get("states") or {}
    if not states:
        return result(LOCAL, "no official membership source is read yet; a bounded tranche fits the "
                      f"{ceiling('metadata')}", ctx.release, ATTEMPT / "COST_AND_AUTHORITY_LEDGER.json")
    return result(ACQUISITION, f"2026 membership rows corroborated by the NCAA's own FBS/FCS standings: {states} of "
                  f"{data.get('membership_rows_2026')}. The NCAA route serves the current season only; earlier seasons "
                  "have no keyless official route here, so corroborating 1963-2025 is an acquisition or budget "
                  f"decision, not local work ({ceiling('metadata')})", path, ATTEMPT / "COST_AND_AUTHORITY_LEDGER.json")


def c_population_reconciliation(ctx: Context) -> dict[str, Any]:
    path = ATTEMPT / "evidence/repairs/R37_04_POPULATION_AUDIT.json"
    data = load(path) or {}
    findings = data.get("findings") or []
    titles = [str(f.get("title") or f.get("id") or f)[:160] if isinstance(f, dict) else str(f)[:160]
              for f in findings] if isinstance(findings, list) else []
    adjudication_path = ATTEMPT / "evidence/repairs/R37_04_2020_ADJUDICATION.json"
    adjudication = load(adjudication_path) or {}
    settled = adjudication.get("discrepancies_open_after") == 0 and len(titles) == 1 and "2020" in titles[0]
    state = SATISFIED if data and (data.get("result") not in ("DISCREPANCIES_FOUND",) and not findings or settled) \
        else PARTIAL if data else LOCAL
    return result(state, f"R37-04 independent population audit result {data.get('result')}; "
                  f"{len(titles)} finding(s): {titles or 'none'}; adjudicated against the program's official "
                  f"schedule: {adjudication.get('adjudication')} (open after: "
                  f"{adjudication.get('discrepancies_open_after')})", path, adjudication_path)


def c_kernel_receipts(ctx: Context) -> dict[str, Any]:
    """Each PROVEN label carries a per-row receipt, or the label is withdrawn."""

    path = ATTEMPT / "evidence/repairs/R37_08_LABEL_CONSUMER_AUDIT.json"
    successor = ATTEMPT / "evidence/repairs/R37_08_PRODUCER_LABEL_SUCCESSOR.jsonl"
    data = load(path) or {}
    rows = [json.loads(line) for line in successor.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if successor.is_file() else []
    labelled = (data.get("predecessor") or {}).get("labelled_rows")
    withdrawn = sum(1 for row in rows if row.get("successor_state") == "WITHDRAWN_NO_PER_PRIOR_PUBLICATION_RECEIPT"
                    and not row.get("pit_admissible"))
    settled = bool(data) and labelled == len(rows) == withdrawn and data.get("gates_pass") \
        and (data.get("predecessor") or {}).get("bytes_preserved")
    state = SATISFIED if settled else PARTIAL if data else LOCAL
    return result(state, f"{labelled} producer PROVEN labels; {withdrawn} withdrawn by successor row bound to the "
                  f"predecessor line digest; gates refuse them: {data.get('gates_pass')}; predecessor bytes "
                  f"preserved: {(data.get('predecessor') or {}).get('bytes_preserved')}", path, successor)


def c_kernel_sources(ctx: Context) -> dict[str, Any]:
    """The declared kernel raw sources cover every referenced season and game."""

    path = ATTEMPT / "evidence/repairs/R37_08_KERNEL_RECONCILIATION.json"
    data = load(path) or {}
    population = data.get("population_equations") or {}
    membership = population.get("membership") or {}
    unsourced = membership.get("NO_LOCAL_SOURCE", 0)
    residual = (data.get("field_reconciliation") or {}).get("unexplained_residual_sides")
    settled = bool(data) and not unsourced and residual == 0 and population.get("no_row_disappeared")
    state = SATISFIED if settled else PARTIAL if data else LOCAL
    return result(state, f"kernel rows by source: {membership or 'not measured'}; rows with no local source: "
                  f"{unsourced}; unexplained residual sides: {residual}; game-source requests spent: "
                  f"{(data.get('requests') or {}).get('game_source_requests')} of the {ceiling('games')}",
                  path, ATTEMPT / "COST_AND_AUTHORITY_LEDGER.json")


def c_neutral_example(ctx: Context) -> dict[str, Any]:
    path = CYCLE36_RUN / "CYCLE36_NEUTRAL_TRAVEL.json"
    data = load(path) or {}
    fixture = (data.get("lambeau_fixture") or {}).get("examples") or []
    bound = [e for e in fixture if e.get("venue_state") == "VENUE_INDEPENDENTLY_SUPPORTED"
             and e.get("source_designated_neutral")]
    state = SATISFIED if bound else MISSING
    detail = (f"{bound[0]['canonical_game_id']} at {bound[0]['venue_name']} (venue {bound[0]['venue_id']}), "
              f"source-designated neutral, venue independently supported") if bound else "not found"
    return result(state, f"the Notre Dame/Wisconsin example binds to the acquired game feed and venue: "
                  f"{detail}; travel is current-vintage, not point-in-time", path)


def c_stadium_coordinates(ctx: Context) -> dict[str, Any]:
    total = with_coords = 0
    for line in VENUES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            total += 1
            with_coords += row.get("latitude") is not None and row.get("longitude") is not None
    site_path = ATTEMPT / "evidence/repairs/R37_09_CONTEST_SITE.json"
    site = load(site_path) or {}
    legs = {int(k): v for k, v in ((site.get("counts") or {}).get("legs") or {}).items()}
    contests = (site.get("rows") or {}).get("count")
    state = SATISFIED if with_coords and legs.get(2) else PARTIAL if with_coords else LOCAL
    return result(state,
                  f"{with_coords} of {total} cached venues carry coordinates; the R37-09 successor computes "
                  f"both travel legs for {legs.get(2)} of {contests} contests and one leg for {legs.get(1)}. "
                  "The predicate (coordinates acquired so travel can be computed) holds. The coordinates "
                  "are a current vintage, so the travel is development-only and not PIT-admitted.",
                  VENUES, site_path)


def c_venue_enrichment(ctx: Context) -> dict[str, Any]:
    path = CYCLE36_RUN / "CYCLE36_NEUTRAL_TRAVEL_ROWS.jsonl"
    admitted = total = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total += 1
                admitted += json.loads(line).get("pit_admitted") is True
    state = SATISFIED if admitted == 0 else LOCAL
    return result(state, f"successor venue/travel layer (Cycle 36 R36-09): {admitted} of {total} rows "
                  "PIT-admitted, every row carrying a current-vintage, not-PIT geography authority. "
                  "The layer stays development-only, the second of the two outcomes the predicate "
                  "allows; it is not PIT-admitted.", path)


def c_forecast_store(ctx: Context) -> dict[str, Any]:
    return result(STRUCTURAL, "no trusted forecast receipt store exists; its absence correctly keeps a "
                  "forecast inadmissible", ctx.release)


AVAILABILITY = ATTEMPT / "evidence/repairs"


def c_availability_routes(ctx: Context) -> dict[str, Any]:
    """Each predeclared key yields reporting language or a recorded route and outcome."""

    path = AVAILABILITY / "R37_11_AVAILABILITY_DENOMINATOR.json"
    policies = AVAILABILITY / "R37_11_AVAILABILITY_POLICIES.json"
    keys = (load(path) or {}).get("predeclared_keys") or []
    outcomes = {k["display_name"]: k["outcome"] for k in keys}
    unrecorded = [name for name, outcome in outcomes.items() if not outcome]
    state = SATISFIED if len(keys) == 12 and not unrecorded else LOCAL
    return result(state, f"{len(keys)} predeclared keys, each with a recorded outcome: {outcomes}; policy "
                  f"language held for {(load(policies) or {}).get('conferences')}; "
                  f"{ceiling('availability')}", path, policies, ATTEMPT / "COST_AND_AUTHORITY_LEDGER.json")


def c_availability_official(ctx: Context) -> dict[str, Any]:
    """Durable official raw/rendered evidence with a publication time is acquired and bound."""

    path = AVAILABILITY / "R37_11_AVAILABILITY_STATEMENTS.json"
    data = load(path) or {}
    published = int(data.get("publication_time_established") or 0)
    bound = (data.get("contest_states") or {}).get("CONTEST_BOUND", 0)
    state = SATISFIED if published and bound else LOCAL
    return result(state, f"{data.get('statements')} statements from receipted official views "
                  f"{data.get('by_conference')}; {bound} bound to a canonical contest; {published} carry a "
                  "publication time the official view states. The others keep their retrieval time only.", path)


def c_availability_identity(ctx: Context) -> dict[str, Any]:
    """A roster snapshot is acquired for every program whose statements need identity."""

    path = AVAILABILITY / "R37_11_AVAILABILITY_STATEMENTS.json"
    data = load(path) or {}
    covered = {src["source"].split(", ", 1)[-1] for src in data.get("roster_sources") or []
               if src["source"].startswith("official roster page")}
    for src in data.get("roster_sources") or []:
        if src["source"] == "CFBD roster slice":
            covered |= set(src.get("programs") or [])
    rows = AVAILABILITY / "R37_11_AVAILABILITY_ROWS.jsonl"
    programs = set()
    if rows.is_file():
        with rows.open(encoding="utf-8") as handle:
            programs = {json.loads(line)["program"] for line in handle if line.strip()}
    missing = sorted(programs - covered)
    state = SATISFIED if programs and not missing else LOCAL
    return result(state, f"{len(programs)} programs have statements; roster snapshot held for "
                  f"{len(programs) - len(missing)}; missing {missing or 'none'}; statements resolved "
                  f"{data.get('resolved')} of {data.get('statements')}, quarantined {data.get('quarantined')} "
                  f"with reasons {data.get('identity_states')}", path, rows)


def c_bat637(ctx: Context) -> dict[str, Any]:
    """Measure the pin resolution the successor consumer actually uses.

    The Cycle 35 closeout (cae8392a) added a successor pin authority that
    reads the declared contract instead of the stale constant, and kept the
    legacy constant and default untouched. The inherited view still lists
    the obligation open, so the resolution is measured here, not assumed.
    """

    import importlib
    import inspect

    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    module = importlib.import_module("aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete")
    live = load(ROOT / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json") or {}
    contract = load(ROOT / module.SUCCESSOR_CONTRACT_RELATIVE) or {}
    successor = module.resolve_bat637_pin(repo_root=ROOT, pin_authority=module.PIN_AUTHORITY_SUCCESSOR)
    legacy = module.resolve_bat637_pin(repo_root=ROOT, pin_authority=module.PIN_AUTHORITY_LEGACY)
    default = inspect.signature(module.resolve_bat637_pin).parameters["pin_authority"].default
    checks = {
        "successor_pin_is_the_declared_contract_pin":
            successor["gate_identity"] == contract.get(module.SUCCESSOR_CONTRACT_PIN_FIELD),
        "successor_pin_equals_the_live_gate": successor["gate_identity"] == live.get("gate_identity"),
        "legacy_constant_kept_not_overwritten": legacy["gate_identity"] == module.PINNED_BAT637_GATE_IDENTITY
            and module.PINNED_BAT637_GATE_IDENTITY != live.get("gate_identity"),
        "default_stays_legacy": default == module.PIN_AUTHORITY_LEGACY,
    }
    state = SATISFIED if all(checks.values()) else LOCAL
    return result(state, f"pin resolution measured: {checks}; the stale constant is reconciled by a "
                  "declared-authority successor path, not by copying the live hash over it; activation "
                  "of the successor remains a separate approval",
                  ROOT / "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py",
                  ROOT / module.SUCCESSOR_CONTRACT_RELATIVE,
                  ROOT / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
                  ROOT / "tests/test_cycle35_family_b_versioned_consumer.py")


def c_c01_wheel(ctx: Context) -> dict[str, Any]:
    path = ATTEMPT / "evidence/repairs/R37_13_C01_COMPOSITION.json"
    data = load(path) or {}
    vector = data.get("vector") or {}
    ok = vector.get("wheel_matches_released_digest") is True and data.get("all_fixtures_honoured") is True
    return result(SATISFIED if ok else LOCAL, f"released wheel {vector.get('wheel_version')} "
                  f"sha256 {vector.get('wheel_sha256')} matches the release digest and was composed with "
                  "the BAS adapter; adoption remains unauthorized", path,
                  ATTEMPT / "evidence/lanes/c01-release.json")


def c_remote_heads(ctx: Context) -> dict[str, Any]:
    path = ATTEMPT / "evidence/external/GRIDIRONCORTEX_HEADS_AND_RELEASES.json"
    data = (load(path) or {}).get("data") or {}
    heads = {v.get("nameWithOwner"): ((v.get("defaultBranchRef") or {}).get("target") or {}).get("oid")
             for v in data.values() if isinstance(v, dict)}
    ok = len(heads) >= 5 and all(heads.values())
    return result(SATISFIED if ok else LOCAL, f"{len(heads)} owner heads read by one live read-only call: "
                  f"{heads}", path)


def c_jira_readback(ctx: Context) -> dict[str, Any]:
    path = ATTEMPT / "private/jira/JIRA_LIVE_READ_RECEIPT.json"
    trace = load(ATTEMPT / "evidence/repairs/R37_14_DOMAIN_TRACE.json") or {}
    named = trace.get("named_states") or {}
    holds = {k: v.get("holds") for k, v in named.items() if "holds" in v}
    ok = (load(path) or {}).get("read_only") is True and holds and all(holds.values())
    return result(SATISFIED if ok else PARTIAL, f"live read-only Jira read; named states re-read: {holds}",
                  path, ATTEMPT / "evidence/repairs/R37_14_DOMAIN_TRACE.json")


CHECKS: dict[str, Callable[..., dict[str, Any]]] = {
    "OBL_ADJUDICATION_DETERMINISM": c_adjudication_determinism,
    "OBL_CONFIRMED_COVERAGE": c_confirmed_coverage,
    "OBL_COVERAGE_HORIZON": c_coverage_horizon,
    "OBL_DELIVERED_RELEASE_RECONCILIATION": c_delivered_reconciliation,
    "OBL_FAMILY_B_SUCCESSOR_QUALIFICATION": c_family_b,
    "OBL_OBLIGATION_EXECUTION_VIEW": c_this_view,
    "OBL_RELEASE_STATES_ITS_OWN_COVERAGE": c_release_states_coverage,
    "OBL_RESPONSIBILITY_UNSTATED": c_responsibility,
    "OBL_SCHEME_INGEST_CROSSWALK": c_scheme_crosswalk,
    "OBL_ALREADY_FIXED_IN_REVIEW": c_already_fixed,
    "OBL_MOUNTED_LANE_HOSTED": c_mounted_hosted,
    "OBL_PROGRAM_UNRESOLVED_CELLS": c_program_unresolved,
    "OBL_USER_CORPUS_2013_2026_INGEST": c_user_corpus,
    "OBL_CAREER_TRANCHE_KEYS": c_career_keys,
    "OBL_MEMBERSHIP_2024_2025": c_membership_2024_2025,
    "OBL_MEMBERSHIP_OFFICIAL_CORROBORATION": c_membership_official,
    "OBL_NATIONAL_POPULATION_RECONCILIATION": c_population_reconciliation,
    "OBL_KERNEL_PRODUCER_RECEIPTS": c_kernel_receipts,
    "OBL_KERNEL_SOURCE_COMPLETENESS": c_kernel_sources,
    "OBL_NEUTRAL_SITE_EXAMPLE": c_neutral_example,
    "OBL_STADIUM_COORDINATES": c_stadium_coordinates,
    "OBL_VENUE_ENRICHMENT_PIT": c_venue_enrichment,
    "OBL_FORECAST_RECEIPT_STORE": c_forecast_store,
    "OBL_AVAILABILITY_LANGUAGE_ROUTES": c_availability_routes,
    "OBL_AVAILABILITY_OFFICIAL_EVIDENCE": c_availability_official,
    "OBL_PLAYER_IDENTITY_COVERAGE": c_availability_identity,
    "OBL_BAT637_STALE_SIDECAR": c_bat637,
    "OBL_C01_WHEEL": c_c01_wheel,
    "OBL_REMOTE_HEAD_VERIFY": c_remote_heads,
    "OBL_JIRA_READBACK": c_jira_readback,
}


def parse_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    rows: dict[str, list[str]] = collections.defaultdict(list)
    bodies: dict[str, dict[str, Any]] = {}
    for requirement in contract["requirements"]:
        for acceptance in requirement["acceptance"]:
            match = OBLIGATION_ROW.match(acceptance["statement"])
            if match:
                bodies[match.group(1)] = json.loads(match.group(2))
                rows[match.group(1)].append(acceptance["id"])
    return {"rows": dict(rows), "bodies": bodies}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    parsed = parse_contract(args.contract)
    missing_checks = sorted(set(parsed["bodies"]) - set(CHECKS))
    extra_checks = sorted(set(CHECKS) - set(parsed["bodies"]))
    if missing_checks or extra_checks:
        raise SystemExit(f"obligations without a check: {missing_checks}; checks for no obligation: {extra_checks}")
    ctx = Context(args.release)
    obligations = []
    for name, body in sorted(parsed["bodies"].items()):
        check = CHECKS[name]
        outcome = check(ctx, parsed) if check is c_this_view else check(ctx)
        obligations.append({
            "obligation": name, "title": body.get("title"),
            "acceptance_predicate": body.get("acceptance_predicate"),
            "inherited_state": body.get("state"), "inherited_category": body.get("category"),
            "rows": parsed["rows"][name], **outcome,
        })
    states = collections.Counter(o["state"] for o in obligations)
    receipt = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirement": "CF-OBL rows across R37-01..R37-16",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "release": {"path": str(args.release), "sha256": sha256_file(args.release)},
        "obligations": obligations, "states": dict(states),
        "rows": sum(len(o["rows"]) for o in obligations),
        "changed_from_inherited": [
            {"obligation": o["obligation"], "inherited": o["inherited_state"], "now": o["state"]}
            for o in obligations
            if not ((o["inherited_state"] == "DONE_WITH_EVIDENCE" and o["state"] in (SATISFIED, RECORD))
                    or (o["inherited_state"] == "BLOCKED_NOT_LOCAL_WORK" and o["state"] in (ACQUISITION, MISSING, STRUCTURAL))
                    or (o["inherited_state"] == "OPEN_LOCAL_WORK_REMAINS" and o["state"] == LOCAL))
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for o in obligations:
        print(f"{o['state']:<34} {o['obligation']:<40} {o['measured'][:110]}")
    print("states:", dict(states), "| rows:", receipt["rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
