"""BAT-719 (Cycle #47 — Attempt #1, TP47-A01): the explicit retrospective games-only baseline benchmark on tiny owned
worlds.

Every world is real (``retrospective_baseline_fixture``): an accepted-builder parent and history prefix, then the
repository benchmark builder with the committed contract whose history binding names that fixture history. The
producer is the repository builder and the consumer is the query module (``main`` and its verified handle) with the
fixture anchors. The world holds 0, 1 and several prior games, both orientations, a tie target and a tie prior, cold
starts, a same-date doubleheader, a neutral site, a mid-season rename, FCS priors, 2020-21 spring games and protected
2024/2025 contests. Forgeries are coordinated -- block bytes, block index columns, table counts, identity document,
identity directory and manifest are all rewritten consistently -- so each one must be refused by its own rule, never
by a stale outer hash.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import national_history_fixture as hx  # noqa: E402
import retrospective_baseline_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402
from aggie_analytics.retrospective_baseline import query  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
SHA_FIELDS = ("feature_record_sha256", "game_feature_record_sha256")


def frac(value: dict) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def semantic(estimate: dict) -> dict:
    """An estimate without the identities of its (possibly re-hashed) input records."""
    return {k: v for k, v in estimate.items() if k not in SHA_FIELDS}


class World(unittest.TestCase):
    """One accepted fixture world and its benchmark, built once per class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="rb-")
        cls.tmp = Path(cls._tmp.name)
        cls.world = fx.build_world(cls.tmp / "w")
        cls.contract_path = fx.write_contract(cls.tmp / "bc.json", fx.contract_for(cls.world))
        cls.anchors = fx.anchors_for(cls.contract_path, cls.world)
        code, cls.result, stderr = fx.run_build(cls.contract_path, cls.world, cls.tmp / "b")
        if code != 0:
            raise AssertionError(f"benchmark build refused: {stderr}")
        cls.db = fx.database_of(cls.result)
        with bm.RetrospectiveBenchmark(cls.db, history_database=cls.world["history_db"], anchors=cls.anchors) as rb:
            cls.derived = rb.derived

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def est(self, key: str, model: str = bm.MODEL_SMOOTHED, orientation: str = "A") -> dict:
        return next(r for r in self.derived["estimates"] if (r["contest_key"], r["model_id"], r["orientation"]) ==
                    (key, model, orientation))

    def feature(self, key: str, view: str = "A") -> dict:
        return next(r for r in self.derived["features"] if (r["contest_key"], r["view"]) == (key, view))

    def score(self, key: str, model: str = bm.MODEL_SMOOTHED) -> dict:
        return next(r for r in self.derived["scores"] if (r["contest_key"], r["model_id"]) == (key, model))

    def label(self, key: str) -> dict:
        return next(r for r in self.derived["labels"] if r["contest_key"] == key)

    def serve(self, *argv: str, database: Path | None = None, history: Path | None = None) -> tuple[int, dict | None,
                                                                                                   str | None]:
        args = ["--database", str(database or self.db), "--history-database", str(history or self.world["history_db"]),
                *argv]
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(bm, "ANCHORS", self.anchors), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            try:
                code = query.main(args)
            except SystemExit as exc:
                code = exc.code
        return code, (json.loads(out.getvalue()) if out.getvalue().strip() else None), fx.refusal(err.getvalue())


# --------------------------------------------------------------------------------------------- contract

class ContractTests(unittest.TestCase):
    def test_the_committed_contract_equals_the_reader_rules_and_is_pinned(self) -> None:
        contract, sha, anchors = fx.builder().load_contract(fx.CONTRACT_PATH)
        self.assertEqual(sha, bm.ANCHORS["contract_sha256"])
        self.assertEqual(anchors, bm.ANCHORS)
        self.assertEqual(contract["models"], bm.MODELS)
        self.assertEqual(sorted(contract["models"]), sorted(bm.MODEL_IDS))
        self.assertEqual(contract["parent"]["history"]["expected_targets"],
                         {"2016": 733, "2017": 753, "2018": 766, "2019": 769, "2020": 524, "2021": 767, "2022": 775,
                          "2023": 788})
        self.assertEqual(sum(contract["parent"]["history"]["expected_targets"].values()), 5875)
        self.assertIsInstance(contract["numeric_contract"]["independent_tolerance"], str)

    def test_a_contract_with_other_rules_is_refused(self) -> None:
        base = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="rc-") as tmp:
            for name, mutate in (
                    ("formula", lambda c: c["models"][bm.MODEL_SMOOTHED].update(parameters={"pseudo_wins": 2})),
                    ("home_bonus", lambda c: c["models"][bm.MODEL_NULL].update(home_advantage=0.03)),
                    ("numeric", lambda c: c["numeric_contract"].update(independent_tolerance="1E-9")),
                    ("split", lambda c: c["split"]["partitions"][0]["seasons"].append(2024)),
                    ("labels", lambda c: c["labels"].update(pit_eligibility="PIT_ELIGIBLE")),
                    ("scope", lambda c: c["scope"].update(target_seasons=list(range(2016, 2026)))),
                    ("contract_id", lambda c: c.update(contract_id="BAT-719-OTHER")),
                    ("history_contract", lambda c: c["parent"]["history"].update(contract_sha256="0" * 64))):
                contract = copy.deepcopy(base)
                mutate(contract)
                path = fx.write_contract(Path(tmp) / f"{name}.json", contract)
                with self.subTest(name), self.assertRaises(Exception) as caught:
                    fx.builder().load_contract(path)
                self.assertEqual(getattr(caught.exception, "code", None), "CONTRACT_INVALID")


# --------------------------------------------------------------------------------------------- derivation

