from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from cycle26_frozen_predecessor import contained_reconstruction  # noqa: E402

from aggie_analytics.data.tamu_official_gamebook_union_2004_expanded import (  # noqa: E402
    OFFICIAL_2004_EXPECTED,
    OFFICIAL_2004_INDEX_URL,
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    PINNED_BAT603_GATE_IDENTITY,
    PINNED_BAT603_UNION_IDENTITY,
    PINNED_BAT604_GATE_IDENTITY,
    PINNED_BAT605_ACQUISITION_IDENTITY,
    PINNED_BAT605_DATASET_IDENTITY,
    PINNED_BAT605_GAMES_IDENTITY,
    PINNED_BAT605_GATE_IDENTITY,
    PINNED_BAT606_GATE_IDENTITY,
    PINNED_BAT606_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    PRIOR_UNION_CAPTURED_GAMES,
    VALIDATION_CONTRACT_VERSION,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2004,
    compute_gate_identity,
    lake_is_ready,
    load_json,
    reconstruct_objects,
    recompute_bat605_identities,
    recompute_bat606_payload_identity,
    validate_artifact,
    validate_bat605_external_payload,
    validate_bat606_external_payload,
)


DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(
    DATA_ROOT
)
EXPECTED_GATE_IDENTITY = (
    "525706ab4273443ca36e4c65ee386e6e2d9870644de16565ca16820bffcc98a9"
)
EXPECTED_UNION_IDENTITY = (
    "0bd42472491241967a2f562ea32561f5c7ee726a7146d2699728988e212a98f7"
)


def _copy(value):
    return json.loads(json.dumps(value))


