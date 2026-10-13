"""BAT-727: the explicit immutable successor of the official schedule evidence (TP55-A01; retained capture only).

Synthetic worlds only (official_shadow_schedule_expansion_fixture over official_shadow_schedule_fixture): the committed
successor contract, the accepted V1 contract and the packaged profiles stay the only defaults; fixture authorities are
passed explicitly. A mounted test serves the real canonical successor when the packaged gate pins one and a data root is
mounted.
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

import official_shadow_schedule_expansion_fixture as xfx  # noqa: E402
import official_shadow_schedule_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import query  # noqa: E402
from aggie_analytics.retrospective_baseline import schedule as v1  # noqa: E402
from aggie_analytics.retrospective_baseline import schedule_expansion as sx  # noqa: E402

LATE = "2030-01-01T00:00:00Z"
GATE = ROOT / "artifacts" / "data_lake" / "official_shadow_schedule_expansion_20261017_gate.json"
K1, K2, K3 = xfx.K1, xfx.K2, xfx.K3
NAMESPACE_SPELLINGS = (r"\\fixture-server\share" + "\\" + "c" * 64 + r"\schedule.json", r"\\.\PhysicalDrive0")


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="x55"))


def _cleanup(path: Path) -> None:
    shutil.rmtree(fx.sfx.ext(path), ignore_errors=False)


def native_location_case(spelling: str, directory: str, os_name: str = os.name) -> tuple[str, str]:
    """The location the query is given for a namespace spelling and the refusal its native path rules owe: Windows
    refuses the share/device lexically before any access; under POSIX the same characters are one ordinary file name
    inside the test's own directory, which does not exist."""
    if os_name == "nt":
        return spelling, "SCHEDULE_LOCATION_UNSUPPORTED"
    return posixpath.join(directory, spelling), "SCHEDULE_MISSING"


def owner(**names: str) -> dict:
    base = {"official_name": "Boston College", "directory_host": "www.bceagles.com",
            "provider_names": {"displayName": "Boston College Eagles", "shortDisplayName": "Boston College",
                               "location": "Boston College", "name": "Eagles", "abbreviation": "BC"}}
    base.update(names)
    return base


class ContractTests(unittest.TestCase):
    def test_committed_contract_is_the_pinned_authority(self) -> None:
        data = xfx.CONTRACT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), sx.CONTRACT_SHA256)
        spec = sx._spec(data, sx.CONTRACT_SHA256)
        self.assertEqual(spec["contract_id"], sx.CONTRACT_ID)
        self.assertFalse(spec["policy"]["draft"])

    def test_contract_rules_equal_the_frozen_code_and_pin_the_accepted_predecessor(self) -> None:
        data = xfx.CONTRACT_PATH.read_bytes()
        spec = json.loads(data)
        for member, constant in sx.contract_code_document().items():
            self.assertEqual(sx.v1.canonical_bytes(spec[member]), sx.v1.canonical_bytes(constant), member)
        pins = spec["predecessor"]
        self.assertEqual(pins["identity"], v1.SCHEDULE_PROFILE["schedule_identity"])
        self.assertEqual(pins["schedule_sha256"], v1.SCHEDULE_PROFILE["schedule_sha256"])
        self.assertEqual(pins["journal_sha256"], v1.SCHEDULE_PROFILE["journal_sha256"])
        self.assertEqual((pins["contract_id"], pins["contract_sha256"]), (v1.CONTRACT_ID, v1.CONTRACT_SHA256))
        frozen = v1.parse_utc_text(spec["policy_frozen_utc"])
        self.assertGreater(frozen, v1.parse_utc_text(v1.SCHEDULE_PROFILE["availability_bound_utc"]))
        v1_contract = json.loads((ROOT / "configs" / "official_shadow_schedule_20261017_contract.json").read_text(
            encoding="utf-8"))
        cohort = {e["event_key"]: e["owner"] for e in v1_contract["expected"]["events"]}
        self.assertEqual(len(spec["expected"]["events"]), 25)
        for row in spec["expected"]["events"]:
            self.assertEqual((row["ncaa_org_id"], row["official_name"], row["directory_host"]),
                             tuple(cohort[row["event_key"]][k] for k in ("ncaa_org_id", "official_name",
                                                                       "directory_host")))
        orgs = {e["ncaa_org_id"]: e for e in spec["expected"]["events"]}
        for decision in spec["institution_decisions"]:
            row = orgs[decision["ncaa_org_id"]]
            self.assertEqual((decision["official_name"], decision["directory_host"]),
                             (row["official_name"], row["directory_host"]), decision["id"])
            self.assertTrue(decision["witness_documents"], decision["id"])

    def test_packaged_gate_matches_the_reader_profile(self) -> None:
        if sx.EXPANSION_PROFILE is None:
            self.assertFalse(GATE.exists())
            return
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["profile"], sx.EXPANSION_PROFILE)
        self.assertEqual(gate["contract_sha256"], sx.CONTRACT_SHA256)

    def test_v1_constants_and_rules_are_unchanged(self) -> None:
        self.assertEqual(v1.CONTRACT_SHA256, "ac521dc513f39ec247cc88324420c02fae3f3140874ef8de5bfe8ea518dd35e2")
        self.assertEqual(v1.SCHEDULE_PROFILE["schedule_identity"],
                         "a99d70767971b653261c921f57422cc19a749ec53a7ee3ccc8c9c9d5e1c5663e")
        for name in v1.STRUCTURES:
            self.assertEqual(sx.STRUCTURES[name], v1.STRUCTURES[name])
        self.assertNotIn("SIDEARM_CLASSIC_SCHEDULE_DATA", v1.STRUCTURES)
        self.assertNotIn("opponent_annotation", v1.NAME_RULES)


