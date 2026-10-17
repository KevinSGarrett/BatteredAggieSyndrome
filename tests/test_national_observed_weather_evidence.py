"""BAT-731 national observed-weather evidence 2024 (Cycle #60 TP60-A01): contract, input qualification, the four grains,
independent raw-row reconstruction of the original pilot, exact provider/parent relations, determinism, the installed
query front, coordinated forgeries by their own rules with valid controls, malformed JSON boundaries and the reader's
numeric and key domains.

The tiny world is built once per module through the real input formats (see ``weather_evidence_fixture``)."""
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

import weather_evidence_fixture as fx  # noqa: E402
from aggie_analytics.weather_evidence import evidence as we  # noqa: E402
from aggie_analytics.weather_evidence import query as wq  # noqa: E402

CONTRACT_PATH = ROOT / we.CONTRACT_REL
GATE_PATH = ROOT / "artifacts" / "data_lake" / "national_observed_weather_evidence_2024_gate.json"
_STATE: dict = {}


def setUpModule() -> None:
    tmp = tempfile.TemporaryDirectory(prefix="nwe-")
    base = Path(tmp.name)
    world = fx.build_world(base / "w")
    anchors_ = fx.anchors_for(world)
    contract_path = fx.write_contract(base / "cc.json", fx.contract_for(world, anchors_))
    anchors = fx.contract_anchors(contract_path, world["repo_root"])
    code, result, stderr = fx.run_build(contract_path, world, base / "o")
    if code != 0:
        raise AssertionError(f"weather build refused: {stderr}")
    db = fx.database_of(result)
    with we.WeatherEvidence(db, anchors=anchors) as reader:
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

    def one(self, table: str, **match) -> dict:
        rows = [r for r in self.records[table] if all(r.get(k) == v for k, v in match.items())]
        self.assertEqual(len(rows), 1, f"{table} {match}")
        return rows[0]


# --------------------------------------------------------------------------------------------- contract

