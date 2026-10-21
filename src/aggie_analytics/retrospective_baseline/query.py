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

The same explicit option also serves a successor sidecar (BAT-727,
:mod:`aggie_analytics.retrospective_baseline.schedule_expansion`) when the selected sidecar's own bundled contract
names that profile: a separately frozen policy re-qualifying the retained BAT-726 capture, its predecessor verified
by the accepted BAT-726 reader, served only at or after both the original observation bound and the successor's
policy-frozen time. A V1 sidecar is still served by the V1 reader with its unchanged answers and refusals.

``--reference-comparison <national_retrospective_reference.sqlite>`` (BAT-423 bounded research contribution, Cycle 56)
is the explicit national retrospective reference comparison mode, served by
:mod:`aggie_analytics.retrospective_baseline.reference` and imported only then: the immutable 2016-2023 comparison of
the two unchanged C47 fixed models with a site-blind Elo, a paired zero-intercept L2 logistic probability and a ridge
expected margin fitted only on 2016-2022, at the ``reference-feature``, ``reference-estimate``,
``reference-parameter``, ``reference-score`` and ``reference-summary`` grains, verified against
``--history-database`` and ``--population-database`` (both required) with a complete re-derivation and refit before any
row is served. Filters ``--season``, ``--team``, ``--contest``, ``--model``, ``--partition`` and (summary only)
``--slice``; exact paging. Every answer is RETROSPECTIVE_REFERENCE_NOT_PIT_NOT_SKILL and UNTRUSTED_SHADOW;
``--require-pit`` is refused. It is never combined with ``--database`` or another explicit mode
(REFERENCE_MODE_CONFLICT). Invocations without the option keep their parsers and bytes, ``--help`` included; the mode's
own parser describes it (``--reference-comparison <file> --help``).

``--personnel-association <national_personnel_association.sqlite>`` (BAT-732 bounded research contribution, Cycle 61)
is the explicit national posthoc personnel/history association mode, served by
:mod:`aggie_analytics.retrospective_baseline.personnel_association` and imported only then: the immutable 2016-2022
association of the 2023-observed C59 season roster set rates with the accepted C56 history and outcomes on one common
cohort (fixed NULL and unchanged C47 smoothed controls, and exactly two frozen zero-intercept L2 logistic fits on
2016-2020: history only, and history plus three roster-rate differences), at the ``personnel-qualification``,
``personnel-feature``, ``personnel-estimate``, ``personnel-parameter``, ``personnel-score`` and ``personnel-summary``
grains. The reader needs no data root: it verifies every record, collection, rule, a fresh refit and every identity
before serving. Filters ``--season``, ``--team``, ``--contest``, ``--model`` and ``--partition`` follow the declared
selector matrix (an inapplicable one is refused); exact paging. Every answer is POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST,
RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and NOT_CALIBRATED with predictive skill NOT_ESTABLISHED;
``--require-pit`` is refused. It is never combined with ``--database``, ``--history-database`` or another explicit mode
(ASSOCIATION_MODE_CONFLICT). Invocations without the option keep their parsers, answers and refusals; only ``--help`` of
the original parser gains one paragraph naming it.

