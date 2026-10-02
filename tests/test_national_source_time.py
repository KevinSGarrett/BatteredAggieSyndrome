"""BAT-712 national 2016-2023 source-time evidence (Cycle #40 TP40-A01): producer and independent validator tests.

Every unmounted test uses the synthetic national world in ``national_source_time_fixture`` (fictional teams, pages,
receipts and repository versions written in the real lake layout). Nothing here reads the real lake.
"""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_source_time_fixture as fx  # noqa: E402

WORLD: dict = {}


def setUpModule() -> None:  # noqa: N802 - unittest hook
    WORLD["tmp"] = tempfile.TemporaryDirectory()
    base = Path(WORLD["tmp"].name)
    WORLD["world"] = fx.build_world(base / "w")
    code, result, err = fx.run_build(WORLD["world"], base / "o")
    assert code == 0, err
    WORLD["result"] = result
    WORLD["payload"] = {name: fx.read_payload(result, name) for name in (
        "partition.jsonl", "contests.jsonl", "assertions.jsonl", "lineage_rows.jsonl", "repository_rows.jsonl",
        "captures.jsonl", "relations.jsonl")}


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    WORLD["tmp"].cleanup()


def payload(name: str) -> list[dict]:
    return WORLD["payload"][name]


def repo_row(event_id: str) -> dict:
    return next(r for r in payload("repository_rows.jsonl") if r["literals"]["id"] == event_id)


def contest(key: str) -> dict:
    return next(r for r in payload("contests.jsonl") if r["contest_key"] == key)


