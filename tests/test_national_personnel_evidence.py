"""BAT-730 national personnel evidence 2004-2022 (Cycle #59 TP59-A01): contract, input qualification, the six grains,
independent returning-production reconstruction, determinism, the installed query front, coordinated forgeries and
valid controls, malformed JSON boundaries, and the reader's numeric and program-key domains (MF59A01-01).

The tiny world is built once per module through the real input formats (see ``personnel_evidence_fixture``)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import personnel_evidence_fixture as fx  # noqa: E402
from aggie_analytics.personnel_evidence import evidence as pe  # noqa: E402
from aggie_analytics.personnel_evidence import query as pq  # noqa: E402

CONTRACT_PATH = ROOT / pe.CONTRACT_REL
GATE_PATH = ROOT / "artifacts" / "data_lake" / "national_personnel_evidence_2004_2022_gate.json"
_STATE: dict = {}


def setUpModule() -> None:
    tmp = tempfile.TemporaryDirectory(prefix="npe-")
    base = Path(tmp.name)
    world = fx.build_world(base / "w")
    anchors_ = fx.anchors_for(world)
    contract_path = fx.write_contract(base / "cc.json", fx.contract_for(world, anchors_))
    anchors = fx.contract_anchors(contract_path, world["repo_root"])
    code, result, stderr = fx.run_build(contract_path, world, base / "o")
    if code != 0:
        raise AssertionError(f"personnel build refused: {stderr}")
    db = fx.database_of(result)
    with pe.PersonnelEvidence(db, anchors=anchors) as reader:
        records = reader.records
        identities = (reader.database_identity, reader.content_identity)
    profiled = {**anchors, "profile": {"database_identity": identities[0], "content_identity": identities[1]}}
    _STATE.update(tmp=tmp, base=base, world=world, anchors=anchors, profiled=profiled, contract_path=contract_path,
                  result=result, db=db, records=records)


def tearDownModule() -> None:
    _STATE["tmp"].cleanup()


class World(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for key, value in _STATE.items():
            setattr(cls, key, value)

    def serve(self, *argv: str, database: Path | None = None, anchors: dict | None = None
              ) -> tuple[int, dict | None, str | None]:
        code, doc, err = fx.query(anchors or self.anchors, database or self.db, *argv)
        return code, doc, fx.refusal(err)

    def rows(self, table: str, **match) -> list[dict]:
        return [r for r in self.records[table] if all(r.get(k) == v for k, v in match.items())]


# --------------------------------------------------------------------------------------------- contract

class ContractTests(unittest.TestCase):
    def test_the_committed_contract_equals_the_module_rules_and_is_pinned(self) -> None:
        raw = CONTRACT_PATH.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        self.assertEqual(pe.canonical_json_bytes(contract["rules"]), pe.canonical_json_bytes(pe.rules_document()))
        for key in ("inputs", "captures", "parent_contracts", "expected"):
            self.assertEqual(contract[key], pe.ANCHORS[key], key)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), pe.ANCHORS["contract_sha256"])
        expected = pe.ANCHORS["expected"]
        self.assertEqual((expected["memberships"], expected["exclusions"], expected["program_seasons"],
                          expected["summaries"], expected["components"]), (154387, 52386, 1760, 982, 5867))
        self.assertEqual(len(expected["program_seasons_keys"]), 1760)
        self.assertEqual(pe.keys_sha256(expected["program_seasons_keys"]), expected["program_seasons_keys_sha256"])
        self.assertEqual(pe.keys_sha256(expected["summaries_keys"]), expected["summaries_keys_sha256"])
        _contract, sha, anchors = fx.builder().load_contract(CONTRACT_PATH, ROOT)
        self.assertEqual(sha, pe.ANCHORS["contract_sha256"])
        self.assertEqual(anchors, pe.ANCHORS)

    def test_a_contract_with_other_rules_is_refused(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        mutations = {
            "pairs": lambda c: c["rules"]["returning"]["pairs"].pop(),
            "labels": lambda c: c["rules"]["labels"].__setitem__("pit_eligibility", "PIT_ADMITTED"),
            "allowlist": lambda c: c["rules"]["exclusion_source_fields"].append("first_name"),
            "selectors": lambda c: c["rules"]["selectors"]["matrix"]["roster-exclusion"].append("program"),
            "database": lambda c: c["outputs"].__setitem__("database", "other.sqlite"),
            "inputs": lambda c: c.__setitem__("inputs", []),
        }
        with tempfile.TemporaryDirectory(prefix="npc-") as tmp:
            for name, mutate in mutations.items():
                changed = copy.deepcopy(contract)
                mutate(changed)
                path = fx.write_contract(Path(tmp) / f"{name}.json", changed)
                with self.subTest(name):
                    with self.assertRaises(Exception) as ctx:
                        fx.builder().load_contract(path, ROOT)
                    self.assertEqual(getattr(ctx.exception, "code", None), "CONTRACT_INVALID")

    def test_the_gate_and_the_pinned_profile_agree_with_the_contract(self) -> None:
        gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(gate["profile"], pe.PERSONNEL_PROFILE)
        self.assertEqual(gate["contract_sha256"], pe.ANCHORS["contract_sha256"])
        document = gate["database_identity_document"]
        self.assertEqual(pe.sha256_bytes(pe.canonical_json_bytes(document)), pe.PERSONNEL_PROFILE["database_identity"])
        self.assertEqual(pe.sha256_bytes(pe.canonical_json_bytes(gate["content_identity_document"])),
                         pe.PERSONNEL_PROFILE["content_identity"])
        self.assertEqual(document["content_identity"], pe.PERSONNEL_PROFILE["content_identity"])
        self.assertEqual(gate["content_identity_document"]["rules_sha256"], pe.rules_sha256())
        self.assertEqual(gate["content_identity_document"]["inputs"], pe.inputs_claim(pe.ANCHORS))
        self.assertEqual(gate["labels"], pe.LABELS)

    def test_record_fields_selectors_and_layout_are_single_sourced(self) -> None:
        self.assertEqual(pe.DDL, tuple(tuple(d) for d in pe.LAYOUT["database"]["ddl"]))
        self.assertEqual(set(pe.SELECTOR_MATRIX), set(pe.GRAINS))
        self.assertEqual(len(pe.BLOCK_LAYOUT), 19 * 2 + 7 + 8 * 2 + 2)
        self.assertFalse(set(pe.RECORD_FIELDS["exclusions"]) & set(pe.FORBIDDEN_EXCLUSION_FIELDS))
        self.assertFalse(set(pe.RECORD_FIELDS["memberships"]) & set(pe.FORBIDDEN_MEMBERSHIP_FIELDS))
        for field in ("first_name", "last_name", "team", "headshot_url", "home_latitude", "recruit_ids_json",
                      "current_first_name", "canonical_team_label"):
            self.assertIn(field, pe.FORBIDDEN_EXCLUSION_FIELDS)
        self.assertEqual(len(pe.PAIR_FIELDS), 6)

    def test_the_console_script_is_declared(self) -> None:
        self.assertIn('bas-personnel-evidence-query = "aggie_analytics.personnel_evidence.query:main"',
                      (ROOT / "pyproject.toml").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------- qualification

class QualificationTests(World):
    def test_every_membership_and_exclusion_is_served_with_its_lineage(self) -> None:
        self.assertEqual(len(self.records["memberships"]), len(self.world["members"]))
        self.assertEqual(len(self.records["exclusions"]), len(self.world["quarantine"]))
        for record in self.records["memberships"]:
            self.assertEqual(record["source_witness_key"].startswith("INPUT|roster_raw_"), True)
            self.assertIsNone(record["membership_effective_day_utc"])
            self.assertIs(record["game_time_availability"], False)
        exclusion = self.records["exclusions"][0]
        self.assertEqual(set(exclusion) & set(pe.FORBIDDEN_EXCLUSION_FIELDS), set())
        self.assertEqual({e["reconciliation_disposition"] for e in self.records["exclusions"]},
                         set(pe.EXCLUSION_DISPOSITIONS))
        self.assertTrue(all(e["canonical_identity_state"] == "UNRESOLVED_OR_NONADMITTED"
                            for e in self.records["exclusions"]))
        repeated = [e for e in self.records["exclusions"] if e["season_athlete_exclusion_rows"] > 1]
        self.assertTrue(repeated)
        self.assertTrue(any(e["season_athlete_admitted_rows"] >= 1 for e in self.records["exclusions"]))

    def test_multi_team_player_seasons_stay_distinct_associations(self) -> None:
        multi = [m for m in self.records["memberships"] if m["multi_team_player_season"]]
        self.assertEqual(len(multi), 2)
        self.assertEqual({m["canonical_team_id"] for m in multi}, {fx.TEAMS["Alpha"][0], fx.TEAMS["Charlie"][0]})
        self.assertTrue(all(m["player_season_team_count"] == 2 for m in multi))
        self.assertEqual(self.records["census"]["multi_team_player_seasons"], 1)

    def test_program_season_chains_keep_every_unsupported_and_ambiguous_state(self) -> None:
        state = {p["program_season_key"]: p for p in self.records["program_seasons"]}
        self.assertEqual(state["2016|org:202"]["chain_state"], "UNQUALIFIED_C38_BINDING_NOT_ACCEPTED")
        self.assertEqual(state["2016|org:203"]["chain_state"], "UNQUALIFIED_NO_SRC002_TEAM_ENTITY")
        self.assertIsNone(state["2016|org:203"]["canonical_team_id"], "the SRC-001 decoy key must never join")
        self.assertEqual(state["2016|org:204"]["chain_state"], "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON")
        self.assertEqual(state["2016|org:205"]["chain_state"], "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON")
        self.assertEqual(state["2016|org:206"]["chain_state"], "UNQUALIFIED_NO_C38_BINDING_ROW")
        self.assertEqual(state["2016|org:208"]["chain_state"], "UNQUALIFIED_SRC002_ENTITY_NOT_ACCEPTED")
        self.assertEqual(state["2016|org:209"]["chain_state"], "AMBIGUOUS_MULTIPLE_SRC002_TEAM_ENTITIES")
        self.assertEqual((state["2016|org:207"]["division"], state["2016|org:207"]["divisions"]),
                         ("DIVISION_CONFLICT", ["FBS", "FCS"]))
        self.assertNotIn("2016|org:301", state)
        for key in ("2016|org:202", "2016|org:204", "2016|org:206"):
            self.assertEqual([state[key][f] for f in ("admitted_membership_rows", "admitted_distinct_players")],
                             [None, None], "unknown person counts are null, never zero")
        self.assertEqual((state["2016|org:201"]["coverage_state"], state["2016|org:201"]["admitted_membership_rows"]),
                         ("NO_ADMITTED_ROSTER_ROWS", 0))
        self.assertEqual(state["2016|org:103"]["coverage_state"], "ROSTER_WITHOUT_RETURNING_TRANSITION")
        self.assertIn("NO_PRIOR_SEASON_ADMITTED_ROSTER_ROWS", state["2016|org:103"]["coverage_reasons"])
        delta = [m for m in self.records["memberships"] if m["canonical_team_id"] == fx.TEAMS["Delta"][0]
                 and m["season"] == 2016]
        self.assertTrue(delta and all(m["census_association"] ==
                                      "NO_QUALIFIED_CENSUS_PROGRAM_FOR_CANONICAL_TEAM_SEASON" for m in delta))

    def test_returning_production_is_recomputed_and_equals_the_original_research(self) -> None:
        agreement = self.records["census"]["original_research_agreement"]
        self.assertEqual((agreement["summaries_equal"], agreement["components_equal"], agreement["coverage_equal"]),
                         (len(self.world["original_features"]), len(self.world["original_components"]), 8))
        outside = [c for c in self.records["components"] if c["outside_unit_interval"]]
        self.assertEqual(len(outside), 1)
        self.assertGreater(outside[0]["returning_share"], 1.0, "signed yardage is never clipped")
        zero = [c for c in self.records["components"] if c["prior_total"] == 0]
        self.assertTrue(zero and all(c["returning_share"] is None for c in zero))
        missing = [s for s in self.records["summaries"] if s["missing_component_pairs"]]
        self.assertEqual([s["defensive_interceptions_returning_share"] for s in missing], [None])
        partial = [s for s in self.records["summaries"] if s["target_season"] == 2021]
        self.assertTrue(partial and all(s["partial_prior_metric_season"] for s in partial))
        outside_census = [s for s in self.records["summaries"] if s["target_season"] == 2015]
        self.assertTrue(all(s["census_scope_state"] == "TARGET_AND_PRIOR_OUTSIDE_CENSUS_SEASONS"
                            for s in outside_census))
        for s in self.records["summaries"]:
            self.assertEqual(s["union_roster_count"], s["returning_roster_count"] + s["departed_roster_count"] +
                             s["arrival_roster_count"])

    def test_witnesses_name_every_input_and_the_distinct_clocks(self) -> None:
        witnesses = {w["witness_key"]: w for w in self.records["witnesses"]}
        self.assertEqual(len(witnesses), len(self.anchors["inputs"]) + len(self.anchors["parent_contracts"]))
        raw = next(w for w in witnesses.values() if w["name"].startswith("roster_raw_"))
        self.assertEqual(raw["source_committer_utc"], pe.SOURCE_KNOWN_AT)
        self.assertNotEqual(raw["capture_acquired_at_utc"], raw["source_committer_utc"])
        self.assertEqual(raw["clock_kinds"], ["SOURCE_REPOSITORY_COMMITTER_TIME", "CAPTURE_ACQUIRED_AT"])

    def test_tampered_or_missing_inputs_are_refused_by_the_builder(self) -> None:
        with tempfile.TemporaryDirectory(prefix="npt-") as tmp:
            data = Path(tmp) / "data"
            shutil.copytree(self.world["data_root"], data)
            world = {**self.world, "data_root": data}
            payload = data / Path(*self.anchors["inputs"]["metric_payload"]["relative_path"].split("/"))
            payload.write_bytes(payload.read_bytes() + b"\x00")
            self.assertEqual(fx.refusal(fx.run_build(self.contract_path, world, Path(tmp) / "o")[2]),
                             "PERSONNEL_INPUT_TAMPERED")
            payload.unlink()
            self.assertEqual(fx.refusal(fx.run_build(self.contract_path, world, Path(tmp) / "o")[2]),
                             "PERSONNEL_INPUT_MISSING")


# --------------------------------------------------------------------------------------------- determinism

class DeterminismTests(World):
    def test_order_chunk_and_resume_variants_reproduce_every_byte(self) -> None:
        genuine = self.db.read_bytes()
        variants = {"reverse": ("--input-order", "reverse"), "shuffle": ("--input-order", "shuffle:5901"),
                    "chunk1": ("--chunk-size", "1", "--checkpoint-dir", "{ck}"),
                    "chunk17": ("--chunk-size", "17", "--checkpoint-dir", "{ck}")}
        for name, extra in variants.items():
            with self.subTest(name):
                out = self.base / f"det-{name}"
                argv = [a.replace("{ck}", str(out / "ck")) for a in extra]
                code, result, err = fx.run_build(self.contract_path, self.world, out, *argv)
                self.assertEqual(code, 0, err)
                self.assertEqual(result["database_identity"], self.result["database_identity"])
                self.assertEqual(fx.database_of(result).read_bytes(), genuine)
        out = self.base / "det-resume"
        ck = str(out / "ck")
        code, result, _e = fx.run_build(self.contract_path, self.world, out, "--chunk-size", "3", "--checkpoint-dir",
                                        ck, "--stop-after-chunks", "2")
        self.assertEqual((code, result["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        code, result, err = fx.run_build(self.contract_path, self.world, out, "--chunk-size", "3", "--checkpoint-dir",
                                         ck, "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual(fx.database_of(result).read_bytes(), genuine)

    def test_an_existing_identity_is_verified_and_a_collision_refused(self) -> None:
        out = self.base / "det-again"
        shutil.copytree(self.base / "o", out)
        code, result, err = fx.run_build(self.contract_path, self.world, out)
        self.assertEqual((code, result["state"]), (0, "ALREADY_PRESENT_IDENTICAL"), err)
        target = fx.database_of(result)
        os.chmod(target, 0o666)
        target.write_bytes(target.read_bytes() + b"\x00")
        self.assertEqual(fx.refusal(fx.run_build(self.contract_path, self.world, out)[2]),
                         "REFUSED_IMMUTABLE_COLLISION")


# --------------------------------------------------------------------------------------------- the query front

class QueryTests(World):
    def test_every_grain_serves_its_complete_collection(self) -> None:
        for grain, table in pe.GRAINS.items():
            with self.subTest(grain):
                code, doc, refused = self.serve("--grain", grain, "--all")
                self.assertEqual((code, refused), (0, None))
                self.assertEqual(doc["total"], len(self.records[table]))
                self.assertEqual(doc["rows"], self.records[table])
                self.assertEqual(doc["source_time"]["source_repository_commit_utc"], pe.SOURCE_KNOWN_AT)
                self.assertEqual(doc["pit_eligibility"], "PIT_NOT_ADMITTED")

    def test_selectors_intersect_page_and_return_empty_for_unknown_or_disjoint(self) -> None:
        alpha, bravo = fx.TEAMS["Alpha"][0], fx.TEAMS["Bravo"][0]
        code, doc, _r = self.serve("--grain", "roster-membership", "--season", "2016", "--team", alpha, "--all")
        self.assertTrue(doc["rows"] and all(r["season"] == 2016 and r["canonical_team_id"] == alpha
                                            for r in doc["rows"]))
        code, doc, _r = self.serve("--grain", "roster-membership", "--program", "101", "--all")
        self.assertTrue(doc["rows"] and all(r["census_key"].endswith("|org:101") for r in doc["rows"]))
        code, doc, _r = self.serve("--grain", "roster-membership", "--player", fx.player(1), "--all")
        self.assertEqual({r["canonical_team_id"] for r in doc["rows"]}, {alpha, fx.TEAMS["Charlie"][0]})
        code, doc, _r = self.serve("--grain", "program-season-coverage", "--team", alpha, "--all")
        self.assertEqual([r["program_season_key"] for r in doc["rows"]], ["2016|org:101", "2020|org:101",
                                                                          "2021|org:101"])
        code, doc, _r = self.serve("--grain", "returning-summary", "--season", "2021")
        self.assertEqual(len(doc["transition_coverage"]), 1)
        code, doc, _r = self.serve("--grain", "returning-component", "--program", "org:102", "--season", "2021")
        self.assertTrue(doc["rows"] and all(r["canonical_team_id"] == bravo for r in doc["rows"]))
        code, doc, _r = self.serve("--grain", "source-witness", "--season", "2014", "--all")
        self.assertTrue(doc["rows"] and all(r["season"] == 2014 for r in doc["rows"]))
        n = len(self.records["memberships"])
        code, doc, _r = self.serve("--grain", "roster-membership", "--limit", "3", "--offset", "2")
        self.assertEqual((doc["total"], doc["returned"], doc["next_offset"]), (n, 3, 5))
        self.assertEqual(doc["rows"], self.records["memberships"][2:5])
        code, doc, _r = self.serve("--grain", "roster-membership", "--offset", str(n))
        self.assertEqual((doc["returned"], doc["next_offset"]), (0, None))
        empty = [("roster-membership", "--team", "team_" + "0" * 32),
                 ("roster-membership", "--player", "player_" + "0" * 32),
                 ("roster-exclusion", "--team", "team_" + "0" * 32),
                 ("program-season-coverage", "--program", "org:999999"),
                 ("returning-summary", "--team", alpha, "--program", "org:102"),
                 ("returning-component", "--team", "team_" + "0" * 32),
                 ("roster-membership", "--team", alpha, "--program", "org:102")]
        for grain, *argv in empty:
            with self.subTest(grain=grain, argv=argv):
                code, doc, _r = self.serve("--grain", grain, *argv)
                self.assertEqual((code, doc["total"], doc["rows"]), (0, 0, []))
                if grain == "returning-summary":
                    self.assertEqual(doc["transition_coverage"], [])
        for grain, season in (("roster-membership", "2023"), ("program-season-coverage", "2015"),
                              ("returning-summary", "2014"), ("roster-exclusion", "2003")):
            with self.subTest(grain=grain, season=season):
                code, doc, _r = self.serve("--grain", grain, "--season", season)
                self.assertEqual((doc["season_scope_state"], doc["total"]), ("SEASON_OUTSIDE_RELEASE", 0))

    def test_misuse_is_refused_before_any_file_is_read(self) -> None:
        missing = self.base / "nowhere" / "x.sqlite"
        cases = {("--grain", "roster-exclusion", "--program", "org:101"): "FILTER_NOT_APPLICABLE",
                 ("--grain", "program-season-coverage", "--player", fx.player(1)): "FILTER_NOT_APPLICABLE",
                 ("--grain", "returning-summary", "--player", fx.player(1)): "FILTER_NOT_APPLICABLE",
                 ("--grain", "source-witness", "--team", fx.TEAMS["Alpha"][0]): "FILTER_NOT_APPLICABLE",
                 ("--grain", "roster-membership", "--team", "Alpha"): "TEAM_INVALID",
                 ("--grain", "roster-membership", "--team", fx.TEAMS["Alpha"][0].upper()): "TEAM_INVALID",
                 ("--grain", "roster-membership", "--program", "Texas A&M"): "PROGRAM_INVALID",
                 ("--grain", "roster-membership", "--player", "player_xyz"): "PLAYER_INVALID",
                 ("--grain", "roster-membership", "--season", "2016.0"): "SEASON_INVALID",
                 ("--grain", "roster-membership", "--limit", "-1"): "NEGATIVE_LIMIT",
                 ("--grain", "roster-membership", "--offset", "x"): "OFFSET_INVALID",
                 ("--grain", "roster-membership", "--require-pit"): "PERSONNEL_PIT_NOT_ADMITTED",
                 ("--grain", "roster-membership", "--as-of", "2016-09-01"): "ARGUMENT_INVALID",
                 ("--grain", "availability"): "ARGUMENT_INVALID",
                 ("--grain", "roster-membership", "--expect-identity", "abc"): "STALE_PERSONNEL_IDENTITY"}
        for argv, code in cases.items():
            with self.subTest(argv=argv):
                self.assertEqual(self.serve(*argv, database=missing)[2], code)
        self.assertFalse(missing.parent.exists())

    def test_the_release_is_read_only_and_nothing_is_created(self) -> None:
        missing = self.base / "o2" / "canonical" / pe.POPULATION / "sha256" / ("0" * 64) / pe.DB_FILE
        self.assertEqual(self.serve("--grain", "roster-membership", database=missing)[2],
                         "PERSONNEL_DATABASE_MISSING")
        self.assertFalse(missing.exists())
        before = {p: (p.stat().st_mtime_ns, p.stat().st_size) for p in Path(self.db).parent.iterdir()}
        self.assertEqual(self.serve("--grain", "roster-membership")[0], 0)
        self.assertEqual({p: (p.stat().st_mtime_ns, p.stat().st_size) for p in Path(self.db).parent.iterdir()},
                         before)
        if os.name == "nt":
            for location in (r"\\server\share\x.sqlite", r"\\.\nul", r"\\?\UNC\server\share\x.sqlite"):
                with self.subTest(location):
                    self.assertEqual(self.serve("--grain", "roster-membership", database=Path(location))[2],
                                     "DATABASE_LOCATION_UNSUPPORTED")
            self.assertEqual(self.serve("--grain", "roster-membership", "--manifest", r"\\server\share\m.json")[2],
                             "PERSONNEL_MANIFEST_LOCATION_UNSUPPORTED")
        self.assertEqual(self.serve("--grain", "roster-membership", "--expect-identity", "f" * 64)[2],
                         "STALE_PERSONNEL_IDENTITY")
        self.assertEqual(self.serve("--grain", "roster-membership", "--manifest",
                                    str(self.base / "no-manifest.json"))[2], "PERSONNEL_MANIFEST_MISSING")

    def test_rehoused_long_and_explicit_manifest_locations_serve_identically(self) -> None:
        def ext(path: Path | str) -> str:
            text = os.path.abspath(str(path))
            return "\\\\?\\" + text if os.name == "nt" and not text.startswith("\\\\?\\") else text
        tmp = tempfile.mkdtemp(prefix="npl-")
        try:
            long_root = Path(tmp).joinpath(*[f"long-native-location-component-{c}-" + c * 40 for c in "abcd"])
            identity = Path(self.db).parent.name
            manifest = fx.manifest_of(self.db)
            targets = {self.db: long_root / "canonical" / pe.POPULATION / "sha256" / identity / pe.DB_FILE,
                       manifest: long_root / "manifests" / pe.POPULATION / "sha256" / identity / "run_manifest.json"}
            for source, target in targets.items():
                os.makedirs(ext(target.parent), exist_ok=True)
                with open(ext(target), "xb") as handle:
                    handle.write(Path(source).read_bytes())
            long_db = targets[self.db]
            self.assertGreater(len(str(long_db)), 260)
            original = self.serve("--grain", "returning-summary", "--all")
            self.assertEqual(original[0], 0)
            self.assertEqual(self.serve("--grain", "returning-summary", "--all", database=long_db), original)
            self.assertEqual(self.serve("--grain", "returning-summary", "--all", database=Path(ext(long_db))),
                             original)
            self.assertEqual(self.serve("--grain", "returning-summary", "--all", "--manifest",
                                        str(targets[manifest])), original)
        finally:
            shutil.rmtree(ext(tmp), ignore_errors=True)

    def test_relative_and_special_character_locations_serve_identically(self) -> None:
        original = self.serve("--grain", "program-season-coverage", "--all")
        self.assertEqual(original[0], 0)
        identity = Path(self.db).parent.name
        with tempfile.TemporaryDirectory(prefix="npu-") as tmp:
            root = Path(tmp) / "r\u00e9lease #%&' \u00fcn\u00efcode \u2603"
            for source, target in ((self.db, root / "canonical" / pe.POPULATION / "sha256" / identity / pe.DB_FILE),
                                   (fx.manifest_of(self.db), root / "manifests" / pe.POPULATION / "sha256" / identity /
                                    "run_manifest.json")):
                target.parent.mkdir(parents=True)
                target.write_bytes(Path(source).read_bytes())
            special = root / "canonical" / pe.POPULATION / "sha256" / identity / pe.DB_FILE
            self.assertEqual(self.serve("--grain", "program-season-coverage", "--all", database=special), original)
            previous = os.getcwd()
            os.chdir(root / "canonical")
            try:
                relative = Path(pe.POPULATION) / "sha256" / identity / pe.DB_FILE
                self.assertEqual(self.serve("--grain", "program-season-coverage", "--all", database=relative),
                                 original)
            finally:
                os.chdir(previous)

    def test_the_module_front_matches_the_function_front(self) -> None:
        with pe.PersonnelEvidence(self.db, anchors=self.anchors) as reader:
            direct = reader.query("program-season-coverage", season=2016, limit=5)
        code, doc, _r = self.serve("--grain", "program-season-coverage", "--season", "2016", "--limit", "5")
        self.assertEqual((code, doc), (0, json.loads(json.dumps(direct))))
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "BAS_"))}
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src")] + [p for p in env.get("PYTHONPATH", "").split(
            os.pathsep) if p])
        run = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.personnel_evidence.query", "--database",
                              str(self.db), "--grain", "roster-membership", "--require-pit"], capture_output=True,
                             text=True, env=env, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stderr.strip().splitlines()[-1])["refused"], "PERSONNEL_PIT_NOT_ADMITTED")
        run = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.personnel_evidence.query", "--database",
                              str(self.db), "--grain", "roster-membership"], capture_output=True, text=True, env=env,
                             check=False)
        self.assertEqual((run.returncode, json.loads(run.stderr.strip().splitlines()[-1])["refused"]),
                         (2, "PERSONNEL_CONTRACT_MISMATCH"), "the production front pins the committed contract")


# --------------------------------------------------------------------------------------------- coordinated forgeries

class ForgingWorld(World):
    """A Forger over the tiny release (no tests of its own)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.base / f"f-{cls.__name__}", cls.anchors)
        cls.counter = 0

    def refused(self, path: Path, anchors: dict | None = None) -> str | None:
        return self.serve("--grain", "roster-membership", "--limit", "1", database=path, anchors=anchors)[2]

    def forge(self, **kwargs) -> Path:
        type(self).counter += 1
        return self.forger.forge(f"f{type(self).counter}", **kwargs)

    @staticmethod
    def first(tables: dict, table: str, **match) -> dict:
        return next(r for r in tables[table] if all(r.get(k) == v for k, v in match.items()))


