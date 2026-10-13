"""BAT-726: the explicit immutable official schedule evidence sidecar of the frozen October 17 shadow (TP54-A01).

Synthetic worlds only (official_shadow_schedule_fixture): the committed contract and the packaged profile stay the only
defaults; fixture authorities are passed explicitly. A mounted test serves the real canonical sidecar when the packaged
gate pins one and a data root is mounted.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import gzip
import hashlib
import io
import json
import ntpath
import os
import posixpath
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / "src"), str(ROOT), str(ROOT / "tests")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import official_shadow_schedule_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import query  # noqa: E402
from aggie_analytics.retrospective_baseline import schedule as sc  # noqa: E402

CUT = "2026-10-13T00:00:00Z"
GATE = ROOT / "artifacts" / "data_lake" / "official_shadow_schedule_20261017_gate.json"
#: The original network-share and device spellings of QueryTests.test_locations. They name a namespace only under the
#: Windows path rules; under the POSIX rules a backslash is an ordinary file-name character (MF54A01-01: PR710's
#: Ubuntu jobs failed while the Windows refusal was expected on every platform).
NAMESPACE_SPELLINGS = (r"\\fixture-server\share" + "\\" + "a" * 64 + r"\schedule.json", r"\\.\PhysicalDrive0")


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="s54"))


def _cleanup(path: Path) -> None:
    shutil.rmtree(fx.sfx.ext(path), ignore_errors=False)


def native_location_case(spelling: str, directory: str, os_name: str = os.name) -> tuple[str, str]:
    """The location the query is given for an original namespace spelling and the refusal its native path rules owe.

    Windows: the spelling itself, a network share or device that the lexical location rule refuses before any access.
    POSIX: the same characters as one ordinary file name inside the test's own temporary ``directory`` (never the
    shared working directory); no such file exists, so the query reports it missing."""
    if os_name == "nt":
        return spelling, "SCHEDULE_LOCATION_UNSUPPORTED"
    return posixpath.join(directory, spelling), "SCHEDULE_MISSING"


class ContractTests(unittest.TestCase):
    def test_committed_contract_is_the_pinned_authority(self) -> None:
        data = (ROOT / "configs" / "official_shadow_schedule_20261017_contract.json").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), sc.CONTRACT_SHA256)
        spec = sc._spec(data, sc.CONTRACT_SHA256)
        self.assertEqual(spec["expected"]["expected_events"], 25)
        self.assertEqual(len(spec["expected"]["events"]), 25)
        self.assertEqual(spec["expected"]["expected_participants"], 50)
        self.assertEqual(spec["shadow"], sc.PRODUCTION_SHADOW)
        self.assertIsNone(spec["capture_contract_sha256"])
        hosts = {e["owner"]["directory_host"].removeprefix("www.") for e in spec["expected"]["events"]}
        self.assertEqual(len(hosts), 25)

    def test_contract_rules_must_equal_the_frozen_code(self) -> None:
        data = (ROOT / "configs" / "official_shadow_schedule_20261017_contract.json").read_bytes()
        doc = json.loads(data.decode("utf-8"))
        for member in ("structures", "time_rules", "labels", "acquisition"):
            changed = fx.deep(doc)
            changed[member] = {"changed": True}
            raw = (json.dumps(changed, indent=1) + "\n").encode("utf-8")
            with self.assertRaises(sc.ScheduleError) as ctx:
                sc._spec(raw, hashlib.sha256(raw).hexdigest())
            self.assertEqual(ctx.exception.code, "CONTRACT_CODE_DISAGREEMENT")
        with self.assertRaises(sc.ScheduleError) as ctx:
            sc._spec(data + b" ", sc.CONTRACT_SHA256)
        self.assertEqual(ctx.exception.code, "CONTRACT_NOT_COMMITTED_AUTHORITY")

    def test_packaged_gate_matches_the_reader_profile(self) -> None:
        if not GATE.is_file():
            self.assertIsNone(sc.SCHEDULE_PROFILE)
            return
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["profile"], sc.SCHEDULE_PROFILE)
        self.assertEqual(gate["contract_sha256"], sc.CONTRACT_SHA256)
        self.assertEqual((gate["contract_id"], gate["population_id"]), (sc.CONTRACT_ID, sc.POPULATION))
        self.assertEqual(gate["schedule_identity"], gate["profile"]["schedule_identity"])
        self.assertEqual(gate["shadow_identity"], sc.PRODUCTION_SHADOW["identity"])
        self.assertEqual(gate["identity_document"]["schema"], sc.IDENTITY_SCHEMA)
        self.assertEqual(gate["identity_document"]["schedule_sha256"], gate["profile"]["schedule_sha256"])
        self.assertEqual(gate["labels"], sc.LABELS)
        self.assertEqual((gate["counts"]["events"], gate["counts"]["participants"]), (25, 50))
        self.assertEqual(sum(gate["summary"]["dispositions"].values()), 25)
        self.assertEqual(gate["acquisition"]["attempts"], gate["profile"]["attempts"])
        self.assertLessEqual(gate["profile"]["attempts"], gate["acquisition"]["ceiling"])
        self.assertEqual(gate["acquisition"]["availability_bound_utc"], gate["profile"]["availability_bound_utc"])


class TimeAndNameTests(unittest.TestCase):
    def test_time_texts(self) -> None:
        self.assertEqual(sc.parse_time_text("3:30 p.m."), {"kind": "NAIVE", "local_time": "15:30"})
        self.assertEqual(sc.parse_time_text("12:00 PM"), {"kind": "NAIVE", "local_time": "12:00"})
        self.assertEqual(sc.parse_time_text("12:15 a.m."), {"kind": "NAIVE", "local_time": "00:15"})
        self.assertEqual(sc.parse_time_text("TBA")["kind"], "TBA")
        self.assertEqual(sc.parse_time_text("T.B.D.")["kind"], "TBA")
        self.assertEqual(sc.parse_time_text("7:30 p.m. ET")["designator"], "ET")
        self.assertEqual(sc.parse_time_text("13:30 p.m.")["kind"], "UNRECOGNIZED")
        self.assertEqual(sc.parse_time_text("3:30 p.m.\n")["kind"], "NAIVE")
        self.assertEqual(sc.parse_time_text("after the band")["kind"], "UNRECOGNIZED")

    def test_zone_rules_never_infer_and_respect_daylight(self) -> None:
        october = dt.datetime(2026, 10, 17, 19, 30)
        self.assertEqual(sc.zone_offset("ET", october), ("-04:00", None))
        self.assertEqual(sc.zone_offset("CT", october), ("-05:00", None))
        self.assertEqual(sc.zone_offset("PT", october), ("-07:00", None))
        self.assertEqual(sc.zone_offset("EDT", october), ("-04:00", None))
        self.assertEqual(sc.zone_offset("EST", october)[1], "ZONE_DESIGNATOR_DISAGREES_WITH_DAYLIGHT_RULE")
        self.assertEqual(sc.zone_offset("MT", october)[1], "GENERIC_MT_AMBIGUOUS_ARIZONA")
        self.assertEqual(sc.zone_offset("MST", october), ("-07:00", None))
        self.assertEqual(sc.zone_offset("ET", dt.datetime(2026, 12, 5, 12, 0)), ("-05:00", None))
        self.assertEqual(sc.zone_offset("ET", dt.datetime(2026, 3, 8, 2, 30))[1], "LOCAL_TIME_IN_DAYLIGHT_TRANSITION_GAP")
        self.assertEqual(sc.zone_offset("CT", dt.datetime(2026, 11, 1, 1, 30))[1],
                         "LOCAL_TIME_IN_DAYLIGHT_TRANSITION_FOLD")
        self.assertEqual(sc.zone_offset("HST", october)[1], "ZONE_DESIGNATOR_UNRECOGNIZED")
        stated = sc.time_statement("2026-10-17", sc.parse_time_text("3:30 p.m. ET"))
        self.assertEqual(stated["utc"], "2026-10-17T19:30:00.000000Z")
        self.assertEqual(sc.time_statement(None, sc.parse_time_text("3:30 p.m. ET"))["kind"], "AMBIGUOUS")

    def test_resolution_states(self) -> None:
        naive = {"kind": "NAIVE", "local_time": "15:30"}
        instant = {"kind": "INSTANT", "basis": "EXPLICIT_OFFSET", "local_time": "15:30", "utc": "X"}
        other = {"kind": "INSTANT", "basis": "STATED_ZONE", "local_time": "15:30", "utc": "Y"}
        self.assertEqual(sc.resolve_time([{"time": [naive, naive]}])["state"], "NAIVE_LOCAL_TIME_ONLY")
        self.assertEqual(sc.resolve_time([{"time": [naive, instant]}])["state"], "SUPPORTED_INSTANT")
        self.assertEqual(sc.resolve_time([{"time": [instant]}, {"time": [other]}])["state"], "CONFLICTING")
        self.assertEqual(sc.resolve_time([{"time": [naive]}, {"time": [{"kind": "NAIVE", "local_time": "12:00"}]}]
                                         )["state"], "CONFLICTING")
        self.assertEqual(sc.resolve_time([{"time": [{"kind": "TBA"}]}, {"time": [naive]}])["state"], "CONFLICTING")
        self.assertEqual(sc.resolve_time([{"time": [{"kind": "TBA"}]}])["state"], "TBA")
        self.assertEqual(sc.resolve_time([{"time": [{"kind": "AMBIGUOUS", "local_time": "15:30", "designator": "MT",
                                                     "reason": "GENERIC_MT_AMBIGUOUS_ARIZONA"}]}])["state"],
                         "AMBIGUOUS_TIMEZONE")
        self.assertEqual(sc.resolve_time([])["state"], "UNSUPPORTED")

    def test_names_strip_only_a_leading_rank(self) -> None:
        self.assertEqual(sc.name_key(" (#8)  Texas A&amp;M "), "texas a&m")
        self.assertEqual(sc.name_key("#23/21 Auburn"), "auburn")
        self.assertEqual(sc.name_key("No. 5 Ohio State"), "ohio state")
        self.assertEqual(sc.name_key("Ohio"), "ohio")
        self.assertNotEqual(sc.name_key("Ohio State"), sc.name_key("Ohio"))

    def test_provider_date_set_covers_us_offsets_only(self) -> None:
        self.assertEqual(sc.provider_date_set("2026-10-17T16:00:00Z"), ["2026-10-17"])
        self.assertEqual(sc.provider_date_set("2026-10-18T02:00:00Z"), ["2026-10-17"])
        self.assertEqual(sc.provider_date_set("2026-10-18T08:00:00Z"), ["2026-10-17", "2026-10-18"])


class StructureTests(unittest.TestCase):
    def test_sidearm_nuxt_and_text_table(self) -> None:
        page = fx.sidearm_page("Alpha State", [fx.nuxt_game("2026-10-17T11:00:00", "11:00 a.m.", "H", "Beta Tech")],
                               table=[("Oct 17 (Sat)", "11:00 a.m.", "Home", "Beta Tech", "Alpha, St. (1 Field)",
                                       "W 99-0")])
        doc = sc.extract_document(page)
        kinds = [s["structure"] for s in doc["structures"]]
        self.assertEqual(kinds, ["SIDEARM_NUXT_SCHEDULE", "SIDEARM_TEXT_TABLE"])
        self.assertTrue(all(s["season_bound"] for s in doc["structures"]))
        table = doc["structures"][1]["records"][0]["members"]
        self.assertNotIn("Result", table)
        self.assertNotIn("Tournament", table)
        values = sc.record_values("SIDEARM_TEXT_TABLE", table)
        self.assertEqual((values["event_date"], values["location"], values["facility"], values["designation"]),
                         ("2026-10-17", "Alpha, St.", "1 Field", "HOME"))

    def test_other_season_and_other_sport_do_not_bind(self) -> None:
        page = fx.sidearm_page("Alpha State", [fx.nuxt_game("2025-10-18T11:00:00", "11:00 a.m.", "H", "Beta Tech")],
                               season="2025", table=[("Oct 18 (Sat)", "11:00 a.m.", "Home", "Beta Tech", "X", "")])
        doc = sc.extract_document(page)
        self.assertFalse(any(s["season_bound"] for s in doc["structures"]))
        basketball = fx.nuxt_script("Alpha State", [], sport="mbball")
        self.assertEqual(sc.extract_document(basketball.encode("utf-8"))["structures"], [])

    def test_header_or_chrome_never_binds_a_season(self) -> None:
        chrome = '<h1>2026 Football Schedule</h1><div class="countdown">Oct 17 vs Beta Tech 11:00 a.m.</div>'
        page = ("<html><head><title>2026 Football Schedule</title></head><body>" + chrome +
                "</body></html>").encode("utf-8")
        self.assertEqual(sc.extract_document(page)["structures"], [])

    def test_table_weekday_must_match(self) -> None:
        self.assertEqual(sc._table_date("Oct 17 (Sat)"), ("2026-10-17", None))
        self.assertEqual(sc._table_date("Oct 17 (Fri)"), (None, "DATE_WEEKDAY_MISMATCH"))
        self.assertEqual(sc._table_date("Jan 1 (Fri)"), ("2027-01-01", None))
        self.assertEqual(sc._table_date("Week 7"), (None, "DATE_TEXT_UNRECOGNIZED"))

    def test_wmt_list_items_only(self) -> None:
        item = fx.wmt_item("Gamma A&M", "Delta College", "2026-10-17T12:00:00.000-05:00", rank="(#8)")
        page = fx.wmt_page([item], table_view=fx.wmt_item("Gamma A&M", "Other U", "2026-10-17T18:00:00.000-05:00"))
        structures = sc.extract_document(page)["structures"]
        self.assertEqual([s["structure"] for s in structures], ["WMT_SCHEDULE_LIST"])
        self.assertEqual(len(structures[0]["records"]), 1)
        values = sc.record_values("WMT_SCHEDULE_LIST", structures[0]["records"][0]["members"])
        self.assertEqual(values["time"][0]["utc"], "2026-10-17T17:00:00.000000Z")
        tba = fx.wmt_item("Gamma A&M", "Delta College", "2026-10-17T14:30:00.000-05:00", tba=True)
        values = sc.record_values("WMT_SCHEDULE_LIST", sc.extract_document(fx.wmt_page([tba]))["structures"][0][
            "records"][0]["members"])
        self.assertEqual(values["time"], [{"member": "time_tba", "raw": True, "kind": "TBA"}])


class WorldTestCase(unittest.TestCase):
    world: fx.ScheduleWorld
    genuine: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = _tmp()
        cls.world = fx.ScheduleWorld(cls.tmp / "w")
        cls.genuine = cls.world.build(cls.tmp / "g")
        cls.path = cls.genuine["path"]
        cls.profile = cls.genuine["profile"]

    @classmethod
    def tearDownClass(cls) -> None:
        _cleanup(cls.tmp)

    def q(self, *args: str, path: Path | None = None, profile: object = "pinned") -> tuple[int, dict | None, str]:
        return self.world.query(path or self.path, *args, profile=self.profile if profile == "pinned" else profile)


class QualificationTests(WorldTestCase):
    def event(self, key: str) -> dict:
        code, doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, "--event", key)
        self.assertEqual(code, 0, err)
        return doc["rows"][0]["schedule"]

    def build_with(self, pages: dict[str, bytes]) -> dict:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        built = self.world.build(tmp, self.world.genuine_capture(pages))
        code, doc, err = self.world.query(built["path"], "--grain", "shadow-schedule", "--cutoff", CUT, "--all",
                                          profile=built["profile"])
        self.assertEqual(code, 0, err)
        return {r["schedule"]["event_key"]: r["schedule"] for r in doc["rows"]}

    def test_genuine_fields(self) -> None:
        one = self.event("espn:event:900000001")
        self.assertEqual(one["disposition"], "RECORD_BOUND")
        self.assertEqual(one["fields"]["scheduled_time"]["state"], "NAIVE_LOCAL_TIME_ONLY")
        self.assertEqual(len(one["fields"]["designation"]["witnesses"]), 2)  # Nuxt record and text row agree
        two = self.event("espn:event:900000002")
        self.assertEqual(two["fields"]["scheduled_time"]["value"]["utc"], "2026-10-17T17:00:00.000000Z")
        self.assertEqual(two["fields"]["scheduled_time"]["comparison"], "AGREES")
        three = self.event("espn:event:900000003")
        self.assertEqual(three["fields"]["scheduled_time"]["value"]["bases"], ["STATED_ZONE"])
        for record in (one, two, three):
            self.assertEqual(record["labels"]["schedule_authority"], "SCHEDULE_NOT_ACTUAL_KICKOFF")
            self.assertEqual(record["provider_claims"]["source"], "FROZEN_PROVIDER_CLAIM_FROM_THE_ACCEPTED_SHADOW")

    def test_role_reversal_date_conflict_other_opponent_and_contradictions(self) -> None:
        pages = self.world.genuine_pages()
        pages["espn:event:900000001"] = fx.sidearm_page("Alpha State", [
            fx.nuxt_game("2026-10-17T11:00:00", "11:00 a.m.", "A", "Beta Tech")],
            table=[("Oct 17 (Sat)", "2:00 p.m.", "Home", "Beta Tech", "Alpha, St. (1 Field)", "")])
        pages["espn:event:900000002"] = fx.wmt_page([fx.wmt_item("Gamma A&M", "Delta College",
                                                                 "2026-10-24T12:00:00.000-05:00")])
        pages["espn:event:900000003"] = fx.sidearm_page("Epsilon City", [
            fx.nuxt_game("2026-10-17T15:30:00", "3:30 p.m. ET", "H", "Somebody Else")])
        got = self.build_with(pages)
        one = got["espn:event:900000001"]
        self.assertEqual(one["fields"]["designation"]["state"], "CONFLICTING")
        self.assertEqual(one["fields"]["designation"]["value"], ["AWAY", "HOME"])
        self.assertEqual(one["fields"]["scheduled_time"]["state"], "CONFLICTING")
        two = got["espn:event:900000002"]
        self.assertEqual(two["disposition"], "OPPONENT_RECORD_ON_OTHER_DATE")
        self.assertEqual(two["fields"]["event_date"]["state"], "CONFLICTING")
        self.assertEqual(two["fields"]["designation"]["state"], "UNSUPPORTED")  # never borrowed from that row
        three = got["espn:event:900000003"]
        self.assertEqual(three["disposition"], "UNBOUND_OPPONENT_ON_EVENT_DATE")
        self.assertEqual(three["fields"]["opponent"]["state"], "UNSUPPORTED")
        self.assertEqual(three["fields"]["opponent"]["unbound_names"], ["Somebody Else"])
        self.assertEqual(three["fields"]["scheduled_time"]["state"], "UNSUPPORTED")

    def test_reversed_home_role_disagrees(self) -> None:
        pages = self.world.genuine_pages()
        pages["espn:event:900000003"] = fx.sidearm_page("Epsilon City", [
            fx.nuxt_game("2026-10-17T15:30:00", "3:30 p.m. ET", "A", "Zeta Southern")])
        three = self.build_with(pages)["espn:event:900000003"]
        self.assertEqual((three["fields"]["designation"]["value"], three["fields"]["designation"]["comparison"]),
                         ("AWAY", "DISAGREES"))

    def test_abbreviation_mascot_and_owner_mismatch_never_bind(self) -> None:
        pages = self.world.genuine_pages()
        pages["espn:event:900000001"] = fx.sidearm_page("Alpha State", [
            fx.nuxt_game("2026-10-17T11:00:00", "11:00 a.m.", "H", "BET")])
        pages["espn:event:900000002"] = fx.wmt_page([fx.wmt_item("Gamma A&M", "Hawks",
                                                                 "2026-10-17T12:00:00.000-05:00")])
        pages["espn:event:900000003"] = fx.sidearm_page("Epsilon State", [
            fx.nuxt_game("2026-10-17T15:30:00", "3:30 p.m. ET", "H", "Zeta Southern")])
        got = self.build_with(pages)
        self.assertEqual(got["espn:event:900000001"]["disposition"], "UNBOUND_OPPONENT_ON_EVENT_DATE")
        self.assertEqual(got["espn:event:900000002"]["disposition"], "UNBOUND_OPPONENT_ON_EVENT_DATE")
        self.assertEqual(got["espn:event:900000002"]["fields"]["designation"]["state"], "UNSUPPORTED")
        self.assertEqual(got["espn:event:900000003"]["disposition"], "OWNER_NOT_VERIFIED")

    def test_repeated_equal_witnesses_and_unsupported_structure(self) -> None:
        pages = self.world.genuine_pages()
        item = fx.wmt_item("Gamma A&M", "Delta College", "2026-10-17T12:00:00.000-05:00",
                           location="Gamma City / 2 Field")
        pages["espn:event:900000002"] = fx.wmt_page([item, item])
        pages["espn:event:900000003"] = b"<html><body><ul><li class='sidearm-schedule-game'>Zeta</li></ul></body></html>"
        got = self.build_with(pages)
        two = got["espn:event:900000002"]
        self.assertEqual(two["fields"]["scheduled_time"]["state"], "SUPPORTED_INSTANT")
        self.assertEqual(len(two["fields"]["opponent"]["witnesses"]), 2)
        self.assertEqual(got["espn:event:900000003"]["disposition"], "NO_DECLARED_STRUCTURE")


class JournalTests(WorldTestCase):
    def refuse(self, capture: fx.Capture, code: str, *, end: bool = True) -> None:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415
        acq = capture.write(tmp / "acq", end=end)
        with self.assertRaises(builder.BuildRefused) as ctx:
            builder.build_sidecar(self.world.build_args(acq, tmp), contract_authority=self.world.authority,
                                  shadow_profile=self.world.shadow_profile)
        self.assertEqual(ctx.exception.code, code)

    def base(self) -> tuple[fx.Capture, list[str], dict[str, bytes]]:
        return self.world.capture(), sorted(self.world.events), self.world.genuine_pages()

    def test_spacing_host_stop_and_route_rules(self) -> None:
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 200, pages[keys[0]])
        cap.attempt(keys[1], "900000002-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[1]), 200, pages[keys[1]],
                    spacing=1_999_999_999)
        self.refuse(cap, "SCHEDULE_SPACING_VIOLATED")
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, "https://alpha.example.evil/sports/football/"
                    "schedule/2026", 200, b"x")
        self.refuse(cap, "SCHEDULE_UNAUTHORIZED_HOST")
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 429, b"slow down")
        cap.attempt(keys[0], "900000001-3", "LANDING_ROUTE", 1, "https://www.alpha.example/sports/football/schedule",
                    200, pages[keys[0]])
        self.refuse(cap, "SCHEDULE_STOPPED_HOST_REQUESTED")
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, "https://alpha.example/sports/football/"
                    "schedule", 200, pages[keys[0]])
        for key in keys[1:]:
            cap.attempt(key, f"{key[-9:]}-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(key), 200, pages[key])
        self.refuse(cap, "SCHEDULE_ROUTE_POLICY_VIOLATED")

    def test_fallback_after_a_qualified_document_is_refused(self) -> None:
        cap = self.world.genuine_capture()
        key = "espn:event:900000002"
        cap.attempt(key, "900000002-3", "LANDING_ROUTE", 1, "https://gamma.example/sports/football/schedule", 200,
                    self.world.genuine_pages()[key])
        self.refuse(cap, "SCHEDULE_ROUTE_POLICY_VIOLATED")

    def test_ceiling_sequence_and_unreferenced_body(self) -> None:
        cap, keys, pages = self.base()
        for n in range(81):
            cap.attempt(keys[0], f"x-{n}", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 404, b"no")
        self.refuse(cap, "SCHEDULE_CEILING_EXCEEDED")
        cap = self.world.genuine_capture()
        cap.lines[3]["seq"] = 7
        self.refuse(cap, "SCHEDULE_JOURNAL_SEQUENCE_INVALID")
        cap = self.world.genuine_capture()
        cap.bodies[hashlib.sha256(b"stray").hexdigest()] = b"stray"
        self.refuse(cap, "SCHEDULE_RAW_BODY_UNREFERENCED")

    def test_redirect_rules_and_decisions(self) -> None:
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 301, b"",
                    headers=[["Location", "https://elsewhere.example/2026"]])
        cap.decision(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", "https://elsewhere.example/2026",
                     "REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED")
        for key in keys[1:]:
            cap.decision(key, f"{key[-9:]}-1", "INITIAL_SEASON_ROUTE", self.world.initial(key),
                         "NOT_REQUESTED_BUDGET_EXHAUSTED")
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        built = self.world.build(tmp, cap)
        code, doc, err = self.world.query(built["path"], "--grain", "shadow-schedule-source", "--cutoff", CUT,
                                          "--all", profile=built["profile"])
        self.assertEqual(code, 0, err)
        outcomes = {r["source"]["logical"]: (r["source"]["outcome"], r["source"]["attempts"]) for r in doc["rows"]}
        self.assertEqual(outcomes["900000001-1"], ("REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED", 1))
        self.assertEqual(outcomes["900000002-1"], ("NOT_REQUESTED_BUDGET_EXHAUSTED", 0))
        code, doc, err = self.world.query(built["path"], "--grain", "shadow-schedule", "--cutoff", CUT, "--all",
                                          profile=built["profile"])
        self.assertEqual({r["schedule"]["disposition"] for r in doc["rows"]}, {"SOURCE_NOT_RETRIEVED"})
        self.assertEqual(doc["total"], 3)
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 301, b"",
                    headers=[["Location", self.world.initial(keys[0], "www.alpha.example")]])
        cap.decision(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", "x", "REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED")
        self.refuse(cap, "SCHEDULE_JOURNAL_DECISION_INVALID")

    def test_budget_stop_inside_a_redirect_chain(self) -> None:
        cap, keys, pages = self.base()
        target = self.world.initial(keys[0], "www.alpha.example")
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 301, b"",
                    headers=[["Location", target]])
        cap.decision(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", target, "NOT_REQUESTED_BUDGET_EXHAUSTED")
        for key in keys[1:]:
            cap.decision(key, f"{key[-9:]}-1", "INITIAL_SEASON_ROUTE", self.world.initial(key),
                         "NOT_REQUESTED_BUDGET_EXHAUSTED")
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        built = self.world.build(tmp, cap)
        code, doc, err = self.world.query(built["path"], "--grain", "shadow-schedule-source", "--cutoff", CUT,
                                          "--event", keys[0], profile=built["profile"])
        self.assertEqual((doc["rows"][0]["source"]["outcome"], doc["rows"][0]["source"]["attempts"]),
                         ("NOT_REQUESTED_BUDGET_EXHAUSTED", 1))
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 200, pages[keys[0]])
        cap.decision(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", "x", "NOT_REQUESTED_BUDGET_EXHAUSTED")
        self.refuse(cap, "SCHEDULE_JOURNAL_DECISION_INVALID")

    def test_interrupted_attempt_counts_and_failures_stay_distinct(self) -> None:
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), None, b"",
                    error="URLError: timed out")
        cap.attempt(keys[1], "900000002-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[1]), 200,
                    b"x" * 10, truncated=True)
        cap.attempt(keys[2], "900000003-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[2]), 200, b"",
                    result=False)
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        built = self.world.build(tmp, cap)
        code, doc, err = self.world.query(built["path"], "--grain", "shadow-schedule-source", "--cutoff", CUT,
                                          "--all", profile=built["profile"])
        outcomes = [r["source"]["outcome"] for r in doc["rows"]]
        self.assertEqual(outcomes, ["FAILED_NO_RESPONSE", "TRUNCATED_BODY", "INTERRUPTED"])
        cap, keys, pages = self.base()
        cap.attempt(keys[0], "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(keys[0]), 302, b"moved",
                    headers=[["Content-Type", "text/html"]])
        for key in keys[1:]:
            cap.attempt(key, f"{key[-9:]}-1", "INITIAL_SEASON_ROUTE", 1, self.world.initial(key), 200, pages[key])
        tmp2 = _tmp()
        self.addCleanup(_cleanup, tmp2)
        built = self.world.build(tmp2, cap)
        code, doc, err = self.world.query(built["path"], "--grain", "shadow-schedule-source", "--cutoff", CUT,
                                          "--event", keys[0], profile=built["profile"])
        self.assertEqual(doc["rows"][0]["source"]["outcome"], "FAILED_HTTP")
        self.assertEqual(doc["acquisition"]["attempts"], 3)


class SidecarTests(WorldTestCase):
    def test_identity_rebuild_variants_interrupt_and_rehouse(self) -> None:
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        acq = self.world.genuine_capture().write(tmp / "acq")
        args = self.world.build_args(acq, self.tmp / "g")
        again = builder.build_sidecar(args, contract_authority=self.world.authority,
                                      shadow_profile=self.world.shadow_profile)
        self.assertEqual((again["identity"], again["state"]), (self.genuine["identity"], "ALREADY_PRESENT_IDENTICAL"))
        for name, extra in (("r", {"processing_order": "reversed", "chunk_size": "1"}),
                            ("s", {"processing_order": "shuffled:54", "chunk_size": "17"})):
            out = builder.build_sidecar(self.world.build_args(acq, tmp / name, **extra),
                                        contract_authority=self.world.authority,
                                        shadow_profile=self.world.shadow_profile)
            self.assertEqual(out["identity"], self.genuine["identity"])
            self.assertEqual(out["members"], self.genuine["members"])
        with self.assertRaises(builder.BuildInterrupted):
            builder.build_sidecar(self.world.build_args(acq, tmp / "i", stop_after_members=2),
                                  contract_authority=self.world.authority, shadow_profile=self.world.shadow_profile)
        self.assertFalse((tmp / "i" / "c" / "sha256" / self.genuine["identity"]).exists())
        resumed = builder.build_sidecar(self.world.build_args(acq, tmp / "i"), contract_authority=self.world.authority,
                                        shadow_profile=self.world.shadow_profile)
        self.assertEqual(resumed["members"], self.genuine["members"])
        moved = fx.rehouse(self.path, tmp / "rehoused")
        a = self.q("--grain", "shadow-schedule", "--cutoff", CUT, "--all")
        b = self.q("--grain", "shadow-schedule", "--cutoff", CUT, "--all", path=moved)
        self.assertEqual(a, b)

    def test_second_different_sidecar_refused_without_successor(self) -> None:
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415
        pages = self.world.genuine_pages()
        pages["espn:event:900000001"] = pages["espn:event:900000001"].replace(b"11:00 a.m.", b"12:00 p.m.")
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        acq = self.world.genuine_capture(pages).write(tmp / "acq")
        with self.assertRaises(builder.BuildRefused) as ctx:
            builder.build_sidecar(self.world.build_args(acq, self.tmp / "g"), contract_authority=self.world.authority,
                                  shadow_profile=self.world.shadow_profile)
        self.assertEqual(ctx.exception.code, "SIDECAR_ALREADY_FROZEN")

    def test_profile_pin_is_required(self) -> None:
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, profile=None)
        self.assertEqual((code, fx.refusal(err)), (2, "SCHEDULE_PROFILE_NOT_PINNED"))
        wrong = dict(self.profile, attempts=self.profile["attempts"] + 1)
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, profile=wrong)
        self.assertEqual((code, fx.refusal(err)), (2, "SCHEDULE_NOT_PINNED_SIDECAR"))


class NativeLocationRuleTests(unittest.TestCase):
    def test_namespace_refusal_is_owed_only_under_windows_path_rules(self) -> None:
        """MF54A01-01 regression, run on every host: the refusal expected for an original namespace spelling follows the
        path rules of the platform, never Windows alone. Lexical only; test_locations runs the real query under the
        host's own rules."""
        owned = "/owned/tmp"
        for spelling in NAMESPACE_SPELLINGS:
            self.assertTrue(ntpath.splitdrive(spelling)[0], spelling)  # a share or device under the Windows rules
            self.assertEqual(posixpath.split(spelling), ("", spelling))  # one file name under the POSIX rules
            self.assertEqual(native_location_case(spelling, owned, "nt"), (spelling, "SCHEDULE_LOCATION_UNSUPPORTED"))
            location, expected = native_location_case(spelling, owned, "posix")
            self.assertEqual((posixpath.dirname(location), expected), (owned, "SCHEDULE_MISSING"), spelling)
            self.assertEqual(location, posixpath.join(owned, spelling))


