"""Cycle #37 — Attempt #5 — the BAS canonical write guard, v37.5 (MF37A04-01 repair over v37.4/MF37A03-01).

v37.5 changes how a git child's command line is judged: a typed grammar of exact options, value types and
positional types per admitted subcommand replaces v37.4's scan for forbidden option names and letters; native Git
writes (``init``, ``config <declared key> <value>``, ``add``, ``commit``) need an explicitly declared Git scratch
root (no default), lie there by every spelling, and refuse a repository whose metadata holds a reparse point or a
multiply-linked file. The Attempt #4 manager showed that v37.4 admitted ``git config -f../p/x key value`` in a
scratch repository and let it rewrite a protected file. The git section below says exactly what changed; every
other route is unchanged from v37.4.

v37.4 changed which git children are admitted and under which environment, plus the refusal of native
process-creation entry points through ``ctypes``. The Attempt #3 manager showed that v37.3 admitted
``git -c alias.x=!<shell>`` because it checked only path-shaped arguments.

Loaded through ``sitecustomize`` in the canonical-mounted validation lanes only, and only when
``BAS_CANONICAL_WRITE_GUARD`` names the guarded root. Under that root, outside the roots listed in
``BAS_CANONICAL_WRITE_ALLOW``, a Python process that has the guard installed cannot change a byte, a name or
a timestamp through any route this module enumerates.

What was wrong with v1 (reproduced by the Attempt #2 manager, WRITE_GUARD_INDEPENDENT_PROBE.json):

* the refusing wrappers read the target only from a *positional* argument, so ``os.unlink(path=...)``
  passed straight through and deleted a protected file;
* a read-write ``sqlite3.connect`` under the root was logged, not refused, so ``UPDATE`` + ``commit``
  changed a protected database;
* every wrapper replaced one attribute of ``os``/``io``, so ``nt.unlink``, ``_io.FileIO``, a module that had
  bound ``os.remove`` before installation, or any C-level caller was never seen at all.

v2 enforces through ``sys.addaudithook``. CPython raises its audit events inside the C implementations, so a
keyword argument, an ``nt``/``_io`` alias, an early-bound reference and ``pathlib`` all arrive at the same
check, and an audit hook cannot be removed once added. The attribute patches that remain do exactly one
thing the hook cannot: skip a whole-file write whose bytes equal the existing file's (nothing is opened for
writing, so neither bytes nor times change). They are no longer the enforcement layer.

A path is protected when any of its forms -- the literal absolute path, the fully resolved path (junctions,
symbolic links and 8.3 short names expanded), the ``\\\\?\\``/``\\\\.\\``/loopback-administrative-share
spellings mapped back to a drive -- lies under the guarded root and outside every allowed root, or when a
parent of the resolved path is *the same directory* (volume serial and file index) as the guarded root
before it meets an allowed root. An existing multiply-linked file on the guarded volume is refused for
in-place content or metadata changes wherever it is named, because its other names are not enumerable.

Refused, each with ``CanonicalWriteRefused`` naming the path and the route:

* opens with any write, append, create, truncate or update flag (``open``, ``Path.write_*``, ``io.FileIO``,
  ``os.open``, ``tempfile``) -- except the identical-bytes whole-file write above;
* delete, rename/replace (as source or destination), directory creation or removal, ``chmod``, ``utime``,
  ``truncate``, hard links to or from a protected file, symbolic links or junctions created under the root,
  ``shutil`` tree operations and archive extraction into it;
* SQLite: a read-write connection to a protected database (only ``file:...?mode=ro`` or ``immutable=1`` URIs
  are read-only), ``ATTACH``/``VACUUM INTO`` of a protected file from any connection, and loading an
  extension (native code with unrestricted writes);
* child processes, unless the child is a Python interpreter that will itself install this guard: same guard
  root, allow list, git scratch roots and log in its environment, this directory on its ``PYTHONPATH``, and no
  ``-I``/``-E``/``-S`` flag. ``git`` is admitted only as an exactly described operation (v37.4): the git
  resolved at installation, found the way CreateProcess would find it; exact global options; a command line
  that parses under the typed grammar of an admitted read-only subcommand, or (v37.5) one of the four writing
  forms inside an explicitly declared git scratch root whose metadata is plain; the controlled git environment
  (:func:`controlled_git_environment`: no system or global configuration, hooks/fsmonitor/pagers/editors/
  signing/credential helpers/submodules/implicit bare repositories neutralized, only the ``file`` transport);
  no other ``GIT_*`` variable; and repository/global configuration files that declare no include, alias,
  filter, textconv/diff command, merge driver, fsmonitor, credential or transport helper. ``os.system``,
  ``os.startfile`` and every other executable are refused while the guard is installed;
* ``ctypes`` lookups of the Win32/NT file-mutation entry points, of ``GetProcAddress`` and (v37.4) of every
  native process-creation entry point (``CreateProcess*``, ``ShellExecute*``, ``WinExec``, the C runtime's
  ``system``/``_spawn*``/``_exec*``/``_popen``);
* when ``BAS_NETWORK_GUARD=DENY_NON_LOOPBACK`` is also set, every name lookup, connect or datagram send to a
  host that is not loopback (``NetworkRefused``). The setting is propagated into Python children exactly like
  the write roots, so an attempt's offline lanes stay offline through their test subprocesses.

What this is not. It is a guard over the Python process tree that installs it, not an operating-system
sandbox. Native code that is already loaded and performs its own I/O (a compiled extension writing through
its own file layer, or a DLL whose load-time code runs before any lookup), a deliberate in-process replacement
of a SQLite connection's authorizer through the base ``sqlite3.Connection`` method, a defect inside git itself,
and any process started outside this tree are not governed by it. An admitted git child is confined by its
command, options, environment and configuration, not by the operating system. The canonical-mounted lanes therefore keep measuring the data root before and
after every run; this guard is the prevention, that measurement is the detection, and neither is claimed as
the other.

Every event is appended as one JSON line to ``BAS_CANONICAL_WRITE_GUARD_LOG``. Without
``BAS_CANONICAL_WRITE_GUARD`` nothing is installed.
"""

from __future__ import annotations

import builtins
import contextlib
import errno
import io
import json
import ntpath
import os
import re
import sys
import threading

GUARD_VERSION = "BAS-CANONICAL-WRITE-GUARD-v37.5"
PREDECESSOR_GUARD_VERSION = "BAS-CANONICAL-WRITE-GUARD-v37.4"

_ROOT = os.environ.get("BAS_CANONICAL_WRITE_GUARD")
_LOG = os.environ.get("BAS_CANONICAL_WRITE_GUARD_LOG")
#: The only network mode: refuse any lookup or connection whose host is not loopback.
NETWORK_DENY = "DENY_NON_LOOPBACK"
_NETWORK = os.environ.get("BAS_NETWORK_GUARD")
_ORIGINAL: dict = {}
_STATE: dict = {"installed": False, "roots": None, "allow": None, "root_ids": (), "allow_ids": (),
                "guard_dir": None, "connection_class": None}
#: Set while the guard itself does I/O (its log, its own reads), so its own events are not re-checked.
_LOCAL = threading.local()

_WRITE_FLAGS = (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
                | getattr(os, "O_TEMPORARY", 0) | getattr(os, "O_EXCL", 0))
#: GENERIC_WRITE, GENERIC_ALL, DELETE, FILE_WRITE_DATA, FILE_APPEND_DATA, FILE_WRITE_EA,
#: FILE_WRITE_ATTRIBUTES, WRITE_DAC and WRITE_OWNER; and the creating/truncating dispositions.
_WIN_WRITE_ACCESS = 0x40000000 | 0x10000000 | 0x00010000 | 0x2 | 0x4 | 0x10 | 0x100 | 0x40000 | 0x80000
_WIN_CREATING_DISPOSITIONS = {1, 2, 4, 5}

#: Win32/NT entry points that create, change, move or delete a file. A ``ctypes`` lookup of one of these
#: while the guard is installed is refused; ``GetProcAddress`` too, because it resolves any of them by name.
_NATIVE_MUTATORS = frozenset(name.casefold() for name in (
    "CreateFileA", "CreateFileW", "CreateFile2", "CreateFileTransactedA", "CreateFileTransactedW",
    "DeleteFileA", "DeleteFileW", "DeleteFileTransactedA", "DeleteFileTransactedW",
    "MoveFileA", "MoveFileW", "MoveFileExA", "MoveFileExW", "MoveFileWithProgressA", "MoveFileWithProgressW",
    "MoveFileTransactedA", "MoveFileTransactedW", "ReplaceFileA", "ReplaceFileW",
    "CopyFileA", "CopyFileW", "CopyFileExA", "CopyFileExW", "CopyFile2", "CopyFileTransactedA",
    "CopyFileTransactedW", "RemoveDirectoryA", "RemoveDirectoryW", "RemoveDirectoryTransactedA",
    "RemoveDirectoryTransactedW", "CreateDirectoryA", "CreateDirectoryW", "CreateDirectoryExA",
    "CreateDirectoryExW", "CreateHardLinkA", "CreateHardLinkW", "CreateSymbolicLinkA", "CreateSymbolicLinkW",
    "SetFileAttributesA", "SetFileAttributesW", "SetFileInformationByHandle", "SetFileTime", "SetEndOfFile",
    "SetFileValidData", "WriteFile", "WriteFileEx", "WriteFileGather", "DeviceIoControl",
    "SHFileOperationA", "SHFileOperationW", "NtCreateFile", "NtOpenFile", "NtWriteFile",
    "NtSetInformationFile", "NtDeleteFile", "NtFsControlFile", "ZwCreateFile", "ZwOpenFile", "ZwWriteFile",
    "ZwSetInformationFile", "ZwDeleteFile", "ZwFsControlFile", "GetProcAddress", "LdrGetProcedureAddress",
    # v37.4: every native route that starts a process. A child started this way would never pass the child
    # check, so the lookup itself is refused (MF37A03-01: deny native children that are not confined).
    "CreateProcessA", "CreateProcessW", "CreateProcessAsUserA", "CreateProcessAsUserW",
    "CreateProcessWithLogonW", "CreateProcessWithTokenW", "CreateProcessInternalA", "CreateProcessInternalW",
    "NtCreateUserProcess", "NtCreateProcess", "NtCreateProcessEx", "ZwCreateUserProcess", "ZwCreateProcess",
    "ZwCreateProcessEx", "RtlCreateUserProcess", "RtlCreateUserProcessEx", "WinExec", "LoadModule",
    "ShellExecuteA", "ShellExecuteW", "ShellExecuteExA", "ShellExecuteExW", "system", "_system", "_wsystem",
    "_popen", "_wpopen",
    *(f"{prefix}{verb}{suffix}" for prefix in ("_", "_w") for verb in ("spawn", "exec")
      for suffix in ("l", "le", "lp", "lpe", "v", "ve", "vp", "vpe")),
))
_PYTHON_NAME = re.compile(r"^(python|pythonw)(\d+(\.\d+)?)?(_d)?(\.exe)?$", re.IGNORECASE)
_LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]", "0:0:0:0:0:0:0:1", "."}
_SQLITE_ATTACH = 24


class CanonicalWriteRefused(OSError):
    """A write the guard refused. Deliberately not a PermissionError: on Windows tempfile.mkstemp retries a
    PermissionError up to os.TMP_MAX times, so refusing with one would hang any temporary file under the root."""


class NetworkRefused(OSError):
    """A non-loopback lookup or connection refused in an offline lane."""


