"""Tests of the fixed-profile C37 2026 availability source-assertion query (BAT-733, TP62-A01).

Synthetic tiny worlds (tests/availability_evidence_fixture.py) exercise every grain, decoding, qualification class,
selector, paging, cutoff and refusal through the real reader with an injected *trusted synthetic profile*; the public
builtin profile is never replaced and the public whole-file anchor is exercised against the synthetic bytes (always
DATABASE_IDENTITY_MISMATCH). The mounted genuine cases read the fixed C37 database and the five witnesses under
AGGIE_ANALYTICS_DATA_ROOT and skip when it is absent.
"""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import availability_evidence_fixture as fx

from aggie_analytics.availability_evidence import audit
from aggie_analytics.availability_evidence import evidence as ae
from aggie_analytics.availability_evidence import profile as P
from aggie_analytics.availability_evidence import query as q

REPO = Path(__file__).resolve().parents[1]
GENUINE_DB_REL = ("ops/cycle37/attempts/REWORK-20260922T171601Z/release/sha256/"
                  "67d2ce357dc36d5a13a8edc94d0ffa9fc27115768817b1ee1ac9dff567757671/CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite")
EXT = "\\\\?\\"


def run_cli(argv: list[str], *, profile=None, hooks=None) -> tuple[int, dict | None, dict | None]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = q.main(argv, profile=profile, hooks=hooks)
    stdout, stderr = out.getvalue(), err.getvalue()
    return (code, json.loads(stdout) if stdout.strip() else None,
            json.loads(stderr.strip().splitlines()[-1]) if stderr.strip() else None)


class WorldCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.world = fx.World(self.tmp / "w")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def session(self, world: fx.World | None = None, **kwargs) -> ae.AvailabilityEvidence:
        world = world or self.world
        kwargs.setdefault("profile", world.profile)
        return ae.AvailabilityEvidence(world.database, world.data_root, **kwargs)

    def cli(self, *args: str, world: fx.World | None = None, profile="synthetic", hooks=None):
        world = world or self.world
        prof = world.profile if profile == "synthetic" else profile
        return run_cli(["--database", str(world.database), "--data-root", str(world.data_root), *args],
                       profile=prof, hooks=hooks)

    def refused(self, code: str, *args: str, exit_code: int = 2, **kwargs) -> dict:
        got, out, err = self.cli(*args, **kwargs)
        self.assertEqual((got, (err or {}).get("refused"), out), (exit_code, code, None), err)
        return err


# --------------------------------------------------------------------------------------------- contract

class ContractTests(unittest.TestCase):
    def test_committed_contract_equals_the_rendered_document(self) -> None:
        self.assertEqual((REPO / P.CONTRACT_REL).read_text(encoding="utf-8"), P.render_contract())

    def test_rules_and_profile_identities_are_the_frozen_literals(self) -> None:
        self.assertEqual(P.rules_sha256(), P.RULES_SHA256)
        self.assertEqual(P.profile_sha256(), P.PROFILE_SHA256)
        self.assertEqual(P.CONTRACT_DOCUMENT["rules_sha256"], P.RULES_SHA256)

    def test_builtin_profile_binds_the_fixed_database_and_five_witnesses(self) -> None:
        self.assertEqual(P.PROFILE["database"]["sha256"],
                         "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331")
        self.assertNotEqual(P.PROFILE["database"]["sha256"], P.PROFILE["database"]["content_addressed_directory_key"])
        self.assertEqual(sorted(P.WITNESSES), ["ACC_ARCHIVE", "ACC_CURRENT_POSTING", "BIG12_ARCHIVE", "BIGTEN_ARCHIVE",
                                               "SEC_RAW_CAPTURE"])
        for wid, spec in P.WITNESSES.items():
            self.assertNotIn("\\", spec["relative_path"], wid)
            self.assertFalse(spec["relative_path"].startswith("/"), wid)
        self.assertEqual({k: P.TABLES[k]["rows"] for k in P.TABLES}, {"statement": 1592, "opportunity": 3474,
                                                                       "policy": 13})
        self.assertEqual(len(P.TABLES["opportunity"]["columns"]), 16)
        self.assertEqual(P.AUTHORITY["pit_admission"], "NOT_ADMITTED")
        self.assertIs(P.AUTHORITY["healthy_default"], False)

    def test_selector_matrix_is_the_adopted_table(self) -> None:
        matrix = {k: sorted(v["grains"]) for k, v in P.RULES["selectors"].items()}
        self.assertEqual(matrix, {
            "--statement-id": ["statement"], "--policy-id": ["opportunity", "policy"],
            "--team": ["opportunity", "statement"], "--conference": ["opportunity", "policy", "statement"],
            "--season": ["opportunity", "statement"], "--policy-season": ["policy"],
            "--contest": ["opportunity", "statement"], "--person-id": ["statement"],
            "--published-name": ["statement"], "--source-sha256": ["policy", "statement"], "--stage": ["statement"],
            "--reported-status": ["statement"], "--presence": ["statement"], "--identity-state": ["statement"],
            "--contest-state": ["statement"], "--cutoff": ["statement"]})

    def test_pyproject_declares_the_console_script(self) -> None:
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('bas-availability-evidence-query = "aggie_analytics.availability_evidence.query:main"', text)

    def test_the_gate_records_the_committed_audit_pin_and_frozen_identities(self) -> None:
        gate = json.loads((REPO / "artifacts" / "data_lake" / "availability_evidence_2026_gate.json").read_text(
            encoding="utf-8"))
        self.assertEqual((gate["profile_id"], gate["rules_sha256"], gate["profile_sha256"], gate["database_sha256"]),
                         (P.PROFILE_ID, P.RULES_SHA256, P.PROFILE_SHA256, P.PROFILE["database"]["sha256"]))
        self.assertEqual((gate["qualified_audit"]["sha256"], gate["qualified_audit"]["lines"],
                          gate["qualified_audit"]["summary"]),
                         (audit.QUALIFIED_AUDIT["lines_sha256"], audit.QUALIFIED_AUDIT["rows"],
                          audit.QUALIFIED_AUDIT["summary"]))
        self.assertEqual((audit.QUALIFIED_AUDIT["rules_sha256"], audit.QUALIFIED_AUDIT["database_sha256"]),
                         (P.RULES_SHA256, P.PROFILE["database"]["sha256"]))
        self.assertEqual((gate["labels"]["pit_admission"], gate["labels"]["availability_state_asserted"],
                          gate["labels"]["healthy_default"]), ("NOT_ADMITTED", False, False))


# --------------------------------------------------------------------------------------------- grains and records

