"""BAT-736 national frozen shallow-tree comparison (Cycle #65 TP65-A01): rules, arithmetic, tree structure, build,
reader, query, precedence, coordinated forgeries, locations and the unchanged legacy query surface.

Every world is the accepted builders' tiny invented world (``shallow_boosting_fixture``) with a genuine C56-format parent;
the test runtime has no modeling backend, so builds use the fixture's invented (never fitted) trees. No real data is read
except the committed contract, module and gate artifact of this checkout.
"""
from __future__ import annotations

import copy
import decimal
import io
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zlib
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import shallow_boosting_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import boosting_build as bb  # noqa: E402
from aggie_analytics.retrospective_baseline import boosting_comparison as bc  # noqa: E402
from aggie_analytics.retrospective_baseline import boosting_query as bq  # noqa: E402
from aggie_analytics.retrospective_baseline import query as q  # noqa: E402

CONTRACT = ROOT / bc.CONTRACT_REL
GATE = ROOT / "artifacts" / "data_lake" / "national_shallow_boosting_comparison_2016_2023_gate.json"


def _code(fn, *args, **kwargs) -> str | None:
    try:
        fn(*args, **kwargs)
    except bc.BoostingError as exc:
        return exc.code
    return None


class _World(unittest.TestCase):
    """One built world per test class (the accepted builders' tiny world and its canonical release)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="sbc")
        cls.base = Path(cls._tmp.name)
        cls.world = fx.build_world(cls.base / "w")
        cls.contract = fx.contract_for(cls.world)
        cls.contract_path = fx.write_contract(cls.base / "c.json", cls.contract)
        cls.anchors = {**fx.contract_anchors(cls.contract_path), "profile": None}
        code, result, err = fx.run_build(cls.contract_path, cls.world, cls.base / "o")
        if code != 0:
            raise AssertionError(f"fixture build refused: {err}")
        cls.result = result
        cls.db = fx.database_of(result)
        cls.reader = bc.BoostingComparison(cls.db, anchors=cls.anchors)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def ask(self, *argv: str, anchors=None, database=None):
        return fx.query(anchors or self.anchors, database or self.db, *argv)

    def refused(self, *argv: str, anchors=None, database=None) -> str | None:
        code, doc, err = self.ask(*argv, anchors=anchors, database=database)
        self.assertEqual(code, 2, err)
        self.assertIsNone(doc)
        return fx.refusal(err)


class RulesTests(unittest.TestCase):
    def test_committed_contract_restates_the_frozen_rules_and_parent_pin(self) -> None:
        raw = CONTRACT.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        self.assertEqual(contract["schema"], bb.CONTRACT_SCHEMA)
        self.assertEqual(bc.canonical_json_bytes(contract["rules"]), bc.canonical_json_bytes(bc.rules_document()))
        self.assertEqual(contract["rules_sha256"], bc.rules_sha256())
        self.assertEqual(bc.ANCHORS["contract_sha256"], bc.sha256_bytes(raw))
        self.assertEqual({k: bc.ANCHORS[k] for k in bb.ANCHOR_KEYS}, {k: contract[k] for k in bb.ANCHOR_KEYS})
        pin = contract["parent"]
        self.assertEqual((pin["database_identity"], pin["sqlite_sha256"], pin["bytes"], pin["content_identity"]),
                         ("ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
                          "17a0776587eb30918903dc0d38c736958b1984feb4b40379bbfc80425035785d", 10584064,
                          "fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0"))
        self.assertEqual(pin["record_counts"], {"features": 11750, "estimates": 58750, "labels": 5875,
                                                "parameters": 5, "scores": 29375, "summary": 1})
        expected = contract["expected"]
        self.assertEqual(expected["counts"], {"features": 11750, "labels": 5875, "parameters": 2, "estimates": 23500,
                                              "scores": 41125, "summary": 308})
        self.assertEqual((expected["games"], expected["fit_games"], expected["comparison_games"]), (5875, 5087, 788))
        self.assertEqual(expected["y_a_counts"], {"1": 2843, "0": 3032})
        self.assertEqual(expected["label_states"], {"DECISIVE": 5875, "TIE": 0})

    def test_exactly_two_frozen_definitions_with_every_option_explicit(self) -> None:
        self.assertEqual(bc.TREE_MODELS, ("HIST_GB_DEPTH2_V1", "HIST_GB_DEPTH3_V1"))
        for model_id, depth in zip(bc.TREE_MODELS, (2, 3)):
            params = bc.TREE_PARAMS[model_id]
            self.assertEqual(len(params), 21)
            self.assertEqual((params["max_depth"], params["max_iter"], params["learning_rate"], params["random_state"],
                              params["early_stopping"], params["class_weight"]), (depth, 100, 0.05, 0, False, None))
        self.assertEqual(bc.MODEL_IDS[-2:], bc.TREE_MODELS)
        self.assertEqual(len(bc.MODEL_IDS), 7)

    def test_gate_equals_the_pinned_profile(self) -> None:
        if bc.BOOSTING_PROFILE is None:
            self.assertFalse(GATE.exists())
            return
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["profile"], bc.BOOSTING_PROFILE)
        self.assertEqual(gate["contract_sha256"], bc.ANCHORS["contract_sha256"])
        self.assertEqual(gate["labels"], bc.LABELS)

    def test_rules_document_is_a_deep_copy(self) -> None:
        doc = bc.rules_document()
        doc["models"][bc.TREE_DEPTH2]["constructor"]["max_depth"] = 9
        self.assertEqual(bc.TREE_PARAMS[bc.TREE_DEPTH2]["max_depth"], 2)
        self.assertEqual(bc.rules_document()["models"][bc.TREE_DEPTH2]["constructor"]["max_depth"], 2)


class ArithmeticTests(unittest.TestCase):
    def test_served_pair_rounds_a_once_and_b_is_its_exact_complement(self) -> None:
        a, b = bc.served_pair(0.6, 0.3)
        self.assertEqual((a, b), ("0.650000000000", "0.350000000000"))
        a, b = bc.served_pair(0.12345678901249, 0.9)
        self.assertEqual(Fraction(decimal.Decimal(a)) + Fraction(decimal.Decimal(b)), 1)
        self.assertEqual(bc.served_pair(0.0, 1.0), ("0.000000000000", "1.000000000000"))
        self.assertEqual(bc.served_pair(1.0, 0.0), ("1.000000000000", "0.000000000000"))
        p = (0.7 + (1.0 - 0.2)) / 2.0
        want = decimal.Decimal.from_float(p).quantize(decimal.Decimal("0.000000000001"),
                                                      rounding=decimal.ROUND_HALF_EVEN)
        self.assertEqual(bc.served_pair(0.7, 0.2)[0], format(want, "f"))
        for bad in (math.nan, math.inf, -0.1, 1.5):
            self.assertEqual(_code(bc.served_pair, bad, 0.5), "TREE_ESTIMATE_MISMATCH")
        self.assertEqual(_code(bc.served_pair, True, 0.5), "TREE_ESTIMATE_MISMATCH")

    def test_ambient_decimal_context_is_neither_read_nor_changed(self) -> None:
        want = bc.served_pair(0.613579246801, 0.27)
        with decimal.localcontext() as ctx:
            ctx.prec = 2
            ctx.rounding = decimal.ROUND_DOWN
            ctx.traps[decimal.Inexact] = True
            ctx.traps[decimal.Rounded] = True
            ctx.flags[decimal.Clamped] = True
            before = (ctx.prec, ctx.rounding, dict(ctx.traps), dict(ctx.flags))
            self.assertEqual(bc.served_pair(0.613579246801, 0.27), want)
            self.assertEqual(bc.dec12(0.1), "0.100000000000")
            after = (decimal.getcontext().prec, decimal.getcontext().rounding, dict(decimal.getcontext().traps),
                     dict(decimal.getcontext().flags))
            self.assertEqual(before, after)

    def test_decimal_displays_and_rationals(self) -> None:
        self.assertEqual(bc.decimal_text(Fraction(1, 3)), "0.333333333333")
        self.assertEqual(bc.decimal_text(Fraction(-1, 10 ** 13)), "0.000000000000")
        self.assertEqual(bc.decimal_text(Fraction(5, 10 ** 13)), "0.000000000000")
        self.assertEqual(bc.decimal_text(Fraction(15, 10 ** 13)), "0.000000000002")
        self.assertEqual(bc.dec12(-0.0), "0.000000000000")
        self.assertEqual(_code(bc.dec12, math.inf), "TREE_SUMMARY_MISMATCH")

    def test_log_loss_clips_only_the_logarithm_argument(self) -> None:
        self.assertEqual(bc.log_loss_value(Fraction(1), 1), -math.log(1.0 - 1e-15))
        self.assertEqual(bc.log_loss_value(Fraction(0), 1), -math.log(1e-15))
        self.assertEqual(bc.log_loss_value(Fraction(1, 4), 0), -math.log(0.75))

    def test_stable_sigmoid_and_frozen_traversal(self) -> None:
        self.assertEqual(bc.sigmoid(0.0), 0.5)
        self.assertEqual(bc.sigmoid(800.0), 1.0)
        self.assertEqual(bc.sigmoid(-800.0), 0.0)
        leaf = {"value": 0.0, "count": 1, "feature_idx": 0, "num_threshold": 0.0, "missing_go_to_left": False,
                "left": 0, "right": 0, "gain": -1.0, "depth": 1, "is_leaf": True, "bin_threshold": 0,
                "is_categorical": False, "bitset_idx": 0}
        root = {**leaf, "is_leaf": False, "depth": 0, "feature_idx": 3, "num_threshold": 1.0, "left": 1, "right": 2,
                "missing_go_to_left": True, "gain": 1.0}
        stage = [root, {**leaf, "value": 0.25}, {**leaf, "value": -0.5}]
        export = {"baseline": 0.125, "stages": [copy.deepcopy(stage) for _ in range(100)]}
        baseline, compiled, counts = bc.compile_trees(bc.TREE_DEPTH2, export["baseline"], export["stages"])
        self.assertEqual(counts, {"node_count": 300, "leaf_count": 200, "max_depth_seen": 1})
        x = [0.0] * 10
        x[3] = 1.0  # <= threshold goes left
        z, value = bc.traverse(baseline, compiled, x)
        self.assertEqual(z, 0.125 + sum([0.25] * 100))
        self.assertEqual(value, bc.sigmoid(z))
        x[3] = 1.0000000000000002
        self.assertEqual(bc.traverse(baseline, compiled, x)[0], 0.125 + sum([-0.5] * 100))
        x[3] = math.nan  # a synthetic NaN follows missing_go_to_left
        self.assertEqual(bc.traverse(baseline, compiled, x)[0], 0.125 + sum([0.25] * 100))

    def test_a_nonfinite_intermediate_margin_refuses(self) -> None:
        leaf = {"value": 1e308, "count": 1, "feature_idx": 0, "num_threshold": 0.0, "missing_go_to_left": False,
                "left": 0, "right": 0, "gain": -1.0, "depth": 0, "is_leaf": True, "bin_threshold": 0,
                "is_categorical": False, "bitset_idx": 0}
        stages = [[dict(leaf)] for _ in range(100)]
        stages[3][0]["value"] = -1e308
        baseline, compiled, _counts = bc.compile_trees(bc.TREE_DEPTH2, 0.0, stages)
        with self.assertRaises(bc.BoostingError) as caught:
            bc.traverse(baseline, compiled, [0.0] * 10)
        self.assertEqual(caught.exception.code, "TREE_ESTIMATE_MISMATCH")
        self.assertIn("TREE_MARGIN_NONFINITE", str(caught.exception))

    def test_raw_witness_text_must_be_its_canonical_repr(self) -> None:
        self.assertEqual(bc.repr_float("0.5"), 0.5)
        self.assertEqual(bc.repr_float(repr(0.1 + 0.2)), 0.1 + 0.2)
        for bad in ("0.50", "nan", "inf", "1e999", " 0.5", "0.5\n", 0.5, None, True, "x" * 40):
            self.assertIsNone(bc.repr_float(bad))


class TreeStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.export = fx.synthetic_export(bc.TREE_DEPTH3, 3)

    def refuse(self, mutate) -> str | None:
        export = copy.deepcopy(self.export)
        mutate(export)
        return _code(bc.compile_trees, bc.TREE_DEPTH3, export["baseline"], export["stages"])

    def first_internal(self, export):
        for nodes in export["stages"]:
            for i, node in enumerate(nodes):
                if not node["is_leaf"] and len(nodes) >= 5:
                    return nodes, i
        raise AssertionError("no internal node")

    def test_genuine_export_compiles(self) -> None:
        _b, _c, counts = bc.compile_trees(bc.TREE_DEPTH3, self.export["baseline"], self.export["stages"])
        self.assertLessEqual(counts["max_depth_seen"], 3)

    def test_every_structural_rule_refuses_for_its_own_cause(self) -> None:
        def cycle(e):
            nodes, i = self.first_internal(e)
            nodes[nodes[i]["left"]] = {**nodes[i], "depth": nodes[i]["depth"] + 1, "left": i, "right": nodes[i]["right"]}

        def shared(e):
            nodes, i = self.first_internal(e)
            nodes[i]["right"] = nodes[i]["left"]

        def dangling(e):
            e["stages"][0].append({**e["stages"][0][-1]})

        def child_out_of_range(e):
            nodes, i = self.first_internal(e)
            nodes[i]["right"] = len(nodes)

        def feature(e):
            nodes, i = self.first_internal(e)
            nodes[i]["feature_idx"] = 10

        def bool_count(e):
            e["stages"][0][0]["count"] = True

        def float_count(e):
            e["stages"][0][0]["count"] = 3.0

        def leaf_children(e):
            nodes = e["stages"][0]
            leaf = next(n for n in nodes if n["is_leaf"])
            leaf["left"] = 1

        def categorical(e):
            e["stages"][0][0]["is_categorical"] = True

        def stages(e):
            e["stages"].pop()

        def nonfinite(e):
            e["stages"][0][0]["num_threshold"] = math.inf

        def baseline(e):
            e["baseline"] = 1

        def extra_field(e):
            e["stages"][0][0]["callable"] = "os.system"

        def depth(e):
            nodes, i = self.first_internal(e)
            nodes[i]["depth"] += 1

        for mutate in (cycle, shared, dangling, child_out_of_range, feature, bool_count, float_count, leaf_children,
                       categorical, stages, nonfinite, baseline, extra_field, depth):
            self.assertEqual(self.refuse(mutate), "TREE_STRUCTURE_MISMATCH", mutate.__name__)

    def test_depth_and_leaf_bounds_follow_the_model(self) -> None:
        deep = fx.synthetic_export(bc.TREE_DEPTH3, 11)
        if any(n["depth"] == 3 for nodes in deep["stages"] for n in nodes):
            self.assertEqual(_code(bc.compile_trees, bc.TREE_DEPTH2, deep["baseline"], deep["stages"]),
                             "TREE_STRUCTURE_MISMATCH")


class BuildTests(_World):
    def test_release_counts_follow_the_parent(self) -> None:
        games = self.reader.games
        counts = self.result["row_counts"]
        self.assertEqual(counts["features"], 2 * len(games))
        self.assertEqual(counts["labels"], len(games))
        self.assertEqual(counts["estimates"], 4 * len(games))
        self.assertEqual(counts["scores"], 7 * len(games))
        self.assertEqual(counts["parameters"], 2)
        census = self.reader.records["parameters"][0]["training"]
        fit_decisive = sum(1 for g in games if g["partition"] == bc.PARTITION_FIT and g["label_state"] == "DECISIVE")
        self.assertEqual((census["games"], census["oriented_rows"], census["positive_rows"]),
                         (fit_decisive, 2 * fit_decisive, fit_decisive))
        self.assertGreaterEqual(census["excluded_tie_games"], 1)
        self.assertEqual(census["comparison_games_excluded"],
                         sum(1 for g in games if g["partition"] == bc.PARTITION_COMPARISON))
        self.assertEqual(self.result["reader_check"]["verified"], True)

    def test_identical_rebuild_and_order_chunk_resume_variants_reproduce_every_byte(self) -> None:
        code, again, err = fx.run_build(self.contract_path, self.world, self.base / "o")
        self.assertEqual((code, again["state"]), (0, "ALREADY_PRESENT_IDENTICAL"), err)
        identity = self.result["database_identity"]
        for order in ("reverse", "shuffle:7"):
            code, other, err = fx.run_build(self.contract_path, self.world, self.base / f"v{order[:3]}",
                                            "--input-order", order)
            self.assertEqual((code, other["database_identity"]), (0, identity), err)
        ck = self.base / "ck"
        code, part, err = fx.run_build(self.contract_path, self.world, self.base / "vck", "--chunk-size", "5",
                                       "--checkpoint-dir", str(ck), "--stop-after-chunks", "1")
        self.assertEqual((code, part["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"), err)
        code, done, err = fx.run_build(self.contract_path, self.world, self.base / "vck", "--chunk-size", "5",
                                       "--checkpoint-dir", str(ck), "--resume")
        self.assertEqual((code, done["database_identity"]), (0, identity), err)

    def test_tie_target_is_unscored_for_probabilities_and_ridge_keeps_its_margin(self) -> None:
        tie = next(g for g in self.reader.games if g["label_state"] == "TIE")
        scores = [s for s in self.reader.records["scores"] if s["contest_key"] == tie["contest_key"]]
        self.assertEqual(len(scores), 7)
        for s in scores:
            if s["model_id"] == bc.PARENT_RIDGE:
                self.assertEqual((s["score_state"], s["margin_label_a"]), ("SCORED", 0))
            else:
                self.assertEqual((s["score_state"], s["y_a"], s["brier"], s["log_loss"]), ("UNSCORED", None, None, None))
        label = next(r for r in self.reader.records["labels"] if r["contest_key"] == tie["contest_key"])
        self.assertEqual((label["y_a"], label["unscored_reason"]), (None, "LABEL_TIE"))

    def test_collision_contract_drift_parent_tamper_and_backend_disagreement_refuse(self) -> None:
        out = self.base / "col"
        code, first, err = fx.run_build(self.contract_path, self.world, out)
        self.assertEqual(code, 0, err)
        released = fx.database_of(first)
        size = released.stat().st_size
        with released.open("r+b") as handle:
            handle.seek(size - 1)
            last = handle.read(1)
            handle.seek(size - 1)
            handle.write(bytes([last[0] ^ 0xFF]))
        code, _r, err = fx.run_build(self.contract_path, self.world, out)
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"))
        drifted = copy.deepcopy(self.contract)
        drifted["rules"]["models"][bc.TREE_DEPTH2]["constructor"]["max_depth"] = 4
        path = fx.write_contract(self.base / "drift.json", drifted)
        code, _r, err = fx.run_build(path, self.world, self.base / "drift")
        self.assertEqual((code, fx.refusal(err)), (2, "CONTRACT_RULES_DRIFT"))
        parent = Path(self.world["reference_db"])
        fake = self.base / "fp" / "canonical" / bc.PARENT_POPULATION / "sha256" / parent.parent.name / bc.PARENT_DB_FILE
        fake.parent.mkdir(parents=True)
        data = bytearray(parent.read_bytes())
        data[-5] ^= 1
        fake.write_bytes(bytes(data))
        world = {**self.world, "reference_db": fake}
        code, _r, err = fx.run_build(self.contract_path, world, self.base / "tamper")
        self.assertEqual((code, fx.refusal(err)), (2, "PARENT_TAMPERED"))

        def disagreeing(rows, views):
            fitted = fx.synthetic_fitter(rows, views)
            fitted[bc.TREE_DEPTH3]["backend_q"][0] += 1e-9
            return fitted

        code, _r, err = fx.run_build(self.contract_path, self.world, self.base / "dis", fitter=disagreeing)
        self.assertEqual((code, fx.refusal(err)), (2, "BACKEND_DISAGREEMENT"))

    def test_population_drift_refuses_before_any_fit(self) -> None:
        drifted = copy.deepcopy(self.contract)
        drifted["expected"]["fit_games"] += 1
        path = fx.write_contract(self.base / "pdrift.json", drifted)
        calls = []
        code, _r, err = fx.run_build(path, self.world, self.base / "pd",
                                     fitter=lambda rows, views: calls.append(1) or fx.synthetic_fitter(rows, views))
        self.assertEqual((code, fx.refusal(err), calls), (2, "REFUSED_POPULATION_DRIFT", []))

    def test_training_rows_use_only_decisive_fit_games_a_then_b(self) -> None:
        rows = bc.training_rows(self.reader.games)
        fit = [g for g in self.reader.games if g["partition"] == bc.PARTITION_FIT and g["label_state"] == "DECISIVE"]
        self.assertEqual(len(rows), 2 * len(fit))
        for i, g in enumerate(fit):
            self.assertEqual(rows[2 * i], (g["x_a"], g["y_a"], 0.5))
            self.assertEqual(rows[2 * i + 1], (g["x_b"], 1 - g["y_a"], 0.5))
            self.assertEqual(g["design_b"], [-v for v in g["design_a"]])
        self.assertFalse(any(g["season"] == 2023 for g in fit))


class QueryTests(_World):
    def test_every_grain_serves_its_complete_collection(self) -> None:
        for grain, table in bc.GRAINS.items():
            code, doc, err = self.ask("--grain", grain, "--all")
            self.assertEqual(code, 0, err)
            want = len(self.reader.records[table]) if grain != "tree-summary" else \
                sum(1 for r in self.reader.records["summary"] if r["slice"] == "NATIONAL")
            self.assertEqual((doc["total"], doc["returned"], doc["next_offset"]), (want, want, None))
            self.assertEqual((doc["pit_eligibility"], doc["predictive_skill"], doc["trust_state"]),
                             ("PIT_NOT_ADMITTED", "NOT_ESTABLISHED", "UNTRUSTED_SHADOW"))

    def test_filters_intersect_canonical_games_and_team_matches_either_participant(self) -> None:
        game = next(g for g in self.reader.games if g["texas_am_game"])
        _c, doc, _e = self.ask("--grain", "tree-feature", "--contest", game["contest_key"], "--all")
        self.assertEqual([r["view"] for r in doc["rows"]], ["A", "B"])
        _c, doc, _e = self.ask("--grain", "tree-feature", "--team", "org:697", "--all")
        keys = {r["contest_key"] for r in doc["rows"]}
        self.assertEqual(keys, {g["contest_key"] for g in self.reader.games if "org:697" in (g["a_key"], g["b_key"])})
        self.assertEqual(doc["total"], 2 * len(keys))
        _c, by_name, _e = self.ask("--grain", "tree-feature", "--team", "  tExAs a&M ", "--all")
        self.assertEqual(by_name["total"], doc["total"])
        _c, digits, _e = self.ask("--grain", "tree-feature", "--team", "697", "--all")
        self.assertEqual(digits["total"], doc["total"])
        _c, scores, _e = self.ask("--grain", "tree-score", "--contest", game["contest_key"], "--all")
        self.assertEqual([r["model_id"] for r in scores["rows"]], list(bc.MODEL_IDS))
        _c, est, _e = self.ask("--grain", "tree-estimate", "--contest", game["contest_key"], "--all")
        self.assertEqual([(r["orientation"], r["model_id"]) for r in est["rows"]],
                         [(v, m) for v in bc.VIEWS for m in bc.TREE_MODELS])
        a, b = est["rows"][0], est["rows"][2]
        self.assertEqual((a["raw_q_a_repr"], a["raw_q_b_repr"]), (b["raw_q_a_repr"], b["raw_q_b_repr"]))
        self.assertEqual(Fraction(decimal.Decimal(a["probability"])) + Fraction(decimal.Decimal(b["probability"])), 1)
        _c, part, _e = self.ask("--grain", "tree-estimate", "--partition", "COMPARISON_EXPOSED_2023", "--all")
        self.assertEqual({r["season"] for r in part["rows"]}, {2023})

    def test_unknown_and_disjoint_selections_have_no_rows(self) -> None:
        for argv in (("--grain", "tree-score", "--team", "org:999999"), ("--grain", "tree-score", "--team", "Nobody"),
                     ("--grain", "tree-score", "--contest", "ncaa:1"), ("--grain", "tree-score", "--season", "2019"),
                     ("--grain", "tree-estimate", "--model", "NULL_HALF_V1"),
                     ("--grain", "tree-score", "--model", "UNKNOWN_MODEL_1"),
                     ("--grain", "tree-score", "--season", "2023", "--partition", "FIT_2016_2022"),
                     ("--grain", "tree-summary", "--season", "2019"), ("--grain", "tree-parameter", "--model", "ZED")):
            code, doc, err = self.ask(*argv)
            self.assertEqual((code, doc["total"], doc["returned"], doc["rows"], doc["next_offset"]),
                             (0, 0, 0, [], None), (argv, err))

    def test_summary_selection_recomputes_over_the_selected_games(self) -> None:
        _c, full, _e = self.ask("--grain", "tree-summary", "--slice", "TEXAS_AM", "--all")
        _c, team, _e = self.ask("--grain", "tree-summary", "--team", "org:697", "--slice", "TEXAS_AM", "--all")
        self.assertEqual([r["summary_key"] for r in full["rows"]], [r["summary_key"] for r in team["rows"]])
        self.assertEqual([r["brier_total"] for r in full["rows"]], [r["brier_total"] for r in team["rows"]])
        game = next(g for g in self.reader.games if g["season"] == 2023 and g["label_state"] == "DECISIVE")
        _c, one, _e = self.ask("--grain", "tree-summary", "--contest", game["contest_key"], "--all")
        self.assertEqual({r["scope"] for r in one["rows"]}, {"POOLED", "COMPARISON_EXPOSED_2023", "SEASON_2023"})
        self.assertTrue(all(r["games"] == 1 for r in one["rows"]))
        tree = next(r for r in one["rows"] if r["model_id"] == bc.TREE_DEPTH2 and r["scope"] == "POOLED")
        score = next(s for s in self.reader.records["scores"]
                     if s["contest_key"] == game["contest_key"] and s["model_id"] == bc.TREE_DEPTH2)
        self.assertEqual(tree["brier_total"], score["brier"])
        self.assertEqual(len(tree["comparisons"]), 4)
        _c, model, _e = self.ask("--grain", "tree-summary", "--model", bc.TREE_DEPTH3)
        self.assertTrue(all(r["model_id"] == bc.TREE_DEPTH3 and r["slice"] == "NATIONAL" for r in model["rows"]))

    def test_paging_is_exact(self) -> None:
        _c, doc, _e = self.ask("--grain", "tree-score", "--limit", "0", "--offset", "3")
        self.assertEqual((doc["rows"], doc["returned"], doc["next_offset"]), ([], 0, 3))
        total = doc["total"]
        _c, doc, _e = self.ask("--grain", "tree-score", "--limit", "0", "--offset", str(total))
        self.assertIsNone(doc["next_offset"])
        _c, doc, _e = self.ask("--grain", "tree-score", "--limit", "4", "--offset", "2")
        self.assertEqual((doc["returned"], doc["next_offset"]), (4, 6))
        _c, doc, _e = self.ask("--grain", "tree-score", "--limit", " 5 ", "--offset", str(total - 2))
        self.assertEqual((doc["returned"], doc["next_offset"]), (2, None))
        _c, default, _e = self.ask("--grain", "tree-score")
        self.assertEqual((default["limit"], default["offset"], default["returned"]), (50, 0, min(50, total)))

    def test_direct_interface_accepts_typed_values_and_refuses_before_access(self) -> None:
        doc = self.reader.query("tree-score", season=2023, limit=3, offset=0)
        self.assertEqual(doc["returned"], 3)
        missing = self.base / "nowhere" / "x.sqlite"
        for kwargs, code in (({"grain": "tree-score", "season": 10 ** 5000}, "SEASON_INVALID"),
                             ({"grain": "tree-score", "season": True}, "SEASON_INVALID"),
                             ({"grain": "tree-score", "season": [[[[2019]]]]}, "SEASON_INVALID"),
                             ({"grain": "tree-score", "team": "\ud800Texas"}, "TEAM_INVALID"),
                             ({"grain": "tree-score", "model": 7}, "MODEL_INVALID"),
                             ({"grain": "tree-score", "limit": 10 ** 5000}, "LIMIT_INVALID"),
                             ({"grain": "tree-score", "offset": -(10 ** 5000)}, "OFFSET_INVALID"),
                             ({"grain": "tree-score", "limit": 1.0}, "LIMIT_INVALID"),
                             ({"grain": "tree-score", "limit": False}, "LIMIT_INVALID"),
                             ({"grain": {"x": 1}}, "UNKNOWN_GRAIN"),
                             ({"grain": "tree-score", "expect_identity": 10 ** 5000}, "STALE_TREE_IDENTITY")):
            with self.assertRaises(bc.BoostingError) as caught:
                bc.query(missing, **kwargs)
            self.assertEqual(caught.exception.code, code, kwargs)
            self.assertLess(len(str(caught.exception)), 400)
            self.assertNotIn("\ud800", str(caught.exception))
        self.assertEqual(_code(bc.query, 10 ** 5000, "tree-score"), "TREE_DATABASE_LOCATION_UNSUPPORTED")
        self.assertEqual(_code(bc.query, missing, "tree-score"), "TREE_DATABASE_MISSING")
        self.assertFalse(missing.parent.exists())

    def test_ambiguous_team_name_refuses(self) -> None:
        reader = copy.copy(self.reader)
        reader.names = {k: set(v) for k, v in self.reader.names.items()}
        season = self.reader.games[0]["season"]
        keys = sorted({k for (s, k) in reader.names if s == season})[:2]
        for key in keys:
            reader.names[(season, key)].add("twin")
        self.assertEqual(_code(reader.query, "tree-score", team="Twin"), "TEAM_AMBIGUOUS")


class PrecedenceTests(unittest.TestCase):
    """Every selection, paging and identity refusal precedes any file access (a missing database is never reached)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="sbp")
        cls.missing = str(Path(cls._tmp.name) / "absent" / bc.DB_FILE)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            try:
                code = q.main(list(argv))
            except SystemExit as exc:  # the legacy parser's own accepted argument-error exit
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def code(self, *argv: str) -> str | None:
        code, out, err = self.run_main("--boosting-comparison", self.missing, *argv)
        self.assertEqual((code, out), (2, ""), err)
        lines = err.splitlines()
        self.assertEqual(len(lines), 1)
        doc = json.loads(lines[0])
        self.assertEqual(sorted(doc), ["error", "refused"])
        return doc["refused"]

    def test_frozen_precedence(self) -> None:
        cases = [
            (["--grain", "tree-score", "--database", "x", "--require-pit"], "TREE_MODE_CONFLICT"),
            (["--grain", "tree-score", "--context-association", "x"], "TREE_MODE_CONFLICT"),
            (["--grain", "BAD", "--require-pit", "--as-of", "2020"], "TREE_PIT_NOT_ADMITTED"),
            (["--grain", "BAD", "--as-of", ""], "AS_OF_STATE_NOT_SUPPORTED"),
            (["--grain", "BAD", "--as-of", "99999-99-99T99:99:99+99:99"], "AS_OF_STATE_NOT_SUPPORTED"),
            (["--grain", "BAD", "--season", "x"], "UNKNOWN_GRAIN"),
            (["--grain", "tree-score", "--season", "\x7f2019", "--team", ""], "SEASON_INVALID"),
            (["--grain", "tree-score", "--season", "2019\x85"], "SEASON_INVALID"),
            (["--grain", "tree-score", "--season", "20190"], "SEASON_INVALID"),
            (["--grain", "tree-score", "--team", "", "--contest", "x"], "TEAM_INVALID"),
            (["--grain", "tree-score", "--team", "org:69x"], "TEAM_INVALID"),
            (["--grain", "tree-score", "--team", "\x01org:697"], "TEAM_INVALID"),
            (["--grain", "tree-score", "--contest", "1234", "--model", "bad"], "CONTEST_INVALID"),
            (["--grain", "tree-score", "--contest", "ncaa:1234\x00"], "CONTEST_INVALID"),
            (["--grain", "tree-score", "--model", "bad", "--partition", "x"], "MODEL_INVALID"),
            (["--grain", "tree-score", "--model", ""], "MODEL_INVALID"),
            (["--grain", "tree-score", "--partition", "FIT", "--slice", "x"], "PARTITION_INVALID"),
            (["--grain", "tree-score", "--slice", "BAD"], "SLICE_INVALID"),
            (["--grain", "tree-score", "--slice", "NATIONAL"], "FILTER_NOT_APPLICABLE"),
            (["--grain", "tree-parameter", "--season", "2019"], "FILTER_NOT_APPLICABLE"),
            (["--grain", "tree-feature", "--model", "HIST_GB_DEPTH2_V1"], "FILTER_NOT_APPLICABLE"),
            (["--grain", "tree-score", "--all", "--limit", "0", "--offset", "x"], "PAGING_CONFLICT"),
            (["--grain", "tree-score", "--all", "--offset", "0"], "PAGING_CONFLICT"),
            (["--grain", "tree-score", "--limit", "1.5", "--offset", "-1"], "LIMIT_INVALID"),
            (["--grain", "tree-score", "--limit", "1234567890123"], "LIMIT_INVALID"),
            (["--grain", "tree-score", "--limit", "-1", "--offset", "x"], "NEGATIVE_LIMIT"),
            (["--grain", "tree-score", "--offset", "x", "--expect-identity", "x"], "OFFSET_INVALID"),
            (["--grain", "tree-score", "--offset", "-0001"], "NEGATIVE_OFFSET"),
            (["--grain", "tree-score", "--expect-identity", "ABC"], "STALE_TREE_IDENTITY"),
            (["--grain", "tree-score", "--expect-identity", ""], "STALE_TREE_IDENTITY"),
            (["--grain", "tree-score", "--expected-identity", "a" * 64], "ARGUMENT_INVALID"),
            (["--grain", "tree-score", "--cutoff", "x"], "ARGUMENT_INVALID"),
            (["--season", "2019"], "ARGUMENT_INVALID"),
            (["--grain", "tree-score"], "TREE_DATABASE_MISSING"),
        ]
        for argv, want in cases:
            self.assertEqual(self.code(*argv), want, argv)

    def test_location_spellings_refuse_by_their_own_code(self) -> None:
        cases = [
            (["--boosting-comparison", r"\\server\share\x.sqlite"], "TREE_DATABASE_LOCATION_UNSUPPORTED"),
            (["--boosting-comparison", ""], "TREE_DATABASE_LOCATION_UNSUPPORTED"),
            (["--boosting-comparison", self.missing, "--manifest", r"\\server\share\m.json"],
             "TREE_MANIFEST_LOCATION_UNSUPPORTED"),
        ]
        if os.name == "nt":
            cases.append((["--boosting-comparison", "\\\\?\\C:\\x\\..\\y.sqlite"], "TREE_DATABASE_LOCATION_NOT_LITERAL"))
        for argv, want in cases:
            code, out, err = self.run_main(*argv, "--grain", "tree-score")
            self.assertEqual((code, out, fx.refusal(err)), (2, "", want), argv)

    def test_routing_needs_the_exact_option_token(self) -> None:
        self.assertTrue(bq.boosting_mode(["--boosting-comparison=x.sqlite"]))
        self.assertFalse(bq.boosting_mode(["--team", "--boosting-comparison-x"]))
        code, _out, err = self.run_main("--boosting-comparison=" + self.missing, "--grain", "tree-score")
        self.assertEqual((code, fx.refusal(err)), (2, "TREE_DATABASE_MISSING"))
        code, _out, err = self.run_main("--database", "a.sqlite", "--history-database", "b.sqlite", "--grain",
                                        "summary", "--team=--boosting-comparison")
        self.assertEqual(code, 2)
        self.assertNotIn("TREE_", err)
        self.assertFalse(bq.boosting_mode(["--team=--boosting-comparison", "x--boosting-comparison"]))


