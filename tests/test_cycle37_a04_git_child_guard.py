"""Cycle #37 — Attempt #4 — MF37A03-01: a guarded process's git children are confined to exact operations.

The Attempt #3 manager showed that the v37.3 guard refused ``Path.write_text`` on a protected sentinel but
admitted ``git -c alias.manager-probe=!printf ... > <sentinel> manager-probe``, which changed the sentinel.
The failure class is broader than ``-c``: git runs programs named by repository configuration (alias,
fsmonitor, filter, textconv), by configuration files outside the command line (include, the global file), by
the environment (GIT_EXTERNAL_DIFF, GIT_CONFIG_COUNT, GIT_TRACE, GIT_REDIRECT_*), by hooks, by an implicit
bare repository it discovers, and a program merely *named* git is not git.

``LiveVectorControls`` first shows each vector is real: run without a guard, its payload writes a canary. (When
this suite itself runs inside a guarded lane, the same attempts must be refused -- or, for hooks, neutralized
-- by that outer guard instead.) ``GitChildMatrixTests`` then runs every case in one guarded child whose
payloads target a protected sentinel, with a declared polarity, the refusal reason each negative must reach,
and a byte-for-byte check of the protected tree afterwards.

Three cases are this attempt's own challenges to assumptions the manager's probe did not test: the command
line is the whole command (repository and global configuration, implicit bare repositories); the program named
git is git (an impostor ``git.exe``); and the audited command line is parsed as git will parse it (quoted
Windows command-line strings).
"""

from __future__ import annotations

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
IMPOSTOR_SOURCE = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32" / "hostname.exe"


def _outer_guard_installed() -> bool:
    outer = sys.modules.get("bas_canonical_write_guard")
    return bool(outer is not None and outer._STATE.get("installed"))


def _git(*args: str, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120, check=False)


def _payload(target: Path) -> str:
    return f"printf LIVE > '{target.as_posix()}'"


def _append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _repo(path: Path) -> Path:
    """A repository with two commits, built before any malicious configuration is added."""

    path.mkdir(parents=True)
    for args in (("init", "-q"), ("config", "user.name", "fixture"), ("config", "user.email", "fixture@bas.invalid")):
        completed = _git(*args, cwd=path)
        assert completed.returncode == 0, completed.stderr
    for text, message in (("one\n", "one"), ("two\n", "two")):
        (path / "f.txt").write_text(text, encoding="utf-8", newline="\n")
        assert _git("add", "-A", cwd=path).returncode == 0
        completed = _git("commit", "-q", "-m", message, cwd=path)
        assert completed.returncode == 0, completed.stderr
    return path


def _bare_copy(source: Path, target: Path) -> Path:
    """An implicit bare repository made by copying a .git directory (no git command needed)."""

    shutil.copytree(source / ".git", target)
    _append(target / "config", "[core]\n\tbare = true\n")
    return target


