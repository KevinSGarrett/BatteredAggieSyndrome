"""Cycle #37 — Attempt #6 — MF37A05-01: successor lineage and raw evidence are typed identity bindings.

The Attempt 5 manager served seven Fred Mariani rows from two forged, re-hashed and explicitly pinned copies: one
swapped predecessor edges between Fred's row and Johnny Roland's, both ways; the other replaced one Fred row's raw
capture, digests, text and spans with Johnny's genuine capture while keeping Fred's page and revision. Reciprocity
and self-declared hashes hold in both, so neither is lineage evidence. These cases build a small, realistic
successor over three revision pages -- two different people and a homonym who shares the first one's display name
-- with a split row, an added row, an alias title and a row without a team span, and prove through the consumer
(``attach_successor`` and ``RawBytesVerifier``) that:

* every forgery class is refused for its own cause, each built independently from the genuine fixture:
  a reciprocal cross-person edge swap (Attempt 5 and Attempt 4 formats), a row naming a predecessor of another
  page, revision or family, another person's genuine raw capture under the row's own page and revision, an added
  row carrying another page's capture, a re-labelled display name or Wikidata item, a predecessor-row digest that
  is not the open predecessor's, an Attempt 4 edge of another page, an Attempt 4 row whose raw locator differs, and
  a mapping digest the Attempt 4 file's row does not hash to;
* a capture of another page, a display name not derivable from the capture's title and a contradicting Wikidata
  item are refused when a row is served, while a capture that states no Wikidata item is served and says so;
* the genuine fixture, a legitimate split, an added row, an alias, a homonym and a missing team span attach and serve.

A display name is never the identity: the homonym is a different page and a different Wikidata item.

Cycle #37 -- Attempt #8 (MF37A07-01): the verifier now proves every recorded span is the source field its row's
identity names in the cited revision. This fixture's revision was a bare list whose span ``[2, 10]`` held a link inside
a list line -- a witness no parser writes -- so the revision is now an infobox whose ``coach_team1``/``coach_years1``
values are exactly row 1's recorded spans (and text). No assertion or row changes.
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

TEXT = ("{{Infobox college coach\n| coach_years1 = 2009–2010\n| coach_team1 = [[Iowa]]\n| coach_years2 = 2011\n"
        "| coach_team2 = [[Ohio]]\n}}\n")
#: A11 (MF37A10-01): every successor row -- and every Attempt 4 row an edge names -- is now read again from its own
#: revision, and no field of a cited revision may be dropped whole. The fixture's rows stated dates their revision never
#: says (2009–2009 for ``2009–2010`` and ``2011``), its "legitimate split" divided a field that states one interval, and
#: its added row named a field its revision does not have. Each page now has its own revision: page 11's second field
#: states the two periods its split rows are (``2009, 2010``, read as one by the delivered parser -- a genuine re-read)
#: and page 22 states the field its added row is (``coach_years9``); every Attempt 4 and Attempt 5 row states what v37.4
#: and v37.5 read. The assertions are unchanged except the Attempt 4 format's row count (page 11's two Attempt 4 rows).
TEXTS = {11: TEXT.replace("| coach_years2 = 2011\n", "| coach_years2 = 2009, 2010\n"),
         22: TEXT.replace("}}\n", "| coach_years9 = 2011\n| coach_team9 = [[Rice]]\n}}\n"),
         33: TEXT}


def _read(page: int, row: int) -> list[tuple[int, int]]:
    """(start, end) of every interval the parsers read in a page's field."""

    if row == 1:
        return [(2009, 2010)]
    return [(2009, 2009), (2010, 2010)] if page == 11 else [(2011, 2011)]
#: (pageid, revision, title, display name, Wikidata item) -- the third page is a homonym of the first.
PAGES = ((11, 101, "Alpha Person", "Alpha Person", "Q11"),
         (22, 202, "Beta Person (American football)", "Beta Person", "Q22"),
         (33, 303, "Alpha Person (coach)", "Alpha Person", "Q33"))
ROWS = (1, 2)


