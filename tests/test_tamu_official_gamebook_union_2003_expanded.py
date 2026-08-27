from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2003_expanded import (  # noqa: E402
    OFFICIAL_2003_EXPECTED,
    OFFICIAL_2003_INDEX_URL,
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    PINNED_BAT603_GATE_IDENTITY,
    PINNED_BAT603_UNION_IDENTITY,
    PINNED_BAT607_GATE_IDENTITY,
    PINNED_BAT607_UNION_IDENTITY,
    PINNED_BAT608_GATE_IDENTITY,
    PINNED_BAT608_UNION_IDENTITY,
    PINNED_BAT609_GATE_IDENTITY,
    PINNED_BAT610_ACQUISITION_IDENTITY,
    PINNED_BAT610_DATASET_IDENTITY,
    PINNED_BAT610_GAMES_IDENTITY,
    PINNED_BAT610_GATE_IDENTITY,
    PINNED_BAT611_GATE_IDENTITY,
    PINNED_BAT611_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    PRIOR_UNION_CAPTURED_GAMES,
    VALIDATION_CONTRACT_VERSION,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2003,
    compute_gate_identity,
    lake_is_ready,
    load_json,
    reconstruct_objects,
    recompute_bat610_identities,
    recompute_bat611_payload_identity,
    validate_artifact,
    validate_bat610_external_payload,
    validate_bat611_external_payload,
)


DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = lake_is_ready(DATA_ROOT)
EXPECTED_GATE_IDENTITY = "50e92663d6dbfd8c6770746c99c857cc9db2f1761714e5124a8334eff384f99f"
EXPECTED_UNION_IDENTITY = "22ab52efad425074ddab75593c882ca7d1fb0fab6e99df160af1681cfc26f5aa"


def _copy(value):
    return json.loads(json.dumps(value))


