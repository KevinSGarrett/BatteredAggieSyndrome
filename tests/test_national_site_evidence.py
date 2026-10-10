"""BAT-721 (Cycle #49 — Attempt #1, TP49-A01): the explicit official-site evidence sidecar on tiny owned worlds.

The producer is the repository builder (tools/build_national_site_evidence.py) and the consumer is the query module
(``main`` and its verified handle). The predecessor is the accepted alias builder's successor over the same world.
Evidence and rule negatives change one thing at a time and must refuse (or decide) by that rule's own code; database
forgeries are coordinated (bytes, counts, identity document, identity directory and manifest rewritten consistently) so
each must be refused by its semantic rule, never by a stale outer hash.

One test uses only accepted behaviour and passes on the unfixed base (BEFORE_REPRODUCTION): the accepted alias successor
keeps every site disagreement with both claims side by side and resolves none.
"""
from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(ROOT / "src"), str(Path(__file__).resolve().parent)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from aggie_analytics.national_population import query  # noqa: E402
import national_site_evidence_fixture as fx  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
CONTRACT = ROOT / "configs" / "national_site_evidence_2024_2025_contract.json"
UNIVERSE = list(fx.EXPECTED)


def native(path: str | Path) -> str:
    text = os.path.abspath(str(path)) if not str(path).startswith(EXT) else str(path)
    return EXT + text if WINDOWS and not text.startswith(EXT) else text


def long_root(base: str) -> str:
    return os.path.join(base, "long " + "x" * 120, "deeper # % é ' " + "y" * 120, "tail " + "z" * 40)