def _loopback_host(host) -> bool:
    """True for loopback or local-only hosts; a name that could resolve anywhere else is not loopback."""

    if host is None:
        return True
    if isinstance(host, (bytes, bytearray)):
        host = bytes(host).decode("ascii", "replace")
    text = str(host).strip().strip("[]").casefold()
    if text in ("", "localhost", "localhost.", "ip6-localhost"):
        return True
    import ipaddress

    try:
        return ipaddress.ip_address(text.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _network_address_host(address):
    """The host of a socket address; a non-tuple address (an AF_UNIX path) is local by construction."""

    if isinstance(address, tuple) and address:
        return address[0]
    return None


def _loopback_names() -> set[str]:
    names = set(_LOOPBACK)
    for key in ("COMPUTERNAME", "USERDOMAIN_ROAMINGPROFILE"):
        value = os.environ.get(key)
        if value:
            names.add(value.casefold())
    return names


def _text(path) -> str | None:
    """A filesystem path as text, or None for a file descriptor or an unusable object."""

    if path is None or isinstance(path, int):
        return None
    try:
        return os.fsdecode(os.fspath(path))
    except (TypeError, ValueError):
        return None


def _drive_form(text: str) -> str:
    """Map the ``\\\\?\\``, ``\\\\.\\`` and loopback administrative-share spellings back to a drive path."""

    value = text.replace("/", "\\")
    for prefix in ("\\\\?\\UNC\\", "\\??\\UNC\\"):
        if value.upper().startswith(prefix):
            value = "\\\\" + value[len(prefix):]
    for prefix in ("\\\\?\\", "\\\\.\\", "\\??\\"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    if value.startswith("\\\\"):
        parts = value[2:].split("\\")
        if len(parts) >= 2 and parts[0].casefold() in _loopback_names() and re.fullmatch(r"[A-Za-z]\$", parts[1]):
            value = parts[1][0] + ":\\" + "\\".join(parts[2:])
    return value


def _forms(text: str) -> set[str]:
    """Every comparable spelling of a path: literal absolute and fully resolved, both case-normalized."""

    literal = _drive_form(text)
    forms = {os.path.normcase(os.path.abspath(literal))}
    try:
        resolved = os.path.realpath(literal)
        forms.add(os.path.normcase(os.path.abspath(_drive_form(resolved))))
    except (OSError, ValueError):
        pass
    return forms


def _under(base: str, path: str) -> bool:
    return path == base or path.startswith(base.rstrip("\\/") + os.sep)


def _inside(base: str, path: str) -> bool:
    """Strictly inside ``base``: an allowed root's contents are writable, the root's own entry is not."""

    return path != base and path.startswith(base.rstrip("\\/") + os.sep)


def _identity(path: str):
    try:
        stat = os.stat(path)
    except (OSError, ValueError):
        return None
    if not stat.st_ino:
        return None
    return (stat.st_dev, stat.st_ino)


def _identity_verdict(text: str) -> str | None:
    """Walk the resolved path's existing parents by file identity: ALLOW, PROTECT or None (no verdict)."""

    root_ids = _STATE["root_ids"]
    if not root_ids:
        return None
    try:
        current = os.path.realpath(_drive_form(text))
    except (OSError, ValueError):
        return None
    # Allowed roots are re-identified on every check: one created after installation (a lane's own output
    # directory) must still be recognized when the walk reaches it.
    allow_ids = set(_STATE["allow_ids"]) | {i for i in (_identity(a) for a in _settings()[1]) if i is not None}
    for depth in range(256):
        identity = _identity(current)
        if identity is not None:
            # Only an allowed root's *contents* are writable, so the target itself matching one is no allowance.
            if depth and identity in allow_ids:
                return "ALLOW"
            if identity in root_ids:
                return "PROTECT"
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
    return None


def protected(path) -> bool:
    """True for a path under the guarded root and outside every allowed root, by name or by identity."""

    if not _ROOT:
        return False
    text = _text(path)
    if text is None:
        return False
    roots, allow = _settings()
    for form in _forms(text):
        if any(_under(root, form) for root in roots) and not any(_inside(a, form) for a in allow):
            return True
    return _identity_verdict(text) == "PROTECT"


# ``guarded`` is the v37.2 name; callers and tests that used it keep working.
guarded = protected


def _root_forms(value: str) -> tuple[str, ...]:
    literal = os.path.normcase(os.path.abspath(_drive_form(value)))
    try:
        resolved = os.path.normcase(os.path.abspath(_drive_form(os.path.realpath(_drive_form(value)))))
    except (OSError, ValueError):
        resolved = literal
    return tuple(dict.fromkeys((literal, resolved)))


def _split_roots(value: str | None) -> list[str]:
    return [part for part in (value or "").split(os.pathsep) if part.strip()]


def _settings() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(guarded root forms, allowed root forms). ``BAS_CANONICAL_WRITE_GUARD`` may name several roots."""

    if _STATE["roots"] is not None:
        return _STATE["roots"], _STATE["allow"]
    roots = tuple(dict.fromkeys(form for root in _split_roots(_ROOT) for form in _root_forms(root)))
    allow = tuple(dict.fromkeys(form for a in _split_roots(os.environ.get("BAS_CANONICAL_WRITE_ALLOW"))
                                for form in _root_forms(a)))
    return roots, allow


def _multiply_linked_on_guarded_volume(path) -> bool:
    text = _text(path)
    volumes = {identity[0] for identity in _STATE["root_ids"]}
    if text is None or not volumes:
        return False
    try:
        stat = os.stat(text)
    except (OSError, ValueError):
        return False
    return bool(stat.st_nlink and stat.st_nlink > 1 and stat.st_dev in volumes and not os.path.isdir(text))


def _log(event: str, operation: str, path, detail: str = "") -> None:
    if not _LOG:
        return
    record = {"event": event, "operation": operation, "path": _text(path) if _text(path) is not None else path,
              "pid": os.getpid(), "argv0": (sys.argv[0] if sys.argv else ""), "detail": detail,
              "guard_version": GUARD_VERSION}
    opener = _ORIGINAL.get("open", io.open)
    previous = getattr(_LOCAL, "busy", False)
    _LOCAL.busy = True
    try:
        with opener(_LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    except OSError:
        pass
    finally:
        _LOCAL.busy = previous


def _refuse(operation: str, path, detail: str = "") -> None:
    _log("BLOCKED", operation, path, detail)
    shown = _text(path)
    raise CanonicalWriteRefused(errno.EROFS, f"BAS canonical write guard: {operation} refused under the guarded root"
                                + (f" ({detail})" if detail else ""), shown if shown is not None else str(path))


def _existing(path) -> bytes | None:
    try:
        with _ORIGINAL["open"](path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def _settle(path, data: bytes, operation: str) -> None:
    """Skip a whole-file write whose bytes are already there; refuse any other."""

    existing = _existing(path)
    if existing == data:
        _log("SKIPPED_IDENTICAL", operation, path, f"{len(data)} bytes")
        return
    _refuse(operation, path, "the bytes differ from the existing file" if existing is not None
            else "the file does not exist")


class _Capture(io.BytesIO):
    """A whole-file write held in memory and settled against the existing bytes on close."""

    def __init__(self, path, operation: str) -> None:
        super().__init__()
        self._bas_path = path
        self._bas_operation = operation
        self._bas_settled = False
        self.name = _text(path)
        self.mode = "wb"

    def close(self) -> None:
        if not self._bas_settled and not self.closed:
            self._bas_settled = True
            data = self.getvalue()
            super().close()
            _settle(self._bas_path, data, self._bas_operation)
            return
        super().close()


def _open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if isinstance(mode, str) and any(flag in mode for flag in "wax+") and protected(file):
        if "a" in mode or "x" in mode or "+" in mode:
            _refuse(f"open(mode={mode!r})", file)
        capture = _Capture(file, f"open(mode={mode!r})")
        if "b" in mode:
            return capture
        return io.TextIOWrapper(capture, encoding=encoding, errors=errors, newline=newline, write_through=True)
    return _ORIGINAL["open"](file, mode, buffering, encoding, errors, newline, closefd, opener)


def _replace_like(name):
    def replace(src, dst, *args, **kwargs):
        if not protected(src) and protected(dst):
            data = _existing(src)
            if data is not None and _existing(dst) == data:
                _log("SKIPPED_IDENTICAL", f"os.{name}", dst, f"{len(data)} bytes")
                _ORIGINAL["os.unlink"](src)
                return None
        return _ORIGINAL[f"os.{name}"](src, dst, *args, **kwargs)
    return replace


# ---------------------------------------------------------------- SQLite


def _sqlite_target(database) -> tuple[str | None, bool]:
    """(filesystem path or None for memory/temporary, read_only) for a sqlite3.connect database argument."""

    if isinstance(database, (bytes, bytearray)):
        database = os.fsdecode(bytes(database))
    text = _text(database)
    if text is None or text in ("", ":memory:"):
        return None, False
    if text.startswith("file:"):
        from urllib.parse import parse_qs, unquote

        body, _, query = text[5:].partition("?")
        params = {k.lower(): [v.lower() for v in vals] for k, vals in parse_qs(query).items()}
        read_only = "ro" in params.get("mode", []) or any(v in ("1", "true", "yes", "on")
                                                            for v in params.get("immutable", []))
        if "memory" in params.get("mode", []) or body in ("", ":memory:"):
            return None, False
        path = unquote(body)
        if path.startswith("///"):
            path = path[3:]
        elif path.startswith("//"):
            host, _, rest = path[2:].partition("/")
            path = rest if host.casefold() in ("", "localhost") else "\\\\" + host + "\\" + rest
        if re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
        return path, read_only
    return text, False


def _authorizer(action, arg1, arg2, database, trigger):
    if action == _SQLITE_ATTACH:
        if not arg1:
            # SQLite passes no filename when it is an expression or a bound parameter, so the target cannot
            # be checked; an unverifiable attach is denied rather than assumed harmless.
            _log("BLOCKED", "sqlite ATTACH", "<non-literal filename>", "attach target is not a literal")
            return 1  # SQLITE_DENY
        path, read_only = _sqlite_target(arg1)
        if path is not None and not read_only and protected(path):
            _log("BLOCKED", "sqlite ATTACH/VACUUM INTO", path, "read-write attach of a protected database")
            return 1  # SQLITE_DENY
    return 0  # SQLITE_OK


def _composed_authorizer(user_callback):
    def authorize(action, arg1, arg2, database, trigger):
        verdict = _authorizer(action, arg1, arg2, database, trigger)
        if verdict != 0 or user_callback is None:
            return verdict
        return user_callback(action, arg1, arg2, database, trigger)
    return authorize


def _guarded_connection_class():
    import sqlite3

    class GuardedConnection(sqlite3.Connection):
        """A connection whose ``set_authorizer`` composes the caller's callback after the guard's."""

        def set_authorizer(self, authorizer_callback):  # noqa: D401 - sqlite3 API name
            return super().set_authorizer(_composed_authorizer(authorizer_callback))

    return GuardedConnection


def _sqlite_connect(database, *args, **kwargs):
    path, read_only = _sqlite_target(database)
    if path is not None and not read_only and protected(path):
        _refuse("sqlite3.connect(read-write)", path,
                "open a protected database with a file: URI and mode=ro or immutable=1")
    if len(args) >= 5 or kwargs.get("factory") not in (None, _STATE["connection_class"]):
        _refuse("sqlite3.connect(factory)", path or "<database>",
                "a caller-supplied connection factory cannot carry the guard's ATTACH authorizer")
    kwargs["factory"] = _STATE["connection_class"]
    connection = _ORIGINAL["sqlite3.connect"](database, *args, **kwargs)
    # The authorizer is installed here, after construction: CPython raises sqlite3.connect/handle before the
    # connection is initialized, so the hook can only check that this path produced the connection.
    connection.set_authorizer(None)
    return connection


# ---------------------------------------------------------- child processes


def _split_command_line(text: str) -> list[str]:
    """Split a Windows command line exactly as the C runtime (and git.exe) will: the inverse of
    ``subprocess.list2cmdline``. 2n backslashes before a quote are n backslashes and a quote toggle; 2n+1 are
    n backslashes and a literal quote; ``""`` inside quotes is a literal quote; other backslashes are literal."""

    args: list[str] = []
    current: list[str] = []
    in_quotes = False
    started = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\":
            run = 0
            while index < len(text) and text[index] == "\\":
                run += 1
                index += 1
            if index < len(text) and text[index] == '"':
                current.append("\\" * (run // 2))
                if run % 2:
                    current.append('"')
                    index += 1
                started = True
                continue
            current.append("\\" * run)
            started = True
            continue
        if char == '"':
            if in_quotes and index + 1 < len(text) and text[index + 1] == '"':
                current.append('"')
                index += 2
                continue
            in_quotes = not in_quotes
            started = True
            index += 1
            continue
        if char in " \t" and not in_quotes:
            if started:
                args.append("".join(current))
                current, started = [], False
            index += 1
            continue
        current.append(char)
        started = True
        index += 1
    if started:
        args.append("".join(current))
    return args


def _argv(args) -> list[str]:
    if args is None:
        return []
    if isinstance(args, (str, bytes)):
        return _split_command_line(os.fsdecode(args))
    try:
        return [os.fsdecode(os.fspath(a)) if not isinstance(a, str) else a for a in args]
    except TypeError:
        return [str(a) for a in args]


def _child_environment(env) -> dict:
    if env is None:
        return dict(os.environ)
    try:
        return {os.fsdecode(k): os.fsdecode(v) for k, v in dict(env).items()}
    except (TypeError, ValueError):
        return {}


def _env_get(env: dict, key: str) -> str | None:
    for name, value in env.items():
        if name.upper() == key:
            return value
    return None


def _disabling_interpreter_flag(argv: list[str]) -> str | None:
    """The first interpreter flag that would stop the child importing sitecustomize from PYTHONPATH."""

    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--" or arg == "-" or not arg.startswith("-"):
            return None
        if arg.startswith("--"):
            index += 2 if arg == "--check-hash-based-pycs" else 1
            continue
        body = arg[1:]
        skip_next = False
        for position, flag in enumerate(body):
            if flag in "IES":
                return arg
            if flag in "cm":
                return None
            if flag in "XW":
                skip_next = position == len(body) - 1
                break
        index += 2 if skip_next else 1
    return None


def _env_key(env, key: str) -> str:
    for name in list(env.keys()):
        if str(name).upper() == key:
            return name
    return key


def _python_child_reinstalls_guard(argv: list[str], env) -> tuple[bool, str]:
    """Admit a Python child only when it will install this guard over at least the same roots.

    ``env`` is the mapping ``subprocess.Popen`` will hand to CreateProcess, or ``None`` for an inherited
    environment. When it is a caller-built mapping that dropped or narrowed the guard -- the common test
    idiom ``env = dict(os.environ); env["PYTHONPATH"] = src`` -- the guard is *propagated* into it rather than
    the launch refused: this process's roots are added to the child's, this process's allowed roots are
    added to the child's, and the guard directory is put first on the child's ``PYTHONPATH``. A child may
    guard more (a test's own temporary root) but never less: an allowed root that would open a path this
    process protects is refused, as is an interpreter flag that disables ``PYTHONPATH`` or ``site``.
    """

    flag = _disabling_interpreter_flag(argv)
    if flag:
        return False, f"interpreter flag {flag} disables PYTHONPATH or site, so the guard would not load"
    guard_dir = _STATE["guard_dir"]
    inherited = env is None
    mapping = os.environ if inherited else env
    try:
        child_roots = _split_roots(_env_get(dict(mapping), "BAS_CANONICAL_WRITE_GUARD"))
        child_allow = _split_roots(_env_get(dict(mapping), "BAS_CANONICAL_WRITE_ALLOW"))
        python_path = [p for p in (_env_get(dict(mapping), "PYTHONPATH") or "").split(os.pathsep) if p]
    except (TypeError, ValueError):
        return False, "the child environment is not a readable mapping"
    for entry in child_allow:
        # The child may allow a directory only if this process would already allow writing inside it.
        if protected(os.path.join(entry, "__bas_guard_allow_probe__")):
            return False, f"the child would allow {entry!r}, which this process protects"
    own_roots = _split_roots(_ROOT)
    own_allow = _split_roots(os.environ.get("BAS_CANONICAL_WRITE_ALLOW"))
    covered = {form for root in child_roots for form in _root_forms(root)}
    missing_roots = [root for root in own_roots if _root_forms(root)[0] not in covered]
    missing_allow = [a for a in own_allow if a not in child_allow]
    first_is_guard = bool(python_path) and os.path.normcase(os.path.abspath(python_path[0])) == guard_dir
    # An offline process's children stay offline: the network setting is never narrowed or dropped.
    network_kept = not _NETWORK or _env_get(dict(mapping), "BAS_NETWORK_GUARD") == _NETWORK
    # A child may build git scratch repositories only where this process may (v37.4); it may narrow, never widen.
    own_scratch = _split_roots(os.environ.get("BAS_CANONICAL_WRITE_GIT_SCRATCH"))
    child_scratch = _split_roots(_env_get(dict(mapping), "BAS_CANONICAL_WRITE_GIT_SCRATCH"))
    for entry in child_scratch:
        if entry not in own_scratch and not _in_scratch(os.path.join(entry, "__bas_guard_scratch_probe__")):
            return False, f"the child would build git repositories in {entry!r}, outside this process's scratch roots"
    scratch_kept = bool(child_scratch) or not own_scratch
    if not missing_roots and not missing_allow and first_is_guard and network_kept and scratch_kept:
        return True, "Python child re-installs the guard from its environment"
    if inherited:
        return False, "this process's own environment no longer carries the guard, so an inherited child would not"
    try:
        if not network_kept:
            mapping[_env_key(mapping, "BAS_NETWORK_GUARD")] = _NETWORK
        if not scratch_kept:
            mapping[_env_key(mapping, "BAS_CANONICAL_WRITE_GIT_SCRATCH")] = os.pathsep.join(own_scratch)
        mapping[_env_key(mapping, "BAS_CANONICAL_WRITE_GUARD")] = os.pathsep.join(child_roots + missing_roots)
        if child_allow or missing_allow:
            mapping[_env_key(mapping, "BAS_CANONICAL_WRITE_ALLOW")] = os.pathsep.join(child_allow + missing_allow)
        if not _env_get(dict(mapping), "BAS_CANONICAL_WRITE_GUARD_LOG") and _LOG:
            mapping[_env_key(mapping, "BAS_CANONICAL_WRITE_GUARD_LOG")] = _LOG
        if not first_is_guard:
            mapping[_env_key(mapping, "PYTHONPATH")] = os.pathsep.join([os.path.dirname(os.path.abspath(__file__))]
                                                                       + python_path)
    except TypeError:
        return False, "the child environment is immutable and does not carry the guard"
    return True, (f"guard propagated into the child environment (added roots {missing_roots}, allowed "
                  f"{missing_allow}, guard first on PYTHONPATH: {not first_is_guard}, network setting "
                  f"restored: {not network_kept})")


# ------------------------------------------------------------- git children (v37.5, MF37A04-01)
#
# v37.3 admitted any ``git`` whose path-shaped arguments stayed outside the guarded root; v37.4 (MF37A03-01) added
# the controlled environment, configuration scanning and trusted-program resolution below, but still judged
# options by *scanning* them for forbidden names and letters, and treated every argument that did not begin with a
# dash as a possible path. The Attempt #4 manager ran ``git config -f../p/x fixture.value CHANGED`` in a
# repository inside the declared Git scratch root: a scratch ``config`` write whose file option, attached to its
# flag, was never read as a path -- and it rewrote a protected file. v37.5 parses every git command line with a
# typed grammar instead of scanning it:
#
# * each admitted subcommand declares its exact options -- a flag, or an option whose value has a declared type
#   (revision, pathspec, format, integer, enumeration, text, path, configuration key or value, commit message) --
#   and its positional arguments by type. An option git would accept as an abbreviation is not that option; an
#   undeclared option, short-option letter, positional or ``--`` is refused before the child starts;
# * git itself writes through four forms only: ``init``, ``config <declared key> <value>``, ``add`` and
#   ``commit``. v37.5 no longer defaults the Git scratch root to TEMP: a guarded process runs a native Git write
#   only where its lane declared ``BAS_CANONICAL_WRITE_GIT_SCRATCH``. Every repository path -- work tree, git and
#   common directories, index, object directory, a ``.git`` file's target, an ``init`` target -- must lie inside
#   that root by its literal *and* its resolved spelling and outside every protected root, and the repository's
#   metadata may contain no reparse point and no multiply-linked file, either of which would carry git's own
#   writes elsewhere. A configuration write never names a file: ``-f``/``--file``, ``--blob``, ``--global``,
#   ``--system`` and ``--worktree`` are not in the grammar, and only a declared key may be written;
# * the fixture repositories that tests and lanes read are built before the guard is installed.
#
# The environment, configuration-scanning and program-resolution rules of v37.4 are unchanged. This confines git
# to reading and to building owned scratch repositories; it is not operating-system isolation.

_GIT_GLOBAL_FLAGS = frozenset(("--no-pager", "--no-optional-locks", "--no-replace-objects", "--literal-pathspecs",
                               "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs", "--no-advice"))
_GIT_GLOBAL_PATH_OPTIONS = ("--git-dir", "--work-tree")
#: ``-c`` keys that only shape how data is read or written. Their values must be literal.
_GIT_SAFE_CONFIG_KEYS = frozenset(("core.quotepath", "color.ui", "core.autocrlf", "core.safecrlf", "core.eol",
                                   "core.longpaths", "safe.directory", "gc.auto", "maintenance.auto", "user.name",
                                   "user.email", "init.defaultbranch", "i18n.logoutputencoding",
                                   "i18n.commitencoding"))
_GIT_FALSE_ONLY_KEYS = frozenset(("core.fsmonitor", "log.showsignature", "commit.gpgsign", "tag.gpgsign"))
#: The keys of git's own sections that ``git config <key> <value>`` may write inside a scratch repository:
#: identity and data shaping only.
_GIT_WRITABLE_CONFIG_KEYS = frozenset(("user.name", "user.email", "core.autocrlf", "core.safecrlf", "core.eol",
                                       "core.longpaths", "core.quotepath", "core.filemode", "core.ignorecase",
                                       "init.defaultbranch", "gc.auto", "maintenance.auto", "i18n.commitencoding",
                                       "i18n.logoutputencoding", "color.ui", "commit.gpgsign", "tag.gpgsign"))
#: The configuration sections git (and git-lfs) define. A key in one of these sections is written only if it is
#: declared above; a key in a section git does not define (``fixture.owned``) is inert data to git and is admitted.
_GIT_KNOWN_SECTIONS = frozenset((
    "add", "advice", "alias", "am", "apply", "attr", "author", "bitmappseudomerge", "blame", "branch", "browser",
    "bundle", "checkout", "clean", "clone", "color", "column", "commit", "commitgraph", "committer", "completion",
    "core", "credential", "diff", "difftool", "extensions", "fastimport", "feature", "fetch", "filter", "format",
    "fsck", "fsmonitor", "gc", "gitcvs", "gitweb", "gpg", "grep", "gui", "guitool", "help", "http", "https", "i18n",
    "imap", "include", "includeif", "index", "init", "instaweb", "interactive", "lfs", "log", "lsrefs", "mailinfo",
    "mailmap", "maintenance", "man", "merge", "mergetool", "notes", "pack", "pager", "pretty", "promisor",
    "protocol", "pull", "push", "rebase", "receive", "reftable", "remote", "remotes", "repack", "rerere", "revert",
    "safe", "sendemail", "sendpack", "sequence", "showbranch", "sparse", "splitindex", "ssh", "stash", "status",
    "submodule", "tag", "tar", "trace2", "trailer", "transfer", "uploadarchive", "uploadpack", "url", "user",
    "versionsort", "web", "worktree"))
#: Long options that run a program, write a file, open an editor or pager, reach another repository or verify
#: signatures. None is in the grammar; the list only names *why* a refused option (or an abbreviation of it) is
#: refused, so a negative control can show it reached its own cause.
_GIT_HAZARD_LONG = ("--output", "--ext-diff", "--textconv", "--show-signature", "--open-files-in-pager", "--filters",
                    "--remote", "--exec", "--upload-pack", "--receive-pack", "--paginate", "--edit", "--template",
                    "--config-env", "--exec-path", "--gpg-sign", "--verify-signatures", "--interactive", "--patch",
                    "--separate-git-dir", "--recurse-submodules")
#: Short options with the same effect, per subcommand (``-O`` opens files in a pager; ``-e`` edits; ``-S`` signs;
#: ``-p``/``-i`` are interactive for add; ``-w`` writes an object).
_GIT_HAZARD_SHORT = {"grep": "O", "config": "e", "commit": "Se", "add": "pie", "hash-object": "w"}
#: ``git config`` options that name a configuration file other than the command's own repository's, or write.
_GIT_CONFIG_FILE_OPTIONS = ("--file", "--blob", "--global", "--system", "--worktree")
_GIT_CONFIG_WRITE_ACTIONS = ("--add", "--unset", "--unset-all", "--replace-all", "--rename-section",
                             "--remove-section", "--edit", "--comment")
#: Formats that make git call a signature program.
_GIT_SIGNATURE_FORMAT = re.compile(r"%G|%\(signature", re.IGNORECASE)
#: ``GIT_*`` variables that describe identity, dates or pathspec behaviour, and repository paths the policy
#: checks itself. Any other ``GIT_*`` variable (GIT_EXTERNAL_DIFF, GIT_SSH_COMMAND, GIT_TRACE*, GIT_CONFIG,
#: GIT_CONFIG_SYSTEM, GIT_REDIRECT_*, GIT_CONFIG_PARAMETERS, GIT_EXEC_PATH, GIT_TEMPLATE_DIR, ...) refuses the launch.
_GIT_BENIGN_ENV = frozenset(("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE", "GIT_COMMITTER_NAME",
                             "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE", "GIT_FLUSH", "GIT_CEILING_DIRECTORIES",
                             "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS",
                             "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS", "GIT_NO_REPLACE_OBJECTS",
                             "GIT_DEFAULT_HASH", "GIT_ADVICE", "GIT_MERGE_VERBOSITY"))
_GIT_PATH_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")
_GIT_PATH_ENV_READ_ONLY = ("GIT_ALTERNATE_OBJECT_DIRECTORIES",)
#: Configuration the command-scope values cannot neutralize by name, so its presence refuses the launch.
_GIT_REFUSED_CONFIG = (
    (re.compile(r"^include\.|^includeif\."), "configuration include (indirection to an unscanned file)"),
    (re.compile(r"^alias\."), "alias"),
    (re.compile(r"^filter\..+\.(clean|smudge|process)$"), "filter driver program"),
    (re.compile(r"^diff\..+\.(textconv|command)$|^diff\.external$"), "diff or textconv program"),
    (re.compile(r"^merge\..+\.driver$"), "merge driver program"),
    (re.compile(r"^credential\."), "credential helper"),
    (re.compile(r"^core\.(sshcommand|gitproxy|askpass|alternaterefscommand)$"), "transport or prompt program"),
    (re.compile(r"^remote\..+\.(uploadpack|receivepack|vcs|proxy)$"), "transport program"),
    (re.compile(r"^uploadpack\.packobjectshook$"), "pack-objects hook"),
)
_GIT_FALSEY = frozenset(("false", "no", "off", "0", ""))
_GIT_SECTION = re.compile(r'^\s*\[\s*([A-Za-z0-9.-]+)(?:\s+"((?:[^"\\]|\\.)*)")?\s*\]')
_GIT_KEY = re.compile(r"^\s*([A-Za-z][A-Za-z0-9-]*)\s*(?:=(.*))?$")
#: Repository metadata larger than this is not walked; a write there is refused rather than assumed safe.
_GIT_METADATA_WALK_LIMIT = 50000


# ---- the typed grammar ------------------------------------------------------------------------------------------

_FLAG, _VALUE, _OPTIONAL = "FLAG", "VALUE", "OPTIONAL"
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_ENUMS = {
    "PORCELAIN": frozenset(("v1", "v2")), "UNTRACKED": frozenset(("all", "no", "normal")),
    "IGNORED": frozenset(("traditional", "matching", "no")), "PATH_FORMAT": frozenset(("absolute", "relative")),
    "ABBREV_REF": frozenset(("strict", "loose")), "OBJECT_TYPE": frozenset(("blob", "tree", "commit", "tag")),
    "OBJECT_FORMAT": frozenset(("sha1", "sha256")),
    "CONFIG_TYPE": frozenset(("bool", "int", "bool-or-int", "path", "expiry-date", "color", "bool-or-str")),
    "SUBMODULES": frozenset(("none", "untracked", "dirty", "all")),
}


def _type_problem(kind: str, value: str | None) -> str | None:
    """None when ``value`` is a well-formed argument of ``kind``; otherwise why it is not."""

    if value is None:
        return f"a {kind} value is required"
    if kind in _ENUMS:
        return None if value in _ENUMS[kind] else f"{value!r} is not one of {sorted(_ENUMS[kind])}"
    if kind == "MESSAGE":
        return "a commit message may not contain NUL" if "\x00" in value else None
    if _CONTROL.search(value):
        return f"{value!r} contains a control character"
    if kind == "INT":
        return None if re.fullmatch(r"\d{1,9}", value) else f"{value!r} is not a nonnegative integer"
    if kind == "FORMAT":
        if _GIT_SIGNATURE_FORMAT.search(value):
            return f"{value!r} asks git to verify a signature with an external program"
        return None if len(value) <= 2048 else "format longer than 2048 characters"
    if kind == "DIFF_FILTER":
        return None if re.fullmatch(r"[ACDMRTUXBacdmrtuxb*]+", value) else f"{value!r} is not a diff filter"
    if kind == "NAME":
        return None if re.fullmatch(r"(?!-)[A-Za-z0-9._/+-]{1,200}", value) else f"{value!r} is not a plain name"
    if kind == "VAR":
        return None if re.fullmatch(r"GIT_[A-Z_]{1,64}", value) else f"{value!r} is not a git variable name"
    if kind == "CONFIG_KEY":
        return None if re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*(?:\.[^=\s][^=]*)?", value) else f"{value!r} is not a key"
    if kind == "CONFIG_VALUE":
        if value.startswith("!"):
            return f"{value!r} begins with '!' (a shell command in some keys)"
        return None if len(value) <= 256 else "configuration value longer than 256 characters"
    if kind in ("REV", "PATHSPEC", "PATH", "TEXT", "PATTERN"):
        if kind in ("REV", "PATHSPEC", "PATH") and value.startswith("-"):
            return f"{value!r} begins with '-' where a {kind.lower()} is expected"
        return None if len(value) <= 4096 else f"{kind.lower()} longer than 4096 characters"
    return f"unknown argument type {kind}"


class _Opt:
    __slots__ = ("kind", "type", "separate", "joined")

    def __init__(self, kind: str, type_: str | None = None, *, separate: bool = True, joined: bool = True) -> None:
        self.kind, self.type, self.separate, self.joined = kind, type_, separate, joined


def _flags(*names: str) -> dict:
    return {name: _Opt(_FLAG) for name in names}


def _values(type_: str, *names: str, separate: bool = True, joined: bool = True) -> dict:
    return {name: _Opt(_VALUE, type_, separate=separate, joined=joined) for name in names}


def _optional(type_: str, *names: str) -> dict:
    """An option with an optional value: attached only (``--opt=value``, or ``-xVALUE`` for a short one)."""

    return {name: _Opt(_OPTIONAL, type_, separate=False) for name in names}


class _Spec:
    __slots__ = ("options", "positional", "minimum", "maximum", "dashdash", "writes", "check")

    def __init__(self, options: dict, positional: str | None = None, minimum: int = 0, maximum: int | None = 0,
                 dashdash: str | None = None, writes: bool = False, check=None) -> None:
        self.options, self.positional, self.minimum, self.maximum = options, positional, minimum, maximum
        self.dashdash, self.writes, self.check = dashdash, writes, check


def _has(parsed: dict, *names: str) -> bool:
    return any(name in parsed["options"] for name in names)


def _check_config(parsed: dict) -> tuple[str | None, bool]:
    """``git config`` reads by an explicit action, or writes exactly ``<declared key> <value>`` with no option."""

    positionals, options = parsed["positionals"], parsed["options"]
    if positionals[:1] in (["set"], ["unset"], ["rename-section"], ["remove-section"], ["edit"]):
        return "git config write form (only `config <declared key> <value>` may write)", False
    if positionals[:1] == ["get"]:
        rest = positionals[1:]
        return (None if len(rest) == 1 and not _type_problem("CONFIG_KEY", rest[0])
                else "git config get takes one key"), False
    if positionals[:1] == ["list"]:
        return (None if len(positionals) == 1 else "git config list takes no argument"), False
    if _has(parsed, "--get", "--get-all", "--get-regexp"):
        ok = 1 <= len(positionals) <= 2 and not _type_problem("CONFIG_KEY", positionals[0])
        return (None if ok else "git config --get takes a key and an optional value pattern"), False
    if _has(parsed, "--list", "-l"):
        return (None if not positionals else "git config --list takes no argument"), False
    if len(positionals) == 1:
        return _type_problem("CONFIG_KEY", positionals[0]), False
    if len(positionals) == 2:
        if options:
            return f"git config write form with options {sorted(options)} (the write form takes none)", True
        key = positionals[0].lower()
        problem = _type_problem("CONFIG_KEY", positionals[0])
        if problem:
            return f"git config key: {problem}", True
        if key.split(".", 1)[0] in _GIT_KNOWN_SECTIONS and key not in _GIT_WRITABLE_CONFIG_KEYS:
            return (f"git config key {positionals[0]!r} is not a declared write key of git's own sections "
                    f"({sorted(_GIT_WRITABLE_CONFIG_KEYS)})"), True
        if key in ("commit.gpgsign", "tag.gpgsign") and positionals[1].lower() not in _GIT_FALSEY:
            return f"git config {positionals[0]}={positionals[1]!r} would run a signing program", True
        return _type_problem("CONFIG_VALUE", positionals[1]), True
    return "git config with no key, or more than two arguments", False


def _check_branch(parsed: dict) -> tuple[str | None, bool]:
    if parsed["positionals"] and not _has(parsed, "--list", "-l"):
        return "git branch with a name creates a branch", False
    return None, False


def _check_symbolic_ref(parsed: dict) -> tuple[str | None, bool]:
    if len(parsed["positionals"]) != 1:
        return "git symbolic-ref write form", False
    return _type_problem("NAME", parsed["positionals"][0]), False


def _check_worktree(parsed: dict) -> tuple[str | None, bool]:
    return (None if parsed["positionals"] == ["list"] else "git worktree other than list"), False


def _check_remote(parsed: dict) -> tuple[str | None, bool]:
    positionals = parsed["positionals"]
    if not positionals and not _has(parsed, "--all", "--push"):
        return None, False
    if len(positionals) == 2 and positionals[0] == "get-url" and not _type_problem("NAME", positionals[1]):
        return None, False
    return "git remote other than listing or get-url", False


def _check_cat_file(parsed: dict) -> tuple[str | None, bool]:
    positionals = parsed["positionals"]
    modes = [name for name in ("-t", "-s", "-e", "-p") if name in parsed["options"]]
    batch = _has(parsed, "--batch", "--batch-check")
    if batch:
        return (None if not positionals and not modes else "git cat-file --batch takes no object argument"), False
    if len(modes) == 1:
        return (None if len(positionals) == 1 else "git cat-file -t/-s/-e/-p takes one object"), False
    if not modes and len(positionals) == 2 and positionals[0] in _ENUMS["OBJECT_TYPE"]:
        return None, False
    return "git cat-file needs exactly one of -t/-s/-e/-p with one object, a type and an object, or --batch", False


def _check_ls_tree(parsed: dict) -> tuple[str | None, bool]:
    return (None if parsed["positionals"] else "git ls-tree needs a tree-ish"), False


def _check_writes(parsed: dict) -> tuple[str | None, bool]:
    return None, True


_DIFF_READ = {**_flags("--name-only", "--name-status", "--stat", "--numstat", "--shortstat", "--no-renames", "-z",
                       "--no-ext-diff", "--no-textconv", "--no-color", "--raw", "--summary", "-p", "-s",
                       "--no-patch", "-w", "--ignore-all-space", "--ignore-space-at-eol", "--ignore-blank-lines",
                       "-R", "--full-index", "--binary", "--abbrev", "--no-abbrev"),
              **_values("DIFF_FILTER", "--diff-filter", separate=False),
              **_values("INT", "-U", "--unified", "-M", "-C", "--find-renames", "--find-copies", separate=False)}
_LOG_READ = {**_DIFF_READ,
             **_flags("--oneline", "--reverse", "--no-merges", "--merges", "--first-parent", "--no-decorate",
                      "--topo-order", "--date-order", "--all", "--follow", "--full-history", "--abbrev-commit",
                      "--no-abbrev-commit", "-r", "--root", "--no-walk", "--decorate", "--source",
                      "--branches", "--tags", "--remotes", "--simplify-by-decoration", "--ancestry-path",
                      "--patch-with-stat", "--graph"),
             **_values("FORMAT", "--format", separate=False), **_optional("FORMAT", "--pretty"),
             **_values("INT", "-n", "--max-count", "--skip"),
             **_values("TEXT", "--since", "--until", "--after", "--before", "--author", "--committer", "--grep",
                       "--date", separate=False)}

#: Every admitted subcommand. A subcommand that is not here -- an alias, a program-running builtin, anything that
#: reaches the network or writes a ref -- is refused.
_GIT_GRAMMAR: dict[str, _Spec] = {
    "version": _Spec({}),
    "rev-parse": _Spec({**_flags("--show-toplevel", "--git-dir", "--git-common-dir", "--absolute-git-dir",
                                 "--is-inside-work-tree", "--is-inside-git-dir", "--is-bare-repository",
                                 "--is-shallow-repository", "--show-prefix", "--show-cdup", "--verify", "-q",
                                 "--quiet", "--symbolic-full-name", "--symbolic", "--show-object-format", "--all",
                                 "--branches", "--tags", "--remotes", "--show-superproject-working-tree"),
                        **_optional("ABBREV_REF", "--abbrev-ref"), **_optional("INT", "--short"),
                        **_values("PATH_FORMAT", "--path-format", separate=False)},
                       "REV", 0, None, dashdash="PATHSPEC"),
    "rev-list": _Spec({**_flags("--count", "--reverse", "--first-parent", "--no-merges", "--merges", "--topo-order",
                                "--date-order", "--all", "--left-right", "--boundary", "--branches", "--tags",
                                "--remotes", "--ancestry-path"),
                       **_values("INT", "-n", "--max-count", "--skip"),
                       **_values("INT", "--max-parents", "--min-parents", separate=False),
                       **_values("TEXT", "--since", "--until", "--after", "--before", separate=False)},
                      "REV", 0, None, dashdash="PATHSPEC"),
    "log": _Spec(_LOG_READ, "REV", 0, None, dashdash="PATHSPEC"),
    "show": _Spec({**_LOG_READ, **_flags("--quiet")}, "REV", 0, None, dashdash="PATHSPEC"),
    "diff": _Spec({**_DIFF_READ, **_flags("--quiet", "--exit-code", "--cached", "--staged", "--check")},
                  "REV", 0, 2, dashdash="PATHSPEC"),
    "diff-tree": _Spec({**_DIFF_READ, **_flags("-r", "--no-commit-id", "--root", "-t", "-c", "--cc", "-m")},
                       "REV", 1, 2, dashdash="PATHSPEC"),
    "ls-files": _Spec({**_flags("-z", "--cached", "-c", "--others", "-o", "--exclude-standard", "--deleted", "-d",
                                "--modified", "-m", "--stage", "-s", "--full-name", "--error-unmatch", "--ignored",
                                "-i", "--directory", "--no-empty-directory", "-t", "-v", "--killed", "-k",
                                "--unmerged", "-u", "--eol"),
                       **_values("PATTERN", "--exclude", "-x", separate=True),
                       **_values("FORMAT", "--format", separate=False)},
                      "PATHSPEC", 0, None, dashdash="PATHSPEC"),
    "ls-tree": _Spec({**_flags("-r", "-t", "-d", "-l", "--long", "-z", "--name-only", "--name-status", "--full-tree",
                               "--full-name", "--object-only"),
                      **_optional("INT", "--abbrev"), **_values("FORMAT", "--format", separate=False)},
                     "REV", 1, None, check=_check_ls_tree),
    "cat-file": _Spec({**_flags("-t", "-s", "-e", "-p", "--batch-all-objects", "--buffer", "--follow-symlinks",
                                "--unordered"),
                       **_optional("FORMAT", "--batch", "--batch-check")},
                      "REV", 0, 2, check=_check_cat_file),
    "merge-base": _Spec(_flags("--is-ancestor", "--all", "--octopus", "--independent"), "REV", 1, None),
    "status": _Spec({**_flags("--short", "-s", "--branch", "-b", "-z", "--long", "--no-renames", "--ahead-behind",
                              "--no-ahead-behind", "--show-stash", "-v", "--verbose"),
                     **_optional("PORCELAIN", "--porcelain"), **_optional("UNTRACKED", "--untracked-files", "-u"),
                     **_optional("IGNORED", "--ignored"), **_optional("SUBMODULES", "--ignore-submodules")},
                    "PATHSPEC", 0, None, dashdash="PATHSPEC"),
    "branch": _Spec({**_flags("--all", "-a", "--verbose", "-v", "-vv", "--no-abbrev", "--list", "-l", "--remotes",
                              "-r", "--show-current", "--no-color", "--no-column", "-i", "--ignore-case"),
                     **_optional("REV", "--contains", "--no-contains", "--merged", "--no-merged"),
                     **_values("REV", "--points-at"), **_values("FORMAT", "--format", separate=False),
                     **_values("TEXT", "--sort", separate=False)},
                    "PATTERN", 0, None, check=_check_branch),
    "for-each-ref": _Spec({**_flags("--ignore-case", "--omit-empty"),
                           **_values("FORMAT", "--format", separate=False), **_values("TEXT", "--sort", separate=False),
                           **_values("INT", "--count", separate=False),
                           **_values("REV", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at",
                                     separate=False)},
                          "PATTERN", 0, None),
    "show-ref": _Spec({**_flags("--heads", "--tags", "--head", "-d", "--dereference", "--verify", "-q", "--quiet",
                                "-s", "--exists"),
                       **_optional("INT", "--abbrev", "--hash")},
                      "PATTERN", 0, None),
    "symbolic-ref": _Spec(_flags("--short", "-q", "--quiet"), "NAME", 0, None, check=_check_symbolic_ref),
    "describe": _Spec({**_flags("--tags", "--all", "--always", "--long", "--exact-match", "--first-parent",
                                "--contains"),
                       **_optional("INT", "--abbrev"), **_values("PATTERN", "--match", "--exclude", separate=False),
                       **_values("INT", "--candidates", separate=False)},
                      "REV", 0, None),
    "name-rev": _Spec({**_flags("--name-only", "--tags", "--always", "--undefined", "--no-undefined"),
                       **_values("PATTERN", "--refs", "--exclude", separate=False)},
                      "REV", 0, None),
    "config": _Spec({**_flags("--get", "--get-all", "--get-regexp", "--list", "-l", "-z", "--null", "--name-only",
                              "--show-origin", "--show-scope", "--includes", "--no-includes", "--bool", "--int",
                              "--bool-or-int", "--path", "--local"),
                     **_values("CONFIG_TYPE", "--type", separate=False), **_values("TEXT", "--default", separate=False)},
                    "TEXT", 0, 3, check=_check_config),
    "remote": _Spec(_flags("-v", "--verbose", "--all", "--push"), "TEXT", 0, 2, check=_check_remote),
    "worktree": _Spec(_flags("--porcelain", "-z", "-v", "--verbose"), "TEXT", 1, 1, check=_check_worktree),
    "grep": _Spec({**_flags("-n", "--line-number", "-i", "--ignore-case", "-l", "--files-with-matches", "--name-only",
                            "-L", "--files-without-match", "-c", "--count", "-w", "--word-regexp", "-F",
                            "--fixed-strings", "-E", "--extended-regexp", "-G", "--basic-regexp", "-I", "--cached",
                            "-z", "--null", "-h", "-H", "--full-name", "-v", "--invert-match", "-q", "--quiet",
                            "--untracked", "--no-color", "-a", "--text", "--all-match", "--break", "--heading",
                            "-o", "--only-matching", "--column"),
                   **_values("PATTERN", "-e", joined=False), **_values("INT", "-m", "--max-count", "--max-depth"),
                   **_values("INT", "-A", "-B", "-C", "--context", "--after-context", "--before-context")},
                  "PATTERN", 0, None, dashdash="PATHSPEC"),
    "hash-object": _Spec({**_flags("--no-filters", "--stdin"), **_values("OBJECT_TYPE", "-t", joined=False)},
                         "PATHSPEC", 0, None, dashdash="PATHSPEC"),
    "count-objects": _Spec(_flags("-v", "--verbose", "-H", "--human-readable")),
    "var": _Spec({}, "VAR", 1, 1),
    "check-ignore": _Spec(_flags("-q", "--quiet", "-v", "--verbose", "-n", "--non-matching", "--no-index", "-z"),
                          "PATHSPEC", 0, None, dashdash="PATHSPEC"),
    "check-attr": _Spec(_flags("-a", "--all", "-z", "--cached"), "PATTERN", 0, None, dashdash="PATHSPEC"),
    "blame": _Spec({**_flags("-l", "-s", "-e", "-w", "--porcelain", "--line-porcelain", "-p", "-t", "-f", "-n",
                             "--root", "--show-stats", "--show-email", "--show-name", "--show-number"),
                    **_values("TEXT", "-L", joined=True)},
                   "REV", 0, 2, dashdash="PATHSPEC"),
    # ---- the only native Git writes, each admitted only inside a declared Git scratch root
    "init": _Spec({**_flags("-q", "--quiet"), **_values("NAME", "-b"), **_values("NAME", "--initial-branch"),
                   **_values("OBJECT_FORMAT", "--object-format")},
                  "PATH", 0, 1, writes=True, check=_check_writes),
    "add": _Spec(_flags("-A", "--all", "-u", "--update", "-f", "--force", "-v", "--verbose", "-N", "--intent-to-add",
                        "--no-all", "--ignore-removal", "--no-ignore-removal", "-n", "--dry-run"),
                 "PATHSPEC", 0, None, dashdash="PATHSPEC", writes=True, check=_check_writes),
    "commit": _Spec({**_flags("-q", "--quiet", "-a", "--all", "--allow-empty", "--allow-empty-message", "--no-verify",
                              "-n", "--no-edit", "--no-status", "--no-post-rewrite"),
                     **_values("MESSAGE", "-m", "--message"), **_values("TEXT", "--author", "--date", separate=False)},
                    "PATHSPEC", 0, None, dashdash="PATHSPEC", writes=True, check=_check_writes),
}


def _unknown_option(subcommand: str, arg: str, letter: str | None = None) -> str:
    """Why an option that is not in ``subcommand``'s grammar is refused, naming its hazard when it has one."""

    name = arg.split("=", 1)[0]
    if subcommand == "config":
        long_names = _GIT_CONFIG_FILE_OPTIONS + _GIT_CONFIG_WRITE_ACTIONS
        if letter == "-f" or name == "-f" or (name.startswith("--") and len(name) > 3
                                               and any(o.startswith(name) for o in _GIT_CONFIG_FILE_OPTIONS)):
            return (f"git config {arg!r} names a configuration file other than the repository's own (read or write "
                    "indirection); the typed grammar never admits -f/--file/--blob/--global/--system/--worktree "
                    "or an abbreviation of one")
        if name.startswith("--") and len(name) > 3 and any(o.startswith(name) for o in long_names):
            return (f"git config {arg!r} is a configuration write action or an abbreviation of one; only "
                    "`config <declared key> <value>` writes, inside a scratch repository")
    if name.startswith("--") and len(name) > 3 and any(forbidden.startswith(name) for forbidden in _GIT_HAZARD_LONG):
        return (f"git option {arg!r} runs a program, writes a file or reaches another repository (it, or the option "
                "it abbreviates, is not in the typed grammar)")
    if subcommand == "grep" and (letter or name)[1:2] == "O":
        return "git grep -O opens files in a pager program"
    hazard_letters = _GIT_HAZARD_SHORT.get(subcommand, "")
    if hazard_letters and not name.startswith("--") and ((letter or name)[1:2] in hazard_letters):
        return f"git {subcommand} {arg!r} runs a program or edits interactively"
    spec = _GIT_GRAMMAR.get(subcommand)
    if spec is not None and name.startswith("--"):
        expanded = [option for option in spec.options if option.startswith(name) and option != name]
        if expanded:
            return (f"git {subcommand} option {arg!r} abbreviates {sorted(expanded)}; the typed grammar admits "
                    "only the exact option")
    return f"git {subcommand} option {(letter or arg)!r} is not in the typed grammar"


def _parse_git_arguments(subcommand: str, args: list[str]) -> tuple[dict | None, str]:
    """Parse ``args`` against the subcommand's grammar: (parsed options, positionals and pathspecs, writes) or why not."""

    spec = _GIT_GRAMMAR.get(subcommand)
    if spec is None:
        return None, f"git {subcommand!r} is not an admitted read-only builtin (aliases and program-running commands are refused)"
    for arg in args:
        if _GIT_SIGNATURE_FORMAT.search(arg):
            return None, f"{arg!r} asks git to verify a signature with an external program"
    options: dict[str, list] = {}
    positionals: list[str] = []
    pathspecs: list[str] = []
    after_dashdash = False
    index = 0
    while index < len(args):
        arg = args[index]
        if after_dashdash:
            problem = _type_problem(spec.dashdash, arg) if not arg.startswith("-") else (
                _type_problem("TEXT", arg))
            if problem:
                return None, f"git {subcommand} pathspec: {problem}"
            pathspecs.append(arg)
            index += 1
            continue
        if arg == "--":
            if spec.dashdash is None:
                return None, f"git {subcommand} takes no '--' pathspecs"
            after_dashdash = True
            index += 1
            continue
        if arg.startswith("--"):
            name, equals, value = arg.partition("=")
            option = spec.options.get(name)
            if option is None:
                return None, _unknown_option(subcommand, arg)
            if option.kind == _FLAG:
                if equals:
                    return None, f"git {subcommand} option {name!r} takes no value"
                options.setdefault(name, []).append(None)
            elif option.kind == _OPTIONAL:
                if equals:
                    problem = _type_problem(option.type, value)
                    if problem:
                        return None, f"git {subcommand} {name}: {problem}"
                options.setdefault(name, []).append(value if equals else None)
            else:
                if not equals:
                    if not option.separate or index + 1 >= len(args):
                        return None, f"git {subcommand} option {name!r} needs {'an attached ' if not option.separate else 'a '}value"
                    index += 1
                    value = args[index]
                problem = _type_problem(option.type, value)
                if problem:
                    return None, f"git {subcommand} {name}: {problem}"
                options.setdefault(name, []).append(value)
            index += 1
            continue
        if arg.startswith("-") and len(arg) > 1:
            exact = spec.options.get(arg)
            if exact is not None and exact.kind == _FLAG:
                options.setdefault(arg, []).append(None)
                index += 1
                continue
            cluster = arg[1:]
            position = 0
            while position < len(cluster):
                letter = "-" + cluster[position]
                option = spec.options.get(letter)
                if option is None:
                    return None, _unknown_option(subcommand, arg, letter)
                rest = cluster[position + 1:]
                if option.kind == _FLAG:
                    options.setdefault(letter, []).append(None)
                    position += 1
                    continue
                if option.kind == _OPTIONAL:
                    problem = _type_problem(option.type, rest) if rest else None
                    if problem:
                        return None, f"git {subcommand} {letter}: {problem}"
                    options.setdefault(letter, []).append(rest or None)
                    break
                if rest:
                    if not option.joined:
                        return None, f"git {subcommand} {letter} takes its value as the next argument"
                    value = rest
                else:
                    if not option.separate or index + 1 >= len(args):
                        return None, f"git {subcommand} option {letter!r} needs a value"
                    index += 1
                    value = args[index]
                problem = _type_problem(option.type, value)
                if problem:
                    return None, f"git {subcommand} {letter}: {problem}"
                options.setdefault(letter, []).append(value)
                break
            index += 1
            continue
        positionals.append(arg)
        index += 1
    if spec.positional is None and positionals:
        return None, f"git {subcommand} takes no positional argument ({positionals[:3]})"
    if len(positionals) < spec.minimum or (spec.maximum is not None and len(positionals) > spec.maximum):
        return None, (f"git {subcommand} takes {spec.minimum}..{spec.maximum if spec.maximum is not None else 'n'} "
                      f"positional arguments, not {len(positionals)}")
    if spec.check is None:
        for value in positionals:
            problem = _type_problem(spec.positional, value)
            if problem:
                return None, f"git {subcommand} argument: {problem}"
    parsed = {"subcommand": subcommand, "options": options, "positionals": positionals, "pathspecs": pathspecs,
              "writes": spec.writes}
    if spec.check is not None:
        problem, writes = spec.check(parsed)
        parsed["writes"] = writes
        if problem:
            return None, problem
        if subcommand in ("init", "add", "commit"):
            for value in positionals:
                problem = _type_problem(spec.positional, value)
                if problem:
                    return None, f"git {subcommand} argument: {problem}"
    return parsed, ""


def _no_program_path(name: str) -> str:
    """A path under the first guarded root that must never exist: the target of neutralized hooks/programs."""

    roots = _split_roots(_ROOT)
    base = roots[0] if roots else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


def _git_command_scope() -> tuple[tuple[str, str], ...]:
    return (
        ("core.hooksPath", _no_program_path("__bas_guard_no_git_hooks__")),
        ("core.fsmonitor", "false"),
        ("core.pager", "cat"),
        ("core.editor", ":"),
        ("sequence.editor", ":"),
        # No credential.helper reset here: a Windows environment variable cannot hold the empty value that
        # resets the list. Credential helpers stay unreachable because system and global configuration are not
        # read, a repository that declares credential.* is refused, and no admitted subcommand authenticates.
        ("log.showSignature", "false"),
        ("commit.gpgSign", "false"),
        ("tag.gpgSign", "false"),
        ("gpg.program", _no_program_path("__bas_guard_no_gpg__.exe")),
        ("gpg.ssh.program", _no_program_path("__bas_guard_no_gpg__.exe")),
        ("gpg.x509.program", _no_program_path("__bas_guard_no_gpg__.exe")),
        ("protocol.allow", "never"),
        ("protocol.file.allow", "always"),
        ("safe.bareRepository", "explicit"),
        ("diff.ignoreSubmodules", "all"),
        ("submodule.recurse", "false"),
    )


def controlled_git_environment() -> dict[str, str]:
    """The exact variables the guard gives every admitted git child (``GIT_CONFIG_GLOBAL`` may name a file)."""

    fixed = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat",
             "GIT_EDITOR": ":", "GIT_SEQUENCE_EDITOR": ":", "GIT_ALLOW_PROTOCOL": "file",
             "GIT_PROTOCOL_FROM_USER": "0", "GIT_NO_LAZY_FETCH": "1"}
    scope = _git_command_scope()
    fixed["GIT_CONFIG_COUNT"] = str(len(scope))
    for index, (key, value) in enumerate(scope):
        fixed[f"GIT_CONFIG_KEY_{index}"] = key
        fixed[f"GIT_CONFIG_VALUE_{index}"] = value
    return fixed


def _parse_git_config(path: str) -> tuple[list[tuple[str, str | None]], str | None]:
    """(dotted key, value) pairs of one git configuration file, or an error that fails closed.

    Section and key names are case-insensitive in git and are lowercased; a quoted subsection keeps its case.
    A line this parser cannot read is an error, never skipped: an unreadable file is not a clean one.
    """

    try:
        with _ORIGINAL.get("open", io.open)(path, "r", encoding="utf-8", errors="strict") as handle:
            lines = handle.read().lstrip("\ufeff").splitlines()
    except FileNotFoundError:
        return [], None
    except (OSError, UnicodeDecodeError) as error:
        return [], f"cannot read {path}: {error}"
    entries: list[tuple[str, str | None]] = []
    section: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        while line.rstrip().endswith("\\") and index < len(lines):
            line = line.rstrip()[:-1] + lines[index]
            index += 1
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        header = _GIT_SECTION.match(line)
        if header:
            name, sub = header.group(1).lower(), header.group(2)
            section = name if sub is None else f"{name}.{sub}"
            line = line[header.end():]
            if not line.strip() or line.strip()[0] in "#;":
                continue
        match = _GIT_KEY.match(line)
        if not match or section is None:
            return entries, f"unparseable configuration line in {path}: {stripped[:80]!r}"
        value = match.group(2)
        if value is not None:
            if '"' not in value:
                value = re.sub(r"[#;].*$", "", value)
            value = value.strip().strip('"')
        entries.append((f"{section}.{match.group(1).lower()}", value))
    return entries, None


def _scan_git_config(path: str) -> str | None:
    """None when a configuration file declares nothing the command-scope settings cannot neutralize."""

    entries, error = _parse_git_config(path)
    if error:
        return error
    for key, value in entries:
        lowered = key.lower()
        for pattern, meaning in _GIT_REFUSED_CONFIG:
            if pattern.search(lowered):
                return f"{path} declares {key} ({meaning})"
        if lowered == "core.fsmonitor" and (value or "").strip().lower() not in _GIT_FALSEY:
            return f"{path} declares core.fsmonitor={value!r} (a monitor program or hook)"
    return None


def _git_dir_from_dotgit(dotgit: str, owner: str) -> str | None:
    if os.path.isdir(dotgit):
        return os.path.normpath(dotgit)
    if os.path.isfile(dotgit):
        try:
            with _ORIGINAL.get("open", io.open)(dotgit, "r", encoding="utf-8", errors="replace") as handle:
                first = handle.readline().strip()
        except OSError:
            return None
        if first.lower().startswith("gitdir:"):
            return os.path.normpath(os.path.join(owner, first.split(":", 1)[1].strip()))
    return None


def _git_repository(base: str, git_dir: str | None, work_tree: str | None) -> dict:
    """The repository a git child at ``base`` would use: its work tree, git dir and common dir."""

    if git_dir is None:
        current = os.path.abspath(base)
        while True:
            found = _git_dir_from_dotgit(os.path.join(current, ".git"), current)
            if found:
                git_dir, work_tree = found, work_tree or current
                break
            # A directory that is itself a repository (HEAD, objects, refs) is one git would use implicitly;
            # its configuration is as live as a .git directory's. It is reported, and refused by the caller.
            if (os.path.isfile(os.path.join(current, "HEAD")) and os.path.isdir(os.path.join(current, "objects"))
                    and os.path.isdir(os.path.join(current, "refs"))):
                inside_dotgit = ".git" in [part.casefold() for part in current.replace("/", "\\").split("\\")]
                return {"git_dir": current, "work_tree": None, "common_dir": current,
                        "implicit_bare": not inside_dotgit}
            parent = os.path.dirname(current)
            if parent == current:
                return {"git_dir": None, "work_tree": work_tree, "common_dir": None}
            current = parent
    common = git_dir
    commondir = os.path.join(git_dir, "commondir")
    if os.path.isfile(commondir):
        try:
            with _ORIGINAL.get("open", io.open)(commondir, "r", encoding="utf-8", errors="replace") as handle:
                common = os.path.normpath(os.path.join(git_dir, handle.readline().strip()))
        except OSError:
            common = git_dir
    return {"git_dir": os.path.normpath(git_dir), "work_tree": work_tree, "common_dir": common}


def _scratch_roots() -> tuple[str, ...]:
    return tuple(dict.fromkeys(form for root in _split_roots(os.environ.get("BAS_CANONICAL_WRITE_GIT_SCRATCH"))
                               for form in _root_forms(root)))


def _in_scratch(path: str | None) -> bool:
    """Inside a declared Git scratch root by *every* spelling (literal and resolved) and outside every protected root.

    v37.5: v37.4 accepted a path when any one spelling was inside a scratch root, so a junction inside the root
    that resolved elsewhere still counted as scratch.
    """

    if not path:
        return False
    roots = _scratch_roots()
    forms = _forms(path)
    return bool(roots) and all(any(_inside(root, form) for root in roots) for form in forms) and not protected(path)


def _metadata_problem(directory: str | None) -> str | None:
    """Why a repository's metadata could carry git's writes out of the scratch root: a reparse point or a
    multiply-linked file anywhere inside it. None when it is plain."""

    if not directory or not os.path.lexists(directory):
        return None
    stack = [directory]
    seen = 0
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    seen += 1
                    if seen > _GIT_METADATA_WALK_LIMIT:
                        return f"repository metadata under {directory!r} exceeds {_GIT_METADATA_WALK_LIMIT} entries"
                    try:
                        stat = os.lstat(entry.path)
                    except OSError as error:
                        return f"cannot read {entry.path!r}: {error}"
                    if getattr(stat, "st_file_attributes", 0) & 0x400 or entry.is_symlink():
                        return f"reparse point in the repository metadata: {entry.path!r}"
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif stat.st_nlink and stat.st_nlink > 1:
                        return f"multiply linked file in the repository metadata: {entry.path!r}"
        except OSError as error:
            return f"cannot walk {current!r}: {error}"
    return None


def _trusted_git() -> frozenset[str]:
    return _STATE.get("trusted_git") or frozenset()


def _resolve_program(program: str, explicit_executable: bool) -> str | None:
    """The file Windows would start for ``program``, resolved the way CreateProcess resolves it.

    An explicit ``executable=`` without a directory is completed from the current directory only. A command
    line's first token without a directory is searched in the application directory, the parent's current
    directory, the system directories and then PATH, with ``.exe`` appended when there is no extension.
    """

    program = program.strip('"')
    has_extension = bool(ntpath.splitext(program)[1])
    if ntpath.dirname(program) or explicit_executable:
        path = program if ntpath.isabs(program) else os.path.join(os.getcwd(), program)
        for option in ([path] if has_extension else [path + ".exe", path]):
            if os.path.isfile(option):
                return os.path.normcase(os.path.realpath(option))
        return None
    system_root = os.environ.get("SYSTEMROOT") or r"C:\Windows"
    search = [os.path.dirname(getattr(sys, "_base_executable", None) or sys.executable)]
    if not os.environ.get("NODEFAULTCURRENTDIRECTORYINEXEPATH"):
        search.append(os.getcwd())
    search += [os.path.join(system_root, "System32"), os.path.join(system_root, "System"), system_root]
    search += [p for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]
    name = program if has_extension else program + ".exe"
    for directory in search:
        option = os.path.join(directory.strip('"'), name)
        if os.path.isfile(option):
            return os.path.normcase(os.path.realpath(option))
    return None


def _discover_trusted_git() -> frozenset[str]:
    """The git on PATH at installation (never the application or current directory) and its installation's
    sibling launchers. A file inside any writable or scratch root is never trusted."""

    found = None
    for directory in [p for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]:
        option = os.path.join(directory.strip('"'), "git.exe")
        if os.path.isfile(option):
            found = os.path.realpath(option)
            break
    if found is None:
        return frozenset()
    trusted = {found}
    parent = os.path.dirname(found)
    install = os.path.dirname(parent) if os.path.basename(parent).lower() in ("cmd", "bin") else None
    if install and os.path.basename(install).lower() == "mingw64":
        install = os.path.dirname(install)
    if install:
        for relative in (("cmd", "git.exe"), ("bin", "git.exe"), ("mingw64", "bin", "git.exe")):
            candidate = os.path.join(install, *relative)
            if os.path.isfile(candidate):
                trusted.add(os.path.realpath(candidate))
    _, allow = _settings()
    writable = tuple(allow) + _scratch_roots()
    return frozenset(os.path.normcase(path) for path in trusted
                     if not any(_under(root, os.path.normcase(os.path.abspath(path))) for root in writable))


def _git_environment_problem(env, inherited: bool) -> str | None:
    """Why a git child's environment is refused, or None.

    A controlled variable may be absent from a caller-built mapping (it is then added) but never different:
    a caller that sets ``GIT_CONFIG_KEY_0=alias.x`` is refused, not silently corrected. An inherited
    environment must carry every controlled value, because nothing can be added to it on the way out.
    """

    mapping = dict(os.environ) if inherited else dict(env)
    controlled = controlled_git_environment()
    for key, value in mapping.items():
        upper = str(key).upper()
        if not upper.startswith("GIT_"):
            continue
        if upper in controlled:
            if value != controlled[upper]:
                return f"{upper}={value!r} differs from the guard's controlled git environment"
            continue
        if upper == "GIT_CONFIG_GLOBAL":
            continue
        if upper.startswith("GIT_CONFIG_KEY_") or upper.startswith("GIT_CONFIG_VALUE_"):
            return f"{upper} is set outside the guard's command-scope configuration"
        if upper in _GIT_BENIGN_ENV or upper in _GIT_PATH_ENV or upper in _GIT_PATH_ENV_READ_ONLY:
            continue
        return f"{upper} is set in the git child environment (it can run a program, write a file or add configuration)"
    if inherited:
        for key, value in controlled.items():
            if _env_get(mapping, key) != value:
                return f"this process's environment no longer carries {key}={value!r}"
    return None


def _normalize_git_environment(mapping) -> None:
    """Add every controlled variable to ``mapping``; at installation also replace stale inherited values."""

    for key, value in controlled_git_environment().items():
        mapping[_env_key(mapping, key)] = value
    for key in [k for k in list(mapping.keys()) if str(k).upper().startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))]:
        if str(key).upper() not in controlled_git_environment():
            del mapping[key]
    if not _env_get(dict(mapping), "GIT_CONFIG_GLOBAL"):
        mapping[_env_key(mapping, "GIT_CONFIG_GLOBAL")] = os.devnull


