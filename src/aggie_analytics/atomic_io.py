"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Drop-in atomic replacements for ``Path.write_text``, ``Path.write_bytes`` and
``with Path.open("w" | "wb") as f`` (U37-11).

``Path.write_text`` opens its target with ``O_TRUNC``: the old content is gone
the moment the handle opens, so a kill, a crash or a full disk part-way
through leaves a truncated file and no original -- the zero-byte canonical
inventory of 2026-09-22 is this failure. These helpers write the new bytes to
a temporary file in the same directory and ``os.replace`` it over the target,
so a reader sees the old bytes or the new bytes, never a prefix.

They change nothing else:

* the temporary file is written by the very call being replaced
  (``Path.write_text`` / ``write_bytes`` / ``open`` with the caller's
  encoding, errors and newline), so the bytes are identical to what the plain
  call would have written, and a test that patches ``Path.write_text`` still
  intercepts the write;
* a missing parent directory raises ``FileNotFoundError`` as before, and no
  directory is created;
* the return value is the plain call's;
* a symbolic link is written through to its target, as the plain call does;
* an object that is not a ``pathlib.Path`` gets its own method unchanged.

The module is standard-library only so any module can import it without an
import cycle.
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import stat
import tempfile
import time
from typing import IO, Any, Iterator

_UMASK = os.umask(0)
os.umask(_UMASK)


def _destination(path: pathlib.Path) -> pathlib.Path:
    return path.resolve() if path.is_symlink() else path


def _temporary(target: pathlib.Path) -> pathlib.Path:
    # "~" plus eight random characters: no longer than most target names, so a
    # write that fits the path-length budget does not overflow it here.
    handle, name = tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")
    os.close(handle)
    return pathlib.Path(name)


def _commit(temporary: pathlib.Path, target: pathlib.Path) -> None:
    with open(temporary, "rb+") as stream:
        os.fsync(stream.fileno())
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode)
    except FileNotFoundError:
        mode = 0o666 & ~_UMASK
    os.chmod(temporary, mode)
    # Windows can hold a just-written file briefly (scanners, the indexer);
    # a bounded retry keeps that from failing a write the plain call made.
    for attempt in range(6):
        try:
            os.replace(temporary, target)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))


def _discard(temporary: pathlib.Path) -> None:
    try:
        temporary.unlink()
    except OSError:
        pass


def write_text(path: Any, *args: Any, **kwargs: Any) -> int:
    """``path.write_text(*args, **kwargs)``, replaced atomically; the arguments pass through unchanged."""

    if not isinstance(path, pathlib.Path):
        return path.write_text(*args, **kwargs)
    target = _destination(path)
    temporary = _temporary(target)
    try:
        written = temporary.write_text(*args, **kwargs)
        _commit(temporary, target)
    except BaseException:
        _discard(temporary)
        raise
    return written


def write_bytes(path: Any, *args: Any, **kwargs: Any) -> int:
    """``path.write_bytes(*args, **kwargs)``, replaced atomically; the arguments pass through unchanged."""

    if not isinstance(path, pathlib.Path):
        return path.write_bytes(*args, **kwargs)
    target = _destination(path)
    temporary = _temporary(target)
    try:
        written = temporary.write_bytes(*args, **kwargs)
        _commit(temporary, target)
    except BaseException:
        _discard(temporary)
        raise
    return written


@contextlib.contextmanager
def open_write(path: Any, *args: Any, **kwargs: Any) -> Iterator[IO[Any]]:
    """``with path.open(*args, **kwargs) as f`` for a truncating write mode, committed atomically on success."""

    mode = args[0] if args else kwargs.get("mode", "r")
    if str(mode).replace("t", "").replace("b", "") != "w":
        raise ValueError(f"open_write replaces only truncating writes, not mode {mode!r}")
    if not isinstance(path, pathlib.Path):
        with path.open(*args, **kwargs) as stream:
            yield stream
        return
    target = _destination(path)
    temporary = _temporary(target)
    try:
        with temporary.open(*args, **kwargs) as stream:
            yield stream
        _commit(temporary, target)
    except BaseException:
        _discard(temporary)
        raise
