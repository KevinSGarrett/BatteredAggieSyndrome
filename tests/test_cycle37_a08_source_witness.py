"""Cycle #37 — Attempt #8 — MF37A07-01: a lineage anchor's witness must be the source field its row's identity names.

The Attempt 7 manager swapped the reciprocal default and Attempt 4 edges of Fred Mariani's 1974 graduate-assistant row
and his 2009 Rutgers row, then enlarged both rows' genuine team and years spans to one envelope running from the first
job's parameter to the sixth's. Each enlarged span was an exact substring of the revision and overlapped both jobs'
fields, so every anchor agreed and the installed consumer served seven rows. These cases build one realistic revision
in the parser's own forms -- numbered fields (a two-interval field, an empty field, a years-only field, a field whose
value holds an HTML comment with a bar), and a ``pastcoaching`` list with a bullet line, a nested line under it and an
employer line with role lines -- its delivered (v37.2), Attempt 4 (v37.4) and Attempt 5 (v37.5) rows, and prove through
``attach_successor`` and the parser's units (``career_witness.source_units``) that:

* every genuine form attaches and serves, rows with no recorded span stay absent fields, and the units the verifier
  derives are exactly the spans the parser writes for this revision (``career_infobox.career_rows``);
* each substitution, built independently from the genuine fixture and resealed as a careful forger would, is refused
  for its source-field cause (``REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH``) through the Attempt 5 and the
  Attempt 4 format entrypoints: the manager's enlarged envelope with the reciprocal swap, a year-only, a team-only and
  a both-fields envelope, a full-page span, a boundary shifted into the next parameter, a partial (shrunk) span, a
  witness moved onto another job's genuine field (same role, another period), a list line enlarged over its neighbour,
  and an Attempt 4 file row carrying an envelope;
* the refusal comes from the witness, not from a stale hash: each forgery reseals every ledger and pins its digest.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.cycle37 import career_infobox as ci  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402
from aggie_analytics.cycle37 import career_witness as cw  # noqa: E402

PAGE, REVISION, TITLE, QID = 61958463, 1368703693, "Fixture Coach (American football)", "Q61958463"
GA = "[[Saint Joseph's Pumas football|Saint Joseph's (IN)]] ([[Graduate assistant|GA]])"
DFO = "[[Rutgers Scarlet Knights football|Rutgers]] (DFO)"
OC = "[[Lehigh Mountain Hawks football|Lehigh]] (OC)"
IONA = "[[Iona Gaels football|Iona]] <!-- head coach | per the 1998 media guide -->"
CLE = "[[Cleveland Browns]] (2005–2008)"
CLE_NESTED = "Defensive backs coach (2007–2008)"
PHI = "[[Philadelphia Eagles]] (2015–2019)<br>Defensive backs coach (2015–2016)<br>Passing game coordinator (2017–2019)"
TEXT = ("{{Infobox college coach\n| name = Fixture Coach\n"
        "| coach_years1 = 1974\n| coach_team1 = " + GA + "\n"
        "| coach_years2 = 1984, 1986–1987\n| coach_team2 = " + OC + "\n"
        "| coach_years3 = 1990–1993\n| coach_team3 = " + OC + "\n"
        "| coach_years4 = 1998–2008\n| coach_team4 = " + IONA + "\n"
        "| coach_years5 = \n| coach_team5 = \n"
        "| coach_years6 = 2009–?\n| coach_team6 = " + DFO + "\n"
        "| coach_years7 = 2012\n"
        "| pastcoaching =\n* " + CLE + "\n** " + CLE_NESTED + "\n* " + PHI + "\n}}\n")
PARSED = {(row["family"], row["index"]): row for row in ci.career_rows(TEXT)["rows"]}


#: The same revision read the way the v37.2 and v37.4 parsers split it (comments and nowiki are not literal text).
OLD_UNITS = cw.source_units(TEXT, literal_blanking=False)


def span(family_index: tuple[str, int], field: str, *, old: bool = False) -> list[int] | None:
    """The span the parser writes for this revision -- the v37.5 parser's, or (``old``) the v37.2/v37.4 reading."""

    if old:
        unit = OLD_UNITS[family_index][0]
        value = unit.team if field == "team" else unit.years
    else:
        value = PARSED[family_index][f"{field}_span"]
    return list(value) if value else None


