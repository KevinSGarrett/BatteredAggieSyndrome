"""Cycle #37 - Attempts #2 and #3: the BAS canonical write guard the canonical-mounted lanes run under.

A child interpreter is started with the guard installed over a temporary root, so the tests exercise the same
sitecustomize path the lanes use without touching any real data root.

Attempt #3 (MF37A02-01). The Attempt #2 manager showed two routes through the v37.2 guard with a probe of its
own (WRITE_GUARD_INDEPENDENT_PROBE.json): ``Path.write_text`` was refused, but ``sqlite3`` ``UPDATE`` +
``commit`` changed a protected database and ``os.unlink(path=...)`` deleted a protected file.
``ManagerCounterexampleTests`` replays that probe's three calls verbatim. ``RouteMatrixTests`` then covers the
general classes each counterexample belongs to -- keyword and alias entry points, SQLite, renames, traversal
and reparse aliases, child processes and native lookups -- with a declared polarity for every case, and
checks that the protected tree's names, sizes, times and bytes are unchanged after every refusal.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD_DIR = REPO / "tools" / "cycle37" / "canonical_write_guard"

CHILD = textwrap.dedent(r"""
    import json, os, sys, tempfile
    from pathlib import Path

    root = Path(sys.argv[1])
    guarded, allowed, outside = root / "guarded", root / "guarded" / "allowed", root / "outside"
    existing = guarded / "existing.json"
    results = {}

    def check(name, fn):
        try:
            fn()
            results[name] = "OK"
        except OSError as error:
            results[name] = "REFUSED" if type(error).__name__ == "CanonicalWriteRefused" else repr(error)

    def open_w(data, mode):
        with open(existing, mode, **({} if "b" in mode else {"encoding": "utf-8", "newline": ""})) as handle:
            handle.write(data)

    before = (existing.read_bytes(), existing.stat().st_mtime_ns)
    check("identical_text", lambda: existing.write_text('{"a": 1}\n', encoding="utf-8", newline=""))
    check("identical_bytes", lambda: existing.write_bytes(b'{"a": 1}\n'))
    check("identical_open_w", lambda: open_w('{"a": 1}\n', "w"))
    check("different_text", lambda: existing.write_text('{"a": 2}\n', encoding="utf-8", newline=""))
    check("different_open_wb", lambda: open_w(b"x", "wb"))
    check("append", lambda: open(existing, "a").close())
    check("new_file", lambda: (guarded / "new.json").write_bytes(b"{}"))
    check("new_dir", lambda: (guarded / "new").mkdir())
    check("existing_dir_exist_ok", lambda: guarded.mkdir(parents=True, exist_ok=True))
    check("unlink", lambda: existing.unlink())
    check("utime", lambda: os.utime(existing))
    check("temporary_file", lambda: tempfile.mkstemp(dir=guarded))
    incoming = outside / "incoming.json"
    incoming.write_bytes(b'{"a": 1}\n')
    check("replace_identical", lambda: os.replace(incoming, existing))
    incoming.write_bytes(b"different")
    check("replace_different", lambda: os.replace(incoming, existing))
    check("allowed_root", lambda: (allowed / "ok.json").write_bytes(b"{}"))
    check("outside_root", lambda: (outside / "ok.json").write_bytes(b"{}"))
    check("read", lambda: existing.read_bytes())
    sys.path.insert(0, sys.argv[2])
    from aggie_analytics import atomic_io
    check("atomic_identical", lambda: atomic_io.write_text(existing, '{"a": 1}\n', encoding="utf-8", newline=""))
    check("atomic_different", lambda: atomic_io.write_text(existing, "zzz", encoding="utf-8", newline=""))
    results["unchanged"] = (existing.read_bytes(), existing.stat().st_mtime_ns) == before
    results["guarded_entries"] = sorted(p.name for p in guarded.iterdir())
    print(json.dumps(results))
