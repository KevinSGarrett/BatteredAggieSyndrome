r"""Read-only explicit consumer of the fixed retrospective 2016-2023 baseline benchmark (BAT-719).

``bas-retrospective-baseline-query --database <canonical\national_retrospective_baseline_2016_2023\sha256\<id>\
national_retrospective_baseline.sqlite> --history-database <accepted national_history.sqlite> --grain score
--season 2019 --team "Texas A&M" --model SMOOTHED_HISTORY_ODDS_V1 --limit 50 --offset 0``

Both databases are selected explicitly; nothing here is a default and no generic forecast consumer becomes active.
Before any row is served the accepted history is verified and pinned, and the benchmark's location, manifest identity,
bytes, schema, meta claims and every record of every table, the summary, the content identity and the contract-defined
identity document are re-derived from that history and the two frozen models
(:class:`aggie_analytics.retrospective_baseline.benchmark.RetrospectiveBenchmark`); any difference is refused with
a stable code (exit 2, ``{"refused": ...}`` on stderr).

Grains: ``feature`` (two oriented views per target), ``estimate`` (target x model x orientation), ``score`` (one
A-oriented record per target and model, scored or explicitly unscored) and ``summary`` (per model and per season,
development partition and pooled scope, plus descriptive smoothed-minus-null differences). Filters: ``--season``,
``--team`` (org:<digits>, bare digits or a team name of the record's own season), ``--contest``, ``--model`` and
``--partition``; paging with ``--limit``/``--offset`` or ``--all`` returns exact totals in payload order. Every
response carries ``RETROSPECTIVE_DATE_ORDER_ONLY_NOT_PIT_NOT_SKILL``; ``--require-pit`` is always refused.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from aggie_analytics.retrospective_baseline import benchmark as bm


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bas-retrospective-baseline-query", allow_abbrev=False,
                                     description="Read-only explicit retrospective 2016-2023 baseline benchmark "
                                                 "(calendar order only; not PIT, not a forecast, no skill claim).")
    parser.add_argument("--database", required=True, type=Path,
                        help="the explicitly selected benchmark database (never a default)")
    parser.add_argument("--history-database", dest="history_database", required=True, type=Path,
                        help="the accepted national history-prefix database the benchmark was built from")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True, choices=list(bm.GRAINS))
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--partition", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: no benchmark row is PIT eligible")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.require_pit:
        raise bm.BenchmarkError("PIT_ELIGIBILITY_NOT_ESTABLISHED",
                                "every benchmark row is RETROSPECTIVE_DATE_ORDER_ONLY_NOT_PIT_NOT_SKILL; calendar "
                                "order is not PIT authority")
    if args.expect_identity is not None and not bm.IDENTITY_RE.match(args.expect_identity):
        raise bm.BenchmarkError("STALE_BENCHMARK_IDENTITY", "--expect-identity must be a SHA-256 identity")
    with bm.RetrospectiveBenchmark(args.database, history_database=args.history_database, manifest=args.manifest,
                                   expect_identity=args.expect_identity) as benchmark:
        return benchmark.query(args.grain, season=args.season, team=args.team, contest=args.contest,
                               model=args.model, partition=args.partition, limit=args.limit, offset=args.offset,
                               all_rows=args.all_rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except bm.BenchmarkError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
