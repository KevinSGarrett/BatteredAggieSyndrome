"""A tiny synthetic personnel association world in the accepted parent record shapes (BAT-732, Cycle #61 TP61-A01).

The accepted parents are read in production through their accepted readers (the C56 reference and the C59 personnel
evidence); this fixture writes the records those readers return -- C56 feature, label and C47 estimate records and C59
program-season, summary and component records, each with its canonical JSON line -- for a small invented national
world, and injects them through the builder's ``loader`` hook. Nothing here is real data: every team, game, roster
count and outcome is generated deterministically from a fixed seed. Planted classes: an unqualified chain (FCS), a
qualified program-season without a same-season returning summary, a summary link naming another season, a study side
with no program-season at all, the partial 2020 -> 2021 metric transition, signed yardage shares above 1 and below 0
(kept unclipped), a missing share pair (null), two tie labels (one in a supported FIT game, one in the comparison),
cold starts and games outside common support in both partitions."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import random
import shutil
import sqlite3
import sys
import zlib
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.retrospective_baseline import personnel_association as pa  # noqa: E402

POP = pa.POPULATION
REFERENCE_ID = "a" * 64
REFERENCE_CONTENT = "b" * 64
PERSONNEL_ID = "c" * 64
PERSONNEL_CONTENT = "d" * 64
SEASONS = (2018, 2019, 2020, 2021, 2022)
TEAMS = tuple(range(1, 11))
#: (season, org) program-seasons planted outside joinability, and the side that never has a program-season.
NO_SUMMARY = (2019, 9)
UNQUALIFIED = (2021, 10)
LINK_MISMATCH = (2022, 8)
NO_PROGRAM_ORG = 11


def builder() -> Any:
    sys.path.insert(0, str(ROOT / "tools"))
    import build_national_personnel_association as b  # noqa: PLC0415

    return b


def _h(text: str, n: int = 32) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def team_id(org: int) -> str:
    return f"team_{_h(f'team-{org}')}"


def name(org: int) -> str:
    return f"Fixture State {org}" if org != 3 else "Fixture Tech"


def _line(record: dict[str, Any]) -> str:
    return pa.canonical_line(record)


def _schedule(rng: random.Random, season: int) -> list[tuple[str, str, int, int]]:
    """(contest_key, date, a_org, b_org) per week: five games among the ten teams, plus a game with org 11."""
    games = []
    for week in range(1, 7):
        orgs = list(TEAMS)
        rng.shuffle(orgs)
        for i in range(0, 10, 2):
            date = f"{season}-09-{week * 3 + i // 2:02d}"
            games.append((f"ncaa:{season}{week:02d}{i:02d}", date, orgs[i], orgs[i + 1]))
    games.append((f"ncaa:{season}9901", f"{season}-11-30", 1 + season % 10, NO_PROGRAM_ORG))
    if season == 2022:
        games.append((f"ncaa:{season}9902", f"{season + 1}-01-02", 2, 5))   # a bowl dated in the next calendar year
    return games


def joinable(season: int, org: int) -> bool:
    return org in TEAMS and (season, org) not in (NO_SUMMARY, UNQUALIFIED, LINK_MISMATCH)


def build_world(seed: int = 6101) -> dict[str, Any]:
    rng = random.Random(seed)
    strength = {org: rng.uniform(-1.0, 1.0) for org in (*TEAMS, NO_PROGRAM_ORG)}
    features, labels, c47 = [], [], []
    tie_seasons = {2019, 2022}
    for season in SEASONS:
        tie_done = False
        played: dict[int, list[tuple[str, str, int, str]]] = {org: [] for org in (*TEAMS, NO_PROGRAM_ORG)}
        for index, (key, date, a, b) in enumerate(_schedule(rng, season)):
            def side(org: int, opp: int) -> dict[str, Any]:
                prior = [g for g in played[org] if g[1] < date]
                wins = sum(1 for g in prior if g[3] == "W")
                losses = sum(1 for g in prior if g[3] == "L")
                ties = sum(1 for g in prior if g[3] == "T")
                return {"games": len(prior), "wins": wins, "losses": losses, "ties": ties,
                        "cold_start": not prior, "contributing": [
                            {"contest_key": g[0], "contest_date": g[1], "opponent_key": f"org:{g[2]}", "result": g[3]}
                            for g in prior]}
            sa, sb = side(a, b), side(b, a)
            for view, (team, opp, st, so) in (("A", (a, b, sa, sb)), ("B", (b, a, sb, sa))):
                features.append({"contest_key": key, "season": season, "contest_date": date, "view": view,
                                 "team_key": f"org:{team}", "team_name": name(team), "team_org_id": str(team),
                                 "opponent_key": f"org:{opp}", "opponent_name": name(opp), "opponent_org_id": str(opp),
                                 "team": st, "opponent": so, "record_type": "reference_feature"})
            margin = strength[a] - strength[b] + rng.gauss(0.0, 0.8)
            tie = season in tie_seasons and not tie_done and index >= 10 and joinable(season, a) and \
                joinable(season, b)
            tie_done = tie_done or tie
            result = "T" if tie else ("W" if margin > 0 else "L")
            state = "TIE" if result == "T" else "DECISIVE"
            labels.append({"record_type": "label", "contest_key": key, "season": season, "contest_date": date,
                           "a_key": f"org:{a}", "b_key": f"org:{b}", "label_state": state,
                           "y_a": None if state == "TIE" else (1 if result == "W" else 0)})
            for org, opp, res in ((a, b, result), (b, a, {"W": "L", "L": "W", "T": "T"}[result])):
                played[org].append((key, date, opp, res))
            qa = pa.strength_q(sa["wins"], sa["ties"], sa["games"])
            qb = pa.strength_q(sb["wins"], sb["ties"], sb["games"])
            for model_id, p in ((pa.MODEL_NULL, Fraction(1, 2)), (pa.MODEL_SMOOTHED, pa.smoothed_probability(qa, qb))):
                for orientation, mine in (("A", p), ("B", 1 - p)):
                    c47.append({"record_type": "estimate", "contest_key": key, "season": season, "model_id": model_id,
                                "orientation": orientation, "probability": pa.rational(mine)})
    programs, summaries, components = [], [], []
    for season in SEASONS:
        for org in (*TEAMS, 50):
            division = "FCS" if org == 50 else "FBS"
            unqualified = (season, org) == UNQUALIFIED or org == 50
            summary_key = f"{season}|{team_id(org)}"
            target = None
            if not unqualified and (season, org) != NO_SUMMARY:
                target = summary_key if (season, org) != LINK_MISMATCH else f"{season - 1}|{team_id(org)}"
            programs.append({
                "record_type": "PROGRAM_SEASON_COVERAGE", "program_season_key": f"{season}|org:{org}",
                "season": season, "team_key": f"org:{org}", "org_id": str(org), "division": division,
                "divisions": [division], "team_names": [name(org)],
                "chain_state": "UNQUALIFIED_NO_SRC002_TEAM_ENTITY" if unqualified else "QUALIFIED_EXACT_CHAIN",
                "canonical_team_id": None if unqualified else team_id(org), "returning_target_summary_key": target,
                "coverage_state": "ROSTER_AND_RETURNING_TRANSITION" if target else "NO_ADMITTED_ROSTER_ROWS",
                "roster_presence": "ADMITTED_ROSTER_ROWS" if target else "NO_ADMITTED_ROSTER_ROWS",
                "transition_presence": "RETURNING_TRANSITION" if target else "NO_RETURNING_TRANSITION"})
            if unqualified or (season, org) == NO_SUMMARY:
                continue
            prior = rng.randint(60, 95)
            returning = rng.randint(30, prior - 5)
            arrival = rng.randint(10, 40)
            shares = {f: round(rng.uniform(0.2, 0.95), 6) for f in pa.SHARE_FIELDS}
            if (season, org) == (2020, 4):
                shares["passing_yards_returning_share"] = 1.0821
            if (season, org) == (2021, 6):
                shares["rushing_yards_returning_share"] = -0.0417
            if (season, org) == (2022, 7):
                shares["receiving_yards_returning_share"] = None
            summaries.append({
                "record_type": "RETURNING_SUMMARY", "summary_key": summary_key, "prior_season": season - 1,
                "target_season": season, "canonical_team_id": team_id(org), "canonical_team_label": name(org),
                "prior_roster_count": prior, "current_roster_count": returning + arrival,
                "returning_roster_count": returning, "departed_roster_count": prior - returning,
                "arrival_roster_count": arrival, "union_roster_count": prior + arrival,
                "roster_retention_rate": returning / prior, "roster_arrival_rate": arrival / (returning + arrival),
                "roster_jaccard": returning / (prior + arrival), **shares,
                "component_keys": [f"{summary_key}|{c}|{s}" for c, s in (("passing", "YDS"), ("rushing", "YDS"))],
                "missing_component_pairs": ["receiving|YDS"] if shares["receiving_yards_returning_share"] is None
                else [], "partial_prior_metric_season": season == 2021,
                "source_known_at_utc": pa.ROSTER_SOURCE_KNOWN_AT, "original_transition_time_pit_eligible": False,
                "target_game_feature_eligible": False, "protected_eligible": False,
                "feature_identity": _h(summary_key, 64), "census_scope_state": "TARGET_AND_PRIOR_IN_CENSUS"})
            components.append({"record_type": "RETURNING_COMPONENT", "component_key": f"{summary_key}|passing|YDS",
                               "summary_key": summary_key})
    return {"features": features, "labels": labels, "c47": c47, "programs": programs, "summaries": summaries,
            "components": components, "seed": seed}


def inputs_for(world: dict[str, Any], order: str = "natural",
               patch: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    world = copy.deepcopy(world)
    if patch is not None:
        patch(world)
    pairs = {k: [(r, _line(r)) for r in world[k]] for k in ("features", "labels", "c47", "programs", "summaries",
                                                           "components")}
    return {"paths": {n: f"<fixture {n}>" for n in pa.INPUT_NAMES},
            "reference": {"identity": REFERENCE_ID, "content_identity": REFERENCE_CONTENT,
                          "features": pa._ordered(pairs["features"], order),
                          "labels": pa._ordered(pairs["labels"], order),
                          "c47_estimates": pa._ordered(pairs["c47"], order)},
            "personnel": {"identity": PERSONNEL_ID, "content_identity": PERSONNEL_CONTENT,
                          "program_seasons": pa._ordered(pairs["programs"], order),
                          "summaries": pa._ordered(pairs["summaries"], order),
                          "components": pa._ordered(pairs["components"], order)}}


def pins() -> dict[str, Any]:
    out = {}
    for n in pa.INPUT_NAMES:
        identity = REFERENCE_ID if n.startswith("reference") else PERSONNEL_ID if n.startswith("personnel") else \
            _h(n, 64)
        content = REFERENCE_CONTENT if n == "reference_database" else PERSONNEL_CONTENT if n == "personnel_database" \
            else None
        out[n] = {"relative_path": f"fixture/{n}", "sha256": _h(f"bytes-{n}", 64), "bytes": 1, "identity": identity,
                  "content_identity": content, "role": f"FIXTURE_{n.upper()}", "supports": []}
    return out


def expected_for(world: dict[str, Any]) -> dict[str, Any]:
    """The expected collections exactly as the contract generator observes them (qualification and features only)."""
    inputs = inputs_for(world)
    quals = pa.qualify(inputs["personnel"])
    features = pa.derive_features(inputs["reference"], quals)
    pa.involvement(features, quals)
    a_views = [f for f in features if f["view"] == "A"]
    targets = sorted(({"contest_key": f["contest_key"], "season": f["season"], "contest_date": f["contest_date"]}
                      for f in a_views), key=lambda t: (t["season"], t["contest_date"], t["contest_key"]))
    expected = {"targets": targets,
                "qualification_keys": [quals[k]["qualification_key"] for k in sorted(
                    quals, key=lambda k: (k[0], pa._org_number(k[1])))],
                "common_support_games": sorted(f["contest_key"] for f in a_views
                                               if f["support_state"] == "COMMON_SUPPORT"),
                "signed_shares_outside_unit_interval": sorted(
                    f"{q['summary']['summary_key']}|{field}" for q in quals.values() if q["summary"]
                    for field in pa.SIGNED_SHARE_FIELDS if q["summary"]["share_outside_unit_interval"][field]),
                "personnel_signed_shares_outside_unit_interval_all_summaries": [],
                "latest_study_contest_date": max(t["contest_date"] for t in targets), "counts": {}}
    expected["keys_sha256"] = {t: pa.keys_sha256(k) for t, k in pa.expected_keys(expected).items()}
    return expected


def contract_for(world: dict[str, Any], **patch: Any) -> dict[str, Any]:
    contract = {"schema_version": "1.0", "contract_id": pa.CONTRACT_ID, "jira_key": "FIXTURE", "cycle_number": 61,
                "attempt_number": 1, "population_id": pa.POPULATION, "inputs": pins(), "parent_contracts": {},
                "expected": expected_for(world), "rules": pa.rules_document(), "outputs": {"database": pa.DB_FILE}}
    contract.update(patch)
    return contract


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(contract, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return Path(path)


def contract_anchors(path: Path) -> dict[str, Any]:
    return {**builder().load_contract(path, ROOT)[2], "profile": None}


def run_build(contract_path: Path, world: dict[str, Any], out: Path, *extra: str,
              patch: Callable[[dict[str, Any]], None] | None = None) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract_path), "--data-root", str(out), "--output-root", str(Path(out) / "canonical" / POP),
            "--manifest-root", str(Path(out) / "manifests" / POP), "--repo-root", str(ROOT), *extra]

    def loader(_data_root: Any, _anchors: Any, *, input_order: str = "natural") -> dict[str, Any]:
        return inputs_for(world, input_order, patch)
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv, loader=loader)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    text = stderr.strip()
    return json.loads(text.splitlines()[-1]).get("refused") if text else None


def database_of(result: dict[str, Any]) -> Path:
    return Path(result["release"]["data_dir"]) / pa.DB_FILE


def manifest_of(database: Path) -> Path:
    return pa.manifest_path_for(Path(database))


def query(anchors: dict[str, Any], database: Path | str, *argv: str, front: Callable | None = None
          ) -> tuple[int, Any, str]:
    """The query's main() in process with fixture anchors; returns (exit, parsed stdout or None, stderr)."""
    from aggie_analytics.retrospective_baseline import query as q  # noqa: PLC0415

    tokens = ["--personnel-association", str(database), *argv]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = (front or q.main)(tokens, association_anchors=anchors)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