class DerivationTests(World):
    def test_every_target_has_two_views_four_estimates_one_label_and_two_scores(self) -> None:
        targets = [t["contest_key"] for t in self.derived["targets"]]
        self.assertEqual(targets, ["ncaa:303", "ncaa:102", "ncaa:103", "ncaa:104", "ncaa:105", "ncaa:106", "ncaa:107",
                                   "ncaa:111", "ncaa:114", "ncaa:201", "ncaa:202", "ncaa:205"])
        self.assertEqual(len(self.derived["features"]), 2 * len(targets))
        self.assertEqual(len(self.derived["estimates"]), 4 * len(targets))
        self.assertEqual(len(self.derived["labels"]), len(targets))
        self.assertEqual(len(self.derived["scores"]), 2 * len(targets))
        keys = [bm.record_key("estimates", r) for r in self.derived["estimates"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(self.result["row_counts"], {"estimates.jsonl.gz": 48, "features.jsonl.gz": 24,
                                                     "labels.jsonl.gz": 12, "scores.jsonl.gz": 24, "summary.json": 1})

    def test_zero_one_and_several_prior_games_give_the_exact_frozen_probabilities(self) -> None:
        cold = self.est("ncaa:102")
        self.assertEqual((cold["team_cold_start"], cold["opponent_cold_start"]), (True, True))
        self.assertEqual(frac(cold["team_strength_q"]), Fraction(1, 2))
        self.assertEqual(frac(cold["probability"]), Fraction(1, 2))
        one = self.est("ncaa:103")      # Alpha 1-0-0 against Bravo 0-0-1 (the 2018-09-01 tie)
        self.assertEqual((frac(one["team_strength_q"]), frac(one["opponent_strength_q"])), (Fraction(2, 3), Fraction(1, 2)))
        self.assertEqual(frac(one["probability"]), Fraction(2, 3))
        self.assertEqual(one["probability_decimal"], "0.666666666667")
        several = self.feature("ncaa:111")
        self.assertEqual(several["team"]["contributing_contest_keys"], ["ncaa:101", "ncaa:103", "ncaa:105"])
        self.assertEqual(several["opponent"]["contributing_contest_keys"],
                         ["ncaa:102", "ncaa:104", "ncaa:113", "ncaa:107"])
        team, opp = several["team"], several["opponent"]
        q_a = Fraction(2 * team["wins"] + team["ties"] + 2, 2 * team["games"] + 4)
        q_b = Fraction(2 * opp["wins"] + opp["ties"] + 2, 2 * opp["games"] + 4)
        self.assertEqual(frac(self.est("ncaa:111")["probability"]), q_a * (1 - q_b) / (q_a * (1 - q_b) + q_b * (1 - q_a)))

    def test_both_orientations_are_one_game(self) -> None:
        for est in [r for r in self.derived["estimates"] if r["orientation"] == "A"]:
            mirror = self.est(est["contest_key"], est["model_id"], "B")
            self.assertEqual(frac(est["probability"]) + frac(mirror["probability"]), 1)
            self.assertEqual((mirror["team_key"], mirror["opponent_key"]), (est["opponent_key"], est["team_key"]))
            self.assertEqual(mirror["game_grain_probability_a"], est["probability"])
            self.assertEqual((mirror["team_strength_q"], mirror["opponent_strength_q"]),
                             (est["opponent_strength_q"], est["team_strength_q"]))
            self.assertTrue(0 < frac(est["probability"]) < 1)
            self.assertEqual(frac(est["opponent_probability"]), 1 - frac(est["probability"]))

    def test_a_prior_tie_counts_half_and_the_null_is_one_half_everywhere(self) -> None:
        bravo = self.feature("ncaa:103", "B")["team"]
        self.assertEqual((bravo["games"], bravo["ties"]), (1, 1))
        self.assertEqual(frac(self.est("ncaa:103", orientation="B")["team_strength_q"]), Fraction(1, 2))
        for est in [r for r in self.derived["estimates"] if r["model_id"] == bm.MODEL_NULL]:
            self.assertEqual(frac(est["probability"]), Fraction(1, 2))
            self.assertIsNone(est["team_strength_q"])

    def test_same_date_and_later_contests_never_contribute(self) -> None:
        for key, other in (("ncaa:106", "ncaa:107"), ("ncaa:107", "ncaa:106")):
            bravo = self.feature(key)["team"]   # Bravo plays both on 2018-09-22
            self.assertNotIn(other, bravo["contributing_contest_keys"])
            self.assertNotIn(key, bravo["contributing_contest_keys"])
        dates = {t["contest_key"]: (t["season"], t["contest_date"]) for t in self.derived["targets"]}
        pool = {**dates}
        for feature in self.derived["features"]:
            for side in ("team", "opponent"):
                for prior in feature[side]["contributing_contest_keys"]:
                    if prior in pool:
                        self.assertLess(pool[prior][1], feature["contest_date"])
                        self.assertEqual(pool[prior][0], feature["season"])

    def test_season_identity_spring_rename_neutral_and_fcs_priors_are_retained(self) -> None:
        spring = self.feature("ncaa:205")
        self.assertEqual((spring["season"], spring["contest_date"], spring["partition"]), (2020, "2021-04-03",
                                                                                         "SPLIT-DEV-HIST"))
        self.assertIn("ncaa:202", spring["team"]["contributing_contest_keys"])
        self.assertEqual(self.feature("ncaa:105")["team_name"], "Charlie State")
        self.assertEqual(self.feature("ncaa:104")["team_name"], "Charlie St.")
        self.assertEqual(self.feature("ncaa:103")["target_site"], "NEUTRAL")
        self.assertEqual(self.est("ncaa:103")["probability"], self.est("ncaa:103")["game_grain_probability_a"])
        self.assertIn("ncaa:101", self.feature("ncaa:103")["team"]["contributing_contest_keys"])   # an FCS opponent

    def test_protected_contests_never_enter_any_record(self) -> None:
        for table in bm.RECORD_TABLES:
            for record in self.derived[table]:
                self.assertNotIn(record["contest_key"], ("ncaa:401", "ncaa:402"))
                self.assertIn(record["season"], bm.TARGET_SEASONS)
                self.assertEqual(record["evidence_label"], bm.EVIDENCE_LABEL)
                self.assertEqual(record["pit_eligibility"], bm.PIT_STATE)

    def test_labels_are_separate_and_the_tie_stays_unscored(self) -> None:
        for table in ("features", "estimates"):
            for record in self.derived[table]:
                self.assertFalse(set(bm.LABEL_FIELDS) & set(record))
        tie = self.label("ncaa:102")
        self.assertEqual((tie["label_state"], tie["y_a"], tie["unscored_reason"]), ("TIE", None, "LABEL_TIE"))
        for model in bm.MODEL_IDS:
            score = self.score("ncaa:102", model)
            self.assertEqual((score["score_state"], score["brier"], score["log_loss"], score["unscored_reason"]),
                             ("UNSCORED", None, None, "LABEL_TIE"))
        self.assertEqual(self.label("ncaa:111")["y_a"], 1)
        self.assertEqual(self.label("ncaa:105")["y_a"], 0)

    def test_scores_are_exact_one_per_game_and_model(self) -> None:
        for score in self.derived["scores"]:
            self.assertEqual(score["orientation"], "A")
            if score["score_state"] != "SCORED":
                continue
            p, y = frac(score["probability_a"]), score["y_a"]
            self.assertEqual(frac(score["brier"]), (p - y) ** 2)
            expected = -math.log(p.numerator / p.denominator) if y == 1 else \
                -math.log((p.denominator - p.numerator) / p.denominator)
            self.assertEqual(float(score["log_loss"]), expected)
            self.assertEqual(score["log_loss"], repr(expected))
        null = self.score("ncaa:111", bm.MODEL_NULL)
        self.assertEqual((frac(null["brier"]), null["log_loss"]), (Fraction(1, 4), repr(math.log(2))))

    def test_summary_denominators_partitions_and_comparison(self) -> None:
        rows = {(r["model_id"], r["scope_id"]): r for r in self.derived["summary"]["rows"]}
        pooled = rows[(bm.MODEL_SMOOTHED, "2016-2023")]
        self.assertEqual((pooled["population_targets"], pooled["score_records"], pooled["scored_targets"],
                          pooled["unscored_targets"], pooled["unscored_by_reason"]), (12, 12, 11, 1, {"LABEL_TIE": 1}))
        scored = [s for s in self.derived["scores"] if s["model_id"] == bm.MODEL_SMOOTHED and s["score_state"] == "SCORED"]
        total = sum((frac(s["brier"]) for s in scored), Fraction(0))
        self.assertEqual(frac(pooled["brier_total"]), total)
        self.assertEqual(frac(pooled["brier_mean"]), total / 11)
        self.assertEqual(float(pooled["log_loss_total"]), math.fsum(float(s["log_loss"]) for s in scored))
        self.assertEqual(rows[(bm.MODEL_NULL, "2016-2023")]["brier_mean"], {"numerator": 1, "denominator": 4})
        self.assertEqual(rows[(bm.MODEL_SMOOTHED, "SPLIT-DEV-HIST")]["population_targets"], 12)
        self.assertEqual(rows[(bm.MODEL_SMOOTHED, "SPLIT-DEV-SEL")]["population_targets"], 0)
        self.assertIsNone(rows[(bm.MODEL_SMOOTHED, "SPLIT-DEV-SEL")]["brier_mean"])
        self.assertEqual(rows[(bm.MODEL_SMOOTHED, "2018")]["population_targets"], 8)
        comparison = next(c for c in self.derived["summary"]["comparisons"] if c["scope_id"] == "2016-2023")
        self.assertEqual(frac(comparison["brier_mean_difference_smoothed_minus_null"]), total / 11 - Fraction(1, 4))
        self.assertEqual(len(self.derived["summary"]["rows"]), 2 * 11)


class InvarianceTests(unittest.TestCase):
    """Estimates depend only on features: a later or target outcome change leaves every earlier estimate (and the
    changed target's own estimate) semantically unchanged, while a permitted past-history change moves the comparison
    in the expected direction and leaves the null unchanged."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="ri-")
        cls.tmp = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def derive(self, name: str, change: dict[str, tuple[int, int]] | None = None) -> dict:
        contests = hx.fixture_contests()
        for c in contests:
            if change and c["contest_key"] in change:
                c["a_points"], c["b_points"] = change[c["contest_key"]]
        world = fx.build_world(self.tmp / name, contests)
        contract = fx.write_contract(self.tmp / f"{name}.json", fx.contract_for(world))
        anchors = fx.anchors_for(contract, world)
        return bm.derive(bm.load_history(world["history_db"], anchors), anchors)

    def by_key(self, derived: dict) -> dict:
        return {bm.record_key("estimates", r): semantic(r) for r in derived["estimates"]}

    def test_target_and_later_outcomes_never_change_earlier_estimates(self) -> None:
        base = self.derive("base")
        changed = self.derive("later", {"ncaa:111": (3, 24), "ncaa:114": (27, 30)})
        a, b = self.by_key(base), self.by_key(changed)
        self.assertEqual(sorted(a), sorted(b))
        for key, est in a.items():
            if not key.startswith("ncaa:114|"):     # 111 (and 114) changed outcome; only 114 counts 111 as a prior
                self.assertEqual(b[key], est, key)
        self.assertNotEqual(b["ncaa:114|SMOOTHED_HISTORY_ODDS_V1|A"], a["ncaa:114|SMOOTHED_HISTORY_ODDS_V1|A"])
        self.assertEqual(b["ncaa:114|NULL_HALF_V1|A"], a["ncaa:114|NULL_HALF_V1|A"])
        labels = {lab["contest_key"]: lab["y_a"] for lab in changed["labels"]}
        self.assertEqual((labels["ncaa:111"], labels["ncaa:114"]), (0, 0))

    def test_a_past_result_change_moves_the_comparison_and_never_the_null(self) -> None:
        base = self.derive("base2")
        changed = self.derive("past", {"ncaa:103": (21, 28)})   # Alpha now loses its second game
        a, b = self.by_key(base), self.by_key(changed)
        smoothed = "ncaa:105|SMOOTHED_HISTORY_ODDS_V1|A"        # Charlie (A) against Alpha (B), a week later
        self.assertGreater(frac(b[smoothed]["probability"]), frac(a[smoothed]["probability"]))
        null = "ncaa:105|NULL_HALF_V1|A"
        self.assertEqual(b[null]["probability"], a[null]["probability"])
        self.assertEqual(b["ncaa:102|SMOOTHED_HISTORY_ODDS_V1|A"], a["ncaa:102|SMOOTHED_HISTORY_ODDS_V1|A"])


# --------------------------------------------------------------------------------------------- refused inputs

class InputRefusalTests(World):
    """Self-consistent rehashed history inputs (every outer identity agrees and the anchors pin the forged bytes) are
    refused by the derivation's own semantic rules."""

    def refused(self, name: str, statements: list[tuple[str, tuple]], **anchor_patch: object) -> str | None:
        forged = fx.rehash_history(self.world["history_db"], self.tmp / "hf", name, statements)
        anchors = copy.deepcopy(self.anchors)
        binding = fx.history_binding(forged, self.world["history_contract"])
        anchors["history"].update({k: binding[k] for k in ("database_identity", "sqlite_sha256")}, **anchor_patch)
        try:
            bm.derive(bm.load_history(forged, anchors), anchors)
        except bm.BenchmarkError as exc:
            return exc.code
        return None

    def view_update(self, key: str, view: str, mutate) -> list[tuple[str, tuple]]:
        _ord, record = fx.history_record(self.world["history_db"], "history",
                                         f"target_contest_key = '{key}' AND view = '{view}'")
        mutate(record)
        return [("UPDATE history SET record = ? WHERE target_contest_key = ? AND view = ?",
                 (fx.canonical(record), key, view))]

    def test_count_types_and_sums(self) -> None:
        for name, value in (("float", 1.0), ("bool", True), ("string", "1"), ("negative", -1)):
            with self.subTest(name):
                statements = self.view_update("ncaa:103", "A", lambda r: r["team_history"].update(games=value))
                self.assertEqual(self.refused(f"count_{name}", statements), "BENCHMARK_FEATURE_INPUT_INVALID")

    def test_future_same_date_and_target_leakage(self) -> None:
        def future(r):
            h = r["team_history"]
            h["contributing"].append({"contest_date": "2018-10-13", "contest_key": "ncaa:111", "opponent_key": "org:5",
                                      "opponent_division_label": "FBS", "points_for": 24, "points_against": 3,
                                      "result": "W", "side": "A"})
            h["contributing_contest_keys"].append("ncaa:111")
            h.update(games=h["games"] + 1, wins=h["wins"] + 1)

        def own(r):
            h = r["team_history"]
            h["contributing"].append({"contest_date": "2018-09-08", "contest_key": "ncaa:103", "opponent_key": "org:2",
                                      "opponent_division_label": "FBS", "points_for": 28, "points_against": 21,
                                      "result": "W", "side": "A"})
            h["contributing_contest_keys"].append("ncaa:103")
            h.update(games=h["games"] + 1, wins=h["wins"] + 1)

        def same_date(r):
            h = r["team_history"]
            h["contributing"].append({"contest_date": "2018-09-22", "contest_key": "ncaa:107", "opponent_key": "org:5",
                                      "opponent_division_label": "FBS", "points_for": 17, "points_against": 24,
                                      "result": "L", "side": "A"})
            h["contributing_contest_keys"].append("ncaa:107")
            h.update(games=h["games"] + 1, losses=h["losses"] + 1)
        self.assertEqual(self.refused("future", self.view_update("ncaa:103", "A", future)), "BENCHMARK_FEATURE_LEAKAGE")
        self.assertEqual(self.refused("own", self.view_update("ncaa:103", "A", own)), "BENCHMARK_FEATURE_LEAKAGE")
        self.assertEqual(self.refused("same", self.view_update("ncaa:106", "A", same_date)), "BENCHMARK_FEATURE_LEAKAGE")

    def test_wrong_source_season_mapping_orientation_and_mirror(self) -> None:
        self.assertEqual(self.refused("mapping", self.view_update("ncaa:104", "A",
                                                                  lambda r: r.update(team_name="Charlie State"))),
                         "BENCHMARK_ORIENTATION_INVALID")
        self.assertEqual(self.refused("mirror", self.view_update(
            "ncaa:111", "B", lambda r: r["team_history"].update(points_for_total=999))), "BENCHMARK_ORIENTATION_INVALID")

    def test_a_relabelled_protected_contest_is_refused_for_membership(self) -> None:
        _ord, record = fx.history_record(self.world["history_db"], "targets", "contest_key = 'ncaa:303'")
        record.update(contest_key="ncaa:401", season=2018, contest_date="2018-12-01")
        statements = [("INSERT INTO targets (contest_key, season, contest_date, a_key, b_key, record) VALUES "
                       "(?, ?, ?, ?, ?, ?)", ("ncaa:401", 2018, "2018-12-01", record["a_key"], record["b_key"],
                                              fx.canonical(record)))]
        expected = dict(self.anchors["history"]["expected_targets"])
        expected["2018"] += 1
        self.assertEqual(self.refused("relabel", statements, expected_targets=expected), "BENCHMARK_PROTECTED_KEY")

    def test_a_label_contradicting_the_history_and_a_missing_label(self) -> None:
        _ord, label = fx.history_record(self.world["history_db"], "target_labels", "contest_key = 'ncaa:103'")
        label.update(a_points=21, b_points=28, a_result="L", b_result="W", a_margin=-7)
        self.assertEqual(self.refused("label", [("UPDATE target_labels SET record = ? WHERE contest_key = ?",
                                                 (fx.canonical(label), "ncaa:103"))]), "BENCHMARK_LABEL_INPUT_INVALID")
        # adjacent positive: a missing label is an explicit UNSCORED record, never a dropped target
        forged = fx.rehash_history(self.world["history_db"], self.tmp / "hf", "missing",
                                   [("DELETE FROM target_labels WHERE contest_key = ?", ("ncaa:205",))])
        anchors = copy.deepcopy(self.anchors)
        binding = fx.history_binding(forged, self.world["history_contract"])
        anchors["history"].update({k: binding[k] for k in ("database_identity", "sqlite_sha256")})
        derived = bm.derive(bm.load_history(forged, anchors), anchors)
        missing = next(r for r in derived["scores"] if r["contest_key"] == "ncaa:205")
        self.assertEqual((missing["score_state"], missing["unscored_reason"]), ("UNSCORED", "LABEL_MISSING"))
        self.assertEqual(len(derived["scores"]), 24)

    def test_another_history_than_the_bound_one_is_refused(self) -> None:
        other = fx.rehash_history(self.world["history_db"], self.tmp / "hf", "other",
                                  [("UPDATE target_labels SET record = record || ' ' WHERE contest_key = ?",
                                    ("ncaa:205",))])
        with self.assertRaises(bm.BenchmarkError) as caught:
            bm.load_history(other, self.anchors)
        self.assertEqual(caught.exception.code, "BENCHMARK_HISTORY_MISMATCH")


# --------------------------------------------------------------------------------------------- determinism

class DeterminismTests(World):
    def test_orders_chunks_and_a_resumed_build_give_identical_bytes(self) -> None:
        reference = (self.result["content_identity"], self.result["database_sha256"], self.result["payload_sha256"])
        for name, extra in (("reverse", ["--input-order", "reverse"]), ("shuffle", ["--input-order", "shuffle:47"]),
                            ("chunk1", ["--chunk-size", "1", "--checkpoint-dir", str(self.tmp / "ck1")]),
                            ("chunk17", ["--chunk-size", "17", "--checkpoint-dir", str(self.tmp / "ck17")]),
                            ("chunk257", ["--chunk-size", "257", "--checkpoint-dir", str(self.tmp / "ck257")])):
            with self.subTest(name):
                code, result, stderr = fx.run_build(self.contract_path, self.world, self.tmp / name, *extra)
                self.assertEqual(code, 0, stderr)
                self.assertEqual((result["content_identity"], result["database_sha256"], result["payload_sha256"]),
                                 reference)
        common = ["--chunk-size", "5", "--checkpoint-dir", str(self.tmp / "ck5")]
        code, stopped, _ = fx.run_build(self.contract_path, self.world, self.tmp / "resume", *common,
                                        "--stop-after-chunks", "1")
        self.assertEqual((code, stopped["state"], stopped["completed_chunks"]), (3, "INTERRUPTED_AT_CHECKPOINT", 1))
        self.assertFalse((self.tmp / "resume" / "canonical").exists())
        code, resumed, stderr = fx.run_build(self.contract_path, self.world, self.tmp / "resume", *common, "--resume")
        self.assertEqual(code, 0, stderr)
        self.assertEqual((resumed["content_identity"], resumed["database_sha256"], resumed["resumed"]),
                         (reference[0], reference[1], True))

    def test_materialization_is_create_only(self) -> None:
        code, again, _ = fx.run_build(self.contract_path, self.world, self.tmp / "b")
        self.assertEqual((code, again["state"], again["database"]["state"]),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"))
        manifest = Path(again["database"]["manifest"])
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        root = self.tmp / "collision"
        shutil.copytree(self.tmp / "b", root)
        forged = root / "manifests" / bm.POPULATION / "sha256" / doc["identity"] / "run_manifest.json"
        doc["identity_document"]["table_counts"] = {k: float(v) for k, v in doc["identity_document"]["table_counts"].items()}
        forged.write_text(json.dumps(doc), encoding="utf-8")
        code, _, stderr = fx.run_build(self.contract_path, self.world, root)
        self.assertEqual((code, fx.refusal(stderr)), (2, "REFUSED_IMMUTABLE_COLLISION"))

    def test_a_forked_checkpoint_or_another_history_is_refused(self) -> None:
        directory = self.tmp / "fork"
        code, _, _ = fx.run_build(self.contract_path, self.world, self.tmp / "fork_out", "--chunk-size", "3",
                                  "--checkpoint-dir", str(directory), "--stop-after-chunks", "1")
        self.assertEqual(code, 3)
        chunk = directory / "chunks" / "chunk_000001.gz"
        chunk.write_bytes(chunk.read_bytes() + b"x")
        code, _, stderr = fx.run_build(self.contract_path, self.world, self.tmp / "fork_out", "--chunk-size", "3",
                                       "--checkpoint-dir", str(directory), "--resume")
        self.assertEqual((code, fx.refusal(stderr)), (2, "REFUSED_ALTERED_PREFIX"))
        other = fx.build_world(self.tmp / "w2", [c for c in hx.fixture_contests() if c["contest_key"] != "ncaa:205"])
        other = dict(other, history_contract=self.world["history_contract"])   # only the history bytes differ
        code, _, stderr = fx.run_build(self.contract_path, other, self.tmp / "other")
        self.assertEqual((code, fx.refusal(stderr)), (2, "BENCHMARK_HISTORY_MISMATCH"))


# --------------------------------------------------------------------------------------------- consumer

class ConsumerTests(World):
    def test_every_grain_serves_verified_records_with_exact_paging(self) -> None:
        expected = {"feature": 24, "estimate": 48, "score": 24, "summary": 22 + 11}
        for grain, total in expected.items():
            code, doc, refused = self.serve("--grain", grain, "--all")
            self.assertEqual((code, refused, doc["total"], doc["returned"]), (0, None, total, total))
            self.assertEqual(doc["pit_eligibility"], bm.PIT_STATE)
            self.assertEqual(doc["evidence_label"], bm.EVIDENCE_LABEL)
            self.assertEqual(doc["benchmark_identity"], self.db.parent.name)
        pages = [self.serve("--grain", "estimate", "--limit", "10", "--offset", str(o))[1] for o in range(0, 50, 10)]
        self.assertEqual(sum(p["returned"] for p in pages), 48)
        self.assertEqual([p["next_offset"] for p in pages], [10, 20, 30, 40, None])
        rows = [r for p in pages for r in p["rows"]]
        self.assertEqual(rows, self.serve("--grain", "estimate", "--all")[1]["rows"])

    def test_filters_resolve_names_through_their_own_season(self) -> None:
        # Charlie (org 3) carried both names in 2018 (renamed mid-season): either name or the key selects all three
        # of its 2018 games; a name never reaches another season or organization
        for team in ("org:3", "3", "Charlie St.", "charlie state", "CHARLIE STATE"):
            code, doc, _ = self.serve("--grain", "score", "--team", team, "--model", bm.MODEL_SMOOTHED, "--all")
            self.assertEqual((code, sorted(r["contest_key"] for r in doc["rows"])),
                             (0, ["ncaa:104", "ncaa:105", "ncaa:106"]), team)
        self.assertEqual(self.serve("--grain", "score", "--team", "Charlie St.", "--season", "2017", "--all")[1]["total"],
                         0)
        self.assertEqual(self.serve("--grain", "feature", "--team", "Alpha", "--all")[1]["total"],
                         sum(1 for f in self.derived["features"] if f["team_key"] == "org:1"))
        self.assertEqual(self.serve("--grain", "score", "--team", "No Such Team", "--all")[1]["total"], 0)
        self.assertEqual(self.serve("--grain", "estimate", "--contest", "102", "--all")[1]["total"], 4)
        self.assertEqual(self.serve("--grain", "summary", "--model", bm.MODEL_NULL, "--partition", "SPLIT-DEV-HIST",
                                    "--all")[1]["total"], 1)
        self.assertEqual(self.serve("--grain", "summary", "--season", "2018", "--all")[1]["total"], 3)
        for season, state in ((2024, "PROTECTED_SEASON_NOT_IN_BENCHMARK"), (2026, "FORWARD_SEASON_NOT_IN_BENCHMARK"),
                              (2015, "OUTSIDE_BENCHMARK_SCOPE")):
            doc = self.serve("--grain", "score", "--season", str(season))[1]
            self.assertEqual((doc["season_scope_state"], doc["total"], doc["rows"]), (state, 0, []))

    def test_misuse_is_refused(self) -> None:
        for argv, code in ((["--grain", "score", "--require-pit"], "PIT_ELIGIBILITY_NOT_ESTABLISHED"),
                           (["--grain", "feature", "--model", bm.MODEL_NULL], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "summary", "--team", "org:1"], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "summary", "--contest", "102"], "FILTER_NOT_APPLICABLE"),
                           (["--grain", "score", "--model", "ELO"], "MODEL_UNKNOWN"),
                           (["--grain", "score", "--partition", "SPLIT-PROTECTED"], "PARTITION_UNKNOWN"),
                           (["--grain", "score", "--limit", "-1"], "NEGATIVE_LIMIT"),
                           (["--grain", "score", "--offset", "-1"], "NEGATIVE_OFFSET"),
                           (["--grain", "score", "--contest", "bad\x01key"], "CONTEST_KEY_INVALID"),
                           (["--grain", "score", "--expect-identity", "0" * 64], "STALE_BENCHMARK_IDENTITY")):
            with self.subTest(argv):
                self.assertEqual(self.serve(*argv)[0::2], (2, code))
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                query.main(["--database", "x", "--history-database", "y", "--grain", "score", "--al"])

    def test_the_benchmark_connection_is_read_only_and_nothing_is_created(self) -> None:
        with mock.patch.object(bm, "ANCHORS", self.anchors):
            with bm.RetrospectiveBenchmark(self.db, history_database=self.world["history_db"]) as rb:
                with self.assertRaises(sqlite3.OperationalError):
                    rb.conn.execute("DELETE FROM meta")
        missing = self.tmp / "missing" / bm.POPULATION / "sha256" / ("0" * 64) / bm.DB_FILE
        self.assertEqual(self.serve("--grain", "score", database=missing)[0::2], (2, "BENCHMARK_DATABASE_MISSING"))
        self.assertFalse(missing.parent.exists())

    def test_genuine_rehoused_long_and_extended_copies_serve_the_same_rows(self) -> None:
        identity = self.db.parent.name
        manifest = bm.manifest_path_for(self.db)
        far = os.path.join(str(self.tmp), "long " + "x" * 120, "deeper # % é ' " + "y" * 120, "tail " + "z" * 40)
        target = os.path.join(far, "canonical", bm.POPULATION, "sha256", identity, bm.DB_FILE)
        target_man = os.path.join(far, "manifests", bm.POPULATION, "sha256", identity, "run_manifest.json")
        for src, dst in ((self.db, target), (manifest, target_man)):
            os.makedirs(EXT + os.path.dirname(dst) if WINDOWS else os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, EXT + dst if WINDOWS else dst)
        self.assertGreater(len(target), 300)
        if WINDOWS:   # the class temporary directory cannot remove a tree beyond the classic path limit
            self.addCleanup(shutil.rmtree, EXT + os.path.join(str(self.tmp), "long " + "x" * 120))
        original = self.serve("--grain", "estimate", "--all")[1]
        for spelling in ((EXT + target) if WINDOWS else target, (EXT + str(self.db)) if WINDOWS else str(self.db)):
            code, doc, refused = self.serve("--grain", "estimate", "--all", database=Path(spelling))
            self.assertEqual((code, refused), (0, None))
            self.assertEqual(doc["rows"], original["rows"])
        if WINDOWS:
            dotted = EXT + str(self.tmp / "dot.") + "\\" + bm.DB_FILE
            self.assertEqual(self.serve("--grain", "score", database=Path(dotted))[0::2],
                             (2, "DATABASE_LOCATION_NOT_LITERAL"))
            self.assertEqual(self.serve("--grain", "score", database=Path("\\\\.\\C47NoSuchDevice\\x.sqlite"))[0::2],
                             (2, "DATABASE_LOCATION_UNSUPPORTED"))

    def test_provenance_only_manifest_changes_keep_the_identity(self) -> None:
        identity = self.db.parent.name
        root = self.tmp / "prov"
        db = root / "canonical" / bm.POPULATION / "sha256" / identity / bm.DB_FILE
        db.parent.mkdir(parents=True)
        shutil.copyfile(self.db, db)
        doc = json.loads(bm.manifest_path_for(self.db).read_text(encoding="utf-8"))
        doc["provenance"] = {"rehoused": True, "note": "provenance-only metadata is not identity"}
        man = root / "manifests" / bm.POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps(doc), encoding="utf-8")
        code, served, refused = self.serve("--grain", "summary", "--limit", "1", database=db)
        self.assertEqual((code, refused, served["benchmark_identity"]), (0, None, identity))


