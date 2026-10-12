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

``--prospective-preview <preview.json>`` (BAT-724) is a separate explicit mode served by
:mod:`aggie_analytics.retrospective_baseline.preview`, imported only then: the provider-record baseline preview over the
accepted 2026-10-11 provider observation at the ``preview-feature``, ``preview-estimate`` and ``preview-summary`` grains
with ``--cutoff`` (required), ``--season``, ``--event espn:event:<id>``, ``--team espn:team:<id>``, ``--model``,
``--orientation home|away`` and exact paging. Every answer is PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST and
PIT_NOT_ADMITTED. It is never combined with ``--database``, ``--history-database`` or ``--manifest``
(PREVIEW_MODE_CONFLICT); ``--contest`` and ``--partition`` do not apply to it (FILTER_NOT_APPLICABLE). When the option is
absent the original parser handles the invocation, so every existing invocation, answer and refusal is unchanged.

``--prospective-shadow <snapshot.json>`` (BAT-725) is another separate explicit mode, served by
:mod:`aggie_analytics.retrospective_baseline.shadow` and imported only then: the immutable private UNTRUSTED_SHADOW
snapshot of the fixed provider-record predictions for the accepted October 17 provider cohort, anchored by a hash-only
Jira comment's service-created time, at the ``shadow-prediction`` and ``shadow-summary`` grains with ``--cutoff``
(required; before the anchor it refuses), ``--season``, ``--event``, ``--team``, ``--model``, ``--orientation`` and exact
paging. It is never combined with the historical databases, ``--manifest`` or ``--prospective-preview``
(SHADOW_MODE_CONFLICT), and ``--require-pit`` is always refused. Invocations without the option keep their existing
parsers and bytes; only ``--help`` of the original parser gains one paragraph naming it.

