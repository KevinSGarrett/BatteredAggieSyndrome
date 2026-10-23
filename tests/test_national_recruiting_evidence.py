"""National recruiting evidence 2010-2017 (BAT-735, Cycle #64 TP64-A01).

Synthetic tiny worlds only (``tests/recruiting_evidence_fixture.py``: an invented but complete retained-source closure
whose registry hashes are restated independently): every person, program, value and time rule, the 34-cell partition
census and source witnesses, filtered summaries, determinism and create-only materialization, the explicit
``--recruiting-evidence`` routing with the one appended legacy help paragraph, the frozen refusal precedence and
applicability, coordinated own-rule forgeries (and the pinned profile against fully coordinated value forgeries),
malformed JSON, literal local locations, native aliases and raw controls. The mounted genuine case runs only when the
private data root and the pinned canonical profile are present."""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

import recruiting_evidence_fixture as fx  # noqa: E402
from aggie_analytics.personnel_evidence import query as pq  # noqa: E402
from aggie_analytics.personnel_evidence import recruiting as rc  # noqa: E402
from aggie_analytics.personnel_evidence import recruiting_build as rb  # noqa: E402

STATE: dict = {}
TAB, LF, US, DEL, NEL, APC, NBSP = chr(9), chr(10), chr(31), chr(127), chr(0x85), chr(0x9F), chr(0xA0)
HIGH, LOW = chr(0xD800), chr(0xDC00)
CC_POINTS = (*range(0x20), *range(0x7F, 0xA0))


def setUpModule() -> None:
    base = Path(tempfile.mkdtemp(prefix="rce-t-"))
    world = fx.build_world(base / "w")
    contract_doc = fx.contract_for(world)
    contract = fx.write_contract(base / "contract.json", contract_doc)
    anchors = fx.contract_anchors(contract)
    code, result, err = fx.run_build(contract, world, base / "out")
    if code != 0:
        raise AssertionError(f"the fixture build refused: {err}")
    STATE.update(base=base, world=world, contract=contract, contract_doc=contract_doc, anchors=anchors,
                 result=result, db=fx.database_of(result))


def tearDownModule() -> None:
    shutil.rmtree(STATE["base"], ignore_errors=True)


def ask(*argv: str, db=None, anchors=None):
    return fx.query(STATE["anchors"] if anchors is None else anchors, STATE["db"] if db is None else db, *argv)


def rows(grain: str, *argv: str) -> list[dict]:
    code, doc, err = ask("--grain", grain, "--all", *argv)
    if code != 0:
        raise AssertionError(err)
    return doc["rows"]


def quals() -> dict[str, dict]:
    return {q["source_recruit_id"]: q for q in rows("recruiting-qualification")}


def observations() -> dict[str, dict]:
    return {o["source_recruit_id"]: o for o in rows("recruiting-observation")}


def plan(tag: str) -> dict:
    return STATE["world"]["plan"][tag]


class RuleTests(unittest.TestCase):
    def test_rules_are_deep_copies_and_hash_stably(self) -> None:
        first = rc.rules_document()
        first["labels"]["pit_eligibility"] = "PIT_ADMITTED"
        first["field_types"]["observations"]["rating"] = "s"
        self.assertEqual(rc.rules_document()["labels"]["pit_eligibility"], "PIT_NOT_ADMITTED")
        self.assertEqual(rc.LABELS["pit_eligibility"], "PIT_NOT_ADMITTED")
        self.assertEqual(rc.rules_sha256(), rc.sha256_bytes(rc.canonical_json_bytes(rc.rules_document())))

    def test_the_committed_contract_restates_the_module_rules_and_is_pinned(self) -> None:
        path = ROOT / rc.CONTRACT_REL
        if rc.ANCHORS["contract_sha256"] == "0" * 64:
            self.skipTest("the contract has not been generated in this checkout yet")
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        self.assertEqual(rc.sha256_bytes(raw), rc.ANCHORS["contract_sha256"])
        self.assertEqual(rc.canonical_json_bytes(contract["rules"]), rc.canonical_json_bytes(rc.rules_document()))
        for key in rb.ANCHOR_KEYS:
            self.assertEqual(rc.canonical_json_bytes(contract[key]), rc.canonical_json_bytes(rc.ANCHORS[key]), key)
        counts = contract["expected"]["counts"]
        self.assertEqual(counts["requested_cells"], counts["captured_cells"] + counts["not_captured_cells"])
        self.assertEqual(contract["expected"]["national_expected_universe"], "NOT_ESTABLISHED")

    def test_identity_formulas_match_the_independent_restatements(self) -> None:
        a = plan("A")
        self.assertEqual(rc.person_id_for_slot(a["slot"]), a["canonical"])
        self.assertIsNone(rc.person_id_for_slot("people-v1:coach:00000001"))
        self.assertIsNone(rc.person_id_for_slot("people-v1:player:1"))
        self.assertEqual(rc.team_id_for_slot("core-v1:team:00000001"), STATE["world"]["teams"]["alpha"])
        self.assertEqual(rc.identity_key_for("1001", "100001"),
                         ("SOURCE_ATHLETE_ID", "PLAYER|SRC-002|1001", "1001"))
        self.assertEqual(rc.identity_key_for(None, "300003"),
                         ("SOURCE_RECRUIT_ID_ONLY", "PLAYER|SRC-002|RECRUIT|300003", "RECRUIT:300003"))
        self.assertEqual(rc.identity_key_for("-2002", "100002")[1], "PLAYER|SRC-002|-2002")
        self.assertEqual(rc.observation_key("cap_x", 7, "123"), "SRC-002|cap_x|7|123")

    def test_json_kinds_never_confuse_booleans_integers_and_floats(self) -> None:
        self.assertEqual([rc.json_kind(v) for v in (True, 1, 1.0, None, "1")],
                         ["boolean", "integer", "float", "null", "string"])
        self.assertFalse(rc._check_type("num?", True))
        self.assertTrue(rc._check_type("num?", 1) and rc._check_type("num?", 1.0) and rc._check_type("num?", None))
        self.assertFalse(rc._check_type("num?", float("nan")))
        self.assertFalse(rc._check_type("i?", True))

    def test_selector_grammars_and_applicability(self) -> None:
        team, player = STATE["world"]["teams"]["alpha"], plan("A")["canonical"]
        self.assertEqual(rc.validate_selection("recruiting-observation", season=" 2014 ", team=" " + team,
                                               player=player + " ", recruit=" 0123 "),
                         {"season": 2014, "team": team, "player": player, "recruit": "0123"})
        self.assertEqual(rc.validate_selection("recruiting-partition", season=2015), {"season": 2015})
        cases = [(dict(season="14"), "SEASON_INVALID"), (dict(season="0999"), "SEASON_INVALID"),
                 (dict(season=True), "SEASON_INVALID"), (dict(season=2014.0), "SEASON_INVALID"),
                 (dict(season=NBSP + "2014"), "SEASON_INVALID"), (dict(team="Alpha State"), "TEAM_INVALID"),
                 (dict(team=team.upper()), "TEAM_INVALID"), (dict(player="player_" + "g" * 32), "PLAYER_INVALID"),
                 (dict(recruit="1" * 13), "RECRUIT_INVALID"), (dict(recruit="-1"), "RECRUIT_INVALID"),
                 (dict(recruit=""), "RECRUIT_INVALID")]
        for kwargs, code in cases:
            with self.subTest(kwargs=repr(kwargs)), self.assertRaises(rc.RecruitingError) as caught:
                rc.validate_selection("recruiting-observation", **kwargs)
            self.assertEqual(caught.exception.code, code)
        for grain, name in (("recruiting-partition", "team"), ("recruiting-partition", "player"),
                            ("recruiting-partition", "recruit"), ("recruiting-source", "season")):
            with self.subTest(grain=grain, name=name), self.assertRaises(rc.RecruitingError) as caught:
                rc.validate_selection(grain, **{name: {"team": team, "player": player, "recruit": "1",
                                                       "season": "2014"}[name]})
            self.assertEqual(caught.exception.code, "FILTER_NOT_APPLICABLE")

    def test_paging_rules(self) -> None:
        self.assertEqual(rc.validate_paging(" 3 ", "1", False, limit_given=True, offset_given=True), (3, 1))
        self.assertEqual(rc.validate_paging(50, 0, True, limit_given=False, offset_given=False), (None, 0))
        self.assertEqual(rc.validate_paging("123456789012", "0", False, limit_given=True, offset_given=True)[0],
                         123456789012)
        for limit, offset, all_rows, code in (("1234567890123", "0", False, "LIMIT_INVALID"),
                                             (10 ** 12, 0, False, "LIMIT_INVALID"), (True, 0, False, "LIMIT_INVALID"),
                                             (1.0, 0, False, "LIMIT_INVALID"), ("-1", "x", False, "NEGATIVE_LIMIT"),
                                             ("1", "x", False, "OFFSET_INVALID"), ("1", "-2", False, "NEGATIVE_OFFSET"),
                                             ("x", "0", True, "PAGING_CONFLICT")):
            with self.subTest(limit=limit, offset=offset), self.assertRaises(rc.RecruitingError) as caught:
                rc.validate_paging(limit, offset, all_rows, limit_given=True, offset_given=False)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(rc.page([1, 2, 3], 0, 1), ([], 1))
        self.assertEqual(rc.page([1, 2, 3], 0, 3), ([], None))
        self.assertEqual(rc.page([1, 2, 3], 2, 0), ([1, 2], 2))
        self.assertEqual(rc.page([1, 2, 3], 2, 2), ([3], None))
        self.assertEqual(rc.page([1, 2, 3], None, 1), ([2, 3], None))
        self.assertEqual(rc.page([], 5, 0), ([], None))