# --------------------------------------------------------------------------------------------- forgeries

class ForgeryTests(World):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.tmp / "fg")

    def refused(self, path: Path) -> str | None:
        code, _doc, refused = self.serve("--grain", "score", "--limit", "1", database=path)
        self.assertEqual(code, 2 if refused else 0)
        return refused

    def edit(self, table: str, key: str, mutate) -> callable:
        def apply(tables: dict) -> None:
            record = next(r for r in tables[table] if bm.record_key(table, r) == key)
            mutate(record)
        return apply

    def test_omitted_extra_duplicate_and_reordered_records(self) -> None:
        def drop(table, key):
            return lambda t: t[table].remove(next(r for r in t[table] if bm.record_key(table, r) == key))

        def duplicate(t):
            t["estimates"].insert(1, dict(t["estimates"][0]))

        def extra_label(t):
            extra = dict(t["labels"][-1], contest_key="ncaa:999")
            t["labels"].append(extra)

        def reorder(t):
            t["scores"][0], t["scores"][1] = t["scores"][1], t["scores"][0]
        cases = {"drop_feature": (drop("features", "ncaa:111|B"), "BENCHMARK_FEATURE_ROW_MISSING"),
                 "drop_estimate": (drop("estimates", "ncaa:111|NULL_HALF_V1|B"), "BENCHMARK_ESTIMATE_ROW_MISSING"),
                 "drop_unscored": (drop("scores", "ncaa:102|SMOOTHED_HISTORY_ODDS_V1"), "BENCHMARK_SCORE_ROW_MISSING"),
                 "drop_model": (lambda t: t.update(estimates=[r for r in t["estimates"]
                                                              if r["model_id"] != bm.MODEL_NULL]),
                                "BENCHMARK_ESTIMATE_ROW_MISSING"),
                 "extra_label": (extra_label, "BENCHMARK_LABEL_ROW_EXTRA"),
                 "duplicate": (duplicate, "BENCHMARK_DUPLICATE_ROW"),
                 "reorder": (reorder, "BENCHMARK_ORDER_MISMATCH")}
        for name, (mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, records=mutate)), code)

    def test_semantic_record_forgeries(self) -> None:
        def swap_prob(r):
            r["probability"], r["opponent_probability"] = r["opponent_probability"], r["probability"]

        def leak_target(r):
            r["team"]["contributing_contest_keys"].append(r["contest_key"])

        def leak_future(r):
            r["opponent"]["contributing_contest_keys"].append("ncaa:114")
        label_sha = bm.sha256_bytes(fx.canonical(self.label("ncaa:111")).encode("utf-8"))
        cases = {
            "feature_leak_target": ("features", "ncaa:103|A", leak_target, "BENCHMARK_FEATURE_MISMATCH"),
            "feature_leak_future": ("features", "ncaa:106|A", leak_future, "BENCHMARK_FEATURE_MISMATCH"),
            "team_mapping": ("estimates", "ncaa:105|SMOOTHED_HISTORY_ODDS_V1|A",
                             lambda r: r.update(team_name="Charlie St."), "BENCHMARK_TEAM_MAPPING_MISMATCH"),
            "swapped_probability": ("estimates", "ncaa:103|SMOOTHED_HISTORY_ODDS_V1|A", swap_prob,
                                    "BENCHMARK_ESTIMATE_MISMATCH"),
            "swapped_winner": ("labels", "ncaa:111", lambda r: r.update(a_result="L", y_a=0),
                               "BENCHMARK_LABEL_MISMATCH"),
            "score_flipped": ("scores", "ncaa:105|SMOOTHED_HISTORY_ODDS_V1", lambda r: r.update(y_a=1),
                              "BENCHMARK_LABEL_MISMATCH"),
            "label_of_another_target": ("scores", "ncaa:105|SMOOTHED_HISTORY_ODDS_V1",
                                        lambda r: r.update(label_record_sha256=label_sha), "BENCHMARK_LABEL_MISMATCH"),
            "false_log_loss": ("scores", "ncaa:105|SMOOTHED_HISTORY_ODDS_V1", lambda r: r.update(log_loss="0.5"),
                               "BENCHMARK_SCORE_MISMATCH"),
            "false_brier": ("scores", "ncaa:105|NULL_HALF_V1",
                            lambda r: r.update(brier={"numerator": 1, "denominator": 5}), "BENCHMARK_SCORE_MISMATCH"),
            "false_model_pin": ("estimates", "ncaa:105|SMOOTHED_HISTORY_ODDS_V1|A",
                                lambda r: r.update(model_sha256="a" * 64), "BENCHMARK_MODEL_MISMATCH"),
            "swapped_orientation_keys": ("estimates", "ncaa:105|NULL_HALF_V1|B",
                            lambda r: r.update(team_key=r["opponent_key"], opponent_key=r["team_key"]),
                            "BENCHMARK_TEAM_MAPPING_MISMATCH"),
            "fabricated_cutoff": ("estimates", "ncaa:105|NULL_HALF_V1|A",
                                  lambda r: r.update(forecast_cutoff="2018-09-14T00:00:00Z"),
                                  "BENCHMARK_PIT_CLAIM_INVALID"),
            "pit_claim_record": ("scores", "ncaa:105|NULL_HALF_V1", lambda r: r.update(pit_eligibility="PIT_ELIGIBLE"),
                                 "BENCHMARK_PIT_CLAIM_INVALID"),
            "partition_claim": ("scores", "ncaa:105|NULL_HALF_V1", lambda r: r.update(partition="SPLIT-DEV-SEL"),
                                "BENCHMARK_SPLIT_CLAIM_INVALID"),
            "label_leak": ("estimates", "ncaa:105|NULL_HALF_V1|A", lambda r: r.update(y_a=0),
                           "BENCHMARK_LABEL_LEAKAGE"),
            "count_float": ("features", "ncaa:111|A", lambda r: r["team"].update(games=3.0),
                            "BENCHMARK_FEATURE_COUNT_INVALID"),
            "count_bool": ("features", "ncaa:103|A", lambda r: r["team"].update(wins=True),
                           "BENCHMARK_FEATURE_COUNT_INVALID"),
            "count_string": ("features", "ncaa:111|A", lambda r: r["team"].update(games="3"),
                             "BENCHMARK_FEATURE_COUNT_INVALID"),
            "count_negative": ("features", "ncaa:111|A", lambda r: r["team"].update(losses=-1, games=2),
                               "BENCHMARK_FEATURE_COUNT_INVALID"),
            "float_probability": ("estimates", "ncaa:105|NULL_HALF_V1|A",
                                  lambda r: r.update(probability={"numerator": 1.0, "denominator": 2}),
                                  "BENCHMARK_FLOAT_VALUE"),
            "cold_start_suppressed": ("estimates", "ncaa:102|SMOOTHED_HISTORY_ODDS_V1|A",
                                      lambda r: r.update(team_cold_start=False), "BENCHMARK_ESTIMATE_MISMATCH"),
        }
        for name, (table, key, mutate, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, records=self.edit(table, key, mutate))), code)

    def test_protected_relabel_and_mirrored_double_count(self) -> None:
        def relabel(t):
            row = dict(next(r for r in t["estimates"] if r["contest_key"] == "ncaa:303"), contest_key="ncaa:401")
            t["estimates"].append(row)

        def mirror(t):
            row = dict(t["scores"][0], orientation="B")
            t["scores"].insert(1, row)

        def protected_season(t):
            t["labels"][0]["season"] = 2024
        self.assertEqual(self.refused(self.forger.forge("relabel", records=relabel)), "BENCHMARK_PROTECTED_KEY")
        self.assertEqual(self.refused(self.forger.forge("mirror", records=mirror)), "BENCHMARK_MIRROR_DOUBLE_COUNT")
        self.assertEqual(self.refused(self.forger.forge("season", records=protected_season)),
                         "BENCHMARK_PROTECTED_KEY")

    def test_rehashed_meta_claims(self) -> None:
        summary = self.forger.meta_value("summary")
        bumped = copy.deepcopy(summary)
        bumped["rows"][0]["scored_targets"] += 1
        false_log = copy.deepcopy(summary)
        false_log["rows"][1]["log_loss_mean"] = "0.1"
        models = self.forger.meta_value("models")
        models[bm.MODEL_SMOOTHED]["definition"]["parameters"]["pseudo_games"] = 3
        labels = dict(bm.LABELS, pit_eligibility="PIT_ELIGIBLE")
        protected = dict(bm.LABELS, protected_lane="PROTECTED_RELEASED")
        split = copy.deepcopy(bm.SPLIT)
        split["partitions"][1]["seasons"] = [2023, 2024]
        parent = dict(self.anchors["history"], database_identity="b" * 64)
        cases = {"summary_denominator": ({"summary": bumped}, "BENCHMARK_SUMMARY_MISMATCH"),
                 "summary_log_loss": ({"summary": false_log}, "BENCHMARK_SUMMARY_MISMATCH"),
                 "model_parameters": ({"models": models}, "BENCHMARK_MODEL_MISMATCH"),
                 "pit_claim": ({"labels": labels}, "BENCHMARK_PIT_CLAIM_INVALID"),
                 "protected_claim": ({"labels": protected}, "BENCHMARK_PROTECTED_CLAIM_INVALID"),
                 "split_claim": ({"split": split}, "BENCHMARK_SPLIT_CLAIM_INVALID"),
                 "parent_claim": ({"parent": parent}, "BENCHMARK_PARENT_MISMATCH"),
                 "scope_claim": ({"scope": dict(bm.SCOPE, target_seasons=list(range(2016, 2026)))},
                                 "BENCHMARK_SCOPE_CLAIM_INVALID"),
                 "numeric_claim": ({"numeric_contract": dict(bm.NUMERIC_CONTRACT, independent_tolerance="1E-6")},
                                   "BENCHMARK_NUMERIC_CONTRACT_MISMATCH"),
                 "contract_claim": ({"contract_sha256": "c" * 64}, "BENCHMARK_CONTRACT_MISMATCH"),
                 "content_identity": ({"content_identity": "e" * 64}, "BENCHMARK_CONTENT_IDENTITY_MISMATCH")}
        for name, (meta, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, meta=meta)), code)

    def test_identity_documents_index_columns_and_schema(self) -> None:
        counts = self.forger.manifest["identity_document"]["table_counts"]
        cases = {
            "doc_extra_member": ({"document": {"pit_eligibility": "PIT_ELIGIBLE"}}, "BENCHMARK_IDENTITY_DOCUMENT_MISMATCH"),
            "doc_float_counts": ({"document": {"table_counts": {k: float(v) for k, v in counts.items()}}},
                                 "BENCHMARK_IDENTITY_DOCUMENT_MISMATCH"),
            "doc_one_float_count": ({"document": {"table_counts": {**counts, "blocks": float(counts["blocks"])}}},
                                    "BENCHMARK_IDENTITY_DOCUMENT_MISMATCH"),
            "doc_extra_output": ({"document": lambda d: d["outputs"].update({"fabricated_evidence.json": "f" * 64})},
                                 "BENCHMARK_IDENTITY_DOCUMENT_MISMATCH"),
            "doc_contract": ({"document": {"contract_sha256": "c" * 64}}, "BENCHMARK_CONTRACT_MISMATCH"),
            "index_records": ({"after_blocks": [("UPDATE blocks SET records = records + 1 WHERE ord = 0", ())]},
                              "BENCHMARK_INDEX_MISMATCH"),
            "schema_extra_table": ({"statements": ["CREATE TABLE extra (x TEXT)"]}, "BENCHMARK_SCHEMA_UNSUPPORTED"),
        }
        for name, (kwargs, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused(self.forger.forge(name, **kwargs)), code)

    def test_outer_identity_refusals(self) -> None:
        identity = self.db.parent.name
        root = self.tmp / "outer"
        tampered = root / "t" / "canonical" / bm.POPULATION / "sha256" / identity / bm.DB_FILE
        tampered.parent.mkdir(parents=True)
        data = bytearray(self.db.read_bytes())
        data[-100] ^= 1
        tampered.write_bytes(bytes(data))
        man = root / "t" / "manifests" / bm.POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        shutil.copyfile(bm.manifest_path_for(self.db), man)
        no_manifest = root / "n" / "canonical" / bm.POPULATION / "sha256" / identity / bm.DB_FILE
        no_manifest.parent.mkdir(parents=True)
        shutil.copyfile(self.db, no_manifest)
        mismatch = root / "m" / "canonical" / bm.POPULATION / "sha256" / identity / bm.DB_FILE
        mismatch.parent.mkdir(parents=True)
        shutil.copyfile(self.db, mismatch)
        doc = json.loads(bm.manifest_path_for(self.db).read_text(encoding="utf-8"))
        doc["identity_document"]["table_counts"]["meta"] += 1
        man2 = root / "m" / "manifests" / bm.POPULATION / "sha256" / identity / "run_manifest.json"
        man2.parent.mkdir(parents=True)
        man2.write_text(json.dumps(doc), encoding="utf-8")
        elsewhere = root / "e" / bm.DB_FILE
        elsewhere.parent.mkdir(parents=True)
        shutil.copyfile(self.db, elsewhere)
        for path, code in ((tampered, "BENCHMARK_DATABASE_TAMPERED"), (no_manifest, "BENCHMARK_MANIFEST_MISSING"),
                           (mismatch, "BENCHMARK_IDENTITY_MISMATCH"), (elsewhere, "BENCHMARK_LOCATION_INVALID")):
            with self.subTest(code):
                self.assertEqual(self.refused(path), code)
        other = fx.rehash_history(self.world["history_db"], self.tmp / "hf2", "other",
                                  [("UPDATE target_labels SET record = record || ' ' WHERE contest_key = ?",
                                    ("ncaa:205",))])
        self.assertEqual(self.serve("--grain", "score", history=other)[0::2], (2, "BENCHMARK_HISTORY_MISMATCH"))


if __name__ == "__main__":
    unittest.main()
