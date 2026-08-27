from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2001_expanded import (  # noqa: E402
    FORBIDDEN_UNION_URLS,
    OFFICIAL_2001_ADMITTED_EXPECTED,
    OFFICIAL_2001_EXPECTED,
    OFFICIAL_2001_INDEX_URL,
    OKLAHOMA_2002_UNMATCHED_URL,
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    PINNED_BAT603_GATE_IDENTITY,
    PINNED_BAT603_UNION_IDENTITY,
    PINNED_BAT607_GATE_IDENTITY,
    PINNED_BAT607_UNION_IDENTITY,
    PINNED_BAT608_GATE_IDENTITY,
    PINNED_BAT608_UNION_IDENTITY,
    PINNED_BAT612_GATE_IDENTITY,
    PINNED_BAT612_UNION_IDENTITY,
    PINNED_BAT617_GATE_IDENTITY,
    PINNED_BAT617_PAYLOAD_IDENTITY,
    PINNED_BAT618_GATE_IDENTITY,
    PINNED_BAT618_UNION_IDENTITY,
    PINNED_BAT620_DATASET_IDENTITY,
    PINNED_BAT620_GATE_IDENTITY,
    PINNED_BAT621_GATE_IDENTITY,
    PINNED_BAT622_ACQUISITION_IDENTITY,
    PINNED_BAT622_DATASET_IDENTITY,
    PINNED_BAT622_GAMES_IDENTITY,
    PINNED_BAT622_GATE_IDENTITY,
    PINNED_BAT623_GATE_IDENTITY,
    PINNED_BAT623_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    PRIOR_UNION_CAPTURED_GAMES,
    VALIDATION_CONTRACT_VERSION,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2001,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    load_json,
    reconstruct_objects,
    recompute_bat622_identities,
    recompute_bat623_payload_identity,
    validate_artifact,
    validate_bat622_external_payload,
    validate_bat623_external_payload,
)


DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT, REPO_ROOT)
EXPECTED_GATE_IDENTITY = "6a202220816144915474278d15e46a43b2ac5610b6a8d87fdfa7b180b1a41710"
EXPECTED_UNION_IDENTITY = "cb6ff59928119325851db92e7dd1dfc221923da8c86b895e234f459b6adf63a8"


def _copy(value):
    return json.loads(json.dumps(value))