def _git_invocation(argv: list[str], cwd, env: dict) -> tuple[dict | None, str]:
    """Parse the global part of a git command line (exact options only) into its base, repository and subcommand."""

    base = os.path.abspath(_text(cwd) or os.getcwd())
    git_dir = _env_get(env, "GIT_DIR")
    work_tree = _env_get(env, "GIT_WORK_TREE")
    config_pairs: list[str] = []
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg in _GIT_GLOBAL_FLAGS:
            index += 1
            continue
        if arg == "-C":
            if index + 1 >= len(argv):
                return None, "-C has no value"
            problem = _type_problem("PATH", argv[index + 1])
            if problem:
                return None, f"git -C: {problem}"
            base = os.path.abspath(os.path.join(base, argv[index + 1]))
            index += 2
            continue
        if arg == "-c":
            if index + 1 >= len(argv):
                return None, "-c has no value"
            config_pairs.append(argv[index + 1])
            index += 2
            continue
        option = next((name for name in _GIT_GLOBAL_PATH_OPTIONS if arg == name or arg.startswith(name + "=")), None)
        if option:
            if arg == option:
                if index + 1 >= len(argv):
                    return None, f"{option} has no value"
                value, index = argv[index + 1], index + 2
            else:
                value, index = arg.split("=", 1)[1], index + 1
            problem = _type_problem("PATH", value)
            if problem:
                return None, f"git {option}: {problem}"
            if option == "--git-dir":
                git_dir = value
            else:
                work_tree = value
            continue
        if arg in ("--version", "-v"):
            if index != len(argv) - 1:
                return None, f"git {arg} takes no further argument"
            return {"subcommand": "version", "args": [], "base": base, "git_dir": None, "work_tree": None}, ""
        if arg.startswith("-"):
            return None, f"git global option {arg!r} is not admitted"
        break
    if index >= len(argv):
        return None, "git with no subcommand"
    for pair in config_pairs:
        key, sep, value = pair.partition("=")
        lowered = key.strip().lower()
        if lowered in _GIT_FALSE_ONLY_KEYS and sep and value.strip().lower() in _GIT_FALSEY:
            continue
        if lowered not in _GIT_SAFE_CONFIG_KEYS or not sep or value.startswith("!") or any(ord(c) < 32 for c in value):
            return None, f"git -c {key!r} is not a literal data-shaping setting"
    if git_dir is not None:
        git_dir = os.path.abspath(os.path.join(base, git_dir))
    if work_tree is not None:
        work_tree = os.path.abspath(os.path.join(base, work_tree))
    return {"subcommand": argv[index], "args": argv[index + 1:], "base": base, "git_dir": git_dir,
            "work_tree": work_tree}, ""


