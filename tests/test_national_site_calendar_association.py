"""National retrospective site/calendar association 2016-2023 (BAT-734, Cycle #63 TP63-A01).

Synthetic tiny worlds only (``tests/site_calendar_association_fixture.py``: the accepted builders' parents plus invented
provider captures, bindings and receipts): every qualification and derivation rule, the frozen fits on invented data,
determinism, the six-grain applicability matrix and refusal precedence, coordinated rehashed forgeries, malformed JSON
and numeric boundaries, literal local locations and native aliases. The mounted genuine case runs only when the private
data root and the pinned canonical profile are present."""
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

import site_calendar_association_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import context_association as ca  # noqa: E402
from aggie_analytics.retrospective_baseline import context_association_build as cab  # noqa: E402
from aggie_analytics.retrospective_baseline import query as q  # noqa: E402
from aggie_analytics.retrospective_baseline import reference_fit as rf  # noqa: E402

STATE: dict = {}


def setUpModule() -> None:
    base = Path(tempfile.mkdtemp(prefix="scs-t-"))
    world = fx.build_world(base / "w")
    contract_doc, qualified = fx.contract_for(world)
    contract = fx.write_contract(base / "contract.json", contract_doc)
    anchors = fx.contract_anchors(contract)
    code, result, err = fx.run_build(contract, world, base / "out")
    if code != 0:
        raise AssertionError(f"the fixture build refused: {err}")
    STATE.update(base=base, world=world, contract=contract, contract_doc=contract_doc, qualified=qualified,
                 anchors=anchors, result=result, db=fx.database_of(result))


def tearDownModule() -> None:
    shutil.rmtree(STATE["base"], ignore_errors=True)


def ask(*argv: str, db=None, anchors=None):
    return fx.query(STATE["anchors"] if anchors is None else anchors, STATE["db"] if db is None else db, *argv)


def records(grain: str, *argv: str) -> list[dict]:
    code, doc, err = ask("--grain", grain, "--all", *argv)
    if code != 0:
        raise AssertionError(err)
    return doc["rows"]


def quals() -> dict[str, dict]:
    return {r["contest_key"]: r for r in records("context-qualification")}


