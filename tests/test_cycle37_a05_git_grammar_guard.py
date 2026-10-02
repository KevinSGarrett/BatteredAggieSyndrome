"""Cycle #37 — Attempt #5 — MF37A04-01: a guarded process's git children parse under a typed grammar.

The Attempt #4 manager ran ``git config -f../p/x fixture.value CHANGED`` in a repository inside the declared Git
scratch root, whose ``p`` directory was a protected root, and the v37.4 guard admitted it: ``config`` was a
scratch write, and its file option -- attached to the flag -- was never read as a path. The fixture changed.

v37.5 admits a git child only when its whole command line parses under the typed grammar of an admitted
subcommand, and the four writing forms only inside an explicitly declared scratch root (no TEMP default), by
every spelling, with plain repository metadata. This suite:

* rebuilds the manager's exact layout (scratch ``F/temp``, protected ``F/temp/p``, repository ``F/temp/g``) and
  every fixture repository *before* any guard is installed;
* first shows each new vector is live without a guard (``LiveVectorControls``) -- the attached file option, its
  separated and abbreviated spellings, a junction in the repository metadata and a hard link there;
* then runs one guarded child over positives (identity and diff reads, a scratch repository, guarded Python
  children, an owned write, a protected read-only SQLite read) and negatives (the manager's alias and file
  options, option abbreviations, configuration/environment/helper indirection, path aliases and reparse points,
  native children, the network, and a guarded process with no declared scratch root), each with the refusal
  reason it must reach, and compares the protected tree byte for byte afterwards.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD_DIR = REPO / "tools" / "cycle37" / "canonical_write_guard"


def _outer_guard_installed() -> bool:
    outer = sys.modules.get("bas_canonical_write_guard")
    return bool(outer is not None and outer._STATE.get("installed"))


def _git(*args: str, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120, check=False)


def _repo(path: Path, commits: int = 1) -> Path:
    path.mkdir(parents=True)
    for args in (("init", "-q"), ("config", "user.name", "fixture"), ("config", "user.email", "fixture@bas.invalid")):
        completed = _git(*args, cwd=path)
        assert completed.returncode == 0, completed.stderr
    for number in range(commits):
        (path / "f.txt").write_text(f"{number}\n", encoding="utf-8", newline="\n")
        assert _git("add", "-A", cwd=path).returncode == 0
        completed = _git("commit", "-q", "-m", f"c{number}", cwd=path)
        assert completed.returncode == 0, completed.stderr
    return path


def _junction(target: Path, link: Path) -> None:
    import _winapi  # noqa: PLC0415

    _winapi.CreateJunction(str(target), str(link))


def _short_path(path: Path) -> str | None:
    buffer = ctypes.create_unicode_buffer(1024)
    if ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, 1024) and buffer.value.lower() != str(path).lower():
        return buffer.value
    return None


def tree_state(path: Path) -> dict:
    state: dict = {}
    for current, directories, files in os.walk(path):
        for name in sorted(files):
            file = Path(current) / name
            stat = file.stat()
            state[file.relative_to(path).as_posix()] = [stat.st_size, stat.st_mtime_ns,
                                                        hashlib.sha256(file.read_bytes()).hexdigest()]
        for name in directories:
            state[(Path(current) / name).relative_to(path).as_posix() + "/"] = ["DIR"]
    return dict(sorted(state.items()))


def build_layout(root: Path) -> dict:
    """The manager's layout plus this suite's alias and reparse fixtures. No guard is installed here."""

    scratch = root / "temp"
    protected = scratch / "p"
    protected.mkdir(parents=True)
    target = protected / "x"
    target.write_text("[fixture]\n\tvalue = ORIGINAL\n", encoding="utf-8", newline="\n")
    (protected / "fake.git").mkdir()
    (protected / "fake.git" / "config").write_text("[core]\n\tbare = false\n", encoding="utf-8", newline="\n")
    (protected / "objects").mkdir()
    (protected / "logtarget").write_text("PROTECTED-LOG-BYTES\n", encoding="utf-8", newline="\n")
    connection = sqlite3.connect(protected / "db.sqlite")
    connection.execute("create table t(v text)")
    connection.execute("insert into t values ('ORIGINAL')")
    connection.commit()
    connection.close()
    layout = {"root": str(root), "scratch": str(scratch), "protected": str(protected), "target": str(target)}
    layout["repo"] = str(_repo(scratch / "g"))                    # the manager's repository inside the scratch root
    layout["clean"] = str(_repo(root / "outside" / "clean", 2))    # a read-only subject outside the scratch root
    (root / "outside" / "allowed").mkdir()
    layout["allowed"] = str(root / "outside" / "allowed")
    _junction(protected, scratch / "j")                            # a junction inside the scratch root to p
    layout["junction"] = str(scratch / "j")
    gitfile = scratch / "gf"                                       # a work tree whose .git file names p/fake.git
    gitfile.mkdir()
    (gitfile / ".git").write_text(f"gitdir: {(protected / 'fake.git').as_posix()}\n", encoding="utf-8")
    layout["gitfile_repo"] = str(gitfile)
    # A repository with no commit yet (its objects directory holds only empty directories) whose objects directory
    # is replaced by a junction to p: the first commit would write its objects into the protected root.
    objects = _repo(scratch / "oj", commits=0)
    shutil.rmtree(objects / ".git" / "objects")
    for part in ("info", "pack"):
        (protected / "objects" / "linked" / part).mkdir(parents=True)
    _junction(protected / "objects" / "linked", objects / ".git" / "objects")
    layout["objects_junction_repo"] = str(objects)
    layout["junctions"] = [str(scratch / "j"), str(objects / ".git" / "objects")]
    linked = _repo(scratch / "hl")                                 # a repository whose reflog is a hard link into p
    head_log = linked / ".git" / "logs" / "HEAD"
    head_log.unlink()
    os.link(protected / "logtarget", head_log)
    layout["hardlink_repo"] = str(linked)
    layout["short_protected"] = _short_path(protected)
    layout["global_include"] = str(root / "outside" / "global_include.cfg")
    Path(layout["global_include"]).write_text(f"[include]\n\tpath = {target.as_posix()}\n", encoding="utf-8")
    return layout


@unittest.skipUnless(os.name == "nt", "live vectors require Windows junctions and executable discovery")
class LiveVectorControls(unittest.TestCase):
    """Each new vector changes bytes when nothing guards it (outside a guarded lane)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name) / "live"
        cls.scratch = cls.root / "temp"
        cls.outside = cls.root / "elsewhere"
        cls.outside.mkdir(parents=True)
        cls.repo = _repo(cls.scratch / "g")
        cls.objects_target = cls.outside / "objects_target"
        cls.linked_target = cls.outside / "linked_target"
        cls.linked_target.write_text("LIVE-LOG\n", encoding="utf-8", newline="\n")
        objects = _repo(cls.scratch / "oj", commits=0)
        shutil.rmtree(objects / ".git" / "objects")
        for part in ("info", "pack"):
            (cls.objects_target / part).mkdir(parents=True)
        _junction(cls.objects_target, objects / ".git" / "objects")
        cls.objects_repo = objects
        linked = _repo(cls.scratch / "hl")
        (linked / ".git" / "logs" / "HEAD").unlink()
        os.link(cls.linked_target, linked / ".git" / "logs" / "HEAD")
        cls.linked_repo = linked

    @classmethod
    def tearDownClass(cls) -> None:
        os.rmdir(cls.objects_repo / ".git" / "objects")  # removes this suite's own junction, never its target
        cls._tmp.cleanup()

    def _attempt(self, argv: list[str], cwd: Path) -> str:
        try:
            completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
            return f"EXIT:{completed.returncode}"
        except OSError as error:
            return "REFUSED" if type(error).__name__ == "CanonicalWriteRefused" else repr(error)

    def test_file_option_spellings_write_outside_the_repository(self) -> None:
        outer = _outer_guard_installed()
        for number, argv in enumerate((["git", "config", "-f../../elsewhere/cfg0", "k.v", "LIVE"],
                                       ["git", "config", "-f", "../../elsewhere/cfg1", "k.v", "LIVE"],
                                       ["git", "config", "--file=../../elsewhere/cfg2", "k.v", "LIVE"],
                                       ["git", "config", "--fil=../../elsewhere/cfg3", "k.v", "LIVE"])):
            with self.subTest(spelling=argv[2]):
                outcome = self._attempt(argv, self.repo)
                written = (self.outside / f"cfg{number}").exists()
                if outer:
                    self.assertEqual((outcome, written), ("REFUSED", False))
                else:
                    self.assertEqual((outcome, written), ("EXIT:0", True), argv)

    def test_reparse_and_hard_link_metadata_carry_commits_out(self) -> None:
        outer = _outer_guard_installed()
        before_objects = sum(1 for _ in self.objects_target.rglob("*"))
        before_log = self.linked_target.read_bytes()
        objects = self._attempt(["git", "commit", "-q", "--allow-empty", "-m", "live"], self.objects_repo)
        linked = self._attempt(["git", "commit", "-q", "--allow-empty", "-m", "live"], self.linked_repo)
        grew = sum(1 for _ in self.objects_target.rglob("*")) > before_objects
        appended = self.linked_target.read_bytes() != before_log
        if outer:
            self.assertEqual((objects, grew, linked, appended), ("REFUSED", False, "REFUSED", False))
        else:
            self.assertEqual((objects, grew, linked, appended), ("EXIT:0", True, "EXIT:0", True))