class GrainTests(WorldCase):
    def test_every_grain_serves_its_whole_population_with_the_authority_labels(self) -> None:
        s = self.session()
        for grain, total in (("statement", 28), ("opportunity", 10), ("policy", 2), ("profile", 1)):
            out = s.query(grain, {}, all_rows=True)
            self.assertEqual((out["total_count"], out["returned"]), (total, total), grain)
            self.assertEqual(out["authority"], P.AUTHORITY)
            self.assertEqual(out["qualification_rules"], {"schema": P.QUALIFICATION_SCHEMA, "sha256": P.RULES_SHA256})
            self.assertEqual(out["profile"], "SYNTHETIC_TEST_PROFILE_NOT_PUBLIC")

    def test_original_record_keeps_the_original_schema_and_documented_decoding(self) -> None:
        out = self.session().query("statement", {"--statement-id": "1"})
        rec = out["rows"][0]["original_record"]
        self.assertEqual(list(rec), list(P.TABLES["statement"]["columns"]))
        self.assertIsInstance(rec["contest"], dict)
        self.assertIsInstance(rec["identity"], dict)
        self.assertIs(rec["quarantined"], False)
        self.assertIs(rec["no_medical_detail"], True)
        self.assertIsInstance(rec["availability_row_id"], int)
        self.assertNotIsInstance(rec["availability_row_id"], bool)
        self.assertIsNone(rec["effective_utc"])
        self.assertIs(rec["contest"]["conference_game"], True)
        self.assertNotIn("source_occurrence", out["rows"][0])
        pol = self.session().query("policy", {"--policy-id": "CUSA-FB"})["rows"][0]["original_record"]
        self.assertEqual(list(pol), list(P.TABLES["policy"]["columns"]))
        self.assertIsInstance(pol["quotes"], list)
        self.assertIsInstance(pol["quotes_verified_in_extracted_text"], dict)
        self.assertIsNone(pol["policy_season"])

    def test_opportunity_rows_carry_a_separate_pinned_occurrence_wrapper(self) -> None:
        out = self.session().query("opportunity", {}, all_rows=True)
        for row in out["rows"]:
            self.assertEqual(list(row["original_record"]), list(P.TABLES["opportunity"]["columns"]))
            self.assertNotIn("original_sqlite_rowid", row["original_record"])
            occ = row["source_occurrence"]
            self.assertEqual(sorted(occ), ["database_sha256", "original_sqlite_rowid", "table"])
            self.assertEqual(occ["database_sha256"], self.world.profile["database"]["sha256"])
        self.assertEqual(sorted(r["source_occurrence"]["original_sqlite_rowid"] for r in out["rows"]), list(range(1, 11)))

    def test_order_is_the_frozen_key_order_with_duplicates_by_rowid(self) -> None:
        out = self.session().query("opportunity", {}, all_rows=True)
        keys = [(r["original_record"]["canonical_contest_id"], r["original_record"]["team_id"],
                 r["original_record"]["side"], r["source_occurrence"]["original_sqlite_rowid"]) for r in out["rows"]]
        self.assertEqual(keys, sorted(keys))
        ids = [r["original_record"]["availability_row_id"] for r in self.session().query("statement", {},
                                                                                           all_rows=True)["rows"]]
        self.assertEqual(ids, list(range(1, 29)))

    def test_profile_grain_is_one_coverage_record_with_no_data_selector(self) -> None:
        out = self.session().query("profile", {})
        rec = out["rows"][0]["profile"]
        self.assertEqual(rec["population"], fx.POPULATION)
        self.assertEqual(rec["population"]["opportunity_occurrences"], 10)
        self.assertEqual(rec["population"]["opportunity_distinct_business_keys"], 8)
        self.assertEqual(rec["population"]["schedule_record_occurrences"], 5)
        self.assertEqual(rec["population"]["schedule_distinct_game_ids"], 4)
        for option in P.RULES["selectors"]:
            with self.subTest(option=option):
                with self.assertRaises(ae.AvailabilityError) as ctx:
                    self.session().query("profile", {option: "x"})
                self.assertEqual(ctx.exception.code, "SELECTOR_NOT_APPLICABLE")


# --------------------------------------------------------------------------------------------- qualifications