``--context-association <national_site_calendar_association.sqlite>`` (BAT-734 bounded research contribution, Cycle 63)
is the explicit national retrospective site/calendar association mode, served by
:mod:`aggie_analytics.retrospective_baseline.context_association` and imported only then: every accepted 2016-2023 target
qualified for its agreed designated source site and its latest strictly earlier eligible same-season calendar interval,
the frozen complete-case common cohort, exactly two frozen zero-intercept lambda-1 logistic fits on its 2016-2022 games
(CTX-HISTORY-LOGIT-V1 on history, CTX-SITE-CALENDAR-LOGIT-V1 on history, site and calendar) and the five unchanged C56
game-score comparators projected on the same cohort, at the ``context-qualification``, ``context-feature``,
``context-parameter``, ``context-estimate``, ``context-score`` and ``context-summary`` grains. The reader needs no data
root: it verifies every record, collection, rule, a fresh refit and every identity before serving. Filters ``--season``,
``--partition``, ``--team``, ``--contest`` and ``--model`` follow the declared applicability matrix (an inapplicable one
is refused before any file is read); exact paging (``--all`` excludes an explicit ``--limit``/``--offset``). Every
answer is RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, NOT_A_FORECAST and NOT_CALIBRATED with predictive
skill NOT_ESTABLISHED; ``--require-pit`` is refused. It is never combined with another mode's option
(CONTEXT_MODE_CONFLICT). Invocations without the option keep their parsers, answers and refusals byte for byte, the
original ``--help`` included (TP63 allows one added help paragraph; it is not used because the accepted Cycle 61 test
pins that help text exactly); the mode's own parser describes it (``--context-association <file> --help``).
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
                   "--history-database or --prospective-preview. The same option serves an explicitly "
                   "selected successor sidecar (BAT-727 expansion profile: its own frozen contract and "
                   "policy time, refused before the policy-frozen time) when its bundled contract names "
                   "that profile")
REFERENCE_OPTION = "--reference-comparison"
REFERENCE_GRAINS = ("reference-feature", "reference-estimate", "reference-parameter", "reference-score",
                    "reference-summary")
REFERENCE_EPILOG = ("explicit national retrospective reference comparison mode (BAT-423, Cycle 56): "
                    "--reference-comparison <national_retrospective_reference.sqlite> --history-database <accepted "
                    "history sqlite> --population-database <accepted parent population sqlite> --grain "
                    "{reference-feature,reference-estimate,reference-parameter,reference-score,reference-summary} "
                    "[--season] [--team] [--contest] [--model] [--partition] [--slice (summary)] [--limit] [--offset] "
                    "[--all]: the two unchanged C47 fixed models with a site-blind Elo, a paired zero-intercept L2 "
                    "logistic probability and a ridge expected margin fitted only on 2016-2022 (2023 an exposed "
                    "out-of-fit comparison); RETROSPECTIVE_REFERENCE_NOT_PIT_NOT_SKILL, UNTRUSTED_SHADOW, "
                    "PIT_ELIGIBILITY_NOT_ESTABLISHED, predictive skill and calibration NOT_ESTABLISHED, no champion; "
                    "never combined with --database or another explicit mode")
ASSOCIATION_OPTION = "--personnel-association"
ASSOCIATION_EPILOG = ("explicit national posthoc personnel/history association mode (BAT-732, Cycle 61): "
                      "--personnel-association <national_personnel_association.sqlite> --grain "
                      "{personnel-qualification,personnel-feature,personnel-estimate,personnel-parameter,"
                      "personnel-score,personnel-summary} [--season] [--team] [--contest] [--model] [--partition] "
                      "[--limit] [--offset] [--all] [--manifest] [--expect-identity]: 2023-observed C59 season roster "
                      "set rates associated after the fact with the accepted C56 2016-2022 history and outcomes on one "
                      "common cohort (fixed null and C47 smoothed controls, two frozen L2 logistic fits on 2016-2020); "
                      "POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST, RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, "
                      "PIT_NOT_ADMITTED, NOT_CALIBRATED, predictive skill NOT_ESTABLISHED; never combined with "
                      "--database or another explicit mode")
CONTEXT_OPTION = "--context-association"
CONTEXT_EPILOG = ("explicit national retrospective site/calendar association mode (BAT-734, Cycle 63): "
                  "--context-association <national_site_calendar_association.sqlite> --grain "
                  "{context-qualification,context-feature,context-parameter,context-estimate,context-score,"
                  "context-summary} [--season] [--partition] [--team] [--contest] [--model] [--limit] [--offset] "
                  "[--all] [--manifest] [--expect-identity]: every accepted 2016-2023 target's agreed designated "
                  "source site and latest strictly earlier eligible same-season calendar interval, two frozen "
                  "zero-intercept L2 logistic fits on the common 2016-2022 games (history; history, site and calendar) "
                  "and the five unchanged C56 comparators on the same cohort, 2023 an exposed comparison; "
                  "RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, NOT_A_FORECAST, NOT_CALIBRATED, "
                  "predictive skill NOT_ESTABLISHED, no causal site, rest or travel claim; never combined with "
                  "--database or another explicit mode")