class ForgeryTests(ForgingWorld):
    def test_collection_forgeries(self) -> None:
        def extra_membership(t):
            r = copy.deepcopy(t["memberships"][-1])
            r["membership_key"] = r["observation_id"] = "hist_roster_" + "f" * 24
            t["memberships"].append(r)

        def reorder(t):
            t["memberships"][0], t["memberships"][1] = t["memberships"][1], t["memberships"][0]

        cases = {
            "omitted membership": (lambda t: t["memberships"].pop(3), "PERSONNEL_MEMBERSHIP_ROW_MISSING"),
            "extra membership": (extra_membership, "PERSONNEL_MEMBERSHIP_ROW_EXTRA"),
            "duplicate exclusion": (lambda t: t["exclusions"].insert(1, t["exclusions"][0]), "PERSONNEL_DUPLICATE_ROW"),
            "reordered memberships": (reorder, "PERSONNEL_ORDER_MISMATCH"),
            "omitted program-season": (lambda t: t["program_seasons"].pop(4), "PERSONNEL_PROGRAM_SEASON_ROW_MISSING"),
            "omitted component": (lambda t: t["components"].pop(0), "PERSONNEL_COMPONENT_ROW_MISSING"),
            "omitted witness": (lambda t: t["witnesses"].pop(2), "PERSONNEL_WITNESS_ROW_MISSING"),
            "replaced exclusion key": (lambda t: t["exclusions"][-1].update(
                exclusion_key="hist_roster_" + "f" * 24, observation_id="hist_roster_" + "f" * 24),
                "PERSONNEL_EXCLUSION_KEYS_MISMATCH"),
        }
        for name, (mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forge(records=mutate)), code)

    def test_semantic_field_forgeries(self) -> None:
        def duplicate_player(t):
            members = t["memberships"]
            for a, b in zip(members, members[1:]):
                if a["season"] == b["season"] and a["canonical_team_id"] != b["canonical_team_id"] and \
                        a["observation_id"] < b["observation_id"] and a["canonical_player_id"] != \
                        b["canonical_player_id"]:
                    b.update(canonical_player_id=a["canonical_player_id"], canonical_team_id=a["canonical_team_id"],
                             canonical_team_label=a["canonical_team_label"], team=a["team"])
                    return
            raise AssertionError("no adjacent pair to duplicate")

        def clipped(t):
            c = next(r for r in t["components"] if r["outside_unit_interval"])
            c.update(returning_share=1.0)

        def clipped_everywhere(t):
            c = next(r for r in t["components"] if r["outside_unit_interval"])
            c.update(returning_total=c["prior_total"], returning_share=1.0, outside_unit_interval=False)
            s = next(r for r in t["summaries"] if r["summary_key"] == c["summary_key"])
            field = dict(pe.PAIR_FIELDS)[(c["category"], c["stat_type"])]
            s[field] = 1.0
            s["feature_identity"] = pe.original_feature(s)["feature_identity"]
            c["component_identity"] = pe.original_component(c)["component_identity"]

        unqualified = next(p for p in self.records["program_seasons"] if p["chain_state"].startswith("UNQUALIFIED"))
        qualified = next(p for p in self.records["program_seasons"] if p["chain_state"] == "QUALIFIED_EXACT_CHAIN"
                         and p["returning_target_summary_key"])
        missing = next(s for s in self.records["summaries"] if s["missing_component_pairs"])
        missing_field = dict((f"{c}|{st}", f) for (c, st), f in pe.PAIR_FIELDS)[missing["missing_component_pairs"][0]]
        zero = next(c for c in self.records["components"] if c["prior_total"] == 0)
        last_member = self.records["memberships"][-1]
        cases = {
            "future roster season": (lambda t: t["memberships"][-1].update(season=2023),
                                     "PERSONNEL_FUTURE_OR_CURRENT_ROSTER"),
            "duplicate player": (duplicate_player, "PERSONNEL_DUPLICATE_NATURAL_KEY"),
            "quarantine promoted": (lambda t: t["exclusions"][0].update(admission_state="DEVELOPMENT_ONLY"),
                                    "PERSONNEL_QUARANTINE_PROMOTED"),
            "identity state promoted": (lambda t: t["exclusions"][0].update(canonical_identity_state="ADMITTED"),
                                        "PERSONNEL_QUARANTINE_PROMOTED"),
            "exclusion name leaked": (lambda t: t["exclusions"][0].update(first_name="First1"),
                                      "PERSONNEL_FORBIDDEN_FIELD_PRESENT"),
            "membership headshot leaked": (lambda t: t["memberships"][0].update(headshot_url="x"),
                                           "PERSONNEL_FORBIDDEN_FIELD_PRESENT"),
            "wrong namespace": (lambda t: self.first(t, "program_seasons", program_season_key=qualified[
                "program_season_key"]).update(core_identity_key="TEAM|SRC-001|" + qualified["cfbd_team_id"]),
                                "PERSONNEL_NAMESPACE_INVALID"),
            "unknown count invented": (lambda t: self.first(t, "program_seasons", program_season_key=unqualified[
                "program_season_key"]).update(admitted_membership_rows=0), "PERSONNEL_UNKNOWN_COUNT_INVENTED"),
            "clipped ratio": (clipped, "PERSONNEL_RATIO_CLIPPED"),
            "clipped coherently": (clipped_everywhere, "PERSONNEL_RATIO_CLIPPED"),
            "absent pair as zero": (lambda t: self.first(t, "summaries", summary_key=missing["summary_key"]).update(
                {missing_field: 0.0}), "PERSONNEL_MISSING_NULL_INVALID"),
            "zero denominator share": (lambda t: self.first(t, "components", component_key=zero[
                "component_key"]).update(returning_share=0.0), "PERSONNEL_ZERO_DENOMINATOR_SHARE"),
            "partial source dropped": (lambda t: next(s for s in t["summaries"] if s["target_season"] == 2021).update(
                partial_prior_metric_season=False), "PERSONNEL_PARTIAL_SOURCE_INVALID"),
            "returning set": (lambda t: t["summaries"][0].update(
                returning_roster_count=t["summaries"][0]["returning_roster_count"] + 1),
                              "PERSONNEL_RETURNING_SET_MISMATCH"),
            "rate": (lambda t: t["summaries"][0].update(roster_jaccard=0.5), "PERSONNEL_RATE_MISMATCH"),
            "multi-team flag": (lambda t: t["memberships"][0].update(
                multi_team_player_season=not t["memberships"][0]["multi_team_player_season"]),
                                "PERSONNEL_MULTI_TEAM_MISMATCH"),
            "availability claim": (lambda t: t["memberships"][0].update(game_time_availability=True),
                                   "PERSONNEL_AVAILABILITY_CLAIM_INVALID"),
            "effective day invented": (lambda t: t["memberships"][0].update(
                membership_effective_day_utc="2016-09-01T00:00:00Z"), "PERSONNEL_EFFECTIVE_DAY_INVENTED"),
            "pit claim": (lambda t: t["memberships"][0].update(pit_eligibility="PIT_ADMITTED"),
                          "PERSONNEL_PIT_CLAIM_INVALID"),
            "target-game claim": (lambda t: t["components"][0].update(target_game_feature_eligible=True),
                                  "PERSONNEL_PIT_CLAIM_INVALID"),
            "census association": (lambda t: next(m for m in t["memberships"] if m["census_key"]).update(
                census_key=None), "PERSONNEL_CENSUS_ASSOCIATION_MISMATCH"),
            "coverage count": (lambda t: self.first(t, "program_seasons", program_season_key=qualified[
                "program_season_key"]).update(admitted_membership_rows=qualified["admitted_membership_rows"] + 1),
                               "PERSONNEL_COVERAGE_COUNT_MISMATCH"),
            "transition link": (lambda t: self.first(t, "program_seasons", program_season_key=qualified[
                "program_season_key"]).update(returning_target_summary_key=None), "PERSONNEL_TRANSITION_LINK_MISMATCH"),
            "chain links": (lambda t: self.first(t, "program_seasons", program_season_key=qualified[
                "program_season_key"]).update(core_entity_rows=2), "PERSONNEL_CHAIN_STATE_INVALID"),
            "duplicate diagnosis": (lambda t: t["exclusions"][0].update(season_athlete_exclusion_rows=9),
                                    "PERSONNEL_DUPLICATE_DIAGNOSIS_MISMATCH"),
            "source clock": (lambda t: t["memberships"][0].update(source_known_at_utc="2016-08-01T00:00:00Z"),
                             "PERSONNEL_SOURCE_CLOCK_MISMATCH"),
            "capture lineage": (lambda t: t["memberships"][0].update(source_capture_id="0" * 64),
                                "PERSONNEL_SOURCE_LINEAGE_MISMATCH"),
            "witness": (lambda t: t["witnesses"][0].update(sha256="0" * 64), "PERSONNEL_WITNESS_MISMATCH"),
            "census": (lambda t: t["census"][0].update(memberships=1), "PERSONNEL_CENSUS_MISMATCH"),
            "original identity": (lambda t: t["summaries"][0].update(feature_identity="0" * 64),
                                  "PERSONNEL_ORIGINAL_IDENTITY_MISMATCH"),
            "integral float season": (lambda t: t["memberships"][0].update(season=float(t["memberships"][0]["season"])),
                                      "PERSONNEL_FIELD_TYPE_INVALID"),
            "boolean jersey": (lambda t: next(m for m in t["memberships"] if m["jersey"] is not None).update(
                jersey=True), "PERSONNEL_FIELD_TYPE_INVALID"),
            "extra member": (lambda t: t["summaries"][0].update(transfer_episode="IN"),
                             "PERSONNEL_RECORD_SHAPE_INVALID"),
            "non-string key": (lambda t: t["memberships"][0].update(membership_key=7),
                               "PERSONNEL_RECORD_TYPE_INVALID"),
            "changed member value": (lambda t: t["memberships"][0].update(first_name="Someone"),
                                     "PERSONNEL_CONTENT_IDENTITY_MISMATCH"),
        }
        self.assertEqual(last_member["season"], max(fx.ROSTER_SEASONS))
        for name, (mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forge(records=mutate)), code)

    def test_meta_identity_manifest_forgeries_and_valid_controls(self) -> None:
        self.assertEqual(self.refused(self.forge(meta={"labels": {**pe.LABELS, "pit_eligibility": "PIT_ADMITTED"}})),
                         "PERSONNEL_PIT_CLAIM_INVALID")
        self.assertEqual(self.refused(self.forge(meta={"labels": {**pe.LABELS, "trust_state": "TRUSTED"}})),
                         "PERSONNEL_LABEL_CLAIM_INVALID")
        self.assertEqual(self.refused(self.forge(meta={"rules": {"returning": "clip"}})),
                         "PERSONNEL_RULES_CLAIM_INVALID")
        claim = copy.deepcopy(pe.inputs_claim(self.anchors))
        claim["expected"]["memberships"] += 1
        self.assertEqual(self.refused(self.forge(meta={"inputs": claim})), "PERSONNEL_PARENT_MISMATCH")
        self.assertEqual(self.refused(self.forge(document=lambda d: d["table_counts"].update(
            meta=float(d["table_counts"]["meta"])))), "PERSONNEL_IDENTITY_DOCUMENT_MISMATCH")
        self.assertEqual(self.refused(self.forge(document=lambda d: d["table_counts"].update(
            blocks=d["table_counts"]["blocks"] + 1))), "PERSONNEL_COUNT_MISMATCH")
        self.assertEqual(self.refused(self.forge(document={"provenance": True})),
                         "PERSONNEL_IDENTITY_DOCUMENT_MISMATCH")
        self.assertEqual(self.refused(self.forge(identity_override="f" * 64)), "PERSONNEL_IDENTITY_MISMATCH")
        self.assertEqual(self.refused(self.forge(manifest_patch={"identity": "e" * 64})), "PERSONNEL_IDENTITY_MISMATCH")
        self.assertEqual(self.refused(self.forge(manifest_patch={"extra": 1})), "PERSONNEL_MANIFEST_MALFORMED")
        self.assertEqual(self.refused(self.forge(document={"contract_sha256": "a" * 64})),
                         "PERSONNEL_CONTRACT_MISMATCH")
        self.assertEqual(self.refused(self.forge(manifest_patch={"content_document": {"schema": "other"}})),
                         "PERSONNEL_CONTENT_IDENTITY_MISMATCH")
        self.assertEqual(self.refused(self.forge(after_blocks=[("UPDATE blocks SET records = records + 1 WHERE ord = 0",
                                                                ())])), "PERSONNEL_INDEX_MISMATCH")
        rehashed = self.forge(records=lambda t: t["memberships"][0].update(first_name="Someone"), rehash_content=True)
        self.assertIsNone(self.refused(rehashed), "a coordinated rehash is internally consistent ...")
        self.assertEqual(self.refused(rehashed, anchors=self.profiled), "PERSONNEL_PROFILE_MISMATCH",
                         "... and only the pinned profile refuses it")
        provenance_only = self.forge(provenance={"producer": "rehoused", "issued_at_utc": "2026-10-17T00:00:00Z"})
        self.assertIsNone(self.refused(provenance_only, anchors=self.profiled))
        self.assertEqual(self.serve("--grain", "returning-summary", "--all", database=provenance_only,
                                    anchors=self.profiled)[1]["rows"], self.records["summaries"])
        genuine = self.forge()
        self.assertIsNone(self.refused(genuine, anchors=self.profiled))
        os.chmod(genuine, 0o666)
        genuine.write_bytes(genuine.read_bytes()[:-1] + b"\x00")
        self.assertEqual(self.refused(genuine), "PERSONNEL_DATABASE_TAMPERED")