class QualificationTests(WorldCase):
    def rows(self, grain: str = "statement", **sel) -> list[dict]:
        return self.session().query(grain, {f"--{k.replace('_', '-')}": v for k, v in sel.items()}, all_rows=True)["rows"]

    def test_every_source_cell_is_verified_against_its_pinned_witness_coordinate(self) -> None:
        for row in self.rows():
            cell = row["qualification"]["source_cell"]
            self.assertEqual(cell["state"], "VERIFIED_RETAINED_SOURCE_CELL", row["original_record"]["availability_row_id"])
            self.assertEqual(cell["source_sha256"], row["original_record"]["source_sha256"])
            self.assertEqual(cell["raw"]["cell"], row["original_record"]["exact_status_text"])
            self.assertGreaterEqual(cell["fields_compared"], 15)

    def test_both_source_empty_representations_are_one_qualification_with_originals_kept(self) -> None:
        empty = self.rows(presence="PUBLISHED_EMPTY")
        self.assertEqual(len(empty), 12)
        reps = {r["original_record"]["normalized_status"] for r in empty}
        self.assertEqual(reps, {None, "UNKNOWN"})
        for r in empty:
            cell = r["qualification"]["source_cell"]
            self.assertTrue(cell["source_empty"])
            self.assertEqual(r["original_record"]["exact_status_text"], "-")
            self.assertEqual(cell["original_empty_representation"]["normalized_status"],
                             r["original_record"]["normalized_status"])

    def test_available_and_exempt_stay_literal_source_statements(self) -> None:
        avail = self.rows(reported_status="Available")
        self.assertEqual(len(avail), 1)
        self.assertEqual(avail[0]["qualification"]["status"]["note"], P.RULES["statement_qualification"]["status"]["available"])
        self.assertEqual(avail[0]["qualification"]["health_inference"], "NOT_ASSERTED")
        exempt = self.rows(reported_status="Exempt")
        self.assertEqual(len(exempt), 3)
        self.assertTrue(all(r["qualification"]["status"]["note"].startswith("EXEMPT_IS_NEITHER") for r in exempt))

    def test_posting_claims_are_witnessed_in_the_later_capture_and_all_else_unknown(self) -> None:
        rows = self.rows()
        witnessed = [r for r in rows if r["qualification"]["publication"]["state"] ==
                     "SOURCE_POSTING_CLAIM_WITNESSED_IN_LATER_CAPTURE"]
        self.assertEqual(len(witnessed), 2)
        for r in witnessed:
            pub = r["qualification"]["publication"]
            self.assertEqual(pub["claim_utc"], fx.POSTED_UTC)
            self.assertEqual(pub["witness"]["id"], "ACC_CURRENT_POSTING")
            self.assertEqual(pub["witness"]["card_kind"], "INITIAL REPORT")
            self.assertEqual(pub["witness"]["posted_utc_offset_hours"], -4)
            self.assertIn("FIRST_KNOWN_TIME", pub["not_established"])
        self.assertEqual(sum(r["qualification"]["publication"]["state"] == "PUBLICATION_TIME_UNKNOWN" for r in rows), 26)
        for r in rows:
            self.assertEqual(r["qualification"]["effective_time"]["state"], "EFFECTIVE_TIME_UNKNOWN")
            self.assertEqual(r["qualification"]["first_known"], "FIRST_KNOWN_NOT_ESTABLISHED")
            self.assertEqual(r["qualification"]["pit"]["pit_admission"], "NOT_ADMITTED")
            self.assertEqual(r["qualification"]["stage_time"]["state"], "SOURCE_COLUMN_ONLY_PUBLICATION_INSTANT_UNKNOWN")

    def test_identity_and_contest_predicates_stay_separate(self) -> None:
        rows = self.rows()
        joint = {}
        for r in rows:
            joint[r["qualification"]["joint"]] = joint.get(r["qualification"]["joint"], 0) + 1
        self.assertEqual(joint, {"RETAINED_PERSON_AND_CONTEST_CLAIMS": 20, "PERSON_CLAIM_UNRESOLVED": 4,
                                 "CONTEST_CLAIM_NOT_QUALIFIED": 4})
        unresolved = self.rows(identity_state="UNRESOLVED_NO_ROSTER_ROW_MATCHES")
        self.assertTrue(all(r["qualification"]["identity"]["state"] == "UNRESOLVED_NO_ROSTER_ROW_MATCHES" and
                            r["qualification"]["contest"]["state"] == "RETAINED_PARSER_CONTEST_CLAIM" and
                            r["original_record"]["quarantined"] is True for r in unresolved))
        selfopp = self.rows(contest_state="CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF")
        self.assertEqual(len(selfopp), 4)
        for r in selfopp:
            self.assertEqual(r["qualification"]["contest"]["state"], "CONTEST_NOT_QUALIFIED_SELF_OPPONENT")
            self.assertEqual(r["qualification"]["identity"]["state"], "RETAINED_PARSER_IDENTITY_CLAIM")
            self.assertIs(r["original_record"]["quarantined"], False)
            self.assertEqual(r["qualification"]["quarantine_flag"]["state"],
                             "IDENTITY_ONLY_FLAG_NOT_WHOLE_ROW_QUALIFICATION")
        name_only = self.rows(identity_state="RESOLVED_UNIQUE_NAME_JERSEY_NOT_STATED")
        self.assertEqual(len(name_only), 4)
        self.assertEqual({r["original_record"]["player_name"] for r in name_only}, {"Kris Hughes"})
        self.assertTrue(all(r["qualification"]["identity"]["jersey_not_stated"] for r in name_only))
        self.assertTrue(all(r["qualification"]["identity"]["global_person_identity"] == "NOT_QUALIFIED" for r in rows))

    def test_disputed_witness_text_keeps_the_original_and_shows_the_competing_text(self) -> None:
        def change(witnesses):
            doc = json.loads(witnesses["BIGTEN_ARCHIVE"])
            doc["rows"][1][4] = "Carsen Williams"
            witnesses["BIGTEN_ARCHIVE"] = json.dumps(doc).encode("utf-8")
        world = fx.World(self.tmp / "d", mutate_witnesses=change,
                         mutate_statements=lambda rows: [r.update(player_name="Carson Williams") for r in rows
                                                         if r["program"] == "Indiana"])
        rows = self.session(world).query("statement", {"--team": "Indiana"}, all_rows=True)["rows"]
        self.assertEqual(len(rows), 4)
        for r in rows:
            cell = r["qualification"]["source_cell"]
            self.assertEqual(cell["state"], "DISPUTED_AGAINST_PINNED_WITNESS")
            self.assertIn({"field": "player_name", "original": "Carson Williams", "witness": "Carsen Williams"},
                          cell["conflicts"])
            self.assertEqual(r["original_record"]["player_name"], "Carson Williams")

    def test_a_posting_claim_without_a_matching_entry_is_disputed_not_dropped(self) -> None:
        def change(witnesses):
            doc = json.loads(witnesses["ACC_CURRENT_POSTING"])
            doc["cards"][0]["columns"][0]["text"] = "QUESTIONABLE\nS #11 Polo Anderson"
            witnesses["ACC_CURRENT_POSTING"] = json.dumps(doc).encode("utf-8")
        world = fx.World(self.tmp / "p", mutate_witnesses=change)
        rows = self.session(world).query("statement", {"--team": "Clemson", "--stage": "initial_status"})["rows"]
        pub = rows[0]["qualification"]["publication"]
        self.assertEqual(pub["state"], "DISPUTED_AGAINST_PINNED_WITNESS")
        self.assertEqual(rows[0]["original_record"]["publication_utc"], fx.POSTED_UTC)

    def test_opportunity_duplicates_policy_and_denominator_meanings(self) -> None:
        rows = self.rows("opportunity", contest="SRC-002:GAME:200")
        self.assertEqual(len(rows), 4)
        for r in rows:
            occ = r["qualification"]["occurrence"]
            self.assertEqual(occ["state"], "EXACT_DUPLICATE_ASSERTION_OF_THE_SAME_BUSINESS_KEY")
            self.assertEqual(occ["business_key_multiplicity"], 2)
            self.assertEqual(len(occ["sibling_original_sqlite_rowids"]), 1)
            self.assertEqual(r["qualification"]["policy"]["state"], "POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF")
            self.assertTrue(r["qualification"]["statements_ingested"]["reconciles"])
            self.assertEqual(r["qualification"]["denominator"]["state"], "RETAINED_FIXED_AS_OF_DENOMINATOR_ASSERTION")
        unknown = [r for r in self.rows("opportunity") if r["original_record"]["state"] == "UNKNOWN_NOT_HEALTHY"]
        self.assertEqual(len(unknown), 4)
        self.assertTrue(all(r["qualification"]["state_meaning"]["state"] ==
                            "NO_REPORT_STATEMENT_INGESTED_UNKNOWN_NOT_HEALTHY" and
                            r["qualification"]["health_inference"] == "NOT_ASSERTED" for r in unknown))

    def test_policy_qualification_keeps_the_original_season_and_completeness_limit(self) -> None:
        rows = {r["original_record"]["policy_id"]: r["qualification"] for r in self.rows("policy")}
        self.assertEqual(rows["CUSA-FB"]["policy_season"]["state"], "POLICY_SEASON_UNSTATED")
        self.assertEqual(rows["ACC-FB-2026-27"]["policy_season"]["state"], "ORIGINAL_POLICY_SEASON")
        self.assertEqual(rows["ACC-FB-2026-27"]["opportunity_references"], 4)
        self.assertTrue(all(v["state"] == "POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF" for v in rows.values()))

    def test_qualification_is_deterministic_across_sessions(self) -> None:
        a, b = self.session(), self.session()
        self.assertEqual(a.audit_lines(), b.audit_lines())
        self.assertEqual(a.audit_identity(), b.audit_identity())

    def test_qualification_does_not_depend_on_input_record_order(self) -> None:
        # The duplicate business key SRC-002:GAME:200 (rowids 5 and 7, 6 and 8) makes an order-dependent occurrence
        # ordinal or sibling list visible.
        base = self.session()
        lines, ident = base.audit_lines(), base.audit_identity()
        for name, reorder in (("reversed", lambda rows: list(reversed(rows))),
                              ("interleaved", lambda rows: rows[1::2] + rows[0::2])):
            other = self.session()
            other.records = {grain: reorder(rows) for grain, rows in other.records.items()}
            other._qualify()
            other._population()
            with self.subTest(order=name):
                self.assertEqual(other.audit_lines(), lines)
                self.assertEqual(other.audit_identity(), ident)
                dup = [q["occurrence"] for q in other.qualifications["opportunity"]
                       if q["key"]["original_sqlite_rowid"] in (5, 7)]
                self.assertEqual([(d["occurrence_ordinal_within_key"], d["sibling_original_sqlite_rowids"])
                                  for d in dup], [(1, [7]), (2, [5])])


# --------------------------------------------------------------------------------------------- selectors

