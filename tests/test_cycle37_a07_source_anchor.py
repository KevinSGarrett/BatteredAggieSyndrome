"""Cycle #37 — Attempt #7 — MF37A06-01: every lineage edge is bound to the source field and interval it was read from.

The Attempt 6 manager swapped the reciprocal default and Attempt 4 edges of two jobs on one biography -- Fred
Mariani's 1974 graduate-assistant row and his 2009 Rutgers row -- re-sealed the successor and was served: page,
revision, family, capture and row digests were all genuine. These cases build one realistic revision (an infobox
whose fields hold a single-year job, a two-interval field, two Rutgers jobs, an empty parameter, an employer line with
role lines, a field whose years are re-read as one interval, and rows with no fields at all), its predecessor rows, an
Attempt 4 file and an Attempt 5 successor, and prove through ``attach_successor`` and ``RawBytesVerifier`` that:

* the genuine fixture attaches and serves: role lines inside their employer line, a re-read (restructured) field, an
  empty parameter's zero-length spans, fieldless rows of the same parameter, a corrected date and an added row all
  keep their lineage -- no display name, normalized title or positional index is equated;
* each substitution, built independently from the genuine fixture, is refused for its own cause: the saved
  same-page cross-episode swap (``EPISODE``, default and Attempt 4 format entrypoints), a year-only anchor moved to
  another job's years (``YEARS``), a team-only anchor moved to another job's team (``TEAM``), two intervals of one
  field swapped -- same role, different period (``PERIOD``), a false restructure claim (``RESTRUCTURE_CLAIM``), two
  fieldless rows of different parameters swapped (``UNANCHORED``), an Attempt 4 edge naming another job
  (``A04_ANCHOR``) and an Attempt 4 file whose own lineage disagrees (``CROSS_VERSION_LINEAGE``).

Cycle #37 -- Attempt #8 (MF37A07-01). The verifier now proves, before comparing anchors, that every recorded span is
exactly the source field its row's identity names in the cited revision -- the check the Attempt 7 manager's enlarged
envelopes defeated. Two parts of this fixture were witnesses no parser writes, and are corrected to the parser's own
forms (every one of the 218,110 genuine rows records its unit exactly): the Northern Illinois employer line with its
role lines is a ``pastcoaching`` list line (rows 1001, 100101 and 100102, the parser's numbering) instead of role
rows 501/502 inside a numbered ``coach_team5`` value; and an empty parameter's zero-length span sits where the parser
puts it, after the value's whitespace. Rows with no recorded span stay absent fields. Two expectations change for the
stricter reason: a year-only or team-only anchor moved onto another job's field is no longer the victim row's own
source field, so it is refused as ``REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH`` before any anchor is
compared; the ``YEARS`` and ``TEAM`` anchor causes remain proved on their own in ``test_the_anchor_rules_on_their_own``.
``test_cycle37_a08_source_witness`` adds the enlarged-envelope, boundary and full-page substitutions.

Cycle #37 -- Attempt #9 (MF37A08-01). An edge is now anchored by the source units its two rows' identities name in the
cited revision -- never by the rows' own spans or text, which the Attempt 8 manager nulled and enlarged -- so a row
whose identity names nothing in the revision can carry no lineage (no genuine row of the three populations is such a
row). Rows 9 and 11 were such "fieldless" rows; they are now years-only numbered fields (``coach_years9``,
``coach_years11``, no team parameter), the genuine form of 22 Attempt 5 rows. Their edges are anchored by their years
fields (the parameter-only count falls from 2 to 0), and the swap of the two is refused as the ``YEARS`` anchor it is.
The ``UNANCHORED`` cause -- no comparable field and another parameter, or a row naming no unit -- is proved by
``test_cycle37_a09_missing_witness``. The added row 12 stays fieldless: it carries no lineage. The delivered rows'
years text without a years span is exactly each field's value, which the Attempt 9 rule keeps.

Cycle #37 -- Attempt #10 (MF37A09-01). Interval text is never agreement: inside one multi-interval field an edge joins
the interval its two identities name (equal ordinals), and a successor row's stated interval is read again from its
source by its own parser version. The ``PERIOD`` swap below is refused for its crossed ordinals (its message still
quotes the texts, which decide nothing); ``period_agrees`` -- the text-containment rule the Attempt 9 manager defeated
with blank and copied text -- is gone, and ``test_the_anchor_rules_on_their_own`` asserts the ordinal rule instead.
One part of this fixture was a form no parser writes, and is corrected: the Attempt 4 file held the delivered v37.2
reading of ``coach_years6 = 1911&ndash;1916`` (two rows, ``1911`` and ``1916``), but the v37.4 parser reads it as one
interval, ``1911–1916`` -- the genuine Attempt 4 file matches its parser on all 281 rows of its multi-interval fields.
The Attempt 4 file now holds that one row, restructured from the two delivered rows, and the Attempt 5 row ``C6`` derives
from it unchanged; so the Attempt 4 file has 9 rows (was 10) and the Attempt 4 relation 11 edges (was 12).
``test_cycle37_a10_interval_lineage`` adds the interval-grain forgeries and legitimate forms.
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

from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402

PAGE, REVISION, TITLE, QID = 7, 70, "Fixture Coach (American football)", "Q7"
NIU = ("[[Northern Illinois Huskies football|Northern Illinois]] (1980–1984)<br>Wide receivers (1980–1981)<br>"
       "Defensive line (1982–1984)")
FIELDS = [("coach_years1", "1974"), ("coach_team1", "[[Saint Joseph's Pumas football|Saint Joseph's (IN)]] (GA)"),
          ("coach_years2", "1926, 1928–1930"), ("coach_team2", "[[William & Mary Tribe football|William & Mary]]"),
          ("coach_years3", "2009–?"), ("coach_team3", "[[Rutgers Scarlet Knights football|Rutgers]] (DFO)"),
          ("coach_years4", ""), ("coach_team4", ""),
          ("coach_years6", "1911&ndash;1916"), ("coach_team6", "[[YMCA (Columbus, Georgia)|Columbus YMCA]]"),
          # A9: years-only numbered fields (no team parameter), formerly "fieldless" rows naming nothing.
          ("coach_years9", "1950"), ("coach_years11", "1955")]
#: A8: the employer line with its role lines is a career list line, as the parser reads one (row 1001 and its role
#: lines 100101, 100102).
TEXT = ("{{Infobox college coach\n" + "".join(f"| {name} = {value}\n" for name, value in FIELDS)
        + "| pastcoaching =\n* " + NIU + "\n}}\n")


def at(name: str) -> list[int]:
    """The span of a parameter's value; an empty value's zero-length span sits after its whitespace, where the
    parser's parameter split puts it."""

    start = TEXT.index(f"| {name} = ") + len(f"| {name} = ")
    if not dict(FIELDS)[name]:
        while TEXT[start] in " \t\n":
            start += 1
    return [start, start + len(dict(FIELDS)[name])]