# --------------------------------------------------------------------------------------------- malformed JSON boundaries

DEEP_ARRAY = "[" * 100_000 + "0" + "]" * 100_000


class MalformedJsonBoundaryTests(ForgingWorld):
    def edit_line(self, table: str, edit) -> Path:
        def lines(raw):
            raw[table][0] = edit(raw[table][0])
        return self.forge(lines=lines)

    def test_record_lines_with_malformed_json_values(self) -> None:
        cases = {
            "lone surrogate": (lambda line: line.replace('"first_name":"', '"first_name":"\\udc80', 1),
                               "PERSONNEL_RECORD_MALFORMED"),
            "deep nesting": (lambda line: line.replace('"first_name":', '"first_name":' + DEEP_ARRAY + ',"x":', 1),
                             "PERSONNEL_RECORD_MALFORMED"),
            "NaN": (lambda line: line.replace('"season":', '"season":NaN,"y":', 1), "PERSONNEL_RECORD_MALFORMED"),
            "Infinity": (lambda line: line.replace('"season":', '"season":Infinity,"y":', 1),
                         "PERSONNEL_RECORD_MALFORMED"),
            "beyond binary64": (lambda line: line.replace('"season":', '"season":1e999,"y":', 1),
                                "PERSONNEL_RECORD_MALFORMED"),
            "integer beyond the digit limit": (lambda line: line.replace('"season":', '"season":' + "9" * 5000 +
                                                                         ',"y":', 1), "PERSONNEL_RECORD_MALFORMED"),
            "not JSON": (lambda line: line[:-1], "PERSONNEL_RECORD_TYPE_INVALID"),
            "not an object": (lambda line: "[1, 2]", "PERSONNEL_RECORD_TYPE_INVALID"),
        }
        for name, (edit, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.edit_line("memberships", edit)), code)

    def test_meta_and_manifest_with_malformed_json(self) -> None:
        self.assertEqual(self.refused(self.forge(meta={"labels": '{"pit_eligibility": NaN}'})),
                         "PERSONNEL_META_MALFORMED")
        self.assertEqual(self.refused(self.forge(meta={"rules": DEEP_ARRAY})), "PERSONNEL_META_MALFORMED")
        self.assertEqual(self.refused(self.forge(meta={"inputs": '"\\udc80"'})), "PERSONNEL_META_MALFORMED")
        self.assertEqual(self.refused(self.forge(manifest_text=lambda text: text.replace('"provenance":',
                                                                                         '"provenance":NaN,"p":', 1))),
                         "PERSONNEL_MANIFEST_MALFORMED")
        self.assertEqual(self.refused(self.forge(manifest_text=lambda text: text.replace(
            '"provenance":', '"provenance":' + DEEP_ARRAY + ',"p":', 1))), "PERSONNEL_MANIFEST_MALFORMED")
        self.assertEqual(self.refused(self.forge(manifest_text=lambda text: text[:-1])), "PERSONNEL_MANIFEST_MALFORMED")
        self.assertEqual(self.refused(self.forge(manifest_text=lambda text: text.replace(
            '"identity_document":', '"identity_document":{"x":"\\udc80"},"q":', 1))), "PERSONNEL_MANIFEST_MALFORMED")


