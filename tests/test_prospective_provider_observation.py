"""BAT-723 prospective provider-observation capsule: builder, reader and the explicit query mode (TP51-A01 3-4)."""
from __future__ import annotations

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

REPO_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import prospective_provider_observation_fixture as fx  # noqa: E402
from aggie_analytics.national_source_time import prospective, query  # noqa: E402
from tools import build_prospective_provider_observation as builder  # noqa: E402

CUTOFF = "2026-10-12T00:00:00Z"


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="bat723-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def build(self, world: fx.World, name: str = "w", **overrides) -> tuple[dict, Path]:
        result = builder.build(world.build_args(self.tmp / name, **overrides))
        return result, Path(result["capsule"])

    def run_cli(self, argv: list[str], authority: str | None) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(argv, prospective_contract_sha256=authority)
            except SystemExit as exc:
                code = exc.code
        refused = None
        for line in reversed(err.getvalue().strip().splitlines()):
            try:
                refused = json.loads(line).get("refused")
                break
            except ValueError:
                continue
        return code, (json.loads(out.getvalue()) if out.getvalue().strip() else None), refused or err.getvalue()


class CommittedContractTests(unittest.TestCase):
    def test_reader_anchor_is_the_committed_contract(self) -> None:
        data = fx.CONTRACT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), prospective.CONTRACT_SHA256)
        contract = json.loads(data.decode("utf-8"))
        self.assertEqual(contract["contract_id"], prospective.CONTRACT_ID)
        self.assertEqual(contract["population_id"], prospective.POPULATION)
        self.assertEqual(contract["capsule"]["top_level_members"], list(prospective.TOP_LEVEL))
        self.assertEqual(contract["capsule"]["bundle"], prospective.BUNDLE)
        self.assertEqual(contract["labels"], prospective.LABELS)
        self.assertEqual(contract["query_rules"]["grains"], list(prospective.GRAINS))
        self.assertEqual(contract["capsule"]["identity"]["members"], list(prospective.identity_document(
            {"contract": {"sha256": "0" * 64}, "bundle": {}, **{k: None for k in prospective.TOP_LEVEL
                                                                 if k not in ("contract", "bundle")}})))

    def test_committed_membership_is_the_frozen_finite_cohort(self) -> None:
        contract = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        keys = contract["membership"]["event_keys"]
        participants = contract["membership"]["participants"]
        self.assertEqual((len(keys), len(set(keys))), (25, 25))
        self.assertEqual(len(participants), 50)
        self.assertEqual(sorted(keys), keys)
        self.assertTrue(all(prospective.EVENT_KEY_RE.match(k) for k in keys))
        self.assertTrue(all(prospective.TEAM_KEY_RE.match(p["team_key"]) for p in participants))
        self.assertEqual({p["side"] for p in participants}, {"home", "away"})
        self.assertEqual(contract["source"]["raw_sha256"],
                         "f0e86a3051635e28f5b5a43edb51a67fe4b7cf0e4f6469754c8b1ae4b5152fa9")
        self.assertEqual(contract["source"]["receipt_sha256"],
                         "d3e99883741c269425a5aeab94ba5f901875e759209e9ab326ae976871993c26")
        self.assertEqual(contract["source"]["expected_cohort_sha256"],
                         "f92240caf742c3e1ccea9e9ee79a7331f9c586e9c8ddf222467aea9f6342b328")

    def test_default_authority_refuses_a_fixture_contract(self) -> None:
        world = fx.World()
        with self.assertRaises(prospective.ProspectiveEvidenceError) as caught:
            prospective.derive(world.raw, world.receipt, world.expected, world.contract)
        self.assertEqual(caught.exception.code, "CONTRACT_NOT_COMMITTED_AUTHORITY")