class SelectorTests(WorldCase):
    def total(self, grain: str, **sel) -> int:
        return self.session().query(grain, sel)["total_count"]

    def test_exact_selectors_and_intersections(self) -> None:
        s = self.session()
        self.assertEqual(s.query("statement", {"--team": "Texas A&M"})["total_count"], 4)
        self.assertEqual(s.query("statement", {"--team": "Texas A&M", "--stage": "update_2_status",
                                               "--presence": "PUBLISHED_EMPTY"})["total_count"], 1)
        self.assertEqual(s.query("statement", {"--person-id": "OFFICIAL:Texas A&M:2026:5"})["total_count"], 4)
        self.assertEqual(s.query("statement", {"--published-name": "AK Dear"})["total_count"], 4)
        self.assertEqual(s.query("statement", {"--contest": "SRC-002:GAME:200"})["total_count"], 8)
        self.assertEqual(s.query("statement", {"--season": "2026"})["total_count"], 28)
        self.assertEqual(s.query("statement", {"--conference": "Big 12"})["total_count"], 4)
        sha = self.world.profile["witnesses"]["SEC_RAW_CAPTURE"]["sha256"]
        self.assertEqual(s.query("statement", {"--source-sha256": sha})["total_count"], 8)
        self.assertEqual(s.query("opportunity", {"--policy-id": "ACC-FB-2026-27"})["total_count"], 4)
        self.assertEqual(s.query("opportunity", {"--team": "Kentucky"})["total_count"], 2)
        self.assertEqual(s.query("opportunity", {"--conference": "MEAC"})["total_count"], 1)
        self.assertEqual(s.query("policy", {"--policy-season": "2026"})["total_count"], 1)
        self.assertEqual(s.query("policy", {"--source-sha256": "b" * 64})["total_count"], 1)
        self.assertEqual(s.query("policy", {"--conference": "ACC"})["total_count"], 1)

    def test_a_known_contest_returns_every_retained_occurrence_including_duplicates(self) -> None:
        self.assertEqual(self.total("opportunity", **{"--contest": "SRC-002:GAME:200"}), 4)

    def test_represented_selectors_with_an_empty_intersection_answer_an_explicit_empty_match(self) -> None:
        out = self.session().query("statement", {"--team": "Texas A&M", "--published-name": "AK Dear"})
        self.assertEqual((out["total_count"], out["rows"]), (0, []))
        self.assertEqual(out["empty_match"]["state"], "REPRESENTED_SELECTORS_WITH_EMPTY_INTERSECTION")
        out = self.session().query("statement", {"--team": "Delaware State"})
        self.assertEqual(out["total_count"], 0)
        self.assertIn("NOT_HEALTH", out["empty_match"]["meaning"])

    def test_foreign_well_formed_keys_refuse_as_not_in_profile(self) -> None:
        cases = [("statement", "--team", "East Texas A&M"), ("statement", "--team", "Texas"),
                 ("statement", "--team", "texas a&m"), ("opportunity", "--team", "Hogwarts"),
                 ("statement", "--contest", "SRC-002:GAME:999"), ("opportunity", "--contest", "SRC-002:GAME:999"),
                 ("statement", "--person-id", "CFBD:999"), ("statement", "--person-id", "OFFICIAL:Hogwarts:2026:1"),
                 ("statement", "--published-name", "Nobody Here"), ("statement", "--source-sha256", "c" * 64),
                 ("policy", "--source-sha256", "c" * 64), ("policy", "--policy-id", "NOPE-FB"),
                 ("opportunity", "--policy-id", "NOPE-FB"), ("statement", "--statement-id", "999"),
                 ("statement", "--reported-status", "Suspended"), ("statement", "--conference", "Ivy"),
                 ("policy", "--conference", "Ivy")]
        for grain, option, value in cases:
            with self.subTest(option=option, value=value):
                with self.assertRaises(ae.AvailabilityError) as ctx:
                    self.session().query(grain, {option: value})
                self.assertEqual(ctx.exception.code, "KEY_NOT_IN_PROFILE")

    def test_foreign_seasons_refuse_as_season_not_in_profile(self) -> None:
        for grain, option, value in (("statement", "--season", "2025"), ("opportunity", "--season", "2019"),
                                     ("policy", "--policy-season", "2019"),
                                     ("statement", "--person-id", "OFFICIAL:Kansas:2025:2")):
            with self.subTest(option=option, value=value):
                with self.assertRaises(ae.AvailabilityError) as ctx:
                    self.session().query(grain, {option: value})
                self.assertEqual(ctx.exception.code, "SEASON_NOT_IN_PROFILE")

    def test_malformed_selector_values_refuse_before_any_data_access(self) -> None:
        cases = [("--statement-id", v) for v in ("0", "-1", "1.0", "true", "+1", " 1", "99999999999999999999", "", "1e3")]
        cases += [("--contest", "401"), ("--contest", "SRC-002:GAME:"), ("--source-sha256", "A" * 64),
                  ("--source-sha256", "a" * 63), ("--stage", "final"), ("--presence", "EMPTY"),
                  ("--identity-state", "RESOLVED"), ("--contest-state", "BOUND"), ("--team", " Alabama"),
                  ("--team", ""), ("--team", "Ala\u0000bama"), ("--team", "Tex\ud800as"), ("--team", "x" * 201),
                  ("--published-name", "AK Dear "), ("--season", "26"), ("--season", "2026.0"),
                  ("--person-id", "CFBD:"), ("--person-id", "cfbd:1"), ("--cutoff", "2026-09-20"),
                  ("--cutoff", "2026-09-20T05:00:00"), ("--cutoff", "garbage"), ("--cutoff", "2026-02-30T00:00:00Z")]
        for option, value in cases:
            with self.subTest(option=option, value=value):
                with self.assertRaises(ae.AvailabilityError) as ctx:
                    ae.validate_selectors("statement", {option: value})
                self.assertEqual(ctx.exception.code, "INVALID_SELECTOR")

    def test_every_inapplicable_selector_is_refused_never_ignored(self) -> None:
        for option, spec in P.RULES["selectors"].items():
            for grain in P.GRAINS:
                if grain in spec["grains"]:
                    continue
                with self.subTest(option=option, grain=grain):
                    with self.assertRaises(ae.AvailabilityError) as ctx:
                        ae.validate_selectors(grain, {option: "x"})
                    self.assertEqual(ctx.exception.code, "SELECTOR_NOT_APPLICABLE")

    def test_cli_refuses_repeated_abbreviated_and_unknown_options(self) -> None:
        self.refused("ARGUMENT_INVALID", "--grain", "statement", "--team", "Kansas", "--team", "Kentucky")
        self.refused("ARGUMENT_INVALID", "--grain", "statement", "--tea", "Kansas")
        self.refused("ARGUMENT_INVALID", "--grain", "statement", "--bogus", "1")
        self.refused("ARGUMENT_INVALID", "--grain", "forecast")
        got, out, err = run_cli(["--grain", "statement"])
        self.assertEqual((got, err["refused"]), (2, "ARGUMENT_INVALID"))

    def test_unknown_profile_is_refused(self) -> None:
        self.refused("PROFILE_UNKNOWN", "--grain", "statement", "--profile", "OTHER_PROFILE")
        code, out, _err = self.cli("--grain", "profile", "--profile", P.PROFILE_ID)
        self.assertEqual(code, 0)