""")


def guard_env(root: Path, *, install: bool = True) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(GUARD_DIR)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in ("BAS_CANONICAL_WRITE_GUARD", "BAS_CANONICAL_WRITE_ALLOW", "BAS_CANONICAL_WRITE_GUARD_LOG"):
        env.pop(key, None)
    if install:
        env["BAS_CANONICAL_WRITE_GUARD"] = str(root / "guarded")
        env["BAS_CANONICAL_WRITE_ALLOW"] = str(root / "guarded" / "allowed")
        env["BAS_CANONICAL_WRITE_GUARD_LOG"] = str(root / "outside" / "events.jsonl")
    return env


def tree_state(path: Path) -> dict:
    """Names, sizes, modification times and SHA-256 of everything under ``path``.

    Links and junctions are recorded as such and never followed, so an alias into the tree cannot make the
    walk loop or count a file twice.
    """

    state: dict = {}
    stack = [path]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(path).as_posix()
                if entry.is_symlink() or entry.is_junction():
                    state[relative] = ["LINK", os.readlink(entry.path)]
                elif entry.is_dir(follow_symlinks=False):
                    state[relative] = ["DIR"]
                    stack.append(Path(entry.path))
                else:
                    stat = entry.stat(follow_symlinks=False)
                    state[relative] = [stat.st_size, stat.st_mtime_ns,
                                       hashlib.sha256(Path(entry.path).read_bytes()).hexdigest()]
    return dict(sorted(state.items()))


def events(root: Path) -> list[dict]:
    log = root / "outside" / "events.jsonl"
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


class CanonicalWriteGuardTests(unittest.TestCase):
    def _run(self, install: bool) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "guarded" / "allowed").mkdir(parents=True)
            (root / "outside").mkdir()
            (root / "guarded" / "existing.json").write_bytes(b'{"a": 1}\n')
            completed = subprocess.run(
                [sys.executable, "-B", "-c", CHILD, str(root), str(REPO / "src")],
                capture_output=True, text=True, env=guard_env(root, install=install), timeout=120, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            results = json.loads(completed.stdout)
            results["_events"] = [row["event"] for row in events(root)]
            return results

    def test_identical_writes_are_skipped_and_leave_bytes_and_times_alone(self) -> None:
        results = self._run(install=True)
        for name in ("identical_text", "identical_bytes", "identical_open_w", "replace_identical",
                     "atomic_identical", "existing_dir_exist_ok", "read"):
            self.assertEqual(results[name], "OK", name)
        self.assertTrue(results["unchanged"])
        self.assertIn("SKIPPED_IDENTICAL", results["_events"])

    def test_every_other_write_under_the_root_is_refused_without_hanging(self) -> None:
        results = self._run(install=True)
        for name in ("different_text", "different_open_wb", "append", "new_file", "new_dir", "unlink", "utime",
                     "temporary_file", "replace_different", "atomic_different"):
            self.assertEqual(results[name], "REFUSED", name)
        self.assertEqual(results["guarded_entries"], ["allowed", "existing.json"])
        self.assertIn("BLOCKED", results["_events"])

    def test_the_allowed_root_and_paths_outside_the_root_stay_writable(self) -> None:
        results = self._run(install=True)
        self.assertEqual(results["allowed_root"], "OK")
        self.assertEqual(results["outside_root"], "OK")

    def test_without_the_variable_nothing_is_installed(self) -> None:
        results = self._run(install=False)
        self.assertEqual(results["different_text"], "OK")
        self.assertEqual(results["_events"], [])


# --------------------------------------------------------------------------- Attempt #3 (MF37A02-01)

#: The manager's probe body, kept verbatim apart from the directory it points at: plain write, SQLite UPDATE,
#: and os.unlink(path=...). Each result is the exception class name, or ALLOWED.
MANAGER_PROBE = textwrap.dedent(r'''
    import os,json,sqlite3
    from pathlib import Path
    p=Path(os.environ["PROBE_ROOT"])
    results={}
    try:(p/"plain.txt").write_text("MODIFIED",encoding="utf-8");results["ordinary_write"]="ALLOWED"
    except OSError as e:results["ordinary_write"]=type(e).__name__
    try:
        c=sqlite3.connect(p/"test.sqlite");c.execute("update t set value='MODIFIED'");c.commit();c.close()
        results["sqlite_update"]="ALLOWED"
    except OSError as e:results["sqlite_update"]=type(e).__name__
    try:os.unlink(path=p/"keyword-delete.txt");results["keyword_unlink"]="ALLOWED"
    except OSError as e:results["keyword_unlink"]=type(e).__name__
    print(json.dumps(results))
''')


class ManagerCounterexampleTests(unittest.TestCase):
    """The three MF37A02-01 calls, replayed against a fresh owned fixture."""

    def test_the_three_demonstrated_routes_are_refused_and_bytes_survive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "simulated-canonical"
            protected.mkdir()
            (root / "outside").mkdir()
            (protected / "plain.txt").write_text("ORIGINAL", encoding="utf-8")
            (protected / "keyword-delete.txt").write_text("PRESERVE", encoding="utf-8")
            database = protected / "test.sqlite"
            connection = sqlite3.connect(database)
            connection.execute("create table t(value text)")
            connection.execute("insert into t values ('ORIGINAL')")
            connection.commit()
            connection.close()
            before = tree_state(protected)
            env = dict(os.environ)
            for key in list(env):
                if any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")):
                    env.pop(key)
            env.update(PYTHONPATH=str(GUARD_DIR), PYTHONDONTWRITEBYTECODE="1", PROBE_ROOT=str(protected),
                       BAS_CANONICAL_WRITE_GUARD=str(protected), BAS_CANONICAL_WRITE_ALLOW="",
                       BAS_CANONICAL_WRITE_GUARD_LOG=str(root / "outside" / "events.jsonl"))
            completed = subprocess.run([sys.executable, "-B", "-c", MANAGER_PROBE], env=env, cwd=root,
                                       capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            results = json.loads(completed.stdout)
            self.assertEqual(results, {"ordinary_write": "CanonicalWriteRefused",
                                       "sqlite_update": "CanonicalWriteRefused",
                                       "keyword_unlink": "CanonicalWriteRefused"})
            self.assertEqual(tree_state(protected), before)
            reader = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
            try:
                self.assertEqual(reader.execute("select value from t").fetchone()[0], "ORIGINAL")
            finally:
                reader.close()
            blocked = [row["operation"] for row in events(root) if row["event"] == "BLOCKED"]
            self.assertIn("sqlite3.connect(read-write)", blocked)
            self.assertIn("os.remove", blocked)


#: Every case the route matrix runs in one guarded child. g is the protected directory, a an allowed directory
#: inside it and o an unguarded directory beside it. N_ cases must be refused, P_ cases must keep working.
MATRIX = textwrap.dedent(r'''
    import ctypes, io, json, nt, os, shutil, sqlite3, subprocess, sys, tempfile, _io, _winapi
    from pathlib import Path
    g, a, o = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    extra = json.loads(sys.argv[4])
    log = o / "events.jsonl"
    out, routes = {}, {}

    def blocked_since(offset):
        rows = log.read_text(encoding="utf-8").splitlines()[offset:] if log.is_file() else []
        return [json.loads(row)["operation"] for row in rows if json.loads(row)["event"] == "BLOCKED"]

    def run(name, fn):
        offset = len(log.read_text(encoding="utf-8").splitlines()) if log.is_file() else 0
        try:
            fn()
            out[name] = "ALLOWED"
        except OSError as error:
            out[name] = "REFUSED" if type(error).__name__ == "CanonicalWriteRefused" else "OSERROR:" + type(error).__name__
        except sqlite3.Error as error:
            text = str(error).lower()
            out[name] = ("SQLITE_READONLY" if "readonly" in text else
                         "SQLITE_DENIED" if "not authorized" in text or "authorization denied" in text else
                         "SQLITE:" + str(error)[:80])
        except subprocess.CalledProcessError as error:
            out[name] = f"CHILD_EXIT:{error.returncode}"
        except Exception as error:  # noqa: BLE001 - the class is the datum
            out[name] = "EXCEPTION:" + type(error).__name__ + ":" + str(error)[:80]
        routes[name] = blocked_since(offset)

    def quoted(path):
        return "'" + str(path).replace("'", "''") + "'"

    def sql_update(target, uri=False):
        c = sqlite3.connect(target, uri=uri)
        try:
            c.execute("update t set v='X'"); c.commit()
        finally:
            c.close()

    def sql_read(target):
        c = sqlite3.connect(target, uri=True)
        try:
            v = c.execute("select v from t").fetchone()[0]
        finally:
            c.close()
        assert v == "ORIGINAL", v

    def attach(statement, *parameters, authorizer=None):
        c = sqlite3.connect(":memory:")
        try:
            if authorizer is not None:
                c.set_authorizer(authorizer)
            c.execute(statement, parameters)
            c.execute("update x.t set v='X'"); c.commit()
        finally:
            c.close()

    def vacuum_into():
        c = sqlite3.connect((g / "db.sqlite").as_uri() + "?mode=ro", uri=True)
        try:
            c.execute("vacuum into " + quoted(g / "copy.sqlite"))
        finally:
            c.close()

    def load_extension():
        c = sqlite3.connect(":memory:")
        try:
            c.enable_load_extension(True)
        finally:
            c.close()

    def raw_connection():
        import _sqlite3
        _sqlite3.connect(":memory:").close()

    def attach_outside():
        c = sqlite3.connect(":memory:")
        try:
            c.execute("attach database " + quoted(o / "run.sqlite") + " as r")
        finally:
            c.close()

    def allowed_sqlite_rw():
        c = sqlite3.connect(a / "run.sqlite")
        try:
            c.execute("create table if not exists r(x)"); c.commit()
        finally:
            c.close()

    def chdir_write():
        os.chdir(g)
        try:
            Path("f.txt").write_text("X")
        finally:
            os.chdir(o)

    def child(args, env=None, **kw):
        subprocess.run(args, env=env, check=True, capture_output=True, timeout=60, **kw)

    stripped = {"SYSTEMROOT": os.environ["SYSTEMROOT"], "PATH": os.environ.get("PATH", "")}
    write_code = "import sys; from pathlib import Path; Path(sys.argv[1]).write_text('X')"
    delete_code = "import os, sys; os.remove(sys.argv[1])"

    cases = {
        # --- keyword and alias entry points (the os.unlink(path=...) class)
        "N_os_unlink_keyword": lambda: os.unlink(path=g / "f.txt"),
        "N_os_remove_keyword": lambda: os.remove(path=str(g / "f.txt")),
        "N_nt_unlink": lambda: nt.unlink(str(g / "f.txt")),
        "N_nt_remove_bytes": lambda: nt.remove(os.fsencode(str(g / "f.txt"))),
        "N_os_rmdir_keyword": lambda: os.rmdir(path=g / "empty"),
        "N_path_unlink": lambda: (g / "f.txt").unlink(),
        "N_fileio_write": lambda: _io.FileIO(str(g / "f.txt"), "w").close(),
        "N_io_open_keyword_append": lambda: io.open(file=g / "f.txt", mode="a").close(),
        "N_os_open_keyword_trunc": lambda: os.close(os.open(path=g / "f.txt", flags=os.O_WRONLY | os.O_TRUNC)),
        "N_os_truncate_keyword": lambda: os.truncate(path=g / "f.txt", length=0),
        "N_os_utime_keyword": lambda: os.utime(path=g / "f.txt"),
        "N_os_chmod_keyword": lambda: os.chmod(path=g / "f.txt", mode=0o444),
        "N_path_touch_existing": lambda: (g / "f.txt").touch(),
        "N_path_touch_new": lambda: (g / "touched.txt").touch(),
        "N_makedirs_new": lambda: os.makedirs(g / "x" / "y"),
        "N_mkdtemp": lambda: tempfile.mkdtemp(dir=g),
        "N_named_temporary_file": lambda: tempfile.NamedTemporaryFile(dir=g).close(),
        "N_winapi_createfile_write": lambda: _winapi.CloseHandle(
            _winapi.CreateFile(str(g / "f.txt"), 0x40000000, 0, 0, 3, 0x80, 0)),
        # --- rename, move, copy and link (as source or destination)
        "N_rename_keyword_out": lambda: os.rename(src=g / "f.txt", dst=o / "stolen.txt"),
        "N_replace_keyword_in": lambda: ((o / "in.txt").write_text("IN"), os.replace(src=o / "in.txt", dst=g / "f.txt")),
        "N_path_rename": lambda: (g / "f.txt").rename(o / "stolen2.txt"),
        "N_shutil_move_out": lambda: shutil.move(str(g / "f.txt"), str(o / "moved.txt")),
        "N_shutil_copyfile_in": lambda: ((o / "c.txt").write_text("C"), shutil.copyfile(o / "c.txt", g / "f.txt")),
        "N_shutil_copy2_new": lambda: ((o / "c2.txt").write_text("C"), shutil.copy2(o / "c2.txt", g / "copied.txt")),
        "N_shutil_rmtree_protected": lambda: shutil.rmtree(g / "sub"),
        "N_hard_link_to_protected": lambda: os.link(g / "f.txt", o / "alias.txt"),
        "N_hard_link_into_root": lambda: os.link(o / "outside.txt", g / "linked.txt"),
        "N_create_junction_in_root": lambda: _winapi.CreateJunction(str(o), str(g / "junction")),
        # --- SQLite (the UPDATE + commit class)
        "N_sqlite_rw_plain_path": lambda: sql_update(g / "db.sqlite"),
        "N_sqlite_rw_uri": lambda: sql_update((g / "db.sqlite").as_uri() + "?mode=rw", uri=True),
        "N_sqlite_update_through_readonly": lambda: sql_update((g / "db.sqlite").as_uri() + "?mode=ro", uri=True),
        "N_sqlite_attach_literal": lambda: attach("attach database " + quoted(g / "db.sqlite") + " as x"),
        "N_sqlite_attach_parameter": lambda: attach("attach database ? as x", str(g / "db.sqlite")),
        "N_sqlite_attach_after_user_authorizer": lambda: attach(
            "attach database " + quoted(g / "db.sqlite") + " as x", authorizer=lambda *args: 0),
        "N_sqlite_vacuum_into": vacuum_into,
        "N_sqlite_load_extension": load_extension,
        "N_sqlite_custom_factory": lambda: sqlite3.connect(
            ":memory:", factory=type("F", (sqlite3.Connection,), {})).close(),
        "N_sqlite_raw_constructor": raw_connection,
        # --- traversal and reparse aliases of a protected path
        "N_traversal_from_allowed": lambda: (a / ".." / "f.txt").write_text("X"),
        "N_case_variant": lambda: Path(str(g / "f.txt").upper()).write_text("X"),
        "N_extended_prefix": lambda: Path("\\\\?\\" + str(g / "f.txt")).write_text("X"),
        "N_trailing_dot_component": lambda: os.remove(str(g) + "." + os.sep + "f.txt"),
        "N_alternate_data_stream": lambda: Path(str(g / "f.txt") + ":ads").write_text("X"),
        "N_junction_outside_into_root": lambda: (o / "to_guarded" / "f.txt").write_text("X"),
        "N_junction_in_allowed_into_root": lambda: (a / "to_guarded" / "f.txt").write_text("X"),
        "N_preexisting_hard_link_write": lambda: (o / "hard_alias.txt").write_text("X"),
        "N_relative_after_chdir": chdir_write,
        "N_remove_allowed_root_itself": lambda: os.rmdir(a),
        # --- child processes and native lookups
        "N_python_child_stripped_env_writes": lambda: child(
            [sys.executable, "-B", "-c", write_code, str(g / "f.txt")], env=dict(stripped)),
        "N_python_child_stripped_env_deletes": lambda: child(
            [sys.executable, "-B", "-c", delete_code, str(g / "f.txt")], env=dict(stripped)),
        "N_python_child_isolated": lambda: child([sys.executable, "-I", "-c", "pass"]),
        "N_python_child_no_site_clustered": lambda: child([sys.executable, "-BS", "-c", "pass"]),
        "N_python_child_ignore_env_after_x": lambda: child([sys.executable, "-X", "utf8", "-E", "-c", "pass"]),
        "N_python_child_widening_allow": lambda: child(
            [sys.executable, "-c", "pass"], env={**os.environ, "BAS_CANONICAL_WRITE_ALLOW": str(g)}),
        "N_cmd_delete": lambda: child(["cmd", "/c", "del", str(g / "f.txt")]),
        "N_powershell_delete": lambda: child(["powershell", "-NoProfile", "-Command", "Remove-Item", str(g / "f.txt")]),
        "N_shell_true": lambda: child("del " + str(g / "f.txt"), shell=True),
        "N_os_system": lambda: os.system("echo guarded"),
        "N_git_into_root": lambda: child(["git", "-C", str(g), "init"]),
        "N_git_output_into_root": lambda: child(["git", "--no-pager", "log", "--output=" + str(g / "log.txt")]),
        "N_ctypes_deletefile_lookup": lambda: ctypes.windll.kernel32.DeleteFileW,
        "N_ctypes_createfile_lookup": lambda: ctypes.WinDLL("kernel32")["CreateFileW"],
        "N_ctypes_getprocaddress_lookup": lambda: ctypes.windll.kernel32.GetProcAddress,
        # --- positive controls: reads, run-owned writes and identical-bytes skips keep working
        "P_read_bytes": lambda: (g / "f.txt").read_bytes(),
        "P_list_directory": lambda: os.listdir(g),
        "P_sqlite_read_only_uri": lambda: sql_read((g / "db.sqlite").as_uri() + "?mode=ro"),
        "P_sqlite_immutable_uri": lambda: sql_read((g / "db.sqlite").as_uri() + "?immutable=1"),
        "P_sqlite_memory_attach_outside": attach_outside,
        "P_allowed_write_rename_delete": lambda: ((a / "w.txt").write_text("W"), os.replace(a / "w.txt", a / "w2.txt"),
                                                  os.remove(a / "w2.txt")),
        "P_allowed_sqlite_rw": allowed_sqlite_rw,
        "P_outside_write": lambda: (o / "ok.txt").write_text("OK"),
        "P_identical_write_skipped": lambda: (g / "f.txt").write_text("PROTECTED"),
        "P_mkdir_exist_ok_existing": lambda: g.mkdir(parents=True, exist_ok=True),
        "P_python_child_inherits_and_writes_outside": lambda: child(
            [sys.executable, "-B", "-c", write_code, str(o / "child.txt")]),
        "P_python_child_stripped_env_writes_outside": lambda: child(
            [sys.executable, "-B", "-c", write_code, str(o / "child2.txt")], env=dict(stripped)),
        "P_git_outside": lambda: child(["git", "--version"]),
        "P_tempfile_outside": lambda: os.close(tempfile.mkstemp(dir=o)[0]),
    }
    if extra.get("short"):
        cases["N_short_8dot3_alias"] = lambda: Path(extra["short"]).write_text("X")
    if extra.get("loopback"):
        cases["N_loopback_admin_share"] = lambda: Path(extra["loopback"]).write_text("X")
    for name, fn in cases.items():
        run(name, fn)
    print(json.dumps({"outcomes": out, "routes": routes}))
''')

#: The guard route each negative case must be refused by: the operation recorded in the guard log while the
#: case ran. A refusal by an unrelated rule would not show that the case's own class is closed.
EXPECTED_ROUTES = {
    "N_os_unlink_keyword": "os.remove", "N_os_remove_keyword": "os.remove", "N_nt_unlink": "os.remove",
    "N_nt_remove_bytes": "os.remove", "N_os_rmdir_keyword": "os.rmdir", "N_path_unlink": "os.remove",
    "N_fileio_write": "open(write)", "N_io_open_keyword_append": "open(mode='a')",
    "N_os_open_keyword_trunc": "open(write)", "N_os_truncate_keyword": "os.truncate",
    "N_os_utime_keyword": "os.utime", "N_os_chmod_keyword": "os.chmod", "N_path_touch_existing": "open(write)",
    "N_path_touch_new": "open(write)", "N_makedirs_new": "os.mkdir", "N_mkdtemp": "os.mkdir",
    "N_named_temporary_file": "open(mode='w+b')", "N_winapi_createfile_write": "_winapi.CreateFile",
    "N_rename_keyword_out": "os.rename(source)", "N_replace_keyword_in": "os.rename(destination)",
    "N_path_rename": "os.rename(source)", "N_shutil_move_out": "shutil.move(source)",
    "N_shutil_copyfile_in": "shutil.copyfile", "N_shutil_copy2_new": "_winapi.CopyFile2",
    "N_shutil_rmtree_protected": "shutil.rmtree", "N_hard_link_to_protected": "os.link(protected target)",
    "N_hard_link_into_root": "os.link(new name)", "N_create_junction_in_root": "_winapi.CreateJunction",
    "N_sqlite_rw_plain_path": "sqlite3.connect(read-write)", "N_sqlite_rw_uri": "sqlite3.connect(read-write)",
    "N_sqlite_attach_literal": "sqlite ATTACH/VACUUM INTO", "N_sqlite_attach_parameter": "sqlite ATTACH",
    "N_sqlite_attach_after_user_authorizer": "sqlite ATTACH/VACUUM INTO",
    "N_sqlite_vacuum_into": "sqlite ATTACH/VACUUM INTO",
    "N_sqlite_load_extension": "sqlite3.enable_load_extension",
    "N_sqlite_custom_factory": "sqlite3.connect(factory)", "N_sqlite_raw_constructor": "sqlite3.connect/handle",
    "N_traversal_from_allowed": "open(mode='w')", "N_case_variant": "open(mode='w')",
    "N_extended_prefix": "open(mode='w')", "N_trailing_dot_component": "os.remove",
    "N_alternate_data_stream": "open(mode='w')", "N_junction_outside_into_root": "open(mode='w')",
    "N_junction_in_allowed_into_root": "open(mode='w')", "N_preexisting_hard_link_write": "open(write)",
    "N_relative_after_chdir": "open(mode='w')", "N_remove_allowed_root_itself": "os.rmdir",
    "N_python_child_stripped_env_writes": "open(mode='w')", "N_python_child_stripped_env_deletes": "os.remove",
    "N_python_child_isolated": "subprocess.Popen", "N_python_child_no_site_clustered": "subprocess.Popen",
    "N_python_child_ignore_env_after_x": "subprocess.Popen", "N_python_child_widening_allow": "subprocess.Popen",
    "N_cmd_delete": "subprocess.Popen", "N_powershell_delete": "subprocess.Popen", "N_shell_true": "subprocess.Popen",
    "N_os_system": "os.system", "N_git_into_root": "subprocess.Popen", "N_git_output_into_root": "subprocess.Popen",
    "N_ctypes_deletefile_lookup": "ctypes.dlsym", "N_ctypes_createfile_lookup": "ctypes.dlsym",
    "N_ctypes_getprocaddress_lookup": "ctypes.dlsym", "N_short_8dot3_alias": "open(mode='w')",
    "N_loopback_admin_share": "open(mode='w')",
}
#: The one negative whose refusal is SQLite's own: a read-only connection is admitted and SQLite refuses the
#: UPDATE itself, so no guard route is logged for it.
NO_GUARD_ROUTE = {"N_sqlite_update_through_readonly"}

#: Negative cases that end in a native refusal rather than CanonicalWriteRefused, and why that is correct.
NATIVE_REFUSALS = {
    # A read-only connection is allowed; SQLite itself refuses its UPDATE, so the bytes cannot change.
    "N_sqlite_update_through_readonly": "SQLITE_READONLY",
    # The authorizer denies the attach inside SQLite, which reports it as a sqlite3.DatabaseError.
    "N_sqlite_attach_literal": "SQLITE_DENIED",
    "N_sqlite_attach_parameter": "SQLITE_DENIED",
    "N_sqlite_attach_after_user_authorizer": "SQLITE_DENIED",
    "N_sqlite_vacuum_into": "SQLITE_DENIED",
    # These children were launched with the guard propagated into them; each refused inside itself (exit 1).
    "N_python_child_stripped_env_writes": "CHILD_EXIT:1",
    "N_python_child_stripped_env_deletes": "CHILD_EXIT:1",
}


def _short_path(path: Path) -> str | None:
    import ctypes

    buffer = ctypes.create_unicode_buffer(1024)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, 1024)
    value = buffer.value if length else None
    return value if value and os.path.normcase(value) != os.path.normcase(str(path)) else None


@unittest.skipUnless(os.name == "nt", "the reparse, short-name and native cases are Windows routes")
class RouteMatrixTests(unittest.TestCase):
    """Every route class, each case with a declared polarity; bytes unchanged after every refusal."""

    @classmethod
    def setUpClass(cls) -> None:
        import _winapi

        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name) / "route_matrix_long_directory_name"
        g, a, o = root / "guarded", root / "guarded" / "allowed", root / "outside"
        (g / "sub").mkdir(parents=True)
        (g / "empty").mkdir()
        a.mkdir()
        o.mkdir()
        (g / "f.txt").write_text("PROTECTED")
        (g / "sub" / "s.txt").write_text("SUB")
        (o / "outside.txt").write_text("OUTSIDE")
        connection = sqlite3.connect(g / "db.sqlite")
        connection.execute("create table t(v text)")
        connection.execute("insert into t values ('ORIGINAL')")
        connection.commit()
        connection.close()
        # Aliases made before the guard exists, as an attacker's earlier step would be.
        _winapi.CreateJunction(str(g), str(o / "to_guarded"))
        _winapi.CreateJunction(str(g), str(a / "to_guarded"))
        os.link(g / "f.txt", o / "hard_alias.txt")
        extra = {}
        short = _short_path(g)
        if short:
            extra["short"] = str(Path(short) / "f.txt")
        drive, rest = os.path.splitdrive(str(g / "f.txt"))
        loopback = f"\\\\localhost\\{drive[0]}$" + rest
        if os.path.exists(loopback):
            extra["loopback"] = loopback
        cls.extra = extra
        cls.before = tree_state(g)
        env = dict(os.environ)
        env.update(PYTHONPATH=str(GUARD_DIR), PYTHONDONTWRITEBYTECODE="1", BAS_CANONICAL_WRITE_GUARD=str(g),
                   BAS_CANONICAL_WRITE_ALLOW=str(a), BAS_CANONICAL_WRITE_GUARD_LOG=str(o / "events.jsonl"))
        completed = subprocess.run([sys.executable, "-B", "-c", MATRIX, str(g), str(a), str(o), json.dumps(extra)],
                                   env=env, cwd=o, capture_output=True, text=True, timeout=600, check=False)
        cls.completed = completed
        payload = json.loads(completed.stdout) if completed.returncode == 0 and completed.stdout.strip() else {}
        cls.results = payload.get("outcomes", {})
        cls.routes = payload.get("routes", {})
        cls.after = tree_state(g)
        cls.g, cls.a, cls.o = g, a, o

    @classmethod
    def tearDownClass(cls) -> None:
        for junction in (cls.o / "to_guarded", cls.a / "to_guarded"):
            try:
                os.rmdir(junction)
            except OSError:
                pass
        cls._tmp.cleanup()

    def test_the_matrix_child_completed(self) -> None:
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr[-4000:])
        self.assertGreater(len(self.results), 60)

    def test_every_negative_case_is_refused_for_its_intended_cause(self) -> None:
        negatives = {name: outcome for name, outcome in self.results.items() if name.startswith("N_")}
        self.assertGreater(len(negatives), 50)
        for name, outcome in sorted(negatives.items()):
            with self.subTest(case=name):
                self.assertEqual(outcome, NATIVE_REFUSALS.get(name, "REFUSED"), name)

    def test_every_negative_case_reached_its_own_guard_route(self) -> None:
        self.assertEqual(set(EXPECTED_ROUTES) | NO_GUARD_ROUTE,
                         {name for name in self.results if name.startswith("N_")} | {"N_short_8dot3_alias",
                                                                                     "N_loopback_admin_share"})
        for name, route in sorted(EXPECTED_ROUTES.items()):
            if name not in self.results:
                continue
            with self.subTest(case=name):
                self.assertIn(route, self.routes.get(name, []), name)
        for name in NO_GUARD_ROUTE:
            self.assertEqual(self.routes.get(name), [], name)

    def test_every_positive_case_still_works(self) -> None:
        positives = {name: outcome for name, outcome in self.results.items() if name.startswith("P_")}
        self.assertGreater(len(positives), 10)
        for name, outcome in sorted(positives.items()):
            with self.subTest(case=name):
                self.assertEqual(outcome, "ALLOWED", name)

    def test_the_protected_tree_is_byte_for_byte_unchanged(self) -> None:
        # The allowed root's contents may change (positive cases write there); everything else may not.
        protected_before = {k: v for k, v in self.before.items() if not k.startswith("allowed/")}
        protected_after = {k: v for k, v in self.after.items() if not k.startswith("allowed/")}
        self.assertEqual(protected_after, protected_before)
        self.assertTrue(self.a.is_dir(), "the allowed root itself must survive an attempted removal")

    def test_the_alias_cases_were_actually_exercised_here(self) -> None:
        # A route this machine cannot express is reported by its absence, not silently counted as covered.
        for name in ("N_junction_outside_into_root", "N_junction_in_allowed_into_root",
                     "N_preexisting_hard_link_write", "N_extended_prefix", "N_trailing_dot_component"):
            self.assertIn(name, self.results)
        if "short" in self.extra:
            self.assertEqual(self.results.get("N_short_8dot3_alias"), "REFUSED")
        if "loopback" in self.extra:
            self.assertEqual(self.results.get("N_loopback_admin_share"), "REFUSED")

    def test_refusals_are_logged_with_their_route(self) -> None:
        rows = [json.loads(line) for line in (self.o / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        operations = {row["operation"] for row in rows if row["event"] == "BLOCKED"}
        for expected in ("os.remove", "open(write)", "os.rename(source)", "sqlite3.connect(read-write)",
                         "subprocess.Popen", "os.system", "ctypes.dlsym"):
            self.assertIn(expected, operations)
        self.assertIn("CHILD_ADMITTED", {row["event"] for row in rows})


#: Every non-loopback target below is refused inside the audit hook, before any lookup or packet is made, so
#: the test itself never touches the network. 192.0.2.1 is TEST-NET-1 and example.invalid is a reserved name.
NETWORK_CHILD = textwrap.dedent(r'''
    import json, os, socket, subprocess, sys
    results = {}

    def check(name, fn):
        try:
            fn()
            results[name] = "OK"
        except OSError as error:
            results[name] = type(error).__name__

    def connect(host):
        handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        handle.settimeout(0.5)
        try:
            handle.connect((host, 9))
        finally:
            handle.close()

    def sendto(host):
        handle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            handle.sendto(b"x", (host, 9))
        finally:
            handle.close()

    check("lookup_reserved_name", lambda: socket.getaddrinfo("example.invalid", 443))
    check("gethostbyname_reserved_name", lambda: socket.gethostbyname("example.invalid"))
    check("lookup_localhost", lambda: socket.getaddrinfo("localhost", 80))
    check("connect_test_net", lambda: connect("192.0.2.1"))
    check("connect_loopback", lambda: connect("127.0.0.1"))
    check("sendto_test_net", lambda: sendto("192.0.2.1"))
    # A caller-built environment that drops the setting must not take the grandchild online.
    env = {key: value for key, value in os.environ.items() if key != "BAS_NETWORK_GUARD"}
    probe = ("import socket\n"
             "try:\n"
             "    socket.getaddrinfo('example.invalid', 443)\n"
             "    print('OK')\n"
             "except OSError as error:\n"
             "    print(type(error).__name__)\n")
    child = subprocess.run([sys.executable, "-B", "-c", probe], env=env, capture_output=True, text=True, timeout=60)
    results["grandchild_with_the_setting_dropped"] = child.stdout.strip() or child.stderr.strip()[-200:]
    print(json.dumps(results))
''')


class NetworkGuardTests(unittest.TestCase):
    """Attempt #3 (R37A03-07): offline lanes refuse non-loopback network access through their children."""

    def test_non_loopback_access_is_refused_and_loopback_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "guarded" / "allowed").mkdir(parents=True)
            (root / "outside").mkdir()
            env = guard_env(root)
            env["BAS_NETWORK_GUARD"] = "DENY_NON_LOOPBACK"
            completed = subprocess.run([sys.executable, "-B", "-c", NETWORK_CHILD], env=env, cwd=root,
                                       capture_output=True, text=True, timeout=120)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            results = json.loads(completed.stdout.strip().splitlines()[-1])
            for name in ("lookup_reserved_name", "gethostbyname_reserved_name", "connect_test_net",
                         "sendto_test_net", "grandchild_with_the_setting_dropped"):
                with self.subTest(case=name):
                    self.assertEqual(results[name], "NetworkRefused")
            self.assertEqual(results["lookup_localhost"], "OK")
            self.assertNotEqual(results["connect_loopback"], "NetworkRefused")
            blocked = {row["operation"] for row in events(root) if row["event"] == "BLOCKED"}
            self.assertTrue({"socket.getaddrinfo", "socket.connect", "socket.sendto"} <= blocked)

    def test_the_setting_is_inert_without_the_guard(self) -> None:
        """``BAS_NETWORK_GUARD`` alone installs nothing: the network refusal is part of the guard.

        Inside a guarded process -- the canonical-mounted lanes run the whole suite under one -- no Python child
        can start without the guard, because the guard is propagated into every child together with the network
        setting. There the complementary property is asserted: the child re-installs the guard and keeps the
        setting. WRITE_PROTECTION runs this suite unguarded, where inertness itself is asserted.
        """
        outer = sys.modules.get("bas_canonical_write_guard")
        outer_installed = bool(outer is not None and outer._STATE.get("installed"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outside").mkdir()
            env = guard_env(root, install=False)
            env["BAS_NETWORK_GUARD"] = "DENY_NON_LOOPBACK"
            probe = ("import os, bas_canonical_write_guard as g\n"
                     "print(g._STATE['installed'], os.environ.get('BAS_NETWORK_GUARD'))\n")
            completed = subprocess.run([sys.executable, "-B", "-c", probe], env=env, cwd=root,
                                       capture_output=True, text=True, timeout=60)
            observed = tuple(completed.stdout.split())
            expected = ("True" if outer_installed else "False", "DENY_NON_LOOPBACK")
            self.assertEqual(observed, expected, completed.stderr)


class GuardedLaneSelection(unittest.TestCase):
    def test_exactly_the_canonical_mounted_lanes_are_guarded(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("rework_lanes_guard_selection", REPO / "tools" / "cycle37" / "rework_lanes.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.GUARDED_LANES,
                         frozenset({"strict-mounted", "full-baseline-mounted", "full-final-mounted", "c36-15"}))
        self.assertEqual(module.GUARD_DIR, GUARD_DIR)


if __name__ == "__main__":
    unittest.main()
