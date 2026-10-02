r"""Cycle #37 — Attempt #5 — keep a command's whole standard output without an uncompressed copy of it in the log.

    python -S -B attempt05_stream_stdout.py <gzip target> <echo limit bytes> <summary json> -- <command...>

Runs ``<command>`` with its standard error inherited. Standard output up to the echo limit is passed through
unchanged, so the lane's command log is what it would have been. A larger output goes instead, byte for byte,
into the new gzip target and is not repeated in the log. Either way the size and SHA-256 of the raw bytes are
written to the new summary file. The exit code is the command's. The helper uses only the standard library and
is started with ``-S``, so it installs nothing of its own. The command inherits the lane's environment
unchanged, including the write guard it installs for itself. Nothing is overwritten: both files are
created exclusively.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys


def main(argv: list[str]) -> int:
    if len(argv) < 5 or argv[3] != "--":
        sys.stderr.write(__doc__.split("\n\n")[1] + "\n")
        return 2
    target, limit, summary, command = argv[0], int(argv[1]), argv[2], argv[4:]
    digest, size, held, out = hashlib.sha256(), 0, [], None
    child = subprocess.Popen(command, stdout=subprocess.PIPE)
    for chunk in iter(lambda: child.stdout.read(1 << 20), b""):
        digest.update(chunk)
        size += len(chunk)
        if out is None and size <= limit:
            held.append(chunk)
            continue
        if out is None:
            out = gzip.open(target, "xb")
            out.writelines(held)
            held = []
        out.write(chunk)
    code = child.wait()
    if out is None:
        sys.stdout.buffer.write(b"".join(held))
        sys.stdout.buffer.flush()
    else:
        out.close()
        sys.stderr.write(f"[standard output: {size} bytes, sha256 {digest.hexdigest()}, kept whole in {target}]\n")
    with open(summary, "x", encoding="utf-8", newline="\n") as handle:
        json.dump({"exit": code, "stdout_bytes": size, "stdout_sha256": digest.hexdigest(), "echo_limit": limit,
                   "echoed_to_log": out is None, "streamed_to": target if out is not None else None}, handle)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