def _mutated(gate: dict, **changes):
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class CompactExpanded2001UnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2001-expanded union gate not materialized yet")
        self.gate = load_json(path)

    def test_committed_counts_predecessor_and_2001_admissions(self) -> None:
        if EXPECTED_GATE_IDENTITY:
            self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
            self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(
            self.gate["predecessor_union_identity"], PINNED_BAT618_UNION_IDENTITY
        )
        self.assertEqual(
            self.gate["predecessor_gate_identity"], PINNED_BAT618_GATE_IDENTITY
        )
        self.assertEqual(
            self.gate["validation_contract_version"], VALIDATION_CONTRACT_VERSION
        )
        self.assertEqual(
            self.gate["counts"]["new_games_added"], OFFICIAL_2001_ADMITTED_EXPECTED
        )
        self.assertEqual(
            self.gate["counts"]["official_2001_admitted"],
            OFFICIAL_2001_ADMITTED_EXPECTED,
        )
        self.assertEqual(self.gate["counts"]["official_2001_rejected"], 0)
        self.assertEqual(
            self.gate["counts"]["official_2001_target_games"], OFFICIAL_2001_EXPECTED
        )
        self.assertEqual(self.gate["counts"]["official_2002_rejected"], 1)
        self.assertEqual(
            self.gate["counts"]["predecessor_296_union_games_preserved"],
            PRIOR_UNION_CAPTURED_GAMES,
        )
        self.assertEqual(self.gate["counts"]["union_captured_games"], 308)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 295)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["scoring_summary_present_games"], 105)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["counts"]["overlays_became_rich_this_phase"], 12)
        self.assertEqual(
            self.gate["upstream_identities"]["bat618_union_identity"],
            PINNED_BAT618_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat612_union_identity"],
            PINNED_BAT612_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat608_union_identity"],
            PINNED_BAT608_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat607_union_identity"],
            PINNED_BAT607_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat603_union_identity"],
            PINNED_BAT603_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat602_union_identity"],
            PINNED_BAT602_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat620_gate_identity"],
            PINNED_BAT620_GATE_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat622_dataset_identity"],
            PINNED_BAT622_DATASET_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat623_payload_identity"],
            PINNED_BAT623_PAYLOAD_IDENTITY,
        )
        self.assertEqual(
            self.gate["recomputed_upstream"]["bat622_dataset_identity"],
            PINNED_BAT622_DATASET_IDENTITY,
        )
        self.assertEqual(
            self.gate["recomputed_upstream"]["bat623_payload_identity"],
            PINNED_BAT623_PAYLOAD_IDENTITY,
        )
        self.assertEqual(
            self.gate["validator_code_identity"], compute_code_identity(REPO_ROOT)
        )
        self.assertTrue(self.gate["recomputed_upstream"]["validator_code_identity"])
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertTrue(set(FORBIDDEN_UNION_URLS).isdisjoint(admitted))
        self.assertNotIn(OKLAHOMA_2002_UNMATCHED_URL, admitted)
        self.assertEqual(len(self.gate["admitted_official_2001_games"]), 12)
        self.assertEqual(len(self.gate["enriched_official_games"]), 105)
        self.assertTrue(
            all(
                item.get("parent_url") == OFFICIAL_2001_INDEX_URL
                for item in self.gate["admitted_official_2001_games"]
            )
        )
        self.assertTrue(
            all(
                item.get("structured_row_payload_identity")
                == PINNED_BAT623_PAYLOAD_IDENTITY
                for item in self.gate["admitted_official_2001_games"]
            )
        )
        self.assertTrue(
            all(
                item.get("availability") == "NOT_ESTABLISHED"
                for item in self.gate["admitted_official_2001_games"]
            )
        )
        self.assertFalse(
            any(
                item.get("availability_claim")
                for item in self.gate["enriched_official_games"]
            )
        )
        self.assertFalse(
            any(
                item.get("ncaa_contest_id")
                for item in self.gate["enriched_official_games"]
            )
        )
        self.assertEqual(
            self.gate["admissions"]["bat_429"], "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES"
        )
        self.assertEqual(self.gate["admissions"]["bat_523"], "IN_PROGRESS")
        self.assertEqual(self.gate["admissions"]["gap_005"], "OPEN")
        self.assertEqual(self.gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertFalse(
            self.gate["authority"]["trusted_declared_upstream_identity_only"]
        )
        self.assertEqual(
            self.gate["selected_seasons"],
            [2009, 2008, 2007, 2006, 2005, 2004, 2003, 2002, 2001],
        )

    def test_prior_identities_are_not_rewritten(self) -> None:
        bat618 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2002_expanded_gate.json"
        )
        bat612 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2003_expanded_gate.json"
        )
        bat608 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_integrity_complete_gate.json"
        )
        bat607 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2004_expanded_gate.json"
        )
        bat603 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2005_integrity_bound_gate.json"
        )
        bat602 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2005_expanded_gate.json"
        )
        bat620 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_2002_2009_structured_row_corpus_integrity_gate.json"
        )
        bat622 = load_json(
            REPO_ROOT / "artifacts/data_lake/tamu_official_2001_boxscore_gate.json"
        )
        bat623 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_2001_structured_domains_gate.json"
        )
        bat621 = load_json(
            REPO_ROOT / "artifacts/data_lake/tamu_official_2001_season_index_gate.json"
        )
        self.assertEqual(bat618["union_identity"], PINNED_BAT618_UNION_IDENTITY)
        self.assertEqual(bat618["gate_identity"], PINNED_BAT618_GATE_IDENTITY)
        self.assertEqual(bat612["union_identity"], PINNED_BAT612_UNION_IDENTITY)
        self.assertEqual(bat612["gate_identity"], PINNED_BAT612_GATE_IDENTITY)
        self.assertEqual(bat608["union_identity"], PINNED_BAT608_UNION_IDENTITY)
        self.assertEqual(bat608["gate_identity"], PINNED_BAT608_GATE_IDENTITY)
        self.assertEqual(bat607["union_identity"], PINNED_BAT607_UNION_IDENTITY)
        self.assertEqual(bat607["gate_identity"], PINNED_BAT607_GATE_IDENTITY)
        self.assertEqual(bat603["union_identity"], PINNED_BAT603_UNION_IDENTITY)
        self.assertEqual(bat603["gate_identity"], PINNED_BAT603_GATE_IDENTITY)
        self.assertEqual(bat602["union_identity"], PINNED_BAT602_UNION_IDENTITY)
        self.assertEqual(bat602["gate_identity"], PINNED_BAT602_GATE_IDENTITY)
        self.assertEqual(bat620["gate_identity"], PINNED_BAT620_GATE_IDENTITY)
        self.assertEqual(bat620["dataset_identity"], PINNED_BAT620_DATASET_IDENTITY)
        self.assertEqual(bat622["gate_identity"], PINNED_BAT622_GATE_IDENTITY)
        self.assertEqual(bat622["dataset_identity"], PINNED_BAT622_DATASET_IDENTITY)
        self.assertEqual(
            bat622["acquisition_identity"], PINNED_BAT622_ACQUISITION_IDENTITY
        )
        self.assertEqual(bat622["games_identity"], PINNED_BAT622_GAMES_IDENTITY)
        self.assertEqual(bat623["payload_identity"], PINNED_BAT623_PAYLOAD_IDENTITY)
        self.assertEqual(bat623["gate_identity"], PINNED_BAT623_GATE_IDENTITY)
        self.assertEqual(bat621["gate_identity"], PINNED_BAT621_GATE_IDENTITY)
        self.assertEqual(
            load_json(
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2002_structured_domains_gate.json"
            )["payload_identity"],
            PINNED_BAT617_PAYLOAD_IDENTITY,
        )
        self.assertEqual(
            load_json(
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2002_structured_domains_gate.json"
            )["gate_identity"],
            PINNED_BAT617_GATE_IDENTITY,
        )

    def test_parent_url_fallback_is_forbidden(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "parent_url missing"):
            compact_official_2001(
                {"url": "https://example.invalid/box"}, OFFICIAL_2001_INDEX_URL
            )
        with self.assertRaisesRegex(AuthorityViolation, "does not match BAT-621"):
            compact_official_2001(
                {
                    "url": "https://example.invalid/box",
                    "parent_url": "https://files.12thman.com/history/football/years/2002.html",
                    "source_season": 2001,
                    "football_season": 2001,
                },
                OFFICIAL_2001_INDEX_URL,
            )

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_forged_done_verified_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="DONE", classification="VERIFIED"),
                require_rebuild=False,
            )

    def test_ncaa_id_rejected_url_oklahoma_and_429_fail(self) -> None:
        counts = _copy(self.gate["counts"])
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, counts=counts),
                require_rebuild=False,
            )
        games = _copy(self.gate["enriched_official_games"])
        games.append(_copy(self.gate["preserved_rejections"][0]))
        with self.assertRaisesRegex(AuthorityViolation, "rejected"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, enriched_official_games=games),
                require_rebuild=False,
            )
        oklahoma = _copy(self.gate["enriched_official_games"])
        oklahoma.append(
            {
                "url": OKLAHOMA_2002_UNMATCHED_URL,
                "availability": "NOT_ESTABLISHED",
                "availability_claim": False,
                "ncaa_contest_id": None,
            }
        )
        with self.assertRaisesRegex(AuthorityViolation, "Oklahoma"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, enriched_official_games=oklahoma),
                require_rebuild=False,
            )
        admissions = _copy(self.gate["admissions"])
        admissions["bat_429"] = "DONE_VERIFIED"
        with self.assertRaisesRegex(AuthorityViolation, "BAT-429"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, admissions=admissions),
                require_rebuild=False,
            )


