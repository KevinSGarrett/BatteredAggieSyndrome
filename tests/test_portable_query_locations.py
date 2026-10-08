"""BAT-717 (Cycle #45 — Attempt #1, TP45-A01-02/03): installed query consumers at portable local locations.

Consumer level: every test drives an existing consumer entry -- the national population query (``main`` and its
verified handle), the read-only connections of the national history, source-time and staff queries, the staff
import API and the career successor attachment with its Attempt 4 parent. None imports the shared helper, so this
module runs unchanged against a copy of the unfixed base (BEFORE_REPRODUCTION): ordinary short, relative and
punctuation locations pass there, and the native extended-length, long, trailing-dot, device and '#'-bearing
Attempt 4 locations fail there.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from aggie_analytics.cycle33 import query as staff_query  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402
from aggie_analytics.national_history import query as history_query  # noqa: E402
from aggie_analytics.national_population import query as population_query  # noqa: E402
from aggie_analytics.national_source_time import query as source_time_query  # noqa: E402
from test_cycle37_a05_career_successor import IDS, READ, REVISION_TEXT, _a4, _a5, _pid, _table  # noqa: E402
from test_national_population_query import build_database  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
PUNCTUATION = "p #%'é &x=1 %3Fq"
FORGED = " [C45 FORGED TWIN]"


def native(path: str | Path) -> str:
    """The spelling every fixture file operation uses: verbatim on Windows (any length) and never normalized --
    ``os.path.abspath`` would strip a trailing dot and so name a different directory."""
    text = str(path)
    if not os.path.isabs(text):
        text = os.path.join(os.getcwd(), text)
    return EXT + text if WINDOWS and not text.startswith(EXT) else text


def copy_tree(source: Path, target: str) -> None:
    """Copy every file of ``source`` under ``target`` (verbatim paths on Windows, so any length works)."""
    for dirpath, _dirs, files in os.walk(source):
        for name in files:
            src = os.path.join(dirpath, name)
            dst = native(os.path.join(target, os.path.relpath(src, source)))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)


def long_root(base: str) -> str:
    """A directory whose files lie beyond 300 characters from any local temporary root.

    Below a bare drive root the extended spelling of ``db #.sqlite`` has 326 characters (longest component 135). With
    only the first two components the hosted Windows runners' 22-character temporary root gave exactly 300, and the
    consumer test's own length check failed before any consumer ran (MF45A01-01)."""
    return os.path.join(base, "long " + "x" * 120, "deeper # % é ' " + "y" * 120, "tail " + "z" * 40)


