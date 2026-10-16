"""BAT-729 national 2023 game context (Cycle #58 TP58-A01): contract, qualification rules, reference geometry,
calendar intervals, frozen-score strata, determinism, the installed query front and coordinated forgeries.

The world is built once per module by the accepted builders (see ``game_context_fixture``)."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import game_context_fixture as fx  # noqa: E402
from aggie_analytics.game_context import context as gc  # noqa: E402

_STATE: dict = {}


def setUpModule() -> None:
    tmp = tempfile.TemporaryDirectory(prefix="gc-")
    base = Path(tmp.name)
    world = fx.build_world(base / "w")
    anchors_ = fx.anchors_for(world)
    contract_path = fx.write_contract(base / "cc.json", fx.contract_for(world, anchors_))
    anchors = fx.contract_anchors(contract_path)
    code, result, stderr = fx.run_build(contract_path, world, base / "o")
    if code != 0:
        raise AssertionError(f"context build refused: {stderr}")
    db = fx.database_of(result)
    with gc.GameContext(db, data_root=world["data_root"], anchors=anchors) as reader:
        derived = reader.derived
    _STATE.update(tmp=tmp, base=base, world=world, anchors=anchors, contract_path=contract_path, result=result, db=db,
                  derived=derived)


def tearDownModule() -> None:
    _STATE["tmp"].cleanup()


class World(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for key, value in _STATE.items():
            setattr(cls, key, value)

    def serve(self, *argv: str, database: Path | None = None, data_root: Path | None = None
              ) -> tuple[int, dict | None, str | None]:
        code, doc, err = fx.query(self.world, self.anchors, database or self.db, *argv, data_root=data_root)
        return code, doc, fx.refusal(err)

    def contest(self, kind: str) -> dict:
        key = next(k for k, v in self.world["plan"].items() if v == kind)
        return next(c for c in self.derived["contests"] if c["contest_key"] == key)

    def teams_of(self, key: str) -> list[dict]:
        return [t for t in self.derived["teams"] if t["contest_key"] == key]


# --------------------------------------------------------------------------------------------- contract and numerics

class ContractTests(unittest.TestCase):
    def test_the_committed_contract_equals_the_reader_rules_and_is_pinned(self) -> None:
        raw = fx.CONTRACT_PATH.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        self.assertEqual(gc.canonical_json_bytes(contract["rules"]), gc.canonical_json_bytes(gc.rules_document()))
        self.assertEqual(contract["inputs"], gc.inputs_claim(gc.ANCHORS))
        self.assertEqual(contract["source_clocks"], gc.ANCHORS["source_clocks"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), gc.ANCHORS["contract_sha256"])
        self.assertEqual(len(contract["expected"]["target_keys"]), gc.ANCHORS["expected"]["contests"])
        self.assertEqual(gc.target_keys_sha256(contract["expected"]["target_keys"]),
                         gc.ANCHORS["expected"]["target_keys_sha256"])
        _contract, sha, anchors = fx.builder().load_contract(fx.CONTRACT_PATH)
        self.assertEqual(sha, gc.ANCHORS["contract_sha256"])
        self.assertEqual(anchors, gc.ANCHORS)

    def test_a_contract_with_other_rules_is_refused(self) -> None:
        contract = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        mutations = {
            "bins": lambda c: c["rules"]["strata"]["calendar_bins"].__setitem__(0, ["DAYS_1_6", 0, 6]),
            "radius": lambda c: c["rules"]["distance"].__setitem__("radius_m", "6371000"),
            "labels": lambda c: c["rules"]["labels"].__setitem__("pit_eligibility", "PIT_ADMITTED"),
            "payloads": lambda c: c["outputs"]["payloads"].pop(),
            "keys": lambda c: c["expected"]["target_keys"].pop(),
            "inputs": lambda c: c["inputs"]["history"].pop("content_identity"),
        }
        with tempfile.TemporaryDirectory(prefix="gcc-") as tmp:
            for name, mutate in mutations.items():
                changed = copy.deepcopy(contract)
                mutate(changed)
                path = fx.write_contract(Path(tmp) / f"{name}.json", changed)
                with self.subTest(name):
                    with self.assertRaises(Exception) as ctx:
                        fx.builder().load_contract(path)
                    self.assertEqual(getattr(ctx.exception, "code", None), "CONTRACT_INVALID")

    def test_the_gate_and_the_pinned_profile_agree_with_the_contract(self) -> None:
        gate = json.loads((ROOT / "artifacts" / "data_lake" / "national_game_context_2023_gate.json").read_text(
            encoding="utf-8"))
        self.assertEqual(gate["profile"], gc.CONTEXT_PROFILE)
        self.assertEqual(gate["contract_sha256"], gc.ANCHORS["contract_sha256"])
        document = gate["database_identity_document"]
        self.assertEqual(gc.sha256_bytes(gc.canonical_json_bytes(document)), gc.CONTEXT_PROFILE["database_identity"])
        self.assertEqual(gc.sha256_bytes(gc.canonical_json_bytes(gate["content_identity_document"])),
                         gc.CONTEXT_PROFILE["content_identity"])
        self.assertEqual(document["content_identity"], gc.CONTEXT_PROFILE["content_identity"])
        self.assertEqual(gate["content_identity_document"]["rules_sha256"], gc.rules_sha256())
        self.assertEqual(gate["content_identity_document"]["inputs"], gc.inputs_claim(gc.ANCHORS))
        self.assertEqual(gate["labels"], gc.LABELS)

    def test_record_fields_and_layout_are_single_sourced(self) -> None:
        self.assertEqual(gc.DDL, tuple(tuple(d) for d in gc.LAYOUT["database"]["ddl"]))
        self.assertEqual(len(gc.SOURCES), 9)
        self.assertEqual(sum(len(v) for v in gc.FAMILIES.values()) * len(gc.MODEL_IDS), 70)
        self.assertEqual(gc.MARGIN_MODELS, ("PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1",))


class NumericTests(unittest.TestCase):
    @staticmethod
    def vector_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """An independent formulation: unit vectors and atan2(|u x v|, u . v)."""
        def unit(lat: float, lon: float) -> tuple[float, float, float]:
            p, l = math.radians(lat), math.radians(lon)
            return (math.cos(p) * math.cos(l), math.cos(p) * math.sin(l), math.sin(p))
        u, v = unit(lat1, lon1), unit(lat2, lon2)
        cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        return 6371008.8 * math.atan2(math.sqrt(sum(c * c for c in cross)), sum(a * b for a, b in zip(u, v)))

    def test_zero_antimeridian_polar_and_known_controls(self) -> None:
        cases = [((30.0, -97.0), (30.0, -97.0)), ((0.0, 179.9), (0.0, -179.9)), ((89.9, 0.0), (89.9, 180.0)),
                 ((-90.0, 0.0), (90.0, 0.0)), ((53.33523, -6.228447), (41.698378, -86.2339425)),
                 ((21.3, -157.8), (40.0, -105.0)), ((0.0, 0.0), (0.0, 1e-9))]
        for (a, b) in cases:
            with self.subTest(a=a, b=b):
                got = gc.reference_distance_m(*a, *b)
                self.assertIs(type(got), int)
                self.assertLessEqual(abs(got - self.vector_metres(*a, *b)), 0.5 + 1e-3)
                self.assertEqual(got, gc.reference_distance_m(*b, *a))
        self.assertEqual(gc.reference_distance_m(30.0, -97.0, 30.0, -97.0), 0)
        self.assertLess(gc.reference_distance_m(0.0, 179.9, 0.0, -179.9), 25_000)
        self.assertLess(gc.reference_distance_m(89.9, 0.0, 89.9, 180.0), 25_000)

    def test_coordinates_reject_booleans_strings_nonfinite_and_out_of_range(self) -> None:
        for value in (True, False, "30.0", None, float("nan"), float("inf"), 90.0001, -91, [30]):
            with self.subTest(value=value):
                self.assertIsNone(gc._coordinate(value, 90))
        self.assertEqual(gc._coordinate(-90, 90), -90)
        self.assertEqual(gc._coordinate(180.0, 180), 180.0)
        self.assertIsNone(gc._coordinate(180.5, 180))

    def test_date_window_has_exact_bounds_and_infers_no_timezone(self) -> None:
        self.assertEqual(gc.date_state("2023-09-01T10:00:00.000Z", "2023-09-02")[0], "COMPATIBLE_WITH_PARENT_LOCAL_DATE")
        self.assertEqual(gc.date_state("2023-09-01T09:59:59Z", "2023-09-02")[0], "INCOMPATIBLE_WITH_PARENT_LOCAL_DATE")
        self.assertEqual(gc.date_state("2023-09-03T11:59:59.999Z", "2023-09-02")[0],
                         "COMPATIBLE_WITH_PARENT_LOCAL_DATE")
        self.assertEqual(gc.date_state("2023-09-03T12:00:00Z", "2023-09-02")[:2],
                         ("INCOMPATIBLE_WITH_PARENT_LOCAL_DATE", "PROVIDER_START_OUTSIDE_PARENT_DATE_WINDOW"))
        self.assertEqual(gc.date_state("2023-09-03T01:00:00Z", "2023-09-02")[2], 1)
        for bad in ("2023-09-02", "2023-09-02T12:00:00+00:00", 20230902, None, "2023-13-02T12:00:00Z"):
            self.assertEqual(gc.date_state(bad, "2023-09-02")[:2], ("UNSUPPORTED", "PROVIDER_START_MALFORMED"))

    def test_bins_are_closed_and_exhaustive(self) -> None:
        self.assertEqual([gc.calendar_bin(d) for d in (1, 6, 7, 8, 13, 14, 300)],
                         ["DAYS_1_6", "DAYS_1_6", "DAYS_7", "DAYS_8_13", "DAYS_8_13", "DAYS_14_PLUS", "DAYS_14_PLUS"])
        self.assertEqual([gc.distance_bin(m) for m in (0, 499_999, 500_000, 1_499_999, 1_500_000)],
                         ["M_0_499999", "M_0_499999", "M_500000_1499999", "M_500000_1499999", "M_1500000_PLUS"])
        with self.assertRaises(gc.ContextError):
            gc.calendar_bin(0)


# --------------------------------------------------------------------------------------------- the derived world

class QualificationTests(World):
    def test_every_target_and_view_is_served_with_fixed_witness_multiplicity(self) -> None:
        keys = [t["contest_key"] for t in self.world["targets"]]
        self.assertEqual([c["contest_key"] for c in self.derived["contests"]], keys)
        self.assertEqual([(t["contest_key"], t["view"]) for t in self.derived["teams"]],
                         [(k, v) for k in keys for v in "AB"])
        per = {}
        for w in self.derived["witnesses"]:
            per[w["contest_key"]] = per.get(w["contest_key"], 0) + 1
        self.assertEqual(per, {**{k: 15 for k in keys}, None: 3})

    def test_planted_unsupported_and_conflicting_fields_stay_with_reasons(self) -> None:
        absent = self.contest("ABSENT")
        self.assertEqual((absent["provider_join_state"], absent["provider_join_reason"]),
                         ("UNSUPPORTED", "PROVIDER_GAME_ABSENT_FROM_CAPTURE"))
        self.assertEqual((absent["venue_coordinate_state"], absent["max_distance_stratum"]), ("UNSUPPORTED", "UNSUPPORTED"))
        self.assertTrue(all(t["reference_distance_m"] is None and t["distance_reason"] == "VENUE_UNSUPPORTED"
                            for t in self.teams_of(absent["contest_key"])))
        disagree = self.contest("SITE_DISAGREE")
        self.assertEqual((disagree["provider_site_claim"], disagree["site_agreement"]), ("NEUTRAL", "DISAGREE"))
        self.assertNotEqual(disagree["parent_site"], "NEUTRAL")
        self.assertEqual(disagree["site_class"], "NON_NEUTRAL_HOME_AWAY")
        late = self.contest("START_OUTSIDE_WINDOW")
        self.assertEqual((late["provider_date_state"], late["venue_coordinate_reason"]),
                         ("INCOMPATIBLE_WITH_PARENT_LOCAL_DATE", "PROVIDER_DATE_INCOMPATIBLE"))
        off = self.contest("OFF_CAMPUS_HOME")
        home = next(t for t in self.teams_of(off["contest_key"]) if t["parent_role_for_team"] == "HOME")
        self.assertGreater(home["reference_distance_m"], 0)
        self.assertFalse(home["origin_is_game_venue"])
        hotel = [t for t in self.derived["teams"] if t["team_key"] == "org:8"]
        self.assertTrue(hotel and all(t["origin_state"] == "UNSUPPORTED" and t["origin_reason"] ==
                                      "ORIGIN_COORDINATE_INVALID" and t["reference_distance_m"] is None
                                      for t in hotel))

    def test_neutral_sites_never_become_home_and_each_side_uses_its_own_origin(self) -> None:
        neutral = [c for c in self.derived["contests"] if c["parent_site"] == "NEUTRAL"]
        self.assertTrue(neutral)
        for c in neutral:
            teams = self.teams_of(c["contest_key"])
            self.assertEqual({t["parent_role_for_team"] for t in teams}, {"NEUTRAL"})
        for t in self.derived["teams"]:
            if t["origin_state"] == "QUALIFIED_REFERENCE_ORIGIN":
                org = t["team_org_id"]
                self.assertEqual((t["origin_latitude"], t["origin_longitude"]), fx.LOCATIONS[org][1:])
                self.assertEqual(t["cfbd_team_id"], fx.CFBD[org])

    def test_calendar_cold_start_tie_and_strict_earlier_dates(self) -> None:
        echo_first = min((t for t in self.derived["teams"] if t["team_key"] == "org:5"),
                         key=lambda t: t["contest_date"])
        self.assertEqual((echo_first["calendar_state"], echo_first["calendar_interval_days"],
                          echo_first["eligible_prior_count"]), ("NO_ELIGIBLE_SAME_SEASON_PRIOR", None, 0))
        alpha_first = min((t for t in self.derived["teams"] if t["team_key"] == "org:1"),
                          key=lambda t: t["contest_date"])
        self.assertEqual(alpha_first["calendar_state"], "AMBIGUOUS_LATEST_PRIOR")
        self.assertEqual(len(alpha_first["latest_prior_contest_keys"]), 2)
        self.assertIsNone(alpha_first["calendar_interval_days"])
        game = next(c for c in self.derived["contests"] if c["contest_key"] == alpha_first["contest_key"])
        self.assertEqual(game["min_calendar_stratum"], "UNSUPPORTED")
        for t in self.derived["teams"]:
            if t["calendar_state"] == "QUALIFIED_CALENDAR_INTERVAL":
                self.assertLess(t["latest_prior_date"], t["contest_date"])
                self.assertEqual(t["intervening_calendar_days"], t["calendar_interval_days"] - 1)
                self.assertGreaterEqual(t["calendar_interval_days"], 1)

    def test_strata_partition_every_model_once_and_ridge_has_no_probability(self) -> None:
        strata = self.derived["strata"]
        self.assertEqual(len(strata), 70)
        n = len(self.derived["contests"])
        for family in gc.FAMILY_IDS:
            for model in gc.MODEL_IDS:
                rows = [r for r in strata if r["family"] == family and r["model_id"] == model]
                self.assertEqual(sum(r["games"] for r in rows), n, (family, model))
        for r in strata:
            if r["model_id"] in gc.MARGIN_MODELS:
                self.assertFalse(any(k.startswith(("brier", "log_loss")) for k in r))
                self.assertEqual(r["output_kind"], "EXPECTED_MARGIN_ONLY_NO_PROBABILITY")
            else:
                self.assertNotIn("mae", r)
        all_null = next(r for r in strata if r["family"] == "ALL" and r["model_id"] == "NULL_HALF_V1")
        scores = [s for (k, m), (_l, s) in self.derived["scores"].items() if m == "NULL_HALF_V1"]
        total = sum((Fraction(s["brier"]["numerator"], s["brier"]["denominator"]) for s in scores
                     if s["score_state"] == "SCORED"), Fraction(0))
        self.assertEqual(Fraction(all_null["brier_total"]["numerator"], all_null["brier_total"]["denominator"]), total)

    def test_census_counts_match_the_records(self) -> None:
        census = self.derived["census"]
        self.assertEqual(census["contests"], len(self.derived["contests"]))
        self.assertEqual(census["team_states"]["origin_state"].get("UNSUPPORTED"),
                         sum(1 for t in self.derived["teams"] if t["origin_state"] == "UNSUPPORTED"))
        self.assertEqual(census["labels"] if "labels" in census else census["pit_eligibility"], "PIT_NOT_ADMITTED")


class DeterminismTests(World):
    def test_order_chunk_and_resume_variants_reproduce_every_byte(self) -> None:
        identity = self.result["database_identity"]
        for name, extra in (("rev", ("--input-order", "reverse")), ("shf", ("--input-order", "shuffle:5801")),
                            ("c1", ("--chunk-size", "1", "--checkpoint-dir", str(self.base / "ck1"))),
                            ("c17", ("--chunk-size", "17", "--checkpoint-dir", str(self.base / "ck17")))):
            with self.subTest(name):
                code, result, stderr = fx.run_build(self.contract_path, self.world, self.base / name, *extra)
                self.assertEqual(code, 0, stderr)
                self.assertEqual(result["database_identity"], identity)
        resume = ("--chunk-size", "2", "--checkpoint-dir", str(self.base / "ckr"))
        code, result, _err = fx.run_build(self.contract_path, self.world, self.base / "res", *resume,
                                          "--stop-after-chunks", "2")
        self.assertEqual((code, result["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        code, result, stderr = fx.run_build(self.contract_path, self.world, self.base / "res", *resume, "--resume")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(result["database_identity"], identity)
        code, again, _err = fx.run_build(self.contract_path, self.world, self.base / "o")
        self.assertEqual((code, again["state"]), (0, "ALREADY_PRESENT_IDENTICAL"))

    def test_a_differing_existing_identity_is_refused(self) -> None:
        out = self.base / "col"
        code, result, _err = fx.run_build(self.contract_path, self.world, out)
        self.assertEqual(code, 0)
        target = Path(result["database"]["data_dir"]) / gc.DB_FILE
        os.chmod(target, 0o666)
        target.write_bytes(target.read_bytes() + b"x")
        code, _r, stderr = fx.run_build(self.contract_path, self.world, out)
        self.assertEqual((code, fx.refusal(stderr)), (2, "REFUSED_IMMUTABLE_COLLISION"))


# --------------------------------------------------------------------------------------------- the query front

class QueryTests(World):
    def test_grains_selectors_intersections_paging_and_empty_selections(self) -> None:
        n = len(self.derived["contests"])
        code, doc, _r = self.serve("--grain", "contest-context", "--limit", "3", "--offset", "1")
        self.assertEqual((code, doc["total"], doc["returned"], doc["next_offset"]), (0, n, 3, 4))
        code, doc, _r = self.serve("--grain", "team-context", "--team", "org:697", "--orientation", "B", "--all")
        self.assertTrue(doc["rows"] and all(r["team_key"] == "org:697" and r["view"] == "B" for r in doc["rows"]))
        key = self.derived["contests"][0]["contest_key"]
        code, doc, _r = self.serve("--grain", "context-witness", "--contest", key, "--all")
        self.assertEqual(doc["total"], 15)
        code, doc, _r = self.serve("--grain", "context-witness", "--source", "SOURCE_RECEIPT", "--all")
        self.assertEqual(doc["total"], 3)
        code, doc, _r = self.serve("--grain", "context-witness", "--model", "NULL_HALF_V1", "--orientation", "A")
        self.assertEqual(doc["total"], 0)  # disjoint: score witnesses carry no orientation
        code, doc, _r = self.serve("--grain", "context-score-summary", "--family", "SITE")
        self.assertEqual(doc["total"], 15)
        code, doc, _r = self.serve("--grain", "context-score-summary", "--contest", key)
        self.assertEqual((doc["summary_selection"]["selected_games"], doc["total"]), (1, 4 * 5))
        for unknown in (("--contest", "ncaa:1"), ("--team", "org:999999")):
            for grain in gc.GRAINS:
                with self.subTest(grain=grain, unknown=unknown):
                    code, doc, _r = self.serve("--grain", grain, *unknown)
                    self.assertEqual((code, doc["total"], doc["rows"]), (0, 0, []))
        code, doc, _r = self.serve("--grain", "contest-context", "--season", "2022")
        self.assertEqual((doc["season_scope_state"], doc["total"]), ("SEASON_NOT_YET_AUDITED", 0))
        code, doc, _r = self.serve("--grain", "contest-context", "--season", "2023", "--all")
        self.assertEqual(doc["total"], n)

    def test_misuse_is_refused_before_any_file_is_read(self) -> None:
        missing = self.base / "nowhere" / "x.sqlite"
        cases = {("--grain", "contest-context", "--orientation", "A"): "FILTER_NOT_APPLICABLE",
                 ("--grain", "team-context", "--orientation", "C"): "ORIENTATION_INVALID",
                 ("--grain", "contest-context", "--source", "VENUE_REFERENCE"): "FILTER_NOT_APPLICABLE",
                 ("--grain", "context-witness", "--source", "WEATHER"): "SOURCE_UNKNOWN",
                 ("--grain", "team-context", "--model", "NULL_HALF_V1"): "FILTER_NOT_APPLICABLE",
                 ("--grain", "context-score-summary", "--model", "CHAMPION"): "MODEL_UNKNOWN",
                 ("--grain", "context-witness", "--family", "ALL"): "FILTER_NOT_APPLICABLE",
                 ("--grain", "context-score-summary", "--family", "TRAVEL"): "FAMILY_UNKNOWN",
                 ("--grain", "contest-context", "--team", "Texas A&M"): "TEAM_INVALID",
                 ("--grain", "contest-context", "--contest", "cfbd:401525434"): "CONTEST_KEY_INVALID",
                 ("--grain", "contest-context", "--season", "2023.0"): "SEASON_INVALID",
                 ("--grain", "contest-context", "--limit", "-1"): "NEGATIVE_LIMIT",
                 ("--grain", "contest-context", "--offset", "x"): "OFFSET_INVALID",
                 ("--grain", "contest-context", "--require-pit"): "CONTEXT_PIT_NOT_ADMITTED",
                 ("--grain", "forecast"): "ARGUMENT_INVALID"}
        for argv, code in cases.items():
            with self.subTest(argv=argv):
                self.assertEqual(self.serve(*argv, database=missing)[2], code)
        self.assertFalse(missing.parent.exists())

    def test_the_release_is_read_only_and_nothing_is_created(self) -> None:
        missing = self.base / "o2" / "canonical" / gc.POPULATION / "sha256" / ("0" * 64) / gc.DB_FILE
        self.assertEqual(self.serve("--grain", "contest-context", database=missing)[2], "CONTEXT_DATABASE_MISSING")
        self.assertFalse(missing.exists())
        before = {p: p.stat().st_mtime_ns for p in Path(self.db).parent.iterdir()}
        self.assertEqual(self.serve("--grain", "contest-context")[0], 0)
        self.assertEqual({p: p.stat().st_mtime_ns for p in Path(self.db).parent.iterdir()}, before)
        unsupported = r"\\server\share\x.sqlite" if os.name == "nt" else None
        if unsupported:
            self.assertEqual(self.serve("--grain", "contest-context", database=Path(unsupported))[2],
                             "DATABASE_LOCATION_UNSUPPORTED")
            self.assertEqual(self.serve("--grain", "contest-context", "--manifest", r"\\server\share\m.json")[2],
                             "CONTEXT_MANIFEST_LOCATION_UNSUPPORTED")

    def test_plain_long_locations_serve_identically(self) -> None:
        """A byte copy of the release and of every pinned input at a plain (non-extended) location beyond the classic
        Windows path limit serves exactly what the original serves (INSTALLED_CONSUMERS 20261016T022654085206Z found
        the plain long database spelling crashing in SQLite's open)."""
        def ext(path: Path | str) -> str:
            text = os.path.abspath(str(path))
            return "\\\\?\\" + text if os.name == "nt" and not text.startswith("\\\\?\\") else text
        tmp = tempfile.mkdtemp(prefix="gcl-")
        try:
            long_root = Path(tmp).joinpath(*[f"long-native-location-component-{c}-" + c * 40 for c in "abcd"])
            identity = Path(self.db).parent.name
            pop_root = Path(self.db).parent.parent.parent
            copies = {Path(self.db): long_root / "canonical" / gc.POPULATION / "sha256" / identity / gc.DB_FILE,
                      pop_root.parent.parent / "manifests" / gc.POPULATION / "sha256" / identity / "run_manifest.json":
                      long_root / "manifests" / gc.POPULATION / "sha256" / identity / "run_manifest.json"}
            for name in gc.INPUT_NAMES:
                rel = Path(*self.anchors["inputs"][name]["relative_path"].split("/"))
                copies[Path(self.world["data_root"]) / rel] = long_root / "data" / rel
            for source, target in copies.items():
                os.makedirs(ext(target.parent), exist_ok=True)
                with open(ext(target), "xb") as handle:
                    handle.write(Path(source).read_bytes())
            long_db = copies[Path(self.db)]
            self.assertGreater(len(str(long_db)), 300)
            for argv in (("--grain", "contest-context", "--all"), ("--grain", "context-score-summary", "--all")):
                with self.subTest(argv=argv):
                    original = self.serve(*argv)
                    rehoused = self.serve(*argv, database=long_db, data_root=long_root / "data")
                    self.assertEqual(original[0], 0)
                    self.assertEqual(rehoused, original)
        finally:
            import shutil  # noqa: PLC0415
            shutil.rmtree(ext(tmp), ignore_errors=True)

    def test_input_tamper_and_missing_inputs_are_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gct-") as tmp:
            root = Path(tmp)
            for name in gc.INPUT_NAMES:
                rel = self.anchors["inputs"][name]["relative_path"]
                target = root / Path(*rel.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((Path(self.world["data_root"]) / Path(*rel.split("/"))).read_bytes())
            self.assertEqual(self.serve("--grain", "contest-context", data_root=root)[0], 0)
            teams = root / Path(*self.anchors["inputs"]["provider_teams"]["relative_path"].split("/"))
            teams.write_bytes(teams.read_bytes().replace(b"30.6101", b"30.6102"))
            self.assertEqual(self.serve("--grain", "contest-context", data_root=root)[2], "CONTEXT_INPUT_TAMPERED")
            teams.unlink()
            self.assertEqual(self.serve("--grain", "contest-context", data_root=root)[2], "CONTEXT_INPUT_MISSING")
        self.assertEqual(self.serve("--grain", "contest-context", data_root=self.base / "no-root")[2],
                         "CONTEXT_DATA_ROOT_MISSING")

    def test_the_module_front_matches_the_function_front(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "BAS_"))}
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src")] + [p for p in env.get("PYTHONPATH", "").split(
            os.pathsep) if p])
        run = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.game_context.query", "--database",
                              str(self.db), "--data-root", str(self.world["data_root"]), "--grain", "contest-context",
                              "--require-pit"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stderr.strip().splitlines()[-1])["refused"], "CONTEXT_PIT_NOT_ADMITTED")
        self.assertIn('bas-game-context-query = "aggie_analytics.game_context.query:main"',
                      (ROOT / "pyproject.toml").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------- coordinated forgeries

class ForgeryTests(World):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.base / "f")
        cls.counter = 0

    def refused(self, path: Path) -> str | None:
        return self.serve("--grain", "contest-context", "--limit", "1", database=path)[2]

    def forge(self, **kwargs) -> Path:
        type(self).counter += 1
        return self.forger.forge(f"f{type(self).counter}", **kwargs)

    @staticmethod
    def first(tables: dict, table: str, **match) -> dict:
        return next(r for r in tables[table] if all(r.get(k) == v for k, v in match.items()))

    def test_collection_forgeries(self) -> None:
        cases = {
            "missing contest": (lambda t: t["contests"].pop(0), "CONTEXT_CONTEST_ROW_MISSING"),
            "extra contest": (lambda t: t["contests"].append({**t["contests"][0], "contest_key": "ncaa:77"}),
                              "CONTEXT_CONTEST_ROW_EXTRA"),
            "duplicate team": (lambda t: t["teams"].insert(1, t["teams"][0]), "CONTEXT_DUPLICATE_ROW"),
            "reordered teams": (lambda t: t["teams"].insert(0, t["teams"].pop(1)), "CONTEXT_ORDER_MISMATCH"),
            "missing witness": (lambda t: t["witnesses"].pop(3), "CONTEXT_WITNESS_ROW_MISSING"),
            "mirror double count": (lambda t: [r.update(games=2 * r["games"]) for r in t["strata"]
                                               if r["family"] == "ALL"], "CONTEXT_MIRROR_DOUBLE_COUNT"),
            "partition broken": (lambda t: t["strata"][1].update(games=t["strata"][1]["games"] + 1),
                                 "CONTEXT_STRATA_PARTITION_INVALID"),
        }
        for name, (mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forge(records=mutate)), code)

    def test_semantic_field_forgeries(self) -> None:
        def team(tables, **match):
            return self.first(tables, "teams", **match)

        a_team = self.derived["teams"][0]
        b_team = self.derived["teams"][1]
        qualified = next(t for t in self.derived["teams"] if t["calendar_state"] == "QUALIFIED_CALENDAR_INTERVAL")
        cases = {
            "participant": (lambda t: t["contests"][0].update(b_key="org:1234"), "CONTEXT_PARTICIPANT_MISMATCH"),
            "date": (lambda t: t["contests"][0].update(contest_date="2023-09-03"), "CONTEXT_DATE_MISMATCH"),
            "site": (lambda t: t["contests"][0].update(parent_site="NEUTRAL"), "CONTEXT_SITE_MISMATCH"),
            "neutral as home": (lambda t: team(t, contest_key=a_team["contest_key"], view="A").update(
                parent_role_for_team="HOME" if a_team["parent_role_for_team"] != "HOME" else "AWAY"),
                                "CONTEXT_SITE_MISMATCH"),
            "borrowed opponent origin": (lambda t: team(t, contest_key=a_team["contest_key"], view="A").update(
                origin_latitude=b_team["origin_latitude"], origin_longitude=b_team["origin_longitude"]),
                                         "CONTEXT_GEOGRAPHY_MISMATCH"),
            "distance": (lambda t: team(t, contest_key=a_team["contest_key"], view="A").update(
                reference_distance_m=(a_team["reference_distance_m"] or 0) + 1), "CONTEXT_DISTANCE_MISMATCH"),
            "integral float distance": (lambda t: team(t, contest_key=qualified["contest_key"],
                                                       view=qualified["view"]).update(
                calendar_interval_days=float(qualified["calendar_interval_days"])), "CONTEXT_CALENDAR_MISMATCH"),
            "omitted reason": (lambda t: next(r for r in t["teams"] if r["origin_reason"]).update(origin_reason=None),
                               "CONTEXT_GEOGRAPHY_MISMATCH"),
            "false observation time": (lambda t: team(t, contest_key=a_team["contest_key"], view="A").update(
                origin_observed_at_utc="2023-08-01T00:00:00Z"), "CONTEXT_SOURCE_CLOCK_MISMATCH"),
            "pit claim": (lambda t: t["contests"][0].update(pit_eligibility="PIT_ADMITTED"), "CONTEXT_PIT_CLAIM_INVALID"),
            "wrong latest prior": (lambda t: team(t, contest_key=qualified["contest_key"],
                                                  view=qualified["view"]).update(
                calendar_interval_days=qualified["calendar_interval_days"] + 7), "CONTEXT_CALENDAR_MISMATCH"),
            "tie resolved by order": (lambda t: next(r for r in t["teams"] if r["calendar_state"] ==
                                                     "AMBIGUOUS_LATEST_PRIOR").update(
                calendar_state="QUALIFIED_CALENDAR_INTERVAL"), "CONTEXT_CALENDAR_MISMATCH"),
            "source locator": (lambda t: t["witnesses"][2].update(locator={**t["witnesses"][2]["locator"],
                                                                         "json_pointer": "/999999"}),
                               "CONTEXT_WITNESS_LOCATOR_MISMATCH"),
            "score metric": (lambda t: next(r for r in t["strata"] if r["metric_kind"] == "PROBABILITY").update(
                brier_total={"numerator": 1, "denominator": 1}), "CONTEXT_SCORE_METRIC_MISMATCH"),
            "model": (lambda t: t["strata"][0].update(model_sha256="0" * 64), "CONTEXT_MODEL_MISMATCH"),
            "ridge probability": (lambda t: next(r for r in t["strata"] if r["model_id"] in gc.MARGIN_MODELS).update(
                brier_mean={"numerator": 1, "denominator": 4}), "CONTEXT_RIDGE_PROBABILITY_INVENTED"),
            "extra member": (lambda t: t["contests"][0].update(home_field_effect=3), "CONTEXT_RECORD_SHAPE_INVALID"),
            "non-string key": (lambda t: t["contests"][0].update(contest_key=3150887), "CONTEXT_RECORD_TYPE_INVALID"),
            "census": (lambda t: t["census"][0].update(contests=1), "CONTEXT_CENSUS_MISMATCH"),
        }
        for name, (mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forge(records=mutate)), code)

    def test_line_meta_identity_and_manifest_forgeries(self) -> None:
        self.assertEqual(self.refused(self.forge(lines=lambda raw: raw["contests"].__setitem__(0, "[1, 2]"))),
                         "CONTEXT_RECORD_TYPE_INVALID")
        self.assertEqual(self.refused(self.forge(meta={"labels": {**gc.LABELS, "pit_eligibility": "PIT_ADMITTED"}})),
                         "CONTEXT_PIT_CLAIM_INVALID")
        self.assertEqual(self.refused(self.forge(meta={"rules": {"distance": "flat earth"}})),
                         "CONTEXT_RULES_CLAIM_INVALID")
        clocks = copy.deepcopy(self.anchors["source_clocks"])
        clocks["provider_teams"]["retrieved_at_utc"] = "2023-08-01T00:00:00Z"
        self.assertEqual(self.refused(self.forge(meta={"source_clocks": clocks})), "CONTEXT_SOURCE_CLOCK_MISMATCH")
        self.assertEqual(self.refused(self.forge(document=lambda d: d["table_counts"].update(
            meta=float(d["table_counts"]["meta"])))), "CONTEXT_IDENTITY_DOCUMENT_MISMATCH")
        self.assertEqual(self.refused(self.forge(document={"provenance": True})), "CONTEXT_IDENTITY_DOCUMENT_MISMATCH")
        self.assertEqual(self.refused(self.forge(identity_override="f" * 64)), "CONTEXT_IDENTITY_MISMATCH")
        self.assertEqual(self.refused(self.forge(manifest_patch={"identity": "e" * 64})), "CONTEXT_IDENTITY_MISMATCH")
        self.assertEqual(self.refused(self.forge(document={"contract_sha256": "a" * 64})), "CONTEXT_CONTRACT_MISMATCH")
        self.assertEqual(self.refused(self.forge(after_blocks=[("UPDATE blocks SET records = records + 1 WHERE ord = 0",
                                                                ())])), "CONTEXT_INDEX_MISMATCH")
        genuine = self.forge()
        self.assertIsNone(self.refused(genuine))
        os.chmod(genuine, 0o666)
        genuine.write_bytes(genuine.read_bytes()[:-1] + b"\x00")
        self.assertEqual(self.refused(genuine), "CONTEXT_DATABASE_TAMPERED")