_DEFAULT = object()


class _HistoricalParser(argparse.ArgumentParser):
    """The original parser; its help gains one trailing paragraph naming the shadow mode and (Cycle 61) one more
    trailing paragraph naming the personnel association mode (usage, description, the preview epilog, the shadow
    paragraph and every error output are unchanged)."""

    def format_help(self) -> str:
        formatter = self._get_formatter()
        formatter.add_text(SHADOW_EPILOG)
        association = self._get_formatter()
        association.add_text(ASSOCIATION_EPILOG)
        return super().format_help() + "\n" + formatter.format_help() + "\n" + association.format_help()


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


def build_reference_parser() -> argparse.ArgumentParser:
    """The explicit BAT-423 reference comparison mode's parser (selected only when --reference-comparison is named)."""
    parser = argparse.ArgumentParser(prog="bas-retrospective-baseline-query --reference-comparison", allow_abbrev=False,
                                     description="Explicit immutable national retrospective reference comparison "
                                                 "2016-2023 (research only: not PIT admitted, not a forecast, no "
                                                 "calibration, skill or champion claim).",
                                     epilog=REFERENCE_EPILOG)
    parser.add_argument(REFERENCE_OPTION, dest="reference_comparison", required=True, type=Path,
                        help="the explicitly selected reference database of a verified identity directory (never a "
                             "default)")
    parser.add_argument("--history-database", dest="history_database", type=Path, default=None,
                        help="the accepted national history-prefix database the reference was built from (required)")
    parser.add_argument("--population-database", dest="population_database", type=Path, default=None,
                        help="the accepted parent population database the reference was built from (required)")
    parser.add_argument("--manifest", type=Path, default=None, help="the reference run manifest (default: beside)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True, choices=list(REFERENCE_GRAINS) + list(bm.GRAINS) +
                        list(PREVIEW_GRAINS) + list(SHADOW_GRAINS) + list(SCHEDULE_GRAINS))
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--partition", default=None)
    parser.add_argument("--slice", dest="slice_id", default=None,
                        help="NATIONAL, TEXAS_AM, FIRST_FOUR_TEAM_GAMES or COLD_START (summary grain only)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the reference is never PIT admitted")
    # Other modes' options, recognized only to refuse the ambiguous or inapplicable selection clearly.
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument(PREVIEW_OPTION, dest="prospective_preview", type=Path, default=None)
    parser.add_argument(SHADOW_OPTION, dest="prospective_shadow", type=Path, default=None)
    parser.add_argument(SCHEDULE_OPTION, dest="schedule_evidence", type=Path, default=None)
    parser.add_argument("--cutoff", default=None)
    parser.add_argument("--event", default=None)
    parser.add_argument("--orientation", default=None)
    return parser


