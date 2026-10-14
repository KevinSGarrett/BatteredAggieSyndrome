"""BAT-423 bounded research contribution (Cycle #56 — Attempt #1, TP56-A01): the national retrospective reference
comparison on tiny owned worlds.

Every world is real (``retrospective_reference_fixture``): an accepted-builder parent, history prefix and C47
benchmark, then the repository reference builder with the committed research contract whose parent bindings name those
fixtures. The world holds training seasons 2021-2022 and the comparison season 2023, FCS and outside-division priors,
a non-NCAA excluded input, an FBS tie target, an FCS prior-pool tie, cold starts, same-date games, a neutral site, a
mid-season rename, Texas A&M (org:697) in every season, the 2020-21 academic year with spring games and protected
2024/2025 rows. Forgeries are coordinated -- block bytes, index columns, table counts, identity document, identity
directory and manifest are rewritten consistently -- so each must be refused by its own rule, never by a stale hash.

Cycle #56 continuation C56-CONT-01 adds the issued consumer behaviour the reviewed head missed: summary selection by
--team and --contest over the selected canonical games (MF56A01-01, compared with this module's own computation),
malformed governed record shapes refused for their own cause instead of escaping the refusal boundary (MF56A01-02), and
an explicit --manifest validated by the literal local-file policy before any filesystem access (MF56A01-03; network and
device spellings are never accessed: access sentinels refuse them, with native Windows and POSIX expectations).
"""
from __future__ import annotations

import builtins
import contextlib
import copy
import io
import json
import math
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import national_history_fixture as hx  # noqa: E402
import retrospective_reference_fixture as fx  # noqa: E402
from aggie_analytics.data import national_di_population as pop  # noqa: E402
from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402
from aggie_analytics.retrospective_baseline import query  # noqa: E402
from aggie_analytics.retrospective_baseline import reference as rc  # noqa: E402
from aggie_analytics.retrospective_baseline import reference_fit as rf  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
NEW_MODELS = (rc.MODEL_ELO, rc.MODEL_LOGISTIC, rc.MODEL_RIDGE)


def frac(value: dict) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


#: C56-CONT-01 (MF56A01-03): the host and device names an explicit --manifest must never be opened through.
SENTINEL_HOST = "bas-c56-sentinel-host"
SENTINEL_TOKENS = (SENTINEL_HOST, "\\\\.\\nul", "\\\\.\\pipe\\", "\\\\?\\globalroot\\", "\\\\?\\volume{",
                   "dot.\\run_manifest")


def manifest_refusal_expected(kind: str, os_name: str) -> str:
    """The refusal an explicit --manifest spelling of ``kind`` gets on a platform. On Windows a network share, device or
    other namespace spelling ("unsupported") and a non-literal extended spelling ("not_literal") are refused lexically
    before any access; on POSIX the same characters name an ordinary local (relative) path, which does not exist."""
    if os_name == "nt":
        return {"unsupported": "REFERENCE_MANIFEST_LOCATION_UNSUPPORTED",
                "not_literal": "REFERENCE_MANIFEST_LOCATION_NOT_LITERAL"}[kind]
    return "REFERENCE_MANIFEST_MISSING"


class ProhibitedAccess(BaseException):
    """Raised by the access sentinels instead of a filesystem or network operation on a prohibited spelling (never an
    OSError, so no reader handler can turn it into a refusal)."""


@contextlib.contextmanager
def access_sentinels(tokens: tuple[str, ...]):
    """Every filesystem, SQLite and network entry point the reader can reach refuses (records and raises) a path, URI or
    host holding one of ``tokens`` (casefolded, separators normalized); every other call passes through unchanged."""
    hits: list[str] = []
    folded = tuple(t.replace("/", "\\").casefold() for t in tokens)

    def prohibited(value: object) -> bool:
        if isinstance(value, (tuple, list)):
            return any(prohibited(v) for v in value)
        try:
            text = os.fsdecode(os.fspath(value))
        except TypeError:
            return False
        return any(t in text.replace("/", "\\").casefold() for t in folded)

    def wrap(name: str, func):
        def guarded(*args, **kwargs):
            for value in (*args[:2], *kwargs.values()):
                if prohibited(value):
                    hits.append(f"{name}({value!r})")
                    raise ProhibitedAccess(f"{name} reached {value!r}")
            return func(*args, **kwargs)
        return guarded
    targets = [(os, "stat"), (os, "lstat"), (os, "open"), (os, "scandir"), (os, "listdir"), (os.path, "exists"),
               (os.path, "isfile"), (os.path, "isdir"), (os.path, "realpath"), (builtins, "open"), (io, "open"),
               (sqlite3, "connect"), (socket, "getaddrinfo"), (socket, "create_connection")]
    with contextlib.ExitStack() as stack:
        for module, name in targets:
            stack.enter_context(mock.patch.object(module, name, wrap(f"{module.__name__}.{name}",
                                                                     getattr(module, name))))
        stack.enter_context(mock.patch.object(socket.socket, "connect", wrap("socket.connect",
                                                                              socket.socket.connect)))
        yield hits