def _mutated(gate: dict, **changes):
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class CompactExpanded2003UnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2003-expanded union gate not materialized yet")
        self.gate = load_json(path)

    def test_committed_counts_predecessor_and_2003_admissions(self) -> None:
        if EXPECTED_GATE_IDENTITY.startswith("PLACEHOLDER"):
            self.assertEqual(len(self.gate["gate_identity"]), 64)
            self.assertEqual(len(self.gate["union_identity"]), 64)
        else:
            self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
            self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(self.gate["predecessor_union_identity"], PINNED_BAT608_UNION_IDENTITY)
        self.assertEqual(self.gate["predecessor_gate_identity"], PINNED_BAT608_GATE_IDENTITY)
        self.assertEqual(self.gate["validation_contract_version"], VALIDATION_CONTRACT_VERSION)
        self.assertEqual(self.gate["counts"]["new_games_added"], OFFICIAL_2003_EXPECTED)
        self.assertEqual(self.gate["counts"]["official_2003_admitted"], OFFICIAL_2003_EXPECTED)
        self.assertEqual(self.gate["counts"]["official_2003_rejected"], 0)
        self.assertEqual(self.gate["counts"]["predecessor_273_union_games_preserved"], PRIOR_UNION_CAPTURED_GAMES)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 285)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 272)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["scoring_summary_present_games"], 82)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["counts"]["overlays_became_rich_this_phase"], 12)
        self.assertEqual(self.gate["upstream_identities"]["bat608_union_identity"], PINNED_BAT608_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat607_union_identity"], PINNED_BAT607_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat603_union_identity"], PINNED_BAT603_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat602_union_identity"], PINNED_BAT602_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat610_dataset_identity"], PINNED_BAT610_DATASET_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat611_payload_identity"], PINNED_BAT611_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["recomputed_upstream"]["bat610_dataset_identity"], PINNED_BAT610_DATASET_IDENTITY)
        self.assertEqual(self.gate["recomputed_upstream"]["bat611_payload_identity"], PINNED_BAT611_PAYLOAD_IDENTITY)
        self.assertTrue(self.gate["recomputed_upstream"]["validator_code_identity"])
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertEqual(len(self.gate["admitted_official_2003_games"]), 12)
        self.assertEqual(len(self.gate["enriched_official_games"]), 82)
        self.assertTrue(all(item.get("parent_url") == OFFICIAL_2003_INDEX_URL for item in self.gate["admitted_official_2003_games"]))
        self.assertTrue(
            all(item.get("structured_row_payload_identity") == PINNED_BAT611_PAYLOAD_IDENTITY for item in self.gate["admitted_official_2003_games"])
        )
        self.assertTrue(all(item.get("availability") == "NOT_ESTABLISHED" for item in self.gate["admitted_official_2003_games"]))
        self.assertFalse(any(item.get("availability_claim") for item in self.gate["enriched_official_games"]))
        self.assertFalse(any(item.get("ncaa_contest_id") for item in self.gate["enriched_official_games"]))
        self.assertEqual(self.gate["admissions"]["bat_429"], "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES")
        self.assertEqual(self.gate["admissions"]["bat_523"], "IN_PROGRESS")
        self.assertEqual(self.gate["admissions"]["gap_005"], "OPEN")
        self.assertEqual(self.gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertFalse(self.gate["authority"]["trusted_declared_upstream_identity_only"])
        self.assertEqual(self.gate["selected_seasons"], [2009, 2008, 2007, 2006, 2005, 2004, 2003])

    def test_prior_identities_are_not_rewritten(self) -> None:
        bat608 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_integrity_complete_gate.json")
        bat607 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_2004_expanded_gate.json")
        bat603 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_2005_integrity_bound_gate.json")
        bat602 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_2005_expanded_gate.json")
        bat610 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_2003_boxscore_gate.json")
        bat611 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_2003_structured_domains_gate.json")
        bat609 = load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_2003_season_index_gate.json")
        self.assertEqual(bat608["union_identity"], PINNED_BAT608_UNION_IDENTITY)
        self.assertEqual(bat608["gate_identity"], PINNED_BAT608_GATE_IDENTITY)
        self.assertEqual(bat607["union_identity"], PINNED_BAT607_UNION_IDENTITY)
        self.assertEqual(bat607["gate_identity"], PINNED_BAT607_GATE_IDENTITY)
        self.assertEqual(bat603["union_identity"], PINNED_BAT603_UNION_IDENTITY)
        self.assertEqual(bat603["gate_identity"], PINNED_BAT603_GATE_IDENTITY)
        self.assertEqual(bat602["union_identity"], PINNED_BAT602_UNION_IDENTITY)
        self.assertEqual(bat602["gate_identity"], PINNED_BAT602_GATE_IDENTITY)
        self.assertEqual(bat610["gate_identity"], PINNED_BAT610_GATE_IDENTITY)
        self.assertEqual(bat610["dataset_identity"], PINNED_BAT610_DATASET_IDENTITY)
        self.assertEqual(bat610["acquisition_identity"], PINNED_BAT610_ACQUISITION_IDENTITY)
        self.assertEqual(bat610["games_identity"], PINNED_BAT610_GAMES_IDENTITY)
        self.assertEqual(bat611["payload_identity"], PINNED_BAT611_PAYLOAD_IDENTITY)
        self.assertEqual(bat611["gate_identity"], PINNED_BAT611_GATE_IDENTITY)
        self.assertEqual(bat609["gate_identity"], PINNED_BAT609_GATE_IDENTITY)

    def test_parent_url_fallback_is_forbidden(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "parent_url missing"):
            compact_official_2003({"url": "https://example.invalid/box"}, OFFICIAL_2003_INDEX_URL)
        with self.assertRaisesRegex(AuthorityViolation, "does not match BAT-609"):
            compact_official_2003(
                {
                    "url": "https://example.invalid/box",
                    "parent_url": "https://files.12thman.com/history/football/years/2004.html",
                    "source_season": 2003,
                    "football_season": 2003,
                },
                OFFICIAL_2003_INDEX_URL,
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

    def test_ncaa_id_rejected_url_and_429_fail(self) -> None:
        counts = _copy(self.gate["counts"])
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)
        games = _copy(self.gate["enriched_official_games"])
        games.append(_copy(self.gate["preserved_rejections"][0]))
        with self.assertRaisesRegex(AuthorityViolation, "rejected"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, enriched_official_games=games),
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


@unittest.skipUnless(LAKE_READY, "external BAT-608/BAT-610/BAT-611 payloads are not mounted")
class Expanded2003ReconstructionAndTamperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.bat610 = _copy(self.objects["bat610"]["payload"])
        self.bat611 = _copy(self.objects["bat611"]["payload"])

    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["counts"]["new_games_added"], 12)
        self.assertEqual(result["counts"]["union_captured_games"], 285)
        self.assertEqual(result["recomputed_upstream"]["bat610_dataset_identity"], PINNED_BAT610_DATASET_IDENTITY)
        self.assertEqual(result["recomputed_upstream"]["bat611_payload_identity"], PINNED_BAT611_PAYLOAD_IDENTITY)
        gate = load_json(REPO_ROOT / GATE_RELATIVE)
        self.assertEqual(result["gate_identity"], gate["gate_identity"])
        self.assertEqual(result["union_identity"], gate["union_identity"])

    def test_bat610_identity_recompute_matches_pins(self) -> None:
        recomputed = recompute_bat610_identities(self.bat610)
        self.assertEqual(recomputed["dataset_identity"], PINNED_BAT610_DATASET_IDENTITY)
        self.assertEqual(recomputed["acquisition_identity"], PINNED_BAT610_ACQUISITION_IDENTITY)
        self.assertEqual(recomputed["games_identity"], PINNED_BAT610_GAMES_IDENTITY)
        validated = validate_bat610_external_payload(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT,
            allowed_urls=[item["url"] for item in self.objects["gate"]["admitted_official_2003_games"]],
        )
        self.assertEqual(validated["identities"], recomputed)
        self.assertTrue(all(game["parent_url"] == OFFICIAL_2003_INDEX_URL for game in validated["games"]))

    def test_bat611_row_counts_recompute_from_serialized_rows(self) -> None:
        validated = validate_bat611_external_payload(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(validated["payload_identity"], PINNED_BAT611_PAYLOAD_IDENTITY)
        total_rows = 0
        for game in validated["games"].values():
            counts = game["row_counts"]
            self.assertGreater(sum(counts.values()), 0)
            total_rows += sum(counts.values())
            for domain, flag in game["domain_coverage"].items():
                if domain in counts and flag == "PRESENT":
                    self.assertGreater(counts[domain], 0)
        self.assertEqual(total_rows, 5528)

    def test_bat610_opponent_score_sha_parent_and_membership_tampers_fail(self) -> None:
        opponent = _copy(self.bat610)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=opponent)
        score = _copy(self.bat610)
        score["games"][0]["tamu_points"] = 99
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=score)
        sha = _copy(self.bat610)
        sha["games"][0]["source_sha256"] = "0" * 64
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=sha)
        missing = _copy(self.bat610)
        missing["games"][0].pop("parent_url", None)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=missing)
        substituted = _copy(self.bat610)
        substituted["games"][0]["parent_url"] = "https://files.12thman.com/history/football/years/2004.html"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=substituted)
        captures = _copy(self.bat610)
        captures["captures"] = captures["captures"][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=captures)
        name_only = _copy(self.bat610)
        name_only["games"][0]["canonical_game_match_status"] = "MATCHED_OPPONENT_NAME_ONLY"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=name_only)

    def test_bat611_row_and_coverage_tampers_fail(self) -> None:
        changed = _copy(self.bat611)
        if changed["rows"][0]:
            changed["rows"][0][0]["cells"] = ["FORGED"]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat611_payload=changed)
        removed = _copy(self.bat611)
        removed["rows"][0] = removed["rows"][0][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat611_payload=removed)
        added = _copy(self.bat611)
        extra = _copy(added["rows"][0][0]) if added["rows"][0] else {"domain": "team_statistics"}
        added["rows"][0] = list(added["rows"][0]) + [extra]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat611_payload=added)
        present_zero = _copy(self.bat611)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat611_payload=present_zero)
        parser = _copy(self.bat611)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat611_payload=parser)
        availability = _copy(self.bat611)
        availability["availability_claim"] = True
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat611_payload=availability)
        compact = _copy(load_json(REPO_ROOT / "artifacts/data_lake/tamu_official_2003_structured_domains_gate.json")["games"])
        compact[0]["row_counts"]["team_statistics"] = int(compact[0]["row_counts"]["team_statistics"]) + 1
        with self.assertRaises(AuthorityViolation):
            validate_bat611_external_payload(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                payload=self.bat611,
                compact_games=compact,
            )

    def test_coordinated_tamper_plus_recomputed_outer_identity_fails(self) -> None:
        bat610 = _copy(self.bat610)
        bat610["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        bat610.update(recompute_bat610_identities(bat610))
        bat611 = _copy(self.bat611)
        if bat611["rows"][0]:
            bat611["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        bat611["payload_identity"] = recompute_bat611_payload_identity(bat611)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat610_payload=bat610, bat611_payload=bat611)


if __name__ == "__main__":
    unittest.main()