def contains_negative_zero(value) -> bool:
    if isinstance(value, float):
        return value == 0.0 and math.copysign(1.0, value) < 0
    if isinstance(value, dict):
        return any(contains_negative_zero(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_negative_zero(v) for v in value)
    return False


class RuleTests(unittest.TestCase):
    def test_date_window_is_minus_14_to_plus_36_hours_without_an_inferred_timezone(self) -> None:
        self.assertEqual(ca.date_state("2021-09-03T10:00:00Z", "2021-09-04")[0], "COMPATIBLE_WITH_PARENT_LOCAL_DATE")
        self.assertEqual(ca.date_state("2021-09-03T09:59:59.999Z", "2021-09-04")[0],
                         "INCOMPATIBLE_WITH_PARENT_LOCAL_DATE")
        self.assertEqual(ca.date_state("2021-09-05T11:59:59Z", "2021-09-04"),
                         ("COMPATIBLE_WITH_PARENT_LOCAL_DATE", None, 1))
        self.assertEqual(ca.date_state("2021-09-05T12:00:00Z", "2021-09-04")[1],
                         "PROVIDER_START_OUTSIDE_PARENT_DATE_WINDOW")
        for bad in ("2021-09-04T12:00:00", "2021-09-04 12:00:00Z", "2021-09-04T12:00:00+00:00", None, 7, ""):
            self.assertEqual(ca.date_state(bad, "2021-09-04"), ("UNSUPPORTED", "PROVIDER_START_MALFORMED", None))

    def test_site_claims_codes_and_agreement(self) -> None:
        self.assertEqual((ca.site_claim(True, "A"), ca.site_claim(False, "B")), ("NEUTRAL", "HOME_B"))
        self.assertEqual(ca.site_agreement("HOME_A", "HOME_A"), "AGREE")
        self.assertEqual(ca.site_agreement("HOME_A", "NEUTRAL"), "DISAGREE")
        self.assertEqual(ca.site_agreement("UNKNOWN", "HOME_A"), "UNSUPPORTED")
        self.assertEqual([ca.site_code(s, v) for s in ("HOME_A", "HOME_B", "NEUTRAL") for v in "AB"],
                         [1, -1, -1, 1, 0, 0])
        self.assertIsNone(ca.site_code(None, "A"))

    def test_calendar_blocks_never_impute_zero_or_choose_by_input_order(self) -> None:
        empty = ca.calendar_block([], ["2021-08-01"], "2021-09-04", None)
        self.assertEqual((empty["state"], empty["interval_days"], empty["excluded_prior_count"]),
                         ("NO_ELIGIBLE_SAME_SEASON_PRIOR", None, 1))
        tie = ca.calendar_block([("ncaa:2", "2021-08-28"), ("ncaa:1", "2021-08-28")], [], "2021-09-04", None)
        self.assertEqual((tie["state"], tie["latest_prior_contest_keys"], tie["interval_days"]),
                         ("AMBIGUOUS_LATEST_PRIOR", ["ncaa:1", "ncaa:2"], None))
        qualified = ca.calendar_block([("ncaa:1", "2021-08-21"), ("ncaa:2", "2021-08-28")], ["2021-08-30"],
                                      "2021-09-04", None)
        self.assertEqual((qualified["interval_days"], qualified["intervening_calendar_days"],
                          qualified["excluded_prior_after_latest_eligible"]), (7, 6, 1))
        broken = ca.calendar_block([("ncaa:1", "2021-08-21")], [], "2021-09-04", "PRIOR_DATE_DIFFERS")
        self.assertEqual((broken["state"], broken["interval_days"]), ("PRIOR_LINEAGE_INVALID", None))

    def test_rules_are_deep_copies_and_the_model_namespace_is_closed(self) -> None:
        doc = ca.rules_document()
        doc["labels"]["pit_eligibility"] = "PIT_ADMITTED"
        doc["models"][ca.MODEL_HISTORY]["solver"]["lambda"] = 99
        self.assertEqual(ca.LABELS["pit_eligibility"], "PIT_NOT_ADMITTED")
        self.assertEqual(ca.MODELS[ca.MODEL_HISTORY]["solver"]["lambda"], 1)
        self.assertEqual(len(ca.MODEL_IDS), 7)
        self.assertEqual(ca.MARGIN_MODELS, (ca.PARENT_RIDGE,))
        self.assertEqual(ca.COLUMNS[ca.MODEL_SITE_CALENDAR][0], ca.COLUMNS[ca.MODEL_HISTORY][0])

    def test_the_committed_contract_restates_the_module_rules(self) -> None:
        path = ROOT / ca.CONTRACT_REL
        if not path.is_file():
            self.skipTest("the research contract is not committed in this checkout state")
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(ca.canonical_json_bytes(contract["rules"]), ca.canonical_json_bytes(ca.rules_document()))
        self.assertEqual(ca.ANCHORS["contract_sha256"], ca.sha256_file(path))
        for key in ("inputs", "parent_contracts", "expected"):
            self.assertEqual(ca.canonical_json_bytes(contract[key]), ca.canonical_json_bytes(ca.ANCHORS[key]), key)


class QualificationTests(unittest.TestCase):
    def test_every_planted_provider_class_keeps_its_state_and_reason(self) -> None:
        got = quals()
        want = {"SITE_DISAGREE": ("PROVIDER_GAME_JOINED", "SITE_DISAGREES_WITH_PARENT"),
                "START_OUTSIDE_WINDOW": ("PROVIDER_GAME_JOINED", "DATE_PROVIDER_START_OUTSIDE_PARENT_DATE_WINDOW"),
                "ABSENT": ("UNSUPPORTED", "PROVIDER_GAME_ABSENT_FROM_CAPTURE"),
                "DUPLICATED": ("UNSUPPORTED", "PROVIDER_GAME_ID_DUPLICATED"),
                "MALFORMED": ("UNSUPPORTED", "PROVIDER_FIELD_MALFORMED"),
                "PARTICIPANTS_DIFFER": ("UNSUPPORTED", "PROVIDER_PARTICIPANTS_DIFFER"),
                "SEASON_DIFFERS": ("UNSUPPORTED", "PROVIDER_SEASON_DIFFERS")}
        self.assertEqual(sorted(STATE["world"]["plan"].values()), sorted(want))
        for key, kind in STATE["world"]["plan"].items():
            record = got[key]
            state, reason = want[kind]
            self.assertEqual(record["provider_state"], state, kind)
            self.assertIn(reason, record["support_reasons"], kind)
            self.assertEqual(record["support_state"], "OUTSIDE_COMMON_SUPPORT", kind)
            if state == "UNSUPPORTED":
                self.assertEqual((record["site_agreement"], record["agreed_site"], record["date_state"]),
                                 ("UNSUPPORTED", None, "UNSUPPORTED"), kind)
        self.assertEqual(got[next(k for k, v in STATE["world"]["plan"].items() if v == "MALFORMED")]["provider"], None)

    def test_unconfirmed_bindings_are_unsupported_never_matched_by_number_or_name(self) -> None:
        org = STATE["world"]["unconfirmed_org"]
        for record in quals().values():
            if org in (record["a_org_id"], record["b_org_id"]):
                side = "a" if record["a_org_id"] == org else "b"
                self.assertEqual((record[f"{side}_binding"]["state"], record[f"{side}_binding"]["reason"],
                                  record[f"{side}_binding"]["cfbd_team_id"]),
                                 ("UNSUPPORTED", "BINDING_NOT_CONFIRMED", None))
                self.assertEqual(record["provider_reason"], "PARTICIPANT_BINDING_UNSUPPORTED")
                self.assertIn(f"{side.upper()}_BINDING_NOT_CONFIRMED", record["support_reasons"])

    def test_sites_neutral_swaps_and_codes_follow_the_agreed_parent_role(self) -> None:
        got = quals()
        agreed = [r for r in got.values() if r["site_agreement"] == "AGREE"]
        self.assertEqual({r["agreed_site"] for r in agreed}, {"HOME_A", "HOME_B", "NEUTRAL"})
        features = {f["feature_key"]: f for f in records("context-feature")}
        swapped = 0
        for r in agreed:
            a, b = features[f"{r['contest_key']}|A"], features[f"{r['contest_key']}|B"]
            want = {"HOME_A": 1, "HOME_B": -1, "NEUTRAL": 0}[r["agreed_site"]]
            self.assertEqual((a["site_code"], b["site_code"]), (want, -want))
            if r["agreed_site"] == "NEUTRAL":
                swapped += r["provider_home_side"] == "B"
        self.assertGreaterEqual(swapped, 1, "a provider home/away designation swap at a neutral site")

    def test_calendar_intervals_are_latest_strictly_earlier_same_season_priors(self) -> None:
        got = quals()
        states = {r[f"{s}_calendar"]["state"] for r in got.values() for s in "ab"}
        self.assertTrue({"QUALIFIED_CALENDAR_INTERVAL", "NO_ELIGIBLE_SAME_SEASON_PRIOR",
                         "AMBIGUOUS_LATEST_PRIOR"} <= states)
        for r in got.values():
            for s in "ab":
                cal, hist = r[f"{s}_calendar"], r[f"{s}_history"]
                self.assertEqual(cal["eligible_prior_count"], hist["games"])
                if cal["state"] == "QUALIFIED_CALENDAR_INTERVAL":
                    self.assertLess(cal["latest_prior_date"], r["contest_date"])
                    self.assertIn(cal["latest_prior_contest_keys"][0], hist["contributing_contest_keys"])
                    self.assertGreaterEqual(cal["interval_days"], 1)
                else:
                    self.assertIsNone(cal["interval_days"])
                self.assertNotIn(r["contest_key"], hist["contributing_contest_keys"])

    def test_support_requires_every_join_and_the_cohort_is_never_forced(self) -> None:
        got = quals()
        census = STATE["result"]["census"]
        supported = [r for r in got.values() if r["support_state"] == "COMMON_SUPPORT"]
        self.assertEqual(len(supported), census["common_support_games"])
        self.assertEqual(sorted(k for k, r in got.items() if r["support_state"] != "COMMON_SUPPORT"),
                         sorted(STATE["anchors"]["expected"]["excluded_games"]))
        for r in supported:
            self.assertEqual((r["support_reasons"], r["site_agreement"], r["date_state"]),
                             ([], "AGREE", "COMPATIBLE_WITH_PARENT_LOCAL_DATE"))
        tie = got[STATE["world"]["tie_key"]]
        self.assertEqual((tie["support_state"], tie["label_state"]), ("COMMON_SUPPORT", "TIE"))

    def test_source_clocks_and_lineage_stay_visible(self) -> None:
        for r in quals().values():
            if r["provider"] is None:
                continue
            clock = r["capture_clock"]
            self.assertTrue(clock["observed_after_target"])
            self.assertEqual(clock["response_sha256"], r["provider"]["capture_sha256"])
            self.assertIn("NOT_AN_INDEPENDENT_CONFIRMATION", clock["upstream_lineage"])
            self.assertEqual(len(r["history_view_sha256"]), 2)


class DerivationTests(unittest.TestCase):
    def test_views_are_exact_negations_and_no_negative_zero_is_stored(self) -> None:
        features = records("context-feature")
        by = {(f["contest_key"], f["view"]): f for f in features}
        for (key, view), a in by.items():
            if view != "A":
                continue
            b = by[(key, "B")]
            self.assertEqual(b["history_log_odds_difference"], ca.negate(a["history_log_odds_difference"]))
            if a["design_site_calendar"] is not None:
                self.assertEqual(b["design_site_calendar"], [ca.negate(v) for v in a["design_site_calendar"]])
                self.assertEqual(a["design_history"], a["design_site_calendar"][:1])
            else:
                self.assertIsNone(b["design_site_calendar"])
        for grain in ("context-feature", "context-estimate", "context-parameter"):
            self.assertFalse(any(contains_negative_zero(r) for r in records(grain)), grain)

    def test_design_columns_are_the_frozen_h_s_and_c(self) -> None:
        for f in records("context-feature"):
            th, oh = f["team_history"], f["opponent_history"]
            self.assertEqual(th["log_odds"], ca.history_log_odds(th["wins"], th["losses"], th["ties"]))
            if f["view"] == "A":
                self.assertEqual(f["history_log_odds_difference"], th["log_odds"] - oh["log_odds"] + 0.0)
            if f["support_state"] == "COMMON_SUPPORT":
                tc, oc = f["team_calendar"], f["opponent_calendar"]
                self.assertEqual(f["calendar_interval_difference_days"], tc["interval_days"] - oc["interval_days"])
                self.assertEqual(f["design_site_calendar"][1:], [float(f["site_code"]) + 0.0,
                                                                 float(f["calendar_interval_difference_days"]) + 0.0])

    def test_scales_and_fits_use_only_2016_2022_common_decisive_rows(self) -> None:
        features = records("context-feature")
        got = quals()
        cohort = [f for f in features if f["view"] == "A" and f["season"] in ca.FIT_SEASONS and
                  f["support_state"] == "COMMON_SUPPORT" and got[f["contest_key"]]["label_state"] == "DECISIVE"]
        params = {p["model_id"]: p for p in records("context-parameter")}
        n = len(cohort)
        self.assertEqual(params[ca.MODEL_HISTORY]["training"]["games"], n)
        for j in range(3):
            want = math.sqrt(math.fsum(t for f in cohort for v in (f["design_site_calendar"][j],
                                                                   -f["design_site_calendar"][j])
                                       for t in (0.5 * v * v,)) / n)
            self.assertEqual(params[ca.MODEL_SITE_CALENDAR]["scales_repr"][j], repr(want))
        self.assertEqual(params[ca.MODEL_HISTORY]["scales_repr"][0], params[ca.MODEL_SITE_CALENDAR]["scales_repr"][0])
        self.assertEqual(params[ca.MODEL_HISTORY]["training"]["oriented_rows"], 2 * n)
        self.assertEqual(params[ca.MODEL_HISTORY]["training"]["excluded_by_label_state"], {"TIE": 1})

    def test_comparison_outcomes_never_reach_the_fit(self) -> None:
        qualified = copy.deepcopy(STATE["qualified"])
        flipped = copy.deepcopy(qualified["labels"])
        for q_ in qualified["qualifications"]:
            if q_["season"] in ca.COMPARISON_SEASONS and flipped[q_["contest_key"]]["label_state"] == "DECISIVE":
                flipped[q_["contest_key"]]["y_a"] = 1 - flipped[q_["contest_key"]]["y_a"]
        genuine = ca.derive_from_qualifications(qualified["qualifications"], qualified["labels"], qualified["witnesses"])
        changed = ca.derive_from_qualifications(qualified["qualifications"], flipped, qualified["witnesses"])
        self.assertEqual(genuine["parameters"], changed["parameters"])
        self.assertNotEqual(genuine["scores"], changed["scores"])

    def test_fit_failure_is_recorded_and_every_affected_game_abstains(self) -> None:
        qualified = copy.deepcopy(STATE["qualified"])
        for q_ in qualified["qualifications"]:
            if q_["season"] in ca.FIT_SEASONS:
                q_["a_calendar"] = ca.calendar_block([], [], q_["contest_date"], None)
                q_["support_state"], q_["support_reasons"], q_["support_pattern"] = ca.support_decision(q_)
        derived = ca.derive_from_qualifications(qualified["qualifications"], qualified["labels"],
                                                qualified["witnesses"])
        states = {p["model_id"]: p["parameter_state"] for p in derived["parameters"]}
        self.assertEqual(states, {m: "FIT_EMPTY" for m in ca.NEW_MODELS})
        supported = [e for e in derived["estimates"] if e["estimate_state"] == "SUPPORTED"]
        self.assertEqual(supported, [])
        reasons = {e["abstention_reason"] for e in derived["estimates"] if e["season"] in ca.COMPARISON_SEASONS}
        self.assertIn("ABSTAIN_FIT_FAILED", reasons)
        challenger = [r for r in derived["summary"] if r["model_id"] == ca.MODEL_SITE_CALENDAR]
        self.assertEqual({r["delta_state"] for r in challenger}, {"NULL_FIT_FAILED"})
        self.assertTrue(all(r["brier_mean_difference"] is None for r in challenger))

    def test_the_accepted_primitive_fits_independently_built_rows_identically(self) -> None:
        params = {p["model_id"]: p for p in records("context-parameter")}
        features = records("context-feature")
        got = quals()
        labels = {k: STATE["qualified"]["labels"][k] for k in got}
        cohort = [f for f in features if f["view"] == "A" and f["season"] in ca.FIT_SEASONS and
                  f["support_state"] == "COMMON_SUPPORT" and labels[f["contest_key"]]["label_state"] == "DECISIVE"]
        scales = [float(s) for s in params[ca.MODEL_SITE_CALENDAR]["scales_repr"]]
        rows = []
        for f in cohort:
            z = tuple(v / s for v, s in zip(f["design_site_calendar"], scales))
            y = float(labels[f["contest_key"]]["y_a"])
            rows += [rf.Row(z, y, 0.5), rf.Row(tuple(-v for v in z), 1.0 - y, 0.5)]
        result = rf.fit_logistic(rows, 3)
        self.assertEqual([repr(b) for b in result.coefficients], params[ca.MODEL_SITE_CALENDAR]["coefficients_repr"])

    def test_estimates_complement_exactly_and_scores_are_exact(self) -> None:
        estimates = {e["estimate_key"]: e for e in records("context-estimate")}
        labels = STATE["qualified"]["labels"]
        for e in estimates.values():
            if e["orientation"] != "A":
                continue
            b = estimates[f"{e['contest_key']}|{e['model_id']}|B"]
            if e["estimate_state"] == "SUPPORTED":
                self.assertEqual(Fraction(e["probability"]) + Fraction(b["probability"]), 1)
                self.assertEqual(ca.frac(e["probability_exact"]), Fraction(e["probability"]))
            else:
                self.assertEqual((b["estimate_state"], b["probability"]), ("ABSTAINED", None))
        for s in records("context-score"):
            if s["score_source"] != ca.SCORE_SOURCES["scores"]:
                continue
            label = labels[s["contest_key"]]
            if s["score_state"] == "SCORED":
                p = ca.frac(s["probability_a_exact"])
                self.assertEqual(ca.frac(s["brier"]), (p - label["y_a"]) ** 2)
                self.assertEqual(s["log_loss"], repr(ca.log_loss_value(p, label["y_a"])))
            elif label["label_state"] == "TIE" and s["support_state"] == "COMMON_SUPPORT":
                self.assertEqual(s["unscored_reason"], "LABEL_TIE")

    def test_parent_witnesses_are_the_unchanged_c56_game_scores(self) -> None:
        witnesses = [s for s in records("context-score") if s["score_source"] == ca.SCORE_SOURCES["witnesses"]]
        self.assertEqual(len(witnesses), 5 * len(quals()))
        for w in witnesses:
            self.assertEqual(ca.sha256_bytes(ca.canonical_line(w["parent_score"]).encode("utf-8")),
                             w["parent_score_line_sha256"])
            self.assertEqual(w["model_sha256"], ca.PARENT_MODEL_SHA256[w["model_id"]])
            if w["model_id"] == ca.PARENT_RIDGE:
                self.assertEqual(w["metric_kind"], "MARGIN")
                self.assertNotIn("brier", w["parent_score"])
            else:
                self.assertEqual(w["metric_kind"], "PROBABILITY")


class SummaryTests(unittest.TestCase):
    def test_seventy_canonical_rows_on_the_common_cohort_with_one_primary_delta(self) -> None:
        rows = records("context-summary")
        self.assertEqual(len(rows), 70)
        self.assertEqual(sum(1 for r in rows if r["primary"]), 1)
        primary = next(r for r in rows if r["primary"])
        self.assertEqual((primary["model_id"], primary["scope_kind"], primary["scope_id"]),
                         (ca.MODEL_SITE_CALENDAR, "PARTITION", "COMPARISON"))
        for r in rows:
            if r["model_id"] == ca.MODEL_SITE_CALENDAR and r["scored_games"]:
                self.assertEqual(r["delta_state"], "COMPUTED_ON_IDENTICAL_SCORED_GAMES")
                control = next(c for c in rows if c["model_id"] == ca.MODEL_HISTORY and
                               (c["scope_kind"], c["scope_id"]) == (r["scope_kind"], r["scope_id"]))
                self.assertEqual(ca.frac(r["brier_mean_difference"]),
                                 ca.frac(r["brier_mean"]) - ca.frac(control["brier_mean"]))
            elif r["model_id"] != ca.MODEL_SITE_CALENDAR:
                self.assertEqual((r["delta_state"], r["brier_mean_difference"]), ("NOT_CLAIMED", None))
            if r["model_id"] == ca.PARENT_RIDGE:
                self.assertEqual((r["metric_kind"], r["brier_mean"]), ("MARGIN", None))
        windows = {(r["scope_kind"], r["scope_id"]): r["eligible_games"] for r in rows}
        self.assertEqual(windows[("PARTITION", "COMPARISON")], windows[("SEASON", "2023")])

    def test_filtered_summaries_recompute_before_paging_and_model_filtering(self) -> None:
        got = quals()
        team = got[next(k for k, r in got.items() if r["support_state"] == "COMMON_SUPPORT" and r["season"] == 2023)]
        rows = records("context-summary", "--team", team["a_key"])
        selected = [r for r in got.values() if team["a_key"] in (r["a_key"], r["b_key"]) and
                    r["support_state"] == "COMMON_SUPPORT"]
        for r in rows:
            window = [s for s in selected if s["season"] in r["seasons"]]
            self.assertEqual(r["eligible_games"], len(window))
            self.assertFalse(r["primary"])
        hidden = records("context-summary", "--team", team["a_key"], "--model", ca.MODEL_SITE_CALENDAR)
        self.assertEqual([r["summary_key"] for r in hidden],
                         [r["summary_key"] for r in rows if r["model_id"] == ca.MODEL_SITE_CALENDAR])
        self.assertEqual([r["brier_mean_difference"] for r in hidden],
                         [r["brier_mean_difference"] for r in rows if r["model_id"] == ca.MODEL_SITE_CALENDAR])
        code, page, _err = ask("--grain", "context-summary", "--team", team["a_key"], "--limit", "3", "--offset", "2")
        self.assertEqual((code, page["total"], page["rows"]), (0, len(rows), rows[2:5]))

    def test_empty_disjoint_and_unknown_selections_serve_no_rows(self) -> None:
        for argv in (("--team", "org:424242"), ("--contest", "ncaa:424242"), ("--season", "2019"),
                     ("--season", "2024"), ("--season", "2023", "--partition", "FIT"),
                     ("--team", "No Such Program")):
            for grain in ("context-summary", "context-score", "context-feature", "context-qualification"):
                code, doc, err = ask("--grain", grain, *argv)
                self.assertEqual((code, doc["total"], doc["rows"]), (0, 0, []), f"{grain} {argv} {err}")
        code, doc, _err = ask("--grain", "context-summary", "--season", "2024")
        self.assertEqual(doc["season_scope_state"], "SEASON_OUTSIDE_RELEASE")
        code, doc, _err = ask("--grain", "context-summary", "--season", "2023", "--partition", "FIT")
        self.assertEqual(doc["season_scope_state"], "SEASON_AND_PARTITION_DISJOINT")
        compatible = records("context-summary", "--season", "2022", "--partition", "FIT")
        self.assertEqual({(r["scope_kind"], r["scope_id"]) for r in compatible},
                         {("SEASON", "2022"), ("PARTITION", "FIT")})
        by_scope = {(r["scope_id"], r["model_id"]): r for r in compatible}
        for model_id in ca.MODEL_IDS:
            self.assertEqual(by_scope[("2022", model_id)]["eligible_games"], by_scope[("FIT", model_id)]["eligible_games"])
        outside = next(k for k, r in quals().items() if r["support_state"] != "COMMON_SUPPORT")
        code, doc, _err = ask("--grain", "context-summary", "--contest", outside)
        self.assertEqual((code, doc["rows"]), (0, []))


class BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="scs-b-"))
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_order_chunk_and_interrupted_builds_are_byte_identical(self) -> None:
        genuine = STATE["result"]
        variants = [("reverse", ("--input-order", "reverse")), ("shuffle", ("--input-order", "shuffle:63")),
                    ("chunk1", ("--chunk-size", "1", "--checkpoint-dir", str(self.base / "c1"))),
                    ("chunk17", ("--chunk-size", "17", "--checkpoint-dir", str(self.base / "c17")))]
        for name, extra in variants:
            code, result, err = fx.run_build(STATE["contract"], STATE["world"], self.base / name, *extra)
            self.assertEqual(code, 0, f"{name}: {err}")
            self.assertEqual((result["database_sha256"], result["content_identity"], result["database_identity"]),
                             (genuine["database_sha256"], genuine["content_identity"], genuine["database_identity"]))
        ckpt = ("--chunk-size", "17", "--checkpoint-dir", str(self.base / "ci"))
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], self.base / "int", *ckpt,
                                         "--stop-after-chunks", "1")
        self.assertEqual((code, result["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"), err)
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], self.base / "int", *ckpt, "--resume")
        self.assertEqual((code, result["database_identity"]), (0, genuine["database_identity"]), err)
        code, again, err = fx.run_build(STATE["contract"], STATE["world"], self.base / "int", *ckpt, "--resume")
        self.assertEqual((code, again["state"]), (0, "ALREADY_PRESENT_IDENTICAL"), err)

    def test_collisions_and_drift_are_refused(self) -> None:
        out = self.base / "col"
        code, result, err = fx.run_build(STATE["contract"], STATE["world"], out)
        self.assertEqual(code, 0, err)
        db = fx.database_of(result)
        db.write_bytes(db.read_bytes() + b"\0")
        code, _r, err = fx.run_build(STATE["contract"], STATE["world"], out)
        self.assertEqual((code, fx.refusal(err)), (2, "REFUSED_IMMUTABLE_COLLISION"))
        doc = copy.deepcopy(STATE["contract_doc"])
        doc["rules"]["labels"]["pit_eligibility"] = "PIT_ADMITTED"
        code, _r, err = fx.run_build(fx.write_contract(self.base / "c1.json", doc), STATE["world"], self.base / "o1")
        self.assertEqual((code, fx.refusal(err)), (2, "CONTRACT_INVALID"))
        doc = copy.deepcopy(STATE["contract_doc"])
        first = next(iter(doc["expected"]["excluded_games"]))
        del doc["expected"]["excluded_games"][first]
        code, _r, err = fx.run_build(fx.write_contract(self.base / "c2.json", doc), STATE["world"], self.base / "o2")
        self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_INPUT_POPULATION_DRIFT"))
        doc = copy.deepcopy(STATE["contract_doc"])
        doc["inputs"]["provider_games"]["2021"]["sha256"] = "0" * 64
        code, _r, err = fx.run_build(fx.write_contract(self.base / "c3.json", doc), STATE["world"], self.base / "o3")
        self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_INPUT_TAMPERED"))
        doc = copy.deepcopy(STATE["contract_doc"])
        doc["parent_contracts"] = {"configs/national_di_population_2016_2025_contract.json": "0" * 64}
        code, _r, err = fx.run_build(fx.write_contract(self.base / "c4.json", doc), STATE["world"], self.base / "o4")
        self.assertEqual((code, fx.refusal(err)), (2, "PARENT_CONTRACT_MISMATCH"))

    def test_input_locations_are_literal_and_never_written(self) -> None:
        argv = ["--contract", str(STATE["contract"]), "--output-root", str(self.base / "c"),
                "--manifest-root", str(self.base / "m")]
        for root, code_ in (("\\\\bas-c63-host\\share\\data" if os.name == "nt" else None,
                             "CONTEXT_DATA_ROOT_LOCATION_UNSUPPORTED"),
                            (str(self.base / "absent"), "CONTEXT_DATA_ROOT_MISSING")):
            if root is None:
                continue
            code, _r, err = fx.run_build(STATE["contract"], {"data_root": root}, self.base / "x")
            self.assertEqual((code, fx.refusal(err)), (2, code_), root)
        self.assertTrue(argv)