def _git_child_is_confined(argv: list[str], cwd, env, inherited: bool) -> tuple[bool, str]:
    environment = _child_environment(env)
    problem = _git_environment_problem(environment if not inherited else None, inherited)
    if problem:
        return False, problem
    invocation, reason = _git_invocation(argv, cwd, environment)
    if invocation is None:
        return False, reason
    subcommand = invocation["subcommand"]
    if subcommand == "version" and not invocation["args"]:
        return True, "git --version"
    parsed, reason = _parse_git_arguments(subcommand, invocation["args"])
    if parsed is None:
        return False, reason
    writes = parsed["writes"]
    base = invocation["base"]
    if protected(base):
        return False, "git working directory is protected"
    for key in _GIT_PATH_ENV:
        value = _env_get(environment, key)
        if value and protected(os.path.join(base, value)):
            return False, f"{key} resolves into the guarded root"
    for value in (invocation["git_dir"], invocation["work_tree"]):
        if value and protected(value):
            return False, "--git-dir or --work-tree resolves into the guarded root"
    for value in parsed["positionals"] + parsed["pathspecs"]:
        if value and not value.startswith((":", "-")) and protected(os.path.join(base, value)):
            return False, f"git argument {value!r} resolves into the guarded root"
    if writes and not _scratch_roots():
        return False, (f"git {subcommand} writes a repository and this process declares no git scratch root "
                       "(v37.5: native Git writes need BAS_CANONICAL_WRITE_GIT_SCRATCH; there is no default)")
    if subcommand == "init":
        target = parsed["positionals"][0] if parsed["positionals"] else None
        target = os.path.abspath(os.path.join(base, target)) if target else base
        if not _in_scratch(target) or (invocation["git_dir"] and not _in_scratch(invocation["git_dir"])):
            return False, f"git init target {target!r} is not inside a git scratch root"
        dotgit = invocation["git_dir"] or _git_dir_from_dotgit(os.path.join(target, ".git"), target) \
            or os.path.join(target, ".git")
        repository = {"git_dir": dotgit, "work_tree": target, "common_dir": dotgit}
        if os.path.lexists(os.path.join(target, ".git")) and not _in_scratch(dotgit):
            return False, f"git init target's .git resolves outside the git scratch root ({dotgit!r})"
    else:
        repository = _git_repository(base, invocation["git_dir"], invocation["work_tree"])
        common_override = _env_get(environment, "GIT_COMMON_DIR")
        if common_override:
            repository["common_dir"] = os.path.abspath(os.path.join(base, common_override))
        if repository.get("implicit_bare"):
            return False, (f"{repository['git_dir']!r} is an implicit bare repository; only an explicit --git-dir "
                           "or GIT_DIR may name a bare repository")
    configs = []
    if repository["git_dir"]:
        configs = list(dict.fromkeys(os.path.join(d, name) for d, name in (
            (repository["common_dir"], "config"), (repository["git_dir"], "config"),
            (repository["git_dir"], "config.worktree"))))
    global_config = _env_get(environment if not inherited else dict(os.environ), "GIT_CONFIG_GLOBAL")
    if global_config and global_config.strip().lower() not in (os.devnull.lower(), "/dev/null"):
        if not os.path.isfile(global_config):
            return False, f"GIT_CONFIG_GLOBAL {global_config!r} is not an existing file"
        configs.append(global_config)
    for path in configs:
        problem = _scan_git_config(path)
        if problem:
            return False, problem
        if writes:
            entries, _ = _parse_git_config(path)
            for key, value in entries:
                if key.lower() == "core.worktree" and value and not _in_scratch(os.path.join(os.path.dirname(path), value)):
                    return False, f"{path} moves the work tree outside the git scratch roots"
    for sink in (_no_program_path("__bas_guard_no_git_hooks__"), _no_program_path("__bas_guard_no_gpg__.exe")):
        if os.path.exists(sink):
            return False, f"the neutralized program path {sink!r} exists, so hooks or signing could run"
    if writes:
        paths = [repository["work_tree"], repository["git_dir"], repository["common_dir"],
                 _env_get(environment, "GIT_INDEX_FILE"), _env_get(environment, "GIT_OBJECT_DIRECTORY")]
        outside = [p for p in paths if p and not _in_scratch(os.path.join(base, p))]
        if not repository["git_dir"] or outside:
            return False, (f"git {subcommand} writes a repository that is not wholly inside a git scratch root "
                           f"({outside or 'no repository'})")
        for directory in dict.fromkeys(d for d in (repository["common_dir"], repository["git_dir"]) if d):
            problem = _metadata_problem(directory)
            if problem:
                return False, f"git {subcommand} would write through {problem}"
        return True, f"git {subcommand} confined to the scratch repository {repository['work_tree']} (typed grammar)"
    return True, f"git {subcommand} read-only, controlled environment, repository configuration scanned, typed grammar"