CHILD = textwrap.dedent(r'''
    import ctypes, json, os, socket, sqlite3, subprocess, sys
    from pathlib import Path
    layout = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    scratch, protected, target = Path(layout["scratch"]), Path(layout["protected"]), Path(layout["target"])
    repo, clean, allowed = Path(layout["repo"]), Path(layout["clean"]), Path(layout["allowed"])
    log = Path(layout["root"]) / "outside" / "events.jsonl"
    out = {}

    def events_since(offset):
        rows = log.read_text(encoding="utf-8").splitlines()[offset:] if log.is_file() else []
        return [json.loads(row) for row in rows]

    def run(name, fn):
        offset = len(log.read_text(encoding="utf-8").splitlines()) if log.is_file() else 0
        try:
            result = fn()
            if isinstance(result, subprocess.CompletedProcess):
                out[name] = {"outcome": f"EXIT:{result.returncode}", "stdout": (result.stdout or "")[:160],
                             "stderr": (result.stderr or "")[-300:]}
            else:
                out[name] = {"outcome": "ALLOWED"}
        except OSError as error:
            out[name] = {"outcome": type(error).__name__, "error": str(error)[:500]}
        except Exception as error:  # noqa: BLE001 - the class is the datum
            out[name] = {"outcome": "EXCEPTION:" + type(error).__name__, "error": str(error)[:500]}
        rows = events_since(offset)
        out[name]["blocked"] = [{"operation": r["operation"], "detail": r["detail"][:700]} for r in rows
                                if r["event"] == "BLOCKED"]

    def git(*args, cwd=None, env=None):
        return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)

    env = dict(os.environ)
    child_read = "import subprocess, sys; sys.exit(subprocess.run(['git', '-C', sys.argv[1], 'rev-parse', 'HEAD']).returncode)"

    def scratch_build():
        r = scratch / "built"
        results = [git("init", "-q", str(r)), git("-C", str(r), "config", "user.name", "scratch"),
                   git("-C", str(r), "config", "user.email", "scratch@bas.invalid")]
        (r / "x.txt").write_text("x\n")
        results += [git("-C", str(r), "add", "-A"), git("-C", str(r), "commit", "-q", "-m", "scratch build")]
        bad = [x for x in results if x.returncode != 0]
        return bad[0] if bad else git("-C", str(r), "log", "--format=%s", "-n", "1")

    def sql_read():
        c = sqlite3.connect((protected / "db.sqlite").as_uri() + "?mode=ro", uri=True)
        try:
            assert c.execute("select v from t").fetchone()[0] == "ORIGINAL"
        finally:
            c.close()

    def connect_test_net():
        handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        handle.settimeout(0.5)
        try:
            handle.connect(("192.0.2.1", 9))
        finally:
            handle.close()

    short =layout.get("short_protected")
    cases = {
        # ---- positives
        "P_rev_parse": lambda: git("-C", str(clean), "rev-parse", "HEAD", "HEAD^{tree}"),
        "P_diff_name_only": lambda: git("-C", str(clean), "diff", "--name-only", "HEAD~1", "HEAD"),
        "P_log_format": lambda: git("-C", str(clean), "log", "--format=%H %s", "-n", "2"),
        "P_status_porcelain": lambda: git("-C", str(clean), "status", "--porcelain=v1", "-uall", "-z"),
        "P_show_stat": lambda: git("-C", str(clean), "show", "--stat", "--format=%H", "HEAD"),
        "P_cat_file_exists": lambda: git("-C", str(clean), "cat-file", "-e", "HEAD^{commit}"),
        "P_ls_files": lambda: git("-C", str(clean), "ls-files", "--cached", "--others", "--exclude-standard", "-z"),
        "P_config_read": lambda: git("-C", str(clean), "config", "--get", "user.name"),
        "P_manager_owned_config_write": lambda: git("config", "fixture.owned", "OK", cwd=repo),
        "P_declared_identity_write": lambda: git("config", "user.name", "owned-positive", cwd=repo),
        "P_scratch_init_add_commit": scratch_build,
        "P_python_child_git_read": lambda: subprocess.run([sys.executable, "-B", "-c", child_read, str(clean)],
                                                          capture_output=True, text=True, timeout=120),
        "P_owned_write": lambda: (allowed / "owned.txt").write_text("owned"),
        "P_protected_sqlite_read_only": sql_read,
        # ---- the manager's counterexample and every spelling of a configuration file option
        "N_manager_attached_file": lambda: git("config", "-f../p/x", "fixture.value", "CHANGED", cwd=repo),
        "N_manager_attached_file_abbreviated_unset": lambda: git("config", "-f../p/x", "--unse", "fixture.value",
                                                                 cwd=repo),
        "N_separated_short_file": lambda: git("config", "-f", "../p/x", "fixture.value", "CHANGED", cwd=repo),
        "N_long_file_attached": lambda: git("config", "--file=../p/x", "fixture.value", "CHANGED", cwd=repo),
        "N_long_file_separated": lambda: git("config", "--file", "../p/x", "fixture.value", "CHANGED", cwd=repo),
        "N_long_file_abbreviated": lambda: git("config", "--fil=../p/x", "fixture.value", "CHANGED", cwd=repo),
        "N_long_file_abbreviated_short": lambda: git("config", "--fi", "../p/x", "fixture.value", "CHANGED", cwd=repo),
        "N_config_global": lambda: git("config", "--global", "fixture.value", "CHANGED", cwd=repo),
        "N_config_system": lambda: git("config", "--system", "fixture.value", "CHANGED", cwd=repo),
        "N_config_worktree": lambda: git("config", "--worktree", "fixture.value", "CHANGED", cwd=repo),
        "N_config_blob": lambda: git("config", "--blob=HEAD:f.txt", "--get", "x.y", cwd=repo),
        "N_config_unset": lambda: git("config", "--unset", "user.name", cwd=repo),
        "N_config_add": lambda: git("config", "--add", "user.name", "x", cwd=repo),
        "N_config_set_verb": lambda: git("config", "set", "user.name", "x", cwd=repo),
        "N_config_edit": lambda: git("config", "-e", cwd=repo),
        "N_config_undeclared_include": lambda: git("config", "include.path", "../p/x", cwd=repo),
        "N_config_undeclared_hookspath": lambda: git("config", "core.hooksPath", "../p", cwd=repo),
        "N_config_undeclared_alias": lambda: git("config", "alias.x", "!printf X > ../p/x", cwd=repo),
        "N_config_undeclared_worktree": lambda: git("config", "core.worktree", "../p", cwd=repo),
        # ---- option abbreviations of admitted options
        "N_log_format_abbreviated": lambda: git("-C", str(clean), "log", "--form=%H"),
        "N_status_porcelain_abbreviated": lambda: git("-C", str(clean), "status", "--porc"),
        "N_undeclared_short_letter": lambda: git("-C", str(clean), "status", "-X"),
        # ---- configuration, environment and helper indirection
        "N_dash_c_include": lambda: git("-c", "include.path=../p/x", "status", cwd=repo),
        "N_dash_c_protocol": lambda: git("-c", "protocol.allow=always", "status", cwd=repo),
        "N_config_env_option": lambda: git("--config-env=core.editor=PATH", "status", cwd=repo),
        "N_env_git_config_file": lambda: git("config", "user.name", "x", cwd=repo,
                                             env={**env, "GIT_CONFIG": str(target)}),
        "N_env_git_config_system": lambda: git("status", cwd=repo, env={**env, "GIT_CONFIG_SYSTEM": str(target)}),
        "N_env_global_config_include": lambda: git("status", cwd=repo,
                                                   env={**env, "GIT_CONFIG_GLOBAL": layout["global_include"]}),
        "N_env_git_dir_protected": lambda: git("status", cwd=repo, env={**env, "GIT_DIR": str(protected / "fake.git")}),
        "N_env_index_file_protected": lambda: git("add", "-A", cwd=repo,
                                                  env={**env, "GIT_INDEX_FILE": str(protected / "idx")}),
        "N_env_object_directory_protected": lambda: git("commit", "-q", "--allow-empty", "-m", "x", cwd=repo,
                                                        env={**env, "GIT_OBJECT_DIRECTORY": str(protected / "objects")}),
        # ---- path aliases and reparse points
        "N_init_through_junction": lambda: git("init", "-q", str(Path(layout["junction"]) / "newrepo")),
        "N_read_through_junction": lambda: git("-C", layout["junction"], "status"),
        "N_gitfile_to_protected_write": lambda: git("-C", layout["gitfile_repo"], "config", "user.name", "x"),
        "N_objects_junction_commit": lambda: git("-C", layout["objects_junction_repo"], "commit", "-q",
                                                 "--allow-empty", "-m", "x"),
        "N_hardlinked_reflog_commit": lambda: git("-C", layout["hardlink_repo"], "commit", "-q", "--allow-empty",
                                                  "-m", "x"),
        "N_extended_length_prefix": lambda: git("-C", "\\\\?\\" + str(protected), "status"),
        "N_admin_share_spelling": lambda: git("-C", "\\\\localhost\\" + str(protected)[0] + "$" + str(protected)[2:],
                                              "status"),
        "N_short_name_spelling": (lambda: git("-C", short, "status")) if short else None,
        # ---- native children
        "N_cmd_child": lambda: subprocess.run(["cmd", "/c", "echo X > " + str(target)], capture_output=True),
        "N_shell_true": lambda: subprocess.run("echo X > " + str(target), shell=True, capture_output=True),
        "N_powershell_child": lambda: subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Content", str(target),
                                                      "X"], capture_output=True),
        "N_os_system": lambda: os.system("echo X > " + str(target)),
        "N_ctypes_createprocess": lambda: ctypes.windll.kernel32.CreateProcessW,
        # ---- the network
        "N_git_ls_remote": lambda: git("ls-remote", "https://example.invalid/repo.git", cwd=repo),
        "N_git_fetch": lambda: git("fetch", str(clean), cwd=repo),
        "N_network_test_net": connect_test_net,
    }
    for name, fn in cases.items():
        if fn is not None:
            run(name, fn)
    print(json.dumps(out))
''')