# --------------------------------------------------------------------------------------------- malformed JSON boundaries

MARKER = "MF58A01-01"
LONE = "JSON_LONE_SURROGATE"
DEEP = "JSON_NESTING_TOO_DEEP"
#: JSON nesting far beyond any interpreter's decoder/encoder depth (raw text; no canonical encoder produces it).
DEEP_ARRAY = "[" * 100_000 + "0" + "]" * 100_000
DEEP_OBJECT = '{"a":' * 100_000 + "0" + "}" * 100_000


class MalformedJsonBoundaryTests(World):
    """MF58A01-01 (TP58 03B controlled malformed-record errors): valid JSON that is malformed data -- an escaped lone
    surrogate or nesting beyond the JSON depth -- in a block record, a meta claim or the run manifest of a coordinated,
    rehashed forgery is refused at the query front by that boundary's own rule (exit 2), never escapes as a traceback;
    genuine Unicode, ordinary malformed fields and the existing rules keep their outcomes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.base / "mj")
        cls.counter = 0

    def outcome(self, **forge) -> str:
        """``exit:refusal:reason`` of the in-process query front over one forgery; an exception escaping the front is
        ``UNCAUGHT:<class>``."""
        type(self).counter += 1
        path = self.forger.forge(f"m{type(self).counter}", **forge)
        try:
            code, _doc, err = fx.query(self.world, self.anchors, path, "--grain", "contest-context", "--limit", "1")
        except (UnicodeEncodeError, RecursionError) as exc:
            return f"UNCAUGHT:{type(exc).__name__}"
        return f"{code}:{fx.refusal(err)}:{next((r for r in (LONE, DEEP) if r in err), '-')}"

    def expect(self, cases: dict[str, tuple[dict, str]]) -> None:
        for name, (forge, want) in cases.items():
            with self.subTest(name):
                got = self.outcome(**forge)
                if got != want:
                    self.fail(f"{MARKER} {name}: {got} != {want}")

    @staticmethod
    def member(table: str, index: int, name: str, text: str):
        """A ``lines`` forgery replacing one member's JSON value text in one canonical record line."""
        def edit(raw: dict) -> None:
            record = json.loads(raw[table][index])
            old = f'"{name}":' + json.dumps(record[name], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if raw[table][index].count(old) != 1:
                raise AssertionError(f"{table}[{index}] has no single member text {old!r}")
            raw[table][index] = raw[table][index].replace(old, f'"{name}":{text}')
        return edit

    def test_lone_surrogates_in_record_members_are_malformed_records(self) -> None:
        want = f"2:CONTEXT_RECORD_MALFORMED:{LONE}"
        self.expect({
            "high surrogate in a team member": ({"lines": self.member("teams", 0, "origin_location_name",
                                                                      '"\\ud800"')}, want),
            "low surrogate in a contest member": ({"lines": self.member("contests", 0, "venue_reference_name",
                                                                        '"Venue \\udfff"')}, want),
            "high surrogate in a stratum member": ({"lines": self.member("strata", 0, "reading", '"\\udbff"')}, want),
            "reversed surrogate pair": ({"lines": self.member("teams", 1, "origin_location_name",
                                                              '"\\ude00\\ud83d"')}, want),
            "lone surrogate as a nested object value": ({"lines": self.member("witnesses", 0, "raw",
                                                                              '{"bad":"\\udfff"}')}, want),
            "lone surrogate as a nested object key": ({"lines": self.member("witnesses", 0, "raw",
                                                                            '{"\\ud800":1}')}, want),
        })

    def test_excessive_record_nesting_is_a_malformed_record(self) -> None:
        want = f"2:CONTEXT_RECORD_MALFORMED:{DEEP}"
        self.expect({
            "array nesting in a team member": ({"lines": self.member("teams", 0, "origin_location_name", DEEP_ARRAY)},
                                               want),
            "object nesting in a witness member": ({"lines": self.member("witnesses", 0, "raw", DEEP_OBJECT)}, want),
            "array nesting in the census record": ({"lines": self.member("census", 0, "contests", DEEP_ARRAY)}, want),
        })

    def test_lone_surrogates_in_meta_claims_are_malformed_meta(self) -> None:
        want = f"2:CONTEXT_META_MALFORMED:{LONE}"
        self.expect({
            "high surrogate in the inputs claim": ({"meta": {"inputs": '{"history":"\\ud800"}'}}, want),
            "low surrogate as a nested source-clock key": ({"meta": {"source_clocks": '{"\\udfff":{"x":1}}'}}, want),
            "high surrogate in the rules claim": ({"meta": {"rules": '{"distance":["\\udbff"]}'}}, want),
        })

    def test_excessive_meta_nesting_is_malformed_meta(self) -> None:
        want = f"2:CONTEXT_META_MALFORMED:{DEEP}"
        self.expect({
            "array nesting in the inputs claim": ({"meta": {"inputs": DEEP_ARRAY}}, want),
            "object nesting in the labels claim": ({"meta": {"labels": DEEP_OBJECT}}, want),
        })

    def test_excessive_manifest_nesting_is_a_malformed_manifest(self) -> None:
        want = f"2:CONTEXT_MANIFEST_MALFORMED:{DEEP}"
        self.expect({
            "identity document member": ({"document": {"extra": "DEEP"},
                                          "document_text": lambda t: t.replace('"DEEP"', DEEP_ARRAY)}, want),
            "manifest member outside the identity document": ({"manifest_patch": {"provenance": "DEEP"},
                                                               "manifest_text": lambda t: t.replace('"DEEP"',
                                                                                                    DEEP_OBJECT)}, want),
        })

    def test_unencodable_record_members_never_escape_the_comparison(self) -> None:
        want_record = self.derived["teams"][0]
        deep: object = 0
        for _ in range(100_000):
            deep = [deep]
        cases = {"lone high surrogate": ("\ud800", LONE), "lone low surrogate as a nested key": ({"\udfff": 1}, LONE),
                 "nesting beyond the canonical encoder": (deep, DEEP)}
        for name, (value, reason) in cases.items():
            with self.subTest(name):
                got = {**want_record, "origin_location_name": value}
                try:
                    gc.GameContext._compare("teams", [("forged line", got)], [gc.canonical_line(want_record)],
                                            [want_record])
                    outcome = "NOT_REFUSED"
                except gc.ContextError as exc:
                    outcome = f"{exc.code}:{reason if reason in str(exc) else '-'}"
                except (UnicodeEncodeError, RecursionError) as exc:
                    outcome = f"UNCAUGHT:{type(exc).__name__}"
                if outcome != f"CONTEXT_RECORD_MALFORMED:{reason}":
                    self.fail(f"{MARKER} {name}: {outcome}")

    def test_genuine_unicode_and_ordinary_malformed_data_keep_their_rules(self) -> None:
        geography = "2:CONTEXT_GEOGRAPHY_MISMATCH:-"
        nested = "[" * 64 + '"x"' + "]" * 64
        self.expect({
            "ordinary wrong text": ({"lines": self.member("teams", 0, "origin_location_name", '"INVENTED_NAME"')},
                                    geography),
            "genuine BMP text": ({"lines": self.member("teams", 0, "origin_location_name", '"São José"')},
                                 geography),
            "genuine non-BMP text": ({"lines": self.member("teams", 0, "origin_location_name",
                                                           '"Honolulu \U0001F33A"')}, geography),
            "non-BMP text as an escaped surrogate pair": ({"lines": self.member("teams", 0, "origin_location_name",
                                                                                '"Honolulu \\ud83c\\udf3a"')},
                                                          geography),
            "moderate nesting": ({"lines": self.member("teams", 0, "origin_location_name", nested)}, geography),
            "non-JSON line": ({"lines": lambda raw: raw["teams"].__setitem__(0, "{not json")},
                              "2:CONTEXT_RECORD_TYPE_INVALID:-"),
            "lone surrogate in an identity member": ({"lines": self.member("contests", 1, "contest_key",
                                                                           '"ncaa:1\\ud800"')},
                                                     "2:CONTEXT_CONTEST_ROW_MISSING:-"),
            "lone surrogate in the census line": ({"lines": self.member("census", 0, "contests", '"\\udfff"')},
                                                  "2:CONTEXT_CENSUS_MISMATCH:-"),
            "lone surrogate in the labels claim": ({"meta": {"labels": gc.canonical_line(gc.LABELS).replace(
                '"PIT_NOT_ADMITTED"', '"PIT\\ud800"')}}, "2:CONTEXT_PIT_CLAIM_INVALID:-"),
            "lone surrogate as the content identity": ({"meta": {"content_identity": '"\\ud800"'}},
                                                       "2:CONTEXT_CONTENT_IDENTITY_MISMATCH:-"),
            "lone surrogate in the identity document": ({"document": {"extra": "LONE"},
                                                         "document_text": lambda t: t.replace('"LONE"',
                                                                                              '"\\ud800"')},
                                                        "2:CONTEXT_MANIFEST_MALFORMED:-"),
            "genuine rehashed release": ({}, "0:None:-"),
        })


# --------------------------------------------------------------------------------------------- the genuine release

class MountedGenuineContextTests(unittest.TestCase):
    def test_genuine_context_serves_every_accepted_target(self) -> None:
        profile = gc.CONTEXT_PROFILE
        data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        if profile is None or not data_root or not Path(data_root).is_dir():
            self.skipTest("no pinned canonical context profile or no mounted data root")
        db = Path(data_root) / "canonical" / gc.POPULATION / "sha256" / profile["database_identity"] / gc.DB_FILE
        if not db.is_file():
            self.skipTest("the pinned canonical context is not present under the mounted data root")
        with gc.GameContext(db, data_root=Path(data_root), expect_identity=profile["database_identity"]) as reader:
            self.assertEqual(reader.content_identity, profile["content_identity"])
            census = reader.derived["census"]
            self.assertEqual((census["contests"], census["team_views"], census["witnesses"], census["strata_rows"]),
                             (profile["contests"], profile["team_views"], profile["witnesses"], profile["strata_rows"]))
            answer = reader.query("context-score-summary", family="ALL", all_rows=True)
            self.assertEqual(sum(r["games"] for r in answer["rows"]), 5 * profile["contests"])


if __name__ == "__main__":
    unittest.main()
