"""National posthoc personnel/history association 2016-2022 (BAT-732, Cycle #61 TP61-A01).

Synthetic tiny worlds only (``tests/personnel_association_fixture.py``): every derivation rule, the frozen fits on
invented data, determinism, the six-grain selector matrix and refusals, coordinated rehashed forgeries, malformed JSON and
numeric boundaries and literal local locations. The mounted genuine case runs only when the private data root and the
pinned canonical profile are present."""
from __future__ import annotations

import copy
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

import personnel_association_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import personnel_association as pa  # noqa: E402
from aggie_analytics.retrospective_baseline import query as q  # noqa: E402
from aggie_analytics.retrospective_baseline import reference_fit as rf  # noqa: E402

STATE: dict = {}


def setUpModule() -> None:
    base = Path(tempfile.mkdtemp(prefix="npa-t-"))
    world = fx.build_world()
    contract = fx.write_contract(base / "contract.json", fx.contract_for(world))
    anchors = fx.contract_anchors(contract)
    code, result, err = fx.run_build(contract, world, base / "out")
    if code != 0:
        raise AssertionError(f"the fixture build refused: {err}")
    STATE.update(base=base, world=world, contract=contract, anchors=anchors, result=result,
                 db=fx.database_of(result))


def tearDownModule() -> None:
    shutil.rmtree(STATE["base"], ignore_errors=True)


def ask(*argv: str, db=None, anchors=None):
    return fx.query(STATE["anchors"] if anchors is None else anchors, STATE["db"] if db is None else db, *argv)


def records(grain: str, *argv: str) -> list[dict]:
    code, doc, err = ask("--grain", grain, "--all", *argv)
    if code != 0:
        raise AssertionError(err)
    return doc["rows"]


