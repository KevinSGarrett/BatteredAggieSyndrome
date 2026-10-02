r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-06: a row-grain successor for play-calling responsibility and scheme
assertions over the whole cached population.

Responsibility
  * Every one of the 3,709 predecessor rows is carried with its predecessor
    disposition, its release row id, the staff observation it came from
    (joined on capture, person and title, and reporting the current program
    binding after the R37-03 crosswalk), and a rebuilt disposition from the
    context rules in ``cycle37.responsibility``. A capture-text row gets its
    quoted span back from the capture bytes.
  * The whole population is then scanned: every staff title (not only
    HC/OC/DC ones), the rendered text of every official capture whether or
    not it is bound to a program, and every cached encyclopedia revision.
    Each mention is classified in its own sentence.
  * Only an official staff title that states play-calling, bound to a
    program and a season, is a current responsibility. Encyclopedia
    statements are historical candidates with their years and programs as
    written.

Scheme
  * The delivered source-stated scheme rows are kept, each given a declared
    category (offensive scheme, defensive base/family) with the categories
    the source never states (special-teams system, coaching philosophy,
    realized team scheme) counted explicitly as absent. A family that
    belongs to the other side is reported, not silently re-sided.
  * The three source-text conflicts and every candidate/unknown state are
    kept; every count is over a declared enum.

A blind sample of mentions across sources, eras and dispositions is written
without its dispositions, for labelling before any comparison.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import responsibility as rs
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
CYCLE36 = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output")
PREDECESSOR_ROWS = CYCLE36 / "CYCLE36_RESPONSIBILITY_ASSERTIONS.jsonl"
CAPTURES = CYCLE36 / "CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl"
WIKIMEDIA = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/wikimedia")
NORMALIZATION_VERSION = "BAS-SCHEME-TAXONOMY-v36.1"

#: Declared scheme categories. The source (team-season infobox fields) states
#: only the first two; the rest are counted as absent, never inferred.
OFFENSIVE = "OFFENSIVE_SCHEME_SOURCE_STATED"
DEFENSIVE = "DEFENSIVE_BASE_FAMILY_SOURCE_STATED"
ABSENT_CATEGORIES = {
    "SPECIAL_TEAMS_SYSTEM": "no cached source field states a special-teams system",
    "COACHING_PHILOSOPHY": "a philosophy is not an infobox field; no row carries one",
    "REALIZED_TEAM_SCHEME": "realized scheme is film-owned (F10); a source-stated family is not it",
    "PLAY_CALLING_RESPONSIBILITY": "kept in the responsibility rows, never in a scheme row",
}
DEFENSIVE_FAMILY = re.compile(r"^(FRONT_|NICKEL|DIME|MULTIPLE|3_3_5|4_2_5|BEAR|TAMPA|COVER)")
OFFENSIVE_FAMILY = re.compile(r"^(SPREAD|PRO_STYLE|AIR_RAID|WEST_COAST|OPTION|TRIPLE_OPTION|VEER|WISHBONE|PISTOL|"
                              r"RUN_AND_SHOOT|WING_T|SINGLE_WING|I_FORMATION|POWER|MULTIPLE|SPREAD_OPTION|FLEXBONE|"
                              r"SHOTGUN|SMASHMOUTH|PRO_SPREAD|T_FORMATION|SPLIT_BACK)")
SCHEME_STATES = ("ADMITTED_CANDIDATE_SCHEME_ASSERTION", "RETAINED_PROGRAM_UNRESOLVED", "RETAINED_SOURCE_STATED_NOTHING")
PERSON_PAGE_EXCLUDE = re.compile(r"\d|football|university|college|stadium|season|bowl|conference|league|list of|"
                                 r"team|association|division|championship|field|athletic|school", re.I)
HELDOUT_TARGET = 40


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:24]