class AcceptedPredecessorTests(unittest.TestCase):
    """Accepted behaviour only (the BEFORE_REPRODUCTION positive on the unfixed base): no site evidence is involved."""

    def test_the_alias_successor_keeps_every_site_disagreement_side_by_side(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            world = fx.build_world(work / "d")
            v1 = fx.build_v1(work / "d", world, work)
            alias = fx.build_alias_successor(work / "d", world, v1, work)
            with query.NationalPopulationDatabase(world["parent_db"]) as parent:
                with query.AliasReconciliationSuccessor(alias["database"], parent=parent,
                                                        parent_database=world["parent_db"],
                                                        anchors=alias["anchors"]) as handle:
                    records = handle.records["parent-reconciliation"]
        site = [r for r in records if r["relation"] and "DISAGREE" in (r["comparisons"]["neutral_status"]["result"],
                                                                       r["comparisons"]["home_orientation"]["result"])]
        self.assertEqual([r["contest_key"] for r in site], UNIVERSE)
        self.assertTrue(all(r["disposition"] == "RECONCILED_FIELD_CONFLICT" for r in site))
        by = {r["contest_key"]: r for r in site}
        self.assertEqual(by["ncaa:9104"]["field_conflicts"], ["home_orientation"])
        self.assertTrue(all(by[k]["field_conflicts"] == ["neutral_status"] for k in UNIVERSE if k != "ncaa:9104"))
        self.assertEqual((by["ncaa:9101"]["comparisons"]["neutral_status"]["parent_site"],
                          by["ncaa:9101"]["comparisons"]["neutral_status"]["provider_neutral_site"]), ("HOME_B", True))
        agree = next(r for r in records if r["contest_key"] == "ncaa:9105")
        self.assertEqual(agree["disposition"], "RECONCILED_FIELDS_AGREE")


class Fixture(unittest.TestCase):
    """One world per class: parent, inputs, the V1 and alias predecessors, the evidence bundle, the contract and a
    canonical sidecar build (read only for the tests)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.setup_error = None
        try:
            cls.work = Path(cls._tmp.name)
            cls.base = cls.work / "d"
            cls.world = fx.build_world(cls.base)
            cls.parent_db = cls.world["parent_db"]
            cls.v1 = fx.build_v1(cls.base, cls.world, cls.work)
            cls.alias = fx.build_alias_successor(cls.base, cls.world, cls.v1, cls.work)
            cls.ev = fx.evidence()
            cls.evidence_dir = cls.work / "ev"
            cls.pins = fx.write_evidence(cls.evidence_dir, cls.ev)
            cls.contract = cls.work / "site_contract.json"
            cls.anchors = fx.site_contract(cls.contract, cls.alias, cls.pins, UNIVERSE)
            cls.builder = fx.load_module(fx.BUILDER, "build_national_site_evidence_fixture")
            code, cls.built, err = cls.build(cls.contract, cls.base)
            if code != 0:
                raise AssertionError(f"fixture build refused: {err}")
            cls.sidecar = Path(cls.built["database"]["data_dir"]) / fx.DB_NAME
            with cls.predecessor() as pred:
                cls.parent_records = pred.records["parent-reconciliation"]
            cls.bundle_root = cls.base / "canonical" / fx.POPULATION
        except Exception as exc:  # noqa: BLE001 - each test then fails on its own identity (unfixed-base proof)
            cls.setup_error = f"{type(exc).__name__}: {exc}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    @classmethod
    def build(cls, contract: Path, out: Path, *extra: str, evidence: Path | None = None) -> tuple[int, dict, str]:
        return fx.run_builder(cls.builder, [
            "--contract", str(contract), "--predecessor-contract", str(cls.alias["contract"]),
            "--v1-contract", str(cls.v1["contract"]), "--parent-database", str(cls.parent_db),
            "--reconciliation", str(cls.alias["database"]), "--evidence-source", str(evidence or cls.evidence_dir),
            "--output-root", str(out / "canonical" / fx.POPULATION),
            "--manifest-root", str(out / "manifests" / fx.POPULATION), *extra])

    @classmethod
    @contextlib.contextmanager
    def predecessor(cls, alias_anchors: dict | None = None):
        with query.NationalPopulationDatabase(cls.parent_db) as parent:
            with query.AliasReconciliationSuccessor(cls.alias["database"], parent=parent, parent_database=cls.parent_db,
                                                    anchors=alias_anchors or cls.alias["anchors"]) as pred:
                yield pred

    def setUp(self) -> None:
        if self.setup_error:
            self.fail(f"fixture unavailable: {self.setup_error}")

    def open(self, sidecar: Path | None = None, *, anchors: dict | None = None, **kwargs):
        with self.predecessor() as pred:
            return query.SiteEvidenceSidecar(sidecar or self.sidecar, predecessor=pred, anchors=anchors or self.anchors,
                                             **kwargs)

    def refused(self, code: str, sidecar: Path | None = None, **kwargs) -> None:
        with self.assertRaises(query.NationalQueryError) as ctx:
            self.open(sidecar, **kwargs).close()
        self.assertEqual(ctx.exception.code, code, str(ctx.exception))

    def records(self) -> dict[str, dict]:
        with self.open() as handle:
            return {r["contest_key"]: r for r in handle.records}

    def run_main(self, *args: str, anchors: dict | None = None) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(query, "SITE_EVIDENCE_ANCHORS", anchors if anchors is not None else self.anchors), \
                mock.patch.object(query, "ALIAS_ANCHORS", self.alias["anchors"]), \
                mock.patch.object(query, "RECONCILIATION_ANCHORS", self.v1["anchors"]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(["--database", str(self.parent_db), *args])
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def site_main(self, *args: str, sidecar: Path | None = None, **kwargs) -> tuple[int, dict | None, str]:
        return self.run_main("--reconciliation", str(self.alias["database"]), "--site-evidence",
                             str(sidecar or self.sidecar), "--grain", "site-evidence", *args, **kwargs)

    def refusal(self, *args: str, **kwargs) -> str | None:
        code, _r, err = self.run_main(*args, **kwargs)
        self.assertEqual(code, 2, err)
        return json.loads(err.strip().splitlines()[-1]).get("refused")


class DerivationTests(Fixture):
    def test_every_contest_gets_exactly_its_designed_disposition(self) -> None:
        records = self.records()
        self.assertEqual(list(records), UNIVERSE)
        self.assertEqual({k: r["disposition"] for k, r in records.items()}, fx.EXPECTED)
        self.assertEqual(self.built["summary"]["contests"], 7)
        self.assertTrue(all(r["pit_class"] == query.SITE_PIT_CLASS for r in records.values()))

    def test_an_alternate_home_venue_supports_the_parent_home_site(self) -> None:
        r = self.records()["ncaa:9101"]
        self.assertEqual(r["fields"]["neutral_designation"]["state"], "SUPPORTED")
        self.assertIs(r["fields"]["neutral_designation"]["value"], False)
        self.assertEqual(r["fields"]["designated_home"]["value"], {"side": "b", "participant_key": "org:811"})
        self.assertEqual(r["fields"]["physical_venue"]["value"], "Lakefront Temporary Field")
        self.assertEqual(r["claim_checks"]["provider"]["neutral_designation"], "CONTRADICTED")
        self.assertEqual({e["side"]: e["opponent_binding"] for e in r["event_records"]},
                         {"a": "DOCUMENTED_NAME", "b": "OFFICIAL_SITE"})

    def test_a_genuinely_neutral_event_names_its_flagged_designated_home(self) -> None:
        r = self.records()["ncaa:9102"]
        self.assertIs(r["fields"]["neutral_designation"]["value"], True)
        self.assertEqual(r["fields"]["designated_home"]["value"]["side"], "b")
        self.assertEqual(r["claim_checks"]["parent"], {"neutral_designation": "CONTRADICTED",
                                                       "designated_home": "SUPPORTED"})

    def test_conflicting_official_sources_are_kept_never_voted(self) -> None:
        r = self.records()["ncaa:9103"]
        field = r["fields"]["neutral_designation"]
        self.assertEqual((field["state"], field["value"]), ("CONFLICTING", None))
        self.assertEqual(sorted((s["side"], s["value"]) for s in field["sources"]), [("a", False), ("b", True)])
        self.assertEqual(r["disposition"], "OFFICIAL_SOURCES_CONFLICT")

    def test_a_designated_home_team_at_the_opponents_stadium(self) -> None:
        r = self.records()["ncaa:9104"]
        self.assertEqual((r["discrepancy"], r["disputed_field"]), ("HOME_ORIENTATION_DISAGREEMENT", "home_orientation"))
        self.assertEqual(r["fields"]["designated_home"]["value"], {"side": "b", "participant_key": "org:813"})
        self.assertEqual(r["fields"]["physical_venue"]["value"], "Summit Stadium")
        self.assertIs(r["fields"]["neutral_designation"]["value"], True)
        self.assertEqual(r["claim_checks"]["parent"]["neutral_designation"], "CONTRADICTED")
        self.assertEqual(r["claim_checks"]["provider"]["designated_home"], "SUPPORTED")

    def test_unbound_and_denied_sources_leave_explicit_unsupported_fields(self) -> None:
        r = self.records()["ncaa:9202"]
        self.assertEqual(r["event_records"], [])
        self.assertEqual(r["unsupported_fields"], list(query.SITE_FIELDS))
        self.assertEqual(sorted(e["outcome"] for e in r["examined_documents"]),
                         ["ATTEMPT_WITHOUT_DOCUMENT", "RECORD_ON_DATE_OPPONENT_NOT_BOUND"])
        denied = next(e for e in r["examined_documents"] if e["outcome"] == "ATTEMPT_WITHOUT_DOCUMENT")
        self.assertEqual(denied["detail"], {"attempt_outcome": "HOST_STOPPED_HTTP_403"})

    def test_venue_or_tournament_never_states_neutral_and_a_stale_date_is_not_borrowed(self) -> None:
        r = self.records()["ncaa:9203"]
        self.assertEqual(r["disposition"], "UNSUPPORTED_FIELD_NOT_STATED")
        self.assertEqual(r["fields"]["physical_venue"]["value"], "Lakefront Temporary Field")
        self.assertEqual(r["fields"]["neutral_designation"]["state"], "UNSUPPORTED")
        stale = next(e for e in r["examined_documents"] if e["outcome"] == "OPPONENT_RECORD_ON_OTHER_DATE")
        self.assertEqual(stale["detail"], {"dates": ["2025-10-03"], "final_event_date": "2025-10-04"})

    def test_a_january_final_belongs_to_its_season_and_an_unadmitted_page_is_reported(self) -> None:
        r = self.records()["ncaa:9201"]
        self.assertEqual((r["season"], r["final_event_date"]), (2025, "2026-01-19"))
        self.assertEqual(r["event_records"][0]["locator"]["path"][3], "schedules-football,2025")
        plain = next(e for e in r["examined_documents"] if e["side"] == "b")
        self.assertEqual(plain["outcome"], "NO_DECLARED_RECORD_SCHEMA")
        self.assertIn("SIDEARM_NUXT_SCHEDULE", plain["detail"])

    def test_widget_and_other_sport_records_are_never_used(self) -> None:
        r = self.records()["ncaa:9101"]
        home = next(e for e in r["event_records"] if e["side"] == "b")
        self.assertEqual(home["locator"]["path"][:4], ["pinia", "schedule", "schedules", "schedules-football,2024"])
        self.assertEqual(home["values"]["location_designation"], "H")

    def test_every_document_and_attempt_is_accounted(self) -> None:
        with self.open() as handle:
            sources = handle.sources
        self.assertEqual([s["source_key"] for s in sources], sorted(a["request_id"] for a in
                                                                    self.ev["sources"]["attempts"]))
        self.assertEqual(sum(1 for s in sources if s["outcome"] == "RETAINED_200"), 11)
        schedules = [s for s in sources if s["role"] == "OFFICIAL_SEASON_SCHEDULE" and s["document"]]
        self.assertTrue(all(s["examined_for"] for s in schedules))
        self.assertEqual(self.built["summary"]["examined_outcomes"]["BOUND"], self.built["summary"]["event_records"])

    def test_original_claims_are_the_predecessors_and_the_predecessor_is_unchanged(self) -> None:
        before = fx.sha(self.alias["database"])
        by = {r["contest_key"]: r for r in self.parent_records}
        for key, r in self.records().items():
            source = by[key]
            self.assertEqual(r["original_claims"]["field_conflicts"], source["field_conflicts"])
            self.assertEqual(r["original_claims"]["parent_site"], source["comparisons"]["neutral_status"]["parent_site"])
            self.assertEqual(r["provider_row_key"], source["relation"]["provider_row_key"])
        self.assertEqual(fx.sha(self.alias["database"]), before)


class RuleTests(Fixture):
    """The decision rules on single records: designations, flags, opponent binding and field states."""

    def statements(self, **values) -> dict:
        base = {"location_designation": None, "neutral_home_team": None, "facility": None, "location": None}
        base.update(values)
        return query._statements(base, "SIDEARM_NUXT_SCHEDULE", "a", "b")

    def test_only_the_three_way_designation_states_neutral_or_home(self) -> None:
        self.assertEqual(self.statements(location_designation="H")["neutral_designation"], False)
        self.assertEqual(self.statements(location_designation="A")["designated_home"], "b")
        self.assertEqual(self.statements(location_designation="N")["designated_home"], None)
        for value in ("h", "Home", "", "vs", None):
            with self.subTest(value=value):
                s = self.statements(location_designation=value, facility="Somewhere Field")
                self.assertEqual((s["neutral_designation"], s["designated_home"]), (None, None))
                self.assertEqual(s["physical_venue"], "Somewhere Field")

    def test_the_neutral_home_flag_must_be_a_boolean_true_on_a_neutral_record(self) -> None:
        self.assertEqual(self.statements(location_designation="N", neutral_home_team=True)["designated_home"], "a")
        for flag in ("true", 1, False, None):
            with self.subTest(flag=flag):
                self.assertIsNone(self.statements(location_designation="N", neutral_home_team=flag)["designated_home"])
        self.assertEqual(self.statements(location_designation="A", neutral_home_team=True)["designated_home"], "b")

    def test_opponent_binding_by_official_site_or_documented_name_only(self) -> None:
        opponent = {"team_name": "Prairie St.", "provider_name": "Prairie State"}
        org = {"host_family": ["prairiestatesports.example", "www.prairiestatesports.example"],
               "name_official": "Prairie State University"}
        bind = query._opponent_binding
        self.assertEqual(bind({"opponent_site": "http://www.prairiestatesports.example/x"}, opponent, org),
                         "OFFICIAL_SITE")
        for name in ("Prairie St.", "prairie state", "Prairie State University", "PRAIRIE ST"):
            with self.subTest(name=name):
                self.assertEqual(bind({"opponent_name": name, "opponent_site": None}, opponent, org), "DOCUMENTED_NAME")
        for name in ("Prairie", "Prairie State A&M", "North Prairie State", ""):
            with self.subTest(name=name):
                self.assertIsNone(bind({"opponent_name": name, "opponent_site": "https://prairie.example/"},
                                       opponent, org))

    def test_field_states_never_vote(self) -> None:
        self.assertEqual(query._field([("d1", "a", True), ("d2", "b", True)])["state"], "SUPPORTED")
        self.assertEqual(query._field([("d1", "a", True), ("d2", "b", False), ("d3", "b", False)])["state"],
                         "CONFLICTING")
        self.assertEqual(query._field([("d1", "a", None)])["state"], "UNSUPPORTED")

    def test_classic_pages_bind_by_weekday_year_title_and_their_own_game_elements(self) -> None:
        games = [{"date": "Jan 19 (Mon)", "token": "sidearm-schedule-neutral-game", "opponent": "Canyon A&amp;M",
                  "site": "canyonaggies.example", "spans": ["Metro City, ST", "Metro Dome"]},
                 {"date": "Apr 13 (Sat)", "token": "sidearm-schedule-home-game", "opponent": "Spring Game",
                  "spans": ["Lakeside, ST", "Lakeside, ST"]},
                 {"date": "Sep 7 (Fri)", "token": "sidearm-schedule-away-game", "opponent": "Prairie"},
                 {"date": "Oct 4", "token": "sidearm-schedule-home-game sidearm-schedule-away-game",
                  "opponent": "Harbor Tech"}]
        page = fx.classic_page("811", 2025, games)
        result = query.extract_site_records(page, 2025)
        self.assertEqual(result["schema"], "SIDEARM_CLASSIC_SCHEDULE")
        self.assertEqual(len(result["events"]), 4)
        first, spring, wrong_weekday, broken = (e["values"] for e in result["events"])
        self.assertEqual(query.site_event_date(first, result["schema"], 2025), "2026-01-19")
        self.assertEqual((first["location_designation"], first["opponent_name"], first["facility"]),
                         ("sidearm-schedule-neutral-game", "Canyon A&M", "Metro Dome"))
        self.assertEqual(query.site_event_date(spring, result["schema"], 2025), None)  # Apr 13 is no Saturday in 2025/26
        self.assertIsNone(spring["facility"])  # a second span repeating the location is no facility
        self.assertIsNone(query.site_event_date(wrong_weekday, result["schema"], 2025))
        self.assertIsNone(query.site_event_date(broken, result["schema"], 2025))
        self.assertIsNone(broken["location_designation"])  # two designation tokens state nothing
        self.assertEqual(query.site_event_date(spring, result["schema"], 2024), "2024-04-13")
        other = query.extract_site_records(fx.classic_page("811", 2025, games, title="Lakefront Athletics"), 2025)
        self.assertFalse(other["matched"])
        self.assertIn("CLASSIC_TITLE_NOT_A_SEASON_SCHEDULE", other["reasons"]["SIDEARM_CLASSIC_SCHEDULE"])
        self.assertFalse(query.extract_site_records(page, 2024)["matched"])  # another season's page
        start, end = result["events"][0]["locator"]["element_bytes"]
        self.assertTrue(page[start:end].startswith(b"<li class=\"sidearm-schedule-game ") and page[start:end].endswith(
            b"</li>"))
        r = self.records()["ncaa:9103"]
        delta = next(e for e in r["event_records"] if e["side"] == "a")
        self.assertEqual((delta["schema"], delta["event_local_date"], delta["statements"]["designation"]),
                         ("SIDEARM_CLASSIC_SCHEDULE", "2024-10-05", "HOME"))

    def test_wmt_pages_use_the_date_elements_venue_designation_and_split_city_from_facility(self) -> None:
        games = [{"venue": "home", "datetime": "2025-10-04T19:00:00.000-05:00", "opponent": "#4/5 Harbor Tech",
                  "location": "Lakeside, ST / Lakefront Temporary Field"},
                 {"venue": "away", "datetime": "2026-01-19T19:30:00.000-05:00", "opponent": "Canyon A&amp;M",
                  "location": "Metro City, ST"},
                 {"venue": "bogus", "datetime": "2025-11-01", "opponent": "Prairie St.", "location": "Lakeside"}]
        page = fx.wmt_page("811", 2025, games)
        result = query.extract_site_records(page, 2025)
        self.assertEqual(result["schema"], "WMT_EVENT_SCHEDULE")
        first, second, third = (e["values"] for e in result["events"])
        self.assertEqual(query.site_event_date(first, result["schema"], 2025), "2025-10-04")
        self.assertEqual(query.site_event_date(second, result["schema"], 2025), "2026-01-19")
        self.assertEqual((first["location"], first["facility"], first["location_designation"], first["at_vs"]),
                         ("Lakeside, ST", "Lakefront Temporary Field", "schedule-event-date--venue-home", "vs."))
        self.assertEqual((second["location"], second["facility"], second["opponent_name"]),
                         ("Metro City, ST", None, "Canyon A&M"))
        self.assertIsNone(third["location_designation"])
        s = query._statements(first, "WMT_EVENT_SCHEDULE", "a", "b")
        self.assertEqual((s["designation"], s["neutral_designation"], s["designated_home"], s["physical_venue"]),
                         ("HOME", False, "a", "Lakefront Temporary Field"))
        opponent = {"team_name": "Harbor Tech", "provider_name": "Harbor Tech"}
        self.assertEqual(query._opponent_binding(first, opponent, None), "DOCUMENTED_NAME")
        self.assertIsNone(query._opponent_binding({"opponent_name": "4 Harbor Tech"}, opponent, None))
        self.assertFalse(query.extract_site_records(fx.wmt_page("811", 2025, games, title="Schedule"), 2025)["matched"])
        r = self.records()["ncaa:9104"]
        summit = next(e for e in r["event_records"] if e["side"] == "a")
        self.assertEqual((summit["schema"], summit["opponent_binding"], summit["statements"]["physical_venue"]),
                         ("WMT_EVENT_SCHEDULE", "DOCUMENTED_NAME", "Summit Stadium"))

    def test_two_bound_records_on_the_final_date_are_ambiguous(self) -> None:
        sources = dict(query.verify_site_sources(query.load_site_bundle(self.bundle_root, self.anchors)))
        lake = next(d for d in sources["documents"].values() if d["org_id"] == "811" and d["season"] == 2024)
        double = fx.schedule_page("811", 2024, [
            fx.event("2024-09-07", "Prairie", "H", site=fx.site("812")),
            fx.event("2024-09-07", "Prairie State", "N")])
        sources["bodies"] = dict(sources["bodies"], **{lake["sha256"]: double})
        derived = query.derive_site_evidence(self.parent_records, sources)
        r = next(x for x in derived["records"] if x["contest_key"] == "ncaa:9101")
        self.assertIn("AMBIGUOUS_RECORDS_ON_DATE", [e["outcome"] for e in r["examined_documents"]])
        self.assertEqual([e["side"] for e in r["event_records"]], ["a"])


class BundleTests(Fixture):
    """The sources document and the bundle files: each mutation refuses for its own rule."""

    def verify(self, change) -> str | None:
        bundle = query.load_site_bundle(self.bundle_root, self.anchors)
        bundle = dict(bundle, sources=copy.deepcopy(bundle["sources"]))
        change(bundle["sources"])
        try:
            sources = query.verify_site_sources(bundle)
            query.derive_site_evidence(self.parent_records, sources)
        except query.NationalQueryError as exc:
            return exc.code
        return None

    def doc(self, sources: dict, org: str, season: int) -> dict:
        return next(d for d in sources["documents"] if d["org_id"] == org and d["season"] == season)

    def attempt(self, sources: dict, sha: str) -> dict:
        return next(a for a in sources["attempts"] if a["hops"] and a["hops"][-1]["body_sha256"] == sha)

    def test_the_genuine_sources_verify(self) -> None:
        self.assertIsNone(self.verify(lambda s: None))

    def test_receipts_must_be_consistent_200_hop_chains(self) -> None:
        def bad_status(s):
            self.doc(s, "811", 2024)["hops"][-1]["status"] = 301
        self.assertEqual(self.verify(bad_status), "SITE_EVIDENCE_RECEIPT_INVALID")

        def outcome(s):
            s["attempts"][-1]["outcome"] = "HOST_STOPPED_HTTP_429"
        self.assertEqual(self.verify(outcome), "SITE_EVIDENCE_RECEIPT_INVALID")

        def retrieved(s):
            d = self.doc(s, "812", 2024)
            d["retrieved_at"] = "2026-10-10"
        self.assertEqual(self.verify(retrieved), "SITE_EVIDENCE_RECEIPT_INVALID")

    def test_forged_source_metadata_refuses_for_its_own_rule(self) -> None:
        def other_org(s):  # Lakefront's page claimed as Prairie's
            d = self.doc(s, "811", 2024)
            a = self.attempt(s, d["sha256"])
            d["org_id"] = a["org_id"] = "812"
        self.assertEqual(self.verify(other_org), "SITE_EVIDENCE_DOMAIN_UNPROVEN")

        def other_season(s):
            d = self.doc(s, "812", 2024)
            a = self.attempt(s, d["sha256"])
            d["season"] = a["season"] = 2025
        self.assertEqual(self.verify(other_season), "SITE_EVIDENCE_SEASON_UNPROVEN")

        def unknown_org(s):
            d = self.doc(s, "815", 2025)
            a = self.attempt(s, d["sha256"])
            d["org_id"] = a["org_id"] = "777"
        self.assertEqual(self.verify(unknown_org), "SITE_EVIDENCE_DOMAIN_UNPROVEN")

    def test_reordered_omitted_and_unrelated_sources_refuse(self) -> None:
        self.assertEqual(self.verify(lambda s: s["attempts"].reverse()), "SITE_EVIDENCE_SOURCES_ORDER_INVALID")
        self.assertEqual(self.verify(lambda s: s["documents"].reverse()), "SITE_EVIDENCE_SOURCES_ORDER_INVALID")

        def orphan(s):  # a retained document whose acquisition attempt is omitted
            sha = self.doc(s, "813", 2024)["sha256"]
            s["attempts"] = [a for a in s["attempts"] if not (a["hops"] and a["hops"][-1]["body_sha256"] == sha)]
        self.assertEqual(self.verify(orphan), "SITE_EVIDENCE_SOURCES_INVALID")

        def unrelated(s):  # Summit's 2025 schedule belongs to no universe contest
            a = copy.deepcopy(s["attempts"][-1])
            a.update(request_id="C49-P02-R98", org_id="816", season=2025,
                     request_url=fx.schedule_url("816", 2025))
            a["hops"][0]["url"] = a["request_url"]
            s["attempts"].insert(-1, a)
        self.assertEqual(self.verify(unrelated), "SITE_EVIDENCE_SOURCES_INVALID")

    def test_a_directory_must_be_one_ncaa_member_list(self) -> None:
        def foreign(s):
            d = next(x for x in s["documents"] if x["role"] == "NCAA_MEMBER_DIRECTORY")
            a = self.attempt(s, d["sha256"])
            for hop in (d["hops"][0], a["hops"][0]):
                hop["url"] = "https://directory.example/members"
            d["request_url"] = d["final_url"] = a["request_url"] = "https://directory.example/members"
        self.assertEqual(self.verify(foreign), "SITE_EVIDENCE_DIRECTORY_INVALID")

    def bundle_copy(self, name: str) -> Path:
        root = self.work / "bundles" / name
        for kind in ("canonical", "manifests"):
            shutil.copytree(self.base / kind / fx.POPULATION / "sha256" / self.pins["bundle_identity"],
                            root / kind / fx.POPULATION / "sha256" / self.pins["bundle_identity"])
        return root / "canonical" / fx.POPULATION

    def test_bundle_bytes_listing_and_pins(self) -> None:
        root = self.bundle_copy("flip")
        body = next(p for p in (root / "sha256" / self.pins["bundle_identity"]).iterdir() if p.suffix == ".gz")
        raw = bytearray(gzip.decompress(body.read_bytes()))
        raw[len(raw) // 2] ^= 1
        body.write_bytes(gzip.compress(bytes(raw), mtime=0))
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_site_bundle(root, self.anchors)
        self.assertEqual(ctx.exception.code, "SITE_EVIDENCE_BYTES_MISMATCH")
        root = self.bundle_copy("extra")
        (root / "sha256" / self.pins["bundle_identity"] / "extra.gz").write_bytes(b"x")
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_site_bundle(root, self.anchors)
        self.assertEqual(ctx.exception.code, "SITE_EVIDENCE_LISTING_MISMATCH")
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_site_bundle(self.bundle_root, dict(self.anchors, evidence={
                "bundle_identity": self.pins["bundle_identity"], "sources_sha256": "e" * 64}))
        self.assertEqual(ctx.exception.code, "SITE_EVIDENCE_PIN_MISMATCH")


class ForgeryTests(Fixture):
    """Coordinated sidecar forgeries: bytes, counts, identity document, identity directory and manifest consistent;
    the evidence bundle travels with each copy, so only the forged member can explain the refusal."""

    def setUp(self) -> None:
        super().setUp()
        self._forge = tempfile.TemporaryDirectory()
        self.forge_root = Path(self._forge.name)
        self.count = 0

    def tearDown(self) -> None:
        self._forge.cleanup()

    def forge(self, statements: list[tuple[str, tuple]], document: dict | None = None, *,
              bundle: tuple[Path, str] | None = None) -> Path:
        """A coordinated forgery of the canonical sidecar beside a copy of an evidence bundle (``bundle`` = (base
        holding canonical/ and manifests/, bundle identity); the genuine bundle by default)."""
        self.count += 1
        root = self.forge_root / f"f{self.count}"
        source, bundle_id = bundle or (self.base, self.pins["bundle_identity"])
        for kind in ("canonical", "manifests"):
            shutil.copytree(source / kind / fx.POPULATION / "sha256" / bundle_id,
                            root / kind / fx.POPULATION / "sha256" / bundle_id)
        work = root / "work.sqlite"
        shutil.copyfile(self.sidecar, work)
        conn = sqlite3.connect(work)
        for sql, params in statements:
            changed = conn.execute(sql, params).rowcount
            if not sql.lstrip().upper().startswith("CREATE"):
                self.assertGreater(changed, 0, sql)
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in query.SITE_TABLES}
        conn.close()
        manifest = json.loads((self.base / "manifests" / fx.POPULATION / "sha256" / self.sidecar.parent.name /
                               "run_manifest.json").read_text(encoding="utf-8"))
        doc = copy.deepcopy(manifest["identity_document"])
        doc["outputs"] = {fx.DB_NAME: fx.sha(work)}
        doc["table_counts"] = counts
        doc.update(document or {})
        identity = hashlib.sha256(query.canonical_json_bytes(doc)).hexdigest()
        target = root / "canonical" / fx.POPULATION / "sha256" / identity / fx.DB_NAME
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = root / "manifests" / fx.POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps({"identity": identity, "identity_document": doc, "provenance": {}}), encoding="utf-8")
        return target

    def record_update(self, table: str, key_column: str, key: str, mutate) -> tuple[str, tuple]:
        conn = sqlite3.connect(self.sidecar.as_uri() + "?mode=ro", uri=True)
        text = conn.execute(f"SELECT record FROM {table} WHERE {key_column} = ?", (key,)).fetchone()[0]
        conn.close()
        record = json.loads(text)
        mutate(record)
        return f"UPDATE {table} SET record = ? WHERE {key_column} = ?", (query.reconciliation_line(record), key)

    @staticmethod
    def meta(key: str, value) -> tuple[str, tuple]:
        return "UPDATE meta SET value = ? WHERE key = ?", (json.dumps(value, sort_keys=True, separators=(",", ":")), key)

    def test_forged_decisions_claims_and_sources_refuse_for_their_own_rule(self) -> None:
        def venue_neutral(r):  # neutral inferred from the venue: the field and the disposition flipped together
            r["fields"]["neutral_designation"].update(state="SUPPORTED", value=True)
            r["disposition"] = "PROVIDER_CLAIM_SUPPORTED"
        self.refused("SITE_EVIDENCE_FIELD_MISMATCH", self.forge([
            self.record_update("site_evidence", "contest_key", "ncaa:9203", venue_neutral)]))

        def role(r):
            r["disposition"] = "PARENT_CLAIM_SUPPORTED"
        self.refused("SITE_EVIDENCE_DISPOSITION_MISMATCH", self.forge([
            self.record_update("site_evidence", "contest_key", "ncaa:9103", role)]))

        def claim(r):
            r["original_claims"]["provider_neutral_site"] = False
        self.refused("SITE_EVIDENCE_CLAIM_MISMATCH", self.forge([
            self.record_update("site_evidence", "contest_key", "ncaa:9101", claim)]))

        def omit_capture(r):
            r["examined_documents"] = [e for e in r["examined_documents"] if e["outcome"] != "ATTEMPT_WITHOUT_DOCUMENT"]
        self.refused("SITE_EVIDENCE_SOURCE_RECORD_MISMATCH", self.forge([
            self.record_update("site_evidence", "contest_key", "ncaa:9202", omit_capture)]))

        def other_event(r):
            r["event_records"][0]["locator"]["path"][-1] = 1
        self.refused("SITE_EVIDENCE_SOURCE_RECORD_MISMATCH", self.forge([
            self.record_update("site_evidence", "contest_key", "ncaa:9101", other_event)]))

        def denial(r):
            r["outcome"] = "RETAINED_200"
        self.refused("SITE_EVIDENCE_SOURCE_RECORD_MISMATCH", self.forge([
            self.record_update("site_source", "source_key", "C49-P02-R99", denial)]))

    def test_missing_extra_duplicate_and_reordered_records_refuse(self) -> None:
        self.refused("SITE_EVIDENCE_RECORD_MISSING", self.forge([
            ("DELETE FROM site_evidence WHERE contest_key = ?", ("ncaa:9202",))]))
        conn = sqlite3.connect(self.sidecar.as_uri() + "?mode=ro", uri=True)
        row = list(conn.execute("SELECT * FROM site_evidence WHERE contest_key = 'ncaa:9101'").fetchone())
        conn.close()
        extra = dict(json.loads(row[-1]), contest_key="ncaa:9105")
        self.refused("SITE_EVIDENCE_RECORD_EXTRA", self.forge([
            ("INSERT INTO site_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             (99, "ncaa:9105", *row[2:-1], query.reconciliation_line(extra)))]))
        self.refused("SITE_EVIDENCE_DUPLICATE_ROW", self.forge([
            ("INSERT INTO site_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (99, *row[1:]))]))
        self.refused("SITE_EVIDENCE_ORDER_MISMATCH", self.forge([
            ("UPDATE site_evidence SET ord = ord + 100 WHERE contest_key = ?", ("ncaa:9101",))]))
        self.refused("SITE_EVIDENCE_INDEX_MISMATCH", self.forge([
            ("UPDATE site_evidence SET disposition = ? WHERE contest_key = ?", ("PARENT_CLAIM_SUPPORTED", "ncaa:9103"))]))

    def test_rehashed_claims_summaries_and_identity_documents_refuse(self) -> None:
        summary = json.loads(json.dumps(self.built["summary"]))
        summary["by_disposition"]["PARENT_CLAIM_SUPPORTED"] += 1
        self.refused("SITE_EVIDENCE_SUMMARY_MISMATCH", self.forge([self.meta("summary", summary)]))
        self.refused("SITE_EVIDENCE_PIT_CLAIM_INVALID", self.forge([self.meta(
            "labels", dict(query.SITE_LABELS, pit_eligibility="PIT_ELIGIBLE"))]))
        self.refused("SITE_EVIDENCE_PIN_MISMATCH", self.forge([self.meta(
            "evidence", {"bundle_identity": "d" * 64, "sources_sha256": self.pins["sources_sha256"]})]))
        self.refused("SITE_EVIDENCE_PREDECESSOR_MISMATCH", self.forge([self.meta(
            "predecessor", dict(self.anchors["predecessor"], content_identity="a" * 64))]))
        counts = self.built["table_counts"]
        self.refused("SITE_EVIDENCE_IDENTITY_DOCUMENT_MISMATCH",
                     self.forge([], {"table_counts": {k: float(v) for k, v in counts.items()}}))
        self.refused("SITE_EVIDENCE_IDENTITY_DOCUMENT_MISMATCH", self.forge([], {"outputs": {
            fx.DB_NAME: fx.sha(self.sidecar), "fabricated_evidence.json": "f" * 64}}))
        self.refused("SITE_EVIDENCE_SCHEMA_UNSUPPORTED", self.forge([("CREATE TABLE extra (x TEXT)", ())]))

    def test_an_edited_raw_witness_with_coordinated_hashes_reaches_its_semantic_rule(self) -> None:
        """Lakefront's 2024 record edited from H to N, then every hash rewritten: the body name, the document entry,
        the attempt's receipt, the sources document and the bundle identity."""
        ev = copy.deepcopy(self.ev)
        sources = ev["sources"]
        lake = next(d for d in sources["documents"] if d["org_id"] == "811" and d["season"] == 2024)
        old = lake["sha256"]
        body = ev["bodies"].pop(old).replace(b'"H"', b'"N"', 1)
        new = hashlib.sha256(body).hexdigest()
        self.assertNotEqual(new, old)
        ev["bodies"][new] = body
        lake.update(sha256=new, file=new + ".gz", bytes=len(body))
        attempt = next(a for a in sources["attempts"] if a["hops"] and a["hops"][-1]["body_sha256"] == old)
        attempt["hops"][-1].update(body_sha256=new, body_bytes=len(body))
        sources["documents"].sort(key=lambda d: d["sha256"])
        edited_dir = self.forge_root / "edited-ev"
        pins = fx.write_evidence(edited_dir, ev)
        edited = self.forge_root / "edited"
        repinned = dict(self.anchors, evidence=pins)
        self.builder.materialize_evidence(edited_dir, edited / "canonical" / fx.POPULATION,
                                          edited / "manifests" / fx.POPULATION, repinned, {})
        # under the genuine identity directory, the edited bundle is not the pinned evidence
        under = self.forge_root / "under-genuine-identity"
        for kind in ("canonical", "manifests"):
            shutil.copytree(edited / kind / fx.POPULATION / "sha256" / pins["bundle_identity"],
                            under / kind / fx.POPULATION / "sha256" / self.pins["bundle_identity"])
        manifest = under / "manifests" / fx.POPULATION / "sha256" / self.pins["bundle_identity"] / "run_manifest.json"
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        doc["identity"] = self.pins["bundle_identity"]
        manifest.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_site_bundle(under / "canonical" / fx.POPULATION, self.anchors)
        self.assertEqual(ctx.exception.code, "SITE_EVIDENCE_IDENTITY_MISMATCH")
        # a coordinated re-pin (contract and sidecar meta) reaches the re-derived records, which differ
        forged = self.forge([self.meta("evidence", pins)], bundle=(edited, pins["bundle_identity"]))
        self.refused("SITE_EVIDENCE_SOURCE_RECORD_MISMATCH", forged, anchors=repinned)

    def test_a_sidecar_without_its_evidence_or_another_universe_or_predecessor_refuses(self) -> None:
        copy_root = self.forge_root / "no-evidence"
        identity = self.sidecar.parent.name
        for kind, name in (("canonical", fx.DB_NAME), ("manifests", "run_manifest.json")):
            target = copy_root / kind / fx.POPULATION / "sha256" / identity / name
            target.parent.mkdir(parents=True)
            shutil.copyfile(self.base / kind / fx.POPULATION / "sha256" / identity / name, target)
        self.refused("SITE_EVIDENCE_MISSING", copy_root / "canonical" / fx.POPULATION / "sha256" / identity / fx.DB_NAME)
        short = dict(self.anchors, universe={"keys": UNIVERSE[:-1]})
        self.refused("SITE_EVIDENCE_SCOPE_CLAIM_INVALID", anchors=short)
        self.refused("SITE_EVIDENCE_UNIVERSE_MISMATCH", self.forge([self.meta("scope", query.site_scope(short))]),
                     anchors=short)
        self.refused("SITE_EVIDENCE_PREDECESSOR_MISMATCH",
                     anchors=dict(self.anchors, predecessor=dict(self.anchors["predecessor"], database_identity="b" * 64)))
        tampered = self.forge_root / "tampered" / "canonical" / fx.POPULATION / "sha256" / identity / fx.DB_NAME
        tampered.parent.mkdir(parents=True)
        data = bytearray(self.sidecar.read_bytes())
        data[-100] ^= 1
        tampered.write_bytes(bytes(data))
        man = self.forge_root / "tampered" / "manifests" / fx.POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        shutil.copyfile(self.base / "manifests" / fx.POPULATION / "sha256" / identity / "run_manifest.json", man)
        self.refused("SITE_EVIDENCE_DATABASE_TAMPERED", tampered)
        elsewhere = self.forge_root / "elsewhere" / fx.DB_NAME
        elsewhere.parent.mkdir(parents=True)
        shutil.copyfile(self.sidecar, elsewhere)
        self.refused("SITE_EVIDENCE_LOCATION_INVALID", elsewhere)


class ConsumerTests(Fixture):
    def keys(self, *argv: str) -> list[str]:
        code, result, err = self.site_main(*argv)
        self.assertEqual(code, 0, err)
        return [r["contest_key"] for r in result["rows"]]

    def test_the_full_collection_paging_and_identities(self) -> None:
        code, everything, err = self.site_main("--all")
        self.assertEqual(code, 0, err)
        self.assertEqual((everything["total"], everything["returned"]), (7, 7))
        self.assertEqual(everything["site_evidence_identity"], self.sidecar.parent.name)
        self.assertEqual(everything["reconciliation_identity"], self.alias["built"]["database_identity"])
        self.assertEqual(everything["evidence"], self.pins)
        self.assertEqual(everything["pit_eligibility"], "PIT_ELIGIBILITY_NOT_ESTABLISHED")
        self.assertEqual(everything["collection_denominators"], self.built["summary"])
        seen, offset = [], 0
        while True:
            code, page, _ = self.site_main("--limit", "3", "--offset", str(offset))
            seen.extend(page["rows"])
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        self.assertEqual(seen, everything["rows"])
        code, empty, _ = self.site_main("--limit", "0")
        self.assertEqual((empty["total"], empty["returned"], empty["rows"]), (7, 0, []))

    def test_season_team_contest_and_disposition_filters_combine(self) -> None:
        self.assertEqual(self.keys("--season", "2025", "--all"), ["ncaa:9202", "ncaa:9203", "ncaa:9201"])
        by_org = self.keys("--team", "org:811", "--all")
        self.assertEqual(by_org, ["ncaa:9101", "ncaa:9203", "ncaa:9201"])
        for team in ("Lakefront", "lakefront", "811", "cfbdteam:7811"):
            with self.subTest(team=team):
                self.assertEqual(self.keys("--team", team, "--all"), by_org)
        self.assertEqual(self.keys("--team", "Prairie State", "--all"), self.keys("--team", "Prairie St.", "--all"))
        self.assertEqual(self.keys("--team", "Lakefront", "--season", "2025", "--disposition",
                                   "PROVIDER_CLAIM_SUPPORTED", "--all"), ["ncaa:9201"])
        self.assertEqual(self.keys("--contest", "9104", "--all"), ["ncaa:9104"])
        self.assertEqual(self.keys("--team", "Elsewhere", "--all"), [])
        code, outside, _ = self.site_main("--season", "2023", "--all")
        self.assertEqual((outside["season_scope_state"], outside["total"]), ("OUTSIDE_SITE_EVIDENCE_SCOPE", 0))

    def test_misuse_and_unpinned_readers_refuse(self) -> None:
        alias, v1 = str(self.alias["database"]), str(self.v1["database"])
        site = str(self.sidecar)
        cases = [
            (("--grain", "site-evidence"), "SITE_EVIDENCE_NOT_SELECTED"),
            (("--site-evidence", site, "--reconciliation", alias, "--grain", "parent-reconciliation"),
             "SITE_EVIDENCE_GRAIN_REQUIRED"),
            (("--site-evidence", site, "--grain", "site-evidence"), "SITE_EVIDENCE_PREDECESSOR_REQUIRED"),
            (("--site-evidence", site, "--reconciliation", v1, "--grain", "site-evidence"),
             "SITE_EVIDENCE_PREDECESSOR_MISMATCH"),
            (("--site-evidence", site, "--reconciliation", alias, "--grain", "site-evidence", "--require-pit"),
             "PIT_ELIGIBILITY_NOT_ESTABLISHED"),
            (("--site-evidence", site, "--reconciliation", alias, "--grain", "site-evidence", "--disposition", "X"),
             "DISPOSITION_UNKNOWN"),
            (("--site-evidence", site, "--reconciliation", alias, "--grain", "site-evidence", "--division", "FBS"),
             "FILTER_NOT_APPLICABLE"),
            (("--site-evidence", "\\\\.\\C49NoSuchDevice\\x.sqlite", "--reconciliation", alias, "--grain",
              "site-evidence"), "DATABASE_LOCATION_UNSUPPORTED"),
            (("--site-evidence", str(self.work / "absent" / fx.POPULATION / "sha256" / ("0" * 64) / fx.DB_NAME),
              "--reconciliation", alias, "--grain", "site-evidence"), "SITE_EVIDENCE_DATABASE_MISSING"),
            (("--site-evidence", site, "--reconciliation", alias, "--grain", "site-evidence",
              "--expect-site-evidence-identity", "0" * 64), "STALE_SITE_EVIDENCE_IDENTITY"),
            (("--reconciliation", alias, "--grain", "parent-reconciliation", "--expect-site-evidence-identity",
              "0" * 64), "SITE_EVIDENCE_NOT_SELECTED"),
            (("--grain", "contest", "--site-evidence-manifest", "x.json"), "SITE_EVIDENCE_NOT_SELECTED"),
        ]
        if not WINDOWS:
            cases = [c for c in cases if "C49NoSuchDevice" not in " ".join(c[0])]
        for argv, refusal in cases:
            with self.subTest(refusal=refusal):
                self.assertEqual(self.refusal(*argv), refusal)
        self.assertEqual(self._unpinned(site, alias), "SITE_EVIDENCE_NOT_PINNED")

    def _unpinned(self, site: str, alias: str) -> str:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(query, "SITE_EVIDENCE_ANCHORS", None), \
                mock.patch.object(query, "ALIAS_ANCHORS", self.alias["anchors"]), \
                mock.patch.object(query, "RECONCILIATION_ANCHORS", self.v1["anchors"]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = query.main(["--database", str(self.parent_db), "--site-evidence", site, "--reconciliation", alias,
                               "--grain", "site-evidence"])
        self.assertEqual((code, out.getvalue()), (2, ""))
        return json.loads(err.getvalue().strip().splitlines()[-1])["refused"]

    def test_predecessor_views_and_defaults_are_unchanged(self) -> None:
        for argv in (("--grain", "contest", "--all"), ("--grain", "orientation", "--all"),
                     ("--reconciliation", str(self.alias["database"]), "--grain", "parent-reconciliation", "--all"),
                     ("--reconciliation", str(self.v1["database"]), "--grain", "provider-reconciliation", "--all")):
            with self.subTest(argv=argv):
                code, with_sidecar, err = self.run_main(*argv)
                self.assertEqual(code, 0, err)
                code, unpinned, _ = self.run_main(*argv, anchors={})
                self.assertEqual(with_sidecar, unpinned)
                self.assertNotIn("site_evidence_identity", json.dumps(with_sidecar))

    def test_the_sidecar_connection_is_read_only(self) -> None:
        with self.open() as handle:
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("DELETE FROM site_evidence")

    def test_short_and_long_extended_locations_serve_the_same_rows(self) -> None:
        if not WINDOWS:
            self.skipTest("extended-length spellings are Windows locations")
        holder = tempfile.TemporaryDirectory()
        tmp = os.path.realpath(holder.name)
        try:
            far_root = long_root(tmp)
            for kind in ("canonical", "manifests"):
                for identity in (self.sidecar.parent.name, self.pins["bundle_identity"]):
                    source = self.base / kind / fx.POPULATION / "sha256" / identity
                    for name in os.listdir(source):
                        target = native(os.path.join(far_root, kind, fx.POPULATION, "sha256", identity, name))
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        shutil.copyfile(source / name, target)
            far = native(os.path.join(far_root, "canonical", fx.POPULATION, "sha256", self.sidecar.parent.name,
                                      fx.DB_NAME))
            self.assertGreater(len(far), 300)
            with self.open() as near, self.open(Path(far)) as distant:
                self.assertEqual(near.records, distant.records)
            code, result, err = self.site_main("--all", sidecar=Path(far))
            self.assertEqual(code, 0, err)
            self.assertEqual(result["content_identity"], self.built["content_identity"])
        finally:
            shutil.rmtree(native(tmp))
            holder.cleanup()


class DeterminismTests(Fixture):
    def test_orders_chunks_and_a_resumed_build_give_identical_bytes(self) -> None:
        reference = (self.built["content_identity"], self.built["database_sha256"])
        work = self.work
        variants = [("reverse", ["--input-order", "reverse"]), ("shuffle", ["--input-order", "shuffle:49"]),
                    ("chunk2", ["--chunk-size", "2", "--checkpoint-dir", str(work / "ck2")]),
                    ("chunk5", ["--chunk-size", "5", "--checkpoint-dir", str(work / "ck5")])]
        for name, extra in variants:
            with self.subTest(variant=name):
                code, built, err = self.build(self.contract, work / f"v-{name}", *extra)
                self.assertEqual(code, 0, err)
                self.assertEqual((built["content_identity"], built["database_sha256"]), reference)
        checkpoint = work / "ck3"
        code, first, _ = self.build(self.contract, work / "v-resume", "--chunk-size", "3", "--checkpoint-dir",
                                    str(checkpoint), "--stop-after-chunks", "2")
        self.assertEqual((code, first["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        code, resumed, err = self.build(self.contract, work / "v-resume", "--chunk-size", "3", "--checkpoint-dir",
                                        str(checkpoint), "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual((resumed["content_identity"], resumed["database_sha256"]), reference)

    def test_materialization_is_create_only(self) -> None:
        code, again, err = self.build(self.contract, self.base)
        self.assertEqual((code, again.get("state"), again.get("database", {}).get("state"),
                          again.get("evidence", {}).get("state")),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"), err)
        collide = self.work / "collide"
        shutil.copytree(self.base / "canonical" / fx.POPULATION, collide / "canonical" / fx.POPULATION)
        target = collide / "canonical" / fx.POPULATION / "sha256" / self.built["content_identity"] / "summary.json"
        target.write_bytes(target.read_bytes() + b" ")
        code, _b, err = self.build(self.contract, collide)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED_IMMUTABLE_COLLISION", err)

    def test_a_contract_with_other_rules_universe_or_predecessor_is_refused(self) -> None:
        for name, change, refusal in (
                ("parameters", lambda c: c["parameters"].update(ncaa_hosts=["example.org"]), "CONTRACT_INVALID"),
                ("labels", lambda c: c["labels"].update(pit_eligibility="PIT"), "CONTRACT_INVALID"),
                ("predecessor", lambda c: c["predecessor"].update(contract_sha256="9" * 64), "CONTRACT_INVALID"),
                ("universe", lambda c: (c["universe"]["keys"].pop(), c.update(content_scope=query.site_scope(
                    {"universe": c["universe"]}))), "SITE_EVIDENCE_UNIVERSE_MISMATCH")):
            with self.subTest(change=name):
                bad = json.loads(self.contract.read_text(encoding="utf-8"))
                change(bad)
                path = self.work / f"bad-{name}.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                code, _b, err = self.build(path, self.work / f"v-bad-{name}")
                self.assertEqual(code, 2)
                self.assertIn(refusal, err)


class ContractPinTests(unittest.TestCase):
    """The reader pins the committed site-evidence contract once it exists; until then no sidecar is served."""

    def test_the_reader_pins_the_committed_contract_or_nothing(self) -> None:
        if not CONTRACT.is_file():
            self.assertIsNone(query.SITE_EVIDENCE_ANCHORS)
            return
        raw = CONTRACT.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        anchors = query.SITE_EVIDENCE_ANCHORS
        self.assertEqual(anchors["contract_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(anchors["contract_id"], contract["contract_id"])
        self.assertEqual(anchors["predecessor"], contract["predecessor"])
        self.assertEqual(anchors["universe"], contract["universe"])
        self.assertEqual(anchors["evidence"], contract["evidence"])
        self.assertEqual(anchors["predecessor"]["contract_sha256"], query.ALIAS_ANCHORS["contract_sha256"])
        self.assertEqual(contract["parameters"], query.SITE_PARAMETERS)
        self.assertEqual(contract["labels"], query.SITE_LABELS)


if __name__ == "__main__":
    unittest.main()