class NameDateAndBasisRuleTests(unittest.TestCase):
    def test_opponent_annotation_is_narrow(self) -> None:
        away = {"missouri", "missouri tigers"}
        self.assertEqual(sx.binds_opponent("#13 Missouri (Homecoming)", away),
                         (True, ["LEADING_POLL_RANK_REMOVED", "EVENT_ANNOTATION_REMOVED:Homecoming"], "missouri"))
        self.assertEqual(sx.binds_opponent("Missouri (Homecoming)", away)[0:2],
                         (True, ["EVENT_ANNOTATION_REMOVED:Homecoming"]))
        for text in ("Missouri (Senior Day)", "Missouri (homecoming)", "Missouri(Homecoming)", "Miami (OH)",
                     "Missouri (Homecoming) (Homecoming)", "Missouri State (Homecoming)", "Homecoming", "MIZ",
                     "Missouri Tigers (Family Weekend)"):
            self.assertFalse(sx.binds_opponent(text, away)[0], text)
        self.assertFalse(sx.binds_opponent("Miami (OH)", {"miami"})[0])
        self.assertTrue(sx.binds_opponent("Miami (OH)", {"miami (oh)"})[0])

    def test_season_dates_need_a_matching_weekday(self) -> None:
        self.assertEqual(sx.split_date("Sat", "Oct 17"), ("2026-10-17", None))
        self.assertEqual(sx.joined_date("Sat, Oct 17"), ("2026-10-17", None))
        self.assertEqual(sx.joined_date("Fri, Oct 17"), (None, "DATE_WEEKDAY_MISMATCH"))
        self.assertEqual(sx.joined_date("Sat, Jan 2"), ("2027-01-02", None))
        self.assertEqual(sx.split_date("", "Oct 17"), (None, "DATE_TEXT_UNRECOGNIZED"))
        self.assertEqual(sx.joined_date("Oct 17"), (None, "DATE_TEXT_UNRECOGNIZED"))
        self.assertEqual(sx.joined_date("Sat, Feb 30"), (None, "DATE_TEXT_INVALID"))

    def test_decision_bases_are_exact(self) -> None:
        bc = owner()
        self.assertTrue(sx.basis_holds("OFFICIAL_NAME_WITHOUT_FINAL_WORD", "Boston", bc))
        self.assertTrue(sx.basis_holds("OFFICIAL_NAME_PLUS_ATHLETICS", "Boston College Athletics", bc))
        self.assertFalse(sx.basis_holds("OFFICIAL_NAME_PLUS_ATHLETICS", "Boston University Athletics", bc))
        self.assertTrue(sx.basis_holds("PROVIDER_TEAM_NAME", "Eagles", bc))
        self.assertFalse(sx.basis_holds("PROVIDER_TEAM_NAME", "Terriers", bc))
        ub = owner(official_name="University at Buffalo, the State University of New York",
                   directory_host="www.ubbulls.com")
        self.assertTrue(sx.basis_holds("OFFICIAL_LEADING_CLAUSE", "University at Buffalo", ub))
        self.assertTrue(sx.basis_holds("OFFICIAL_LEADING_CLAUSE_WITHOUT_FIRST_WORD", "at Buffalo", ub))
        self.assertFalse(sx.basis_holds("OFFICIAL_LEADING_CLAUSE", "Buffalo State", ub))
        army = owner(official_name="U.S. Military Academy", directory_host="goarmywestpoint.com",
                     provider_names={"displayName": "Army Black Knights", "location": "Army", "name": "Black Knights"})
        self.assertTrue(sx.basis_holds("DIRECTORY_ATHLETICS_HOST_BRAND", "Army West Point", army))
        self.assertFalse(sx.basis_holds("DIRECTORY_ATHLETICS_HOST_BRAND", "Navy West Point", army))
        self.assertFalse(sx.basis_holds("DIRECTORY_ATHLETICS_HOST_BRAND", "Army West Point",
                                        {**army, "directory_host": "vmikeydets.com"}))
        lsu = owner(provider_names={"location": "LSU"})
        self.assertTrue(sx.basis_holds("PROVIDER_LOCATION_OFFICIAL_WEBSITE_TITLE",
                                       "LSUsports.net - The Official Website of LSU Athletics", lsu))
        self.assertFalse(sx.basis_holds("PROVIDER_LOCATION_OFFICIAL_WEBSITE_TITLE",
                                        "The Official Website of LSU Athletics Shop", lsu))
        self.assertFalse(sx.basis_holds("UNDECLARED_BASIS", "Boston", bc))
        self.assertFalse(sx.basis_holds("OFFICIAL_NAME_WITHOUT_FINAL_WORD", "", owner(official_name="Boston")))

    def test_json_ld_dates(self) -> None:
        self.assertEqual(sx.ld_dates("2026-10-17T13:30:00"), ["2026-10-17"])
        self.assertEqual(sx.ld_dates("2026-11-28T00:30:00.000000Z"), ["2026-11-27"])
        self.assertEqual(sx.ld_dates("2026-10-17T19:30:00-04:00"), ["2026-10-17"])
        self.assertEqual(sx.ld_dates("2026-10-17T03:30:00Z"), ["2026-10-16"])
        self.assertEqual((sx.ld_dates("nonsense"), sx.ld_dates(None)), ([], []))

    def test_result_labels_and_event_block_clock(self) -> None:
        values = sx.record_values("WMT_DEFAULT_EVENT_VIEW", {"weekday": "Sat", "month_day": "Oct 10", "divider": "at",
                                                             "opponent": "Kentucky", "location": "Lexington, Ky. (KF)",
                                                             "result_label": "L Loss 34-35"})
        self.assertEqual((values["event_date"], values["designation"], values["time"]), ("2026-10-10", "AWAY", []))
        self.assertNotIn("34-35", json.dumps(values))
        values = sx.record_values("WMT_DEFAULT_EVENT_VIEW", {"weekday": "Sat", "month_day": "Oct 17", "divider": "vs.",
                                                             "opponent": "Mississippi State", "location": "BR (TS)",
                                                             "result_label": "11:00 AM CT"})
        self.assertIsNone(values["designation"])
        self.assertEqual(values["time"][0]["utc"], "2026-10-17T16:00:00.000000Z")
        block = sx.record_values("WMT_EVENT_BLOCK_VIEW", {"day.datetime": "2026-11-14T12:00:00.000-05:00",
                                                          "venue_class": "schedule-event-date--venue-home",
                                                          "opponent": "Stanford", "venue": "Lane", "location": "B, Va.",
                                                          "result_label": "TBA"})
        self.assertEqual([s["kind"] for s in block["time"]], ["TBA"])
        self.assertEqual(v1.resolve_time([{"time": block["time"]}])["state"], "TBA")