def _check_child(executable, args, cwd, env, route: str) -> None:
    argv = _argv(args)
    program = _text(executable) or (argv[0] if argv else "")
    name = ntpath.basename(program.strip('"')).casefold()
    if _PYTHON_NAME.match(name) or os.path.normcase(program.strip('"')) in {
            os.path.normcase(sys.executable), os.path.normcase(getattr(sys, "_base_executable", sys.executable))}:
        ok, reason = _python_child_reinstalls_guard(argv or [program], env)
    elif name in ("git", "git.exe"):
        resolved = _resolve_program(program, _text(executable) is not None)
        if resolved is None or resolved not in _trusted_git():
            ok, reason = False, (f"{program!r} resolves to {resolved!r}, not the git this guard resolved at "
                                 f"installation {sorted(_trusted_git())}")
        else:
            ok, reason = _git_child_is_confined(argv, cwd, env, env is None)
            if ok and env is not None:
                try:
                    _normalize_git_environment(env)
                except TypeError:
                    ok, reason = False, "the git child environment is immutable and cannot be normalized"
    else:
        ok, reason = False, f"{name or 'an unnamed program'} is neither a guard-installing Python child nor confined git"
    shown = [str(a)[:200] for a in argv[:24]]
    if not ok:
        _log("BLOCKED", route, program or "<child process>", f"{reason} | argv={shown}")
        shown_program = _text(program) if _text(program) is not None else str(program)
        raise CanonicalWriteRefused(errno.EROFS, f"BAS canonical write guard: {route} refused under the guarded root"
                                    f" ({reason})", shown_program or "<child process>")
    _log("CHILD_ADMITTED", route, program, f"{reason} | argv={shown}")