class QueryTests(WorldTestCase):
    def test_grains_filters_paging_and_empty_sets(self) -> None:
        code, full, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, "--all")
        self.assertEqual((code, full["total"], full["returned"], full["next_offset"]), (0, 3, 3, None), err)
        keys = [r["schedule"]["event_key"] for r in full["rows"]]
        self.assertEqual(keys, sorted(keys))
        paged = []
        for offset in (0, 1, 2):
            code, page, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, "--limit", "1", "--offset",
                                     str(offset))
            paged += [r["schedule"]["event_key"] for r in page["rows"]]
            self.assertEqual(page["next_offset"], offset + 1 if offset < 2 else None)
        self.assertEqual(paged, keys)
        for extra in (["--limit", "0"], ["--offset", "9"], ["--event", "espn:event:1"], ["--team", "espn:team:1"],
                      ["--event", "espn:event:900000001", "--team", "espn:team:9004"]):
            code, doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, *extra)
            self.assertEqual((code, doc["returned"], doc["rows"]), (0, 0, []), extra)
            if extra[0] != "--limit" and extra[0] != "--offset":
                self.assertEqual((doc["total"], doc["next_offset"]), (0, None), extra)
        code, doc, err = self.q("--grain", "shadow-schedule-source", "--cutoff", CUT, "--team", "espn:team:9006", "--all")
        self.assertEqual([r["source"]["logical"] for r in doc["rows"]], ["900000003-1", "900000003-3"])
        code, doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, "--season", "2025")
        self.assertEqual((doc["season_scope_state"], doc["total"], doc["rows"]), ("NOT_YET_AUDITED", 0, []))
        for row in full["rows"]:
            self.assertEqual(row["labels"], sc.RECORD_LABELS)
            self.assertEqual(row["labels"]["anchor_authority"], "NO_RETROACTIVE_ANCHOR_AUTHORITY")

    def test_cutoff_bound_offsets_and_refusals(self) -> None:
        bound = json.loads(self.path.read_bytes())["acquisition"]["availability_bound_utc"]
        moment = dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ")
        before = (moment - dt.timedelta(microseconds=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", before)
        self.assertEqual((code, fx.refusal(err)), (2, "SCHEDULE_UNAVAILABLE_BEFORE_OBSERVATION_BOUND"))
        at = self.q("--grain", "shadow-schedule", "--cutoff", bound, "--all")[1]
        shifted = (moment - dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "-05:00"
        same = self.q("--grain", "shadow-schedule", "--cutoff", shifted, "--all")[1]
        self.assertEqual(at["rows"], same["rows"])
        self.assertEqual(at["cutoff"]["utc"], same["cutoff"]["utc"])
        late = self.q("--grain", "shadow-schedule", "--cutoff", "2030-01-01T00:00:00Z", "--all")[1]
        self.assertEqual(late["rows"], at["rows"])
        for value, code_name in (("2026-10-13T00:00:00", "CUTOFF_TIMEZONE_REQUIRED"), ("tomorrow", "CUTOFF_INVALID"),
                                 (CUT + "\n", "CUTOFF_INVALID"), ("0001-01-01T00:00:00+14:00", "CUTOFF_OUT_OF_RANGE"),
                                 ("9999-12-31T23:59:59-14:00", "CUTOFF_OUT_OF_RANGE")):
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", value)
            self.assertEqual((code, fx.refusal(err)), (2, code_name), value)
        code, _doc, err = self.q("--grain", "shadow-schedule")
        self.assertEqual(fx.refusal(err), "CUTOFF_REQUIRED")

    def test_mode_and_filter_refusals(self) -> None:
        cases = ((["--require-pit"], "SCHEDULE_PIT_NOT_ADMITTED"), (["--database", "x"], "SCHEDULE_MODE_CONFLICT"),
                 (["--prospective-preview", "x"], "SCHEDULE_MODE_CONFLICT"), (["--model", "m"], "FILTER_NOT_APPLICABLE"),
                 (["--orientation", "home"], "FILTER_NOT_APPLICABLE"), (["--partition", "p"], "FILTER_NOT_APPLICABLE"),
                 (["--event", "401856719"], "EVENT_KEY_INVALID"), (["--team", "Georgia"], "TEAM_KEY_INVALID"),
                 (["--offset", "-1"], "NEGATIVE_OFFSET"), (["--limit", "-1"], "NEGATIVE_LIMIT"),
                 (["--expect-identity", "nothex"], "STALE_SCHEDULE_IDENTITY"),
                 (["--expect-identity", "0" * 64], "STALE_SCHEDULE_IDENTITY"))
        for extra, code_name in cases:
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, *extra)
            self.assertEqual((code, fx.refusal(err)), (2, code_name), extra)
        code, _doc, err = self.q("--grain", "shadow-prediction", "--cutoff", CUT)
        self.assertEqual(fx.refusal(err), "SCHEDULE_GRAIN_REQUIRED")
        out, errs = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errs):
            code = query.main(["--schedule-evidence", str(self.path), "--grain", "shadow-schedule", "--cutoff", CUT])
        self.assertEqual((code, fx.refusal(errs.getvalue())), (2, "SCHEDULE_SHADOW_REQUIRED"))

    def test_locations(self) -> None:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        missing = tmp / ("b" * 64) / "schedule.json"
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, path=missing)
        self.assertEqual(fx.refusal(err), "SCHEDULE_MISSING")
        self.assertFalse(missing.parent.exists())
        for spelling in NAMESPACE_SPELLINGS:
            location, expected = native_location_case(spelling, str(tmp))
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, path=Path(location))
            self.assertEqual((code, fx.refusal(err)), (2, expected), spelling)
            if os.name == "nt":
                self.assertIn("is a network share or a device or namespace path", err, spelling)
            else:
                self.assertFalse(os.path.lexists(location), spelling)
            self.assertEqual(os.listdir(tmp), [], spelling)
        plain = tmp / "plain"
        fx.sfx.write_tree(plain, fx.sfx.read_tree(self.path.parent))
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, path=plain / "schedule.json")
        self.assertEqual(fx.refusal(err), "SCHEDULE_LOCATION_INVALID")

    def test_existing_invocations_unchanged_and_lazy(self) -> None:
        before = set(sys.modules)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = query.main(["--prospective-shadow", str(self.world.shadow), "--grain", "shadow-prediction",
                               "--cutoff", CUT, "--all"], shadow_contract_sha256=self.world.shadow_world.authority,
                              shadow_profile=self.world.shadow_profile)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["total"], 12)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err), \
                self.assertRaises(SystemExit):
            query.main(["--prospective-shadow", str(self.world.shadow), "--grain", "shadow-schedule", "--cutoff", CUT])
        self.assertIn("invalid choice: 'shadow-schedule'", err.getvalue())
        self.assertNotIn("--schedule-evidence", query.build_parser().format_help())
        self.assertNotIn("--schedule-evidence", query.build_shadow_parser().format_help())
        self.assertIn("explicit official schedule evidence mode", query.build_schedule_parser().format_help())
        self.assertNotIn("aggie_analytics.retrospective_baseline.schedule", set(sys.modules) - before)