# --------------------------------------------------------------------------------------------- numeric and key domains

#: The least integer magnitude ``float()`` cannot convert (independent of the reader's own constant).
OVERFLOW = 2 ** 1024 - 2 ** 970
SUPERSCRIPT_TWO, CIRCLED_ONE = "²", "①"
ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


class NumericAndKeyDomainTests(ForgingWorld):
    """MF59A01-01: untrusted values reaching an unsafe conversion -- a returning-component total the binary64 share
    converts, a program-key body the collection order converts -- refuse by their own rule (exit 2, one structured
    code, no traceback); adjacent values keep their existing codes and the genuine release is served."""

    MARK = "MF59A01-01"

    def outcome(self, path: Path) -> tuple[object, str | None, str]:
        """(exit, refusal code, stderr) of the query front; an exception escaping the front is the defect itself and
        is reported as a value, so the assertions below fail rather than error."""
        try:
            code, _doc, err = fx.query(self.anchors, path, "--grain", "returning-component", "--limit", "1")
        except (OverflowError, ValueError) as exc:  # a PersonnelError never escapes main(): it exits 2 there
            return "UNCAUGHT " + type(exc).__name__, None, str(exc)[:200]
        return code, fx.refusal(err), err

    def assert_refused(self, path: Path, code: str, reason: str | None = None) -> None:
        got, refused, err = self.outcome(path)
        self.assertEqual((got, refused), (2, code), f"{self.MARK}: {err[-300:]}")
        self.assertNotIn("Traceback", err, self.MARK)
        if reason:
            self.assertIn(reason, err, self.MARK)

    def converting(self) -> dict:
        return next(c for c in self.records["components"] if c["prior_total"] > 0 and c["returning_share"] is not None
                    and 0.0 <= c["returning_share"] <= 1.0)

    def total(self, **values) -> Path:
        key = self.converting()["component_key"]
        return self.forge(records=lambda t: self.first(t, "components", component_key=key).update(values))

    def program_key(self, position: int, team_key) -> Path:
        """The program-season at ``position`` (0 first, -1 last) of the season with the most program-seasons."""
        seasons: dict[int, list[dict]] = {}
        for p in self.records["program_seasons"]:
            seasons.setdefault(p["season"], []).append(p)
        rows = max(seasons.values(), key=len)
        key = rows[position]["program_season_key"]
        self.assertGreater(len(rows), 2)
        return self.forge(records=lambda t: self.first(t, "program_seasons", program_season_key=key).update(
            team_key=team_key))

    def test_component_totals_beyond_binary64_are_malformed_records(self) -> None:
        cases = {"numerator at the overflow bound": {"returning_total": OVERFLOW},
                 "negative numerator at the bound": {"returning_total": -OVERFLOW},
                 "numerator 10**400": {"returning_total": 10 ** 400},
                 "negative numerator 10**400": {"returning_total": -(10 ** 400)},
                 "numerator at the decoder digit limit": {"returning_total": 10 ** 4299},
                 "denominator at the overflow bound": {"prior_total": OVERFLOW},
                 "denominator 10**400": {"prior_total": 10 ** 400},
                 "both totals 10**400": {"returning_total": 10 ** 400, "prior_total": 10 ** 400}}
        for name, values in cases.items():
            with self.subTest(name):
                self.assert_refused(self.total(**values), "PERSONNEL_RECORD_MALFORMED", "JSON_NONFINITE_NUMBER")

    def test_program_keys_outside_the_decimal_domain_reach_their_rules(self) -> None:
        cases = {"superscript digit first": (0, f"org:{SUPERSCRIPT_TWO}", "PERSONNEL_ORDER_MISMATCH"),
                 "circled digit first": (0, f"org:{CIRCLED_ONE}", "PERSONNEL_ORDER_MISMATCH"),
                 "5000 digits first": (0, "org:" + "1" * 5000, "PERSONNEL_ORDER_MISMATCH"),
                 "one digit past the conversion limit first": (0, "org:" + "1" * 4301, "PERSONNEL_ORDER_MISMATCH"),
                 "superscript digit last (the program grammar)": (-1, f"org:{SUPERSCRIPT_TWO}",
                                                                  "PERSONNEL_KEY_MISMATCH"),
                 "5000 digits last (the program grammar)": (-1, "org:" + "9" * 5000, "PERSONNEL_KEY_MISMATCH")}
        for name, (position, team_key, code) in cases.items():
            with self.subTest(name):
                self.assert_refused(self.program_key(position, team_key), code)

    def test_adjacent_numeric_values_keep_their_codes(self) -> None:
        zero = next(c for c in self.records["components"] if c["prior_total"] == 0)
        conv = self.converting()
        cases = {
            "numerator one below the bound": (self.total(returning_total=OVERFLOW - 1), "PERSONNEL_RATIO_CLIPPED"),
            "negative numerator one below the bound": (self.total(returning_total=-(OVERFLOW - 1)),
                                                       "PERSONNEL_RATIO_CLIPPED"),
            "wrong ordinary numerator": (self.total(returning_total=1234567), "PERSONNEL_RATIO_CLIPPED"),
            "negative denominator beyond the bound (never converted)": (self.total(prior_total=-OVERFLOW),
                                                                        "PERSONNEL_ZERO_DENOMINATOR_SHARE"),
            "numerator beyond the bound over a zero denominator (never converted)": (self.forge(
                records=lambda t: self.first(t, "components", component_key=zero["component_key"]).update(
                    returning_total=10 ** 400)), "PERSONNEL_ORIGINAL_IDENTITY_MISMATCH"),
            "integral float denominator": (self.total(prior_total=1.0), "PERSONNEL_FIELD_TYPE_INVALID"),
            "boolean numerator": (self.total(returning_total=True), "PERSONNEL_FIELD_TYPE_INVALID"),
            "nested numerator": (self.total(returning_total=[10 ** 400]), "PERSONNEL_FIELD_TYPE_INVALID"),
            "string numerator": (self.total(returning_total="1"), "PERSONNEL_FIELD_TYPE_INVALID"),
            "float literal beyond binary64": (self.forge(lines=lambda raw: raw["components"].__setitem__(
                0, raw["components"][0].replace('"returning_share":', '"returning_share":1e999,"z":', 1))),
                "PERSONNEL_RECORD_MALFORMED"),
            "integer beyond the decoder digit limit": (self.forge(lines=lambda raw: raw["components"].__setitem__(
                0, raw["components"][0].replace('"returning_total":', '"returning_total":' + "9" * 4301 + ',"z":',
                                                1))), "PERSONNEL_RECORD_MALFORMED"),
            "huge integer in a field never converted": (self.forge(records=lambda t: t["memberships"][0].update(
                source_row_number=10 ** 400)), "PERSONNEL_CONTENT_IDENTITY_MISMATCH"),
        }
        self.assertGreater(conv["prior_total"], 0)
        for name, (path, code) in cases.items():
            with self.subTest(name):
                self.assert_refused(path, code)

    def test_adjacent_program_keys_keep_their_codes(self) -> None:
        seasons: dict[int, list[dict]] = {}
        for p in self.records["program_seasons"]:
            seasons.setdefault(p["season"], []).append(p)
        body = max(seasons.values(), key=len)[0]["team_key"].split(":", 1)[1]
        cases = {"non-digit body": (0, "org:x", "PERSONNEL_ORDER_MISMATCH"),
                 "zero body": (0, "org:0", "PERSONNEL_KEY_MISMATCH"),
                 "Arabic-Indic digits of the same value": (0, "org:" + body.translate(ARABIC_INDIC),
                                                           "PERSONNEL_KEY_MISMATCH"),
                 "leading zeros beyond twelve digits": (0, "org:" + "0" * 13 + body, "PERSONNEL_KEY_MISMATCH"),
                 "exactly the conversion limit": (0, "org:" + "1" * 4300, "PERSONNEL_ORDER_MISMATCH"),
                 "no namespace prefix": (0, body, "PERSONNEL_KEY_MISMATCH"),
                 "integer key": (0, 101, "PERSONNEL_FIELD_TYPE_INVALID"),
                 "nested key": (0, [f"org:{body}"], "PERSONNEL_FIELD_TYPE_INVALID"),
                 "null key": (0, None, "PERSONNEL_FIELD_TYPE_INVALID")}
        for name, (position, team_key, code) in cases.items():
            with self.subTest(name):
                self.assert_refused(self.program_key(position, team_key), code)
        for program in (SUPERSCRIPT_TWO, CIRCLED_ONE, "1" * 5000, body.translate(ARABIC_INDIC), f"org:{body}²"):
            with self.subTest(selector=program[:24]):
                self.assertEqual(self.serve("--grain", "program-season-coverage", "--program", program)[2],
                                 "PROGRAM_INVALID")

    def test_genuine_release_keeps_unicode_signed_ratios_null_and_partial_states(self) -> None:
        code, doc, refused = self.serve("--grain", "returning-component", "--all")
        self.assertEqual((code, refused, doc["rows"]), (0, None, self.records["components"]))
        self.assertTrue(any(c["returning_share"] is not None and c["returning_share"] > 1.0 for c in doc["rows"]))
        self.assertTrue(any(c["prior_total"] == 0 and c["returning_share"] is None for c in doc["rows"]))
        code, doc, _r = self.serve("--grain", "program-season-coverage", "--all")
        self.assertEqual(doc["rows"], self.records["program_seasons"])
        self.assertEqual([p["program_season_key"] for p in doc["rows"]],
                         sorted((p["program_season_key"] for p in doc["rows"]),
                                key=lambda k: (int(k.split("|")[0]), int(k.split(":")[1]))))
        renamed = self.forge(records=lambda t: t["program_seasons"][0].update(team_names=["São José ☃"]))
        self.assert_refused(renamed, "PERSONNEL_CONTENT_IDENTITY_MISMATCH")


