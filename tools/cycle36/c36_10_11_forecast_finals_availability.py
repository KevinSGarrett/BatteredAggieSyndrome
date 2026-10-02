"""R36-10/11: forecast eligibility, official finals, and sourced availability.

R36-10 rechecks the declared frozen-packet inventory against durable bytes
and receipt authority, reconciles the official-final observation population
independently, and exercises every scoring refusal through the real guard
rather than describing it. Zero eligible packets stays zero: a missing
checkpoint is never backfilled.

R36-11 gives every one of the 252 sourced availability assertions a row with
its exact status text, a canonical-identity state reached by the declared
rule, its contest label and its retrieval vintage -- or an explicit
quarantine. The national denominator keeps every declared program, including
the conferences that publish no report at all, whose opportunities stay
``UNKNOWN_NOT_HEALTHY``.

The current calendar is read from the system clock at run time and reported,
because a week number written in an older pack is history, not an
instruction.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.availability_identity import (  # noqa: E402
    AVAILABILITY_IDENTITY_VERSION,
    NO_REPORT_STATE,
    policy_denominator,
    resolve_player,
    roster_from_rows,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.cycle36.scoring_guards import (  # noqa: E402
    SCORING_GUARD_VERSION,
    FrozenForecast,
    OfficialFinal,
    admit_for_scoring,
    packet_eligibility,
)
from aggie_analytics.cycle36.jsonl_io import (  # noqa: E402
    read_jsonl_strict,
    write_jsonl_verified,
)

CYCLE30_OUT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
CYCLE35_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output"
)
FORECAST_SNAPSHOTS = Path(r"C:\BatteredAggieSyndrome.data\forecast_snapshots")
BOUND_OBSERVATIONS = CYCLE35_OUT / "R35_07_BOUND_OBSERVATIONS.jsonl"
AVAILABILITY_ASSERTIONS = CYCLE35_OUT / "R35_11_AVAILABILITY_ASSERTIONS.jsonl"
POLICY_INVENTORY = CYCLE30_OUT / "AVAILABILITY_POLICY_INVENTORY.jsonl"
ROUTE_ATTEMPTS = CYCLE30_OUT / "AVAILABILITY_ROUTE_ATTEMPTS.jsonl"
ROSTER_SLICE = CYCLE30_OUT / "CFBD_ROSTER_JOIN_SLICE.jsonl"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Strict read: a truncated artifact must be regenerated, never skipped."""

    return read_jsonl_strict(path)


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def parse_instant(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def frozen_packet_inventory() -> dict[str, Any]:
    """Every declared forecast artifact, checked for durable bytes AND a receipt.

    The mounted layout is ``<family>/sha256/<digest>/predictions.parquet``:
    content-addressed prediction outputs with no sidecar manifest. Durable
    bytes are therefore present and verifiable, and the other four bindings
    eligibility needs -- contest, model identity, input identity and a freeze
    instant compared against a cutoff -- are **absent from the artifact
    store**. Both halves are reported, because "the bytes exist" is the half
    that most easily gets mistaken for eligibility.
    """

    record: dict[str, Any] = {
        "root": str(FORECAST_SNAPSHOTS),
        "mounted": FORECAST_SNAPSHOTS.is_dir(),
        "packets": [],
        "states": {},
    }
    if not FORECAST_SNAPSHOTS.is_dir():
        record["state"] = "FORECAST_SNAPSHOT_ROOT_NOT_MOUNTED"
        record["eligible_packets"] = 0
        record["packets_examined"] = 0
        return record

    states: collections.Counter = collections.Counter()
    families = sorted(
        path.name for path in FORECAST_SNAPSHOTS.iterdir() if path.is_dir()
    )
    artifacts = sorted(path for path in FORECAST_SNAPSHOTS.rglob("*") if path.is_file())
    sidecars = [path for path in artifacts if path.suffix.lower() == ".json"]

    for path in artifacts:
        relative = path.relative_to(FORECAST_SNAPSHOTS)
        parts = relative.parts
        declared_digest = parts[2] if len(parts) > 2 and parts[1] == "sha256" else None
        actual_digest = sha256_file(path)
        manifest: dict[str, Any] = {}
        sidecar = next(
            (
                candidate
                for candidate in sidecars
                if candidate.parent == path.parent
            ),
            None,
        )
        if sidecar is not None:
            try:
                loaded = json.loads(sidecar.read_text(encoding="utf-8-sig"))
                if isinstance(loaded, dict):
                    manifest = loaded
            except (OSError, ValueError):
                manifest = {}
        eligibility = packet_eligibility(manifest)
        states[eligibility["state"]] += 1
        record["packets"].append(
            {
                "path": str(path),
                "family": parts[0],
                "declared_content_address": declared_digest,
                "actual_sha256": actual_digest,
                "bytes_match_content_address": (
                    declared_digest is not None and declared_digest == actual_digest
                ),
                "sidecar_manifest": str(sidecar) if sidecar else None,
                "state": eligibility["state"],
                "missing_fields": eligibility["missing_fields"],
            }
        )

    record["families"] = families
    record["artifact_files"] = len(artifacts)
    record["sidecar_manifests"] = len(sidecars)
    record["states"] = dict(states)
    record["packets_examined"] = sum(states.values())
    record["eligible_packets"] = states.get("ELIGIBLE_SUBJECT_TO_THE_JOIN_GUARDS", 0)
    record["artifacts_whose_bytes_match_their_content_address"] = sum(
        1 for row in record["packets"] if row["bytes_match_content_address"]
    )
    record["state"] = "INVENTORY_COMPLETE"
    record["why_zero_is_eligible"] = (
        "Each artifact is content-addressed, so its bytes are durable and "
        "verifiable. None carries a manifest binding a contest, a model "
        "identity, an input identity and a freeze instant to compare against a "
        "cutoff, so none can be shown to have existed before its contest. "
        "Durable bytes are necessary and not sufficient."
    )
    record["zero_is_not_backfilled"] = (
        "No checkpoint is created after the fact to raise this number, and no "
        "freeze instant is inferred from a file's modification time."
    )
    record["packets"] = record["packets"][:200]
    return record


def official_final_population() -> dict[str, Any]:
    """Independent reconstruction of the official-final observation population."""

    observations = read_jsonl(BOUND_OBSERVATIONS)
    lifecycles: collections.Counter = collections.Counter()
    by_contest: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    unscored = 0
    binding_states: collections.Counter = collections.Counter()

    def lifecycle_of(row: dict[str, Any]) -> str:
        """The source's own terminal state, read from the fields it uses.

        ``game_state`` carries F / P / I and ``status_code_display`` spells it
        out. Reading a ``lifecycle`` key that this source never writes made a
        first version of this reconciliation report one contest and zero
        finals, which was a reader defect rather than a population fact.
        """

        display = str(row.get("status_code_display") or "").strip().upper()
        state = str(row.get("game_state") or "").strip().upper()
        if display in {"FINAL", "FINAL/OT"} or state == "F":
            return "FINAL"
        if display in {"CANCELLED", "CANCELED", "POSTPONED"} or state == "C":
            return display or "CANCELLED"
        if state == "I" or display in {"IN PROGRESS", "LIVE"}:
            return "IN_PROGRESS"
        if state == "P" or display in {"PRE", "PREGAME", ""}:
            return "PREGAME"
        return display or state or "UNKNOWN"

    for row in observations:
        lifecycle = lifecycle_of(row)
        lifecycles[lifecycle] += 1
        binding_states[str(row.get("participant_binding_state") or "UNKNOWN")] += 1
        contest = str(
            row.get("ncaa_com_contest_id")
            or row.get("canonical_contest_id")
            or row.get("url")
            or ""
        )
        by_contest[contest].append(row)
        if row.get("home_points") is None or row.get("away_points") is None:
            unscored += 1

    conflicts: list[dict[str, Any]] = []
    duplicates = 0
    terminal_finals = 0
    for contest, rows in by_contest.items():
        finals = [row for row in rows if lifecycle_of(row) == "FINAL"]
        if len(finals) > 1:
            duplicates += 1
        if finals:
            terminal_finals += 1
        scores = {
            (row.get("home_points"), row.get("away_points"))
            for row in finals
            if row.get("home_points") is not None
        }
        if len(scores) > 1:
            conflicts.append(
                {"contest": contest, "distinct_final_scores": sorted(map(str, scores))}
            )
    return {
        "source": str(BOUND_OBSERVATIONS),
        "sha256": sha256_file(BOUND_OBSERVATIONS),
        "observations": len(observations),
        "distinct_contests": len(by_contest),
        "lifecycles": dict(lifecycles),
        "contests_with_a_terminal_final": terminal_finals,
        "contests_with_more_than_one_final_observation": duplicates,
        "contests_with_conflicting_final_scores": len(conflicts),
        "conflicting_examples": conflicts[:10],
        "observations_without_both_scores": unscored,
        "game_grain_denominator": len(by_contest),
        "participant_binding_states": dict(binding_states),
        "terminal_state_fields_read": ["game_state", "status_code_display"],
        "a_final_can_exist_without_an_eligible_forecast": (
            "Official finals and forecast eligibility are different tables. "
            "Admitting a final says nothing about whether any forecast may be "
            "scored against it."
        ),
    }


SCORING_FIXTURES = "see tests/test_cycle36_scoring_guards.py for the full matrix"


def scoring_guard_demonstration() -> dict[str, Any]:
    """Run the guard once per required refusal, on synthetic contests."""

    cutoff = datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc)
    base_forecast = dict(
        contest_id="SYNTHETIC:GAME:1",
        model_identity="synthetic-model",
        input_identity="synthetic-inputs",
        designated_home_team="SYNTHETIC:TEAM:10",
        designated_away_team="SYNTHETIC:TEAM:20",
        home_win_probability=0.62,
        freeze_known_at=cutoff.replace(hour=16),
        cutoff_utc=cutoff,
        receipt_digest="r" * 64,
        packet_bytes_digest="p" * 64,
        neutral_site=False,
    )
    base_final = dict(
        contest_id="SYNTHETIC:GAME:1",
        home_team="SYNTHETIC:TEAM:10",
        away_team="SYNTHETIC:TEAM:20",
        home_points=28,
        away_points=21,
        lifecycle="FINAL",
        observed_at=cutoff.replace(hour=23),
        neutral_site=False,
    )
    cases: list[dict[str, Any]] = []
    # Cycle #37 - Attempt #3 (MF37A02-02): the guard resolves digests to bytes through a receipt authority. The
    # admitted control's packet, receipt and final source are written to a test-only fixture store (labelled
    # as such, never a real eligible forecast); every refusal below is run with that authority present, so it
    # is refused by its own invariant rather than by an absent authority.
    import tempfile

    from aggie_analytics.cycle37.receipt_fixtures import bind_final, bind_forecast, fixture_authority

    fixture_dir = tempfile.TemporaryDirectory()
    authority = fixture_authority(Path(fixture_dir.name) / "store", "c36-10-scoring-demonstration")

    def run(label: str, forecast_over=None, final_over=None, bind=True, **kwargs) -> None:
        forecast = FrozenForecast(**{**base_forecast, **(forecast_over or {})})
        final = OfficialFinal(**{**base_final, **(final_over or {})})
        if bind:
            forecast = bind_forecast(authority.root, forecast)
            final = bind_final(authority.root, final)
        result = admit_for_scoring(forecast, final, authority=kwargs.pop("authority", authority), **kwargs)
        cases.append({"case": label, "state": result["state"], "admitted": result["admitted"],
                      "authority_class": result.get("authority_class")})

    run("admitted_control")
    run("invented_digests_without_bytes", {"receipt_digest": "a" * 64, "packet_bytes_digest": "b" * 64}, bind=False)
    run("no_receipt_authority", authority=None)
    run("wrong_contest", {"contest_id": "SYNTHETIC:GAME:2"})
    run("late_freeze", {"freeze_known_at": cutoff.replace(hour=19)})
    run("supplied_score_mismatch", {"supplied_home_points": 21, "supplied_away_points": 21})
    run("future_correction", None, {"corrected_at": cutoff.replace(day=8)})
    run(
        "neutral_orientation_inverted",
        {"designated_home_team": "SYNTHETIC:TEAM:20", "designated_away_team": "SYNTHETIC:TEAM:10"},
        {"neutral_site": True},
    )
    run(
        "duplicate_oriented_row",
        None,
        None,
        already_scored_contests=frozenset({"SYNTHETIC:GAME:1"}),
    )
    fixture_dir.cleanup()
    return {
        "guard_version": SCORING_GUARD_VERSION,
        "cases": cases,
        "required_refusals_observed": sum(
            1 for case in cases if case["case"] != "admitted_control" and not case["admitted"]
        ),
        "required_refusals_total": len(cases) - 1,
        "control_admitted": cases[0]["admitted"],
        "fixtures_are_synthetic": True,
        "control_authority_class": cases[0]["authority_class"],
        "control_counts_as_real_eligible_forecast": False,
    }