class QualificationTests(unittest.TestCase):
    def test_every_planted_person_class_keeps_its_state_and_reasons(self) -> None:
        q = quals()
        want = {"100001": [], "100002": [], "300003": [], "400004": ["NO_PERSON_RECORD", "NO_SOURCE_MAPPING"],
                "500005": ["MULTIPLE_PERSON_RECORDS"], "600006": ["NO_SOURCE_MAPPING"],
                "700007": ["SOURCE_MAPPING_CONFLICT"], "800008": ["PERSON_ID_NOT_UNIQUE", "PERSON_SLOT_NOT_UNIQUE"],
                "131313": ["PERSON_RECORD_INTEGRITY_FAILED"]}
        for rid, reasons in want.items():
            with self.subTest(recruit=rid):
                self.assertEqual(q[rid]["person_reasons"], reasons)
                self.assertEqual(q[rid]["person_state"], "UNSUPPORTED_SOURCE_PERSON" if reasons else
                                 "QUALIFIED_EXISTING_SOURCE_PERSON")
                self.assertEqual(q[rid]["canonical_player_id"] is None, bool(reasons))
        self.assertEqual(q["100001"]["canonical_player_id"], plan("A")["canonical"])

    def test_namespaces_are_exact_and_never_fall_back(self) -> None:
        q, o = quals(), observations()
        self.assertEqual((q["100002"]["source_namespace"], q["100002"]["identity_key"]),
                         ("SOURCE_ATHLETE_ID", "PLAYER|SRC-002|-2002"))
        self.assertEqual(o["100002"]["source_athlete_id"], "-2002")
        self.assertEqual(o["1400014"]["source_athlete_id"], "-1414")
        self.assertEqual((q["300003"]["source_namespace"], q["300003"]["source_mapping_entity_key"]),
                         ("SOURCE_RECRUIT_ID_ONLY", "RECRUIT:300003"))
        self.assertEqual(o["900009"]["source_field_kinds"]["athleteId"], "absent")
        self.assertIn("athleteId", o["900009"]["absent_served_fields"])
        self.assertEqual(o["300003"]["source_field_kinds"]["athleteId"], "null")
        self.assertEqual(q["900009"]["source_namespace"], "SOURCE_RECRUIT_ID_ONLY")
        # an athlete observation with no exact person is unsupported, never matched through its recruit-only key
        self.assertEqual(q["400004"]["person_witnesses"], [])

    def test_program_classes_and_witnesses(self) -> None:
        q, teams = quals(), STATE["world"]["teams"]
        want = {"100001": ("EXACT_ALIAS_CORRESPONDENCE", teams["alpha"]), "100002": ("SOURCE_PROGRAM_LABEL_NULL", None),
                "900009": ("SOURCE_PROGRAM_LABEL_ABSENT", None), "400004": ("NO_EXACT_SOURCE_BACKED_ALIAS", None),
                "101010": ("NO_EXACT_SOURCE_BACKED_ALIAS", None), "1400014": ("NO_EXACT_SOURCE_BACKED_ALIAS", None),
                "500005": ("AMBIGUOUS_ALIAS_CANDIDATES", None), "600006": ("NO_EXACT_SOURCE_BACKED_ALIAS", None),
                "700007": ("ALIAS_WITNESS_INTEGRITY_FAILED", None), "800008": ("TEAM_RECORD_UNSUPPORTED", None),
                "300003": ("EXACT_ALIAS_CORRESPONDENCE", teams["beta"])}
        for rid, (state, team) in want.items():
            with self.subTest(recruit=rid):
                self.assertEqual((q[rid]["program_state"], q[rid]["canonical_team_id"]), (state, team))
                self.assertEqual(q[rid]["historical_membership_state"], "UNQUALIFIED")
        alpha = q["100001"]["alias_witnesses"]
        self.assertEqual(len(alpha), 2)
        self.assertEqual({(w["source_system_id"], w["effective_from"], w["effective_to_exclusive"]) for w in alpha},
                         {("SRC-002", "", ""), ("SRC-001", "2010-01-01", "2016-01-01")})
        self.assertEqual(q["500005"]["candidate_team_ids"], sorted([teams["delta1"], teams["delta2"]]))
        self.assertEqual([w["witness_state"] for w in q["600006"]["alias_witnesses"]], ["NOT_SOURCE_BACKED"])
        self.assertEqual([w["witness_state"] for w in q["700007"]["alias_witnesses"]], ["INTEGRITY_FAILED"])
        self.assertTrue(all(w["alias"] == "Alpha State" for w in alpha))
        sources = {s["source_key"]: s for s in rows("recruiting-source")}
        self.assertFalse(any(s["row"] and s["row"]["entity_type"] == "conference" for s in sources.values()))
        self.assertEqual(q["101010"]["legacy_program_agreement"], "LEGACY_ONLY_NOT_ADOPTED")
        self.assertEqual(q["151515"]["legacy_program_agreement"], "DIFFERENT_TEAM")
        self.assertEqual(q["111111"]["legacy_observation_state"], "DISAGREES")
        self.assertEqual(q["121212"]["legacy_observation_state"], "ABSENT")

    def test_values_keep_their_source_kinds_and_states(self) -> None:
        q, o = quals(), observations()
        self.assertIs(type(o["300003"]["rating"]), int)
        self.assertEqual(o["300003"]["source_field_kinds"]["rating"], "integer")
        self.assertIs(type(o["100001"]["rating"]), float)
        self.assertEqual(q["100002"]["rating_triplet_state"], "JOINT_NULL")
        self.assertEqual((o["100002"]["rating"], o["100002"]["ranking"], o["100002"]["stars"]), (None, None, None))
        self.assertEqual(q["121212"]["rating_triplet_state"], "MIXED")
        self.assertEqual((q["101010"]["rating_domain_state"], q["101010"]["ranking_domain_state"],
                          q["101010"]["stars_domain_state"]),
                         ("OUTSIDE_DECLARED_UNIT_INTERVAL", "NONPOSITIVE_INTEGER", "OUTSIDE_ZERO_TO_FIVE"))
        self.assertEqual(q["121212"]["cohort_year_state"], "DIFFERS_FROM_REQUEST_SEASON")
        self.assertEqual((q["100001"]["rating_scale"], q["100001"]["rating_system_version"],
                          q["100001"]["rating_upstream_independence"]),
                         ("SOURCE_AS_SERVED_SCALE_UNVERIFIED", None, "NOT_ESTABLISHED"))
        self.assertEqual((o["161616"]["recruit_type"], o["161616"]["position"], o["161616"]["school"]),
                         (None, None, None))
        self.assertEqual(o["101010"]["name"], fx.NAME_UNICODE)
        self.assertEqual(o["161616"]["name"], fx.NAME_DIACRITIC)

    def test_times_stay_null_and_clocks_are_the_capture_receipt(self) -> None:
        for q in quals().values():
            for name in rc.TIME_FIELDS:
                self.assertIsNone(q[name], name)
            self.assertIs(q["pit_eligible"], False)
            self.assertEqual((q["capture_known_at_utc"], q["retrieved_at_utc"], q["provider_http_date"]),
                             ("2026-08-10T01:48:07Z", "2026-08-10T01:48:07Z", "Mon, 10 Aug 2026 01:48:07 GMT"))
            self.assertEqual(q["pit_eligibility"], "PIT_NOT_ADMITTED")

    def test_observations_bind_the_whole_row_but_serve_only_permitted_fields(self) -> None:
        arrays = STATE["world"]["arrays"]
        for o in observations().values():
            raw = arrays[o["request_season"]][o["raw_row_ordinal"]]
            self.assertEqual(o["raw_row_sha256"], rc.sha256_bytes(rc.canonical_json_bytes(raw)))
            self.assertEqual(o["raw_member_names"], sorted(raw))
            for private in ("city", "hometownInfo", "height", "weight", "stateProvince", "country"):
                self.assertNotIn(private, o)
            self.assertEqual(o["source_recruit_id"], raw["id"])