``--schedule-evidence <schedule.json>`` together with ``--prospective-shadow <snapshot.json>`` (BAT-726) is the explicit
official schedule evidence mode, served by :mod:`aggie_analytics.retrospective_baseline.schedule` and imported only then:
the immutable private sidecar of bounded official 2026 schedule observations for all 25 events of that accepted shadow at
the ``shadow-schedule`` (one record per event) and ``shadow-schedule-source`` (every request, hop, failure and
zero-request decision) grains with ``--cutoff`` (required; before the sidecar's observation bound it refuses),
``--season``, ``--event``, ``--team`` and exact paging. Every row is an OFFICIAL_SCHEDULE_CLAIM, never an actual
kickoff, and carries UNTRUSTED_SHADOW and PIT_NOT_ADMITTED. It is never combined with the historical databases,
``--manifest`` or ``--prospective-preview`` (SCHEDULE_MODE_CONFLICT), needs the shadow (SCHEDULE_SHADOW_REQUIRED), and
``--model``/``--orientation``/``--contest``/``--partition`` do not apply (FILTER_NOT_APPLICABLE). Invocations without
the option keep their existing parsers and bytes, ``--help`` included; the mode's own parser describes it
(``--schedule-evidence <schedule.json> --help``).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from aggie_analytics.retrospective_baseline import benchmark as bm

PREVIEW_OPTION = "--prospective-preview"
PREVIEW_GRAINS = ("preview-feature", "preview-estimate", "preview-summary")
PREVIEW_EPILOG = ("explicit preview mode (BAT-724): --prospective-preview <preview.json> --grain "
                  "{preview-feature,preview-estimate,preview-summary} --cutoff <instant with zone> [--season] "
                  "[--event espn:event:<id>] [--team espn:team:<id>] [--model] [--orientation home|away] [--limit] "
                  "[--offset] [--all]: the provider-record baseline preview over the accepted 2026-10-11 provider "
                  "observation; PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST, PIT_NOT_ADMITTED, not calibrated, no "
                  "skill claim; never combined with --database or --history-database")
SHADOW_OPTION = "--prospective-shadow"
SHADOW_GRAINS = ("shadow-prediction", "shadow-summary")
SHADOW_EPILOG = ("explicit shadow mode (BAT-725): --prospective-shadow <snapshot.json> --grain "
                 "{shadow-prediction,shadow-summary} --cutoff <instant with zone> [--season] [--event espn:event:<id>] "
                 "[--team espn:team:<id>] [--model] [--orientation home|away] [--limit] [--offset] [--all]: the "
                 "immutable private snapshot of the fixed provider-record predictions for the accepted October 17 "
                 "provider cohort, anchored by a hash-only Jira comment's service-created time; UNTRUSTED_SHADOW, "
                 "PROVIDER_CLAIM_INPUTS, PIT_NOT_ADMITTED, NOT_CALIBRATED, PREDICTIVE_SKILL_NOT_ESTABLISHED, national "
                 "coverage UNKNOWN; refused before the anchor time; never combined with --database, --history-database "
                 "or --prospective-preview")
SCHEDULE_OPTION = "--schedule-evidence"
SCHEDULE_GRAINS = ("shadow-schedule", "shadow-schedule-source")
SCHEDULE_EPILOG = ("explicit official schedule evidence mode (BAT-726): --prospective-shadow <snapshot.json> "
                   "--schedule-evidence <schedule.json> --grain {shadow-schedule,shadow-schedule-source} --cutoff "
                   "<instant with zone> [--season] [--event espn:event:<id>] [--team espn:team:<id>] [--limit] "
                   "[--offset] [--all]: the immutable private sidecar of bounded official 2026 schedule observations "
                   "for the 25 events of that accepted shadow; OFFICIAL_SCHEDULE_CLAIM, SCHEDULE_NOT_ACTUAL_KICKOFF, "
                   "CURRENT_OBSERVATION_NOT_ORIGINAL_PUBLICATION, NO_RETROACTIVE_ANCHOR_AUTHORITY, UNTRUSTED_SHADOW, "
                   "PIT_NOT_ADMITTED; refused before the observation bound; never combined with --database, "
                   "--history-database or --prospective-preview")
_DEFAULT = object()


class _HistoricalParser(argparse.ArgumentParser):
    """The original parser; its help gains one trailing paragraph naming the shadow mode (usage, description, the
    preview epilog and every error output are unchanged)."""

    def format_help(self) -> str:
        formatter = self._get_formatter()
        formatter.add_text(SHADOW_EPILOG)
        return super().format_help() + "\n" + formatter.format_help()


def build_parser() -> argparse.ArgumentParser:
    parser = _HistoricalParser(prog="bas-retrospective-baseline-query", allow_abbrev=False,
                               description="Read-only explicit retrospective 2016-2023 baseline benchmark "
                                           "(calendar order only; not PIT, not a forecast, no skill claim).",
                               epilog=PREVIEW_EPILOG)
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


def build_preview_parser() -> argparse.ArgumentParser:
    """The explicit BAT-724 preview mode's parser (selected only when --prospective-preview is named)."""
    parser = argparse.ArgumentParser(prog="bas-retrospective-baseline-query --prospective-preview", allow_abbrev=False,
                                     description="Explicit provider-record baseline preview over the accepted "
                                                 "2026-10-11 provider observation (illustrative fixed calculation; "
                                                 "not a forecast, not PIT admitted, not calibrated, no skill claim).")
    parser.add_argument(PREVIEW_OPTION, dest="prospective_preview", required=True, type=Path,
                        help="the explicitly selected preview.json of a verified preview directory (never a default)")
    parser.add_argument("--grain", required=True, choices=list(PREVIEW_GRAINS) + list(bm.GRAINS))
    parser.add_argument("--cutoff", default=None, help="ISO-8601 instant with seconds and an explicit zone")
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--event", default=None, help="provider event key espn:event:<digits>")
    parser.add_argument("--team", default=None, help="provider team key espn:team:<digits>")
    parser.add_argument("--model", default=None)
    parser.add_argument("--orientation", default=None, help="home or away (provider designation)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the preview is never PIT admitted")
    # Historical-mode options, recognized only to refuse the ambiguous combination clearly.
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--history-database", dest="history_database", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--partition", default=None)
    return parser


