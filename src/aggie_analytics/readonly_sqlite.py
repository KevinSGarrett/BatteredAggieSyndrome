r"""Read-only SQLite connections that open exactly the literal local file a caller names (BAT-717).

A database argument is a filesystem path, never a caller-supplied SQLite URI. :func:`literal_path` turns it into the
absolute path the platform's SQLite VFS will open, and refuses a location that would open another object or reach
beyond a local file:

* Windows: an ordinary relative or absolute drive path is made absolute exactly as Win32 resolves it
  (``GetFullPathNameW``, through :func:`os.path.abspath`), so SQLite opens the object every other file API opens for
  the same spelling. A native extended-length drive path (``\\?\C:\...``, the only spelling of a location beyond the
  ordinary 260-character limit on a host without long-path support) is kept verbatim -- but only when it is already in
  that normal form. SQLite's Windows VFS applies the same normalization to every name it opens, so a verbatim name with
  a trailing dot, a ``.`` or ``..`` component or a forward slash would make SQLite open a different file than the one
  the caller's own reads (hashes, manifests) see: ``DATABASE_LOCATION_NOT_LITERAL``. The local drive device spelling
  ``\\.\C:\...`` is normalized by Win32 like an ordinary path and names the same file as ``C:\...``, which is what
  SQLite is given. UNC shares (``\\server\share``, ``//server/share``, ``\\?\UNC\``), every other ``\\.\`` device and
  every other ``\\?\`` namespace (volume GUIDs, GLOBALROOT) are refused before any filesystem access:
  ``DATABASE_LOCATION_UNSUPPORTED`` (network and device locations are not supported).
* POSIX: the realpath of the given path, as the consumers used before.

:func:`readonly_uri` percent-encodes every character of that path that is not unreserved, so ``?``, ``#``, ``%``,
``&``, ``=``, an apostrophe, spaces and non-ASCII characters stay part of the file name and can never become SQLite URI
parameters, a fragment or an authority; the only parameters are this module's own ``mode=ro`` (plus ``immutable=1``
where a caller deliberately asks for it, as the career successor attachment always has). :func:`connect_readonly` and
:func:`attach_readonly` open read-only (no read-write fallback; a missing file is never created) and then confirm from
``PRAGMA database_list`` that SQLite opened the same filesystem object as the literal path
(``DATABASE_LOCATION_NOT_LITERAL`` otherwise).

The rules live in one block, the literal-location core below. The national population and national history query
modules are standard-library only by their accepted contract (BAT-710, BAT-711), so each carries a byte-identical
copy of that block instead of importing this module; ``tests/test_readonly_sqlite_location.py`` requires the three
copies to stay identical.
"""

from __future__ import annotations

import os
import re
import sqlite3
import urllib.parse
from pathlib import Path

# ---- BEGIN BAT-717 LITERAL-LOCATION CORE (byte-identical in aggie_analytics.readonly_sqlite,
# ---- aggie_analytics.national_population.query and aggie_analytics.national_history.query) ----
_LOCATION_UNSUPPORTED = "DATABASE_LOCATION_UNSUPPORTED"
_LOCATION_NOT_LITERAL = "DATABASE_LOCATION_NOT_LITERAL"
_EXTENDED_PREFIX = "\\\\?\\"
_DEVICE_PREFIX = "\\\\.\\"
_VERBATIM_DRIVE = re.compile(r"\\\\\?\\[A-Za-z]:\\")
_DEVICE_DRIVE = re.compile(r"\\\\\.\\[A-Za-z]:\\")
_DRIVE_ABSOLUTE = re.compile(r"[A-Za-z]:\\")


