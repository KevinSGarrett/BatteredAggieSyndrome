from __future__ import annotations

import json
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2004_expanded import (  # noqa: E402
    PINNED_UNION_IDENTITY as PINNED_BAT607_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT607_UNION_MANIFEST_FILE_SHA256,
    union_manifest_path as bat607_union_manifest_path,
    validate_artifact as validate_bat607,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (  # noqa: E402
    PINNED_UNION_IDENTITY as PINNED_BAT603_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT603_UNION_MANIFEST_FILE_SHA256,
    union_manifest_path as bat603_union_manifest_path,
    validate_artifact as validate_bat603,
)
from aggie_analytics.data.tamu_official_gamebook_union_integrity_complete import (  # noqa: E402
    OFFICIAL_2004_EXPECTED,
    PINNED_BAT603_GATE_IDENTITY,
    PINNED_BAT606_PAYLOAD_IDENTITY,
    PINNED_BAT607_GATE_IDENTITY,
    PRESERVED_REJECTION_URLS,
    PRIOR_UNION_CAPTURED_GAMES,
    VALIDATION_CONTRACT_VERSION,
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    lake_is_ready,
    load_json,
    recompute_bat606_payload_identity,
    reconstruct_objects,
    union_manifest_path,
    upstream_is_ready,
    validate_artifact,
    write_json,
)


DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = upstream_is_ready(DATA_ROOT)
EXPECTED_GATE_IDENTITY = "f8866261d2d6fbf971a85e5ef9cf393d7b4546332dd57153ed5a7e50e9946b9f"
EXPECTED_UNION_IDENTITY = "5743e4d47a14fda8dab4e14796d89d704dd70807628a421a7dc6e6f7d271f2fd"


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _mutated(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


@contextmanager
def _temporarily_moved(path: Path) -> Iterator[None]:
    hidden = path.with_name(path.name + ".hidden_cycle15")
    if hidden.exists():
        hidden.unlink()
    path.replace(hidden)
    try:
        yield
    finally:
        if path.exists():
            path.unlink()
        hidden.replace(path)


@contextmanager
def _temporarily_written(path: Path, payload: Any) -> Iterator[None]:
    original = path.read_bytes()
    write_json(path, payload)
    try:
        yield
    finally:
        path.write_bytes(original)


class CompactIntegrityCompleteUnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("integrity-complete union gate not materialized yet")
        self.gate = load_json(path)

    def test_committed_counts_predecessor_and_no_new_games(self) -> None:
        if EXPECTED_GATE_IDENTITY.startswith("PLACEHOLDER"):
            self.assertEqual(len(self.gate["gate_identity"]), 64)
            self.assertEqual(len(self.gate["union_identity"]), 64)
        else:
            self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
            self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(self.gate["predecessor_union_identity"], PINNED_BAT607_UNION_IDENTITY)
        self.assertEqual(self.gate["predecessor_gate_identity"], PINNED_BAT607_GATE_IDENTITY)
        self.assertEqual(self.gate["validation_contract_version"], VALIDATION_CONTRACT_VERSION)
        self.assertEqual(self.gate["counts"]["new_games_added"], 0)
        self.assertEqual(self.gate["counts"]["official_2004_added"], 0)
        self.assertEqual(self.gate["counts"]["official_2004_preserved"], OFFICIAL_2004_EXPECTED)
        self.assertEqual(self.gate["counts"]["predecessor_273_union_games_preserved"], PRIOR_UNION_CAPTURED_GAMES)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 273)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 260)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["scoring_summary_present_games"], 70)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(len(self.gate["enriched_official_games"]), 70)
        self.assertEqual(len(self.gate["admitted_official_2004_games"]), 12)
        self.assertEqual(self.gate["upstream_identities"]["bat603_union_identity"], PINNED_BAT603_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat603_gate_identity"], PINNED_BAT603_GATE_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat607_union_identity"], PINNED_BAT607_UNION_IDENTITY)
        self.assertEqual(
            self.gate["upstream_identities"]["bat603_union_manifest_file_sha256"],
            PINNED_BAT603_UNION_MANIFEST_FILE_SHA256,
        )
        self.assertEqual(
            self.gate["upstream_identities"]["bat607_union_manifest_file_sha256"],
            PINNED_BAT607_UNION_MANIFEST_FILE_SHA256,
        )
        self.assertEqual(self.gate["recomputed_upstream"]["bat606_payload_identity"], PINNED_BAT606_PAYLOAD_IDENTITY)
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertTrue(
            all(item.get("availability") in {None, "NOT_ESTABLISHED"} for item in self.gate["enriched_official_games"])
        )
        self.assertTrue(all(item.get("availability") == "NOT_ESTABLISHED" for item in self.gate["admitted_official_2004_games"]))
        self.assertFalse(any(item.get("availability_claim") for item in self.gate["enriched_official_games"]))
        self.assertFalse(any(item.get("ncaa_contest_id") for item in self.gate["enriched_official_games"]))
        self.assertEqual(self.gate["admissions"]["bat_429"], "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES")
        self.assertEqual(self.gate["admissions"]["bat_523"], "IN_PROGRESS")
        self.assertEqual(self.gate["admissions"]["gap_005"], "OPEN")
        self.assertEqual(self.gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertFalse(self.gate["authority"]["trusted_declared_upstream_identity_only"])
        self.assertEqual(self.gate["selected_seasons"], [2009, 2008, 2007, 2006, 2005, 2004])

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

    def test_ncaa_id_rejected_url_and_availability_fail(self) -> None:
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
        admissions["pregame_availability"] = "OPEN"
        with self.assertRaisesRegex(AuthorityViolation, "availability"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, admissions=admissions),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-605/BAT-606 payloads are not mounted")
class IntegrityCompleteReconstructionAndTamperTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("integrity-complete union gate not materialized yet")
        self.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.bat606 = _copy(self.objects["bat606"]["payload"])

    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["counts"]["new_games_added"], 0)
        self.assertEqual(result["counts"]["union_captured_games"], 273)
        self.assertEqual(result["recomputed_upstream"]["bat606_payload_identity"], PINNED_BAT606_PAYLOAD_IDENTITY)
        self.assertEqual(result["recomputed_upstream"]["bat603_union_manifest_file_sha256"], PINNED_BAT603_UNION_MANIFEST_FILE_SHA256)
        self.assertEqual(result["recomputed_upstream"]["bat607_union_manifest_file_sha256"], PINNED_BAT607_UNION_MANIFEST_FILE_SHA256)
        self.assertTrue(lake_is_ready(DATA_ROOT))

    def test_missing_predecessor_union_manifests_fail_closed(self) -> None:
        with _temporarily_moved(bat603_union_manifest_path(DATA_ROOT)):
            with self.assertRaisesRegex(AuthorityViolation, "union manifest is missing"):
                validate_bat603(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        with _temporarily_moved(bat607_union_manifest_path(DATA_ROOT)):
            with self.assertRaisesRegex(AuthorityViolation, "union manifest is missing"):
                validate_bat607(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)

    def test_substituted_and_altered_union_manifests_fail_closed(self) -> None:
        path = bat607_union_manifest_path(DATA_ROOT)
        substituted = _copy(load_json(path))
        substituted["counts"]["new_games_added"] = 99
        with _temporarily_written(path, substituted):
            with self.assertRaises(AuthorityViolation):
                validate_bat607(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        altered = _copy(load_json(path))
        altered["enriched_official_games"][0]["opponent_candidate"] = "ALTERED WHILE IDENTITY UNCHANGED"
        with _temporarily_written(path, altered):
            with self.assertRaises(AuthorityViolation):
                validate_bat607(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)

    def test_extra_union_manifest_fails_closed(self) -> None:
        extra = bat607_union_manifest_path(DATA_ROOT).with_name("extra_manifest.json")
        extra.write_text("{}\n", encoding="utf-8")
        try:
            with self.assertRaisesRegex(AuthorityViolation, "extra union manifests"):
                validate_bat607(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        finally:
            if extra.exists():
                extra.unlink()

    def test_missing_successor_union_manifest_fails_closed(self) -> None:
        gate = load_json(REPO_ROOT / GATE_RELATIVE)
        path = union_manifest_path(DATA_ROOT, str(gate["union_identity"]))
        with _temporarily_moved(path):
            with self.assertRaisesRegex(AuthorityViolation, "union manifest is missing"):
                validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)

    def test_bat606_row_tampers_fail_against_raw_reconstruction(self) -> None:
        sha = _copy(self.bat606)
        if sha["rows"][0]:
            sha["rows"][0][0]["source_sha256"] = "0" * 64
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=sha)
        season = _copy(self.bat606)
        season["games"][0]["source_season"] = 1999
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=season)
        parser = _copy(self.bat606)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=parser)
        domain = _copy(self.bat606)
        if domain["rows"][0]:
            domain["rows"][0][0]["domain"] = "forged_domain"
            domain["rows"][0][0]["source_domain"] = "forged_domain"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=domain)
        duplicate = _copy(self.bat606)
        if duplicate["rows"][0]:
            duplicate["rows"][0] = list(duplicate["rows"][0]) + [_copy(duplicate["rows"][0][0])]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=duplicate)
        gapped = _copy(self.bat606)
        if gapped["rows"][0]:
            gapped["rows"][0] = gapped["rows"][0][1:]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=gapped)
        present_zero = _copy(self.bat606)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=present_zero)
        warnings = _copy(self.bat606)
        warnings["games"][0]["warnings"] = ["forged warning"]
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=warnings)

    def test_coordinated_bat606_and_outer_rehash_fail(self) -> None:
        coordinated = _copy(self.bat606)
        if coordinated["rows"][0]:
            coordinated["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        coordinated["payload_identity"] = recompute_bat606_payload_identity(coordinated)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, bat606_payload=coordinated)
        gate = load_json(REPO_ROOT / GATE_RELATIVE)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(gate, union_identity="0" * 64),
                require_rebuild=True,
                bat606_payload=coordinated,
            )


if __name__ == "__main__":
    unittest.main()