#: The refusal each negative case must reach (a substring of the guard's logged reason).
EXPECTED_REASONS = {
    "N_manager_attached_file": "names a configuration file",
    "N_manager_attached_file_abbreviated_unset": "names a configuration file",
    "N_separated_short_file": "names a configuration file",
    "N_long_file_attached": "names a configuration file",
    "N_long_file_separated": "names a configuration file",
    "N_long_file_abbreviated": "names a configuration file",
    "N_long_file_abbreviated_short": "names a configuration file",
    "N_config_global": "names a configuration file",
    "N_config_system": "names a configuration file",
    "N_config_worktree": "names a configuration file",
    "N_config_blob": "names a configuration file",
    "N_config_unset": "configuration write action",
    "N_config_add": "configuration write action",
    "N_config_set_verb": "git config write form",
    "N_config_edit": "runs a program or edits interactively",
    "N_config_undeclared_include": "is not a declared write key",
    "N_config_undeclared_hookspath": "is not a declared write key",
    "N_config_undeclared_alias": "is not a declared write key",
    "N_config_undeclared_worktree": "is not a declared write key",
    "N_log_format_abbreviated": "abbreviates",
    "N_status_porcelain_abbreviated": "abbreviates",
    "N_undeclared_short_letter": "is not in the typed grammar",
    "N_dash_c_include": "is not a literal data-shaping setting",
    "N_dash_c_protocol": "is not a literal data-shaping setting",
    "N_config_env_option": "global option",
    "N_env_git_config_file": "GIT_CONFIG is set",
    "N_env_git_config_system": "GIT_CONFIG_SYSTEM is set",
    "N_env_global_config_include": "configuration include",
    "N_env_git_dir_protected": "GIT_DIR resolves into the guarded root",
    "N_env_index_file_protected": "GIT_INDEX_FILE resolves into the guarded root",
    "N_env_object_directory_protected": "GIT_OBJECT_DIRECTORY resolves into the guarded root",
    "N_init_through_junction": "resolves into the guarded root",
    "N_read_through_junction": "git working directory is protected",
    "N_gitfile_to_protected_write": "not wholly inside a git scratch root",
    "N_objects_junction_commit": "reparse point in the repository metadata",
    "N_hardlinked_reflog_commit": "multiply linked file in the repository metadata",
    "N_extended_length_prefix": "git working directory is protected",
    "N_admin_share_spelling": "git working directory is protected",
    "N_short_name_spelling": "git working directory is protected",
    "N_cmd_child": "is neither a guard-installing Python child nor confined git",
    "N_shell_true": "is neither a guard-installing Python child nor confined git",
    "N_powershell_child": "is neither a guard-installing Python child nor confined git",
    "N_os_system": "cannot be confined",
    "N_ctypes_createprocess": "native file-mutation entry point",
    "N_git_ls_remote": "is not an admitted read-only builtin",
    "N_git_fetch": "is not an admitted read-only builtin",
}
NETWORK_NEGATIVES = {"N_network_test_net": "NetworkRefused"}