class World(unittest.TestCase):
    """One accepted fixture world, its C47 benchmark and its reference, built once per class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="rr-")
        cls.tmp = Path(cls._tmp.name)
        cls.world = fx.build_world(cls.tmp / "w")
        cls.contract_path = fx.write_contract(cls.tmp / "rc.json", fx.contract_for(cls.world))
        cls.anchors = fx.anchors_for(cls.contract_path, cls.world)
        code, cls.result, stderr = fx.run_build(cls.contract_path, cls.world, cls.tmp / "o")
        if code != 0:
            raise AssertionError(f"reference build refused: {stderr}")
        cls.db = fx.database_of(cls.result)
        with rc.ReferenceComparison(cls.db, history_database=cls.world["history_db"],
                                    population_database=cls.world["parent"]["database"], anchors=cls.anchors) as ref:
            cls.derived = ref.derived

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def serve(self, *argv: str, database: Path | None = None) -> tuple[int, dict | None, str | None]:
        code, doc, err = fx.query(self.world, self.anchors, database or self.db, *argv)
        return code, doc, fx.refusal(err)

    def inputs(self) -> dict:
        return rc.load_inputs(self.world["history_db"], self.world["parent"]["database"], self.anchors)

    def estimate(self, key: str, model: str, orientation: str = "A") -> dict:
        return next(r for r in self.derived["estimates"] if (r["contest_key"], r["model_id"], r["orientation"]) ==
                    (key, model, orientation))


# --------------------------------------------------------------------------------------------- contract

class ContractTests(unittest.TestCase):
    def test_the_committed_contract_equals_the_reader_rules_and_is_pinned(self) -> None:
        contract, sha, anchors = fx.builder().load_contract(fx.CONTRACT_PATH)
        self.assertEqual(sha, rc.ANCHORS["contract_sha256"])
        self.assertEqual(anchors, rc.ANCHORS)
        self.assertEqual(sorted(contract["models"]), sorted(rc.MODEL_IDS))
        self.assertEqual(contract["models"][rc.MODEL_NULL], bm.MODELS[rc.MODEL_NULL])
        self.assertEqual(contract["models"][rc.MODEL_SMOOTHED], bm.MODELS[rc.MODEL_SMOOTHED])
        self.assertEqual(contract["parent"]["expected"], {"targets": 5875, "views": 11750, "pool": 11528,
                                                          "training_targets": 5087, "comparison_targets": 788})
        self.assertEqual(contract["parent"]["benchmark"]["database_identity"],
                         "627b25af33e6d920bce5612f5e9b9c411ce4b2a792e6ff9d53ab04cc7e5521a1")
        self.assertEqual(contract["elo"]["k_factor"], 20)
        self.assertEqual(len(contract["design_columns"]), 10)

    def test_a_contract_with_other_rules_is_refused(self) -> None:
        base = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="rk-") as tmp:
            for name, mutate in (
                    ("elo_k", lambda c: c["elo"].update(k_factor=32)),
                    ("elo_site", lambda c: c["elo"].update(site_bonus=65)),
                    ("lambda", lambda c: c["models"][rc.MODEL_LOGISTIC].update(objective="sum")),
                    ("columns", lambda c: c["design_columns"].pop()),
                    ("fit_seasons", lambda c: c["models"][rc.MODEL_RIDGE]["fit_seasons"].append(2023)),
                    ("c47_formula", lambda c: c["models"][rc.MODEL_SMOOTHED].update(parameters={"pseudo_wins": 2})),
                    ("numeric", lambda c: c["numeric_contract"].update(independent_tolerance="1e-6")),
                    ("slices", lambda c: c["slices"].update(FIRST_FOUR_TEAM_GAMES="both sides")),
                    ("labels", lambda c: c["labels"].update(pit_eligibility="PIT_ELIGIBLE")),
                    ("scope", lambda c: c["scope"].update(training_seasons=list(range(2016, 2024)))),
                    ("split", lambda c: c["split"]["partitions"][0]["seasons"].append(2024)),
                    ("payloads", lambda c: c["outputs"]["payloads"].pop()),
                    ("benchmark_contract", lambda c: c["parent"]["benchmark"].update(contract_sha256="0" * 64)),
                    ("expected", lambda c: c["parent"].update(expected={"targets": 5875.0})),
                    ("contract_id", lambda c: c.update(contract_id="BAT-423-OTHER"))):
                contract = copy.deepcopy(base)
                mutate(contract)
                path = fx.write_contract(Path(tmp) / f"{name}.json", contract)
                with self.subTest(name), self.assertRaises(Exception) as caught:
                    fx.builder().load_contract(path)
                self.assertEqual(getattr(caught.exception, "code", None), "CONTRACT_INVALID")


# --------------------------------------------------------------------------------------------- numerics and fits

class NumericTests(unittest.TestCase):
    def test_decimal12_rounding_complement_negation_and_negative_zero(self) -> None:
        for value in (0.1, 0.5, 1.0 / 3.0, 2.0 / 3.0, 1500.123456789012345, -3.25, 1e-13, -1e-13, 0.9999999999995):
            with self.subTest(value):
                expected = Decimal(value).quantize(Decimal("1e-12"), rounding="ROUND_HALF_EVEN")
                text = rc.dec12(value)
                self.assertEqual(Decimal(text), expected)
                self.assertRegex(text, rc.DEC12_RE)
                self.assertFalse(text.startswith("-0.000000000000"))
        self.assertEqual(rc.dec12(-0.0), "0.000000000000")
        self.assertEqual(rc.dec_complement("0.123456789012"), "0.876543210988")
        self.assertEqual(rc.dec_complement("1.000000000000"), "0.000000000000")
        self.assertEqual(rc.dec_negation("0.000000000000"), "0.000000000000")
        self.assertEqual(rc.dec_negation("-2.500000000000"), "2.500000000000")
        for bad in (float("nan"), float("inf"), 1):
            with self.subTest(bad=bad), self.assertRaises(rc.ReferenceError) as caught:
                rc.dec12(bad)
            self.assertEqual(caught.exception.code, "REFERENCE_NONFINITE_VALUE")

    def test_stable_sigmoid_and_cross_entropy(self) -> None:
        self.assertEqual(rf.sigmoid(1000.0), 1.0)
        self.assertEqual(rf.sigmoid(-1000.0), 0.0)
        self.assertAlmostEqual(rf.sigmoid(0.0), 0.5)
        self.assertTrue(math.isfinite(rf.bce(-800.0, 1.0)) and math.isfinite(rf.bce(800.0, 0.0)))
        self.assertAlmostEqual(rf.bce(0.3, 1.0), -math.log(rf.sigmoid(0.3)), places=15)
        self.assertAlmostEqual(rf.bce(0.3, 0.0), -math.log(1.0 - rf.sigmoid(0.3)), places=15)

    @staticmethod
    def paired(points: list[tuple[tuple[float, ...], float]], margin: bool = False) -> list[rf.Row]:
        rows = []
        for z, y in points:
            rows.append(rf.Row(z, y, 0.5))
            rows.append(rf.Row(tuple(-v for v in z), (-y) if margin else 1.0 - y, 0.5))
        return rows

    def test_logistic_fit_reaches_the_frozen_objective_optimum(self) -> None:
        points = [((1.0, 0.5, 0.0), 1.0), ((-0.4, 1.2, 0.0), 0.0), ((0.8, -1.5, 0.0), 1.0), ((-1.1, -0.2, 0.0), 0.0),
                  ((0.3, 0.9, 0.0), 0.0), ((2.0, 0.1, 0.0), 1.0)]
        rows = self.paired(points)
        fit = rf.fit_logistic(rows, 3)
        self.assertEqual(fit.state, "CONVERGED")
        self.assertLessEqual(fit.gradient_inf_norm, 1e-10)
        self.assertEqual(fit.coefficients[2], 0.0)           # an all-zero column stays exactly zero under the penalty
        total = math.fsum(r.weight for r in rows)
        self.assertEqual(total, float(len(points)))          # one canonical game has weight one
        best = rf.logistic_objective(rows, fit.coefficients, total, 1.0)
        for j in range(2):
            for step in (1e-5, -1e-5):
                moved = list(fit.coefficients)
                moved[j] += step
                self.assertGreater(rf.logistic_objective(rows, moved, total, 1.0), best)
        # the paired objective equals the canonical-orientation objective with weight one (zero intercept symmetry)
        canonical = [rf.Row(z, y, 1.0) for z, y in points]
        self.assertAlmostEqual(rf.logistic_objective(canonical, fit.coefficients, float(len(points)), 1.0), best,
                               places=14)

    def test_logistic_fit_failures_are_recorded_never_accepted(self) -> None:
        rows = self.paired([((1.0, 0.5), 1.0), ((-0.4, 1.2), 0.0)])
        with self.assertRaises(rf.ReferenceFitError) as caught:
            rf.fit_logistic(rows, 2, max_steps=0)
        self.assertEqual(caught.exception.code, "FIT_NOT_CONVERGED")
        self.assertEqual(len(caught.exception.record["trajectory"]), 1)
        calls = {"n": 0}
        real = rf.logistic_objective

        def increasing(*args, **kwargs):
            calls["n"] += 1
            return real(*args, **kwargs) + calls["n"]     # every candidate looks worse than the current point
        with mock.patch.object(rf, "logistic_objective", increasing), self.assertRaises(rf.ReferenceFitError) as caught:
            rf.fit_logistic(rows, 2)
        self.assertEqual(caught.exception.code, "FIT_BACKTRACK_EXHAUSTED")
        self.assertEqual(caught.exception.record["trajectory"][-1]["halvings"], 30)
        for bad_rows, code in (([], "FIT_EMPTY"), ([rf.Row((float("nan"), 1.0), 1.0, 0.5)], "FIT_NONFINITE_INPUT"),
                               ([rf.Row((1.0,), 1.0, 0.5)], "FIT_RAGGED")):
            with self.subTest(code), self.assertRaises(rf.ReferenceFitError) as caught:
                rf.fit_logistic(bad_rows, 2)
            self.assertEqual(caught.exception.code, code)

    def test_backtracking_halves_until_the_objective_does_not_increase(self) -> None:
        rows = self.paired([((1.0, 0.5), 1.0), ((-0.4, 1.2), 0.0), ((0.7, -0.3), 1.0)])
        real = rf.logistic_objective
        state = {"first_candidate": True}

        def once(rows_, beta, total, lam):
            value = real(rows_, beta, total, lam)
            if any(b != 0.0 for b in beta) and state["first_candidate"]:
                state["first_candidate"] = False
                return value + 10.0                   # the full first step is rejected once
            return value
        with mock.patch.object(rf, "logistic_objective", once):
            fit = rf.fit_logistic(rows, 2)
        self.assertEqual(fit.trajectory[0]["halvings"], 1)
        self.assertEqual(fit.trajectory[0]["step_scale"], repr(0.5))
        self.assertEqual(fit.state, "CONVERGED")

    def test_ridge_solves_the_regularized_normal_equations(self) -> None:
        points = [((1.0,), 7.0), ((-0.5,), -3.0), ((2.0,), 10.0), ((0.25,), 0.0)]
        rows = self.paired(points, margin=True)
        fit = rf.fit_ridge(rows, 1)
        zz = math.fsum(z[0] * z[0] for z, _m in points) / len(points)
        zm = math.fsum(z[0] * m for z, m in points) / len(points)
        self.assertAlmostEqual(fit.coefficients[0], zm / (zz + 1.0), places=14)
        self.assertLessEqual(fit.residual_inf_norm, 1e-8)
        with mock.patch.object(rf, "solve", lambda a, b: [float("nan")]), self.assertRaises(rf.ReferenceFitError) as c:
            rf.fit_ridge(rows, 1)
        self.assertEqual(c.exception.code, "FIT_NONFINITE")


# --------------------------------------------------------------------------------------------- features and Elo

def pool_row(key: str, season: int, date: str, a: str, b: str, a_pts: int, b_pts: int) -> dict:
    return {"contest_key": key, "season": season, "contest_date": date, "a_key": a, "b_key": b, "a_points": a_pts,
            "b_points": b_pts, "a_team_name": a.upper(), "b_team_name": b.upper(), "a_division_label": "FBS",
            "b_division_label": "FBS"}


class EloAndPriorTests(unittest.TestCase):
    def test_same_date_games_use_start_of_date_ratings_and_updates_apply_after(self) -> None:
        pool = {r["contest_key"]: r for r in (
            pool_row("k1", 2021, "2021-09-01", "A", "B", 30, 10),
            pool_row("k2", 2021, "2021-09-08", "A", "C", 20, 21),
            pool_row("k3", 2021, "2021-09-08", "B", "D", 14, 14),
            pool_row("k4", 2021, "2021-09-15", "C", "D", 7, 3))}
        targets = [{"contest_key": k, "season": 2021, "contest_date": pool[k]["contest_date"], "a_key": pool[k]["a_key"],
                    "b_key": pool[k]["b_key"]} for k in ("k2", "k3", "k4")]
        elo = rc.derive_elo(pool, targets)
        after_d1 = 1500.0 + 20.0 * (1.0 - rc.elo_expected(1500.0, 1500.0))
        self.assertEqual(elo["targets"]["k2"]["a_rating"], after_d1)                  # A after day 1 only
        self.assertEqual(elo["targets"]["k3"]["a_rating"], 1500.0 - (after_d1 - 1500.0))  # B after day 1 only
        self.assertEqual((elo["targets"]["k2"]["b_rating"], elo["targets"]["k3"]["b_rating"]), (1500.0, 1500.0))
        # day 2 updates from start-of-day ratings, applied together afterwards (zero-sum per game; a tie scores 1/2)
        b_after_d1 = 1500.0 - (after_d1 - 1500.0)
        c_after = 1500.0 + -(20.0 * (0.0 - rc.elo_expected(after_d1, 1500.0)))
        d_after = 1500.0 + -(20.0 * (0.5 - rc.elo_expected(b_after_d1, 1500.0)))
        self.assertEqual((elo["targets"]["k4"]["a_rating"], elo["targets"]["k4"]["b_rating"]), (c_after, d_after))
        self.assertEqual((elo["targets"]["k4"]["a_games"], elo["targets"]["k4"]["b_games"]), (1, 1))
        self.assertEqual((elo["games"], elo["dates"]), (4, 3))

    def test_every_season_restarts_at_1500(self) -> None:
        pool = {r["contest_key"]: r for r in (pool_row("k1", 2021, "2021-09-01", "A", "B", 30, 10),
                                              pool_row("k2", 2022, "2022-09-01", "A", "B", 3, 10))}
        targets = [{"contest_key": "k2", "season": 2022, "contest_date": "2022-09-01", "a_key": "A", "b_key": "B"}]
        state = rc.derive_elo(pool, targets)["targets"]["k2"]
        self.assertEqual((state["a_rating"], state["b_rating"], state["a_games"]), (1500.0, 1500.0, 0))

    def test_ties_count_half_and_cold_starts_are_missing_with_zero_values(self) -> None:
        games = [pool_row("k1", 2021, "2021-09-01", "A", "B", 30, 10), pool_row("k2", 2021, "2021-09-08", "C", "A", 14, 14)]
        block = rc._side_block("A", games)
        self.assertEqual((block["games"], block["wins"], block["ties"]), (2, 1, 1))
        self.assertEqual(frac(block["win_rate"]), Fraction(3, 4))
        self.assertEqual([c["side"] for c in block["contributing"]], ["A", "B"])
        self.assertEqual(frac(block["margin_mean"]), Fraction(20, 2))
        cold = rc._side_block("Z", [])
        self.assertTrue(cold["cold_start"])
        self.assertEqual([cold[n] for n in rc.SIDE_FIELDS[1:]], [None] * 4)
        self.assertEqual(cold["missing"], {"games": 0, "win_rate": 1, "points_for_mean": 1, "points_against_mean": 1,
                                           "margin_mean": 1})
        self.assertEqual([rc.side_value(cold, n) for n in rc.SIDE_FIELDS], [0] * 5)

    def test_own_and_later_outcomes_cannot_change_pre_date_state(self) -> None:
        rows = [pool_row("k1", 2021, "2021-09-01", "A", "B", 30, 10), pool_row("k2", 2021, "2021-09-08", "A", "C", 20, 3),
                pool_row("k3", 2021, "2021-09-15", "B", "C", 9, 6), pool_row("k4", 2021, "2021-09-22", "A", "B", 1, 2)]
        targets = [{"contest_key": k, "season": 2021, "contest_date": r["contest_date"], "a_key": r["a_key"],
                    "b_key": r["b_key"]} for k, r in ((r["contest_key"], r) for r in rows)]
        genuine = rc.derive_elo({r["contest_key"]: r for r in rows}, targets)["targets"]["k3"]
        changed = [dict(r) for r in rows]
        changed[2].update(a_points=0, b_points=50)        # k3's own outcome
        changed[3].update(a_points=99, b_points=0)        # a later outcome
        self.assertEqual(rc.derive_elo({r["contest_key"]: r for r in changed}, targets)["targets"]["k3"], genuine)
        index = rc.team_pool_index({r["contest_key"]: r for r in changed})
        prior = [r for d, k in index[("B", 2021)] for r in changed if r["contest_key"] == k and d < "2021-09-15"]
        self.assertEqual(rc._side_block("B", prior), rc._side_block("B", [rows[0]]))
        earlier = [dict(r) for r in rows]
        earlier[0].update(a_points=0, b_points=50)        # an earlier outcome does change it
        self.assertNotEqual(rc.derive_elo({r["contest_key"]: r for r in earlier}, targets)["targets"]["k3"], genuine)


# --------------------------------------------------------------------------------------------- derivation

class DerivationTests(World):
    def test_population_counts_and_c47_bytes_are_preserved(self) -> None:
        counts = self.result["population_counts"]
        self.assertEqual(counts, self.anchors["expected"])
        self.assertGreater(counts["comparison_targets"], 0)
        self.assertEqual(len(self.derived["estimates"]), counts["targets"] * 2 * len(rc.MODEL_IDS))
        self.assertEqual(len(self.derived["scores"]), counts["targets"] * len(rc.MODEL_IDS))
        with bm.RetrospectiveBenchmark(self.world["benchmark_db"], history_database=self.world["history_db"],
                                       anchors=rc.history_anchors(self.anchors)) as bench:
            c47 = bm.record_lines(bench.derived)
        ours = [line for record, line in zip(self.derived["estimates"], rc.record_lines(self.derived)["estimates"])
                if record["model_id"] in rc.C47_MODELS]
        self.assertEqual(ours, c47["estimates"])
        self.assertEqual(rc.record_lines(self.derived)["labels"], c47["labels"])
        self.assertEqual(self.result["c47_preservation"]["estimate_lines_equal"], len(c47["estimates"]))

    def test_prior_records_are_rederived_from_parent_rows_with_full_lineage(self) -> None:
        inputs = self.inputs()
        pool = inputs["pool"]["rows"]
        views = {(r[1], r[2]): json.loads(r[7]) for r in inputs["history"]["views"]}
        tie_half_seen = False
        for feature in self.derived["features"]:
            team = feature["team"]
            view = views[(feature["contest_key"], feature["view"])]["team_history"]
            self.assertEqual([c["contest_key"] for c in team["contributing"]], view["contributing_contest_keys"])
            for item in team["contributing"]:
                row = pool[item["contest_key"]]
                self.assertLess(item["contest_date"], feature["contest_date"])
                self.assertEqual(row["season"], feature["season"])
                mine = (row["a_points"], row["b_points"]) if item["side"] == "A" else (row["b_points"], row["a_points"])
                self.assertEqual((item["points_for"], item["points_against"]), mine)
            if team["ties"]:
                tie_half_seen = True
                self.assertEqual(frac(team["win_rate"]), Fraction(2 * team["wins"] + team["ties"], 2 * team["games"]))
            self.assertEqual(feature["first_four_team_games"],
                             min(feature["team"]["games"], feature["opponent"]["games"]) < 4)
            self.assertEqual(feature["cold_start"], min(feature["team"]["games"], feature["opponent"]["games"]) == 0)
        self.assertTrue(tie_half_seen)
        self.assertTrue(any(f["cold_start"] for f in self.derived["features"]))
        outside = {c["opponent_division_label"] for f in self.derived["features"] for c in f["team"]["contributing"]}
        self.assertTrue({"FCS", "DII"} <= outside)

    def test_oriented_estimates_are_one_canonical_value_and_its_exact_complement(self) -> None:
        for record in self.derived["estimates"]:
            if record["model_id"] in rc.C47_MODELS or record["orientation"] != "A":
                continue
            other = self.estimate(record["contest_key"], record["model_id"], "B")
            with self.subTest(key=record["contest_key"], model=record["model_id"]):
                if record["model_id"] == rc.MODEL_RIDGE:
                    self.assertEqual(Decimal(record["margin"]) + Decimal(other["margin"]), 0)
                    self.assertNotIn("probability", record)
                    self.assertNotIn("probability", other)
                else:
                    self.assertEqual(Decimal(record["probability"]) + Decimal(other["probability"]), 1)
                    self.assertTrue(0 < Decimal(record["probability"]) < 1)
                    self.assertTrue(rc._coherent_pair(record, other))

    def test_swapping_roles_is_antisymmetric(self) -> None:
        features = {(f["contest_key"], f["view"]): f for f in self.derived["features"]}
        fits = self.derived["fits"]
        for target in self.derived["targets"]:
            key = target["contest_key"]
            a, b = features[(key, "A")], features[(key, "B")]
            za = rc.scaled(rc.design_row(a), fits["scales"])
            zb = rc.scaled(rc.design_row(b), fits["scales"])
            with self.subTest(key):
                self.assertEqual(zb, tuple(-v for v in za))          # the B view is the exact negated design
                p_b_direct = rf.sigmoid(rf.linear(zb, fits["logistic"].coefficients))
                served_b = Decimal(self.estimate(key, rc.MODEL_LOGISTIC, "B")["probability"])
                self.assertLessEqual(abs(Decimal(p_b_direct) - served_b), Decimal("1e-11"))
                self.assertEqual(rf.linear(zb, fits["ridge"].coefficients),
                                 -rf.linear(za, fits["ridge"].coefficients))
                elo_a = self.estimate(key, rc.MODEL_ELO, "A")
                elo_b = self.estimate(key, rc.MODEL_ELO, "B")
                self.assertEqual((elo_a["team_rating"], elo_a["opponent_rating"]),
                                 (elo_b["opponent_rating"], elo_b["team_rating"]))

    def test_fits_use_training_rows_only_and_2023_cannot_move_them(self) -> None:
        features = self.derived["features"]
        labels = {lab["contest_key"]: lab for lab in self.derived["labels"]}
        genuine = rc.derive_fits(features, labels)
        moved = [copy.deepcopy(f) for f in features]
        flipped = copy.deepcopy(labels)
        for feature in moved:
            if feature["season"] == 2023:
                feature["differences"]["values"] = [bm.rational(Fraction(99))] * 5
        for key, label in flipped.items():
            if label["season"] == 2023 and label["y_a"] is not None:
                label["y_a"] = 1 - label["y_a"]
                label["a_points"], label["b_points"] = label["b_points"], label["a_points"]
        changed = rc.derive_fits(moved, flipped)
        self.assertEqual(changed["scales"], genuine["scales"])
        self.assertEqual(changed["logistic"].coefficients, genuine["logistic"].coefficients)
        self.assertEqual(changed["ridge"].coefficients, genuine["ridge"].coefficients)
        # the wrong rule (2023 in the fit) would move them: the guard is real, not vacuous
        with mock.patch.object(rc, "TRAINING_SEASONS", rc.TARGET_SEASONS):
            leaked = rc.derive_fits(moved, flipped)
        self.assertNotEqual(leaked["logistic"].coefficients, genuine["logistic"].coefficients)
        tie = [k for k, lab in labels.items() if lab["label_state"] == "TIE"]
        self.assertEqual(genuine["excluded"], {"logistic:TIE": len(tie)})
        self.assertEqual(genuine["used"]["ridge"], genuine["training_targets"])

    def test_held_parameters_make_earlier_estimates_independent_of_later_outcomes(self) -> None:
        inputs = self.inputs()
        fits = self.derived["fits"]
        last_date = max(t["contest_date"] for t in self.derived["targets"] if t["season"] == 2022)
        later = [k for k, r in inputs["pool"]["rows"].items() if r["season"] == 2022 and r["contest_date"] >= last_date]
        changed = copy.deepcopy(inputs)
        for key in later:
            changed["pool"]["rows"][key].update(a_points=0, b_points=77)
        c47 = bm.derive(inputs["history"], rc.history_anchors(self.anchors))
        feats, _sides = rc.derive_features(c47, inputs)
        elo_a = rc.derive_elo(inputs["pool"]["rows"], c47["targets"])
        elo_b = rc.derive_elo(changed["pool"]["rows"], c47["targets"])
        lines = [rc.canonical_line(f) for f in feats]
        a = rc.derive_estimates(c47, feats, elo_a, fits, lines)
        b = rc.derive_estimates(c47, feats, elo_b, fits, lines)
        for (ra, _la), (rb, _lb) in zip(a, b):
            if ra["season"] == 2022 and ra["contest_date"] <= last_date:
                self.assertEqual(ra, rb)

    def test_scores_one_per_game_and_model_from_the_served_values(self) -> None:
        estimates = {(e["contest_key"], e["model_id"]): e for e in self.derived["estimates"] if e["orientation"] == "A"}
        labels = {lab["contest_key"]: lab for lab in self.derived["labels"]}
        self.assertTrue(all(s["orientation"] == "A" for s in self.derived["scores"]))
        for score in self.derived["scores"]:
            estimate, label = estimates[(score["contest_key"], score["model_id"])], labels[score["contest_key"]]
            with self.subTest(key=score["contest_key"], model=score["model_id"]):
                if score["model_id"] == rc.MODEL_RIDGE:
                    self.assertNotIn("brier", score)
                    if label["label_state"] in ("DECISIVE", "TIE"):
                        error = (label["a_points"] - label["b_points"]) - Fraction(Decimal(estimate["margin"]))
                        self.assertEqual(frac(score["absolute_error"]), abs(error))
                        self.assertEqual(frac(score["squared_error"]), error * error)
                    continue
                p = frac(estimate["probability"]) if score["model_id"] in rc.C47_MODELS else \
                    Fraction(Decimal(estimate["probability"]))
                if label["y_a"] is None:
                    self.assertEqual(score["score_state"], "UNSCORED")
                    continue
                self.assertEqual(frac(score["brier"]), (p - label["y_a"]) ** 2)
                q = p if label["y_a"] == 1 else 1 - p
                self.assertEqual(score["log_loss"], repr(-math.log(min(max(float(q), 1e-15), 1 - 1e-15))))
                self.assertEqual(score["log_loss_convention"], "CLIPPED_LOG_ARGUMENT_1E-15")

    def test_summary_slices_empty_scopes_common_support_and_calibration(self) -> None:
        summary = self.derived["summary"]
        rows = summary["rows"]
        self.assertEqual(len(rows), len(rc.SLICE_IDS) * 11 * len(rc.MODEL_IDS))
        empty = [r for r in rows if r["scope_id"] == "2016"]
        self.assertTrue(empty and all(r["scored_games"] == 0 for r in empty))
        self.assertTrue(all(r.get("brier_mean") is None and r.get("mae") is None for r in empty))
        scores = self.derived["scores"]
        for row in rows:
            seasons = set(row["seasons"])
            chosen = [s for s in scores if s["model_id"] == row["model_id"] and s["season"] in seasons and
                      rc.in_slice(row["slice"], s) and s["score_state"] == "SCORED"]
            with self.subTest(slice=row["slice"], scope=row["scope_id"], model=row["model_id"]):
                self.assertEqual(row["scored_games"], len(chosen))
                if row["metric_kind"] == "PROBABILITY":
                    self.assertEqual(sum(b["count"] for b in row["calibration"]), len(chosen))
                    if chosen:
                        self.assertEqual(frac(row["brier_mean"]),
                                         sum((frac(s["brier"]) for s in chosen), Fraction(0)) / len(chosen))
        tamu = [s for s in scores if s["model_id"] == rc.MODEL_NULL and s["texas_am_target"]]
        self.assertTrue(tamu and all(rc.TAMU_KEY in (s["a_key"], s["b_key"]) for s in tamu))
        self.assertEqual(len(summary["comparisons"]), len(rc.SLICE_IDS) * 11 * 3)

    def test_sample_states_label_in_sample_and_out_of_fit(self) -> None:
        for record in self.derived["estimates"]:
            if record["model_id"] in rc.C47_MODELS:
                continue
            want = ("NOT_FITTED" if record["model_id"] == rc.MODEL_ELO else
                    "IN_SAMPLE_TRAINING_NOT_A_LABEL_ANCHOR" if record["season"] <= 2022 else "OUT_OF_FIT_EXPOSED_2023")
            self.assertEqual(record["sample_state"], want)


# --------------------------------------------------------------------------------------------- determinism and inputs

class DeterminismTests(World):
    def test_order_chunk_and_resume_variants_reproduce_every_byte(self) -> None:
        genuine = (self.result["content_identity"], self.result["database_identity"], self.result["payload_sha256"],
                   self.result["database_sha256"])
        for name, extra in (("rev", ["--input-order", "reverse"]), ("shuf", ["--input-order", "shuffle:17"]),
                            ("c1", ["--chunk-size", "1", "--checkpoint-dir", str(self.tmp / "k1")]),
                            ("c17", ["--chunk-size", "17", "--checkpoint-dir", str(self.tmp / "k17")]),
                            ("c257", ["--chunk-size", "257", "--checkpoint-dir", str(self.tmp / "k257")])):
            with self.subTest(name):
                code, result, stderr = fx.run_build(self.contract_path, self.world, self.tmp / name, *extra)
                self.assertEqual(code, 0, stderr)
                self.assertEqual((result["content_identity"], result["database_identity"], result["payload_sha256"],
                                  result["database_sha256"]), genuine)
        resume = ["--chunk-size", "7", "--checkpoint-dir", str(self.tmp / "kr")]
        code, result, _err = fx.run_build(self.contract_path, self.world, self.tmp / "res", *resume,
                                          "--stop-after-chunks", "2")
        self.assertEqual((code, result["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        self.assertFalse((self.tmp / "res" / "canonical").exists())
        code, result, stderr = fx.run_build(self.contract_path, self.world, self.tmp / "res", *resume, "--resume")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(result["database_identity"], genuine[1])
        code, again, _err = fx.run_build(self.contract_path, self.world, self.tmp / "o")
        self.assertEqual((code, again["state"], again["database"]["state"]),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"))
        code, _r, stderr = fx.run_build(self.contract_path, self.world, self.tmp / "res2", *resume)
        self.assertEqual((code, fx.refusal(stderr)), (2, "CHECKPOINT_EXISTS"))


class InputRefusalTests(World):
    def rehash_parent(self, name: str, statements: list[tuple[str, tuple]]) -> tuple[Path, dict]:
        """A self-consistent copy of the fixture parent with ``statements`` applied (new identity and manifest)."""
        parent = self.world["parent"]
        work = self.tmp / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(parent["database"], work)
        conn = sqlite3.connect(work)
        for sql, params in statements:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"parent forgery {name} changed nothing")
        conn.commit()
        conn.close()
        doc = json.loads(parent["manifest"].read_text(encoding="utf-8"))["identity_document"]
        doc["outputs"] = {pop.DB_FILE_NAME: pop.sha256_file(work)}
        identity = bm.sha256_bytes(bm.canonical_json_bytes(doc))
        target = self.tmp / name / "canonical" / "p" / "sha256" / identity / pop.DB_FILE_NAME
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.tmp / name / "manifests" / "p" / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps({"identity": identity, "identity_document": doc}), encoding="utf-8")
        anchors = copy.deepcopy(self.anchors)
        anchors["population"].update(database_identity=identity, sqlite_sha256=pop.sha256_file(target))
        return target, anchors

    def test_parent_binding_pool_and_label_contradictions_are_refused(self) -> None:
        with self.assertRaises(rc.ReferenceError) as caught:
            rc.load_inputs(self.world["history_db"], self.world["parent"]["database"],
                           {**self.anchors, "population": {**self.anchors["population"], "sqlite_sha256": "0" * 64}})
        self.assertEqual(caught.exception.code, "REFERENCE_POPULATION_MISMATCH")
        pool_key = next(k for k, r in self.inputs()["pool"]["rows"].items() if r["season"] == 2021 and
                        r["a_key"].startswith("org:") and r["contest_date"] == "2021-08-26")
        target, anchors = self.rehash_parent("pm", [("UPDATE contest SET contest_status = 'FORFEIT' WHERE contest_key = ?",
                                                     (pool_key,))])
        with self.assertRaises(rc.ReferenceError) as caught:
            rc.load_inputs(self.world["history_db"], target, anchors)
        self.assertEqual(caught.exception.code, "REFERENCE_POOL_MISMATCH")
        early = next(t for t in self.derived["targets"] if t["season"] == 2021 and t["contest_date"] == "2021-09-02")
        target, anchors = self.rehash_parent("lm", [("UPDATE contest SET a_points = a_points + 1 WHERE contest_key = ?",
                                                     (early["contest_key"],))])
        with self.assertRaises(rc.ReferenceError) as caught:
            rc.derive(rc.load_inputs(self.world["history_db"], target, anchors), anchors)
        self.assertEqual(caught.exception.code, "REFERENCE_FEATURE_LINEAGE_MISMATCH")
        last = max((t for t in self.derived["targets"] if t["season"] == 2023), key=lambda t: t["contest_date"])
        target, anchors = self.rehash_parent("ll", [("UPDATE contest SET a_points = a_points + 1 WHERE contest_key = ?",
                                                     (last["contest_key"],))])
        with self.assertRaises(rc.ReferenceError) as caught:
            rc.derive(rc.load_inputs(self.world["history_db"], target, anchors), anchors)
        self.assertEqual(caught.exception.code, "REFERENCE_LABEL_INPUT_INVALID")

    def test_missing_inputs_and_another_benchmark_are_refused(self) -> None:
        missing = self.tmp / "nope" / "national_history.sqlite"
        self.assertEqual(self.serve("--grain", "reference-score", "--all")[0], 0)
        code, _doc, err = fx.query(self.world, self.anchors, self.db, "--grain", "reference-score",
                                   "--history-database", str(missing))
        self.assertEqual(code, 2)
        self.assertTrue(fx.refusal(err).startswith(("HISTORY_", "DATABASE_LOCATION_", "REFERENCE_HISTORY")), err)
        bad = copy.deepcopy(self.anchors)
        bad["benchmark"]["database_identity"] = "0" * 64
        code, _r, stderr = fx.run_build(fx.write_contract(self.tmp / "bad_bench.json", fx.contract_for(
            self.world, parent__benchmark=bad["benchmark"])), self.world, self.tmp / "bb")
        self.assertEqual((code, fx.refusal(stderr)), (2, "REFERENCE_C47_BENCHMARK_MISMATCH"))


# --------------------------------------------------------------------------------------------- consumer

class ConsumerTests(World):
    def expect(self, grain: str, **f) -> list[dict]:
        records = (self.derived["summary"]["rows"] + self.derived["summary"]["comparisons"]
                   if grain == "reference-summary" else self.derived[rc.GRAINS[grain]])
        names = bm.team_name_index(self.derived["targets"])
        out = []
        for r in records:
            if grain == "reference-parameter":
                if "model" in f and r["model_id"] != f["model"]:
                    continue
                out.append(r)
                continue
            if grain == "reference-summary":
                if "season" in f and (r["scope_id"] != str(f["season"]) or
                                      ("partition" in f and f["season"] not in rc.PARTITION_SEASONS[f["partition"]])):
                    continue
                if "season" not in f and "partition" in f and r["scope_id"] != f["partition"]:
                    continue
                if "model" in f and r["model_id"] != f["model"]:
                    continue
                if "slice" in f and r["slice"] != f["slice"]:
                    continue
                out.append(r)
                continue
            if "season" in f and r["season"] != f["season"]:
                continue
            if "partition" in f and r["partition"] != f["partition"]:
                continue
            if "model" in f and r["model_id"] != f["model"]:
                continue
            if "contest" in f and r["contest_key"] != f["contest"]:
                continue
            if "team" in f:
                sides = (r["a_key"], r["b_key"]) if grain == "reference-score" else (r["team_key"],)
                if not any(bm.team_matches(f["team"], r["season"], s, names) for s in sides):
                    continue
            out.append(r)
        return out

    def test_grains_filters_intersections_paging_and_empty_selections(self) -> None:
        key = next(t["contest_key"] for t in self.derived["targets"] if t["season"] == 2022)
        cases = [("reference-feature", {}), ("reference-feature", {"season": 2023, "team": "org:697"}),
                 ("reference-feature", {"team": "Texas A&M"}), ("reference-feature", {"contest": key}),
                 ("reference-estimate", {"model": rc.MODEL_ELO}),
                 ("reference-estimate", {"partition": "SPLIT-DEV-SEL", "model": rc.MODEL_LOGISTIC}),
                 ("reference-estimate", {"season": 2021, "partition": "SPLIT-DEV-SEL"}),
                 ("reference-estimate", {"team": "Charlie State", "season": 2021}),
                 ("reference-parameter", {}), ("reference-parameter", {"model": rc.MODEL_RIDGE}),
                 ("reference-score", {"model": rc.MODEL_RIDGE, "season": 2023}),
                 ("reference-score", {"team": "org:697", "partition": "SPLIT-DEV-HIST"}),
                 ("reference-score", {"team": "org:999999"}), ("reference-score", {"contest": "ncaa:999999"}),
                 ("reference-summary", {}), ("reference-summary", {"season": 2023, "slice": "TEXAS_AM"}),
                 ("reference-summary", {"season": 2023, "partition": "SPLIT-DEV-HIST"}),
                 ("reference-summary", {"partition": "SPLIT-DEV-HIST", "model": rc.MODEL_NULL}),
                 ("reference-summary", {"slice": "COLD_START", "model": rc.MODEL_RIDGE})]
        flags = {"season": "--season", "team": "--team", "contest": "--contest", "model": "--model",
                 "partition": "--partition", "slice": "--slice"}
        for grain, f in cases:
            argv = ["--grain", grain]
            for name, value in f.items():
                argv += [flags[name], str(value)]
            with self.subTest(grain=grain, filters=f):
                code, doc, refused = self.serve(*argv, "--all")
                self.assertEqual((code, refused), (0, None))
                want = self.expect(grain, **f)
                self.assertEqual(doc["rows"], want)
                self.assertEqual((doc["total"], doc["returned"], doc["next_offset"]), (len(want), len(want), None))
                self.assertEqual(doc["reference_identity"], self.db.parent.name)
                pages, offset = [], 0
                while True:
                    page = self.serve(*argv, "--limit", "4", "--offset", str(offset))[1]
                    pages += page["rows"]
                    if page["next_offset"] is None:
                        break
                    offset = page["next_offset"]
                self.assertEqual(pages, want)
        for season, state in ((2024, "PROTECTED_SEASON_NOT_IN_REFERENCE"), (2030, "FORWARD_SEASON_NOT_IN_REFERENCE"),
                              (2010, "OUTSIDE_REFERENCE_SCOPE")):
            for grain in ("reference-summary", "reference-score"):
                with self.subTest(season=season, grain=grain):
                    doc = self.serve("--grain", grain, "--season", str(season))[1]
                    self.assertEqual((doc["total"], doc["rows"], doc["season_scope_state"]), (0, [], state))

    def test_misuse_is_refused_before_any_file_is_read(self) -> None:
        for argv, code in ((["--grain", "reference-score", "--require-pit"], "REFERENCE_PIT_NOT_ADMITTED"),
                           (["--grain", "reference-feature", "--model", rc.MODEL_NULL], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "reference-parameter", "--season", "2021"], "FILTER_NOT_APPLICABLE"),
                           # the parameter grain describes the models, not games (team/contest select summary games;
                           # C56-CONT-01 MF56A01-01 removed the reviewed head's summary refusals)
                           (["--grain", "reference-parameter", "--team", "org:1"], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "reference-parameter", "--contest", "1"], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "reference-parameter", "--partition", "SPLIT-DEV-SEL"],
                            "FILTER_NOT_APPLICABLE"),
                           (["--grain", "reference-score", "--slice", "NATIONAL"], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "reference-score", "--model", "ELO"], "MODEL_UNKNOWN"),
                           (["--grain", "reference-score", "--partition", "SPLIT-PROTECTED"], "PARTITION_UNKNOWN"),
                           (["--grain", "reference-summary", "--slice", "SEC"], "SLICE_UNKNOWN"),
                           (["--grain", "reference-score", "--limit", "-1"], "NEGATIVE_LIMIT"),
                           (["--grain", "reference-score", "--offset", "-1"], "NEGATIVE_OFFSET"),
                           (["--grain", "reference-score", "--contest", "bad\x01key"], "CONTEST_KEY_INVALID"),
                           (["--grain", "reference-score", "--team", " "], "TEAM_INVALID"),
                           (["--grain", "score"], "UNKNOWN_GRAIN"),
                           (["--grain", "reference-score", "--expect-identity", "x"], "STALE_REFERENCE_IDENTITY"),
                           (["--grain", "reference-score", "--expect-identity", "0" * 64], "STALE_REFERENCE_IDENTITY"),
                           (["--grain", "reference-score", "--database", "x"], "REFERENCE_MODE_CONFLICT"),
                           (["--grain", "reference-score", "--prospective-shadow", "x"], "REFERENCE_MODE_CONFLICT"),
                           (["--grain", "reference-score", "--schedule-evidence", "x"], "REFERENCE_MODE_CONFLICT"),
                           (["--grain", "reference-score", "--cutoff", "2026-01-01T00:00:00Z"],
                            "FILTER_NOT_APPLICABLE")):
            with self.subTest(argv):
                self.assertEqual(self.serve(*argv)[0::2], (2, code))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(query.main(["--reference-comparison", str(self.db), "--grain", "reference-score"],
                                        reference_anchors=self.anchors), 2)
        self.assertEqual(fx.refusal(err.getvalue()), "REFERENCE_INPUT_REQUIRED")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            query.main(["--reference-comparison", str(self.db), "--grain", "reference-score", "--al"])

    def test_existing_invocations_unchanged_and_the_mode_is_lazy(self) -> None:
        self.assertNotIn("--reference-comparison", query.build_parser().format_help())
        for parser in (query.build_preview_parser(), query.build_shadow_parser(), query.build_schedule_parser()):
            self.assertNotIn("reference-comparison", parser.format_help())
        self.assertIn("explicit national retrospective reference comparison mode",
                      query.build_reference_parser().format_help())
        script = ("import sys, contextlib, io; sys.path.insert(0, sys.argv[1]); "
                  "from aggie_analytics.retrospective_baseline import query; "
                  "out = io.StringIO()\n"
                  "with contextlib.redirect_stdout(out):\n"
                  "    try:\n        query.main(['--help'])\n    except SystemExit:\n        pass\n"
                  "print(sorted(m for m in sys.modules if m.startswith('aggie_analytics.retrospective_baseline.')))")
        proc = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT / "src")], capture_output=True, text=True,
                              check=True)
        loaded = proc.stdout.strip().splitlines()[-1]
        self.assertNotIn("reference", loaded)
        self.assertIn("benchmark", loaded)

    def test_the_reference_connection_is_read_only_and_nothing_is_created(self) -> None:
        with rc.ReferenceComparison(self.db, history_database=self.world["history_db"],
                                    population_database=self.world["parent"]["database"], anchors=self.anchors) as ref:
            with self.assertRaises(sqlite3.OperationalError):
                ref.conn.execute("DELETE FROM meta")
        missing = self.tmp / "missing" / rc.POPULATION / "sha256" / ("0" * 64) / rc.DB_FILE
        self.assertEqual(self.serve("--grain", "reference-score", database=missing)[0::2],
                         (2, "REFERENCE_DATABASE_MISSING"))
        self.assertFalse(missing.parent.exists())
        wrong = self.tmp / "wrong" / "x" / "sha256" / self.db.parent.name / rc.DB_FILE
        wrong.parent.mkdir(parents=True)
        shutil.copyfile(self.db, wrong)
        self.assertEqual(self.serve("--grain", "reference-score", database=wrong)[0::2],
                         (2, "REFERENCE_LOCATION_INVALID"))

    def test_genuine_rehoused_long_and_extended_copies_serve_the_same_rows(self) -> None:
        identity = self.db.parent.name
        manifest = rc.manifest_path_for(self.db)
        far = os.path.join(str(self.tmp), "long " + "x" * 110, "deeper # % é ' " + "y" * 110)
        target = os.path.join(far, "canonical", rc.POPULATION, "sha256", identity, rc.DB_FILE)
        target_man = os.path.join(far, "manifests", rc.POPULATION, "sha256", identity, "run_manifest.json")
        for src, dst in ((self.db, target), (manifest, target_man)):
            os.makedirs(EXT + os.path.dirname(dst) if WINDOWS else os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, EXT + dst if WINDOWS else dst)
        self.assertGreater(len(target), 300)
        if WINDOWS:   # the class temporary directory cannot remove a tree beyond the classic path limit
            self.addCleanup(shutil.rmtree, EXT + os.path.join(str(self.tmp), "long " + "x" * 110))
        original = self.serve("--grain", "reference-estimate", "--all")[1]
        for spelling in ((EXT + target) if WINDOWS else target, (EXT + str(self.db)) if WINDOWS else str(self.db)):
            code, doc, refused = self.serve("--grain", "reference-estimate", "--all", database=Path(spelling))
            self.assertEqual((code, refused), (0, None))
            self.assertEqual(doc["rows"], original["rows"])
        if WINDOWS:
            dotted = EXT + str(self.tmp / "dot.") + "\\" + rc.DB_FILE
            self.assertEqual(self.serve("--grain", "reference-score", database=Path(dotted))[0::2],
                             (2, "DATABASE_LOCATION_NOT_LITERAL"))
            self.assertEqual(self.serve("--grain", "reference-score",
                                        database=Path("\\\\server\\share\\x\\" + rc.DB_FILE))[0::2],
                             (2, "DATABASE_LOCATION_UNSUPPORTED"))

    def test_provenance_only_manifest_changes_keep_the_identity(self) -> None:
        identity = self.db.parent.name
        root = self.tmp / "prov"
        db = root / "canonical" / rc.POPULATION / "sha256" / identity / rc.DB_FILE
        db.parent.mkdir(parents=True)
        shutil.copyfile(self.db, db)
        doc = json.loads(rc.manifest_path_for(self.db).read_text(encoding="utf-8"))
        doc["provenance"] = {"rehoused": True}
        man = root / "manifests" / rc.POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps(doc), encoding="utf-8")
        code, served, refused = self.serve("--grain", "reference-parameter", database=db)
        self.assertEqual((code, refused, served["reference_identity"]), (0, None, identity))

    # ---- C56-CONT-01 MF56A01-01 (TP56 section 4): --team and --contest select canonical games at the summary grain

    def selected(self, team: str | None = None, contest: str | None = None) -> set[str]:
        """This test's own selection: accepted targets by exact contest key and by either participant through that
        season's names (org:<digits>, bare digits or a name the team carries in that season)."""
        names: dict[tuple[int, str], set[str]] = {}
        for t in self.derived["targets"]:
            for key, name in ((t["a_key"], t["a_team_name"]), (t["b_key"], t["b_team_name"])):
                names.setdefault((t["season"], key), set()).add(str(name).casefold())

        def matches(key: str, season: int) -> bool:
            digits = re.fullmatch(r"(?:org:)?([0-9]{1,12})", team)
            return key == f"org:{int(digits.group(1))}" if digits else \
                team.casefold() in names.get((season, key), set())
        return {t["contest_key"] for t in self.derived["targets"]
                if (contest is None or t["contest_key"] == (f"ncaa:{contest}" if contest.isdigit() else contest)) and
                (team is None or matches(t["a_key"], t["season"]) or matches(t["b_key"], t["season"]))}

    def expected_summary(self, games: set[str], **f) -> list[tuple]:
        """Summary rows then comparisons over the selected games' verified A-oriented score records, computed here from
        the frozen rules (exact rationals; no row for a slice and scope without a selected game), then the scope, model
        and slice filters exactly as for the canonical summary."""
        scores = [s for s in self.derived["scores"] if s["contest_key"] in games]
        scopes = [(str(s), (s,)) for s in rc.TARGET_SEASONS] + \
            [(p, tuple(sorted(rc.PARTITION_SEASONS[p]))) for p in rc.PARTITION_IDS] + \
            [("2016-2023", tuple(rc.TARGET_SEASONS))]
        member = {"NATIONAL": lambda s: True, "TEXAS_AM": lambda s: rc.TAMU_KEY in (s["a_key"], s["b_key"]),
                  "FIRST_FOUR_TEAM_GAMES": lambda s: s["first_four_team_games"], "COLD_START": lambda s: s["cold_start"]}
        rows, comparisons = [], []
        for slice_id in rc.SLICE_IDS:
            for scope_id, seasons in scopes:
                group = [s for s in scores if s["season"] in seasons and member[slice_id](s)]
                if not group:
                    continue
                means = {}
                for model in rc.MODEL_IDS:
                    mine = [s for s in group if s["model_id"] == model]
                    scored = [s for s in mine if s["score_state"] == "SCORED"]
                    if model in rc.PROBABILITY_MODELS:
                        brier = sum((frac(s["brier"]) for s in scored), Fraction(0)) / len(scored) if scored else None
                        log = math.fsum(float(s["log_loss"]) for s in scored) / len(scored) if scored else None
                        bins = [0] * 10
                        for s in scored:
                            bins[min(int(frac(s["probability_a_exact"]) * 10), 9)] += 1
                        values = (brier, log, tuple(bins))
                        means[model] = (brier, log, len(scored))
                    else:
                        values = tuple(sum((frac(s[k]) for s in scored), Fraction(0)) / len(scored) if scored else None
                                       for k in ("absolute_error", "squared_error"))
                    rows.append(("reference_summary_row", slice_id, scope_id, model, len(mine), len(scored), values))
                for model in (rc.MODEL_SMOOTHED, rc.MODEL_ELO, rc.MODEL_LOGISTIC):
                    brier, log, scored_games = means[model]
                    base = means[rc.MODEL_NULL]
                    comparisons.append(("reference_comparison_row", slice_id, scope_id, model, scored_games,
                                        None if brier is None or base[0] is None else brier - base[0]))
        out = []
        for row in rows + comparisons:
            scope_id, model, slice_id = row[2], row[3], row[1]
            if "season" in f:
                if "partition" in f and f["season"] not in rc.PARTITION_SEASONS[f["partition"]]:
                    continue
                if scope_id != str(f["season"]):
                    continue
            elif "partition" in f and scope_id != f["partition"]:
                continue
            if "model" in f and model != f["model"] or "slice" in f and slice_id != f["slice"]:
                continue
            out.append(row)
        return out

    @staticmethod
    def project(rows: list[dict]) -> list[tuple]:
        """Served summary rows and comparisons in the expected shape."""
        out = []
        for r in rows:
            if r["record_type"] == "reference_summary_row":
                if r["metric_kind"] == "PROBABILITY":
                    values = (None if r["brier_mean"] is None else frac(r["brier_mean"]),
                              None if r["log_loss_mean"] is None else float(r["log_loss_mean"]),
                              tuple(b["count"] for b in r["calibration"]))
                else:
                    values = tuple(None if r[k] is None else frac(r[k]) for k in ("mae", "mse"))
                out.append((r["record_type"], r["slice"], r["scope_id"], r["model_id"], r["score_records"],
                            r["scored_games"], values))
            else:
                out.append((r["record_type"], r["slice"], r["scope_id"], r["model_id"], r["scored_games"],
                            None if r["brier_mean_difference"] is None else frac(r["brier_mean_difference"])))
        return out

    def summary_answer(self, ref: rc.ReferenceComparison, **f) -> dict:
        try:
            return ref.query("reference-summary", season=f.get("season"), team=f.get("team"), contest=f.get("contest"),
                             model=f.get("model"), partition=f.get("partition"), slice_id=f.get("slice"),
                             all_rows=True)
        except rc.ReferenceError as exc:
            self.fail(f"MF56A01-01 the summary selection {f} was refused: {exc.code}")

    def test_summary_team_and_contest_select_canonical_games(self) -> None:
        targets = self.derived["targets"]
        tamu_b = next(t for t in targets if t["b_key"] == rc.TAMU_KEY)
        other = next(t for t in targets if rc.TAMU_KEY not in (t["a_key"], t["b_key"]))
        game = next(t for t in targets if t["season"] == 2022)
        cases = [("key", {"team": "org:697"}), ("digits", {"team": "697"}), ("name", {"team": "Texas A&M"}),
                 ("name, other casing", {"team": "texas a&m"}),
                 ("opponent orientation", {"team": "org:697", "season": tamu_b["season"]}),
                 ("contest", {"contest": game["contest_key"]}),
                 ("bare contest digits", {"contest": game["contest_key"].split(":")[1]}),
                 ("team and its contest", {"team": "org:697", "contest": tamu_b["contest_key"]}),
                 ("team and another game", {"team": "org:697", "contest": other["contest_key"]}),
                 ("unknown team key", {"team": "org:999999999"}), ("unknown team name", {"team": "No Such Team"}),
                 ("unknown contest", {"contest": "ncaa:999999999999"}),
                 ("unknown team in a season", {"team": "org:999999999", "season": 2022}),
                 ("known team, season without games", {"team": "org:697", "season": 2016}),
                 ("contest, other season", {"contest": game["contest_key"], "season": 2023}),
                 ("compatible partition", {"team": "org:697", "partition": "SPLIT-DEV-SEL"}),
                 ("season within its partition", {"team": "org:697", "season": 2023, "partition": "SPLIT-DEV-SEL"}),
                 ("incompatible partition", {"team": "org:697", "season": 2023, "partition": "SPLIT-DEV-HIST"}),
                 ("contest, incompatible partition", {"contest": game["contest_key"], "partition": "SPLIT-DEV-SEL"})]
        renamed = sorted({t["season"] for t in targets if "Charlie State" in (t["a_team_name"], t["b_team_name"])})
        if renamed:
            cases.append(("renamed name of its season", {"team": "Charlie State", "season": renamed[0]}))
        plain = sorted({t["season"] for t in targets if "org:3" in (t["a_key"], t["b_key"])} - set(renamed))
        if plain:
            cases.append(("renamed name, a season without it", {"team": "Charlie State", "season": plain[0]}))
        cases += [(f"{m}/{s}", {"team": "org:697", "model": m, "slice": s}) for m in rc.MODEL_IDS for s in rc.SLICE_IDS]
        self.assertIn(tamu_b["contest_key"], self.selected(team="org:697"))   # the team on side B is selected too
        empty_seen = known_seen = 0
        with rc.ReferenceComparison(self.db, history_database=self.world["history_db"],
                                    population_database=self.world["parent"]["database"], anchors=self.anchors) as ref:
            for name, f in cases:
                with self.subTest(name, **f):
                    games = self.selected(team=f.get("team"), contest=f.get("contest"))
                    want = self.expected_summary(games, **f)
                    doc = self.summary_answer(ref, **f)
                    self.assertEqual(len(doc["rows"]), len(want), f"MF56A01-01 {name}")
                    self.assertEqual(self.project(doc["rows"]), want, f"MF56A01-01 {name}")
                    self.assertEqual((doc["total"], doc["returned"], doc["next_offset"]), (len(want), len(want), None))
                    self.assertEqual(doc["summary_selection"]["canonical_games"], len(games))
                    empty_seen += not want
                    known_seen += bool(want)
            self.assertTrue(empty_seen >= 8 and known_seen >= 20)
            # a game counts once whichever side the team is on: the pooled national null row counts every selected game
            pooled = self.summary_answer(ref, team="org:697", slice="NATIONAL", model=rc.MODEL_NULL)["rows"]
            row = next(r for r in pooled if r["scope_id"] == "2016-2023")
            self.assertEqual(row["score_records"], len(self.selected(team="org:697")))
            # Texas A&M's own selection under its slice is the canonical TEXAS_AM summary, every non-empty scope
            stored = [r for r in self.derived["summary"]["rows"] + self.derived["summary"]["comparisons"]
                      if r["slice"] == "TEXAS_AM" and any(r["scope_id"] == x["scope_id"] and x["score_records"]
                                                          for x in self.derived["summary"]["rows"]
                                                          if x["slice"] == "TEXAS_AM")]
            self.assertEqual(self.summary_answer(ref, team="org:697", slice="TEXAS_AM")["rows"], stored)
            # the canonical (unselected) summary and its existing filters are unchanged
            self.assertEqual(ref.query("reference-summary", all_rows=True)["rows"],
                             self.derived["summary"]["rows"] + self.derived["summary"]["comparisons"])
            self.assertNotIn("summary_selection", ref.query("reference-summary", season=2023, all_rows=True))

    def test_summary_selection_through_the_cli_with_paging(self) -> None:
        for argv in (["--team", "org:697"], ["--team", "Texas A&M", "--season", "2023"], ["--contest", "ncaa:999999999999"],
                     ["--team", "org:999999999", "--season", "2019"]):
            with self.subTest(argv):
                code, doc, refused = self.serve("--grain", "reference-summary", *argv, "--all")
                self.assertEqual((code, refused), (0, None), "MF56A01-01 the summary selection was refused")
                f = dict(zip([a[2:] for a in argv[::2]], argv[1::2]))
                f = {k: int(v) if k == "season" else v for k, v in f.items()}
                want = self.expected_summary(self.selected(team=f.get("team"), contest=f.get("contest")), **f)
                self.assertEqual(self.project(doc["rows"]), want)
                if not want:
                    self.assertEqual((doc["rows"], doc["total"], doc["returned"], doc["next_offset"]), ([], 0, 0, None))
                pages, offset = [], 0
                while True:
                    page = self.serve("--grain", "reference-summary", *argv, "--limit", "37", "--offset", str(offset))[1]
                    pages += page["rows"]
                    if page["next_offset"] is None:
                        break
                    offset = page["next_offset"]
                self.assertEqual(pages, doc["rows"])

    # ---- C56-CONT-01 MF56A01-03: an explicit --manifest passes the literal local-file policy before any access

    def test_manifest_refusal_expectation_on_both_platforms(self) -> None:
        self.assertEqual(manifest_refusal_expected("unsupported", "nt"), "REFERENCE_MANIFEST_LOCATION_UNSUPPORTED")
        self.assertEqual(manifest_refusal_expected("not_literal", "nt"), "REFERENCE_MANIFEST_LOCATION_NOT_LITERAL")
        self.assertEqual(manifest_refusal_expected("unsupported", "posix"), "REFERENCE_MANIFEST_MISSING")
        self.assertEqual(manifest_refusal_expected("not_literal", "posix"), "REFERENCE_MANIFEST_MISSING")
        self.assertEqual(rc.MANIFEST_LOCATION_CODES, {"DATABASE_LOCATION_UNSUPPORTED":
                                                      "REFERENCE_MANIFEST_LOCATION_UNSUPPORTED",
                                                      "DATABASE_LOCATION_NOT_LITERAL":
                                                      "REFERENCE_MANIFEST_LOCATION_NOT_LITERAL"})

    def test_explicit_manifest_network_and_device_spellings_are_never_accessed(self) -> None:
        cases = [(f"\\\\{SENTINEL_HOST}\\share\\run_manifest.json", "unsupported"),
                 (f"//{SENTINEL_HOST}/share/run_manifest.json", "unsupported"),
                 (f"\\\\?\\UNC\\{SENTINEL_HOST}\\share\\run_manifest.json", "unsupported"),
                 ("\\\\.\\NUL", "unsupported"), ("\\\\.\\PIPE\\bas-c56-sentinel-pipe", "unsupported"),
                 ("\\\\?\\GLOBALROOT\\Device\\Null", "unsupported"),
                 ("\\\\?\\Volume{00000000-0000-0000-0000-000000000000}\\run_manifest.json", "unsupported"),
                 (EXT + str(self.tmp / "dot.") + "\\run_manifest.json", "not_literal")]
        for spelling, kind in cases:
            with self.subTest(spelling=spelling):
                want = manifest_refusal_expected(kind, os.name)
                if WINDOWS:
                    with access_sentinels(SENTINEL_TOKENS) as hits:
                        try:
                            code, _doc, refused = self.serve("--grain", "reference-parameter", "--manifest", spelling)
                        except ProhibitedAccess as exc:
                            self.fail(f"MF56A01-03 the explicit manifest location was accessed before validation: "
                                      f"{exc}")
                    self.assertEqual(hits, [], "MF56A01-03 an access sentinel was reached")
                else:   # POSIX: the characters name an ordinary local relative path (MF54A01-01 native expectation)
                    code, _doc, refused = self.serve("--grain", "reference-parameter", "--manifest", spelling)
                self.assertEqual((code, refused), (2, want), "MF56A01-03 the manifest spelling was not refused")

    def test_the_access_sentinels_catch_a_real_manifest_access(self) -> None:
        control = self.tmp / "sentinel-control-dir"
        control.mkdir(exist_ok=True)
        shutil.copyfile(rc.manifest_path_for(self.db), control / "run_manifest.json")
        with access_sentinels(("sentinel-control-dir",)) as hits, self.assertRaises(ProhibitedAccess):
            self.serve("--grain", "reference-parameter", "--manifest", str(control / "run_manifest.json"))
        self.assertTrue(hits)

    def test_explicit_manifest_local_spellings_serve_identical_rows(self) -> None:
        manifest = rc.manifest_path_for(self.db)
        original = self.serve("--grain", "reference-parameter", "--all")[1]
        reserved = self.tmp / "mf # % é ' ü 漢"
        reserved.mkdir(exist_ok=True)
        shutil.copyfile(manifest, reserved / "run_manifest.json")
        spellings = {"absolute": (str(manifest), None), "relative": ("run_manifest.json", manifest.parent),
                     "parent_relative": (os.path.join("..", manifest.parent.name, "run_manifest.json"),
                                         manifest.parent),
                     "reserved_and_unicode": (str(reserved / "run_manifest.json"), None)}
        if WINDOWS:
            # beyond 300 characters even from a bare drive root (a hosted runner's temporary root is short)
            far = os.path.join(str(self.tmp), "mlong " + "x" * 140, "deeper # % é ' " + "y" * 140)
            os.makedirs(EXT + far, exist_ok=True)
            shutil.copyfile(manifest, EXT + os.path.join(far, "run_manifest.json"))
            self.addCleanup(shutil.rmtree, EXT + os.path.join(str(self.tmp), "mlong " + "x" * 140))
            junction = self.tmp / "mjunction"
            if not junction.exists():
                import _winapi  # noqa: PLC0415
                _winapi.CreateJunction(str(reserved), str(junction))
                self.addCleanup(os.rmdir, str(junction))
            spellings.update(forward_slashes=(str(manifest).replace("\\", "/"), None),
                             extended=(EXT + str(manifest), None), local_device=("\\\\.\\" + str(manifest), None),
                             long_ordinary=(os.path.join(far, "run_manifest.json"), None),
                             long_extended=(EXT + os.path.join(far, "run_manifest.json"), None),
                             junction=(str(junction / "run_manifest.json"), None))
            self.assertGreater(len(spellings["long_ordinary"][0]), 300)
        else:
            link = self.tmp / "mlink"
            if not link.exists():
                os.symlink(reserved, link)
            spellings["symlink"] = (str(link / "run_manifest.json"), None)
        for name, (spelling, cwd) in spellings.items():
            with self.subTest(name), (contextlib.chdir(cwd) if cwd else contextlib.nullcontext()):
                code, doc, refused = self.serve("--grain", "reference-parameter", "--all", "--manifest", spelling)
                self.assertEqual((code, refused), (0, None), f"MF56A01-03 the local spelling {name} was refused")
                self.assertEqual((doc["rows"], doc["reference_identity"]),
                                 (original["rows"], original["reference_identity"]))


