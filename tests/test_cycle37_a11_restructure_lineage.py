"""Cycle #37 — Attempt #11 — MF37A10-01: a restructure claim never licenses a count, an ordinal or a period its source
does not state.

The Attempt 10 manager removed Walter Camp's second Stanford interval (``coachyears2 = 1892, 1894–1895``), claimed both
genuine parents for the remaining row as a re-read (``RESTRUCTURED_INTERVALS``) field in both reciprocal relations and
resealed. The v6 verifier read a row's interval again only on an unrestructured edge inside a multi-interval field, and
it took the claim's changed count as a restructure: the installed console script, the installed module and the source
module served three Walter rows instead of four -- and an invented 1800–2099 period and a third interval ordinal.

These cases build one revision in the parser's own forms, with every exception branch the v6 verifier skipped: a
two-interval numbered field (the Walter Camp form), a single-interval field, a field the delivered parser split into
three intervals that v37.4/v37.5 read as two (a genuine re-read), a decade range the delivered parser split into two
(a genuine merge), a field the delivered parser did not read (a row added without a predecessor), a ``pastcoaching``
line stating two separately parenthesized periods that v37.2 and v37.4 read as one (a genuine split, restructured in both
relations) and a line with a role line (a split into another unit). Delivered (v37.2) rows are the declared readings;
Attempt 4 rows are exactly what the v37.4 reader reads; Attempt 5 rows exactly what ``career_infobox.career_rows``
writes. Every forgery is built independently from the genuine fixture and resealed as a careful forger would:

* the manager's count-changing collapse with the remaining row's period genuine, forged, blank, enlarged or copied from
  the removed row; expansion past the source's count, with and without a fabricated period; a fabricated ordinal in a
  genuinely restructured field; a restructured merge expanded past its source; a restructured split collapsed and
  re-labelled an ordinary one-to-one field -- all ``INTERVAL_CARDINALITY``;
* a forged period on every row the v6 exemptions skipped -- an ordinary single-interval row, a row with no predecessor,
  a role line, a restructured merge and split row -- and in the declared Attempt 4 file itself: ``PERIOD_WITNESS``;
* a partial restructure (the re-read field's rows not all claimed): ``RESTRUCTURE``; the Attempt 4 format collapse,
  expansion and single forgery;
* retained: a count-preserving false restructure, a collapse claimed in one relation only and a forged period on a row
  its unrestructured Attempt 4 edge reaches stay refused by the earlier rules;
* legitimate forms serve: the genuine fixture in both formats, blank period text and unstated dates on every row
  (restructured ones included), the re-read, the merge, the split, the role line and the added row.

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
from aggie_analytics.cycle37 import career_interval as civ  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402
from aggie_analytics.cycle37 import career_witness as cw  # noqa: E402

REFUSED_CARDINALITY = "REFUSED_CAREER_SUCCESSOR_INTERVAL_CARDINALITY_MISMATCH"
REFUSED_PERIOD_WITNESS = "REFUSED_CAREER_SUCCESSOR_PERIOD_WITNESS_MISMATCH"
REFUSED_RESTRUCTURE = "REFUSED_CAREER_SUCCESSOR_RESTRUCTURE_CLAIM_MISMATCH"
REFUSED_A04_ANCHOR = "REFUSED_CAREER_SUCCESSOR_A04_ANCHOR_MISMATCH"
RESTRUCTURED, UNCHANGED, CORRECTED = "RESTRUCTURED_INTERVALS", "UNCHANGED", "CORRECTED"

PAGE, REVISION, TITLE, QID = 176859, 1373372051, "Restructure Fixture (American football)", "Q176859"
CAMP = "1892, 1894–1895"
TEXT = ("{{Infobox college coach\n| name = Restructure Fixture\n"
        "| coach_years1 = " + CAMP + "\n| coach_team1 = [[Stanford Cardinal football|Stanford]]\n"
        "| coach_years2 = 1974\n| coach_team2 = [[Yale Bulldogs football|Yale]] (GA)\n"
        "| coach_years3 = 1911&ndash;1916, 1920\n| coach_team3 = [[Ohio Bobcats football|Ohio]]\n"
        "| coach_years4 = 1960s–1970s\n| coach_team4 = [[Iowa Hawkeyes football|Iowa]]\n"
        "| coach_years5 = 1999\n| coach_team5 = [[Rice Owls football|Rice]]\n"
        "| pastcoaching =\n* [[Cleveland Browns]] (2002); (2004)\n"
        "* [[Philadelphia Eagles]] (2015–2019)<br>Defensive backs coach (2015–2016)\n}}\n")
#: What v37.5 (Attempt 5) and v37.4 (Attempt 4) read: the rows of each format are exactly these.
PARSED = {(row["family"], row["index"]): row for row in ci.career_rows(TEXT)["rows"]}
V374 = civ.source_intervals(TEXT, civ.V374)
#: The v37.2/v37.4 splitting of the revision (their spans).
OLD_UNITS = cw.source_units(TEXT, literal_blanking=False)
FIELDS = civ.INTERVAL_FIELDS
#: The delivered (v37.2) readings: field 3 split into three bare years, field 4 into two decades, the Cleveland line
#: read as its last period only, field 5 not read at all.
DELIVERED = {1: [("1892", 1892, 1892), ("1894–1895", 1894, 1895)], 2: [("1974", 1974, 1974)],
             3: [("1911", 1911, 1911), ("1916", 1916, 1916), ("1920", 1920, 1920)],
             4: [("1960s", None, None), ("1970s", None, None)], 1001: [("2004", 2004, 2004)],
             1002: [("2015–2019", 2015, 2019)]}
#: (row index -> (default disposition, Attempt 4 disposition)) for every Attempt 5 field.
A05_STATES = {1: (UNCHANGED, UNCHANGED), 2: (UNCHANGED, UNCHANGED), 3: (RESTRUCTURED, UNCHANGED),
              4: (RESTRUCTURED, UNCHANGED), 5: ("ADDED", UNCHANGED), 1001: (RESTRUCTURED, RESTRUCTURED),
              1002: (CORRECTED, CORRECTED), 100201: (CORRECTED, CORRECTED)}
FORGED = {"years_as_written": "1800–2099", "start": 1800, "end": 2099, "definite_first_season": 1800,
          "definite_last_season": 2099}


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


def _spans(index: int, *, old: bool) -> dict:
    """The row's witnesses under its parser's splitting: a numbered field's team and years spans; a line's team span,
    with its years text (inside the line) and, for the current parser, its years span."""

    if old:
        unit = OLD_UNITS[("COACHING", index)][0]
        team, years = unit.team, unit.years
        years_raw = TEXT[years[0]:years[1]] if years else PARSED[("COACHING", index)]["years_raw"]
    else:
        row = PARSED[("COACHING", index)]
        team, years = row["team_span"], row["years_span"]
        years_raw = row["years_raw"]
    return {"team_raw": TEXT[team[0]:team[1]], "team_char_span": json.dumps(list(team)),
            "years_raw": years_raw, "years_char_span": json.dumps(list(years)) if years else None}


class RestructureLineageTests(unittest.TestCase):
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
                "person_display": "Restructure Fixture", "wikidata_qid": QID, "raw_file": str(raw),
                "raw_file_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "wikitext_sha256": hashlib.sha256(TEXT.encode("utf-8")).hexdigest(),
                "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "assignments": "[]"}
        self.page = page
        # Delivered (v37.2): the declared readings; no row for field 5 and none for the role line.
        self.old = {}
        for index, readings in DELIVERED.items():
            for k, (text, start, end) in enumerate(readings):
                self.old[_id("R37-05", index, k)] = {**page, **_spans(index, old=True),
                                                     "episode_id": _id("R37-05", index, k), "row_index": index,
                                                     "interval_index": k, "ongoing": 0, "years_as_written": text,
                                                     "start": start, "end": end}

        def delivered(index: int) -> list[str]:
            return [_id("R37-05", index, k) for k in range(len(DELIVERED.get(index, [])))]

        # Attempt 4 (v37.4): exactly that reader's intervals; field 3 and 4 re-read from their delivered rows.
        self.a4_rows = {}
        for (family, index), intervals in sorted(V374.items(), key=lambda item: item[0][1]):
            parents = delivered(index)
            restructured = len(intervals) != len(parents) and parents
            for k, interval in enumerate(intervals):
                mine = parents if restructured else parents[k:k + 1]
                self.a4_rows[_id("C37A04", index, k)] = {
                    **page, **_spans(index, old=True), **_stated(interval), "episode_id": _id("C37A04", index, k),
                    "row_index": index, "interval_index": k, "predecessor_episode_ids": json.dumps(mine),
                    "lineage_state": cs.DERIVED if mine else cs.ADDED_STATES[cs.FORMAT_VERSION],
                    "disposition": (RESTRUCTURED if restructured else UNCHANGED) if mine else "ADDED"}
        # Attempt 5 (v37.5): the parser's own rows; the role line derives from its employer line's rows.
        self.episodes = []
        for (family, index), row in sorted(PARSED.items(), key=lambda item: item[0][1]):
            source = index // 100 if index > 100_000 else index
            default, a04 = A05_STATES[index]
            parents = delivered(source)
            a4_parents = [i for i in self.a4_rows if i.startswith(_id("C37A04", source, 0)[:-1])]
            for k, interval in enumerate(row["intervals"]):
                mine = parents if default in (RESTRUCTURED, CORRECTED) else parents[k:k + 1]
                mine4 = a4_parents if a04 in (RESTRUCTURED, CORRECTED) else a4_parents[k:k + 1]
                self.episodes.append({
                    **page, **_spans(index, old=False), **_stated(interval), "episode_id": _id("C37A05", index, k),
                    "row_index": index, "interval_index": k, "predecessor_episode_ids": json.dumps(mine),
                    "lineage_state": cs.DERIVED if mine else cs.ADDED_STATES[cs.A05_FORMAT_VERSION],
                    "disposition": default, "a04_episode_ids": json.dumps(mine4),
                    "a04_lineage_state": cs.A04_DERIVED if mine4 else cs.A04_ADDED, "a04_disposition": a04,
                    "date_basis": row["date_basis"], "uncertainty_classes": "[]"})
        self.predecessor = self.root / "predecessor.sqlite"
        a8._table(self.predecessor, cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, list(self.old.values()))
        self.a4 = self.root / "a04.sqlite"
        a8._table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ helpers
    def row(self, rows: list[dict], index: int, interval: int = 0, prefix: str = "C37A05") -> dict:
        return next(r for r in rows if r["episode_id"] == _id(prefix, index, interval))

    def refused(self, code: str, successor: Path, *causes: str) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            self.attach(successor)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        for cause in causes:
            self.assertIn(cause, str(caught.exception))
        return str(caught.exception)

    def claim(self, rows: list[dict], targets: list[str], parents: list[str], a4_parents: list[str] | None,
              state: str) -> None:
        """Every target claims every parent (the dispositions are derived from these edges, both ways)."""

        for target in rows:
            if target["episode_id"] in targets:
                target["predecessor_episode_ids"], target["disposition"] = json.dumps(parents), state
                if a4_parents is not None:
                    target["a04_episode_ids"], target["a04_disposition"] = json.dumps(a4_parents), state

    def collapse(self, rows: list[dict], index: int, *, a04: bool = True, prefix: str = "C37A05") -> dict:
        """The manager's recipe: every interval row of the field but the first removed; the first claims every
        parent of the field as a re-read field, in both relations."""

        field = sorted((r for r in rows if r["row_index"] == index), key=lambda r: r["interval_index"])
        keep = field[0]
        parents = sorted({p for r in field for p in json.loads(r["predecessor_episode_ids"])})
        a4_parents = sorted({p for r in field for p in json.loads(r["a04_episode_ids"])}) if prefix == "C37A05" else None
        for victim in field[1:]:
            rows.remove(victim)
        self.claim(rows, [keep["episode_id"]], parents, a4_parents if a04 else None, RESTRUCTURED)
        return keep

    def expand(self, rows: list[dict], index: int, extra: int = 1, *, fabricated: bool = False,
               prefix: str = "C37A05") -> list[str]:
        field = sorted((r for r in rows if r["row_index"] == index), key=lambda r: r["interval_index"])
        parents = sorted({p for r in field for p in json.loads(r["predecessor_episode_ids"])})
        a4_parents = sorted({p for r in field for p in json.loads(r["a04_episode_ids"])}) if prefix == "C37A05" else None
        added = []
        for k in range(extra):
            ordinal = len(field) + k
            new = {**field[-1], "episode_id": _id(prefix, index, ordinal), "interval_index": ordinal}
            if fabricated:
                new.update(years_as_written=str(1896 + k), start=1896 + k, end=1896 + k,
                           definite_first_season=1896 + k, definite_last_season=1896 + k)
            rows.append(new)
            added.append(new["episode_id"])
        self.claim(rows, [r["episode_id"] for r in field] + added, parents, a4_parents, RESTRUCTURED)
        return added

    # ------------------------------------------------------------------ accepted
    def test_the_genuine_fixture_serves_with_every_row_read_again_and_every_restructure_qualified(self) -> None:
        binding = self.attach(self.successor("genuine.sqlite"))
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        rows = lineage["source_intervals_proved"]
        self.assertEqual(rows["rows_read_again_from_source"], len(self.episodes))
        self.assertEqual((rows["multi_interval_fields"], rows["rows_in_multi_interval_fields"]), (3, 6))
        self.assertEqual(lineage["a04_source_intervals_proved"]["rows_read_again_from_source"], 9)
        default, a04 = lineage["parent_edges_bound_to_source_field"], lineage["a04_edges_bound_to_source_field"]
        # Fields 3, 4 and the Cleveland line are genuine re-reads against the delivered rows; the Cleveland line also
        # against its one Attempt 4 row.
        self.assertEqual((default["restructured_entries"], default["restructure_claims_qualified"]), (3, 3))
        self.assertEqual((a04["restructured_entries"], a04["restructure_claims_qualified"]), (1, 1))
        served = {r["episode_id"]: r for r in binding["_rows"]}
        self.assertEqual(len(served), 11)
        self.assertEqual(json.loads(served[_id("C37A05", 3, 1)]["predecessor_episode_ids"]),
                         [_id("R37-05", 3, k) for k in range(3)])                 # a re-read
        self.assertEqual(json.loads(served[_id("C37A05", 4, 0)]["predecessor_episode_ids"]),
                         [_id("R37-05", 4, k) for k in range(2)])                 # a merge
        self.assertEqual([served[_id("C37A05", 1001, k)]["years_as_written"] for k in (0, 1)], ["2002", "2004"])
        self.assertEqual(served[_id("C37A05", 5, 0)]["predecessor_episode_ids"], "[]")   # added without a predecessor
        self.assertEqual(json.loads(served[_id("C37A05", 100201, 0)]["predecessor_episode_ids"]),
                         [_id("R37-05", 1002, 0)])                                # a role line of a split

    def test_the_attempt4_format_serves_with_every_row_read_again(self) -> None:
        binding = self.attach(self.a4_format("a4-genuine.sqlite", [dict(r) for r in self.a4_rows.values()]))
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        self.assertEqual(lineage["source_intervals_proved"]["rows_read_again_from_source"], 9)
        self.assertEqual(lineage["parent_edges_bound_to_source_field"]["restructure_claims_qualified"], 2)

    def test_blank_period_text_and_unstated_dates_serve_on_every_branch(self) -> None:
        # Genuinely absent metadata grants nothing and blocks nothing -- restructured, added and role-line rows too.
        for label, blank in (("NULL", None), ("empty", ""), ("whitespace", "  ")):
            with self.subTest(text=label):
                episodes = self.copy()
                for row in episodes:
                    row["years_as_written"] = blank
                    for field in FIELDS:
                        row[field] = None
                self.assertEqual(len(self.attach(self.successor(f"blank-{label}.sqlite", episodes))["_rows"]), 11)

    # ------------------------------------------------------------------ the manager's collapse
    def test_the_managers_count_changing_collapse_is_refused_whatever_period_the_remaining_row_states(self) -> None:
        for period in ("genuine", "forged", "blank", "enlarged", "parent-copied"):
            with self.subTest(period=period):
                episodes = self.copy()
                other = dict(self.row(episodes, 1, 1))
                keep = self.collapse(episodes, 1)
                keep.update({"genuine": {}, "forged": FORGED, "blank": {"years_as_written": None},
                             "enlarged": {"years_as_written": CAMP},
                             "parent-copied": {k: other[k] for k in ("years_as_written", "start", "end",
                                                                     "definite_first_season",
                                                                     "definite_last_season")}}[period])
                message = self.refused(REFUSED_CARDINALITY, self.successor(f"collapse-{period}.sqlite", episodes),
                                       _id("C37A05", 1, 0))
                self.assertIn("holds 1 row(s) here and its source states 2 interval(s)", message)

    def test_an_expansion_past_the_source_count_is_refused(self) -> None:
        for fabricated in (False, True):
            with self.subTest(fabricated_period=fabricated):
                episodes = self.copy()
                added = self.expand(episodes, 1, fabricated=fabricated)
                message = self.refused(REFUSED_CARDINALITY, self.successor(f"expand-{fabricated}.sqlite", episodes),
                                       added[0])
                self.assertIn(civ.ORDINAL_NOT_STATED, message)

    def test_a_fabricated_ordinal_in_a_genuinely_restructured_field_is_refused(self) -> None:
        # The Cleveland line is re-read in both relations; the count stays the source's (two rows) but one identity
        # names an interval the source does not state. (In a field restructured against one relation only, the other
        # relation's ordinal rule refuses the same construction first.)
        episodes = self.copy()
        victim = self.row(episodes, 1001, 1)
        victim["episode_id"], victim["interval_index"] = _id("C37A05", 1001, 7), 7
        self.refused(REFUSED_CARDINALITY, self.successor("fabricated-ordinal.sqlite", episodes), _id("C37A05", 1001, 7),
                     civ.ORDINAL_NOT_STATED)

    def test_a_restructured_merge_expanded_past_its_source_is_refused(self) -> None:
        episodes = self.copy()
        added = self.expand(episodes, 4, extra=2)
        self.refused(REFUSED_CARDINALITY, self.successor("merge-expanded.sqlite", episodes), added[0])

    def test_a_restructured_split_collapsed_and_relabelled_an_ordinary_field_is_refused(self) -> None:
        # The Cleveland line states two periods; one row left, claimed as an ordinary one-to-one edge in both relations:
        # a single-interval field to every edge rule.
        episodes = self.copy()
        keep = self.collapse(episodes, 1001)
        self.claim(episodes, [keep["episode_id"]], [_id("R37-05", 1001, 0)], [_id("C37A04", 1001, 0)], UNCHANGED)
        self.refused(REFUSED_CARDINALITY, self.successor("split-relabelled.sqlite", episodes), _id("C37A05", 1001, 0))

    # ------------------------------------------------------------------ periods on the branches v6 skipped
    def test_a_forged_period_on_every_formerly_exempt_branch_is_refused(self) -> None:
        for label, index, interval in (("ordinary single", 2, 0), ("added without a predecessor", 5, 0),
                                       ("role line of a split", 100201, 0), ("restructured merge", 4, 0),
                                       ("restructured split", 1001, 1)):
            with self.subTest(branch=label):
                episodes = self.copy()
                self.row(episodes, index, interval).update(FORGED)
                self.refused(REFUSED_PERIOD_WITNESS, self.successor(f"forged-{index}-{interval}.sqlite", episodes),
                             _id("C37A05", index, interval), civ.TEXT_NOT_ITS_INTERVAL)

    def test_a_forged_period_on_a_row_its_unrestructured_attempt4_edge_reaches_stays_refused(self) -> None:
        # Field 3 is re-read against its delivered rows but one to one against its Attempt 4 rows: the v6 edge rule
        # already read this row again through that edge, and still does.
        episodes = self.copy()
        self.row(episodes, 3, 1).update(FORGED)
        self.refused(REFUSED_PERIOD_WITNESS, self.successor("forged-3-1.sqlite", episodes), _id("C37A05", 3, 1),
                     civ.TEXT_NOT_ITS_INTERVAL)

    def test_a_forged_period_in_the_declared_attempt4_file_is_refused(self) -> None:
        # The parent side of the Attempt 4 relation: the declared Attempt 4 file's own row states another period.
        genuine_a4, genuine_rows = self.a4, self.a4_rows
        try:
            self.a4_rows = {k: dict(v) for k, v in genuine_rows.items()}
            self.a4_rows[_id("C37A04", 2, 0)].update(FORGED)
            self.a4 = self.root / "a04-forged.sqlite"
            a8._table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))
            successor = self.successor("a4-parent-forged.sqlite", self.copy())
        finally:
            self.a4, self.a4_rows = genuine_a4, genuine_rows
        self.refused(REFUSED_PERIOD_WITNESS, successor, "Attempt 4 file", _id("C37A04", 2, 0))

    # ------------------------------------------------------------------ the restructure claim
    def test_a_partial_restructure_that_leaves_a_reread_row_unclaimed_is_refused(self) -> None:
        # Field 3's three delivered rows name only the first re-read row; the second claims to be newly added in both
        # relations. Every row's interval is the source's -- the lineage is what is false.
        episodes = self.copy()
        first, second = self.row(episodes, 3, 0), self.row(episodes, 3, 1)
        self.claim(episodes, [first["episode_id"]], [_id("R37-05", 3, k) for k in range(3)], None, RESTRUCTURED)
        second.update(predecessor_episode_ids="[]", lineage_state=cs.ADDED_STATES[cs.A05_FORMAT_VERSION],
                      disposition="ADDED")
        second.update(a04_episode_ids="[]", a04_lineage_state=cs.A04_ADDED, a04_disposition="ADDED_IN_A05")
        message = self.refused(REFUSED_RESTRUCTURE, self.successor("partial-restructure.sqlite", episodes))
        self.assertIn("1 of 1 target(s)", message)
        self.assertIn("the child field holding 2 row(s)", message)

    def test_a_count_preserving_false_restructure_stays_refused(self) -> None:
        episodes = self.copy()
        both = [_id("R37-05", 1, 0), _id("R37-05", 1, 1)]
        self.claim(episodes, [_id("C37A05", 1, k) for k in (0, 1)], both, None, RESTRUCTURED)
        self.refused(REFUSED_RESTRUCTURE, self.successor("count-preserving.sqlite", episodes))

    def test_a_collapse_claimed_in_one_relation_only_stays_refused(self) -> None:
        episodes = self.copy()
        # The default relation claims the collapse; the Attempt 4 relation keeps its first row only (its second
        # Attempt 4 row is left NOT_PRODUCED): that relation's count changes without a claim.
        keep = self.collapse(episodes, 1, a04=False)
        self.assertEqual(json.loads(keep["a04_episode_ids"]), [_id("C37A04", 1, 0)])
        self.refused(REFUSED_A04_ANCHOR, self.successor("one-relation.sqlite", episodes), "RESTRUCTURE")

    # ------------------------------------------------------------------ the Attempt 4 format
    def test_the_attempt4_format_collapse_expansion_and_forgery_are_refused(self) -> None:
        rows = [dict(r) for r in self.a4_rows.values()]
        self.collapse(rows, 1, prefix="C37A04")
        self.refused(REFUSED_CARDINALITY, self.a4_format("a4-collapse.sqlite", rows), _id("C37A04", 1, 0))
        rows = [dict(r) for r in self.a4_rows.values()]
        added = self.expand(rows, 1, prefix="C37A04")
        self.refused(REFUSED_CARDINALITY, self.a4_format("a4-expand.sqlite", rows), added[0])
        rows = [dict(r) for r in self.a4_rows.values()]
        self.row(rows, 2, 0, "C37A04").update(FORGED)
        self.refused(REFUSED_PERIOD_WITNESS, self.a4_format("a4-forged.sqlite", rows), _id("C37A04", 2, 0))

    # ------------------------------------------------------------------ the rules on their own
    def test_the_source_interval_check_on_its_own(self) -> None:
        intervals = civ.source_intervals(TEXT, civ.V375)
        genuine = [r for r in self.copy() if r["row_index"] == 1]

        def reading(row):
            return intervals.get((row["family"], int(row["row_index"])), civ.NO_SOURCE_ROW)

        counts = cs.check_source_intervals(genuine, "unit", reading)
        self.assertEqual((counts["rows_read_again_from_source"], counts["multi_interval_fields"]), (2, 1))
        with self.assertRaises(cs.CareerSuccessorError) as collapsed:
            cs.check_source_intervals(genuine[:1], "unit", reading)
        self.assertEqual(collapsed.exception.code, REFUSED_CARDINALITY)
        with self.assertRaises(cs.CareerSuccessorError) as forged:
            cs.check_source_intervals([{**genuine[0], **FORGED}, genuine[1]], "unit", reading)
        self.assertEqual(forged.exception.code, REFUSED_PERIOD_WITNESS)
        # the count is a field's, over the whole population the rows belong to
        cs.check_source_intervals(genuine[:1], "unit", reading, population=genuine)
        self.assertTrue(civ.is_cardinality(civ.COUNT_NOT_STATED) and civ.is_cardinality(civ.ORDINAL_NOT_STATED))
        self.assertFalse(civ.is_cardinality(civ.TEXT_NOT_ITS_INTERVAL))

    def test_the_restructure_qualification_on_its_own(self) -> None:
        # Rows compared by their own spans (no derived units): a claim naming only part of the re-read field refuses.
        child = {"episode_id": _id("C37A05", 3, 0), "pageid": PAGE, "revision": str(REVISION), "family": "COACHING",
                 "row_index": 3, "interval_index": 0, "team_char_span": "[272, 302]", "years_char_span": "[234, 255]",
                 "_parents": [_id("R37-05", 3, k) for k in range(3)]}
        sibling = {**child, "episode_id": _id("C37A05", 3, 1), "interval_index": 1, "_parents": []}
        parents = {_id("R37-05", 3, k): {**child, "episode_id": _id("R37-05", 3, k), "interval_index": k}
                   for k in range(3)}
        partial = {p: (RESTRUCTURED, [child["episode_id"]]) for p in parents}
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.check_anchors([child, sibling], parents, partial, "_parents", "predecessor")
        self.assertEqual(caught.exception.code, REFUSED_RESTRUCTURE)
        whole = {p: (RESTRUCTURED, [child["episode_id"], sibling["episode_id"]]) for p in parents}
        sibling["_parents"] = child["_parents"]
        counts = cs.check_anchors([child, sibling], parents, whole, "_parents", "predecessor")
        self.assertEqual(counts["restructure_claims_qualified"], 1)

    def test_each_refusal_left_the_genuine_fixture_attachable(self) -> None:
        for name in ("after-1.sqlite", "after-2.sqlite"):
            self.assertEqual(len(self.attach(self.successor(name))["_rows"]), 11)


if __name__ == "__main__":
    unittest.main()
