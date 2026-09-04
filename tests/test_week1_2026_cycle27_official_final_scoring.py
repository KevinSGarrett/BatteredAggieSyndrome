"""Cycle 27 pinned Week 1 official-final scoring regressions.

Fixtures live in isolated temp roots. Production Cycle 26 gate/dataset paths and
the live scoreboard directory are never written.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

from aggie_analytics.data.week1_2026_cycle27_official_final_scoring import (  # noqa: E402
    NO_DIRECTION,
    PREDECESSOR_JOINED_FORECAST_ROWS,
    PREDECESSOR_SCORED_ROW_COUNT,
    PREDECESSOR_SCORING_DATASET_IDENTITY,
    PREDECESSOR_SCORING_GATE_IDENTITY,
    STATE_ABSTAINED,
    STATE_AUTHORIZED_EXCLUSION,
    STATE_AWAITING,
    STATE_CONFLICT,
    STATE_MISSED_CUTOFF,
    STATE_SCORED,
    Week1Cycle27OfficialFinalScoringError,
    build_pinned_input_manifest,
    capture_record_from_file,
    favorite_direction,
    frozen_probability_identity,
    jsonl_bytes,
    parser_module_sha256,
    schema_identity,
    score_from_pinned_manifest,
)
from validate_week1_2026_cycle27_official_final_scoring import validate  # noqa: E402


FREEZE_UTC = "2026-09-03T06:47:23Z"
KICKOFF_UTC = "2026-09-03T22:00:00Z"
AS_OF_UTC = "2026-09-04T16:45:00Z"
ISSUED_AT = "2026-09-04T16:45:00Z"


def render_scoreboard(
    *,
    contest_id: str,
    home_points: int,
    away_points: int,
    terminal: bool = True,
    form_date: str = "09/03/2026",
) -> str:
    status = ""
    if terminal:
        status = (
            f'<!-- <div class="livestream_status_{contest_id} livestream_status '
            f'livestream_game_over ">Final</div> -->'
        )
    return f"""<html><body>
<form><input type="hidden" name="game_date" value="{form_date}" /></form>
{status}
<table><tr><td>{form_date} 06:00 PM ESPN</td></tr>
<tr id="contest_{contest_id}">
  <td><a href="/teams/1">Away (0-1)</a></td>
  <td><div id="score_1" class="score">{away_points}</div></td>
</tr>
<tr id="contest_{contest_id}">
  <td><a href="/teams/2">Home (1-0)</a></td>
  <td><div id="score_2" class="score">{home_points}</div></td>
