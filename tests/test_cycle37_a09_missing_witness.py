"""Cycle #37 — Attempt #9 — MF37A08-01: an absent witness never lets a row's own text anchor a lineage edge.

The Attempt 8 manager swapped the reciprocal default and Attempt 4 edges of Fred Mariani's 1974 graduate-assistant row
and his 2009 Rutgers row, set both rows' team, byte and years spans to NULL and enlarged their team and years text to
run over all six jobs, then resealed. The v4 verifier skipped the absent witnesses, the anchor fell back to the rows'
text (each contained the other) and every entrypoint served seven rows. The v5 verifier resolves every row to the
source unit its identity names in its verified revision, witnessed or not, accepts unwitnessed text only where it is
that unit's own (a line's years: inside the line), and anchors each edge by the two derived units alone.

These cases reuse the Attempt 8 witness fixture (one realistic revision with numbered fields -- a two-interval field,
two jobs of the same role in two periods, an empty field, a years-only field, a comment with a bar -- and a
``pastcoaching`` list with a nested line and role lines; its delivered, Attempt 4 and Attempt 5 rows). Every negative
is built independently from the genuine fixture and resealed as a careful forger would, so a refusal reaches its rule,
not a stale hash. They cover:

* the saved construction in every absent representation (SQL NULL, JSON ``null``, ``[null, null]``, empty string);
* missingness combined with forged reciprocal edges, with enlarged, full-page, exact (the row's own) and blank text;
  team-only, year-only and both witnesses absent; the same role in another period; both relations; both formats; a
  forged row in the declared Attempt 4 file (enlarged text, or relabelled under another identity);
* the positive meaning of genuinely absent witnesses (a years-only field, an empty field, list lines whose years live
  inside the line) in every representation, and unwitnessed text that is exactly the unit's own;
* the ``UNANCHORED`` cause (a row naming no unit; no comparable field and another parameter) and the unit-level rules.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

import test_cycle37_a08_source_witness as a8  # noqa: E402  (the Attempt 8 fixture, reused -- its tests are not rerun)
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402
from aggie_analytics.cycle37 import career_witness as cw  # noqa: E402

TEXT, span, _id, _table = a8.TEXT, a8.span, a8._id, a8._table
#: The v37.9 causes, spelled out (not read from the module) so this suite also runs, and fails for what the verifier
#: does, over the unfixed base's bytes.
TEAM_TEXT_NOT_ITS_SOURCE_UNIT = "TEAM_TEXT_WITHOUT_A_WITNESS_IS_NOT_ITS_SOURCE_UNIT"
YEARS_TEXT_NOT_ITS_SOURCE_UNIT = "YEARS_TEXT_WITHOUT_A_WITNESS_IS_NOT_ITS_SOURCE_UNIT"
YEARS_TEXT_NOT_IN_ITS_LINE = "YEARS_TEXT_WITHOUT_A_WITNESS_IS_NOT_IN_ITS_LINE"
TEXT_WITHOUT_A_SOURCE_UNIT = "TEXT_WITHOUT_A_SOURCE_UNIT"
#: The four spellings of "no witness recorded" the verifier treats as one absent state.
ABSENT = (("SQL NULL", None), ("JSON null", "null"), ("[null, null]", "[null, null]"), ("empty string", ""))
TEXT_PREFIX = "REFUSED_CAREER_SUCCESSOR_"


class MissingWitnessTests(unittest.TestCase):
    setUp = a8.SourceWitnessTests.setUp
    tearDown = a8.SourceWitnessTests.tearDown
    _dispositions = a8.SourceWitnessTests._dispositions
    _seal = a8.SourceWitnessTests._seal
    successor = a8.SourceWitnessTests.successor
    a4_format = a8.SourceWitnessTests.a4_format
    attach = a8.SourceWitnessTests.attach
    copy = a8.SourceWitnessTests.copy
    row = a8.SourceWitnessTests.row
    swap = a8.SourceWitnessTests.swap

    # ------------------------------------------------------------------ helpers
    def refused(self, code: str, successor: Path, *causes: str) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            self.attach(successor)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        for cause in causes:
            self.assertIn(cause, str(caught.exception))
        return str(caught.exception)

    @staticmethod
    def unwitness(row: dict, fields: tuple[str, ...], absent=None, text: str | None = "keep") -> None:
        """Remove a row's witnesses for ``fields`` (``absent`` spelling), and set their text: ``"keep"`` leaves it,
        anything else replaces it (None blanks it)."""

        for field in fields:
            row[f"{field}_char_span"] = absent
            if field == "team":
                row["team_byte_span"] = absent
            if text != "keep":
                row[f"{field}_raw"] = text

    @staticmethod
    def own_text(row_index: int, field: str) -> str | None:
        where = span(("COACHING", row_index), field)
        return TEXT[where[0]:where[1]] if where else None

    def managers_construction(self, episodes: list[dict], absent=None) -> None:
        """The Attempt 8 manager's recipe, on this fixture: jobs 1 and 6 swapped in both relations, their spans
        removed, their team and years text enlarged from job 1's parameter to job 6's."""

        self.swap(episodes, 1, 6)
        team = (span(("COACHING", 1), "team")[0], span(("COACHING", 6), "team")[1])
        years = (span(("COACHING", 1), "years")[0], span(("COACHING", 6), "years")[1])
        for index in (1, 6):
            victim = self.row(episodes, index)
            victim["team_raw"], victim["years_raw"] = TEXT[team[0]:team[1]], TEXT[years[0]:years[1]]
            self.unwitness(victim, ("team", "years"), absent)

    # ------------------------------------------------------------------ the saved construction is refused
    def test_the_managers_null_span_enlarged_text_swap_is_refused_in_every_absent_spelling(self) -> None:
        for label, absent in ABSENT:
            with self.subTest(absent=label):
                episodes = self.copy()
                self.managers_construction(episodes, absent)
                self.refused(cs.REFUSED_SOURCE_FIELD, self.successor(f"manager-{label}.sqlite", episodes),
                             TEAM_TEXT_NOT_ITS_SOURCE_UNIT, YEARS_TEXT_NOT_ITS_SOURCE_UNIT, _id("C37A05", 1))

    def test_missing_witnesses_with_forged_edges_are_refused_whatever_text_they_carry(self) -> None:
        # Missingness combined with the forged reciprocal edges -- not missingness alone. Enlarged and full-page text
        # is not the unit's own; the rows' own exact text, or none, passes the text rule and is then refused by the
        # anchor, which compares the units jobs 1 and 6 name (two numbered fields: EPISODE).
        full_page = TEXT
        for fields in (("team",), ("years",), ("team", "years")):
            for label, text, code in (
                    ("enlarged", "enlarged", cs.REFUSED_SOURCE_FIELD),
                    ("full-page", full_page, cs.REFUSED_SOURCE_FIELD),
                    ("exact-own", "own", cs.REFUSED_EPISODE_ANCHOR),
                    ("blank", None, cs.REFUSED_EPISODE_ANCHOR)):
                with self.subTest(fields=fields, text=label):
                    episodes = self.copy()
                    self.swap(episodes, 1, 6)
                    for index in (1, 6):
                        victim = self.row(episodes, index)
                        for field in fields:
                            if text == "enlarged":
                                lo = span(("COACHING", 1), field)[0]
                                hi = span(("COACHING", 6), field)[1]
                                value = TEXT[lo:hi]
                            elif text == "own":
                                value = self.own_text(index, field)
                            else:
                                value = text
                            self.unwitness(victim, (field,), None, value)
                    message = self.refused(code, self.successor(f"missing-{'-'.join(fields)}-{label}.sqlite",
                                                                episodes))
                    if code == cs.REFUSED_EPISODE_ANCHOR:
                        self.assertIn(f"{_id('C37A05', 1)} <- {_id('R37-05', 6)}", message)

    def test_the_same_role_in_another_period_is_refused_without_witnesses(self) -> None:
        # Jobs 2 and 3 are both "Lehigh (OC)". Job 2's first interval, with no witnesses and job 3's (identical) team
        # text, is pointed at job 3's parents: the v4 text fallback agreed. The units are two numbered fields.
        episodes = self.copy()
        victim, donor = self.row(episodes, 2, 0), self.row(episodes, 3)
        self.assertEqual(victim["team_raw"], donor["team_raw"])
        for field in ("predecessor_episode_ids", "a04_episode_ids"):
            victim[field] = donor[field]
        donor["predecessor_episode_ids"], donor["a04_episode_ids"] = "[]", "[]"
        donor["lineage_state"], donor["a04_lineage_state"] = (cs.ADDED_STATES[cs.A05_FORMAT_VERSION], cs.A04_ADDED)
        donor["disposition"], donor["a04_disposition"] = "ADDED", "ADDED_IN_A05"
        self.unwitness(victim, ("team", "years"), None, "keep")
        victim["years_raw"] = None
        message = self.refused(cs.REFUSED_EPISODE_ANCHOR, self.successor("same-role-other-period.sqlite", episodes))
        self.assertIn(f"{_id('C37A05', 2)} <- {_id('R37-05', 3)}", message)

    def test_the_attempt4_relation_alone_is_refused(self) -> None:
        # The default edges stay genuine; only the Attempt 4 edges of jobs 1 and 6 swap, with no witnesses and blank
        # text: refused by the Attempt 4 anchor (the units the two Attempt 4 identities name).
        episodes = self.copy()
        x, y = self.row(episodes, 1), self.row(episodes, 6)
        for field in ("a04_episode_ids", "a04_disposition"):
            x[field], y[field] = y[field], x[field]
        for victim in (x, y):
            self.unwitness(victim, ("team", "years"), None, None)
        message = self.refused(cs.REFUSED_A04_ANCHOR, self.successor("a04-relation-only.sqlite", episodes), "EPISODE")
        self.assertIn(_id("C37A04", 6), message)

    def test_the_attempt4_format_entrypoint_is_refused(self) -> None:
        for label, text, code in (("enlarged", "enlarged", cs.REFUSED_SOURCE_FIELD),
                                  ("blank", None, cs.REFUSED_EPISODE_ANCHOR)):
            with self.subTest(text=label):
                rows = [dict(r) for r in self.a4_rows.values()]
                a, b = (next(r for r in rows if r["episode_id"] == _id("C37A04", n)) for n in (1, 6))
                a["predecessor_episode_ids"], b["predecessor_episode_ids"] = (b["predecessor_episode_ids"],
                                                                             a["predecessor_episode_ids"])
                lo, hi = span(("COACHING", 1), "team", old=True)[0], span(("COACHING", 6), "team", old=True)[1]
                for row in (a, b):
                    self.unwitness(row, ("team", "years"), None, TEXT[lo:hi] if text == "enlarged" else None)
                self.refused(code, self.a4_format(f"a4-format-{label}.sqlite", rows), "parser BAS-CAREER-INFOBOX-v37.4"
                             if code == cs.REFUSED_SOURCE_FIELD else "EPISODE")

    def test_a_declared_attempt4_file_row_without_witnesses_is_refused(self) -> None:
        # Every Attempt 5 row genuine; the declared Attempt 4 file's job-1 row has no witnesses and enlarged text.
        victim = self.a4_rows[_id("C37A04", 1)]
        lo, hi = span(("COACHING", 1), "team", old=True)[0], span(("COACHING", 6), "team", old=True)[1]
        self.unwitness(victim, ("team", "years"), None, TEXT[lo:hi])
        self.a4 = self.root / "a04-missing.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))
        self.refused(cs.REFUSED_SOURCE_FIELD, self.successor("a4-file-missing.sqlite"), "Attempt 4 file",
                     TEAM_TEXT_NOT_ITS_SOURCE_UNIT)

    def test_a_declared_attempt4_file_row_relabelled_under_another_identity_is_refused(self) -> None:
        # The file's job-6 row carries job 1's row index, witnesses and text: its unit would be job 1's, which its
        # episode identity does not name. Job 1's Attempt 5 row is pointed at it.
        victim = self.a4_rows[_id("C37A04", 6)]
        genuine_one = self.a4_rows[_id("C37A04", 1)]
        for field in ("row_index", "team_char_span", "team_byte_span", "team_raw", "years_char_span", "years_raw",
                      "years_as_written", "predecessor_episode_ids"):
            victim[field] = genuine_one.get(field)
        self.a4 = self.root / "a04-relabelled.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))
        episodes = self.copy()
        x, y = self.row(episodes, 1), self.row(episodes, 6)
        for field in ("a04_episode_ids", "a04_disposition"):
            x[field], y[field] = y[field], x[field]
        self.refused(cs.REFUSED_A04_IDENTITY, self.successor("a4-file-relabelled.sqlite", episodes), _id("C37A04", 6))

    def test_a_row_naming_no_source_unit_anchors_no_edge(self) -> None:
        # A successor row whose identity names nothing in the revision (row 8: no such field) and records nothing,
        # pointed at a genuine parent: no unit can be derived for the child, so the edge is refused as UNANCHORED.
        episodes = self.copy()
        base = self.row(episodes, 7)
        orphan = {**base, "episode_id": _id("C37A05", 8), "row_index": 8, "team_char_span": None, "team_byte_span": None,
                  "years_char_span": None, "team_raw": None, "years_raw": None, "years_as_written": None,
                  "predecessor_episode_ids": base["predecessor_episode_ids"], "a04_episode_ids": base["a04_episode_ids"]}
        base["predecessor_episode_ids"], base["a04_episode_ids"] = "[]", "[]"
        base["lineage_state"], base["a04_lineage_state"] = cs.ADDED_STATES[cs.A05_FORMAT_VERSION], cs.A04_ADDED
        base["disposition"], base["a04_disposition"] = "ADDED", "ADDED_IN_A05"
        episodes.append(orphan)
        message = self.refused(cs.REFUSED_UNANCHORED, self.successor("no-unit.sqlite", episodes))
        self.assertIn("no source unit was derived for the child", message)
        # Recording text there is refused before any anchor.
        orphan["team_raw"] = "[[Anywhere]]"
        self.refused(cs.REFUSED_SOURCE_FIELD, self.successor("no-unit-text.sqlite", episodes),
                     TEXT_WITHOUT_A_SOURCE_UNIT)

    def test_no_comparable_field_and_another_parameter_is_unanchored(self) -> None:
        # The years-only field (job 7: no team parameter) pointed at the list line's parent (no years field): the two
        # units share no field and are different parameters.
        episodes = self.copy()
        x, y = self.row(episodes, 7), self.row(episodes, 1001)
        for field in ("predecessor_episode_ids", "disposition", "a04_episode_ids", "a04_disposition"):
            x[field], y[field] = y[field], x[field]
        self.refused(cs.REFUSED_UNANCHORED, self.successor("no-comparable-field.sqlite", episodes),
                     _id("C37A05", 7))

    def test_a_lines_years_text_outside_its_line_is_refused(self) -> None:
        episodes = self.copy()
        victim = self.row(episodes, 1001)
        victim["years_char_span"], victim["years_raw"] = None, "2015–2019"   # the next line's dates
        self.refused(cs.REFUSED_SOURCE_FIELD, self.successor("line-years-elsewhere.sqlite", episodes),
                     YEARS_TEXT_NOT_IN_ITS_LINE)

    # ------------------------------------------------------------------ genuine absences keep their meaning
    def test_genuinely_absent_witnesses_keep_their_meaning_in_every_spelling(self) -> None:
        binding = self.attach(self.successor("genuine.sqlite"))
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        witnessed = lineage["source_witnesses_proved"]
        self.assertEqual(witnessed["successor"]["rows_resolved_to_their_source_unit"], len(a8.JOBS))
        self.assertEqual(witnessed["successor"]["unwitnessed_fields"], {"team:PARAMETER:NOT_STATED": 1})
        # the delivered list and nested lines' years live inside their lines, with no years span
        delivered = witnessed["delivered_predecessor"]["unwitnessed_fields"]
        self.assertEqual((delivered.get("years:LIST_LINE:TEXT_IN_ITS_LINE"),
                          delivered.get("years:NESTED_LINE:TEXT_IN_ITS_LINE")), (2, 1))
        for label, absent in ABSENT:
            with self.subTest(absent=label):
                episodes = self.copy()
                seven = self.row(episodes, 7)            # the years-only field: no team parameter
                seven["team_char_span"] = absent
                five = self.row(episodes, 5)             # the empty field: nothing stated, zero-length witnesses
                self.unwitness(five, ("team", "years"), absent, None)
                served = {r["episode_id"]: r for r in self.attach(self.successor(f"absent-{label}.sqlite",
                                                                                  episodes))["_rows"]}
                self.assertEqual(len(served), len(a8.JOBS))
                self.assertIsNone(served[_id("C37A05", 7)]["team_raw"])
                self.assertEqual(served[_id("C37A05", 7)]["years_raw"], "2012")

    def test_unwitnessed_text_that_is_the_units_own_is_kept(self) -> None:
        # A row that did not record its coordinates but whose text is exactly its unit's keeps that text; its edges
        # are anchored by its unit (nothing is swapped here).
        episodes = self.copy()
        for index in (1, 6):
            self.unwitness(self.row(episodes, index), ("team", "years"), None, "keep")
        served = {r["episode_id"]: r for r in self.attach(self.successor("own-text.sqlite", episodes))["_rows"]}
        self.assertEqual(served[_id("C37A05", 6)]["team_raw"], a8.DFO)
        self.assertEqual(json.loads(served[_id("C37A05", 1)]["predecessor_episode_ids"]), [_id("R37-05", 1)])

    def test_the_genuine_fixture_still_attaches_after_every_negative(self) -> None:
        self.assertEqual(len(self.attach(self.successor("after.sqlite"))["_rows"]), len(a8.JOBS))

    # ------------------------------------------------------------------ the unit-level rules
    def test_the_absent_spellings_and_malformed_spans(self) -> None:
        for value in (None, "null", "[null, null]", "[null,null]", "", "  "):
            self.assertIsNone(cw.recorded_span(value), value)
        for value in ("[]", "[1]", "[5, 2]", "[true, false]", "x", '""', "[1, 2, 3]"):
            self.assertEqual(cw.recorded_span(value), (-1, -1), value)
        self.assertEqual(cw.recorded_span("[3, 9]"), (3, 9))

    def test_resolve_unit_refuses_ambiguity_and_text_without_a_unit(self) -> None:
        self.assertEqual((cw.AMBIGUOUS_SOURCE_UNIT, cw.TEXT_WITHOUT_A_SOURCE_UNIT, cw.TEAM_TEXT_NOT_ITS_SOURCE_UNIT,
                          cw.YEARS_TEXT_NOT_ITS_SOURCE_UNIT, cw.YEARS_TEXT_NOT_IN_ITS_LINE),
                         ("AMBIGUOUS_SOURCE_UNIT", TEXT_WITHOUT_A_SOURCE_UNIT, TEAM_TEXT_NOT_ITS_SOURCE_UNIT,
                          YEARS_TEXT_NOT_ITS_SOURCE_UNIT, YEARS_TEXT_NOT_IN_ITS_LINE))
        one = cw.Unit(cw.PARAMETER, "coach_team1", (10, 20), (2, 6))
        other = cw.Unit(cw.PARAMETER, "coach_team1", (30, 40), (22, 26))
        text = "x" * 50
        row = {"family": "COACHING", "row_index": 1}
        self.assertEqual(cw.resolve_unit(row, {("COACHING", 1): [one, other]}, text)[0], [cw.AMBIGUOUS_SOURCE_UNIT])
        self.assertEqual(cw.resolve_unit({**row, "team_char_span": "[30, 40]"}, {("COACHING", 1): [one, other]},
                                         text)[2], other)
        self.assertEqual(cw.resolve_unit(row, {}, text), ([], "NONE", None))
        self.assertEqual(cw.resolve_unit({**row, "years_raw": "1999"}, {}, text)[0], [TEXT_WITHOUT_A_SOURCE_UNIT])
        self.assertEqual(cw.resolve_unit({**row, "team_char_span": "[1, 2]"}, {}, text)[0], [cw.NO_SOURCE_UNIT])
        anchor = cw.anchor_of({"episode_id": "E", "row_index": 1}, one)
        self.assertEqual(anchor, {"episode_id": "E", "row_index": 1, "form": cw.PARAMETER, "team_char_span": [10, 20],
                                  "years_char_span": [2, 6]})
        self.assertNotIn("team_raw", anchor)


if __name__ == "__main__":
    unittest.main()
