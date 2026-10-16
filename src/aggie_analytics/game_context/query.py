r"""Read-only explicit consumer of the national 2023 game-context release (BAT-729, Cycle #58 TP58-A01).

``bas-game-context-query --database <data>\canonical\national_game_context_2023\sha256\<id>\national_game_context.sqlite
--data-root <data> --grain contest-context [--season 2023] [--contest ncaa:<id>] [--team org:<id>] [--limit 50]
[--offset 0] [--all]`` (also ``python -m aggie_analytics.game_context.query``).

The release database and the data root holding its pinned inputs are both named explicitly; nothing here is a default
and no forecast or feature consumer becomes active. Before any row is served the release's location, run manifest
identity, bytes, schema and meta claims, every pinned input under the data root (each by its contract SHA-256) and every
record of every table, the census, the content identity and the contract-defined identity document are re-derived and
compared (:class:`aggie_analytics.game_context.context.GameContext`); any difference is refused with a stable code (exit
2, ``{"refused": ...}`` on stderr). Every path passes the BAT-717 literal local-file policy before any filesystem
access; the release is opened read-only and a missing file is never created; no network or device access is made.

Grains: ``contest-context`` (one record per accepted 2023 target), ``team-context`` (two oriented records per target),
``context-witness`` (every source and qualification witness) and ``context-score-summary`` (descriptive strata of the
frozen C56 scores; with ``--contest``/``--team`` re-derived over exactly the selected games). Selectors: ``--season``
(2023 is audited; any other season is reported NOT_YET_AUDITED with no row), ``--contest`` (ncaa:<digits>), ``--team``
(org:<digits>), ``--orientation`` (A or B; team and witness grains), ``--source`` (witness grain), ``--model`` (summary
and witness grains) and ``--family`` (summary grain); they intersect, and an unknown or disjoint valid selection serves
no row. Malformed or inapplicable selectors are refused before any file is read. ``--require-pit`` is always refused.
Every answer is RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED; reference
distance is geometry, not travel; calendar intervals are not rest.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from aggie_analytics.game_context import context as gc

EPILOG = ("explicit national 2023 game context (BAT-729): grains contest-context, team-context, context-witness, "
          "context-score-summary; RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, predictive skill "
          "NOT_ESTABLISHED; later-observed reference geography is not historically effective and reference distance "
          "is not travel; calendar intervals are not physiological rest; score strata are descriptive exposed-2023 "
          "slices, not effects, a blind test or a skill claim")


class _Parser(argparse.ArgumentParser):
    """Argument errors become controlled refusals (``ARGUMENT_INVALID``) instead of a usage dump."""

    def error(self, message: str) -> NoReturn:
        raise gc.ContextError("ARGUMENT_INVALID", message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="bas-game-context-query", allow_abbrev=False, epilog=EPILOG,
                     description="Read-only explicit national 2023 game-context release (retrospective research only: "
                                 "not PIT admitted, not a forecast, no travel, rest, home-field or skill claim).")
    parser.add_argument("--database", required=True, type=Path,
                        help="the explicitly selected release database of a verified identity directory")
    parser.add_argument("--data-root", dest="data_root", required=True, type=Path,
                        help="the data root holding every pinned input at the contract's relative locators")
    parser.add_argument("--manifest", type=Path, default=None, help="the release run manifest (default: beside)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True, choices=list(gc.GRAINS))
    parser.add_argument("--season", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--orientation", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--family", default=None)
    parser.add_argument("--limit", default="50")
    parser.add_argument("--offset", default="0")
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the context is research only and never PIT admitted")
    return parser


def _integer(text: Any, code: str, what: str) -> int:
    value = str(text).strip()
    body = value[1:] if value.startswith("-") else value
    if not body.isascii() or not body.isdigit() or len(body) > 12:
        raise gc.ContextError(code, f"{what} must be an integer, got {text!r}")
    return int(value)


def run(args: argparse.Namespace, anchors: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every malformed or inapplicable selection is refused before any file is read; then the release and its pinned
    inputs are verified completely and queried."""
    if args.require_pit:
        raise gc.ContextError("CONTEXT_PIT_NOT_ADMITTED", "the context is RETROSPECTIVE_RESEARCH and never PIT admitted")
    season = None if args.season is None else _integer(args.season, "SEASON_INVALID", "season")
    limit = _integer(args.limit, "LIMIT_INVALID", "limit")
    offset = _integer(args.offset, "OFFSET_INVALID", "offset")
    if limit < 0:
        raise gc.ContextError("NEGATIVE_LIMIT", "limit must be zero or positive")
    if offset < 0:
        raise gc.ContextError("NEGATIVE_OFFSET", "offset must be zero or positive")
    gc.GameContext.filters(args.grain, season=season, contest=args.contest, team=args.team,
                           orientation=args.orientation, source=args.source, model=args.model, family=args.family)
    if args.expect_identity is not None and not gc.IDENTITY_RE.match(args.expect_identity):
        raise gc.ContextError("STALE_CONTEXT_IDENTITY", "--expect-identity must be a SHA-256 identity")
    with gc.GameContext(args.database, data_root=args.data_root, manifest=args.manifest,
                        expect_identity=args.expect_identity, anchors=anchors) as selected:
        return selected.query(args.grain, season=season, contest=args.contest, team=args.team,
                              orientation=args.orientation, source=args.source, model=args.model, family=args.family,
                              limit=limit, offset=offset, all_rows=args.all_rows)


def _write(text: str) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        sys.stdout.flush()
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)


def main(argv: Sequence[str] | None = None, *, anchors: dict[str, Any] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        args = build_parser().parse_args(tokens)
        result = run(args, anchors)
    except gc.ContextError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    _write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    # ``python -m`` runs this file as __main__; delegate to the package module so every shared class has one identity.
    from aggie_analytics.game_context import query as _package_query  # noqa: PLC0415

    raise SystemExit(_package_query.main())
