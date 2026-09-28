"""Cycle #37 — Attempt #10 — MF37A09-01: inside one source field, a lineage edge joins the interval its identities name.

The Attempt 9 manager took Walter Camp's two Stanford rows (``coachyears2 = 1892, 1894–1895``), swapped their reciprocal
default and Attempt 4 edges, set their ``years_as_written`` to NULL (or copied the other row's text) and resealed. The
v5 verifier compared that text by containment and treated blank text as agreement: the installed console script, the
installed module and the source module served four rows. Every row of the field shares its page, revision, capture,
source unit and spans, so none of those says which interval a row is; text a row carries about itself proves nothing.

These cases build one realistic revision in the parser's own forms -- a two-interval numbered field (the Walter Camp
form), a single-interval field, a two-interval field with an unknown end that the delivered parser read as a bare year
(a legitimate correction), a field the delivered parser split into three intervals that v37.4/v37.5 read as two (a
legitimate restructure) and a ``pastcoaching`` list line stating two intervals -- with its delivered (v37.2), Attempt 4
(v37.4) and Attempt 5 (v37.5) rows. Attempt 5 rows carry exactly what the parser writes (``career_infobox.career_rows``).
Every forgery is built independently from the genuine fixture and resealed as a careful forger would. They cover:

* the saved construction and its text variants: NULL, empty, whitespace, parent-copied, enlarged (the whole field),
  substring and genuine text, each with the reciprocal swap -- refused as ``PERIOD`` (the identities' ordinals cross);
* a one-sided swap, each relation alone, the Attempt 4 format, the list line, missing witnesses with the swap, a false
  restructure claim with blank text, and an identity relabel that keeps each identity's edges but moves the rows'
  content (refused as ``PERIOD_WITNESS``: the stated interval is not the identity's in its source);
* stated interval text or dates that are not the identity's interval (forged, enlarged, the other row's) with genuine
  edges -- ``PERIOD_WITNESS``;
* the legitimate forms: the genuine fixture, blank interval text and unstated dates with genuine edges, the corrected
  reading ``1990`` -> ``1990–?`` (an unknown end), the restructured field, the list line, and the Attempt 4 format.

Refusal codes are spelled out (not read from the module) so this suite also runs, and fails for what the verifier does,
over the unfixed base's bytes. Unit-level checks of the new helpers import them inside their own tests.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

import test_cycle37_a08_source_witness as a8  # noqa: E402  (its successor/seal/attach helpers -- its tests are not rerun)
from aggie_analytics.cycle37 import career_infobox as ci  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402
from aggie_analytics.cycle37 import career_witness as cw  # noqa: E402

REFUSED_PERIOD = "REFUSED_CAREER_SUCCESSOR_PERIOD_ANCHOR_MISMATCH"
REFUSED_PERIOD_WITNESS = "REFUSED_CAREER_SUCCESSOR_PERIOD_WITNESS_MISMATCH"
REFUSED_A04_ANCHOR = "REFUSED_CAREER_SUCCESSOR_A04_ANCHOR_MISMATCH"
REFUSED_RESTRUCTURE = "REFUSED_CAREER_SUCCESSOR_RESTRUCTURE_CLAIM_MISMATCH"

PAGE, REVISION, TITLE, QID = 176858, 1373372050, "Interval Fixture (American football)", "Q176858"
CAMP = "1892, 1894–1895"
TEXT = ("{{Infobox college coach\n| name = Interval Fixture\n"
        "| coach_years1 = " + CAMP + "\n| coach_team1 = [[Stanford Cardinal football|Stanford]]\n"
        "| coach_years2 = 1974\n| coach_team2 = [[Yale Bulldogs football|Yale]] (GA)\n"
        "| coach_years3 = 1990–?, 1995\n| coach_team3 = [[Iowa Hawkeyes football|Iowa]] (OC)\n"
        "| coach_years4 = 1911&ndash;1916, 1920\n| coach_team4 = [[Ohio Bobcats football|Ohio]]\n"
        "| pastcoaching =\n* [[Cleveland Browns]] (1970–1974, 1977)\n}}\n")
#: What the current parser (v37.5) reads: the Attempt 5 rows are exactly these.
PARSED = {(row["family"], row["index"]): row for row in ci.career_rows(TEXT)["rows"]}
#: The v37.2/v37.4 splitting of the same revision (their spans).
OLD_UNITS = cw.source_units(TEXT, literal_blanking=False)
FIELDS = ("start", "end", "ongoing", "start_state", "end_state", "start_bounds", "end_bounds", "start_qualifier",
          "end_qualifier", "definite_first_season", "definite_last_season", "bounds_consistent")
#: How the delivered v37.2 parser read each field: no HTML entity decoding ("1911&ndash;1916" is two bare years), no
#: open ends ("1990–?" is a bare year) -- the Attempt 5 rows correct and restructure these readings.
DELIVERED = {1: [("1892", 1892, 1892), ("1894–1895", 1894, 1895)], 2: [("1974", 1974, 1974)],
             3: [("1990", 1990, 1990), ("1995", 1995, 1995)],
             4: [("1911", 1911, 1911), ("1916", 1916, 1916), ("1920", 1920, 1920)],
             1001: [("1970–1974", 1970, 1974), ("1977", 1977, 1977)]}
#: Each Attempt 5 entry's disposition against the delivered rows (the Attempt 4 relation is unchanged throughout).
DISPOSITIONS = {1: [cs.UNCHANGED, cs.UNCHANGED], 2: [cs.UNCHANGED], 3: [cs.UNRESOLVED_EXPLICIT, cs.UNCHANGED],
                4: [cs.RESTRUCTURED, cs.RESTRUCTURED], 1001: [cs.UNCHANGED, cs.UNCHANGED]}


def _id(prefix: str, row: int, interval: int = 0) -> str:
    return f"{prefix}:{PAGE}:{REVISION}:COACHING:{row}:{interval}"


def _db(value):
    """An interval field as the builders store it: a boolean as 0/1, bounds as JSON."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, list):
        return json.dumps(value)
    return value