class PartitionAndSourceTests(unittest.TestCase):
    def test_every_requested_cell_is_kept_distinct(self) -> None:
        cells = rows("recruiting-partition")
        self.assertEqual(len(cells), 34)
        captured = [c for c in cells if c["request_state"] == "CAPTURED"]
        self.assertEqual(len(captured), 15)
        portal = [c for c in captured if c["dataset"] == "transfer_portal"]
        self.assertEqual(len(portal), 7)
        self.assertEqual(len({c["capture_id"] for c in portal}), 7)
        self.assertEqual(len({c["response_sha256"] for c in portal}), 1)
        self.assertTrue(all(c["payload_state"] == "EMPTY_ARRAY" and c["release_observations"] == 0 for c in portal))
        missing = [c for c in cells if c["request_state"] != "CAPTURED"]
        self.assertEqual(len(missing), 19)
        self.assertTrue(all(c["payload_state"] is None and c["row_count"] is None and
                            c["missing_reason"] == "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED" for c in missing))
        ranges = [c for c in cells if c["season"] is None]
        self.assertEqual({c["dataset"] for c in ranges}, {"coaches", "coach_seasons"})
        selected = rows("recruiting-partition", "--season", "2016")
        self.assertEqual({c["dataset"] for c in selected}, {"recruiting_players", "transfer_portal"})
        self.assertEqual(rows("recruiting-partition", "--season", "2030"), [])

    def test_source_witnesses_cover_every_pinned_file_and_referenced_row(self) -> None:
        sources = rows("recruiting-source")
        files = [s for s in sources if s["witness_kind"] == "FILE"]
        self.assertEqual([s["source_key"] for s in files], rc.file_source_keys(STATE["anchors"]))
        portal = [s for s in files if s["role"].startswith("transfer_portal:")]
        self.assertEqual(len(portal), 7)
        self.assertEqual(len({s["relative_path"] for s in portal}), 7)
        contract = next(s for s in files if s["role"] == "contract")
        self.assertEqual((contract["sha256"], contract["frozen_at_utc"]),
                         (STATE["anchors"]["contract_sha256"], fx.FROZEN))
        rights = next(s for s in files if s["role"] == "rights_metadata")
        self.assertEqual(rights["rights_decision"]["decision_id"], rb.RIGHTS_DECISION_ID)
        core = [s for s in sources if s["witness_kind"] != "FILE"]
        referenced = {w["source_key"] for q in quals().values() for w in q["alias_witnesses"] + q["team_witnesses"]}
        self.assertEqual({s["source_key"] for s in core}, referenced)
        tampered = next(s for s in core if s["row"]["alias"] == "Zeta A&M")
        self.assertEqual((tampered["integrity_state"], tampered["witness_state"]),
                         ("RECORD_HASH_MISMATCH", "INTEGRITY_FAILED"))


class SummaryTests(unittest.TestCase):
    def test_unfiltered_summary_rows_and_counts(self) -> None:
        summary = rows("recruiting-summary")
        self.assertEqual([r["summary_key"] for r in summary], rc.SUMMARY_KEYS)
        total = summary[0]
        self.assertEqual((total["observations"], total["athlete_id_observations"], total["recruit_only_observations"],
                          total["negative_athlete_id_observations"]), (16, 13, 3, 2))
        self.assertEqual(total["rating_kinds"], {"float": 13, "integer": 1, "null": 2})
        self.assertEqual((total["historical_times_known"], total["pit_eligible_observations"]), (0, 0))
        for key in total:
            self.assertFalse(any(word in key for word in ("mean", "average", "prior", "score", "rank_")), key)

    def test_filters_intersect_before_the_summary_and_paging(self) -> None:
        team = STATE["world"]["teams"]["alpha"]
        code, doc, err = ask("--grain", "recruiting-summary", "--team", team, "--all")
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["selected_observations"], 4)
        self.assertEqual(doc["rows"][0]["observations"], 4)
        self.assertEqual({r["summary_key"] for r in doc["rows"][1:]},
                         {"REQUEST_SEASON|2010", "REQUEST_SEASON|2015", "REQUEST_SEASON|2017"})
        code, doc, err = ask("--grain", "recruiting-summary", "--team", team, "--season", "2017", "--limit", "1")
        self.assertEqual((doc["total"], doc["returned"], doc["next_offset"], doc["rows"][0]["observations"]),
                         (2, 1, 1, 2))
        for argv in (("--season", "2030"), ("--team", "team_" + "0" * 32), ("--player", "player_" + "0" * 32),
                     ("--recruit", "0100001"), ("--season", "2010", "--team", STATE["world"]["teams"]["beta"])):
            with self.subTest(argv=argv):
                for grain in ("recruiting-summary", "recruiting-observation", "recruiting-qualification"):
                    code, doc, err = ask("--grain", grain, *argv)
                    self.assertEqual((code, doc["rows"], doc["total"], doc["returned"], doc["next_offset"]),
                                     (0, [], 0, 0, None), err)

    def test_zero_limit_is_count_only(self) -> None:
        code, doc, _err = ask("--grain", "recruiting-observation", "--limit", "0", "--offset", "3")
        self.assertEqual((doc["rows"], doc["returned"], doc["total"], doc["next_offset"]), ([], 0, 16, 3))
        code, doc, _err = ask("--grain", "recruiting-observation", "--limit", "0", "--offset", "16")
        self.assertEqual(doc["next_offset"], None)
        code, doc, _err = ask("--grain", "recruiting-observation", "--limit", "5", "--offset", "14")
        self.assertEqual((doc["returned"], doc["next_offset"]), (2, None))


class BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="rce-b-"))
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_order_chunk_and_interrupted_builds_are_byte_identical(self) -> None:
        want = (STATE["result"]["database_identity"], STATE["result"]["database_sha256"])
        for index, extra in enumerate((("--input-order", "reverse"), ("--input-order", "shuffle:6401"),
                                       ("--chunk-size", "1", "--checkpoint-dir", str(self.base / "c1")),
                                       ("--chunk-size", "3", "--checkpoint-dir", str(self.base / "c3")),
                                       ("--chunk-size", "7", "--checkpoint-dir", str(self.base / "c7"),
                                        "--input-order", "reverse"))):
            with self.subTest(extra=extra):
                code, result, err = fx.run_build(STATE["contract"], STATE["world"], self.base / f"o{index}", *extra)
                self.assertEqual(code, 0, err)
                self.assertEqual((result["database_identity"], result["database_sha256"]), want)
        ck = self.base / "ck"
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], self.base / "oi", "--chunk-size", "2",
                                         "--checkpoint-dir", str(ck), "--stop-after-chunks", "3")
        self.assertEqual((code, result["state"]), (rb.INTERRUPTED_EXIT, "INTERRUPTED_AT_CHECKPOINT"), err)
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], self.base / "oi", "--chunk-size", "2",
                                         "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual((code, result["database_identity"]), (0, want[0]), err)
        observed = {o["observation_key"]: o["raw_row_ordinal"] for o in rows("recruiting-observation")}
        for key, ordinal in observed.items():
            self.assertEqual(int(key.split("|")[2]), ordinal)

    def test_identical_rebuilds_are_present_and_collisions_refused(self) -> None:
        out = STATE["db"].parents[4]
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], out)
        self.assertEqual((code, result["state"], result["release"]["manifest_state"]),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT"), err)
        copy_root = self.base / "collide"
        shutil.copytree(out, copy_root)
        target = copy_root / "canonical" / fx.POP / "sha256" / STATE["result"]["database_identity"] / rc.DB_FILE
        data = bytearray(target.read_bytes())
        data[-1] ^= 1
        target.write_bytes(bytes(data))
        code, _result, err = fx.run_build(STATE["contract"], STATE["world"], copy_root)
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"), err)

    def test_source_and_population_drift_are_refused(self) -> None:
        world = fx.build_world(self.base / "w")
        contract = fx.write_contract(self.base / "c.json", fx.contract_for(world))
        rel = next(p for p in (world["data"] / "raw").rglob("*.json") if "recruiting_players" in str(p) and
                   "2013" in str(p))
        original = rel.read_bytes()
        rel.write_bytes(original.replace(b"700007", b"700008"))
        code, _r, err = fx.run_build(contract, world, self.base / "o1")
        self.assertEqual(fx.refusal(err), "RECRUITING_INPUT_TAMPERED", err)
        rel.write_bytes(original)
        doc = json.loads(contract.read_text(encoding="utf-8"))
        doc["expected"]["observations"]["2013"]["keys_sha256"] = "0" * 64
        fx.write_contract(contract, doc)
        code, _r, err = fx.run_build(contract, world, self.base / "o2")
        self.assertEqual(fx.refusal(err), "RECRUITING_INPUT_POPULATION_DRIFT", err)
        doc["rules"]["labels"]["pit_eligibility"] = "PIT_ADMITTED"
        fx.write_contract(contract, doc)
        code, _r, err = fx.run_build(contract, world, self.base / "o3")
        self.assertEqual(fx.refusal(err), "CONTRACT_INVALID", err)

    def test_source_schema_violations_are_refused_never_coerced(self) -> None:
        backslash = bytes([92])
        cases = {"boolean rating": (b'"rating": 0.88', b'"rating": true', "RECRUITING_SOURCE_SCHEMA_INVALID"),
                 "string stars": (b'"stars": 3', b'"stars": "3"', "RECRUITING_SOURCE_SCHEMA_INVALID"),
                 "nan rating": (b'"rating": 0.88', b'"rating": NaN', "RECRUITING_INPUT_MALFORMED"),
                 "lone surrogate name": (b'"Eve Eng"', b'"Eve ' + backslash + b'ud800Eng"',
                                         "RECRUITING_SOURCE_SCHEMA_INVALID"),
                 "huge ranking": (b'"ranking": 50', b'"ranking": ' + b"9" * 5000, "RECRUITING_INPUT_MALFORMED"),
                 "nested position": (b'"position": "WR"', b'"position": ["WR"]', "RECRUITING_SOURCE_SCHEMA_INVALID")}
        for label, (old, new, code) in cases.items():
            with self.subTest(case=label):
                world = fx.build_world(self.base / label.replace(" ", "_"))
                raw = next(p for p in (world["data"] / "raw").rglob("*.json") if "recruiting_players" in str(p) and
                           "2012" in str(p))
                payload = raw.read_bytes()
                self.assertIn(old, payload)
                raw.write_bytes(payload.replace(old, new, 1))
                self._repin(world, raw)
                try:
                    contract = fx.write_contract(world["base"] / "c.json", fx.contract_for(world))
                except rc.RecruitingError as exc:
                    got = exc.code
                else:
                    build_code, _r, err = fx.run_build(contract, world, world["base"] / "o")
                    got = fx.refusal(err) if build_code else "BUILT"
                self.assertEqual(got, code)

    def _repin(self, world: dict, raw: Path) -> None:
        """Rewrite the raw array's receipt and manifest entry so the forged bytes are the captured bytes."""
        data = raw.read_bytes()
        acquisition_path = world["data"] / Path(*rb.ACQUISITION_REL.split("/"))
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        rel = raw.relative_to(world["data"]).as_posix()
        for entry in acquisition["captures"]:
            if entry["immutable_path"] == rel:
                new_rel = rel.rsplit("/", 1)[0] + f"/sha256_{fx.sha(data)}.json"
                new = world["data"] / Path(*new_rel.split("/"))
                raw.rename(new)
                entry.update(immutable_path=new_rel, response_sha256=fx.sha(data), response_bytes=len(data))
                entry["response_headers"]["content-length"] = str(len(data))
                receipt = {k: v for k, v in entry.items() if k != "capture_manifest_path"}
                (world["data"] / Path(*entry["capture_manifest_path"].split("/"))).write_text(
                    json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        acquisition_path.write_text(json.dumps(acquisition, indent=2, sort_keys=True), encoding="utf-8")

    def test_duplicate_source_ids_are_refused(self) -> None:
        world = fx.build_world(self.base / "dup")
        raw = next(p for p in (world["data"] / "raw").rglob("*.json") if "recruiting_players" in str(p) and
                   "2017" in str(p))
        raw.write_bytes(raw.read_bytes().replace(b'"161616"', b'"151515"'))
        self._repin(world, raw)
        contract = fx.write_contract(world["base"] / "c.json", fx.contract_for(world))
        code, _r, err = fx.run_build(contract, world, world["base"] / "o")
        self.assertEqual(fx.refusal(err), "RECRUITING_SOURCE_DUPLICATE_ID", err)

    def test_receipts_must_equal_their_manifest_entries(self) -> None:
        world = fx.build_world(self.base / "r")
        receipt = next((world["data"] / "manifests" / "captures" / "SRC-002").glob("*.json"))
        doc = json.loads(receipt.read_text(encoding="utf-8"))
        doc["retrieved_at_utc"] = "2017-01-01T00:00:00Z"
        receipt.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(rc.RecruitingError) as caught:
            fx.contract_for(world)
        self.assertEqual(caught.exception.code, "RECRUITING_RECEIPT_MISMATCH")

    def test_inputs_are_never_written_and_the_contract_is_source_only(self) -> None:
        before = {p: fx.sha(p.read_bytes()) for p in STATE["world"]["data"].rglob("*") if p.is_file()}
        code, _r, err = fx.run_build(STATE["contract"], STATE["world"], self.base / "o")
        self.assertEqual(code, 0, err)
        after = {p: fx.sha(p.read_bytes()) for p in STATE["world"]["data"].rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        doc = STATE["contract_doc"]
        self.assertEqual(rb.contract_bytes(doc), rb.contract_bytes(fx.contract_for(STATE["world"])))
        text = json.dumps(doc["expected"])
        for decision in ("QUALIFIED_EXISTING_SOURCE_PERSON", "EXACT_ALIAS_CORRESPONDENCE", "player_", "team_"):
            self.assertNotIn(decision, text)


class QueryTests(unittest.TestCase):
    def test_every_grain_serves_its_complete_collection(self) -> None:
        counts = {"recruiting-observation": 16, "recruiting-qualification": 16, "recruiting-partition": 34,
                  "recruiting-summary": 9}
        for grain, count in counts.items():
            code, doc, err = ask("--grain", grain, "--all")
            self.assertEqual((code, doc["total"], doc["returned"], doc["next_offset"]), (0, count, count, None), err)
            for key, value in rc.LABELS.items():
                self.assertEqual(doc[key], value)
        code, doc, _err = ask("--grain", "recruiting-observation", "--limit", "5", "--offset", "5")
        self.assertEqual((doc["returned"], doc["next_offset"]), (5, 10))

    def test_selectors_intersect_on_exact_keys(self) -> None:
        a = plan("A")
        self.assertEqual([r["source_recruit_id"] for r in rows("recruiting-qualification", "--player", a["canonical"])],
                         ["100001"])
        self.assertEqual([r["source_recruit_id"] for r in rows("recruiting-observation", "--recruit", "100001")],
                         ["100001"])
        self.assertEqual([r["source_recruit_id"] for r in rows("recruiting-observation", "--season", "2011")],
                         ["300003", "400004"])
        beta = STATE["world"]["teams"]["beta"]
        self.assertEqual(sorted(r["source_recruit_id"] for r in rows("recruiting-qualification", "--team", beta)),
                         ["121212", "131313", "300003"])
        self.assertEqual(rows("recruiting-observation", "--team", beta, "--player", plan("C")["canonical"])[0]
                         ["source_recruit_id"], "300003")

    def test_frozen_precedence_and_refusals_before_any_file_access(self) -> None:
        team = STATE["world"]["teams"]["alpha"]
        cases = [(("--grain", "recruiting-summary", "--database", "x", "--require-pit"), "RECRUITING_MODE_CONFLICT"),
                 (("--grain", "recruiting-summary", "--database=", "--as-of", "x"), "RECRUITING_MODE_CONFLICT"),
                 (("--grain", "nope", "--require-pit", "--as-of", ""), "RECRUITING_PIT_NOT_ADMITTED"),
                 (("--grain", "nope", "--as-of", ""), "AS_OF_STATE_NOT_SUPPORTED"),
                 (("--grain", "nope", "--season", "x"), "UNKNOWN_GRAIN"),
                 (("--grain", "recruiting-source", "--season", "x", "--team", "y"), "SEASON_INVALID"),
                 (("--grain", "recruiting-source", "--team", "y", "--player", "z"), "TEAM_INVALID"),
                 (("--grain", "recruiting-source", "--player", "z", "--recruit", "q"), "PLAYER_INVALID"),
                 (("--grain", "recruiting-source", "--recruit", "q", "--limit", "x"), "RECRUIT_INVALID"),
                 (("--grain", "recruiting-source", "--team", team, "--all", "--limit", "x"), "FILTER_NOT_APPLICABLE"),
                 (("--grain", "recruiting-partition", "--season", "2014", "--all", "--offset", "x"), "PAGING_CONFLICT"),
                 (("--grain", "recruiting-partition", "--all", "--limit", "0"), "PAGING_CONFLICT"),
                 (("--grain", "recruiting-partition", "--limit", "x", "--offset", "-1"), "LIMIT_INVALID"),
                 (("--grain", "recruiting-partition", "--limit", "-1", "--offset", "x"), "NEGATIVE_LIMIT"),
                 (("--grain", "recruiting-partition", "--offset", "x", "--expect-identity", "z"), "OFFSET_INVALID"),
                 (("--grain", "recruiting-partition", "--offset", "-1", "--expect-identity", "z"), "NEGATIVE_OFFSET"),
                 (("--grain", "recruiting-partition", "--expect-identity", "Z" * 64), "STALE_RECRUITING_IDENTITY"),
                 (("--grain", "recruiting-partition", "--season", "2014", "--season", "2015"), "ARGUMENT_INVALID"),
                 (("--grain", "recruiting-partition", "--bogus"), "ARGUMENT_INVALID"),
                 (("--season", "2014",), "ARGUMENT_INVALID")]
        for argv, code in cases:
            with self.subTest(argv=argv):
                exit_code, refused, accessed, err = raw_ask(*argv)
                self.assertEqual((exit_code, refused, accessed), (2, code, False), err)
                self.assertNotIn("Traceback", err)

    def test_mode_routing_is_exact_and_legacy_invocations_never_route(self) -> None:
        code, doc, err = fx.query(STATE["anchors"], None, f"--recruiting-evidence={STATE['db']}", "--grain",
                                  "recruiting-summary", "--limit", "1")
        self.assertEqual((code, doc["returned"]), (0, 1), err)
        self.assertFalse(pq.recruiting_mode(["--database=--recruiting-evidence", "--grain", "x"]))
        self.assertFalse(pq.recruiting_mode(["--database", "x--recruiting-evidence"]))
        code, _doc, err = fx.query(None, None, "--database", str(STATE["base"] / "nope.sqlite"), "--grain",
                                   "roster-membership")
        self.assertEqual(code, 2)
        self.assertNotEqual(fx.refusal(err), "RECRUITING_MODE_CONFLICT")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT / "src"), env.get("PYTHONPATH")) if p)
        probe = ("import sys,json;from aggie_analytics.personnel_evidence import query as q;"
                 "rc=q.main(['--database','missing.sqlite','--grain','roster-membership']);"
                 "print(json.dumps([rc,'aggie_analytics.personnel_evidence.recruiting' in sys.modules]))")
        with tempfile.TemporaryDirectory(prefix="rce-q-") as tmp:
            proc = subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, env=env, cwd=tmp,
                                  timeout=300)
        self.assertEqual(json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1]), [2, False])

    def test_legacy_help_gains_exactly_one_paragraph_and_the_mode_describes_itself(self) -> None:
        parser = pq.build_parser()
        accepted = argparse.ArgumentParser.format_help(parser)
        self.assertEqual(parser.format_help(), accepted + "\n" + pq.RECRUITING_HELP_PARAGRAPH + "\n")
        self.assertTrue(accepted.endswith("\n"))
        self.assertEqual(pq.RECRUITING_HELP_PARAGRAPH,
                         "Explicit --recruiting-evidence <database> selects the private 2010-2017 recruiting evidence "
                         "release: recruiting-observation, recruiting-qualification, recruiting-partition, "
                         "recruiting-source and recruiting-summary. This mode is RETROSPECTIVE_RESEARCH, "
                         "UNTRUSTED_SHADOW and PIT_NOT_ADMITTED; predictive skill is NOT_ESTABLISHED.")
        with fx.captured() as holder, self.assertRaises(SystemExit) as caught:
            pq.main(["--recruiting-evidence", "x", "--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn(b"usage: bas-personnel-evidence-query --recruiting-evidence", holder["out"])
        self.assertIn(b"PIT_NOT_ADMITTED", holder["out"])


class _InputAccess(Exception):
    """Raised by the access sentinel: the selection reached the release's input access."""


def _no_input_access(path):
    raise _InputAccess(str(path))


RAW_MISSING = "never-read/national_recruiting_evidence.sqlite"


def raw_ask(*argv: str) -> tuple:
    """The public main on a never-read database path with every input access trapped by a sentinel:
    (exit, refusal code, input accessed, stderr)."""
    with mock.patch.object(rc, "_io_path", _no_input_access):
        try:
            code, _doc, err = fx.query(STATE["anchors"], RAW_MISSING, *argv)
        except _InputAccess:
            return None, None, True, ""
    return code, fx.refusal(err), False, err


class RawControlSelectorTests(unittest.TestCase):
    OPTIONS = {"season": ("2014", "SEASON_INVALID"), "recruit": ("100001", "RECRUIT_INVALID"),
               "limit": ("20", "LIMIT_INVALID"), "offset": ("10", "OFFSET_INVALID")}

    def setUp(self) -> None:
        self.options = dict(self.OPTIONS, team=(STATE["world"]["teams"]["alpha"], "TEAM_INVALID"),
                            player=(plan("A")["canonical"], "PLAYER_INVALID"))

    def test_raw_controls_and_surrogates_refuse_by_their_own_code_before_access(self) -> None:
        for option, (value, code) in self.options.items():
            for point in (*CC_POINTS, 0xD800, 0xDFFF):
                for where, text in (("prefix", chr(point) + value), ("suffix", value + chr(point)),
                                    ("infix", value[:2] + chr(point) + value[2:])):
                    with self.subTest(option=option, codepoint=f"U+{point:04X}", position=where):
                        exit_code, refused, accessed, err = raw_ask("--grain", "recruiting-observation",
                                                                    f"--{option}", text)
                        self.assertEqual((exit_code, refused, accessed), (2, code, False), err)
                        self.assertNotIn("Traceback", err)

    def test_only_u0020_spaces_trim_and_names_are_never_ids(self) -> None:
        for option, (value, code) in self.options.items():
            for text in (" " + value, value + "  "):
                with self.subTest(option=option, text=repr(text)):
                    exit_code, refused, accessed, err = raw_ask("--grain", "recruiting-observation", f"--{option}",
                                                                text)
                    self.assertEqual((exit_code, refused, accessed), (None, None, True), err)
            for text in (NBSP + value, value + chr(0x3000), value + chr(0x200B)):
                with self.subTest(option=option, text=repr(text)):
                    exit_code, refused, accessed, err = raw_ask("--grain", "recruiting-observation", f"--{option}",
                                                                text)
                    self.assertEqual((exit_code, refused, accessed), (2, code, False), err)
        for team in ("Alpha State", fx.NAME_UNICODE, "team_" + "A" * 32):
            exit_code, refused, accessed, _err = raw_ask("--grain", "recruiting-observation", "--team", team)
            self.assertEqual((exit_code, refused, accessed), (2, "TEAM_INVALID", False))

    def test_direct_main_nul_is_a_controlled_refusal(self) -> None:
        exit_code, refused, accessed, err = raw_ask("--grain", "recruiting-observation", "--recruit", "1" + chr(0))
        self.assertEqual((exit_code, refused, accessed), (2, "RECRUIT_INVALID", False))
        code, _doc, err = fx.query(STATE["anchors"], "x" + chr(0) + ".sqlite", "--grain", "recruiting-source")
        self.assertEqual((code, fx.refusal(err)), (2, "RECRUITING_DATABASE_LOCATION_UNSUPPORTED"), err)

    def test_a_real_child_process_refuses_controls_without_a_traceback(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT / "src"), env.get("PYTHONPATH")) if p)
        with tempfile.TemporaryDirectory(prefix="rce-r-") as tmp:
            missing = Path(tmp) / "absent" / rc.DB_FILE
            for option, text, code in (("season", TAB + "2014", "SEASON_INVALID"),
                                       ("recruit", "100001" + NEL, "RECRUIT_INVALID"),
                                       ("limit", LF + "20", "LIMIT_INVALID"), ("offset", "1" + DEL, "OFFSET_INVALID")):
                proc = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.personnel_evidence.query",
                                       "--recruiting-evidence", str(missing), "--grain", "recruiting-observation",
                                       f"--{option}", text], capture_output=True, env=env, cwd=tmp, timeout=300)
                with self.subTest(option=option):
                    self.assertEqual((proc.returncode, fx.refusal(proc.stderr.decode("utf-8", "replace")),
                                      proc.stdout), (2, code, b""))
                    self.assertNotIn(b"Traceback", proc.stderr)
            self.assertFalse(missing.parent.exists())


class ForgeryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="rce-f-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.count = 0

    def refused(self, mutate, *, coordinate=False, anchors=None, meta_edit=None, raw_lines=None) -> str | None:
        self.count += 1
        db = fx.forge(STATE["db"], self.base / f"f{self.count}", STATE["anchors"], mutate, coordinate=coordinate,
                      meta_edit=meta_edit, raw_lines=raw_lines)
        code, _doc, err = ask("--grain", "recruiting-summary", "--limit", "1", db=db, anchors=anchors)
        return "SERVED" if code == 0 else fx.refusal(err)

    @staticmethod
    def edit(table: str, recruit: str, **changes):
        def mutate(records):
            record = fx.find(records[table], source_recruit_id=recruit)
            record.update(changes)
        return mutate

    def test_own_rule_challenges_reach_their_own_codes(self) -> None:
        other = plan("K")["canonical"]
        alpha = STATE["world"]["teams"]["alpha"]

        def drop_season(records):
            for table in ("observations", "qualifications"):
                records[table] = [r for r in records[table] if r["request_season"] != 2013]

        def substitute(records):
            o = fx.find(records["observations"], source_recruit_id="100002")
            o.update(source_recruit_id="199999", observation_key=o["observation_key"].replace("100002", "199999"))

        def swap_ordinals(records):
            a, b = [o for o in records["observations"] if o["request_season"] == 2010]
            a["raw_row_ordinal"], b["raw_row_ordinal"] = b["raw_row_ordinal"], a["raw_row_ordinal"]

        def collapse_portals(records):
            keep = []
            for p in records["partitions"]:
                if p["dataset"] == "transfer_portal" and p["request_state"] == "CAPTURED" and p["season"] != 2010:
                    continue
                keep.append(p)
            records["partitions"] = keep

        def missing_as_empty(records):
            p = next(p for p in records["partitions"] if p["request_state"] == "NOT_CAPTURED")
            p.update(request_state="CAPTURED", payload_state="EMPTY_ARRAY", row_count=0, missing_reason=None)

        def portal_event(records):
            p = next(p for p in records["partitions"] if p["dataset"] == "transfer_portal" and
                     p["request_state"] == "CAPTURED")
            p.update(row_count=1, payload_state="NONEMPTY_ARRAY")

        def omit_witness(records):
            records["sources"] = [s for s in records["sources"] if not (s["row"] and s["row"]["alias"] == "Beta Tech")]

        def omit_qualification(records):
            records["qualifications"] = [q for q in records["qualifications"] if q["source_recruit_id"] != "100001"]

        def alter_summary(records):
            records["summary"][1]["observations"] += 1

        def alter_census(records):
            records["census"][0]["population"]["requested_cells"] = 33

        def duplicate(records):
            records["partitions"].insert(1, copy.deepcopy(records["partitions"][0]))

        def foreign_mapping(records):
            q = fx.find(records["qualifications"], source_recruit_id="100001")
            w = copy.deepcopy(fx.find(records["qualifications"], source_recruit_id="111111")["mapping_witnesses"][0])
            q["mapping_witnesses"] = [w]

        def ambiguous_team(records):
            q = fx.find(records["qualifications"], source_recruit_id="500005")
            q["team_witnesses"] = copy.deepcopy(fx.find(records["qualifications"],
                                                        source_recruit_id="100001")["team_witnesses"])

        def malformed_witness_row(records):
            for s in records["sources"]:
                if s["row"] and s["row"]["alias"] == "Beta Tech":
                    s["row"] = None

        def foreign_legacy(records):
            q = fx.find(records["qualifications"], source_recruit_id="100001")
            q["legacy_observation_witnesses"] = copy.deepcopy(
                fx.find(records["qualifications"], source_recruit_id="161616")["legacy_observation_witnesses"])

        cases = [
            ("wrong namespace", self.edit("qualifications", "100001", identity_key="PLAYER|SRC-002|RECRUIT|100001"),
             "RECRUITING_IDENTITY_KEY_MISMATCH"),
            ("name-only merge", self.edit("qualifications", "100001", canonical_player_id=other),
             "RECRUITING_PERSON_CORRESPONDENCE_INVALID"),
            ("unsupported person promoted", self.edit("qualifications", "400004", person_state=
                                                      "QUALIFIED_EXISTING_SOURCE_PERSON", person_reasons=[]),
             "RECRUITING_PERSON_CORRESPONDENCE_INVALID"),
            ("unmapped label forced bound", self.edit("qualifications", "400004", program_state=
                                                      "EXACT_ALIAS_CORRESPONDENCE", canonical_team_id=alpha),
             "RECRUITING_PROGRAM_CORRESPONDENCE_INVALID"),
            ("alias interval as membership", self.edit("qualifications", "100001", historical_membership_state=
                                                       "QUALIFIED_BY_ALIAS_INTERVAL"),
             "RECRUITING_PROGRAM_CORRESPONDENCE_INVALID"),
            ("invented known-at", self.edit("qualifications", "100001", historical_known_at="2010-02-03T00:00:00Z"),
             "RECRUITING_TIME_CLAIM_INVALID"),
            ("cohort year as signing day", self.edit("qualifications", "100001", signing_time="2010-02-03"),
             "RECRUITING_TIME_CLAIM_INVALID"),
            ("capture clock transplanted", self.edit("qualifications", "100001",
                                                     capture_known_at_utc="2010-02-03T00:00:00Z"),
             "RECRUITING_TIME_CLAIM_INVALID"),
            ("pit admitted", self.edit("qualifications", "100001", pit_eligible=True), "RECRUITING_PIT_CLAIM_INVALID"),
            ("missing observed season", drop_season, "RECRUITING_OBSERVATION_ROW_MISSING"),
            ("count-preserving substitution", substitute, "RECRUITING_OBSERVATION_KEYS_MISMATCH"),
            ("ordinal substitution", swap_ordinals, "RECRUITING_ORDER_MISMATCH"),
            ("typed value corruption", self.edit("observations", "300003", rating=1.0),
             "RECRUITING_OBSERVATION_KIND_MISMATCH"),
            ("source null to zero", self.edit("observations", "100002", rating=0),
             "RECRUITING_OBSERVATION_KIND_MISMATCH"),
            ("boolean as integer", self.edit("observations", "100001", ranking=True), "RECRUITING_FIELD_TYPE_INVALID"),
            ("seven empty portals collapsed", collapse_portals, "RECRUITING_PARTITION_ROW_MISSING"),
            ("quota-missing relabeled empty", missing_as_empty, "RECRUITING_PARTITION_MISMATCH"),
            ("roster movement relabeled portal rows", portal_event, "RECRUITING_PARTITION_MISMATCH"),
            ("omitted witness", omit_witness, "RECRUITING_SOURCE_CLOSURE_INVALID"),
            ("omitted qualification", omit_qualification, "RECRUITING_QUALIFICATION_ROW_MISSING"),
            ("altered summary cohort", alter_summary, "RECRUITING_SUMMARY_MISMATCH"),
            ("altered census", alter_census, "RECRUITING_CENSUS_MISMATCH"),
            ("duplicate row", duplicate, "RECRUITING_DUPLICATE_ROW"),
            ("foreign mapping witness", foreign_mapping, "RECRUITING_PERSON_CORRESPONDENCE_INVALID"),
            ("team witness on an ambiguous label", ambiguous_team, "RECRUITING_PROGRAM_CORRESPONDENCE_INVALID"),
            ("foreign legacy witness", foreign_legacy, "RECRUITING_LEGACY_WITNESS_MISMATCH"),
            ("malformed referenced witness row", malformed_witness_row, "RECRUITING_SOURCE_MISMATCH"),
            ("legacy witness relabeled", self.edit("qualifications", "111111", legacy_observation_state="AGREES"),
             "RECRUITING_LEGACY_WITNESS_MISMATCH"),
            ("value state", self.edit("qualifications", "101010", rating_domain_state="WITHIN_DECLARED_UNIT_INTERVAL"),
             "RECRUITING_VALUE_STATE_MISMATCH"),
            ("extra member", self.edit("observations", "100001", talent_prior=0.9), "RECRUITING_RECORD_SHAPE_INVALID"),
            ("label claim", self.edit("observations", "100001", trust_state="TRUSTED"),
             "RECRUITING_LABEL_CLAIM_INVALID"),
        ]
        for label, mutate, code in cases:
            with self.subTest(case=label):
                self.assertEqual(self.refused(mutate), code)

    def test_fully_coordinated_value_forgeries_need_the_pinned_profile(self) -> None:
        def int_to_float(records):
            o = fx.find(records["observations"], source_recruit_id="300003")
            o["rating"] = 1.0
            o["source_field_kinds"]["rating"] = "float"

        def null_to_zero(records):
            o = fx.find(records["observations"], source_recruit_id="100002")
            o["rating"] = 0.0
            o["source_field_kinds"]["rating"] = "float"

        def person_swap(records):
            q = fx.find(records["qualifications"], source_recruit_id="100001")
            w = q["person_witnesses"][0]
            w["canonical_id"] = w["record_id"] = plan("K")["canonical"]
            w["assignment_slot"] = plan("K")["slot"]
            m = q["mapping_witnesses"][0]
            m.update(canonical_id=plan("K")["canonical"], assignment_slot=plan("K")["slot"],
                     record_id=rc.mapping_record_id("1001", plan("K")["canonical"]))

        pinned = {**STATE["anchors"], "profile": {"content_identity": STATE["result"]["content_identity"],
                                                  "database_identity": STATE["result"]["database_identity"]}}
        for label, mutate in (("int 1 to float 1.0", int_to_float), ("null to zero", null_to_zero),
                              ("person swap", person_swap)):
            with self.subTest(case=label):
                self.assertEqual(self.refused(mutate, coordinate=True), "SERVED")
                self.assertEqual(self.refused(mutate, coordinate=True, anchors=pinned), "RECRUITING_PROFILE_MISMATCH")
        code, doc, err = ask("--grain", "recruiting-summary", "--limit", "1", anchors=pinned)
        self.assertEqual(code, 0, err)

    def test_meta_manifest_and_identity_forgeries(self) -> None:
        def meta(key, value):
            def edit(m):
                m[key] = value
            return edit
        labels = dict(rc.LABELS, pit_eligibility="PIT_ADMITTED")
        rules = rc.rules_document()
        rules["values"]["rating"] = "imputed"
        self.assertEqual(self.refused(lambda r: None, meta_edit=meta("labels", rc.canonical_line(labels))),
                         "RECRUITING_PIT_CLAIM_INVALID")
        self.assertEqual(self.refused(lambda r: None, meta_edit=meta("rules", rc.canonical_line(rules))),
                         "RECRUITING_RULES_CLAIM_INVALID")
        inputs = rc.inputs_claim(STATE["anchors"])
        inputs["frozen_at_utc"] = "2010-01-01T00:00:00Z"
        self.assertEqual(self.refused(lambda r: None, meta_edit=meta("inputs", rc.canonical_line(inputs))),
                         "RECRUITING_INPUTS_CLAIM_INVALID")
        self.assertEqual(self.refused(lambda r: None, raw_lines=lambda t, v: [line.replace('":', '": ', 1)
                                                                              if t == "census" else line for line in v]),
                         "RECRUITING_RECORD_NOT_CANONICAL")
        db = fx.forge(STATE["db"], self.base / "tamper", STATE["anchors"], lambda r: None)
        data = bytearray(db.read_bytes())
        data[100] ^= 1
        db.write_bytes(bytes(data))
        code, _doc, err = ask("--grain", "recruiting-source", db=db)
        self.assertEqual(fx.refusal(err), "RECRUITING_DATABASE_TAMPERED")
        db = fx.forge(STATE["db"], self.base / "floatcount", STATE["anchors"], lambda r: None)
        manifest = rc.manifest_path_for(db)
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        doc["identity_document"]["table_counts"]["meta"] = float(doc["identity_document"]["table_counts"]["meta"])
        identity = rc.sha256_bytes(rc.canonical_json_bytes(doc["identity_document"]))
        doc["identity"] = identity
        target = db.parents[1] / identity
        shutil.copytree(db.parent, target)
        new_manifest = manifest.parents[1] / identity / "run_manifest.json"
        new_manifest.parent.mkdir(parents=True)
        new_manifest.write_text(json.dumps(doc), encoding="utf-8")
        code, _doc, err = ask("--grain", "recruiting-source", db=target / rc.DB_FILE)
        self.assertEqual(fx.refusal(err), "RECRUITING_IDENTITY_DOCUMENT_MISMATCH")
        code, _doc, err = ask("--grain", "recruiting-source", "--expect-identity", "0" * 64)
        self.assertEqual(fx.refusal(err), "STALE_RECRUITING_IDENTITY")
        other = {**STATE["anchors"], "contract_sha256": "1" * 64}
        code, _doc, err = ask("--grain", "recruiting-source", anchors=other)
        self.assertEqual(fx.refusal(err), "RECRUITING_CONTRACT_MISMATCH")


class MalformedJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="rce-m-"))
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_malformed_record_lines_are_controlled_refusals(self) -> None:
        cases = {"lone surrogate": ('"Ann Able"', '"Ann ' + chr(92) + 'ud800Able"', "JSON_LONE_SURROGATE"),
                 "nonfinite": ('"rating":0.9512', '"rating":NaN', "JSON_NONFINITE_NUMBER"),
                 "huge integer": ('"ranking":10', '"ranking":' + "9" * 5000, "JSON_INTEGER_TOO_LONG"),
                 "deep nesting": ('"position":"WR"', '"position":' + "[" * 100000 + "]" * 100000,
                                  "JSON_NESTING_TOO_DEEP")}
        for index, (label, (old, new, reason)) in enumerate(cases.items()):
            with self.subTest(case=label):
                def raw_lines(table, lines, old=old, new=new):
                    if table != "observations":
                        return lines
                    return [line.replace(old, new, 1) if '"100001"' in line else line for line in lines]
                db = fx.forge(STATE["db"], self.base / f"m{index}", STATE["anchors"], lambda r: None,
                              raw_lines=raw_lines)
                code, _doc, err = ask("--grain", "recruiting-source", db=db)
                self.assertEqual(code, 2)
                self.assertIn(fx.refusal(err), ("RECRUITING_RECORD_MALFORMED", "RECRUITING_RECORD_TYPE_INVALID",
                                                "RECRUITING_FIELD_TYPE_INVALID"))
                self.assertNotIn("Traceback", err)
                if reason != "JSON_NESTING_TOO_DEEP":
                    self.assertIn(reason, err)

    def test_malformed_manifests_are_refused(self) -> None:
        for index, payload in enumerate(("[]", "{", '{"identity": NaN}', "{" + '"a":' * 1 + "[" * 100000 + "]" * 100000
                                         + "}")):
            with self.subTest(payload=payload[:20]):
                target = self.base / f"r{index}"
                shutil.copytree(STATE["db"].parents[4], target)
                db = target / "canonical" / fx.POP / "sha256" / STATE["result"]["database_identity"] / rc.DB_FILE
                rc.manifest_path_for(db).write_text(payload, encoding="utf-8")
                code, _doc, err = ask("--grain", "recruiting-source", db=db)
                self.assertEqual((code, fx.refusal(err)), (2, "RECRUITING_MANIFEST_MALFORMED"), err)
                self.assertNotIn("Traceback", err)


class LocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="rce-l-"))
        self.addCleanup(shutil.rmtree, ("\\\\?\\" if os.name == "nt" else "") + os.path.abspath(self.base), True)

    def test_missing_and_misplaced_files_are_refused_and_never_created(self) -> None:
        missing = self.base / "nowhere" / "canonical" / fx.POP / "sha256" / ("0" * 64) / rc.DB_FILE
        code, _doc, err = ask("--grain", "recruiting-source", db=missing)
        self.assertEqual((code, fx.refusal(err)), (2, "RECRUITING_DATABASE_MISSING"))
        self.assertFalse(missing.parent.exists())
        loose = self.base / "loose" / rc.DB_FILE
        loose.parent.mkdir()
        shutil.copyfile(STATE["db"], loose)
        code, _doc, err = ask("--grain", "recruiting-source", db=loose)
        self.assertEqual(fx.refusal(err), "RECRUITING_LOCATION_INVALID")
        code, _doc, err = ask("--grain", "recruiting-source", "--manifest", str(self.base / "no" / "m.json"))
        self.assertEqual(fx.refusal(err), "RECRUITING_MANIFEST_MISSING")
        code, _doc, err = ask("--grain", "recruiting-source", db="")
        self.assertEqual(fx.refusal(err), "RECRUITING_DATABASE_LOCATION_UNSUPPORTED")
        code, _doc, err = ask("--grain", "recruiting-source", "--manifest", "")
        self.assertEqual(fx.refusal(err), "RECRUITING_MANIFEST_LOCATION_UNSUPPORTED")

    @unittest.skipUnless(os.name == "nt", "Windows network/device spellings")
    def test_network_and_device_spellings_are_refused_before_access(self) -> None:
        sentinel = []
        real = rc._io_path

        def guard(path):
            sentinel.append(str(path))
            return real(path)
        with mock.patch.object(rc, "_io_path", guard):
            for spelling in ("\\\\bas-c64-test-host\\share\\x.sqlite", "\\\\.\\nul", "\\\\.\\pipe\\c64",
                             "\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1\\x.sqlite", "\\\\?\\UNC\\h\\s\\x.sqlite",
                             "//bas-c64-test-host/share/x.sqlite"):
                code, _doc, err = ask("--grain", "recruiting-source", db=spelling)
                self.assertEqual((code, fx.refusal(err)), (2, "RECRUITING_DATABASE_LOCATION_UNSUPPORTED"), spelling)
            code, _doc, err = ask("--grain", "recruiting-source", "--manifest",
                                  "\\\\bas-c64-test-host\\share\\run_manifest.json")
            self.assertEqual(fx.refusal(err), "RECRUITING_MANIFEST_LOCATION_UNSUPPORTED")
            code, _doc, err = ask("--grain", "recruiting-source", db="\\\\?\\C:\\x\\..\\y.sqlite")
            self.assertEqual(fx.refusal(err), "RECRUITING_DATABASE_LOCATION_NOT_LITERAL")
        self.assertEqual(sentinel, [], "no filesystem access before the location policy")

    def test_legitimate_local_spellings_answer_identically(self) -> None:
        genuine = ask("--grain", "recruiting-summary", "--limit", "3")[1]
        ident = STATE["result"]["database_identity"]
        long_base = self.base.joinpath(*[f"long-rehoused-recruiting-component-{c}-" + c * 24 for c in "abcd"])
        special = self.base / ("sp" + chr(0xE9) + " cial " + chr(0x2603) + " [x] #%&")
        for root in (long_base, special):
            for kind in ("canonical", "manifests"):
                src = STATE["db"].parents[3].parent / kind / fx.POP / "sha256" / ident
                dst = root / kind / fx.POP / "sha256" / ident
                os.makedirs(rc._io_path(dst))
                for name in os.listdir(rc._io_path(src)):
                    shutil.copyfile(rc._io_path(src / name), rc._io_path(dst / name))
        spellings = [long_base / "canonical" / fx.POP / "sha256" / ident / rc.DB_FILE,
                     special / "canonical" / fx.POP / "sha256" / ident / rc.DB_FILE]
        if os.name == "nt":
            spellings.append("\\\\?\\" + os.path.abspath(STATE["db"]))
            spellings.append("\\\\?\\" + os.path.abspath(spellings[0]))
        self.assertGreater(len(str(spellings[0])), 260)
        for spelling in spellings:
            code, doc, err = ask("--grain", "recruiting-summary", "--limit", "3", db=spelling)
            self.assertEqual(code, 0, f"{spelling}: {err}")
            self.assertEqual((doc["release_identity"], doc["rows"]), (genuine["release_identity"], genuine["rows"]))
        manifest = rc.manifest_path_for(STATE["db"])
        copied = self.base / "copied_manifest.json"
        shutil.copyfile(manifest, copied)
        code, doc, err = ask("--grain", "recruiting-summary", "--limit", "3", "--manifest", str(copied))
        self.assertEqual((code, doc["rows"]), (0, genuine["rows"]), err)
        cwd = os.getcwd()
        try:
            os.chdir(STATE["db"].parent)
            code, doc, err = ask("--grain", "recruiting-summary", "--limit", "3", db=rc.DB_FILE)
        finally:
            os.chdir(cwd)
        self.assertEqual((code, doc["rows"]), (0, genuine["rows"]), err)