# --------------------------------------------------------------------------------------------- paging

class PagingTests(WorldCase):
    def test_adjacent_pages_conserve_every_key_and_occurrence_exactly_once(self) -> None:
        s = self.session()
        for grain, key in (("statement", lambda r: r["original_record"]["availability_row_id"]),
                           ("opportunity", lambda r: r["source_occurrence"]["original_sqlite_rowid"]),
                           ("policy", lambda r: r["original_record"]["policy_id"])):
            whole = s.query(grain, {}, all_rows=True)
            for limit in (1, 2, 3, 7):
                seen, offset = [], 0
                while True:
                    page = s.query(grain, {}, limit=str(limit), offset=str(offset))
                    self.assertEqual(page["total_count"], whole["total_count"])
                    seen += page["rows"]
                    if page["next_offset"] is None:
                        break
                    offset = page["next_offset"]
                self.assertEqual([key(r) for r in seen], [key(r) for r in whole["rows"]], (grain, limit))
                self.assertEqual(seen, whole["rows"])

    def test_duplicate_pairs_crossing_a_page_boundary_are_both_served(self) -> None:
        s = self.session()
        whole = s.query("opportunity", {"--contest": "SRC-002:GAME:200"}, all_rows=True)["rows"]
        first = s.query("opportunity", {"--contest": "SRC-002:GAME:200"}, limit="1", offset="0")["rows"]
        second = s.query("opportunity", {"--contest": "SRC-002:GAME:200"}, limit="1", offset="1")["rows"]
        self.assertEqual(first + second, whole[:2])
        self.assertEqual(first[0]["original_record"], second[0]["original_record"])
        self.assertNotEqual(first[0]["source_occurrence"], second[0]["source_occurrence"])

    def test_paging_bounds_and_offset_beyond_the_population(self) -> None:
        s = self.session()
        self.assertEqual(s.query("statement", {})["limit"], 100)
        out = s.query("statement", {"--team": "Kansas"}, limit="10", offset="999")
        self.assertEqual((out["rows"], out["total_count"], out["page_state"]), ([], 4,
                                                                                 "OFFSET_BEYOND_FILTERED_POPULATION"))
        for limit, offset, all_rows in (("0", None, False), ("1001", None, False), ("-1", None, False),
                                        ("ten", None, False), (None, "-1", False), (None, "1.0", False),
                                        (None, "99999999999999999999", False), ("5", None, True),
                                        (None, "0", True), (True, None, False)):
            with self.subTest(limit=limit, offset=offset, all_rows=all_rows):
                with self.assertRaises(ae.AvailabilityError) as ctx:
                    s.query("statement", {}, limit=limit, offset=offset, all_rows=all_rows)
                self.assertEqual(ctx.exception.code, "PAGING_INVALID")

    def test_all_equals_the_concatenated_pages_through_the_cli(self) -> None:
        code, whole, _ = self.cli("--grain", "statement", "--all")
        pages, offset = [], 0
        while True:
            code2, page, _ = self.cli("--grain", "statement", "--limit", "5", "--offset", str(offset))
            pages += page["rows"]
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        self.assertEqual((code, code2), (0, 0))
        self.assertEqual(whole["rows"], pages)


# --------------------------------------------------------------------------------------------- cutoff and time

class CutoffTests(WorldCase):
    def test_cutoff_compares_clocks_without_filtering_rows(self) -> None:
        s = self.session()
        plain = s.query("statement", {}, all_rows=True)
        cut = s.query("statement", {"--cutoff": "2026-09-22T23:00:00-04:00"}, all_rows=True)
        self.assertEqual(plain["total_count"], cut["total_count"])
        self.assertEqual([r["original_record"] for r in plain["rows"]], [r["original_record"] for r in cut["rows"]])
        claim = next(r for r in cut["rows"] if r["original_record"]["publication_time_established"])
        clocks = {c["clock"]: c for c in claim["cutoff_comparison"]["clocks"]}
        self.assertEqual(clocks["SOURCE_REPORTED_POSTING_CLAIM"]["relation"], "AT")
        self.assertEqual(clocks["PRIMARY_CAPTURE_RETRIEVAL_OBSERVATION"]["relation"], "AFTER")
        self.assertEqual(clocks["LATER_POSTING_CAPTURE_OBSERVATION"]["relation"], "AFTER")
        self.assertEqual(clocks["EFFECTIVE_TIME"]["relation"], "UNKNOWN")
        self.assertEqual(clocks["FIRST_KNOWN_TIME"]["relation"], "UNKNOWN")
        sec = next(r for r in cut["rows"] if r["original_record"]["conference"] == "SEC")
        clocks = {c["clock"]: c for c in sec["cutoff_comparison"]["clocks"]}
        self.assertEqual(clocks["PRIMARY_CAPTURE_RETRIEVAL_OBSERVATION"]["relation"], "BEFORE")
        self.assertEqual(clocks["SOURCE_REPORTED_POSTING_CLAIM"]["relation"], "UNKNOWN")
        self.assertEqual(cut["selectors"]["--cutoff"], "2026-09-23T03:00:00+00:00")

    def test_cutoff_is_only_a_statement_comparison(self) -> None:
        for grain in ("opportunity", "policy", "profile"):
            with self.assertRaises(ae.AvailabilityError) as ctx:
                ae.validate_selectors(grain, {"--cutoff": "2026-09-22T00:00:00Z"})
            self.assertEqual(ctx.exception.code, "SELECTOR_NOT_APPLICABLE")

    def test_us_eastern_offset_rule(self) -> None:
        import datetime as dt
        self.assertEqual(ae._us_eastern_offset(dt.date(2026, 9, 22), 23), -4)
        self.assertEqual(ae._us_eastern_offset(dt.date(2026, 12, 1), 12), -5)
        self.assertEqual(ae._us_eastern_offset(dt.date(2026, 3, 8), 1), -5)
        self.assertEqual(ae._us_eastern_offset(dt.date(2026, 3, 8), 3), -4)
        self.assertEqual(ae._us_eastern_offset(dt.date(2026, 11, 1), 1), -4)
        self.assertEqual(ae._us_eastern_offset(dt.date(2026, 11, 1), 2), -5)


class TemporalRefusalTests(WorldCase):
    def test_as_of_current_latest_pit_and_forecast_requests_are_refused_before_file_access(self) -> None:
        missing = str(self.tmp / "no" / "db.sqlite")
        for flag, code in (("--current", "CURRENT_STATE_NOT_SUPPORTED"), ("--latest", "CURRENT_STATE_NOT_SUPPORTED"),
                           ("--require-pit", "PIT_NOT_ADMITTED"),
                           ("--forecast-input", "FORECAST_ADMISSION_NOT_SUPPORTED")):
            with self.subTest(flag=flag):
                got, out, err = run_cli(["--database", missing, "--data-root", missing, "--grain", "statement", flag])
                self.assertEqual((got, err["refused"], out), (2, code, None))
        got, out, err = run_cli(["--database", missing, "--data-root", missing, "--grain", "statement", "--as-of",
                                 "2026-09-22T00:00:00Z"])
        self.assertEqual((got, err["refused"]), (2, "AS_OF_STATE_NOT_SUPPORTED"))
        self.assertFalse((self.tmp / "no").exists())

    def test_a_posting_claim_before_the_cutoff_still_does_not_admit_pit(self) -> None:
        self.refused("PIT_NOT_ADMITTED", "--grain", "statement", "--team", "Clemson", "--cutoff",
                     "2026-09-24T00:00:00Z", "--require-pit")