# --------------------------------------------------------------- lineage
def predecessor_lineage(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [json.loads(line) for line in PREDECESSOR_ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    release = conn.execute("SELECT responsibility_id, person, program_id, season, source_title, evidence_code, "
                           "disposition FROM responsibility_assertion ORDER BY responsibility_id").fetchall()
    if len(release) != len(rows):
        raise SystemExit(f"release has {len(release)} responsibility rows, predecessor file {len(rows)}")
    observations: dict[tuple, list[tuple]] = collections.defaultdict(list)
    for obs in conn.execute("SELECT observation_id, capture_path, person, source_title, program_id, season, "
                            "binding_state FROM staff_observation"):
        observations[(obs[1], obs[2], obs[3])].append(obs)
    out, mismatched = [], 0
    for index, (row, rel) in enumerate(zip(rows, release), 1):
        if (rel[1], rel[4] or "", rel[6]) != (row.get("person"), row.get("source_title") or "", row.get("disposition")):
            mismatched += 1
        base = {"successor_key": key("pred", index), "responsibility_version": rs.RESPONSIBILITY_VERSION,
                "source_kind": "PREDECESSOR_ROW", "predecessor_row_index": index,
                "release_responsibility_id": rel[0], "predecessor_version": row.get("responsibility_version"),
                "predecessor_disposition": row.get("disposition"), "predecessor_evidence_code": row.get("evidence_code"),
                "capture_path": row.get("capture_path"), "payload_sha256": row.get("payload_sha256"),
                "person": row.get("person"), "source_title": row.get("source_title")}
        if row.get("source_title"):
            matches = observations.get((row.get("capture_path"), row.get("person"), row.get("source_title")), [])
            obs = matches[0] if len(matches) == 1 else None
            code, disposition = rs.classify_title(row["source_title"])
            program = obs[4] if obs else row.get("program_id")
            season = obs[5] if obs else row.get("season")
            if disposition == rs.CURRENT_TITLE and not (program and season):
                disposition = rs.UNATTRIBUTABLE
            out.append({**base, "observation_id": obs[0] if obs else None,
                        "observation_join": "UNIQUE" if obs else ("AMBIGUOUS" if matches else "NONE"),
                        "program_id": program, "season": season,
                        "program_binding_state": obs[6] if obs else None,
                        "evidence_code": code, "disposition": disposition or rs.MENTION_ONLY})
        else:
            quoted, person = None, None
            path = Path(row.get("capture_path") or "")
            if path.is_file() and row.get("offset_in_rendered_text") is not None:
                text = rs.html_rendered(path.read_text(encoding="utf-8", errors="replace"))
                recorded = int(row["offset_in_rendered_text"])
                # The predecessor rendered the page with a slightly different
                # tag order, so its offset drifts; the mention nearest to it,
                # with the same matched text, is the one it recorded.
                near = [m for m in rs.MENTION.finditer(text)
                        if m.group(0).casefold() == str(row.get("matched_text") or m.group(0)).casefold()]
                at = min(near, key=lambda m: abs(m.start() - recorded)).start() if near else recorded
                quoted = text[max(0, at - 220): at + 220]
                # A staff directory prints each name immediately before its
                # title, so the statement belongs to the capture's staff name
                # that ends nearest before the mention.
                window_start = max(0, at - 160)
                before = text[window_start:at]
                staff = {o[2] for (cap, _, _), obs in observations.items() if cap == row["capture_path"]
                         for o in obs if o[2]}
                ends = {n: before.rfind(n) + len(n) for n in staff if before.rfind(n) >= 0}
                person = max(ends, key=ends.get) if ends else None
            obs_for_capture = [o for (cap, _, _), obs in observations.items() if cap == row.get("capture_path")
                               for o in obs]
            programs = {o[4] for o in obs_for_capture if o[4]}
            program = next(iter(programs)) if len(programs) == 1 else row.get("program_id")
            # A capture-text match beside a title that already states play-calling
            # is a second copy of that statement, not a second responsibility.
            disposition = rs.TEXT_COPY if person else rs.UNNAMED
            out.append({**base, "observation_id": None, "program_id": program, "season": row.get("season"),
                        "quoted_span": quoted, "person_attributed": person,
                        "evidence_code": row.get("evidence_code"), "disposition": disposition,
                        "duplicate_of_title_statement": bool(person)})
    return out, {"predecessor_rows": len(rows), "release_rows": len(release), "row_order_mismatches": mismatched,
                 "predecessor_sha256": sha256_file(PREDECESSOR_ROWS)}


# ------------------------------------------------------ whole population
def scan_titles(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows, examined = [], 0
    for obs in conn.execute("SELECT observation_id, capture_path, person, source_title, program_id, season "
                            "FROM staff_observation"):
        examined += 1
        title = obs[3] or ""
        if not rs.MENTION.search(title):
            continue
        code, disposition = rs.classify_title(title)
        if disposition == rs.CURRENT_TITLE and not (obs[4] and obs[5]):
            disposition = rs.UNATTRIBUTABLE
        rows.append({"successor_key": key("title", obs[0]), "responsibility_version": rs.RESPONSIBILITY_VERSION,
                     "source_kind": "STAFF_TITLE", "observation_id": obs[0], "capture_path": obs[1],
                     "person": obs[2], "source_title": title, "program_id": obs[4], "season": obs[5],
                     "evidence_code": code, "disposition": disposition or rs.MENTION_ONLY})
    return rows, {"titles_examined": examined, "titles_with_a_mention": len(rows)}


def scan_captures(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], dict[str, int]]:
    bound = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT capture_path, MIN(program_id), MIN(season) FROM staff_observation GROUP BY capture_path")}
    titled = {r[0] for r in conn.execute("SELECT capture_path, source_title FROM staff_observation")
              if rs.TITLE_PLAY_CALLER.search(r[1] or "")}
    rows, read = [], 0
    for line in CAPTURES.read_text(encoding="utf-8").splitlines():
        capture = json.loads(line).get("capture_path")
        path = Path(capture or "")
        if not path.is_file():
            continue
        read += 1
        text = rs.html_rendered(path.read_text(encoding="utf-8", errors="replace"))
        for match in rs.MENTION.finditer(text):
            program, season = bound.get(capture, (None, None))
            window = text[max(0, match.start() - 160): match.end() + 120]
            if capture in titled:
                verdict = {"disposition": rs.TEXT_COPY,
                           "reasons": ["the capture's own staff title states this; the text is a copy of it"]}
            else:
                sentence, offset = rs.sentence_at(text, match.start(), match.end())
                verdict = rs.classify_sentence(sentence, offset, match.group(0), page_subject=None)
            rows.append({"successor_key": key("capture", capture, match.start()),
                         "responsibility_version": rs.RESPONSIBILITY_VERSION, "source_kind": "OFFICIAL_CAPTURE_TEXT",
                         "capture_path": capture, "offset_in_rendered_text": match.start(),
                         "matched_text": match.group(0), "quoted_span": window, "program_id": program,
                         "season": season, **verdict})
    return rows, {"captures_read": read, "capture_mentions": len(rows)}


def scan_encyclopedia() -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows, pages, with_mentions = [], 0, 0
    for name in sorted(os.listdir(WIKIMEDIA)):
        try:
            payload = json.loads((WIKIMEDIA / name).read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        found = ((payload or {}).get("query") or {}).get("pages") if isinstance(payload, dict) else None
        if isinstance(found, dict):
            found = list(found.values())
        for page in found or []:
            revisions = page.get("revisions") or []
            if not revisions:
                continue
            pages += 1
            slot = (revisions[0].get("slots") or {}).get("main") or {}
            raw = slot.get("*") or slot.get("content") or ""
            if not rs.MENTION.search(raw):
                continue
            with_mentions += 1
            title = str(page.get("title") or "")
            # "Blake Anderson (American football)" is a person page: the
            # disambiguator is not part of the name and must not exclude it.
            core = re.sub(r"\s*\(.*?\)\s*$", "", title)
            subject = None if PERSON_PAGE_EXCLUDE.search(core) else core
            text = rs.wiki_plain(raw)
            for match in rs.MENTION.finditer(text):
                sentence, offset = rs.sentence_at(text, match.start(), match.end())
                verdict = rs.classify_sentence(sentence, offset, match.group(0), page_subject=subject)
                rows.append({"successor_key": key("wiki", name, match.start()),
                             "responsibility_version": rs.RESPONSIBILITY_VERSION,
                             "source_kind": "ENCYCLOPEDIA_REVISION", "wiki_file": name, "page_title": title,
                             "page_kind": "PERSON" if subject else "NON_PERSON",
                             "revision_id": revisions[0].get("revid"), "revision_timestamp": revisions[0].get("timestamp"),
                             "offset_in_plain_text": match.start(), "matched_text": match.group(0),
                             "sentence": sentence, **verdict,
                             "program_as_written": None, "program_resolution": "NOT_ATTEMPTED_AS_WRITTEN_ONLY",
                             "known_at": "UNKNOWN_RETRIEVED_REVISION_NOT_PIT"})
    return rows, {"encyclopedia_pages_read": pages, "pages_with_a_mention": with_mentions,
                  "encyclopedia_mentions": len(rows)}


# ------------------------------------------------------------------ scheme
def scheme_successor(conn: sqlite3.Connection, out_dir: Path) -> dict[str, Any]:
    conflicts = conn.execute("SELECT conflict_id, page_title, season, side, conflict_texts, program_resolution_state "
                             "FROM scheme_conflict").fetchall()
    conflict_keys = {(c[1], c[3]) for c in conflicts}
    categories, states, cross_side = collections.Counter(), collections.Counter(), []
    residual_states = collections.Counter()
    path = out_dir / "R37_06_SCHEME_ROWS.jsonl"
    total = 0
    with _bas_atomic.open_write(path, "w", encoding="utf-8", newline="\n") as sink:
        for row in conn.execute("SELECT scheme_assertion_id, program_id, season, side, source_text, normalized_families, "
                                "source_disposition, state, evidence_tier, official_corroboration, page_title, "
                                "wikimedia_revision, pit_admitted, inferred_from_title FROM scheme_assertion "
                                "ORDER BY scheme_assertion_id"):
            total += 1
            families = json.loads(row[5] or "[]")
            category = OFFENSIVE if row[3] == "OFFENSE" else DEFENSIVE if row[3] == "DEFENSE" else None
            categories[category] += 1
            if row[7] in SCHEME_STATES:
                states[row[7]] += 1
            else:
                residual_states[row[7]] += 1
            wrong = [f for f in families if f != "MULTIPLE" and (
                (category == OFFENSIVE and DEFENSIVE_FAMILY.match(f)) or
                (category == DEFENSIVE and OFFENSIVE_FAMILY.match(f) and not DEFENSIVE_FAMILY.match(f)))]
            if wrong:
                cross_side.append({"scheme_assertion_id": row[0], "side": row[3], "families": wrong,
                                   "source_text": row[4]})
            sink.write(json.dumps({
                "scheme_assertion_id": row[0], "category": category, "program_id": row[1], "season": row[2],
                "effective_interval": f"season {row[2]}" if row[2] is not None else "UNKNOWN",
                "source_role_unit": f"team-season infobox field {row[3].lower()}" if row[3] else None,
                "person": "NOT_APPLICABLE_TEAM_SEASON_INFOBOX", "source_text": row[4], "normalized_families": families,
                "normalization_version": NORMALIZATION_VERSION, "source_disposition": row[6], "state": row[7],
                "evidence_tier": row[8], "official_corroboration": row[9], "page_title": row[10],
                "wikimedia_revision": row[11], "known_at": "UNKNOWN_RETRIEVED_REVISION_NOT_PIT",
                "conflict_state": "SOURCE_TEXT_CONFLICT" if (row[10], row[3]) in conflict_keys else "NONE_RECORDED",
                "pit_admitted": bool(row[12]), "inferred_from_title": bool(row[13]),
                "is_realized_scheme": False, "is_play_calling_responsibility": False,
            }, sort_keys=True) + "\n")
    return {"rows": total, "path": str(path), "sha256": sha256_file(path),
            "categories": {k: v for k, v in categories.items()},
            "absent_categories": ABSENT_CATEGORIES,
            "states_over_declared_enum": dict(states), "states_outside_enum": dict(residual_states),
            "conflicts_preserved": [{"conflict_id": c[0], "page_title": c[1], "season": c[2], "side": c[3],
                                     "texts": json.loads(c[4]), "program_resolution_state": c[5]} for c in conflicts],
            "families_on_the_other_side": {"count": len(cross_side), "rows": cross_side[:100]},
            "normalization_version": NORMALIZATION_VERSION}


# ------------------------------------------------------------------ sample
def blind_sample(rows: list[dict[str, Any]], out_dir: Path, *, name: str, target: int,
                 exclude: set[str] | None = None, salt: str = "") -> dict[str, Any]:
    """Mentions across sources, eras and dispositions, written WITHOUT dispositions.

    The tuning sample (``salt=""``) was drawn once, labelled, and used to
    write the rules. The held-out sample excludes every tuning key and orders
    by a salted digest, so it measures the final rules on mentions nobody
    looked at while writing them.
    """

    exclude = exclude or set()
    pool: dict[tuple, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        if row["source_kind"] not in ("ENCYCLOPEDIA_REVISION", "STAFF_TITLE") or row["successor_key"] in exclude:
            continue
        years = row.get("years_as_written") or ([str(row["season"])] if row.get("season") else [])
        decade = f"{years[0][:3]}0s" if years else "undated"
        pool[(row["source_kind"], row["disposition"], decade)].append(row)
    picked = []
    strata = sorted(pool)
    round_index = 0
    while len(picked) < target and any(len(pool[s]) > round_index for s in strata):
        for stratum in strata:
            ordered = sorted(pool[stratum], key=lambda r: hashlib.sha256((salt + r["successor_key"]).encode()).hexdigest()
                             if salt else r["successor_key"])
            if round_index < len(ordered) and len(picked) < target:
                picked.append(ordered[round_index])
        round_index += 1
    blind = [{"successor_key": r["successor_key"], "source_kind": r["source_kind"],
              "page_title": r.get("page_title"), "page_kind": r.get("page_kind"),
              "text": r.get("sentence") or r.get("source_title"), "matched_text": r.get("matched_text"),
              "program_id": r.get("program_id"), "season": r.get("season")} for r in picked]
    path = out_dir / name
    with _bas_atomic.open_write(path, "w", encoding="utf-8", newline="\n") as sink:
        for row in blind:
            sink.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return {"path": str(path), "sha256": sha256_file(path), "rows": len(blind), "excluded": len(exclude),
            "strata_drawn": len({(r["source_kind"], r.get("disposition")) for r in picked}),
            "rule": "written without dispositions; labels are recorded before any comparison"}


def carry_tuning_sample(source: Path | None, out_dir: Path,
                        name: str = "R37_06_CONTEXT_SAMPLE_BLIND.jsonl") -> tuple[dict[str, Any], set[str]]:
    """Keep a labelled sample byte for byte; never redraw it."""

    if source is None:
        return {"state": "NO_TUNING_SAMPLE_GIVEN"}, set()
    target = out_dir / name
    data = source.read_bytes()
    if source.resolve() != target.resolve():
        _bas_atomic.write_bytes(target, data)
    keys = {json.loads(line)["successor_key"] for line in data.decode("utf-8").splitlines() if line.strip()}
    return {"path": str(target), "sha256": hashlib.sha256(data).hexdigest(), "rows": len(keys),
            "carried_from": str(source), "rule": "the tuning sample is carried, not redrawn"}, keys


THIRD_NAME = "R37_06_CONTEXT_SAMPLE_THIRD_BLIND.jsonl"


def third_sample(rows: list[dict[str, Any]], out_dir: Path, exclude: set[str]) -> dict[str, Any]:
    """W37R-33: a third blind sample, drawn once after the v37.2 rules froze.

    It excludes every tuning and held-out key. An existing third sample is
    carried, never redrawn, so its labels always refer to the same mentions.
    """

    existing = out_dir / THIRD_NAME
    if existing.is_file():
        meta, _keys = carry_tuning_sample(existing, out_dir, THIRD_NAME)
        return {**meta, "rule": "carried; a labelled sample is never redrawn"}
    if not exclude:
        raise SystemExit("a third sample needs both earlier samples to exclude")
    drawn = blind_sample(rows, out_dir, name=THIRD_NAME, target=HELDOUT_TARGET, exclude=exclude, salt="third-v37.2")
    return {**drawn, "salt": "third-v37.2", "drawn_after_rules": rs.RESPONSIBILITY_VERSION}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=ATTEMPT / "evidence" / "repairs")
    parser.add_argument("--tuning-sample", type=Path, default=None,
                        help="the labelled tuning sample to carry byte for byte and exclude from the held-out draw")
    parser.add_argument("--heldout-sample", type=Path, default=None,
                        help="a labelled held-out sample to carry byte for byte instead of drawing one")
    parser.add_argument("--third-sample", action="store_true",
                        help="draw (or, if it exists, carry) a third blind sample excluding both earlier samples")
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{args.release}?mode=ro", uri=True)

    lineage, lineage_meta = predecessor_lineage(conn)
    tuning_meta, tuning_keys = carry_tuning_sample(args.tuning_sample, args.out_dir)
    heldout_name = "R37_06_CONTEXT_SAMPLE_HELDOUT_BLIND.jsonl"
    heldout_carried, heldout_keys = (carry_tuning_sample(args.heldout_sample, args.out_dir, heldout_name)
                                     if args.heldout_sample else ({}, set()))
    titles, title_meta = scan_titles(conn)
    captures, capture_meta = scan_captures(conn)
    wiki, wiki_meta = scan_encyclopedia()
    rows = lineage + titles + captures + wiki
    path = args.out_dir / "R37_06_RESPONSIBILITY_ROWS.jsonl"
    with _bas_atomic.open_write(path, "w", encoding="utf-8", newline="\n") as sink:
        for row in rows:
            sink.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")

    def over_enum(subset: list[dict[str, Any]]) -> dict[str, int]:
        counts = collections.Counter(r["disposition"] for r in subset)
        outside = {k: v for k, v in counts.items() if k not in rs.DISPOSITIONS}
        if outside:
            raise SystemExit(f"dispositions outside the declared enum: {outside}")
        return {d: counts.get(d, 0) for d in rs.DISPOSITIONS}

    current = [r for r in rows if r["disposition"] in rs.CURRENT_RESPONSIBILITY]
    # One responsibility can be supported by several rows (a predecessor row
    # and the same title found by the population scan; repeated captures of
    # one page). Episodes are counted once, with every supporting row named.
    episodes: dict[tuple, list[str]] = collections.defaultdict(list)
    for row in current:
        episodes[(row.get("person"), row.get("program_id"), row.get("season"))].append(row["successor_key"])
    receipt = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-06",
        "responsibility_version": rs.RESPONSIBILITY_VERSION, "predecessor_version": rs.PREDECESSOR_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "release": {"path": str(args.release), "sha256": sha256_file(args.release)},
        "lineage": {**lineage_meta, "dispositions": over_enum(lineage),
                    "predecessor_dispositions": dict(collections.Counter(r["predecessor_disposition"] for r in lineage))},
        "population": {**title_meta, **capture_meta, **wiki_meta,
                       "titles": over_enum(titles), "captures": over_enum(captures), "encyclopedia": over_enum(wiki)},
        "current_responsibility_rows": [{k: r.get(k) for k in ("successor_key", "person", "program_id", "season",
                                                               "source_title", "observation_id", "source_kind")}
                                        for r in current],
        "current_responsibility_episodes": [{"person": p, "program_id": g, "season": y, "supporting_rows": keys}
                                            for (p, g, y), keys in sorted(episodes.items(), key=str)],
        "rows": {"path": str(path), "sha256": sha256_file(path), "count": len(rows)},
        "scheme": scheme_successor(conn, args.out_dir),
        "tuning_sample": tuning_meta,
        "heldout_sample": heldout_carried or blind_sample(rows, args.out_dir, name=heldout_name,
                                                          target=HELDOUT_TARGET, exclude=tuning_keys,
                                                          salt="heldout-v37.1"),
        "third_sample": third_sample(rows, args.out_dir, tuning_keys | heldout_keys) if args.third_sample else None,
        "boundaries": [
            "Only an official staff title stating play-calling, bound to a program and season, is a current "
            "responsibility; encyclopedia statements are historical candidates as written.",
            "A coordinator or head-coach title is never a play-calling statement.",
            "Source-stated schemes are candidate historical evidence, not official confirmation, realized scheme "
            "or causal proof.",
        ],
    }
    out = args.out_dir / "R37_06_SCHEME_RESPONSIBILITY.json"
    _bas_atomic.write_text(out, json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print("lineage:", receipt["lineage"]["dispositions"])
    print("population:", {k: v for k, v in receipt["population"].items() if not isinstance(v, dict)})
    print("encyclopedia:", {k: v for k, v in receipt["population"]["encyclopedia"].items() if v})
    print("current responsibility episodes:", receipt["current_responsibility_episodes"])
    print("scheme:", receipt["scheme"]["categories"], receipt["scheme"]["states_outside_enum"],
          "cross-side:", receipt["scheme"]["families_on_the_other_side"]["count"])
    print("tuning sample:", receipt["tuning_sample"].get("rows"), "| held-out sample:", receipt["heldout_sample"]["rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