class ForgeryTests(_World):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.forger = fx.Forger(cls.db, cls.base / "f")
        cls.n = 0

    def forged(self, **kwargs) -> Path:
        ForgeryTests.n += 1
        return self.forger.forge(f"f{ForgeryTests.n}", **kwargs)

    def assert_refused(self, want: str, reason: str | None = None, *, reader_anchors=None, **kwargs) -> None:
        path = self.forged(**kwargs)
        with self.assertRaises(bc.BoostingError) as caught:
            bc.BoostingComparison(path, anchors=reader_anchors or self.anchors)
        self.assertEqual(caught.exception.code, want, str(caught.exception))
        if reason:
            self.assertIn(reason, str(caught.exception))

    def edit(self, table: str, index: int, field: str, value):
        def mutate(tables):
            tables[table][index][field] = value
        return mutate

    def test_genuine_release_verifies_and_a_rehashed_copy_still_verifies(self) -> None:
        path = self.forged(records=lambda t: None, rehash_content=True, anchors=self.anchors)
        with bc.BoostingComparison(path, anchors=self.anchors) as reader:
            self.assertEqual(reader.content_identity, self.reader.content_identity)

    def test_coordinated_value_forgeries_refuse_by_their_own_rule(self) -> None:
        r = self.reader.records

        def design(tables):
            f = tables["features"][0]
            f["design"][1] = f["design"][1] + 0.5
        self.assert_refused("TREE_FEATURE_MISMATCH", records=design, rehash_content=True, anchors=self.anchors)

        def label(tables):
            lab = next(x for x in tables["labels"] if x["label_state"] == "DECISIVE")
            lab["y_a"] = 1 - lab["y_a"]
        self.assert_refused("TREE_LABEL_MISMATCH", records=label, rehash_content=True, anchors=self.anchors)

        def leaf(tables):
            p = tables["parameters"][0]
            p["baseline"] = p["baseline"] + 0.001
            p["export_sha256"] = bc.export_sha256(p)
        self.assert_refused("TREE_ESTIMATE_MISMATCH", records=leaf, rehash_content=True, anchors=self.anchors)

        def digest(tables):
            node = next(n for n in tables["parameters"][1]["stages"][0] if n["is_leaf"])
            node["value"] = node["value"] + 0.001
        self.assert_refused("TREE_STRUCTURE_MISMATCH", records=digest, rehash_content=True, anchors=self.anchors)

        def cycle(tables):
            nodes = tables["parameters"][0]["stages"][0]
            nodes[nodes[0]["left"]] = {**nodes[0], "depth": 1}
            tables["parameters"][0]["export_sha256"] = bc.export_sha256(tables["parameters"][0])
        self.assert_refused("TREE_STRUCTURE_MISMATCH", records=cycle, rehash_content=True, anchors=self.anchors)

        def definition(tables):
            tables["parameters"][1]["definition"]["constructor"]["max_depth"] = 4
        self.assert_refused("TREE_FIT_MISMATCH", records=definition, rehash_content=True, anchors=self.anchors)

        def census(tables):
            tables["parameters"][0]["training"]["comparison_games_excluded"] = 0
        self.assert_refused("TREE_FIT_MISMATCH", records=census, rehash_content=True, anchors=self.anchors)

        def raw_q(tables):
            for e in tables["estimates"][:4]:
                e["raw_q_a_repr"] = repr(float(e["raw_q_a_repr"]) + 1e-9)
        self.assert_refused("TREE_ESTIMATE_MISMATCH", "1e-12", records=raw_q, rehash_content=True,
                            anchors=self.anchors)

        def witness_split(tables):
            e = next(x for x in tables["estimates"] if x["orientation"] == "B" and
                     x["raw_z_a_repr"] != x["raw_z_b_repr"])
            e["raw_z_b_repr"] = e["raw_z_a_repr"]
        self.assert_refused("TREE_ESTIMATE_MISMATCH", records=witness_split, rehash_content=True, anchors=self.anchors)

        def served(tables):
            e = tables["estimates"][0]
            e["probability"] = bc.decimal_text(Fraction(decimal.Decimal(e["probability"])) + Fraction(1, 10 ** 12))
        self.assert_refused("TREE_ESTIMATE_MISMATCH", records=served, rehash_content=True, anchors=self.anchors)

        tree_score = next(i for i, s in enumerate(r["scores"]) if s["model_id"] == bc.TREE_DEPTH2 and s["brier"])
        parent_score = next(i for i, s in enumerate(r["scores"]) if s["model_id"] == bc.PARENT_SMOOTHED)

        def brier(tables):
            s = tables["scores"][tree_score]
            s["brier"] = bc.rational(bc.frac(s["brier"]) + Fraction(1, 10 ** 20))
        self.assert_refused("TREE_SCORE_MISMATCH", records=brier, rehash_content=True, anchors=self.anchors)

        def log_loss_far(tables):
            s = tables["scores"][tree_score]
            s["log_loss"] = repr(float(s["log_loss"]) + 1e-9)
        self.assert_refused("TREE_SCORE_MISMATCH", "1e-12", records=log_loss_far, rehash_content=True,
                            anchors=self.anchors)

        def parent_copy(tables):
            tables["scores"][parent_score]["parent_score"]["brier_decimal"] = "0.999999999999"
        self.assert_refused("TREE_SCORE_MISMATCH", records=parent_copy, rehash_content=True, anchors=self.anchors)

        summary = next(i for i, s in enumerate(r["summary"]) if s["model_id"] == bc.TREE_DEPTH3)

        def summary_brier(tables):
            s = tables["summary"][summary]
            s["brier_total"] = bc.rational(bc.frac(s["brier_total"]) + Fraction(1, 10 ** 20))
        self.assert_refused("TREE_SUMMARY_MISMATCH", records=summary_brier, rehash_content=True, anchors=self.anchors)

        def summary_log_loss(tables):
            s = tables["summary"][summary]
            s["log_loss_total"] = repr(float(s["log_loss_total"]) + 1e-9)
        self.assert_refused("TREE_SUMMARY_MISMATCH", records=summary_log_loss, rehash_content=True,
                            anchors=self.anchors)

        def calibration(tables):
            s = tables["summary"][summary]
            s["calibration"][0]["count"] += 1
        self.assert_refused("TREE_SUMMARY_MISMATCH", records=calibration, rehash_content=True, anchors=self.anchors)

    def test_collection_record_and_meta_forgeries(self) -> None:
        self.assert_refused("TREE_COLLECTION_MISMATCH", records=lambda t: t["estimates"].pop(3), rehash_content=True,
                            anchors=self.anchors)

        def swap(tables):
            tables["scores"][0], tables["scores"][1] = tables["scores"][1], tables["scores"][0]
        self.assert_refused("TREE_COLLECTION_MISMATCH", records=swap, rehash_content=True, anchors=self.anchors)
        self.assert_refused("TREE_RECORD_MALFORMED", records=self.edit("features", 0, "pit_eligibility",
                                                                       "PIT_ADMITTED"),
                            rehash_content=True, anchors=self.anchors)
        self.assert_refused("TREE_RECORD_MALFORMED", records=self.edit("labels", 0, "a_points", True),
                            rehash_content=True, anchors=self.anchors)
        self.assert_refused("TREE_RECORD_MALFORMED", records=self.edit("scores", 0, "extra", 1),
                            rehash_content=True, anchors=self.anchors)
        self.assert_refused("TREE_META_MALFORMED",
                            meta={"labels": {**bc.LABELS, "pit_eligibility": "PIT_ADMITTED"}})
        for reason, line in (("JSON_NONFINITE_NUMBER", '{"season": NaN}'),
                             ("JSON_NONFINITE_NUMBER", '{"season": 1e999}'),
                             ("JSON_INTEGER_TOO_LONG", '{"season": ' + "9" * 5000 + "}"),
                             ("JSON_NESTING_TOO_DEEP", "[" * 100000 + "]" * 100000)):
            def corrupt(raw, line=line):
                raw["labels"][0] = line
            self.assert_refused("TREE_RECORD_MALFORMED", reason, lines=corrupt)

        def surrogate(raw):
            raw["labels"][0] = raw["labels"][0].replace('"label_state":"', '"label_state":"\\ud800')
        self.assert_refused("TREE_RECORD_MALFORMED", lines=surrogate)

    def test_parent_reference_forgeries(self) -> None:
        self.assert_refused("TREE_PARENT_REFERENCE_MISMATCH",
                            after_blocks=[("UPDATE parent_reference SET snapshot = ? WHERE singleton = 1",
                                           (b"\x00" * self.anchors["parent"]["bytes"],))])
        self.assert_refused("TREE_PARENT_REFERENCE_MISMATCH",
                            after_blocks=[("UPDATE parent_reference SET snapshot = CAST(snapshot AS TEXT)", ())])
        pin = {**self.anchors["parent"], "sqlite_sha256": "0" * 64}
        self.assert_refused("TREE_PARENT_REFERENCE_MISMATCH", reader_anchors={**self.anchors, "parent": pin},
                            records=lambda t: None)

    def test_outer_identity_and_profile(self) -> None:
        self.assert_refused("TREE_MANIFEST_MALFORMED", "IDENTITY_MISMATCH", identity_override="a" * 64)
        self.assert_refused("TREE_MANIFEST_MALFORMED", "CONTENT_IDENTITY",
                            manifest_patch={"content_identity": "b" * 64})
        work = self.base / "tampered"
        shutil.copytree(self.db.parents[3], work / "canonical")
        shutil.copytree(bc.manifest_path_for(self.db).parents[3], work / "manifests")
        db = work / "canonical" / bc.POPULATION / "sha256" / self.db.parent.name / bc.DB_FILE
        with db.open("r+b") as handle:
            handle.seek(150)
            handle.write(b"\x01")
        self.assertEqual(_code(bc.BoostingComparison, db, anchors=self.anchors), "TREE_MANIFEST_MALFORMED")
        profile = {"database_identity": "c" * 64, "content_identity": "d" * 64, "database_sha256": "e" * 64}
        self.assertEqual(_code(bc.BoostingComparison, self.db, anchors={**self.anchors, "profile": profile}),
                         "STALE_TREE_IDENTITY")
        self.assertEqual(_code(bc.BoostingComparison, self.db, anchors=self.anchors, expect_identity="f" * 64),
                         "STALE_TREE_IDENTITY")
        genuine = {"database_identity": self.reader.database_identity,
                   "content_identity": self.reader.content_identity,
                   "database_sha256": bc.sha256_file(self.db)}
        bc.BoostingComparison(self.db, anchors={**self.anchors, "profile": genuine})

    def test_fully_coordinated_rederivation_with_other_trees_needs_the_profile(self) -> None:
        other = fx.synthetic_fitter([], [], seed=99)
        games = self.reader.games
        census = bc.training_census(games)
        agreement = self.reader.records["parameters"][0]["backend_agreement"]
        parameters = [bc.parameter_record(m, other[m]["export"], census, agreement) for m in bc.TREE_MODELS]
        derived = bc.derive(games, parameters, bc.witness_texts(bc.raw_witnesses(games, parameters)))

        def replace(tables):
            for table in bc.RECORD_TABLES:
                tables[table][:] = derived[table]
        path = self.forged(records=replace, rehash_content=True, anchors=self.anchors)
        bc.BoostingComparison(path, anchors=self.anchors)
        genuine = {"database_identity": self.reader.database_identity,
                   "content_identity": self.reader.content_identity, "database_sha256": bc.sha256_file(self.db)}
        self.assertEqual(_code(bc.BoostingComparison, path, anchors={**self.anchors, "profile": genuine}),
                         "STALE_TREE_IDENTITY")

    def test_host_recomputation_within_tolerance_validates_without_changing_served_bytes(self) -> None:
        real_sigmoid, real_log_loss = bc.sigmoid, bc.log_loss_value
        with mock.patch.object(bc, "sigmoid", lambda z: real_sigmoid(z) * (1.0 + 2.0 ** -53)), \
                mock.patch.object(bc, "log_loss_value", lambda p, y: real_log_loss(p, y) + 1e-15):
            with bc.BoostingComparison(self.db, anchors=self.anchors) as reader:
                self.assertEqual(reader.records["estimates"], self.reader.records["estimates"])
                self.assertEqual(reader.records["scores"], self.reader.records["scores"])
        with mock.patch.object(bc, "log_loss_value", lambda p, y: real_log_loss(p, y) + 1e-9):
            self.assertEqual(_code(bc.BoostingComparison, self.db, anchors=self.anchors), "TREE_SCORE_MISMATCH")
        with mock.patch.object(bc, "sigmoid", lambda z: min(1.0, real_sigmoid(z) + 1e-9)):
            self.assertEqual(_code(bc.BoostingComparison, self.db, anchors=self.anchors), "TREE_ESTIMATE_MISMATCH")


