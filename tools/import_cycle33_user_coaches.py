"""Import the preserved user-coaches snapshot into Cycle 33 research tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aggie_analytics.cycle33.query import connect_for_import, load_import
from aggie_analytics.cycle33.user_coaches import coverage_by_year, import_snapshot

DEFAULT_SNAPSHOT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z\source_snapshot"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--database", required=True)
    parser.add_argument("--json-out")
    args = parser.parse_args(argv)
    imported = import_snapshot(Path(args.snapshot))
    conn = connect_for_import(Path(args.database))
    n = load_import(conn, imported)
    summary = {
        "staff_observation_count": imported["staff_observation_count"],
        "queue_row_count": imported["queue_row_count"],
        "role_cell_count": imported["role_cell_count"],
        "loaded_role_cells": n,
        "coverage": coverage_by_year(imported),
        "pit_admitted": False,
        "source_class": imported["source_class"],
    }
    if args.json_out:
        slim = {
            key: imported[key]
            for key in (
                "artifact_type",
                "file_count",
                "staff_file_count",
                "staff_observation_count",
                "role_cell_count",
                "queue_row_count",
                "files",
                "pit_admitted",
                "source_class",
                "importer_version",
            )
        }
        Path(args.json_out).write_text(
            json.dumps(slim, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