# --------------------------------------------------------------------------------------------- the genuine release

class MountedGenuinePersonnelTests(unittest.TestCase):
    def test_genuine_release_serves_every_population(self) -> None:
        profile = pe.PERSONNEL_PROFILE
        data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        if profile is None or not data_root or not Path(data_root).is_dir():
            self.skipTest("no pinned canonical personnel profile or no mounted data root")
        db = Path(data_root) / "canonical" / pe.POPULATION / "sha256" / profile["database_identity"] / pe.DB_FILE
        if not db.is_file():
            self.skipTest("the pinned canonical personnel release is not present under the mounted data root")
        with pe.PersonnelEvidence(db, expect_identity=profile["database_identity"]) as reader:
            self.assertEqual(reader.content_identity, profile["content_identity"])
            census = reader.census
            self.assertEqual({k: census[k] for k in ("memberships", "exclusions", "program_seasons", "summaries",
                                                     "components", "witnesses")},
                             {k: profile[k] for k in ("memberships", "exclusions", "program_seasons", "summaries",
                                                      "components", "witnesses")})
            agreement = census["original_research_agreement"]
            self.assertEqual((agreement["summaries_equal"], agreement["components_equal"], agreement["coverage_equal"]),
                             (982, 5867, 8))
            self.assertEqual(census["signed_ratios_outside_unit_interval"], 13)


if __name__ == "__main__":
    unittest.main()
