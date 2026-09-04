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

from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (  # noqa: E402
    HARDCODED_PARENT_FALLBACK,
    OFFICIAL_2005_EXPECTED,
    PINNED_BAT600_ACQUISITION_IDENTITY,
    PINNED_BAT600_DATASET_IDENTITY,
    PINNED_BAT600_GAMES_IDENTITY,
    PINNED_BAT600_GATE_IDENTITY,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    PRESERVED_REJECTION_URLS,
    PRIOR_UNION_CAPTURED_GAMES,
    VALIDATION_CONTRACT_VERSION,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2005,
    compute_gate_identity,
    lake_is_ready,
    load_json,
    reconstruct_objects,
    recompute_bat600_identities,
    recompute_bat601_payload_identity,
    validate_artifact,
    validate_bat600_external_payload,
    validate_bat601_external_payload,
)
from aggie_analytics.data.tamu_official_2005_boxscores import (  # noqa: E402
    OFFICIAL_2005_INDEX_URL,
)


DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(
    DATA_ROOT
)
EXPECTED_GATE_IDENTITY = (
    "ad6d5a15a7b70350f109cd55f3f91e2e01e91a8b924451698b313031b65a5580"
)
EXPECTED_UNION_IDENTITY = (
    "51b668f1be25ac3768dee68f409fa93d58873e55d3e6c0d6930f061dd030f459"
)


def _copy(value):
    return json.loads(json.dumps(value))