def line(part: str) -> list[int]:
    """The span of a list line or role line of the ``pastcoaching`` list (it occurs once in the revision)."""

    start = TEXT.index(part)
    return [start, start + len(part)]


def inside(outer: str, part: str) -> list[int]:
    start = TEXT.index(outer) + outer.index(part)
    return [start, start + len(part)]


def _id(prefix: str, row: int, interval: int = 0) -> str:
    return f"{prefix}:{PAGE}:{REVISION}:COACHING:{row}:{interval}"


def _table(path: Path, table: str, columns: tuple[str, ...], rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE {table} ({', '.join(chr(34) + c + chr(34) for c in columns)})")
    for row in rows:
        conn.execute(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in columns)})", [row.get(c) for c in columns])
    conn.commit()
    conn.close()


class SourceAnchorTests(unittest.TestCase):
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

        def team(n: int) -> dict:
            return {"team_raw": dict(FIELDS)[f"coach_team{n}"], "team_char_span": json.dumps(at(f"coach_team{n}"))}

        def years_text(n: int) -> dict:
            return {"years_raw": dict(FIELDS)[f"coach_years{n}"]}

        def years_span(n: int) -> dict:
            return {"years_char_span": json.dumps(at(f"coach_years{n}"))}

        # The delivered predecessor's parser recorded team spans but no years spans (as 21,597 genuine rows do), read
        # two-endpoint years as separate intervals, and recorded empty parameters as zero-length spans.
        self.old = {r["episode_id"]: {**page, **r} for r in [
            {"episode_id": _id("R37-05", 1), "row_index": 1, "interval_index": 0, **team(1), **years_text(1),
             "years_as_written": "1974", "start": 1974, "end": 1974},
            {"episode_id": _id("R37-05", 2, 0), "row_index": 2, "interval_index": 0, **team(2), **years_text(2),
             "years_as_written": "1926", "start": 1926, "end": 1926},
            {"episode_id": _id("R37-05", 2, 1), "row_index": 2, "interval_index": 1, **team(2), **years_text(2),
             "years_as_written": "1928–1930", "start": 1928, "end": 1930},
            {"episode_id": _id("R37-05", 3), "row_index": 3, "interval_index": 0, **team(3), **years_text(3),
             "years_as_written": "2009", "start": 2009, "end": 2009},
            {"episode_id": _id("R37-05", 4), "row_index": 4, "interval_index": 0, **team(4), **years_text(4),
             **years_span(4), "start": None, "end": None},
            {"episode_id": _id("R37-05", 1001), "row_index": 1001, "interval_index": 0, "team_raw": NIU,
             "team_char_span": json.dumps(line(NIU)), "years_raw": "1980–1984", "years_as_written": "1980–1984",
             "start": 1980, "end": 1984},
            {"episode_id": _id("R37-05", 6, 0), "row_index": 6, "interval_index": 0, **team(6), **years_text(6),
             "years_as_written": "1911", "start": 1911, "end": 1911},
            {"episode_id": _id("R37-05", 6, 1), "row_index": 6, "interval_index": 1, **team(6), **years_text(6),
             "years_as_written": "1916", "start": 1916, "end": 1916},
            {"episode_id": _id("R37-05", 9), "row_index": 9, "interval_index": 0, **years_text(9),
             "years_as_written": "1950", "start": 1950, "end": 1950},
            {"episode_id": _id("R37-05", 11), "row_index": 11, "interval_index": 0, **years_text(11),
             "years_as_written": "1955", "start": 1955, "end": 1955},
        ]}
        # Attempt 4: the predecessor's rows one for one, with their own lineage (the Attempt 4 relation).
        self.a4_rows = {i.replace("R37-05", "C37A04"): {**r, "episode_id": i.replace("R37-05", "C37A04"),
                                                        "predecessor_episode_ids": json.dumps([i]),
                                                        "lineage_state": cs.DERIVED, "disposition": cs.UNCHANGED}
                        for i, r in self.old.items()}
        # A10: v37.4 reads "1911&ndash;1916" as one interval (the genuine Attempt 4 form), restructured from the two
        # delivered rows -- not the delivered reading's two rows copied into the Attempt 4 file.
        for interval in (0, 1):
            del self.a4_rows[_id("C37A04", 6, interval)]
        self.a4_rows[_id("C37A04", 6)] = {**self.old[_id("R37-05", 6, 0)], "episode_id": _id("C37A04", 6),
                                          "years_as_written": "1911–1916", "start": 1911, "end": 1916,
                                          "predecessor_episode_ids": json.dumps([_id("R37-05", 6, 0),
                                                                                 _id("R37-05", 6, 1)]),
                                          "lineage_state": cs.DERIVED, "disposition": cs.RESTRUCTURED}
        # Attempt 5: years spans recorded; the second job keeps two intervals; role lines of the employer line are their
        # own rows; the YMCA years are re-read as one interval (restructured); an added row.
        new = [
            ("C1", [_id("R37-05", 1)], {"row_index": 1, "interval_index": 0, **team(1), **years_text(1), **years_span(1),
                                        "years_as_written": "1974", "start": 1974, "end": 1974}, cs.CORRECTED),
            ("C2a", [_id("R37-05", 2, 0)], {"row_index": 2, "interval_index": 0, **team(2), **years_text(2),
                                             **years_span(2), "years_as_written": "1926", "start": 1926, "end": 1926},
             cs.CORRECTED),
            ("C2b", [_id("R37-05", 2, 1)], {"row_index": 2, "interval_index": 1, **team(2), **years_text(2),
                                             **years_span(2), "years_as_written": "1928–1930", "start": 1928,
                                             "end": 1930}, cs.CORRECTED),
            ("C3", [_id("R37-05", 3)], {"row_index": 3, "interval_index": 0, **team(3), **years_text(3), **years_span(3),
                                        "years_as_written": "2009–?", "start": 2009, "end": None},
             cs.UNRESOLVED_EXPLICIT),
            ("C4", [_id("R37-05", 4)], {"row_index": 4, "interval_index": 0, **team(4), **years_text(4),
                                        **years_span(4), "start": None, "end": None}, cs.UNCHANGED),
            ("C1001", [_id("R37-05", 1001)], {"row_index": 1001, "interval_index": 0, "team_raw": NIU,
                                              "team_char_span": json.dumps(line(NIU)), "years_raw": "1980–1984",
                                              "years_char_span": json.dumps(inside(NIU, "1980–1984")),
                                              "years_as_written": "1980–1984", "start": 1980, "end": 1984}, cs.CORRECTED),
            ("C100101", [_id("R37-05", 1001)], {"row_index": 100101, "interval_index": 0,
                                                "team_raw": "Wide receivers (1980–1981)",
                                                "team_char_span": json.dumps(line("Wide receivers (1980–1981)")),
                                                "years_raw": "1980–1981",
                                                "years_char_span": json.dumps(inside("Wide receivers (1980–1981)",
                                                                                     "1980–1981")),
                                                "years_as_written": "1980–1981", "start": 1980, "end": 1981},
             cs.CORRECTED),
            ("C100102", [_id("R37-05", 1001)], {"row_index": 100102, "interval_index": 0,
                                                "team_raw": "Defensive line (1982–1984)",
                                                "team_char_span": json.dumps(line("Defensive line (1982–1984)")),
                                                "years_raw": "1982–1984",
                                                "years_char_span": json.dumps(inside("Defensive line (1982–1984)",
                                                                                     "1982–1984")),
                                                "years_as_written": "1982–1984", "start": 1982, "end": 1984},
             cs.CORRECTED),
            ("C6", [_id("R37-05", 6, 0), _id("R37-05", 6, 1)],
             {"row_index": 6, "interval_index": 0, **team(6), **years_text(6), **years_span(6),
              "years_as_written": "1911–1916", "start": 1911, "end": 1916}, cs.RESTRUCTURED),
            ("C9", [_id("R37-05", 9)], {"row_index": 9, "interval_index": 0, **years_text(9), **years_span(9),
                                        "years_as_written": "1950", "start": 1950, "end": 1950}, cs.UNCHANGED),
            ("C11", [_id("R37-05", 11)], {"row_index": 11, "interval_index": 0, **years_text(11), **years_span(11),
                                          "years_as_written": "1955", "start": 1955, "end": 1955}, cs.UNCHANGED),
        ]
        ids = {"C1": _id("C37A05", 1), "C2a": _id("C37A05", 2, 0), "C2b": _id("C37A05", 2, 1), "C3": _id("C37A05", 3),
               "C4": _id("C37A05", 4), "C1001": _id("C37A05", 1001), "C100101": _id("C37A05", 100101),
               "C100102": _id("C37A05", 100102), "C6": _id("C37A05", 6), "C9": _id("C37A05", 9),
               "C11": _id("C37A05", 11)}
        self.ids = ids
        self.episodes = []
        for key, parents, fields, disposition in new:
            a4 = [p.replace("R37-05", "C37A04") for p in parents]
            a4_disposition = disposition
            if key == "C6":   # A10: the one Attempt 4 row "1911–1916", read again unchanged
                a4, a4_disposition = [_id("C37A04", 6)], cs.UNCHANGED
            self.episodes.append({**page, **fields, "episode_id": ids[key], "predecessor_episode_ids": json.dumps(parents),
                                  "lineage_state": cs.DERIVED, "disposition": disposition,
                                  "a04_episode_ids": json.dumps(a4), "a04_lineage_state": cs.A04_DERIVED,
                                  "a04_disposition": a4_disposition, "date_basis": "FIXTURE",
                                  "uncertainty_classes": "[]"})
        self.episodes.append({**page, "episode_id": _id("C37A05", 12), "row_index": 12, "interval_index": 0,
                              "start": 2020, "end": 2020, "predecessor_episode_ids": "[]",
                              "lineage_state": cs.ADDED_STATES[cs.A05_FORMAT_VERSION], "disposition": "ADDED",
                              "a04_episode_ids": "[]", "a04_lineage_state": cs.A04_ADDED,
                              "a04_disposition": "ADDED_IN_A05", "date_basis": "FIXTURE", "uncertainty_classes": "[]"})
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
        rows = []
        for identity, owner in owners.items():
            children = sorted(edges.get(identity, []))
            states = {row["disposition" if key == "predecessor_episode_ids" else "a04_disposition"]
                      for row in episodes if row["episode_id"] in children}
            state = cs.NOT_PRODUCED if not children else (states.pop() if len(states) == 1 else cs.CORRECTED)
            rows.append({id_key: identity, "disposition": state, list_key: json.dumps(children),
                         "changed_fields": "{}", digest[0]: digest[1](owner), "screens": "[]", "reason": "fixture"})
        return rows

    def successor(self, name: str, episodes: list[dict] | None = None) -> Path:
        """Write and seal an Attempt 5 successor, every ledger recomputed as a careful forger would."""

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

    def attach(self, successor: Path) -> dict:
        conn = sqlite3.connect(self.predecessor.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            binding = cs.attach_successor(conn, successor, database=self.predecessor)
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME} ORDER BY episode_id")]
        finally:
            conn.close()
        verifier = cs.RawBytesVerifier()
        for row in rows:
            verifier.verify(row)
        binding["_rows"] = rows
        return binding

    def refused(self, code: str, successor: Path) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            self.attach(successor)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    def copy(self) -> list[dict]:
        return [dict(r) for r in self.episodes]

    def row(self, episodes: list[dict], key: str) -> dict:
        return next(r for r in episodes if r["episode_id"] == self.ids[key])

    def swap(self, episodes: list[dict], a: str, b: str, *, default: bool = True, a04: bool = True) -> None:
        """Swap two rows' edges both ways, with their disposition texts, as the manager's probe does."""

        x, y = self.row(episodes, a), self.row(episodes, b)
        if default:
            x["predecessor_episode_ids"], y["predecessor_episode_ids"] = (y["predecessor_episode_ids"],
                                                                         x["predecessor_episode_ids"])
            x["disposition"], y["disposition"] = y["disposition"], x["disposition"]
        if a04:
            x["a04_episode_ids"], y["a04_episode_ids"] = y["a04_episode_ids"], x["a04_episode_ids"]
            x["a04_disposition"], y["a04_disposition"] = y["a04_disposition"], x["a04_disposition"]

    # ------------------------------------------------------------------ accepted
    def test_the_genuine_fixture_attaches_and_serves_with_every_edge_anchored(self) -> None:
        binding = self.attach(self.successor("genuine.sqlite"))
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        default, a04 = lineage["parent_edges_bound_to_source_field"], lineage["a04_edges_bound_to_source_field"]
        # A9: rows 9 and 11 are years-only fields now, anchored by their years fields (were 10 and 2 parameter-only).
        self.assertEqual((default["edges"], default["anchored_by_source_field"], default["anchored_by_parameter_only"],
                          default["restructured_entries"], default["interval_checked"]), (12, 12, 0, 1, 2))
        # A10: C6 derives from the one Attempt 4 row v37.4 wrote for the re-read field (was two copied rows).
        self.assertEqual((a04["edges"], a04["anchored_by_parameter_only"]), (11, 0))
        self.assertEqual((default["anchored_on"], a04["anchored_on"]), ("DERIVED_SOURCE_UNITS", "DERIVED_SOURCE_UNITS"))
        self.assertEqual(lineage["rows_whose_versions_agree_on_predecessor_rows"], 12)
        self.assertEqual(len(binding["_rows"]), 12)
        served = {r["episode_id"]: r for r in binding["_rows"]}
        self.assertEqual(served[self.ids["C100101"]]["team_raw"], "Wide receivers (1980–1981)")   # a role line
        self.assertEqual(json.loads(served[self.ids["C6"]]["predecessor_episode_ids"]),       # a re-read field
                         [_id("R37-05", 6, 0), _id("R37-05", 6, 1)])

    def test_the_anchor_rules_on_their_own(self) -> None:
        empty = {"team_char_span": "[40, 40]", "team_raw": ""}
        self.assertEqual(cs.field_anchor(empty, {"team_char_span": "[40, 40]"}, "team"), "AGREES")
        self.assertEqual(cs.field_anchor({"years_char_span": "[50, 54]"}, {"team_char_span": "[30, 80]"}, "years"),
                         "AGREES")                                                  # inside the parent's region
        self.assertEqual(cs.field_anchor({"years_char_span": "[5, 9]", "years_raw": "1974"},
                                         {"team_char_span": "[30, 80]", "years_raw": "1974"}, "years"), "AGREES")
        self.assertEqual(cs.field_anchor({"years_char_span": "[5, 9]", "years_raw": "2009–?"},
                                         {"team_char_span": "[30, 80]", "years_raw": "1974"}, "years"), "DISAGREES")
        self.assertEqual(cs.field_anchor({"team_raw": None}, {"team_raw": "[[X]]"}, "team"), "NOT_COMPARABLE")
        # A8: the anchor causes on their own -- one field of another job (the other agreeing) names that field; two
        # proven units that merely overlap are two fields, never one.
        one = {"team_char_span": "[10, 40]", "years_char_span": "[2, 6]"}
        three = {"team_char_span": "[10, 40]", "years_char_span": "[50, 56]"}
        self.assertEqual(cs.edge_anchor(one, three)[0], "YEARS")
        self.assertEqual(cs.edge_anchor({"team_char_span": "[60, 90]", "years_char_span": "[50, 56]"}, three)[0],
                         "TEAM")
        self.assertEqual(cs.field_anchor({"team_char_span": "[10, 40]"}, {"team_char_span": "[30, 60]"}, "team"),
                         "DISAGREES")
        # A10 (MF37A09-01): inside one field an edge joins the interval its identities name -- the ordinal, never the
        # text ("1959" read again as "1959–1967" keeps ordinal 0; "1926" and "1928–1930" are ordinals 0 and 1).
        self.assertEqual((cs.interval_ordinal(_id("C37A05", 2, 0)), cs.interval_ordinal(_id("R37-05", 2, 1))), (0, 1))
        self.assertIsNone(cs.interval_ordinal("1926"))
        self.assertFalse(hasattr(cs, "period_agrees"))

    # ------------------------------------------------------------------ refused, each built from the genuine fixture
    def test_the_saved_same_page_cross_episode_swap_is_refused_as_an_episode_anchor(self) -> None:
        episodes = self.copy()
        self.swap(episodes, "C1", "C3")                   # the 1974 GA row and the 2009 Rutgers row, both relations
        message = self.refused(cs.REFUSED_EPISODE_ANCHOR, self.successor("same-page-swap.sqlite", episodes))
        self.assertIn(f"{self.ids['C1']} <- {_id('R37-05', 3)}", message)

    def test_the_same_swap_through_the_attempt4_format_entrypoint_is_refused(self) -> None:
        rows = [dict(r) for r in self.a4_rows.values()]
        a, b = (next(r for r in rows if r["episode_id"] == _id("C37A04", n)) for n in (1, 3))
        a["predecessor_episode_ids"], b["predecessor_episode_ids"] = (b["predecessor_episode_ids"],
                                                                     a["predecessor_episode_ids"])
        self.refused(cs.REFUSED_EPISODE_ANCHOR, self.a4_format("a4-swap.sqlite", rows))
        # A10: 9 Attempt 4 rows -- the re-read field is the one row v37.4 wrote (was two copied delivered rows).
        self.assertEqual(len(self.attach(self.a4_format("a4-genuine.sqlite",
                                                        [dict(r) for r in self.a4_rows.values()]))["_rows"]), 9)

    def test_a_year_only_anchor_substitution_is_refused_as_a_years_anchor(self) -> None:
        # A8: the moved years span is another job's field, not the one row 1's identity names -- refused as a source
        # field witness before any anchor is compared (the YEARS anchor cause itself: test_the_anchor_rules_on_their_own).
        episodes = self.copy()
        victim = self.row(episodes, "C1")
        victim["years_raw"], victim["years_char_span"] = "2009–?", json.dumps(at("coach_years3"))
        message = self.refused(cs.REFUSED_SOURCE_FIELD, self.successor("year-only.sqlite", episodes))
        self.assertIn("YEARS_NOT_SOURCE_UNIT", message)

    def test_a_team_only_anchor_substitution_is_refused_as_a_team_anchor(self) -> None:
        # A8: likewise for a team span moved onto another job's team field.
        episodes = self.copy()
        victim = self.row(episodes, "C1")
        victim["team_raw"], victim["team_char_span"] = dict(FIELDS)["coach_team3"], json.dumps(at("coach_team3"))
        message = self.refused(cs.REFUSED_SOURCE_FIELD, self.successor("team-only.sqlite", episodes))
        self.assertIn("TEAM_NOT_SOURCE_UNIT", message)

    def test_same_role_different_period_intervals_swapped_are_refused_as_a_period_anchor(self) -> None:
        episodes = self.copy()
        self.swap(episodes, "C2a", "C2b")                  # 1926 and 1928–1930 of one William & Mary field
        message = self.refused(cs.REFUSED_PERIOD_ANCHOR, self.successor("period-swap.sqlite", episodes))
        self.assertIn("'1926'", message)

    def test_a_false_restructure_claim_is_refused(self) -> None:
        episodes = self.copy()
        both = json.dumps([_id("R37-05", 2, 0), _id("R37-05", 2, 1)])
        for key in ("C2a", "C2b"):                          # two intervals claimed "re-read" into the same two
            row = self.row(episodes, key)
            row["predecessor_episode_ids"], row["disposition"] = both, cs.RESTRUCTURED
        self.refused(cs.REFUSED_RESTRUCTURE, self.successor("false-restructure.sqlite", episodes))

    def test_years_only_rows_of_different_parameters_swapped_are_refused_as_a_years_anchor(self) -> None:
        # A9: formerly "fieldless rows ... are unanchored"; rows 9 and 11 are years-only fields now, so their swap names
        # another years field (the UNANCHORED cause: test_cycle37_a09_missing_witness).
        episodes = self.copy()
        self.swap(episodes, "C9", "C11")
        self.refused(cs.REFUSED_YEARS_ANCHOR, self.successor("unanchored.sqlite", episodes))

    def test_a_cross_version_anchor_substitution_is_refused(self) -> None:
        episodes = self.copy()
        self.swap(episodes, "C1", "C3", default=False)     # the default edges stay genuine; the Attempt 4 ones swap
        message = self.refused(cs.REFUSED_A04_ANCHOR, self.successor("cross-version-anchor.sqlite", episodes))
        self.assertIn("EPISODE", message)
        episodes = self.copy()
        self.swap(episodes, "C2a", "C2b", default=False)   # two intervals, Attempt 4 relation only
        message = self.refused(cs.REFUSED_A04_ANCHOR, self.successor("cross-version-period.sqlite", episodes))
        self.assertIn("PERIOD", message)

    def test_an_attempt4_file_whose_own_lineage_disagrees_is_refused(self) -> None:
        # Every Attempt 5 edge is genuine and anchored; the Attempt 4 rows themselves claim each other's parents.
        one, three = self.a4_rows[_id("C37A04", 1)], self.a4_rows[_id("C37A04", 3)]
        one["predecessor_episode_ids"], three["predecessor_episode_ids"] = (three["predecessor_episode_ids"],
                                                                           one["predecessor_episode_ids"])
        self.a4 = self.root / "a04-crossed.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, list(self.a4_rows.values()))
        self.refused(cs.REFUSED_CROSS_VERSION, self.successor("cross-version-lineage.sqlite"))

    def test_each_refusal_left_the_genuine_fixture_attachable(self) -> None:
        for name in ("after-1.sqlite", "after-2.sqlite"):
            self.assertEqual(len(self.attach(self.successor(name))["_rows"]), 12)


if __name__ == "__main__":
    unittest.main()
