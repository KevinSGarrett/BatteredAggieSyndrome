from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from tools.validate_w25_final import validate

ROOT = Path(__file__).resolve().parents[1]


def rows(rel: str):
    with (ROOT / rel).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class W25FinalHandoffTests(unittest.TestCase):
    def test_w25_validator(self):
        self.assertEqual([], validate(ROOT))

    def test_w24_parent_tree_is_fully_preserved(self):
        preservation = rows("governance/W25_W24_PARENT_PRESERVATION.csv")
        self.assertEqual(844, len(preservation))
        self.assertNotIn("MISSING", {r["status"] for r in preservation})

    def test_wave_program_is_terminal_and_handoff_not_wave26(self):
        state = (ROOT / "governance/CURRENT_STATE.yaml").read_text(encoding="utf-8")
        self.assertIn("current_wave: W25", state)
        self.assertIn("next_wave: CODEX_IMPLEMENTATION_HANDOFF", state)
        self.assertIn("wave_program_complete: true", state)
        self.assertIn("w26_allowed: false", state)

    def test_target_hardware_blocker_is_preserved(self):
        tasks = {r["task_id"]: r for r in rows("governance/IMPLEMENTATION_WBS.csv")}
        self.assertEqual("BLOCKED_TARGET_HARDWARE", tasks["TASK-161"]["status"])
        self.assertEqual("BLOCKED_AC038_TARGET_HARDWARE", tasks["TASK-163"]["status"])
        gaps = {r["gap_id"]: r for r in rows("docs/final/FINAL_KNOWN_GAPS.csv")}
        self.assertIn("AC-038", gaps["GAP-001"]["final_state"])

    def test_advanced_and_live_research_are_not_falsely_completed(self):
        tasks = {r["task_id"]: r for r in rows("governance/IMPLEMENTATION_WBS.csv")}
        for tid in [f"TASK-{i:03d}" for i in range(165, 173)]:
            self.assertEqual("PLANNED", tasks[tid]["status"])

    def test_final_maturity_is_explicit(self):
        values = {r["component"]: r["final_maturity"] for r in rows("docs/final/FINAL_COMPONENT_MATURITY.csv")}
        self.assertIn("AWAITING_TARGET_HARDWARE_VALIDATION", set(values.values()))
        self.assertIn("AWAITING_DATA_AND_EXECUTION", set(values.values()))
        self.assertIn("DEFERRED_CONDITIONAL", set(values.values()))

    def test_final_backlog_starts_with_real_evidence_work(self):
        backlog = rows("docs/final/FINAL_BACKLOG.csv")
        by_id = {r["handoff_id"]: r for r in backlog}
        self.assertEqual("RUN_TARGET_BENCHMARK", by_id["HANDOFF-001"]["workstream"])
        self.assertEqual("SOURCE_ACCESS", by_id["HANDOFF-002"]["workstream"])
        self.assertIn("histor", by_id["HANDOFF-003"]["action"].lower())

    def test_no_empirical_model_claims_are_inserted(self):
        state = (ROOT / "governance/CURRENT_STATE.yaml").read_text(encoding="utf-8")
        for flag in (
            "empirical_historical_replay_completed: false",
            "trained_production_champion_selected: false",
            "production_feature_set_selected: false",
            "tamu_specialization_lift_claimed: false",
            "aggie_excess_claimed: false",
            "bas_empirical_effect_claimed: false",
        ):
            self.assertIn(flag, state)

    def test_final_adr_and_requirement_traceability(self):
        adr_map = {r["adr_id"]: r for r in rows("governance/ADR_ACCEPTANCE_TRACEABILITY.csv")}
        for aid in ("ADR-347", "ADR-348", "ADR-349"):
            self.assertEqual("MAPPED", adr_map[aid]["status"])
        req = {r["requirement_id"]: r for r in rows("governance/REQUIREMENT_ACCEPTANCE_MATRIX.csv")}
        self.assertEqual("VERIFIED_W25_FINAL", req["REQ-130"]["acceptance_state"])


if __name__ == "__main__":
    unittest.main()
