"""BAT-717 (Cycle #45 — Attempt #1, TP45-A01-02): the shared literal-path read-only SQLite helper.

Every BAS read-only query consumer opens its database, its parents and the career successor through
:mod:`aggie_analytics.readonly_sqlite`. These tests pin what that helper guarantees on every platform -- a path is a
literal file name, never a SQLite URI; reserved characters stay in the name; the connection is read-only, never
creates a file and is confirmed to be the file the caller named -- and, on Windows, the native extended-length
spelling of a long location, the refusal of a verbatim spelling that SQLite would open as another file, and the
lexical refusal (no filesystem access at all) of network and device locations. The national population and history
query modules are standard-library only by their accepted contract, so they carry the helper's literal-location core
verbatim; these tests require the copies to stay identical and to answer exactly as the helper does.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics import readonly_sqlite as ro  # noqa: E402
from aggie_analytics.national_history import query as history_query  # noqa: E402
from aggie_analytics.national_population import query as population_query  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
#: Legal in a file name on Windows and POSIX alike; each is reserved somewhere in a URI.
PUNCTUATION = "a #%'\u00e9 &x=1 %3Fmode=rw;q+b"
CORE_BEGIN = "# ---- BEGIN BAT-717 LITERAL-LOCATION CORE"
CORE_END = "# ---- END BAT-717 LITERAL-LOCATION CORE ----"
#: Standard-library-only query modules (BAT-710, BAT-711) that carry the core instead of importing the helper.
STANDALONE = {"national_population": population_query, "national_history": history_query}


def verbatim(path: str) -> str:
    """The Windows verbatim spelling of an absolute path, never normalized (``os.path.abspath`` would strip a
    trailing dot and so name a different directory)."""
    return path if path.startswith(EXT) else EXT + path


def make_db(path: str, value: str) -> str:
    """A one-row database at ``path``: built at a staging file, then copied through the verbatim spelling on Windows
    (any length works, and SQLite itself would normalize a trailing-dot directory away when creating a file)."""
    native = verbatim(path) if WINDOWS else path
    os.makedirs(os.path.dirname(native), exist_ok=True)
    handle, stage = tempfile.mkstemp(suffix=".sqlite")
    os.close(handle)
    os.remove(stage)
    conn = sqlite3.connect(stage)
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t VALUES (?)", (value,))
    conn.commit()
    conn.close()
    shutil.copyfile(stage, native)
    os.remove(stage)
    return native


def sha(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def query_part(uri: str) -> str:
    return uri.partition("?")[2]


def core_block(path: str) -> str:
    text = Path(path).read_text(encoding="utf-8")
    start, stop = text.find(CORE_BEGIN), text.find(CORE_END)
    return text[start:stop + len(CORE_END)] if 0 <= start < stop else ""


class TempRoot(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)

    def tearDown(self) -> None:
        if WINDOWS:  # a tree beyond 260 characters is removable only through the verbatim spelling
            shutil.rmtree(verbatim(self.root))
        self._tmp.cleanup()


class LiteralUriTests(TempRoot):
    def test_reserved_characters_stay_in_the_file_name(self) -> None:
        path = os.path.join(self.root, PUNCTUATION, "db #1 %41.sqlite")
        uri = ro.readonly_uri(path)
        self.assertEqual(query_part(uri), "mode=ro")
        self.assertNotIn("#", uri)
        decoded = urllib.parse.unquote(uri[len("file:"):].partition("?")[0])
        self.assertTrue(decoded.replace("/", os.sep).endswith(os.path.join(PUNCTUATION, "db #1 %41.sqlite")))

    def test_only_the_helper_chooses_parameters(self) -> None:
        for name in ("x.sqlite?mode=rwc", "x.sqlite&immutable=0", "x.sqlite#frag", "x.sqlite?vfs=unix-none"):
            uri = ro.readonly_uri(os.path.join(self.root, name))
            self.assertEqual(query_part(uri), "mode=ro", name)
        self.assertEqual(query_part(ro.readonly_uri(os.path.join(self.root, "y.sqlite"), immutable=True)),
                         "mode=ro&immutable=1")

    def test_a_relative_path_is_made_absolute_against_the_working_directory(self) -> None:
        here = os.getcwd()
        try:
            os.chdir(self.root)
            self.assertEqual(ro.literal_path(os.path.join("sub", "db.sqlite")),
                             os.path.join(self.root, "sub", "db.sqlite"))
        finally:
            os.chdir(here)

    def test_an_empty_or_nul_path_is_refused(self) -> None:
        for value in ("", "db\x00.sqlite"):
            with self.assertRaises(ro.DatabaseLocationError) as caught:
                ro.literal_path(value)
            self.assertEqual(caught.exception.code, ro.LOCATION_UNSUPPORTED)


class ConnectionTests(TempRoot):
    def test_a_punctuation_location_is_read_as_its_literal_file(self) -> None:
        path = make_db(os.path.join(self.root, PUNCTUATION, "db #.sqlite"), "punctuation")
        conn = ro.connect_readonly(path)
        try:
            self.assertEqual(conn.execute("SELECT v FROM t").fetchone()[0], "punctuation")
        finally:
            conn.close()

    def test_writes_through_the_connection_are_refused_and_change_no_byte(self) -> None:
        path = make_db(os.path.join(self.root, "w.sqlite"), "unchanged")
        before = sha(path)
        conn = ro.connect_readonly(path)
        try:
            for statement in ("INSERT INTO t VALUES ('x')", "UPDATE t SET v = 'x'", "DELETE FROM t",
                              "CREATE TABLE u (v)", "DROP TABLE t", "PRAGMA user_version = 7"):
                with self.assertRaises(sqlite3.OperationalError, msg=statement):
                    conn.execute(statement)
                    conn.commit()
        finally:
            conn.close()
        self.assertEqual(sha(path), before)

    def test_a_missing_file_is_refused_and_never_created(self) -> None:
        for name in ("absent.sqlite", os.path.join(PUNCTUATION, "absent #.sqlite")):
            path = os.path.join(self.root, name)
            with self.assertRaises(sqlite3.OperationalError):
                ro.connect_readonly(path)
            self.assertFalse(os.path.exists(path), name)

    def test_a_uri_looking_name_is_a_literal_name_not_options(self) -> None:
        # Written as a URI it would ask for read-write-create; as a path it is only a (missing) file name.
        text = "file:" + os.path.join(self.root, "made.sqlite").replace(os.sep, "/") + "?mode=rwc"
        with self.assertRaises(sqlite3.OperationalError):
            ro.connect_readonly(text)
        self.assertFalse(os.path.exists(os.path.join(self.root, "made.sqlite")))

    def test_an_attachment_is_read_only_immutable_and_confirmed(self) -> None:
        main = make_db(os.path.join(self.root, "main.sqlite"), "main")
        other = make_db(os.path.join(self.root, PUNCTUATION, "other #.sqlite"), "other")
        before = sha(other)
        conn = ro.connect_readonly(main)
        try:
            location = ro.attach_readonly(conn, other, "succ", immutable=True)
            self.assertEqual(conn.execute("SELECT v FROM succ.t").fetchone()[0], "other")
            self.assertTrue(ro.verify_opened(conn, "succ", location))
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO succ.t VALUES ('x')")
            with self.assertRaises(ValueError):
                ro.attach_readonly(conn, other, "bad name")
        finally:
            conn.close()
        self.assertEqual(sha(other), before)

    def test_an_opened_file_that_is_not_the_named_file_is_refused(self) -> None:
        first = make_db(os.path.join(self.root, "first.sqlite"), "first")
        second = make_db(os.path.join(self.root, "second.sqlite"), "second")
        conn = ro.connect_readonly(first)
        try:
            with self.assertRaises(ro.DatabaseLocationError) as caught:
                ro.verify_opened(conn, "main", ro.literal_path(second))
            self.assertEqual(caught.exception.code, ro.LOCATION_NOT_LITERAL)
        finally:
            conn.close()

    @unittest.skipIf(WINDOWS, "a backslash, '?' and a newline are file-name characters only on POSIX")
    def test_posix_names_with_query_and_separator_characters_stay_literal(self) -> None:
        for name in ("q?mode=rw.sqlite", "back\\slash.sqlite", "line\nbreak.sqlite"):
            path = make_db(os.path.join(self.root, name), name)
            conn = ro.connect_readonly(path)
            try:
                self.assertEqual(conn.execute("SELECT v FROM t").fetchone()[0], name)
            finally:
                conn.close()


@unittest.skipUnless(WINDOWS, "Windows extended-length, UNC and device spellings")
class WindowsLocationTests(TempRoot):
    def long_root(self) -> str:
        return os.path.join(self.root, "long " + "x" * 120, "deeper # % \u00e9 ' " + "y" * 120)

    def test_a_verbatim_location_beyond_260_characters_is_read(self) -> None:
        path = make_db(os.path.join(self.long_root(), PUNCTUATION, "db.sqlite"), "long")
        self.assertGreater(len(path), 300)
        self.assertEqual(ro.literal_path(path), path)
        self.assertTrue(ro.readonly_uri(path).startswith("file:%5C%5C%3F%5C"))
        conn = ro.connect_readonly(path)
        try:
            self.assertEqual(conn.execute("SELECT v FROM t").fetchone()[0], "long")
        finally:
            conn.close()

    def test_a_short_verbatim_location_keeps_its_prefix_and_is_read(self) -> None:
        path = make_db(os.path.join(self.root, "short.sqlite"), "short")
        self.assertTrue(path.startswith(EXT))
        conn = ro.connect_readonly(path)
        try:
            self.assertEqual(conn.execute("SELECT v FROM t").fetchone()[0], "short")
        finally:
            conn.close()

    def test_an_ordinary_drive_path_keeps_its_previous_uri(self) -> None:
        path = os.path.join(self.root, "x y", "db.sqlite")
        self.assertEqual(ro.readonly_uri(path), Path(path).as_uri() + "?mode=ro")
        self.assertEqual(ro.readonly_uri(path.replace("\\", "/")), Path(path).as_uri() + "?mode=ro")

    def test_a_verbatim_spelling_sqlite_would_open_as_another_file_is_refused(self) -> None:
        literal = make_db(os.path.join(self.root, "dot.", "t.sqlite"), "literal")
        make_db(os.path.join(self.root, "dot", "t.sqlite"), "normalized twin")
        variants = [literal, EXT + self.root + "\\dot\\..\\dot\\t.sqlite", EXT + self.root + "\\.\\dot\\t.sqlite",
                    EXT + self.root + "/dot/t.sqlite"]
        for text in variants:
            with self.assertRaises(ro.DatabaseLocationError, msg=text) as caught:
                ro.connect_readonly(text)
            self.assertEqual(caught.exception.code, ro.LOCATION_NOT_LITERAL, text)

    def test_the_local_drive_device_spelling_reads_the_same_file(self) -> None:
        path = make_db(os.path.join(self.root, "dev", "db.sqlite"), "device")
        plain = path[len(EXT):]
        self.assertEqual(ro.literal_path("\\\\.\\" + plain), plain)
        self.assertEqual(ro.literal_path("\\\\.\\" + os.path.join(self.root, "dev", "x", "..", "db.sqlite")), plain)
        conn = ro.connect_readonly("\\\\.\\" + plain)
        try:
            self.assertEqual(conn.execute("SELECT v FROM t").fetchone()[0], "device")
        finally:
            conn.close()

    def test_network_and_device_spellings_are_refused_without_filesystem_access(self) -> None:
        spellings = ["\\\\server\\share\\db.sqlite", "//server/share/db.sqlite", "\\\\?\\UNC\\server\\share\\db.sqlite",
                     "\\\\.\\UNC\\server\\share\\db.sqlite", "\\\\.\\pipe\\db.sqlite", "\\\\.\\NUL",
                     "\\\\.\\PhysicalDrive0", "\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1\\db.sqlite",
                     "\\\\?\\Volume{00000000-0000-0000-0000-000000000000}\\db.sqlite", "\\/server/share/db.sqlite",
                     "//?/C:/db.sqlite"]

        def forbidden(*_args, **_kwargs):
            raise AssertionError("filesystem access before the location was refused")
        with mock.patch("os.stat", forbidden), mock.patch("os.lstat", forbidden), \
                mock.patch("sqlite3.connect", forbidden):
            for text in spellings:
                with self.assertRaises(ro.DatabaseLocationError, msg=text) as caught:
                    ro.connect_readonly(text)
                self.assertEqual(caught.exception.code, ro.LOCATION_UNSUPPORTED, text)

    def test_a_missing_verbatim_file_is_never_created(self) -> None:
        path = EXT + os.path.join(self.long_root(), "absent.sqlite")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with self.assertRaises(sqlite3.OperationalError):
            ro.connect_readonly(path)
        self.assertFalse(os.path.exists(path))


class CoreCopyTests(TempRoot):
    def test_the_standard_library_only_query_modules_carry_the_identical_core(self) -> None:
        helper = core_block(ro.__file__)
        self.assertGreater(len(helper), 2000)
        for name, module in STANDALONE.items():
            self.assertEqual(core_block(module.__file__), helper, name)

    def test_every_copy_answers_exactly_as_the_helper(self) -> None:
        spellings = [os.path.join(self.root, "db.sqlite"), os.path.join("rel", "db.sqlite"),
                     os.path.join(self.root, PUNCTUATION, "db #.sqlite"), "", "db\x00.sqlite"]
        if WINDOWS:
            plain = os.path.join(self.root, "x", "db.sqlite")
            spellings += [EXT + plain, EXT + os.path.join(self.root, "x.", "db.sqlite"),
                          EXT + os.path.join(self.root, "x", "..", "db.sqlite"), EXT + plain.replace("\\", "/"),
                          "\\\\.\\" + plain, "\\\\server\\share\\db.sqlite", "//server/share/db.sqlite",
                          "\\\\?\\UNC\\server\\share\\db.sqlite", "\\\\.\\pipe\\db.sqlite",
                          "\\\\?\\Volume{00000000-0000-0000-0000-000000000000}\\db.sqlite"]

        def outcome(literal, uri, value):
            try:
                location = literal(value)
            except ValueError as exc:
                return ("refused", getattr(exc, "code", None))
            return ("literal", location, uri(location, False), uri(location, True))
        for value in spellings:
            expected = outcome(ro.literal_path, ro._location_uri, value)
            for name, module in STANDALONE.items():
                self.assertEqual(outcome(module._literal_path, module._location_uri, value), expected, (name, value))

    def test_every_copy_refuses_through_its_own_query_error(self) -> None:
        if not WINDOWS:
            self.skipTest("the refused spelling is a Windows network share")
        for error, module in ((population_query.NationalQueryError, population_query),
                              (history_query.HistoryQueryError, history_query)):
            with self.assertRaises(error) as caught:
                module.connect_readonly(Path("\\\\server\\share\\db.sqlite"))
            self.assertEqual(caught.exception.code, ro.LOCATION_UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
