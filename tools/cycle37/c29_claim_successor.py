"""Cycle #37 — Attempt #3 — versioned successor to the Cycle 29 claim inventory.

W37R-71 / R37A03-06. The committed ``CYCLE29_CLAIM_INVENTORY.json`` is a
historical receipt and stays byte-for-byte unchanged. This tool writes a
separate, versioned successor that inventories the numeric claims the
original never declared:

* the 35 (artifact, field) pairs the repaired validator reports, and
* 3 further pairs the repaired validator cannot see, because it matches
  declared claims by field name only and a same-named claim in another
  artifact hides them.

Each claim is addressed by exact JSON pointer and artifact digest, given a
meaning, and classified by an independent recomputation run here from
bytes, never by restating the producer:

``EVIDENCE_BACKED``
    recomputed exactly from rows or lists of declared, hash-verified Cycle 29
    artifacts (or derived exactly from other declared claims, which are then
    named as dependencies);
``RECONSTRUCTED``
    recomputed exactly from retained bytes outside the declared artifact set
    (raw payloads, the predecessor canonical payload, an undeclared external
    output, a producer fixture literal), each bound by path and SHA-256;
``UNSUPPORTED``
    no retained bytes re-derive the value;
``CONTRADICTED``
    the recomputation disagrees with the recorded value.

Every numeric value the independent census found is accounted for exactly
once. An inventory that is complete is not evidence that its numbers are
scientifically true, and this bounded tranche is not a Cycle 1-36 audit.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

SUCCESSOR_VERSION = "BAS-C29-CLAIM-INVENTORY-SUCCESSOR-v1"
TOOL_VERSION = "BAS-C29-CLAIM-SUCCESSOR-TOOL-v37.3"

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "scientific_integrity" / "cycle29"
EXTERNAL = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\outputs")
GAMES_PAYLOAD = Path(
    r"C:\BatteredAggieSyndrome.data\canonical\national_foundation_reconciliation\sha256"
    r"\d2af2bab981f8e7b33a6823e3e4b4b65eb2f96593a0eeafd56dedce1b84fd477"
    r"\national_normalized_games.jsonl"
)
#: The digest the Cycle 28 manager deep audit recorded for that payload
#: (ops/cycle29/CYCLE28_MANAGER_DEEP_AUDIT.md, line 79).
GAMES_PAYLOAD_AUDITED_SHA256 = "8ac949ef3ecbdbc560bb8080e2f302cbd000ab96437dfafef9f1a14165d1c574"
RAW_CYCLE29 = Path(r"C:\BatteredAggieSyndrome.data\raw\CYCLE29")
INVENTORY = "CYCLE29_CLAIM_INVENTORY.json"
#: Files the repaired validator deliberately does not scan.
VALIDATOR_SKIP = {
    "CYCLE29_CLAIM_INVENTORY.json",
    "CYCLE29_MATERIALIZATION_MANIFEST.json",
    "CYCLE29_PREFLIGHT_AND_PRESERVATION.json",
}

EVIDENCE_BACKED = "EVIDENCE_BACKED"
RECONSTRUCTED = "RECONSTRUCTED"
UNSUPPORTED = "UNSUPPORTED"
CONTRADICTED = "CONTRADICTED"
CLASSES = (EVIDENCE_BACKED, RECONSTRUCTED, UNSUPPORTED, CONTRADICTED)

MISSOURI_STATE_SOURCE_TEAM_ID = 2623


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


class Context:
    """Every input a recomputation may read, each bound by digest once."""

    def __init__(self, art: Path, external: Path, games: Path, raw: Path) -> None:
        self.art = art
        self.external = external
        self.games_path = games
        self.raw = raw
        self.inputs: dict[str, dict[str, Any]] = {}
        self._docs: dict[str, Any] = {}
        self._jsonl: dict[str, list[Any]] = {}
        self._games: list[dict[str, Any]] | None = None
        manifest = json.loads((art / "CYCLE29_MATERIALIZATION_MANIFEST.json").read_text(encoding="utf-8"))
        self.manifest: dict[str, str] = manifest["file_hashes"]

    def bind(self, label: str, path: Path, *, expected: str | None = None) -> bytes:
        data = path.read_bytes()
        digest = sha256_bytes(data)
        self.inputs[label] = {
            "path": str(path),
            "sha256": digest,
            "bytes": len(data),
            "expected_sha256": expected,
            "matches_expected": None if expected is None else digest == expected,
        }
        return data

    def doc(self, name: str) -> Any:
        if name not in self._docs:
            data = self.bind(f"artifact:{name}", self.art / name, expected=self.manifest.get(name))
            self._docs[name] = json.loads(data.decode("utf-8"))
        return self._docs[name]

    def jsonl(self, name: str) -> list[Any]:
        if name not in self._jsonl:
            data = self.bind(f"external:{name}", self.external / name, expected=self.manifest.get(name))
            self._jsonl[name] = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        return self._jsonl[name]

    def games(self) -> list[dict[str, Any]]:
        if self._games is None:
            data = self.bind("predecessor:national_normalized_games.jsonl", self.games_path,
                             expected=GAMES_PAYLOAD_AUDITED_SHA256)
            self._games = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        return self._games

    def raw_payload(self, target: str, digest: str) -> bytes:
        return self.bind(f"raw:{target}:{digest[:12]}", self.raw / target / f"{digest}.html", expected=digest)

    def literal(self, relative: str, pattern: str) -> dict[str, Any]:
        """Locate a producer literal and bind the source file that holds it."""

        path = ROOT / relative
        data = self.bind(f"producer:{relative}", path)
        text = data.decode("utf-8")
        match = re.search(pattern, text)
        return {
            "path": relative,
            "sha256": sha256_bytes(data),
            "pattern": pattern,
            "found": bool(match),
            "line": None if not match else text.count("\n", 0, match.start()) + 1,
        }


def resolve(document: Any, pointer: str) -> Any:
    node = document
    if pointer == "":
        return node
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


# ------------------------------------------------------------ claim table

Recompute = Callable[[Context, list[str]], dict[str, Any]]
CLAIMS: dict[tuple[str, str], dict[str, Any]] = {}


def claim(artifact: str, field: str, *, meaning: str, unit: str, population: str) -> Callable[[Recompute], Recompute]:
    def register(function: Recompute) -> Recompute:
        CLAIMS[(artifact, field)] = {
            "meaning": meaning, "unit": unit, "population": population, "recompute": function,
        }
        return function
    return register


def same(value: Any, pointers: list[str]) -> dict[str, Any]:
    return {pointer: value for pointer in pointers}


# BAS_CANONICAL_DOMAIN_CATALOG.json -------------------------------------------

@claim("BAS_CANONICAL_DOMAIN_CATALOG.json", "canonical_domain_count",
       meaning="Number of canonical BAS domains the Cycle 29 catalog defines (52 data domains and "
               "4 non-data control domains).",
       unit="domains", population="Cycle 29 canonical BAS domain catalog")
def _canonical_domains(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    domains = ctx.doc("BAS_CANONICAL_DOMAIN_CATALOG.json")["domains"]
    distinct = {row["canonical_domain_id"] for row in domains}
    kinds = collections.Counter(row["kind"] for row in domains)
    return {"class": EVIDENCE_BACKED, "basis": "COUNT_OF_THE_ARTIFACTS_OWN_DOMAIN_ROWS",
            "recomputed": same(len(distinct) if len(distinct) == len(domains) else None, pointers),
            "evidence": {"domain_rows": len(domains), "distinct_domain_ids": len(distinct),
                         "by_kind": dict(sorted(kinds.items()))}}


# BAS_DOMAIN_CATALOG_CROSSWALK.json -------------------------------------------

def _crosswalk(ctx: Context) -> list[dict[str, Any]]:
    return ctx.doc("BAS_DOMAIN_CATALOG_CROSSWALK.json")["mappings"]


def _catalog_count(catalog: str) -> Recompute:
    def recompute(ctx: Context, pointers: list[str]) -> dict[str, Any]:
        rows = _crosswalk(ctx)
        count = sum(1 for row in rows if row["predecessor_catalog"] == catalog)
        return {"class": EVIDENCE_BACKED, "basis": "COUNT_OF_THE_ARTIFACTS_OWN_MAPPING_ROWS",
                "recomputed": same(count, pointers),
                "evidence": {"predecessor_catalog": catalog, "mapping_rows": len(rows),
                             "by_catalog": dict(sorted(collections.Counter(
                                 row["predecessor_catalog"] for row in rows).items()))}}
    return recompute


for _field, _catalog, _meaning in (
    ("w06_term_count", "W06_52", "the W06 52-domain predecessor catalog"),
    ("c28_term_count", "C28_33", "the Cycle 28 33-term predecessor catalog"),
    ("pit_term_count", "PIT_18", "the 18-term PIT vocabulary"),
    ("source_policy_term_count", "SOURCE_POLICY_16", "the 16-term source-policy vocabulary"),
):
    claim("BAS_DOMAIN_CATALOG_CROSSWALK.json", _field,
          meaning=f"Number of crosswalk rows mapping a term of {_meaning} to a canonical BAS domain.",
          unit="predecessor terms", population="Cycle 29 domain-catalog crosswalk rows")(_catalog_count(_catalog))


@claim("BAS_DOMAIN_CATALOG_CROSSWALK.json", "mapping_count",
       meaning="Total crosswalk rows, one per predecessor term across all four predecessor vocabularies.",
       unit="mapping rows", population="Cycle 29 domain-catalog crosswalk rows")
def _mapping_count(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    rows = _crosswalk(ctx)
    return {"class": EVIDENCE_BACKED, "basis": "COUNT_OF_THE_ARTIFACTS_OWN_MAPPING_ROWS",
            "recomputed": same(len(rows), pointers), "evidence": {"mapping_rows": len(rows)}}


@claim("BAS_DOMAIN_CATALOG_CROSSWALK.json", "unmapped_term_count",
       meaning="Crosswalk rows whose predecessor term reaches no canonical domain of the catalog "
               "(state neither MAPPED nor NON_DATA_CONTROL, or a domain id the catalog lacks).",
       unit="predecessor terms", population="Cycle 29 domain-catalog crosswalk rows")
def _unmapped(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    rows = _crosswalk(ctx)
    catalog = {row["canonical_domain_id"] for row in ctx.doc("BAS_CANONICAL_DOMAIN_CATALOG.json")["domains"]}
    unmapped = [row for row in rows
                if row["state"] not in ("MAPPED", "NON_DATA_CONTROL") or row["canonical_domain_id"] not in catalog]
    return {"class": EVIDENCE_BACKED, "basis": "CROSSWALK_ROWS_CHECKED_AGAINST_THE_DECLARED_CATALOG",
            "recomputed": same(len(unmapped), pointers),
            "evidence": {"states": dict(sorted(collections.Counter(row["state"] for row in rows).items())),
                         "rows_with_a_domain_absent_from_the_catalog":
                             sum(1 for row in rows if row["canonical_domain_id"] not in catalog)}}


@claim("BAS_DOMAIN_CATALOG_CROSSWALK.json", "ambiguous_unresolved_mapping_count",
       meaning="Predecessor terms mapped to more than one canonical domain, or left in an "
               "ambiguous/unresolved state.",
       unit="predecessor terms", population="Cycle 29 domain-catalog crosswalk rows")
def _ambiguous(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    rows = _crosswalk(ctx)
    targets: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for row in rows:
        targets[(row["predecessor_catalog"], row["predecessor_term"])].add(row["canonical_domain_id"])
    multi = [key for key, value in targets.items() if len(value) > 1]
    flagged = [row for row in rows if re.search("AMBIG|UNRESOLV", row["state"])]
    return {"class": EVIDENCE_BACKED, "basis": "CROSSWALK_ROWS_GROUPED_BY_PREDECESSOR_TERM",
            "recomputed": same(len(multi) + len(flagged), pointers),
            "evidence": {"terms_with_several_domains": len(multi), "ambiguous_state_rows": len(flagged),
                         "distinct_predecessor_terms": len(targets)}}


# COACHING_COVERAGE_AND_RIGHTS_GATE.json --------------------------------------

@claim("COACHING_COVERAGE_AND_RIGHTS_GATE.json", "W",
       meaning="Number of distinct Week 1 2026 programs (display-name identities, not canonical "
               "program ids) the coaching gate's HC/OC/DC matrix covers.",
       unit="programs", population="Week 1 2026 slice programs")
def _gate_w(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    matrix = ctx.jsonl("WEEK1_2026_HC_OC_DC_ROLE_MATRIX.jsonl")
    programs = {row["program_id"] for row in matrix}
    slice_programs = set(ctx.doc("WEEK1_2026_PROGRAM_SLICE.json")["programs"])
    return {"class": EVIDENCE_BACKED, "basis": "DISTINCT_PROGRAMS_OF_THE_DECLARED_ROLE_MATRIX_AND_SLICE",
            "recomputed": same(len(programs) if programs == slice_programs else None, pointers),
            "evidence": {"matrix_programs": len(programs), "slice_programs": len(slice_programs),
                         "same_program_set": programs == slice_programs}}


@claim("COACHING_COVERAGE_AND_RIGHTS_GATE.json", "week1_cells",
       meaning="Number of Week 1 2026 program-role cells in the HC/OC/DC matrix (one head coach, "
               "offensive coordinator and defensive coordinator cell per program); cells, not "
               "confirmed coaches.",
       unit="program-role cells", population="Week 1 2026 slice programs x {HC, OC, DC}")
def _gate_cells(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    matrix = ctx.jsonl("WEEK1_2026_HC_OC_DC_ROLE_MATRIX.jsonl")
    keys = {(row["program_id"], row["role"]) for row in matrix}
    return {"class": EVIDENCE_BACKED, "basis": "ROW_COUNT_OF_THE_DECLARED_ROLE_MATRIX",
            "recomputed": same(len(matrix) if len(keys) == len(matrix) else None, pointers),
            "evidence": {"matrix_rows": len(matrix), "distinct_program_role_cells": len(keys),
                         "by_role": dict(sorted(collections.Counter(row["role"] for row in matrix).items())),
                         "confirmed_cells": sum(1 for row in matrix if row.get("episode_cardinality"))}}


# CYCLE29_FINDING_SUCCESSOR_LEDGER.json ---------------------------------------

@claim("CYCLE29_FINDING_SUCCESSOR_LEDGER.json", "p0_count",
       meaning="Number of top-level Cycle 28 P0 findings (C28-P0-01 to C28-P0-12) the successor "
               "ledger carries; the 11a/11b/11c sub-rows are not counted separately.",
       unit="findings", population="Cycle 28 P0 finding identifiers")
def _p0(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    ledger = ctx.doc("CYCLE29_FINDING_SUCCESSOR_LEDGER.json")
    top = {row["finding_id"] for row in ledger["rows"] if re.fullmatch(r"C28-P0-\d\d", row["finding_id"])}
    preserved = set(ledger["p0_ids_preserved"])
    return {"class": EVIDENCE_BACKED, "basis": "COUNT_OF_THE_LEDGERS_OWN_TOP_LEVEL_P0_ROWS",
            "recomputed": same(len(top) if top == preserved else None, pointers),
            "evidence": {"top_level_p0_rows": sorted(top), "p0_ids_preserved_equal": top == preserved,
                         "all_p0_prefixed_rows": sum(1 for row in ledger["rows"]
                                                     if row["finding_id"].startswith("C28-P0-"))}}


# CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json ------------------------

WEEK1_FINAL = "CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json"


def _acquisition(ctx: Context, pointer: str) -> dict[str, Any]:
    index = int(pointer.split("/")[2])
    return ctx.doc(WEEK1_FINAL)["acquisitions"][index]


@claim(WEEK1_FINAL, "bytes",
       meaning="Size in bytes of each retained raw capture (scoreboard or contest page) the Week 1 "
               "official-final successor acquired.",
       unit="bytes", population="Cycle 29 remaining Week 1 acquisitions")
def _week1_bytes(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    recomputed, evidence = {}, []
    for pointer in pointers:
        acquisition = _acquisition(ctx, pointer)
        data = ctx.raw_payload(acquisition["target_id"], acquisition["raw_sha256"])
        verified = sha256_bytes(data) == acquisition["raw_sha256"]
        recomputed[pointer] = len(data) if verified else None
        evidence.append({"pointer": pointer, "target_id": acquisition["target_id"],
                         "raw_sha256": acquisition["raw_sha256"], "raw_bytes_verified": verified})
    return {"class": RECONSTRUCTED, "basis": "LENGTH_OF_THE_RETAINED_RAW_PAYLOAD_WITH_THE_RECORDED_DIGEST",
            "recomputed": recomputed, "evidence": {"payloads": evidence}}


@claim(WEEK1_FINAL, "http_status",
       meaning="HTTP status the acquisition route reported for each capture.",
       unit="HTTP status code", population="Cycle 29 remaining Week 1 acquisitions")
def _week1_status(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    retained = []
    for pointer in pointers:
        acquisition = _acquisition(ctx, pointer)
        directory = ctx.raw / acquisition["target_id"]
        retained.append({"pointer": pointer, "target_id": acquisition["target_id"],
                         "retained_files": sorted(path.name for path in directory.iterdir())
                         if directory.is_dir() else []})
    return {"class": UNSUPPORTED, "basis": "TRANSPORT_METADATA_NOT_RETAINED",
            "recomputed": {}, "evidence": {
                "searched": retained,
                "reason": "Only the response bodies are retained, named by their digest. No transport "
                          "receipt holding the status line was retained, and a status cannot be "
                          "re-derived from a body."}}


def _team_scores_from_scoreboard(html: str, team_ids: list[str]) -> dict[str, int | None]:
    """Score beside each team on the NCAA scoreboard, read independently.

    Each team row links ``/teams/<id>``; its total is the first
    ``score_<competitor>`` cell after that link and before the next team link.
    """

    scores: dict[str, int | None] = {}
    for team in team_ids:
        link = re.search(rf'href="/teams/{team}"', html)
        if not link:
            scores[team] = None
            continue
        following = re.search(r'href="/teams/\d+"', html[link.end():])
        window = html[link.end(): link.end() + following.start()] if following else html[link.end():]
        cell = re.search(r'<div id="score_\d+" class="p-1">\s*(\d+)\s*</div>', window)
        scores[team] = int(cell.group(1)) if cell else None
    return scores


def _box_header_scores(html: str) -> list[int]:
    """The two large header totals of an NCAA contest page, in page order.

    The page colours the losing total grey and the winning total black, so
    the colour is not part of the match.
    """

    return [int(value) for value in re.findall(r'font-size:36px; color: [a-z]+">\s*(\d+)\s*</td>', html)]


def _points(side: str) -> Recompute:
    other = "home" if side == "away" else "away"

    def recompute(ctx: Context, pointers: list[str]) -> dict[str, Any]:
        document = ctx.doc(WEEK1_FINAL)
        by_target = {row["target_id"]: row for row in document["acquisitions"]}
        recomputed, evidence = {}, []
        for pointer in pointers:
            _, _, index, block, _field = pointer.split("/")
            contest = document["contests"][int(index)]
            contest_id = contest["ncaa_contest_id"]
            card = contest["scoreboard_card"]
            kickoff_day = contest["kickoff_utc"][:10].replace("-", "_")
            scoreboard_target = f"ncaa_scoreboard_{kickoff_day}"
            board = ctx.raw_payload(scoreboard_target, by_target[scoreboard_target]["raw_sha256"]).decode(
                "utf-8", "replace")
            teams = [card["away_source_team_id"], card["home_source_team_id"]]
            board_scores = _team_scores_from_scoreboard(board, teams)
            value: int | None
            if block == "scoreboard_card":
                value = board_scores[card[f"{side}_source_team_id"]]
            elif block == "box_header":
                page_target = f"ncaa_contest_{contest_id}"
                page = ctx.raw_payload(page_target, by_target[page_target]["raw_sha256"]).decode("utf-8", "replace")
                header = _box_header_scores(page)
                value = header[0 if side == "away" else 1] if len(header) == 2 else None
            else:  # admitted_score: re-oriented to the canonical participants
                admitted = contest["admitted_score"]
                team = admitted[f"{side}_canonical_id"].split(":")[-1]
                value = board_scores.get(team)
            recomputed[pointer] = value
            evidence.append({"pointer": pointer, "contest": contest_id, "scoreboard": scoreboard_target,
                             "scoreboard_scores_by_source_team": board_scores})
        return {"class": RECONSTRUCTED, "basis": "RE_READ_FROM_THE_RETAINED_RAW_HTML",
                "recomputed": recomputed, "evidence": {"reads": evidence, "other_side": other}}
    return recompute


for _side in ("away", "home"):
    claim(WEEK1_FINAL, f"{_side}_points",
          meaning=f"{_side.capitalize()} team points for a remaining Week 1 contest, as read from the "
                  "scoreboard card, the contest box header and the admitted (canonically oriented) "
                  "score; a 0 on a non-terminal card is an in-progress display value, not a final.",
          unit="points", population="Cycle 29 remaining Week 1 contests")(_points(_side))


# HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json ------------------------------

def _classification(value: Any) -> str:
    return "NULL" if value is None else str(value).upper()


def _pair(pair: str) -> Recompute:
    away, home = pair.split("_TO_")

    def recompute(ctx: Context, pointers: list[str]) -> dict[str, Any]:
        games = ctx.games()
        count = sum(1 for row in games if _classification(row["away_classification"]) == away
                    and _classification(row["home_classification"]) == home)
        literal = ctx.literal("src/aggie_analytics/cycle29/populations.py", rf'"{pair}":\s*\d+')
        return {"class": RECONSTRUCTED, "basis": "RECOUNTED_FROM_THE_RETAINED_PREDECESSOR_GAME_PAYLOAD",
                "recomputed": same(count, pointers),
                "evidence": {"games": len(games), "orientation": "AWAY_CLASSIFICATION_TO_HOME_CLASSIFICATION",
                             "producer_origin": {**literal, "kind": "LITERAL_CONSTANT_IN_PRODUCER"}}}
    return recompute


for _pair_name in ("FBS_TO_FBS", "FBS_TO_FCS", "FBS_TO_NULL", "FCS_TO_FBS", "FCS_TO_FCS", "NULL_TO_FBS"):
    _away, _home = _pair_name.split("_TO_")
    claim("HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json", _pair_name,
          meaning=f"Games in the 46,953-row predecessor normalized-game payload whose away participant "
                  f"is classified {_away} and home participant {_home} (NULL = no classification "
                  "recorded). The payload came from an FBS-filtered route, so it is not a national "
                  "FBS/FCS competition graph.",
          unit="games", population="Cycle 28 predecessor normalized games, 1963-2025")(_pair(_pair_name))


# MISSOURI_STATE_RAW_TO_PRIOR_LINEAGE_TRACE.json ------------------------------

def _missouri(kind: str) -> Recompute:
    def recompute(ctx: Context, pointers: list[str]) -> dict[str, Any]:
        games = [row for row in ctx.games()
                 if MISSOURI_STATE_SOURCE_TEAM_ID in (row["home_team_source_id"], row["away_team_source_id"])]
        opponents = {row["away_team_source_id"] if row["home_team_source_id"] == MISSOURI_STATE_SOURCE_TEAM_ID
                     else row["home_team_source_id"] for row in games}
        values = {
            "spine_edges_1963_2025": len(games),
            "distinct_opponents": len(opponents),
            "fcs_v_fcs": sum(1 for row in games if _classification(row["home_classification"]) == "FCS"
                             and _classification(row["away_classification"]) == "FCS"),
        }
        literal = ctx.literal("tools/materialize_cycle29.py", rf'"{kind}":\s*\d+')
        return {"class": RECONSTRUCTED, "basis": "RECOUNTED_FROM_THE_RETAINED_PREDECESSOR_GAME_PAYLOAD",
                "recomputed": same(values[kind], pointers),
                "evidence": {"source_team_id": MISSOURI_STATE_SOURCE_TEAM_ID, "edges": len(games),
                             "edges_through_2023": sum(1 for row in games if row["season"] <= 2023),
                             "seasons": [min(row["season"] for row in games), max(row["season"] for row in games)]
                             if games else None,
                             "producer_origin": {**literal, "kind": "LITERAL_CONSTANT_IN_PRODUCER"},
                             "contradicts_artifact_statement": "The artifact states focus_game_hardcode false "
                                                               "and generator general_transition_program_logic, "
                                                               "but the producer writes this value as a literal."}}
    return recompute


for _kind, _meaning in (
    ("spine_edges_1963_2025", "Every Missouri State game (edge) in the predecessor normalized-game payload; "
                              "the observed games span 1982-2025 despite the field name."),
    ("distinct_opponents", "Distinct opponents of Missouri State in the predecessor normalized-game payload."),
    ("fcs_v_fcs", "Missouri State games in that payload in which both participants are classified FCS."),
):
    claim("MISSOURI_STATE_RAW_TO_PRIOR_LINEAGE_TRACE.json", _kind, meaning=_meaning, unit="games or opponents",
          population="Missouri State (SRC-002:TEAM:2623) predecessor games")(_missouri(_kind))


# PIT_KERNEL_BOUNDED_COMPATIBILITY_FIXTURE.json ------------------------------

def _fixture_literal(ctx: Context) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    relative = "tools/materialize_cycle29.py"
    data = ctx.bind(f"producer:{relative}", ROOT / relative)
    tree = ast.parse(data.decode("utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "fixture_kernel_games":
            values = {}
            for statement in node.body:
                if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name):
                    values[statement.targets[0].id] = ast.literal_eval(statement.value)
            return values["games"], values["outcomes"], {"path": relative, "sha256": sha256_bytes(data),
                                                         "function": "fixture_kernel_games",
                                                         "line": node.lineno}
    raise LookupError("fixture_kernel_games not found")


@claim("PIT_KERNEL_BOUNDED_COMPATIBILITY_FIXTURE.json", "fixture_game_count",
       meaning="Games in the synthetic three-game compatibility fixture the Cycle 29 PIT kernel was "
               "exercised on; synthetic, not real games.",
       unit="fixture games", population="Cycle 29 bounded compatibility fixture")
def _fixture_games(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    games, _, origin = _fixture_literal(ctx)
    return {"class": RECONSTRUCTED, "basis": "COUNTED_FROM_THE_PRODUCER_FIXTURE_LITERAL",
            "recomputed": same(len({game["canonical_game_id"] for game in games}), pointers),
            "evidence": {"fixture": origin}}


@claim("PIT_KERNEL_BOUNDED_COMPATIBILITY_FIXTURE.json", "reconstructed_fixture_rows",
       meaning="Game-grain rows the kernel built from the synthetic fixture: one per fixture game with "
               "exactly two opposed team outcomes. Not proven PIT training rows.",
       unit="fixture game-grain rows", population="Cycle 29 bounded compatibility fixture")
def _fixture_rows(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    games, outcomes, origin = _fixture_literal(ctx)
    by_game: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for outcome in outcomes:
        by_game[outcome["canonical_game_id"]].append(outcome)
    complete = [game for game in games
                if len(by_game[game["canonical_game_id"]]) == 2
                and {row["canonical_team_id"] for row in by_game[game["canonical_game_id"]]}
                == {game["home_canonical_team_id"], game["away_canonical_team_id"]}
                and sum(row["margin"] for row in by_game[game["canonical_game_id"]]) == 0]
    return {"class": RECONSTRUCTED, "basis": "COUNTED_FROM_THE_PRODUCER_FIXTURE_LITERAL",
            "recomputed": same(len(complete), pointers),
            "evidence": {"fixture": origin, "team_outcome_rows": len(outcomes),
                         "games_with_two_opposed_outcomes": len(complete)}}


# PIT_PREDECESSOR_POPULATION_RECONCILIATION.json -----------------------------

@claim("PIT_PREDECESSOR_POPULATION_RECONCILIATION.json", "difference_eligible_minus_oriented",
       meaning="PIT-feature-eligible predecessor rows minus oriented development rows (89,855 - 90,198); "
               "negative because some oriented rows are not feature-eligible.",
       unit="rows", population="Cycle 28 predecessor oriented development rows")
def _difference(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    document = ctx.doc("PIT_PREDECESSOR_POPULATION_RECONCILIATION.json")
    eligible = document["predecessor_pit_feature_eligible_rows"]
    oriented = document["predecessor_oriented_development_rows"]
    return {"class": EVIDENCE_BACKED, "basis": "DERIVED_EXACTLY_FROM_DECLARED_CLAIMS",
            "recomputed": same(eligible - oriented, pointers),
            "dependencies": ["C29 original claim PIT_PREDECESSOR_POPULATION_RECONCILIATION.json/"
                             "predecessor_pit_feature_eligible_rows",
                             "C29 original claim PIT_PREDECESSOR_POPULATION_RECONCILIATION.json/"
                             "predecessor_oriented_development_rows"],
            "evidence": {"eligible": eligible, "oriented": oriented,
                         "limitation": "The two inputs are original-inventory claims; this tranche did not "
                                       "re-derive them from predecessor rows."}}


# PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.json -----------------------

COACHING = "PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.json"
COACHING_JSONL = "PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.jsonl"


def _coaching_rows(ctx: Context) -> list[dict[str, Any]]:
    data = ctx.bind(f"undeclared_external:{COACHING_JSONL}", ctx.external / COACHING_JSONL)
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def _coaching(field: str) -> Recompute:
    def recompute(ctx: Context, pointers: list[str]) -> dict[str, Any]:
        rows = _coaching_rows(ctx)
        categories = collections.Counter(row["predecessor_category"] for row in rows)
        provisional = sum(n for category, n in categories.items() if category != "ACCEPTED_COACH_ROLE_EPISODE")
        values = {
            "accepted_count": categories.get("ACCEPTED_COACH_ROLE_EPISODE", 0),
            "provisional_count": provisional,
            "row_count": len(rows),
            "model_admitted": sum(1 for row in rows if row.get("model_admitted") is True
                                  or str(row.get("successor_disposition", "")).startswith("ADMITTED")),
            "CANDIDATE_GENERATED": categories.get("CANDIDATE_GENERATED", 0),
            "REVIEW_REQUIRED": categories.get("REVIEW_REQUIRED", 0),
            "UNRESOLVED": categories.get("UNRESOLVED", 0),
        }
        return {"class": RECONSTRUCTED, "basis": "RECOUNTED_FROM_THE_NAMED_EXTERNAL_JSONL",
                "recomputed": same(values[field], pointers),
                "evidence": {"rows": len(rows), "by_category": dict(sorted(categories.items())),
                             "by_successor_disposition": dict(sorted(collections.Counter(
                                 row["successor_disposition"] for row in rows).items())),
                             "binding_limitation": "The artifact names this JSONL by path only and the "
                                                   "Cycle 29 manifest does not declare or hash it, so the "
                                                   "binding between the claim and these bytes is by path, "
                                                   "not by digest."}}
    return recompute


for _field, _meaning in (
    ("accepted_count", "Predecessor coaching observations in the ACCEPTED_COACH_ROLE_EPISODE category; "
                       "retained as non-admitted context."),
    ("provisional_count", "Predecessor coaching observations in any provisional category "
                          "(CANDIDATE_GENERATED, REVIEW_REQUIRED, UNRESOLVED)."),
    ("row_count", "All predecessor coaching observations reconciled (accepted plus provisional)."),
    ("model_admitted", "Reconciled coaching observations admitted to a model; zero by design."),
    ("CANDIDATE_GENERATED", "Provisional observations in the CANDIDATE_GENERATED category."),
    ("REVIEW_REQUIRED", "Provisional observations in the REVIEW_REQUIRED category."),
    ("UNRESOLVED", "Provisional observations in the UNRESOLVED category."),
):
    claim(COACHING, _field, meaning=_meaning, unit="observations",
          population="Cycle 28 predecessor coaching observations")(_coaching(_field))


# WEEK1_2026_PROGRAM_SLICE.json ----------------------------------------------

@claim("WEEK1_2026_PROGRAM_SLICE.json", "distinct_canonical_program_count_W",
       meaning="Distinct programs in the Week 1 2026 slice. Despite the field name these are "
               "display-name identities (identity_class DISPLAY_NAME_NOT_CANONICAL), not canonical "
               "program ids.",
       unit="programs", population="Week 1 2026 contest participants")
def _slice_w(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    document = ctx.doc("WEEK1_2026_PROGRAM_SLICE.json")
    programs = document["programs"]
    identity = sha256_bytes(json.dumps(sorted(programs), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {"class": EVIDENCE_BACKED, "basis": "DISTINCT_ENTRIES_OF_THE_ARTIFACTS_OWN_PROGRAM_LIST",
            "recomputed": same(len(set(programs)), pointers),
            "evidence": {"program_entries": len(programs), "distinct": len(set(programs)),
                         "identity_class": document.get("identity_class"),
                         "slice_identity_recomputed": identity,
                         "slice_identity_recorded": document.get("slice_identity")}}


@claim("WEEK1_2026_PROGRAM_SLICE.json", "review_time_expectation_W",
       meaning="The Week 1 program count the reviewer expected; a declared expectation constant, "
               "not a measurement.",
       unit="programs", population="Week 1 2026 contest participants")
def _slice_expectation(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    literal = ctx.literal("src/aggie_analytics/cycle29/populations.py", r'"review_time_expectation_W":\s*182')
    measured = len(set(ctx.doc("WEEK1_2026_PROGRAM_SLICE.json")["programs"]))
    return {"class": UNSUPPORTED, "basis": "DECLARED_EXPECTATION_CONSTANT_NOT_A_MEASUREMENT",
            "recomputed": {},
            "evidence": {"producer_origin": {**literal, "kind": "LITERAL_CONSTANT_IN_PRODUCER"},
                         "measured_distinct_programs": measured,
                         "equals_the_measured_count": measured == 182}}


# Pair-level omissions hidden by field-name matching ---------------------------

@claim("HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.manifest.json", "row_count",
       meaning="Rows in the external expected historical program-season population JSONL: one "
               "placeholder row per season 1963-2026, each BLOCKED (no program enumerated).",
       unit="rows", population="Historical national program-season expected population")
def _expected_rows(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    name = "HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.jsonl"
    rows = ctx.jsonl(name)
    recorded = ctx.doc("HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.manifest.json")["sha256"]
    bound = ctx.inputs[f"external:{name}"]["sha256"] == recorded
    return {"class": EVIDENCE_BACKED, "basis": "ROW_COUNT_OF_THE_DECLARED_EXTERNAL_JSONL",
            "recomputed": same(len(rows) if bound else None, pointers),
            "evidence": {"rows": len(rows), "artifact_records_its_sha256": recorded,
                         "digest_matches": bound,
                         "rows_with_a_program": sum(1 for row in rows if row.get("program_id"))}}


@claim("PIT_KERNEL_POPULATION_MANIFEST.json", "proven_pit_training_rows",
       meaning="Proven PIT training rows in the Cycle 29 production kernel population; zero.",
       unit="rows", population="Cycle 29 PIT kernel production rows")
def _kernel_rows(ctx: Context, pointers: list[str]) -> dict[str, Any]:
    rows = ctx.jsonl("PIT_KERNEL_ROWS.jsonl")
    return {"class": EVIDENCE_BACKED, "basis": "ROW_COUNT_OF_THE_DECLARED_KERNEL_ROWS_JSONL",
            "recomputed": same(len(rows), pointers),
            "evidence": {"kernel_rows": len(rows),
                         "note": "An empty declared row file supports a zero count; it proves absence of "
                                 "rows, not the absence of a defect in the kernel."}}


# ------------------------------------------------------------ assembly

def _types_held(path: Path, field: str) -> set[str]:
    """JSON types held under ``field`` anywhere in a JSON or JSON Lines file."""

    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == field:
                    found.add("boolean" if isinstance(value, bool) else "null" if value is None
                              else type(value).__name__)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    text = path.read_text(encoding="utf-8")
    documents = ([json.loads(line) for line in text.splitlines() if line.strip()]
                 if path.name.endswith(".jsonl") else [json.loads(text)])
    for document in documents:
        walk(document)
    return found


def build(census_path: Path, art: Path, external: Path, games: Path, raw: Path, state: str) -> dict[str, Any]:
    census_bytes = census_path.read_bytes()
    census = json.loads(census_bytes.decode("utf-8"))
    body = {key: value for key, value in census.items() if key != "census_body_sha256"}
    if sha256_bytes(json.dumps(body, sort_keys=True).encode("utf-8")) != census["census_body_sha256"]:
        raise SystemExit("REFUSED: the census body does not match its own digest")
    ctx = Context(art, external, games, raw)
    inventory_bytes = (art / INVENTORY).read_bytes()
    inventory = json.loads(inventory_bytes.decode("utf-8"))
    declared_pairs = {(row["artifact_path"], row["field"]) for row in inventory["claims"]}
    declared_names = {row["field"] for row in inventory["claims"]}

    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for item in census["numeric_values"]:
        if item["key"] is not None:
            by_pair[(item["artifact"], item["key"])].append(item)
    artifacts = {row["artifact"]: row for row in census["artifacts"]}

    def scanned(artifact: str) -> bool:
        return (artifact.endswith(".json") and artifact not in VALIDATOR_SKIP
                and artifacts[artifact]["location"] == "REPOSITORY_ARTIFACT_DIRECTORY")

    validator_omissions = sorted(pair for pair in by_pair if scanned(pair[0]) and pair[1] not in declared_names)
    hidden = sorted(pair for pair in by_pair if scanned(pair[0]) and pair not in declared_pairs
                    and pair[1] in declared_names)
    wanted = validator_omissions + hidden
    missing_recipe = [pair for pair in wanted if pair not in CLAIMS]
    unused_recipe = [pair for pair in CLAIMS if pair not in by_pair]
    if missing_recipe or unused_recipe:
        raise SystemExit(f"REFUSED: claim table and census disagree: missing {missing_recipe}, unused {unused_recipe}")

    claims = []
    for pair in wanted:
        artifact, field = pair
        items = sorted(by_pair[pair], key=lambda item: ((item["line"] or 0), item["pointer"]))
        spec = CLAIMS[pair]
        pointers = [item["pointer"] for item in items]
        result = spec["recompute"](ctx, pointers)
        recomputed = result["recomputed"]
        entries, mismatched = [], False
        for item in items:
            again = resolve(ctx.doc(artifact), item["pointer"])
            if again != item["value"] or type(again) is not type(item["value"]):
                raise SystemExit(f"REFUSED: census value drifted at {artifact}{item['pointer']}")
            value = recomputed.get(item["pointer"]) if recomputed else None
            matches = None if result["class"] == UNSUPPORTED else value == item["value"]
            mismatched = mismatched or matches is False
            entries.append({"line": item["line"], "pointer": item["pointer"], "value": item["value"],
                            "value_type": item["value_type"], "recomputed_value": value,
                            "matches": matches})
        classification = CONTRADICTED if mismatched else result["class"]
        claims.append({
            "claim_id": f"C29S-{Path(artifact).stem.replace('.', '-')}-{field}",
            "artifact": artifact,
            "artifact_sha256": items[0]["artifact_sha256"],
            "artifact_declared_in_manifest": artifacts[artifact]["declared_in_manifest"],
            "field": field,
            "discovery": ("VALIDATOR_OMISSION" if pair in validator_omissions
                          else "PAIR_LEVEL_OMISSION_HIDDEN_BY_FIELD_NAME_MATCHING"),
            "pointers": entries,
            "meaning": spec["meaning"],
            "unit": spec["unit"],
            "population": spec["population"],
            "classification": classification,
            "classification_basis": result["basis"],
            "dependencies": result.get("dependencies", []),
            "evidence": result["evidence"],
            "trust": "INVENTORIED_NOT_SCIENTIFICALLY_ACCEPTED",
        })

    dispositions = []
    successor_pairs = set(wanted)
    for pair in sorted(by_pair):
        artifact, field = pair
        values = [item["value"] for item in by_pair[pair]]
        location = artifacts[artifact]["location"]
        if pair in successor_pairs:
            disposition = "SUCCESSOR_CLAIM"
        elif pair in declared_pairs:
            disposition = "ORIGINAL_INVENTORY_PAIR"
        elif artifact == INVENTORY:
            disposition = "INVENTORY_SELF_DESCRIPTION_NOT_A_DOMAIN_CLAIM"
        elif location == "REPOSITORY_OTHER_ARTIFACT_DIRECTORY":
            disposition = "REFERENCED_ARTIFACT_OF_ANOTHER_SCOPE_OUTSIDE_THIS_TRANCHE"
        elif location == "CYCLE29_EXTERNAL_OUTPUT_DIRECTORY" or artifact.endswith(".jsonl"):
            disposition = "ROW_VALUES_OF_A_DECLARED_EXTERNAL_DATASET_OUTSIDE_THIS_TRANCHE"
        else:
            disposition = "UNACCOUNTED"
        dispositions.append({"artifact": artifact, "field": field, "occurrences": len(values),
                             "min": min(values), "max": max(values), "disposition": disposition})
    unaccounted = [row for row in dispositions if row["disposition"] == "UNACCOUNTED"]
    if unaccounted:
        raise SystemExit(f"REFUSED: census pairs with no disposition: {unaccounted}")
    array_numbers = [{"artifact": item["artifact"], "line": item["line"], "pointer": item["pointer"],
                      "value": item["value"], "disposition": "CONTRACT_BOUND_VALUE_IN_AN_ARRAY_NOT_A_CLAIM_FIELD"}
                     for item in census["numeric_values"] if item["key"] is None]
    accounted = sum(row["occurrences"] for row in dispositions) + len(array_numbers)
    if accounted != census["numeric_value_count"]:
        raise SystemExit(f"REFUSED: accounted {accounted} of {census['numeric_value_count']} numeric values")

    carried = []
    for row in inventory["claims"]:
        pair = (row["artifact_path"], row["field"])
        record = artifacts.get(row["artifact_path"])
        held: list[str] = []
        if record is None:
            status = "ARTIFACT_NOT_IN_THE_CENSUS"
        elif pair in by_pair:
            status = "NUMERIC_FIELD_PRESENT"
        elif record["path"] is None:
            status = "ARTIFACT_NAMED_BUT_ABSENT"
        else:
            held = sorted(_types_held(Path(record["path"]), row["field"]))
            status = "FIELD_PRESENT_BUT_NOT_NUMERIC" if held else "FIELD_ABSENT_FROM_THE_ARTIFACT"
        carried.append({"claim_id": row["claim_id"], "artifact": row["artifact_path"], "field": row["field"],
                        "artifact_location": None if record is None else record["location"],
                        "trust_class_as_originally_recorded": row["trust_class"], "resolution": status,
                        "value_types_held_under_the_field": held,
                        "numeric_values": [item["value"] for item in by_pair.get(pair, [])],
                        "numerator_as_recorded": row.get("numerator"),
                        "denominator_as_recorded": row.get("denominator")})

    counts = collections.Counter(item["classification"] for item in claims)
    document = {
        "label": f"Cycle #37 — Attempt #3 — {state}",
        "cycle_number": 37,
        "attempt_number": 3,
        "artifact_type": "CYCLE29_CLAIM_INVENTORY_SUCCESSOR",
        "successor_version": SUCCESSOR_VERSION,
        "tool_version": TOOL_VERSION,
        "finding": "W37R-71",
        "requirement": "R37A03-06",
        "predecessor_inventory": {
            "path": f"artifacts/scientific_integrity/cycle29/{INVENTORY}",
            "sha256": sha256_bytes(inventory_bytes),
            "claims": len(inventory["claims"]),
            "discovered_count_as_stated": inventory.get("discovered_count"),
            "unmapped_count_as_stated": inventory.get("unmapped_count"),
            "left_unchanged": True,
        },
        "census": {"path": str(census_path), "file_sha256": sha256_bytes(census_bytes),
                   "census_body_sha256": census["census_body_sha256"],
                   "census_version": census["census_version"], "numeric_value_count": census["numeric_value_count"],
                   "artifact_count": census["artifact_count"]},
        "declared_artifact_set": {
            "manifest_sha256": census["manifest"]["sha256"],
            "declared": census["manifest"]["declared_count"],
            "declared_and_hash_verified": sum(1 for row in census["artifacts"]
                                              if row.get("manifest_hash_matches") is True),
            "declared_but_absent": [row["artifact"] for row in census["artifacts"]
                                    if row["declared_in_manifest"] and row["path"] is None],
            "present_in_the_artifact_directory_but_not_declared": [
                row["artifact"] for row in census["artifacts"]
                if row["present_in_artifact_directory"] and not row["declared_in_manifest"]],
            "referenced_only": [
                {"artifact": row["artifact"], "referenced_by": row.get("referenced_by", []),
                 "location": row["location"], "sha256": row.get("sha256")}
                for row in census["artifacts"]
                if not row["declared_in_manifest"] and not row["present_in_artifact_directory"]],
            "hash_mismatches": [row["artifact"] for row in census["artifacts"]
                                if row.get("manifest_hash_matches") is False],
        },
        "scanner": {
            "validator": "tools/validate_cycle29_gates.py",
            "validator_omissions": len(validator_omissions),
            "pair_level_omissions_hidden_by_field_name_matching": [
                {"artifact": artifact, "field": field} for artifact, field in hidden],
            "scanner_limitation": "The repaired validator treats a field name declared for any artifact as "
                                  "declared for every artifact, scans only repository *.json files and "
                                  "records only numbers held under an object key.",
        },
        "claim_count": len(claims),
        "pointer_count": sum(len(item["pointers"]) for item in claims),
        "classification_counts": {name: counts.get(name, 0) for name in CLASSES},
        "claims": claims,
        "census_pair_dispositions": dispositions,
        "array_element_numbers": array_numbers,
        "numeric_value_accounting": {
            "census_numeric_values": census["numeric_value_count"],
            "accounted": accounted,
            "by_disposition": dict(sorted(collections.Counter(
                row["disposition"] for row in dispositions for _ in range(row["occurrences"])).items()))
            | {"CONTRACT_BOUND_VALUE_IN_AN_ARRAY_NOT_A_CLAIM_FIELD": len(array_numbers)},
        },
        "carried_forward_original_claims": carried,
        "inputs": dict(sorted(ctx.inputs.items())),
        "not_claimed": [
            "An inventory that covers every numeric field is not evidence that the numbers are scientifically true.",
            "This is the bounded Cycle 29 tranche, not an audit of Cycles 1-36.",
            "The committed CYCLE29_CLAIM_INVENTORY.json is unchanged and remains incomplete on its own; the "
            "default validator still reports it.",
            "No PIT, forecast, model or trust state changes because of this successor.",
        ],
        "limitations": [
            "Row values of the declared external JSONL datasets (seasons, coverage-cube numerators and "
            "denominators, role-matrix episode cardinalities) are enumerated by the census and dispositioned, "
            "but not inventoried as claims in this tranche.",
            "Original-inventory claims are carried forward with their recorded trust class; this tranche did "
            "not re-derive them.",
            "The HTTP status of each Week 1 acquisition is unsupported: no transport receipt was retained.",
        ],
    }
    document["body_sha256"] = sha256_bytes(json.dumps(document, sort_keys=True).encode("utf-8"))
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--census", required=True)
    parser.add_argument("--artifact-dir", default=str(ART))
    parser.add_argument("--external-dir", default=str(EXTERNAL))
    parser.add_argument("--games-payload", default=str(GAMES_PAYLOAD))
    parser.add_argument("--raw-root", default=str(RAW_CYCLE29))
    parser.add_argument("--state", default="IN_PROGRESS_LOCAL_WORK_REMAINS")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    art = Path(args.artifact_dir).resolve()
    out = Path(args.out).resolve()
    if art == out.parent or art in out.parents:
        print("REFUSED: the successor is never written into the Cycle 29 artifact directory", file=sys.stderr)
        return 2
    if out.exists():
        print(f"REFUSED: {out} exists; successor versions are never overwritten", file=sys.stderr)
        return 2
    document = build(Path(args.census).resolve(), art, Path(args.external_dir), Path(args.games_payload),
                     Path(args.raw_root), args.state)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"claims": document["claim_count"], "pointers": document["pointer_count"],
                      "classification_counts": document["classification_counts"],
                      "accounting": document["numeric_value_accounting"], "out": str(out)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