class ContractTests(unittest.TestCase):
    def test_the_committed_contract_equals_the_module_rules_and_is_pinned(self) -> None:
        raw = CONTRACT_PATH.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        self.assertEqual(we.canonical_json_bytes(contract["rules"]), we.canonical_json_bytes(we.rules_document()))
        for key in ("inputs", "raw", "parent_contracts", "clocks", "rights", "expected"):
            self.assertEqual(contract[key], we.ANCHORS[key], key)
        self.assertEqual(we.ANCHORS["contract_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual((contract["contract_id"], contract["population_id"], contract["outputs"]["database"]),
                         (we.CONTRACT_ID, we.POPULATION, we.DB_FILE))
        expected = contract["expected"]
        self.assertEqual((expected["contests"], expected["pilots"], expected["station_years"]), (1672, 920, 157))
        self.assertEqual((expected["census"]["promoted_relations"], expected["census"]["unpromoted_relations"],
                          expected["census"]["parents_without_promoted_weather"]), (882, 38, 790))
        self.assertEqual(expected["census"]["pilots_by_calendar_year"], {"2024": 909, "2025": 11})

    def test_a_contract_with_other_rules_is_refused(self) -> None:
        world, contract_path = _STATE["world"], _STATE["contract_path"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        for name, patch in (("rules", {"rules": {**contract["rules"], "decoding": {}}}),
                            ("population", {"population_id": "national_observed_weather_evidence_2023"}),
                            ("database", {"outputs": {"database": "other.sqlite"}})):
            with self.subTest(name):
                path = fx.write_contract(_STATE["base"] / f"bad-{name}.json", {**contract, **patch})
                code, _r, err = fx.run_build(path, world, _STATE["base"] / f"bad-{name}")
                self.assertEqual((code, fx.refusal(err)), (2, "CONTRACT_INVALID"))

    def test_the_gate_and_the_pinned_profile_agree_with_the_contract(self) -> None:
        gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        contract_sha = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
        self.assertEqual(gate["contract_sha256"], contract_sha)
        self.assertIsNotNone(we.WEATHER_PROFILE)
        self.assertEqual(gate["profile"], we.WEATHER_PROFILE)
        self.assertEqual(we.WEATHER_PROFILE["contract_sha256"], contract_sha)
        self.assertEqual(we.WEATHER_PROFILE["rules_sha256"], we.rules_sha256())
        document = gate["database_identity_document"]
        self.assertEqual(we.sha256_bytes(we.canonical_json_bytes(document)), we.WEATHER_PROFILE["database_identity"])
        self.assertEqual(we.sha256_bytes(we.canonical_json_bytes(gate["content_identity_document"])),
                         we.WEATHER_PROFILE["content_identity"])
        self.assertEqual(document["content_identity"], we.WEATHER_PROFILE["content_identity"])
        self.assertEqual(document["outputs"], {we.DB_FILE: we.WEATHER_PROFILE["database_sha256"]})
        self.assertEqual(gate["content_identity_document"]["rules_sha256"], we.rules_sha256())
        self.assertEqual(gate["content_identity_document"]["inputs"], we.inputs_claim(we.ANCHORS))
        self.assertEqual(gate["labels"], we.LABELS)
        census = gate["census"]
        self.assertEqual((census["promoted_relations"], census["within_30_minutes"], census["within_30_and_promoted"],
                          census["promoted_not_within_30"], census["within_30_not_promoted"]), (882, 882, 845, 37, 37))
        self.assertEqual(we.sha256_bytes(we.canonical_json_bytes(census)), we.WEATHER_PROFILE["census_sha256"])

    def test_record_fields_selectors_and_layout_are_single_sourced(self) -> None:
        rules = we.rules_document()
        self.assertEqual(rules["field_types"], we.FIELD_TYPES)
        self.assertEqual(sorted(we.SELECTOR_MATRIX), sorted(we.GRAINS))
        self.assertEqual(sorted(we.GRAINS.values()), sorted(we.RECORD_TABLES))
        self.assertEqual([list(b) for b in we.BLOCK_LAYOUT], rules["layout"]["database"]["block_layout"])
        self.assertTrue(set(we.FORBIDDEN_FIELDS).isdisjoint(set().union(*map(set, we.FIELD_TYPES.values()))))
        self.assertEqual(len(we.ORIGINAL_PILOT_FIELDS), 59)
        for table in we.RECORD_TABLES:
            self.assertIn(we.KEY_FIELDS[table], we.FIELD_TYPES[table])

    def test_the_console_script_is_declared(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('bas-weather-evidence-query = "aggie_analytics.weather_evidence.query:main"', text)


# --------------------------------------------------------------------------------------------- qualification

class QualificationTests(World):
    def test_every_parent_contest_is_served_with_its_relation(self) -> None:
        contests = self.records["contests"]
        self.assertEqual(sorted(c["contest_key"] for c in contests), sorted(fx.CONTESTS))
        states = {c["contest_key"]: c["relation_state"] for c in contests}
        self.assertEqual(states["ncaa:1001"], "PROMOTED_ONE_TO_ONE")
        self.assertEqual(states["ncaa:1002"], "PROMOTED_ONE_TO_ONE")
        self.assertEqual(states["ncaa:1003"], "CANDIDATE_NOT_PROMOTED")
        self.assertEqual(states["ncaa:1004"], "NO_PROVIDER_ROW")
        self.assertEqual(states[fx.NOLINK], "NO_PROVIDER_ROW")
        unpromoted = self.one("contests", contest_key="ncaa:1003")
        self.assertEqual((unpromoted["pilot_key"], unpromoted["provider_row_key"], unpromoted["provider_game_id"]),
                         (None, None, None))
        self.assertEqual((unpromoted["alias_relation_provider_row_key"], unpromoted["alias_relation_provider_game_id"]),
                         ("src002:2024:0002", "401000003"))
        pilot = self.one("pilots", pilot_key="401000003")
        self.assertEqual((pilot["relation_state"], pilot["contest_key"], pilot["candidate_contest_key"]),
                         ("CANDIDATE_NOT_PROMOTED", None, "ncaa:1003"))
        conflict = self.one("contests", contest_key="ncaa:1002")
        self.assertEqual(conflict["alias_field_conflicts"], ["neutral_status"])
        self.assertIn("ALIAS_FIELD_CONFLICT_RETAINED", conflict["unsupported_reasons"])
        nolink = self.one("contests", contest_key=fx.NOLINK)
        self.assertEqual((nolink["ncaa_contest_id"], nolink["contest_status"]), (None, "CANCELED"))
        self.assertIn("PARENT_CONTEST_NOT_COMPLETED", nolink["unsupported_reasons"])
        for table in we.RECORD_TABLES:
            for record in self.records[table]:
                self.assertTrue(set(we.FORBIDDEN_FIELDS).isdisjoint(record), table)
        census = self.records["census"]
        self.assertEqual((census["promoted_relations"], census["unpromoted_relations"],
                          census["parents_without_promoted_weather"]), (4, 1, 3))

    def test_unsupported_contests_never_carry_a_zero_or_default_observation(self) -> None:
        for key in ("ncaa:1003", "ncaa:1004", fx.NOLINK):
            contest = self.one("contests", contest_key=key)
            with self.subTest(key):
                self.assertTrue(contest["weather_support_state"].startswith("UNSUPPORTED_"))
                for name in (*we.NEAREST_SUMMARY, "station_id", "station_year_key", "nearest_observed_at_utc",
                             "association_clock_utc", "before_present", "after_present", "reference_venue_dome"):
                    self.assertIsNone(contest[name], name)
                self.assertIn("NO_PROMOTED_ONE_TO_ONE_PROVIDER_RELATION", contest["unsupported_reasons"])

    def test_the_pilot_is_reconstructed_from_raw_and_the_original_kept(self) -> None:
        game, field, planted = fx.PLANTED_DISCREPANCY
        for pilot in self.records["pilots"]:
            with self.subTest(pilot["pilot_key"]):
                if pilot["pilot_key"] == game:
                    self.assertEqual((pilot["reconstruction_state"], pilot["discrepant_fields"]),
                                     ("DISCREPANT", [field]))
                    self.assertEqual(pilot[f"original_{field}"], planted)
                    self.assertEqual(pilot[f"verified_{field}"], self.world["planted_verified"])
                    self.assertIn("ORIGINAL_PILOT_FIELD_DISCREPANCY", pilot["unsupported_reasons"])
                else:
                    self.assertEqual((pilot["reconstruction_state"], pilot["discrepant_fields"]),
                                     ("REPRODUCED_EXACT", []))
                    for name in we.GOVERNED_FIELDS:
                        self.assertEqual(type(pilot[f"verified_{name}"]), type(pilot[f"original_{name}"]), name)
        contest = self.one("contests", contest_key="ncaa:1007")
        self.assertEqual(contest["temperature_c"], self.world["planted_verified"])

    def test_duplicate_ranking_tie_sentinel_and_quality_classes(self) -> None:
        g1 = self.one("pilots", pilot_key="401000001")
        self.assertEqual((g1["verified_nearest_report_type"], g1["verified_before_delta_minutes"],
                          g1["verified_after_delta_minutes"], g1["verified_nearest_absolute_delta_minutes"]),
                         ("FM-12", 0.0, 0.0, 0.0))
        witness = self.one("witnesses", witness_key=g1["nearest_witness_key"])
        self.assertEqual([c["report_type"] for c in witness["timestamp_candidates"]], ["FM-12", "FM-16", "FM-15"])
        self.assertEqual(sorted(witness["selected_by"]),
                         ["401000001:AFTER", "401000001:BEFORE", "401000001:NEAREST"])
        g2 = self.one("pilots", pilot_key="401000002")
        self.assertEqual((g2["verified_before_delta_minutes"], g2["verified_after_delta_minutes"]), (30.0, 30.0))
        self.assertEqual(g2["nearest_witness_key"], g2["before_witness_key"])
        self.assertIsNone(g2["verified_nearest_temperature_c"])
        self.assertEqual(g2["verified_nearest_raw_tmp"], "+9999,9")
        self.assertEqual((g2["verified_nearest_dew_point_quality"], g2["dew_point_quality_meaning"]),
                         ("3", "ERRONEOUS"))
        self.assertIsNone(g2["verified_nearest_wind_direction_degrees"])
        self.assertEqual(g2["verified_nearest_precipitation_raw_json"], '{"AA1":"01,0005,9,1"}')
        self.assertEqual(g2["nearest_precipitation_groups"], 1)
        self.assertIn("NEAREST_VALUE_FLAGGED_SUSPECT_OR_ERRONEOUS", g2["unsupported_reasons"])
        self.assertIn("CATALOG_DOME_FLAG_ROOF_STATE_UNKNOWN", g2["unsupported_reasons"])
        self.assertIn("PROVIDER_START_TIME_TBD", g2["unsupported_reasons"])
        g5 = self.one("pilots", pilot_key="401000005")
        self.assertEqual(g5["temperature_quality_meaning"], "SUSPECT_NCEI_SOURCE")

    def test_summary_of_day_calm_wind_and_visibility_sentinel(self) -> None:
        g3 = self.one("pilots", pilot_key="401000003")
        self.assertEqual((g3["verified_nearest_report_type"], g3["nearest_report_meaning"],
                          g3["verified_nearest_decoded_common_field_count"]),
                         ("SOD  ", "SUMMARY_OF_DAY_NOT_INSTANTANEOUS", 0))
        self.assertIn("NEAREST_OBSERVATION_IS_SUMMARY_NOT_INSTANTANEOUS", g3["unsupported_reasons"])
        self.assertIn("NEAREST_OBSERVATION_HAS_NO_DECODED_COMMON_FIELD", g3["unsupported_reasons"])
        calm = self.one("witnesses", witness_key=g3["after_witness_key"])
        self.assertEqual((calm["row_wind_direction_degrees"], calm["row_wind_speed_mps"], calm["row_visibility_m"],
                          calm["row_temperature_quality"]), (None, 0.0, None, "C"))

    def test_calendar_boundaries_and_missing_candidates(self) -> None:
        g4 = self.one("pilots", pilot_key="401000004")
        contest = self.one("contests", contest_key="ncaa:1006")
        self.assertEqual((g4["original_calendar_year"], contest["contest_calendar_year"]), (2025, 2024))
        self.assertEqual((g4["verified_before_observed_at_utc"], g4["before_missing_reason"]),
                         (None, "NO_EARLIER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE"))
        self.assertTrue(g4["adjacent_calendar_year_captured"])
        self.assertEqual(g4["station_year_key"], f"2025|{fx.S3}")
        g5 = self.one("pilots", pilot_key="401000005")
        self.assertEqual((g5["verified_after_observed_at_utc"], g5["after_missing_reason"]),
                         (None, "NO_LATER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE"))
        self.assertTrue(g5["adjacent_calendar_year_captured"])
        self.assertEqual(contest["before_present"], False)

    def test_station_years_and_witnesses(self) -> None:
        s1 = self.one("station_years", station_year_key=f"2024|{fx.S1}")
        self.assertEqual((s1["data_rows"], s1["malformed_rows"], s1["distinct_timestamps"],
                          s1["duplicate_timestamp_rows"]), (7, 1, 5, 2))
        self.assertEqual(s1["sentinel_rows"]["temperature"], 1)
        self.assertEqual(s1["sentinel_rows"]["sea_level_pressure"], 3)
        self.assertEqual(s1["precipitation_rows"], 1)
        self.assertEqual(s1["pilot_keys"], ["401000001", "401000002"])
        self.assertEqual((s1["candidate_station_elevation_m"], s1["station_reference_state"]),
                         (101.5, "CANDIDATE_REVIEW_REQUIRED"))
        kinds = {}
        for w in self.records["witnesses"]:
            kinds[w["witness_kind"]] = kinds.get(w["witness_kind"], 0) + 1
        self.assertEqual(kinds["INPUT"], 12)
        self.assertEqual(kinds["RAW_FILE"], 4)
        for w in self.records["witnesses"]:
            if w["witness_kind"] == "SELECTED_RAW_ROW":
                self.assertTrue(w["selected_by"])
                self.assertEqual(w["raw_fields"]["STATION"], w["station_id"].replace("-", ""))

    def test_clocks_rights_and_labels(self) -> None:
        for table in (*we.RECORD_TABLES, "census"):
            rows = self.records[table] if table != "census" else [self.records["census"]]
            for record in rows:
                self.assertEqual(record["pit_eligibility"], "PIT_NOT_ADMITTED")
                self.assertEqual(record["predictive_skill"], "NOT_ESTABLISHED")
        for s in self.records["station_years"]:
            self.assertEqual(s["capture_manifest_issued_at_utc"], "2026-08-12T09:15:00Z")
            self.assertEqual(s["acquisition_issued_at_utc"], "2026-08-12T08:55:00Z" if s["calendar_year"] == 2024
                             else None)
            self.assertEqual((s["rights_decision_id"], s["source_publication_time"]),
                             ("PRIVATE-RESEARCH-SRC-029", "NOT_ESTABLISHED"))
        contest = self.one("contests", contest_key="ncaa:1001")
        self.assertEqual(contest["association_clock_utc"], "2024-09-07T18:00:00.000Z")
        self.assertEqual(contest["association_clock"], "PROVIDER_SCHEDULED_TIME_NOT_OFFICIAL_ACTUAL_KICKOFF")
        for pilot in self.records["pilots"]:
            self.assertEqual(pilot["kickoff_clock_agreement"], "AGREE")

    def test_tampered_or_missing_inputs_are_refused_by_the_builder(self) -> None:
        for name, mutate, code in (
                ("raw", lambda w: _append(w["data_root"] / w["captures"][0]["raw_relative_path"]),
                 "WEATHER_RAW_IDENTITY_MISMATCH"),
                ("pilot", lambda w: _append(w["pilot"]), "WEATHER_INPUT_TAMPERED"),
                ("missing", lambda w: w["provider"].unlink(), "WEATHER_INPUT_MISSING")):
            with self.subTest(name):
                base = Path(tempfile.mkdtemp(prefix="t-", dir=self.base))
                world = copy.deepcopy(self.world)
                shutil.copytree(self.world["data_root"], base / "d")
                for key in ("pilot", "provider"):
                    world[key] = base / "d" / Path(self.world[key]).relative_to(self.world["data_root"])
                world["data_root"] = base / "d"
                mutate(world)
                code_, _r, err = fx.run_build(self.contract_path, world, base / "o")
                self.assertEqual((code_, fx.refusal(err)), (2, code))


def _append(path: Path) -> None:
    with Path(path).open("ab") as handle:
        handle.write(b"\n")


# --------------------------------------------------------------------------------------------- determinism

class DeterminismTests(World):
    def test_order_chunk_and_resume_variants_reproduce_every_byte(self) -> None:
        want = self.result["database_identity"]
        for name, extra in (("reverse", ("--input-order", "reverse")), ("shuffle", ("--input-order", "shuffle:7")),
                            ("chunk1", ("--chunk-size", "1", "--checkpoint-dir", str(self.base / "k1"))),
                            ("chunk3", ("--chunk-size", "3", "--checkpoint-dir", str(self.base / "k3")))):
            with self.subTest(name):
                code, result, err = fx.run_build(self.contract_path, self.world, self.base / f"d-{name}", *extra)
                self.assertEqual(code, 0, err)
                self.assertEqual(result["database_identity"], want)
        k = self.base / "kir"
        code, result, err = fx.run_build(self.contract_path, self.world, self.base / "d-ir", "--chunk-size", "1",
                                         "--checkpoint-dir", str(k), "--stop-after-chunks", "2")
        self.assertEqual((code, result["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        code, result, err = fx.run_build(self.contract_path, self.world, self.base / "d-ir", "--chunk-size", "1",
                                         "--checkpoint-dir", str(k), "--resume")
        self.assertEqual((code, result["database_identity"]), (0, want), err)

    def test_an_existing_identity_is_verified_and_a_collision_refused(self) -> None:
        code, result, err = fx.run_build(self.contract_path, self.world, self.base / "o")
        self.assertEqual((code, result["state"]), (0, "ALREADY_PRESENT_IDENTICAL"))
        out = self.base / "col"
        shutil.copytree(self.base / "o", out)
        target = out / "canonical" / fx.POP / "sha256" / self.result["database_identity"] / we.DB_FILE
        data = target.read_bytes()
        target.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        code, _r, err = fx.run_build(self.contract_path, self.world, out)
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"))


# --------------------------------------------------------------------------------------------- query

class QueryTests(World):
    def test_every_grain_serves_its_complete_collection(self) -> None:
        for grain, table in we.GRAINS.items():
            code, doc, err = self.serve("--grain", grain, "--all")
            with self.subTest(grain):
                self.assertEqual(code, 0, err)
                self.assertEqual((doc["total"], doc["returned"]), (len(self.records[table]), len(self.records[table])))
                self.assertEqual([r[we.KEY_FIELDS[table]] for r in doc["rows"]],
                                 [r[we.KEY_FIELDS[table]] for r in self.records[table]])
                self.assertEqual((doc["pit_eligibility"], doc["season_scope_state"]),
                                 ("PIT_NOT_ADMITTED", "RETROSPECTIVE_SEASON_2024"))

    def test_selectors_intersect_page_and_return_empty_for_unknown_or_disjoint(self) -> None:
        def keys(*argv):
            code, doc, err = self.serve(*argv)
            self.assertEqual(code, 0, err)
            return doc["total"], [r[we.KEY_FIELDS[we.GRAINS[argv[1]]]] for r in doc["rows"]]
        self.assertEqual(keys("--grain", "contest-weather", "--station", fx.S1, "--all"),
                         (2, ["ncaa:1001", "ncaa:1002"]))
        self.assertEqual(keys("--grain", "contest-weather", "--station", fx.S1, "--contest", "ncaa:1002", "--all"),
                         (1, ["ncaa:1002"]))
        self.assertEqual(keys("--grain", "contest-weather", "--station", fx.S2, "--contest", "ncaa:1002"), (0, []))
        self.assertEqual(keys("--grain", "contest-weather", "--provider-game", "401000003"), (0, []))
        self.assertEqual(keys("--grain", "pilot-weather", "--provider-game", "401000003"), (1, ["401000003"]))
        self.assertEqual(keys("--grain", "pilot-weather", "--contest", "ncaa:1003"), (0, []))
        self.assertEqual(keys("--grain", "contest-weather", "--contest", "ncaa:999999"), (0, []))
        self.assertEqual(keys("--grain", "station-year", "--station", "999999-99999"), (0, []))
        code, doc, _e = self.serve("--grain", "pilot-weather", "--limit", "2", "--offset", "1")
        self.assertEqual((doc["total"], doc["returned"], doc["next_offset"]), (5, 2, 3))
        code, doc, _e = self.serve("--grain", "source-witness", "--season", "2023")
        self.assertEqual((code, doc["total"], doc["rows"], doc["season_scope_state"]),
                         (0, 0, [], "SEASON_OUTSIDE_RELEASE"))
        code, doc, _e = self.serve("--grain", "source-witness", "--station", fx.S2, "--all")
        self.assertTrue(doc["rows"] and all(r["station_id"] == fx.S2 for r in doc["rows"]))

    def test_misuse_is_refused_before_any_file_is_read(self) -> None:
        missing = self.base / "never" / "canonical" / fx.POP / "sha256" / ("0" * 64) / we.DB_FILE
        for argv, code in (
                (["--grain", "station-year", "--contest", "ncaa:1001"], "FILTER_NOT_APPLICABLE"),
                (["--grain", "source-witness", "--provider-game", "401000001"], "FILTER_NOT_APPLICABLE"),
                (["--grain", "contest-weather", "--contest", "1001"], "CONTEST_INVALID"),
                (["--grain", "contest-weather", "--contest", "cfbd:401000001"], "CONTEST_INVALID"),
                (["--grain", "pilot-weather", "--provider-game", "src002:2024:0001"], "PROVIDER_GAME_INVALID"),
                (["--grain", "pilot-weather", "--provider-game", "9" * 13], "PROVIDER_GAME_INVALID"),
                (["--grain", "station-year", "--station", "72243012960"], "STATION_INVALID"),
                (["--grain", "station-year", "--season", "2024.0"], "SEASON_INVALID"),
                (["--grain", "station-year", "--season", "9" * 30], "SEASON_INVALID"),
                (["--grain", "station-year", "--limit", "-1"], "NEGATIVE_LIMIT"),
                (["--grain", "station-year", "--limit", "ten"], "LIMIT_INVALID"),
                (["--grain", "station-year", "--offset", "-3"], "NEGATIVE_OFFSET"),
                (["--grain", "station-year", "--require-pit"], "WEATHER_PIT_NOT_ADMITTED"),
                (["--grain", "station-year", "--as-of", "2024-09-01"], "ARGUMENT_INVALID"),
                (["--grain", "forecast-weather"], "ARGUMENT_INVALID"),
                (["--grain", "station-year", "--expect-identity", "abc"], "STALE_WEATHER_IDENTITY")):
            with self.subTest(argv):
                self.assertEqual(self.serve(*argv, database=missing)[2], code)
        self.assertFalse(missing.parent.exists())
        self.assertEqual(self.serve("--grain", "station-year", database=missing)[2], "WEATHER_DATABASE_MISSING")
        self.assertFalse(missing.parent.exists())

    def test_the_release_is_read_only_and_nothing_is_created(self) -> None:
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.db.parent.iterdir()}
        for grain in we.GRAINS:
            self.assertEqual(self.serve("--grain", grain, "--all")[0], 0)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.db.parent.iterdir()}
        self.assertEqual(before, after)
        loose = self.base / "loose" / we.DB_FILE
        loose.parent.mkdir(exist_ok=True)
        loose.write_bytes(b"not a release")
        self.assertEqual(self.serve("--grain", "station-year", database=loose)[2], "WEATHER_LOCATION_INVALID")

    def test_rehoused_long_and_explicit_manifest_locations_serve_identically(self) -> None:
        want = self.serve("--grain", "pilot-weather", "--all")[1]
        identity = self.result["database_identity"]
        long_root = self.base.joinpath(*[f"rehoused-weather-component-{c}-" + c * 30 for c in "abcd"])
        first = self.base / ("rehoused-weather-component-a-" + "a" * 30)
        self.addCleanup(shutil.rmtree, "\\\\?\\" + os.path.abspath(first) if os.name == "nt" else first, True)
        for kind in ("canonical", "manifests"):
            src = self.base / "o" / kind / fx.POP / "sha256" / identity
            dst = long_root / kind / fx.POP / "sha256" / identity
            os.makedirs("\\\\?\\" + os.path.abspath(dst) if os.name == "nt" else dst)
            for item in os.listdir(src):
                shutil.copyfile(src / item, "\\\\?\\" + os.path.abspath(dst / item) if os.name == "nt" else dst / item)
        long_db = long_root / "canonical" / fx.POP / "sha256" / identity / we.DB_FILE
        self.assertGreater(len(str(long_db)), 260)
        manifest = fx.manifest_of(self.db)
        for name, database, extra in (("long", long_db, []),
                                      ("long_extended", Path("\\\\?\\" + os.path.abspath(long_db)) if os.name == "nt"
                                       else long_db, []),
                                      ("explicit_manifest", self.db, ["--manifest", str(manifest)])):
            with self.subTest(name):
                code, doc, err = self.serve("--grain", "pilot-weather", "--all", *extra, database=database)
                self.assertEqual(code, 0, err)
                self.assertEqual(doc["rows"], want["rows"])
                self.assertEqual(doc["release_identity"], want["release_identity"])

    def test_relative_and_special_character_locations_serve_identically(self) -> None:
        want = self.serve("--grain", "station-year", "--all")[1]
        identity = self.result["database_identity"]
        special = self.base / "spé cial ☃ [x]"
        for kind in ("canonical", "manifests"):
            shutil.copytree(self.base / "o" / kind / fx.POP / "sha256" / identity,
                            special / kind / fx.POP / "sha256" / identity)
        db = special / "canonical" / fx.POP / "sha256" / identity / we.DB_FILE
        self.assertEqual(self.serve("--grain", "station-year", "--all", database=db)[1]["rows"], want["rows"])
        cwd = os.getcwd()
        try:
            os.chdir(db.parent)
            self.assertEqual(self.serve("--grain", "station-year", "--all", database=Path(we.DB_FILE))[1]["rows"],
                             want["rows"])
        finally:
            os.chdir(cwd)

    def test_a_junction_location_serves_identically(self) -> None:
        """A directory junction (Windows; a directory symlink elsewhere) naming the identity directories is a
        legitimate local spelling of the same release files."""
        want = self.serve("--grain", "station-year", "--all")[1]
        identity = self.result["database_identity"]
        root = self.base / "junction-root"
        for kind in ("canonical", "manifests"):
            link = root / kind / fx.POP / "sha256" / identity
            link.parent.mkdir(parents=True)
            target = self.base / "o" / kind / fx.POP / "sha256" / identity
            if os.name == "nt":
                import _winapi  # noqa: PLC0415 - Windows CPython; the junction is the spelling under test
                _winapi.CreateJunction(str(target), str(link))
                self.addCleanup(os.rmdir, link)
            else:
                os.symlink(target, link, target_is_directory=True)
                self.addCleanup(os.unlink, link)
        db = root / "canonical" / fx.POP / "sha256" / identity / we.DB_FILE
        code, doc, err = self.serve("--grain", "station-year", "--all", database=db)
        self.assertEqual(code, 0, err)
        self.assertEqual((doc["rows"], doc["release_identity"]), (want["rows"], want["release_identity"]))

    def test_the_module_front_matches_the_function_front(self) -> None:
        argv = ["--database", str(self.db), "--grain", "contest-weather", "--station", fx.S1]
        script = ("import json,sys;from aggie_analytics.weather_evidence import query as q;"
                  "a=json.loads(open(sys.argv[1],encoding='utf-8').read());sys.exit(q.main(sys.argv[2:],anchors=a))")
        anchors_file = self.base / "anchors.json"
        if not anchors_file.exists():
            anchors_file.write_text(json.dumps(self.anchors), encoding="utf-8")
        env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])}
        proc = subprocess.run([sys.executable, "-B", "-c", script, str(anchors_file), *argv], capture_output=True,
                              env=env, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        code, doc, _e = self.serve(*argv[2:])
        self.assertEqual(json.loads(proc.stdout.decode("utf-8")), doc)
        refused = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.weather_evidence.query", *argv,
                                  "--require-pit"], capture_output=True, env=env, check=False)
        self.assertEqual((refused.returncode, json.loads(refused.stderr.decode("utf-8").splitlines()[-1])["refused"]),
                         (2, "WEATHER_PIT_NOT_ADMITTED"))
        self.assertNotIn(b"Traceback", refused.stderr)


