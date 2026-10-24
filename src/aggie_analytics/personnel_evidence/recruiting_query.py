r"""The explicit ``--recruiting-evidence`` mode of ``bas-personnel-evidence-query`` (BAT-735, Cycle #64 TP64-A01).

``bas-personnel-evidence-query --recruiting-evidence <data>\canonical\national_recruiting_evidence_2010_2017\sha256\<id>\
national_recruiting_evidence.sqlite --grain recruiting-observation [--season 2014] [--team team_<32 hex>]
[--player player_<32 hex>] [--recruit <digits>] [--limit 50] [--offset 0] [--all] [--manifest <run_manifest.json>]
[--expect-identity <id>]`` (also ``python -m aggie_analytics.personnel_evidence.query``).

:func:`aggie_analytics.personnel_evidence.query.main` routes here only when an argument is exactly
``--recruiting-evidence`` or ``--recruiting-evidence=<path>``, before the unchanged legacy parser; every other invocation
keeps the legacy parser, answers and refusals. This parser keeps every value as the given text (an explicit empty value
is never read as absent), refuses a repeated option, and every argument error is a controlled ARGUMENT_INVALID refusal.
Then, before any file is read, the frozen precedence of :data:`recruiting.PRECEDENCE` applies: a supplied --database
(even empty) is RECRUITING_MODE_CONFLICT, --require-pit RECRUITING_PIT_NOT_ADMITTED, any supplied --as-of (even empty)
AS_OF_STATE_NOT_SUPPORTED, then the grain, the season, team, player and recruit values, their applicability, the
--all/explicit paging conflict, the limit, the offset and the expected identity; only then the database and manifest
location policy and the complete release verification (:class:`recruiting.RecruitingEvidence`). Every refusal is exit 2
with one JSON object ``{"refused": CODE, "error": text}`` on stderr and nothing on stdout; an answer is one canonical
UTF-8 JSON line. No data root is read and no network or device access is made.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn, Sequence

from aggie_analytics.personnel_evidence import recruiting as rc

OPTION = "--recruiting-evidence"
EPILOG = ("explicit private national recruiting evidence 2010-2017 (BAT-735): grains recruiting-observation, "
          "recruiting-qualification, recruiting-partition, recruiting-source, recruiting-summary; RETROSPECTIVE_RESEARCH, "
          "UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, predictive skill NOT_ESTABLISHED; the 2026-08-10 capture clocks are not "
          "historical known-at; a program correspondence is not membership, commitment, signing or enrollment; a person "
          "correspondence is not a roster fact; the 34 requested cells are not national coverage")


class _Parser(argparse.ArgumentParser):
    """Argument errors become controlled refusals (``ARGUMENT_INVALID``) instead of a usage dump."""

    def error(self, message: str) -> NoReturn:
        raise rc.RecruitingError("ARGUMENT_INVALID", message)


class _Once(argparse.Action):
    """A value option given at most once: a repetition would silently replace the first value."""

    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace, values: Any,
                 option_string: str | None = None) -> None:
        marker = "_given_" + self.dest
        if getattr(namespace, marker, False):
            raise rc.RecruitingError("ARGUMENT_INVALID", f"{option_string} given more than once")
        setattr(namespace, marker, True)
        setattr(namespace, self.dest, values)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="bas-personnel-evidence-query --recruiting-evidence", allow_abbrev=False, epilog=EPILOG,
                     description="Explicit private national recruiting evidence release 2010-2017 (retrospective "
                                 "source qualification only: not PIT admitted, not roster, enrollment, commitment or "
                                 "signing evidence, no talent prior, no skill claim).")
    parser.add_argument(OPTION, dest="recruiting_evidence", required=True, action=_Once,
                        help="the explicitly selected release database of a verified identity directory (never a "
                             "default)")
    parser.add_argument("--manifest", default=None, action=_Once,
                        help="the release run manifest (default: the manifests sibling of the identity directory)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None, action=_Once)
    parser.add_argument("--grain", required=True, action=_Once,
                        help="recruiting-observation, recruiting-qualification, recruiting-partition, "
                             "recruiting-source or recruiting-summary")
    parser.add_argument("--season", default=None, action=_Once, help="captured request season (four digits)")
    parser.add_argument("--team", default=None, action=_Once, help="qualified canonical program team_<32 hex>")
    parser.add_argument("--player", default=None, action=_Once, help="qualified canonical person player_<32 hex>")
    parser.add_argument("--recruit", default=None, action=_Once, help="exact source recruit ID (1-12 digits)")
    parser.add_argument("--limit", default=None, action=_Once, help="page size (default 50)")
    parser.add_argument("--offset", default=None, action=_Once, help="page offset (default 0)")
    parser.add_argument("--all", dest="all_rows", action="store_true", help="every selected row (no paging)")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the release is research only and never PIT admitted")
    parser.add_argument("--as-of", dest="as_of", default=None, action=_Once,
                        help="refused: no historical as-of state exists for this release")
    parser.add_argument("--database", dest="conflict_database", default=None, action=_Once,
                        help="refused here: --database selects the legacy personnel release (mode conflict)")
    return parser


def run(args: argparse.Namespace, anchors: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every ambiguous, unsupported, malformed or inapplicable selection is refused before any file is read, in the
    frozen precedence; then the release is verified completely and queried."""
    if args.conflict_database is not None:
        raise rc.RecruitingError("RECRUITING_MODE_CONFLICT", f"--database cannot be combined with {OPTION} "
                                                             "(ambiguous mode selection)")
    if args.require_pit:
        raise rc.RecruitingError("RECRUITING_PIT_NOT_ADMITTED", "the release is RETROSPECTIVE_RESEARCH and never PIT "
                                                                "admitted; no historical known-at claim is supported")
    if args.as_of is not None:
        raise rc.RecruitingError("AS_OF_STATE_NOT_SUPPORTED", "no historical as-of state exists: the source carries no "
                                                              "rating version, commitment, signing or enrollment time")
    rc.validate_selection(args.grain, season=args.season, team=args.team, player=args.player, recruit=args.recruit)
    limit = 50 if args.limit is None else args.limit
    offset = 0 if args.offset is None else args.offset
    rc.validate_paging(limit, offset, args.all_rows, limit_given=args.limit is not None,
                       offset_given=args.offset is not None)
    rc.validate_expected_identity(args.expect_identity)
    with rc.RecruitingEvidence(args.recruiting_evidence, manifest=args.manifest, expect_identity=args.expect_identity,
                               anchors=anchors) as selected:
        return selected.query(args.grain, season=args.season, team=args.team, player=args.player,
                              recruit=args.recruit, limit=limit, offset=offset, all_rows=args.all_rows,
                              limit_given=args.limit is not None, offset_given=args.offset is not None)


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
    except rc.RecruitingError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    _write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0