def _mutated(gate: dict, **changes):
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class CompactIntegrityBoundUnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2005 integrity-bound union gate not materialized yet")
        self.gate = load_json(path)

    def test_committed_counts_predecessor_and_no_new_games(self) -> None:
        self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(
            self.gate["predecessor_union_identity"], PINNED_BAT602_UNION_IDENTITY
        )
        self.assertEqual(
            self.gate["predecessor_gate_identity"], PINNED_BAT602_GATE_IDENTITY
        )
        self.assertEqual(
            self.gate["validation_contract_version"], VALIDATION_CONTRACT_VERSION
        )
        self.assertEqual(self.gate["counts"]["new_games_added"], 0)
        self.assertEqual(self.gate["counts"]["official_2005_added"], 0)
        self.assertEqual(
            self.gate["counts"]["official_2005_preserved"], OFFICIAL_2005_EXPECTED
        )
        self.assertEqual(
            self.gate["counts"]["official_2005_revalidated"], OFFICIAL_2005_EXPECTED
        )
        self.assertEqual(
            self.gate["counts"]["prior_261_union_games_preserved"],
            PRIOR_UNION_CAPTURED_GAMES,
        )
        self.assertEqual(self.gate["counts"]["union_captured_games"], 261)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 248)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["scoring_summary_present_games"], 58)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["date_conflicts"], 4)
        self.assertEqual(self.gate["counts"]["season_header_conflicts"], 1)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(
            self.gate["upstream_identities"]["bat602_union_identity"],
            PINNED_BAT602_UNION_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat600_dataset_identity"],
            PINNED_BAT600_DATASET_IDENTITY,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat601_payload_identity"],
            PINNED_BAT601_PAYLOAD_IDENTITY,
        )
        self.assertEqual(
            self.gate["recomputed_upstream"]["bat600_dataset_identity"],
            PINNED_BAT600_DATASET_IDENTITY,
        )
        self.assertEqual(
            self.gate["recomputed_upstream"]["bat601_payload_identity"],
            PINNED_BAT601_PAYLOAD_IDENTITY,
        )
        self.assertTrue(self.gate["recomputed_upstream"]["validator_code_identity"])
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertEqual(len(self.gate["admitted_official_2005_games"]), 11)
        self.assertTrue(
            all(
                item.get("parent_url") == OFFICIAL_2005_INDEX_URL
                for item in self.gate["admitted_official_2005_games"]
            )
        )
        self.assertTrue(
            all(
                item.get("structured_row_payload_identity")
                == PINNED_BAT601_PAYLOAD_IDENTITY
                for item in self.gate["admitted_official_2005_games"]
            )
        )
        self.assertTrue(
            all(
                item.get("availability") == "NOT_ESTABLISHED"
                for item in self.gate["admitted_official_2005_games"]
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
        self.assertFalse(
            self.gate["scientific_nonclaims"]["new_historical_coverage_claimed"]
        )
        self.assertFalse(self.gate["authority"]["hardcoded_parent_url_fallback"])
        self.assertFalse(
            self.gate["authority"]["trusted_declared_upstream_identity_only"]
        )

    def test_prior_identities_are_not_rewritten(self) -> None:
        bat602 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_gamebook_union_2005_expanded_gate.json"
        )
        bat600 = load_json(
            REPO_ROOT / "artifacts/data_lake/tamu_official_2005_boxscore_gate.json"
        )
        bat601 = load_json(
            REPO_ROOT
            / "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json"
        )
        self.assertEqual(bat602["union_identity"], PINNED_BAT602_UNION_IDENTITY)
        self.assertEqual(bat602["gate_identity"], PINNED_BAT602_GATE_IDENTITY)
        self.assertEqual(bat600["gate_identity"], PINNED_BAT600_GATE_IDENTITY)
        self.assertEqual(bat600["dataset_identity"], PINNED_BAT600_DATASET_IDENTITY)
        self.assertEqual(
            bat600["acquisition_identity"], PINNED_BAT600_ACQUISITION_IDENTITY
        )
        self.assertEqual(bat600["games_identity"], PINNED_BAT600_GAMES_IDENTITY)
        self.assertEqual(bat601["payload_identity"], PINNED_BAT601_PAYLOAD_IDENTITY)

    def test_parent_url_fallback_is_forbidden(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "parent_url missing"):
            compact_official_2005(
                {"url": "https://example.invalid/box"}, OFFICIAL_2005_INDEX_URL
            )
        with self.assertRaisesRegex(AuthorityViolation, "does not match BAT-599"):
            compact_official_2005(
                {
                    "url": "https://example.invalid/box",
                    "parent_url": "https://files.12thman.com/history/football/years/2004.html",
                },
                OFFICIAL_2005_INDEX_URL,
            )
        self.assertEqual(HARDCODED_PARENT_FALLBACK, OFFICIAL_2005_INDEX_URL)

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

    def test_ncaa_id_and_rejected_url_fail(self) -> None:
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


@unittest.skipUnless(LAKE_READY, "external BAT-600/BAT-601 payloads are not mounted")
class IntegrityBoundReconstructionAndTamperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.objects = contained_reconstruction(
            self,
            repo_root=REPO_ROOT,
            gate_relative=GATE_RELATIVE,
            call=lambda: reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT),
        )
        self.predecessor_contained = self.objects is None
        if self.predecessor_contained:
            self.bat600 = None
            self.bat601 = None
            return
        self.bat600 = _copy(self.objects["bat600"]["payload"])
        self.bat601 = _copy(self.objects["bat601"]["payload"])

    def test_committed_gate_reconstructs(self) -> None:
        if self.predecessor_contained:
            return
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
        self.assertEqual(result["counts"]["new_games_added"], 0)
        self.assertEqual(result["counts"]["union_captured_games"], 261)
        self.assertEqual(
            result["recomputed_upstream"]["bat600_dataset_identity"],
            PINNED_BAT600_DATASET_IDENTITY,
        )
        self.assertEqual(
            result["recomputed_upstream"]["bat601_payload_identity"],
            PINNED_BAT601_PAYLOAD_IDENTITY,
        )
        gate = load_json(REPO_ROOT / GATE_RELATIVE)
        self.assertEqual(result["gate_identity"], gate["gate_identity"])
        self.assertEqual(result["union_identity"], gate["union_identity"])

    def test_bat600_identity_recompute_matches_pins(self) -> None:
        if self.predecessor_contained:
            return
        recomputed = recompute_bat600_identities(self.bat600)
        self.assertEqual(recomputed["dataset_identity"], PINNED_BAT600_DATASET_IDENTITY)
        self.assertEqual(
            recomputed["acquisition_identity"], PINNED_BAT600_ACQUISITION_IDENTITY
        )
        self.assertEqual(recomputed["games_identity"], PINNED_BAT600_GAMES_IDENTITY)
        validated = validate_bat600_external_payload(
            repo_root=REPO_ROOT, data_root=DATA_ROOT
        )
        self.assertEqual(validated["identities"], recomputed)
        self.assertTrue(
            all(
                game["parent_url"] == OFFICIAL_2005_INDEX_URL
                for game in validated["games"]
            )
        )

    def test_bat601_row_counts_recompute_from_serialized_rows(self) -> None:
        if self.predecessor_contained:
            return
        validated = validate_bat601_external_payload(
            repo_root=REPO_ROOT, data_root=DATA_ROOT
        )
        self.assertEqual(validated["payload_identity"], PINNED_BAT601_PAYLOAD_IDENTITY)
        total_rows = 0
        for game in validated["games"].values():
            counts = game["row_counts"]
            self.assertGreater(sum(counts.values()), 0)
            total_rows += sum(counts.values())
            for domain, flag in game["domain_coverage"].items():
                if domain in counts and flag == "PRESENT":
                    self.assertGreater(counts[domain], 0)
        self.assertGreater(total_rows, 0)

    def test_bat600_opponent_score_sha_parent_and_membership_tampers_fail(self) -> None:
        if self.predecessor_contained:
            return
        opponent = _copy(self.bat600)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=opponent
            )
        score = _copy(self.bat600)
        score["games"][0]["tamu_points"] = 99
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=score
            )
        sha = _copy(self.bat600)
        sha["games"][0]["source_sha256"] = "0" * 64
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=sha
            )
        missing = _copy(self.bat600)
        missing["games"][0].pop("parent_url", None)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=missing
            )
        substituted = _copy(self.bat600)
        substituted["games"][0]["parent_url"] = (
            "https://files.12thman.com/history/football/years/2004.html"
        )
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=substituted
            )
        captures = _copy(self.bat600)
        captures["captures"] = captures["captures"][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=captures
            )
        conflicts = _copy(self.bat600)
        conflicts["conflicts"] = conflicts["conflicts"][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat600_payload=conflicts
            )

    def test_bat601_row_and_coverage_tampers_fail(self) -> None:
        if self.predecessor_contained:
            return
        changed = _copy(self.bat601)
        if changed["rows"][0]:
            changed["rows"][0][0]["cells"] = ["FORGED"]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat601_payload=changed
            )
        removed = _copy(self.bat601)
        removed["rows"][0] = removed["rows"][0][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat601_payload=removed
            )
        added = _copy(self.bat601)
        extra = (
            _copy(added["rows"][0][0])
            if added["rows"][0]
            else {"domain": "team_statistics"}
        )
        added["rows"][0] = list(added["rows"][0]) + [extra]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat601_payload=added
            )
        present_zero = _copy(self.bat601)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat601_payload=present_zero
            )
        parser = _copy(self.bat601)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat601_payload=parser
            )
        availability = _copy(self.bat601)
        availability["availability_claim"] = True
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, bat601_payload=availability
            )
        compact = _copy(
            load_json(
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json"
            )["games"]
        )
        compact[0]["row_counts"]["team_statistics"] = (
            int(compact[0]["row_counts"]["team_statistics"]) + 1
        )
        with self.assertRaises(AuthorityViolation):
            validate_bat601_external_payload(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                payload=self.bat601,
                compact_games=compact,
            )

    def test_coordinated_tamper_plus_recomputed_outer_identity_fails(self) -> None:
        if self.predecessor_contained:
            return
        bat600 = _copy(self.bat600)
        bat600["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        bat600.update(recompute_bat600_identities(bat600))
        bat601 = _copy(self.bat601)
        if bat601["rows"][0]:
            bat601["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        bat601["payload_identity"] = recompute_bat601_payload_identity(bat601)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                bat600_payload=bat600,
                bat601_payload=bat601,
            )


if __name__ == "__main__":
    unittest.main()