# --------------------------------------------------------------------------------------------- coordinated forgeries

class ForgingWorld(World):
    """A Forger over the tiny release (no tests of its own)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.base / f"f-{cls.__name__}", cls.anchors)
        cls.counter = 0

    def refused(self, path: Path, anchors: dict | None = None) -> str | None:
        return self.serve("--grain", "station-year", "--limit", "1", database=path, anchors=anchors)[2]

    def forge(self, **kwargs) -> Path:
        type(self).counter += 1
        return self.forger.forge(f"f{type(self).counter}", **kwargs)

    def resorted(self, mutate):
        """``mutate`` followed by the canonical record order (a coordinated forgery reaches its own rule, never the
        order rule)."""
        sources = we.source_order(self.anchors)

        def run(tables):
            mutate(tables)
            for table in we.RECORD_TABLES:
                tables[table].sort(key=lambda r: we._order_key(table, r, sources))
        return run

    @staticmethod
    def first(tables: dict, table: str, **match) -> dict:
        return next(r for r in tables[table] if all(r.get(k) == v for k, v in match.items()))

    def assert_cases(self, cases: dict) -> None:
        for name, (mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forge(records=mutate)), code)


class ForgeryTests(ForgingWorld):
    def test_collection_forgeries(self) -> None:
        def extra_contest(t):
            r = copy.deepcopy(self.first(t, "contests", contest_key="ncaa:1004"))
            r.update(contest_key="ncaa:1005", ncaa_contest_id="1005")
            t["contests"].append(r)

        def substitute(t):
            self.first(t, "contests", contest_key="ncaa:1004").update(contest_key="ncaa:1008", ncaa_contest_id="1008")

        def reorder(t):
            t["pilots"][0], t["pilots"][1] = t["pilots"][1], t["pilots"][0]

        self.assert_cases({
            "omitted FCS-only contest": (lambda t: t["contests"].remove(self.first(t, "contests",
                                                                                 contest_key="ncaa:1004")),
                                         "WEATHER_CONTEST_ROW_MISSING"),
            "extra contest": (extra_contest, "WEATHER_CONTEST_ROW_EXTRA"),
            "count-preserving substitution": (substitute, "WEATHER_CONTEST_ROW_MISSING"),
            "duplicate pilot": (lambda t: t["pilots"].insert(1, t["pilots"][0]), "WEATHER_DUPLICATE_ROW"),
            "reordered pilots": (reorder, "WEATHER_ORDER_MISMATCH"),
            "omitted station-year": (lambda t: t["station_years"].pop(0), "WEATHER_STATION_YEAR_ROW_MISSING"),
            "omitted source witness": (lambda t: t["witnesses"].pop(0), "WEATHER_WITNESS_ROW_MISSING")})

    def test_raw_decoding_forgeries(self) -> None:
        def row(t, game, role):
            pilot = self.first(t, "pilots", pilot_key=game)
            return self.first(t, "witnesses", witness_key=pilot[f"{role}_witness_key"])

        self.assert_cases({
            "sentinel changed to zero": (lambda t: row(t, "401000002", "nearest").update(row_temperature_c=0.0),
                                         "WEATHER_DECODE_MISMATCH"),
            "units changed": (lambda t: row(t, "401000001", "nearest").update(row_temperature_c=262.0),
                              "WEATHER_DECODE_MISMATCH"),
            "quality changed": (lambda t: row(t, "401000002", "nearest").update(row_dew_point_quality="1"),
                                "WEATHER_DECODE_MISMATCH"),
            "precipitation changed": (lambda t: row(t, "401000002", "nearest").update(
                row_precipitation_raw_json='{"AA1":"01,0050,9,1"}'), "WEATHER_DECODE_MISMATCH"),
            "raw field with an invented column": (lambda t: row(t, "401000001", "nearest")["raw_fields"].update(
                HOURLY_TOTAL="5"), "WEATHER_WITNESS_MISMATCH"),
            "visibility sentinel decoded": (lambda t: row(t, "401000003", "after").update(row_visibility_m=999999.0),
                                            "WEATHER_DECODE_MISMATCH")})

    def test_selection_forgeries(self) -> None:
        def demote(t):
            pilot = self.first(t, "pilots", pilot_key="401000001")
            w = self.first(t, "witnesses", witness_key=pilot["nearest_witness_key"])
            w["timestamp_candidates"] = [w["timestamp_candidates"][2], *w["timestamp_candidates"][:2]]

        def tie(t):
            pilot = self.first(t, "pilots", pilot_key="401000002")
            after = self.first(t, "witnesses", witness_key=pilot["after_witness_key"])
            pilot["nearest_witness_key"] = pilot["after_witness_key"]
            after["selected_by"] = sorted(after["selected_by"] + ["401000002:NEAREST"])
            before = self.first(t, "witnesses", witness_key=pilot["before_witness_key"])
            before["selected_by"] = [s for s in before["selected_by"] if s != "401000002:NEAREST"]

        self.assert_cases({
            "duplicate ranking": (demote, "WEATHER_DUPLICATE_RANKING_INVALID"),
            "tie selection": (tie, "WEATHER_TIE_RULE_VIOLATED"),
            "distance changed": (lambda t: self.first(t, "pilots", pilot_key="401000003").update(
                verified_after_delta_minutes=45.0), "WEATHER_DELTA_MISMATCH"),
            "nearest value not its witness": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                verified_nearest_sea_level_pressure_hpa=1013.0), "WEATHER_NEAREST_MISMATCH"),
            "discrepancy hidden": (lambda t: self.first(t, "pilots", pilot_key="401000005").update(
                discrepant_fields=[], reconstruction_state="REPRODUCED_EXACT"), "WEATHER_DISCREPANCY_MISMATCH"),
            "missing reason invented": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                before_missing_reason="NO_EARLIER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE"),
                "WEATHER_MISSING_REASON_INVALID")})

    def test_transplant_forgeries(self) -> None:
        def witness_transplant(t):
            pilot = self.first(t, "pilots", pilot_key="401000004")
            self.first(t, "witnesses", witness_key=pilot["after_witness_key"])["station_year_key"] = f"2024|{fx.S3}"

        self.assert_cases({
            "pilot to another station-year": (lambda t: self.first(t, "pilots", pilot_key="401000004").update(
                station_year_key=f"2024|{fx.S3}"), "WEATHER_TRANSPLANT"),
            "row witness to another year": (self.resorted(witness_transplant), "WEATHER_KEY_INVALID"),
            "game transplant": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                provider_game_id="401000002"), "WEATHER_PROVIDER_JOIN_MISMATCH"),
            "station-year capture transplant": (lambda t: t["station_years"][0].update(
                raw_sha256=t["station_years"][1]["raw_sha256"]), "WEATHER_STATION_YEAR_MISMATCH")})

    def test_clock_flag_relation_and_association_forgeries(self) -> None:
        def promote_unpromoted(t):
            self.first(t, "contests", contest_key="ncaa:1003").update(relation_state="PROMOTED_ONE_TO_ONE",
                                                                      pilot_key="401000003")

        self.assert_cases({
            "false capture clock": (lambda t: t["station_years"][0].update(
                capture_manifest_issued_at_utc="2024-08-01T00:00:00Z"), "WEATHER_SOURCE_CLOCK_MISMATCH"),
            "false association clock": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                provider_scheduled_start_utc="2024-09-07T17:00:00.000Z"), "WEATHER_SOURCE_CLOCK_MISMATCH"),
            "false PIT flag": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                original_historical_pit_eligible=True), "WEATHER_PIT_CLAIM_INVALID"),
            "false forecast flag": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                original_observed_weather_substitution=True), "WEATHER_FORECAST_CLAIM_INVALID"),
            "false roof flag": (lambda t: self.first(t, "pilots", pilot_key="401000002").update(
                original_dome_observation_feature_eligible=True), "WEATHER_ROOF_CLAIM_INVALID"),
            "PIT label": (lambda t: t["contests"][0].update(pit_eligibility="PIT_ADMITTED"),
                          "WEATHER_PIT_CLAIM_INVALID"),
            "promoted unpromoted relation": (promote_unpromoted, "WEATHER_RELATION_MISMATCH"),
            "missing evidence as zero": (lambda t: self.first(t, "contests", contest_key="ncaa:1004").update(
                temperature_c=0.0), "WEATHER_ASSOCIATION_MISMATCH"),
            "support state invented": (lambda t: self.first(t, "contests", contest_key="ncaa:1004").update(
                weather_support_state="ASSOCIATED_CANDIDATE_STATION_OBSERVATION"), "WEATHER_SUPPORT_STATE_INVALID"),
            "reason removed": (lambda t: self.first(t, "contests", contest_key="ncaa:1001").update(
                unsupported_reasons=[]), "WEATHER_UNSUPPORTED_REASON_MISMATCH"),
            "quality meaning promoted": (lambda t: self.first(t, "pilots", pilot_key="401000002").update(
                dew_point_quality_meaning="PASSED_ALL_QUALITY_CONTROL_CHECKS"), "WEATHER_MEANING_MISMATCH"),
            "score field": (lambda t: t["contests"][0].update(a_points=28), "WEATHER_FORBIDDEN_FIELD_PRESENT"),
            "parent site changed": (lambda t: t["contests"][0].update(site="NEUTRAL"),
                                    "WEATHER_PARENT_FIELD_MISMATCH"),
            "census changed": (lambda t: t["census"][0].update(within_30_minutes=99), "WEATHER_CENSUS_MISMATCH"),
            "original pilot value altered": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                original_station_name="ELSEWHERE"), "WEATHER_ORIGINAL_ALTERED")})

    def test_meta_identity_manifest_forgeries_and_valid_controls(self) -> None:
        identity = self.result["database_identity"]
        cases = {
            "labels": (dict(meta={"labels": {**we.LABELS, "pit_eligibility": "PIT_ADMITTED"}}),
                       "WEATHER_PIT_CLAIM_INVALID"),
            "rules": (dict(meta={"rules": {"other": True}}), "WEATHER_RULES_CLAIM_INVALID"),
            "inputs": (dict(meta={"inputs": {"inputs": {}}}), "WEATHER_PARENT_MISMATCH"),
            "identity document": (dict(document={"population": "other"}), "WEATHER_SCHEMA_UNSUPPORTED"),
            "tampered bytes": (dict(after_blocks=[("UPDATE meta SET value = value || ' ' WHERE key = ?",
                                                   ("contract_id",))], document={"outputs": {we.DB_FILE: "0" * 64}}),
                               "WEATHER_DATABASE_TAMPERED"),
            "manifest members": (dict(manifest_patch={"extra": 1}), "WEATHER_MANIFEST_MALFORMED"),
            "wrong identity directory": (dict(identity_override="1" * 64), "WEATHER_IDENTITY_MISMATCH")}
        for name, (kwargs, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forge(**kwargs)), code)
        changed = self.forge(records=lambda t: t["contests"][0].update(a_team_name="Team ☃"))
        self.assertEqual(self.refused(changed, anchors=self.profiled), "WEATHER_PARENT_FIELD_MISMATCH")
        identical = self.forge(provenance={"note": "provenance only"})
        self.assertIsNone(self.refused(identical))
        self.assertIsNone(self.refused(identical, anchors=self.profiled))
        self.assertEqual(self.serve("--grain", "station-year", database=identical)[1]["release_identity"], identity)
        census_bump = self.forge(records=lambda t: t["witnesses"][-1].update(raw_row_sha256="f" * 64))
        self.assertIsNone(self.refused(census_bump))
        self.assertEqual(self.refused(census_bump, anchors=self.profiled), "WEATHER_PROFILE_MISMATCH")


class MalformedJsonBoundaryTests(ForgingWorld):
    """Valid JSON can still be malformed data: lone surrogates, deep nesting, non-finite and oversized numbers refuse
    with their boundary code and reason, never a traceback (the C58/C59 boundary rule)."""

    def test_record_lines_with_malformed_json_values(self) -> None:
        deep = "[" * 4000 + "]" * 4000
        for name, mutate, reason in (
                ("lone surrogate", lambda r: r["contests"].__setitem__(0, r["contests"][0].replace(
                    '"a_team_name":"', '"a_team_name":"\\ud800', 1)), "JSON_LONE_SURROGATE"),
                ("deep nesting", lambda r: r["contests"].__setitem__(0, r["contests"][0].replace(
                    '"site":"HOME_A"', f'"site":{deep}', 1)), "JSON_NESTING_TOO_DEEP"),
                ("non-finite", lambda r: r["pilots"].__setitem__(0, r["pilots"][0].replace(
                    '"original_distance_km":', '"original_distance_km":NaN,"x":', 1)), "JSON_NONFINITE_NUMBER"),
                ("huge integer", lambda r: r["station_years"].__setitem__(0, r["station_years"][0].replace(
                    '"data_rows":', '"data_rows":' + "9" * 5000 + ',"y":', 1)), "JSON_INTEGER_TOO_LONG")):
            with self.subTest(name):
                path = self.forge(lines=mutate, rehash_content=False)
                code, _doc, err = fx.query(self.anchors, path, "--grain", "station-year")
                self.assertEqual((code, fx.refusal(err)), (2, "WEATHER_RECORD_MALFORMED"))
                self.assertIn(reason, err)
                self.assertNotIn("Traceback", err)

    def test_meta_and_manifest_with_malformed_json(self) -> None:
        deep = "[" * 4000 + "]" * 4000
        meta_path = self.forge(meta={"rules": '{"a": NaN}'})
        self.assertEqual(self.refused(meta_path), "WEATHER_META_MALFORMED")
        manifest_path = self.forge(manifest_text=lambda text: text.replace('"provenance": {',
                                                                           f'"provenance": {{"deep": {deep}, ', 1))
        code, _doc, err = fx.query(self.anchors, manifest_path, "--grain", "station-year")
        self.assertEqual((code, fx.refusal(err)), (2, "WEATHER_MANIFEST_MALFORMED"))
        self.assertNotIn("Traceback", err)
        surrogate = self.forge(manifest_text=lambda text: text.replace('"provenance": {',
                                                                       '"provenance": {"s": "\\udc00", ', 1))
        code, _doc, err = fx.query(self.anchors, surrogate, "--grain", "station-year")
        self.assertEqual((code, fx.refusal(err)), (2, "WEATHER_MANIFEST_MALFORMED"))
        self.assertIn("JSON_LONE_SURROGATE", err)


class NumericAndKeyDomainTests(ForgingWorld):
    def test_types_keys_and_nested_values_reach_their_rules(self) -> None:
        self.assert_cases({
            "boolean for integer": (lambda t: t["contests"][0].update(competitive=True), "WEATHER_FIELD_TYPE_INVALID"),
            "float for integer": (lambda t: t["station_years"][0].update(calendar_year=2024.0),
                                  "WEATHER_FIELD_TYPE_INVALID"),
            "integer for float": (lambda t: self.first(t, "pilots", pilot_key="401000001").update(
                verified_before_delta_minutes=0), "WEATHER_FIELD_TYPE_INVALID"),
            "nested scalar": (lambda t: t["contests"][0].update(site={"value": "HOME_A"}),
                              "WEATHER_FIELD_TYPE_INVALID"),
            "malformed contest key": (lambda t: self.first(t, "contests", contest_key="ncaa:1004").update(
                contest_key="ncaa:1004x"), "WEATHER_CONTEST_ROW_MISSING"),
            "huge temperature": (lambda t: self.first(t, "witnesses", witness_kind="SELECTED_RAW_ROW").update(
                row_temperature_c=1e308), "WEATHER_DECODE_MISMATCH"),
            "huge row number": (self.resorted(lambda t: self.first(t, "witnesses", witness_kind="SELECTED_RAW_ROW")
                                              .update(source_row_number=10 ** 30)), "WEATHER_KEY_INVALID"),
            "candidate list member type": (lambda t: self.first(t, "witnesses", witness_kind="SELECTED_RAW_ROW")[
                "timestamp_candidates"][0].update(source_row_number="2"), "WEATHER_FIELD_TYPE_INVALID")})


# --------------------------------------------------------------------------------------------- the genuine release

class MountedGenuineWeatherTests(unittest.TestCase):
    def test_genuine_release_serves_every_population(self) -> None:
        profile = we.WEATHER_PROFILE
        data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        if profile is None or not data_root or not Path(data_root).is_dir():
            self.skipTest("no pinned canonical weather profile or no mounted data root")
        db = Path(data_root) / "canonical" / we.POPULATION / "sha256" / profile["database_identity"] / we.DB_FILE
        if not db.is_file():
            self.skipTest("the pinned canonical weather release is not present under the mounted data root")
        with we.WeatherEvidence(db, expect_identity=profile["database_identity"]) as reader:
            self.assertEqual(reader.content_identity, profile["content_identity"])
            census = reader.census
            self.assertEqual((census["contests"], census["pilots"], census["station_years"]), (1672, 920, 157))
            self.assertEqual((census["promoted_relations"], census["unpromoted_relations"],
                              census["parents_without_promoted_weather"]), (882, 38, 790))
            self.assertEqual((census["within_30_minutes"], census["within_30_and_promoted"]), (882, 845))
            self.assertEqual(census["pilots_by_calendar_year"], {"2024": 909, "2025": 11})
            self.assertEqual(census["raw_bytes"], 1251673376)
            answer = reader.query("contest-weather", contest="ncaa:5361392")
            row = answer["rows"][0]
            self.assertEqual((answer["total"], row["relation_state"], row["station_id"], row["contest_date"]),
                             (1, "PROMOTED_ONE_TO_ONE", "747460-03904", "2024-08-31"))
            unsupported = reader.query("contest-weather", contest="ncaa:5365269")["rows"][0]
            self.assertEqual((unsupported["relation_state"], unsupported["temperature_c"], unsupported["station_id"]),
                             ("NO_PROVIDER_ROW", None, None))
            self.assertEqual(reader.query("station-year", season=2024)["total"], 157)


if __name__ == "__main__":
    unittest.main()