class LocationTests(_World):
    def answers(self, database) -> list:
        code, doc, err = self.ask("--grain", "tree-parameter", database=database)
        self.assertEqual(code, 0, err)
        return [doc["release_identity"], doc["rows"]]

    def test_relative_long_case_and_alias_spellings_serve_identical_bytes(self) -> None:
        genuine = self.answers(self.db)
        cwd = os.getcwd()
        try:
            os.chdir(self.db.parents[4])
            self.assertEqual(self.answers(os.path.relpath(self.db)), genuine)
        finally:
            os.chdir(cwd)
        if os.name != "nt":
            return
        self.assertEqual(self.answers("\\\\?\\" + str(self.db)), genuine)
        self.assertEqual(self.answers(str(self.db).upper()), genuine)
        deep = self.base / ("d" * 60) / ("e" * 60) / ("f" * 60)
        self.addCleanup(shutil.rmtree, "\\\\?\\" + str(self.base / ("d" * 60)), True)
        target = deep / "canonical" / bc.POPULATION / "sha256" / self.db.parent.name / bc.DB_FILE
        manifest = deep / "manifests" / bc.POPULATION / "sha256" / self.db.parent.name / "run_manifest.json"
        os.makedirs("\\\\?\\" + str(target.parent))
        os.makedirs("\\\\?\\" + str(manifest.parent))
        shutil.copyfile(self.db, "\\\\?\\" + str(target))
        shutil.copyfile(bc.manifest_path_for(self.db), "\\\\?\\" + str(manifest))
        self.assertGreater(len(str(target)), 260)
        self.assertEqual(self.answers(target), genuine)
        junction = self.base / "jn"
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.db.parents[4])],
                              capture_output=True, text=True)
        if made.returncode == 0:
            via = junction / "canonical" / bc.POPULATION / "sha256" / self.db.parent.name / bc.DB_FILE
            self.assertEqual(self.answers(via), genuine)
            os.rmdir(junction)

    def test_layout_and_missing_manifest_refuse(self) -> None:
        loose = self.base / "loose" / bc.DB_FILE
        loose.parent.mkdir(parents=True)
        shutil.copyfile(self.db, loose)
        self.assertEqual(self.refused("--grain", "tree-score", database=loose), "TREE_LOCATION_INVALID")
        orphan = self.base / "orphan" / "canonical" / bc.POPULATION / "sha256" / self.db.parent.name / bc.DB_FILE
        orphan.parent.mkdir(parents=True)
        shutil.copyfile(self.db, orphan)
        self.assertEqual(self.refused("--grain", "tree-score", database=orphan), "TREE_MANIFEST_MISSING")
        copied = self.base / "mcopy.json"
        shutil.copyfile(bc.manifest_path_for(self.db), copied)
        code, _doc, err = self.ask("--grain", "tree-parameter", "--manifest", str(copied), database=orphan)
        self.assertEqual(code, 0, err)


