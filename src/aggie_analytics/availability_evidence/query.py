r"""Read-only fixed-profile query of the existing C37 2026 availability source/parser assertions (BAT-733, TP62-A01).

``bas-availability-evidence-query --database <C37 corrected national release sqlite> --data-root <data root>
--grain statement|opportunity|policy|profile [selectors] [--limit N] [--offset N] [--all] [--cutoff <instant>]
[--profile C37_2026_AVAILABILITY_ASSERTIONS_V1] [--expect-sha256 <hex>]`` (also
``python -m aggie_analytics.availability_evidence.query``).

``--database``, ``--data-root`` and ``--grain`` are required literal inputs; nothing is discovered from the environment,
a manifest or the network, and no missing file is ever created. Trust comes only from the builtin profile
``C37_2026_AVAILABILITY_ASSERTIONS_V1`` (:mod:`.profile`): the exact whole-database SHA-256 and the five small
report/posting witnesses at their frozen paths under the data root are verified before any grain is served; another
``--profile`` is refused and ``--expect-sha256`` only adds a constraint. Selectors follow the frozen applicability
matrix (``RULES['selectors']``): an inapplicable selector is refused (SELECTOR_NOT_APPLICABLE), a malformed one is
INVALID_SELECTOR, a well-formed key or name not represented in the fixed profile is KEY_NOT_IN_PROFILE, a foreign
season is SEASON_NOT_IN_PROFILE, and represented selectors whose intersection is empty answer ``rows=[]`` with an
explicit empty-match disposition. ``--cutoff`` compares each statement's clocks with an instant and filters nothing.
``--as-of``, ``--current``, ``--latest``, ``--require-pit`` and ``--forecast-input`` are always refused (any supplied
``--as-of`` value, an empty one included): this is a static retained slice of source/parser assertions, never an
availability state, a PIT gateway or a forecast input.

Exit 0 answers one JSON document on stdout; exit 2 is a request refusal and exit 3 an input integrity failure, each
with ``{"refused": CODE, "refusal_class": ..., "error": ...}`` on stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn, Sequence

from aggie_analytics.availability_evidence import evidence as ae
from aggie_analytics.availability_evidence import profile as P

EPILOG = ("fixed profile C37_2026_AVAILABILITY_ASSERTIONS_V1 (BAT-733): grains statement (1,592 source-cell "
          "assertions), opportunity (3,474 retained schedule-record x program-side occurrences, 3,220 business keys), "
          "policy (13 observations), profile (coverage); HISTORICAL_SOURCE_AND_PARSER_ASSERTIONS_ONLY, "
          "availability_state_asserted=false, pit_admission=NOT_ADMITTED, model_feature_admission=NOT_ADMITTED, "
          "healthy_default=false, predictive skill NOT_ESTABLISHED; a source 'Available', a blank cell or source "
          "silence is never a healthy player; every effective time is unknown and no first-known time is established")

SELECTOR_OPTIONS = [option for option in P.RULES["selectors"]]
TEMPORAL_REFUSALS = P.RULES["temporal_state_refusals"]


class _Parser(argparse.ArgumentParser):
    """Argument errors become controlled refusals (``ARGUMENT_INVALID``) instead of a usage dump."""

    def error(self, message: str) -> NoReturn:
        raise ae.AvailabilityError("ARGUMENT_INVALID", message)


class _Once(argparse.Action):
    """An option that may be given at most once (a repeated selector is refused, never silently replaced)."""

    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace, values: Any,
                 option_string: str | None = None) -> None:
        if getattr(namespace, self.dest, None) is not None:
            raise ae.AvailabilityError("ARGUMENT_INVALID", f"{option_string} may be given only once")
        setattr(namespace, self.dest, values)


class _OnceFlag(argparse.Action):
    def __init__(self, option_strings: list[str], dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, nargs=0, default=False, **kwargs)

    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace, values: Any,
                 option_string: str | None = None) -> None:
        if getattr(namespace, self.dest, False):
            raise ae.AvailabilityError("ARGUMENT_INVALID", f"{option_string} may be given only once")
        setattr(namespace, self.dest, True)


def _dest(option: str) -> str:
    return option[2:].replace("-", "_")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="bas-availability-evidence-query", allow_abbrev=False, epilog=EPILOG,
                     description="Read-only fixed-profile query of the existing C37 2026 availability source and "
                                 "parser assertions (historical source assertions only: not an availability state, "
                                 "not PIT admitted, not a forecast input, no skill claim).")
    parser.add_argument("--database", required=True, action=_Once,
                        help="the literal local C37 corrected national release database file")
    parser.add_argument("--data-root", dest="data_root", required=True, action=_Once,
                        help="the literal local data root holding the five frozen report/posting witnesses")
    parser.add_argument("--grain", required=True, action=_Once, choices=list(P.GRAINS))
    parser.add_argument("--profile", action=_Once, default=None,
                        help=f"optional; only {P.PROFILE_ID} (the default) is accepted")
    parser.add_argument("--expect-sha256", dest="expect_sha256", action=_Once, default=None,
                        help="an additional caller constraint on the database SHA-256 (never a trust override)")
    for option in SELECTOR_OPTIONS:
        parser.add_argument(option, dest=_dest(option), action=_Once, default=None)
    parser.add_argument("--limit", action=_Once, default=None)
    parser.add_argument("--offset", action=_Once, default=None)
    parser.add_argument("--all", dest="all_rows", action=_OnceFlag)
    parser.add_argument("--as-of", dest="as_of", action=_Once, default=None,
                        help="refused: no availability state as of any time is supported")
    parser.add_argument("--current", action=_OnceFlag, help="refused: no current availability state is supported")
    parser.add_argument("--latest", action=_OnceFlag, help="refused: no latest availability state is supported")
    parser.add_argument("--require-pit", dest="require_pit", action=_OnceFlag,
                        help="refused: the fixed slice is never PIT admitted")
    parser.add_argument("--forecast-input", dest="forecast_input", action=_OnceFlag,
                        help="refused: the fixed slice is never a forecast input")
    return parser


def run(args: argparse.Namespace, *, profile: dict[str, Any] | None = None,
        hooks: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every temporal-state request, unknown profile, inapplicable or malformed selector and malformed paging value is
    refused before any file is read; then the fixed inputs are verified completely and queried. ``profile``/``hooks``
    are internal test injections (a trusted synthetic profile); the console never passes them."""
    for flag, dest in (("--as-of", "as_of"), ("--current", "current"), ("--latest", "latest"),
                       ("--require-pit", "require_pit"), ("--forecast-input", "forecast_input")):
        # Presence, never truthiness: an explicitly supplied --as-of value is refused whatever it is, an empty one
        # included (C62-CONT-01, MF62A01-02); the other four are flags.
        supplied = getattr(args, dest)
        if supplied is not None and supplied is not False:
            raise ae.AvailabilityError(TEMPORAL_REFUSALS[flag], f"{flag}: the fixed profile is a static retained slice "
                                                                f"of source/parser assertions; no as-of, current or "
                                                                f"latest availability state, PIT admission or forecast "
                                                                f"input is supported")
    if args.profile is not None and args.profile != P.PROFILE_ID:
        raise ae.AvailabilityError("PROFILE_UNKNOWN", f"only the builtin profile {P.PROFILE_ID} is supported")
    selectors = {option: getattr(args, _dest(option)) for option in SELECTOR_OPTIONS}
    ae.validate_selectors(args.grain, selectors)
    ae.validate_paging(args.limit, args.offset, args.all_rows)
    session = ae.AvailabilityEvidence(args.database, args.data_root, expect_sha256=args.expect_sha256,
                                      profile=profile, hooks=hooks)
    return session.query(args.grain, selectors, limit=args.limit, offset=args.offset, all_rows=args.all_rows)


def _write(text: str) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        sys.stdout.flush()
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)


def main(argv: Sequence[str] | None = None, *, profile: dict[str, Any] | None = None,
         hooks: dict[str, Any] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        args = build_parser().parse_args(tokens)
        result = run(args, profile=profile, hooks=hooks)
    except ae.AvailabilityError as exc:
        print(json.dumps({"refused": exc.code, "refusal_class": exc.refusal_class, "error": str(exc)}), file=sys.stderr)
        return exc.exit_code
    _write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    # ``python -m`` runs this file as __main__; delegate to the package module so every shared class has one identity.
    from aggie_analytics.availability_evidence import query as _package_query  # noqa: PLC0415

    raise SystemExit(_package_query.main())