# ------------------------------------------------------------- audit hook


def _open_event(path, mode, flags) -> None:
    if isinstance(path, int):
        return
    writes = bool(isinstance(flags, int) and flags & _WRITE_FLAGS) or bool(
        isinstance(mode, str) and any(c in mode for c in "wax+"))
    if not writes:
        return
    if protected(path):
        _refuse("open(write)", path, f"mode={mode!r} flags={flags!r}")
    if _multiply_linked_on_guarded_volume(path):
        _refuse("open(write)", path, "multiply linked file on the guarded volume; its other names are unknown")


def _relative_to_fd(dir_fd) -> bool:
    """CPython reports an absent dir_fd as None or -1; anything else is a real descriptor."""

    return dir_fd is not None and dir_fd != -1


def _hook(event: str, args) -> None:
    if getattr(_LOCAL, "busy", False):
        return
    _LOCAL.busy = True
    try:
        _dispatch(event, args)
    finally:
        _LOCAL.busy = False


def _dispatch(event: str, args) -> None:
    if event == "open":
        _open_event(*args[:3])
    elif event in ("os.remove", "os.rmdir"):
        path, dir_fd = args[0], args[1] if len(args) > 1 else None
        if _relative_to_fd(dir_fd):
            _refuse(event, path, "dir_fd-relative mutation cannot be resolved and is refused")
        if protected(path):
            _refuse(event, path)
    elif event == "os.rename":
        src, dst = args[0], args[1]
        if any(_relative_to_fd(fd) for fd in args[2:4]):
            _refuse(event, dst, "dir_fd-relative rename cannot be resolved and is refused")
        if protected(src):
            _refuse(event + "(source)", src)
        if protected(dst):
            _refuse(event + "(destination)", dst)
    elif event == "os.mkdir":
        path = args[0]
        dir_fd = args[2] if len(args) > 2 else None
        if _relative_to_fd(dir_fd):
            _refuse(event, path, "dir_fd-relative mutation cannot be resolved and is refused")
        text = _text(path)
        if protected(path) and not (text is not None and os.path.isdir(text)):
            _refuse(event, path)
    elif event in ("os.chmod", "os.chown", "os.utime", "os.chflags", "os.lchflags", "os.setxattr",
                   "os.removexattr", "os.truncate"):
        path = args[0]
        if isinstance(path, int):
            return
        if protected(path):
            _refuse(event, path)
        if event in ("os.chmod", "os.utime", "os.truncate") and _multiply_linked_on_guarded_volume(path):
            _refuse(event, path, "multiply linked file on the guarded volume")
    elif event == "os.link":
        src, dst = args[0], args[1]
        if protected(dst):
            _refuse(event + "(new name)", dst)
        if protected(src):
            _refuse(event + "(protected target)", src, "a hard link would be a writable alias of a protected file")
    elif event == "os.symlink":
        if protected(args[1]):
            _refuse(event, args[1])
    elif event == "_winapi.CreateJunction":
        if protected(args[1]):
            _refuse(event, args[1])
    elif event == "_winapi.CreateFile":
        name = args[0]
        access = args[1] if len(args) > 1 else 0
        disposition = args[3] if len(args) > 3 else None
        wants_change = (isinstance(access, int) and access & _WIN_WRITE_ACCESS) or disposition in _WIN_CREATING_DISPOSITIONS
        if wants_change and protected(name):
            _refuse(event, name, "write, delete, attribute or creating access requested")
    elif event == "_winapi.CopyFile2":
        # shutil.copy2 on Windows (3.12+) copies through CopyFile2 without opening the destination in Python.
        if len(args) > 1 and protected(args[1]):
            _refuse(event, args[1])
    elif event == "shutil.rmtree":
        if protected(args[0]):
            _refuse(event, args[0])
    elif event in ("shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.copytree"):
        if protected(args[1]):
            _refuse(event, args[1])
    elif event == "shutil.move":
        if protected(args[0]):
            _refuse(event + "(source)", args[0])
        if protected(args[1]):
            _refuse(event + "(destination)", args[1])
    elif event == "shutil.chown":
        if protected(args[0]):
            _refuse(event, args[0])
    elif event == "shutil.make_archive":
        if protected(args[0]):
            _refuse(event, args[0])
    elif event == "shutil.unpack_archive":
        if len(args) > 1 and protected(args[1]):
            _refuse(event, args[1])
    elif event == "sqlite3.connect":
        path, read_only = _sqlite_target(args[0])
        if path is not None and not read_only and protected(path):
            _refuse("sqlite3.connect(read-write)", path, "only mode=ro or immutable=1 URIs may open a protected database")
    elif event == "sqlite3.connect/handle":
        # Raised before the connection is initialized, so the authorizer cannot be set here. What can be
        # checked is that the guarded connect produced it; a connection made any other way (the C constructor
        # directly, an early-bound module function, a caller factory) would have no ATTACH authorizer.
        connection_class = _STATE.get("connection_class")
        if connection_class is not None and type(args[0]) is not connection_class:
            _refuse("sqlite3.connect/handle", "<connection>",
                    f"{type(args[0]).__name__} was not created through the guarded connect")
    elif event in ("sqlite3.enable_load_extension", "sqlite3.load_extension"):
        if event == "sqlite3.load_extension" or (len(args) > 1 and args[1]):
            _refuse(event, args[1] if event == "sqlite3.load_extension" and len(args) > 1 else "<extension>",
                    "a SQLite extension is native code with unrestricted writes")
    elif event == "subprocess.Popen":
        executable, argv, cwd, env = (list(args) + [None] * 4)[:4]
        _check_child(executable, argv, cwd, env, event)
        _LOCAL.popen_admitted = True
    elif event == "_winapi.CreateProcess":
        # CPython 3.12 passes this event's command line as an unusable value, so the program cannot be read
        # here. subprocess.Popen raises its own event, with the real arguments and environment, immediately
        # before calling CreateProcess on the same thread; that checked launch is admitted once. A direct
        # CreateProcess with no checked Popen before it is refused.
        if getattr(_LOCAL, "popen_admitted", False):
            _LOCAL.popen_admitted = False
        else:
            _refuse(event, "<child process>", "a direct CreateProcess without a checked subprocess.Popen")
    elif event in ("os.exec", "os.spawn"):
        if event == "os.exec":
            path, argv, env = (list(args) + [None] * 3)[:3]
        else:
            _mode, path, argv, env = (list(args) + [None] * 4)[:4]
        _check_child(path, argv, None, env, event)
    elif event in ("os.system", "os.startfile", "os.posix_spawn"):
        _refuse(event, args[0] if args else "<command>", "a shell or file-association launch cannot be confined")
    elif event in ("ctypes.dlsym", "ctypes.dlsym/handle"):
        name = args[1] if len(args) > 1 else None
        if isinstance(name, str) and name.casefold() in _NATIVE_MUTATORS:
            _refuse(event, name, "native file-mutation entry point")
    elif _NETWORK == NETWORK_DENY and event in _NETWORK_EVENTS:
        host = _NETWORK_EVENTS[event](args)
        if not _loopback_host(host):
            _log("BLOCKED", event, str(host), "offline lane: non-loopback network access")
            raise NetworkRefused(errno.ENETUNREACH,
                                 f"BAS network guard: {event} to {host!r} refused in an offline lane")