class LegacySurfaceTests(unittest.TestCase):
    def test_original_help_gains_exactly_one_appended_paragraph(self) -> None:
        parser = q.build_parser()
        formatter = parser._get_formatter()
        formatter.add_text(q.SHADOW_EPILOG)
        association = parser._get_formatter()
        association.add_text(q.ASSOCIATION_EPILOG)
        old = super(q._HistoricalParser, parser).format_help() + "\n" + formatter.format_help() + "\n" + \
            association.format_help()
        self.assertEqual(parser.format_help(), old + "\n" + q.BOOSTING_HELP_PARAGRAPH + "\n")
        self.assertEqual(q.BOOSTING_HELP_PARAGRAPH, bq.HELP_PARAGRAPH)

    def test_invocations_without_the_option_never_import_the_mode(self) -> None:
        code = (f"import sys; sys.path[:0] = [{str(ROOT / 'src')!r}]; "
                "from aggie_analytics.retrospective_baseline import query; "
                "rc = query.main(['--database', 'missing.sqlite', '--history-database', 'm.sqlite', '--grain', "
                "'summary']); print(rc, any(m.endswith(('boosting_comparison', 'boosting_query', 'boosting_build')) "
                "for m in sys.modules), 'sklearn' in sys.modules)")
        with tempfile.TemporaryDirectory(prefix="sbl") as tmp:
            proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=tmp)
        self.assertEqual(proc.stdout.strip(), "2 False False")

    def test_the_mode_imports_no_modeling_package(self) -> None:
        code = (f"import sys; sys.path[:0] = [{str(ROOT / 'src')!r}]; "
                "from aggie_analytics.retrospective_baseline import query; "
                "rc = query.main(['--boosting-comparison', 'absent.sqlite', '--grain', 'tree-score']); "
                "print(rc, sorted(m for m in ('sklearn', 'numpy', 'scipy') if m in sys.modules))")
        with tempfile.TemporaryDirectory(prefix="sbm") as tmp:
            proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=tmp)
        self.assertEqual(proc.stdout.strip(), "2 []")


class MountedGenuineTests(unittest.TestCase):
    def test_the_canonical_release_verifies_with_the_pinned_profile(self) -> None:
        data = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or ""
        profile = bc.BOOSTING_PROFILE
        if not data or profile is None:
            self.skipTest("the private data root or the pinned canonical profile is absent")
        db = Path(data) / "canonical" / bc.POPULATION / "sha256" / profile["database_identity"] / bc.DB_FILE
        if not db.is_file():
            self.skipTest("the canonical shallow-tree comparison release is not mounted")
        with bc.BoostingComparison(db) as reader:
            self.assertEqual((reader.database_identity, reader.content_identity),
                             (profile["database_identity"], profile["content_identity"]))
            self.assertEqual({t: len(reader.records[t]) for t in bc.RECORD_TABLES}, bc.ANCHORS["expected"]["counts"])
            self.assertEqual(len(reader.games), 5875)
            census = reader.records["parameters"][0]["training"]
            self.assertEqual((census["games"], census["oriented_rows"], census["comparison_games_excluded"]),
                             (5087, 10174, 788))
            doc = reader.query("tree-summary", season=None)
            self.assertEqual(doc["total"], 77)


if __name__ == "__main__":
    unittest.main()
