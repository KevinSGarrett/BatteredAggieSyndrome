r"""Read-only explicit consumer of the national observed-weather evidence release 2024 (BAT-731, Cycle #60 TP60-A01).

``bas-weather-evidence-query --database <data>\canonical\national_observed_weather_evidence_2024\sha256\<id>\
national_observed_weather_evidence.sqlite --grain contest-weather [--season 2024] [--contest ncaa:<id>]
[--provider-game <SRC-002 game id>] [--station NNNNNN-NNNNN] [--limit 50] [--offset 0] [--all]
[--manifest <run_manifest.json>] [--expect-identity <id>]`` (also ``python -m aggie_analytics.weather_evidence.query``).

The release database is named explicitly and the run manifest optionally; nothing here is a default and no forecast,
feature or model consumer becomes active. No data root is read. Before any row is served the release's location, run
manifest identity, bytes, schema and meta claims, every record's exact members and JSON types, the complete expected
collection of every grain, every rule the records can re-derive (raw-row decoding, duplicate ranking, candidate order,
distances and the earlier-wins tie rule, discrepancy and unsupported-reason derivations, relations, associations,
source authorities and clocks, and the census), the rebuilt content document, the contract-defined database identity
document and the pinned canonical profile are verified
(:class:`aggie_analytics.weather_evidence.evidence.WeatherEvidence`); any difference is refused with a stable code
(exit 2, ``{"refused": ...}`` on stderr). Both locations pass the BAT-717 literal local-file policy before any
filesystem access; the release is opened read-only and a missing file is never created; no network or device access is
made.

Grains: ``contest-weather`` (all 1,672 parent contests), ``pilot-weather`` (all 920 original pilot rows),
``station-year`` (all 157 captures) and ``source-witness``. Selectors follow the declared matrix (SELECTOR_MATRIX):
``--season`` on every grain, ``--contest`` (exact ncaa:<digits>; bare digits are refused because an NCAA number never
equals a provider number) and ``--provider-game`` (exact SRC-002 game ID) on the contest and pilot grains, and
``--station`` (exact NNNNNN-NNNNN) on every grain. They intersect; an unknown or disjoint valid selection serves no row;
a selector that does not apply to a grain is refused, never ignored. ``--require-pit`` is always refused and no
historical as-of selector exists. Every answer states its clocks explicitly and is RETROSPECTIVE_RESEARCH,
UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED; a station measurement is not a stadium
condition, the provider scheduled time is not the actual kickoff, and catalog venues and roof flags are not historical
effective facts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from aggie_analytics.weather_evidence import evidence as we

EPILOG = ("explicit national observed-weather evidence 2024 (BAT-731): grains contest-weather, pilot-weather, "
          "station-year, source-witness; RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, predictive skill "
          "NOT_ESTABLISHED; observation clock = each NOAA ISD row's UTC time, association clock = the provider "
          "scheduled start (not the actual kickoff); a candidate station measurement is not a stadium condition; "
          "catalog venues and roof flags are not historical effective facts; not a forecast input")


class _Parser(argparse.ArgumentParser):
    """Argument errors become controlled refusals (``ARGUMENT_INVALID``) instead of a usage dump."""

    def error(self, message: str) -> NoReturn:
        raise we.WeatherError("ARGUMENT_INVALID", message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="bas-weather-evidence-query", allow_abbrev=False, epilog=EPILOG,
                     description="Read-only explicit national observed-weather evidence release 2024 (retrospective "
                                 "research only: not PIT admitted, not a forecast, not stadium conditions, no skill "
                                 "claim).")
    parser.add_argument("--database", required=True, type=Path,
                        help="the explicitly selected release database of a verified identity directory")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="the release run manifest (default: the manifests sibling of the identity directory)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True, choices=list(we.GRAINS))
    parser.add_argument("--season", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--provider-game", dest="provider_game", default=None)
    parser.add_argument("--station", default=None)
    parser.add_argument("--limit", default="50")
    parser.add_argument("--offset", default="0")
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the release is research only and never PIT admitted")
    return parser


def _integer(text: Any, code: str, what: str) -> int:
    value = str(text).strip()
    body = value[1:] if value.startswith("-") else value
    if not body.isascii() or not body.isdigit() or len(body) > 12:
        raise we.WeatherError(code, f"{what} must be an integer, got {text!r}")
    return int(value)


def run(args: argparse.Namespace, anchors: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every malformed or inapplicable selection is refused before any file is read; then the release is verified
    completely and queried."""
    if args.require_pit:
        raise we.WeatherError("WEATHER_PIT_NOT_ADMITTED", "the release is RETROSPECTIVE_RESEARCH and never PIT "
                                                          "admitted; no historical as-of claim is supported")
    season = None if args.season is None else _integer(args.season, "SEASON_INVALID", "season")
    limit = _integer(args.limit, "LIMIT_INVALID", "limit")
    offset = _integer(args.offset, "OFFSET_INVALID", "offset")
    if limit < 0:
        raise we.WeatherError("NEGATIVE_LIMIT", "limit must be zero or positive")
    if offset < 0:
        raise we.WeatherError("NEGATIVE_OFFSET", "offset must be zero or positive")
    we.WeatherEvidence.filters(args.grain, season=season, contest=args.contest, provider_game=args.provider_game,
                               station=args.station)
    if args.expect_identity is not None and not we.IDENTITY_RE.match(args.expect_identity):
        raise we.WeatherError("STALE_WEATHER_IDENTITY", "--expect-identity must be a SHA-256 identity")
    with we.WeatherEvidence(args.database, manifest=args.manifest, expect_identity=args.expect_identity,
                            anchors=anchors) as selected:
        return selected.query(args.grain, season=season, contest=args.contest, provider_game=args.provider_game,
                              station=args.station, limit=limit, offset=offset, all_rows=args.all_rows)


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
    except we.WeatherError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    _write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    # ``python -m`` runs this file as __main__; delegate to the package module so every shared class has one identity.
    from aggie_analytics.weather_evidence import query as _package_query  # noqa: PLC0415

    raise SystemExit(_package_query.main())