# --------------------------------------------------------------------------------------------- forgeries

class ForgeryTests(World):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.tmp / "f")

    def refused(self, path: Path) -> str | None:
        return self.serve("--grain", "reference-parameter", database=path)[2]

    @staticmethod
    def pick(tables: dict, table: str, **match) -> dict:
        return next(r for r in tables[table] if all(r.get(k) == v for k, v in match.items()))

    def test_record_set_forgeries(self) -> None:
        def omit(t):
            t["estimates"].remove(self.pick(t, "estimates", model_id=rc.MODEL_ELO, orientation="B"))

        def extra(t):
            row = copy.deepcopy(t["scores"][-1])
            row["contest_key"] = "ncaa:999999"
            t["scores"].append(row)

        def duplicate(t):
            t["features"].insert(1, copy.deepcopy(t["features"][0]))

        def reorder(t):
            first = next(i for i, r in enumerate(t["estimates"]) if r["model_id"] == rc.MODEL_ELO)
            t["estimates"][first], t["estimates"][first + 2] = t["estimates"][first + 2], t["estimates"][first]
        for name, records, code in (("omit", omit, "REFERENCE_ESTIMATE_ROW_MISSING"),
                                    ("extra", extra, "REFERENCE_SCORE_ROW_EXTRA"),
                                    ("dup", duplicate, "REFERENCE_DUPLICATE_ROW"),
                                    ("reorder", reorder, "REFERENCE_ORDER_MISMATCH")):
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, records=records)), code)

    def test_count_type_forgeries(self) -> None:
        def float_count(raw):
            line = raw["features"][-1]
            start = line.index('"games":') + len('"games":')
            end = start
            while line[end].isdigit():
                end += 1
            raw["features"][-1] = line[:start] + line[start:end] + ".0" + line[end:]

        def bool_count(raw):
            i = next(i for i, l in enumerate(raw["estimates"]) if '"team_rating_games":' in l)
            line = raw["estimates"][i]
            start = line.index('"team_rating_games":') + len('"team_rating_games":')
            end = start
            while line[end].isdigit():
                end += 1
            raw["estimates"][i] = line[:start] + "true" + line[end:]
        for name, lines in (("fcount", float_count), ("bcount", bool_count)):
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, lines=lines)), "REFERENCE_COUNT_TYPE_INVALID")
        self.assertEqual(self.refused(self.forger.forge("idfloat", document=lambda d: d["table_counts"].update(
            blocks=float(d["table_counts"]["blocks"])))), "REFERENCE_IDENTITY_DOCUMENT_MISMATCH")
        self.assertEqual(self.refused(self.forger.forge("cfrac", document=lambda d: d["table_counts"].update(
            blocks=d["table_counts"]["blocks"] + 0.5))), "REFERENCE_COUNT_MISMATCH")

    def test_semantic_claim_forgeries(self) -> None:
        def both(t, model, mutate):
            key = next(r["contest_key"] for r in t["estimates"] if r["model_id"] == model and r["season"] == 2022)
            for record in t["estimates"]:
                if record["contest_key"] == key and record["model_id"] == model:
                    mutate(record)

        def probability(r):
            p = "0.400000000000" if r["orientation"] == "A" else "0.600000000000"
            r.update(probability=p, opponent_probability=rc.dec_complement(p), game_grain_probability_a="0.400000000000")

        def margin(r):
            m = "3.000000000000" if r["orientation"] == "A" else "-3.000000000000"
            r.update(margin=m, opponent_margin=rc.dec_negation(m), game_grain_margin_a="3.000000000000")

        def incoherent(t):
            self.pick(t, "estimates", model_id=rc.MODEL_LOGISTIC, orientation="A")["probability"] = "0.123456789012"

        def ridge_probability(t):
            for r in t["estimates"]:
                if r["model_id"] == rc.MODEL_RIDGE and r["contest_key"] == t["estimates"][0]["contest_key"]:
                    r["probability"] = "0.500000000000"

        def lineage(t):
            record = next(r for r in t["features"] if r["team"]["contributing"])
            record["team"]["contributing"][0]["points_for"] += 1

        def partition(t):
            self.pick(t, "features", season=2022)["partition"] = "SPLIT-DEV-SEL"

        def metric(t):
            score = next(s for s in t["scores"] if s["model_id"] == rc.MODEL_ELO and s["score_state"] == "SCORED")
            score["brier"] = {"numerator": 1, "denominator": 7}

        def parameter(t):
            self.pick(t, "parameters", model_id=rc.MODEL_LOGISTIC)["coefficients"][0] = "0.000000000001"

        def summary_metric(t):
            row = next(r for r in t["summary"][0]["rows"] if r["scored_games"])
            row["scored_games"] += 1

        def mirror(t):
            t["scores"][0]["orientation"] = "B"

        def leakage(t):
            t["features"][0]["y_a"] = 1

        def protected(t):
            t["labels"][0]["contest_key"] = "ncaa:401"
        cases =[("prob", lambda t: both(t, rc.MODEL_ELO, probability), "REFERENCE_PROBABILITY_MISMATCH"),
                 ("marg", lambda t: both(t, rc.MODEL_RIDGE, margin), "REFERENCE_MARGIN_MISMATCH"),
                 ("model", lambda t: both(t, rc.MODEL_ELO, lambda r: r.update(model_sha256="0" * 64)),
                  "REFERENCE_MODEL_MISMATCH"),
                 ("sample", lambda t: both(t, rc.MODEL_LOGISTIC, lambda r: r.update(
                     sample_state="OUT_OF_FIT_EXPOSED_2023")), "REFERENCE_SAMPLE_STATE_MISMATCH"),
                 ("incoh", incoherent, "REFERENCE_PAIR_INCOHERENT"),
                 ("ridgep", ridge_probability, "REFERENCE_RIDGE_PROBABILITY_INVENTED"),
                 ("lineage", lineage, "REFERENCE_LINEAGE_MISMATCH"),
                 ("part", partition, "REFERENCE_PARTITION_MISMATCH"),
                 ("metric", metric, "REFERENCE_METRIC_MISMATCH"),
                 ("param", parameter, "REFERENCE_PARAMETER_MISMATCH"),
                 ("summ", summary_metric, "REFERENCE_METRIC_MISMATCH"),
                 ("mirror", mirror, "REFERENCE_MIRROR_DOUBLE_COUNT"),
                 ("leak", leakage, "REFERENCE_LABEL_LEAKAGE"),
                 ("prot", protected, "REFERENCE_PROTECTED_KEY")]
        for name, records, code in cases:
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, records=records)), code)

        def json_float(raw):
            i = next(i for i, l in enumerate(raw["estimates"]) if '"probability":"' in l and "ELO" in l)
            raw["estimates"][i] = raw["estimates"][i].replace('"probability":"', '"probability":0.5,"x":"', 1)
        self.assertEqual(self.refused(self.forger.forge("jfloat", lines=json_float)), "REFERENCE_FLOAT_VALUE")

    def test_meta_identity_and_outer_forgeries(self) -> None:
        labels = dict(rc.LABELS, pit_eligibility="PIT_ELIGIBLE")
        models = rc.models_claim()
        models[rc.MODEL_ELO]["definition"] = dict(models[rc.MODEL_ELO]["definition"], version=2)
        for name, meta, code in (("mpit", {"labels": labels}, "REFERENCE_PIT_CLAIM_INVALID"),
                                 ("mmodel", {"models": models}, "REFERENCE_MODEL_MISMATCH"),
                                 ("mscope", {"scope": dict(rc.SCOPE, training_seasons=[2016])},
                                  "REFERENCE_SCOPE_CLAIM_INVALID"),
                                 ("mslice", {"slices": dict(rc.SLICES, NATIONAL="x")}, "REFERENCE_SLICE_CLAIM_INVALID"),
                                 ("mcid", {"content_identity": "0" * 64}, "REFERENCE_CONTENT_IDENTITY_MISMATCH"),
                                 ("mcontract", {"contract_sha256": "0" * 64}, "REFERENCE_CONTRACT_MISMATCH")):
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, meta=meta)), code)
        self.assertEqual(self.refused(self.forger.forge("index", after_blocks=[
            ("UPDATE blocks SET records = records + 1 WHERE ord = ?", (0,))])), "REFERENCE_INDEX_MISMATCH")
        tampered = self.tmp / "t" / "canonical" / rc.POPULATION / "sha256" / self.db.parent.name / rc.DB_FILE
        tampered.parent.mkdir(parents=True)
        shutil.copyfile(self.db, tampered)
        man = self.tmp / "t" / "manifests" / rc.POPULATION / "sha256" / self.db.parent.name / "run_manifest.json"
        man.parent.mkdir(parents=True)
        shutil.copyfile(rc.manifest_path_for(self.db), man)
        with open(tampered, "r+b") as handle:
            handle.seek(200)
            byte = handle.read(1)
            handle.seek(200)
            handle.write(bytes([byte[0] ^ 1]))
        self.assertEqual(self.refused(tampered), "REFERENCE_DATABASE_TAMPERED")
        self.assertEqual(self.serve("--grain", "reference-score", "--expect-identity", "1" * 64)[0::2],
                         (2, "STALE_REFERENCE_IDENTITY"))

    # ---- C56-CONT-01 MF56A01-02: malformed governed shapes are refused for their own cause, never escape the boundary

    def shape_refusal(self, path: Path) -> str | None:
        try:
            return self.serve("--grain", "reference-parameter", database=path)[2]
        except Exception as exc:  # noqa: BLE001 - the reviewed head's escape (MF56A01-02) becomes this test's failure
            return f"UNCAUGHT {type(exc).__name__}: {exc}"[:200]

    def test_malformed_governed_shapes_refuse_for_their_own_cause(self) -> None:
        def first_contributing(t: dict) -> dict:
            return next(r for r in t["features"] if r["team"]["contributing"])

        def side(member: str, field: str, value: object):
            return lambda t: first_contributing(t)[member].__setitem__(field, value)

        def diff(field: str | None, value: object):
            return lambda t: (t["features"][0].__setitem__("differences", value) if field is None else
                              t["features"][0]["differences"].__setitem__(field, value))

        def summary(path: tuple, value: object):
            def apply(t: dict) -> None:
                node = t["summary"][0]
                for part in path[:-1]:
                    node = node[part]
                node[path[-1]] = value
            return apply

        def key(table: str, field: str, value: object):
            return lambda t: t[table][0].__setitem__(field, value)
        lineage, feature, metric = "REFERENCE_LINEAGE_MISMATCH", "REFERENCE_FEATURE_MISMATCH", "REFERENCE_METRIC_MISMATCH"
        count, model, record = "REFERENCE_COUNT_TYPE_INVALID", "REFERENCE_MODEL_MISMATCH", "REFERENCE_RECORD_MISMATCH"
        cases = [
            # the eight manager classes (MF56A01-02) ...
            ("s-miss-bool", side("team", "missing", True), lineage),
            ("s-diff-list", diff(None, ["not a record"]), feature),
            ("s-pop-list", summary(("population",), ["not a record"]), count),
            ("s-row-null", summary(("rows", 0), None), metric),
            ("s-bin-null", summary(("rows", 0, "calibration", 0), None), metric),
            ("s-cmp-str", summary(("comparisons", 0), "not a record"), metric),
            ("s-model-list", key("estimates", "model_id", ["wrong model"]), model),
            ("s-key-list", key("features", "contest_key", ["ncaa:1"]), record),
            # ... and their nearby null/list/bool/scalar/malformed-key neighbours across the governed tables
            ("s-miss-list", side("opponent", "missing", [0]), lineage), ("s-miss-null", side("team", "missing", None),
                                                                          lineage),
            ("s-miss-str", side("team", "missing", "x"), lineage), ("s-miss-int", side("opponent", "missing", 1), lineage),
            ("s-con-bool", side("team", "contributing", True), lineage),
            ("s-con-int", side("team", "contributing", 5), lineage),
            ("s-con-obj", side("opponent", "contributing", {}), lineage),
            ("s-con-item", lambda t: first_contributing(t)["team"]["contributing"].__setitem__(0, "x"), lineage),
            ("s-diff-null", diff(None, None), feature), ("s-diff-str", diff(None, "x"), feature),
            ("s-mv-bool", diff("missing_values", True), feature), ("s-mv-obj", diff("missing_values", {}), feature),
            ("s-pop-str", summary(("population",), "x"), count), ("s-pop-null", summary(("population",), None), count),
            ("s-rows-obj", summary(("rows",), {}), metric), ("s-rows-null", summary(("rows",), None), metric),
            ("s-row-list", summary(("rows", 0), []), metric), ("s-row-str", summary(("rows", 0), "x"), metric),
            ("s-cal-bool", summary(("rows", 0, "calibration"), True), metric),
            ("s-cal-obj", summary(("rows", 0, "calibration"), {}), metric),
            ("s-bin-list", summary(("rows", 0, "calibration", 0), []), metric),
            ("s-cmp-null", summary(("comparisons", 0), None), metric),
            ("s-cmps-bool", summary(("comparisons",), True), metric),
            ("s-model-obj", key("estimates", "model_id", {"m": 1}), model),
            ("s-model-null", key("estimates", "model_id", None), model),
            ("s-model-int", key("scores", "model_id", 5), model),
            ("s-model-par", key("parameters", "model_id", ["x"]), model),
            ("s-key-obj", key("labels", "contest_key", {"k": 1}), record),
            ("s-key-int", key("scores", "contest_key", 5), record),
            ("s-key-null", key("estimates", "contest_key", None), record),
            ("s-key-bool", key("features", "contest_key", True), record),
            # the adjacent controls keep their prior refusals and precedence
            ("s-diag-bool", lambda t: self.pick(t, "parameters", model_id=rc.MODEL_LOGISTIC).__setitem__(
                "diagnostics", True), "REFERENCE_PARAMETER_MISMATCH"),
            ("s-miss-float", lambda t: first_contributing(t)["team"]["missing"].__setitem__("games", 1.0), count),
            ("s-extra", key("features", "manager_unexpected", "extra"), record)]
        for name, records, code in cases:
            with self.subTest(name):
                self.assertEqual(self.shape_refusal(self.forger.forge(name, records=records)), code,
                                 f"MF56A01-02 {name}")
        # genuine empty and missing states stay valid: a cold start's empty contributing list and null rates
        cold = next(f for f in self.derived["features"] if f["cold_start"])
        side_ = cold["team"] if cold["team"]["games"] == 0 else cold["opponent"]
        self.assertEqual((side_["contributing"], side_["win_rate"]), ([], None))
        self.assertIsNone(rc._container_problem("features", cold))
        self.assertIsNone(rc._container_problem("summary", self.derived["summary"]))