class CensusAndJoinTests(unittest.TestCase):
    def test_universe_is_targets_plus_contributors_from_history_relations(self) -> None:
        keys = {r["contest_key"]: r["roles"] for r in payload("contests.jsonl")}
        self.assertEqual(keys["ncaa:1001"], ["CONTRIBUTOR"])  # FBS-FCS exclusion that feeds Alpha's history
        self.assertEqual(keys["ncaa:1007"], ["TARGET"])
        self.assertNotIn("ncaa:1006", keys)  # an FBS-FCS game nobody's history references
        self.assertNotIn("ncaa:4001", keys)

    def test_partition_accounts_every_parent_key_once(self) -> None:
        part = {r["contest_key"]: r for r in payload("partition.jsonl")}
        self.assertEqual(sorted(part), sorted(r["contest_key"] for r in WORLD["world"]["rows"]))
        self.assertEqual((part["ncaa:4001"]["history_partition"], part["ncaa:4001"]["source_time_scope"]),
                         ("OUT_OF_SCOPE", "KEY_ONLY_PROTECTED_EXPOSED"))
        self.assertEqual((part["ncaa:1001"]["history_partition"], part["ncaa:1001"]["source_time_scope"]),
                         ("EXCLUSION", "IN_SCOPE"))
        self.assertEqual(part["ncaa:1009"]["source_time_scope"], "NOT_REFERENCED_BY_HISTORY_RELATIONS")

    def test_every_relation_of_every_view_is_preserved(self) -> None:
        import sqlite3
        conn = sqlite3.connect(Path(WORLD["world"]["history_db"]).resolve().as_uri() + "?mode=ro", uri=True)
        expected = []
        for key, view, record in conn.execute("SELECT target_contest_key, view, record FROM history ORDER BY ord"):
            data = json.loads(record)
            expected.append(("TARGET_CONTEST", key, view, None, key))
            for side, block in (("TEAM", "team_history"), ("OPPONENT", "opponent_history")):
                expected += [("CONTRIBUTOR", key, view, side, c["contest_key"]) for c in data[block]["contributing"]]
        conn.close()
        got = [(r["relation_type"], r["target_contest_key"], r["view"], r["side"], r["contributor_contest_key"])
               for r in payload("relations.jsonl")]
        self.assertEqual(got, expected)
        target = next(r for r in payload("relations.jsonl") if r["relation_type"] == "TARGET_CONTEST")
        self.assertEqual(target["required_fields"], ["season", "contest_date", "a_participant", "b_participant"])

    def test_cold_start_target_has_only_its_target_relations(self) -> None:
        rels = [r for r in payload("relations.jsonl") if r["target_contest_key"] == "ncaa:1002"]
        self.assertEqual([r["relation_type"] for r in rels], ["TARGET_CONTEST", "TARGET_CONTEST"])

    def test_every_repository_row_has_a_disposition(self) -> None:
        states = {r["literals"]["id"]: (r["join_state"], r["join_reasons"]) for r in payload("repository_rows.jsonl")}
        self.assertEqual(len(states), sum(v["rows"] for v in WORLD["world"]["versions"]))
        self.assertEqual(states["91001"], ("JOINED", []))
        self.assertEqual(states["91004"], ("CONFLICTING", ["CONFLICTING_PARTICIPANT_IDENTITY"]))
        self.assertEqual(states["91005"], ("CONFLICTING", ["CONFLICTING_SCORES"]))
        self.assertEqual(states["91006"], ("CONFLICTING", ["DATE_NOT_IN_DECLARED_US_LOCAL_CANDIDATES"]))
        self.assertEqual(states["91009"], ("JOINED_OUTSIDE_UNIVERSE", []))
        self.assertEqual(states["91010"], ("AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES",
                                           ["AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES"]))
        self.assertEqual(states["99999"], ("UNJOINED", ["UNJOINED_NO_PARENT_CANDIDATE"]))
        self.assertEqual(states["92003"], ("CONFLICTING", ["SOURCE_VALUE_MALFORMED"]))

    def test_equal_numeric_id_in_another_namespace_is_not_a_join(self) -> None:
        row = repo_row("91004")
        self.assertEqual(row["identifiers"]["away_team"], {"namespace": "ESPN_TEAM_ID", "value": "99105"})
        self.assertEqual(contest("ncaa:1004")["b_cfbd_team_id"], {"namespace": "CFBD_TEAM_ID", "value": "105"})
        self.assertIsNone(row["national_contest_key"])
        self.assertIn("REPOSITORY_VERSION_ROW_NOT_JOINED", contest("ncaa:1004")["missing_evidence"])

    def test_switched_home_away_orients_by_identity_and_neutral_note(self) -> None:
        self.assertEqual(repo_row("91003")["orientation"], {"home_side": "B"})
        points = {a["field"]: a["value"] for a in payload("assertions.jsonl")
                  if a["contest_key"] == "ncaa:1003" and a["source_kind"] == "REPOSITORY_VERSION"}
        self.assertEqual((points["a_points"], points["b_points"]), (28, 21))
        self.assertEqual(repo_row("91002")["site_note"], "SITE_DESIGNATION_DIFFERS_SOURCE_NEUTRAL")

    def test_tie_keeps_both_scores_without_position_swap(self) -> None:
        rows = [a for a in payload("assertions.jsonl") if a["contest_key"] == "ncaa:1002" and
                a["field"] in ("a_points", "b_points")]
        self.assertTrue(rows and all(a["value"] == 20 and a["corroboration"] == "AGREES_WITH_PARENT" for a in rows))

    def test_string_typed_version_normalizes_without_coercing_malformed(self) -> None:
        row = repo_row("92001")
        self.assertEqual((row["literals"]["game_id"], row["literals"]["home_score"]), ("92001.0", "21"))
        self.assertEqual(row["join_state"], "JOINED")
        bad = repo_row("92003")
        self.assertEqual(bad["literals"]["home_score"], "3a")

    def test_spring_2020_keeps_season_label(self) -> None:
        self.assertEqual((contest("ncaa:2002")["season"], contest("ncaa:2002")["term"]), (2020, "SPRING"))
        self.assertEqual(repo_row("92002")["join_state"], "JOINED")

    def test_renamed_program_matches_by_organization(self) -> None:
        record = contest("ncaa:3001")
        self.assertEqual((record["a_team_name"], record["a_key"]), ("Charlie State", "org:3"))

    def test_absent_2023_version_is_explicit_missing_evidence(self) -> None:
        for key in ("ncaa:3001", "ncaa:3002"):
            self.assertEqual(contest(key)["missing_evidence"], ["REPOSITORY_VERSION_ABSENT_FOR_SEASON"])
            self.assertEqual(contest(key)["source_coverage"]["REPOSITORY_VERSION"], 0)

    def test_assertions_are_field_grain_with_namespaced_lineage(self) -> None:
        rows = [a for a in payload("assertions.jsonl") if a["contest_key"] == "ncaa:1001"]
        kinds = {(a["source_kind"], a["capture_id"].split(":")[0]) for a in rows}
        self.assertEqual(kinds, {("NCAA_TEAM_SEASON_PAGE", "ncaa_page"), ("CFBD_ROUTE_RESPONSE", "cfbd_route"),
                                 ("REPOSITORY_VERSION", "repo_version")})
        self.assertEqual(len(rows), 7 * (2 + 2 + 1))  # two mirror pages, two CFBD routes, one repository row
        keys = [(a["contest_key"], a["capture_id"], a["native_row_key"], a["field"], a["source_revision"]) for a in
                payload("assertions.jsonl")]
        self.assertEqual(len(keys), len(set(keys)))


