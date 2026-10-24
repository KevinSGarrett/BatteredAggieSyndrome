r"""Read-only explicit consumer of the national personnel evidence release 2004-2022 (BAT-730, Cycle #59 TP59-A01).

``bas-personnel-evidence-query --database <data>\canonical\national_personnel_evidence_2004_2022\sha256\<id>\
national_personnel_evidence.sqlite --grain roster-membership [--season 2019] [--team team_<32 hex>]
[--program org:<id>] [--player player_<32 hex>] [--limit 50] [--offset 0] [--all] [--manifest <run_manifest.json>]
[--expect-identity <id>]`` (also ``python -m aggie_analytics.personnel_evidence.query``).

The release database is named explicitly and the run manifest optionally; nothing here is a default and no forecast,
feature or model consumer becomes active. No data root is read. Before any row is served the release's location, run
manifest identity, bytes, schema and meta claims, every record's exact members and JSON types, the complete expected
collection of every grain, every rule the records can re-derive (returning sets, rates and shares, foreign keys, census
associations, coverage counts, duplicate diagnoses, witnesses and the census), the rebuilt content document, the
contract-defined database identity document and the pinned canonical profile are verified
(:class:`aggie_analytics.personnel_evidence.evidence.PersonnelEvidence`); any difference is refused with a stable code
(exit 2, ``{"refused": ...}`` on stderr). Both locations pass the BAT-717 literal local-file policy before any
filesystem access; the release is opened read-only and a missing file is never created; no network or device access is
made.

Grains: ``roster-membership``, ``roster-exclusion``, ``program-season-coverage``, ``returning-component``,
``returning-summary`` and ``source-witness``. Selectors follow the declared matrix (SELECTOR_MATRIX): ``--season`` on
every grain, ``--team`` (exact canonical team ID) and ``--player`` (exact canonical player ID) where meaningful, and
``--program`` (source-qualified org:<id>, bare digits read as org:<digits>) on the coverage, membership and returning
grains. They intersect; an unknown or disjoint valid selection serves no row; a selector that does not apply to a grain
is refused, never ignored. ``--require-pit`` is always refused and no historical as-of selector exists. Every answer
states the source time explicitly and is RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill
NOT_ESTABLISHED; season roster presence is not completeness or availability, and a seasonal arrival or departure is not
a transfer episode.

An argument that is exactly ``--recruiting-evidence`` or ``--recruiting-evidence=<path>`` routes the whole invocation,
before this parser, to the explicit private recruiting evidence mode (:mod:`.recruiting_query`, BAT-735); every other
invocation is unchanged, and the legacy ``--help`` gains only the one appended paragraph naming that mode.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from aggie_analytics.personnel_evidence import evidence as pe

EPILOG = ("explicit national personnel evidence 2004-2022 (BAT-730): grains roster-membership, roster-exclusion, "
          "program-season-coverage, returning-component, returning-summary, source-witness; RETROSPECTIVE_RESEARCH, "
          "UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, predictive skill NOT_ESTABLISHED; source clock 2023-05-05T03:50:21Z "
          "(repository commit, season grain only); roster presence is not completeness, availability, depth, starter, "
          "injury or eligibility; seasonal arrival/departure is not a transfer episode")
#: The explicit BAT-735 recruiting evidence mode option and the one paragraph the legacy help appends (TP64 section 5).
RECRUITING_OPTION = "--recruiting-evidence"
RECRUITING_HELP_PARAGRAPH = (
    "Explicit --recruiting-evidence <database> selects the private 2010-2017 recruiting evidence release: "
    "recruiting-observation, recruiting-qualification, recruiting-partition, recruiting-source and recruiting-summary. "
    "This mode is RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW and PIT_NOT_ADMITTED; predictive skill is NOT_ESTABLISHED.")


class _Parser(argparse.ArgumentParser):
    """Argument errors become controlled refusals (``ARGUMENT_INVALID``) instead of a usage dump."""

    def error(self, message: str) -> NoReturn:
        raise pe.PersonnelError("ARGUMENT_INVALID", message)

    def format_help(self) -> str:
        """The accepted help, byte for byte, then one blank line, the recruiting mode paragraph and one newline."""
        return super().format_help() + "\n" + RECRUITING_HELP_PARAGRAPH + "\n"


def recruiting_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit recruiting evidence option (exactly, or as
    ``--recruiting-evidence=<path>``); a substring inside another option's value never routes."""
    return any(token == RECRUITING_OPTION or token.startswith(RECRUITING_OPTION + "=") for token in argv)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="bas-personnel-evidence-query", allow_abbrev=False, epilog=EPILOG,
                     description="Read-only explicit national personnel evidence release 2004-2022 (retrospective "
                                 "research only: not PIT admitted, not availability, not a transfer episode, no skill "
                                 "claim).")
    parser.add_argument("--database", required=True, type=Path,
                        help="the explicitly selected release database of a verified identity directory")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="the release run manifest (default: the manifests sibling of the identity directory)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True, choices=list(pe.GRAINS))
    parser.add_argument("--season", default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--program", default=None)
    parser.add_argument("--player", default=None)
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
        raise pe.PersonnelError(code, f"{what} must be an integer, got {text!r}")
    return int(value)


def run(args: argparse.Namespace, anchors: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every malformed or inapplicable selection is refused before any file is read; then the release is verified
    completely and queried."""
    if args.require_pit:
        raise pe.PersonnelError("PERSONNEL_PIT_NOT_ADMITTED", "the release is RETROSPECTIVE_RESEARCH and never PIT "
                                                              "admitted; no historical as-of claim is supported")
    season = None if args.season is None else _integer(args.season, "SEASON_INVALID", "season")
    limit = _integer(args.limit, "LIMIT_INVALID", "limit")
    offset = _integer(args.offset, "OFFSET_INVALID", "offset")
    if limit < 0:
        raise pe.PersonnelError("NEGATIVE_LIMIT", "limit must be zero or positive")
    if offset < 0:
        raise pe.PersonnelError("NEGATIVE_OFFSET", "offset must be zero or positive")
    pe.PersonnelEvidence.filters(args.grain, season=season, team=args.team, program=args.program, player=args.player)
    if args.expect_identity is not None and not pe.IDENTITY_RE.match(args.expect_identity):
        raise pe.PersonnelError("STALE_PERSONNEL_IDENTITY", "--expect-identity must be a SHA-256 identity")
    with pe.PersonnelEvidence(args.database, manifest=args.manifest, expect_identity=args.expect_identity,
                              anchors=anchors) as selected:
        return selected.query(args.grain, season=season, team=args.team, program=args.program, player=args.player,
                              limit=limit, offset=offset, all_rows=args.all_rows)


def _write(text: str) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        sys.stdout.flush()
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)


def main(argv: Sequence[str] | None = None, *, anchors: dict[str, Any] | None = None,
         recruiting_anchors: dict[str, Any] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if recruiting_mode(tokens):
        from aggie_analytics.personnel_evidence import recruiting_query  # noqa: PLC0415 - explicit option only

        return recruiting_query.main(tokens, anchors=recruiting_anchors)
    try:
        args = build_parser().parse_args(tokens)
        result = run(args, anchors)
    except pe.PersonnelError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    _write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    # ``python -m`` runs this file as __main__; delegate to the package module so every shared class has one identity.
    from aggie_analytics.personnel_evidence import query as _package_query  # noqa: PLC0415

    raise SystemExit(_package_query.main())