class StructureTests(unittest.TestCase):
    def test_classic_object_needs_its_registration_season_and_sport(self) -> None:
        game = xfx.classic_game("2026-10-17T13:30:00", "1:30 p.m.", "H", "Zeta Southern")
        doc = sx.extract_document(xfx.classic_page("Epsilon City", [game]))
        classic = [s for s in doc["structures"] if s["structure"] == "SIDEARM_CLASSIC_SCHEDULE_DATA"]
        self.assertEqual((len(classic), classic[0]["season_bound"], classic[0]["owner_names"]),
                         (1, True, ["Epsilon City"]))
        self.assertEqual(classic[0]["records"][0]["members"]["opponent.title"], "Zeta Southern")
        for page in (xfx.classic_page("Epsilon City", [game], register=False),):
            self.assertFalse([s for s in sx.extract_document(page)["structures"]
                              if s["structure"] == "SIDEARM_CLASSIC_SCHEDULE_DATA"])
        for kwargs in ({"season": "2025"}, {"sport": "basketball"}):
            doc = sx.extract_document(xfx.classic_page("Epsilon City", [game], **kwargs))
            self.assertFalse(doc["structures"][0]["season_bound"], kwargs)

    def test_wmt_views_and_headings(self) -> None:
        block = xfx.event_block("2026-10-17T12:00:00.000-05:00", "away", "Delta College")
        doc = sx.extract_document(xfx.wmt_variant_page([block], og="X"))
        view = [s for s in doc["structures"] if s["structure"] == "WMT_EVENT_BLOCK_VIEW"][0]
        self.assertTrue(view["season_bound"])
        self.assertEqual(view["season_witness"]["member"], "h1.schedule-hero-block__title")
        self.assertEqual(view["records"][0]["members"]["venue_class"], "schedule-event-date--venue-away")
        self.assertEqual(doc["identity"]["og:site_name"], ["X"])
        for heading in ("2025 Football Schedule", "Football 2026 Schedule", "2026 Basketball Schedule"):
            doc = sx.extract_document(xfx.wmt_variant_page([block], heading=heading))
            self.assertFalse([s for s in doc["structures"] if s["season_bound"]], heading)
        team = xfx.team_default("Sat, Oct 17", "home", "Delta College")
        doc = sx.extract_document(xfx.wmt_variant_page([team], heading="2026-27 Football Schedule",
                                                       heading_class="schedule-hero__title"))
        view = [s for s in doc["structures"] if s["structure"] == "WMT_TEAM_DEFAULT_VIEW"][0]
        self.assertEqual((view["season_bound"], view["season_witness"]["season_label"]), (True, "2026-27"))
        self.assertEqual(sx.record_values("WMT_TEAM_DEFAULT_VIEW", view["records"][0]["members"])["designation"],
                         "HOME")
        event = xfx.default_event("Sat", "Oct 17", "vs.", "Mississippi State", rank="#16")
        doc = sx.extract_document(xfx.wmt_variant_page([event], heading="2026 Football Schedule",
                                                       heading_class="schedule-hero__title"))
        view = [s for s in doc["structures"] if s["structure"] == "WMT_DEFAULT_EVENT_VIEW"][0]
        members = view["records"][0]["members"]
        self.assertEqual((members["opponent"], members["opponent_rank"], view["owner_names"]),
                         ("Mississippi State", "#16", []))

    def test_page_identity_members(self) -> None:
        page = xfx.nuxt_sidearm_page("Boston", [], site_name="Boston College Athletics", mascot="Eagles",
                                     og="Boston College Athletics")
        identity = sx.extract_document(page)["identity"]
        self.assertEqual(identity, {"siteSettings.siteName": ["Boston College Athletics"],
                                    "siteSettings.mascotPlural": ["Eagles"], "og:site_name": ["Boston College Athletics"]})


class WorldTestCase(unittest.TestCase):
    world: xfx.ExpansionWorld
    built: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = _tmp()
        cls.world = xfx.ExpansionWorld(cls.tmp / "w")
        cls.built = cls.world.build(cls.tmp / "g")
        cls.path = cls.built["path"]

    @classmethod
    def tearDownClass(cls) -> None:
        _cleanup(cls.tmp)

    def q(self, *args: str, built: dict | None = None, path: Path | None = None, profile: object = "pinned"
          ) -> tuple[int, dict | None, str]:
        return self.world.query(built or self.built, *args, path=path, profile=profile)

    def events(self, built: dict) -> dict:
        code, doc, err = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--all", built=built)
        self.assertEqual(code, 0, err)
        return {r["schedule"]["event_key"]: r["schedule"] for r in doc["rows"]}

    def variant(self, **kwargs: object) -> dict:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        return self.world.build(tmp, **kwargs)