class QueryTests(unittest.TestCase):
    MISSING = "missing-dir/national_site_calendar_association.sqlite"

    def refusal(self, *argv: str, db=None) -> str | None:
        code, doc, err = ask(*argv, db=self.MISSING if db is None else db)
        self.assertNotIn("Traceback", err)
        return fx.refusal(err) if code == 2 else None

    def test_every_grain_serves_its_complete_collection(self) -> None:
        counts = STATE["anchors"]["expected"]["counts"]
        for grain, total in (("context-qualification", counts["qualifications"]),
                             ("context-feature", counts["features"]), ("context-parameter", 2),
                             ("context-estimate", counts["estimates"]),
                             ("context-score", counts["scores"] + counts["witnesses"]), ("context-summary", 70)):
            code, doc, err = ask("--grain", grain, "--all")
            self.assertEqual((code, doc["total"], doc["returned"]), (0, total, total), f"{grain}: {err}")
            self.assertEqual(doc["pit_eligibility"], "PIT_NOT_ADMITTED")

    def test_applicability_matrix_is_refused_before_any_file_access(self) -> None:
        cases = [(("--grain", "context-feature", "--model", ca.PARENT_NULL), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-qualification", "--model", ca.MODEL_HISTORY), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-estimate", "--model", ca.PARENT_ELO), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-parameter", "--model", ca.PARENT_RIDGE), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-parameter", "--season", "2021"), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-parameter", "--team", "org:1"), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-parameter", "--partition", "FIT"), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-parameter", "--contest", "ncaa:1"), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-feature", "--model", "NOPE"), "MODEL_INVALID"),
                 (("--grain", "context-score", "--model", ""), "MODEL_INVALID"),
                 (("--grain", "context-parameter", "--team", ""), "INVALID_SELECTOR"),
                 (("--grain", "context-summary", "--season", "20x1"), "INVALID_SELECTOR"),
                 (("--grain", "context-summary", "--season", ""), "INVALID_SELECTOR"),
                 (("--grain", "context-summary", "--partition", "fit"), "INVALID_SELECTOR"),
                 (("--grain", "context-summary", "--contest", "espn:1"), "INVALID_SELECTOR"),
                 (("--grain", "context-summary", "--team", "org:x"), "INVALID_SELECTOR"),
                 (("--grain", "context-summary", "--team", "Tex\x07as"), "INVALID_SELECTOR"),
                 (("--grain", "nope"), "UNKNOWN_GRAIN"),
                 (("--grain", "context-score", "--limit", "x"), "LIMIT_INVALID"),
                 (("--grain", "context-score", "--limit", ""), "LIMIT_INVALID"),
                 (("--grain", "context-score", "--offset", "1.5"), "OFFSET_INVALID"),
                 (("--grain", "context-score", "--limit", "-1"), "NEGATIVE_LIMIT"),
                 (("--grain", "context-score", "--offset", "-2"), "NEGATIVE_OFFSET"),
                 (("--grain", "context-score", "--all", "--limit", "5"), "PAGING_CONFLICT"),
                 (("--grain", "context-score", "--all", "--offset", "0"), "PAGING_CONFLICT"),
                 (("--grain", "context-score", "--require-pit"), "CONTEXT_PIT_NOT_ADMITTED"),
                 (("--grain", "context-score", "--cutoff", "2023-09-01T00:00:00Z"), "TEMPORAL_FLAG_UNSUPPORTED"),
                 (("--grain", "context-score", "--as-of", "2023-09-01"), "TEMPORAL_FLAG_UNSUPPORTED"),
                 (("--grain", "context-score", "--orientation", "home"), "SELECTOR_NOT_APPLICABLE"),
                 (("--grain", "context-score", "--database", "x.sqlite"), "CONTEXT_MODE_CONFLICT"),
                 (("--grain", "context-score", "--personnel-association", "x.sqlite"), "CONTEXT_MODE_CONFLICT"),
                 (("--grain", "context-score", "--expect-identity", "abc"), "STALE_CONTEXT_IDENTITY"),
                 (("--grain", "context-score", "--bogus"), "ARGUMENT_INVALID"),
                 (("--season", "2021"), "ARGUMENT_INVALID")]
        for argv, code in cases:
            self.assertEqual(self.refusal(*argv), code, argv)
        self.assertFalse(Path(self.MISSING).parent.exists())
        self.assertEqual(self.refusal("--grain", "context-score"), "CONTEXT_DATABASE_MISSING")

    def test_frozen_precedence_between_refusal_families(self) -> None:
        self.assertEqual(self.refusal("--grain", "context-feature", "--model", "NOPE", "--team", ""), "MODEL_INVALID")
        self.assertEqual(self.refusal("--grain", "context-parameter", "--team", "", "--model", ca.PARENT_NULL),
                         "INVALID_SELECTOR")
        self.assertEqual(self.refusal("--grain", "nope", "--limit", "x"), "UNKNOWN_GRAIN")
        self.assertEqual(self.refusal("--grain", "context-score", "--limit", "x", "--model", "NOPE"), "LIMIT_INVALID")
        self.assertEqual(self.refusal("--grain", "nope", "--require-pit"), "CONTEXT_PIT_NOT_ADMITTED")
        self.assertEqual(self.refusal("--grain", "context-score", "--cutoff", "x", "--database", "y"),
                         "CONTEXT_MODE_CONFLICT")

    def test_selectors_intersect_and_team_names_stay_within_their_season(self) -> None:
        got = quals()
        record = got[next(k for k, r in got.items() if r["season"] == 2022)]
        by_key = ask("--grain", "context-feature", "--team", record["a_key"], "--season", "2022", "--all")[1]
        by_name = ask("--grain", "context-feature", "--team", record["a_team_name"].upper(), "--season", "2022",
                      "--all")[1]
        self.assertTrue(by_key["rows"])
        self.assertEqual(by_key["rows"], by_name["rows"])
        both = ask("--grain", "context-feature", "--team", record["a_key"], "--contest", record["contest_key"],
                   "--all")[1]
        self.assertEqual([r["feature_key"] for r in both["rows"]], [f"{record['contest_key']}|A"])
        scores = ask("--grain", "context-score", "--contest", record["contest_key"], "--all")[1]
        self.assertEqual(scores["total"], 7)
        self.assertEqual([r["model_id"] for r in scores["rows"]], list(ca.MODEL_IDS))

    def test_original_help_is_unchanged_and_the_mode_parser_describes_itself(self) -> None:
        parser = q.build_parser()
        formatter = parser._get_formatter()
        formatter.add_text(q.SHADOW_EPILOG)
        association = parser._get_formatter()
        association.add_text(q.ASSOCIATION_EPILOG)
        old = super(q._HistoricalParser, parser).format_help() + "\n" + formatter.format_help()
        self.assertEqual(parser.format_help(), old + "\n" + association.format_help())
        self.assertNotIn("context-association", parser.format_help())
        context = q.build_context_parser()
        epilog = context._get_formatter()
        epilog.add_text(q.CONTEXT_EPILOG)
        self.assertTrue(context.format_help().endswith(epilog.format_help()))

    def test_invocations_without_the_option_never_import_the_mode(self) -> None:
        code = (f"import sys; sys.path[:0] = [{str(ROOT / 'src')!r}]; "
                "from aggie_analytics.retrospective_baseline import query; "
                "rc = query.main(['--database', 'missing.sqlite', '--history-database', 'm.sqlite', '--grain', "
                "'summary']); rc2 = query.main(['--personnel-association', 'missing.sqlite', '--grain', "
                "'personnel-summary']); print(rc, rc2, "
                "'aggie_analytics.retrospective_baseline.context_association' in sys.modules)")
        with tempfile.TemporaryDirectory(prefix="scs-q-") as tmp:
            proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=tmp)
        self.assertEqual(proc.stdout.strip(), "2 2 False", proc.stderr)


class ForgeryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="scs-f-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.forger = fx.Forger(STATE["db"], self.base)

    def code(self, path: Path, anchors=None) -> str | None:
        try:
            with ca.ContextAssociation(path, anchors=STATE["anchors"] if anchors is None else anchors):
                return None
        except ca.ContextError as exc:
            return exc.code

    def forge(self, name: str, **kw) -> str | None:
        return self.code(self.forger.forge(name, **kw))

    def test_coordinated_scientific_forgeries_reach_their_own_rules(self) -> None:
        def joined(t):
            return next(r for r in t["qualifications"] if r["provider_state"] == "PROVIDER_GAME_JOINED" and
                        r["support_state"] == "COMMON_SUPPORT")

        def common_feature(t, view="A"):
            return next(f for f in t["features"] if f["support_state"] == "COMMON_SUPPORT" and f["view"] == view)

        def claim(t):
            r = joined(t)
            r["provider_site_claim"] = "NEUTRAL" if r["provider_site_claim"] != "NEUTRAL" else "HOME_A"

        def agreement(t):
            joined(t)["agreed_site"] = "HOME_B" if joined(t)["agreed_site"] != "HOME_B" else "HOME_A"

        def date(t):
            joined(t)["provider_utc_date_offset_days"] = 5

        def clock(t):
            joined(t)["capture_clock"]["retrieved_at_utc"] = "2016-01-01T00:00:00Z"

        def leakage(t):
            r = next(r for r in t["qualifications"] if r["a_history"]["games"] > 0)
            r["a_history"]["contributing_contest_keys"][0] = r["contest_key"]

        def log_odds(t):
            joined(t)["a_history"]["log_odds"] += 1e-9

        def interval(t):
            r = joined(t)
            r["a_calendar"]["interval_days"] += 1
            r["a_calendar"]["intervening_calendar_days"] += 1

        def zero(t):
            r = next(r for r in t["qualifications"] if r["a_calendar"]["state"] == "NO_ELIGIBLE_SAME_SEASON_PRIOR")
            r["a_calendar"]["interval_days"] = 0

        def support(t):
            r = next(r for r in t["qualifications"] if r["support_state"] != "COMMON_SUPPORT")
            r["support_state"] = "COMMON_SUPPORT"

        def binding(t):
            joined(t)["a_binding"]["rule"] = "FUZZY_NAME"

        def orientation(t):
            f = common_feature(t, "B")
            f["history_log_odds_difference"] += 0.5

        def design(t):
            common_feature(t)["design_site_calendar"][2] += 1.0

        def missing_zero(t):
            f = next(f for f in t["features"] if f["support_state"] != "COMMON_SUPPORT")
            f["design_site_calendar"] = [0.0, 0.0, 0.0]

        def feature_name(t):
            t["features"][0]["team_name"] = "Renamed"

        def complement(t):
            e = next(e for e in t["estimates"] if e["estimate_state"] == "SUPPORTED")
            e["opponent_probability"] = "0.000000000001"

        def parameter(t):
            t["parameters"][1]["coefficients"][0] = "1.000000000000"

        def estimate(t):
            e = next(e for e in t["estimates"] if e["estimate_state"] == "SUPPORTED" and e["orientation"] == "A")
            e["linear_predictor_repr"] = "0.5"

        def score(t):
            s = next(s for s in t["scores"] if s["score_state"] == "SCORED")
            s["brier_decimal"] = "0.999999999999"

        def witness(t):
            w = next(w for w in t["witnesses"] if w["metric_kind"] == "PROBABILITY")
            w["parent_score"]["brier_decimal"] = "0.999999999999"

        def witness_rehash(t):
            w = next(w for w in t["witnesses"] if w["metric_kind"] == "PROBABILITY")
            w["parent_score"]["brier_decimal"] = "0.999999999999"
            w["parent_score_line_sha256"] = ca.sha256_bytes(ca.canonical_line(w["parent_score"]).encode("utf-8"))

        def label(t):
            key = next(s["contest_key"] for s in t["scores"] if s["score_state"] == "SCORED")
            for s in t["scores"]:
                if s["contest_key"] == key:
                    s["y_a"] = 1 - s["y_a"]

        def summary(t):
            t["summary"][0]["window_targets"] += 1

        def census(t):
            t["census"][0]["population"]["targets"] += 1

        cases = {"CONTEXT_PROVIDER_CLAIM_INVALID": claim, "CONTEXT_SITE_MISMATCH": agreement,
                 "CONTEXT_DATE_STATE_INVALID": date, "CONTEXT_SOURCE_CLOCK_INVALID": clock,
                 "CONTEXT_HISTORY_LEAKAGE": leakage, "CONTEXT_LOG_ODDS_MISMATCH": log_odds,
                 "CONTEXT_CALENDAR_INVALID": interval, "CONTEXT_MISSING_AS_ZERO": zero,
                 "CONTEXT_SUPPORT_MISMATCH": support, "CONTEXT_BINDING_INVALID": binding,
                 "CONTEXT_ORIENTATION_MISMATCH": orientation, "CONTEXT_DESIGN_MISMATCH": design,
                 "CONTEXT_FEATURE_MISMATCH": feature_name, "CONTEXT_COMPLEMENT_INVALID": complement,
                 "CONTEXT_PARAMETER_MISMATCH": parameter, "CONTEXT_ESTIMATE_MISMATCH": estimate,
                 "CONTEXT_SCORE_MISMATCH": score, "CONTEXT_WITNESS_MISMATCH": witness,
                 "CONTEXT_PARENT_WITNESS_DRIFT": witness_rehash, "CONTEXT_LABEL_INCONSISTENT": label,
                 "CONTEXT_SUMMARY_MISMATCH": summary, "CONTEXT_CENSUS_MISMATCH": census}
        for want, fn in cases.items():
            self.assertEqual(self.forge(want.lower(), records=fn), want, want)
        self.assertEqual(self.forge("missing_zero_design", records=missing_zero), "CONTEXT_MISSING_AS_ZERO")

    def test_frozen_common_cohort_drift_is_refused(self) -> None:
        def fabricate(t):
            r = next(r for r in t["qualifications"] if r["support_pattern"] ==
                     "QUALIFIED_CALENDAR_INTERVAL,QUALIFIED_CALENDAR_INTERVAL" and r["support_state"] != "COMMON_SUPPORT")
            r["provider_reason"] = None
            r["support_state"], r["support_reasons"], r["support_pattern"] = "COMMON_SUPPORT", [], r["support_pattern"]
        # every coherent path to a different cohort is refused (support rule first, frozen cohort for a coherent one)
        self.assertIn(self.forge("cohort", records=fabricate), ("CONTEXT_PROVIDER_CLAIM_INVALID",
                                                                 "CONTEXT_SUPPORT_MISMATCH",
                                                                 "CONTEXT_COMMON_COHORT_DRIFT"))
        anchors = copy.deepcopy(STATE["anchors"])
        anchors["expected"]["excluded_games"].pop(next(iter(anchors["expected"]["excluded_games"])))
        self.assertEqual(self.code(STATE["db"], anchors), "CONTEXT_PARENT_MISMATCH")

    def test_collections_types_aliases_and_identities(self) -> None:
        def drop(t):
            t["features"].pop(3)

        def extra(t):
            t["features"].append({**t["features"][0], "feature_key": "ncaa:1|A"})

        def swap(t):
            t["features"][0], t["features"][1] = t["features"][1], t["features"][0]

        def duplicate(t):
            t["parameters"].append(t["parameters"][0])

        def float_count(t):
            history = t["qualifications"][0]["a_history"]
            history["games"] = float(history["games"])

        def float_season(t):
            t["qualifications"][0]["season"] = float(t["qualifications"][0]["season"])

        def bool_code(t):
            f = next(f for f in t["features"] if f["site_code"] == 1)
            f["site_code"] = True

        def shape(t):
            t["census"][0]["extra"] = 1

        def pit(t):
            t["scores"][0]["pit_eligibility"] = "PIT_ADMITTED"

        def kind(t):
            t["scores"][0]["record_type"] = "CONTEXT_FORECAST"

        cases = {"CONTEXT_FEATURE_ROW_MISSING": drop, "CONTEXT_FEATURE_ROW_EXTRA": extra,
                 "CONTEXT_ORDER_MISMATCH": swap, "CONTEXT_DUPLICATE_ROW": duplicate,
                 "CONTEXT_FIELD_TYPE_INVALID": float_count, "CONTEXT_INDEX_MISMATCH": float_season,
                 "CONTEXT_RECORD_SHAPE_INVALID": shape, "CONTEXT_PIT_CLAIM_INVALID": pit,
                 "CONTEXT_RECORD_TYPE_INVALID": kind}
        for want, fn in cases.items():
            self.assertEqual(self.forge(want.lower(), records=fn), want, want)
        self.assertEqual(self.forge("bool_code", records=bool_code), "CONTEXT_FIELD_TYPE_INVALID")
        def spaced(raw):
            changed = raw["census"][0].replace("{", "{ ", 1)
            self.assertNotEqual(changed, raw["census"][0])
            raw["census"][0] = changed
        self.assertEqual(self.forge("canonical", lines=spaced), "CONTEXT_RECORD_NOT_CANONICAL")
        self.assertEqual(self.forge("index", after_blocks=[("UPDATE blocks SET records = records + 1 WHERE ord = 0",
                                                            ())]), "CONTEXT_INDEX_MISMATCH")
        self.assertEqual(self.forge("labels", meta={"labels": {**ca.LABELS, "pit_eligibility": "PIT_ADMITTED"}}),
                         "CONTEXT_PIT_CLAIM_INVALID")
        self.assertEqual(self.forge("rules", meta={"rules": {"rules": 1}}), "CONTEXT_RULES_CLAIM_INVALID")
        self.assertEqual(self.forge("inputs", meta={"inputs": {"inputs": {}, "expected": {}}}),
                         "CONTEXT_PARENT_MISMATCH")
        self.assertEqual(self.forge("float_count", document=lambda d: d["table_counts"].__setitem__(
            "blocks", float(d["table_counts"]["blocks"]))), "CONTEXT_IDENTITY_DOCUMENT_MISMATCH")
        self.assertEqual(self.forge("content", manifest_patch={"content_identity": "0" * 64}),
                         "CONTEXT_CONTENT_IDENTITY_MISMATCH")
        self.assertEqual(self.forge("contract", document={"contract_sha256": "0" * 64}), "CONTEXT_CONTRACT_MISMATCH")
        self.assertEqual(self.forge("members", manifest_patch={"extra": 1}), "CONTEXT_MANIFEST_MALFORMED")

    def test_profile_pins_coordinated_value_forgeries_and_controls_are_served(self) -> None:
        def start(t):
            r = next(r for r in t["qualifications"] if r["provider_state"] == "PROVIDER_GAME_JOINED" and
                     r["provider_utc_date_offset_days"] == 0)
            r["provider"]["start_claim_utc"] = r["contest_date"] + "T20:00:00Z"
            labels = ca.labels_from_scores(t["scores"])
            rebuilt = ca.derive_from_qualifications(t["qualifications"], labels, t["witnesses"])
            for table in ca.RECORD_TABLES:
                t[table] = rebuilt[table]
        path = self.forger.forge("value", records=start, rehash_content=True, anchors=STATE["anchors"])
        self.assertIsNone(self.code(path), "a fully coordinated raw-claim forgery is internally consistent")
        pinned = dict(STATE["anchors"], profile={"database_identity": STATE["result"]["database_identity"],
                                                 "content_identity": STATE["result"]["content_identity"]})
        self.assertEqual(self.code(path, pinned), "CONTEXT_PROFILE_MISMATCH")
        self.assertIsNone(self.code(STATE["db"], pinned))
        self.assertIsNone(self.code(self.forger.forge("control")))


class MalformedJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="scs-m-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.forger = fx.Forger(STATE["db"], self.base)

    def code(self, path: Path) -> str | None:
        try:
            with ca.ContextAssociation(path, anchors=STATE["anchors"]):
                return None
        except ca.ContextError as exc:
            return exc.code

    def test_malformed_record_lines_are_controlled_refusals(self) -> None:
        backslash = chr(92)
        # Decoder stack limits differ by Python build and host. Exceed both the Python limit and
        # native decoder limits rather than assuming that 5,000 levels are malformed everywhere.
        depth = max(sys.getrecursionlimit() * 2 + 50, 100_000)
        for name, member in (("nan", '"x":NaN,'), ("huge", '"x":1e999,'), ("deep", '"x":' + "[" * depth + "]" * depth + ","),
                             ("surrogate", '"x":"' + backslash + 'ud800",'), ("long_int", '"x":' + "9" * 5000 + ",")):
            def inject(raw, member=member):
                line = raw["census"][0]
                self.assertIn('"population":{', line)
                raw["census"][0] = line.replace('"population":{', '"population":{' + member, 1)
            got = self.code(self.forger.forge(name, lines=inject))
            self.assertEqual(got, "CONTEXT_RECORD_MALFORMED", name)
        self.assertIsNone(self.code(self.forger.forge("control")))

    def test_malformed_manifests_are_refused(self) -> None:
        ident = STATE["result"]["database_identity"]
        root = self.base / "man"
        for kind in ("canonical", "manifests"):
            shutil.copytree(STATE["db"].parents[3].parent / kind / ca.POPULATION / "sha256" / ident,
                            root / kind / ca.POPULATION / "sha256" / ident)
        manifest = root / "manifests" / ca.POPULATION / "sha256" / ident / "run_manifest.json"
        db = root / "canonical" / ca.POPULATION / "sha256" / ident / ca.DB_FILE
        depth = max(sys.getrecursionlimit() * 2 + 50, 100_000)
        for text in ("not json", '{"identity": NaN}', "[1]", "[" * depth + "]" * depth):
            manifest.write_text(text, encoding="utf-8")
            self.assertEqual(self.code(db), "CONTEXT_MANIFEST_MALFORMED", text[:20])


class LocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="scs-l-"))
        # the long rehoused copies exceed the classic Windows limit: remove them through the extended form
        self.addCleanup(shutil.rmtree, ("\\\\?\\" if os.name == "nt" else "") + os.path.abspath(self.base), True)

    def test_missing_and_misplaced_files_are_refused_and_never_created(self) -> None:
        missing = self.base / "nowhere" / "canonical" / ca.POPULATION / "sha256" / ("0" * 64) / ca.DB_FILE
        code, _doc, err = ask("--grain", "context-parameter", db=missing)
        self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_DATABASE_MISSING"))
        self.assertFalse(missing.parent.exists())
        loose = self.base / "loose" / ca.DB_FILE
        loose.parent.mkdir()
        shutil.copyfile(STATE["db"], loose)
        code, _doc, err = ask("--grain", "context-parameter", db=loose)
        self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_LOCATION_INVALID"))
        code, _doc, err = ask("--grain", "context-parameter", "--manifest", str(self.base / "no" / "m.json"))
        self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_MANIFEST_MISSING"))
        code, _doc, err = ask("--grain", "context-parameter", db="")
        self.assertEqual((code, fx.refusal(err)), (2, "DATABASE_LOCATION_UNSUPPORTED"))
        code, _doc, err = ask("--grain", "context-parameter", "--manifest", "")
        self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_MANIFEST_LOCATION_UNSUPPORTED"))

    @unittest.skipUnless(os.name == "nt", "Windows network/device spellings")
    def test_network_and_device_spellings_are_refused_before_access(self) -> None:
        sentinel = []
        real = ca._io_path

        def guard(path):
            sentinel.append(str(path))
            return real(path)
        with mock.patch.object(ca, "_io_path", guard):
            for spelling in ("\\\\bas-c63-test-host\\share\\x.sqlite", "\\\\.\\nul", "\\\\.\\pipe\\c63",
                             "\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1\\x.sqlite", "\\\\?\\UNC\\h\\s\\x.sqlite"):
                code, _doc, err = ask("--grain", "context-parameter", db=spelling)
                self.assertEqual((code, fx.refusal(err)), (2, "DATABASE_LOCATION_UNSUPPORTED"), spelling)
            code, _doc, err = ask("--grain", "context-parameter", "--manifest",
                                  "\\\\bas-c63-test-host\\share\\run_manifest.json")
            self.assertEqual((code, fx.refusal(err)), (2, "CONTEXT_MANIFEST_LOCATION_UNSUPPORTED"))
        self.assertEqual(sentinel, [], "no filesystem access before the location policy")
        code, _doc, err = ask("--grain", "context-parameter", db=self.base / "control" / ca.DB_FILE)
        self.assertEqual(fx.refusal(err), "CONTEXT_DATABASE_MISSING", "the access control does reach the filesystem")

    def test_legitimate_local_spellings_answer_identically(self) -> None:
        genuine = ask("--grain", "context-summary", "--limit", "3")[1]
        ident = STATE["result"]["database_identity"]
        long_base = self.base.joinpath(*[f"long-rehoused-context-component-{c}-" + c * 24 for c in "abcd"])
        special = self.base / "spé cial ☃ [x] #%&"
        for root in (long_base, special):
            for kind in ("canonical", "manifests"):
                src = STATE["db"].parents[3].parent / kind / ca.POPULATION / "sha256" / ident
                dst = root / kind / ca.POPULATION / "sha256" / ident
                os.makedirs(ca._io_path(dst))
                for name in os.listdir(ca._io_path(src)):
                    shutil.copyfile(ca._io_path(src / name), ca._io_path(dst / name))
        spellings = [long_base / "canonical" / ca.POPULATION / "sha256" / ident / ca.DB_FILE,
                     special / "canonical" / ca.POPULATION / "sha256" / ident / ca.DB_FILE]
        if os.name == "nt":
            spellings.append("\\\\?\\" + os.path.abspath(STATE["db"]))
            spellings.append("\\\\?\\" + os.path.abspath(spellings[0]))
        self.assertGreater(len(str(spellings[0])), 260)
        for spelling in spellings:
            code, doc, err = ask("--grain", "context-summary", "--limit", "3", db=spelling)
            self.assertEqual(code, 0, f"{spelling}: {err}")
            self.assertEqual((doc["release_identity"], doc["rows"]), (genuine["release_identity"], genuine["rows"]))
        cwd = os.getcwd()
        try:
            os.chdir(STATE["db"].parent)
            code, doc, err = ask("--grain", "context-summary", "--limit", "3", db=ca.DB_FILE)
        finally:
            os.chdir(cwd)
        self.assertEqual((code, doc["rows"]), (0, genuine["rows"]), err)


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
    parts = list(Path(db).parts)
    parts[-1 - index] = spell(parts[-1 - index])
    return Path(*parts)