@unittest.skipUnless(os.name == "nt", "junctions, 8.3 names and the native cases are Windows routes")
class GitGrammarMatrixTests(unittest.TestCase):
    """The manager's layout, every alias and indirection, one guarded child, byte-for-byte protected tree."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name) / "grammar"
        (root / "outside").mkdir(parents=True)
        layout = build_layout(root)
        (root / "outside" / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
        cls.layout = layout
        cls.protected = Path(layout["protected"])
        cls.before = tree_state(cls.protected)
        env = dict(os.environ)
        env.update(PYTHONPATH=str(GUARD_DIR), PYTHONDONTWRITEBYTECODE="1", BAS_CANONICAL_WRITE_GUARD=str(cls.protected),
                   BAS_CANONICAL_WRITE_ALLOW=layout["allowed"],
                   BAS_CANONICAL_WRITE_GUARD_LOG=str(root / "outside" / "events.jsonl"),
                   BAS_CANONICAL_WRITE_GIT_SCRATCH=layout["scratch"], BAS_NETWORK_GUARD="DENY_NON_LOOPBACK")
        completed = subprocess.run([sys.executable, "-B", "-c", CHILD, str(root / "outside" / "layout.json")], env=env,
                                   cwd=root / "outside", capture_output=True, text=True, timeout=900, check=False)
        cls.completed = completed
        cls.results = json.loads(completed.stdout) if completed.returncode == 0 and completed.stdout.strip() else {}
        cls.after = tree_state(cls.protected)
        cls.events = [json.loads(line) for line in (root / "outside" / "events.jsonl").read_text(encoding="utf-8")
                      .splitlines()] if (root / "outside" / "events.jsonl").is_file() else []

    @classmethod
    def tearDownClass(cls) -> None:
        for junction in cls.layout.get("junctions", []):
            if os.path.lexists(junction):
                os.rmdir(junction)  # removes this suite's own junction, never its target
        cls._tmp.cleanup()

    def expected_negatives(self) -> set:
        expected = set(EXPECTED_REASONS) | set(NETWORK_NEGATIVES)
        if not self.layout.get("short_protected"):
            expected.discard("N_short_name_spelling")
        return expected

    def test_the_matrix_child_completed(self) -> None:
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr[-4000:])
        self.assertEqual({n for n in self.results if n.startswith("N_")}, self.expected_negatives())

    def test_every_positive_case_still_works(self) -> None:
        positives = {name: row for name, row in self.results.items() if name.startswith("P_")}
        self.assertEqual(len(positives), 14)
        for name, row in sorted(positives.items()):
            with self.subTest(case=name):
                self.assertIn(row["outcome"], ("EXIT:0", "ALLOWED"), row)
                self.assertEqual(row["blocked"], [], name)

    def test_every_negative_case_is_refused_for_its_intended_cause(self) -> None:
        for name, reason in sorted(EXPECTED_REASONS.items()):
            if name not in self.results:
                continue
            row = self.results[name]
            with self.subTest(case=name):
                self.assertEqual(row["outcome"], "CanonicalWriteRefused", row)
                self.assertTrue(any(reason in blocked["detail"] for blocked in row["blocked"]),
                                f"{name}: {reason!r} not in {row['blocked']}")
        for name, outcome in NETWORK_NEGATIVES.items():
            self.assertEqual(self.results[name]["outcome"], outcome, name)

    def test_the_protected_tree_is_byte_for_byte_unchanged(self) -> None:
        self.assertEqual(self.after, self.before)
        self.assertEqual(Path(self.layout["target"]).read_text(encoding="utf-8"), "[fixture]\n\tvalue = ORIGINAL\n")

    def test_the_owned_positives_wrote_only_the_scratch_repository(self) -> None:
        for key, value in (("fixture.owned", "OK"), ("user.name", "owned-positive")):
            with self.subTest(key=key):
                completed = _git("config", "--get", key, cwd=Path(self.layout["repo"]))
                self.assertEqual(completed.stdout.strip(), value)

    def test_admitted_git_writes_name_the_typed_grammar(self) -> None:
        installed = [row for row in self.events if row["event"] == "INSTALLED"]
        self.assertTrue(installed)
        self.assertTrue(all("BAS-CANONICAL-WRITE-GUARD-v37.5" == row["guard_version"] for row in installed))
        admitted = [row["detail"] for row in self.events if row["event"] == "CHILD_ADMITTED"]
        self.assertTrue(any("confined to the scratch repository" in d and "typed grammar" in d for d in admitted))
        self.assertTrue(any("read-only, controlled environment" in d and "typed grammar" in d for d in admitted))


class GrammarUnitTests(unittest.TestCase):
    """The grammar parser itself, imported directly (importing installs nothing)."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(GUARD_DIR))
        import bas_canonical_write_guard as guard  # noqa: PLC0415

        cls.guard = guard

    def parse(self, subcommand: str, *args: str):
        return self.guard._parse_git_arguments(subcommand, list(args))

    def test_every_form_the_attempt_4_lanes_admitted_still_parses(self) -> None:
        # The complete set of git forms the Attempt 4 lanes' guard logs admitted (their argv skeletons).
        admitted = [
            ("log", "--format=%H %s", "ade8f25a..HEAD"), ("ls-tree", "-r", "--full-tree", "cfdc588c"),
            ("rev-parse", "--abbrev-ref", "HEAD"), ("rev-parse", "HEAD"), ("status", "--porcelain=v1", "-uall"),
            ("status", "--porcelain=v1", "-uall", "--", "jira"), ("add", "-A"), ("add", ".gitignore", "tracked.txt"),
            ("cat-file", "--batch"), ("cat-file", "-e", "b1c01b48^{commit}"), ("commit", "-q", "-am", "later"),
            ("commit", "-q", "-m", "discovery"), ("config", "user.email", "fixture@example.invalid"), ("init", "-q"),
            ("log", "--format=%H", "--", "docs/plan.md"), ("ls-files", "--cached", "--others", "--exclude-standard",
                                                            "-z"),
            ("merge-base", "--is-ancestor", "cfdc588c", "HEAD"), ("commit", "-q", "--allow-empty", "-m", "noop"),
            ("branch", "--all", "--verbose", "--no-abbrev"), ("cat-file", "-t", "d4bce7be"),
            ("log", "--diff-filter=A", "--format=%H", "--", "artifacts/x.json"), ("log", "--format=%H%x00%s", "a..b"),
            ("log", "--format=%h %s", "a..b"), ("log", "--format=%s", "-n", "1"), ("ls-files", "-z"),
            ("remote", "get-url", "origin"), ("rev-list", "origin/main..HEAD"),
            ("rev-parse", "--path-format=absolute", "--git-common-dir"), ("rev-parse", "--show-toplevel"),
            ("status", "--porcelain"), ("status", "--short", "--branch"), ("worktree", "list", "--porcelain"),
            ("init", "-q", r"C:\x\repo"),
        ]
        for form in admitted:
            with self.subTest(form=form):
                parsed, reason = self.parse(*form)
                self.assertIsNotNone(parsed, reason)

    def test_writes_are_exactly_the_four_forms(self) -> None:
        self.assertTrue(self.parse("config", "user.name", "x")[0]["writes"])
        self.assertFalse(self.parse("config", "--get", "user.name")[0]["writes"])
        self.assertTrue(self.parse("init", "-q")[0]["writes"])
        self.assertTrue(self.parse("add", "-A")[0]["writes"])
        self.assertTrue(self.parse("commit", "-q", "-m", "x")[0]["writes"])
        writers = {name for name, spec in self.guard._GIT_GRAMMAR.items() if spec.writes}
        self.assertEqual(writers, {"init", "add", "commit"})

    def test_values_are_typed_wherever_they_are_written(self) -> None:
        for args in (("config", "-f../p/x", "k.v", "x"), ("config", "-fx", "k.v", "x"), ("log", "-n", "x"),
                     ("status", "-uevery"), ("log", "--diff-filter=Q"), ("init", "-b", "-bad"),
                     ("rev-parse", "--path-format=weird", "--git-dir"), ("log", "--format=%G?"),
                     ("cat-file", "-t"), ("worktree", "add", "x"), ("symbolic-ref", "HEAD", "refs/heads/x")):
            with self.subTest(args=args):
                parsed, reason = self.parse(*args)
                self.assertIsNone(parsed)
                self.assertTrue(reason)

    def test_without_a_declared_scratch_root_no_git_write_is_admitted(self) -> None:
        # v37.5 has no TEMP default. A guarded child cannot be made without the root here -- a guard propagates its
        # scratch root into every Python child it starts (a child may narrow it, never drop it) -- so the rule is
        # checked on the decision function; the WRITE_PROTECTION lane also runs it live from an unguarded parent.
        from unittest import mock  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(self.guard, "_scratch_roots", return_value=()):
            ok, reason = self.guard._git_child_is_confined(["git", "init", "-q", str(Path(tmp) / "r")], tmp, {}, False)
            self.assertFalse(ok)
            self.assertIn("declares no git scratch root", reason)
            ok, reason = self.guard._git_child_is_confined(["git", "rev-parse", "--is-inside-work-tree"], tmp, {}, False)
            self.assertTrue(ok, reason)

    def test_short_clusters_expand_only_to_declared_letters(self) -> None:
        self.assertIsNotNone(self.parse("commit", "-qam", "x")[0])
        self.assertIsNone(self.parse("commit", "-qSm", "x")[0])
        self.assertEqual(self.parse("status", "-sb")[0]["options"], {"-s": [None], "-b": [None]})
        self.assertEqual(self.parse("status", "-uno")[0]["options"], {"-u": ["no"]})


if __name__ == "__main__":
    unittest.main()