class SuccessorTests(WorldTestCase):
    def test_genuine_movements_fields_and_witnesses(self) -> None:
        events = self.events(self.built)
        self.assertEqual({k: (e["predecessor"]["disposition"], e["disposition"], e["movement"]["event"])
                          for k, e in events.items()},
                         {K1: ("OWNER_NOT_VERIFIED", "RECORD_BOUND", "NEWLY_RECORD_BOUND"),
                          K2: ("NO_DECLARED_STRUCTURE", "RECORD_BOUND", "NEWLY_RECORD_BOUND"),
                          K3: ("RECORD_BOUND", "RECORD_BOUND", "PRESERVED_RECORD_BOUND")})
        alpha = events[K1]
        self.assertEqual(alpha["owner"]["identity"][0]["state"], "OWNER_VERIFIED_DOCUMENTED_IDENTITY")
        self.assertEqual(alpha["owner"]["identity"][0]["decision"], "ALPHA_ATHLETICS_OWNER_NAME")
        witness = alpha["fields"]["opponent"]["witnesses"][0]
        self.assertEqual((witness["raw"], witness["normalized"], witness["transformations"]),
                         ("#13 Beta Tech (Homecoming)", "beta tech",
                          ["LEADING_POLL_RANK_REMOVED", "EVENT_ANNOTATION_REMOVED:Homecoming"]))
        self.assertEqual(alpha["fields"]["scheduled_time"]["value"]["utc"], "2026-10-17T16:00:00.000000Z")
        gamma = events[K2]
        self.assertEqual(gamma["owner"]["identity"][0]["state"], "OWNER_VERIFIED_PAGE_IDENTITY")
        self.assertEqual(len(gamma["fields"]["opponent"]["witnesses"]), 2)
        self.assertEqual(gamma["fields"]["designation"]["value"], "HOME")
        self.assertEqual(gamma["fields"]["scheduled_time"]["value"]["utc"], "2026-10-17T17:00:00.000000Z")
        self.assertEqual(events[K3]["movement"]["fields"], {f: "UNCHANGED" for f in sx.FIELDS})
        for event in events.values():
            self.assertEqual(event["labels"]["policy_authority"], "SUCCESSOR_POLICY_NOT_ORIGINAL_INTERPRETATION")

    def test_predecessor_sources_and_timing_are_kept(self) -> None:
        doc = json.loads(self.path.read_bytes())
        v1doc = json.loads(self.built["v1"]["path"].read_bytes())
        self.assertEqual(doc["predecessor"]["identity"], self.built["v1"]["identity"])
        self.assertEqual([{k: s[k] for k in ("logical", "route", "url", "outcome", "hops", "decision")}
                          for s in doc["sources"]],
                         [{k: s[k] for k in ("logical", "route", "url", "outcome", "hops", "decision")}
                          for s in v1doc["sources"]])
        self.assertEqual(doc["availability"]["observation_bound_utc"], v1doc["acquisition"]["availability_bound_utc"])
        self.assertEqual(doc["availability"]["effective_utc"], doc["policy"]["policy_frozen_utc"])
        self.assertEqual(doc["acquisition"]["new_requests"], 0)
        self.assertEqual(doc["shadow"], v1doc["shadow"])
        members = sorted(fx.sfx.read_tree(self.path.parent))
        prefix = f"predecessor/{self.built['v1']['identity']}/"
        self.assertEqual(sorted(m[len(prefix):] for m in members if m.startswith(prefix)),
                         sorted(fx.sfx.read_tree(self.built["v1"]["path"].parent)))
        self.assertEqual(sorted(m for m in members if not m.startswith(prefix)), ["inputs/contract.json",
                                                                                 "schedule.json"])

    def test_cutoffs_effective_availability_and_refusals(self) -> None:
        doc = json.loads(self.path.read_bytes())
        bound, frozen = doc["availability"]["observation_bound_utc"], doc["availability"]["policy_frozen_utc"]

        def shift(text: str, **delta: int) -> str:
            moment = dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ") + dt.timedelta(**delta)
            return moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        for cutoff, code_name in ((shift(bound, microseconds=-1), "SCHEDULE_UNAVAILABLE_BEFORE_OBSERVATION_BOUND"),
                                  (bound, "SCHEDULE_UNAVAILABLE_BEFORE_POLICY_FROZEN"),
                                  (shift(frozen, microseconds=-1), "SCHEDULE_UNAVAILABLE_BEFORE_POLICY_FROZEN")):
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", cutoff)
            self.assertEqual((code, xfx.refusal(err)), (2, code_name), cutoff)
        at = self.q("--grain", "shadow-schedule", "--cutoff", frozen, "--all")[1]
        moment = dt.datetime.strptime(frozen, "%Y-%m-%dT%H:%M:%S.%fZ")
        same = self.q("--grain", "shadow-schedule", "--cutoff",
                      (moment - dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "-05:00", "--all")[1]
        late = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--all")[1]
        self.assertEqual((at["rows"], at["cutoff"]["utc"]), (same["rows"], same["cutoff"]["utc"]))
        self.assertEqual(late["rows"], at["rows"])
        for value, code_name in (("2026-10-14T00:00:00", "CUTOFF_TIMEZONE_REQUIRED"), ("soon", "CUTOFF_INVALID"),
                                 (LATE + "\n", "CUTOFF_INVALID"), ("0001-01-01T00:00:00+14:00", "CUTOFF_OUT_OF_RANGE")):
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", value)
            self.assertEqual((code, xfx.refusal(err)), (2, code_name), value)
        for extra, code_name in ((["--require-pit"], "SCHEDULE_PIT_NOT_ADMITTED"),
                                 (["--database", "x"], "SCHEDULE_MODE_CONFLICT"),
                                 (["--model", "m"], "FILTER_NOT_APPLICABLE"),
                                 (["--expect-identity", "0" * 64], "STALE_SCHEDULE_IDENTITY")):
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", LATE, *extra)
            self.assertEqual((code, xfx.refusal(err)), (2, code_name), extra)

    def test_grains_filters_paging_and_empty_sets(self) -> None:
        code, full, err = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--all")
        self.assertEqual((code, full["total"], full["returned"], full["next_offset"]), (0, 3, 3, None), err)
        keys = [r["schedule"]["event_key"] for r in full["rows"]]
        paged = []
        for offset in (0, 1, 2):
            page = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--limit", "1", "--offset", str(offset))[1]
            paged += [r["schedule"]["event_key"] for r in page["rows"]]
            self.assertEqual(page["next_offset"], offset + 1 if offset < 2 else None)
        self.assertEqual(paged, keys)
        for extra in (["--limit", "0"], ["--offset", "9"], ["--event", "espn:event:1"], ["--team", "espn:team:1"],
                      ["--event", K1, "--team", "espn:team:9004"]):
            doc = self.q("--grain", "shadow-schedule", "--cutoff", LATE, *extra)[1]
            self.assertEqual((doc["returned"], doc["rows"]), (0, []), extra)
            if extra[0] not in ("--limit", "--offset"):
                self.assertEqual((doc["total"], doc["next_offset"]), (0, None), extra)
        doc = self.q("--grain", "shadow-schedule-source", "--cutoff", LATE, "--team", "espn:team:9006", "--all")[1]
        self.assertEqual([r["source"]["logical"] for r in doc["rows"]], ["900000003-1", "900000003-3"])
        doc = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--season", "2025")[1]
        self.assertEqual((doc["season_scope_state"], doc["total"], doc["rows"]), ("NOT_YET_AUDITED", 0, []))
        self.assertEqual(full["season_scope_state"], sx.IN_SCOPE_STATE)
        for row in full["rows"]:
            self.assertEqual(row["labels"], sx.RECORD_LABELS)

    def test_v1_sidecars_keep_the_v1_reader_and_answers(self) -> None:
        v1_path = self.built["v1"]["path"]
        self.assertFalse(sx.selects(v1_path))
        self.assertTrue(sx.selects(self.path))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = query.main(["--prospective-shadow", str(self.world.v1.shadow), "--schedule-evidence", str(v1_path),
                               "--grain", "shadow-schedule", "--cutoff", LATE, "--all"],
                              schedule_contract_sha256=self.world.v1.authority,
                              schedule_profile=self.built["v1"]["profile"], shadow_profile=self.world.v1.shadow_profile)
        with v1.ScheduleEvidence(v1_path, self.world.v1.shadow, contract_sha256=self.world.v1.authority,
                                 profile=self.built["v1"]["profile"],
                                 shadow_profile=self.world.v1.shadow_profile) as evidence:
            direct = evidence.query("shadow-schedule", cutoff=LATE, all_rows=True)
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(out.getvalue(), json.dumps(direct, ensure_ascii=False, sort_keys=True) + "\n")
        self.assertEqual(json.loads(out.getvalue())["contract_id"], v1.CONTRACT_ID)

    def test_lazy_import_and_help(self) -> None:
        before = set(sys.modules)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            query.main(["--prospective-shadow", str(self.world.v1.shadow), "--grain", "shadow-prediction", "--cutoff",
                        LATE, "--all"], shadow_contract_sha256=self.world.v1.shadow_world.authority,
                       shadow_profile=self.world.v1.shadow_profile)
        self.assertFalse({"aggie_analytics.retrospective_baseline.schedule_expansion"} & (set(sys.modules) - before))
        text = " ".join(query.build_schedule_parser().format_help().split())
        self.assertIn("explicit official schedule evidence mode", text)
        self.assertIn("BAT-727 expansion profile", text)
        self.assertNotIn("--schedule-evidence", query.build_parser().format_help())


class VariantTests(WorldTestCase):
    def test_wrong_program_and_substituted_identity_never_bind(self) -> None:
        pages = self.world.genuine_pages()
        cases = {"similar_program": pages[K1].replace(b"Fixture Alpha Owls", b"Fixture Alpha Hawks"),
                 "other_institution": pages[K1].replace(b'"Owls"', b'"Terriers"'),
                 "statement_not_decided": pages[K1].replace(b"Alpha State Athletics", b"Alpha Athletic Club")}
        for name, alpha in cases.items():
            events = self.events(self.variant(pages={**pages, K1: alpha}))
            self.assertEqual(events[K1]["disposition"], "OWNER_NOT_VERIFIED", name)
            self.assertEqual(events[K1]["fields"]["event_date"]["state"], "UNSUPPORTED", name)
        events = self.events(self.variant(decisions=[xfx.gamma_decision()]))  # no decision for alpha's institution
        self.assertEqual(events[K1]["disposition"], "OWNER_NOT_VERIFIED")
        self.assertEqual(events[K2]["disposition"], "RECORD_BOUND")
        gamma = pages[K2].replace(b"Gamma A&amp;M University Athletics", b"Gamma Tech Athletics").replace(
            b"Gamma A&M University Athletics", b"Gamma Tech Athletics")
        self.assertEqual(self.events(self.variant(pages={**pages, K2: gamma}))[K2]["disposition"],
                         "OWNER_NOT_VERIFIED")

    def test_decorations_unrelated_participants_and_annotation_limits(self) -> None:
        pages = self.world.genuine_pages()
        for text, disposition in ((b"#13 Beta Tech (Senior Day)", "UNBOUND_OPPONENT_ON_EVENT_DATE"),
                                  (b"Zeta (Homecoming)", "UNBOUND_OPPONENT_ON_EVENT_DATE"),
                                  (b"Epsilon City", "UNBOUND_OPPONENT_ON_EVENT_DATE"),
                                  (b"Beta Tech", "RECORD_BOUND")):
            alpha = pages[K1].replace(b"#13 Beta Tech (Homecoming)", text)
            events = self.events(self.variant(pages={**pages, K1: alpha}))
            self.assertEqual(events[K1]["disposition"], disposition, text)
            if disposition != "RECORD_BOUND":
                self.assertEqual(events[K1]["fields"]["opponent"]["unbound_names"], [text.decode()], text)

    def test_layout_rules_roles_and_json_ld_conflicts(self) -> None:
        pages = self.world.genuine_pages()
        away = xfx.wmt_variant_page([xfx.event_block("2026-10-17T12:00:00.000-05:00", "away", "Delta College")],
                                    og="Gamma A&M University Athletics")
        events = self.events(self.variant(pages={**pages, K2: away}))
        self.assertEqual((events[K2]["fields"]["designation"]["value"], events[K2]["fields"]["designation"]["comparison"]),
                         ("AWAY", "DISAGREES"))
        stale = xfx.wmt_variant_page([xfx.event_block("2026-10-17T12:00:00.000-05:00", "home", "Delta College")],
                                     heading="2025 Football Schedule", og="Gamma A&M University Athletics")
        self.assertEqual(self.events(self.variant(pages={**pages, K2: stale}))[K2]["disposition"],
                         "NO_DECLARED_STRUCTURE")
        team = xfx.wmt_variant_page([xfx.team_default("Sat, Oct 17", "home", "Delta College"),
                                     xfx.team_default("Fri, Oct 17", "home", "Delta College", row=True)],
                                    heading="2026-27 Football Schedule", heading_class="schedule-hero__title",
                                    og="Gamma A&M University Athletics")
        gamma = self.events(self.variant(pages={**pages, K2: team}))[K2]
        self.assertEqual((gamma["disposition"], len(gamma["fields"]["event_date"]["witnesses"])), ("RECORD_BOUND", 1))
        self.assertEqual(gamma["occurrences"][0]["relation"], "BOUND_OPPONENT_DATE_UNDETERMINED")
        lsu = xfx.wmt_variant_page([xfx.default_event("Sat", "Oct 17", "vs.", "Delta College", rank="#16"),
                                    xfx.default_event("Sat", "Oct 17", "vs.", "Delta College", rank="#16", row=True)],
                                   heading="2026 Football Schedule", heading_class="schedule-hero__title",
                                   og="Gamma A&M University Athletics")
        gamma = self.events(self.variant(pages={**pages, K2: lsu}))[K2]
        self.assertEqual((gamma["disposition"], gamma["fields"]["designation"]["state"]), ("RECORD_BOUND",
                                                                                           "UNSUPPORTED"))
        self.assertEqual(gamma["fields"]["scheduled_time"]["value"]["utc"], "2026-10-17T16:00:00.000000Z")
        game = xfx.classic_game("2026-10-17T15:30:00", "3:30 p.m. ET", "H", "Zeta Southern", facility="3 Field")
        for ld, state in (([xfx.ld_event("2026-10-17T15:30:00", "Epsilon City University", "Zeta Southern")],
                           "SUPPORTED"),
                          ([xfx.ld_event("2026-10-17T15:30:00", "Zeta Southern", "Epsilon City University")],
                           "CONFLICTING")):
            epsilon = xfx.classic_page("Epsilon City", [game], ld=ld)
            event = self.events(self.variant(pages={**pages, K3: epsilon}))[K3]
            self.assertEqual((event["disposition"], event["fields"]["designation"]["state"]), ("RECORD_BOUND", state))
        epsilon = xfx.classic_page("Epsilon City", [xfx.classic_game("2026-10-17T15:30:00", "3:30 p.m.", "H",
                                                                     "Zeta Southern University")])
        event = self.events(self.variant(pages={**pages, K3: epsilon}))[K3]
        self.assertEqual((event["predecessor"]["disposition"], event["disposition"], event["movement"]["event"]),
                         ("NO_DECLARED_STRUCTURE", "UNBOUND_OPPONENT_ON_EVENT_DATE",
                          "STILL_UNSUPPORTED_DISPOSITION_REFINED"))
        self.assertEqual(event["fields"]["opponent"]["unbound_names"], ["Zeta Southern University"])

    def test_borrowed_zone_and_page_identity_never_supply_fields(self) -> None:
        pages = self.world.genuine_pages()
        naive = pages[K1].replace(b"11:00 a.m. CT", b"11:00 a.m.").replace(b"</title>", b" (all times CT)</title>")
        alpha = self.events(self.variant(pages={**pages, K1: naive}))[K1]
        self.assertEqual(alpha["fields"]["scheduled_time"]["state"], "NAIVE_LOCAL_TIME_ONLY")
        nameless = xfx.wmt_variant_page([xfx.event_block("2026-10-17T12:00:00.000-05:00", "home", "")],
                                        og="Gamma A&M University Athletics")
        gamma = self.events(self.variant(pages={**pages, K2: nameless}))[K2]
        self.assertEqual((gamma["disposition"], gamma["fields"]["opponent"]["unbound_names"]),
                         ("UNBOUND_OPPONENT_ON_EVENT_DATE", [""]))
        self.assertTrue(all(f["state"] == "UNSUPPORTED" for f in gamma["fields"].values()))

    def test_contract_timing_and_decision_refusals(self) -> None:
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415

        bound = self.built["v1"]["profile"]["availability_bound_utc"]
        early = (dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ") - dt.timedelta(seconds=1)).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ")
        cases = ((dict(policy_frozen_utc=early), "SCHEDULE_EXPANSION_RETROACTIVE_POLICY_TIME"),
                 (dict(decisions=[xfx.alpha_decision(identity_members=[{"member": "siteSettings.mascotPlural",
                                                                        "value": "Hawks",
                                                                        "basis": "PROVIDER_TEAM_NAME"}])]),
                  "SCHEDULE_EXPANSION_DECISION_BASIS_INVALID"),
                 (dict(decisions=[xfx.alpha_decision(ncaa_org_id=1)]), "SCHEDULE_EXPANSION_DECISION_INVALID"),
                 (dict(decisions=[xfx.alpha_decision(kind="SOMETHING")]), "SCHEDULE_EXPANSION_CONTRACT_MALFORMED"),
                 (dict(edit=lambda c: c["expected"]["events"].pop()), "SCHEDULE_EXPANSION_COHORT_MISMATCH"),
                 (dict(edit=lambda c: c["shadow"].update(identity="0" * 64)), "SCHEDULE_EXPANSION_SHADOW_MISMATCH"),
                 (dict(edit=lambda c: c["predecessor"].update(attempts=float(c["predecessor"]["attempts"]))),
                  "SCHEDULE_EXPANSION_CONTRACT_MALFORMED"),
                 (dict(edit=lambda c: c["predecessor"].update(journal_sha256="0" * 64)),
                  "SCHEDULE_EXPANSION_PREDECESSOR_NOT_PINNED"),
                 (dict(edit=lambda c: c["predecessor"].update(identity="0" * 64)),
                  "SCHEDULE_EXPANSION_PREDECESSOR_NOT_PINNED"),
                 (dict(edit=lambda c: c["labels"].update(policy_authority="ORIGINAL")),
                  "SCHEDULE_EXPANSION_CONTRACT_CODE_DISAGREEMENT"))
        for kwargs, code_name in cases:
            tmp = _tmp()
            self.addCleanup(_cleanup, tmp)
            with self.assertRaises(builder.BuildRefused) as caught:
                self.world.build(tmp, v1_built=self.built["v1"], **kwargs)
            self.assertEqual(caught.exception.code, code_name, kwargs)


class SidecarTests(WorldTestCase):
    def test_determinism_rebuild_interrupt_rehouse_and_profile(self) -> None:
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415

        for overrides in ({"processing_order": "reversed"}, {"processing_order": "shuffled:7"}, {"chunk_size": "7"}):
            tmp = _tmp()
            self.addCleanup(_cleanup, tmp)
            other = self.world.build(tmp, v1_built=self.built["v1"], **overrides)
            self.assertEqual(other["identity"], self.built["identity"], overrides)
            self.assertEqual(other["path"].read_bytes(), self.path.read_bytes())
        again = self.world.build(self.tmp / "g", v1_built=self.built["v1"])
        self.assertEqual((again["identity"], again["state"]), (self.built["identity"], "ALREADY_PRESENT_IDENTICAL"))
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        with self.assertRaises(builder.BuildInterrupted):
            self.world.build(tmp, v1_built=self.built["v1"], stop_after_members=5)
        self.assertFalse((tmp / "x" / "sha256").exists())
        resumed = self.world.build(tmp, v1_built=self.built["v1"])
        self.assertEqual(resumed["identity"], self.built["identity"])
        moved = xfx.rehouse(self.path, tmp / ("r" * 80))
        code, doc, err = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--all", path=moved)
        full = self.q("--grain", "shadow-schedule", "--cutoff", LATE, "--all")[1]
        self.assertEqual((code, doc["rows"]), (0, full["rows"]), err)
        code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", LATE, profile=sx.PINNED)
        self.assertEqual(xfx.refusal(err), "SCHEDULE_EXPANSION_PROFILE_NOT_PINNED" if sx.EXPANSION_PROFILE is None
                         else "SCHEDULE_EXPANSION_NOT_PINNED_SIDECAR")

    def test_locations(self) -> None:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        missing = tmp / ("e" * 64) / "schedule.json"
        self.assertEqual(xfx.refusal(self.q("--grain", "shadow-schedule", "--cutoff", LATE, path=missing)[2]),
                         "SCHEDULE_MISSING")
        self.assertFalse(missing.parent.exists())
        for spelling in NAMESPACE_SPELLINGS:
            location, expected = native_location_case(spelling, str(tmp))
            code, _doc, err = self.q("--grain", "shadow-schedule", "--cutoff", LATE, path=Path(location))
            self.assertEqual((code, xfx.refusal(err)), (2, expected), spelling)
            self.assertEqual(os.listdir(tmp), [], spelling)
        plain = tmp / "plain"
        fx.sfx.write_tree(plain, fx.sfx.read_tree(self.path.parent))
        self.assertEqual(xfx.refusal(self.q("--grain", "shadow-schedule", "--cutoff", LATE,
                                            path=plain / "schedule.json")[2]), "SCHEDULE_LOCATION_INVALID")


class NativeLocationRuleTests(unittest.TestCase):
    def test_namespace_refusal_is_owed_only_under_windows_path_rules(self) -> None:
        owned = "/owned/tmp"
        for spelling in NAMESPACE_SPELLINGS:
            self.assertTrue(ntpath.splitdrive(spelling)[0], spelling)
            self.assertEqual(posixpath.split(spelling), ("", spelling))
            self.assertEqual(native_location_case(spelling, owned, "nt"), (spelling, "SCHEDULE_LOCATION_UNSUPPORTED"))
            location, expected = native_location_case(spelling, owned, "posix")
            self.assertEqual((posixpath.dirname(location), expected, location),
                             (owned, "SCHEDULE_MISSING", posixpath.join(owned, spelling)))


class ForgeryTests(WorldTestCase):
    def refused(self, path: Path) -> str | None:
        return xfx.refusal(self.q("--grain", "shadow-schedule", "--cutoff", LATE, path=path)[2])

    def forge(self, **kwargs: object) -> Path:
        tmp = _tmp()
        self.addCleanup(_cleanup, tmp)
        return xfx.forge(self.path, tmp, **kwargs)

    def test_schedule_document_forgeries_reach_their_family(self) -> None:
        cases = (
            (lambda d: d["events"][1]["fields"]["designation"].update(value="AWAY"), "SCHEDULE_EXPANSION_EVENT_RECORD"),
            (lambda d: d["events"][0]["fields"]["opponent"]["witnesses"][0].update(transformations=[]),
             "SCHEDULE_EXPANSION_EVENT_RECORD"),
            (lambda d: d["events"][0]["owner"]["identity"][0].update(decision=None), "SCHEDULE_EXPANSION_EVENT_RECORD"),
            (lambda d: d["events"][0]["fields"]["scheduled_time"]["value"].update(utc="2026-10-17T20:00:00.000000Z"),
             "SCHEDULE_EXPANSION_EVENT_RECORD"),
            (lambda d: d["events"][2]["movement"].update(event="NEWLY_RECORD_BOUND"),
             "SCHEDULE_EXPANSION_EVENT_RECORD"),
            (lambda d: d["events"][0]["predecessor"].update(disposition="RECORD_BOUND"),
             "SCHEDULE_EXPANSION_EVENT_RECORD"),
            (lambda d: d["events"].pop(), "SCHEDULE_EXPANSION_EVENT_MEMBERSHIP"),
            (lambda d: d["events"].append(d["events"][0]), "SCHEDULE_EXPANSION_EVENT_MEMBERSHIP"),
            (lambda d: d["events"].reverse(), "SCHEDULE_EXPANSION_EVENT_MEMBERSHIP"),
            (lambda d: d["sources"].pop(), "SCHEDULE_EXPANSION_SOURCE_MEMBERSHIP"),
            (lambda d: d["sources"][0]["hops"][0].update(status=200), "SCHEDULE_EXPANSION_SOURCE_RECORD"),
            (lambda d: d["sources"][1]["document"]["json_ld"].update(admitted=True),
             "SCHEDULE_EXPANSION_SOURCE_RECORD"),
            (lambda d: d["availability"].update(effective_utc=d["availability"]["observation_bound_utc"]),
             "SCHEDULE_EXPANSION_AVAILABILITY"),
            (lambda d: d["policy"].update(policy_frozen_utc=d["availability"]["observation_bound_utc"]),
             "SCHEDULE_EXPANSION_POLICY"),
            (lambda d: d["predecessor"].update(attempts=float(d["predecessor"]["attempts"])),
             "SCHEDULE_EXPANSION_PREDECESSOR"),
            (lambda d: d["acquisition"].update(new_requests=False), "SCHEDULE_EXPANSION_ACQUISITION"),
            (lambda d: d["counts"].update(events=True), "SCHEDULE_EXPANSION_COUNTS"),
            (lambda d: d["counts"].update(new_requests=0.0), "SCHEDULE_EXPANSION_COUNTS"),
            (lambda d: d["summary"]["movements"].update(SUPPORT_LOST=1), "SCHEDULE_EXPANSION_SUMMARY"),
            (lambda d: d["labels"].update(anchor_authority="RETROACTIVE"), "SCHEDULE_EXPANSION_LABELS"),
            (lambda d: d.update(extra=1), "SCHEDULE_EXPANSION_SCHEMA"),
        )
        for edit, family in cases:
            self.assertEqual(self.refused(self.forge(schedule_edit=edit)), f"{family}_MISMATCH", family)

    def test_member_forgeries(self) -> None:
        prefix = f"predecessor/{self.built['v1']['identity']}/"

        def drop_body(files: dict) -> None:
            files.pop(next(n for n in sorted(files) if n.startswith(prefix + "raw/")))

        def swap_body(files: dict) -> None:
            name = next(n for n in sorted(files) if n.startswith(prefix + "raw/"))
            files[name] = gzip.compress(gzip.decompress(files[name]) + b" ", mtime=0)

        def extra(files: dict) -> None:
            files["inputs/notes.txt"] = b"x"

        def extra_predecessor(files: dict) -> None:
            files[prefix + "raw/extra.gz"] = gzip.compress(b"x", mtime=0)

        def contract(files: dict) -> None:
            files["inputs/contract.json"] = files["inputs/contract.json"].replace(b'"version": "2.0.0"',
                                                                                b'"version": "2.0.1"')
        for edit, code_name in ((drop_body, "SCHEDULE_EXPANSION_PREDECESSOR_SCHEDULE_RAW_BODY_MISSING"),
                                (swap_body, "SCHEDULE_EXPANSION_PREDECESSOR_SCHEDULE_RAW_BODY_MISMATCH"),
                                (extra, "SCHEDULE_EXPANSION_BUNDLE_MEMBERSHIP_MISMATCH"),
                                (extra_predecessor, "SCHEDULE_EXPANSION_PREDECESSOR_SCHEDULE_BUNDLE_MEMBERSHIP_MISMATCH"),
                                (contract, "SCHEDULE_EXPANSION_CONTRACT_NOT_COMMITTED_AUTHORITY")):
            self.assertEqual(self.refused(self.forge(file_edit=edit)), code_name, edit.__name__)

    def test_rebuilt_edited_capture_needs_the_pinned_predecessor(self) -> None:
        pages = self.world.genuine_pages()
        pages[K3] = pages[K3].replace(b"3 Field", b"Borrowed Bowl")
        forged = self.variant(pages=pages)
        self.assertNotEqual(forged["identity"], self.built["identity"])
        # a fully consistent successor over an edited capture (its own contract authority and profile) is refused
        # only because its predecessor is not the pinned accepted V1 evidence
        code, _doc, err = self.world.query({**forged, "v1": self.built["v1"]}, "--grain", "shadow-schedule",
                                           "--cutoff", LATE)
        self.assertEqual((code, xfx.refusal(err)), (2, "SCHEDULE_EXPANSION_PREDECESSOR_SCHEDULE_NOT_PINNED_SIDECAR"))
        self.assertEqual(xfx.refusal(self.q("--grain", "shadow-schedule", "--cutoff", LATE, path=forged["path"])[2]),
                         "SCHEDULE_EXPANSION_CONTRACT_NOT_COMMITTED_AUTHORITY")


@unittest.skipUnless(sx.EXPANSION_PROFILE is not None and os.environ.get("AGGIE_ANALYTICS_DATA_ROOT"),
                     "the packaged gate pins no successor or no data root is mounted")
class MountedGenuineSuccessorTests(unittest.TestCase):
    def test_genuine_successor_serves_all_25_events(self) -> None:
        root = Path(os.environ["AGGIE_ANALYTICS_DATA_ROOT"])
        sidecar = root / "canonical" / sx.POPULATION / "sha256" / sx.EXPANSION_PROFILE["schedule_identity"] / \
            sx.SCHEDULE_FILE
        shadow_path = root / "canonical" / "provider_record_shadow_20261017" / "sha256" / \
            v1.PRODUCTION_SHADOW["identity"] / "snapshot.json"
        if not sidecar.is_file() or not shadow_path.is_file():
            self.skipTest("the mounted data root holds no canonical successor")
        with sx.ExpansionEvidence(sidecar, shadow_path) as evidence:
            effective = evidence.schedule["availability"]["effective_utc"]
            doc = evidence.query("shadow-schedule", cutoff=effective, all_rows=True)
            source = evidence.query("shadow-schedule-source", cutoff=effective, all_rows=True)
        self.assertEqual(doc["total"], 25)
        self.assertEqual(source["total"], 40)
        self.assertEqual(evidence.schedule["counts"]["new_requests"], 0)
        self.assertEqual(evidence.schedule["predecessor"]["identity"], v1.SCHEDULE_PROFILE["schedule_identity"])
        self.assertEqual(sum(r["schedule"]["movement"]["event"] == "SUPPORT_LOST" for r in doc["rows"]), 0)


if __name__ == "__main__":
    unittest.main()
