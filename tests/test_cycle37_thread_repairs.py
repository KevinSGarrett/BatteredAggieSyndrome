"""Cycle #37 - Attempt #2: reproductions for the unresolved review threads repaired this attempt (R37-I).

Each test fails on the pre-repair code and passes on the repair; the thread index is in the test name.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggie_analytics.cycle28.scoring import Cycle28ScoringError, score_game_grain  # noqa: E402
from aggie_analytics.cycle29.claims import ClaimError, discover_authority_claims, inventory_claims  # noqa: E402
from aggie_analytics.cycle29.pit_kernel import PitKernelError, build_game_grain_kernel  # noqa: E402
from aggie_analytics.cycle30.pit_kernel import build_game_grain_kernel as build_cycle30_kernel  # noqa: E402
from aggie_analytics.cycle30.populations import week1_slice_from_contests  # noqa: E402
from aggie_analytics.data.producer_market_math import one_observation_per_book  # noqa: E402
from aggie_analytics.data.week1_2026_current_contest_binding_successor import (  # noqa: E402
    build_current_contest_row,
    resolve_current_contest,
)
from aggie_analytics.data.week1_2026_market_integrity_successor import focus_game_quote_count  # noqa: E402
from aggie_analytics.scientific_reference.coherence import (  # noqa: E402
    inverse_normal_cdf,
    joint_distribution_coherent,
)
from aggie_analytics.scientific_reference.cycle28_scoring import (  # noqa: E402
    IndependentScoringError,
    reject_prekickoff_final,
)
from aggie_analytics.scientific_reference.cycle29.pit import (  # noqa: E402
    IndependentPitError,
    reconstruct_game_features,
)
from jira.tools import import_bat_live  # noqa: E402


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(f"_c37_{name}", ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _outcomes(game: dict, home_points: int, away_points: int) -> list[dict]:
    return [
        {"canonical_game_id": game["canonical_game_id"], "canonical_team_id": game["home_canonical_team_id"],
         "label_win": home_points > away_points, "points_for": home_points, "points_against": away_points,
         "margin": home_points - away_points, "season": game["season"]},
        {"canonical_game_id": game["canonical_game_id"], "canonical_team_id": game["away_canonical_team_id"],
         "label_win": away_points > home_points, "points_for": away_points, "points_against": home_points,
         "margin": away_points - home_points, "season": game["season"]},
    ]


def _game(game_id: str, start: str, season: int = 2015, home: str = "H", away: str = "A") -> dict:
    return {"canonical_game_id": game_id, "home_canonical_team_id": home, "away_canonical_team_id": away,
            "season": season, "start_date_utc_text": start, "date_precision": "INSTANT", "source_id": "SRC-002"}


class Pr678ThreadRepairs(unittest.TestCase):
    def test_thread_02_08_padded_team_key_does_not_select_itself(self) -> None:
        contests = [{"contest_id": "1", "home_team_key": "A", "away_team_key": "B"}]
        row = build_current_contest_row(
            team_key="A ", contests=contests, historical_priors={"A": 1, "B": 1}, current_conference="C",
            current_subdivision="FBS", current_rank=None, rank_admitted=False,
            official_2026_finals_known_before_cutoff=None, trust_gate_open=False,
        )
        self.assertEqual(row["opponent_key"], "B")
        self.assertIsNone(resolve_current_contest("A", [{"contest_id": "2", "home_team_key": "A",
                                                          "away_team_key": "A"}]))

    def test_thread_06_canonical_cycle_identity_orders_the_ledger(self) -> None:
        attributions = import_bat_live._cycle_attributions({"supersessions": [{
            "supersession_kind": "CYCLE_IDENTITY_ATTRIBUTION", "jira_key": "BAT-523",
            "original_comment_id": "14723", "canonical_cycle_id": "CYCLE-25.5"}]})
        stored = {"jira_key": "BAT-523", "comment_id": "14723", "cycle": 26}
        real_26 = {"jira_key": "BAT-523", "comment_id": "15000", "cycle": "CYCLE-26"}
        self.assertEqual(import_bat_live._entry_canonical_cycle(stored, attributions), (25, 5))
        self.assertEqual(import_bat_live._entry_canonical_cycle(real_26, attributions), (26, 0))
        self.assertLess(import_bat_live._entry_canonical_cycle(stored, attributions),
                        import_bat_live._entry_canonical_cycle(real_26, attributions))
        self.assertIsNone(import_bat_live._parse_canonical_cycle("CYCLE-0"))
        self.assertIsNone(import_bat_live._parse_canonical_cycle(True))

        head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            entries = []
            for comment_id, cycle in (("14723", 26), ("15000", "CYCLE-26")):
                snapshot = Path(tmp) / f"{comment_id}.json"
                snapshot.write_text(json.dumps({"comment": comment_id}), encoding="utf-8")
                digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
                entries.append({
                    "jira_key": "BAT-523", "local_issue_id": "PARENT", "comment_id": comment_id,
                    "comment_body_sha256": "b" * 64, "material_merge_sha": head,
                    "immutable_evidence_snapshot_path": snapshot.relative_to(ROOT).as_posix(),
                    "immutable_evidence_snapshot_sha256": digest,
                    "evidence_classification": "IMMUTABLE_CYCLE_SNAPSHOT", "parent_progress_kind": "parent_progress",
                    "local_evidence_identity": digest, "cycle": cycle, "kind": "parent_progress"})
            ledger = {"schema_version": 2, "comments": entries, "supersessions": [{
                "supersession_kind": "CYCLE_IDENTITY_ATTRIBUTION", "jira_key": "BAT-523",
                "original_comment_id": "14723", "canonical_cycle_id": "CYCLE-25.5"}]}
            findings = import_bat_live.validate_authority_progress_comment_ledger_static(ROOT, ledger)
            cycle_findings = [item for item in findings if "cycle" in item and "supersession" not in item]
            self.assertEqual([], cycle_findings)
            ledger["comments"] = list(reversed(entries))
            findings = import_bat_live.validate_authority_progress_comment_ledger_static(ROOT, ledger)
            self.assertTrue(any("non-monotonic cycle order" in item for item in findings))

    def test_thread_07_reference_abstains_without_interval_mass(self) -> None:
        z = inverse_normal_cdf(0.975)
        row = {"expected_margin_home": 0.0, "home_win_probability": 0.5, "interval_lower": -z,
               "interval_upper": z}
        without_mass = joint_distribution_coherent(row, residual_stdev=1.0, quantile=z)
        self.assertFalse(without_mass["coherent"])
        self.assertEqual(without_mass["abstain_reason"], "ABSTAIN_INTERVAL_MASS_REQUIRED")
        self.assertTrue(joint_distribution_coherent(row, residual_stdev=1.0, interval_mass=0.95)["coherent"])

    def test_thread_09_bookless_or_nameless_quotes_are_counted_not_fatal(self) -> None:
        quote = {"home_team": "Texas A&M", "away_team": "Missouri St.", "event_id": "e1", "book": "Draft Kings",
                 "snapshot_id": "s1", "home_price": -400}
        result = focus_game_quote_count([quote, {**quote, "book": ""}, {**quote, "home_team": ""}])
        self.assertEqual(result["quote_count"], 1)
        self.assertEqual(result["rejected_empty_identifier_rows"], 2)

    def test_thread_10_producer_rejects_nonfinite_or_out_of_range_probabilities(self) -> None:
        for bad in (math.nan, math.inf, 1.2, -0.1):
            with self.assertRaises(ValueError):
                one_observation_per_book([0.5, bad], ["a", "b"])
        self.assertEqual(one_observation_per_book([0.4, 0.6], ["a", "b"])[0], [0.4, 0.6])


class Pr681ThreadRepairs(unittest.TestCase):
    def test_thread_31_scoring_compares_instants(self) -> None:
        # 19:30-05:00 is 00:30Z the next day: after a 00:00Z kickoff although the text sorts first.
        reject_prekickoff_final("2026-09-06T19:30:00-05:00", "2026-09-07T00:00:00Z")
        with self.assertRaises(IndependentScoringError):
            reject_prekickoff_final("2026-09-06T23:00:00Z", "2026-09-06T19:00:00-05:00")
        with self.assertRaises(IndependentScoringError):
            reject_prekickoff_final("2026-09-06T23:00:00", "2026-09-06T19:00:00Z")

    def test_thread_32_non_success_scrapfly_status_is_not_a_capture(self) -> None:
        tool = _load_tool("acquire_cycle28_official_atomic")
        payload = json.dumps({"result": {"status_code": 503, "content": "<html>error</html>"}}).encode()
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(payload)
        with mock.patch.object(tool.urllib.request, "urlopen", return_value=response):
            body, outcome = tool.transport_fetch("https://example.invalid/", "token")
        self.assertIsNone(body)
        self.assertEqual(outcome["condition"], "UPSTREAM_STATUS_503")

    def test_threads_33_40_request_identity_is_semantic(self) -> None:
        tool = _load_tool("acquire_cycle28_official_atomic")
        target = dict(tool.TARGETS[0])
        self.assertEqual(tool.request_identity(target), tool.request_identity(dict(target)))
        self.assertNotEqual(tool.request_identity(target),
                            tool.request_identity({**target, "source_uri": target["source_uri"] + "?x"}))

    def test_thread_35_one_payload_cannot_capture_two_contests(self) -> None:
        tool = _load_tool("acquire_cycle28_official_atomic")
        records = tool.quarantine_cross_contest_duplicates([
            {"state": "CAPTURED", "raw_sha256": "r1", "ncaa_contest_id": "1"},
            {"state": "CAPTURED", "raw_sha256": "r1", "ncaa_contest_id": "2"},
            {"state": "CAPTURED", "raw_sha256": "r2", "ncaa_contest_id": "3"},
            {"state": "CAPTURED", "raw_sha256": "r1", "ncaa_contest_id": None},
        ])
        self.assertEqual([row["state"] for row in records],
                         ["DUPLICATE_PAYLOAD_ACROSS_CONTESTS", "DUPLICATE_PAYLOAD_ACROSS_CONTESTS", "CAPTURED",
                          "CAPTURED"])

    def test_thread_39_game_grain_scoring_collapses_oriented_pairs(self) -> None:
        rows = [
            {"ncaa_contest_id": "1", "orientation": "HOME", "predicted_probability": 0.7, "observed_win": 1},
            {"ncaa_contest_id": "1", "orientation": "AWAY", "predicted_probability": 0.3, "observed_win": 0},
            {"ncaa_contest_id": "2", "orientation": "HOME", "predicted_probability": 0.4, "observed_win": 0},
            {"ncaa_contest_id": "2", "orientation": "AWAY", "predicted_probability": 0.6, "observed_win": 1},
        ]
        self.assertEqual(score_game_grain(contests=rows)["unique_games"], 2)
        broken = [dict(row) for row in rows]
        broken[1]["predicted_probability"] = 0.5
        with self.assertRaises(Cycle28ScoringError):
            score_game_grain(contests=broken)


class Pr685ThreadRepairs(unittest.TestCase):
    def test_threads_55_discovery_scans_every_artifact_and_numeric_field(self) -> None:
        declared = [{"claim_id": "rows", "artifact_path": "KNOWN.json", "field": "proven_pit_training_rows",
                     **{field: "x" for field in ("formula", "numerator", "denominator", "population",
                                                 "source_identities", "temporal_authority", "producer",
                                                 "validator", "independent_reference", "dependencies",
                                                 "trust_class")}}]
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp)
            (art / "KNOWN.json").write_text(json.dumps({"proven_pit_training_rows": 0}), encoding="utf-8")
            (art / "TRACE.json").write_text(json.dumps({"spine_edges_1963_2025": 52}), encoding="utf-8")
            discovered = discover_authority_claims(art, declared)
            self.assertIn(("TRACE.json", "spine_edges_1963_2025"),
                          {(row["artifact_path"], row["field"]) for row in discovered})
            with self.assertRaises(ClaimError):
                inventory_claims(declared, discovered)

    def test_thread_56_validator_reads_the_inventory(self) -> None:
        tool = _load_tool("validate_cycle29_gates")
        claim = {field: "x" for field in tool.INVENTORY_CLAIM_FIELDS}
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp)
            inventory = {"claims": [{**claim, "field": "a_count"}], "unmapped_count": 3, "discovered_count": 1}
            (art / "CYCLE29_CLAIM_INVENTORY.json").write_text(json.dumps(inventory), encoding="utf-8")
            (art / "GATE.json").write_text(json.dumps({"a_count": 1, "undeclared": 2}), encoding="utf-8")
            findings = tool.claim_inventory_findings(art)
            self.assertTrue(any("unmapped_count" in item for item in findings))
            self.assertTrue(any("absent from the inventory" in item for item in findings))
            inventory["unmapped_count"] = 0
            (art / "CYCLE29_CLAIM_INVENTORY.json").write_text(json.dumps(inventory), encoding="utf-8")
            (art / "GATE.json").write_text(json.dumps({"a_count": 1}), encoding="utf-8")
            self.assertEqual([], tool.claim_inventory_findings(art))

    def test_thread_57_duplicate_game_identity_is_rejected(self) -> None:
        game = _game("G1", "2015-09-05T19:00:00Z")
        with self.assertRaises(PitKernelError):
            build_game_grain_kernel([game, dict(game)], _outcomes(game, 21, 14), expected_population_complete=False,
                                    contemporaneous_fbs_authority=True, cross_subdivision=False)
        with self.assertRaises(IndependentPitError):
            reconstruct_game_features([game, dict(game)], _outcomes(game, 21, 14))

    def test_thread_58_incoherent_outcome_pair_is_not_proven(self) -> None:
        first, second = _game("G1", "2015-09-05T19:00:00Z"), _game("G2", "2015-09-19T19:00:00Z")
        both_win = _outcomes(second, 21, 14)
        both_win[1]["label_win"] = True
        kernel = build_game_grain_kernel([first, second], [*_outcomes(first, 21, 14), *both_win],
                                         expected_population_complete=False, contemporaneous_fbs_authority=True,
                                         cross_subdivision=False)
        self.assertNotIn("G2", [row["canonical_game_id"] for row in kernel["rows"]])
        self.assertIn({"canonical_game_id": "G2", "blocker": "REJECTED_INCOHERENT_OUTCOME_PAIR"},
                      kernel["blockers"])
        rebuilt = reconstruct_game_features([first, second], [*_outcomes(first, 21, 14), *both_win])
        self.assertNotIn("G2", {row["canonical_game_id"] for row in rebuilt})

    def test_thread_59_admission_uses_the_capture_upstream_state(self) -> None:
        tree = ast.parse((ROOT / "tools" / "acquire_cycle29_remaining_week1.py").read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and getattr(node.func, "id", "") == "admit_official_final"]
        self.assertTrue(calls)
        for call in calls:
            upstream = next(kw.value for kw in call.keywords if kw.arg == "upstream_ok")
            self.assertNotIsInstance(upstream, ast.Constant)


class Pr686Pr687ThreadRepairs(unittest.TestCase):
    def test_thread_68_retrospective_prior_taints_every_later_row(self) -> None:
        prior = _game("P", "2015-09-05T19:00:00Z")
        first = _game("T1", "2015-09-12T19:00:00Z")
        second = _game("T2", "2015-09-19T19:00:00Z")

        def proven(game: dict) -> dict:
            known = game["start_date_utc_text"].replace("T19:", "T09:")
            return {"source_id": "SRC-002", "effective_utc": known, "known_at_utc": known,
                    "source_publication_utc": known, "receipt_sha256": "a" * 64,
                    "classification": "PUBLISHED_RESULT", "evidence_class": "PUBLICATION_RECEIPT"}

        kernel = build_cycle30_kernel(
            [prior, first, second],
            [*_outcomes(prior, 21, 14), *_outcomes(first, 24, 17), *_outcomes(second, 28, 3)],
            expected_population_complete=False,
            authorities={"T1": proven(first), "T2": proven(second)},
            target_cutoff_by_game={game["canonical_game_id"]: game["start_date_utc_text"]
                                   for game in (prior, first, second)},
        )
        proven_ids = {row["canonical_game_id"] for row in kernel["rows"]}
        self.assertNotIn("T1", proven_ids)
        self.assertNotIn("T2", proven_ids)
        self.assertIn("T2", {row["canonical_game_id"] for row in kernel["retrospective_rows"]})

    def test_thread_69_source_ids_are_not_canonical(self) -> None:
        payload = week1_slice_from_contests([
            {"ncaa_contest_id": "1", "home_id": "622349", "away_canonical_team_id": "SRC-002:TEAM:2"},
        ])
        self.assertEqual(payload["identity_class"], "SOURCE_ID_NOT_CANONICAL")
        self.assertEqual(payload["unresolved_contest_ids"], ["1"])
        self.assertEqual(payload["artifact_class"], "BLOCKER_METADATA")

    def test_thread_70_science_needs_live_reconstruction(self) -> None:
        tool = _load_tool("validate_cycle30_gates")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            art = root / tool.ART_REL
            art.mkdir(parents=True)
            (art / "PIT_KERNEL_POPULATION_MANIFEST.json").write_text(json.dumps({"game_grain_count": 1}),
                                                                      encoding="utf-8")
            rows = root / "rows.jsonl"
            rows.write_text(json.dumps({"canonical_game_id": "G"}) + "\n", encoding="utf-8")
            games = root / "games.jsonl"
            games.write_text("", encoding="utf-8")
            passthrough = {"rows_opened": 1}
            with mock.patch.object(tool, "reject_empty_science_pass"), \
                    mock.patch.object(tool, "reject_vacuous_row_count", return_value=1), \
                    mock.patch.object(tool, "open_and_rehash", return_value=passthrough), \
                    mock.patch.object(tool, "reject_pass_without_opening"), \
                    mock.patch("aggie_analytics.scientific_reference.cycle30.pit.challenge_kernel_rows"):
                self.assertEqual(tool._science(root, kernel_rows=rows), 2)
                with mock.patch("aggie_analytics.scientific_reference.cycle30.pit.reconstruct_game_features",
                                return_value=[]):
                    self.assertEqual(tool._science(root, kernel_rows=rows, source_games=games,
                                                   source_outcomes=games), 1)


class Pr678Thread03PairCensus(unittest.TestCase):
    def test_thread_03_pairs_need_two_distinct_orientations(self) -> None:
        tool = _load_tool("cycle26_evidence_collection")
        rows = [
            {"candidate_id": "c", "canonical_game_id": "g1", "canonical_team_id": "H",
             "predicted_win_probability": 0.6, "predicted_margin": 3.0},
            {"candidate_id": "c", "canonical_game_id": "g1", "canonical_team_id": "A",
             "predicted_win_probability": 0.4, "predicted_margin": -3.0},
            {"candidate_id": "c", "canonical_game_id": "g2", "canonical_team_id": "H",
             "predicted_win_probability": 0.2, "predicted_margin": 1.0},
        ]
        raw = "\n".join(json.dumps(row) for row in rows).encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "p.jsonl").write_bytes(raw)
            with mock.patch.object(tool, "DATA_ROOT", Path(tmp)), \
                    mock.patch.object(tool, "PREDICTIONS", {"26": ("p.jsonl", hashlib.sha256(raw).hexdigest())}):
                summary = tool.pair_census()["26"]["candidate_results"]["c"]
        self.assertEqual(summary["all_game_pairs"], 1)
        self.assertEqual(summary["malformed_game_groups"], 1)
        self.assertEqual(summary["probability_sum_failures_tolerance_1e_8"], 0)


if __name__ == "__main__":
    unittest.main()