# --------------------------------------------------------------------------------------------- integrity

class IntegrityTests(WorldCase):
    def test_the_public_anchor_refuses_any_other_database_bytes(self) -> None:
        err = self.refused("DATABASE_IDENTITY_MISMATCH", "--grain", "statement", profile=None, exit_code=3)
        self.assertEqual(err["refusal_class"], "INPUT_INTEGRITY_FAILURE")

    def test_a_caller_pin_adds_a_constraint_and_cannot_bless_other_bytes(self) -> None:
        sha = self.world.profile["database"]["sha256"]
        self.assertEqual(self.cli("--grain", "profile", "--expect-sha256", sha)[0], 0)
        self.refused("EXPECTED_SHA256_MISMATCH", "--grain", "profile", "--expect-sha256", "f" * 64)
        self.refused("INVALID_SELECTOR", "--grain", "profile", "--expect-sha256", "F" * 64)
        conn = sqlite3.connect(self.world.database)
        conn.execute("UPDATE availability_statement_successor SET exact_status_text='Out' WHERE availability_row_id=1")
        conn.commit()
        conn.close()
        forged = fx.sha256_file(self.world.database)
        self.refused("DATABASE_IDENTITY_MISMATCH", "--grain", "profile", "--expect-sha256", forged, exit_code=3)
        self.refused("DATABASE_IDENTITY_MISMATCH", "--grain", "profile", "--expect-sha256", forged, exit_code=3,
                     profile=None)

    def test_tampering_an_unselected_table_still_refuses_the_whole_file(self) -> None:
        conn = sqlite3.connect(self.world.database)
        conn.execute("UPDATE release_identity SET value='tampered'")
        conn.commit()
        conn.close()
        self.refused("DATABASE_IDENTITY_MISMATCH", "--grain", "policy", exit_code=3)

    def test_missing_inputs_refuse_and_are_never_created(self) -> None:
        missing = self.tmp / "absent" / "x.sqlite"
        got, _out, err = run_cli(["--database", str(missing), "--data-root", str(self.world.data_root), "--grain",
                                  "profile"], profile=self.world.profile)
        self.assertEqual((got, err["refused"]), (3, "DATABASE_MISSING"))
        self.assertFalse(missing.parent.exists())
        got, _out, err = run_cli(["--database", str(self.world.database), "--data-root", str(self.tmp / "noroot"),
                                  "--grain", "profile"], profile=self.world.profile)
        self.assertEqual((got, err["refused"]), (3, "DATA_ROOT_MISSING"))
        self.assertFalse((self.tmp / "noroot").exists())
        posting = self.world.data_root.joinpath(*P.WITNESSES["ACC_CURRENT_POSTING"]["relative_path"].split("/"))
        posting.unlink()
        self.refused("WITNESS_MISSING", "--grain", "profile", exit_code=3)
        self.assertFalse(posting.exists())

    def test_a_tampered_witness_refuses_by_its_own_identity(self) -> None:
        sec = self.world.data_root.joinpath(*P.WITNESSES["SEC_RAW_CAPTURE"]["relative_path"].split("/"))
        sec.write_bytes(sec.read_bytes().replace(b"Questionable", b"Questionabl3"))
        self.refused("WITNESS_IDENTITY_MISMATCH", "--grain", "statement", exit_code=3)

    def test_a_trusted_but_malformed_witness_refuses_its_format(self) -> None:
        for wid, data in (("SEC_RAW_CAPTURE", b"Team\tDate\nAlabama\t9/12/26\n"),
                          ("ACC_ARCHIVE", b'{"rows": [["Team"]], "rendered_utc": "x"}'),
                          ("BIG12_ARCHIVE", b'{"rows": "not a table"}'),
                          ("BIGTEN_ARCHIVE", b"\xff\xfe not json"),
                          ("ACC_CURRENT_POSTING", b'{"cards": "not a list", "h1": "x"}')):
            with self.subTest(witness=wid):
                world = fx.World(self.tmp / f"m{wid}", mutate_witnesses=lambda w, wid=wid, data=data: w.update(
                    {wid: data}))
                self.world = world
                self.refused("WITNESS_FORMAT_INVALID", "--grain", "statement", exit_code=3)

    def _retrusted(self, sql: str) -> dict:
        conn = sqlite3.connect(self.world.database)
        conn.executescript(sql)
        conn.commit()
        conn.close()
        return fx.retrust(self.world)

    def test_trusted_synthetic_schema_forgeries_refuse_as_schema_mismatch(self) -> None:
        for sql in ('ALTER TABLE availability_policy ADD COLUMN "extra"',
                    'ALTER TABLE availability_policy DROP COLUMN "label"',
                    'ALTER TABLE availability_policy RENAME TO other_policy',
                    "INSERT INTO availability_policy (policy_id) VALUES ('X')",
                    "DELETE FROM availability_opportunity WHERE rowid = 3"):
            with self.subTest(sql=sql):
                world = fx.World(self.tmp / f"s{abs(hash(sql))}")
                self.world = world
                prof = self._retrusted(sql)
                self.refused("SCHEMA_MISMATCH", "--grain", "policy", profile=prof, exit_code=3)

    def test_trusted_synthetic_record_forgeries_refuse_as_record_invalid(self) -> None:
        cases = ["UPDATE availability_statement_successor SET quarantined = 2 WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET quarantined = 1.0 WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET availability_row_id = '1' WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET identity = '{bad' WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET identity = '[]' WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET contest = '{\"a\": NaN, \"state\": \"CONTEST_BOUND\"}' "
                 "WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET contest = '{\"state\": \"CONTEST_BOUND\", \"state\": "
                 "\"CONTEST_BOUND\"}' WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET contest = '" + '{"x":' * 40 + "1" + "}" * 40 +
                 "' WHERE availability_row_id = 1",
                 "UPDATE availability_statement_successor SET stage = 'final' WHERE availability_row_id = 1",
                 "UPDATE availability_opportunity SET side = 'neutral' WHERE rowid = 1",
                 "UPDATE availability_opportunity SET conference_game = 'yes' WHERE rowid = 1",
                 "UPDATE availability_policy SET quotes = '{}' WHERE policy_id = 'CUSA-FB'"]
        for sql in cases:
            with self.subTest(sql=sql[:80]):
                world = fx.World(self.tmp / f"r{abs(hash(sql))}")
                self.world = world
                prof = self._retrusted(sql)
                self.refused("RECORD_INVALID", "--grain", "policy", profile=prof, exit_code=3)

    def test_a_population_difference_refuses(self) -> None:
        prof = copy.deepcopy(self.world.profile)
        prof["population"]["publication_claims"] = 3
        self.refused("POPULATION_MISMATCH", "--grain", "profile", profile=prof, exit_code=3)

    def test_tampered_rules_or_builtin_profile_refuse_before_serving(self) -> None:
        rules = copy.deepcopy(P.RULES)
        rules["statement_qualification"]["first_known"] = "FIRST_KNOWN_ESTABLISHED"
        with self.assertRaises(ae.AvailabilityError) as ctx:
            ae.AvailabilityEvidence(self.world.database, self.world.data_root, profile=self.world.profile, rules=rules)
        self.assertEqual(ctx.exception.code, "QUALIFICATION_RULES_MISMATCH")
        with mock.patch.dict(P.PROFILE["database"], {"sha256": self.world.profile["database"]["sha256"]}):
            self.refused("PROFILE_INTEGRITY_MISMATCH", "--grain", "profile", profile=None, exit_code=3)

    def test_a_change_during_the_session_refuses_mixed_bytes(self) -> None:
        def mutate() -> None:
            with open(self.world.database, "ab") as handle:
                handle.write(b"\0")
        self.refused("INPUT_CHANGED_DURING_SESSION", "--grain", "profile", hooks={"after_read": mutate}, exit_code=3)

    def test_a_pinned_audit_identity_must_equal_the_qualification_collection(self) -> None:
        ident = self.session().audit_identity()
        self.assertEqual(self.session(audit=ident).query("profile", {})["qualified_audit"]["rows"], 40)
        wrong = {**ident, "lines_sha256": "0" * 64}
        with self.assertRaises(ae.AvailabilityError) as ctx:
            self.session(audit=wrong)
        self.assertEqual(ctx.exception.code, "QUALIFICATION_AUDIT_MISMATCH")

    def test_the_committed_audit_pin_binds_only_the_builtin_profile(self) -> None:
        wrong = {**self.session().audit_identity(), "lines_sha256": "0" * 64}
        with mock.patch.object(ae._audit, "QUALIFIED_AUDIT", wrong):
            # an injected synthetic profile is not bound by the builtin profile's pin ...
            self.assertIsNone(self.session().query("profile", {})["qualified_audit"])
            # ... while the builtin profile still verifies the whole-file anchor before any pin
            self.refused("DATABASE_IDENTITY_MISMATCH", "--grain", "profile", profile=None, exit_code=3)

    def test_refusal_codes_are_closed_and_classified(self) -> None:
        with self.assertRaises(ValueError):
            ae.AvailabilityError("SOMETHING_NEW", "x")
        self.assertEqual(ae.AvailabilityError("PIT_NOT_ADMITTED", "x").exit_code, 2)
        self.assertEqual(ae.AvailabilityError("DATABASE_IDENTITY_MISMATCH", "x").exit_code, 3)