def _id(prefix: str, page: int, revision: int, row: int, interval: int = 0, family: str = "COACHING") -> str:
    return f"{prefix}:{page}:{revision}:{family}:{row}:{interval}"


def _table(path: Path, table: str, columns: tuple[str, ...], rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE {table} ({', '.join(chr(34) + c + chr(34) for c in columns)})")
    for row in rows:
        conn.execute(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in columns)})", [row.get(c) for c in columns])
    conn.commit()
    conn.close()


class SuccessorIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.page = {}
        for pageid, revision, title, display, qid in PAGES:
            raw = self.root / f"raw_{pageid}.json"
            raw.write_bytes(json.dumps({"query": {"pages": {str(pageid): {
                "pageid": pageid, "title": title, "pageprops": {"wikibase_item": qid},
                "revisions": [{"revid": revision, "slots": {"main": {"*": TEXTS[pageid]}}}]}}}}).encode("utf-8"))
            self.page[pageid] = {"pageid": pageid, "revision": str(revision), "page_title": title,
                                 "person_display": display, "wikidata_qid": qid, "raw_file": str(raw),
                                 "raw_file_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                                 "wikitext_sha256": hashlib.sha256(TEXTS[pageid].encode("utf-8")).hexdigest(),
                                 "family": "COACHING", "ongoing": 0,
                                 "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "assignments": "[]"}
        years_start, team_start = TEXT.index("2009–2010"), TEXT.index("[[Iowa]]")
        spans = {"team_raw": "[[Iowa]]", "team_char_span": json.dumps([team_start, team_start + len("[[Iowa]]")]),
                 "years_raw": "2009–2010",
                 "years_char_span": json.dumps([years_start, years_start + len("2009–2010")])}
        # Predecessor and Attempt 4 rows: two per page.
        self.old = [{**self.page[p], "episode_id": _id("R37-05", p, self.page[p]["revision"], n), "row_index": n,
                     "interval_index": 0, "start": 2009, "end": 2009, **(spans if n == 1 else {})}
                    for p, *_ in PAGES for n in ROWS]
        # A11: the Attempt 4 rows state what v37.4 reads -- page 11's second field is two rows, re-read from its one
        # delivered row.
        self.a4_rows = []
        for row in self.old:
            read = _read(row["pageid"], row["row_index"])
            for interval, (start, end) in enumerate(read):
                self.a4_rows.append({**row, "episode_id": _id("C37A04", row["pageid"], row["revision"], row["row_index"],
                                                              interval),
                                     "interval_index": interval, "start": start, "end": end,
                                     "predecessor_episode_ids": json.dumps([row["episode_id"]]),
                                     "lineage_state": cs.DERIVED,
                                     "disposition": cs.RESTRUCTURED if len(read) > 1 else cs.UNCHANGED})
        # Attempt 5 rows: each predecessor row once, except page 11 row 2, which splits into two intervals
        # (a legitimate restructuring of its delivered row; A11: one to one with its two Attempt 4 rows), plus one row
        # added on page 22 with no predecessor row.
        episodes = []
        for row in self.old:
            read = _read(row["pageid"], row["row_index"])
            for interval, (start, end) in enumerate(read):
                a4 = _id("C37A04", row["pageid"], row["revision"], row["row_index"], interval)
                episodes.append({**row, "episode_id": _id("C37A05", row["pageid"], row["revision"], row["row_index"],
                                                          interval),
                                 "interval_index": interval, "start": start, "end": end,
                                 "predecessor_episode_ids": json.dumps([row["episode_id"]]), "lineage_state": cs.DERIVED,
                                 "a04_episode_ids": json.dumps([a4]), "a04_lineage_state": cs.A04_DERIVED,
                                 "date_basis": "ITEM_DATE_IN_BALANCED_PARENTHESES", "uncertainty_classes": "[]",
                                 "disposition": cs.RESTRUCTURED if len(read) > 1 else cs.UNCHANGED,
                                 "a04_disposition": cs.UNCHANGED})
        episodes.append({**self.page[22], "episode_id": _id("C37A05", 22, 202, 9), "row_index": 9, "interval_index": 0,
                         "start": 2011, "end": 2011, "predecessor_episode_ids": "[]",
                         "lineage_state": cs.ADDED_STATES[cs.A05_FORMAT_VERSION], "disposition": "ADDED",
                         "a04_episode_ids": "[]", "a04_lineage_state": cs.A04_ADDED, "a04_disposition": "ADDED_IN_A05",
                         "date_basis": "ITEM_DATE_IN_BALANCED_PARENTHESES", "uncertainty_classes": "[]"})
        self.episodes = episodes
        self.predecessor = self.root / "predecessor.sqlite"
        _table(self.predecessor, cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, self.old)
        self.a4 = self.root / "a04.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, self.a4_rows)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ building a (possibly forged) successor

    def _edges(self, episodes: list[dict], key: str) -> dict[str, list[str]]:
        edges: dict[str, list[str]] = {}
        for row in episodes:
            for parent in json.loads(row[key]):
                edges.setdefault(parent, []).append(row["episode_id"])
        return edges

    def dispositions(self, episodes: list[dict]) -> list[dict]:
        edges = self._edges(episodes, "predecessor_episode_ids")
        rows = []
        for old in self.old:
            children = sorted(edges.get(old["episode_id"], []))
            disposition = (cs.NOT_PRODUCED if not children else cs.RESTRUCTURED if len(children) > 1
                           else cs.UNCHANGED)
            rows.append({"predecessor_episode_id": old["episode_id"], "disposition": disposition,
                         "successor_episode_ids": json.dumps(children), "changed_fields": "{}",
                         "predecessor_row_sha256": cs.predecessor_row_digest(old), "screens": "[]",
                         "reason": "fixture"})
        return rows

    def mapping(self, episodes: list[dict]) -> list[dict]:
        edges = self._edges(episodes, "a04_episode_ids")
        rows = []
        for a4 in self.a4_rows:
            children = sorted(edges.get(a4["episode_id"], []))
            rows.append({"a04_episode_id": a4["episode_id"],
                         "disposition": cs.RESTRUCTURED if len(children) > 1 else cs.UNCHANGED,
                         "a05_episode_ids": json.dumps(children), "changed_fields": "{}",
                         "a04_row_sha256": cs.episode_row_digest(a4), "screens": "[]", "reason": "fixture"})
        return rows

    def successor(self, name: str, episodes: list[dict] | None = None, dispositions: list[dict] | None = None,
                  mapping: list[dict] | None = None) -> Path:
        """Write and seal a successor: every ledger is recomputed, as a careful forger would."""

        episodes = [dict(row) for row in (self.episodes if episodes is None else episodes)]
        dispositions = self.dispositions(episodes) if dispositions is None else dispositions
        mapping = self.mapping(episodes) if mapping is None else mapping
        path = self.root / name
        _table(path, cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, episodes)
        _table(path, cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, dispositions)
        _table(path, cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, mapping)
        self._seal(path, cs.A05_FORMAT_VERSION, cs.A05_SUCCESSOR_VERSION,
                   ((cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, "episode_id"),
                    (cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id"),
                    (cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, "a04_episode_id")),
                   {"a04_successor_path": str(self.a4), "a04_successor_sha256": cs.sha256_file(self.a4),
                    "a04_successor_row_count": str(len(self.a4_rows))})
        return path

    def a4_successor(self, name: str, episodes: list[dict]) -> Path:
        """An Attempt 4 format successor (the other supported entrypoint), sealed."""

        path = self.root / name
        _table(path, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, episodes)
        _table(path, cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, self.dispositions(episodes))
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

    def attach(self, successor: Path):
        conn = sqlite3.connect(self.predecessor.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return cs.attach_successor(conn, successor, database=self.predecessor), conn
        except Exception:
            conn.close()
            raise

    def served(self, successor: Path) -> list[dict]:
        binding, conn = self.attach(successor)
        try:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME} ORDER BY episode_id")]
        finally:
            conn.close()
        verifier = cs.RawBytesVerifier()
        for row in rows:
            verifier.verify(row)
        return rows

    def refused(self, code: str, successor: Path) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            self.served(successor)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    def row(self, episodes: list[dict], identity: str) -> dict:
        return next(r for r in episodes if r["episode_id"] == identity)

    def copy(self) -> list[dict]:
        return [dict(row) for row in self.episodes]

    # ------------------------------------------------------------------ accepted

    def test_the_genuine_fixture_attaches_and_serves_every_row_with_its_bindings_proved(self) -> None:
        binding, conn = self.attach(self.successor("genuine.sqlite"))
        conn.close()
        lineage = binding["lineage_proved_independently_of_the_ledgers"]
        self.assertEqual((lineage["episodes"], lineage["parent_edges_bound_to_page_revision_family"],
                          lineage["pages_uniform"], lineage["pages_without_predecessor_rows"],
                          lineage["a04_edges_bound_to_a04_file_raw_locator"],
                          lineage["dispositions_bound_to_predecessor_row_digest"]), (8, 7, 3, 0, 7, 6))
        self.assertEqual(binding["verifier_version"], cs.VERIFIER_VERSION)
        rows = self.served(self.successor("genuine-served.sqlite"))
        self.assertEqual(len(rows), 8)

    def test_legitimate_splits_added_rows_aliases_homonyms_and_missing_team_spans_serve(self) -> None:
        rows = {r["episode_id"]: r for r in self.served(self.successor("legitimate.sqlite"))}
        split = [i for i in rows if i.startswith("C37A05:11:101:COACHING:2:")]
        self.assertEqual(len(split), 2)                                   # one predecessor row, two successors
        self.assertEqual(rows[_id("C37A05", 22, 202, 9)]["lineage_state"], cs.ADDED_STATES[cs.A05_FORMAT_VERSION])
        self.assertEqual(rows[_id("C37A05", 22, 202, 1)]["person_display"], "Beta Person")   # alias of its title
        homonyms = {(r["pageid"], r["wikidata_qid"]) for r in rows.values() if r["person_display"] == "Alpha Person"}
        self.assertEqual(homonyms, {(11, "Q11"), (33, "Q33")})             # same name, two people
        self.assertIsNone(rows[_id("C37A05", 33, 303, 2)]["team_char_span"])
        verified = cs.RawBytesVerifier().verify(rows[_id("C37A05", 33, 303, 2)])
        self.assertEqual((verified["team_char_span"], verified["wikidata_item"]), ("NOT_RECORDED", "AGREES_WITH_CAPTURE"))

    def test_a_capture_that_states_no_wikidata_item_is_served_and_says_so(self) -> None:
        raw = Path(self.page[11]["raw_file"])
        payload = json.loads(raw.read_bytes())
        payload["query"]["pages"]["11"].pop("pageprops")
        raw.write_bytes(json.dumps(payload).encode("utf-8"))
        row = {**self.row(self.episodes, _id("C37A05", 11, 101, 1)),
               "raw_file_sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
        self.assertEqual(cs.RawBytesVerifier().verify(row)["wikidata_item"], "NOT_STATED_BY_CAPTURE")

    # ------------------------------------------------------------------ attach-time refusals, each independent

    def test_a_reciprocal_cross_person_edge_swap_is_refused_as_a_predecessor_identity_mismatch(self) -> None:
        episodes = self.copy()
        alpha, beta = self.row(episodes, _id("C37A05", 11, 101, 1)), self.row(episodes, _id("C37A05", 22, 202, 1))
        alpha["predecessor_episode_ids"], beta["predecessor_episode_ids"] = (beta["predecessor_episode_ids"],
                                                                             alpha["predecessor_episode_ids"])
        message = self.refused(cs.REFUSED_PREDECESSOR_IDENTITY, self.successor("swap.sqlite", episodes))
        self.assertIn("C37A05:11:101:COACHING:1:0 <- R37-05:22:202:COACHING:1:0", message)

    def test_the_same_swap_through_the_attempt4_format_is_refused(self) -> None:
        episodes = [dict(row) for row in self.a4_rows]
        # page 11 row 1 and page 22 row 1 (A11: by identity; page 11's second field is now two Attempt 4 rows)
        alpha, beta = self.row(episodes, _id("C37A04", 11, 101, 1)), self.row(episodes, _id("C37A04", 22, 202, 1))
        alpha["predecessor_episode_ids"], beta["predecessor_episode_ids"] = (beta["predecessor_episode_ids"],
                                                                             alpha["predecessor_episode_ids"])
        self.refused(cs.REFUSED_PREDECESSOR_IDENTITY, self.a4_successor("a4-swap.sqlite", episodes))
        # The genuine Attempt 4 format still attaches (seven rows: A11, page 11's field read as its two periods).
        self.assertEqual(len(self.served(self.a4_successor("a4-genuine.sqlite", [dict(r) for r in self.a4_rows]))), 7)

    def test_an_edge_to_an_identity_no_predecessor_row_has_is_dangling(self) -> None:
        episodes = self.copy()
        self.row(episodes, _id("C37A05", 11, 101, 1))["predecessor_episode_ids"] = json.dumps(
            ["R37-05:11:999:COACHING:1:0"])
        message = self.refused(cs.REFUSED_DANGLING, self.successor("edge-absent.sqlite", episodes))
        self.assertIn("R37-05:11:999:COACHING:1:0", message)

    def test_an_edge_to_a_predecessor_row_of_another_revision_or_family_is_refused(self) -> None:
        genuine = _id("R37-05", 11, 101, 1)
        for label, extra in (("revision", {"episode_id": "R37-05:11:999:COACHING:1:0", "revision": "999"}),
                             ("family", {"episode_id": _id("R37-05", 11, 101, 1, family="PLAYING"),
                                         "family": "PLAYING"})):
            with self.subTest(label=label):
                # A fixture predecessor that really holds such a row (the delivered predecessor is pinned).
                old = self.old + [{**next(r for r in self.old if r["episode_id"] == genuine), **extra}]
                self.predecessor = self.root / f"predecessor-{label}.sqlite"
                _table(self.predecessor, cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, old)
                saved, self.old = self.old, old
                try:
                    episodes = self.copy()
                    self.row(episodes, _id("C37A05", 11, 101, 1))["predecessor_episode_ids"] = json.dumps(
                        [extra["episode_id"]])
                    message = self.refused(cs.REFUSED_PREDECESSOR_IDENTITY,
                                           self.successor(f"edge-{label}.sqlite", episodes))
                    self.assertIn(extra["episode_id"], message)
                finally:
                    self.old = saved

    def test_another_persons_genuine_capture_under_the_rows_own_page_is_refused_as_a_source_locator_mismatch(self) -> None:
        episodes = self.copy()
        victim, donor = self.row(episodes, _id("C37A05", 11, 101, 1)), self.row(episodes, _id("C37A05", 22, 202, 1))
        for field in ("raw_file", "raw_file_sha256", "wikitext_sha256", "team_char_span", "team_raw",
                      "years_char_span", "years_raw"):
            victim[field] = donor[field]
        victim["raw_file_sha256"] = donor["raw_file_sha256"]
        message = self.refused(cs.REFUSED_SOURCE_LOCATOR, self.successor("other-raw.sqlite", episodes))
        self.assertIn("C37A05:11:101:COACHING:1:0", message)

    def test_an_added_row_carrying_another_pages_capture_is_refused_through_its_page(self) -> None:
        episodes = self.copy()
        added = self.row(episodes, _id("C37A05", 22, 202, 9))
        for field in ("raw_file", "raw_file_sha256"):
            added[field] = self.page[11][field]
        self.refused(cs.REFUSED_PAGE_IDENTITY, self.successor("added-other-raw.sqlite", episodes))

    def test_a_relabelled_display_name_or_wikidata_item_is_refused(self) -> None:
        for field, value in (("person_display", "Gamma Person"), ("wikidata_qid", "Q99"), ("page_title", "Gamma")):
            with self.subTest(field=field):
                episodes = self.copy()
                one = self.row(episodes, _id("C37A05", 22, 202, 1))
                one[field] = value
                self.refused(cs.REFUSED_PAGE_IDENTITY, self.successor(f"one-{field}.sqlite", episodes))
                # Relabelling every row of the page consistently is refused against the predecessor's page.
                episodes = self.copy()
                for row in episodes:
                    if row["pageid"] == 22:
                        row[field] = value
                self.refused(cs.REFUSED_PAGE_IDENTITY, self.successor(f"page-{field}.sqlite", episodes))

    def test_a_disposition_digest_that_is_not_the_open_predecessors_row_is_refused(self) -> None:
        dispositions = self.dispositions(self.episodes)
        dispositions[0] = {**dispositions[0], "predecessor_row_sha256": "0" * 64}
        self.refused(cs.REFUSED_ROW_BINDING, self.successor("digest.sqlite", dispositions=dispositions))

    def test_contradictory_attempt4_mappings_are_refused_for_their_cause(self) -> None:
        # An Attempt 4 edge of another page.
        episodes = self.copy()
        alpha, beta = self.row(episodes, _id("C37A05", 11, 101, 1)), self.row(episodes, _id("C37A05", 22, 202, 1))
        alpha["a04_episode_ids"], beta["a04_episode_ids"] = beta["a04_episode_ids"], alpha["a04_episode_ids"]
        self.refused(cs.REFUSED_A04_IDENTITY, self.successor("a4-edge-swap.sqlite", episodes))
        # An Attempt 4 file whose row carries another capture than the Attempt 5 row it maps to.
        self.a4_rows[0] = {**self.a4_rows[0], "raw_file_sha256": self.page[22]["raw_file_sha256"]}
        _table(self.root / "a04-b.sqlite", cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, self.a4_rows)
        self.a4 = self.root / "a04-b.sqlite"
        self.refused(cs.REFUSED_A04_IDENTITY, self.successor("a4-locator.sqlite"))

    def test_a_mapping_digest_the_attempt4_files_row_does_not_hash_to_is_refused(self) -> None:
        mapping = self.mapping(self.episodes)
        mapping[1] = {**mapping[1], "a04_row_sha256": "f" * 64}
        self.refused(cs.REFUSED_A04_MAPPING, self.successor("a4-digest.sqlite", mapping=mapping))

    # ------------------------------------------------------------------ serve-time refusals

    def test_a_capture_of_another_page_is_refused_when_a_row_is_served_whatever_its_digests_say(self) -> None:
        genuine = self.row(self.episodes, _id("C37A05", 11, 101, 1))
        other = {**genuine, "raw_file": self.page[22]["raw_file"], "raw_file_sha256": self.page[22]["raw_file_sha256"]}
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.RawBytesVerifier().verify(other)
        self.assertEqual(caught.exception.code, cs.REFUSED_RAW_PAGE)
        self.assertIn("the capture of page 22 revision 202", str(caught.exception))

    def test_a_display_name_or_wikidata_item_the_capture_contradicts_is_refused_when_served(self) -> None:
        genuine = self.row(self.episodes, _id("C37A05", 22, 202, 1))
        for field, value in (("person_display", "Fred Mariani"), ("wikidata_qid", "Q99")):
            with self.subTest(field=field):
                with self.assertRaises(cs.CareerSuccessorError) as caught:
                    cs.RawBytesVerifier().verify({**genuine, field: value})
                self.assertEqual(caught.exception.code, cs.REFUSED_PAGE_IDENTITY)
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.RawBytesVerifier().verify({**genuine, "page_title": "Gamma"})
        self.assertEqual(caught.exception.code, cs.REFUSED_RAW_PAGE)

    def test_display_names_are_derived_from_titles_not_trusted(self) -> None:
        self.assertEqual(cs.display_name_of_title("Beta Person (American football)"), "Beta Person")
        self.assertEqual(cs.display_name_of_title("Alpha Person"), "Alpha Person")
        self.assertEqual(cs.parse_identity("C37A05:11:101:COACHING:2:1"), ("C37A05", "11", "101", "COACHING", "2", "1"))
        self.assertIsNone(cs.parse_identity("C37A05:11:101:FENCING:2:1"))


if __name__ == "__main__":
    unittest.main()