def _mutated(gate: dict, **changes):
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class CompactExpanded2004UnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2004-expanded union gate not materialized yet")
        self.gate = load_json(path)

    def test_committed_counts_predecessor_and_2004_admissions(self) -> None:
        if EXPECTED_GATE_IDENTITY.startswith("PLACEHOLDER"):
            self.assertEqual(len(self.gate["gate_identity"]), 64)
            self.assertEqual(len(self.gate["union_identity"]), 64)
        else:
            self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
            self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(
            self.gate["predecessor_union_identity"], PINNED_BAT603_UNION_IDENTITY
        )
        self.assertEqual(
            self.gate["predecessor_gate_identity"], PINNED_BAT603_GATE_IDENTITY
        )
        self.assertEqual(
            self.gate["validation_contract_version"], VALIDATION_CONTRACT_VERSION
        )
        self.assertEqual(self.gate["counts"]["new_games_added"], OFFICIAL_2004_EXPECTED)
        self.assertEqual(
            self.gate["counts"]["official_2004_admitted"], OFFICIAL_2004_EXPECTED
        )
        self.assertEqual(self.gate["counts"]["official_2004_rejected"], 0)
        self.assertEqual(
            self.gate["counts"]["predecessor_261_union_games_preserved"],
            PRIOR_UNION_CAPTURED_GAMES,
        )
        self.assertEqual(self.gate["counts"]["union_captured_games"], 273)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 260)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["scoring_summary_present_games"], 70)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["date_conflicts"], 4)
        self.assertEqual(self.gate["counts"]["season_header_conflicts"], 1)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["counts"]["overlays_became_rich_this_phase"], 12)
        self.assertEqual(
            self.gate["upstream_identities"]["bat603_union_identity"],
            PINNED_BAT603_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat602_union_identity"],
            PINNED_BAT602_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat605_dataset_identity"],
            PINNED_BAT605_DATASET_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat606_payload_identity"],
            PINNED_BAT606_PAYLOAD_IDENTITY,
        )
        self.assertEqual(
            self.gate["recomputed_upstream"]["bat605_dataset_identity"],
            PINNED_BAT605_DATASET_IDENTITY,
        )
        self.assertEqual(
            self.gate["recomputed_upstream"]["bat606_payload_identity"],
            PINNED_BAT606_PAYLOAD_IDENTITY,
        )
        self.assertTrue(self.gate["recomputed_upstream"]["validator_code_identity"])
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertEqual(len(self.gate["admitted_official_2004_games"]), 12)
        self.assertEqual(len(self.gate["enriched_official_games"]), 70)
        self.assertTrue(
            all(
                item.get("parent_url") == OFFICIAL_2004_INDEX_URL
                for item in self.gate["admitted_official_2004_games"]
            )
        )
        self.assertTrue(
            all(
                item.get("structured_row_payload_identity")
                == PINNED_BAT606_PAYLOAD_IDENTITY
                for item in self.gate["admitted_official_2004_games"]
            )
        )
        self.assertTrue(
            all(
                item.get("availability") == "NOT_ESTABLISHED"
                for item in self.gate["admitted_official_2004_games"]
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
            self.gate["selected_seasons"], [2009, 2008, 2007, 2006, 2005, 2004]
        )

    def test_prior_identities_are_not_rewritten(self) -> None:
        bat603 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2005_integrity_bound_gate.json"
        )
        bat602 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2005_expanded_gate.json"
        )
        bat605 = load_json(
            REPO_ROOT / "artifacts/data_lake/tamu_official_2004_boxscore_gate.json"
        )
        bat606 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_2004_structured_domains_gate.json"
        )
        bat604 = load_json(
            REPO_ROOT / "artifacts/data_lake/tamu_official_2004_season_index_gate.json"
        )
        self.assertEqual(bat603["union_identity"], PINNED_BAT603_UNION_IDENTITY)
        self.assertEqual(bat603["gate_identity"], PINNED_BAT603_GATE_IDENTITY)
        self.assertEqual(bat602["union_identity"], PINNED_BAT602_UNION_IDENTITY)
        self.assertEqual(bat602["gate_identity"], PINNED_BAT602_GATE_IDENTITY)
        self.assertEqual(bat605["gate_identity"], PINNED_BAT605_GATE_IDENTITY)
        self.assertEqual(bat605["dataset_identity"], PINNED_BAT605_DATASET_IDENTITY)
        self.assertEqual(
            bat605["acquisition_identity"], PINNED_BAT605_ACQUISITION_IDENTITY
        )
        self.assertEqual(bat605["games_identity"], PINNED_BAT605_GAMES_IDENTITY)
        self.assertEqual(bat606["payload_identity"], PINNED_BAT606_PAYLOAD_IDENTITY)
        self.assertEqual(bat606["gate_identity"], PINNED_BAT606_GATE_IDENTITY)
        self.assertEqual(bat604["gate_identity"], PINNED_BAT604_GATE_IDENTITY)

    def test_parent_url_fallback_is_forbidden(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "parent_url missing"):
            compact_official_2004(
                {"url": "https://example.invalid/box"}, OFFICIAL_2004_INDEX_URL
            )
        with self.assertRaisesRegex(AuthorityViolation, "does not match BAT-604"):
            compact_official_2004(
                {
                    "url": "https://example.invalid/box",
                    "parent_url": "https://files.12thman.com/history/football/years/2005.html",
                    "source_season": 2004,
                    "football_season": 2004,
                },
                OFFICIAL_2004_INDEX_URL,
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
        admissions = _copy(self.gate["admissions"])
        admissions["bat_429"] = "DONE_VERIFIED"
        with self.assertRaisesRegex(AuthorityViolation, "BAT-429"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, admissions=admissions),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-605/BAT-606 payloads are not mounted")
class Expanded2004ReconstructionAndTamperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.bat605 = _copy(self.objects["bat605"]["payload"])
        self.bat606 = _copy(self.objects["bat606"]["payload"])

    def test_committed_gate_reconstructs(self) -> None:
        result = contained_reconstruction(
            self,
            repo_root=REPO_ROOT,
            gate_relative=GATE_RELATIVE,
            call=lambda: validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
            ),
        )
        if result is None:
            return
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["counts"]["new_games_added"], 12)
        self.assertEqual(result["counts"]["union_captured_games"], 273)
        self.assertEqual(
            result["recomputed_upstream"]["bat605_dataset_identity"],
            PINNED_BAT605_DATASET_IDENTITY,
        )
        self.assertEqual(
            result["recomputed_upstream"]["bat606_payload_identity"],
            PINNED_BAT606_PAYLOAD_IDENTITY,
        )
        gate = load_json(REPO_ROOT / GATE_RELATIVE)
        self.assertEqual(result["gate_identity"], gate["gate_identity"])
        self.assertEqual(result["union_identity"], gate["union_identity"])

    def test_bat605_identity_recompute_matches_pins(self) -> None:
        recomputed = recompute_bat605_identities(self.bat605)
        self.assertEqual(recomputed["dataset_identity"], PINNED_BAT605_DATASET_IDENTITY)
        self.assertEqual(
            recomputed["acquisition_identity"], PINNED_BAT605_ACQUISITION_IDENTITY
        )
        self.assertEqual(recomputed["games_identity"], PINNED_BAT605_GAMES_IDENTITY)
        validated = validate_bat605_external_payload(
            repo_root=REPO_ROOT, data_root=DATA_ROOT
        )
        self.assertEqual(validated["identities"], recomputed)
        self.assertTrue(
            all(
                game["parent_url"] == OFFICIAL_2004_INDEX_URL
                for game in validated["games"]
            )
        )

    def test_bat606_row_counts_recompute_from_serialized_rows(self) -> None:
        validated = validate_bat606_external_payload(
            repo_root=REPO_ROOT, data_root=DATA_ROOT
        )
        self.assertEqual(validated["payload_identity"], PINNED_BAT606_PAYLOAD_IDENTITY)
        total_rows = 0
        for game in validated["games"].values():
            counts = game["row_counts"]
            self.assertGreater(sum(counts.values()), 0)
            total_rows += sum(counts.values())
            for domain, flag in game["domain_coverage"].items():
                if domain in counts and flag == "PRESENT":
                    self.assertGreater(counts[domain], 0)
        self.assertEqual(total_rows, 5747)

    def test_bat605_opponent_score_sha_parent_and_membership_tampers_fail(self) -> None:
        opponent = _copy(self.bat605)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=opponent
            )
        score = _copy(self.bat605)
        score["games"][0]["tamu_points"] = 99
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=score
            )
        sha = _copy(self.bat605)
        sha["games"][0]["source_sha256"] = "0" * 64
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=sha
            )
        missing = _copy(self.bat605)
        missing["games"][0].pop("parent_url", None)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=missing
            )
        substituted = _copy(self.bat605)
        substituted["games"][0]["parent_url"] = (
            "https://files.12thman.com/history/football/years/2005.html"
        )
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=substituted
            )
        captures = _copy(self.bat605)
        captures["captures"] = captures["captures"][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=captures
            )
        name_only = _copy(self.bat605)
        name_only["games"][0]["canonical_game_match_status"] = (
            "MATCHED_OPPONENT_NAME_ONLY"
        )
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat605_payload=name_only
            )

    def test_bat606_row_and_coverage_tampers_fail(self) -> None:
        changed = _copy(self.bat606)
        if changed["rows"][0]:
            changed["rows"][0][0]["cells"] = ["FORGED"]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=changed
            )
        removed = _copy(self.bat606)
        removed["rows"][0] = removed["rows"][0][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=removed
            )
        added = _copy(self.bat606)
        extra = (
            _copy(added["rows"][0][0])
            if added["rows"][0]
            else {"domain": "team_statistics"}
        )
        added["rows"][0] = list(added["rows"][0]) + [extra]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=added
            )
        present_zero = _copy(self.bat606)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=present_zero
            )
        parser = _copy(self.bat606)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=parser
            )
        availability = _copy(self.bat606)
        availability["availability_claim"] = True
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=availability
            )
        compact = _copy(
            load_json(
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2004_structured_domains_gate.json"
            )["games"]
        )
        compact[0]["row_counts"]["team_statistics"] = (
            int(compact[0]["row_counts"]["team_statistics"]) + 1
        )
        with self.assertRaises(AuthorityViolation):
            validate_bat606_external_payload(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                payload=self.bat606,
                compact_games=compact,
            )

    def test_coordinated_tamper_plus_recomputed_outer_identity_fails(self) -> None:
        bat605 = _copy(self.bat605)
        bat605["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        bat605.update(recompute_bat605_identities(bat605))
        bat606 = _copy(self.bat606)
        if bat606["rows"][0]:
            bat606["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        bat606["payload_identity"] = recompute_bat606_payload_identity(bat606)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                bat605_payload=bat605,
                bat606_payload=bat606,
            )


if __name__ == "__main__":
    unittest.main()