# --------------------------------------------------------------------------------------------- locations

class LocationTests(WorldCase):
    def answer(self, database: str, data_root: str) -> dict:
        code, out, err = run_cli(["--database", database, "--data-root", data_root, "--grain", "statement",
                                  "--team", "Kansas"], profile=self.world.profile)
        self.assertEqual(code, 0, err)
        return out

    def test_network_device_and_namespace_spellings_refuse_before_any_access(self) -> None:
        root = str(self.world.data_root)
        db = str(self.world.database)
        with mock.patch.object(ae, "_io_path", side_effect=AssertionError("filesystem access")), \
                mock.patch.object(ae, "_file_identity", side_effect=AssertionError("filesystem access")):
            for spelling in ("\\\\bas-c62-host\\share\\db.sqlite", "//bas-c62-host/share/db.sqlite", "\\\\.\\nul",
                             "\\\\.\\pipe\\c62", "\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1\\x.sqlite",
                             "\\\\?\\Volume{00000000-0000-0000-0000-000000000000}\\x.sqlite",
                             "\\\\?\\UNC\\bas-c62-host\\share\\x.sqlite"):
                if os.name != "nt":
                    continue
                with self.subTest(database=spelling):
                    code, _out, err = run_cli(["--database", spelling, "--data-root", root, "--grain", "statement"],
                                              profile=self.world.profile)
                    self.assertEqual((code, err["refused"]), (2, "DATABASE_LOCATION_UNSUPPORTED"))
                with self.subTest(data_root=spelling):
                    code, _out, err = run_cli(["--database", db, "--data-root", spelling, "--grain", "statement"],
                                              profile=self.world.profile)
                    self.assertEqual((code, err["refused"]), (2, "DATA_ROOT_LOCATION_UNSUPPORTED"))

    @unittest.skipUnless(os.name == "nt", "native Windows spellings")
    def test_an_extended_spelling_that_sqlite_would_normalize_is_refused(self) -> None:
        code, _out, err = run_cli(["--database", EXT + str(self.world.database) + ".", "--data-root",
                                   str(self.world.data_root), "--grain", "statement"], profile=self.world.profile)
        self.assertEqual((code, err["refused"]), (2, "DATABASE_LOCATION_NOT_LITERAL"))

    def test_relative_spellings_answer_identically(self) -> None:
        base = self.answer(str(self.world.database), str(self.world.data_root))
        cwd = os.getcwd()
        try:
            os.chdir(self.world.root)
            rel = self.answer(os.path.join("db", "synthetic_release.sqlite"), "data")
        finally:
            os.chdir(cwd)
        self.assertEqual(rel, base)

    @unittest.skipUnless(os.name == "nt", "native Windows spellings")
    def test_native_extended_case_long_unicode_junction_and_deep_relative_spellings(self) -> None:
        import _winapi
        base = self.answer(str(self.world.database), str(self.world.data_root))
        self.assertEqual(self.answer(EXT + str(self.world.database), EXT + str(self.world.data_root)), base)
        self.assertEqual(self.answer(str(self.world.database).upper(), str(self.world.data_root).upper()), base)
        special = self.tmp / "spé cial ☃ [x] #%&"
        shutil.copytree(self.world.root, special)
        self.assertEqual(self.answer(str(special / "db" / "synthetic_release.sqlite"), str(special / "data")), base)
        long_top = self.tmp / "long"
        long_base = long_top.joinpath(*[f"long-c62-component-{c}-" + c * 40 for c in "abcd"])
        os.makedirs(EXT + str(long_base))
        try:
            for part in ("db", "data"):
                shutil.copytree(EXT + str(self.world.root / part), EXT + str(long_base / part))
            long_db = long_base / "db" / "synthetic_release.sqlite"
            self.assertGreater(len(str(long_db)), 260)
            self.assertEqual(self.answer(str(long_db), str(long_base / "data")), base)
            self.assertEqual(self.answer(EXT + str(long_db), EXT + str(long_base / "data")), base)
        finally:
            shutil.rmtree(EXT + str(long_top))
        junction = self.tmp / "jn"
        _winapi.CreateJunction(str(self.world.root), str(junction))
        try:
            self.assertEqual(self.answer(str(junction / "db" / "synthetic_release.sqlite"), str(junction / "data")),
                             base)
        finally:
            os.rmdir(junction)
        # Size the three components from the actual temporary root (hosted runners have shorter roots): the working
        # directory stays below MAX_PATH while the uncollapsed relative join exceeds it (the C61 boundary).
        width = max(8, (240 - len(str(self.world.root))) // 3 - 1)
        deep = self.world.root.joinpath(*[(c * width)[:width] for c in "pqr"])
        self.assertLess(len(str(deep)), 250)
        os.makedirs(EXT + str(deep))
        relative = os.path.join(*[".."] * 3, "db", "synthetic_release.sqlite")
        self.assertGreater(len(os.path.join(str(deep), relative)), 260)
        self.assertLess(len(os.path.abspath(os.path.join(str(deep), relative))), 260)
        cwd = os.getcwd()
        try:
            os.chdir(str(deep))
            self.assertEqual(self.answer(relative, str(self.world.data_root)), base)
        finally:
            os.chdir(cwd)

    @unittest.skipUnless(os.name == "nt", "native Windows spellings")
    def test_native_short_spelling_when_the_volume_provides_one(self) -> None:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        kernel32.GetShortPathNameW.restype = wintypes.DWORD
        target = self.tmp / "a-rather-long-directory-name-for-short-names"
        shutil.copytree(self.world.root, target)
        buffer = ctypes.create_unicode_buffer(1024)
        if not kernel32.GetShortPathNameW(str(target / "db" / "synthetic_release.sqlite"), buffer, 1024) or \
                buffer.value == str(target / "db" / "synthetic_release.sqlite"):
            self.skipTest("the volume reports no 8.3 short name")
        base = self.answer(str(self.world.database), str(self.world.data_root))
        self.assertEqual(self.answer(buffer.value, str(target / "data")), base)


# --------------------------------------------------------------------------------------------- CLI process

class ProcessTests(WorldCase):
    def child(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(REPO / "src"), str(REPO / "tests"), env.get("PYTHONPATH", "")])
        code = ("import sys, availability_evidence_fixture as fx, json; "
                "from aggie_analytics.availability_evidence import query as q; "
                "from pathlib import Path; "
                "prof = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); "
                "raise SystemExit(q.main(sys.argv[2:], profile=prof))")
        prof = self.tmp / "profile.json"
        prof.write_text(json.dumps(self.world.profile), encoding="utf-8")
        return subprocess.run([sys.executable, "-B", "-c", code, str(prof), "--database", str(self.world.database),
                               "--data-root", str(self.world.data_root), *args], capture_output=True, env=env,
                              check=False)

    def test_a_real_child_process_answers_utf8_and_refuses_a_lone_surrogate_without_a_traceback(self) -> None:
        ok = self.child("--grain", "statement", "--team", "Texas A&M")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout.decode("utf-8"))["total_count"], 4)
        if os.name == "nt":
            bad = self.child("--grain", "statement", "--team", "Tex\ud800as")
            self.assertEqual(bad.returncode, 2)
            self.assertNotIn(b"Traceback", bad.stderr)
            self.assertEqual(json.loads(bad.stderr.decode("ascii").strip().splitlines()[-1])["refused"],
                             "INVALID_SELECTOR")
            self.assertEqual(bad.stdout, b"")

    def test_module_help_names_the_fixed_profile_and_its_limits(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(REPO / "src"), env.get("PYTHONPATH", "")])
        out = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.availability_evidence.query", "--help"],
                             capture_output=True, env=env, check=False)
        self.assertEqual(out.returncode, 0)
        text = " ".join(out.stdout.decode("utf-8").split())
        self.assertIn("C37_2026_AVAILABILITY_ASSERTIONS_V1", text)
        self.assertIn("pit_admission=NOT_ADMITTED", text)