# --------------------------------------------------------------------------------------------- forged releases

class Forger:
    """Coordinated forgeries of one personnel association database in owned scratch: records are edited, blocks rebuilt
    with consistent index columns, and (``rehash_content``) the content document, meta claims, identity document,
    directory identity and manifest are all recomputed, so only a rule the reader re-derives can refuse it."""

    def __init__(self, database: Path, root: Path, anchors: dict[str, Any]) -> None:
        self.database = Path(database)
        self.root = Path(root)
        self.anchors = anchors
        self.manifest = json.loads(manifest_of(self.database).read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t, _s in pa.BLOCK_LAYOUT}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              lines: Callable[[dict[str, list[str]]], None] | None = None, meta: dict[str, Any] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              identity_override: str | None = None, manifest_patch: dict[str, Any] | None = None,
              manifest_text: Callable[[str], str] | None = None, rehash_content: bool = True,
              provenance: Any = None) -> Path:
        work = self.root / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(self.database, work)
        conn = sqlite3.connect(work)
        conn.execute("PRAGMA journal_mode = OFF")
        content_doc = copy.deepcopy(self.manifest["content_document"])
        content_identity = self.manifest["content_identity"]
        if records is not None or lines is not None:
            tables = self.tables()
            if records is not None:
                records(tables)
            raw = {t: [pa.canonical_line(r) for r in rows] for t, rows in tables.items()}
            if lines is not None:
                lines(raw)
            conn.execute("DELETE FROM blocks")
            grouped: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
            for table, table_lines in raw.items():
                for line in table_lines:
                    try:
                        value = json.loads(line)
                    except (ValueError, RecursionError):
                        value = {}
                    value = value if isinstance(value, dict) else {}
                    seg = str(value.get("season")) if table in pa.SEASONAL_TABLES else "GLOBAL"
                    if (table, seg) not in pa.BLOCK_LAYOUT:
                        seg = [s for t, s in pa.BLOCK_LAYOUT if t == table][-1]
                    grouped.setdefault((table, seg), []).append((line, value))
            for ord_, (table, segment) in enumerate(pa.BLOCK_LAYOUT):
                chosen = [line for line, _v in grouped.get((table, segment), [])]
                parsed = [v for _l, v in grouped.get((table, segment), [])]
                data = "".join(l + "\n" for l in chosen).encode("utf-8")
                conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (ord_, table, segment, len(chosen),
                              str(parsed[0].get(pa.KEY_FIELDS[table])) if parsed else None,
                              str(parsed[-1].get(pa.KEY_FIELDS[table])) if parsed else None,
                              pa.sha256_bytes(data), zlib.compress(data, 9)))
            if rehash_content:
                derived: dict[str, Any] = {}
                for t in pa.RECORD_TABLES:
                    rows = []
                    for l in raw[t]:
                        try:
                            rows.append(json.loads(l))
                        except (ValueError, RecursionError):
                            rows.append({})
                    derived[t] = rows
                derived["lines"] = raw
                content_doc = pa.content_document(self.anchors, derived)
                content_identity = pa.sha256_bytes(pa.canonical_json_bytes(content_doc))
                summary = derived["summary"][0] if derived["summary"] else {}
                for key, value in pa.meta_values(self.anchors, content_identity,
                                                 {**derived, "summary": [summary]}).items():
                    conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else pa.canonical_line(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in pa.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {pa.DB_FILE: pa.sha256_file(work)}
        doc["table_counts"] = counts
        doc["content_identity"] = content_identity
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = identity_override or pa.sha256_bytes(pa.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / pa.DB_FILE
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.root / name / "manifests" / POP / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        body = {"identity": identity, "identity_document": doc, "content_identity": content_identity,
                "content_document": content_doc, "provenance": provenance if provenance is not None else
                {"forgery": name}}
        body.update(manifest_patch or {})
        text = json.dumps(body)
        if manifest_text is not None:
            text = manifest_text(text)
        man.write_text(text, encoding="utf-8")
        return target