class BuildAndServeTests(_Workspace):
    def test_genuine_fixture_builds_verifies_and_serves_every_record(self) -> None:
        world = fx.World()
        result, capsule = self.build(world)
        self.assertEqual(result["capsule_state"], "MATERIALIZED")
        self.assertEqual(result["counts"]["events"], 3)
        self.assertEqual(result["counts"]["participants"], 6)
        self.assertEqual(capsule.parent.name, result["identity"])
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["identity_document"], result["identity_document"])
        self.assertEqual(manifest["build"]["built_at_role"], "BUILD_CLOCK_ONLY_NOT_OBSERVATION_TIME")
        code, events, _ = self.run_cli(["--prospective-evidence", str(capsule), "--grain", "prospective-event",
                                        "--cutoff", CUTOFF, "--all"], world.authority)
        self.assertEqual(code, 0)
        self.assertEqual([r["event"]["event_key"] for r in events["rows"]],
                         ["espn:event:900000001", "espn:event:900000002", "espn:event:900000003"])
        first = events["rows"][0]["event"]
        self.assertEqual((first["home"]["team_key"], first["away"]["team_key"]), ("espn:team:9001", "espn:team:9002"))
        self.assertEqual(first["scheduled_utc"], "2026-10-17T16:00:00Z")
        self.assertEqual(first["season_year"], 2026)
        self.assertEqual(first["support_state"], "SUPPORTED")
        for row in events["rows"]:
            self.assertEqual(row["labels"]["evidence_authority"], "SOURCE_OBSERVATION_ONLY")
            self.assertEqual(row["labels"]["pit_admission"], "PIT_NOT_ADMITTED")
            self.assertIn("PROVIDER_CLAIM", row["labels"]["source_authority"])
            self.assertIn("COMPLETENESS_UNKNOWN", row["labels"]["coverage"])
            self.assertEqual(row["observation_at_cutoff"], prospective.AVAILABLE)
        code, records, _ = self.run_cli(["--prospective-evidence", str(capsule), "--grain",
                                         "prospective-team-record", "--cutoff", CUTOFF, "--all"], world.authority)
        self.assertEqual(code, 0)
        by_team = {r["participant"]["team_key"]: r["participant"] for r in records["rows"]}
        self.assertEqual(by_team["espn:team:9001"]["overall_record"]["summary"], "4-1")
        self.assertEqual((by_team["espn:team:9001"]["overall_record"]["wins"],
                          by_team["espn:team:9001"]["overall_record"]["losses"],
                          by_team["espn:team:9001"]["overall_record"]["ties"],
                          by_team["espn:team:9001"]["overall_record"]["ties_rule"]),
                         (4, 1, 0, prospective.TIES_ZERO_RULE))
        self.assertEqual((by_team["espn:team:9005"]["overall_record"]["ties"],
                          by_team["espn:team:9005"]["overall_record"]["ties_rule"]), (1, prospective.TIES_STATED_RULE))
        self.assertEqual(by_team["espn:team:9001"]["record_pointer"], "/events/0/competitions/0/competitors/0/records/0")
        self.assertEqual(records["source"]["odds_provider_object"]["role"], prospective.ODDS_PROVIDER_ROLE)
        self.assertEqual(records["source"]["endpoint"], fx.FIXTURE_URL)

    def test_rebuild_is_already_present_identical_and_a_changed_directory_refuses(self) -> None:
        world = fx.World()
        first, capsule = self.build(world)
        args = world.build_args(self.tmp / "w")
        again = builder.build(args)
        self.assertEqual((again["capsule_state"], again["manifest_state"]), ("ALREADY_PRESENT_IDENTICAL",
                                                                             "ALREADY_PRESENT"))
        self.assertEqual(again["identity"], first["identity"])
        (capsule.parent / "extra.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(builder.BuildRefused) as caught:
            builder.build(args)
        self.assertEqual(caught.exception.code, "EXISTING_IDENTITY_DIFFERS")

    def test_order_chunk_and_interrupted_resumed_builds_are_byte_identical(self) -> None:
        world = fx.World()
        base, capsule = self.build(world, "base")
        reference = builder.directory_members(capsule.parent)
        for index, (order, chunk) in enumerate((("reversed", "1"), ("shuffled:7", "13"), ("shuffled:99", "4096"))):
            result, other = self.build(world, f"v{index}", processing_order=order, chunk_size=chunk)
            self.assertEqual(result["identity"], base["identity"])
            self.assertEqual(builder.directory_members(other.parent), reference)
        args = world.build_args(self.tmp / "crash", stop_after_members=2)
        with self.assertRaises(builder.BuildInterrupted):
            builder.build(args)
        final = self.tmp / "crash" / "canonical" / "sha256" / base["identity"]
        self.assertFalse(final.exists())
        staged = list((self.tmp / "crash" / "canonical" / ".staging").iterdir())
        self.assertEqual(len(staged), 1)
        code, _, refused = self.run_cli(["--prospective-evidence", str(final / "capsule.json"), "--grain",
                                         "prospective-event", "--cutoff", CUTOFF], world.authority)
        self.assertEqual((code, refused), (2, "EVIDENCE_MISSING"))
        if (staged[0] / "capsule.json").exists():
            code, _, refused = self.run_cli(["--prospective-evidence", str(staged[0] / "capsule.json"), "--grain",
                                             "prospective-event", "--cutoff", CUTOFF], world.authority)
            self.assertEqual((code, refused), (2, "EVIDENCE_LOCATION_INVALID"))
        resumed = builder.build(world.build_args(self.tmp / "crash"))
        self.assertEqual(resumed["identity"], base["identity"])
        self.assertEqual(builder.directory_members(final), reference)

    def test_unrelated_raw_fields_do_not_change_any_record(self) -> None:
        def noise(events):
            for e in events:
                comp = e["competitions"][0]
                comp["odds"] = [{"details": "changed"}]
                comp["venue"] = {"id": "77", "fullName": "Another Field"}
                comp["neutralSite"] = True
                for c in comp["competitors"]:
                    c["score"] = "35"
                    c["curatedRank"] = {"current": 1}
                    c["records"][1]["summary"] = "9-9"
        a = prospective.derive(*_inputs(fx.World()), contract_sha256=fx.World().authority)
        noisy = fx.World(fx.mutate_events(noise))
        b = prospective.derive(*_inputs(noisy), contract_sha256=noisy.authority)
        self.assertEqual(prospective.canonical_bytes(a["events"]), prospective.canonical_bytes(b["events"]))
        self.assertEqual(prospective.canonical_bytes(a["participants"]), prospective.canonical_bytes(b["participants"]))


def _inputs(world: fx.World) -> tuple[bytes, bytes, bytes, bytes]:
    return world.raw, world.receipt, world.expected, world.contract


class AnomalyRuleTests(unittest.TestCase):
    """Missing/ambiguous source facts stay explicit unsupported (never silently selected, never invented)."""

    def derive(self, mutator) -> dict:
        world = fx.World(fx.mutate_events(mutator))
        return prospective.derive(*_inputs(world), contract_sha256=world.authority)

    def event(self, doc: dict, key: str = "espn:event:900000001") -> dict:
        return next(r for r in doc["events"] if r["event_key"] == key)

    def participant(self, doc: dict, team: str) -> dict:
        return next(r for r in doc["participants"] if r["team_key"] == team)

    def test_duplicate_and_missing_roles(self) -> None:
        def duplicate(events):
            events[0]["competitions"][0]["competitors"][1]["homeAway"] = "home"
        doc = self.derive(duplicate)
        row = self.event(doc)
        self.assertEqual(row["support_state"], "UNSUPPORTED")
        self.assertIn("ROLE_HOME_DUPLICATE", row["unsupported_reasons"])
        self.assertIn("ROLE_AWAY_MISSING", row["unsupported_reasons"])
        self.assertIsNone(row["home"])
        self.assertIsNone(row["away"])

        def neutral(events):
            events[0]["competitions"][0]["competitors"][1]["homeAway"] = "neutral"
        doc = self.derive(neutral)
        self.assertIn("ROLE_VALUE_INVALID", self.event(doc)["unsupported_reasons"])
        self.assertIn("SIDE_INVALID", self.participant(doc, "espn:team:9002")["unsupported_reasons"])

        def single(events):
            del events[0]["competitions"][0]["competitors"][1]
        doc = self.derive(single)
        self.assertIn("COMPETITOR_COUNT_NOT_TWO", self.event(doc)["unsupported_reasons"])
        self.assertIn("ROLE_AWAY_MISSING", self.event(doc)["unsupported_reasons"])

    def test_competition_count_and_contradictions(self) -> None:
        def two(events):
            events[0]["competitions"].append(copy.deepcopy(events[0]["competitions"][0]))
        doc = self.derive(two)
        row = self.event(doc)
        self.assertEqual(row["competition_count"], 2)
        self.assertIn("COMPETITION_COUNT_NOT_ONE", row["unsupported_reasons"])
        self.assertIsNone(row["home"])
        self.assertFalse([p for p in doc["participants"] if p["event_key"] == row["event_key"]])

        def date(events):
            events[0]["competitions"][0]["date"] = "2026-10-17T19:00Z"
        row = self.event(self.derive(date))
        self.assertIn("EVENT_COMPETITION_DATE_CONTRADICTION", row["unsupported_reasons"])
        self.assertIsNone(row["scheduled_utc"])
        self.assertEqual(row["scheduled_literal"]["competition_date"], "2026-10-17T19:00Z")

        def state(events):
            events[0]["competitions"][0]["status"]["type"]["name"] = "STATUS_POSTPONED"
        row = self.event(self.derive(state))
        self.assertIn("EVENT_COMPETITION_STATUS_CONTRADICTION", row["unsupported_reasons"])
        self.assertEqual(row["competition_status"]["name"], "STATUS_POSTPONED")
        self.assertEqual(row["event_status"]["name"], "STATUS_SCHEDULED")

    def test_no_invented_kickoff(self) -> None:
        def naive(events):
            events[0]["date"] = events[0]["competitions"][0]["date"] = "2026-10-17T16:00"
        row = self.event(self.derive(naive))
        self.assertIn("SCHEDULED_TIME_NO_VALID_ZONE", row["unsupported_reasons"])
        self.assertIsNone(row["scheduled_utc"])

        def trailing_newline(events):
            events[0]["date"] = events[0]["competitions"][0]["date"] = "2026-10-17T16:00Z\n"
        row = self.event(self.derive(trailing_newline))
        self.assertIn("SCHEDULED_TIME_NO_VALID_ZONE", row["unsupported_reasons"])
        self.assertIsNone(row["scheduled_utc"])
        self.assertEqual(row["scheduled_literal"]["event_date"], "2026-10-17T16:00Z\n")

        def tba(events):
            events[0]["competitions"][0]["timeValid"] = False
        row = self.event(self.derive(tba))
        self.assertIn("SCHEDULED_TIME_NOT_VALID_PER_SOURCE", row["unsupported_reasons"])
        self.assertIsNone(row["scheduled_utc"])
        self.assertIs(row["time_valid"], False)

        def boolean_season(events):
            events[0]["season"]["year"] = True
        row = self.event(self.derive(boolean_season))
        self.assertIn("SEASON_YEAR_INVALID", row["unsupported_reasons"])
        self.assertIsNone(row["season_year"])

    def test_overall_record_rules(self) -> None:
        cases = {"4-1.0": "RECORD_SUMMARY_MALFORMED", "-1-2": "RECORD_SUMMARY_MALFORMED",
                 "04-1": "RECORD_SUMMARY_MALFORMED", "4\u20131": "RECORD_SUMMARY_MALFORMED",
                 " 4-1": "RECORD_SUMMARY_MALFORMED", "4-1-0-0": "RECORD_SUMMARY_MALFORMED",
                 "\u0664-1": "RECORD_SUMMARY_MALFORMED", "4-1\n": "RECORD_SUMMARY_MALFORMED",
                 "4-1-1\n": "RECORD_SUMMARY_MALFORMED"}
        for summary, reason in cases.items():
            def bad(events, summary=summary):
                events[0]["competitions"][0]["competitors"][0]["records"][0]["summary"] = summary
            row = self.participant(self.derive(bad), "espn:team:9001")
            self.assertIn(reason, row["unsupported_reasons"], summary)
            self.assertEqual(row["overall_record"]["summary"], summary)
            self.assertIsNone(row["overall_record"]["wins"])

        def three(events):
            events[0]["competitions"][0]["competitors"][0]["records"][0]["summary"] = "4-1-1"
        row = self.participant(self.derive(three), "espn:team:9001")
        self.assertEqual((row["overall_record"]["ties"], row["overall_record"]["ties_rule"]),
                         (1, prospective.TIES_STATED_RULE))
        self.assertEqual(row["support_state"], "SUPPORTED")

        def duplicate(events):
            records = events[0]["competitions"][0]["competitors"][0]["records"]
            records.append(dict(records[0], summary="5-0"))
        row = self.participant(self.derive(duplicate), "espn:team:9001")
        self.assertIn("RECORD_OVERALL_TOTAL_MULTIPLE", row["unsupported_reasons"])
        self.assertIsNone(row["overall_record"])
        self.assertIsNone(row["record_pointer"])
        self.assertEqual(len(row["candidate_record_pointers"]), 2)

        def borrowed(events):
            records = events[0]["competitions"][0]["competitors"][0]["records"]
            del records[0]
            records.append({"name": "Overall", "type": "total", "summary": "7-0"})
            records.append({"name": "overall", "type": "homerecord", "summary": "8-0"})
            records.append({"name": "overall record", "type": "total", "summary": "9-0"})
        row = self.participant(self.derive(borrowed), "espn:team:9001")
        self.assertIn("RECORD_OVERALL_TOTAL_MISSING", row["unsupported_reasons"])
        self.assertIsNone(row["overall_record"])

        def missing_summary(events):
            del events[0]["competitions"][0]["competitors"][0]["records"][0]["summary"]
        row = self.participant(self.derive(missing_summary), "espn:team:9001")
        self.assertIn("RECORD_SUMMARY_MISSING", row["unsupported_reasons"])

    def test_participant_identity_rules(self) -> None:
        def disagree(events):
            events[0]["competitions"][0]["competitors"][0]["team"]["id"] = "9999"
        doc = self.derive(disagree)
        row = self.participant(doc, "espn:team:9001")
        self.assertIn("TEAM_ID_DISAGREEMENT", row["unsupported_reasons"])
        self.assertEqual((row["source_competitor_id"], row["source_team_id"]), ("9001", "9999"))

        def invalid(events):
            events[0]["competitions"][0]["competitors"][0]["id"] = "ab9"
            events[0]["competitions"][0]["competitors"][0]["team"]["id"] = "ab9"
        doc = self.derive(invalid)
        row = next(r for r in doc["participants"] if r["source_competitor_id"] == "ab9")
        self.assertIsNone(row["team_key"])
        self.assertIn("PARTICIPANT_ID_INVALID", row["unsupported_reasons"])
        self.assertIn("ROLE_HOME_ID_INVALID", self.event(doc)["unsupported_reasons"])

        def trailing_newline(events):
            events[0]["competitions"][0]["competitors"][0]["id"] = "9001\n"
            events[0]["competitions"][0]["competitors"][0]["team"]["id"] = "9001\n"
        doc = self.derive(trailing_newline)
        row = next(r for r in doc["participants"] if r["source_competitor_id"] == "9001\n")
        self.assertIsNone(row["team_key"])
        self.assertIn("PARTICIPANT_ID_INVALID", row["unsupported_reasons"])

        def event_id(events):
            events[0]["id"] = events[0]["competitions"][0]["id"] = "900000001\n"
        with self.assertRaises(prospective.ProspectiveEvidenceError) as caught:
            self.derive(event_id)
        self.assertEqual(caught.exception.code, "RAW_EVENT_ID_INVALID")

    def test_membership_must_equal_the_frozen_cohort(self) -> None:
        world = fx.World()
        contract = json.loads(world.contract.decode("utf-8"))
        contract["membership"]["event_keys"] = contract["membership"]["event_keys"][:-1]
        forged = (json.dumps(contract, indent=1) + "\n").encode("utf-8")
        with self.assertRaises(prospective.ProspectiveEvidenceError) as caught:
            prospective.derive(world.raw, world.receipt, world.expected, forged,
                               contract_sha256=hashlib.sha256(forged).hexdigest())
        self.assertEqual(caught.exception.code, "COHORT_MEMBERSHIP_MISMATCH")


class CutoffAndSelectorTests(_Workspace):
    def setUp(self) -> None:
        super().setUp()
        self.world = fx.World()
        _, self.capsule = self.build(self.world)

    def q(self, *argv: str) -> tuple[int, dict | None, str]:
        return self.run_cli(["--prospective-evidence", str(self.capsule), *argv], self.world.authority)

    def test_cutoff_boundaries_and_equivalent_zones(self) -> None:
        cases = {"2026-10-11T18:15:55.264958Z": prospective.UNAVAILABLE,
                 "2026-10-11T18:15:55.264959Z": prospective.INDETERMINATE,
                 "2026-10-11T18:15:55.500000Z": prospective.INDETERMINATE,
                 "2026-10-11T18:15:55.744673Z": prospective.INDETERMINATE,
                 "2026-10-11T18:15:55.744674Z": prospective.AVAILABLE,
                 "2026-10-11T13:15:55.744674-05:00": prospective.AVAILABLE,
                 "2026-10-11T20:15:55.264958+02:00": prospective.UNAVAILABLE,
                 "2026-10-01T00:00:00Z": prospective.UNAVAILABLE, "2027-01-01T00:00:00Z": prospective.AVAILABLE}
        for cutoff, state in cases.items():
            for grain in prospective.GRAINS:
                code, doc, _ = self.q("--grain", grain, "--cutoff", cutoff, "--all")
                self.assertEqual(code, 0, cutoff)
                self.assertEqual(doc["observation_at_cutoff"]["state"], state, cutoff)
                self.assertTrue(all(r["observation_at_cutoff"] == state for r in doc["rows"]))
        late = self.q("--grain", "prospective-team-record", "--cutoff", "2027-01-01T00:00:00Z", "--all")[1]
        early = self.q("--grain", "prospective-team-record", "--cutoff", "2026-10-11T18:15:55.744674Z", "--all")[1]
        self.assertEqual([r["participant"] for r in late["rows"]], [r["participant"] for r in early["rows"]])

    def test_cutoff_is_required_and_aware(self) -> None:
        for argv, code in ((["--grain", "prospective-event"], "CUTOFF_REQUIRED"),
                           (["--grain", "prospective-event", "--cutoff", "2026-10-12T00:00:00"],
                            "CUTOFF_TIMEZONE_REQUIRED"),
                           (["--grain", "prospective-event", "--cutoff", "2026-10-12"], "CUTOFF_TIMEZONE_REQUIRED"),
                           (["--grain", "prospective-event", "--cutoff", "tomorrow"], "CUTOFF_INVALID")):
            self.assertEqual(self.q(*argv)[0::2], (2, code))

    def test_filters_paging_and_season_scope(self) -> None:
        base = ["--cutoff", CUTOFF]
        code, doc, _ = self.q("--grain", "prospective-event", "--event", "espn:event:900000002", *base)
        self.assertEqual((code, doc["total"], doc["rows"][0]["event"]["event_key"]), (0, 1, "espn:event:900000002"))
        code, doc, _ = self.q("--grain", "prospective-event", "--team", "espn:team:9006", *base)
        self.assertEqual([r["event"]["event_key"] for r in doc["rows"]], ["espn:event:900000003"])
        code, doc, _ = self.q("--grain", "prospective-team-record", "--team", "espn:team:9006", *base)
        self.assertEqual([r["participant"]["team_key"] for r in doc["rows"]], ["espn:team:9006"])
        code, doc, _ = self.q("--grain", "prospective-team-record", "--event", "espn:event:900000001", *base)
        self.assertEqual(sorted(r["participant"]["team_key"] for r in doc["rows"]), ["espn:team:9001",
                                                                                     "espn:team:9002"])
        code, doc, _ = self.q("--grain", "prospective-team-record", "--season", "2026", "--event",
                              "espn:event:900000001", "--team", "espn:team:9002", *base)
        self.assertEqual((doc["total"], doc["rows"][0]["participant"]["team_key"]), (1, "espn:team:9002"))
        code, doc, _ = self.q("--grain", "prospective-event", "--season", "2026", "--event", "espn:event:900000001",
                              "--team", "espn:team:9001", *base)
        self.assertEqual(doc["total"], 1)
        code, doc, _ = self.q("--grain", "prospective-event", "--event", "espn:event:900000001", "--team",
                              "espn:team:9006", *base)
        self.assertEqual(doc["total"], 0)
        for grain in prospective.GRAINS:
            code, doc, _ = self.q("--grain", grain, "--event", "espn:event:123456789", *base)
            self.assertEqual((code, doc["total"], doc["rows"]), (0, 0, []))
            code, doc, _ = self.q("--grain", grain, "--season", "2025", *base)
            self.assertEqual((code, doc["season_scope_state"], doc["total"]), (0, "NOT_YET_AUDITED", 0))
            code, doc, _ = self.q("--grain", grain, "--season", "2026", *base, "--all")
            self.assertEqual(doc["season_scope_state"], prospective.IN_SCOPE_STATE)
        pages = [self.q("--grain", "prospective-team-record", "--limit", "4", "--offset", str(o), *base)[1]
                 for o in (0, 4)]
        self.assertEqual([p["returned"] for p in pages], [4, 2])
        self.assertEqual([p["next_offset"] for p in pages], [4, None])
        self.assertEqual(sum((p["rows"] for p in pages), []),
                         self.q("--grain", "prospective-team-record", "--all", *base)[1]["rows"])
        for argv, refusal in ((["--event", "900000001"], "EVENT_KEY_INVALID"),
                              (["--event", "espn:event:x1"], "EVENT_KEY_INVALID"),
                              (["--event", "espn:event:900000001\n"], "EVENT_KEY_INVALID"),
                              (["--team", "9001"], "TEAM_KEY_INVALID"), (["--team", "org:9001"], "TEAM_KEY_INVALID"),
                              (["--team", "espn:team:9001\n"], "TEAM_KEY_INVALID"),
                              (["--offset", "-1"], "NEGATIVE_OFFSET"), (["--limit", "-1"], "NEGATIVE_LIMIT")):
            self.assertEqual(self.q("--grain", "prospective-event", *base, *argv)[0::2], (2, refusal), argv)

    def test_mode_conflicts_and_inapplicable_selection(self) -> None:
        authority = self.world.authority
        capsule = str(self.capsule)
        cases = [(["--prospective-evidence", capsule, "--database", "x.sqlite", "--grain", "prospective-event",
                   "--cutoff", CUTOFF], "PROSPECTIVE_MODE_CONFLICT"),
                 (["--prospective-evidence", capsule, "--archive-evidence", "a.sqlite", "--grain", "prospective-event",
                   "--cutoff", CUTOFF], "PROSPECTIVE_MODE_CONFLICT"),
                 (["--prospective-evidence", capsule, "--grain", "contest", "--cutoff", CUTOFF],
                  "PROSPECTIVE_GRAIN_REQUIRED"),
                 (["--prospective-evidence", capsule, "--grain", "prospective-event", "--cutoff", CUTOFF, "--contest",
                   "ncaa:1"], "FILTER_NOT_APPLICABLE"),
                 (["--prospective-evidence", capsule, "--grain", "prospective-event", "--cutoff", CUTOFF,
                   "--require-pit"], "PIT_ADMISSION_AUTHORITY_ABSENT"),
                 (["--database", "x.sqlite", "--grain", "prospective-event", "--cutoff", CUTOFF],
                  "PROSPECTIVE_EVIDENCE_REQUIRED"),
                 (["--database", "x.sqlite", "--grain", "partition", "--event", "espn:event:1"],
                  "PROSPECTIVE_EVIDENCE_REQUIRED")]
        for argv, refusal in cases:
            code, out, got = self.run_cli(argv, authority)
            self.assertEqual((code, got, out), (2, refusal, None), argv)
        code, out, text = self.run_cli(["--grain", "prospective-event", "--cutoff", CUTOFF], authority)
        self.assertEqual(code, 2)
        self.assertIn("the following arguments are required: --database", text)

    def test_historical_invocations_never_import_the_prospective_reader(self) -> None:
        code = (f"import sys; sys.path[:0] = [{str(REPO_ROOT / 'src')!r}]; "
                "from aggie_analytics.national_source_time import query; "
                "rc = query.main(['--database', 'missing.sqlite', '--grain', 'partition']); "
                "print(rc, 'aggie_analytics.national_source_time.prospective' in sys.modules)")
        import subprocess  # noqa: PLC0415
        proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(proc.stdout.strip(), "2 False")


class ForgeryTests(_Workspace):
    """Coordinated forgeries (outer identities recomputed) must refuse for their own semantic rule."""

    def setUp(self) -> None:
        super().setUp()
        self.world = fx.World()
        _, self.capsule = self.build(self.world)
        self.counter = 0

    def refusal(self, path: Path) -> str:
        code, out, refused = self.run_cli(["--prospective-evidence", str(path), "--grain", "prospective-event",
                                           "--cutoff", CUTOFF], self.world.authority)
        self.assertEqual((code, out), (2, None), refused)
        return refused

    def forged(self, edit) -> Path:
        self.counter += 1
        return fx.forge(self.capsule, edit, self.tmp / f"f{self.counter}", identity_of=prospective.capsule_identity)

    def test_capsule_field_forgeries(self) -> None:
        def first_event(d):
            return d["events"][0]

        def first_participant(d):
            return d["participants"][0]
        cases = {
            "omitted_event": (lambda d: (d["events"].pop(), d["counts"].update(events=2)), "CAPSULE_EVENT_MEMBERSHIP_MISMATCH"),
            "extra_event": (lambda d: d["events"].append(copy.deepcopy(d["events"][0])), "CAPSULE_EVENT_MEMBERSHIP_MISMATCH"),
            "duplicate_participant": (lambda d: d["participants"].insert(1, copy.deepcopy(d["participants"][0])),
                                      "CAPSULE_PARTICIPANT_MEMBERSHIP_MISMATCH"),
            "omitted_participant": (lambda d: d["participants"].pop(), "CAPSULE_PARTICIPANT_MEMBERSHIP_MISMATCH"),
            "wrong_side": (lambda d: first_participant(d).update(side="away"), "CAPSULE_PARTICIPANT_MEMBERSHIP_MISMATCH"),
            "wrong_team": (lambda d: first_event(d)["home"].update(team_key="espn:team:9003"), "CAPSULE_EVENT_ROLES_MISMATCH"),
            "swapped_roles": (lambda d: first_event(d).update(home=first_event(d)["away"], away=first_event(d)["home"]),
                              "CAPSULE_EVENT_ROLES_MISMATCH"),
            "wrong_season": (lambda d: first_event(d).update(season_year=2025), "CAPSULE_EVENT_SEASON_MISMATCH"),
            "wrong_time": (lambda d: first_event(d).update(scheduled_utc="2026-10-17T17:00:00Z"),
                           "CAPSULE_EVENT_SCHEDULE_MISMATCH"),
            "wrong_status": (lambda d: first_event(d)["event_status"].update(name="STATUS_FINAL", completed=True),
                             "CAPSULE_EVENT_STATUS_MISMATCH"),
            "borrowed_home_record": (lambda d: first_participant(d)["overall_record"].update(summary="2-0", wins=2,
                                                                                            losses=0),
                                     "CAPSULE_PARTICIPANT_RECORD_MISMATCH"),
            "fabricated_zero_record": (lambda d: first_participant(d)["overall_record"].update(wins=0, losses=0),
                                       "CAPSULE_PARTICIPANT_RECORD_MISMATCH"),
            "support_promoted": (lambda d: first_event(d).update(unsupported_reasons=["ROLE_HOME_MISSING"]),
                                 "CAPSULE_EVENT_SUPPORT_MISMATCH"),
            "count_as_float": (lambda d: d["counts"].update(events=3.0), "CAPSULE_COUNTS_MISMATCH"),
            "count_as_bool": (lambda d: d["counts"].update(unsupported_events=False), "CAPSULE_COUNTS_MISMATCH"),
            "count_as_string": (lambda d: d["counts"].update(participants="6"), "CAPSULE_COUNTS_MISMATCH"),
            "wins_as_float": (lambda d: first_participant(d)["overall_record"].update(wins=float(
                first_participant(d)["overall_record"]["wins"])), "CAPSULE_PARTICIPANT_RECORD_MISMATCH"),
            "false_contract_identity": (lambda d: d["contract"].update(sha256="1" * 64), "CAPSULE_CONTRACT_MISMATCH"),
            "extra_member": (lambda d: d.update(note="restated declaration"), "CAPSULE_SCHEMA_MISMATCH"),
            "extra_record_member": (lambda d: first_event(d).update(official="NCAA"), "CAPSULE_EVENT_IDENTITY_MISMATCH"),
            "pit_admitted": (lambda d: d["labels"].update(pit_admission="ADMITTED"), "CAPSULE_LABELS_MISMATCH"),
            "observation_backdated": (lambda d: d["observation"].update(request_start_utc="2026-10-01T00:00:00.000000Z",
                                                                        request_end_utc="2026-10-01T00:00:01.000000Z"),
                                      "CAPSULE_OBSERVATION_MISMATCH"),
            "forged_url": (lambda d: d["source"].update(endpoint="https://example.invalid/scoreboard"),
                           "CAPSULE_SOURCE_MISMATCH"),
            "forged_body_hash": (lambda d: d["source"].update(body_sha256="2" * 64), "CAPSULE_SOURCE_MISMATCH"),
            "odds_provider_as_source": (lambda d: d["source"].update(provider="FixtureOdds"), "CAPSULE_SOURCE_MISMATCH"),
            "forged_bundle_pin": (lambda d: d["bundle"]["raw/provider-response.json"].update(sha256="3" * 64),
                                  "CAPSULE_BUNDLE_MISMATCH"),
        }
        for name, (edit, expected) in cases.items():
            self.assertEqual(self.refusal(self.forged(edit)), expected, name)

    def test_coordinated_input_forgeries(self) -> None:
        # altered raw (another team name) with every outer member recomputed against the unchanged contract
        altered = copy.deepcopy(self.world.raw_doc)
        altered["events"][0]["competitions"][0]["competitors"][0]["team"]["displayName"] = "Forged Name"
        other = fx.World(raw_doc=altered)
        doc = prospective.derive(*_inputs(other), contract_sha256=other.authority)
        doc["contract"]["sha256"] = self.world.authority
        doc["bundle"]["inputs/contract.json"] = {"sha256": self.world.authority, "bytes": len(self.world.contract)}
        target = self.tmp / "raw" / prospective.capsule_identity(doc)
        (target / "raw").mkdir(parents=True)
        (target / "inputs").mkdir()
        (target / "raw" / "provider-response.json").write_bytes(other.raw)
        (target / "raw" / "provider-receipt.json").write_bytes(other.receipt)
        (target / "inputs" / "EXPECTED_COHORT.json").write_bytes(other.expected)
        (target / "inputs" / "contract.json").write_bytes(self.world.contract)
        (target / "capsule.json").write_bytes(prospective.capsule_file_bytes(doc))
        self.assertEqual(self.refusal(target / "capsule.json"), "RAW_NOT_PINNED_ORIGINAL")
        # the same with the bundled contract re-pinned coherently: not the committed authority
        (target / "inputs" / "contract.json").write_bytes(other.contract)
        self.assertEqual(self.refusal(target / "capsule.json"), "CONTRACT_NOT_COMMITTED_AUTHORITY")
        # a forged receipt clock (receipt rehashed, everything else genuine)
        for member, edit, expected in (
                ("raw/provider-receipt.json", lambda b: b.replace(b"18:15:55.264959", b"18:15:50.000000"),
                 "RECEIPT_NOT_PINNED_ORIGINAL"),
                ("inputs/EXPECTED_COHORT.json", lambda b: b.replace(b"900000003", b"900000009"),
                 "COHORT_NOT_PINNED_ORIGINAL")):
            self.counter += 1
            copy_dir = self.tmp / f"m{self.counter}" / self.capsule.parent.name
            shutil.copytree(self.capsule.parent, copy_dir)
            path = copy_dir / Path(*member.split("/"))
            path.write_bytes(edit(path.read_bytes()))
            self.assertEqual(self.refusal(copy_dir / "capsule.json"), expected, member)

    def test_identity_location_and_file_forgeries(self) -> None:
        wrong = self.tmp / "wrong" / ("f" * 64)
        shutil.copytree(self.capsule.parent, wrong)
        self.assertEqual(self.refusal(wrong / "capsule.json"), "CAPSULE_IDENTITY_MISMATCH")
        plain = self.tmp / "plain" / "not-an-identity"
        shutil.copytree(self.capsule.parent, plain)
        self.assertEqual(self.refusal(plain / "capsule.json"), "EVIDENCE_LOCATION_INVALID")
        missing = self.tmp / "missing" / self.capsule.parent.name
        shutil.copytree(self.capsule.parent, missing)
        (missing / "raw" / "provider-receipt.json").unlink()
        self.assertEqual(self.refusal(missing / "capsule.json"), "BUNDLE_MEMBER_MISSING")
        self.assertEqual(self.refusal(self.tmp / "nowhere" / ("a" * 64) / "capsule.json"), "EVIDENCE_MISSING")
        self.assertFalse((self.tmp / "nowhere").exists())
        pretty = self.tmp / "pretty" / self.capsule.parent.name
        shutil.copytree(self.capsule.parent, pretty)
        doc = json.loads((pretty / "capsule.json").read_text(encoding="utf-8"))
        (pretty / "capsule.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.refusal(pretty / "capsule.json"), "CAPSULE_CANONICAL_FORM_MISMATCH")
        dup = self.tmp / "dup" / self.capsule.parent.name
        shutil.copytree(self.capsule.parent, dup)
        text = (dup / "capsule.json").read_bytes()
        (dup / "capsule.json").write_bytes(b'{"schema":"x",' + text[1:])
        self.assertEqual(self.refusal(dup / "capsule.json"), "CAPSULE_MALFORMED")

    @unittest.skipUnless(os.name == "nt", "Windows location rules")
    def test_network_device_and_non_literal_locations_refuse_before_access(self) -> None:
        for path, refusal in ((r"\\fixture-server\share" + "\\" + "a" * 64 + r"\capsule.json",
                               "EVIDENCE_LOCATION_UNSUPPORTED"),
                              (r"\\.\PhysicalDrive0", "EVIDENCE_LOCATION_UNSUPPORTED"),
                              (r"\\?\GLOBALROOT\Device\x\capsule.json", "EVIDENCE_LOCATION_UNSUPPORTED"),
                              ("\\\\?\\" + str(self.capsule.parent) + r"\..\x" + "\\" + "a" * 64 + r"\capsule.json",
                               "EVIDENCE_LOCATION_NOT_LITERAL")):
            self.assertEqual(self.refusal(Path(path) if not path.startswith("\\\\") else path), refusal, path)


class PortableBundleTests(_Workspace):
    def test_rehoused_and_long_path_bundles_serve_identically(self) -> None:
        world = fx.World()
        _, capsule = self.build(world)
        argv = ["--grain", "prospective-team-record", "--cutoff", CUTOFF, "--all"]
        _, original, _ = self.run_cli(["--prospective-evidence", str(capsule), *argv], world.authority)
        moved = fx.rehouse(capsule, self.tmp / "elsewhere")
        _, rehoused, _ = self.run_cli(["--prospective-evidence", str(moved), *argv], world.authority)
        self.assertEqual(rehoused["rows"], original["rows"])
        self.assertEqual(rehoused["capsule_identity"], original["capsule_identity"])
        relative = os.path.relpath(moved, Path.cwd()) if moved.drive == Path.cwd().drive else str(moved)
        _, relative_doc, _ = self.run_cli(["--prospective-evidence", relative, *argv], world.authority)
        self.assertEqual(relative_doc["rows"], original["rows"])
        if os.name == "nt":
            far = os.path.join(os.path.abspath(self.tmp), "long " + "x" * 110, "deeper " + "y" * 110, "tail " + "z" * 30,
                               capsule.parent.name)
            target = "\\\\?\\" + far
            self.assertGreater(len(target), 300)
            for name, data in builder.directory_members(capsule.parent).items():
                path = os.path.join(target, *name.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "xb") as handle:
                    handle.write(data)
            _, long_doc, _ = self.run_cli(["--prospective-evidence", os.path.join(target, "capsule.json"), *argv],
                                          world.authority)
            self.assertEqual(long_doc["rows"], original["rows"])


class MountedGenuineCapsuleTests(unittest.TestCase):
    """The genuine canonical capsule through the committed authority (mounted lanes; the gate names its identity)."""

    def test_genuine_capsule_serves_the_frozen_cohort(self) -> None:
        root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        gate = REPO_ROOT / "artifacts" / "data_lake" / "prospective_provider_observation_20261011_gate.json"
        if not root or not gate.is_file():
            self.skipTest("mounted data root and committed gate required")
        binding = json.loads(gate.read_text(encoding="utf-8"))
        capsule = Path(root) / "canonical" / prospective.POPULATION / "sha256" / binding["capsule_identity"] / \
            prospective.CAPSULE_FILE
        if not capsule.is_file():
            self.skipTest(f"canonical capsule not mounted at {capsule}")
        verified = prospective.verify_capsule(capsule, expect_identity=binding["capsule_identity"])
        doc = verified["document"]
        contract = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual([r["event_key"] for r in doc["events"]], contract["membership"]["event_keys"])
        self.assertEqual(sorted([p["event_key"], p["side"], p["team_key"]] for p in doc["participants"]),
                         sorted([p["event_key"], p["side"], p["team_key"]]
                                for p in contract["membership"]["participants"]))
        self.assertEqual((doc["counts"]["events"], doc["counts"]["participants"]), (25, 50))
        self.assertEqual(verified["identity_document"], binding["identity_document"])


if __name__ == "__main__":
    unittest.main()
