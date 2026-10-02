"""BAT-711 national 2016-2023 FBS retrospective history prefix (Cycle #39 TP39-A01): producer and oracle tests.

Unmounted tests use the tiny synthetic national world in ``national_history_fixture`` (built with the accepted BAT-710
parent builder). The mounted test needs the bound real parent under ``AGGIE_ANALYTICS_DATA_ROOT`` and only reads it.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_history_fixture as fx  # noqa: E402

LABELS = {"observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
          "pit_eligibility": "PIT_ELIGIBILITY_NOT_ESTABLISHED",
          "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME"}


class Workspace(unittest.TestCase):
    """One synthetic parent and one canonical build per class (built in a fresh temporary directory)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.parent = fx.build_parent(cls.base / "parent")
        cls.contract = fx.write_contract(cls.base / "contract.json", fx.contract_for(cls.parent))
        code, cls.result, err = fx.run_build(cls.contract, cls.parent, cls.base / "out")
        assert code == 0, err
        cls.payload = {name: fx.read_payload(cls.result, name) for name in
                       ("targets.jsonl", "history.jsonl", "exclusions.jsonl", "labels.jsonl", "out_of_scope.jsonl")}
        cls.views = {(r["target_contest_key"], r["view"]): r for r in cls.payload["history.jsonl"]}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()