</tr>
</table></body></html>"""


def forecast_row(
    *,
    contest_id: str,
    candidate_id: str = "national_margin_ridge",
    probability_home: float | None = 0.8,
    expected_margin_home: float | None = 10.0,
    checkpoint_id: str = "EARLY_WEEK1",
    kickoff_utc: str = KICKOFF_UTC,
    identity: str | None = None,
    frozen_identity: str | None = None,
) -> dict:
    row = {
        "ncaa_contest_id": contest_id,
        "candidate_id": candidate_id,
        "checkpoint_id": checkpoint_id,
        "probability_home": probability_home,
        "expected_margin_home": expected_margin_home,
        "kickoff_bound_utc": kickoff_utc,
        "control_only": candidate_id == "national_base_rate",
        "forecast_row_identity": identity
        or f"{contest_id}:{candidate_id}:{checkpoint_id}",
    }
    if frozen_identity is not None:
        row["frozen_probability_identity"] = frozen_identity
    else:
        row["frozen_probability_identity"] = frozen_probability_identity(row)
    return row


class Cycle27OfficialFinalScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmp.name)
        self.forecast_rel = "canonical/test_forecast/week1_forecast_rows.jsonl"
        self.scoreboard_rel = "raw/test_scoreboard"
        (self.data_root / self.forecast_rel).parent.mkdir(parents=True, exist_ok=True)
        (self.data_root / self.scoreboard_rel).mkdir(parents=True, exist_ok=True)
        self.parser_sha = parser_module_sha256(REPO_ROOT)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_forecast(self, rows: list[dict]) -> None:
        path = self.data_root / self.forecast_rel
        path.write_bytes(jsonl_bytes(rows))

    def _write_html(self, name: str, document: str) -> Path:
        path = self.data_root / self.scoreboard_rel / name
        path.write_text(document, encoding="utf-8")
        return path

    def _pin(
        self,
        *,
        html_names: list[str],
        retrieved_at: dict[str, str] | None = None,
        authorized: list[str] | None = None,
        bind_acquisition_receipt: bool = True,
    ) -> dict:
        forecast_path = self.data_root / self.forecast_rel
        payload = forecast_path.read_bytes()
        captures = []
        times = retrieved_at or {}
        for name in html_names:
            relative = f"{self.scoreboard_rel}/{name}"
            html_path = self.data_root / relative
            html_digest = hashlib.sha256(html_path.read_bytes()).hexdigest()
            receipt_rel = None
            receipt_digest = None
            if bind_acquisition_receipt and times.get(name):
                receipt_rel = f"{self.scoreboard_rel}/{name}.acquisition_receipt.json"
                receipt_path = self.data_root / receipt_rel
                receipt_body = json.dumps(
                    {
                        "html_sha256": html_digest,
                        "relative_path": relative,
                        "retrieved_at_utc": times[name],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                receipt_path.write_bytes(receipt_body)
                receipt_digest = hashlib.sha256(receipt_body).hexdigest()
            captures.append(
                capture_record_from_file(
                    data_root=self.data_root,
                    relative_path=relative,
                    retrieved_at_utc=None if receipt_rel else times.get(name),
                    receipt_id=name,
                    acquisition_receipt_relative_path=receipt_rel,
                    acquisition_receipt_sha256=receipt_digest,
                )
            )
        return build_pinned_input_manifest(
            captures=captures,
            forecast_payload={
                "relative_path": self.forecast_rel,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            },
            as_of_utc=AS_OF_UTC,
            parser_module_sha256_hex=self.parser_sha,
            freeze_utc=FREEZE_UTC,
            authorized_exclusion_contest_ids=authorized or [],
        )

    def _score(self, manifest: dict) -> dict:
        return score_from_pinned_manifest(
            repo_root=REPO_ROOT,
            data_root=self.data_root,
            manifest=manifest,
            issued_at_utc=ISSUED_AT,
        )

    def test_receipt_before_kickoff_is_rejected(self) -> None:
        self._write_forecast([forecast_row(contest_id="1001")])
        self._write_html(
            "early.html",
            render_scoreboard(contest_id="1001", home_points=21, away_points=14),
        )
        manifest = self._pin(
            html_names=["early.html"],
            retrieved_at={"early.html": "2026-09-03T21:00:00Z"},
        )
        gate = self._score(manifest)
        rows = gate["_scored_rows"]
        self.assertEqual(rows[0]["state"], STATE_AWAITING)
        self.assertEqual(gate["summary"]["rejected_receipt_before_kickoff_count"], 1)
        self.assertFalse(rows[0]["scored"])

    def test_missing_retrieved_at_is_not_scored(self) -> None:
        self._write_forecast([forecast_row(contest_id="1002")])
        self._write_html(
            "notime.html",
            render_scoreboard(contest_id="1002", home_points=21, away_points=14),
        )
        manifest = self._pin(html_names=["notime.html"])
        gate = self._score(manifest)
        self.assertFalse(gate["_scored_rows"][0]["scored"])
        self.assertEqual(gate["_scored_rows"][0]["state"], STATE_AWAITING)
        self.assertGreaterEqual(
            int(gate["summary"]["rejected_receipt_before_kickoff_count"]), 1
        )

    def test_caller_supplied_time_without_receipt_is_not_authority(self) -> None:
        self._write_forecast([forecast_row(contest_id="1003")])
        self._write_html(
            "supplied.html",
            render_scoreboard(contest_id="1003", home_points=21, away_points=14),
        )
        manifest = self._pin(
            html_names=["supplied.html"],
            retrieved_at={"supplied.html": "2026-09-03T23:00:00Z"},
            bind_acquisition_receipt=False,
        )
        gate = self._score(manifest)
        self.assertFalse(gate["_scored_rows"][0]["scored"])
        self.assertEqual(gate["_scored_rows"][0]["state"], STATE_AWAITING)
        self.assertIn(
            "CALLER_SUPPLIED_TIME_NOT_ACQUISITION_AUTHORITY",
            gate["summary"]["rejected_receipt_reasons"],
        )

    def test_duplicate_conflicted_final_is_quarantined(self) -> None:
        self._write_forecast([forecast_row(contest_id="2002")])
        self._write_html(
            "first.html",
            render_scoreboard(contest_id="2002", home_points=21, away_points=14),
        )
        self._write_html(
            "second.html",
            render_scoreboard(contest_id="2002", home_points=24, away_points=14),
        )
        manifest = self._pin(
            html_names=["first.html", "second.html"],
            retrieved_at={
                "first.html": "2026-09-03T23:00:00Z",
                "second.html": "2026-09-03T23:05:00Z",
            },
        )
        gate = self._score(manifest)
        self.assertEqual(gate["_scored_rows"][0]["state"], STATE_CONFLICT)
        self.assertIn("2002", gate["summary"]["quarantined_conflict_contest_ids"])
        self.assertFalse(gate["_scored_rows"][0]["scored"])

    def test_mutated_frozen_probability_is_not_binding(self) -> None:
        row = forecast_row(contest_id="3003", probability_home=0.8)
        self._write_forecast([row])
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="3003", home_points=21, away_points=14),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        mutated = dict(row)
        mutated["probability_home"] = 0.2
        self._write_forecast([mutated])
        with self.assertRaises(Week1Cycle27OfficialFinalScoringError) as raised:
            self._score(manifest)
        self.assertIn("MUTATED_FROZEN_FORECAST_PAYLOAD", str(raised.exception))

        self._write_forecast([row])
        bound = frozen_probability_identity(row)
        mutated_bound = dict(row)
        mutated_bound["probability_home"] = 0.2
        mutated_bound["frozen_probability_identity"] = bound
        self._write_forecast([mutated_bound])
        mutated_path = self.data_root / self.forecast_rel
        mutated_bytes = mutated_path.read_bytes()
        mutated_manifest = build_pinned_input_manifest(
            captures=manifest["captures"],
            forecast_payload={
                "relative_path": self.forecast_rel,
                "sha256": hashlib.sha256(mutated_bytes).hexdigest(),
                "bytes": len(mutated_bytes),
            },
            as_of_utc=AS_OF_UTC,
            parser_module_sha256_hex=self.parser_sha,
            freeze_utc=FREEZE_UTC,
        )
        with self.assertRaises(Week1Cycle27OfficialFinalScoringError) as raised_row:
            self._score(mutated_manifest)
        self.assertIn(
            "MUTATED_FROZEN_PROBABILITY_NOT_BINDING", str(raised_row.exception)
        )

    def test_extra_and_missing_scored_rows_are_rejected(self) -> None:
        self._write_forecast([forecast_row(contest_id="4004")])
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="4004", home_points=21, away_points=14),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        gate = self._score(manifest)
        extra = dict(gate["_scored_rows"][0])
        extra["ncaa_contest_id"] = "9999"
        extra["forecast_row_identity"] = "extra"
        extra_findings = validate(
            repo_root=REPO_ROOT,
            data_root=self.data_root,
            gate=gate,
            manifest=manifest,
            scored_rows=[*gate["_scored_rows"], extra],
        )
        self.assertTrue(
            any(item.startswith("EXTRA_SCORED_ROWS:") for item in extra_findings)
        )
        missing_findings = validate(
            repo_root=REPO_ROOT,
            data_root=self.data_root,
            gate=gate,
            manifest=manifest,
            scored_rows=[],
        )
        self.assertTrue(
            any(item.startswith("MISSING_SCORED_ROWS:") for item in missing_findings)
        )

    def test_repeated_checkpoints_are_not_independent_games(self) -> None:
        rows = [
            forecast_row(contest_id="5005", checkpoint_id="EARLY_WEEK1"),
            forecast_row(
                contest_id="5005", checkpoint_id="T-90M", probability_home=0.7
            ),
        ]
        self._write_forecast(rows)
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="5005", home_points=28, away_points=10),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        gate = self._score(manifest)
        scored = [row for row in gate["_scored_rows"] if row["scored"]]
        self.assertEqual(len(scored), 2)
        self.assertEqual(gate["summary"]["unique_scored_games"], 1)
        ridge = gate["empirical_assessment"]["candidates"][0]
        self.assertEqual(ridge["unique_games"], 1)

    def test_replay_with_appended_capture_does_not_change_frozen_packet(self) -> None:
        self._write_forecast([forecast_row(contest_id="6006")])
        self._write_html(
            "first.html",
            render_scoreboard(contest_id="6006", home_points=17, away_points=10),
        )
        manifest = self._pin(
            html_names=["first.html"],
            retrieved_at={"first.html": "2026-09-03T23:00:00Z"},
        )
        first = self._score(manifest)
        frozen_bytes = first["_payload_bytes"]
        self._write_html(
            "appended.html",
            render_scoreboard(contest_id="7007", home_points=42, away_points=0),
        )
        replay = self._score(manifest)
        self.assertEqual(frozen_bytes, replay["_payload_bytes"])
        self.assertEqual(first["dataset_identity"], replay["dataset_identity"])
        self.assertEqual(len(replay["_scored_rows"]), 1)

    def test_replay_ignores_unpinned_mtime_and_extra_files(self) -> None:
        self._write_forecast([forecast_row(contest_id="6008")])
        self._write_html(
            "first.html",
            render_scoreboard(contest_id="6008", home_points=21, away_points=7),
        )
        manifest = self._pin(
            html_names=["first.html"],
            retrieved_at={"first.html": "2026-09-03T23:00:00Z"},
        )
        first = self._score(manifest)
        frozen_bytes = first["_payload_bytes"]
        extra = self.data_root / self.scoreboard_rel / "unrelated_later.html"
        extra.write_text("not in the pin", encoding="utf-8")
        extra.touch()
        replay = self._score(manifest)
        self.assertEqual(frozen_bytes, replay["_payload_bytes"])
        self.assertEqual(first["dataset_identity"], replay["dataset_identity"])

    def test_all_expected_states_are_reconstructed(self) -> None:
        rows = [
            forecast_row(contest_id="1101", probability_home=0.8),
            forecast_row(
                contest_id="1102",
                candidate_id="national_elo",
                expected_margin_home=None,
            ),
            forecast_row(
                contest_id="1101",
                candidate_id="national_elo",
                probability_home=None,
                expected_margin_home=None,
            ),
            forecast_row(contest_id="1103"),
            forecast_row(
                contest_id="1104",
                kickoff_utc="2026-09-03T05:00:00Z",
            ),
            forecast_row(contest_id="1105"),
            forecast_row(contest_id="1106"),
        ]
        self._write_forecast(rows)
        self._write_html(
            "s1.html",
            render_scoreboard(contest_id="1101", home_points=21, away_points=14),
        )
        self._write_html(
            "c1.html",
            render_scoreboard(contest_id="1103", home_points=10, away_points=7),
        )
        self._write_html(
            "c2.html",
            render_scoreboard(contest_id="1103", home_points=13, away_points=7),
        )
        self._write_html(
            "tie.html",
            render_scoreboard(contest_id="1105", home_points=14, away_points=14),
        )
        self._write_html(
            "ex.html",
            render_scoreboard(contest_id="1106", home_points=35, away_points=7),
        )
        later = "2026-09-03T23:00:00Z"
        manifest = self._pin(
            html_names=["s1.html", "c1.html", "c2.html", "tie.html", "ex.html"],
            retrieved_at={
                "s1.html": later,
                "c1.html": later,
                "c2.html": later,
                "tie.html": later,
                "ex.html": later,
            },
            authorized=["1106"],
        )
        gate = self._score(manifest)
        ridge_s1 = next(
            row
            for row in gate["_scored_rows"]
            if row["ncaa_contest_id"] == "1101"
            and row["candidate_id"] == "national_margin_ridge"
        )
        elo_s1 = next(
            row
            for row in gate["_scored_rows"]
            if row["ncaa_contest_id"] == "1101"
            and row["candidate_id"] == "national_elo"
        )
        by_contest = {
            row["ncaa_contest_id"]: row
            for row in gate["_scored_rows"]
            if row["ncaa_contest_id"] != "1101"
        }
        self.assertEqual(ridge_s1["state"], STATE_SCORED)
        self.assertEqual(by_contest["1102"]["state"], STATE_AWAITING)
        self.assertEqual(elo_s1["state"], STATE_ABSTAINED)
        self.assertEqual(by_contest["1103"]["state"], STATE_CONFLICT)
        self.assertEqual(by_contest["1104"]["state"], STATE_MISSED_CUTOFF)
        self.assertEqual(by_contest["1105"]["state"], STATE_AUTHORIZED_EXCLUSION)
        self.assertEqual(by_contest["1106"]["state"], STATE_AUTHORIZED_EXCLUSION)
        findings = validate(
            repo_root=REPO_ROOT,
            data_root=self.data_root,
            gate=gate,
            manifest=manifest,
            scored_rows=gate["_scored_rows"],
        )
        self.assertEqual(findings, [])

    def test_p_one_half_is_no_direction_and_null_accuracy_when_den_zero(self) -> None:
        self.assertEqual(favorite_direction(0.5), NO_DIRECTION)
        self._write_forecast(
            [
                forecast_row(
                    contest_id="8008",
                    candidate_id="national_base_rate",
                    probability_home=0.5,
                    expected_margin_home=None,
                )
            ]
        )
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="8008", home_points=21, away_points=14),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        gate = self._score(manifest)
        row = gate["_scored_rows"][0]
        self.assertTrue(row["scored"])
        self.assertEqual(row["favorite_direction"], NO_DIRECTION)
        self.assertAlmostEqual(row["brier"], 0.25)
        candidate = gate["empirical_assessment"]["candidates"][0]
        self.assertEqual(candidate["directional_denominator"], 0)
        self.assertIsNone(candidate["directional_accuracy"])
        findings = validate(
            repo_root=REPO_ROOT,
            data_root=self.data_root,
            gate=gate,
            manifest=manifest,
            scored_rows=gate["_scored_rows"],
        )
        self.assertEqual(findings, [])

    def test_prediction_error_and_residual_signs(self) -> None:
        self._write_forecast(
            [forecast_row(contest_id="9009", expected_margin_home=10.0)]
        )
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="9009", home_points=38, away_points=16),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        row = self._score(manifest)["_scored_rows"][0]
        self.assertEqual(row["actual_margin_home"], 22.0)
        self.assertEqual(row["prediction_error_margin"], -12.0)
        self.assertEqual(row["residual_margin"], 12.0)
        self.assertEqual(row["prediction_error_definition"], "predicted_minus_actual")
        self.assertEqual(row["residual_definition"], "actual_minus_predicted")

    def test_predecessor_lineage_is_preserved(self) -> None:
        self._write_forecast([forecast_row(contest_id="1010")])
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="1010", home_points=21, away_points=7),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        gate = self._score(manifest)
        bound = gate["bound_predecessors"]
        self.assertEqual(
            bound["predecessor_scoring_gate_identity"],
            PREDECESSOR_SCORING_GATE_IDENTITY,
        )
        self.assertEqual(
            bound["predecessor_scoring_dataset_identity"],
            PREDECESSOR_SCORING_DATASET_IDENTITY,
        )
        self.assertEqual(
            bound["predecessor_joined_forecast_rows"], PREDECESSOR_JOINED_FORECAST_ROWS
        )
        self.assertEqual(
            bound["predecessor_scored_row_count"], PREDECESSOR_SCORED_ROW_COUNT
        )
        self.assertFalse(bound["predecessor_scoring_payload_rewritten"])
        self.assertEqual(gate["schema_identity"], schema_identity())
        self.assertEqual(gate["publication_label"], "UNTRUSTED_SHADOW")
        self.assertEqual(gate["operator_hold"], "ACTIVE")
        self.assertFalse(gate["merge_authorized"])
        self.assertEqual(gate["capture_mode"], "PINNED_MANIFEST")

    def test_does_not_write_production_payloads(self) -> None:
        predecessor_gate = (
            REPO_ROOT
            / "artifacts/scientific_integrity/cycle26/CYCLE26_WEEK1_OFFICIAL_FINAL_SCORING.json"
        )
        before = predecessor_gate.read_bytes()
        self._write_forecast([forecast_row(contest_id="1111")])
        self._write_html(
            "ok.html",
            render_scoreboard(contest_id="1111", home_points=21, away_points=7),
        )
        manifest = self._pin(
            html_names=["ok.html"],
            retrieved_at={"ok.html": "2026-09-03T23:00:00Z"},
        )
        self._score(manifest)
        self.assertEqual(predecessor_gate.read_bytes(), before)
        self.assertFalse((self.data_root / "raw/SRC-NCAA-OFFICIAL-STATS").exists())


if __name__ == "__main__":
    unittest.main()