def _id(prefix: str, row: int, interval: int = 0) -> str:
    return f"{prefix}:{PAGE}:{REVISION}:COACHING:{row}:{interval}"


def _table(path: Path, table: str, columns: tuple[str, ...], rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE {table} ({', '.join(chr(34) + c + chr(34) for c in columns)})")
    for row in rows:
        conn.execute(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in columns)})", [row.get(c) for c in columns])
    conn.commit()
    conn.close()


#: (row index, interval, years as written) of every job; the list rows' dates sit inside their lines.
JOBS = [(1, 0, "1974"), (2, 0, "1984"), (2, 1, "1986–1987"), (3, 0, "1990–1993"), (4, 0, "1998–2008"), (5, 0, None),
        (6, 0, "2009–?"), (7, 0, "2012"), (1001, 0, "2005–2008"), (1002, 0, "2007–2008"), (1003, 0, "2015–2019"),
        (100301, 0, "2015–2016"), (100302, 0, "2017–2019")]


class SourceWitnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        raw = self.root / "raw.json"
        raw.write_bytes(json.dumps({"query": {"pages": {str(PAGE): {
            "pageid": PAGE, "title": TITLE, "pageprops": {"wikibase_item": QID},
            "revisions": [{"revid": REVISION, "slots": {"main": {"*": TEXT}}}]}}}}).encode("utf-8"))
        page = {"pageid": PAGE, "revision": str(REVISION), "family": "COACHING", "page_title": TITLE,
                "person_display": "Fixture Coach", "wikidata_qid": QID, "raw_file": str(raw),
                "raw_file_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "wikitext_sha256": hashlib.sha256(TEXT.encode("utf-8")).hexdigest(), "ongoing": 0,
                "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "assignments": "[]"}

        def fields(index: int, *, years: bool, old: bool = False) -> dict:
            team = span(("COACHING", index), "team", old=old)
            when = span(("COACHING", index), "years", old=old) if (old and index < 1000) else span(
                ("COACHING", index), "years")
            return {"team_raw": TEXT[team[0]:team[1]] if team else None,
                    "team_char_span": json.dumps(team) if team else None,
                    "years_raw": TEXT[when[0]:when[1]] if when else PARSED[("COACHING", index)]["years_raw"],
                    "years_char_span": json.dumps(when) if (when and years) else None}

        # The delivered rows (v37.2): one row per field interval, list lines without years spans; no role-line rows
        # (the employer line 1003 is one row). The Attempt 4 rows are the same, with their own lineage.
        old_jobs = [job for job in JOBS if job[0] < 100_000]
        self.old = {_id("R37-05", i, k): {**page, **fields(i, years=i < 1000, old=True),
                                           "episode_id": _id("R37-05", i, k),
                                           "row_index": i, "interval_index": k, "years_as_written": w}
                    for i, k, w in old_jobs}
        self.a4_rows = {pid.replace("R37-05", "C37A04"): {**row, "episode_id": pid.replace("R37-05", "C37A04"),
                                                          "predecessor_episode_ids": json.dumps([pid]),
                                                          "lineage_state": cs.DERIVED, "disposition": cs.UNCHANGED}
                        for pid, row in self.old.items()}
        # Attempt 5: every row with its own years span; the employer line's role lines are rows of their own that
        # derive from the employer line's delivered row.
        self.episodes = []
        for i, k, w in JOBS:
            parent = _id("R37-05", i if i < 100_000 else i // 100, k if i < 100_000 else 0)
            self.episodes.append({**page, **fields(i, years=True), "episode_id": _id("C37A05", i, k), "row_index": i,
                                  "interval_index": k, "years_as_written": w,
                                  "predecessor_episode_ids": json.dumps([parent]), "lineage_state": cs.DERIVED,
                                  "disposition": cs.CORRECTED,
                                  "a04_episode_ids": json.dumps([parent.replace("R37-05", "C37A04")]),
                                  "a04_lineage_state": cs.A04_DERIVED, "a04_disposition": cs.CORRECTED,
                                  "date_basis": "FIXTURE", "uncertainty_classes": "[]"})
        self.predecessor = self.root / "predecessor.sqlite"
        _table(self.predecessor, cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, list(self.old.values()))
        self.a4 = self.root / "a04.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ building (possibly forged) successors
    def _dispositions(self, episodes: list[dict], key: str, owners: dict, id_key: str, list_key: str,
                      digest) -> list[dict]:
        edges: dict[str, list[str]] = {}
        for row in episodes:
            for parent in json.loads(row[key]):
                edges.setdefault(parent, []).append(row["episode_id"])
        state_of = {row["episode_id"]: row["disposition" if key == "predecessor_episode_ids" else "a04_disposition"]
                    for row in episodes}
        rows = []
        for identity, owner in owners.items():
            children = sorted(edges.get(identity, []))
            states = {state_of[child] for child in children}
            rows.append({id_key: identity,
                         "disposition": cs.NOT_PRODUCED if not children else (states.pop() if len(states) == 1
                                                                              else cs.CORRECTED),
                         list_key: json.dumps(children), "changed_fields": "{}", digest[0]: digest[1](owner),
                         "screens": "[]", "reason": "fixture"})
        return rows

    def _seal(self, path: Path, fmt: str, version: str, ledgers, extra: dict) -> None:
        conn = sqlite3.connect(path)
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT, value TEXT)")
        identity = {"format_version": fmt, "successor_version": version,
                    "predecessor_database_sha256": cs.sha256_file(self.predecessor),
                    "predecessor_table": cs.PREDECESSOR_TABLE, "predecessor_row_count": str(len(self.old)),
                    "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
                    "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0", **extra}
        for table, columns, key in ledgers:
            digest, count = cs.table_ledger(conn, table, columns, key)
            identity[f"ledger::{table}::sha256"], identity[f"ledger::{table}::rows"] = digest, str(count)
        conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
        conn.commit()
        conn.close()

    def successor(self, name: str, episodes: list[dict] | None = None) -> Path:
        episodes = [dict(r) for r in (self.episodes if episodes is None else episodes)]
        path = self.root / name
        _table(path, cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, episodes)
        _table(path, cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, self._dispositions(
            episodes, "predecessor_episode_ids", self.old, "predecessor_episode_id", "successor_episode_ids",
            ("predecessor_row_sha256", cs.predecessor_row_digest)))
        _table(path, cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, self._dispositions(
            episodes, "a04_episode_ids", self.a4_rows, "a04_episode_id", "a05_episode_ids",
            ("a04_row_sha256", cs.episode_row_digest)))
        self._seal(path, cs.A05_FORMAT_VERSION, cs.A05_SUCCESSOR_VERSION,
                   ((cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, "episode_id"),
                    (cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id"),
                    (cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, "a04_episode_id")),
                   {"a04_successor_path": str(self.a4), "a04_successor_sha256": cs.sha256_file(self.a4),
                    "a04_successor_row_count": str(len(self.a4_rows))})
        return path

    def a4_format(self, name: str, rows: list[dict]) -> Path:
        path = self.root / name
        _table(path, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, rows)
        _table(path, cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, self._dispositions(
            rows, "predecessor_episode_ids", self.old, "predecessor_episode_id", "successor_episode_ids",
            ("predecessor_row_sha256", cs.predecessor_row_digest)))
        self._seal(path, cs.FORMAT_VERSION, cs.SUCCESSOR_VERSION,
                   ((cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, "episode_id"),
                    (cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id")), {})
        return path

    def attach(self, successor: Path) -> dict:
        conn = sqlite3.connect(self.predecessor.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            binding = cs.attach_successor(conn, successor, database=self.predecessor,
                                          expected_sha256=cs.sha256_file(successor))
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME} ORDER BY episode_id")]
        finally:
            conn.close()
        verifier = cs.RawBytesVerifier()
        for row in rows:
            verifier.verify(row)
        binding["_rows"] = rows
        return binding

    def refused(self, successor: Path, *causes: str) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            self.attach(successor)
        self.assertEqual(caught.exception.code, cs.REFUSED_SOURCE_FIELD, str(caught.exception))
        for cause in causes:
            self.assertIn(cause, str(caught.exception))
        return str(caught.exception)

    def copy(self) -> list[dict]:
        return [dict(r) for r in self.episodes]

    def row(self, episodes: list[dict], index: int, interval: int = 0) -> dict:
        return next(r for r in episodes if r["episode_id"] == _id("C37A05", index, interval))

    @staticmethod
    def envelope(victim: dict, *, team: tuple[int, int] | None = None, years: tuple[int, int] | None = None) -> None:
        """Replace a row's witness with a genuine substring of the revision (its raw text reproduces exactly)."""

        if team is not None:
            victim["team_char_span"], victim["team_raw"] = json.dumps(list(team)), TEXT[team[0]:team[1]]
        if years is not None:
            victim["years_char_span"], victim["years_raw"] = json.dumps(list(years)), TEXT[years[0]:years[1]]

    def swap(self, episodes: list[dict], a: int, b: int) -> None:
        """The manager's recipe: the two rows' reciprocal default and Attempt 4 edges, with their disposition texts."""

        x, y = self.row(episodes, a), self.row(episodes, b)
        for field in ("predecessor_episode_ids", "disposition", "a04_episode_ids", "a04_disposition"):
            x[field], y[field] = y[field], x[field]

    # ------------------------------------------------------------------ the units are the parser's
    def test_the_verifiers_units_are_exactly_the_spans_the_parser_writes(self) -> None:
        units = cw.source_units(TEXT)
        for (family, index), row in PARSED.items():
            with self.subTest(index=index):
                problems, form = cw.witness_problems(
                    {"family": family, "row_index": index, "team_char_span": json.dumps(row["team_span"]),
                     "years_char_span": json.dumps(row["years_span"]) if row["years_span"] else None}, units)
                self.assertEqual(problems, [], (index, form))
        forms = {cw.witness_problems({"family": "COACHING", "row_index": i,
                                      "team_char_span": json.dumps(span(("COACHING", i), "team"))}, units)[1]
                 for i in (1, 1001, 1002, 100301)}
        self.assertEqual(forms, {cw.PARAMETER, cw.LIST_LINE, cw.NESTED_LINE, cw.ROLE_LINE})
        # The comment's bar is literal text in v37.5 and a split in v37.2/v37.4: each reading has its own units.
        self.assertTrue(cw.literals_change_structure(TEXT))
        iona = span(("COACHING", 4), "team")
        self.assertEqual(TEXT[iona[0]:iona[1]], IONA)
        self.assertNotEqual(cw.source_units(TEXT, literal_blanking=False)[("COACHING", 4)][0].team, tuple(iona))

    # ------------------------------------------------------------------ accepted
    def test_every_genuine_form_attaches_and_serves(self) -> None:
        binding = self.attach(self.successor("genuine.sqlite"))
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        witnessed = lineage["source_witnesses_proved"]
        self.assertEqual(witnessed["successor"]["proved_by_form"],
                         {"PARAMETER": 8, "LIST_LINE": 2, "NESTED_LINE": 1, "ROLE_LINE": 2})
        self.assertEqual(witnessed["delivered_predecessor"]["rows_proved"], len(self.old))   # an empty field too
        self.assertEqual(lineage["a04_source_witnesses_proved"]["relation"], "Attempt 4 file")
        self.assertEqual(lineage["parent_edges_bound_to_source_field"]["edges"], len(JOBS))
        self.assertEqual(len(binding["_rows"]), len(JOBS))
        served = {r["episode_id"]: r for r in binding["_rows"]}
        self.assertEqual(served[_id("C37A05", 4)]["team_raw"], IONA)                 # a comment with a bar, served
        self.assertEqual(served[_id("C37A05", 100302)]["team_raw"], "Passing game coordinator (2017–2019)")
        self.assertIsNone(served[_id("C37A05", 7)]["team_char_span"])                # a years-only field
        # The Attempt 4 format entrypoint attaches its genuine rows under the v37.4 reading.
        self.assertEqual(len(self.attach(self.a4_format("a4-genuine.sqlite",
                                                        [dict(r) for r in self.a4_rows.values()]))["_rows"]),
                         len(self.a4_rows))

    def test_a_row_that_records_no_span_is_an_absent_field_not_a_witness(self) -> None:
        episodes = self.copy()
        victim = self.row(episodes, 5)
        self.assertTrue(all(json.loads(victim[f])[0] == json.loads(victim[f])[1]
                            for f in ("team_char_span", "years_char_span")))          # an empty field: zero-length
        for field in ("team_char_span", "years_char_span"):
            victim[field] = None
        binding = self.attach(self.successor("absent.sqlite", episodes))
        self.assertEqual(binding["lineage_proved_independently_of_the_ledgers"]["source_witnesses_proved"]
                         ["successor"]["proved_by_form"].get("PARAMETER"), 7)

    # ------------------------------------------------------------------ refused for the source-field cause
    def test_the_managers_enlarged_envelope_with_the_reciprocal_swap_is_refused(self) -> None:
        episodes = self.copy()
        self.swap(episodes, 1, 6)
        lo_team, hi_team = span(("COACHING", 1), "team")[0], span(("COACHING", 6), "team")[1]
        lo_years, hi_years = span(("COACHING", 1), "years")[0], span(("COACHING", 6), "years")[1]
        for index in (1, 6):
            self.envelope(self.row(episodes, index), team=(lo_team, hi_team), years=(lo_years, hi_years))
        message = self.refused(self.successor("envelope.sqlite", episodes), "TEAM_NOT_SOURCE_UNIT",
                               "YEARS_NOT_SOURCE_UNIT", _id("C37A05", 1))

    def test_year_only_team_only_and_both_field_envelopes_are_refused(self) -> None:
        one, six = span(("COACHING", 1), "years"), span(("COACHING", 6), "years")
        team_one, team_six = span(("COACHING", 1), "team"), span(("COACHING", 6), "team")
        for label, change, cause in (("year-only", {"years": (one[0], six[1])}, "YEARS_NOT_SOURCE_UNIT"),
                                     ("team-only", {"team": (team_one[0], team_six[1])}, "TEAM_NOT_SOURCE_UNIT"),
                                     ("both", {"years": (one[0], six[1]), "team": (team_one[0], team_six[1])},
                                      "TEAM_NOT_SOURCE_UNIT")):
            with self.subTest(label=label):
                episodes = self.copy()
                self.swap(episodes, 1, 6)
                self.envelope(self.row(episodes, 1), **change)
                self.envelope(self.row(episodes, 6), **change)
                self.refused(self.successor(f"{label}.sqlite", episodes), cause)

    def test_a_full_page_a_shifted_boundary_and_a_partial_span_are_refused(self) -> None:
        team = span(("COACHING", 1), "team")
        years = span(("COACHING", 1), "years")
        for label, change, cause in (("full-page", {"team": (0, len(TEXT))}, "TEAM_NOT_SOURCE_UNIT"),
                                     ("boundary-into-next-parameter", {"years": (years[0], years[1] + 6)},
                                      "YEARS_NOT_SOURCE_UNIT"),
                                     ("boundary-from-previous-parameter", {"team": (team[0] - 4, team[1])},
                                      "TEAM_NOT_SOURCE_UNIT"),
                                     ("partial-span", {"team": (team[0], team[0] + 20)}, "TEAM_NOT_SOURCE_UNIT")):
            with self.subTest(label=label):
                episodes = self.copy()
                self.envelope(self.row(episodes, 1), **change)
                self.refused(self.successor(f"{label}.sqlite", episodes), cause)

    def test_a_witness_moved_onto_another_jobs_genuine_field_is_refused(self) -> None:
        # Rows 2 and 3 are both "Lehigh (OC)": the same role, another period. Row 3's genuine witness moved onto row 2
        # with row 2's edges pointed at row 3's parents is every anchor agreeing -- and not row 2's own field.
        episodes = self.copy()
        victim, donor = self.row(episodes, 2, 0), self.row(episodes, 3)
        for field in ("team_char_span", "team_raw", "years_char_span", "years_raw"):
            victim[field] = donor[field]
        self.refused(self.successor("same-role-other-period.sqlite", episodes), "TEAM_NOT_SOURCE_UNIT", _id("C37A05", 2))

    def test_a_list_line_enlarged_over_its_neighbour_is_refused(self) -> None:
        episodes = self.copy()
        first, nested = span(("COACHING", 1001), "team"), span(("COACHING", 1002), "team")
        self.envelope(self.row(episodes, 1001), team=(first[0], nested[1]))
        self.refused(self.successor("list-envelope.sqlite", episodes), "TEAM_NOT_SOURCE_UNIT")
        # A role line moved onto its sibling role line is refused too.
        episodes = self.copy()
        self.envelope(self.row(episodes, 100301), team=tuple(span(("COACHING", 100302), "team")))
        self.refused(self.successor("role-line-moved.sqlite", episodes), "TEAM_NOT_SOURCE_UNIT", _id("C37A05", 100301))

    def test_the_envelope_through_the_attempt4_format_entrypoint_is_refused(self) -> None:
        rows = [dict(r) for r in self.a4_rows.values()]
        a, b = (next(r for r in rows if r["episode_id"] == _id("C37A04", n)) for n in (1, 6))
        a["predecessor_episode_ids"], b["predecessor_episode_ids"] = b["predecessor_episode_ids"], a["predecessor_episode_ids"]
        lo, hi = span(("COACHING", 1), "team")[0], span(("COACHING", 6), "team")[1]
        for row in (a, b):
            self.envelope(row, team=(lo, hi))
        self.refused(self.a4_format("a4-envelope.sqlite", rows), "TEAM_NOT_SOURCE_UNIT", "parser BAS-CAREER-INFOBOX-v37.4")

    def test_an_attempt4_file_row_carrying_an_envelope_is_refused(self) -> None:
        # Every Attempt 5 row is genuine; the declared Attempt 4 file (its digest the successor's own statement) holds
        # an enlarged witness for the row an edge names.
        victim = self.a4_rows[_id("C37A04", 1)]
        self.envelope(victim, team=(span(("COACHING", 1), "team")[0], span(("COACHING", 6), "team")[1]))
        self.a4 = self.root / "a04-envelope.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))
        self.refused(self.successor("a4-file-envelope.sqlite"), "Attempt 4 file", "TEAM_NOT_SOURCE_UNIT")

    def test_each_refusal_left_the_genuine_fixture_attachable(self) -> None:
        for name in ("after-1.sqlite", "after-2.sqlite"):
            self.assertEqual(len(self.attach(self.successor(name))["_rows"]), len(JOBS))


if __name__ == "__main__":
    unittest.main()