class HistoryPositiveTests(Workspace):
    def view(self, key: str, team: str) -> dict:
        return next(r for r in self.payload["history.jsonl"] if r["target_contest_key"] == key and r["team_key"] == team)

    def test_target_census_and_two_views(self) -> None:
        targets = [r["contest_key"] for r in self.payload["targets.jsonl"]]
        self.assertEqual(targets, ["ncaa:303", "ncaa:102", "ncaa:103", "ncaa:104", "ncaa:105", "ncaa:106", "ncaa:107",
                                   "ncaa:111", "ncaa:114", "ncaa:201", "ncaa:202", "ncaa:205"])
        self.assertEqual(sorted(self.views), sorted((k, v) for k in targets for v in ("A", "B")))
        census = targets + [r["contest_key"] for r in self.payload["exclusions.jsonl"]] + \
            [r["contest_key"] for r in self.payload["out_of_scope.jsonl"]]
        self.assertEqual(sorted(census), sorted(c["contest_key"] for c in fx.fixture_contests()))
        self.assertEqual(len(census), len(set(census)))

    def test_zero_history_is_cold_start_with_null_rates(self) -> None:
        block = self.view("ncaa:104", "org:3")["team_history"]
        self.assertEqual((block["history_state"], block["games"], block["rate_denominator"]), ("COLD_START", 0, 0))
        self.assertEqual([block[n] for n in ("win_rate", "points_for_mean", "points_against_mean", "margin_mean")],
                         [None] * 4)

    def test_unequal_schedule_lengths_and_fbs_fcs_history(self) -> None:
        row = self.view("ncaa:111", "org:1")
        self.assertEqual(row["team_history"]["contributing_contest_keys"], ["ncaa:101", "ncaa:103", "ncaa:105"])
        self.assertEqual(row["opponent_history"]["contributing_contest_keys"],
                         ["ncaa:102", "ncaa:104", "ncaa:113", "ncaa:107"])
        first = row["team_history"]["contributing"][0]
        self.assertEqual((first["opponent_key"], first["opponent_division_label"]), ("org:4", "FCS"))
        team = row["team_history"]
        self.assertEqual((team["games"], team["wins"], team["points_for_total"], team["points_against_total"],
                          team["margin_total"]), (3, 3, 94, 41, 53))
        self.assertEqual(team["win_rate"], {"numerator": 3, "denominator": 3})
        self.assertEqual(team["margin_mean"], {"numerator": 53, "denominator": 3})

    def test_neutral_site_target_keeps_both_views(self) -> None:
        target = next(r for r in self.payload["targets.jsonl"] if r["contest_key"] == "ncaa:103")
        self.assertEqual((target["parent_site"], target["views"]), ("NEUTRAL", ["A", "B"]))
        self.assertEqual(self.views[("ncaa:103", "A")]["team_history"]["contributing_contest_keys"], ["ncaa:101"])
        self.assertEqual(self.views[("ncaa:103", "B")]["team_history"]["contributing_contest_keys"], ["ncaa:102"])

    def test_tie_counts_as_tie(self) -> None:
        block = self.view("ncaa:103", "org:2")["team_history"]
        self.assertEqual((block["wins"], block["losses"], block["ties"]), (0, 0, 1))
        self.assertEqual(block["contributing"][0]["result"], "T")
        label = next(r for r in self.payload["labels.jsonl"] if r["contest_key"] == "ncaa:102")
        self.assertEqual((label["a_result"], label["b_result"], label["a_margin"]), ("T", "T", 0))

    def test_renamed_program_matches_by_stable_key(self) -> None:
        row = self.view("ncaa:105", "org:3")
        self.assertEqual(row["team_name"], "Charlie State")
        self.assertEqual(row["team_history"]["contributing_contest_keys"], ["ncaa:104"])

    def test_same_day_doubleheader_excludes_each_other(self) -> None:
        for key, other in (("ncaa:106", "ncaa:107"), ("ncaa:107", "ncaa:106")):
            block = self.view(key, "org:2")["team_history"]
            self.assertEqual(block["contributing_contest_keys"], ["ncaa:102", "ncaa:103"])
            self.assertIn({"contest_key": other, "contest_date": "2018-09-22",
                           "opponent_key": "org:3" if other == "ncaa:106" else "org:5",
                           "reasons": ["SAME_DATE_NOT_STRICTLY_EARLIER"]}, block["excluded_inputs"])

    def test_canceled_forfeit_unscored_are_explicit_exclusions_not_zeroes(self) -> None:
        excl = {r["contest_key"]: r for r in self.payload["exclusions.jsonl"]}
        self.assertEqual(excl["ncaa:108"]["target_exclusion_reasons"],
                         ["DISPOSITION_NOT_VERIFIED_PRESENT", "RECONCILIATION_NOT_RECONCILED_2016_2023",
                          "STATUS_NOT_COMPLETED", "NOT_COMPETITIVE", "SCORE_MISSING"])
        self.assertEqual(excl["ncaa:109"]["target_exclusion_reasons"], ["STATUS_NOT_COMPLETED", "NOT_COMPETITIVE"])
        self.assertEqual(excl["ncaa:110"]["target_exclusion_reasons"], ["STATUS_NOT_COMPLETED", "SCORE_MISSING"])
        self.assertEqual(excl["ncaa:110"]["score_state"], "MISSING")
        block = self.view("ncaa:111", "org:1")["team_history"]
        self.assertEqual([e["contest_key"] for e in block["excluded_inputs"]], ["ncaa:108", "ncaa:110"])
        self.assertNotIn("ncaa:110", block["contributing_contest_keys"])
        self.assertEqual(block["games"], 3)

    def test_2020_spring_keeps_the_2020_season_label(self) -> None:
        row = self.view("ncaa:205", "org:1")
        self.assertEqual(row["term"], "SPRING")
        self.assertEqual(row["team_history"]["contributing_contest_keys"], ["ncaa:201", "ncaa:202", "ncaa:204"])
        bowl = self.view("ncaa:202", "org:1")
        self.assertEqual(bowl["team_history"]["contributing_contest_keys"], ["ncaa:201"])

    def test_invalid_dates_unstable_and_duplicate_keys_and_negative_scores(self) -> None:
        excl = {r["contest_key"]: r for r in self.payload["exclusions.jsonl"]}
        self.assertEqual(excl["ncaa:301"]["target_exclusion_reasons"], ["DATE_INVALID"])
        self.assertEqual(excl["ncaa:302"]["target_exclusion_reasons"], ["DATE_NOT_SINGLE"])
        self.assertEqual(excl["ncaa:304"]["target_exclusion_reasons"], ["NOT_IN_FBS_ESTIMAND_SUBSET", "ORG_KEY_NOT_STABLE"])
        self.assertEqual(excl["ncaa:305"]["target_exclusion_reasons"], ["ORG_KEY_NOT_STABLE", "ORG_KEYS_NOT_DISTINCT"])
        self.assertEqual(excl["ncaa:306"]["target_exclusion_reasons"], ["SCORE_NOT_NONNEGATIVE_INTEGER"])
        block = self.view("ncaa:303", "org:1")["team_history"]
        self.assertEqual(block["history_state"], "COLD_START")
        self.assertEqual([e["contest_key"] for e in block["excluded_inputs"]], ["ncaa:301", "ncaa:302", "ncaa:304"])

    def test_pool_member_exclusions_are_marked(self) -> None:
        excl = {r["contest_key"]: r for r in self.payload["exclusions.jsonl"]}
        self.assertEqual((excl["ncaa:101"]["history_pool_member"], excl["ncaa:101"]["target_exclusion_reasons"]),
                         (True, ["NOT_IN_FBS_ESTIMAND_SUBSET"]))
        self.assertFalse(excl["ncaa:108"]["history_pool_member"])

    def test_protected_seasons_are_key_and_season_only(self) -> None:
        rows = {r["contest_key"]: r for r in self.payload["out_of_scope.jsonl"]}
        self.assertEqual(sorted(rows), ["ncaa:401", "ncaa:402"])
        self.assertEqual(set(rows["ncaa:401"]), {"record_type", "contest_key", "season", "reason", *LABELS})
        self.assertEqual(rows["ncaa:401"]["reason"], "PROTECTED_EXPOSED_SEASON_2024_2025")
        for name in ("targets.jsonl", "history.jsonl", "exclusions.jsonl", "labels.jsonl"):
            self.assertTrue(all(2016 <= r["season"] <= 2023 for r in self.payload[name]), name)

    def test_labels_are_separate_and_every_row_is_retrospective_only(self) -> None:
        for name in ("targets.jsonl", "history.jsonl"):
            for row in self.payload[name]:
                self.assertFalse({"a_points", "b_points", "a_result", "a_margin"} & set(row))
        for rows in self.payload.values():
            for row in rows:
                self.assertEqual({k: row[k] for k in LABELS}, LABELS)

    def test_no_contributor_on_or_after_the_target_date(self) -> None:
        for row in self.payload["history.jsonl"]:
            for block in (row["team_history"], row["opponent_history"]):
                self.assertTrue(all(c["contest_date"] < row["target_date"] for c in block["contributing"]))

    def test_payload_bytes_are_canonical_jsonl_without_floats(self) -> None:
        data_dir = Path(self.result["content"]["data_dir"])
        for name in self.payload:
            raw = (data_dir / name).read_bytes()
            self.assertTrue(raw.endswith(b"\n") and b"\r" not in raw)
            for line in raw.splitlines():
                value = json.loads(line)
                self.assertEqual(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                                 .encode("utf-8"), line)
                self.assertNotIn(".", json.dumps([v for v in _numbers(value)]))