def reference_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit reference option (exactly, or as ``--reference-comparison=<path>``)."""
    return any(token == REFERENCE_OPTION or token.startswith(REFERENCE_OPTION + "=") for token in argv)


def run_reference(args: argparse.Namespace, anchors: Any = _DEFAULT) -> dict[str, Any]:
    """The explicit reference comparison mode (BAT-423): every ambiguous or inapplicable selection and every malformed
    argument is refused before any file is read; then the inputs and the reference are verified completely (refit
    included) and queried."""
    from aggie_analytics.retrospective_baseline import reference  # noqa: PLC0415 - explicit option only

    if args.require_pit:
        raise reference.ReferenceError("REFERENCE_PIT_NOT_ADMITTED", "the reference is research only and never PIT "
                                                                     "admitted")
    conflicts = [flag for flag, value in (("--database", args.database), (PREVIEW_OPTION, args.prospective_preview),
                                          (SHADOW_OPTION, args.prospective_shadow),
                                          (SCHEDULE_OPTION, args.schedule_evidence)) if value is not None]
    if conflicts:
        raise reference.ReferenceError("REFERENCE_MODE_CONFLICT", f"{conflicts} cannot be combined with "
                                                                  f"{REFERENCE_OPTION} (ambiguous mode selection)")
    stray = [flag for flag, value in (("--cutoff", args.cutoff), ("--event", args.event),
                                      ("--orientation", args.orientation)) if value is not None]
    if stray:
        raise reference.ReferenceError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the reference grains")
    missing = [flag for flag, value in (("--history-database", args.history_database),
                                        ("--population-database", args.population_database)) if value is None]
    if missing:
        raise reference.ReferenceError("REFERENCE_INPUT_REQUIRED", f"{REFERENCE_OPTION} needs {missing}")
    reference.ReferenceComparison.filters(args.grain, season=args.season, team=args.team, contest=args.contest,
                                          model=args.model, partition=args.partition, slice_id=args.slice_id)
    if args.offset < 0:
        raise reference.ReferenceError("NEGATIVE_OFFSET", "offset must be zero or positive")
    if args.limit < 0:
        raise reference.ReferenceError("NEGATIVE_LIMIT", "limit must be zero or positive")
    if args.expect_identity is not None and not reference.IDENTITY_RE.match(args.expect_identity):
        raise reference.ReferenceError("STALE_REFERENCE_IDENTITY", "--expect-identity must be a SHA-256 identity")
    authority: dict[str, Any] = {} if anchors is _DEFAULT else {"anchors": anchors}
    with reference.ReferenceComparison(args.reference_comparison, history_database=args.history_database,
                                       population_database=args.population_database, manifest=args.manifest,
                                       expect_identity=args.expect_identity, **authority) as selected:
        return selected.query(args.grain, season=args.season, team=args.team, contest=args.contest, model=args.model,
                              partition=args.partition, slice_id=args.slice_id, limit=args.limit, offset=args.offset,
                              all_rows=args.all_rows)


def association_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit personnel association option (exactly, or as
    ``--personnel-association=<path>``)."""
    return any(token == ASSOCIATION_OPTION or token.startswith(ASSOCIATION_OPTION + "=") for token in argv)


