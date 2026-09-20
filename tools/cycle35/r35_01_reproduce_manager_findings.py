"""R35-01: reproduce every manager adversarial counterexample at the actual head.

Each probe runs the REAL imported implementation (never a re-implementation of
it) and records what the code actually does right now, plus a positive control
that must reject. A probe whose control also passes proves nothing, so the
control verdict is recorded beside every finding verdict.

Output is a machine-readable reproduction ledger; it is deliberately silent
about whether a defect is "fixed" -- that determination belongs to the unit
that repairs it, re-running this same harness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPRO: list[dict[str, Any]] = []


def record(
    finding: str,
    probe: str,
    *,
    defect_reproduced: bool,
    control_rejected: bool | None,
    detail: dict[str, Any],
) -> None:
    REPRO.append(
        {
            "finding_id": finding,
            "probe": probe,
            "defect_reproduced_at_head": defect_reproduced,
            "positive_control_rejected": control_rejected,
            "control_is_meaningful": control_rejected is True,
            "detail": detail,
        }
    )


def _write_receipt(root: Path, payload: dict[str, Any]) -> tuple[Path, str]:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = root / ("receipt_" + digest[:12] + ".json")
    path.write_bytes(raw)
    return path, digest


def probe_mr34_01(tmp: Path) -> None:
    """Post-kickoff self-written receipt + wrong participants are scored."""
    from aggie_analytics.cycle33.scoring_successor import score_unique_frozen_games

    root = tmp / "mr34_01"
    root.mkdir(parents=True, exist_ok=True)
    kickoff = "2026-09-05T23:00:00+00:00"
    payload = {
        "ncaa_contest_id": "fixture-game",
        "candidate_id": "fixture-model",
        "cohort": "fixture",
        "checkpoint": "T24",
        "probability_home": 0.9,
        "frozen_at_utc": "2026-09-06T02:00:00+00:00",
    }
    _, digest = _write_receipt(root, payload)
    forecast = {
        "ncaa_contest_id": "fixture-game",
        "candidate_id": "fixture-model",
        "cohort": "fixture",
        "checkpoint": "T24",
        "probability_home": 0.9,
        "frozen": True,
        "freeze_receipt": {"receipt_id": "r1", "receipt_sha256": digest},
        "home_canonical_team_id": "OTHER_HOME",
        "away_canonical_team_id": "OTHER_AWAY",
    }
    observation = {
        "ncaa_contest_id": "fixture-game",
        "home_points": 30,
        "away_points": 10,
        "home_canonical_team_id": "REAL_HOME",
        "away_canonical_team_id": "REAL_AWAY",
        "status_code_display": "Final",
        "game_state": "F",
        "kickoff_utc": kickoff,
    }
    out = score_unique_frozen_games(
        [observation],
        forecasts=[forecast],
        as_of_utc=datetime(2026, 9, 20, tzinfo=timezone.utc),
        search_roots=[root],
    )
    scored = out["scored_candidate_checkpoint_rows"]

    control = dict(forecast)
    control["freeze_receipt"] = {"receipt_id": "r1", "receipt_sha256": "a" * 64}
    ctl = score_unique_frozen_games(
        [observation],
        forecasts=[control],
        as_of_utc=datetime(2026, 9, 20, tzinfo=timezone.utc),
        search_roots=[root],
    )
    record(
        "MR34-01",
        "post_kickoff_receipt_and_wrong_participants_scored",
        defect_reproduced=scored == 1,
        control_rejected=ctl["scored_candidate_checkpoint_rows"] == 0,
        detail={
            "scored_candidate_checkpoint_rows": scored,
            "kickoff_utc": kickoff,
            "receipt_frozen_at_utc": payload["frozen_at_utc"],
            "freeze_after_kickoff": True,
            "forecast_participants": ["OTHER_HOME", "OTHER_AWAY"],
            "game_participants": ["REAL_HOME", "REAL_AWAY"],
            "control_scored_rows": ctl["scored_candidate_checkpoint_rows"],
        },
    )


def probe_mr34_02(tmp: Path) -> None:
    """Self-rehashed future packet with Boolean probability reads ELIGIBLE."""
    from aggie_analytics.cycle33.forecast_inventory import inspect_forecast_eligibility

    root = tmp / "mr34_02"
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "contest_id": "synthetic-contest",
        "frozen": True,
        "issued_at_utc": "2099-01-01T00:00:00+00:00",
        "known_at_utc": "2099-01-01T00:00:00+00:00",
        "probability_home": True,
    }
    canonical = {k: v for k, v in payload.items() if k != "receipt_sha256"}
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    path = root / "synthetic_forecast.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    verdict = inspect_forecast_eligibility(path)

    control_payload = dict(payload)
    control_payload["receipt_sha256"] = "f" * 64
    control_path = root / "control_forecast.json"
    control_path.write_text(json.dumps(control_payload), encoding="utf-8")
    ctl = inspect_forecast_eligibility(control_path)
    record(
        "MR34-02",
        "self_rehashed_future_boolean_forecast_eligible",
        defect_reproduced=verdict["eligibility_verdict"] == "ELIGIBLE",
        control_rejected=ctl["eligibility_verdict"] == "INELIGIBLE",
        detail={
            "eligibility_verdict": verdict["eligibility_verdict"],
            "failed_predicates": verdict["failed_predicates"],
            "probability_home_type": "bool",
            "issued_at_utc": payload["issued_at_utc"],
            "control_verdict": ctl["eligibility_verdict"],
        },
    )


def probe_mr34_03() -> None:
    """Substring person confirmation and string-'false' role support."""
    from aggie_analytics.cycle33.confirmed_spans import (
        quarantine_unlocatable_cell,
        require_locatable_confirmed,
    )

    html = (
        "<table><tr><td>John Smithson</td><td>Head Coach</td></tr></table>"
    )
    try:
        substring = require_locatable_confirmed(
            html, person="John Smith", title="Head Coach"
        )
        substring_confirmed = bool(substring.get("person_record_bound")) and bool(
            substring.get("role_claim_supported")
        )
        substring_detail = json.dumps(substring, default=str)[:400]
    except Exception as exc:  # noqa: BLE001 - recording actual behavior
        substring_confirmed = False
        substring_detail = type(exc).__name__ + ": " + str(exc)

    try:
        control = require_locatable_confirmed(
            html, person="Nobody Here", title="Head Coach"
        )
        control_rejected = not control.get("person_record_bound")
    except Exception:  # noqa: BLE001
        control_rejected = True

    record(
        "MR34-03",
        "substring_person_confirmed_from_longer_name",
        defect_reproduced=substring_confirmed,
        control_rejected=control_rejected,
        detail={
            "source_html": html,
            "claimed_person": "John Smith",
            "result": substring_detail,
        },
    )

    cell = {
        "person": "A Person",
        "disposition": "CONFIRMED_APPOINTMENT",
        "episode_refs": [
            {"person": "A Person", "title": "Head Coach", "role_claim_supported": "false"}
        ],
    }
    try:
        q = quarantine_unlocatable_cell(cell)
        q_text = json.dumps(q, default=str)[:400]
        string_false_confirms = q.get("disposition") == "CONFIRMED_APPOINTMENT"
    except Exception as exc:  # noqa: BLE001
        q_text = type(exc).__name__ + ": " + str(exc)
        string_false_confirms = False
    cell_ctl = {
        "person": "A Person",
        "disposition": "CONFIRMED_APPOINTMENT",
        "episode_refs": [
            {"person": "A Person", "title": "Head Coach", "role_claim_supported": False}
        ],
    }
    try:
        q_ctl = quarantine_unlocatable_cell(cell_ctl)
        ctl_rejected = q_ctl.get("disposition") != "CONFIRMED_APPOINTMENT"
    except Exception:  # noqa: BLE001
        ctl_rejected = True
    record(
        "MR34-03",
        "string_false_treated_as_role_support",
        defect_reproduced=string_false_confirms,
        control_rejected=ctl_rejected,
        detail={"role_claim_supported": "false (str)", "result": q_text},
    )


def probe_mr34_04() -> None:
    """Caller occupant overrides contradictory page person; no role/time join."""
    from aggie_analytics.cycle33 import career_identity

    # The page's own evidence says Alice; the caller asserts Bob via the
    # page-level `occupant_person` field. Contrary page identity must win.
    page = {
        "wikimedia_page_id": "synthetic-alice",
        "title": "Alice Example (American football)",
        "occupant_person": "Bob Example",
        "episodes": [
            {
                "person": "Alice Example",
                "sport": "American football",
                "program_raw": "Example State",
            }
        ],
    }
    try:
        got = career_identity.join_occupant_to_pages(
            person="Bob Example",
            program_display="Example State",
            pages=[page],
        )
        state = got.get("career_join_state") if isinstance(got, dict) else str(got)
    except TypeError as exc:
        got = None
        state = "SIGNATURE_MISMATCH: " + str(exc)
    except Exception as exc:  # noqa: BLE001
        got = None
        state = type(exc).__name__
    record(
        "MR34-04",
        "conflicting_page_person_accepted_via_caller_override",
        defect_reproduced=state == "EVIDENCE_BOUND_CAREER_JOIN",
        control_rejected=None,
        detail={
            "claimed_occupant": "Bob Example",
            "page_person_evidence": "Alice Example",
            "career_join_state": state,
            "result": json.dumps(got, default=str)[:400],
        },
    )

    # Process-address fallback identity (R35-02: must be eliminated).
    anon_a: dict[str, Any] = {}
    anon_b: dict[str, Any] = {}
    key_a = career_identity.page_identity_key(anon_a)
    key_b = career_identity.page_identity_key(anon_b)
    record(
        "MR34-04",
        "page_identity_key_falls_back_to_process_address",
        defect_reproduced=key_a.startswith("opaque:"),
        control_rejected=key_a != key_b,
        detail={
            "key_a": key_a,
            "key_b": key_b,
            "both_objects_retained": True,
            "note": "Both dicts are held live simultaneously so neither id() "
            "can reuse a freed address (manager's corrected probe).",
        },
    )

    # Role and time are absent from the join's required arguments entirely.
    import inspect as _inspect

    sig = _inspect.signature(career_identity.join_occupant_to_pages)
    params = sorted(sig.parameters)
    record(
        "MR34-04",
        "career_join_does_not_bind_role_or_time",
        defect_reproduced=not any(
            p in params for p in ("role", "season", "valid_from", "checkpoint")
        ),
        control_rejected=None,
        detail={"join_parameters": params},
    )


def probe_mr34_06(db_path: Path) -> None:
    """unresolved_roles returns 0 while direct SQL finds unresolved rows."""
    from aggie_analytics.cycle33 import query as q

    if not db_path.exists():
        record(
            "MR34-06",
            "unresolved_roles_hides_rows",
            defect_reproduced=False,
            control_rejected=None,
            detail={"error": "db absent: " + str(db_path)},
        )
        return
    con = sqlite3.connect("file:" + str(db_path) + "?mode=ro", uri=True)
    try:
        sql_rows = con.execute(
            "SELECT COUNT(*) FROM staff_role_cells "
            "WHERE disposition='ROSTER_OBSERVATION_UNRESOLVED'"
        ).fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM staff_role_cells").fetchone()[0]
    finally:
        con.close()
    try:
        rcon = q.connect_readonly(db_path)
        try:
            returned_n = len(q.unresolved_roles(rcon))
        finally:
            rcon.close()
    except Exception as exc:  # noqa: BLE001
        returned_n = type(exc).__name__ + ": " + str(exc)
    record(
        "MR34-06",
        "unresolved_roles_hides_rows",
        defect_reproduced=(returned_n == 0 and sql_rows > 0),
        control_rejected=None,
        detail={
            "direct_sql_unresolved": sql_rows,
            "query_returned": returned_n,
            "total_rows": total,
            "db": str(db_path),
        },
    )


def probe_mr34_08() -> None:
    """Travel context accepts venue_confirmed='false' and missing identities."""
    from aggie_analytics.cycle33 import neutral

    try:
        got = neutral.travel_context(
            {"neutral_site": False},
            home_distance=1.0,
            away_distance=2.0,
            venue_confirmed="false",  # string, not a boolean
        )
        detail = json.dumps(got, default=str)[:600]
        missing_ids = [
            k
            for k in (
                "canonical_contest_id",
                "administrative_home_id",
                "administrative_away_id",
                "venue_id",
                "venue_timezone",
            )
            if got.get(k) is None
        ]
        accepted = got.get("home_travel_distance") == 1.0
        detail = {
            "result": detail,
            "missing_identity_fields": missing_ids,
            "venue_confirmed_passed": "'false' (str, truthy)",
        }
    except Exception as exc:  # noqa: BLE001
        detail = {"error": type(exc).__name__ + ": " + str(exc)}
        accepted = False
    record(
        "MR34-08",
        "string_false_venue_confirmation_with_missing_ids",
        defect_reproduced=accepted,
        control_rejected=None,
        detail=detail,
    )


def probe_mr34_09() -> None:
    """Contradictory supplied winner survives final admission."""
    from aggie_analytics.cycle33.official_finals import (
        competing_observations,
        is_eligible_official_final,
    )

    obs = {
        "ncaa_contest_id": "fixture-game",
        "home_points": 30,
        "away_points": 10,
        "home_canonical_team_id": "REAL_HOME",
        "away_canonical_team_id": "REAL_AWAY",
        "home_name": "A",
        "away_name": "B",
        "status_code_display": "Final",
        "game_state": "F",
        "winner": "AWAY",
    }
    grouped = competing_observations([obs])
    admitted = [
        g for g in grouped["admitted_unique_games"] if is_eligible_official_final(g)
    ]
    record(
        "MR34-09",
        "contradictory_winner_admitted_as_official_final",
        defect_reproduced=len(admitted) == 1,
        control_rejected=None,
        detail={
            "admitted": len(admitted),
            "home_points": 30,
            "away_points": 10,
            "supplied_winner": "AWAY",
            "quarantined": len(grouped["quarantined_conflicts"]),
        },
    )


def probe_mr34_07() -> None:
    """LOSSLESS verdict while dropping four supplied semantic fields."""
    from aggie_analytics.cycle33 import all22_adapter

    episode = {
        # Every field the adapter declares mandatory, so encoding succeeds...
        "person": "A Coach",
        "role": "OC",
        "source_title": "Official staff page",
        "source_class": "OFFICIAL_PROGRAM_PAGE",
        "valid_time_precision": "SEASON",
        "recorded_at_utc": "2026-01-01T00:00:00+00:00",
        "schema_version": "StaffRoleEpisodeV1Proposed",
        "program_id": "prog-1",
        "person_id": "p1",
        "season": "2021",
        "valid_from": "2020-01-01",
        "valid_to": "2021-01-01",
        "receipt_sha256": "b" * 64,
        "source_span": {"start": 0, "end": 10},
        # ...plus four supplied semantic fields the envelope never carries.
        "conflict_state": "DISPUTED",
        "responsibility": "play_calling",
        "rights_state": "RESTRICTED",
        "source_revision": "rev-123",
    }
    try:
        encoded = all22_adapter.encode_episode(episode)
        report = all22_adapter.verify_lossless_round_trip(episode)
        lossless = bool(report.get("lossless"))
        blob = json.dumps(encoded, default=str)
        dropped = [
            k
            for k in (
                "conflict_state",
                "responsibility",
                "rights_state",
                "source_revision",
            )
            if k not in blob
        ]
        detail = {
            "lossless": lossless,
            "dropped_fields": dropped,
            "report": json.dumps(report, default=str)[:400],
        }
    except Exception as exc:  # noqa: BLE001
        lossless = False
        dropped = []
        detail = {"error": type(exc).__name__ + ": " + str(exc)}
    record(
        "MR34-07",
        "lossless_true_while_dropping_semantic_fields",
        defect_reproduced=lossless and bool(dropped),
        control_rejected=None,
        detail=detail,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default="")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="bas_r35_01_") as td:
        tmp = Path(td)
        for fn, kwargs in (
            (probe_mr34_01, {"tmp": tmp}),
            (probe_mr34_02, {"tmp": tmp}),
            (probe_mr34_03, {}),
            (probe_mr34_04, {}),
            (probe_mr34_07, {}),
            (probe_mr34_08, {}),
            (probe_mr34_09, {}),
        ):
            try:
                fn(**kwargs)
            except Exception as exc:  # noqa: BLE001
                record(
                    fn.__name__,
                    "HARNESS_ERROR",
                    defect_reproduced=False,
                    control_rejected=None,
                    detail={"error": type(exc).__name__ + ": " + str(exc)},
                )
        if args.db:
            try:
                probe_mr34_06(Path(args.db))
            except Exception as exc:  # noqa: BLE001
                record(
                    "MR34-06",
                    "HARNESS_ERROR",
                    defect_reproduced=False,
                    control_rejected=None,
                    detail={"error": type(exc).__name__ + ": " + str(exc)},
                )

    out = {
        "artifact_type": "CYCLE35_R35_01_MANAGER_FINDING_REPRODUCTION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "probes": REPRO,
        "reproduced_count": sum(1 for r in REPRO if r["defect_reproduced_at_head"]),
        "probe_count": len(REPRO),
        "note": "Reproduction at the Cycle #35 starting head. Absence of "
        "reproduction is recorded verbatim and requires separate "
        "false-positive adjudication; it is not a fix claim.",
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {r["probe"]: r["defect_reproduced_at_head"] for r in REPRO}, indent=1
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