def _numbers(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _numbers(item)
    elif isinstance(value, list):
        for item in value:
            yield from _numbers(item)


class DeterminismAndResumeTests(Workspace):
    def build(self, name: str, *extra: str) -> dict:
        code, result, err = fx.run_build(self.contract, self.parent, self.base / name, *extra)
        self.assertEqual(code, 0, err)
        return result

    def test_reordered_and_chunked_builds_are_byte_identical(self) -> None:
        ref = (self.result["content_identity"], self.result["database_identity"], self.result["payload_sha256"])
        for name, extra in (("rev", ["--input-order", "reverse"]), ("shuf", ["--input-order", "shuffle:17"]),
                            ("c1", ["--chunk-size", "1", "--checkpoint-dir", str(self.base / "ck1")]),
                            ("c17", ["--chunk-size", "17", "--checkpoint-dir", str(self.base / "ck17")]),
                            ("c257", ["--chunk-size", "257", "--checkpoint-dir", str(self.base / "ck257")])):
            result = self.build(name, *extra)
            self.assertEqual((result["content_identity"], result["database_identity"], result["payload_sha256"]), ref,
                             name)

    def test_interrupted_build_resumes_to_the_same_identity(self) -> None:
        ck = self.base / "ck-resume"
        code, result, err = fx.run_build(self.contract, self.parent, self.base / "resume", "--chunk-size", "2",
                                         "--checkpoint-dir", str(ck), "--stop-after-chunks", "2")
        self.assertEqual(code, 3, err)
        self.assertEqual((result["state"], result["completed_chunks"]), ("INTERRUPTED_AT_CHECKPOINT", 2))
        self.assertFalse((self.base / "resume").exists())
        resumed = self.build("resume", "--chunk-size", "2", "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual(resumed["content_identity"], self.result["content_identity"])
        again = self.build("resume", "--chunk-size", "2", "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual((again["state"], again["database"]["state"]),
                         ("ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"))

    def interrupted(self, name: str) -> Path:
        ck = self.base / name
        code, _result, err = fx.run_build(self.contract, self.parent, self.base / (name + "o"), "--chunk-size", "2",
                                          "--checkpoint-dir", str(ck), "--stop-after-chunks", "2")
        self.assertEqual(code, 3, err)
        return ck

    def resume_refusal(self, ck: Path, contract: Path | None = None, parent: dict | None = None) -> str:
        code, _result, err = fx.run_build(contract or self.contract, parent or self.parent, self.base / "x",
                                          "--chunk-size", "2", "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual(code, 2)
        return fx.refusal(err)

    def test_checkpoint_from_another_contract_or_parent_is_stale(self) -> None:
        ck = self.interrupted("ck-stale")
        other = fx.contract_for(self.parent)
        other["non_claims"] = other["non_claims"] + ["changed contract"]
        self.assertEqual(self.resume_refusal(ck, contract=fx.write_contract(self.base / "c2.json", other)),
                         "REFUSED_STALE_CHECKPOINT")
        rows = fx.fixture_contests()
        rows[0] = dict(rows[0], a_points=36)
        parent = fx.build_parent(self.base / "parent2", rows)
        contract = fx.write_contract(self.base / "c3.json", fx.contract_for(parent))
        self.assertEqual(self.resume_refusal(ck, contract=contract, parent=parent), "REFUSED_STALE_CHECKPOINT")
        code, _r, err = fx.run_build(self.contract, self.parent, self.base / "y", "--chunk-size", "3",
                                     "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual(fx.refusal(err), "REFUSED_STALE_CHECKPOINT")

    def test_altered_prefix_and_duplicate_ledger_rows_are_refused(self) -> None:
        ck = self.interrupted("ck-alter")
        chunk = ck / "chunks" / "chunk_000001.jsonl"
        chunk.write_bytes(chunk.read_bytes().replace(b'"wins":0', b'"wins":1', 1))
        self.assertEqual(self.resume_refusal(ck), "REFUSED_ALTERED_PREFIX")
        ck2 = self.interrupted("ck-dup")
        ledger = ck2 / "checkpoint.ledger.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
        ledger.write_text(lines[0] + lines[0] + lines[1], encoding="utf-8", newline="\n")
        self.assertEqual(self.resume_refusal(ck2), "REFUSED_ALTERED_PREFIX")

    def test_forked_unrecorded_chunk_and_existing_checkpoint_are_refused(self) -> None:
        ck = self.interrupted("ck-fork")
        (ck / "chunks" / "chunk_000003.jsonl").write_bytes(b'{"forged":true}\n')
        self.assertEqual(self.resume_refusal(ck), "REFUSED_FORKED_CHECKPOINT")
        code, _r, err = fx.run_build(self.contract, self.parent, self.base / "z", "--chunk-size", "2",
                                     "--checkpoint-dir", str(ck))
        self.assertEqual((code, fx.refusal(err)), (2, "CHECKPOINT_EXISTS"))

    def test_existing_identity_with_different_bytes_is_never_overwritten(self) -> None:
        out = self.base / "collide"
        first = self.build("collide")
        victim = Path(first["content"]["data_dir"]) / "labels.jsonl"
        original = victim.read_bytes()
        victim.write_bytes(original.replace(b'"W"', b'"L"', 1))
        code, _r, err = fx.run_build(self.contract, self.parent, out)
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"))
        self.assertNotEqual(victim.read_bytes(), original)  # the refused build rewrote nothing


class ContractAndParentRefusalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.parent = fx.build_parent(cls.base / "parent")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def refused(self, contract: dict, parent: dict | None = None, name: str = "c.json") -> str:
        path = fx.write_contract(self.base / name, contract)
        out = self.base / ("out-" + name)
        code, _r, err = fx.run_build(path, parent or self.parent, out)
        self.assertEqual(code, 2, err)
        self.assertFalse(out.exists(), "a refused build must not create an output root")
        return fx.refusal(err)

    def test_wrong_or_stale_parent(self) -> None:
        contract = fx.contract_for(self.parent)
        contract["parent_binding"]["sqlite_sha256"] = "0" * 64
        self.assertEqual(self.refused(contract, name="w1.json"), "PARENT_BINDING_MISMATCH")
        other = fx.build_parent(self.base / "other", [dict(c, b_points=(c["b_points"] or 0) + 1)
                                                      for c in fx.fixture_contests()])
        self.assertEqual(self.refused(fx.contract_for(self.parent), parent=other, name="w2.json"),
                         "PARENT_BINDING_MISMATCH")

    def test_unknown_contract_or_parent_schema(self) -> None:
        self.assertEqual(self.refused(fx.contract_for(self.parent, schema_version="9.9.9"), name="s1.json"),
                         "CONTRACT_SCHEMA_UNKNOWN")
        odd = fx.build_parent(self.base / "odd", meta_patch={"schema_version": "BAS-UNKNOWN-DB-9"})
        self.assertEqual(self.refused(fx.contract_for(odd), parent=odd, name="s2.json"), "PARENT_SCHEMA_UNKNOWN")

    def test_forged_pit_authority(self) -> None:
        for name, patch in (("p1.json", {"authority__pit_eligibility": "PIT_ELIGIBLE"}),
                            ("p2.json", {"payloads__row_labels": dict(LABELS, temporal_basis="KNOWN_AT_UTC")}),
                            ("p3.json", {"authority__require_pit": "ALLOWED"})):
            self.assertEqual(self.refused(fx.contract_for(self.parent, **patch), name=name), "FORGED_PIT_AUTHORITY")

    def test_protected_or_prospective_year_in_scope(self) -> None:
        seasons = list(range(2016, 2025))
        self.assertEqual(self.refused(fx.contract_for(self.parent, scope__target_seasons=seasons), name="y1.json"),
                         "PROTECTED_SEASON_IN_SCOPE")
        self.assertEqual(self.refused(fx.contract_for(self.parent, scope__target_seasons=[2016, 2026]),
                                      name="y2.json"), "PROTECTED_SEASON_IN_SCOPE")

    def test_subset_and_field_disagreement_refuses(self) -> None:
        rows = fx.fixture_contests()
        subsets = fx.subsets_for(rows)
        subsets["FBS_ESTIMAND_SUBSET"].remove("ncaa:103")
        parent = fx.build_parent(self.base / "inconsistent", rows, subsets=subsets)
        self.assertEqual(self.refused(fx.contract_for(parent), parent=parent, name="i1.json"),
                         "SUBSET_FIELD_INCONSISTENT")

    def test_record_schema_must_match_the_contract(self) -> None:
        contract = fx.contract_for(self.parent)
        contract["payloads"]["record_fields"]["history_block"].append("elo")
        self.assertEqual(self.refused(contract, name="r1.json"), "CONTRACT_INVALID")


class OracleTests(Workspace):
    def run_oracle(self, manifest: Path, name: str) -> tuple[int, dict]:
        report = self.base / f"{name}.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = fx.validator().main(["--contract", str(self.contract), "--parent-database",
                                        str(self.parent["database"]), "--manifest", str(manifest), "--report",
                                        str(report), "--raw-sample-per-stratum", "0"])
        return code, json.loads(report.read_text(encoding="utf-8"))

    def test_independent_oracle_agrees_and_its_challenges_hold(self) -> None:
        code, report = self.run_oracle(Path(self.result["content"]["manifest"]), "oracle-pass")
        self.assertEqual((code, report["result"], report["failed_checks"]), (0, "PASS", []))
        self.assertTrue(all(t["rejected"] for t in report["tamper_cases"]))
        self.assertEqual({c["assumption"]: c["as_expected"] for c in report["oracle_challenges"]},
                         {c["assumption"]: True for c in report["oracle_challenges"]})
        self.assertGreaterEqual(len(report["tamper_cases"]), 17)

    def test_coordinated_rehash_of_bad_semantic_data_is_rejected(self) -> None:
        copy_root = self.base / "rehash"
        shutil.copytree(self.base / "out", copy_root)
        manifest = Path(str(self.result["content"]["manifest"]).replace(str(self.base / "out"), str(copy_root)))
        data_dir = Path(str(self.result["content"]["data_dir"]).replace(str(self.base / "out"), str(copy_root)))
        history = data_dir / "history.jsonl"
        rows = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]
        rows[5]["team_history"]["wins"] += 1  # semantically false; every outer hash below is made consistent
        data = b"".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
                        for r in rows)
        history.write_bytes(data)
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["identity_document"]["outputs"]["history.jsonl"] = hashlib.sha256(data).hexdigest()
        identity = hashlib.sha256(json.dumps(document["identity_document"], sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=False).encode()).hexdigest()
        document["identity"] = identity
        new_manifest = manifest.parent.parent / identity / "run_manifest.json"
        new_manifest.parent.mkdir(parents=True)
        new_manifest.write_text(json.dumps(document), encoding="utf-8")
        shutil.copytree(data_dir, data_dir.parent / identity)
        code, report = self.run_oracle(new_manifest, "oracle-rehash")
        self.assertEqual((code, report["result"]), (1, "FAIL"))
        self.assertIn("reconstruction:history.jsonl", report["failed_checks"])
        self.assertIn("content_identity_recomputes", [c["check"] for c in report["checks"] if c["result"] == "PASS"])

    def test_oracle_imports_no_producer_query_or_project_module(self) -> None:
        tree = ast.parse(fx.VALIDATOR_PATH.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        names.discard("__future__")
        self.assertEqual(sorted(names - set(sys.stdlib_module_names)), [])
        source = fx.VALIDATOR_PATH.read_text(encoding="utf-8")
        for forbidden in ("build_national_history_prefix", "aggie_analytics", "national_history.query"):
            self.assertNotIn(forbidden, source.split('"""', 2)[2])


def _mounted_parent() -> Path | None:
    root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not root:
        return None
    contract = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
    path = (Path(root) / "canonical" / "national_di_population_2016_2025" / "sha256" /
            contract["parent_binding"]["query_db_identity"] / "national_population.sqlite")
    return path if path.is_file() else None


@unittest.skipUnless(_mounted_parent(), "mounted: needs the bound BAT-710 parent under AGGIE_ANALYTICS_DATA_ROOT")
class MountedRealParentTests(unittest.TestCase):
    """Read-only: the producer's census and the independent oracle's enumeration agree on the real parent."""

    def test_real_parent_census_and_target_keys_agree_with_the_oracle(self) -> None:
        build = fx.builder()
        database = _mounted_parent()
        contract, _sha = build.load_contract(fx.CONTRACT_PATH)
        build.verify_parent(contract, database, None)
        dataset = build.Dataset(build.read_parent(contract, database))
        self.assertEqual(len(dataset.targets) + len(dataset.exclusions) + len(dataset.out_of_scope), 15520)
        oracle = fx.validator()
        expectation = oracle.Expectation(oracle.Parent(database))
        self.assertEqual([r["contest_key"] for r in dataset.targets],
                         [r["contest_key"] for r in expectation.targets])
        self.assertEqual(sum(1 for e in dataset.exclusions if e["fbs_estimand_subset"]) + len(dataset.targets), 6001)
        self.assertEqual({r["contest_key"] for r in expectation.pool_rows},
                         {r["contest_key"] for r in dataset.targets} |
                         {e["contest_key"] for e in dataset.exclusions if e["history_pool_member"]})


GATE = fx.ROOT / "artifacts" / "data_lake" / "national_history_prefix_2016_2023_gate.json"


def _canonical_hash(document: dict) -> str:
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


class DeliveredGateTests(unittest.TestCase):
    """Unmounted: the committed delivery gate binds the current contract and recomputes its own identities."""

    def test_gate_binds_the_current_contract_and_its_identities_recompute(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        contract = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(gate["contract_sha256"], hashlib.sha256(fx.CONTRACT_PATH.read_bytes()).hexdigest())
        content, database = gate["content_identity_document"], gate["database_identity_document"]
        self.assertEqual(_canonical_hash(content), gate["content_identity"])
        self.assertEqual(_canonical_hash(database), gate["database_identity"])
        self.assertEqual(database["content_identity"], gate["content_identity"])
        self.assertEqual((content["contract_sha256"], database["contract_sha256"]),
                         (gate["contract_sha256"], gate["contract_sha256"]))
        binding = contract["parent_binding"]
        self.assertEqual({k: content["parent"][k] for k in ("query_db_identity", "sqlite_sha256", "contract_sha256",
                                                            "contest_identity", "program_season_identity")},
                         {k: binding[k] for k in ("query_db_identity", "sqlite_sha256", "contract_sha256",
                                                  "contest_identity", "program_season_identity")})
        self.assertEqual(gate["row_labels"], LABELS)
        counts = content["row_counts"]
        self.assertEqual(counts["history.jsonl"], 2 * counts["targets.jsonl"])
        self.assertEqual(counts["labels.jsonl"], counts["targets.jsonl"])
        self.assertEqual(counts["targets.jsonl"] + counts["exclusions.jsonl"] + counts["out_of_scope.jsonl"],
                         binding["parent_contest_rows"])
        self.assertEqual(database["table_counts"]["history"], counts["history.jsonl"])


def _delivered_root() -> Path | None:
    root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not root or not GATE.is_file():
        return None
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    path = Path(root) / "canonical" / "national_history_prefix_2016_2023" / "sha256"
    return path if (path / gate["database_identity"] / "national_history.sqlite").is_file() else None


@unittest.skipUnless(_delivered_root(), "mounted: needs the delivered history prefix under AGGIE_ANALYTICS_DATA_ROOT")
class MountedDeliveredGateTests(unittest.TestCase):
    """Read-only: the lake bytes and manifests equal the committed gate; the query opens the delivered database."""

    def test_lake_payloads_database_and_manifests_match_the_gate(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        root = _delivered_root()
        manifests = root.parent.parent.parent / "manifests" / "national_history_prefix_2016_2023" / "sha256"
        for name, sha in gate["content_identity_document"]["outputs"].items():
            self.assertEqual(hashlib.sha256((root / gate["content_identity"] / name).read_bytes()).hexdigest(), sha)
        db = root / gate["database_identity"] / "national_history.sqlite"
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),
                         gate["database_identity_document"]["outputs"]["national_history.sqlite"])
        for key, doc in (("content_identity", "content_identity_document"),
                         ("database_identity", "database_identity_document")):
            manifest = json.loads((manifests / gate[key] / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual((manifest["identity"], manifest["identity_document"]), (gate[key], gate[doc]))
        sys.path.insert(0, str(fx.ROOT / "src"))
        from aggie_analytics.national_history import query  # noqa: PLC0415
        with query.NationalHistoryDatabase(db, expect_identity=gate["database_identity"]) as handle:
            page = handle.query("targets", limit=1)
        self.assertEqual(page["total"], gate["content_identity_document"]["row_counts"]["targets.jsonl"])


if __name__ == "__main__":
    unittest.main()
