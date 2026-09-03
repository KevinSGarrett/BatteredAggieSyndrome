from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash  # noqa: E402
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import (  # noqa: E402
    _row_identity_payload,
)
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus_integrity import (  # noqa: E402
    CHILD_DOMAINS,
    CHILD_FILENAMES,
    CODE_BUNDLE_RELATIVE,
    EXPECTED_GAMES,
    EXPECTED_SERIALIZED_ROWS,
    FORBIDDEN_URLS,
    GATE_RELATIVE,
    MANIFEST_NAME,
    MODULE_RELATIVE,
    PINNED_BAT618_UNION_IDENTITY,
    PINNED_BAT619_DATASET_IDENTITY,
    PREFORMATTED_PARSER_IDENTITY,
    AuthorityViolation,
    bind_corpus_row,
    compute_code_identity,
    compute_gate_identity,
    consume_corpus,
    corpus_dir,
    lake_is_ready,
    load_json,
    load_raw_validated_upstream_payloads,
    predecessor_root,
    reconstruct_objects,
    serialize_jsonl,
    validate_artifact,
    write_json,
)
from aggie_analytics.data.tamu_official_gamebook_union_2002_expanded import (  # noqa: E402
    OKLAHOMA_2002_UNMATCHED_URL,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (  # noqa: E402
    PRESERVED_REJECTION_URLS,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
    availability_from_participation,
    refuse_name_only_player_merge,
)
from aggie_analytics.validation.artifact_binding import compute_identity  # noqa: E402


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT, REPO_ROOT)


def _copy(value):
    return json.loads(json.dumps(value))


def _mutated_gate(gate: dict, **changes) -> dict:
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def _source() -> dict:
    return {
        "jira_key": "BAT-617",
        "payload_identity": "0a2e8e6c510f4d935e8cd6e04f7741491856f46f608e47d62c42f73fab6d4697",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": "aggie.data.tamu_official_2002_structured_domains.v1",
    }