class NativeLocationAliasTests(unittest.TestCase):
    """The accepted C61 rule: the reader checks the release layout and identity on the genuine names of the file."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="scs-a-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.genuine = ask("--grain", "context-summary", "--limit", "3")[1]

    def served(self, spelling, why: str, cwd: Path | None = None) -> None:
        previous = os.getcwd()
        try:
            if cwd is not None:
                os.chdir(cwd)
            code, doc, err = ask("--grain", "context-summary", "--limit", "3", db=spelling)
        finally:
            os.chdir(previous)
        self.assertEqual(code, 0, f"{why} {spelling}: {err[-300:]}")
        self.assertEqual((doc["release_identity"], doc["rows"]),
                         (self.genuine["release_identity"], self.genuine["rows"]), why)

    @unittest.skipUnless(os.name == "nt", "Windows case-equivalent spellings")
    def test_case_equivalent_spellings_serve_the_release(self) -> None:
        db = STATE["db"]
        for index in range(4):
            self.served(_respell(db, index, str.upper), f"component {index} upper")
        self.served(ca.DB_FILE.upper(), "relative case-equivalent file name", cwd=db.parent)

    @unittest.skipUnless(os.name == "nt", "Windows native 8.3 short names")
    def test_native_short_spellings_serve_the_release(self) -> None:
        short = _short_spelling(STATE["db"])
        if not short or short == str(STATE["db"]):
            self.skipTest(f"this volume reports no 8.3 short name ({short!r})")
        self.served(short, "native short spelling")

    @unittest.skipUnless(os.name == "nt", "Windows directory junctions")
    def test_spellings_through_junctions_serve_the_release(self) -> None:
        import _winapi  # noqa: PLC0415 - Windows CPython

        db = STATE["db"]
        link = self.base / "jroot"
        _winapi.CreateJunction(str(db.parents[4]), str(link))
        self.addCleanup(os.rmdir, link)
        self.served(link / "canonical" / ca.POPULATION / "sha256" / db.parent.name / ca.DB_FILE, "junction")

    def test_spellings_outside_the_genuine_layout_stay_refused(self) -> None:
        ident = STATE["result"]["database_identity"]
        target = self.base / "x" / "canonical" / (ca.POPULATION + "_copy") / "sha256" / ident
        os.makedirs(target)
        shutil.copyfile(STATE["db"], target / ca.DB_FILE)
        code, _doc, err = ask("--grain", "context-parameter", db=target / ca.DB_FILE)
        self.assertEqual(fx.refusal(err), "CONTEXT_LOCATION_INVALID")


class TeamUnicodeTests(unittest.TestCase):
    def test_lone_surrogates_and_controls_are_refused_and_valid_unicode_selects(self) -> None:
        for team in ("\ud800", "Tex\udfffas", "\x00", "a\x1fb"):
            code, _doc, err = ask("--grain", "context-feature", "--team", team, db="missing.sqlite")
            self.assertEqual((code, fx.refusal(err)), (2, "INVALID_SELECTOR"), repr(team))
            self.assertNotIn("Traceback", err)
        for team in ("Snowman ☃", "\U0001F3C8 Gridiron"):
            code, doc, err = ask("--grain", "context-feature", "--team", team, "--all")
            self.assertEqual((code, doc["total"]), (0, 0), err)


#: MF63A01-01 (C63-CONT-01): every Unicode category Cc character (C0 U+0000-U+001F, DEL U+007F, C1 U+0080-U+009F).
CC_POINTS = (*range(0x20), *range(0x7F, 0xA0))
#: The five string options a raw control can reach, a valid token for each and its own refusal code.
RAW_OPTIONS = {"season": ("2021", "INVALID_SELECTOR"), "team": ("org:697", "INVALID_SELECTOR"),
               "contest": ("ncaa:1001", "INVALID_SELECTOR"), "limit": ("20", "LIMIT_INVALID"),
               "offset": ("10", "OFFSET_INVALID")}
TAB, LF, VT, FS, US, DEL, PAD, NEL, APC = chr(9), chr(10), chr(11), chr(28), chr(31), chr(127), chr(0x80), chr(0x85), \
    chr(0x9F)
NBSP, IDEOGRAPHIC_SPACE, SOFT_HYPHEN, ZWJ, COMBINING_ACUTE = chr(0xA0), chr(0x3000), chr(0xAD), chr(0x200D), chr(0x301)
HIGH, LOW, LAST = chr(0xD800), chr(0xDC00), chr(0xDFFF)
RAW_MISSING = "never-read/national_site_calendar_association.sqlite"


class _InputAccess(Exception):
    """Raised by the access sentinel: the selection reached the release's input access."""


def _no_input_access(path):
    raise _InputAccess(str(path))


def raw_ask(*argv: str) -> tuple:
    """The public main on a never-read database path with every input access trapped by a sentinel:
    (exit, refusal code, input accessed, stderr)."""
    with mock.patch.object(ca, "_io_path", _no_input_access):
        try:
            code, _doc, err = fx.query(STATE["anchors"], RAW_MISSING, *argv)
        except _InputAccess:
            return None, None, True, ""
    return code, fx.refusal(err), False, err


def raw_spellings(value: str, character: str) -> dict:
    half = len(value) // 2
    return {"prefix": character + value, "suffix": value + character,
            "infix": value[:half] + character + value[half:]}