# --------------------------------------------------------------------------------------------- mounted genuine

def _genuine() -> tuple[Path, Path] | None:
    root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not root:
        return None
    db = Path(root).joinpath(*GENUINE_DB_REL.split("/"))
    return (db, Path(root)) if db.is_file() else None


@unittest.skipUnless(_genuine(), "the fixed C37 database and witnesses are not mounted")
class MountedGenuineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db, cls.root = _genuine()
        cls.session = ae.AvailabilityEvidence(cls.db, cls.root)

    def query(self, *args: str) -> dict:
        code, out, err = run_cli(["--database", str(self.db), "--data-root", str(self.root), *args])
        self.assertEqual(code, 0, err)
        return out

    def test_profile_coverage_is_the_frozen_population(self) -> None:
        rec = self.query("--grain", "profile")["rows"][0]["profile"]
        self.assertEqual(rec["population"], P.PROFILE["population"])
        summary = rec["qualification_summary"]
        self.assertEqual(sum(summary["source_cells"].values()), 1592)
        self.assertEqual(summary["publication"].get("SOURCE_POSTING_CLAIM_WITNESSED_IN_LATER_CAPTURE"), 19)
        self.assertEqual(summary["statements_ingested_reconciled"], 3474)

    def test_statement_281_carries_its_archive_cell_and_posting_witness(self) -> None:
        row = self.query("--grain", "statement", "--statement-id", "281")["rows"][0]
        self.assertEqual(row["qualification"]["source_cell"]["witness"], "ACC_ARCHIVE")
        self.assertEqual(row["qualification"]["publication"]["witness"]["id"], "ACC_CURRENT_POSTING")
        self.assertEqual(row["qualification"]["publication"]["claim_utc"], "2026-09-23T03:00:00+00:00")

    def test_texas_am_and_self_opponent_and_empty_cells(self) -> None:
        tamu = self.query("--grain", "statement", "--team", "Texas A&M", "--all")
        self.assertGreater(tamu["total_count"], 0)
        self.assertTrue(all(r["original_record"]["program"] == "Texas A&M" for r in tamu["rows"]))
        self.assertEqual(self.query("--grain", "statement", "--contest-state", "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF",
                                    "--all")["total_count"], 40)
        self.assertEqual(self.query("--grain", "statement", "--presence", "PUBLISHED_EMPTY", "--all")["total_count"], 179)

    def test_unknown_opportunities_policies_cutoff_and_pit_refusal(self) -> None:
        opp = self.query("--grain", "opportunity", "--all")
        self.assertEqual(opp["total_count"], 3474)
        self.assertEqual(sum(r["original_record"]["state"] == "UNKNOWN_NOT_HEALTHY" for r in opp["rows"]), 3431)
        pol = self.query("--grain", "policy", "--policy-id", "ACC-FB-2026-27")
        self.assertEqual(pol["rows"][0]["qualification"]["state"], "POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF")
        cut = self.query("--grain", "statement", "--statement-id", "281", "--cutoff", "2026-09-23T00:00:00Z")
        clocks = {c["clock"]: c["relation"] for c in cut["rows"][0]["cutoff_comparison"]["clocks"]}
        self.assertEqual((clocks["SOURCE_REPORTED_POSTING_CLAIM"], clocks["EFFECTIVE_TIME"]), ("AFTER", "UNKNOWN"))
        code, _out, err = run_cli(["--database", str(self.db), "--data-root", str(self.root), "--grain", "statement",
                                   "--require-pit"])
        self.assertEqual((code, err["refused"]), (2, "PIT_NOT_ADMITTED"))

    def test_the_committed_audit_pin_is_the_genuine_qualification(self) -> None:
        self.assertIsNotNone(audit.QUALIFIED_AUDIT)
        self.assertEqual(self.session.audit_identity(), audit.QUALIFIED_AUDIT)
        self.assertEqual(self.query("--grain", "profile")["qualified_audit"],
                         {"lines_sha256": audit.QUALIFIED_AUDIT["lines_sha256"], "rows": 5079})


if __name__ == "__main__":
    unittest.main()
