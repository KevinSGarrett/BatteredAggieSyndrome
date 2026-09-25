"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04 AC05 / OBL_NATIONAL_POPULATION_RECONCILIATION: the one program the
2020 membership statement omits while the results route records games for
it, settled against the program's own official schedule.

The population audit found Alcorn State absent from the 2020 membership
statement while the results route recorded six completed 2020-season games
(spring 2021). Alcorn State's official 2020-21 schedule page is read, its
games and their stated results listed, and the disagreement adjudicated by
what the program's own page states. Nothing else is inferred.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
PAGE = "8553644ffb3c"
URL = "https://alcornsports.com/sports/football/schedule/2020-21"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_04_2020_ADJUDICATION.json")
    args = parser.parse_args(argv)
    path = next(p for p in (ATTEMPT / "private" / "acquisition" / "metadata").iterdir()
                if p.name.startswith(PAGE) and p.suffix == ".bin")
    raw = path.read_bytes().decode("utf-8", "replace")
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1\s*>", " ", raw,
                                                                            flags=re.S | re.I))))
    games = [{"date": m.group(1), "venue_side": m.group(2), "opponent": m.group(3).strip(), "stated_result": m.group(4)}
             for m in re.finditer(r"(\w{3} \d{1,2}) \(\w{3}\) / Final [^/]*?\b(at|vs)\s+([A-Z][\w&.' -]+?)\s+(Canceled|W|L)\b",
                                  text)]
    record = re.search(r"Overall (\d+-\d+)", text)
    audit = json.loads((ATTEMPT / "evidence" / "repairs" / "R37_04_POPULATION_AUDIT.json").read_text(encoding="utf-8"))
    finding = audit["ac05_2020_investigation"]["absent_but_the_results_route_says_they_played"]
    all_canceled = bool(games) and all(g["stated_result"] == "Canceled" for g in games)
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-04-AC05",
        "finding": finding, "official_source": {"url": URL, "path": str(path),
                                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                                "title": re.search(r"<title[^>]*>(.*?)</title>", raw, re.S).group(1).strip()},
        "official_games": games, "official_overall_record": record.group(1) if record else None,
        "adjudication": ("RESULTS_ROUTE_RECORDS_CANCELED_GAMES_AS_COMPLETED" if all_canceled
                         else "UNSETTLED_THE_OFFICIAL_PAGE_DOES_NOT_STATE_EVERY_GAME_CANCELED"),
        "consequence": ("The membership statement's omission of Alcorn State for 2020 agrees with the program's own "
                        "schedule: every 2020-season game is stated canceled and the record is 0-0. The results "
                        "route's completed games for Alcorn State are a source error, kept as observations and not "
                        "counted as played.") if all_canceled else None,
        "discrepancies_open_after": 0 if all_canceled else 1,
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("finding",)}, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