@unittest.skipUnless(
    LAKE_READY, "external BAT-618/BAT-622/BAT-623 payloads are not mounted"
)
class Expanded2001ReconstructionAndTamperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.bat622 = _copy(self.objects["bat622"]["payload"])
        self.bat623 = _copy(self.objects["bat623"]["payload"])

    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["counts"]["new_games_added"], 12)
        self.assertEqual(result["counts"]["union_captured_games"], 308)
        self.assertEqual(
            result["recomputed_upstream"]["bat622_dataset_identity"],
            PINNED_BAT622_DATASET_IDENTITY,
        )
        self.assertEqual(
            result["recomputed_upstream"]["bat623_payload_identity"],
            PINNED_BAT623_PAYLOAD_IDENTITY,
        )
        gate = load_json(REPO_ROOT / GATE_RELATIVE)
        self.assertEqual(result["gate_identity"], gate["gate_identity"])
        self.assertEqual(result["union_identity"], gate["union_identity"])

    def test_bat622_identity_recompute_matches_pins(self) -> None:
        recomputed = recompute_bat622_identities(self.bat622)
        self.assertEqual(recomputed["dataset_identity"], PINNED_BAT622_DATASET_IDENTITY)
        self.assertEqual(
            recomputed["acquisition_identity"], PINNED_BAT622_ACQUISITION_IDENTITY
        )
        self.assertEqual(recomputed["games_identity"], PINNED_BAT622_GAMES_IDENTITY)
        validated = validate_bat622_external_payload(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT,
            allowed_urls=[item["url"] for item in self.objects["bat622"]["games"]],
        )
        self.assertEqual(validated["identities"], recomputed)
        self.assertTrue(
            all(
                game["parent_url"] == OFFICIAL_2001_INDEX_URL
                for game in validated["games"]
            )
        )
        self.assertEqual(len(validated["games"]), 12)

    def test_bat623_row_counts_recompute_from_serialized_rows(self) -> None:
        validated = validate_bat623_external_payload(
            repo_root=REPO_ROOT, data_root=DATA_ROOT
        )
        self.assertEqual(validated["payload_identity"], PINNED_BAT623_PAYLOAD_IDENTITY)
        total_rows = 0
        for game in validated["games"].values():
            counts = game["row_counts"]
            self.assertGreater(sum(counts.values()), 0)
            total_rows += sum(counts.values())
            for domain, flag in game["domain_coverage"].items():
                if domain in counts and flag == "PRESENT":
                    self.assertGreater(counts[domain], 0)
        self.assertEqual(total_rows, 5249)

    def test_bat622_opponent_score_sha_parent_and_membership_tampers_fail(self) -> None:
        opponent = _copy(self.bat622)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=opponent
            )
        score = _copy(self.bat622)
        score["games"][0]["tamu_points"] = 99
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=score
            )
        sha = _copy(self.bat622)
        sha["games"][0]["source_sha256"] = "0" * 64
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=sha
            )
        missing = _copy(self.bat622)
        missing["games"][0].pop("parent_url", None)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=missing
            )
        substituted = _copy(self.bat622)
        substituted["games"][0]["parent_url"] = (
            "https://files.12thman.com/history/football/years/2002.html"
        )
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=substituted
            )
        captures = _copy(self.bat622)
        captures["captures"] = captures["captures"][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=captures
            )
        name_only = _copy(self.bat622)
        name_only["games"][0]["canonical_game_match_status"] = (
            "MATCHED_OPPONENT_NAME_ONLY"
        )
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat622_payload=name_only
            )

    def test_bat623_row_and_coverage_tampers_fail(self) -> None:
        changed = _copy(self.bat623)
        if changed["rows"][0]:
            changed["rows"][0][0]["cells"] = ["FORGED"]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat623_payload=changed
            )
        removed = _copy(self.bat623)
        removed["rows"][0] = removed["rows"][0][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat623_payload=removed
            )
        added = _copy(self.bat623)
        extra = (
            _copy(added["rows"][0][0])
            if added["rows"][0]
            else {"domain": "team_statistics"}
        )
        added["rows"][0] = list(added["rows"][0]) + [extra]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat623_payload=added
            )
        present_zero = _copy(self.bat623)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat623_payload=present_zero
            )
        parser = _copy(self.bat623)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat623_payload=parser
            )
        availability = _copy(self.bat623)
        availability["availability_claim"] = True
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat623_payload=availability
            )
        compact = _copy(
            load_json(
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2001_structured_domains_gate.json"
            )["games"]
        )
        compact[0]["row_counts"]["team_statistics"] = (
            int(compact[0]["row_counts"]["team_statistics"]) + 1
        )
        with self.assertRaises(AuthorityViolation):
            validate_bat623_external_payload(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                payload=self.bat623,
                compact_games=compact,
            )

    def test_coordinated_tamper_plus_recomputed_outer_identity_fails(self) -> None:
        bat622 = _copy(self.bat622)
        bat622["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        bat622.update(recompute_bat622_identities(bat622))
        bat623 = _copy(self.bat623)
        if bat623["rows"][0]:
            bat623["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        bat623["payload_identity"] = recompute_bat623_payload_identity(bat623)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                bat622_payload=bat622,
                bat623_payload=bat623,
            )


if __name__ == "__main__":
    unittest.main()