def build_association_parser() -> argparse.ArgumentParser:
    """The explicit BAT-732 personnel association mode's parser (selected only when --personnel-association is named);
    every argument error is a controlled ARGUMENT_INVALID refusal (exit 2, JSON on stderr), never a usage dump."""
    from aggie_analytics.retrospective_baseline import personnel_association as pa  # noqa: PLC0415 - explicit option

    class _AssociationParser(argparse.ArgumentParser):
        def error(self, message: str) -> Any:
            raise pa.AssociationError("ARGUMENT_INVALID", message)

    parser = _AssociationParser(prog="bas-retrospective-baseline-query --personnel-association", allow_abbrev=False,
                                description="Explicit immutable national posthoc personnel/history association "
                                            "2016-2022 (research only: POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST, not PIT "
                                            "admitted, not calibrated, no skill, champion or causal claim).",
                                epilog=ASSOCIATION_EPILOG)
    parser.add_argument(ASSOCIATION_OPTION, dest="personnel_association", required=True, type=Path,
                        help="the explicitly selected association database of a verified identity directory (never a "
                             "default)")
    parser.add_argument("--manifest", type=Path, default=None, help="the release run manifest (default: beside)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True)
    parser.add_argument("--season", default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--partition", default=None)
    parser.add_argument("--limit", default="50")
    parser.add_argument("--offset", default="0")
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the association is research only and never PIT admitted")
    # Other modes' options, recognized only to refuse the ambiguous or inapplicable selection clearly.
    for flag in ("--database", "--history-database", "--population-database", REFERENCE_OPTION, PREVIEW_OPTION,
                 SHADOW_OPTION, SCHEDULE_OPTION):
        parser.add_argument(flag, dest="conflict_" + flag.lstrip("-").replace("-", "_"), default=None)
    for flag in ("--cutoff", "--event", "--orientation", "--slice"):
        parser.add_argument(flag, dest="stray_" + flag.lstrip("-"), default=None)
    return parser


def _association_integer(text: Any, code: str, what: str) -> int:
    from aggie_analytics.retrospective_baseline import personnel_association as pa  # noqa: PLC0415 - explicit option

    value = str(text).strip()
    body = value[1:] if value.startswith("-") else value
    if not body.isascii() or not body.isdigit() or len(body) > 12:
        raise pa.AssociationError(code, f"{what} must be an integer, got {text!r}")
    return int(value)


def run_association(args: argparse.Namespace, anchors: Any = _DEFAULT) -> dict[str, Any]:
    """The explicit personnel association mode (BAT-732): every ambiguous, inapplicable or malformed selection is
    refused before any file is read; then the release is verified completely (refit included) and queried."""
    from aggie_analytics.retrospective_baseline import personnel_association as pa  # noqa: PLC0415 - explicit option

    if args.require_pit:
        raise pa.AssociationError("ASSOCIATION_PIT_NOT_ADMITTED", "the association is RETROSPECTIVE_RESEARCH and "
                                                                  "POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST; it is never "
                                                                  "PIT admitted and no as-of claim is supported")
    conflicts = [name[len("conflict_"):] for name, value in sorted(vars(args).items())
                 if name.startswith("conflict_") and value is not None]
    if conflicts:
        raise pa.AssociationError("ASSOCIATION_MODE_CONFLICT", f"{conflicts} cannot be combined with "
                                                               f"{ASSOCIATION_OPTION} (ambiguous mode selection)")
    stray = [name[len("stray_"):] for name, value in sorted(vars(args).items())
             if name.startswith("stray_") and value is not None]
    if stray:
        raise pa.AssociationError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the personnel association grains")
    season = None if args.season is None else _association_integer(args.season, "SEASON_INVALID", "season")
    limit = _association_integer(args.limit, "LIMIT_INVALID", "limit")
    offset = _association_integer(args.offset, "OFFSET_INVALID", "offset")
    if limit < 0:
        raise pa.AssociationError("NEGATIVE_LIMIT", "limit must be zero or positive")
    if offset < 0:
        raise pa.AssociationError("NEGATIVE_OFFSET", "offset must be zero or positive")
    pa.PersonnelAssociation.filters(args.grain, season=season, team=args.team, contest=args.contest, model=args.model,
                                    partition=args.partition)
    if args.expect_identity is not None and not pa.IDENTITY_RE.match(args.expect_identity):
        raise pa.AssociationError("STALE_ASSOCIATION_IDENTITY", "--expect-identity must be a SHA-256 identity")
    authority: dict[str, Any] = {} if anchors is _DEFAULT else {"anchors": anchors}
    with pa.PersonnelAssociation(args.personnel_association, manifest=args.manifest,
                                 expect_identity=args.expect_identity, **authority) as selected:
        return selected.query(args.grain, season=season, team=args.team, contest=args.contest, model=args.model,
                              partition=args.partition, limit=limit, offset=offset, all_rows=args.all_rows)


def context_mode(argv: Sequence[str]) -> bool:
    """Whether an invocation names the explicit site/calendar association option (exactly, or as
    ``--context-association=<path>``)."""
    return any(token == CONTEXT_OPTION or token.startswith(CONTEXT_OPTION + "=") for token in argv)


#: Other modes' options the context parser recognizes only to refuse the ambiguous combination (CONTEXT_MODE_CONFLICT).
CONTEXT_CONFLICTS = ("--database", "--history-database", "--population-database", REFERENCE_OPTION, ASSOCIATION_OPTION,
                     PREVIEW_OPTION, SHADOW_OPTION, SCHEDULE_OPTION)
#: Temporal flags (TEMPORAL_FLAG_UNSUPPORTED) and inapplicable selectors (SELECTOR_NOT_APPLICABLE) it recognizes.
CONTEXT_TEMPORAL = ("--cutoff", "--as-of")
CONTEXT_STRAY = ("--event", "--orientation", "--slice")


def build_context_parser() -> argparse.ArgumentParser:
    """The explicit BAT-734 site/calendar association mode's parser (selected only when --context-association is
    named); every argument error is a controlled ARGUMENT_INVALID refusal (exit 2, JSON on stderr), never a usage dump.
    Values are kept as the given text, so an explicit empty value is refused by its own rule, never read as absent."""
    from aggie_analytics.retrospective_baseline import context_association as ca  # noqa: PLC0415 - explicit option

    class _ContextParser(argparse.ArgumentParser):
        def error(self, message: str) -> Any:
            raise ca.ContextError("ARGUMENT_INVALID", message)

    parser = _ContextParser(prog="bas-retrospective-baseline-query --context-association", allow_abbrev=False,
                            description="Explicit immutable national retrospective site/calendar association "
                                        "2016-2023 (research only: not a forecast, not PIT admitted, not calibrated, no "
                                        "skill, champion or causal site, rest or travel claim).",
                            epilog=CONTEXT_EPILOG)
    parser.add_argument(CONTEXT_OPTION, dest="context_association", required=True,
                        help="the explicitly selected association database of a verified identity directory (never a "
                             "default)")
    parser.add_argument("--manifest", default=None, help="the release run manifest (default: beside)")
    parser.add_argument("--expect-identity", dest="expect_identity", default=None)
    parser.add_argument("--grain", required=True)
    parser.add_argument("--season", default=None)
    parser.add_argument("--partition", default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--contest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--limit", default=None, help="page size (default 50)")
    parser.add_argument("--offset", default=None, help="page offset (default 0)")
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: the association is research only and never PIT admitted")
    for flag in CONTEXT_CONFLICTS:
        parser.add_argument(flag, dest="conflict_" + flag.lstrip("-").replace("-", "_"), default=None)
    for flag in CONTEXT_TEMPORAL:
        parser.add_argument(flag, dest="temporal_" + flag.lstrip("-").replace("-", "_"), default=None)
    for flag in CONTEXT_STRAY:
        parser.add_argument(flag, dest="stray_" + flag.lstrip("-"), default=None)
    return parser


def run_context(args: argparse.Namespace, anchors: Any = _DEFAULT) -> dict[str, Any]:
    """The explicit site/calendar association mode (BAT-734): every ambiguous, inapplicable or malformed selection is
    refused before any file is read, in the frozen precedence of ``context_association.PRECEDENCE``; then the release
    is verified completely (refit included) and queried."""
    from aggie_analytics.retrospective_baseline import context_association as ca  # noqa: PLC0415 - explicit option

    if args.require_pit:
        raise ca.ContextError("CONTEXT_PIT_NOT_ADMITTED", "the association is RETROSPECTIVE_RESEARCH and "
                                                          "NOT_A_FORECAST; it is never PIT admitted and no as-of claim "
                                                          "is supported")
    conflicts = [name[len("conflict_"):] for name, value in sorted(vars(args).items())
                 if name.startswith("conflict_") and value is not None]
    if conflicts:
        raise ca.ContextError("CONTEXT_MODE_CONFLICT", f"{conflicts} cannot be combined with {CONTEXT_OPTION} "
                                                       "(ambiguous mode selection)")
    temporal = [name[len("temporal_"):] for name, value in sorted(vars(args).items())
                if name.startswith("temporal_") and value is not None]
    if temporal:
        raise ca.ContextError("TEMPORAL_FLAG_UNSUPPORTED", f"{temporal}: no historical as-of or cutoff selector exists "
                                                           "for the retrospective association")
    stray = [name[len("stray_"):] for name, value in sorted(vars(args).items())
             if name.startswith("stray_") and value is not None]
    if stray:
        raise ca.ContextError("SELECTOR_NOT_APPLICABLE", f"{stray} do not apply to the context association grains")
    if args.grain not in ca.GRAINS:
        raise ca.ContextError("UNKNOWN_GRAIN", f"grain must be one of {list(ca.GRAINS)}, got {args.grain!r}")
    limit = 50 if args.limit is None else args.limit
    offset = 0 if args.offset is None else args.offset
    ca.validate_paging(limit, offset, args.all_rows, limit_given=args.limit is not None,
                       offset_given=args.offset is not None)
    ca.validate_selection(args.grain, season=args.season, partition=args.partition, team=args.team,
                          contest=args.contest, model=args.model)
    if args.expect_identity is not None and not ca.IDENTITY_RE.match(args.expect_identity):
        raise ca.ContextError("STALE_CONTEXT_IDENTITY", "--expect-identity must be a SHA-256 identity")
    authority: dict[str, Any] = {} if anchors is _DEFAULT else {"anchors": anchors}
    with ca.ContextAssociation(args.context_association, manifest=args.manifest,
                               expect_identity=args.expect_identity, **authority) as selected:
        return selected.query(args.grain, season=args.season, partition=args.partition, team=args.team,
                              contest=args.contest, model=args.model, limit=limit, offset=offset,
                              all_rows=args.all_rows, limit_given=args.limit is not None,
                              offset_given=args.offset is not None)


def _write_utf8(text: str) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        sys.stdout.flush()
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)


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
                 shadow_profile: Any = _DEFAULT, expansion_contract_sha256: str | None = None,
                 expansion_profile: Any = _DEFAULT, predecessor_profile: Any = _DEFAULT) -> dict[str, Any]:
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
    from aggie_analytics.retrospective_baseline import schedule_expansion  # noqa: PLC0415 - explicit option only

    if schedule_expansion.selects(args.schedule_evidence):
        successor: dict[str, Any] = {} if expansion_contract_sha256 is None else {
            "contract_sha256": expansion_contract_sha256}
        for name, value in (("profile", expansion_profile), ("predecessor_profile", predecessor_profile),
                            ("shadow_profile", shadow_profile)):
            if value is not _DEFAULT:
                successor[name] = value
        with schedule_expansion.ExpansionEvidence(args.schedule_evidence, args.prospective_shadow,
                                                  expect_identity=args.expect_identity, **successor) as chosen:
            return chosen.query(args.grain, cutoff=args.cutoff, season=args.season, event=args.event,
                                team=args.team, limit=args.limit, offset=args.offset, all_rows=args.all_rows)
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
         schedule_contract_sha256: str | None = None, schedule_profile: Any = _DEFAULT,
         expansion_contract_sha256: str | None = None, expansion_profile: Any = _DEFAULT,
         predecessor_profile: Any = _DEFAULT, reference_anchors: Any = _DEFAULT,
         association_anchors: Any = _DEFAULT, context_anchors: Any = _DEFAULT) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if context_mode(tokens):
        from aggie_analytics.retrospective_baseline import context_association as ca  # noqa: PLC0415 - explicit
        try:
            args = build_context_parser().parse_args(tokens)
            result = run_context(args, context_anchors)
        except ca.ContextError as exc:
            print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
            return 2
        _write_utf8(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    if association_mode(tokens):
        from aggie_analytics.retrospective_baseline import personnel_association as pa  # noqa: PLC0415 - explicit
        try:
            args = build_association_parser().parse_args(tokens)
            result = run_association(args, association_anchors)
        except pa.AssociationError as exc:
            print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
            return 2
        _write_utf8(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    if reference_mode(tokens):
        args = build_reference_parser().parse_args(tokens)
        from aggie_analytics.retrospective_baseline import reference  # noqa: PLC0415 - explicit option only
        try:
            result = run_reference(args, reference_anchors)
        except reference.ReferenceError as exc:
            print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
            return 2
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    if schedule_mode(tokens):
        args = build_schedule_parser().parse_args(tokens)
        from aggie_analytics.retrospective_baseline import schedule  # noqa: PLC0415 - explicit option only
        try:
            result = run_schedule(args, schedule_contract_sha256, schedule_profile, shadow_profile,
                                  expansion_contract_sha256, expansion_profile, predecessor_profile)
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