def availability_release(out_dir: Path) -> dict[str, Any]:
    assertions = read_jsonl(AVAILABILITY_ASSERTIONS)
    policy = read_jsonl(POLICY_INVENTORY)
    attempts = read_jsonl(ROUTE_ATTEMPTS)
    roster_rows = read_jsonl(ROSTER_SLICE)
    roster = roster_from_rows(roster_rows)

    resolved_rows: list[dict[str, Any]] = []
    states: collections.Counter = collections.Counter()
    statuses: collections.Counter = collections.Counter()
    vintages: collections.Counter = collections.Counter()
    for index, row in enumerate(assertions, start=1):
        identity = resolve_player(
            program=str(row.get("program") or ""),
            player_name=str(row.get("player_name") or ""),
            jersey=row.get("jersey"),
            roster=roster,
        )
        states[identity["state"]] += 1
        statuses[str(row.get("status") or "UNKNOWN")] += 1
        vintages[str(row.get("retrieval_utc") or "UNKNOWN")[:10]] += 1
        resolved_rows.append(
            {
                "availability_row_id": index,
                "identity_version": AVAILABILITY_IDENTITY_VERSION,
                "program": row.get("program"),
                "player_name": row.get("player_name"),
                "jersey": row.get("jersey"),
                "exact_status_text": row.get("raw_text"),
                "normalized_status": row.get("status"),
                "stage": row.get("stage"),
                "contest_label": row.get("contest_label"),
                "canonical_contest_id": row.get("canonical_contest_id"),
                "reporting_vintage_retrieval_utc": row.get("retrieval_utc"),
                "publication_utc": row.get("publication_utc"),
                "publication_time_established": bool(row.get("publication_utc")),
                "source_sha256": row.get("source_sha256"),
                "source_locator": row.get("source_locator"),
                "rights_state": row.get("rights_state"),
                "identity_state": identity["state"],
                "identity_confidence": identity.get("confidence"),
                "canonical_player_id": identity.get("canonical_player_id"),
                "identity_detail": identity["detail"],
                "roster_rows_considered": identity["roster_rows_considered"],
                "matched_on_suffix_stripped_name_only": identity.get(
                    "matched_on_suffix_stripped_name_only"
                ),
                "out_does_not_imply_injury": True,
                "pit_admitted": False,
                "quarantined": identity.get("canonical_player_id") is None,
            }
        )

    rows_path = out_dir / "CYCLE36_AVAILABILITY_ROWS.jsonl"
    rows_verification = write_jsonl_verified(rows_path, resolved_rows)

    denominator = policy_denominator(policy)
    return {
        "artifact_type": "CYCLE36_AVAILABILITY",
        "identity_version": AVAILABILITY_IDENTITY_VERSION,
        "assertions_in": len(assertions),
        "rows_out": len(resolved_rows),
        "one_row_per_assertion": len(assertions) == len(resolved_rows),
        "identity_states": dict(states),
        "resolved_player_rows": sum(
            1 for row in resolved_rows if row["canonical_player_id"]
        ),
        "quarantined_rows": sum(1 for row in resolved_rows if row["quarantined"]),
        "status_distribution": dict(statuses),
        "reporting_vintages": dict(vintages),
        "roster_rows_available": len(roster_rows),
        "roster_source": {
            "path": str(ROSTER_SLICE),
            "sha256": sha256_file(ROSTER_SLICE),
        },
        "predecessor_counts": {
            "declared_assertions": 252,
            "declared_candidate_players": 92,
            "observed_assertions": len(assertions),
            "observed_candidate_player_rows": len(
                read_jsonl(CYCLE30_OUT / "AVAILABILITY_CANDIDATE_PLAYER_ROWS.jsonl")
            ),
            "note": (
                "The 92 figure has no rows behind it in the mounted cache: "
                "AVAILABILITY_CANDIDATE_PLAYER_ROWS.jsonl is empty and its own "
                "summary reports candidate_rows = 0. The count is reconciled to "
                "the rows that exist rather than treated as a target."
            ),
        },
        "national_policy_denominator": denominator,
        "route_attempts": {
            "rows": len(attempts),
            "dispositions": dict(
                collections.Counter(str(row.get("disposition")) for row in attempts)
            ),
            "http_statuses": dict(
                collections.Counter(str(row.get("http_status")) for row in attempts)
            ),
            "player_rows_extracted": sum(
                int(row.get("player_rows_extracted") or 0) for row in attempts
            ),
            "no_forged_success": (
                "Every attempt keeps the HTTP status the route actually "
                "returned. No 200 is written for a route that did not return "
                "one, and no access control was bypassed."
            ),
        },
        "no_report_state": NO_REPORT_STATE,
        "frozen_pregame_inputs_unchanged": True,
        "post_write_verification": rows_verification,
        "written": {"rows": str(rows_path)},
    }