def build_vectors(base: Path, target_for: callable) -> dict:
    """Every configuration/environment vector, with its payload writing ``target_for(name)``."""

    base.mkdir(parents=True, exist_ok=True)
    vectors: dict = {"base": str(base)}

    r = _repo(base / "repo_alias")
    _append(r / ".git" / "config", f'[alias]\n\tp = "!{_payload(target_for("repo_alias"))}"\n')
    vectors["repo_alias"] = str(r)

    r = _repo(base / "repo_fsmonitor")
    _append(r / ".git" / "config", f'[core]\n\tfsmonitor = "{_payload(target_for("repo_fsmonitor"))}"\n')
    (r / "f.txt").write_text("three\n", encoding="utf-8", newline="\n")
    vectors["repo_fsmonitor"] = str(r)

    r = _repo(base / "repo_textconv")
    _append(r / ".git" / "config", f'[diff "x"]\n\ttextconv = "{_payload(target_for("repo_textconv"))} ;"\n')
    (r / ".gitattributes").write_text("*.txt diff=x\n", encoding="utf-8", newline="\n")
    vectors["repo_textconv"] = str(r)

    evil = base / "included.cfg"
    evil.write_text(f'[alias]\n\tp = "!{_payload(target_for("repo_include"))}"\n', encoding="utf-8", newline="\n")
    r = _repo(base / "repo_include")
    _append(r / ".git" / "config", f"[include]\n\tpath = {evil.as_posix()}\n")
    vectors["repo_include"] = str(r)

    global_config = base / "global.cfg"
    global_config.write_text(f'[core]\n\tfsmonitor = "{_payload(target_for("global_config"))}"\n',
                             encoding="utf-8", newline="\n")
    r = _repo(base / "repo_global")
    (r / "f.txt").write_text("three\n", encoding="utf-8", newline="\n")
    vectors["global_config"] = str(global_config)
    vectors["repo_global"] = str(r)

    script = base / "external_diff.sh"
    script.write_text(f"#!/bin/sh\n{_payload(target_for('env_external_diff'))}\n", encoding="utf-8", newline="\n")
    vectors["external_diff_script"] = str(script)
    vectors["repo_plain"] = str(_repo(base / "repo_plain"))

    r = _repo(base / "repo_filter")
    _append(r / ".git" / "config", f'[filter "x"]\n\tclean = "{_payload(target_for("repo_filter"))} ;"\n')
    (r / ".gitattributes").write_text("*.txt filter=x\n", encoding="utf-8", newline="\n")
    (r / "g.txt").write_text("new\n", encoding="utf-8", newline="\n")
    vectors["repo_filter"] = str(r)

    # Hook repositories: the file to commit is staged first, so the hooked commit has content and the
    # pre-commit hook would run.
    r = _repo(base / "repo_hook")
    (r / "h.txt").write_text("h\n", encoding="utf-8", newline="\n")
    assert _git("add", "h.txt", cwd=r).returncode == 0
    (r / ".git" / "hooks" / "pre-commit").write_text(f"#!/bin/sh\n{_payload(target_for('repo_hook'))}\n",
                                                     encoding="utf-8", newline="\n")
    vectors["repo_hook"] = str(r)

    r = _repo(base / "repo_hookspath")
    (r / "h.txt").write_text("h\n", encoding="utf-8", newline="\n")
    assert _git("add", "h.txt", cwd=r).returncode == 0
    (r / "myhooks").mkdir()
    (r / "myhooks" / "pre-commit").write_text(f"#!/bin/sh\n{_payload(target_for('repo_hookspath'))}\n",
                                              encoding="utf-8", newline="\n")
    _append(r / ".git" / "config", "[core]\n\thooksPath = myhooks\n")
    vectors["repo_hookspath"] = str(r)

    source = _repo(base / "bare_source")
    bare = _bare_copy(source, base / "bare_trap")
    _append(bare / "config", f'[diff "x"]\n\ttextconv = "{_payload(target_for("implicit_bare"))} ;"\n')
    (bare / "info").mkdir(exist_ok=True)
    (bare / "info" / "attributes").write_text("*.txt diff=x\n", encoding="utf-8", newline="\n")
    vectors["bare_trap"] = str(bare)

    fake = base / "fakebin"
    fake.mkdir()
    shutil.copy2(IMPOSTOR_SOURCE, fake / "git.exe")
    vectors["impostor_git"] = str(fake / "git.exe")
    return vectors


#: Each live vector: how it is triggered from ``cwd`` (a vectors key or the base), with an optional env.
def _live_attempts(v: dict) -> dict:
    env = dict(os.environ)
    return {
        "cli_alias": (["git", "-c", f"alias.p=!{_payload(Path(v['base']) / 'canary_cli_alias')}", "p"], v["base"], None),
        "repo_alias": (["git", "p"], v["repo_alias"], None),
        "repo_fsmonitor": (["git", "status", "--porcelain"], v["repo_fsmonitor"], None),
        "repo_textconv": (["git", "show", "HEAD"], v["repo_textconv"], None),
        "repo_include": (["git", "p"], v["repo_include"], None),
        "global_config": (["git", "status"], v["repo_global"], {**env, "GIT_CONFIG_GLOBAL": v["global_config"]}),
        "env_external_diff": (["git", "diff", "HEAD~1", "HEAD"], v["repo_plain"],
                              {**env, "GIT_EXTERNAL_DIFF": Path(v["external_diff_script"]).as_posix()}),
        "env_config_count": (["git", "p"], v["base"],
                             {**env, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "alias.p",
                              "GIT_CONFIG_VALUE_0": f"!{_payload(Path(v['base']) / 'canary_env_config_count')}"}),
        "env_trace_file": (["git", "--version"], v["base"], {**env, "GIT_TRACE": str(Path(v["base"]) / "canary_env_trace_file")}),
        "env_redirect_stdout": (["git", "--version"], v["base"],
                                {**env, "GIT_REDIRECT_STDOUT": str(Path(v["base"]) / "canary_env_redirect_stdout")}),
        "repo_filter": (["git", "add", "g.txt"], v["repo_filter"], None),
        "repo_hook": (["git", "commit", "-q", "-am", "hook"], v["repo_hook"], None),
        "implicit_bare": (["git", "show", "master"], v["bare_trap"], None),
        "impostor_git": ([v["impostor_git"], "--version"], v["base"], None),
    }