class DerivationTests(unittest.TestCase):
    def test_population_counts_follow_the_joins_never_forced(self) -> None:
        pop = STATE["result"]["population"]
        self.assertEqual(pop["views"], 2 * pop["targets"])
        self.assertEqual(pop["joined_views"] + pop["missing_summary_views"], pop["views"])
        self.assertEqual(pop["estimates"], pop["targets"] * 8)
        self.assertEqual(pop["estimate_states"]["SUPPORTED"], pop["common_support_games"] * 8)
        self.assertEqual(pop["scores"], pop["targets"] * 4)
        self.assertEqual(set(pop["missing_view_states"]), {"CHAIN_NOT_QUALIFIED", "NO_PROGRAM_SEASON",
                                                          "NO_SAME_SEASON_RETURNING_SUMMARY", "SUMMARY_LINK_MISMATCH"})
        self.assertEqual(pop["fit_games"] + pop["comparison_games"], pop["common_support_games"])
        quals = records("personnel-qualification")
        self.assertEqual(len(quals), len(STATE["anchors"]["expected"]["qualification_keys"]))
        self.assertIn("FCS|CHAIN_NOT_QUALIFIED", pop["qualification_states_by_division"])

    def test_rates_are_recomputed_from_integer_counts_and_absence_is_null(self) -> None:
        for qrec in records("personnel-qualification"):
            s = qrec["summary"]
            if qrec["qualification_state"] != "JOINABLE_SAME_SEASON_SUMMARY":
                self.assertIsNone(s)
                continue
            self.assertEqual(s["roster_retention_rate"], s["returning_roster_count"] / s["prior_roster_count"])
            self.assertEqual(s["roster_jaccard"], s["returning_roster_count"] / s["union_roster_count"])
            self.assertEqual(s["roster_arrival_rate"], s["arrival_roster_count"] / s["current_roster_count"])
            self.assertEqual(pa.frac(s["roster_jaccard_exact"]),
                             Fraction(s["returning_roster_count"], s["union_roster_count"]))
            self.assertTrue(s["parent_rates_equal_recomputed"])
        for f in records("personnel-feature"):
            if f["support_state"] != "COMMON_SUPPORT":
                self.assertIsNone(f["design_history_roster"])
                self.assertIsNone(f["roster_rate_differences"])
                self.assertTrue(f["abstention_reasons"])
                for side in ("team", "opponent"):
                    if f[f"{side}_side_state"] != "JOINABLE_SAME_SEASON_SUMMARY":
                        self.assertIsNone(f[f"{side}_roster"])
        for e in records("personnel-estimate"):
            if e["estimate_state"] == "ABSTAINED":
                self.assertIsNone(e["probability"])
                self.assertEqual(e["abstention_reason"], "ABSTAIN_OUTSIDE_COMMON_SUPPORT")

    def test_signed_shares_are_kept_unclipped_and_never_model_columns(self) -> None:
        quals = {qr["qualification_key"]: qr for qr in records("personnel-qualification")}
        passing = quals["2020|org:4"]["summary"]
        self.assertEqual(passing["shares"]["passing_yards_returning_share"], 1.0821)
        self.assertTrue(passing["share_outside_unit_interval"]["passing_yards_returning_share"])
        rushing = quals["2021|org:6"]["summary"]
        self.assertEqual(rushing["shares"]["rushing_yards_returning_share"], -0.0417)
        missing = quals["2022|org:7"]["summary"]
        self.assertIsNone(missing["shares"]["receiving_yards_returning_share"])
        self.assertIsNone(missing["share_outside_unit_interval"]["receiving_yards_returning_share"])
        self.assertEqual(pa.COLUMNS[pa.MODEL_ROSTER], (pa.HISTORY_COLUMN, *pa.ROSTER_COLUMNS))
        for f in records("personnel-feature"):
            if f["design_history_roster"] is not None:
                self.assertEqual(len(f["design_history_roster"]), 4)

    def test_parent_eligibility_flags_stay_false(self) -> None:
        for qrec in records("personnel-qualification"):
            if qrec["summary"]:
                for flag in ("target_game_feature_eligible", "protected_eligible",
                             "original_transition_time_pit_eligible"):
                    self.assertIs(qrec["summary"][flag], False)
            self.assertEqual(qrec["pit_eligibility"], "PIT_NOT_ADMITTED")
            self.assertEqual(qrec["association_authority"], "POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST")

    def test_orientation_negates_every_column_and_probabilities_complement_exactly(self) -> None:
        by = {(f["contest_key"], f["view"]): f for f in records("personnel-feature")}
        for (key, view), a in by.items():
            if view != "A":
                continue
            b = by[(key, "B")]
            self.assertEqual(b["history_log_odds_difference"], -a["history_log_odds_difference"])
            if a["design_history_roster"] is not None:
                self.assertEqual(b["design_history_roster"], [-v for v in a["design_history_roster"]])
        for e in records("personnel-estimate"):
            if e["estimate_state"] == "SUPPORTED":
                self.assertEqual(pa.frac(e["probability_exact"]) + pa.frac(e["opponent_probability_exact"]), 1)
                self.assertEqual(pa.dec_fraction(e["probability"]) + pa.dec_fraction(e["opponent_probability"]), 1)

    def test_history_log_odds_is_the_c47_smoothed_logit(self) -> None:
        for f in records("personnel-feature")[:40]:
            h = f["team_history"]
            q_ = pa.strength_q(h["wins"], h["ties"], h["games"])
            self.assertAlmostEqual(h["log_odds"], math.log(q_ / (1 - q_)), places=12)
            self.assertNotIn(f["contest_key"], h["contributing_contest_keys"])

    def _derive(self, patch=None) -> dict:
        return pa.derive(fx.inputs_for(STATE["world"], "natural", patch))

    def test_scales_and_fits_use_only_fit_rows(self) -> None:
        genuine = self._derive()

        def comparison_rosters(world: dict) -> None:
            for s in world["summaries"]:
                if s["target_season"] in pa.COMPARISON_SEASONS:
                    s["arrival_roster_count"] += 3
                    s["current_roster_count"] += 3
                    s["union_roster_count"] += 3
                    s["roster_arrival_rate"] = s["arrival_roster_count"] / s["current_roster_count"]
                    s["roster_jaccard"] = s["returning_roster_count"] / s["union_roster_count"]
        changed = self._derive(comparison_rosters)
        self.assertEqual(genuine["fits"]["scales"], changed["fits"]["scales"])
        for m in pa.FITTED_MODELS:
            self.assertEqual(genuine["fits"]["models"][m]["result"].coefficients,
                             changed["fits"]["models"][m]["result"].coefficients)

        def fit_rosters(world: dict) -> None:
            for s in world["summaries"]:
                if s["target_season"] == 2019:
                    s["arrival_roster_count"] += 7
                    s["current_roster_count"] += 7
                    s["union_roster_count"] += 7
                    s["roster_arrival_rate"] = s["arrival_roster_count"] / s["current_roster_count"]
                    s["roster_jaccard"] = s["returning_roster_count"] / s["union_roster_count"]
        self.assertNotEqual(genuine["fits"]["scales"], self._derive(fit_rosters)["fits"]["scales"])

    def test_comparison_outcomes_never_reach_the_fit(self) -> None:
        genuine = self._derive()

        def flip(world: dict) -> None:
            for label in world["labels"]:
                if label["season"] in pa.COMPARISON_SEASONS and label["label_state"] == "DECISIVE":
                    label["y_a"] = 1 - label["y_a"]
        flipped = self._derive(flip)
        self.assertEqual(pa.canonical_json_bytes(genuine["parameters"]), pa.canonical_json_bytes(flipped["parameters"]))
        g_scores = {s["score_key"]: s for s in genuine["scores"]}
        changed = [s for s in flipped["scores"] if s["season"] in pa.COMPARISON_SEASONS and s["brier"] is not None
                   and s["brier"] != g_scores[s["score_key"]]["brier"]]
        self.assertTrue(changed)

    def test_ties_stay_unscored_and_out_of_the_fit(self) -> None:
        derived = self._derive()
        ties = [s for s in derived["scores"] if s["label_state"] == "TIE"]
        self.assertTrue(ties)
        for s in ties:
            self.assertEqual(s["score_state"], "UNSCORED")
            self.assertIn(s["unscored_reason"], ("LABEL_TIE", "ABSTAINED_OUTSIDE_COMMON_SUPPORT"))
            self.assertNotIn(s["contest_key"], derived["fits"]["cohort_keys"])
        self.assertEqual(derived["fits"]["excluded_by_label"].get("TIE"), 1)

    def test_fixed_models_equal_the_unchanged_c47_records(self) -> None:
        def tamper(world: dict) -> None:
            supported = {lab["contest_key"] for lab in world["labels"] if lab["season"] == 2021 and
                         fx.joinable(2021, int(lab["a_key"][4:])) and fx.joinable(2021, int(lab["b_key"][4:]))}
            r = next(r for r in world["c47"] if r["model_id"] == pa.MODEL_SMOOTHED and r["contest_key"] in supported)
            r["probability"] = {"numerator": 1, "denominator": 3}
        with self.assertRaises(pa.AssociationError) as caught:
            self._derive(tamper)
        self.assertEqual(caught.exception.code, "ASSOCIATION_INPUT_INVALID")

    def test_target_leakage_is_refused_at_derivation(self) -> None:
        def leak(world: dict) -> None:
            f = next(f for f in world["features"] if f["team"]["games"] > 0)
            f["team"]["contributing"][0]["contest_key"] = f["contest_key"]
        with self.assertRaises(pa.AssociationError) as caught:
            self._derive(leak)
        self.assertIn("leakage", str(caught.exception))

    def test_fit_failure_is_recorded_and_every_affected_game_abstains(self) -> None:
        def no_fit_cohort(world: dict) -> None:
            world["summaries"] = [s for s in world["summaries"] if s["target_season"] not in pa.FIT_SEASONS]
            for p in world["programs"]:
                if p["season"] in pa.FIT_SEASONS:
                    p["returning_target_summary_key"] = None
        derived = self._derive(no_fit_cohort)
        params = {p["model_id"]: p for p in derived["parameters"]}
        for m in pa.FITTED_MODELS:
            self.assertEqual(params[m]["parameter_state"], "FIT_EMPTY")
            self.assertIsNone(params[m]["coefficients"])
        fitted = [e for e in derived["estimates"] if e["model_id"] in pa.FITTED_MODELS and e["season"] == 2021]
        self.assertTrue(any(e["abstention_reason"] == "ABSTAIN_FIT_FAILED" for e in fitted))
        self.assertTrue(all(e["estimate_state"] == "ABSTAINED" for e in fitted))

    def test_the_accepted_primitive_fits_independently_built_rows_identically(self) -> None:
        derived = self._derive()
        cohort = [(f, next(lab["y_a"] for lab in STATE["world"]["labels"] if lab["contest_key"] == f["contest_key"]))
                  for f in derived["features"] if f["view"] == "A" and f["season"] in pa.FIT_SEASONS and
                  f["support_state"] == "COMMON_SUPPORT"]
        cohort = [(f, y) for f, y in cohort if y is not None]
        n = len(cohort)
        scale = math.sqrt(math.fsum(0.5 * v * v for f, _y in cohort for v in (f["design_history"][0],
                                                                              -f["design_history"][0])) / n)
        rows = []
        for f, y in cohort:
            z = f["design_history"][0] / scale
            rows += [rf.Row((z,), float(y), 0.5), rf.Row((-z,), 1.0 - y, 0.5)]
        direct = rf.fit_logistic(rows, 1)
        self.assertEqual(direct.coefficients, derived["fits"]["models"][pa.MODEL_HISTORY]["result"].coefficients)
        self.assertEqual(derived["fits"]["scales"][0], scale)


class BuildTests(unittest.TestCase):
    def test_order_chunk_and_interrupted_builds_are_byte_identical(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="npa-b-"))
        self.addCleanup(shutil.rmtree, base, True)
        ident = STATE["result"]["database_identity"]
        for name, extra in (("rev", ("--input-order", "reverse")), ("shf", ("--input-order", "shuffle:6101")),
                            ("c1", ("--chunk-size", "1", "--checkpoint-dir", str(base / "k1"))),
                            ("c17", ("--chunk-size", "17", "--checkpoint-dir", str(base / "k17")))):
            code, result, err = fx.run_build(STATE["contract"], STATE["world"], base / name, *extra)
            self.assertEqual(code, 0, err)
            self.assertEqual(result["database_identity"], ident, name)
            self.assertEqual(result["fits"], STATE["result"]["fits"])
        code, result, _err = fx.run_build(STATE["contract"], STATE["world"], base / "ir", "--chunk-size", "1",
                                          "--checkpoint-dir", str(base / "kir"), "--stop-after-chunks", "2")
        self.assertEqual(code, 3)
        self.assertEqual(result["state"], "INTERRUPTED_AT_CHECKPOINT")
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], base / "ir", "--chunk-size", "1",
                                         "--checkpoint-dir", str(base / "kir"), "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual(result["database_identity"], ident)
        code, again, _err = fx.run_build(STATE["contract"], STATE["world"], base / "rev")
        self.assertEqual(again["state"], "ALREADY_PRESENT_IDENTICAL")
        target = Path(again["release"]["data_dir"]) / pa.DB_FILE
        data = target.read_bytes()
        target.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        code, _r, err = fx.run_build(STATE["contract"], STATE["world"], base / "rev")
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"))

    def test_contract_drift_and_population_drift_are_refused(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="npa-d-"))
        self.addCleanup(shutil.rmtree, base, True)
        contract = fx.contract_for(STATE["world"])
        contract["rules"]["labels"]["pit_eligibility"] = "PIT_ADMITTED"
        bad = fx.write_contract(base / "bad.json", contract)
        code, _r, err = fx.run_build(bad, STATE["world"], base / "o1")
        self.assertEqual((code, fx.refusal(err)), (2, "CONTRACT_INVALID"))

        def drop_summary(world: dict) -> None:
            world["summaries"] = [s for s in world["summaries"] if s["summary_key"] != f"2021|{fx.team_id(1)}"]
            for p in world["programs"]:
                if p["program_season_key"] == "2021|org:1":
                    p["returning_target_summary_key"] = None
        code, _r, err = fx.run_build(STATE["contract"], STATE["world"], base / "o2", patch=drop_summary)
        self.assertEqual((code, fx.refusal(err)), (2, "ASSOCIATION_INPUT_POPULATION_DRIFT"))