def build_shadow_parser() -> argparse.ArgumentParser:
    """The explicit BAT-725 shadow mode's parser (selected only when --prospective-shadow is named)."""
    parser = argparse.ArgumentParser(prog="bas-retrospective-baseline-query --prospective-shadow", allow_abbrev=False,
                                     description="Explicit immutable private UNTRUSTED_SHADOW snapshot of the fixed "
                                                 "provider-record predictions for the accepted October 17 provider "
                                                 "cohort (not a trusted forecast, not PIT admitted, not calibrated, no "
                                                 "skill claim).")
    parser.add_argument(SHADOW_OPTION, dest="prospective_shadow", required=True, type=Path,
                        help="the explicitly selected snapshot.json of a verified snapshot directory (never a default)")
    parser.add_argument("--grain", required=True, choices=list(SHADOW_GRAINS) + list(PREVIEW_GRAINS) + list(bm.GRAINS))
    parser.add_argument("--cutoff", default=None, help="ISO-8601 instant with seconds and an explicit zone")
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--event", default=None, help="provider event key espn:event:<digits>")
    parser.add_argument("--team", default=None, help="provider team key espn:team:<digits>")
    parser.add_argument("--model", default=None)
    parser.add_argument("--orientation", default=None, help="home or away (provider designation)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the shadow snapshot is never PIT admitted")
    # Other modes' options, recognized only to refuse the ambiguous combination clearly.
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--history-database", dest="history_database", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(PREVIEW_OPTION, dest="prospective_preview", type=Path, default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--partition", default=None)
    return parser


def build_schedule_parser() -> argparse.ArgumentParser:
    """The explicit BAT-726 schedule evidence mode's parser (selected only when --schedule-evidence is named)."""
    parser = argparse.ArgumentParser(prog="bas-retrospective-baseline-query --schedule-evidence", allow_abbrev=False,
                                     description="Explicit immutable private official schedule evidence sidecar for the "
                                                 "accepted October 17 UNTRUSTED_SHADOW cohort (official schedule "
                                                 "claims, never actual kickoff; not PIT admitted; no skill claim).",
                                     epilog=SCHEDULE_EPILOG)
    parser.add_argument(SCHEDULE_OPTION, dest="schedule_evidence", required=True, type=Path,
                        help="the explicitly selected schedule.json of a verified sidecar directory (never a default)")
    parser.add_argument(SHADOW_OPTION, dest="prospective_shadow", type=Path, default=None,
                        help="the accepted snapshot.json the sidecar is bound to (required)")
    parser.add_argument("--grain", required=True, choices=list(SCHEDULE_GRAINS) + list(SHADOW_GRAINS) +
                        list(PREVIEW_GRAINS) + list(bm.GRAINS))
    parser.add_argument("--cutoff", default=None, help="ISO-8601 instant with seconds and an explicit zone")
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--event", default=None, help="provider event key espn:event:<digits>")
    parser.add_argument("--team", default=None, help="provider team key espn:team:<digits>")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the schedule evidence is never PIT admitted")
    # Other modes' options, recognized only to refuse the ambiguous or inapplicable selection clearly.
    parser.add_argument("--model", default=None)
    parser.add_argument("--orientation", default=None)
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--history-database", dest="history_database", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(PREVIEW_OPTION, dest="prospective_preview", type=Path, default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--partition", default=None)
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