class OfficialRowCorpusIntegrityUnitTests(unittest.TestCase):
    def test_player_name_merge_is_refused(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "name-only player merge"):
            refuse_name_only_player_merge([{"name_raw": "D. Crawford"}, {"name_raw": "D. Crawford"}])

    def test_participation_does_not_become_availability(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "participation does not establish availability"):
            availability_from_participation({"name_raw": "D. Crawford", "availability": "NOT_ESTABLISHED"})

    def test_forbidden_urls_include_oklahoma_and_preserved_rejections(self) -> None:
        self.assertIn(OKLAHOMA_2002_UNMATCHED_URL, FORBIDDEN_URLS)
        self.assertTrue(PRESERVED_REJECTION_URLS <= FORBIDDEN_URLS)

    def test_code_identity_hashes_enumerated_bundle_and_is_not_a_literal(self) -> None:
        identity = compute_code_identity(REPO_ROOT)
        hasher = hashlib.sha256()
        hasher.update(b"aggie.integrity.code_bundle.v1\n")
        for relative in CODE_BUNDLE_RELATIVE:
            path = REPO_ROOT / relative
            hasher.update(b"PATH:")
            hasher.update(relative.replace("\\", "/").encode("utf-8"))
            hasher.update(b"\n")
            hasher.update(path.read_bytes())
            hasher.update(b"\n")
        self.assertEqual(identity, hasher.hexdigest())
        source = (REPO_ROOT / MODULE_RELATIVE).read_text(encoding="utf-8")
        start = source.index("def compute_code_identity")
        end = source.index("\ndef ", start + 1)
        function_source = source[start:end]
        self.assertIn("hasher.update(path.read_bytes())", function_source)
        self.assertNotIn('return "abaad66cbc05c9f98d8388e42e3195164458391b2458d9a79491f8ca0b2636c8"', function_source)
        self.assertNotEqual(identity, "abaad66cbc05c9f98d8388e42e3195164458391b2458d9a79491f8ca0b2636c8")

    def test_missing_upstream_provenance_is_rejected(self) -> None:
        raw = {"domain": "drives", "row_order": 0, "parser_identity": PREFORMATTED_PARSER_IDENTITY}
        with self.assertRaisesRegex(AuthorityViolation, "missing upstream provenance"):
            bind_corpus_row(
                raw,
                union_game={
                    "url": "https://files.12thman.com/history/football/stats/2002-2003/example.htm",
                    "source_sha256": "a" * 64,
                    "football_season": 2002,
                },
                payload_game={"url": "https://files.12thman.com/history/football/stats/2002-2003/example.htm"},
                source=_source(),
                payload_identity=_source()["payload_identity"],
                domain_row_order=0,
            )

    def test_unauthorized_parser_default_is_rejected(self) -> None:
        source = _source()
        source["schema_authorizes_parser_default"] = False
        raw = {
            "domain": "drives",
            "row_order": 0,
            "source_url": "https://files.12thman.com/history/football/stats/2002-2003/example.htm",
            "source_sha256": "a" * 64,
        }
        with self.assertRaisesRegex(AuthorityViolation, "upstream parser/default change"):
            bind_corpus_row(
                raw,
                union_game={
                    "url": "https://files.12thman.com/history/football/stats/2002-2003/example.htm",
                    "source_sha256": "a" * 64,
                    "football_season": 2002,
                },
                payload_game={"url": raw["source_url"]},
                source=source,
                payload_identity=source["payload_identity"],
                domain_row_order=0,
            )

    def test_unmounted_data_root_validates_compact_gate_only(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("integrity-complete row-corpus gate not materialized yet")
        empty = Path(tempfile.mkdtemp(prefix="bat620-empty-"))
        result = validate_artifact(repo_root=REPO_ROOT, data_root=empty, require_rebuild=False)
        self.assertEqual(result["external_reconstruction"], "NOT_MOUNTED")
        with self.assertRaisesRegex(AuthorityViolation, "data root is not mounted"):
            validate_artifact(repo_root=REPO_ROOT, data_root=empty, require_rebuild=True)


@unittest.skipUnless(LAKE_READY, "mounted raw upstreams, BAT-618 union, and BAT-619 corpus are required")
class OfficialRowCorpusIntegrityMaterialTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("integrity-complete row-corpus gate not materialized yet")
        self.gate = load_json(path)
        self.dataset_identity = str(self.gate["dataset_identity"])
        self.corpus_root = corpus_dir(DATA_ROOT, self.dataset_identity)
        self.manifest = load_json(self.corpus_root / MANIFEST_NAME)
        self._tmp = Path(tempfile.mkdtemp(prefix="bat620-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _stage(self) -> Path:
        dest = self._tmp / "corpus"
        shutil.copytree(self.corpus_root, dest)
        return dest

    def _stage_predecessor(self) -> Path:
        dest = self._tmp / "predecessor"
        shutil.copytree(predecessor_root(DATA_ROOT), dest)
        return dest

    def _reseal(self, row: dict) -> dict:
        updated = _copy(row)
        updated["row_identity"] = stable_hash(_row_identity_payload(updated))
        return updated

    def _rewrite_child(self, staged: Path, domain: str, rows: list[dict]) -> None:
        payload = serialize_jsonl(rows)
        (staged / CHILD_FILENAMES[domain]).write_bytes(payload)
        manifest = load_json(staged / MANIFEST_NAME)
        manifest["child_payloads"][domain]["sha256"] = hashlib.sha256(payload).hexdigest()
        manifest["child_payloads"][domain]["row_count"] = len(rows)
        write_json(staged / MANIFEST_NAME, manifest)

    def test_reconstruct_matches_committed_gate_and_preserves_bat619_counts(self) -> None:
        reconstructed = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        validated = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(reconstructed["gate"]["gate_identity"], self.gate["gate_identity"])
        self.assertEqual(validated["dataset_identity"], self.dataset_identity)
        self.assertEqual(self.gate["union_identity"], PINNED_BAT618_UNION_IDENTITY)
        self.assertEqual(self.gate["predecessor_dataset_identity"], PINNED_BAT619_DATASET_IDENTITY)
        self.assertEqual(self.gate["counts"]["games"], EXPECTED_GAMES)
        self.assertEqual(self.gate["counts"]["serialized_rows_total"], EXPECTED_SERIALIZED_ROWS)
        self.assertEqual(self.gate["counts"]["scoring_summary_serialized_rows"], 0)
        self.assertFalse(self.gate["scientific_nonclaims"]["predecessor_rows_declared_invalid"])
        self.assertNotEqual(self.gate["validator_code_identity"], "abaad66cbc05c9f98d8388e42e3195164458391b2458d9a79491f8ca0b2636c8")
        consumed = consume_corpus(data_root=DATA_ROOT, dataset_identity=self.dataset_identity)
        self.assertEqual(consumed["scoring_summary"], [])
        for domain in CHILD_DOMAINS:
            self.assertIn(domain, consumed)

    def test_coordinated_upstream_payload_identity_file_hash_mutation(self) -> None:
        loaded_payloads = load_raw_validated_upstream_payloads(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        tampered = _copy(loaded_payloads[0]["payload"])
        tampered["games"][0]["warnings"] = list(tampered["games"][0].get("warnings") or []) + ["TAMPER"]
        tampered["payload_identity"] = compute_identity(tampered, "payload_identity")
        with self.assertRaisesRegex(AuthorityViolation, "raw capture mismatch"):
            reconstruct_objects(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                stored_overrides={"BAT-591": tampered},
                skip_upstream_validators=True,
            )

    def test_raw_capture_mismatch(self) -> None:
        loaded_payloads = load_raw_validated_upstream_payloads(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        tampered = _copy(loaded_payloads[0]["payload"])
        tampered["schema_version"] = "tampered.schema"
        with self.assertRaisesRegex(AuthorityViolation, "raw capture mismatch"):
            reconstruct_objects(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                stored_overrides={loaded_payloads[0]["source"]["jira_key"]: tampered},
                skip_upstream_validators=True,
            )

    def test_changed_code_with_stale_code_identity(self) -> None:
        with mock.patch(
            "aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus_integrity.compute_code_identity",
            return_value="0" * 64,
        ):
            with self.assertRaisesRegex(AuthorityViolation, "stale code identity"):
                reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT, skip_upstream_validators=True)

    def test_missing_predecessor_manifest(self) -> None:
        empty = self._tmp / "missing-predecessor"
        empty.mkdir()
        with self.assertRaisesRegex(AuthorityViolation, "missing predecessor manifest"):
            reconstruct_objects(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                predecessor_root_override=empty,
                skip_upstream_validators=True,
            )

    def test_changed_predecessor_manifest_metadata(self) -> None:
        staged = self._stage_predecessor()
        manifest = load_json(staged / "corpus_manifest.json")
        manifest["counts"] = _copy(manifest["counts"])
        manifest["counts"]["games"] = 1
        write_json(staged / "corpus_manifest.json", manifest)
        with self.assertRaisesRegex(AuthorityViolation, "changed predecessor manifest metadata"):
            reconstruct_objects(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                predecessor_root_override=staged,
                skip_upstream_validators=True,
            )

    def test_changed_child_payload(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["original_text"] = str(first.get("original_text") or "") + " TAMPER"
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
        (staged / CHILD_FILENAMES["team_statistics"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(AuthorityViolation, "unchanged hash declaration"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_changed_coverage_matrix_without_row_change(self) -> None:
        staged = self._stage()
        manifest = load_json(staged / MANIFEST_NAME)
        matrix = _copy(manifest["coverage_matrix"])
        matrix[0]["corpus_coverage"] = "PRESENT"
        matrix[0]["serialized_row_count"] = 99
        manifest["coverage_matrix"] = matrix
        write_json(staged / MANIFEST_NAME, manifest)
        with self.assertRaisesRegex(AuthorityViolation, "changed coverage matrix"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=True,
                skip_upstream_validators=True,
            )

    def test_coordinated_child_and_outer_rehash(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["original_text"] = str(rows[0].get("original_text") or "") + " TAMPER"
        rows[0] = self._reseal(rows[0])
        self._rewrite_child(staged, "team_statistics", rows)
        manifest = load_json(staged / MANIFEST_NAME)
        manifest["dataset_identity"] = "0" * 64
        write_json(staged / MANIFEST_NAME, manifest)
        tampered = _mutated_gate(self.gate, dataset_identity="0" * 64)
        with self.assertRaisesRegex(AuthorityViolation, "coordinated child and outer rehash"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=tampered,
                corpus_root=staged,
                require_rebuild=True,
                skip_upstream_validators=True,
            )

    def test_protected_claim_inserted(self) -> None:
        scientific = _copy(self.gate["scientific_nonclaims"])
        scientific["protected_lane_opened"] = True
        with self.assertRaisesRegex(AuthorityViolation, "protected claim"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated_gate(self.gate, scientific_nonclaims=scientific),
                require_rebuild=False,
            )

    def test_completeness_claim_inserted(self) -> None:
        scientific = _copy(self.gate["scientific_nonclaims"])
        scientific["completeness_claimed"] = True
        with self.assertRaisesRegex(AuthorityViolation, "completeness claim"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated_gate(self.gate, scientific_nonclaims=scientific),
                require_rebuild=False,
            )

    def test_availability_promotion_rejected(self) -> None:
        authority = _copy(self.gate["authority"])
        authority["availability_claim"] = True
        with self.assertRaisesRegex(AuthorityViolation, "participation promoted to availability"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated_gate(self.gate, authority=authority),
                require_rebuild=False,
            )


if __name__ == "__main__":
    unittest.main()
