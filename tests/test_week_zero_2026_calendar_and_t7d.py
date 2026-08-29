"""Deterministic and tamper coverage for the Week Zero 2026 calendar and T-7D gate.

Every test here is offline. Mutated copies are written under a temporary directory so a
test run can never rewrite a tracked artifact.
"""

from __future__ import annotations

import json
import shutil
import tempfile

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.data.week_zero_2026_calendar import (
    CHECKPOINT_CAPTURED,
    CHECKPOINT_MISSED,
    CHECKPOINT_OPEN,
    CONTRACT_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    SOURCE_SUBSTITUTION_QUERY,
    WEEK_ONE,
    WEEK_ZERO,
    assert_forecasts_unrevised,
    assert_no_backdated_capture,
    confirm_official_kickoff,
    evaluate_checkpoints,
    gate_identity_of,
    load_contract,
    parse_tamu_official_events,
    reconcile_membership,
    select_official_event,
    taxonomy_label,
    validate_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

OFFICIAL_EVENT_DOCUMENT = (
    '<html><body><span>Kyle Field</span><a>ESPN</a><strong>Missouri State</strong>'
    '<script type="application/ld+json">'
    '{"@context":"https://schema.org/","@id":"https://12thman.com/x#/schema/event/1",'
    '"@type":"Event","description":"Texas A&M vs. Missouri State",'
    '"eventAttendanceMode":"MixedEventAttendanceMode","eventStatus":"EventScheduled",'
    '"name":"Texas A&M vs. Missouri State","startDate":"2026-09-05T23:00:00.000000Z",'
    '"eventSchedule":{"@type":"Schedule","startDate":"2026-09-05","startTime":"18:00:00",'
    '"scheduleTimezone":"America/Chicago"},'
    '"location":{"@type":"Place","name":"College Station","address":{}}}'
    "</script></body></html>"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class WeekZeroCalendarAndT7DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract(REPO_ROOT)
        cls.gate = read_json(REPO_ROOT / GATE_RELATIVE)
        cls.event = select_official_event(
            parse_tamu_official_events(OFFICIAL_EVENT_DOCUMENT), contract=cls.contract
        )

    # -- merged artifact -----------------------------------------------------

    def test_merged_gate_validates(self) -> None:
        outcome = validate_artifact(REPO_ROOT)
        self.assertEqual(outcome["result"], "PASS", outcome["findings"])

    def test_gate_identity_is_reproducible(self) -> None:
        self.assertEqual(gate_identity_of(self.gate), self.gate["gate_identity"])

    def test_replay_binds_the_gate_identity(self) -> None:
        replay = read_json(REPO_ROOT / EVIDENCE_RELATIVE)
        self.assertEqual(replay["gate_identity"], self.gate["gate_identity"])

    def test_t7d_was_captured_before_its_deadline(self) -> None:
        row = next(
            item for item in self.gate["checkpoint_ledger"] if item["checkpoint_id"] == "T_MINUS_7D"
        )
        self.assertEqual(row["state"], CHECKPOINT_CAPTURED)
        self.assertLess(row["captured_at_utc"], row["deadline_utc"])

    def test_future_checkpoints_are_not_executed_early(self) -> None:
        for checkpoint_id in ("T_MINUS_24H", "T_MINUS_90M"):
            row = next(
                item
                for item in self.gate["checkpoint_ledger"]
                if item["checkpoint_id"] == checkpoint_id
            )
            self.assertEqual(row["state"], CHECKPOINT_OPEN)
            self.assertFalse(row["executed_by_this_unit"])
            self.assertIsNone(row["captured_at_utc"])

    def test_the_official_kickoff_is_independently_confirmed(self) -> None:
        confirmation = self.gate["official_kickoff_confirmation"]
        self.assertTrue(confirmation["kickoff_utc_independently_confirmed"])
        self.assertEqual(confirmation["official_structured_start_utc"], "2026-09-05T23:00:00Z")
        self.assertEqual(
            confirmation["effective_kickoff_utc_for_eligibility"], "2026-09-05T23:00:00Z"
        )
        self.assertFalse(confirmation["retrieval_time_used_as_kickoff_time"])

    # -- corrected taxonomy --------------------------------------------------

    def test_corrected_taxonomy_labels(self) -> None:
        self.assertEqual(taxonomy_label(self.contract, "2026-08-29"), WEEK_ZERO)
        self.assertEqual(taxonomy_label(self.contract, "2026-09-05"), WEEK_ONE)
        self.assertEqual(
            taxonomy_label(self.contract, "2026-08-22"), SOURCE_SUBSTITUTION_QUERY
        )
        with self.assertRaises(ValueError):
            taxonomy_label(self.contract, "2026-10-01")

    def test_relabelling_never_moves_a_contest(self) -> None:
        rows = [
            {
                "game_date": "2026-08-29",
                "corrected_label": WEEK_ZERO,
                "date_observation_state": "OFFICIAL_CONTESTS_PRESENT",
                "official_contest_count": 8,
            }
        ]
        with self.assertRaises(ValueError):
            reconcile_membership(
                rows,
                predecessor_observations={
                    "2026-08-29": {
                        "date_observation_state": "OFFICIAL_CONTESTS_PRESENT",
                        "official_contests_enumerated": 7,
                    }
                },
            )

    def test_a_source_observation_change_is_recorded_not_rejected(self) -> None:
        rows = [
            {
                "game_date": "2026-08-27",
                "corrected_label": WEEK_ZERO,
                "date_observation_state": "SOURCE_SUBSTITUTED_A_DIFFERENT_DATE",
                "official_contest_count": 0,
            }
        ]
        reconciled = reconcile_membership(
            rows,
            predecessor_observations={
                "2026-08-27": {
                    "date_observation_state": "OFFICIAL_CONTESTS_PRESENT",
                    "official_contests_enumerated": 4,
                }
            },
        )
        self.assertEqual(
            reconciled[0]["membership_reconciliation"],
            "SOURCE_OBSERVATION_STATE_CHANGED_AT_THE_OFFICIAL_HOST",
        )
        self.assertEqual(reconciled[0]["official_contest_count_delta"], -4)

    # -- mutation: backdated capture ----------------------------------------

    def test_backdated_capture_is_rejected(self) -> None:
        window_opened = datetime(2026, 8, 22, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            assert_no_backdated_capture(
                [{"retrieved_at_utc": "2026-08-01T00:00:00Z", "source_uri": "https://example"}],
                earliest_permitted=window_opened,
            )
        assert_no_backdated_capture(
            [{"retrieved_at_utc": "2026-08-29T03:45:32Z", "source_uri": "https://example"}],
            earliest_permitted=window_opened,
        )

    # -- mutation: altered official kickoff ---------------------------------

    def test_an_earlier_official_instant_is_rejected(self) -> None:
        event = {**self.event, "start_date_utc_text": "2026-09-05T22:00:00.000000Z"}
        with self.assertRaises(ValueError):
            confirm_official_kickoff(
                contract=self.contract, event=event, document=OFFICIAL_EVENT_DOCUMENT
            )

    def test_a_later_official_instant_withholds_confirmation_and_keeps_the_bound(self) -> None:
        event = {**self.event, "start_date_utc_text": "2026-09-06T02:00:00.000000Z"}
        confirmation = confirm_official_kickoff(
            contract=self.contract, event=event, document=OFFICIAL_EVENT_DOCUMENT
        )
        self.assertFalse(confirmation["kickoff_utc_independently_confirmed"])
        self.assertEqual(
            confirmation["effective_kickoff_utc_for_eligibility"], "2026-09-05T23:00:00Z"
        )

    def test_a_malformed_official_instant_is_rejected(self) -> None:
        for text in ("2026-09-05T23:00:00", "2026-09-05T23:00:00.abcZ", "not-a-time"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    confirm_official_kickoff(
                        contract=self.contract,
                        event={**self.event, "start_date_utc_text": text},
                        document=OFFICIAL_EVENT_DOCUMENT,
                    )

    # -- mutation: false independent confirmation ---------------------------

    def test_false_independent_confirmation_is_withheld(self) -> None:
        stripped = OFFICIAL_EVENT_DOCUMENT.replace("Kyle Field", "Unnamed Venue").replace(
            "<a>ESPN</a>", "<a>Unknown</a>"
        )
        confirmation = confirm_official_kickoff(
            contract=self.contract, event=self.event, document=stripped
        )
        self.assertFalse(confirmation["kickoff_utc_independently_confirmed"])
        self.assertEqual(
            confirmation["confirmation_state"],
            "OFFICIAL_REQUIRED_TOKENS_ABSENT_SO_CONFIRMATION_IS_WITHHELD",
        )

    def test_a_substituted_contest_description_is_rejected(self) -> None:
        substituted = OFFICIAL_EVENT_DOCUMENT.replace("Missouri State", "Sam Houston")
        with self.assertRaises(ValueError):
            select_official_event(
                parse_tamu_official_events(substituted), contract=self.contract
            )

    # -- mutation: deadline bypass ------------------------------------------

    def test_a_capture_after_the_deadline_becomes_missed_cutoff(self) -> None:
        now = datetime.now(timezone.utc)
        elapsed_deadline = now - timedelta(hours=2)
        contract = {
            **self.contract,
            "checkpoints": [
                {
                    **checkpoint,
                    "deadline_utc": elapsed_deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                if checkpoint["checkpoint_id"] == "T_MINUS_7D"
                else checkpoint
                for checkpoint in self.contract["checkpoints"]
            ],
        }
        rows = evaluate_checkpoints(
            contract=contract,
            capture_times={"T_MINUS_7D": now - timedelta(hours=1)},
            execution_time=now,
        )
        row = next(item for item in rows if item["checkpoint_id"] == "T_MINUS_7D")
        self.assertEqual(row["state"], CHECKPOINT_MISSED)
        self.assertFalse(row["backfill_permitted_after_the_deadline"])

    def test_a_capture_claiming_a_time_after_execution_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_checkpoints(
                contract=self.contract,
                capture_times={"T_MINUS_7D": datetime(2026, 8, 29, 12, tzinfo=timezone.utc)},
                execution_time=datetime(2026, 8, 29, 4, tzinfo=timezone.utc),
            )

    def test_a_future_execution_time_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_checkpoints(
                contract=self.contract,
                capture_times={},
                execution_time=datetime.now(timezone.utc) + timedelta(days=1),
            )

    # -- mutation: forecast revision ----------------------------------------

    def test_a_revised_probability_changes_the_frozen_identity(self) -> None:
        rows = self.gate["frozen_target_forecasts"]
        self.assertTrue(rows)
        baseline = assert_forecasts_unrevised(
            rows=rows,
            bound_snapshot_identity=str(self.contract["target_contest"]["bound_snapshot_identity"]),
            kickoff_lower_bound=datetime(2026, 9, 5, 23, tzinfo=timezone.utc),
        )
        self.assertEqual(
            baseline["probability_identity"],
            self.gate["frozen_forecast_preservation"]["probability_identity"],
        )
        mutated = [dict(row) for row in rows]
        mutated[0]["probability_home_win"] = 0.5 + float(mutated[0]["probability_home_win"] or 0) / 2
        revised = assert_forecasts_unrevised(
            rows=mutated,
            bound_snapshot_identity=str(self.contract["target_contest"]["bound_snapshot_identity"]),
            kickoff_lower_bound=datetime(2026, 9, 5, 23, tzinfo=timezone.utc),
        )
        self.assertNotEqual(revised["probability_identity"], baseline["probability_identity"])

    def test_a_post_kickoff_forecast_row_is_rejected(self) -> None:
        rows = [dict(row) for row in self.gate["frozen_target_forecasts"]]
        rows[0]["created_at_utc"] = "2026-09-06T00:00:00Z"
        with self.assertRaises(ValueError):
            assert_forecasts_unrevised(
                rows=rows,
                bound_snapshot_identity=str(
                    self.contract["target_contest"]["bound_snapshot_identity"]
                ),
                kickoff_lower_bound=datetime(2026, 9, 5, 23, tzinfo=timezone.utc),
            )

    def test_a_foreign_snapshot_identity_is_rejected(self) -> None:
        rows = [dict(row) for row in self.gate["frozen_target_forecasts"]]
        rows[0]["snapshot_identity"] = "0" * 64
        with self.assertRaises(ValueError):
            assert_forecasts_unrevised(
                rows=rows,
                bound_snapshot_identity=str(
                    self.contract["target_contest"]["bound_snapshot_identity"]
                ),
                kickoff_lower_bound=datetime(2026, 9, 5, 23, tzinfo=timezone.utc),
            )

    # -- validator tamper coverage ------------------------------------------

    def _mirror(self, destination: Path, mutate) -> Path:
        root = destination / "repo"
        for relative in (
            CONTRACT_RELATIVE,
            GATE_RELATIVE,
            "artifacts/shadow/prospective_2026_shadow_cohort_gate.json",
            "artifacts/shadow/tamu_2026_week1_rehearsal_gate.json",
            "artifacts/shadow/prospective_2026_shadow_forecast_gate.json",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)
        gate_path = root / GATE_RELATIVE
        gate = read_json(gate_path)
        mutate(gate)
        gate_path.write_text(
            json.dumps(gate, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return root

    def test_validator_rejects_gate_mutations(self) -> None:


        mutations = {
            "relabelled_date": lambda gate: gate["corrected_calendar"][0].update(
                {"corrected_label": WEEK_ONE}
            ),
            "membership_changed": lambda gate: gate["corrected_calendar"][0].update(
                {"contest_membership_changed": True}
            ),
            "checkpoint_backfill": lambda gate: gate["checkpoint_ledger"][0].update(
                {"backfill_permitted_after_the_deadline": True}
            ),
            "probability_mutation": lambda gate: gate["frozen_target_forecasts"][0].update(
                {"probability_home_win": 0.123456}
            ),
            "nonclaim_asserted": lambda gate: gate["scientific_nonclaims"].update(
                {"bas_or_aggie_excess": True}
            ),
            "retrieval_time_as_kickoff": lambda gate: gate["official_kickoff_confirmation"].update(
                {"retrieval_time_used_as_kickoff_time": True}
            ),
            "identity_forged": lambda gate: gate.update({"gate_identity": "0" * 64}),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name), tempfile.TemporaryDirectory() as raw:
                root = self._mirror(Path(raw), mutate)
                outcome = validate_artifact(root)
                self.assertEqual(outcome["result"], "FAIL", name)

    def test_validator_accepts_the_unmutated_mirror(self) -> None:


        with tempfile.TemporaryDirectory() as raw:
            root = self._mirror(Path(raw), lambda gate: None)
            outcome = validate_artifact(root)
            self.assertEqual(outcome["result"], "PASS", outcome["findings"])

    def test_the_tracked_gate_is_not_rewritten_by_this_suite(self) -> None:
        before = (REPO_ROOT / GATE_RELATIVE).read_bytes()
        validate_artifact(REPO_ROOT)
        self.assertEqual((REPO_ROOT / GATE_RELATIVE).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