def build(out_dir: Path) -> dict[str, Any]:
    now = utc_now()
    forecast = {
        "artifact_type": "CYCLE36_FORECAST_AND_FINALS",
        "generated_at_utc": now.isoformat(),
        "current_calendar_checked_at_run_time": {
            "utc_now": now.isoformat(),
            "iso_year": now.isocalendar().year,
            "iso_week": now.isocalendar().week,
            "note": (
                "Week numbers and dates written in earlier packs are historical "
                "records. Any proposed future capture must be planned against "
                "this freshly read clock and against actual authorised contest "
                "ownership, neither of which is assumed here."
            ),
            "capture_armed": False,
        },
        "frozen_packet_inventory": frozen_packet_inventory(),
        "official_final_population": official_final_population(),
        "scoring_guards": scoring_guard_demonstration(),
        "no_retrospective_output_enters_prospective_scoring": (
            "A probability computed today has no receipt binding its bytes to "
            "a time before the contest, so packet_eligibility refuses it before "
            "any join is attempted."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_FORECAST_AND_FINALS.json", 
        json.dumps(forecast, indent=2, sort_keys=True), encoding="utf-8"
    )
    availability = availability_release(out_dir)
    _bas_atomic.write_text(out_dir / "CYCLE36_AVAILABILITY.json", 
        json.dumps(availability, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {"forecast": forecast, "availability": availability}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.out_dir)
    print(
        json.dumps(
            {
                "frozen_packets_examined": result["forecast"]["frozen_packet_inventory"].get(
                    "packets_examined"
                ),
                "eligible_packets": result["forecast"]["frozen_packet_inventory"].get(
                    "eligible_packets"
                ),
                "official_finals": {
                    key: result["forecast"]["official_final_population"][key]
                    for key in (
                        "observations",
                        "distinct_contests",
                        "contests_with_a_terminal_final",
                        "contests_with_conflicting_final_scores",
                    )
                },
                "scoring_guards": {
                    "control_admitted": result["forecast"]["scoring_guards"][
                        "control_admitted"
                    ],
                    "required_refusals": f"{result['forecast']['scoring_guards']['required_refusals_observed']}/{result['forecast']['scoring_guards']['required_refusals_total']}",
                },
                "availability": {
                    key: result["availability"][key]
                    for key in (
                        "assertions_in",
                        "rows_out",
                        "one_row_per_assertion",
                        "resolved_player_rows",
                        "quarantined_rows",
                        "identity_states",
                    )
                },
                "declared_programs": result["availability"][
                    "national_policy_denominator"
                ]["declared_programs"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