# --------------------------------------------------------------------------------------------- mounted genuine

@unittest.skipUnless(rc.REFERENCE_PROFILE is not None and os.environ.get("AGGIE_ANALYTICS_DATA_ROOT"),
                     "the packaged gate pins no reference or no data root is mounted")
class MountedGenuineReferenceTests(unittest.TestCase):
    def test_genuine_reference_serves_every_accepted_target(self) -> None:
        root = Path(os.environ["AGGIE_ANALYTICS_DATA_ROOT"])
        profile = rc.REFERENCE_PROFILE
        db = root / "canonical" / rc.POPULATION / "sha256" / profile["database_identity"] / rc.DB_FILE
        history = root / "canonical" / "national_history_prefix_2016_2023" / "sha256" / \
            rc.ANCHORS["history"]["database_identity"] / "national_history.sqlite"
        parent = root / "canonical" / "national_di_population_2016_2025" / "sha256" / \
            rc.ANCHORS["population"]["database_identity"] / "national_population.sqlite"
        if not db.is_file() or not history.is_file() or not parent.is_file():
            self.skipTest("the mounted data root holds no canonical reference or parents")
        with rc.ReferenceComparison(db, history_database=history, population_database=parent) as ref:
            population = ref.derived["summary"]["population"]
            self.assertEqual(ref.content_identity, profile["content_identity"])
            parameters = ref.query("reference-parameter", all_rows=True)
        self.assertEqual((population["targets"], population["feature_views"], population["pool_games"],
                          population["training_targets"], population["comparison_targets"]),
                         (5875, 11750, 11528, 5087, 788))
        self.assertEqual(population["scores"], 5875 * 5)
        self.assertEqual([p["model_id"] for p in parameters["rows"]], list(rc.MODEL_IDS))


if __name__ == "__main__":
    unittest.main()