#: Audit events that reach the network, and where each carries its host.
_NETWORK_EVENTS = {
    "socket.connect": lambda args: _network_address_host(args[1] if len(args) > 1 else None),
    "socket.sendto": lambda args: _network_address_host(args[1] if len(args) > 1 else None),
    "socket.sendmsg": lambda args: _network_address_host(args[1] if len(args) > 1 else None),
    "socket.getaddrinfo": lambda args: args[0] if args else None,
    "socket.gethostbyname": lambda args: args[0] if args else None,
    "socket.gethostbyname_ex": lambda args: args[0] if args else None,
    "socket.gethostbyaddr": lambda args: args[0] if args else None,
    "socket.getnameinfo": lambda args: _network_address_host(args[0] if args else None),
}


def _wrap_atomic_io(module) -> None:
    """Route the atomic writers' protected targets through the plain calls, which the guard settles."""

    original_text, original_bytes, original_open = module.write_text, module.write_bytes, module.open_write

    def write_text(path, *args, **kwargs):
        if protected(path):
            return path.write_text(*args, **kwargs)
        return original_text(path, *args, **kwargs)

    def write_bytes(path, *args, **kwargs):
        if protected(path):
            return path.write_bytes(*args, **kwargs)
        return original_bytes(path, *args, **kwargs)

    @contextlib.contextmanager
    def open_write(path, *args, **kwargs):
        if protected(path):
            with path.open(*args, **kwargs) as stream:
                yield stream
            return
        with original_open(path, *args, **kwargs) as stream:
            yield stream

    module.write_text, module.write_bytes, module.open_write = write_text, write_bytes, open_write