def _short_spelling(path: Path) -> str | None:
    """The native 8.3 spelling Windows reports for an existing path (GetShortPathNameW), or None."""
    if os.name != "nt":
        return None
    import ctypes  # noqa: PLC0415 - Windows only
    from ctypes import wintypes  # noqa: PLC0415 - Windows only

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    kernel32.GetShortPathNameW.restype = wintypes.DWORD
    size = kernel32.GetShortPathNameW(str(path), None, 0)
    if not size:
        return None
    buffer = ctypes.create_unicode_buffer(size)
    return buffer.value if kernel32.GetShortPathNameW(str(path), buffer, size) else None


def _respell(db: Path | str, index: int, spell) -> Path:
    parts = list(Path(db).parts)
    parts[-1 - index] = spell(parts[-1 - index])
    return Path(*parts)


class NativeLocationAliasTests(unittest.TestCase):
    """The accepted C61 rule: the reader checks the release layout and identity on the genuine names of the file."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="rce-a-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.genuine = ask("--grain", "recruiting-summary", "--limit", "3")[1]

    def served(self, spelling, why: str, cwd: Path | None = None) -> None:
        previous = os.getcwd()
        try:
            if cwd is not None:
                os.chdir(cwd)
            code, doc, err = ask("--grain", "recruiting-summary", "--limit", "3", db=spelling)
        finally:
            os.chdir(previous)
        self.assertEqual(code, 0, f"{why} {spelling}: {err[-300:]}")
        self.assertEqual((doc["release_identity"], doc["rows"]),
                         (self.genuine["release_identity"], self.genuine["rows"]), why)

    @unittest.skipUnless(os.name == "nt", "Windows case-equivalent spellings")
    def test_case_equivalent_spellings_serve_the_release(self) -> None:
        db = STATE["db"]
        for index in range(4):
            self.served(_respell(db, index, str.upper), f"component {index} upper")
        self.served(rc.DB_FILE.upper(), "relative case-equivalent file name", cwd=db.parent)

    @unittest.skipUnless(os.name == "nt", "Windows native 8.3 short names")
    def test_native_short_spellings_serve_the_release(self) -> None:
        short = _short_spelling(STATE["db"])
        if not short or short == str(STATE["db"]):
            self.skipTest(f"this volume reports no 8.3 short name ({short!r})")
        self.served(short, "native short spelling")

    @unittest.skipUnless(os.name == "nt", "Windows directory junctions")
    def test_spellings_through_junctions_serve_the_release(self) -> None:
        import _winapi  # noqa: PLC0415 - Windows CPython

        db = STATE["db"]
        link = self.base / "jroot"
        _winapi.CreateJunction(str(db.parents[4]), str(link))
        self.addCleanup(os.rmdir, link)
        self.served(link / "canonical" / fx.POP / "sha256" / db.parent.name / rc.DB_FILE, "junction")

    def test_spellings_outside_the_genuine_layout_stay_refused(self) -> None:
        ident = STATE["result"]["database_identity"]
        target = self.base / "x" / "canonical" / (fx.POP + "_copy") / "sha256" / ident
        os.makedirs(target)
        shutil.copyfile(STATE["db"], target / rc.DB_FILE)
        code, _doc, err = ask("--grain", "recruiting-source", db=target / rc.DB_FILE)
        self.assertEqual(fx.refusal(err), "RECRUITING_LOCATION_INVALID")


class MountedGenuineTests(unittest.TestCase):
    def test_the_canonical_release_verifies_with_the_pinned_profile(self) -> None:
        data = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or "")
        profile = rc.RECRUITING_PROFILE
        if not str(data) or profile is None:
            self.skipTest("the private data root or the pinned canonical profile is absent")
        db = data / "canonical" / rc.POPULATION / "sha256" / profile["database_identity"] / rc.DB_FILE
        if not db.is_file():
            self.skipTest("the canonical recruiting evidence release is not mounted")
        with rc.RecruitingEvidence(db) as reader:
            self.assertEqual(reader.database_identity, profile["database_identity"])
            census = reader.census
            expected = rc.ANCHORS["expected"]["counts"]
            self.assertEqual((census["requested_cells"], census["observations"]),
                             (expected["requested_cells"], expected["observations"]))
            self.assertEqual(census["pit_eligible_observations"], 0)
            self.assertEqual(census["historical_times_known"], 0)


if __name__ == "__main__":
    unittest.main()