def preview_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit preview option (exactly, or as ``--prospective-preview=<path>``)."""
    return any(token == PREVIEW_OPTION or token.startswith(PREVIEW_OPTION + "=") for token in argv)


def run_preview(args: argparse.Namespace, contract_sha256: str | None = None) -> dict[str, Any]:
    """The explicit preview mode (BAT-724): every ambiguous or inapplicable selection and every malformed argument is
    refused before the preview is read; then the preview is verified completely and queried."""
    from aggie_analytics.retrospective_baseline import preview  # noqa: PLC0415 - explicit option only

    if args.require_pit:
        raise preview.PreviewError("PREVIEW_PIT_NOT_ADMITTED", "the preview is PROVIDER_RECORD_BASELINE_PREVIEW_NOT_"
                                                               "FORECAST and never PIT admitted")
    conflicts = [flag for flag, value in (("--database", args.database), ("--history-database", args.history_database),
                                          ("--manifest", args.manifest)) if value is not None]
    if conflicts:
        raise preview.PreviewError("PREVIEW_MODE_CONFLICT", f"{conflicts} cannot be combined with {PREVIEW_OPTION} "
                                                            "(ambiguous mode selection)")
    stray = [flag for flag, value in (("--contest", args.contest), ("--partition", args.partition)) if value is not None]
    if stray:
        raise preview.PreviewError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the preview grains")
    preview.ProviderRecordPreview.filters(args.grain, season=args.season, event=args.event, team=args.team,
                                          model=args.model, orientation=args.orientation)
    if args.offset < 0:
        raise preview.PreviewError("NEGATIVE_OFFSET", "offset must be zero or positive")
    if args.limit < 0:
        raise preview.PreviewError("NEGATIVE_LIMIT", "limit must be zero or positive")
    preview.parse_cutoff(args.cutoff)
    if args.expect_identity is not None and not preview.IDENTITY_RE.match(args.expect_identity):
        raise preview.PreviewError("STALE_PREVIEW_IDENTITY", "--expect-identity must be a SHA-256 identity")
    authority = {} if contract_sha256 is None else {"contract_sha256": contract_sha256}
    with preview.ProviderRecordPreview(args.prospective_preview, expect_identity=args.expect_identity,
                                       **authority) as selected:
        return selected.query(args.grain, cutoff=args.cutoff, season=args.season, event=args.event, team=args.team,
                              model=args.model, orientation=args.orientation, limit=args.limit, offset=args.offset,
                              all_rows=args.all_rows)


def shadow_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit shadow option (exactly, or as ``--prospective-shadow=<path>``)."""
    return any(token == SHADOW_OPTION or token.startswith(SHADOW_OPTION + "=") for token in argv)


def run_shadow(args: argparse.Namespace, contract_sha256: str | None = None, profile: Any = _DEFAULT) -> dict[str, Any]:
    """The explicit shadow mode (BAT-725): every ambiguous or inapplicable selection and every malformed argument is
    refused before the snapshot is read; then the snapshot is verified completely and queried."""
    from aggie_analytics.retrospective_baseline import shadow  # noqa: PLC0415 - explicit option only

    if args.require_pit:
        raise shadow.ShadowError("SHADOW_PIT_NOT_ADMITTED", "the snapshot is UNTRUSTED_SHADOW and never PIT admitted")
    conflicts = [flag for flag, value in (("--database", args.database), ("--history-database", args.history_database),
                                          ("--manifest", args.manifest), (PREVIEW_OPTION, args.prospective_preview))
                 if value is not None]
    if conflicts:
        raise shadow.ShadowError("SHADOW_MODE_CONFLICT", f"{conflicts} cannot be combined with {SHADOW_OPTION} "
                                                         "(ambiguous mode selection)")
    stray = [flag for flag, value in (("--contest", args.contest), ("--partition", args.partition)) if value is not None]
    if stray:
        raise shadow.ShadowError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the shadow grains")
    shadow.ShadowSnapshot.filters(args.grain, season=args.season, event=args.event, team=args.team, model=args.model,
                                  orientation=args.orientation)
    if args.offset < 0:
        raise shadow.ShadowError("NEGATIVE_OFFSET", "offset must be zero or positive")
    if args.limit < 0:
        raise shadow.ShadowError("NEGATIVE_LIMIT", "limit must be zero or positive")
    shadow.parse_cutoff(args.cutoff)
    if args.expect_identity is not None and not shadow.IDENTITY_RE.match(args.expect_identity):
        raise shadow.ShadowError("STALE_SHADOW_IDENTITY", "--expect-identity must be a SHA-256 identity")
    authority = {} if contract_sha256 is None else {"contract_sha256": contract_sha256}
    if profile is not _DEFAULT:
        authority["profile"] = profile
    with shadow.ShadowSnapshot(args.prospective_shadow, expect_identity=args.expect_identity, **authority) as selected:
        return selected.query(args.grain, cutoff=args.cutoff, season=args.season, event=args.event, team=args.team,
                              model=args.model, orientation=args.orientation, limit=args.limit, offset=args.offset,
                              all_rows=args.all_rows)