class QueryTests(unittest.TestCase):
    def test_every_grain_serves_its_complete_collection(self) -> None:
        pop = STATE["result"]["population"]
        want = {"personnel-qualification": pop["qualifications"], "personnel-feature": pop["views"],
                "personnel-estimate": pop["estimates"], "personnel-parameter": 4, "personnel-score": pop["scores"]}
        for grain, total in want.items():
            code, doc, err = ask("--grain", grain, "--limit", "1")
            self.assertEqual((code, doc["total"], doc["returned"]), (0, total, 1), err)
            for label in ("POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST", "UNTRUSTED_SHADOW", "PIT_NOT_ADMITTED",
                          "NOT_CALIBRATED", "NOT_ESTABLISHED"):
                self.assertIn(label, json.dumps(doc))
        code, doc, _err = ask("--grain", "personnel-summary", "--all")
        self.assertEqual(doc["summary_selection"]["selected"], "ALL_CANONICAL_GAMES")
        self.assertEqual(sum(1 for r in doc["rows"] if r.get("primary")), 1)

    def test_inapplicable_selectors_are_refused_never_ignored(self) -> None:
        values = {"season": "2021", "team": "org:1", "contest": "ncaa:1", "model": pa.MODEL_NULL,
                  "partition": "FIT"}
        for grain, allowed in pa.SELECTOR_MATRIX.items():
            for name, value in values.items():
                code, _doc, err = ask("--grain", grain, f"--{name}", value)
                if name in allowed:
                    self.assertEqual(code, 0, f"{grain} {name}: {err}")
                else:
                    self.assertEqual((code, fx.refusal(err)), (2, "FILTER_NOT_APPLICABLE"), f"{grain} {name}")

    def test_selectors_intersect_and_unknown_or_disjoint_selections_serve_no_rows(self) -> None:
        for argv in (["--grain", "personnel-score", "--season", "2021", "--partition", "FIT"],
                     ["--grain", "personnel-feature", "--contest", "ncaa:999999"],
                     ["--grain", "personnel-estimate", "--team", "org:999"],
                     ["--grain", "personnel-summary", "--team", "org:999"],
                     ["--grain", "personnel-summary", "--season", "2019", "--partition", "COMPARISON"],
                     ["--grain", "personnel-qualification", "--team", "No Such Team"]):
            code, doc, err = ask(*argv, "--all")
            self.assertEqual((code, doc["total"], doc["rows"]), (0, 0, []), f"{argv}: {err}")
        rows = records("personnel-score", "--season", "2021", "--team", "org:3", "--model", pa.MODEL_ROSTER)
        self.assertTrue(rows)
        self.assertTrue(all(r["season"] == 2021 and "org:3" in (r["a_key"], r["b_key"]) and
                            r["model_id"] == pa.MODEL_ROSTER for r in rows))

    def test_filtered_summaries_are_recomputed_from_the_selected_games(self) -> None:
        code, doc, _err = ask("--grain", "personnel-summary", "--team", "org:3", "--all")
        self.assertEqual(doc["summary_selection"]["selected"], "SELECTED_CANONICAL_GAMES")
        scores = [s for s in records("personnel-score", "--team", "org:3") if s["model_id"] == pa.MODEL_NULL]
        for row in doc["rows"]:
            if row["record_type"] != "PERSONNEL_SUMMARY_ROW" or row["model_id"] != pa.MODEL_NULL:
                continue
            chosen = [s for s in scores if s["season"] in row["seasons"]]
            self.assertEqual(row["score_records"], len(chosen))
            self.assertEqual(row["scored_games"], sum(1 for s in chosen if s["score_state"] == "SCORED"))
        self.assertFalse(any(r.get("primary") for r in doc["rows"]))
        code, page, _err = ask("--grain", "personnel-summary", "--team", "org:3", "--limit", "2", "--offset", "1")
        self.assertEqual((page["total"], page["rows"]), (doc["total"], doc["rows"][1:3]))

    def test_team_names_resolve_only_within_their_own_season(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="npa-n-"))
        self.addCleanup(shutil.rmtree, base, True)
        world = copy.deepcopy(STATE["world"])
        for f in world["features"]:
            for side, opp in (("team", "opponent"),):
                pass
            if f["season"] == 2019 and f["team_key"] == "org:4":
                f["team_name"] = "Old Name Four"
            if f["season"] == 2019 and f["opponent_key"] == "org:4":
                f["opponent_name"] = "Old Name Four"
        contract = fx.write_contract(base / "c.json", fx.contract_for(world))
        anchors = fx.contract_anchors(contract)
        code, result, err = fx.run_build(contract, world, base / "o")
        self.assertEqual(code, 0, err)
        code, doc, err = ask("--grain", "personnel-score", "--team", "old name four", "--all",
                             db=fx.database_of(result), anchors=anchors)
        self.assertEqual(code, 0, err)
        self.assertTrue(doc["rows"])
        self.assertEqual({r["season"] for r in doc["rows"]}, {2019})

    def test_malformed_selectors_and_paging_are_controlled_refusals(self) -> None:
        cases = [(["--grain", "personnel-score", "--season", "2021.0"], "SEASON_INVALID"),
                 (["--grain", "personnel-score", "--season", "true"], "SEASON_INVALID"),
                 (["--grain", "personnel-score", "--team", " "], "TEAM_INVALID"),
                 (["--grain", "personnel-score", "--contest", "cfbd:401"], "CONTEST_INVALID"),
                 (["--grain", "personnel-score", "--model", "LOGISTIC"], "MODEL_INVALID"),
                 (["--grain", "personnel-score", "--partition", "TEST"], "PARTITION_INVALID"),
                 (["--grain", "personnel-score", "--limit", "-1"], "NEGATIVE_LIMIT"),
                 (["--grain", "personnel-score", "--offset", "x"], "OFFSET_INVALID"),
                 (["--grain", "personnel-forecast"], "UNKNOWN_GRAIN"),
                 (["--grain", "personnel-score", "--as-of", "2021-09-01"], "ARGUMENT_INVALID"),
                 (["--grain", "personnel-score", "--require-pit"], "ASSOCIATION_PIT_NOT_ADMITTED"),
                 (["--grain", "personnel-score", "--database", "x.sqlite"], "ASSOCIATION_MODE_CONFLICT"),
                 (["--grain", "personnel-score", "--reference-comparison", "x.sqlite"], "ASSOCIATION_MODE_CONFLICT"),
                 (["--grain", "personnel-score", "--cutoff", "2021-09-01T00:00:00Z"], "FILTER_NOT_APPLICABLE"),
                 (["--grain", "personnel-summary", "--slice", "NATIONAL"], "FILTER_NOT_APPLICABLE"),
                 (["--grain", "personnel-score", "--expect-identity", "abc"], "STALE_ASSOCIATION_IDENTITY"),
                 (["--grain", "personnel-score", "--expect-identity", "f" * 64], "STALE_ASSOCIATION_IDENTITY")]
        for argv, code_want in cases:
            code, doc, err = ask(*argv)
            self.assertEqual((code, fx.refusal(err), doc), (2, code_want, None), argv)
            self.assertNotIn("Traceback", err)
        code, doc, _err = ask("--grain", "personnel-feature", "--season", "2023")
        self.assertEqual((code, doc["season_scope_state"], doc["total"]), (0, "SEASON_OUTSIDE_RELEASE", 0))
        code, doc, _err = ask("--grain", "personnel-feature", "--limit", "5", "--offset", "300")
        self.assertEqual((doc["returned"], doc["next_offset"]), (5, 305))
        code, doc, _err = ask("--grain", "personnel-feature", "--limit", "5", "--offset", "310")
        self.assertEqual((doc["returned"], doc["next_offset"]), (2, None))

    def test_original_help_gains_only_the_association_paragraph(self) -> None:
        parser = q.build_parser()
        text = parser.format_help()
        formatter = parser._get_formatter()
        formatter.add_text(q.SHADOW_EPILOG)
        association = parser._get_formatter()
        association.add_text(q.ASSOCIATION_EPILOG)
        old = super(q._HistoricalParser, parser).format_help() + "\n" + formatter.format_help()
        self.assertEqual(text, old + "\n" + association.format_help())
        self.assertIn("--personnel-association", association.format_help())

    def test_invocations_without_the_option_never_import_the_mode(self) -> None:
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        probe = ("import io, sys, contextlib\nfrom aggie_analytics.retrospective_baseline import query as q\n"
                 "err = io.StringIO()\nwith contextlib.redirect_stderr(err):\n    try:\n        q.main(['--grain', 'feature'])\n"
                 "    except SystemExit as exc:\n        code = exc.code\n"
                 "print(code, 'aggie_analytics.retrospective_baseline.personnel_association' in sys.modules)\n")
        out = subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, text=True, env=env,
                             check=False)
        self.assertEqual(out.stdout.split(), ["2", "False"], out.stderr)


class ForgeryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="npa-f-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.forger = fx.Forger(STATE["db"], self.base, STATE["anchors"])

    def refused(self, path: Path, anchors=None) -> str | None:
        code, _doc, err = ask("--grain", "personnel-parameter", db=path, anchors=anchors)
        self.assertNotIn("Traceback", err)
        return fx.refusal(err) if code == 2 else None

    def forge(self, name: str, mutate, **kw) -> Path:
        return self.forger.forge(name, records=mutate, **kw)

    def test_coordinated_scientific_forgeries_reach_their_own_rules(self) -> None:
        def first(rows, pred):
            return next(r for r in rows if pred(r))

        def coefficient(t):
            p = first(t["parameters"], lambda r: r["model_id"] == pa.MODEL_ROSTER)
            p["coefficients"][1] = "0.500000000000"

        def scale(t):
            p = first(t["parameters"], lambda r: r["model_id"] == pa.MODEL_HISTORY)
            p["scales"][0] = "1.000000000000"

        def estimate(t):
            e = first(t["estimates"], lambda r: r["model_id"] == pa.MODEL_ROSTER and r["estimate_state"] == "SUPPORTED")
            e["probability"] = pa.dec_complement(e["probability"])
            e["opponent_probability"] = pa.dec_complement(e["opponent_probability"])
            e["probability_exact"], e["opponent_probability_exact"] = e["opponent_probability_exact"], \
                e["probability_exact"]

        def complement(t):
            e = first(t["estimates"], lambda r: r["estimate_state"] == "SUPPORTED")
            e["opponent_probability"] = "0.123456789012"

        def clipped(t):
            q_ = first(t["qualifications"], lambda r: r["qualification_key"] == "2020|org:4")
            q_["summary"]["shares"]["passing_yards_returning_share"] = 1.0
            q_["summary"]["share_outside_unit_interval"]["passing_yards_returning_share"] = False

        def zero(v):
            return 0.0 if isinstance(v, float) else 0 if isinstance(v, int) and not isinstance(v, bool) else v

        def zeros(t):
            f = first(t["features"], lambda r: r["team_roster"] is None)
            f["team_roster"] = {k: zero(v) for k, v in
                                first(t["features"], lambda r: r["team_roster"] is not None)["team_roster"].items()}

        def zero_design(t):
            f = first(t["features"], lambda r: r["support_state"] != "COMMON_SUPPORT")
            f["roster_rate_differences"] = [0.0, 0.0, 0.0]
            f["design_history_roster"] = [f["history_log_odds_difference"], 0.0, 0.0, 0.0]

        def promoted(t):
            q_ = first(t["qualifications"], lambda r: r["summary"] is not None)
            q_["summary"]["target_game_feature_eligible"] = True

        def rate(t):
            q_ = first(t["qualifications"], lambda r: r["summary"] is not None)
            q_["summary"]["roster_retention_rate"] = 0.5
            q_["summary"]["roster_retention_rate_exact"] = {"numerator": 1, "denominator": 2}

        def wrong_season(t):
            f = first(t["features"], lambda r: r["team_roster"] is not None and r["season"] == 2021)
            f["team_roster"]["summary_key"] = f["team_roster"]["summary_key"].replace("2021|", "2020|")

        def leak(t):
            f = first(t["features"], lambda r: r["team_history"]["games"] > 0)
            f["team_history"]["contributing_contest_keys"][0] = f["contest_key"]

        def mirror(t):
            b = first(t["features"], lambda r: r["view"] == "B" and r["support_state"] == "COMMON_SUPPORT" and
                      r["team_history"] != r["opponent_history"])
            b["team_history"], b["opponent_history"] = b["opponent_history"], b["team_history"]
            b["history_log_odds_difference"] = b["team_history"]["log_odds"] - b["opponent_history"]["log_odds"]
            b["design_history"] = [b["history_log_odds_difference"]]
            b["design_history_roster"] = [b["history_log_odds_difference"], *b["roster_rate_differences"]]

        def one_label(t):
            s = first(t["scores"], lambda r: r["model_id"] == pa.MODEL_ROSTER and r["y_a"] is not None)
            s["y_a"] = 1 - s["y_a"]

        def all_labels(t):
            key = first(t["scores"], lambda r: r["season"] == 2019 and r["score_state"] == "SCORED")["contest_key"]
            for s in t["scores"]:
                if s["contest_key"] == key:
                    s["y_a"] = 1 - s["y_a"]

        def summary(t):
            t["summary"][0]["rows"][0]["scored_games"] += 1

        def involvement(t):
            first(t["qualifications"], lambda r: r["study_views"] > 0)["study_views"] += 1

        def partition(t):
            first(t["features"], lambda r: r["season"] == 2021)["partition"] = "FIT"

        cases = [("coefficient", coefficient, "ASSOCIATION_PARAMETER_MISMATCH"),
                 ("scale", scale, "ASSOCIATION_PARAMETER_MISMATCH"),
                 ("estimate", estimate, "ASSOCIATION_ESTIMATE_MISMATCH"),
                 ("complement", complement, "ASSOCIATION_COMPLEMENT_INVALID"),
                 ("clipped", clipped, "ASSOCIATION_SIGNED_SHARE_CLIPPED"),
                 ("zeros", zeros, "ASSOCIATION_MISSING_AS_ZERO"),
                 ("zerodesign", zero_design, "ASSOCIATION_MISSING_AS_ZERO"),
                 ("promoted", promoted, "ASSOCIATION_PARENT_ELIGIBILITY_PROMOTED"),
                 ("rate", rate, "ASSOCIATION_RATE_MISMATCH"),
                 ("wrongseason", wrong_season, "ASSOCIATION_JOIN_MISMATCH"),
                 ("leak", leak, "ASSOCIATION_HISTORY_LEAKAGE"),
                 ("mirror", mirror, "ASSOCIATION_ORIENTATION_MISMATCH"),
                 ("onelabel", one_label, "ASSOCIATION_LABEL_INCONSISTENT"),
                 ("alllabels", all_labels, "ASSOCIATION_PARAMETER_MISMATCH"),
                 ("summary", summary, "ASSOCIATION_SUMMARY_MISMATCH"),
                 ("involvement", involvement, "ASSOCIATION_INVOLVEMENT_MISMATCH"),
                 ("partition", partition, "ASSOCIATION_PARTITION_MISMATCH")]
        for name, mutate, want in cases:
            self.assertEqual(self.refused(self.forge(name, mutate)), want, name)

    def test_collections_types_and_identities(self) -> None:
        def drop(t):
            del t["estimates"][5]

        def extra(t):
            t["scores"].append(dict(t["scores"][0], score_key="ncaa:1|NULL_HALF_V1", contest_key="ncaa:1"))

        def order(t):
            t["features"][0], t["features"][1] = t["features"][1], t["features"][0]

        def float_count(t):
            q_ = next(r for r in t["qualifications"] if r["study_views"] > 0)
            q_["study_views"] = float(q_["study_views"])

        def bool_count(t):
            t["features"][0]["team_history"]["ties"] = False

        def member(t):
            t["parameters"][0]["note"] = "extra"

        def pit(t):
            t["scores"][0]["pit_eligibility"] = "PIT_ADMITTED"

        cases = [("drop", dict(records=drop), "ASSOCIATION_ESTIMATE_ROW_MISSING"),
                 ("extra", dict(records=extra), "ASSOCIATION_SCORE_ROW_EXTRA"),
                 ("order", dict(records=order), "ASSOCIATION_ORDER_MISMATCH"),
                 ("floatcount", dict(records=float_count), "ASSOCIATION_FIELD_TYPE_INVALID"),
                 ("boolcount", dict(records=bool_count), "ASSOCIATION_FIELD_TYPE_INVALID"),
                 ("member", dict(records=member), "ASSOCIATION_RECORD_SHAPE_INVALID"),
                 ("pit", dict(records=pit), "ASSOCIATION_PIT_CLAIM_INVALID"),
                 ("metalabels", dict(meta={"labels": {**pa.LABELS, "pit_eligibility": "PIT_ADMITTED"}}),
                  "ASSOCIATION_PIT_CLAIM_INVALID"),
                 ("docmember", dict(document=lambda d: d.update(note="x")), "ASSOCIATION_IDENTITY_DOCUMENT_MISMATCH"),
                 ("doccount", dict(document=lambda d: d["table_counts"].update(meta=float(d["table_counts"]["meta"]))),
                  "ASSOCIATION_IDENTITY_DOCUMENT_MISMATCH"),
                 ("contentid", dict(manifest_patch={"content_identity": "0" * 64}),
                  "ASSOCIATION_CONTENT_IDENTITY_MISMATCH"),
                 ("identityname", dict(identity_override="1" * 64), "ASSOCIATION_IDENTITY_MISMATCH")]
        for name, kwargs, want in cases:
            self.assertEqual(self.refused(self.forger.forge(name, **kwargs)), want, name)

    def test_profile_pins_coordinated_value_forgeries_and_controls_are_served(self) -> None:
        def share(t):
            q_ = next(r for r in t["qualifications"] if r["summary"] is not None)
            q_["summary"]["shares"]["rushing_carries_returning_share"] = 0.5
        forged = self.forge("share", share)
        self.assertIsNone(self.refused(forged))   # internally consistent: only the pinned profile can refuse it
        pinned = dict(STATE["anchors"], profile={"database_identity": STATE["result"]["database_identity"],
                                                 "content_identity": STATE["result"]["content_identity"]})
        self.assertEqual(self.refused(forged, pinned), "ASSOCIATION_PROFILE_MISMATCH")
        self.assertIsNone(self.refused(STATE["db"], pinned))
        rehoused = self.base / "rehoused"
        ident = STATE["result"]["database_identity"]
        for kind in ("canonical", "manifests"):
            shutil.copytree(STATE["db"].parents[3].parent / kind / pa.POPULATION / "sha256" / ident,
                            rehoused / kind / pa.POPULATION / "sha256" / ident)
        moved = rehoused / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE
        self.assertIsNone(self.refused(moved, pinned))
        man = fx.manifest_of(moved)
        doc = json.loads(man.read_text(encoding="utf-8"))
        doc["provenance"] = {"note": "provenance-only change"}
        man.write_text(json.dumps(doc), encoding="utf-8")
        self.assertIsNone(self.refused(moved, pinned))


class MalformedJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="npa-j-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.forger = fx.Forger(STATE["db"], self.base, STATE["anchors"])

    def outcome(self, path: Path) -> tuple[str | None, str]:
        code, _doc, err = ask("--grain", "personnel-parameter", db=path)
        self.assertEqual(code, 2, err)
        self.assertNotIn("Traceback", err)
        return fx.refusal(err), err

    def test_malformed_record_lines_are_controlled_refusals(self) -> None:
        depth = max(sys.getrecursionlimit() * 2 + 50, 100_000)
        deep = "[" * depth + "]" * depth

        def surrogate(raw):
            raw["features"][0] = raw["features"][0].replace('"team_name":"', '"team_name":"\\ud800', 1)

        def nesting(raw):
            raw["features"][0] = raw["features"][0][:-1] + ',"deep":' + deep + "}"

        def huge(raw):
            raw["features"][0] = raw["features"][0].replace('"season":', '"season":' + "9" * 5000 + "0*0+", 1)

        def nan(raw):
            raw["features"][0] = raw["features"][0].replace('"history_log_odds_difference":',
                                                            '"history_log_odds_difference":NaN,"x":', 1)

        def overflow(raw):
            raw["features"][0] = raw["features"][0].replace('"history_log_odds_difference":',
                                                            '"history_log_odds_difference":1e999,"x":', 1)
        for name, mutate, reason in (("sur", surrogate, "JSON_LONE_SURROGATE"), ("deep", nesting,
                                                                                    "JSON_NESTING_TOO_DEEP"),
                                     ("nan", nan, "JSON_NONFINITE_NUMBER"),
                                     ("ovf", overflow, "JSON_NONFINITE_NUMBER")):
            code, err = self.outcome(self.forger.forge(name, lines=mutate, rehash_content=False))
            self.assertEqual(code, "ASSOCIATION_RECORD_MALFORMED", name)
            self.assertIn(reason, err, name)

        def long_int(raw):
            raw["features"][0] = raw["features"][0].replace('"season":2018', '"season":' + "1" * 5000, 1)
        code, err = self.outcome(self.forger.forge("long", lines=long_int, rehash_content=False))
        self.assertEqual(code, "ASSOCIATION_RECORD_MALFORMED")
        self.assertIn("JSON_INTEGER_TOO_LONG", err)

    def test_huge_valid_counts_are_refused_before_any_binary64_conversion(self) -> None:
        def huge_count(t):
            q_ = next(r for r in t["qualifications"] if r["summary"] is not None)
            for k in ("prior_roster_count", "returning_roster_count"):
                q_["summary"][k] = 10 ** 400
        code, err = self.outcome(self.forger.forge("hugecount", records=huge_count))
        self.assertEqual(code, "ASSOCIATION_COUNT_OUT_OF_DOMAIN")

    def test_malformed_manifest_and_meta_are_refused(self) -> None:
        depth = max(sys.getrecursionlimit() * 2 + 50, 100_000)
        deep = "[" * depth + "]" * depth
        def inside(value):
            return lambda text: text.replace('"provenance": {', '"provenance": {"x": ' + value + ', ', 1)
        code, err = self.outcome(self.forger.forge("mdeep", manifest_text=inside(deep)))
        self.assertEqual(code, "ASSOCIATION_MANIFEST_MALFORMED")
        self.assertIn("JSON_NESTING_TOO_DEEP", err)
        code, err = self.outcome(self.forger.forge("mnan", manifest_text=inside("NaN")))
        self.assertEqual(code, "ASSOCIATION_MANIFEST_MALFORMED")
        self.assertIn("JSON_NONFINITE_NUMBER", err)
        code, err = self.outcome(self.forger.forge("metadeep", meta={"labels": deep}))
        self.assertEqual(code, "ASSOCIATION_META_MALFORMED")
        self.assertIn("JSON_NESTING_TOO_DEEP", err)


class LocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="npa-l-"))
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_missing_and_misplaced_files_are_refused_and_never_created(self) -> None:
        missing = self.base / "nowhere" / "canonical" / pa.POPULATION / "sha256" / ("0" * 64) / pa.DB_FILE
        code, _doc, err = ask("--grain", "personnel-parameter", db=missing)
        self.assertEqual((code, fx.refusal(err)), (2, "ASSOCIATION_DATABASE_MISSING"))
        self.assertFalse(missing.parent.exists())
        loose = self.base / "loose" / pa.DB_FILE
        loose.parent.mkdir()
        shutil.copyfile(STATE["db"], loose)
        code, _doc, err = ask("--grain", "personnel-parameter", db=loose)
        self.assertEqual((code, fx.refusal(err)), (2, "ASSOCIATION_LOCATION_INVALID"))
        code, _doc, err = ask("--grain", "personnel-parameter", "--manifest", str(self.base / "no" / "m.json"))
        self.assertEqual((code, fx.refusal(err)), (2, "ASSOCIATION_MANIFEST_MISSING"))

    @unittest.skipUnless(os.name == "nt", "Windows network/device spellings")
    def test_network_and_device_spellings_are_refused_lexically(self) -> None:
        for spelling in ("\\\\bas-c61-test-host\\share\\x.sqlite", "\\\\.\\nul", "\\\\.\\pipe\\c61",
                         "\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1\\x.sqlite"):
            code, _doc, err = ask("--grain", "personnel-parameter", db=spelling)
            self.assertEqual((code, fx.refusal(err)), (2, "DATABASE_LOCATION_UNSUPPORTED"), spelling)
        code, _doc, err = ask("--grain", "personnel-parameter", "--manifest",
                              "\\\\bas-c61-test-host\\share\\run_manifest.json")
        self.assertEqual((code, fx.refusal(err)), (2, "ASSOCIATION_MANIFEST_LOCATION_UNSUPPORTED"))

    def test_legitimate_local_spellings_answer_identically(self) -> None:
        genuine = ask("--grain", "personnel-summary", "--limit", "3")[1]
        ident = STATE["result"]["database_identity"]
        long_base = self.base.joinpath(*[f"long-rehoused-association-component-{c}-" + c * 24 for c in "abcd"])
        special = self.base / "spé cial ☃ [x] #%&"
        for root in (long_base, special):
            for kind in ("canonical", "manifests"):
                src = STATE["db"].parents[3].parent / kind / pa.POPULATION / "sha256" / ident
                dst = root / kind / pa.POPULATION / "sha256" / ident
                os.makedirs(pa._io_path(dst))
                for name in os.listdir(pa._io_path(src)):
                    shutil.copyfile(pa._io_path(src / name), pa._io_path(dst / name))
        spellings = [long_base / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE,
                     special / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE]
        if os.name == "nt":
            spellings.append("\\\\?\\" + os.path.abspath(STATE["db"]))
        self.assertGreater(len(str(spellings[0])), 260)
        for spelling in spellings:
            code, doc, err = ask("--grain", "personnel-summary", "--limit", "3", db=spelling)
            self.assertEqual(code, 0, f"{spelling}: {err}")
            self.assertEqual((doc["release_identity"], doc["rows"]), (genuine["release_identity"], genuine["rows"]))
        cwd = os.getcwd()
        try:
            os.chdir(STATE["db"].parent)
            code, doc, err = ask("--grain", "personnel-summary", "--limit", "3", db=pa.DB_FILE)
        finally:
            os.chdir(cwd)
        self.assertEqual((code, doc["rows"]), (0, genuine["rows"]), err)


# --------------------------------------------------------------------------------------------- C61-CONT-01
# Cycle #61 -- Work round #2 -- FIRST REPAIR. MF61A01-01: genuine native Windows aliases (8.3 short and case-equivalent
# spellings, through ordinary, extended-length, relative and junction paths) of the same existing release serve it, and
# every integrity rule still refuses by its own code under an alias; spellings outside the genuine layout and POSIX
# spellings keep their refusals. MF61A01-02: a lone surrogate in --team is refused (TEAM_INVALID, exit 2, no traceback)
# before any release access, through real strict UTF-8 output; valid Unicode, non-BMP, unknown and same-season names keep
# their answers. Every assertion that the unrepaired reader fails carries its finding marker.

MF01 = "MF61A01-01"
MF02 = "MF61A01-02"
#: Lone surrogate team selectors: high, low, interior, trailing, a reversed pair and a valid pair given as two code points.
SURROGATE_TEAMS = {"high": "\ud800", "low": "\udc00", "interior": "Tex\ud800as", "trailing": "Texas\udfff",
                   "reversed_pair": "\udc00\ud800", "pair_as_two_code_points": "\ud83d\ude00"}
TEAM_GRAINS = tuple(grain for grain, allowed in pa.SELECTOR_MATRIX.items() if "team" in allowed)
#: A child that answers the fixture release through q.main with its real stdout and stderr pipes (the strict UTF-8 output
#: path a StringIO hides): argv[1] the tests directory, argv[2] the fixture contract, then "argv" and the tokens, or the
#: path of a JSON file holding them (a POSIX argv cannot carry every lone surrogate).
REAL_OUTPUT_CHILD = (
    "import json, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import personnel_association_fixture as fx\n"
    "from aggie_analytics.retrospective_baseline import query as q\n"
    "anchors = fx.contract_anchors(Path(sys.argv[2]))\n"
    "tokens = sys.argv[4:] if sys.argv[3] == 'argv' else json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))\n"
    "raise SystemExit(q.main(tokens, association_anchors=anchors))\n")


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
    """``db`` with one layout component respelled: 0 the file, 1 the identity, 2 sha256, 3 the population."""
    parts = list(Path(db).parts)
    parts[-1 - index] = spell(parts[-1 - index])
    return Path(*parts)


def _filter_refusal(grain: str, team: str) -> str | None:
    try:
        pa.PersonnelAssociation.filters(grain, team=team)
    except pa.AssociationError as exc:
        return exc.code
    return None


def _refusal_of(stderr: bytes) -> str | None:
    try:
        return json.loads(stderr.decode("ascii").strip().splitlines()[-1]).get("refused")
    except (ValueError, UnicodeDecodeError, IndexError, AttributeError):
        return None