class ForgeryTests(WorldTestCase):
    def refused(self, path: Path) -> str | None:
        return fx.refusal(self.q("--grain", "shadow-schedule", "--cutoff", CUT, path=path)[2])

    def test_schedule_document_forgeries_reach_their_family(self) -> None:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        cases = {
            "time": (lambda d: d["events"][1]["fields"]["scheduled_time"]["value"].update(
                utc="2026-10-17T18:00:00.000000Z"), "SCHEDULE_EVENT_RECORD_MISMATCH"),
            "venue": (lambda d: d["events"][0]["fields"]["venue_facility"].update(value="Borrowed Bowl"),
                      "SCHEDULE_EVENT_RECORD_MISMATCH"),
            "role": (lambda d: d["events"][0]["fields"]["designation"].update(value="AWAY"),
                     "SCHEDULE_EVENT_RECORD_MISMATCH"),
            "drop": (lambda d: d["events"].pop(), "SCHEDULE_EVENT_MEMBERSHIP_MISMATCH"),
            "dup": (lambda d: d["events"].append(fx.deep(d["events"][0])), "SCHEDULE_EVENT_MEMBERSHIP_MISMATCH"),
            "order": (lambda d: d["events"].reverse(), "SCHEDULE_EVENT_MEMBERSHIP_MISMATCH"),
            "srcdrop": (lambda d: d["sources"].pop(2), "SCHEDULE_SOURCE_MEMBERSHIP_MISMATCH"),
            "status": (lambda d: d["sources"][2]["hops"][0].update(status=200), "SCHEDULE_SOURCE_RECORD_MISMATCH"),
            "bound": (lambda d: d["acquisition"].update(availability_bound_utc="2026-10-12T00:00:00.000000Z"),
                      "SCHEDULE_ACQUISITION_MISMATCH"),
            "countf": (lambda d: d["counts"].update(events=3.0), "SCHEDULE_COUNTS_MISMATCH"),
            "countb": (lambda d: d["acquisition"].update(attempts=True), "SCHEDULE_ACQUISITION_MISMATCH"),
            "counts": (lambda d: d["counts"].update(events="3"), "SCHEDULE_COUNTS_MISMATCH"),
            "label": (lambda d: d["labels"].update(schedule_authority="ACTUAL_KICKOFF"), "SCHEDULE_LABELS_MISMATCH"),
            "anchor": (lambda d: d["shadow"].update(anchor_created_utc=d["acquisition"]["availability_bound_utc"]),
                       "SCHEDULE_SHADOW_MISMATCH"),
            "summary": (lambda d: d["summary"]["dispositions"].update(RECORD_BOUND=2), "SCHEDULE_SUMMARY_MISMATCH"),
            "erase": (lambda d: d["events"][0]["fields"]["designation"].update(witnesses=[]),
                      "SCHEDULE_EVENT_RECORD_MISMATCH"),
            "extra": (lambda d: d.update(published=True), "SCHEDULE_SCHEMA_MISMATCH"),
        }
        for name, (edit, code_name) in cases.items():
            path = fx.forge(self.path, tmp / name, schedule_edit=edit)
            self.assertEqual(self.refused(path), code_name, name)

    def test_member_forgeries(self) -> None:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        page = next(n for n in fx.sfx.read_tree(self.path.parent) if n.startswith("raw/"))

        def swap_body(files: dict) -> None:
            name = next(n for n in files if n.startswith("raw/") and b"<span>Home</span>" in gzip.decompress(files[n]))
            files[name] = gzip.compress(gzip.decompress(files[name]).replace(b"<span>Home</span>",
                                                                             b"<span>Away</span>"), mtime=0)

        def recompress(files: dict) -> None:
            files[page] = gzip.compress(gzip.decompress(files[page]), compresslevel=1, mtime=0)

        def contract(files: dict) -> None:
            files["inputs/contract.json"] = files["inputs/contract.json"] + b" "

        def journal(files: dict) -> None:
            name = "acquisition/journal-01.jsonl"
            files[name] = files[name].replace(b'"status": 404', b'"status": 200')

        def extra(files: dict) -> None:
            files["notes.txt"] = b"x"
        for name, edit, code_name in (("body", swap_body, "SCHEDULE_RAW_BODY_MISMATCH"),
                                      ("gz", recompress, "SCHEDULE_RAW_BODY_NOT_CANONICAL"),
                                      ("ctr", contract, "CONTRACT_NOT_COMMITTED_AUTHORITY"),
                                      ("jrn", journal, "SCHEDULE_SOURCE_MEMBERSHIP_MISMATCH"),
                                      ("xtra", extra, "SCHEDULE_BUNDLE_MEMBERSHIP_MISMATCH")):
            path = fx.forge(self.path, tmp / name, file_edit=edit)
            got = self.refused(path)
            self.assertIn(got, (code_name, "SCHEDULE_NOT_PINNED_SIDECAR", "SCHEDULE_SOURCE_RECORD_MISMATCH",
                                "SCHEDULE_EVENT_RECORD_MISMATCH", "SCHEDULE_ACQUISITION_MISMATCH",
                                "SCHEDULE_SUMMARY_MISMATCH") if name == "jrn" else (code_name,), name)
        wrong = fx.forge(self.path, tmp / "wdir", schedule_edit=lambda d: None)
        renamed = tmp / "w2" / ("f" * 64)
        fx.sfx.write_tree(renamed, fx.sfx.read_tree(wrong.parent))
        self.assertEqual(self.refused(renamed / "schedule.json"), "SCHEDULE_IDENTITY_MISMATCH")

    def test_rehashed_consistent_journal_forgery_needs_the_pinned_profile(self) -> None:
        pages = self.world.genuine_pages()
        pages["espn:event:900000001"] = pages["espn:event:900000001"].replace(b"1 Field", b"Borrowed Bowl")
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        forged = self.world.build(tmp, self.world.genuine_capture(pages))
        self.assertNotEqual(forged["identity"], self.genuine["identity"])
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", CUT, path=forged["path"])
        self.assertEqual((code, fx.refusal(err)), (2, "SCHEDULE_NOT_PINNED_SIDECAR"))