def schedule_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit schedule evidence option (exactly, or as ``--schedule-evidence=...``)."""
    return any(token == SCHEDULE_OPTION or token.startswith(SCHEDULE_OPTION + "=") for token in argv)


def run_schedule(args: argparse.Namespace, contract_sha256: str | None = None, profile: Any = _DEFAULT,
                 shadow_profile: Any = _DEFAULT) -> dict[str, Any]:
    """The explicit schedule evidence mode (BAT-726): every ambiguous or inapplicable selection and every malformed
    argument is refused before any file is read; then the shadow and the sidecar are verified completely and queried."""
    from aggie_analytics.retrospective_baseline import schedule  # noqa: PLC0415 - explicit option only

    if args.require_pit:
        raise schedule.ScheduleError("SCHEDULE_PIT_NOT_ADMITTED", "the schedule evidence is UNTRUSTED_SHADOW and never "
                                                                  "PIT admitted")
    conflicts = [flag for flag, value in (("--database", args.database), ("--history-database", args.history_database),
                                          ("--manifest", args.manifest), (PREVIEW_OPTION, args.prospective_preview))
                 if value is not None]
    if conflicts:
        raise schedule.ScheduleError("SCHEDULE_MODE_CONFLICT", f"{conflicts} cannot be combined with "
                                                               f"{SCHEDULE_OPTION} (ambiguous mode selection)")
    if args.prospective_shadow is None:
        raise schedule.ScheduleError("SCHEDULE_SHADOW_REQUIRED", f"{SCHEDULE_OPTION} needs the accepted "
                                                                 f"{SHADOW_OPTION} snapshot it is bound to")
    stray = [flag for flag, value in (("--model", args.model), ("--orientation", args.orientation),
                                      ("--contest", args.contest), ("--partition", args.partition)) if value is not None]
    if stray:
        raise schedule.ScheduleError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the schedule evidence grains")
    schedule.ScheduleEvidence.filters(args.grain, season=args.season, event=args.event, team=args.team)
    if args.offset < 0:
        raise schedule.ScheduleError("NEGATIVE_OFFSET", "offset must be zero or positive")
    if args.limit < 0:
        raise schedule.ScheduleError("NEGATIVE_LIMIT", "limit must be zero or positive")
    schedule.parse_cutoff(args.cutoff)
    if args.expect_identity is not None and not schedule.IDENTITY_RE.match(args.expect_identity):
        raise schedule.ScheduleError("STALE_SCHEDULE_IDENTITY", "--expect-identity must be a SHA-256 identity")
    authority: dict[str, Any] = {} if contract_sha256 is None else {"contract_sha256": contract_sha256}
    if profile is not _DEFAULT:
        authority["profile"] = profile
    if shadow_profile is not _DEFAULT:
        authority["shadow_profile"] = shadow_profile
    with schedule.ScheduleEvidence(args.schedule_evidence, args.prospective_shadow,
                                   expect_identity=args.expect_identity, **authority) as selected:
        return selected.query(args.grain, cutoff=args.cutoff, season=args.season, event=args.event, team=args.team,
                              limit=args.limit, offset=args.offset, all_rows=args.all_rows)


def main(argv: Sequence[str] | None = None, *, preview_contract_sha256: str | None = None,
         shadow_contract_sha256: str | None = None, shadow_profile: Any = _DEFAULT,
         schedule_contract_sha256: str | None = None, schedule_profile: Any = _DEFAULT) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if schedule_mode(tokens):
        args = build_schedule_parser().parse_args(tokens)
        from aggie_analytics.retrospective_baseline import schedule  # noqa: PLC0415 - explicit option only
        try:
            result = run_schedule(args, schedule_contract_sha256, schedule_profile, shadow_profile)
        except schedule.ScheduleError as exc:
            print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
            return 2
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    if shadow_mode(tokens):
        args = build_shadow_parser().parse_args(tokens)
        from aggie_analytics.retrospective_baseline import shadow  # noqa: PLC0415 - explicit option only
        try:
            result = run_shadow(args, shadow_contract_sha256, shadow_profile)
        except shadow.ShadowError as exc:
            print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
            return 2
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    if preview_mode(tokens):
        args = build_preview_parser().parse_args(tokens)
        from aggie_analytics.retrospective_baseline import preview  # noqa: PLC0415 - explicit option only
        try:
            result = run_preview(args, preview_contract_sha256)
        except preview.PreviewError as exc:
            print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
            return 2
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
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
