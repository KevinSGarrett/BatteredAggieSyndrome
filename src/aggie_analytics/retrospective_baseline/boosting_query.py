r"""The explicit ``--boosting-comparison`` mode of ``bas-retrospective-baseline-query`` (BAT-736, Cycle #65 TP65-A01).

``bas-retrospective-baseline-query --boosting-comparison <canonical\national_shallow_boosting_comparison_2016_2023\
sha256\<id>\national_shallow_boosting_comparison.sqlite> --grain {tree-feature,tree-parameter,tree-estimate,tree-score,
tree-summary} [--season] [--team] [--contest] [--model] [--partition] [--slice (summary)] [--limit] [--offset] [--all]
[--manifest] [--expect-identity]``

Routed by :func:`aggie_analytics.retrospective_baseline.query.main` before the legacy parser whenever the exact option
token (or ``--boosting-comparison=<value>``) is present; without it every legacy invocation, answer, refusal and the
legacy help (plus exactly one appended paragraph) are unchanged. Every argument error is a controlled ARGUMENT_INVALID
refusal; another release mode's option is TREE_MODE_CONFLICT; ``--require-pit`` is TREE_PIT_NOT_ADMITTED and every
provided ``--as-of`` (empty included) is AS_OF_STATE_NOT_SUPPORTED before any parse; then grain, selector values,
applicability, paging and the expected identity are validated before any file is read (the frozen
:data:`boosting_comparison.PRECEDENCE`), and only then is the release verified completely and queried. A refusal is
exit 2 with nothing on stdout and one JSON object ``{"refused": <code>, "error": <detail>}`` on stderr. Standard library
only: no modeling package is imported.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from aggie_analytics.retrospective_baseline import boosting_comparison as bc

OPTION = "--boosting-comparison"
HELP_PARAGRAPH = ("Explicit --boosting-comparison <database> selects the private 2016-2023 shallow-tree research "
                  "comparison: tree-feature, tree-parameter, tree-estimate, tree-score and tree-summary. This mode is "
                  "RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW and PIT_NOT_ADMITTED; predictive skill is NOT_ESTABLISHED.")
#: Every other release mode's option (and the legacy database options): refused as TREE_MODE_CONFLICT.
CONFLICTS = ("--database", "--history-database", "--population-database", "--reference-comparison",
             "--personnel-association", "--context-association", "--prospective-preview", "--prospective-shadow",
             "--schedule-evidence")
_DEFAULT = object()


def boosting_mode(argv: Sequence[Any]) -> bool:
    """Whether an invocation names the explicit option exactly (or as ``--boosting-comparison=<value>``); a substring
    inside another option's value never routes."""
    return any(type(token) is str and (token == OPTION or token.startswith(OPTION + "=")) for token in argv)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise bc.BoostingError("ARGUMENT_INVALID", "the arguments do not follow the --boosting-comparison grammar")


def build_parser() -> argparse.ArgumentParser:
    """The mode's own parser. Values are kept as the given text, so an explicit empty value is refused by its own rule,
    never read as absent."""
    parser = _Parser(prog="bas-retrospective-baseline-query --boosting-comparison", allow_abbrev=False,
                     description="Explicit immutable national frozen shallow-tree comparison 2016-2023 (research only: "
                                 "RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, not a forecast, not "
                                 "calibrated, predictive skill NOT_ESTABLISHED, no champion or causal claim).",
                     epilog=HELP_PARAGRAPH)
    parser.add_argument(OPTION, dest="boosting_comparison", required=True,
                        help="the explicitly selected release database of a verified identity directory (never a "
                             "default)")
    parser.add_argument("--manifest", default=None, help="the release run manifest (default: beside the release)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True, help="tree-feature, tree-parameter, tree-estimate, tree-score or "
                                                       "tree-summary")
    parser.add_argument("--season", default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--partition", default=None)
    parser.add_argument("--slice", dest="slice_id", default=None, help="summary grain only (default NATIONAL)")
    parser.add_argument("--limit", default=None, help="page size (default 50)")
    parser.add_argument("--offset", default=None, help="page offset (default 0)")
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the comparison is research only and never PIT admitted")
    parser.add_argument("--as-of", dest="as_of", default=None,
                        help="refused: no as-of, cutoff or known-at state exists for this comparison")
    for flag in CONFLICTS:
        parser.add_argument(flag, dest="conflict_" + flag.lstrip("-").replace("-", "_"), default=None)
    return parser


def run(args: argparse.Namespace, anchors: Any = _DEFAULT) -> dict[str, Any]:
    """The frozen precedence: mode conflicts, --require-pit, --as-of, then every selection, paging and identity rule
    before any file is read; then the complete verification and the query."""
    conflicts = [name[len("conflict_"):] for name, value in sorted(vars(args).items())
                 if name.startswith("conflict_") and value is not None]
    if conflicts:
        raise bc.BoostingError("TREE_MODE_CONFLICT", f"{conflicts} cannot be combined with {OPTION} (ambiguous mode "
                                                     "selection)")
    if args.require_pit:
        raise bc.BoostingError("TREE_PIT_NOT_ADMITTED", "the comparison is RETROSPECTIVE_RESEARCH and UNTRUSTED_SHADOW; "
                                                        "it is never PIT admitted")
    if args.as_of is not None:
        raise bc.BoostingError("AS_OF_STATE_NOT_SUPPORTED", "no as-of, cutoff, effective or known-at query state "
                                                            "exists for the retrospective comparison")
    authority: dict[str, Any] = {} if anchors is _DEFAULT else {"anchors": anchors}
    return bc.query(args.boosting_comparison, args.grain, manifest=args.manifest, expect_identity=args.expect_identity,
                    season=args.season, team=args.team, contest=args.contest, model=args.model,
                    partition=args.partition, slice_id=args.slice_id, limit=args.limit, offset=args.offset,
                    all_rows=args.all_rows, **authority)


def _write_utf8(text: str) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        sys.stdout.flush()
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)


def main(argv: Sequence[str] | None = None, anchors: Any = _DEFAULT) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        args = build_parser().parse_args(tokens)
        result = run(args, anchors)
    except bc.BoostingError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    _write_utf8(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0