class NativeLocationAliasTests(unittest.TestCase):
    """MF61A01-01: the reader checks the release layout and identity on the genuine names of the existing file."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="npa-a-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.genuine = ask("--grain", "personnel-summary", "--limit", "3")[1]

    def served(self, spelling, why: str, *argv: str, cwd: Path | None = None) -> None:
        previous = os.getcwd()
        try:
            if cwd is not None:
                os.chdir(cwd)
            code, doc, err = ask("--grain", "personnel-summary", "--limit", "3", *argv, db=spelling)
        finally:
            os.chdir(previous)
        self.assertEqual(code, 0, f"{MF01} {why} {spelling}: {err[-300:]}")
        self.assertEqual((doc["release_identity"], doc["rows"]), (self.genuine["release_identity"],
                                                                  self.genuine["rows"]), f"{MF01} {why} {spelling}")

    def refusal(self, spelling, *argv: str, anchors=None) -> str | None:
        code, _doc, err = ask("--grain", "personnel-parameter", *argv, db=spelling, anchors=anchors)
        self.assertNotIn("Traceback", err)
        return fx.refusal(err) if code == 2 else None

    def junction(self, target: Path, link: Path) -> Path:
        import _winapi  # noqa: PLC0415 - Windows CPython; the junction is the spelling under test

        link.parent.mkdir(parents=True, exist_ok=True)
        _winapi.CreateJunction(str(target), str(link))
        self.addCleanup(os.rmdir, link)   # removes only the reparse point, before the scratch tree is removed
        return link

    @unittest.skipUnless(os.name == "nt", "Windows case-equivalent spellings (POSIX names are case-sensitive)")
    def test_case_equivalent_spellings_of_every_layout_component_serve_the_release(self) -> None:
        db = STATE["db"]
        spellings = [_respell(db, index, spell) for index in range(4) for spell in (str.upper, str.swapcase)]
        spellings.append(Path(str(db).upper()))
        for spelling in spellings:
            self.assertTrue(os.path.samefile(spelling, db), spelling)
            self.served(spelling, "case-equivalent spelling")
        self.served("\\\\?\\" + os.path.abspath(_respell(_respell(db, 3, str.upper), 1, str.upper)),
                    "extended-length case-equivalent spelling")
        self.served(pa.DB_FILE.upper(), "relative case-equivalent file name", cwd=db.parent)
        relative = os.path.join(pa.POPULATION.upper(), "SHA256", db.parent.name.upper(), pa.DB_FILE)
        self.served(relative, "relative case-equivalent layout", cwd=db.parents[3])

    @unittest.skipUnless(os.name == "nt", "Windows native 8.3 short names")
    def test_native_short_spellings_serve_the_release(self) -> None:
        db = STATE["db"]
        short = _short_spelling(db)
        long_parts = Path(db).parts
        short_parts = Path(short).parts if short else ()
        shortened = [i for i in range(4) if len(short_parts) == len(long_parts) and
                     short_parts[-1 - i] != long_parts[-1 - i]]
        if not shortened:
            self.skipTest(f"this volume reports no 8.3 short name for the release layout ({short!r})")
        self.assertTrue(os.path.samefile(short, db), short)
        self.served(short, "native short spelling")
        for index in shortened:
            self.served(_respell(db, index, lambda _part, i=index: short_parts[-1 - i]),
                        f"native short spelling of layout component {index}")
        self.served("\\\\?\\" + short, "extended-length native short spelling")
        self.served(short_parts[-1], "relative native short file name", cwd=db.parent)
        mixed = _respell(_respell(db, shortened[-1], lambda _part: short_parts[-1 - shortened[-1]]), 0, str.upper)
        self.served(mixed, "native short and case-equivalent spelling")

    @unittest.skipUnless(os.name == "nt", "Windows directory junctions")
    def test_aliases_through_junctions_serve_the_release(self) -> None:
        db = STATE["db"]
        ident = db.parent.name
        data_root = db.parents[4]
        root_link = self.junction(data_root, self.base / "jroot")
        self.served(root_link / "canonical" / pa.POPULATION.upper() / "SHA256" / ident.upper() / pa.DB_FILE.upper(),
                    "case-equivalent spelling through a data-root junction")
        self.served(self.base / "JROOT" / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE,
                    "case-equivalent spelling of the junction itself")
        for kind in ("canonical", "manifests"):
            self.junction(data_root / kind / pa.POPULATION / "sha256" / ident,
                          self.base / "jid" / kind / pa.POPULATION / "sha256" / ident)
        self.served(self.base / "jid" / "canonical" / pa.POPULATION.upper() / "sha256" / ident.upper() / pa.DB_FILE,
                    "case-equivalent spelling through an identity-directory junction")
        short = _short_spelling(root_link / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE)
        if short and Path(short).name != pa.DB_FILE:
            self.served(short, "native short spelling through a junction")

    @unittest.skipUnless(os.name == "nt", "Windows native aliases")
    def test_aliases_reach_every_integrity_refusal_by_its_own_rule(self) -> None:
        forger = fx.Forger(STATE["db"], self.base / "f", STATE["anchors"])

        def rate(t):
            q_ = next(r for r in t["qualifications"] if r["summary"] is not None)
            q_["summary"]["roster_retention_rate"] = 0.5
            q_["summary"]["roster_retention_rate_exact"] = {"numerator": 1, "denominator": 2}

        def share(t):
            q_ = next(r for r in t["qualifications"] if r["summary"] is not None)
            q_["summary"]["shares"]["rushing_carries_returning_share"] = 0.5
        upper = lambda path: _respell(path, 3, str.upper)  # noqa: E731
        rated = forger.forge("rate", records=rate)
        self.assertEqual(self.refusal(upper(rated)), "ASSOCIATION_RATE_MISMATCH",
                         f"{MF01} a rehashed forgery under an alias")
        pinned = dict(STATE["anchors"], profile={"database_identity": STATE["result"]["database_identity"],
                                                 "content_identity": STATE["result"]["content_identity"]})
        self.assertEqual(self.refusal(upper(forger.forge("share", records=share)), anchors=pinned),
                         "ASSOCIATION_PROFILE_MISMATCH", f"{MF01} the pinned profile under an alias")
        ident = STATE["result"]["database_identity"]
        tampered = self.base / "t"
        for kind in ("canonical", "manifests"):
            shutil.copytree(STATE["db"].parents[3].parent / kind / pa.POPULATION / "sha256" / ident,
                            tampered / kind / pa.POPULATION / "sha256" / ident)
        moved = tampered / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE
        with moved.open("ab") as handle:
            handle.write(b"\0")
        self.assertEqual(self.refusal(_respell(moved, 1, str.upper)), "ASSOCIATION_DATABASE_TAMPERED",
                         f"{MF01} tampered bytes under an alias")
        alias = _respell(STATE["db"], 0, str.upper)
        self.assertEqual(self.refusal(alias, "--expect-identity", "f" * 64), "STALE_ASSOCIATION_IDENTITY",
                         f"{MF01} a stale expected identity under an alias")
        self.assertEqual(self.refusal(alias, "--manifest", str(fx.manifest_of(rated))), "ASSOCIATION_IDENTITY_MISMATCH",
                         f"{MF01} another release's manifest under an alias")
        self.assertEqual(self.refusal(alias, "--manifest", str(self.base / "no" / "m.json")),
                         "ASSOCIATION_MANIFEST_MISSING", f"{MF01} a missing explicit manifest under an alias")

    def test_spellings_outside_the_genuine_layout_stay_refused(self) -> None:
        ident = STATE["result"]["database_identity"]
        source = STATE["db"].parents[3].parent
        loose = self.base / "loose" / pa.DB_FILE
        loose.parent.mkdir()
        shutil.copyfile(STATE["db"], loose)
        layouts = {"population": ("canonical", pa.POPULATION + "_copy", "sha256", ident),
                   "identity_directory": ("canonical", pa.POPULATION, "sha256", ident.upper()),
                   "sha256_directory": ("canonical", pa.POPULATION, "SHA256", ident)}
        for name, parts in layouts.items():
            target = self.base / name / Path(*parts)
            os.makedirs(target)
            shutil.copyfile(STATE["db"], target / pa.DB_FILE)
            self.assertEqual(self.refusal(target / pa.DB_FILE), "ASSOCIATION_LOCATION_INVALID", name)
        self.assertEqual(self.refusal(loose), "ASSOCIATION_LOCATION_INVALID")
        loose_alias = _respell(loose, 0, str.upper)
        self.assertEqual(self.refusal(loose_alias), "ASSOCIATION_LOCATION_INVALID" if os.path.exists(loose_alias)
                         else "ASSOCIATION_DATABASE_MISSING")
        missing = _respell(STATE["db"].parent / "nope.sqlite", 3, str.upper)
        self.assertEqual(self.refusal(missing), "ASSOCIATION_DATABASE_MISSING")
        self.assertFalse(os.path.exists(missing))
        if os.name == "nt":
            self.assertEqual(self.refusal(str(STATE["db"]) + "::$DATA"), "ASSOCIATION_LOCATION_INVALID")
            short = _short_spelling(loose)
            if short:
                self.assertEqual(self.refusal(short), "ASSOCIATION_LOCATION_INVALID")
        self.assertEqual(self.refusal(STATE["db"]), None)

    def test_posix_spelling_semantics_are_unchanged(self) -> None:
        class PosixOs:
            name = "posix"

            def __getattr__(self, key: str):
                return getattr(os, key)
        alias = _respell(STATE["db"], 3, str.upper)
        want = "ASSOCIATION_LOCATION_INVALID" if os.path.exists(alias) else "ASSOCIATION_DATABASE_MISSING"
        with mock.patch.object(pa, "os", PosixOs()):
            got = self.refusal(alias)
            exact = self.refusal(STATE["db"])
        self.assertEqual((got, exact), (want, None))

    @unittest.skipUnless(os.name == "nt", "Windows directory junctions")
    def test_exact_spellings_through_junctions_serve_the_release(self) -> None:
        db = STATE["db"]
        ident = db.parent.name
        link = self.junction(db.parents[4], self.base / "jroot")
        self.served(link / "canonical" / pa.POPULATION / "sha256" / ident / pa.DB_FILE, "exact junction spelling")
        self.served(db, "exact spelling")


class TeamUnicodeTests(unittest.TestCase):
    """MF61A01-02: team selectors are Unicode text, validated before any release access."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="npa-u-"))
        self.addCleanup(shutil.rmtree, self.base, True)

    def real_query(self, *tokens: str) -> tuple[int, bytes, bytes]:
        argv = ["--personnel-association", str(STATE["db"]), *tokens]
        if os.name == "nt":
            carrier = ["argv", *argv]
        else:
            path = self.base / f"tokens_{len(list(self.base.iterdir()))}.json"
            path.write_text(json.dumps(argv), encoding="ascii")
            carrier = [str(path)]
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run([sys.executable, "-B", "-c", REAL_OUTPUT_CHILD, str(ROOT / "tests"),
                               str(STATE["contract"]), *carrier], capture_output=True, env=env, check=False,
                              timeout=600)
        return proc.returncode, proc.stdout, proc.stderr

    def test_lone_surrogate_team_selectors_are_refused_before_any_release_access(self) -> None:
        missing = self.base / "nowhere" / "canonical" / pa.POPULATION / "sha256" / ("0" * 64) / pa.DB_FILE
        for name, team in SURROGATE_TEAMS.items():
            for grain in TEAM_GRAINS:
                self.assertEqual(_filter_refusal(grain, team), "TEAM_INVALID", f"{MF02} {name} at the {grain} filter")
            code, doc, err = ask("--grain", "personnel-feature", "--team", team, db=missing)
            self.assertEqual((code, fx.refusal(err)), (2, "TEAM_INVALID"),
                             f"{MF02} {name} before release access: {err[-300:]}")
            self.assertIsNone(doc, MF02)
            self.assertNotIn("Traceback", err, MF02)
        self.assertFalse(missing.parent.exists())

    def test_lone_surrogate_team_selectors_refuse_through_real_utf8_output(self) -> None:
        for name in ("high", "low", "interior", "trailing"):
            code, out, err = self.real_query("--grain", "personnel-feature", "--team", SURROGATE_TEAMS[name])
            self.assertEqual((code, _refusal_of(err)), (2, "TEAM_INVALID"),
                             f"{MF02} {name} through real UTF-8 output: {err[-400:]!r}")
            self.assertEqual(out, b"", MF02)
            self.assertNotIn(b"Traceback", err, MF02)
            self.assertTrue(err.isascii(), MF02)

    def test_valid_unicode_unknown_and_same_season_names_answer_through_real_utf8_output(self) -> None:
        feature = next(f for f in records("personnel-feature") if f["season"] == 2021)
        season = str(feature["season"])
        names = {"bmp": "Snowman \u2603", "non_bmp": "\U0001F3C8 Gridiron", "unknown": "No Such Program",
                 "same_season": feature["team_name"], "same_season_case": feature["team_name"].upper()}
        for key, team in names.items():
            for grain in TEAM_GRAINS:
                self.assertIsNone(_filter_refusal(grain, team), f"{key} at the {grain} filter")
            code, out, err = self.real_query("--grain", "personnel-feature", "--team", team, "--season", season,
                                             "--all")
            self.assertEqual(code, 0, f"{key}: {err[-400:]!r}")
            doc = json.loads(out.decode("utf-8"))
            in_code, in_doc, in_err = ask("--grain", "personnel-feature", "--team", team, "--season", season, "--all")
            self.assertEqual(in_code, 0, in_err)
            self.assertEqual(out, (json.dumps(in_doc, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"), key)
            self.assertEqual(doc["filters"]["team"], team, key)
            if key.startswith("same_season"):
                self.assertTrue(doc["rows"], key)
                self.assertEqual({r["team_key"] for r in doc["rows"]}, {feature["team_key"]}, key)
            else:
                self.assertEqual((doc["total"], doc["rows"]), (0, []), key)
        self.assertEqual(err, b"")


class MountedGenuineTests(unittest.TestCase):
    def test_the_canonical_release_verifies_with_the_pinned_profile(self) -> None:
        data = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or "")
        profile = pa.ASSOCIATION_PROFILE
        if not str(data) or profile is None:
            self.skipTest("the private data root or the pinned canonical profile is absent")
        db = data / "canonical" / pa.POPULATION / "sha256" / profile["database_identity"] / pa.DB_FILE
        if not db.is_file():
            self.skipTest("the canonical association release is not mounted")
        with pa.PersonnelAssociation(db) as reader:
            self.assertEqual(reader.database_identity, profile["database_identity"])
            pop = reader.summary["population"]
            expected = pa.ANCHORS["expected"]["counts"]
            self.assertEqual((pop["targets"], pop["views"], pop["joined_views"], pop["common_support_games"]),
                             (expected["targets"], expected["views"], expected["joined_views"],
                              expected["common_support_games"]))
            self.assertEqual(sum(1 for c in reader.summary["comparisons"] if c["primary"]), 1)


if __name__ == "__main__":
    unittest.main()