@unittest.skipUnless(os.name == "nt", "live vectors require Windows executables and reparse points")
class LiveVectorControls(unittest.TestCase):
    """Each vector writes its canary when nothing guards it (outside a guarded lane)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name) / "live"
        cls.vectors = build_vectors(base, lambda name: base / f"canary_{name}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_vector_is_live_or_refused_by_an_outer_guard(self) -> None:
        outer = _outer_guard_installed()
        base = Path(self.vectors["base"])
        for name, (argv, cwd, env) in _live_attempts(self.vectors).items():
            with self.subTest(vector=name):
                canary = base / f"canary_{name}"
                try:
                    completed = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
                    outcome = f"EXIT:{completed.returncode}"
                    stdout = completed.stdout
                except OSError as error:
                    outcome = "REFUSED" if type(error).__name__ == "CanonicalWriteRefused" else repr(error)
                    stdout = ""
                if name == "impostor_git":
                    # Its effect is running a different program, not writing a file.
                    live = outcome.startswith("EXIT:") and not stdout.startswith("git version")
                else:
                    live = canary.exists()
                if not outer:
                    self.assertTrue(live, f"{name}: {outcome}")
                elif name == "repo_hook":
                    # The outer guard admits a commit in its own scratch root but neutralizes the hook.
                    self.assertEqual((outcome, live), ("EXIT:0", False), name)
                else:
                    self.assertEqual((outcome, live), ("REFUSED", False), name)


CHILD = textwrap.dedent(r'''
    import ctypes, json, os, socket, sqlite3, subprocess, sys
    from pathlib import Path
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    v = manifest["vectors"]
    g, a, o, s = (Path(manifest[k]) for k in ("guarded", "allowed", "outside", "scratch"))
    repo = manifest["repo"]
    clean, spaced = manifest["clean"], manifest["spaced"]
    sentinel = g / "sentinel.txt"
    log = o / "events.jsonl"
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
            out[name] = {"outcome": type(error).__name__, "error": str(error)[:400]}
        except Exception as error:  # noqa: BLE001 - the class is the datum
            out[name] = {"outcome": "EXCEPTION:" + type(error).__name__, "error": str(error)[:400]}
        rows = events_since(offset)
        out[name]["blocked"] = [{"operation": r["operation"], "detail": r["detail"][:600]} for r in rows
                                if r["event"] == "BLOCKED"]
        out[name]["admitted"] = [r["detail"][:300] for r in rows if r["event"] == "CHILD_ADMITTED"]

    def git(*args, cwd=None, env=None):
        return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)

    def payload(target):
        return f"printf LIVE > '{Path(target).as_posix()}'"

    def with_environ(changes, fn):
        saved = {k: os.environ.get(k) for k in changes}
        try:
            for key, value in changes.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            return fn()
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def impostor_from_cwd():
        here = os.getcwd()
        os.chdir(Path(v["impostor_git"]).parent)
        try:
            return with_environ({"NODEFAULTCURRENTDIRECTORYINEXEPATH": None}, lambda: git("--version"))
        finally:
            os.chdir(here)

    def scratch_build():
        r = s / "built"
        results = [git("init", "-q", str(r)), git("-C", str(r), "config", "user.name", "scratch"),
                   git("-C", str(r), "config", "user.email", "scratch@bas.invalid")]
        (r / "x.txt").write_text("x\n")
        results += [git("-C", str(r), "add", "-A"), git("-C", str(r), "commit", "-q", "-m", "scratch build")]
        bad = [x for x in results if x.returncode != 0]
        return bad[0] if bad else git("-C", str(r), "log", "--format=%s", "-n", "1")

    def sql_read():
        c = sqlite3.connect((g / "db.sqlite").as_uri() + "?mode=ro", uri=True)
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

    env = dict(os.environ)
    minimal = {"SYSTEMROOT": os.environ["SYSTEMROOT"], "PATH": os.environ.get("PATH", "")}
    child_git = "import subprocess, sys; sys.exit(subprocess.run(['git', '-C', sys.argv[1], 'rev-parse', 'HEAD']).returncode)"
    cases = {
        # ---- positives: local identity/diff reads, scratch repositories, Python children, owned writes
        "P_version": lambda: git("--version"),
        "P_rev_parse": lambda: git("-C", clean, "rev-parse", "HEAD", "HEAD^{tree}"),
        "P_status_porcelain": lambda: git("-C", clean, "status", "--porcelain=v1", "-uall", "-z"),
        "P_diff_stat": lambda: git("-C", clean, "diff", "--stat", "HEAD~1", "HEAD"),
        "P_log_format": lambda: git("-C", clean, "log", "--format=%H %s", "-n", "2"),
        "P_log_patch": lambda: git("-C", clean, "log", "-p", "-n", "1"),
        "P_ls_files": lambda: git("-C", clean, "ls-files", "-z"),
        "P_ls_tree": lambda: git("-C", clean, "ls-tree", "-r", "--full-tree", "HEAD"),
        "P_cat_file": lambda: git("-C", clean, "cat-file", "-t", "HEAD"),
        "P_show_name_only": lambda: git("-C", clean, "show", "--name-only", "--pretty=format:", "HEAD"),
        "P_config_get": lambda: git("-C", clean, "config", "--get", "user.name"),
        "P_branch_show_current": lambda: git("-C", clean, "branch", "--show-current"),
        "P_branch_all_verbose": lambda: git("-C", clean, "branch", "--all", "--verbose"),
        "P_worktree_list": lambda: git("-C", clean, "worktree", "list", "--porcelain"),
        "P_symbolic_ref_read": lambda: git("-C", clean, "symbolic-ref", "HEAD"),
        "P_for_each_ref": lambda: git("-C", clean, "for-each-ref", "--format=%(refname)"),
        "P_merge_base_ancestor": lambda: git("-C", clean, "merge-base", "--is-ancestor", "HEAD~1", "HEAD"),
        "P_rev_list_count": lambda: git("-C", clean, "rev-list", "--count", "HEAD"),
        "P_grep": lambda: git("-C", clean, "grep", "-n", "two"),
        "P_hash_object_read_only": lambda: git("-C", clean, "hash-object", "f.txt"),
        "P_safe_dash_c": lambda: git("-C", clean, "-c", "core.quotepath=off", "ls-files"),
        "P_bas_checkout_rev_parse": lambda: git("-C", repo, "rev-parse", "HEAD"),
        "P_bas_checkout_status": lambda: git("-C", repo, "status", "--porcelain=v1"),
        "P_string_command_line_with_space": lambda: subprocess.run(f'git -C "{spaced}" rev-parse HEAD',
                                                                    capture_output=True, text=True, timeout=60),
        "P_scratch_init_add_commit": scratch_build,
        "P_scratch_commit_hook_not_run": lambda: git("-C", v["repo_hook"], "commit", "-q", "-am", "hook"),
        "P_scratch_commit_hookspath_not_run": lambda: git("-C", v["repo_hookspath"], "commit", "-q", "-am", "hook"),
        "P_python_child_inherited_env_git": lambda: subprocess.run(
            [sys.executable, "-B", "-c", child_git, clean], capture_output=True, text=True, timeout=120),
        "P_python_child_minimal_env_git": lambda: subprocess.run(
            [sys.executable, "-B", "-c", child_git, clean], env=dict(minimal), capture_output=True, text=True,
            timeout=120),
        "P_owned_write": lambda: (a / "owned.txt").write_text("owned"),
        "P_protected_sqlite_read_only": sql_read,
        # ---- the manager's counterexample and its command-line variants
        "N_manager_cli_alias": lambda: git("-c", "alias.manager-probe=!" + payload(sentinel), "manager-probe",
                                           cwd=clean),
        "N_cli_alias_string_command_line": lambda: subprocess.run(
            f'git -c "alias.p=!{payload(sentinel)}" p', cwd=clean, capture_output=True, text=True, timeout=60),
        "N_cli_config_env_option": lambda: git("--config-env=core.pager=GIT_EDITOR", "log", cwd=clean),
        "N_cli_paginate": lambda: git("-p", "log", cwd=clean),
        "N_cli_exec_path": lambda: git("--exec-path=" + str(o), "log", cwd=clean),
        "N_cli_hookspath": lambda: git("-c", "core.hooksPath=" + str(o), "status", cwd=clean),
        # ---- configuration that is not on the command line (inherited helper indirection)
        "N_repo_alias_invoked": lambda: git("p", cwd=v["repo_alias"]),
        "N_repo_alias_present_on_read": lambda: git("status", cwd=v["repo_alias"]),
        "N_repo_fsmonitor": lambda: git("status", "--porcelain", cwd=v["repo_fsmonitor"]),
        "N_repo_textconv": lambda: git("show", "HEAD", cwd=v["repo_textconv"]),
        "N_repo_include": lambda: git("status", cwd=v["repo_include"]),
        "N_global_config_file": lambda: git("status", cwd=v["repo_global"], env={**env, "GIT_CONFIG_GLOBAL": v["global_config"]}),
        "N_scratch_filter_add": lambda: git("add", "g.txt", cwd=v["repo_filter"]),
        "N_implicit_bare_repository": lambda: git("show", "master", cwd=v["bare_trap"]),
        # ---- environment
        "N_env_external_diff": lambda: git("diff", "HEAD~1", "HEAD", cwd=v["repo_plain"],
                                           env={**env, "GIT_EXTERNAL_DIFF": Path(v["external_diff_script"]).as_posix()}),
        "N_env_config_parameters": lambda: git("log", cwd=clean, env={**env, "GIT_CONFIG_PARAMETERS": "'core.pager=x'"}),
        "N_env_config_key_replaced": lambda: git("p", cwd=clean, env={**env, "GIT_CONFIG_KEY_0": "alias.p",
                                                                      "GIT_CONFIG_VALUE_0": "!" + payload(sentinel)}),
        "N_env_config_key_extra": lambda: git("log", cwd=clean, env={**env, "GIT_CONFIG_KEY_40": "core.pager",
                                                                     "GIT_CONFIG_VALUE_40": "x"}),
        "N_env_trace_file": lambda: git("--version", env={**env, "GIT_TRACE": str(g / "trace.txt")}),
        "N_env_redirect_stdout": lambda: git("--version", env={**env, "GIT_REDIRECT_STDOUT": str(g / "out.txt")}),
        "N_env_ssh_command": lambda: git("log", cwd=clean, env={**env, "GIT_SSH_COMMAND": payload(sentinel)}),
        "N_inherited_environment_tampered": lambda: with_environ(
            {"GIT_CONFIG_VALUE_1": payload(sentinel)}, lambda: git("status", cwd=v["repo_plain"])),
        # ---- subcommands that run programs or reach the network
        "N_sub_difftool": lambda: git("difftool", "-y", cwd=clean),
        "N_sub_help": lambda: git("help", "log", cwd=clean),
        "N_sub_fetch": lambda: git("fetch", "origin", cwd=clean),
        "N_sub_ls_remote": lambda: git("ls-remote", "https://example.invalid/repo.git", cwd=clean),
        "N_sub_clone": lambda: git("clone", clean, str(s / "cloned")),
        "N_sub_submodule": lambda: git("submodule", "update", cwd=clean),
        "N_sub_archive_remote": lambda: git("archive", "--remote=ext::sh", "HEAD", cwd=clean),
        "N_sub_bisect_run": lambda: git("bisect", "run", "sh", cwd=clean),
        "N_sub_push": lambda: git("push", str(s / "nowhere"), cwd=clean),
        # ---- options that run a program, write a file or verify signatures
        "N_opt_output_outside": lambda: git("log", "--output=" + str(o / "log.txt"), cwd=clean),
        "N_opt_output_abbreviated": lambda: git("log", "--outp=" + str(o / "log2.txt"), cwd=clean),
        "N_opt_ext_diff": lambda: git("diff", "--ext-diff", "HEAD~1", "HEAD", cwd=clean),
        "N_opt_show_signature": lambda: git("log", "--show-signature", cwd=clean),
        "N_opt_signature_format": lambda: git("log", "--format=%G?", cwd=clean),
        "N_opt_grep_pager": lambda: git("grep", "-O", "-e", "two", cwd=clean),
        "N_opt_cat_file_textconv": lambda: git("cat-file", "--textconv", "HEAD:f.txt", cwd=clean),
        "N_opt_init_template": lambda: git("init", "--template=" + str(o), str(s / "templated")),
        "N_opt_commit_sign": lambda: git("-C", v["repo_hook"], "commit", "-S", "-m", "signed", "--allow-empty"),
        "N_opt_add_patch": lambda: git("-C", v["repo_hook"], "add", "-p"),
        # ---- writes outside a git scratch root, and protected paths
        "N_write_add_outside_scratch": lambda: git("-C", clean, "add", "f.txt"),
        "N_write_config_outside_scratch": lambda: git("-C", clean, "config", "user.name", "changed"),
        "N_write_branch_create": lambda: git("-C", clean, "branch", "created"),
        "N_write_symbolic_ref": lambda: git("-C", clean, "symbolic-ref", "HEAD", "refs/heads/elsewhere"),
        "N_write_init_outside_scratch": lambda: git("init", "-q", str(o / "not_scratch")),
        "N_write_bas_checkout_config": lambda: git("-C", repo, "config", "user.name", "changed"),
        "N_protected_working_directory": lambda: git("-C", str(g), "status"),
        "N_protected_git_dir": lambda: git("--git-dir=" + str(g / "x.git"), "log", cwd=clean),
        # ---- a program named git that is not git
        "N_impostor_absolute_path": lambda: subprocess.run([v["impostor_git"], "--version"], capture_output=True,
                                                           text=True, timeout=60),
        "N_impostor_in_parent_cwd": impostor_from_cwd,
        # ---- other native children and the network
        "N_ctypes_createprocess": lambda: ctypes.windll.kernel32.CreateProcessW,
        "N_ctypes_winexec": lambda: ctypes.WinDLL("kernel32")["WinExec"],
        "N_ctypes_shellexecute": lambda: ctypes.windll.shell32.ShellExecuteW,
        "N_ctypes_crt_system": lambda: ctypes.cdll.msvcrt.system,
        "N_python_child_widening_scratch": lambda: subprocess.run(
            [sys.executable, "-B", "-c", "pass"], env={**env, "BAS_CANONICAL_WRITE_GIT_SCRATCH": str(o)},
            capture_output=True, text=True, timeout=60),
        "N_network_test_net": connect_test_net,
    }
    for name, fn in cases.items():
        run(name, fn)
    print(json.dumps(out))
''')

#: The refusal reason each negative case must reach (a substring of the guard's logged reason). A refusal for
#: another reason would not show that the case's own class is closed.
EXPECTED_REASONS = {
    "N_manager_cli_alias": "is not a literal data-shaping setting",
    "N_cli_alias_string_command_line": "is not a literal data-shaping setting",
    "N_cli_config_env_option": "global option",
    "N_cli_paginate": "global option",
    "N_cli_exec_path": "global option",
    "N_cli_hookspath": "is not a literal data-shaping setting",
    "N_repo_alias_invoked": "is not an admitted read-only builtin",
    "N_repo_alias_present_on_read": "(alias)",
    "N_repo_fsmonitor": "core.fsmonitor",
    "N_repo_textconv": "diff or textconv program",
    "N_repo_include": "configuration include",
    "N_global_config_file": "core.fsmonitor",
    "N_scratch_filter_add": "filter driver program",
    "N_implicit_bare_repository": "implicit bare repository",
    "N_env_external_diff": "GIT_EXTERNAL_DIFF is set",
    "N_env_config_parameters": "GIT_CONFIG_PARAMETERS is set",
    "N_env_config_key_replaced": "differs from the guard's controlled git environment",
    "N_env_config_key_extra": "set outside the guard's command-scope configuration",
    "N_env_trace_file": "GIT_TRACE is set",
    "N_env_redirect_stdout": "GIT_REDIRECT_STDOUT is set",
    "N_env_ssh_command": "GIT_SSH_COMMAND is set",
    "N_inherited_environment_tampered": "differs from the guard's controlled git environment",
    "N_sub_difftool": "is not an admitted read-only builtin",
    "N_sub_help": "is not an admitted read-only builtin",
    "N_sub_fetch": "is not an admitted read-only builtin",
    "N_sub_ls_remote": "is not an admitted read-only builtin",
    "N_sub_clone": "is not an admitted read-only builtin",
    "N_sub_submodule": "is not an admitted read-only builtin",
    "N_sub_archive_remote": "is not an admitted read-only builtin",
    "N_sub_bisect_run": "is not an admitted read-only builtin",
    "N_sub_push": "is not an admitted read-only builtin",
    "N_opt_output_outside": "writes a file",
    "N_opt_output_abbreviated": "writes a file",
    "N_opt_ext_diff": "runs a program",
    "N_opt_show_signature": "runs a program",
    "N_opt_signature_format": "verify a signature",
    "N_opt_grep_pager": "pager program",
    "N_opt_cat_file_textconv": "runs a program",
    "N_opt_init_template": "runs a program",
    "N_opt_commit_sign": "runs a program or edits",
    "N_opt_add_patch": "runs a program or edits",
    "N_write_add_outside_scratch": "not wholly inside a git scratch root",
    "N_write_config_outside_scratch": "not wholly inside a git scratch root",
    "N_write_branch_create": "creates a branch",
    "N_write_symbolic_ref": "symbolic-ref write form",
    "N_write_init_outside_scratch": "is not inside a git scratch root",
    "N_write_bas_checkout_config": "not wholly inside a git scratch root",
    "N_protected_working_directory": "git working directory is protected",
    "N_protected_git_dir": "--git-dir or --work-tree resolves into the guarded root",
    "N_impostor_absolute_path": "not the git this guard resolved",
    "N_impostor_in_parent_cwd": "not the git this guard resolved",
    "N_ctypes_createprocess": "native file-mutation entry point",
    "N_ctypes_winexec": "native file-mutation entry point",
    "N_ctypes_shellexecute": "native file-mutation entry point",
    "N_ctypes_crt_system": "native file-mutation entry point",
    "N_python_child_widening_scratch": "outside this process's scratch roots",
}
#: The negative whose refusal is the network guard's, not the write guard's.
NETWORK_NEGATIVES = {"N_network_test_net": "NetworkRefused"}


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


@unittest.skipUnless(os.name == "nt", "the git launcher, impostor and native cases are Windows routes")
class GitChildMatrixTests(unittest.TestCase):
    """Every git route and native-child case, each with a declared polarity and intended refusal reason."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name) / "git_matrix"
        g, a, o, s = root / "guarded", root / "guarded" / "allowed", root / "outside", root / "scratch"
        for path in (a, o, s):
            path.mkdir(parents=True)
        (g / "sentinel.txt").write_text("ORIGINAL-SENTINEL", encoding="utf-8")
        connection = sqlite3.connect(g / "db.sqlite")
        connection.execute("create table t(v text)")
        connection.execute("insert into t values ('ORIGINAL')")
        connection.commit()
        connection.close()
        sentinel = g / "sentinel.txt"
        # Vectors that are triggered by a read live outside the scratch root; those triggered by a write
        # (filter on add, hooks on commit) live inside it, so only the vector itself can refuse or neutralize them.
        read_vectors = build_vectors(o / "vectors", lambda name: sentinel)
        write_vectors = build_vectors(s / "vectors", lambda name: sentinel)
        vectors = {**read_vectors, "repo_filter": write_vectors["repo_filter"],
                   "repo_hook": write_vectors["repo_hook"], "repo_hookspath": write_vectors["repo_hookspath"]}
        clean = _repo(o / "clean")
        spaced = _repo(o / "with space" / "clean")
        manifest = {"vectors": vectors, "guarded": str(g), "allowed": str(a), "outside": str(o), "scratch": str(s),
                    "repo": str(REPO), "clean": str(clean), "spaced": str(spaced)}
        (o / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        cls.before = tree_state(g)
        cls.hook_heads = {name: _git("rev-parse", "HEAD", cwd=Path(vectors[name])).stdout.strip()
                          for name in ("repo_hook", "repo_hookspath")}
        env = dict(os.environ)
        env.update(PYTHONPATH=str(GUARD_DIR), PYTHONDONTWRITEBYTECODE="1", BAS_CANONICAL_WRITE_GUARD=str(g),
                   BAS_CANONICAL_WRITE_ALLOW=str(a), BAS_CANONICAL_WRITE_GUARD_LOG=str(o / "events.jsonl"),
                   BAS_CANONICAL_WRITE_GIT_SCRATCH=str(s), BAS_NETWORK_GUARD="DENY_NON_LOOPBACK")
        completed = subprocess.run([sys.executable, "-B", "-c", CHILD, str(o / "manifest.json")], env=env, cwd=o,
                                   capture_output=True, text=True, timeout=900, check=False)
        cls.completed = completed
        cls.results = json.loads(completed.stdout) if completed.returncode == 0 and completed.stdout.strip() else {}
        cls.after = tree_state(g)
        cls.vectors, cls.g, cls.o = vectors, g, o
        cls.hook_heads_after = {name: _git("log", "--format=%s", "-n", "1", cwd=Path(vectors[name])).stdout.strip()
                                for name in ("repo_hook", "repo_hookspath")}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_matrix_child_completed(self) -> None:
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr[-4000:])
        self.assertEqual({n for n in self.results if n.startswith("N_")},
                         set(EXPECTED_REASONS) | set(NETWORK_NEGATIVES))

    def test_every_positive_case_still_works(self) -> None:
        positives = {name: row for name, row in self.results.items() if name.startswith("P_")}
        self.assertEqual(len(positives), 31)
        for name, row in sorted(positives.items()):
            with self.subTest(case=name):
                self.assertIn(row["outcome"], ("EXIT:0", "ALLOWED"), row)
                self.assertEqual(row["blocked"], [], name)

    def test_every_negative_case_is_refused_for_its_intended_cause(self) -> None:
        negatives = {name for name in self.results if name.startswith("N_")}
        self.assertEqual(negatives, set(EXPECTED_REASONS) | set(NETWORK_NEGATIVES))
        for name, reason in sorted(EXPECTED_REASONS.items()):
            row = self.results[name]
            with self.subTest(case=name):
                self.assertEqual(row["outcome"], "CanonicalWriteRefused", row)
                self.assertTrue(any(reason in blocked["detail"] for blocked in row["blocked"]),
                                f"{name}: {reason!r} not in {row['blocked']}")
        for name, outcome in NETWORK_NEGATIVES.items():
            self.assertEqual(self.results[name]["outcome"], outcome, name)

    def test_the_protected_tree_is_byte_for_byte_unchanged(self) -> None:
        protected_before = {k: v for k, v in self.before.items() if not k.startswith("allowed")}
        protected_after = {k: v for k, v in self.after.items() if not k.startswith("allowed")}
        self.assertEqual(protected_after, protected_before)
        self.assertEqual((self.g / "sentinel.txt").read_text(encoding="utf-8"), "ORIGINAL-SENTINEL")

    def test_scratch_commits_happened_without_their_hooks(self) -> None:
        # The commit is real (the positive) and the hook, which would have written the sentinel, never ran.
        for name in ("repo_hook", "repo_hookspath"):
            with self.subTest(repository=name):
                self.assertEqual(self.hook_heads_after[name], "hook")

    def test_admitted_git_children_ran_in_the_controlled_environment(self) -> None:
        rows = [json.loads(line) for line in (self.o / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        installed = [row for row in rows if row["event"] == "INSTALLED"]
        self.assertTrue(installed)
        self.assertTrue(all("trusted git:" in row["detail"] for row in installed))
        admitted = [row["detail"] for row in rows if row["event"] == "CHILD_ADMITTED" and "argv=['git'" in row["detail"]]
        self.assertTrue(any("read-only, controlled environment" in detail for detail in admitted))
        self.assertTrue(any("confined to the scratch repository" in detail for detail in admitted))


class ControlledEnvironmentUnitTests(unittest.TestCase):
    """The pure functions, imported directly (no guard installed in this process by the import)."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(GUARD_DIR))
        import bas_canonical_write_guard as guard  # noqa: PLC0415

        cls.guard = guard

    def test_command_line_split_inverts_list2cmdline(self) -> None:
        cases = [["git", "-C", "C:\\a b\\c", "status"], ["x", 'q"uote', "tail\\", "\\\\srv\\share\\\"x\"", ""],
                 ["git", "-c", 'alias.p=!printf X > "C:/p q/s.txt"', "p"]]
        for case in cases:
            self.assertEqual(self.guard._split_command_line(subprocess.list2cmdline(case)), case)

    def test_the_controlled_environment_neutralizes_the_named_settings(self) -> None:
        env = self.guard.controlled_git_environment()
        scope = {env[f"GIT_CONFIG_KEY_{i}"].lower(): env[f"GIT_CONFIG_VALUE_{i}"]
                 for i in range(int(env["GIT_CONFIG_COUNT"]))}
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "file")
        self.assertEqual(env["GIT_OPTIONAL_LOCKS"], "0")
        for key, value in (("core.fsmonitor", "false"), ("protocol.allow", "never"),
                           ("safe.barerepository", "explicit"), ("log.showsignature", "false")):
            self.assertEqual(scope[key], value, key)
        self.assertTrue(scope["core.hookspath"].endswith("__bas_guard_no_git_hooks__"))
        # Windows cannot hold an empty environment value, so no controlled value may be empty.
        self.assertTrue(all(value != "" for value in env.values()))

    def test_the_config_parser_fails_closed_and_reads_subsections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config"
            path.write_text('[core]\n\tbare = false\n[Filter "Mixed"]\n\tClean = "x ; y"\n', encoding="utf-8")
            entries, error = self.guard._parse_git_config(str(path))
            self.assertIsNone(error)
            self.assertIn(("filter.Mixed.clean", "x ; y"), entries)
            self.assertIn("filter driver", self.guard._scan_git_config(str(path)))
            path.write_text("[core]\n\t=== not a key ===\n", encoding="utf-8")
            self.assertIn("unparseable", self.guard._scan_git_config(str(path)))


if __name__ == "__main__":
    unittest.main()
