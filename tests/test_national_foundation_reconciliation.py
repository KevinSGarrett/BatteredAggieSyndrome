from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    CONTRACT_ID,
    ELIGIBILITY_STATES,
    GATE_RELATIVE,
    PASS_RESULT,
    binding_identity,
    build_capture_inventory,
    build_domain_coverage,
    build_gate,
    compute_gate_identity,
    load_contract,
    manifest_authoritative_sha256,
    normalize_game_row,
    rebuild_expected,
    validate_artifact,
)

PROTECTED = frozenset({2024, 2025})


def _source_row(**overrides: object) -> dict[str, object]:
    row = {
        "id": 400000001,
        "season": 2019,
        "seasonType": "regular",
        "week": 3,
        "neutralSite": False,
        "conferenceGame": True,
        "venueId": 3974,
        "venue": "Kyle Field",
        "homeId": 245,
        "homeTeam": "Texas A&M",
        "homeConference": "SEC",
        "homeClassification": "fbs",
        "awayId": 2,
        "awayTeam": "Auburn",
        "awayConference": "SEC",
        "awayClassification": "fbs",
        "startDate": "2019-09-21T23:00:00.000Z",
        "startTimeTBD": False,
        "completed": True,
        "homePoints": 28,
        "awayPoints": 20,
        "attendance": 102000,
        "notes": "",
    }
    row.update(overrides)
    return row


def _normalize(**overrides: object):
    return normalize_game_row(
        _source_row(**overrides), source_id="SRC-002", protected_seasons=PROTECTED
    )


def _capture_entry(**overrides: object) -> dict[str, object]:
    entry = {
        "snapshot_id": "cap_test0001",
        "source_contract": {"source_id": "SRC-002"},
        "content_identity": {
            "external_relative_path": "raw/SRC-002/games/sha256_test.json",
            "sha256": "0" * 64,
            "bytes": 3,
        },
        "coverage": {
            "grain": "GAME",
            "season": 2019,
            "row_count": 1,
            "domain_uses": ["schedules_games_official_outcomes"],
        },
        "quality_and_eligibility": {"pit_eligibility": "CAPTURE_KNOWN_AT_RECORDED"},
    }
    entry.update(overrides)  # type: ignore[arg-type]
    return entry