class RawControlSelectorTests(unittest.TestCase):
    """MF63A01-01: a raw control character in a supplied season, team, contest, limit or offset string is refused by
    that option's own rule before any trimming or input access; ordinary and Unicode spaces still trim, valid Unicode
    text still selects, lone surrogates and already-malformed values keep their codes and the frozen precedence holds."""

    def test_raw_controls_in_every_option_refuse_by_their_own_code_before_any_input_access(self) -> None:
        for option, (value, code) in RAW_OPTIONS.items():
            for point in CC_POINTS:
                for where, text in raw_spellings(value, chr(point)).items():
                    with self.subTest(option=option, codepoint=f"U+{point:04X}", position=where):
                        exit_code, refused, accessed, err = raw_ask("--grain", "context-feature", f"--{option}", text)
                        mark = f"MF63A01-01 --{option} U+{point:04X} {where}"
                        self.assertFalse(accessed, mark + " reached input access")
                        self.assertEqual((exit_code, refused), (2, code), mark)
                        self.assertNotIn("Traceback", err, mark)

    def test_raw_controls_keep_the_frozen_refusal_precedence(self) -> None:
        cases = [
            # paging precedes the model and the game selectors; the limit precedes the offset
            (("--grain", "context-score", "--limit", TAB + "20", "--model", "NOPE"), "LIMIT_INVALID", "limit"),
            (("--grain", "context-score", "--offset", "10" + NEL, "--team", "org:x"), "OFFSET_INVALID", "offset"),
            (("--grain", "context-score", "--limit", "20" + LF, "--offset", APC + "10"), "LIMIT_INVALID", "limit"),
            # game selector values precede applicability and the identity check
            (("--grain", "context-parameter", "--season", "2021" + TAB), "INVALID_SELECTOR", "season"),
            (("--grain", "context-parameter", "--team", PAD + "Texas"), "INVALID_SELECTOR", "team"),
            (("--grain", "context-score", "--contest", US + "ncaa:1001", "--expect-identity", "abc"),
             "INVALID_SELECTOR", "contest"),
            # season precedes team: the earlier malformed value is the one reported
            (("--grain", "context-score", "--season", LF + "2021", "--team", "Tex" + NEL + "as"), "INVALID_SELECTOR",
             "season")]
        for argv, code, option in cases:
            with self.subTest(argv=repr(argv)):
                exit_code, refused, accessed, err = raw_ask(*argv)
                mark = f"MF63A01-01 precedence {argv!r}"
                self.assertFalse(accessed, mark + " reached input access")
                self.assertEqual((exit_code, refused), (2, code), mark)
                self.assertIn(f"{option} must", err, mark)

    def test_a_real_child_process_refuses_raw_controls_without_a_traceback(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT / "src"), env.get("PYTHONPATH")) if p)
        cases = (("season", TAB + "2023", "INVALID_SELECTOR"), ("team", NEL + "org:697", "INVALID_SELECTOR"),
                 ("team", "Tex" + PAD + "as", "INVALID_SELECTOR"), ("contest", "ncaa:2276000" + FS, "INVALID_SELECTOR"),
                 ("limit", LF + "20", "LIMIT_INVALID"), ("offset", "10" + VT, "OFFSET_INVALID"))
        with tempfile.TemporaryDirectory(prefix="scs-r-") as tmp:
            missing = Path(tmp) / "absent" / ca.DB_FILE
            for option, text, code in cases:
                proc = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.retrospective_baseline.query",
                                       "--context-association", str(missing), "--grain", "context-feature",
                                       f"--{option}", text], capture_output=True, env=env, cwd=tmp, timeout=300)
                with self.subTest(option=option, text=repr(text)):
                    mark = f"MF63A01-01 child --{option} {text!r}"
                    self.assertEqual(proc.returncode, 2, mark)
                    self.assertEqual(fx.refusal(proc.stderr.decode("utf-8", "replace")), code, mark)
                    self.assertNotIn(b"Traceback", proc.stderr, mark)
                    self.assertEqual(proc.stdout, b"", mark)
            self.assertFalse(missing.parent.exists())

    def test_ordinary_and_unicode_spaces_and_valid_unicode_text_still_reach_the_release(self) -> None:
        for option, (value, _code) in RAW_OPTIONS.items():
            for text in (value, " " + value, value + " ", NBSP + value + IDEOGRAPHIC_SPACE):
                with self.subTest(option=option, text=repr(text)):
                    exit_code, refused, accessed, err = raw_ask("--grain", "context-feature", f"--{option}", text)
                    self.assertEqual((exit_code, refused, accessed), (None, None, True), err)
        for team in ("Snowman " + chr(0x2603), "Gridiron " + chr(0x1F3C8), "Cafe" + COMBINING_ACUTE,
                     "Join" + ZWJ + "er", "Tex" + SOFT_HYPHEN + "as"):
            with self.subTest(team=repr(team)):
                exit_code, refused, accessed, err = raw_ask("--grain", "context-feature", "--team", team)
                self.assertEqual((exit_code, refused, accessed), (None, None, True), err)

    def test_trimmed_selectors_and_paging_answer_exactly_as_their_plain_spelling(self) -> None:
        record = next(r for r in quals().values() if r["season"] == 2022)
        pairs = [(("--season", " 2022 "), ("--season", "2022")),
                 (("--team", " " + record["a_key"]), ("--team", record["a_key"])),
                 (("--contest", record["contest_key"] + " "), ("--contest", record["contest_key"])),
                 (("--limit", " 3", "--offset", "1 "), ("--limit", "3", "--offset", "1"))]
        for padded, plain in pairs:
            with self.subTest(padded=repr(padded)):
                got, want = ask("--grain", "context-feature", *padded), ask("--grain", "context-feature", *plain)
                self.assertEqual((got[0], want[0]), (0, 0), got[2] + want[2])
                self.assertTrue(want[1]["rows"])
                for key in ("rows", "total", "returned", "next_offset"):
                    self.assertEqual(got[1].get(key), want[1].get(key), key)

    def test_lone_surrogates_and_already_malformed_values_keep_their_codes(self) -> None:
        cases = [("season", HIGH), ("season", "20" + LOW + "21"), ("team", HIGH), ("team", "Tex" + LAST + "as"),
                 ("contest", "ncaa:" + HIGH), ("limit", "2" + HIGH), ("offset", LOW + "1"),
                 ("team", "a" + US + "b"), ("team", "Tex" + chr(7) + "as"), ("season", "20" + DEL + "21"),
                 ("contest", "ncaa:" + chr(0) + "1"), ("limit", "x"), ("offset", "1.5"), ("contest", "espn:1"),
                 ("season", "20x1"), ("team", "org:x"), ("team", ""), ("limit", ""), ("offset", ""),
                 ("limit", "1234567890123")]
        for option, text in cases:
            with self.subTest(option=option, text=repr(text)):
                exit_code, refused, accessed, err = raw_ask("--grain", "context-feature", f"--{option}", text)
                self.assertEqual((exit_code, refused, accessed), (2, RAW_OPTIONS[option][1], False), err)
        for team in (HIGH, "Tex" + LAST + "as", LOW + HIGH):
            with self.subTest(surrogate=repr(team)):
                self.assertIn("lone surrogate", raw_ask("--grain", "context-feature", "--team", team)[3])

    def test_earlier_refusal_families_still_win_over_raw_controls(self) -> None:
        cases = [(("--grain", "context-score", "--require-pit", "--limit", TAB + "20"), "CONTEXT_PIT_NOT_ADMITTED"),
                 (("--grain", "context-score", "--database", "x.sqlite", "--season", LF + "2021"),
                  "CONTEXT_MODE_CONFLICT"),
                 (("--grain", "context-score", "--cutoff", "x", "--team", NEL + "Texas"), "TEMPORAL_FLAG_UNSUPPORTED"),
                 (("--grain", "context-forecast", "--offset", US + "1"), "UNKNOWN_GRAIN"),
                 (("--grain", "context-score", "--model", "NOPE", "--season", TAB + "2021"), "MODEL_INVALID"),
                 (("--grain", "context-score", "--limit", "-1", "--season", APC + "2021"), "NEGATIVE_LIMIT")]
        for argv, code in cases:
            with self.subTest(argv=repr(argv)):
                exit_code, refused, accessed, err = raw_ask(*argv)
                self.assertEqual((exit_code, refused, accessed), (2, code, False), err)

    def test_python_integer_paging_keeps_its_rule_without_a_digit_cap(self) -> None:
        self.assertEqual(ca.validate_paging(10 ** 15, 10 ** 13, False, limit_given=True, offset_given=True),
                         (10 ** 15, 10 ** 13))
        self.assertEqual(ca.validate_paging(" 12 ", "0", False, limit_given=True, offset_given=True), (12, 0))
        self.assertEqual(ca.validate_paging("123456789012", "0", False, limit_given=True, offset_given=True),
                         (123456789012, 0))
        for limit, offset, code in (("1234567890123", "0", "LIMIT_INVALID"), ("5", NBSP + "x", "OFFSET_INVALID")):
            with self.assertRaises(ca.ContextError) as caught:
                ca.validate_paging(limit, offset, False, limit_given=True, offset_given=True)
            self.assertEqual(caught.exception.code, code)


class MountedGenuineTests(unittest.TestCase):
    def test_the_canonical_release_verifies_with_the_pinned_profile(self) -> None:
        data = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or "")
        profile = ca.CONTEXT_PROFILE
        if not str(data) or profile is None:
            self.skipTest("the private data root or the pinned canonical profile is absent")
        db = data / "canonical" / ca.POPULATION / "sha256" / profile["database_identity"] / ca.DB_FILE
        if not db.is_file():
            self.skipTest("the canonical site/calendar association release is not mounted")
        with ca.ContextAssociation(db) as reader:
            self.assertEqual(reader.database_identity, profile["database_identity"])
            counts = ca.ANCHORS["expected"]["counts"]
            census = reader.census
            self.assertEqual((census["targets"], census["views"], census["common_support_games"]),
                             (counts["targets"], counts["views"], counts["common_support_games"]))
            self.assertEqual(sum(1 for r in reader.records["summary"] if r["primary"]), 1)
            self.assertEqual(len(reader.records["summary"]), 70)


if __name__ == "__main__":
    unittest.main()