class ClockTests(unittest.TestCase):
    def caps(self, kind: str) -> list[dict]:
        return [c for c in payload("captures.jsonl") if c["source_kind"] == kind]

    def test_cfbd_fbs_receipt_is_an_exact_request_interval(self) -> None:
        cap = next(c for c in self.caps("CFBD_ROUTE_RESPONSE") if c["route"] == "SRC-002" and c["season"] == 2019)
        clock = cap["clocks"]["retrieval"]
        self.assertEqual((clock["role"], clock["start_literal"], clock["literal"]),
                         ("EXACT_REQUEST_INTERVAL", "2026-08-09T18:59:48Z", "2026-08-09T18:59:49Z"))
        self.assertEqual((clock["earliest_utc"], clock["latest_utc"]),
                         ("2026-08-09T18:59:48.000000Z", "2026-08-09T18:59:49.000000Z"))

    def test_cache_hit_and_batch_stamps_are_possession_upper_bounds(self) -> None:
        fcs = next(c for c in self.caps("CFBD_ROUTE_RESPONSE") if c["route"] == "CYCLE30_FCS")
        self.assertEqual((fcs["clocks"]["retrieval"]["role"], fcs["time_evidence_class"]),
                         ("CACHE_HIT_POSSESSION_UPPER_BOUND", "CACHE_HIT_RECEIPT_ONLY"))
        page = next(c for c in self.caps("NCAA_TEAM_SEASON_PAGE") if c["clocks"]["retrieval"]["state"] == "PRESENT")
        self.assertEqual(page["clocks"]["retrieval"]["role"], "RECORDED_POSSESSION_UPPER_BOUND")
        self.assertGreater(page["receipt_stamp_shared_by"], 1)
        self.assertEqual(page["byte_binding"], "RAW_SHA256_VERIFIED")

    def test_missing_and_contradictory_receipts_stay_unresolved(self) -> None:
        states = sorted(c["clocks"]["retrieval"]["state"] for c in self.caps("NCAA_TEAM_SEASON_PAGE"))
        self.assertIn("ABSENT", states)
        self.assertIn("CONTRADICTORY", states)
        bad = next(c for c in self.caps("NCAA_TEAM_SEASON_PAGE") if c["clocks"]["retrieval"]["state"] == "CONTRADICTORY")
        self.assertEqual(bad["clocks"]["retrieval"]["literal"], f"{fx.EARLY_STAMP}|{fx.NCAA_STAMP}")
        self.assertEqual(bad["time_evidence_class"], "NO_RECEIPT")

    def test_repository_clocks_keep_asserted_commit_times_separate(self) -> None:
        for cap in self.caps("REPOSITORY_VERSION"):
            clocks = cap["clocks"]
            self.assertEqual(clocks["asserted_commit_committer"]["role"], "SOURCE_ASSERTED")
            self.assertEqual(clocks["supported_publication"]["state"], "ABSENT")
            self.assertEqual(clocks["supported_publication"]["reason"], "NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE")
            self.assertEqual(clocks["correction"]["reason"], "SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")
            self.assertLess(clocks["asserted_commit_committer"]["latest_utc"], clocks["retrieval"]["earliest_utc"])
            self.assertEqual(cap["byte_binding"], "GIT_BLOB_SHA1_MATCHES_COMMIT_FILE_ENTRY")

    def test_event_clocks_keep_literal_precision(self) -> None:
        minute = repo_row("91001")["event_clock"]
        self.assertEqual((minute["precision"], minute["earliest_utc"], minute["latest_utc"]),
                         ("minute", "2019-08-31T23:30:00.000000Z", "2019-08-31T23:30:59.999999Z"))
        page = next(r for r in payload("lineage_rows.jsonl") if r["source_kind"] == "NCAA_TEAM_SEASON_PAGE")
        self.assertEqual((page["event_clock"]["precision"], page["event_clock"]["zone"]), ("date", None))

    def test_clock_parser_refuses_naive_and_keeps_offsets(self) -> None:
        b = fx.builder()
        self.assertEqual(b.present_clock("2019-09-01T12:00:00", role="X", document=None, pointer=None)["reason"],
                         "NAIVE_TIMESTAMP_REFUSED")
        self.assertEqual(b.present_clock("2019-09-01T07:00:00-05:00", role="X", document=None,
                                         pointer=None)["earliest_utc"], "2019-09-01T12:00:00.000000Z")
        self.assertEqual(b.present_clock(None, role="X", document=None, pointer=None)["state"], "ABSENT")
        self.assertEqual(b.normalize_int(None), (None, "NULL"))
        self.assertEqual(b.normalize_int("12a"), (None, "MALFORMED"))
        self.assertEqual(b.normalize_int(True), (None, "MALFORMED"))


class RefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def refused(self, *, mutate=None, **kwargs) -> str | None:
        if mutate is not None:
            kwargs["contract"] = fx.patched_contract(WORLD["world"], self.base / "c.json", mutate)
        code, result, err = fx.run_build(WORLD["world"], self.base / "o", **kwargs)
        self.assertEqual(code, 2, err)
        self.assertFalse((self.base / "o").exists())
        return fx.refusal(err)

    def test_wrong_parent_hash_refuses(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c["parent_binding"]["population"].update(
            sqlite_sha256="0" * 64)), "PARENT_BINDING_MISMATCH")

    def test_stale_history_contract_refuses(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c["parent_binding"]["history"].update(
            contract_sha256="1" * 64)), "PARENT_BINDING_MISMATCH")

    def test_source_substitution_refuses(self) -> None:
        def mutate(c: dict) -> None:
            c["source_universe"]["repository_versions"][0]["payload_sha256"] = "2" * 64
        self.assertEqual(self.refused(mutate=mutate), "SOURCE_BINDING_MISMATCH")

    def test_unqualified_publication_claim_refuses(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c["authority"].update(
            qualified_publication_evidence_classes=["GIT_COMMITTER_DATE"])), "PUBLICATION_CLAIM_UNQUALIFIED")

    def test_forged_pit_authority_refuses(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c["authority"].update(pit_admission="ADMITTED")),
                         "FORGED_PIT_AUTHORITY")

    def test_protected_year_input_refuses(self) -> None:
        def mutate(c: dict) -> None:
            c["source_universe"]["repository_versions"][0]["season"] = 2024
        self.assertEqual(self.refused(mutate=mutate), "PROTECTED_SEASON_IN_SCOPE")
        self.assertEqual(self.refused(mutate=lambda c: c["scope"].update(
            target_seasons=list(range(2016, 2025)))), "PROTECTED_SEASON_IN_SCOPE")

    def test_unknown_contract_schema_refuses(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c.update(schema_version="9.0.0")), "CONTRACT_SCHEMA_UNKNOWN")

    def test_source_bindings_naming_another_database_refuse(self) -> None:
        bindings = json.loads(Path(WORLD["world"]["bindings"]).read_text(encoding="utf-8"))
        bindings["history_database"]["sha256"] = "3" * 64
        path = self.base / "ib.json"
        path.write_text(json.dumps(bindings), encoding="utf-8")
        self.assertEqual(self.refused(bindings=path), "SOURCE_BINDING_MISMATCH")

    def test_repository_blob_not_bound_to_its_commit_refuses(self) -> None:
        world = WORLD["world"]
        version = world["versions"][0]
        api = json.loads((world["base"] / version["commit_api"]).read_text(encoding="utf-8"))
        api["files"][0]["sha"] = "4" * 40
        data = (json.dumps(api, indent=1, sort_keys=True) + "\n").encode("utf-8")
        api_sha = hashlib.sha256(data).hexdigest()
        rel = f"raw/historical_known_at/github/sha256/{api_sha}/commit.json"
        fx.write(world["base"] / rel, data)
        # a self-consistent preflight and binding document, so the refusal comes from the git blob binding itself
        preflight = {"captures": [{"season": v["season"], "payload_sha256": v["payload_sha256"],
                                   "api_sha256": api_sha if i == 0 else v["commit_api_sha256"], "rows": v["rows"]}
                                  for i, v in enumerate(world["versions"])]}
        pre = fx.write(self.base / "pre.json", fx.jbytes(preflight))
        bindings = json.loads(Path(world["bindings"]).read_text(encoding="utf-8"))
        bindings["source_preflight"].update(path=str(pre), sha256=fx.sha(pre.read_bytes()))
        bpath = fx.write(self.base / "ib.json", fx.jbytes(bindings))

        def mutate(c: dict) -> None:
            c["source_universe"]["repository_versions"][0].update(commit_api=rel, commit_api_sha256=api_sha)
            c["parent_binding"]["source_bindings"]["cache_preflight_sha256"] = fx.sha(pre.read_bytes())
        self.assertEqual(self.refused(mutate=mutate, bindings=bpath), "REPOSITORY_BYTE_BINDING_MISMATCH")

    def test_population_path_substitution_refuses(self) -> None:
        other = self.base / "canonical" / "p" / "sha256" / ("5" * 64) / "national_population.sqlite"
        other.parent.mkdir(parents=True)
        shutil.copyfile(WORLD["world"]["population_db"], other)
        self.assertEqual(self.refused(population_db=other), "PARENT_BINDING_MISMATCH")


class DeterminismAndResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def build(self, name: str, *extra: str) -> tuple[int, dict | None, str]:
        return fx.run_build(WORLD["world"], self.base / name, *extra)

    def test_input_order_and_chunking_reproduce_the_content_identity(self) -> None:
        ref = WORLD["result"]
        for name, extra in (("r", ("--input-order", "reverse")), ("s", ("--input-order", "shuffle:17")),
                            ("c1", ("--chunk-size", "1", "--checkpoint-dir", str(self.base / "k1"))),
                            ("c17", ("--chunk-size", "17", "--checkpoint-dir", str(self.base / "k17"))),
                            ("c257", ("--chunk-size", "257", "--checkpoint-dir", str(self.base / "k257")))):
            code, got, err = self.build(name, *extra)
            self.assertEqual(code, 0, err)
            self.assertEqual((got["content_identity"], got["semantic_sha256"], got["database_sha256"]),
                             (ref["content_identity"], ref["semantic_sha256"], ref["database_sha256"]), name)

    def test_interrupted_then_resumed_build_is_identical(self) -> None:
        ck = str(self.base / "kr")
        code, got, err = self.build("i", "--chunk-size", "2", "--checkpoint-dir", ck, "--stop-after-chunks", "2")
        self.assertEqual((code, got["state"], got["completed_chunks"]), (3, "INTERRUPTED_AT_CHECKPOINT", 2))
        self.assertFalse((self.base / "i").exists())
        code, got, err = self.build("i", "--chunk-size", "2", "--checkpoint-dir", ck, "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual(got["content_identity"], WORLD["result"]["content_identity"])

    def test_stale_altered_forked_and_existing_checkpoints_refuse(self) -> None:
        ck = self.base / "kx"
        self.build("i", "--chunk-size", "2", "--checkpoint-dir", str(ck), "--stop-after-chunks", "2")
        code, _got, err = self.build("i", "--chunk-size", "3", "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_STALE_CHECKPOINT"))
        code, _got, err = self.build("i", "--chunk-size", "2", "--checkpoint-dir", str(ck))
        self.assertEqual((code, fx.refusal(err)), (2, "CHECKPOINT_EXISTS"))
        chunk = ck / "chunks" / "chunk_000001.jsonl.gz"
        text = gzip.decompress(chunk.read_bytes()).replace(b'"COMPLETED"', b'"NOT_COMPLETED"', 1)
        chunk.write_bytes(gzip.compress(text, mtime=0))
        code, _got, err = self.build("i", "--chunk-size", "2", "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_ALTERED_PREFIX"))
        ledger = ck / "checkpoint.ledger.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines()
        ledger.write_text("\n".join(lines + [lines[-1]]) + "\n", encoding="utf-8")
        code, _got, err = self.build("i", "--chunk-size", "2", "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_ALTERED_PREFIX"))

    def test_rebuild_is_already_present_and_collision_refuses(self) -> None:
        out = self.base / "same"
        code, first, err = fx.run_build(WORLD["world"], out)
        self.assertEqual((code, first["state"]), (0, "MATERIALIZED"), err)
        code, second, err = fx.run_build(WORLD["world"], out)
        self.assertEqual((code, second["state"], second["database_state"]),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"))
        victim = Path(first["content"]["data_dir"]) / "partition.jsonl.gz"
        victim.write_bytes(victim.read_bytes() + b"x")
        code, _got, err = fx.run_build(WORLD["world"], out)
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"))


class IndependentValidatorTests(unittest.TestCase):
    def test_validator_imports_no_producer_query_or_project_code(self) -> None:
        import ast
        tree = ast.parse(fx.VALIDATOR_PATH.read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertFalse(names & {"aggie_analytics", "build_national_source_time", "tools"}, names)
        self.assertNotIn("polars", names)

    def test_validator_passes_the_genuine_delivery_and_rejects_rehashed_semantic_tamper(self) -> None:
        world, result = WORLD["world"], WORLD["result"]
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "r.json"
            argv = ["--contract", str(world["contract"]), "--history-database", str(world["history_db"]),
                    "--population-database", str(world["population_db"]), "--source-bindings", str(world["bindings"]),
                    "--manifest", str(result["content"]["manifest"])]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(fx.validator().main(argv + ["--report", str(report)]), 0)
            doc = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(doc["result"], "PASS")
            self.assertTrue(doc["tamper_cases"] and all(t["rejected"] for t in doc["tamper_cases"]))
            # a coordinated forgery: rewrite one score in the payload and in the database blob, then rehash every
            # outer document consistently in a copied lake root
            copy_root = Path(tmp) / "lake"
            shutil.copytree(Path(result["content"]["manifest"]).parents[4], copy_root)
            content_dir = copy_root / "canonical" / "st" / "sha256" / result["content_identity"]
            data = gzip.decompress((content_dir / "assertions.jsonl.gz").read_bytes())
            forged = data.replace(b'"value":35', b'"value":36', 1)
            self.assertNotEqual(forged, data)
            manifest_path = copy_root / "manifests" / "st" / "sha256" / result["content_identity"] / "run_manifest.json"
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            (content_dir / "assertions.jsonl.gz").write_bytes(gzip.compress(forged, mtime=0))
            doc["identity_document"]["semantic_outputs"]["assertions.jsonl"] = hashlib.sha256(forged).hexdigest()
            doc["identity_document"]["outputs"]["assertions.jsonl.gz"] = hashlib.sha256(
                (content_dir / "assertions.jsonl.gz").read_bytes()).hexdigest()
            new_id = hashlib.sha256(json.dumps(doc["identity_document"], sort_keys=True, separators=(",", ":"),
                                               ensure_ascii=False).encode("utf-8")).hexdigest()
            doc["identity"] = new_id
            new_manifest = manifest_path.parents[1] / new_id / "run_manifest.json"
            new_manifest.parent.mkdir(parents=True)
            new_manifest.write_text(json.dumps(doc), encoding="utf-8")
            shutil.copytree(content_dir, content_dir.parent / new_id)
            report2 = Path(tmp) / "r2.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = fx.validator().main(argv[:-1] + [str(new_manifest), "--report", str(report2)])
            self.assertEqual(code, 1)
            failed = json.loads(report2.read_text(encoding="utf-8"))["failed_checks"]
            self.assertIn("every_record_reconstructed_independently", failed)


if __name__ == "__main__":
    unittest.main()
