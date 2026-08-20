from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import (  # noqa: E402
    CHILD_DOMAINS,
    CHILD_FILENAMES,
    FORBIDDEN_URLS,
    GATE_RELATIVE,
    MANIFEST_NAME,
    OKLAHOMA_2002_UNMATCHED_URL,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PINNED_BAT606_PAYLOAD_IDENTITY,
    PINNED_BAT611_PAYLOAD_IDENTITY,
    PINNED_BAT617_PAYLOAD_IDENTITY,
    PINNED_BAT618_UNION_IDENTITY,
    PREFORMATTED_PARSER_IDENTITY,
    SELECTED_SEASONS,
    AuthorityViolation,
    compute_gate_identity,
    consume_corpus,
    corpus_dir,
    lake_is_ready,
    load_json,
    reconstruct_objects,
    serialize_jsonl,
    stable_hash,
    validate_artifact,
    write_json,
    _row_identity_payload,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (  # noqa: E402
    PRESERVED_REJECTION_URLS,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
    availability_from_participation,
    refuse_name_only_player_merge,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT, REPO_ROOT)


def _copy(value):
    return json.loads(json.dumps(value))


def _mutated_gate(gate: dict, **changes) -> dict:
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official20022009RowCorpusUnitTests(unittest.TestCase):
    def test_player_name_merge_is_refused(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "name-only player merge"):
            refuse_name_only_player_merge([{"name_raw": "D. Crawford"}, {"name_raw": "D. Crawford"}])

    def test_participation_does_not_become_availability(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "participation does not establish availability"):
            availability_from_participation({"name_raw": "D. Crawford", "availability": "NOT_ESTABLISHED"})

    def test_forbidden_urls_include_oklahoma_and_preserved_rejections(self) -> None:
        self.assertIn(OKLAHOMA_2002_UNMATCHED_URL, FORBIDDEN_URLS)
        self.assertTrue(PRESERVED_REJECTION_URLS <= FORBIDDEN_URLS)

    def test_selected_seasons_are_2002_through_2009(self) -> None:
        self.assertEqual(tuple(SELECTED_SEASONS), tuple(range(2002, 2010)))


@unittest.skipUnless(LAKE_READY, "mounted 2002-2009 structured payloads and BAT-618 union are required")
class Official20022009RowCorpusMaterialTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2002-2009 structured row-corpus gate not materialized yet")
        self.gate = load_json(path)
        self.dataset_identity = str(self.gate["dataset_identity"])
        self.corpus_root = corpus_dir(DATA_ROOT, self.dataset_identity)
        self.manifest = load_json(self.corpus_root / MANIFEST_NAME)
        self._tmp = Path(tempfile.mkdtemp(prefix="bat619-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _stage(self) -> Path:
        dest = self._tmp / "corpus"
        shutil.copytree(self.corpus_root, dest)
        return dest

    def _rewrite_child(self, staged: Path, domain: str, rows: list[dict]) -> None:
        payload = serialize_jsonl(rows)
        (staged / CHILD_FILENAMES[domain]).write_bytes(payload)
        manifest = load_json(staged / MANIFEST_NAME)
        manifest["child_payloads"][domain]["sha256"] = hashlib.sha256(payload).hexdigest()
        manifest["child_payloads"][domain]["row_count"] = len(rows)
        write_json(staged / MANIFEST_NAME, manifest)

    def _reseal(self, row: dict) -> dict:
        updated = _copy(row)
        updated["row_identity"] = stable_hash(_row_identity_payload(updated))
        return updated

    def test_reconstruct_matches_committed_gate_and_children(self) -> None:
        reconstructed = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        validated = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(reconstructed["gate"]["gate_identity"], self.gate["gate_identity"])
        self.assertEqual(validated["dataset_identity"], self.dataset_identity)
        self.assertEqual(self.gate["union_identity"], PINNED_BAT618_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat591_payload_identity"], PINNED_BAT591_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat596_payload_identity"], PINNED_BAT596_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat601_payload_identity"], PINNED_BAT601_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat606_payload_identity"], PINNED_BAT606_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat611_payload_identity"], PINNED_BAT611_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat617_payload_identity"], PINNED_BAT617_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["counts"]["scoring_summary_serialized_rows"], 0)
        self.assertGreater(self.gate["counts"]["serialized_rows_total"], 0)
        self.assertEqual(self.gate["counts"]["games"], 93)
        self.assertFalse(self.gate["scientific_nonclaims"]["all_present_70_70_claim"])
        consumed = consume_corpus(data_root=DATA_ROOT, dataset_identity=self.dataset_identity)
        self.assertEqual(consumed["scoring_summary"], [])
        for domain in CHILD_DOMAINS:
            self.assertIn(domain, consumed)

    def test_missing_child_payload(self) -> None:
        staged = self._stage()
        (staged / CHILD_FILENAMES["drives"]).unlink()
        with self.assertRaisesRegex(AuthorityViolation, "missing child payload"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_changed_child_row_with_unchanged_hash(self) -> None:
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

    def test_changed_row_recomputed_child_hash_stale_dataset_identity(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["original_text"] = str(rows[0].get("original_text") or "") + " TAMPER"
        rows[0] = self._reseal(rows[0])
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "stale dataset identity"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=True,
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
            )

    def test_duplicate_row(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["drives"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        extra = _copy(rows[0])
        extra["domain_row_order"] = len(rows)
        rows.append(extra)
        self._rewrite_child(staged, "drives", rows)
        with self.assertRaisesRegex(AuthorityViolation, "duplicate row"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_row_order_gap(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["play_by_play"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[3]["domain_row_order"] = int(rows[3]["domain_row_order"]) + 2
        self._rewrite_child(staged, "play_by_play", rows)
        with self.assertRaisesRegex(AuthorityViolation, "row-order gap"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_cross_game_row_substitution(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        other = next(row for row in rows if row["source_url"] != rows[0]["source_url"])
        rows[0]["source_url"] = other["source_url"]
        rows[0]["source_sha256"] = other["source_sha256"]
        rows[0]["season"] = other["season"]
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "row identity does not recompute"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_source_url_substitution(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["source_url"] = "https://files.12thman.com/history/football/stats/forged.html"
        rows[0]["row_identity"] = "0" * 64
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "non-union game insertion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_source_sha_substitution(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["source_sha256"] = "0" * 64
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "source SHA substitution"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_non_union_game_insertion(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        extra = _copy(rows[0])
        extra["source_url"] = "https://example.invalid/not-in-union.html"
        extra["row_identity"] = hashlib.sha256(b"forged-row").hexdigest()
        extra["domain_row_order"] = len(rows)
        rows.append(extra)
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "non-union game insertion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_rejected_url_insertion(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        extra = _copy(rows[0])
        extra["source_url"] = OKLAHOMA_2002_UNMATCHED_URL
        extra["row_identity"] = hashlib.sha256(b"oklahoma-forged").hexdigest()
        extra["domain_row_order"] = len(rows)
        rows.append(extra)
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "rejected URL insertion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_unknown_parser(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["parser_identity"] = "forged.parser.v9"
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "unknown parser"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_unknown_domain(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["team_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["domain"] = "forged_domain"
        self._rewrite_child(staged, "team_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "unknown domain"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_player_name_merge_row_is_rejected(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["individual_player_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["player_identity"] = "NAME_ONLY_MERGED"
        self._rewrite_child(staged, "individual_player_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "name-only player merge"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
            )

    def test_participation_promoted_to_availability(self) -> None:
        staged = self._stage()
        lines = (staged / CHILD_FILENAMES["individual_player_statistics"]).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        rows[0]["availability"] = "AVAILABLE"
        self._rewrite_child(staged, "individual_player_statistics", rows)
        with self.assertRaisesRegex(AuthorityViolation, "participation does not establish availability"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                corpus_root=staged,
                require_rebuild=False,
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

    def test_forged_done_verified(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "forged DONE/VERIFIED"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated_gate(self.gate, result="DONE", classification="VERIFIED"),
                require_rebuild=False,
            )

    def test_consumer_skips_a_child_payload(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "consumer skips a child payload"):
            consume_corpus(
                data_root=DATA_ROOT,
                dataset_identity=self.dataset_identity,
                skip_children=("scoring_summary",),
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
            )

    def test_oklahoma_is_absent_and_scoring_is_absent(self) -> None:
        consumed = consume_corpus(data_root=DATA_ROOT, dataset_identity=self.dataset_identity)
        for domain in CHILD_DOMAINS:
            self.assertFalse(any(row.get("source_url") == OKLAHOMA_2002_UNMATCHED_URL for row in consumed[domain]))
            self.assertFalse(any(row.get("source_url") in PRESERVED_REJECTION_URLS for row in consumed[domain]))
        self.assertEqual(consumed["scoring_summary"], [])
        scoring = self.gate["coverage_summary"]["by_domain"]["scoring_summary"]
        self.assertEqual(scoring["serialized_rows"], 0)
        self.assertEqual(scoring["corpus_present"], 0)
        self.assertGreater(scoring["union_present_without_serialized_rows"], 0)
        self.assertTrue(
            all(row.get("parser_identity") == PREFORMATTED_PARSER_IDENTITY or row.get("parser_identity") for domain in ("team_statistics",) for row in consumed[domain])
        )


if __name__ == "__main__":
    unittest.main()