class _LocationError(ValueError):
    """A database location that cannot be opened as exactly the literal local file it names."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _literal_path(database: str | os.PathLike[str]) -> str:
    """The absolute path naming exactly the local file ``database`` names, in the form SQLite will open.

    Purely lexical on Windows: an unsupported location is refused before any filesystem access."""

    try:
        text = os.fsdecode(os.fspath(database))
    except TypeError as exc:
        raise _LocationError(_LOCATION_UNSUPPORTED, f"not a filesystem path: {database!r}") from exc
    if not text or "\x00" in text:
        raise _LocationError(_LOCATION_UNSUPPORTED, f"an empty path or one holding a NUL character: {text!r}")
    if os.name != "nt":
        return os.path.realpath(text)
    if text[:1] in "\\/" and text[1:2] in ("\\", "/"):
        if _VERBATIM_DRIVE.match(text):
            normal = os.path.abspath(text)
            if normal != text:
                raise _LocationError(_LOCATION_NOT_LITERAL, (
                    f"SQLite would open {normal!r}, not the verbatim {text!r} (a trailing dot, a '.' or '..' "
                    "component or a forward slash in an extended-length path names a different file than SQLite "
                    "opens)"))
            return text
        normal = os.path.abspath(text)
        if _DEVICE_DRIVE.match(normal):
            # \\.\X:\... is the local drive device: Win32 normalizes it like an ordinary path and it names the same
            # file as X:\... -- the spelling SQLite is given.
            return normal[len(_DEVICE_PREFIX):]
        raise _LocationError(_LOCATION_UNSUPPORTED, (
            f"{text!r} is a network share or a device or namespace path; only a local drive path, its native "
            "extended-length form \\\\?\\X:\\... or its local device form \\\\.\\X:\\... is supported"))
    location = os.path.abspath(text)
    if not _DRIVE_ABSOLUTE.match(location):
        raise _LocationError(_LOCATION_UNSUPPORTED, f"{text!r} resolves to {location!r}, not a local drive path")
    return location


def _location_uri(location: str, immutable: bool) -> str:
    """The read-only ``file:`` URI of a literal path, every reserved character escaped."""

    if os.name == "nt" and location.startswith(_EXTENDED_PREFIX):
        body = "file:" + urllib.parse.quote(location, safe="")
    else:
        body = Path(location).as_uri()
    return body + ("?mode=ro&immutable=1" if immutable else "?mode=ro")


def _same_object(opened: str, location: str) -> bool:
    try:
        first, second = os.stat(opened), os.stat(location)
    except (OSError, ValueError):
        return os.path.normcase(opened) == os.path.normcase(location)
    if first.st_ino and second.st_ino:
        return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
    return os.path.normcase(opened) == os.path.normcase(location)


def _verify_opened(conn: sqlite3.Connection, schema: str, location: str) -> str:
    """Confirm that the database SQLite opened as ``schema`` is the file at ``location``; return SQLite's name."""

    opened = {str(row[1]): str(row[2] or "") for row in conn.execute("PRAGMA database_list")}.get(schema)
    if not opened or not _same_object(opened, location):
        raise _LocationError(_LOCATION_NOT_LITERAL, f"SQLite opened {opened!r} as {schema}, not {location!r}")
    return opened


def _connect_literal(database: str | os.PathLike[str], immutable: bool) -> sqlite3.Connection:
    """A read-only connection to exactly the literal file ``database`` names (never created, never writable)."""

    location = _literal_path(database)
    conn = sqlite3.connect(_location_uri(location, immutable), uri=True)
    try:
        _verify_opened(conn, "main", location)
    except BaseException:
        conn.close()
        raise
    return conn
# ---- END BAT-717 LITERAL-LOCATION CORE ----

LOCATION_UNSUPPORTED = _LOCATION_UNSUPPORTED
LOCATION_NOT_LITERAL = _LOCATION_NOT_LITERAL
EXTENDED_PREFIX = _EXTENDED_PREFIX
DEVICE_PREFIX = _DEVICE_PREFIX
_SCHEMA = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class DatabaseLocationError(_LocationError):
    """A database location that cannot be opened as exactly the literal local file it names."""


def _public(exc: _LocationError) -> DatabaseLocationError:
    return exc if isinstance(exc, DatabaseLocationError) else DatabaseLocationError(exc.code, exc.detail)


def literal_path(database: str | os.PathLike[str]) -> str:
    """The absolute path naming exactly the local file ``database`` names, in the form SQLite will open.

    Purely lexical on Windows: an unsupported location is refused before any filesystem access."""

    try:
        return _literal_path(database)
    except _LocationError as exc:
        raise _public(exc) from exc.__cause__


def readonly_uri(database: str | os.PathLike[str], *, immutable: bool = False) -> str:
    """A read-only ``file:`` URI whose path is exactly :func:`literal_path` of ``database``, every reserved character
    escaped; ``immutable=1`` only when the caller deliberately asks for it."""

    return _location_uri(literal_path(database), immutable)


def verify_opened(conn: sqlite3.Connection, schema: str, location: str) -> str:
    """Confirm that the database SQLite opened as ``schema`` is the file at ``location``; return SQLite's name."""

    try:
        return _verify_opened(conn, schema, location)
    except _LocationError as exc:
        raise _public(exc) from None


def connect_readonly(database: str | os.PathLike[str], *, immutable: bool = False) -> sqlite3.Connection:
    """A read-only connection to exactly the literal file ``database`` names (never created, never writable)."""

    try:
        return _connect_literal(database, immutable)
    except _LocationError as exc:
        raise _public(exc) from exc.__cause__


def attach_readonly(conn: sqlite3.Connection, database: str | os.PathLike[str], schema: str, *,
                    immutable: bool = False) -> str:
    """ATTACH exactly the literal file ``database`` names, read-only, as ``schema``; return its literal path.

    The statement carries the URI as a literal (never a bound parameter), so a write guard can verify the target."""

    if not _SCHEMA.fullmatch(schema):
        raise ValueError(f"not a schema name: {schema!r}")
    location = literal_path(database)
    uri = _location_uri(location, immutable).replace("'", "''")
    conn.execute(f"ATTACH DATABASE '{uri}' AS {schema}")
    try:
        verify_opened(conn, schema, location)
    except BaseException:
        try:
            conn.execute(f"DETACH DATABASE {schema}")
        except sqlite3.Error:
            pass
        raise
    return location