def tiny_database(path: str, value: str) -> str:
    target = native(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    conn = sqlite3.connect(target)
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t VALUES (?)", (value,))
    conn.commit()
    conn.close()
    return target


def sha(path: str) -> str:
    with open(native(path), "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class TempRoot(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)

    def tearDown(self) -> None:
        if WINDOWS:  # a tree beyond 260 characters is removable only through the verbatim spelling
            shutil.rmtree(native(self.root))
        self._tmp.cleanup()


class PopulationLocationTests(TempRoot):
    """The national population query over byte-identical copies of one tiny verified lake."""

    ARGS = ("--grain", "contest", "--all")

    def setUp(self) -> None:
        super().setUp()
        self.base = Path(self.root) / "d"
        self.db = build_database(self.base)
        self.rel = Path(os.path.relpath(self.db, self.base))
        self.reference = self.run_main(str(self.db))

    def run_main(self, database: str, *args: str) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = population_query.main(["--database", database, *(args or self.ARGS)])
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def relocated(self, root: str) -> str:
        copy_tree(self.base, root)
        return os.path.join(root, str(self.rel))

    def assert_same_answer(self, database: str) -> None:
        code, result, err = self.run_main(database)
        self.assertEqual(code, 0, err)
        self.assertEqual(result, self.reference[1])

    def test_the_original_short_location_serves_the_verified_rows(self) -> None:
        code, result, err = self.reference
        self.assertEqual(code, 0, err)
        self.assertEqual(result["total"], 6)

    def test_a_relative_location_serves_the_same_rows(self) -> None:
        here = os.getcwd()
        try:
            os.chdir(self.base)
            self.assert_same_answer(str(self.rel))
        finally:
            os.chdir(here)

    def test_a_punctuation_location_serves_the_same_rows(self) -> None:
        self.assert_same_answer(self.relocated(os.path.join(self.root, PUNCTUATION)))

    def test_a_missing_database_is_refused_and_not_created(self) -> None:
        missing = os.path.join(self.root, "m", str(self.rel))
        code, _result, err = self.run_main(missing)
        self.assertEqual(code, 2, err)
        self.assertFalse(os.path.exists(native(missing)))

    @unittest.skipUnless(WINDOWS, "Windows native extended-length spelling")
    def test_a_long_extended_location_serves_the_same_rows(self) -> None:
        database = native(self.relocated(long_root(self.root)))
        self.assertGreater(len(database), 300)
        self.assert_same_answer(database)

    @unittest.skipUnless(WINDOWS, "Windows native extended-length spelling")
    def test_a_short_extended_location_serves_the_same_rows(self) -> None:
        self.assert_same_answer(native(self.db))

    @unittest.skipUnless(WINDOWS, "Windows trailing-dot names exist only through the extended-length spelling")
    def test_a_trailing_dot_location_is_refused_never_its_normalized_twin(self) -> None:
        literal = native(self.relocated(os.path.join(self.root, "dot.")))
        twin = native(self.relocated(os.path.join(self.root, "dot")))
        conn = sqlite3.connect(twin)
        conn.execute("UPDATE contest SET a_team_name = a_team_name || ?", (FORGED,))
        conn.commit()
        conn.close()
        code, result, err = self.run_main(literal)
        self.assertEqual(code, 2, err)
        self.assertEqual(json.loads(err.strip().splitlines()[-1])["refused"], "DATABASE_LOCATION_NOT_LITERAL")
        self.assertIsNone(result)

    @unittest.skipUnless(WINDOWS, "Windows local drive device spelling")
    def test_the_local_drive_device_spelling_serves_the_same_rows(self) -> None:
        self.assert_same_answer("\\\\.\\" + os.path.abspath(self.db))

    @unittest.skipUnless(WINDOWS, "Windows device namespace")
    def test_a_non_drive_device_location_is_refused(self) -> None:
        code, result, err = self.run_main("\\\\.\\C45NoSuchLocalDevice\\" + str(self.rel))
        self.assertEqual(code, 2, err)
        self.assertEqual(json.loads(err.strip().splitlines()[-1])["refused"], "DATABASE_LOCATION_UNSUPPORTED")
        self.assertIsNone(result)


CONNECTORS = {"population": population_query.connect_readonly, "history": history_query.connect_readonly,
              "source_time": source_time_query.connect_readonly, "staff": staff_query.connect_readonly}


class ConsumerConnectionTests(TempRoot):
    """Each query consumer's own read-only connection reads the literal file at every supported spelling."""

    def read(self, connect, database: str) -> str:
        conn = connect(Path(database) if not database.startswith(EXT) else database)
        try:
            return conn.execute("SELECT v FROM t").fetchone()[0]
        finally:
            conn.close()

    def test_ordinary_absolute_relative_and_punctuation_locations(self) -> None:
        plain = tiny_database(os.path.join(self.root, "plain", "db.sqlite"), "plain")
        punct = tiny_database(os.path.join(self.root, PUNCTUATION, "db #.sqlite"), "punct")
        here = os.getcwd()
        try:
            os.chdir(self.root)
            for name, connect in CONNECTORS.items():
                self.assertEqual(self.read(connect, os.path.join(self.root, "plain", "db.sqlite")), "plain", name)
                self.assertEqual(self.read(connect, os.path.join(PUNCTUATION, "db #.sqlite")), "punct", name)
                self.assertEqual(self.read(connect, os.path.join("plain", "db.sqlite")), "plain", name)
        finally:
            os.chdir(here)
        self.assertTrue(os.path.exists(plain) and os.path.exists(punct))

    def test_writes_through_every_consumer_connection_are_refused(self) -> None:
        path = tiny_database(os.path.join(self.root, "w", "db.sqlite"), "unchanged")
        before = sha(path)
        for name, connect in CONNECTORS.items():
            conn = connect(Path(os.path.join(self.root, "w", "db.sqlite")))
            try:
                with self.assertRaises(sqlite3.OperationalError, msg=name):
                    conn.execute("INSERT INTO t VALUES ('x')")
                    conn.commit()
            finally:
                conn.close()
        self.assertEqual(sha(path), before)

    @unittest.skipUnless(WINDOWS, "Windows native extended-length spelling")
    def test_short_and_long_extended_locations(self) -> None:
        short = tiny_database(os.path.join(self.root, "s", "db.sqlite"), "short")
        far = tiny_database(os.path.join(long_root(self.root), "db #.sqlite"), "long")
        self.assertGreater(len(far), 300)
        for name, connect in CONNECTORS.items():
            self.assertEqual(self.read(connect, short), "short", name)
            self.assertEqual(self.read(connect, far), "long", name)


class LongRootFixtureTests(unittest.TestCase):
    """MF45A01-01: the long-location fixture from roots this host's own temporary directory never shows."""

    @unittest.skipUnless(WINDOWS, "Windows native extended-length spelling")
    def test_the_long_location_exceeds_300_characters_from_any_local_root(self) -> None:
        roots = {"minimal drive root": "C:\\",
                 "hosted runner root": "D:\\a\\_temp\\tmpabcdefgh",  # exactly 300 before MF45A01-01
                 "long temporary root": "C:\\" + "t" * 97}
        roots.update({f"root of {n} characters": "C:\\" + "b" * (n - 3) for n in range(4, 101)})
        for name, root in roots.items():
            with self.subTest(root=name):
                far = native(os.path.join(long_root(root), "db #.sqlite"))
                self.assertGreater(len(far), 300)
                self.assertLessEqual(max(len(part) for part in far[len(EXT):].split("\\")), 255)


class StaffImportApiTests(TempRoot):
    def test_the_explicit_import_api_still_creates_and_writes(self) -> None:
        path = Path(self.root) / "import" / "staff.sqlite"
        path.parent.mkdir()
        conn = staff_query.connect_for_import(path)
        try:
            conn.execute("INSERT INTO staff_role_cells (observation_id, disposition, support_column, "
                         "principal_role_blocked, source_class, pit_admitted, verified) "
                         "VALUES ('o1', 'IMPORTED', 0, 0, 'FIXTURE', 0, 0)")
            conn.commit()
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM staff_role_cells").fetchone()[0], 1)
        finally:
            conn.close()
        self.assertTrue(path.is_file())


class CareerSuccessorLocationTests(TempRoot):
    """The explicit career successor attachment and its declared Attempt 4 file, built at several locations."""

    def build(self, root: str, verbatim: bool) -> tuple[str, str]:
        """The A05 contract fixture (test_cycle37_a05_career_successor) built at ``root``: predecessor, successor.

        Every file is written through the verbatim spelling; the paths the fixture declares (raw file, Attempt 4
        file) and returns use the verbatim spelling only for a ``verbatim`` (long) root, the plain one otherwise."""
        os.makedirs(native(root), exist_ok=True)

        def spelled(name: str) -> str:
            return native(os.path.join(root, name)) if verbatim else os.path.abspath(os.path.join(root, name))
        raw = spelled("raw.json")
        with open(native(raw), "wb") as handle:
            handle.write(json.dumps({"query": {"pages": {"1": {
                "pageid": 1, "title": "Fixture Person (American football)", "pageprops": {"wikibase_item": "Q1"},
                "revisions": [{"revid": 1, "slots": {"main": {"*": REVISION_TEXT}}}]}}}}).encode("utf-8"))
        raw_sha = sha(raw)
        text_sha = hashlib.sha256(REVISION_TEXT.encode("utf-8")).hexdigest()
        base = {"pageid": 1, "revision": "1", "family": "COACHING", "interval_index": 0, "ongoing": 0,
                "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "raw_file": raw, "raw_file_sha256": raw_sha,
                "wikitext_sha256": text_sha, "assignments": "[]", "page_title": "Fixture Person (American football)",
                "person_display": "Fixture Person", "wikidata_qid": "Q1"}
        old = [{**base, "episode_id": _pid(n), "row_index": n, "start": 2009, "end": 2009} for n in IDS]
        predecessor = spelled("predecessor.sqlite")
        _table(Path(native(predecessor)), cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, old)
        a4_rows = [{**base, "episode_id": _a4(n), "row_index": n, "start": READ[n][0], "end": READ[n][1],
                    "predecessor_episode_ids": json.dumps([_pid(n)]), "lineage_state": cs.DERIVED} for n in IDS]
        a4 = spelled("a04.sqlite")
        _table(Path(native(a4)), cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, a4_rows)
        episodes = [{**base, "episode_id": _a5(n), "row_index": n, "start": READ[n][0], "end": READ[n][1],
                     "lineage_state": cs.DERIVED, "disposition": cs.CORRECTED,
                     "predecessor_episode_ids": json.dumps([_pid(n)]), "a04_episode_ids": json.dumps([_a4(n)]),
                     "a04_lineage_state": cs.A04_DERIVED, "a04_disposition": cs.CORRECTED,
                     "date_basis": "ITEM_DATE_IN_BALANCED_PARENTHESES", "uncertainty_classes": "[]"} for n in IDS]
        # as in the A05 contract fixture: the field the delivered parser did not read, added without a predecessor
        # row or an Attempt 4 row, and the first row's team/years source spans
        episodes.append({**episodes[1], "episode_id": _a5(3), "row_index": 3, "start": READ[3][0], "end": READ[3][1],
                         "predecessor_episode_ids": "[]", "lineage_state": cs.ADDED_STATES[cs.A05_FORMAT_VERSION],
                         "disposition": "ADDED", "a04_episode_ids": "[]", "a04_lineage_state": cs.A04_ADDED,
                         "a04_disposition": "ADDED_IN_A05"})
        team = "[[Iowa]] "
        years_start, team_start = REVISION_TEXT.index("2009–2010"), REVISION_TEXT.index("[[Iowa]]")
        episodes[0].update({"team_raw": team.strip(),
                            "team_char_span": json.dumps([team_start, team_start + len(team.strip())]),
                            "years_raw": "2009–2010",
                            "years_char_span": json.dumps([years_start, years_start + len("2009–2010")])})
        dispositions = [{"predecessor_episode_id": _pid(n), "disposition": cs.CORRECTED,
                         "successor_episode_ids": json.dumps([_a5(n)]), "changed_fields": "{}",
                         "predecessor_row_sha256": cs.predecessor_row_digest(old[n - 1]), "screens": "[]",
                         "reason": "fixture"} for n in IDS]
        mapping = [{"a04_episode_id": _a4(n), "disposition": cs.CORRECTED, "a05_episode_ids": json.dumps([_a5(n)]),
                    "changed_fields": "{}", "a04_row_sha256": cs.episode_row_digest(a4_rows[n - 1]), "screens": "[]",
                    "reason": "fixture"} for n in IDS]
        successor = spelled("successor.sqlite")
        _table(Path(native(successor)), cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, episodes)
        _table(Path(native(successor)), cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, dispositions)
        _table(Path(native(successor)), cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, mapping)
        conn = sqlite3.connect(native(successor))
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT, value TEXT)")
        identity = {"format_version": cs.A05_FORMAT_VERSION, "successor_version": cs.A05_SUCCESSOR_VERSION,
                    "predecessor_database_sha256": cs.sha256_file(predecessor),
                    "predecessor_table": cs.PREDECESSOR_TABLE, "predecessor_row_count": str(len(old)),
                    "a04_successor_path": a4, "a04_successor_sha256": cs.sha256_file(a4),
                    "a04_successor_row_count": str(len(a4_rows)), "default_activation": cs.NOT_ACTIVATED,
                    "acceptance_state": cs.NOT_ACCEPTED, "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0"}
        for table, columns, key in ((cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, "episode_id"),
                                    (cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id"),
                                    (cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, "a04_episode_id")):
            digest, count = cs.table_ledger(conn, table, columns, key)
            identity[f"ledger::{table}::sha256"], identity[f"ledger::{table}::rows"] = digest, str(count)
        conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
        conn.commit()
        conn.close()
        return predecessor, successor

    def served(self, root: str, *, verbatim: bool = False) -> tuple[dict, list[dict]]:
        """Attach through the staff query's own read-only connection; the rows without their location field."""
        predecessor, successor = self.build(root, verbatim)
        conn = staff_query.connect_readonly(predecessor)
        try:
            binding = cs.attach_successor(conn, successor, database=predecessor)
            rows = [{k: v for k, v in dict(r).items() if k != "raw_file"}
                    for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME} ORDER BY episode_id")]
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute(f"INSERT INTO {binding['attached_schema']}.{binding['episode_table']} (episode_id) "
                             "VALUES ('x')")
        finally:
            conn.close()
        return binding, rows

    def test_an_ordinary_location_attaches_with_its_attempt_4_file_proved(self) -> None:
        binding, rows = self.served(os.path.join(self.root, "plain"))
        self.assertEqual(binding["lineage_proved_independently_of_the_ledgers"]["a04_file_check"],
                         "A04_FILE_IDENTITY_SET_EQUAL")
        self.assertEqual(len(rows), 3)

    def test_a_punctuation_location_attaches_and_reads_its_attempt_4_file(self) -> None:
        _binding, reference = self.served(os.path.join(self.root, "plain"))
        binding, rows = self.served(os.path.join(self.root, PUNCTUATION))
        self.assertEqual(binding["lineage_proved_independently_of_the_ledgers"]["a04_file_check"],
                         "A04_FILE_IDENTITY_SET_EQUAL")
        self.assertEqual(rows, reference)

    @unittest.skipUnless(WINDOWS, "Windows native extended-length spelling")
    def test_a_long_extended_location_attaches_and_reads_its_attempt_4_file(self) -> None:
        _binding, reference = self.served(os.path.join(self.root, "plain"))
        binding, rows = self.served(long_root(self.root), verbatim=True)
        self.assertEqual(binding["lineage_proved_independently_of_the_ledgers"]["a04_file_check"],
                         "A04_FILE_IDENTITY_SET_EQUAL")
        self.assertEqual(rows, reference)


if __name__ == "__main__":
    unittest.main()