def _stated(interval: dict) -> dict:
    return {**{field: _db(interval.get(field)) for field in FIELDS}, "years_as_written": interval["as_written"]}


class IntervalLineageTests(unittest.TestCase):
    _dispositions = a8.SourceWitnessTests._dispositions
    _seal = a8.SourceWitnessTests._seal
    successor = a8.SourceWitnessTests.successor
    a4_format = a8.SourceWitnessTests.a4_format
    attach = a8.SourceWitnessTests.attach
    copy = a8.SourceWitnessTests.copy

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        raw = self.root / "raw.json"
        raw.write_bytes(json.dumps({"query": {"pages": {str(PAGE): {
            "pageid": PAGE, "title": TITLE, "pageprops": {"wikibase_item": QID},
            "revisions": [{"revid": REVISION, "slots": {"main": {"*": TEXT}}}]}}}}).encode("utf-8"))
        page = {"pageid": PAGE, "revision": str(REVISION), "family": "COACHING", "page_title": TITLE,
                "person_display": "Interval Fixture", "wikidata_qid": QID, "raw_file": str(raw),
                "raw_file_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "wikitext_sha256": hashlib.sha256(TEXT.encode("utf-8")).hexdigest(),
                "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "assignments": "[]"}
        # Delivered (v37.2): numbered fields with their team and years spans, the list line with its team span and
        # the years text inside it.
        self.old = {}
        for index, readings in DELIVERED.items():
            unit = OLD_UNITS[("COACHING", index)][0]
            spans = {"team_raw": TEXT[unit.team[0]:unit.team[1]], "team_char_span": json.dumps(list(unit.team))}
            if unit.years is not None:
                spans.update(years_raw=TEXT[unit.years[0]:unit.years[1]], years_char_span=json.dumps(list(unit.years)))
            else:
                spans.update(years_raw="1970–1974, 1977", years_char_span=None)
            for k, (text, start, end) in enumerate(readings):
                self.old[_id("R37-05", index, k)] = {**page, **spans, "episode_id": _id("R37-05", index, k),
                                                     "row_index": index, "interval_index": k, "ongoing": 0,
                                                     "years_as_written": text, "start": start, "end": end}
        # Attempt 4 (v37.4) and Attempt 5 (v37.5) read these fields the same way: the parser's own rows.
        self.a4_rows, self.episodes = {}, []
        for (family, index), row in sorted(PARSED.items(), key=lambda item: item[0][1]):
            team, years = row["team_span"], row["years_span"]
            spans = {"team_raw": TEXT[team[0]:team[1]], "team_char_span": json.dumps(team),
                     "years_raw": row["years_raw"], "years_char_span": json.dumps(years) if years else None}
            delivered = [_id("R37-05", index, k) for k in range(len(DELIVERED[index]))]
            for k, interval in enumerate(row["intervals"]):
                disposition = DISPOSITIONS[index][k]
                parents = delivered if disposition == cs.RESTRUCTURED else [delivered[k]]
                a4_id = _id("C37A04", index, k)
                self.a4_rows[a4_id] = {**page, **spans, **_stated(interval), "episode_id": a4_id, "row_index": index,
                                       "interval_index": k, "predecessor_episode_ids": json.dumps(parents),
                                       "lineage_state": cs.DERIVED, "disposition": disposition}
                self.episodes.append({**page, **spans, **_stated(interval), "episode_id": _id("C37A05", index, k),
                                      "row_index": index, "interval_index": k,
                                      "predecessor_episode_ids": json.dumps(parents), "lineage_state": cs.DERIVED,
                                      "disposition": disposition, "a04_episode_ids": json.dumps([a4_id]),
                                      "a04_lineage_state": cs.A04_DERIVED, "a04_disposition": cs.UNCHANGED,
                                      "date_basis": "FIXTURE", "uncertainty_classes": "[]"})
        self.predecessor = self.root / "predecessor.sqlite"
        a8._table(self.predecessor, cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, list(self.old.values()))
        self.a4 = self.root / "a04.sqlite"
        a8._table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ helpers
    def row(self, episodes: list[dict], index: int, interval: int, prefix: str = "C37A05") -> dict:
        return next(r for r in episodes if r["episode_id"] == _id(prefix, index, interval))

    def swap(self, episodes: list[dict], index: int, *, default: bool = True, a04: bool = True,
             prefix: str = "C37A05") -> None:
        """The manager's recipe: intervals 0 and 1 of one field swap their reciprocal edges (and disposition texts)."""

        x, y = self.row(episodes, index, 0, prefix), self.row(episodes, index, 1, prefix)
        fields = (("predecessor_episode_ids", "disposition") if default else ()) + \
                 (("a04_episode_ids", "a04_disposition") if a04 and prefix == "C37A05" else ())
        for field in fields:
            x[field], y[field] = y[field], x[field]

    def refused(self, code: str, successor: Path, *causes: str) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            self.attach(successor)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        for cause in causes:
            self.assertIn(cause, str(caught.exception))
        return str(caught.exception)

    def camp_text(self, variant: str, own: dict, other: dict) -> str | None:
        return {"NULL": None, "empty": "", "whitespace": "   ", "parent-copied": other["years_as_written"],
                "enlarged": CAMP, "substring": "189", "genuine": own["years_as_written"]}[variant]

    # ------------------------------------------------------------------ accepted
    def test_the_genuine_fixture_serves_with_every_interval_edge_bound_by_identity(self) -> None:
        binding = self.attach(self.successor("genuine.sqlite"))
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        default, a04 = lineage["parent_edges_bound_to_source_field"], lineage["a04_edges_bound_to_source_field"]
        # Fields 1, 3 and the list line hold two intervals each (6 edges); field 4 is restructured (2 rows x 3 delivered
        # intervals, all-to-all), field 2 single: 13 default edges.
        self.assertEqual((default["edges"], default["interval_checked"], default["restructured_entries"]), (13, 6, 1))
        self.assertEqual((a04["edges"], a04["interval_checked"], a04["restructured_entries"]), (9, 8, 0))
        self.assertEqual(default.get("interval_edges_bound_by_identity_ordinal"), 6)
        self.assertEqual(a04.get("interval_edges_bound_by_identity_ordinal"), 8)
        self.assertEqual(default.get("interval_rows_read_again_from_source"), 6)
        self.assertEqual(len(binding["_rows"]), 9)
        served = {r["episode_id"]: r for r in binding["_rows"]}
        self.assertEqual(served[_id("C37A05", 3, 0)]["years_as_written"], "1990–?")    # a corrected, open end
        self.assertIsNone(served[_id("C37A05", 3, 0)]["end"])
        self.assertEqual(json.loads(served[_id("C37A05", 4, 0)]["predecessor_episode_ids"]),
                         [_id("R37-05", 4, k) for k in range(3)])                       # a restructured field

    def test_blank_interval_text_and_unstated_dates_with_genuine_edges_serve(self) -> None:
        # Genuinely absent metadata grants nothing and blocks nothing: the identities decide the edges.
        for label, blank in (("NULL", None), ("empty", ""), ("whitespace", "  ")):
            with self.subTest(text=label):
                episodes = self.copy()
                for row in episodes:
                    row["years_as_written"] = blank
                    for field in FIELDS:
                        row[field] = None
                binding = self.attach(self.successor(f"blank-{label}.sqlite", episodes))
                self.assertEqual(len(binding["_rows"]), 9)

    def test_the_corrected_reading_the_restructure_and_the_list_line_keep_their_lineage(self) -> None:
        binding = self.attach(self.successor("legitimate.sqlite"))
        served = {r["episode_id"]: r for r in binding["_rows"]}
        # 1990 (delivered) -> 1990–? (Attempt 5): the same interval, ordinal 0, an explicitly unresolved end.
        self.assertEqual(json.loads(served[_id("C37A05", 3, 0)]["predecessor_episode_ids"]), [_id("R37-05", 3, 0)])
        self.assertEqual(served[_id("C37A05", 3, 0)]["disposition"], cs.UNRESOLVED_EXPLICIT)
        # the list line's two intervals, each from its own delivered interval
        for k in (0, 1):
            self.assertEqual(json.loads(served[_id("C37A05", 1001, k)]["predecessor_episode_ids"]),
                             [_id("R37-05", 1001, k)])

    def test_the_attempt4_format_serves(self) -> None:
        binding = self.attach(self.a4_format("a4-genuine.sqlite", [dict(r) for r in self.a4_rows.values()]))
        self.assertEqual(len(binding["_rows"]), 9)

    # ------------------------------------------------------------------ the saved construction and its text variants
    def test_the_managers_crossed_intervals_are_refused_whatever_period_text_they_carry(self) -> None:
        for variant in ("NULL", "empty", "whitespace", "parent-copied", "enlarged", "substring", "genuine"):
            with self.subTest(text=variant):
                episodes = self.copy()
                x, y = self.row(episodes, 1, 0), self.row(episodes, 1, 1)
                genuine = (dict(x), dict(y))
                self.swap(episodes, 1)
                x["years_as_written"] = self.camp_text(variant, genuine[0], genuine[1])
                y["years_as_written"] = self.camp_text(variant, genuine[1], genuine[0])
                message = self.refused(REFUSED_PERIOD, self.successor(f"camp-{variant}.sqlite", episodes))
                self.assertIn(f"{_id('C37A05', 1, 0)} (interval 0", message)
                self.assertIn(f"<- {_id('R37-05', 1, 1)} (interval 1", message)

    def test_a_one_sided_swap_is_refused(self) -> None:
        episodes = self.copy()
        x = self.row(episodes, 1, 0)
        x["predecessor_episode_ids"] = json.dumps([_id("R37-05", 1, 1)])
        x["a04_episode_ids"] = json.dumps([_id("C37A04", 1, 1)])
        x["years_as_written"] = None
        self.refused(REFUSED_PERIOD, self.successor("one-sided.sqlite", episodes), _id("C37A05", 1, 0))

    def test_each_relation_alone_is_refused(self) -> None:
        episodes = self.copy()
        self.swap(episodes, 1, a04=False)               # default edges crossed, Attempt 4 edges genuine
        for row in episodes:
            row["years_as_written"] = None
        self.refused(REFUSED_PERIOD, self.successor("default-only.sqlite", episodes))
        episodes = self.copy()
        self.swap(episodes, 1, default=False)           # Attempt 4 edges crossed, default edges genuine
        for row in episodes:
            row["years_as_written"] = None
        self.refused(REFUSED_A04_ANCHOR, self.successor("a04-only.sqlite", episodes), "PERIOD")

    def test_the_attempt4_format_crossing_is_refused(self) -> None:
        rows = [dict(r) for r in self.a4_rows.values()]
        self.swap(rows, 1, prefix="C37A04")
        for row in rows:
            row["years_as_written"] = None
        self.refused(REFUSED_PERIOD, self.a4_format("a4-crossed.sqlite", rows), _id("C37A04", 1, 0))

    def test_the_list_line_crossing_is_refused(self) -> None:
        episodes = self.copy()
        self.swap(episodes, 1001)
        for k in (0, 1):
            self.row(episodes, 1001, k)["years_as_written"] = None
        self.refused(REFUSED_PERIOD, self.successor("list-line.sqlite", episodes), _id("C37A05", 1001, 0))

    def test_missing_witnesses_with_crossed_intervals_are_refused(self) -> None:
        # The Attempt 8 missingness combined with the Attempt 9 crossing: no spans, no interval text.
        for fields in (("team",), ("years",), ("team", "years")):
            with self.subTest(fields=fields):
                episodes = self.copy()
                self.swap(episodes, 1)
                for k in (0, 1):
                    victim = self.row(episodes, 1, k)
                    victim["years_as_written"] = None
                    for field in fields:
                        victim[f"{field}_char_span"] = None
                        if field == "team":
                            victim["team_byte_span"] = None
                self.refused(REFUSED_PERIOD, self.successor(f"missing-{'-'.join(fields)}.sqlite", episodes))

    def test_a_false_restructure_claim_with_blank_text_is_refused(self) -> None:
        episodes = self.copy()
        both = json.dumps([_id("R37-05", 1, 0), _id("R37-05", 1, 1)])
        for k in (0, 1):
            row = self.row(episodes, 1, k)
            row["predecessor_episode_ids"], row["disposition"], row["years_as_written"] = both, cs.RESTRUCTURED, None
        self.refused(REFUSED_RESTRUCTURE, self.successor("false-restructure.sqlite", episodes))

    def test_an_identity_relabel_that_moves_the_rows_content_is_refused(self) -> None:
        # Each identity keeps its genuine edges, but the rows' content trades places: the row now named interval 1
        # states 1892. Blank text does not hide it -- its stated dates are not interval 1 of its source.
        for text in ("kept", "blank"):
            with self.subTest(text=text):
                episodes = self.copy()
                x, y = self.row(episodes, 1, 0), self.row(episodes, 1, 1)
                content = ("years_as_written",) + FIELDS
                for field in content:
                    x[field], y[field] = y[field], x[field]
                if text == "blank":
                    x["years_as_written"] = y["years_as_written"] = None
                message = self.refused(REFUSED_PERIOD_WITNESS, self.successor(f"relabel-{text}.sqlite", episodes))
                self.assertIn(_id("C37A05", 1, 0), message)

    def test_stated_interval_text_or_dates_that_are_not_the_identitys_are_refused(self) -> None:
        for label, change in (("other row's text", {"years_as_written": "1894–1895"}),
                              ("enlarged text", {"years_as_written": CAMP}),
                              ("substring text", {"years_as_written": "189"}),
                              ("another start", {"start": 1894}),
                              ("another end state", {"end_state": "UNKNOWN"})):
            with self.subTest(change=label):
                episodes = self.copy()
                self.row(episodes, 1, 0).update(change)
                self.refused(REFUSED_PERIOD_WITNESS, self.successor(f"stated-{label}.sqlite", episodes),
                             _id("C37A05", 1, 0))

    def test_an_attempt4_format_relabel_is_refused(self) -> None:
        rows = [dict(r) for r in self.a4_rows.values()]
        x, y = self.row(rows, 1, 0, "C37A04"), self.row(rows, 1, 1, "C37A04")
        for field in ("years_as_written",) + FIELDS:
            x[field], y[field] = y[field], x[field]
        x["years_as_written"] = y["years_as_written"] = None
        self.refused(REFUSED_PERIOD_WITNESS, self.a4_format("a4-relabel.sqlite", rows), _id("C37A04", 1, 0))

    # ------------------------------------------------------------------ the rules on their own
    def test_the_ordinal_rule_and_the_count_rule_on_their_own(self) -> None:
        # Rows compared by their own spans (no derived units): the identities' ordinals decide, never the text.
        child = {"episode_id": _id("C37A05", 1, 0), "pageid": PAGE, "revision": str(REVISION), "family": "COACHING",
                 "row_index": 1, "interval_index": 0, "team_char_span": "[99, 138]", "years_char_span": "[67, 82]",
                 "years_as_written": "1894–1895", "_parents": [_id("R37-05", 1, 1)]}
        sibling = {**child, "episode_id": _id("C37A05", 1, 1), "interval_index": 1, "_parents": [_id("R37-05", 1, 0)]}
        parents = {_id("R37-05", 1, k): {**child, "episode_id": _id("R37-05", 1, k), "interval_index": k}
                   for k in (0, 1)}
        states = {p: (cs.UNCHANGED, []) for p in parents}
        with self.assertRaises(cs.CareerSuccessorError) as crossed:
            cs.check_anchors([child, sibling], parents, states, "_parents", "predecessor")
        self.assertEqual(crossed.exception.code, REFUSED_PERIOD)
        # a third parent interval the child side does not hold: a changed count, claimed as no restructure
        three = {**parents, _id("R37-05", 1, 2): {**child, "episode_id": _id("R37-05", 1, 2), "interval_index": 2}}
        genuine = [{**child, "_parents": [_id("R37-05", 1, 0)]}, {**sibling, "_parents": [_id("R37-05", 1, 1)]}]
        with self.assertRaises(cs.CareerSuccessorError) as changed:
            cs.check_anchors(genuine, three, {p: (cs.UNCHANGED, []) for p in three}, "_parents", "predecessor")
        self.assertEqual(changed.exception.code, REFUSED_RESTRUCTURE)

    def test_the_interval_reader_on_its_own(self) -> None:
        from aggie_analytics.cycle37 import career_interval as civ   # new in Attempt 10
        for version in (civ.V375, civ.V374):
            read = civ.source_intervals(TEXT, version)
            self.assertEqual([i["as_written"] for i in read[("COACHING", 1)]], ["1892", "1894–1895"])
            self.assertEqual([i["as_written"] for i in read[("COACHING", 4)]], ["1911–1916", "1920"])
            self.assertEqual([i["as_written"] for i in read[("COACHING", 1001)]], ["1970–1974", "1977"])
            self.assertEqual(read[("COACHING", 3)][0]["end_state"], "UNKNOWN")
        genuine = self.row(self.copy(), 1, 1)
        intervals = civ.source_intervals(TEXT, civ.V375)[("COACHING", 1)]
        self.assertEqual(civ.interval_problems(genuine, intervals, 2), [])
        self.assertEqual(civ.interval_problems({**genuine, "years_as_written": None, "start": None}, intervals, 2), [])
        self.assertEqual(civ.interval_problems({**genuine, "interval_index": 2}, intervals, 3),
                         [civ.ORDINAL_NOT_STATED])
        self.assertEqual(civ.interval_problems(genuine, intervals, 3), [civ.COUNT_NOT_STATED])
        self.assertEqual(civ.interval_problems({**genuine, "years_as_written": "1892"}, intervals, 2),
                         [civ.TEXT_NOT_ITS_INTERVAL])
        self.assertEqual(civ.interval_problems(genuine, civ.NO_SOURCE_ROW, 2), [civ.NO_SOURCE_ROW])
        self.assertEqual(civ.interval_problems(genuine, None, 2), [civ.AMBIGUOUS_SOURCE_ROW])
        # v37.4 read no role lines: a role-line identity names no v37.4 interval.
        role = "{{Infobox college coach\n| pastcoaching =\n* [[Ohio]] (2015–2019)<br>Line coach (2015–2016)\n}}\n"
        self.assertNotIn(("COACHING", 100101), civ.source_intervals(role, civ.V374))
        self.assertIn(("COACHING", 100101), civ.source_intervals(role, civ.V375))

    def test_each_refusal_left_the_genuine_fixture_attachable(self) -> None:
        for name in ("after-1.sqlite", "after-2.sqlite"):
            self.assertEqual(len(self.attach(self.successor(name))["_rows"]), 9)


if __name__ == "__main__":
    unittest.main()
