r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Reproduce V37-01 against a chosen source tree and the *delivered* databases.

The finding has two halves and they fail in opposite directions, so both are
probed:

* the delivered Cycle 36 national release makes the installed entry point
  exit non-zero, because its schema is detected as unknown;
* the published Cycle 35 release makes it exit *zero* with an empty list,
  which is worse: a query that cannot be answered returned an answer.

Every database is opened read-only and immutable. Nothing is written except
the receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def table_census(database: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{database.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        names = [
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        return {
            name: int(conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
            for name in names
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True)
    parser.add_argument("--database", action="append", required=True, metavar="LABEL=PATH")
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    src = Path(args.src).resolve()
    import_root = src / "src"
    result: dict[str, Any] = {
        "label": args.label,
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "source_tree": str(src),
        "python": sys.version.split()[0],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "databases": {},
    }

    for spec in args.database:
        label, _, raw = spec.partition("=")
        database = Path(raw).resolve()
        entry: dict[str, Any] = {
            "path": str(database),
            "exists": database.is_file(),
            "sha256": sha256_file(database),
            "bytes": database.stat().st_size if database.is_file() else None,
        }
        if database.is_file():
            entry["tables"] = table_census(database)
            detect = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    "import sys, sqlite3, json;"
                    "sys.path.insert(0, sys.argv[1]);"
                    "from aggie_analytics.cycle35 import query as q;"
                    "c = sqlite3.connect('file:' + sys.argv[2] + "
                    "'?mode=ro&immutable=1', uri=True);"
                    "print(json.dumps({'schema_kind': q.schema_kind(c)}))",
                    str(import_root),
                    database.as_posix(),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            entry["schema_detection"] = {
                "exit_code": detect.returncode,
                "stdout": (detect.stdout or "").strip(),
                "stderr": (detect.stderr or "").strip()[-600:],
            }

            probes: dict[str, Any] = {}
            for name, argv in (
                ("unresolved", ["--database", str(database), "--unresolved"]),
                (
                    "team_season",
                    ["--database", str(database), "--team", "Texas A&M", "--season", "2024"],
                ),
            ):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-c",
                        "import sys;"
                        "sys.path.insert(0, sys.argv[1]);"
                        "from aggie_analytics.cycle33.query import main;"
                        "raise SystemExit(main(sys.argv[2:]))",
                        str(import_root),
                        *argv,
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                stdout = completed.stdout or ""
                payload: Any = None
                try:
                    payload = json.loads(stdout)
                except ValueError:
                    payload = None
                probes[name] = {
                    "argv": argv,
                    "exit_code": completed.returncode,
                    "stdout_head": stdout[:400],
                    "stderr_tail": (completed.stderr or "").strip()[-600:],
                    "parsed_row_count": len(payload) if isinstance(payload, list) else None,
                    "returned_empty_list_with_exit_zero": (
                        completed.returncode == 0
                        and isinstance(payload, list)
                        and not payload
                    ),
                }
            entry["cli_probes"] = probes
        result["databases"][label] = entry

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out, json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for label, entry in result["databases"].items():
        if not entry["exists"]:
            print(f"{label}: ABSENT {entry['path']}")
            continue
        detected = entry["schema_detection"]["stdout"]
        print(f"{label}: schema={detected}")
        for name, probe in entry["cli_probes"].items():
            print(
                f"    {name:<12} exit={probe['exit_code']} "
                f"rows={probe['parsed_row_count']} "
                f"silent_empty={probe['returned_empty_list_with_exit_zero']}"
            )
    print("receipt:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