class NationalFoundationUnitTests(unittest.TestCase):
    def test_contract_loads_and_pins_closed_authority(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertEqual(tuple(contract["eligibility_states"]), ELIGIBILITY_STATES)
        for key in (
            "historical_pit_admission",
            "pregame_feature_use",
            "protected_training_admission",
            "protected_evaluation_admission",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            self.assertIs(contract["authority"][key], False)

    def test_normalizes_a_well_formed_game(self) -> None:
        accepted, rejected = _normalize()
        self.assertIsNone(rejected)
        assert accepted is not None
        self.assertEqual(accepted["canonical_game_id"], "SRC-002:GAME:400000001")
        self.assertEqual(accepted["home_team_name"], "Texas A&M")
        self.assertIs(accepted["_protected"], False)

    def test_protected_seasons_are_flagged_not_silently_admitted(self) -> None:
        accepted, rejected = _normalize(season=2025)
        self.assertIsNone(rejected)
        assert accepted is not None
        self.assertIs(accepted["_protected"], True)

    def test_completed_game_without_scores_is_quarantined(self) -> None:
        accepted, rejected = _normalize(homePoints=None)
        self.assertIsNone(accepted)
        assert rejected is not None
        self.assertEqual(rejected["reason_code"], "COMPLETED_WITHOUT_SCORES")

    def test_incomplete_game_carrying_a_score_is_quarantined(self) -> None:
        accepted, rejected = _normalize(completed=False)
        self.assertIsNone(accepted)
        assert rejected is not None
        self.assertEqual(rejected["reason_code"], "SCORES_WITHOUT_COMPLETION")

    def test_non_final_marker_is_quarantined(self) -> None:
        accepted, rejected = _normalize(notes="Game postponed by weather")
        self.assertIsNone(accepted)
        assert rejected is not None
        self.assertEqual(rejected["reason_code"], "NON_FINAL_GAME")

    def test_self_matchup_is_quarantined(self) -> None:
        accepted, rejected = _normalize(awayTeam="Texas A&M")
        self.assertIsNone(accepted)
        assert rejected is not None
        self.assertEqual(rejected["reason_code"], "SELF_MATCHUP")

    def test_missing_identity_is_quarantined(self) -> None:
        for overrides, reason in (
            ({"id": None}, "MISSING_SOURCE_GAME_ID"),
            ({"season": None}, "MISSING_SEASON"),
            ({"homeTeam": None}, "MISSING_TEAM_IDENTITY"),
        ):
            with self.subTest(reason=reason):
                accepted, rejected = _normalize(**overrides)
                self.assertIsNone(accepted)
                assert rejected is not None
                self.assertEqual(rejected["reason_code"], reason)

    def test_missing_capture_is_recorded_as_source_absent(self) -> None:
        inventory = build_capture_inventory(
            data_root=ROOT / "does" / "not" / "exist",
            master_manifest={"snapshot_index": [_capture_entry()]},
        )
        self.assertEqual(inventory["records"][0]["capture_state"], "SOURCE_ABSENT")
        self.assertEqual(inventory["summary"]["absent_captures"], 1)
        self.assertEqual(inventory["summary"]["verified_captures"], 0)

    def test_altered_capture_hash_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload = root / "raw" / "SRC-002" / "games" / "sha256_test.json"
            payload.parent.mkdir(parents=True, exist_ok=True)
            payload.write_bytes(b"[1]")
            inventory = build_capture_inventory(
                data_root=root, master_manifest={"snapshot_index": [_capture_entry()]}
            )
        self.assertEqual(inventory["records"][0]["capture_state"], "QUARANTINED")
        self.assertEqual(inventory["summary"]["quarantined_captures"], 1)

    def test_duplicate_declared_payload_hashes_are_counted(self) -> None:
        first = _capture_entry()
        second = _capture_entry(snapshot_id="cap_test0002")
        inventory = build_capture_inventory(
            data_root=ROOT / "missing", master_manifest={"snapshot_index": [first, second]}
        )
        self.assertEqual(inventory["summary"]["duplicate_payload_sha256"], 1)

    def test_domain_coverage_ignores_unverified_captures(self) -> None:
        record = {
            "capture_state": "SOURCE_ABSENT",
            "domain_uses": ["plays"],
            "row_count": 10,
            "season": 2019,
        }
        self.assertEqual(build_domain_coverage([record]), {})


class NationalFoundationMountedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not (cls.data_root / "raw" / "SRC-002" / "games").is_dir() or not cls.gate_path.is_file():
            raise unittest.SkipTest("national capture foundation or gate is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        cls.manifest = json.loads(
            (cls.data_root / cls.gate["manifest"]["relative_path"]).read_text(encoding="utf-8")
        )

    def test_gate_validates_against_an_independent_rebuild(self) -> None:
        report = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            gate=self.gate,
            manifest=self.manifest,
            expected=self.expected,
        )
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["mode"], "INDEPENDENT_REBUILD")

    def test_every_declared_capture_rehashed_clean(self) -> None:
        summary = self.gate["capture_inventory"]
        self.assertEqual(summary["declared_captures"], summary["verified_captures"])
        self.assertEqual(summary["absent_captures"], 0)
        self.assertEqual(summary["quarantined_captures"], 0)
        self.assertEqual(summary["verified_payload_bytes"], summary["declared_payload_bytes"])

    def test_pit_and_protected_admission_remain_zero(self) -> None:
        census = self.gate["eligibility_census"]
        self.assertEqual(census["PIT_FEATURE_ELIGIBLE"], 0)
        self.assertEqual(census["PROTECTED_ELIGIBLE"], 0)
        self.assertEqual(sorted(census), sorted(ELIGIBILITY_STATES))

    def test_normalized_rows_reconcile_with_source_and_quarantine(self) -> None:
        inventory = self.gate["normalized_inventory"]
        self.assertEqual(
            inventory["source_rows"], inventory["rows"] + inventory["quarantined_rows"]
        )
        by_season = inventory["rows_by_season"]
        self.assertEqual(sum(by_season.values()), inventory["rows"])

    def test_protected_seasons_are_normalized_but_never_label_eligible(self) -> None:
        inventory = self.gate["normalized_inventory"]
        protected_rows = sum(int(inventory["rows_by_season"].get(str(year), 0)) for year in (2024, 2025))
        self.assertGreater(protected_rows, 0)
        self.assertEqual(inventory["protected_rows_excluded_from_labels"], protected_rows)
        self.assertEqual(self.gate["eligibility_census"]["PROTECTED_ELIGIBLE"], 0)
        self.assertLessEqual(
            self.gate["eligibility_census"]["OUTCOME_REFERENCE_ELIGIBLE"],
            inventory["rows"] - protected_rows,
        )

    def test_gate_identity_is_invariant_to_issue_time(self) -> None:
        manifest_entry = self.gate["manifest"]
        payloads = self.gate["payloads"]
        first = build_gate(expected=self.expected, manifest_entry=manifest_entry, payloads=payloads)
        second = build_gate(expected=self.expected, manifest_entry=manifest_entry, payloads=payloads)
        self.assertEqual(first["gate_identity"], second["gate_identity"])
        self.assertEqual(first["gate_identity"], self.gate["gate_identity"])
        self.assertNotIn("issued_at_utc", first)

    def test_manifest_authoritative_hash_excludes_volatile_metadata(self) -> None:
        volatile = json.loads(json.dumps(self.manifest))
        volatile["issued_at_utc"] = "1999-01-01T00:00:00Z"
        volatile["producer"] = {"python": "0.0.0"}
        self.assertEqual(
            manifest_authoritative_sha256(volatile),
            manifest_authoritative_sha256(self.manifest),
        )
        self.assertEqual(
            manifest_authoritative_sha256(self.manifest),
            self.gate["manifest"]["authoritative_sha256"],
        )

    def test_gap_002_remains_open(self) -> None:
        gap = self.gate["gap_002"]
        self.assertEqual(gap["state"], "OPEN")
        self.assertIs(gap["file_existence_alone_closes_gap"], False)
        self.assertIs(self.gate["scientific_nonclaims"]["gap_002_resolved"], False)


class NationalFoundationMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not (cls.data_root / "raw" / "SRC-002" / "games").is_dir() or not cls.gate_path.is_file():
            raise unittest.SkipTest("national capture foundation or gate is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        cls.manifest = json.loads(
            (cls.data_root / cls.gate["manifest"]["relative_path"]).read_text(encoding="utf-8")
        )

    def _forged(self, **changes: object) -> dict[str, object]:
        """Tamper, then re-seal both identities so only semantic rebuild can catch it."""
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        tampered["binding_identity"] = binding_identity(tampered, "binding_identity")
        return tampered

    def _reject(self, gate: dict[str, object], manifest: dict[str, object] | None = None) -> None:
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=gate,
                manifest=self.manifest if manifest is None else manifest,
                expected=self.expected,
            )

    def test_rejects_inflated_normalized_row_count(self) -> None:
        inventory = json.loads(json.dumps(self.gate["normalized_inventory"]))
        inventory["rows"] = int(inventory["rows"]) + 1
        self._reject(self._forged(normalized_inventory=inventory))

    def test_rejects_false_readiness_claim(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["gap_002_resolved"] = True
        self._reject(self._forged(scientific_nonclaims=nonclaims))

    def test_rejects_forced_gap_002_closure(self) -> None:
        gap = dict(self.gate["gap_002"])
        gap["state"] = "CLOSED"
        self._reject(self._forged(gap_002=gap))

    def test_rejects_smuggled_pit_admission(self) -> None:
        census = dict(self.gate["eligibility_census"])
        census["PIT_FEATURE_ELIGIBLE"] = 100
        self._reject(self._forged(eligibility_census=census))

    def test_rejects_opened_protected_lane(self) -> None:
        self._reject(self._forged(protected_lane="OPEN_PROTECTED_LANE"))

    def test_rejects_altered_capture_inventory(self) -> None:
        summary = json.loads(json.dumps(self.gate["capture_inventory"]))
        summary["absent_captures"] = 0
        summary["verified_captures"] = int(summary["verified_captures"]) - 1
        self._reject(self._forged(capture_inventory=summary))

    def test_rejects_substituted_payload_hash(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        manifest["payloads"][0]["sha256"] = "0" * 64
        self._reject(self.gate, manifest)

    def test_rejects_schema_drifted_domain_coverage(self) -> None:
        coverage = json.loads(json.dumps(self.gate["domain_coverage"]))
        coverage["fabricated_domain"] = {
            "verified_captures": 1,
            "declared_source_rows": 1,
            "season_count": 1,
            "season_range": [2019, 2019],
        }
        self._reject(self._forged(domain_coverage=coverage))

    def test_rejects_unsealed_identity(self) -> None:
        tampered = json.loads(json.dumps(self.gate))
        tampered["normalized_inventory"]["rows"] = 1
        self._reject(tampered)

    def test_rejects_non_passing_result(self) -> None:
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self._reject(self._forged(result="PASS_EVERYTHING_IS_READY"))


if __name__ == "__main__":
    unittest.main()