@unittest.skipUnless(sc.SCHEDULE_PROFILE is not None and os.environ.get("AGGIE_ANALYTICS_DATA_ROOT"),
                     "the packaged gate pins no sidecar or no data root is mounted")
class MountedGenuineSidecarTests(unittest.TestCase):
    def test_genuine_sidecar_serves_all_25_events(self) -> None:
        root = Path(os.environ["AGGIE_ANALYTICS_DATA_ROOT"])
        identity = sc.SCHEDULE_PROFILE["schedule_identity"]
        sidecar = root / "canonical" / sc.POPULATION / "sha256" / identity / sc.SCHEDULE_FILE
        shadow_path = root / "canonical" / "provider_record_shadow_20261017" / "sha256" / \
            sc.PRODUCTION_SHADOW["identity"] / "snapshot.json"
        if not sidecar.is_file() or not shadow_path.is_file():
            self.skipTest("the mounted data root holds no canonical sidecar")
        with sc.ScheduleEvidence(sidecar, shadow_path) as evidence:
            bound = evidence.schedule["acquisition"]["availability_bound_utc"]
            doc = evidence.query("shadow-schedule", cutoff=bound, all_rows=True)
            source = evidence.query("shadow-schedule-source", cutoff=bound, all_rows=True)
        self.assertEqual(doc["total"], 25)
        self.assertEqual(len({r["schedule"]["event_key"] for r in doc["rows"]}), 25)
        self.assertGreaterEqual(source["total"], 25)
        self.assertLessEqual(evidence.schedule["acquisition"]["attempts"], 80)


if __name__ == "__main__":
    unittest.main()