class _AtomicIoFinder:
    """Wrap aggie_analytics.atomic_io the moment it is imported."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname != "aggie_analytics.atomic_io":
            return None
        import importlib.machinery

        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            return spec
        loader = spec.loader
        execute = loader.exec_module

        def exec_module(module):
            execute(module)
            _wrap_atomic_io(module)

        loader.exec_module = exec_module
        return spec


def install() -> None:
    if not _ROOT or _STATE["installed"]:
        return
    import sqlite3

    _ORIGINAL.update({"open": io.open, "os.replace": os.replace, "os.rename": os.rename, "os.unlink": os.unlink,
                      "sqlite3.connect": sqlite3.connect})
    # Literal and resolved spellings of every root, so an 8.3 or junction spelling of a root is recognized too.
    roots, allow = _settings()
    _STATE.update(roots=roots, allow=allow,
                  root_ids=tuple(dict.fromkeys(i for i in (_identity(r) for r in roots) if i is not None)),
                  allow_ids=tuple(dict.fromkeys(i for i in (_identity(a) for a in allow) if i is not None)),
                  guard_dir=os.path.normcase(os.path.abspath(os.path.dirname(os.path.abspath(__file__)))),
                  connection_class=_guarded_connection_class())
    # v37.5 (MF37A04-01): there is no default git scratch root. v37.4 defaulted it to TEMP; now a native Git write is
    # admitted only where the lane declared BAS_CANONICAL_WRITE_GIT_SCRATCH, and every git child this process or its
    # inheriting children start runs under the controlled git environment.
    _normalize_git_environment(os.environ)
    _STATE["trusted_git"] = _discover_trusted_git()
    builtins.open = io.open = _open
    os.replace, os.rename = _replace_like("replace"), _replace_like("rename")
    sqlite3.connect = sqlite3.dbapi2.connect = _sqlite_connect
    if "aggie_analytics.atomic_io" in sys.modules:
        _wrap_atomic_io(sys.modules["aggie_analytics.atomic_io"])
    else:
        sys.meta_path.insert(0, _AtomicIoFinder())
    _STATE["installed"] = True
    sys.addaudithook(_hook)
    _log("INSTALLED", "install", _ROOT, os.environ.get("BAS_CANONICAL_WRITE_ALLOW", "")
         + (f" | network: {_NETWORK}" if _NETWORK else "")
         + f" | git scratch: {os.environ.get('BAS_CANONICAL_WRITE_GIT_SCRATCH', '') or 'NONE_DECLARED_NO_GIT_WRITES'}"
         + f" | scratch roots overlapping a protected root: {[r for r in _scratch_roots() if protected(r)]}"
         + f" | trusted git: {sorted(_STATE['trusted_git'])}")
