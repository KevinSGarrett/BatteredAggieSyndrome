"""BAT-724 provider-record baseline preview: builder, reader and the explicit query mode (TP52-A01 sections 3-4)."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import prospective_provider_observation_fixture as pfx  # noqa: E402
import provider_record_baseline_preview_fixture as fx  # noqa: E402
from aggie_analytics.national_source_time import prospective  # noqa: E402
from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402
from aggie_analytics.retrospective_baseline import preview, query  # noqa: E402
from tools import build_provider_record_baseline_preview as builder  # noqa: E402

CUTOFF = "2026-10-12T00:00:00Z"
NULL, SMOOTH = preview.MODEL_NULL, preview.MODEL_SMOOTHED


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="bat724-"))
        # the long-path bundle test writes beyond MAX_PATH: remove through the extended-length form on Windows
        self.addCleanup(shutil.rmtree, "\\\\?\\" + str(self.tmp) if os.name == "nt" else self.tmp)

    def world(self, events=None, *, raw_doc=None, name: str = "w") -> fx.PreviewWorld:
        return fx.PreviewWorld(self.tmp / name, events, raw_doc=raw_doc)

    def build(self, world: fx.PreviewWorld, name: str = "b", **overrides) -> tuple[dict, Path]:
        result = builder.build(world.build_args(self.tmp / name, **overrides))
        return result, Path(result["preview"])

    def doc(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def run_cli(self, argv: list[str], authority: str | None) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(argv, preview_contract_sha256=authority)
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

    def rows(self, path: Path, authority: str, grain: str, *extra: str) -> list[dict]:
        code, doc, refused = self.run_cli(["--prospective-preview", str(path), "--grain", grain, "--cutoff", CUTOFF,
                                           "--all", *extra], authority)
        self.assertEqual(code, 0, refused)
        key = preview.GRAIN_KEY[grain]
        return [r[key] for r in doc["rows"]]


class CommittedContractTests(unittest.TestCase):
    def test_reader_anchor_is_the_committed_contract_and_equals_the_code(self) -> None:
        data = fx.CONTRACT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), preview.CONTRACT_SHA256)
        contract = json.loads(data.decode("utf-8"))
        self.assertEqual(contract["contract_id"], preview.CONTRACT_ID)
        self.assertEqual(contract["population_id"], preview.POPULATION)
        self.assertEqual(contract["models"], preview.MODELS)
        self.assertEqual(contract["labels"], preview.LABELS)
        self.assertEqual(contract["numeric_contract"], preview.NUMERIC_CONTRACT)
        self.assertEqual(contract["abstention_reasons"], preview.REASONS)
        self.assertEqual(contract["preview"]["top_level_members"], list(preview.TOP_LEVEL))
        self.assertEqual(contract["query_rules"]["grains"], list(preview.GRAINS))
        self.assertEqual(contract["query_rules"]["applicable_filters"], {k: list(v) for k, v in
                                                                         preview.APPLICABLE.items()})
        self.assertEqual(contract["feature_rules"]["fields"], {k: list(v) for k, v in preview.FEATURE_FIELDS.items()})
        self.assertEqual(contract["estimate_rules"]["fields"], {k: list(v) for k, v in preview.ESTIMATE_FIELDS.items()})
        self.assertEqual(contract["game_rules"]["fields"], {k: list(v) for k, v in preview.GAME_FIELDS.items()})
        self.assertEqual(contract["summary_rules"]["fields"], list(preview.SUMMARY_FIELDS))
        self.assertEqual(contract["preview"]["identity"]["members"], list(preview.identity_document(
            {"contract": {"sha256": "0" * 64}, "bundle": {}, **{k: None for k in preview.TOP_LEVEL
                                                                 if k not in ("contract", "bundle")}})))

    def test_committed_input_is_the_accepted_capsule(self) -> None:
        pins = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))["input"]
        self.assertEqual(pins["capsule_identity"], "7c108ac8d003350b9a03d8106fa3f08aa3ef5651360cbd575ee9ae3fc18a51f4")
        self.assertEqual(pins["capsule_sha256"], "c336ab07933823c0088861c64dbebff5b7cb7374053d53f3cdf33d6a33871505")
        self.assertEqual(pins["capsule_contract_sha256"], prospective.CONTRACT_SHA256)
        self.assertEqual((pins["expected_events"], pins["expected_participants"]), (25, 50))

    def test_preview_models_are_distinct_from_the_historical_models(self) -> None:
        self.assertFalse(set(preview.MODEL_IDS) & set(bm.MODEL_IDS))
        self.assertEqual(preview.MODELS[SMOOTH]["input_semantics"],
                         "PROVIDER_REPORTED_OVERALL_TOTAL_RECORD_COUNTS_NOT_RECONSTRUCTED_GAME_HISTORY")
        for model in preview.MODELS.values():
            self.assertEqual((model["fitted"], model["home_advantage"], model["margin"], model["score"],
                              model["interval"], model["calibration"]), (False, None, None, None, None,
                                                                         "NOT_CALIBRATED"))

    def test_default_authority_refuses_a_fixture_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bat724c-") as tmp:
            world = fx.PreviewWorld(Path(tmp))
            with self.assertRaises(preview.PreviewError) as caught:
                preview.build_preview(world.capsule, world.contract)
            self.assertEqual(caught.exception.code, "CONTRACT_NOT_COMMITTED_AUTHORITY")


class ArithmeticAndRuleTests(_Workspace):
    def test_genuine_fixture_features_estimates_and_exact_complements(self) -> None:
        world = self.world()
        result, path = self.build(world)
        self.assertEqual(result["preview_state"], "MATERIALIZED")
        self.assertEqual(result["counts"], {"events": 3, "games": 3, "features": 6, "supported_features": 6,
                                            "unsupported_features": 0, "cold_start_features": 0, "estimates": 12,
                                            "supported_estimates": 12, "abstained_estimates": 0})
        self.assertEqual(path.parent.name, result["identity"])
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["build"]["built_at_role"], "BUILD_CLOCK_ONLY_NOT_OBSERVATION_OR_FORECAST_TIME_NOT_"
                                                             "CONTENT")
        self.assertNotIn("built_at", self.doc(path).get("input", {}))
        features = {f["team_key"]: f for f in self.rows(path, world.authority, "preview-feature")}
        records = {"9001": (4, 1, 0), "9002": (2, 3, 0), "9003": (3, 3, 0), "9004": (6, 0, 0), "9005": (5, 0, 1),
                   "9006": (0, 6, 0)}
        for team, (w, l, t) in records.items():
            f = features[f"espn:team:{team}"]
            self.assertEqual((f["wins"], f["losses"], f["ties"], f["games"], f["cold_start"]), (w, l, t, w + l + t,
                                                                                                False))
            self.assertEqual(f["support_state"], "SUPPORTED")
            self.assertTrue(f["event_role_bound"])
            for key in ("wins", "losses", "ties", "games"):
                self.assertIs(type(f[key]), int)
        self.assertEqual(features["espn:team:9005"]["record_summary"], "5-0-1")
        self.assertEqual(features["espn:team:9005"]["ties_rule"], prospective.TIES_STATED_RULE)
        estimates = self.rows(path, world.authority, "preview-estimate")
        self.assertEqual(len(estimates), 12)
        games = {"espn:event:900000001": ("9001", "9002"), "espn:event:900000002": ("9003", "9004"),
                 "espn:event:900000003": ("9005", "9006")}
        for event, (home, away) in games.items():
            q_home, q_away = fx.oracle_q(*records[home]), fx.oracle_q(*records[away])
            want = {SMOOTH: fx.oracle_p(q_home, q_away), NULL: Fraction(1, 2)}
            for row in (e for e in estimates if e["event_key"] == event):
                p_home = want[row["model_id"]]
                p = p_home if row["orientation"] == "home" else 1 - p_home
                self.assertEqual(Fraction(row["probability"]["numerator"], row["probability"]["denominator"]), p)
                self.assertEqual(Fraction(row["opponent_probability"]["numerator"],
                                          row["opponent_probability"]["denominator"]), 1 - p)
                self.assertEqual(row["probability_decimal"], fx.half_even(p))
                self.assertEqual(row["opponent_probability_decimal"], fx.half_even(1 - p))
                self.assertGreater(row["probability"]["denominator"], 0)
                self.assertEqual(Fraction(row["probability"]["numerator"], row["probability"]["denominator"]),
                                 Fraction(row["probability"]["numerator"], row["probability"]["denominator"]))
                self.assertEqual(row["team_key"], f"espn:team:{home if row['orientation'] == 'home' else away}")
                if row["model_id"] == NULL:
                    self.assertEqual((row["team_strength_q"], row["team_feature_sha256"], row["record_dependence"]),
                                     (None, None, "NONE"))
                else:
                    mine = q_home if row["orientation"] == "home" else q_away
                    self.assertEqual(Fraction(row["team_strength_q"]["numerator"],
                                              row["team_strength_q"]["denominator"]), mine)
        tie = next(e for e in estimates if e["event_key"] == "espn:event:900000003" and e["model_id"] == SMOOTH and
                   e["orientation"] == "home")
        self.assertEqual((tie["team_strength_q"], tie["probability"]), ({"numerator": 13, "denominator": 16},
                                                                         {"numerator": 91, "denominator": 94}))

    def test_no_home_advantage_swapping_the_records_swaps_the_probabilities(self) -> None:
        world = self.world()
        _, path = self.build(world)

        def swap(events):
            home, away = fx.competitor_of(events, "900000001", "home"), fx.competitor_of(events, "900000001", "away")
            home["records"], away["records"] = away["records"], home["records"]
        swapped = self.world(fx.events_with(swap), name="s")
        _, other = self.build(swapped, "s2")
        one = {(e["model_id"], e["orientation"]): e for e in self.rows(path, world.authority, "preview-estimate",
                                                                       "--event", "espn:event:900000001")}
        two = {(e["model_id"], e["orientation"]): e for e in self.rows(other, swapped.authority, "preview-estimate",
                                                                       "--event", "espn:event:900000001")}
        self.assertEqual(one[(SMOOTH, "home")]["probability"], two[(SMOOTH, "away")]["probability"])
        self.assertEqual(one[(SMOOTH, "away")]["probability"], two[(SMOOTH, "home")]["probability"])
        self.assertEqual(one[(NULL, "home")]["probability"], two[(NULL, "home")]["probability"])

    def test_cold_start_zero_zero_record_is_a_labelled_half(self) -> None:
        events = fx.events_with(lambda ev: fx.competitor_of(ev, "900000002", "home")["records"][0].update(
            summary="0-0"))
        world = self.world(events)
        _, path = self.build(world)
        feature = next(f for f in self.rows(path, world.authority, "preview-feature") if
                       f["team_key"] == "espn:team:9003")
        self.assertEqual((feature["wins"], feature["losses"], feature["ties"], feature["games"],
                          feature["cold_start"], feature["support_state"]), (0, 0, 0, 0, True, "SUPPORTED"))
        row = next(e for e in self.rows(path, world.authority, "preview-estimate", "--event", "espn:event:900000002",
                                        "--model", SMOOTH, "--orientation", "home"))
        self.assertEqual((row["team_strength_q"], row["team_cold_start"], row["support_state"]),
                         ({"numerator": 1, "denominator": 2}, True, "SUPPORTED"))
        self.assertEqual(Fraction(row["probability"]["numerator"], row["probability"]["denominator"]),
                         fx.oracle_p(Fraction(1, 2), fx.oracle_q(6, 0, 0)))
        summary = self.rows(path, world.authority, "preview-summary", "--model", SMOOTH)[0]
        self.assertEqual(summary["cold_start_features"], 1)

    def test_missing_ambiguous_and_malformed_records_abstain_without_a_fabricated_zero(self) -> None:
        def mutate(events):
            fx.competitor_of(events, "900000001", "home")["records"] = [r for r in fx.competitor_of(
                events, "900000001", "home")["records"] if r["name"] != "overall"]
            fx.competitor_of(events, "900000002", "away")["records"][0]["summary"] = "6-0-x"
            dup = fx.competitor_of(events, "900000003", "away")
            dup["records"].append(dict(dup["records"][0], summary="1-5"))
        world = self.world(fx.events_with(mutate))
        result, path = self.build(world)
        self.assertEqual((result["counts"]["supported_features"], result["counts"]["unsupported_features"]), (3, 3))
        features = {f["team_key"]: f for f in self.rows(path, world.authority, "preview-feature")}
        for team, reason in (("9001", "RECORD_OVERALL_TOTAL_MISSING"), ("9004", "RECORD_SUMMARY_MALFORMED"),
                             ("9006", "RECORD_OVERALL_TOTAL_MULTIPLE")):
            f = features[f"espn:team:{team}"]
            self.assertEqual(f["support_state"], "UNSUPPORTED")
            self.assertIn(reason, f["unsupported_reasons"])
            self.assertEqual((f["wins"], f["losses"], f["ties"], f["games"], f["cold_start"]),
                             (None, None, None, None, None))
        self.assertEqual(features["espn:team:9004"]["record_summary"], "6-0-x")
        estimates = self.rows(path, world.authority, "preview-estimate")
        for e in estimates:
            if e["model_id"] == NULL:
                self.assertEqual(e["support_state"], "SUPPORTED")
                self.assertEqual(e["probability"], {"numerator": 1, "denominator": 2})
            else:
                self.assertEqual((e["support_state"], e["probability"], e["probability_decimal"]),
                                 ("ABSTAINED", None, None))
                self.assertEqual([r["reason"] for r in e["abstention_reasons"]], ["RECORD_UNSUPPORTED"])
        summary = {s["model_id"]: s for s in self.rows(path, world.authority, "preview-summary")}
        self.assertEqual((summary[SMOOTH]["supported_games"], summary[SMOOTH]["abstained_games"]), (0, 3))
        self.assertEqual(summary[SMOOTH]["abstention_reasons"], {
            "RECORD_UNSUPPORTED:RECORD_OVERALL_TOTAL_MISSING": 1, "RECORD_UNSUPPORTED:RECORD_OVERALL_TOTAL_MULTIPLE": 1,
            "RECORD_UNSUPPORTED:RECORD_SUMMARY_MALFORMED": 1})
        self.assertEqual((summary[NULL]["supported_games"], summary[NULL]["abstained_estimates"]), (3, 0))

    def test_identity_problems_abstain_both_models_and_name_the_input(self) -> None:
        def mutate(events):
            fx.competitor_of(events, "900000001", "away")["team"]["id"] = "9999"
            dup = next(e for e in events if e["id"] == "900000002")
            for c in dup["competitions"][0]["competitors"]:
                c["homeAway"] = "home"
        world = self.world(fx.events_with(mutate))
        _, path = self.build(world)
        by = {(e["event_key"], e["model_id"], e["orientation"]): e for e in
              self.rows(path, world.authority, "preview-estimate")}
        team = by[("espn:event:900000001", NULL, "away")]
        self.assertEqual(team["support_state"], "ABSTAINED")
        self.assertEqual([(r["input"], r["reason"], r["detail"]) for r in team["abstention_reasons"]],
                         [("away", "PARTICIPANT_IDENTITY_UNSUPPORTED", "TEAM_ID_DISAGREEMENT")])
        roles = by[("espn:event:900000002", NULL, "home")]
        self.assertEqual((roles["support_state"], roles["team_key"], roles["opponent_team_key"]),
                         ("ABSTAINED", None, None))
        self.assertTrue({r["reason"] for r in roles["abstention_reasons"]} == {"EVENT_UNSUPPORTED_IN_CAPSULE"})
        self.assertIn("ROLE_HOME_DUPLICATE", {r["detail"] for r in roles["abstention_reasons"]})
        self.assertEqual(by[("espn:event:900000003", NULL, "home")]["support_state"], "SUPPORTED")
        features = self.rows(path, world.authority, "preview-feature", "--event", "espn:event:900000002")
        self.assertEqual([f["event_role_bound"] for f in features], [False, False])

    def test_completed_or_live_event_abstains_the_record_model_only(self) -> None:
        def mutate(events):
            event = next(e for e in events if e["id"] == "900000003")
            for node in (event, event["competitions"][0]):
                node["status"] = pfx.status("STATUS_FINAL", "post", True)
        world = self.world(fx.events_with(mutate))
        _, path = self.build(world)
        rows = self.rows(path, world.authority, "preview-estimate", "--event", "espn:event:900000003")
        smoothed = [e for e in rows if e["model_id"] == SMOOTH]
        self.assertTrue(all(e["support_state"] == "ABSTAINED" for e in smoothed))
        self.assertEqual([(r["reason"], r["detail"]) for r in smoothed[0]["abstention_reasons"]],
                         [("EVENT_NOT_PRE_GAME_AT_OBSERVATION", "post:true")])
        self.assertTrue(all(e["support_state"] == "SUPPORTED" for e in rows if e["model_id"] == NULL))

    def test_unsupported_event_and_out_of_season_event_abstain(self) -> None:
        def mutate(events):
            next(e for e in events if e["id"] == "900000001")["competitions"][0]["timeValid"] = False
            next(e for e in events if e["id"] == "900000002")["season"]["year"] = 2025
        world = self.world(fx.events_with(mutate))
        _, path = self.build(world)
        code, doc, _ = self.run_cli(["--prospective-preview", str(path), "--grain", "preview-estimate", "--cutoff",
                                     CUTOFF, "--all"], world.authority)
        self.assertEqual(code, 0)
        by = {(r["estimate"]["event_key"], r["estimate"]["model_id"]): r["estimate"] for r in doc["rows"]}
        self.assertEqual([(r["reason"], r["detail"]) for r in by[("espn:event:900000001", NULL)]["abstention_reasons"]],
                         [("EVENT_UNSUPPORTED_IN_CAPSULE", "SCHEDULED_TIME_NOT_VALID_PER_SOURCE")])
        self.assertEqual([(r["reason"], r["detail"]) for r in by[("espn:event:900000002", NULL)]["abstention_reasons"]],
                         [("EVENT_SEASON_NOT_IN_SCOPE", "2025")])
        self.assertEqual(by[("espn:event:900000003", SMOOTH)]["support_state"], "SUPPORTED")

    def test_decimal_display_is_half_even_at_twelve_places(self) -> None:
        for value, text in ((Fraction(1, 3), "0.333333333333"), (Fraction(2, 3), "0.666666666667"),
                            (Fraction(1, 2 * 10 ** 12), "0.000000000000"), (Fraction(3, 2 * 10 ** 12),
                                                                            "0.000000000002"),
                            (Fraction(91, 94), fx.half_even(Fraction(91, 94)))):
            self.assertEqual(bm.decimal_text(value), text)
            self.assertEqual(fx.half_even(value), text)


class DeterminismTests(_Workspace):
    def test_order_chunk_interrupt_and_resume_are_byte_identical(self) -> None:
        world = self.world()
        first, path = self.build(world)
        members = builder.directory_members(path.parent)
        for name, order, chunk in (("r1", "reversed", "1"), ("s17", "shuffled:17", "17"), ("s9", "shuffled:9", "65536")):
            result, other = self.build(world, name, processing_order=order, chunk_size=chunk)
            self.assertEqual(result["identity"], first["identity"], name)
            self.assertEqual(builder.directory_members(other.parent), members, name)
        with self.assertRaises(builder.BuildInterrupted):
            builder.build(world.build_args(self.tmp / "cut", stop_after_members=3))
        self.assertFalse((self.tmp / "cut" / "canonical" / "sha256" / first["identity"]).exists())
        staged = list((self.tmp / "cut" / "canonical" / ".staging").iterdir())
        self.assertEqual(len(staged), 1)
        code, doc, refused = self.run_cli(["--prospective-preview", str(next(staged[0].rglob("preview.json"), staged[0]
                                                                              / "preview.json")),
                                           "--grain", "preview-feature", "--cutoff", CUTOFF], world.authority)
        self.assertEqual((code, doc), (2, None), refused)
        resumed, again = self.build(world, "cut")
        self.assertEqual(resumed["identity"], first["identity"])
        self.assertEqual(builder.directory_members(again.parent), members)
        rebuilt, _ = self.build(world)
        self.assertEqual(rebuilt["preview_state"], "ALREADY_PRESENT_IDENTICAL")
        (path.parent / "extra.txt").write_bytes(b"x")
        with self.assertRaises(builder.BuildRefused) as caught:
            self.build(world)
        self.assertEqual(caught.exception.code, "EXISTING_IDENTITY_DIFFERS")


class QueryTests(_Workspace):
    def setUp(self) -> None:
        super().setUp()
        self.w = self.world()
        _, self.path = self.build(self.w)

    def cli(self, *argv: str) -> tuple[int, dict | None, str]:
        return self.run_cli(["--prospective-preview", str(self.path), *argv], self.w.authority)

    def test_cutoff_boundaries_equivalent_zones_and_no_refresh(self) -> None:
        cases = [("2026-10-11T18:15:55.264958Z", "PREVIEW_UNAVAILABLE_BEFORE_OBSERVATION"),
                 ("2026-10-11T18:15:55.264959Z", "PREVIEW_INDETERMINATE_WITHIN_OBSERVATION"),
                 ("2026-10-11T18:15:55.744673Z", "PREVIEW_INDETERMINATE_WITHIN_OBSERVATION"),
                 ("2026-10-11T13:15:55.744673-05:00", "PREVIEW_INDETERMINATE_WITHIN_OBSERVATION"),
                 ("2026-10-10T00:00:00Z", "PREVIEW_UNAVAILABLE_BEFORE_OBSERVATION"),
                 ("2026-10-12T00:00:00Z\n", "CUTOFF_INVALID"), ("2026-10-12T00:00:00", "CUTOFF_TIMEZONE_REQUIRED"),
                 ("2026-10-12", "CUTOFF_TIMEZONE_REQUIRED"), ("tomorrow", "CUTOFF_INVALID"),
                 ("2026-10-12T00:00:00+15:00", "CUTOFF_INVALID")]
        for cutoff, refusal in cases:
            code, out, got = self.cli("--grain", "preview-estimate", "--cutoff", cutoff)
            self.assertEqual((code, got, out), (2, refusal, None), cutoff)
        code, out, got = self.cli("--grain", "preview-estimate")
        self.assertEqual((code, got), (2, "CUTOFF_REQUIRED"))
        answers = {}
        for cutoff in ("2026-10-11T18:15:55.744674Z", "2026-10-11T20:15:55.744674+02:00", "2026-10-11T18:15:55.744674"
                       "+00:00", "2026-10-18T00:00:00Z", "2027-01-01T00:00:00-06:00"):
            code, out, got = self.cli("--grain", "preview-estimate", "--cutoff", cutoff, "--all")
            self.assertEqual(code, 0, got)
            self.assertEqual(out["observation_at_cutoff"]["state"], preview.AVAILABLE)
            answers[cutoff] = out
        rows = {json.dumps(a["rows"], sort_keys=True) for a in answers.values()}
        self.assertEqual(len(rows), 1)
        self.assertEqual(answers["2026-10-11T18:15:55.744674Z"]["cutoff"]["utc"],
                         answers["2026-10-11T20:15:55.744674+02:00"]["cutoff"]["utc"])
        for row in answers["2027-01-01T00:00:00-06:00"]["rows"]:
            self.assertEqual(row["labels"]["preview_status"], "PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST")
            self.assertEqual(row["labels"]["pit_admission"], "PIT_NOT_ADMITTED")
            self.assertEqual(row["labels"]["predictive_skill"], "PREDICTIVE_SKILL_NOT_ESTABLISHED")
            self.assertEqual(row["labels"]["calibration"], "NOT_CALIBRATED")
            self.assertEqual(row["labels"]["forecast_issuance"], "NONE_NOT_AN_ISSUED_OR_FROZEN_FORECAST")
            self.assertEqual(row["observation_interval"], ["2026-10-11T18:15:55.264959Z",
                                                           "2026-10-11T18:15:55.744674Z"])

    def test_conjunctive_filter_and_paging_matrix(self) -> None:
        everything = {g: self.rows(self.path, self.w.authority, g) for g in ("preview-feature", "preview-estimate")}
        events = ["espn:event:900000001", "espn:event:900000002", "espn:event:900000003", "espn:event:999"]
        teams = ["espn:team:9001", "espn:team:9004", "espn:team:9006", "espn:team:1"]
        for grain, filters in (("preview-feature", ("event", "team", "orientation", "season")),
                               ("preview-estimate", ("event", "team", "model", "orientation", "season"))):
            values = {"event": [None, *events], "team": [None, *teams], "model": [None, NULL, SMOOTH],
                      "orientation": [None, "home", "away"], "season": [None, 2026]}
            for combo in itertools.product(*(values[f] for f in filters)):
                chosen = {f: v for f, v in zip(filters, combo) if v is not None}
                argv = []
                for f, v in chosen.items():
                    argv += [f"--{f}", str(v)]
                field = {"event": "event_key", "team": "team_key", "model": "model_id", "season": "season",
                         "orientation": "side" if grain == "preview-feature" else "orientation"}
                want = [r for r in everything[grain] if all(r[field[f]] == v for f, v in chosen.items())]
                got = self.rows(self.path, self.w.authority, grain, *argv)
                self.assertEqual(got, want, (grain, chosen))
                pages, offset = [], 0
                while True:
                    code, out, refused = self.cli("--grain", grain, "--cutoff", CUTOFF, "--limit", "2", "--offset",
                                                  str(offset), *argv)
                    self.assertEqual(code, 0, refused)
                    self.assertEqual(out["total"], len(want))
                    pages += [r[preview.GRAIN_KEY[grain]] for r in out["rows"]]
                    if out["next_offset"] is None:
                        break
                    offset = out["next_offset"]
                self.assertEqual(pages, want, (grain, chosen))
        incompatible = self.rows(self.path, self.w.authority, "preview-estimate", "--team", "espn:team:9001",
                                 "--orientation", "away")
        self.assertEqual(incompatible, [])
        code, out, _ = self.cli("--grain", "preview-feature", "--cutoff", CUTOFF, "--season", "2025")
        self.assertEqual((code, out["season_scope_state"], out["total"], out["rows"]),
                         (0, preview.OUT_OF_SCOPE_STATE, 0, []))

    def test_summary_counts_games_once_and_follows_the_selection(self) -> None:
        full = {s["model_id"]: s for s in self.rows(self.path, self.w.authority, "preview-summary")}
        self.assertEqual((full[NULL]["distinct_events"], full[NULL]["features"], full[NULL]["estimates"],
                          full[NULL]["estimates_per_game"]), (3, 6, 6, 2))
        stored = self.doc(self.path)["summary"]
        self.assertEqual(stored, [full[NULL], full[SMOOTH]])
        team = self.rows(self.path, self.w.authority, "preview-summary", "--team", "espn:team:9004", "--model", SMOOTH)
        self.assertEqual(len(team), 1)
        self.assertEqual((team[0]["distinct_events"], team[0]["features"], team[0]["estimates"],
                          team[0]["supported_games"]), (1, 2, 2, 1))
        none = self.rows(self.path, self.w.authority, "preview-summary", "--event", "espn:event:999")
        self.assertEqual([(s["distinct_events"], s["features"], s["estimates"]) for s in none], [(0, 0, 0), (0, 0, 0)])

    def test_malformed_inapplicable_and_conflicting_selections_refuse(self) -> None:
        base = ["--grain", "preview-estimate", "--cutoff", CUTOFF]
        cases = [(base + ["--event", "401856719"], "EVENT_KEY_INVALID"),
                 (base + ["--event", "espn:event:1\n"], "EVENT_KEY_INVALID"),
                 (base + ["--team", "Fixture Alpha Owls"], "TEAM_KEY_INVALID"),
                 (base + ["--team", "org:9001"], "TEAM_KEY_INVALID"),
                 (base + ["--team", "espn:team:9001\n"], "TEAM_KEY_INVALID"),
                 (base + ["--model", "SMOOTHED_HISTORY_ODDS_V1"], "PREVIEW_MODEL_UNKNOWN"),
                 (base + ["--model", "NULL_HALF_V1"], "PREVIEW_MODEL_UNKNOWN"),
                 (base + ["--orientation", "Home"], "ORIENTATION_INVALID"),
                 (["--grain", "preview-feature", "--cutoff", CUTOFF, "--model", NULL], "FILTER_NOT_APPLICABLE"),
                 (["--grain", "preview-summary", "--cutoff", CUTOFF, "--orientation", "home"],
                  "FILTER_NOT_APPLICABLE"),
                 (["--grain", "estimate", "--cutoff", CUTOFF], "PREVIEW_GRAIN_REQUIRED"),
                 (["--grain", "score", "--cutoff", CUTOFF], "PREVIEW_GRAIN_REQUIRED"),
                 (base + ["--database", "x.sqlite"], "PREVIEW_MODE_CONFLICT"),
                 (base + ["--history-database", "x.sqlite"], "PREVIEW_MODE_CONFLICT"),
                 (base + ["--manifest", "x.json"], "PREVIEW_MODE_CONFLICT"),
                 (base + ["--contest", "ncaa:1"], "FILTER_NOT_APPLICABLE"),
                 (base + ["--partition", "SPLIT-DEV-SEL"], "FILTER_NOT_APPLICABLE"),
                 (base + ["--require-pit"], "PREVIEW_PIT_NOT_ADMITTED"),
                 (base + ["--offset", "-1"], "NEGATIVE_OFFSET"), (base + ["--limit", "-1"], "NEGATIVE_LIMIT"),
                 (base + ["--expect-identity", "0" * 64], "STALE_PREVIEW_IDENTITY"),
                 (base + ["--expect-identity", "zz"], "STALE_PREVIEW_IDENTITY")]
        for argv, refusal in cases:
            code, out, got = self.cli(*argv)
            self.assertEqual((code, got, out), (2, refusal, None), argv)
        code, out, text = self.cli("--grain", "preview-estimate", "--cutoff", CUTOFF, "--season", "abc")
        self.assertEqual(code, 2)
        self.assertIn("argument --season: invalid int value", text)
        missing = self.tmp / "nowhere" / ("a" * 64) / "preview.json"
        code, out, got = self.run_cli(["--prospective-preview", str(missing), *base], self.w.authority)
        self.assertEqual((code, got), (2, "PREVIEW_MISSING"))
        self.assertFalse((self.tmp / "nowhere").exists())
        code, out, got = self.run_cli(["--prospective-preview", str(self.w.capsule), *base], self.w.authority)
        self.assertEqual((code, got), (2, "PREVIEW_LOCATION_INVALID"))

    def test_historical_invocations_are_unchanged_and_never_import_the_preview(self) -> None:
        code = (f"import sys; sys.path[:0] = [{str(REPO_ROOT / 'src')!r}]; "
                "from aggie_analytics.retrospective_baseline import query; "
                "rc = query.main(['--database', 'missing.sqlite', '--history-database', 'm.sqlite', '--grain', "
                "'summary']); print(rc, 'aggie_analytics.retrospective_baseline.preview' in sys.modules, "
                "'aggie_analytics.national_source_time.prospective' in sys.modules)")
        proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(proc.stdout.strip(), "2 False False")
        for argv, text in ((["--grain", "preview-estimate", "--database", "a", "--history-database", "b"],
                            "invalid choice: 'preview-estimate'"),
                           (["--database", "a", "--history-database", "b", "--grain", "summary", "--cutoff", CUTOFF],
                            "unrecognized arguments: --cutoff"),
                           (["--grain", "summary"], "the following arguments are required: --database, "
                                                    "--history-database")):
            code, out, got = self.run_cli(argv, None)
            self.assertEqual(code, 2)
            self.assertIn(text, got)
        usage = query.build_parser().format_usage()
        self.assertNotIn("prospective-preview", usage)
        self.assertIn("--prospective-preview", query.build_parser().format_help())


class ForgeryTests(_Workspace):
    """Coordinated forgeries (outer identities recomputed) must refuse for their own semantic rule."""

    def setUp(self) -> None:
        super().setUp()
        self.w = self.world()
        _, self.path = self.build(self.w)
        self.counter = 0

    def refusal(self, path) -> str:
        code, out, refused = self.run_cli(["--prospective-preview", str(path), "--grain", "preview-estimate",
                                           "--cutoff", CUTOFF], self.w.authority)
        self.assertEqual((code, out), (2, None), refused)
        return refused

    def forged(self, edit) -> Path:
        self.counter += 1
        return fx.forge(self.path, edit, self.tmp / f"f{self.counter}")

    def test_preview_field_forgeries_refuse_for_their_own_family(self) -> None:
        def feature(d, i=0):
            return d["features"][i]

        def est(d, i=0):
            return d["estimates"][i]

        def smoothed(d):
            return next(e for e in d["estimates"] if e["model_id"] == SMOOTH)
        cases = {
            "rehashed_wrong_wins": (lambda d: feature(d).update(wins=feature(d)["wins"] + 1), "FEATURE_RECORD"),
            "rehashed_wrong_games": (lambda d: feature(d).update(games=feature(d)["games"] + 1), "FEATURE_RECORD"),
            "rehashed_wrong_ties": (lambda d: feature(d).update(ties=1), "FEATURE_RECORD"),
            "fabricated_zero_record": (lambda d: feature(d).update(wins=0, losses=0, games=0, cold_start=True),
                                       "FEATURE_RECORD"),
            "wins_as_float": (lambda d: feature(d).update(wins=float(feature(d)["wins"])), "FEATURE_RECORD"),
            "cold_start_as_int": (lambda d: feature(d).update(cold_start=0), "FEATURE_RECORD"),
            "feature_side_swap": (lambda d: feature(d).update(side="away"), "FEATURE_MEMBERSHIP"),
            "feature_participant_swap": (lambda d: feature(d).update(team_key=feature(d, 1)["team_key"]),
                                         "FEATURE_MEMBERSHIP"),
            "feature_dropped": (lambda d: d["features"].pop(), "FEATURE_MEMBERSHIP"),
            "feature_duplicated": (lambda d: d["features"].insert(1, copy.deepcopy(feature(d))),
                                   "FEATURE_MEMBERSHIP"),
            "feature_extra_member": (lambda d: feature(d).update(rank=3), "FEATURE_IDENTITY"),
            "feature_support_fabricated": (lambda d: feature(d).update(unsupported_reasons=["INVENTED"]),
                                           "FEATURE_SUPPORT"),
            "feature_provenance": (lambda d: feature(d).update(source_body_sha256="1" * 64), "FEATURE_PROVENANCE"),
            "feature_pit_label": (lambda d: feature(d).update(pit_admission="PIT_ADMITTED"), "FEATURE_LABELS"),
            "estimate_role_swap": (lambda d: est(d).update(team_key=est(d)["opponent_team_key"],
                                                           opponent_team_key=est(d)["team_key"]),
                                   "ESTIMATE_IDENTITY"),
            "estimate_event_swap": (lambda d: est(d).update(event_key="espn:event:900000002"),
                                    "ESTIMATE_MEMBERSHIP"),
            "estimate_dropped": (lambda d: d["estimates"].pop(), "ESTIMATE_MEMBERSHIP"),
            "estimate_extra": (lambda d: d["estimates"].append(copy.deepcopy(d["estimates"][-1])),
                               "ESTIMATE_MEMBERSHIP"),
            "wrong_numerator": (lambda d: smoothed(d)["probability"].update(
                numerator=smoothed(d)["probability"]["numerator"] + 1), "ESTIMATE_VALUE"),
            "wrong_denominator": (lambda d: smoothed(d)["probability"].update(
                denominator=smoothed(d)["probability"]["denominator"] * 2), "ESTIMATE_VALUE"),
            "unreduced_rational": (lambda d: smoothed(d)["probability"].update(
                numerator=smoothed(d)["probability"]["numerator"] * 2,
                denominator=smoothed(d)["probability"]["denominator"] * 2), "ESTIMATE_VALUE"),
            "wrong_decimal": (lambda d: smoothed(d).update(probability_decimal="0.5"), "ESTIMATE_VALUE"),
            "additive_rule_value": (lambda d: smoothed(d).update(game_home_probability={"numerator": 1,
                                                                                         "denominator": 3}),
                                    "ESTIMATE_VALUE"),
            "estimate_fabricated_abstention": (lambda d: est(d).update(support_state="ABSTAINED"),
                                               "ESTIMATE_SUPPORT"),
            "estimate_skill_label": (lambda d: est(d).update(preview_label="FORECAST"), "ESTIMATE_LABELS"),
            "estimate_lineage": (lambda d: smoothed(d).update(team_feature_sha256="2" * 64), "ESTIMATE_LINEAGE"),
            "game_dropped": (lambda d: d["games"].pop(), "GAME_MEMBERSHIP"),
            "game_model_probability": (lambda d: d["games"][0]["models"][1]["home_probability"].update(numerator=1),
                                       "GAME_MODELS"),
            "summary_denominator": (lambda d: d["summary"][0].update(distinct_events=6), "SUMMARY"),
            "summary_as_float": (lambda d: d["summary"][1].update(features=6.0), "SUMMARY"),
            "count_as_bool": (lambda d: d["counts"].update(abstained_estimates=False), "COUNTS"),
            "model_definition": (lambda d: d["models"][SMOOTH]["definition"].update(home_advantage=0.03), "MODELS"),
            "model_pseudo_count": (lambda d: d["models"][SMOOTH]["definition"]["parameters"].update(pseudo_wins=2),
                                   "MODELS"),
            "fake_contract": (lambda d: d["contract"].update(sha256="3" * 64), "CONTRACT"),
            "fake_capsule_pin": (lambda d: d["input"].update(capsule_identity="4" * 64), "INPUT"),
            "observation_backdated": (lambda d: d["input"]["observation"].update(
                request_end_utc="2026-10-01T00:00:00.000000Z"), "INPUT"),
            "pit_admitted": (lambda d: d["labels"].update(pit_admission="PIT_ADMITTED"), "LABELS"),
            "skill_claimed": (lambda d: d["labels"].update(predictive_skill="ESTABLISHED"), "LABELS"),
            "forecast_claimed": (lambda d: d["labels"].update(preview_status="FORECAST_ISSUED"), "LABELS"),
            "false_clock": (lambda d: d["labels"].update(forecast_issuance="2026-10-11T00:00:00Z"), "LABELS"),
            "numeric_contract": (lambda d: d["numeric_contract"].update(probability="floats"), "NUMERIC_CONTRACT"),
            "bundle_pin": (lambda d: d["bundle"][preview.CONTRACT_MEMBER].update(bytes=1), "BUNDLE"),
            "extra_top_member": (lambda d: d.update(issued_at="2026-10-11T00:00:00Z"), "SCHEMA"),
        }
        for name, (edit, family) in cases.items():
            self.assertEqual(self.refusal(self.forged(edit)), f"PREVIEW_{family}_MISMATCH", name)

    def test_bundle_input_and_location_forgeries(self) -> None:
        capsule_dir = Path(preview.CAPSULE_ROOT) / self.w.capsule_identity
        cases = [("raw/provider-response.json", lambda b: b.replace(b"Fixture Alpha Owls", b"Fixture Alpha Hawk"),
                  "INPUT_RAW_NOT_PINNED_ORIGINAL"),
                 ("raw/provider-receipt.json", lambda b: b.replace(b"18:15:55.264959", b"18:15:50.000000"),
                  "INPUT_RECEIPT_NOT_PINNED_ORIGINAL"),
                 ("capsule.json", lambda b: b.replace(b'"4-1"', b'"5-0"'), "INPUT_CAPSULE_PARTICIPANT_RECORD_MISMATCH")]
        for member, edit, expected in cases:
            self.counter += 1
            target = self.tmp / f"m{self.counter}" / self.path.parent.name
            shutil.copytree(self.path.parent, target)
            path = target / capsule_dir / Path(*member.split("/"))
            path.write_bytes(edit(path.read_bytes()))
            # coordinated outer rehash: the preview bundle pins and directory follow the altered member
            doc = json.loads((target / "preview.json").read_text(encoding="utf-8"))
            rel = f"{preview.CAPSULE_ROOT}/{self.w.capsule_identity}/{member}"
            doc["bundle"][rel] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                  "bytes": path.stat().st_size}
            (target / "preview.json").write_bytes(preview.preview_file_bytes(doc))
            moved = target.parent / preview.preview_identity(doc)
            target.rename(moved)
            self.assertEqual(self.refusal(moved / "preview.json"), expected, member)
        other = fx.PreviewWorld(self.tmp / "o", fx.events_with(lambda ev: ev.pop()))
        self.assertNotEqual(other.contract, self.w.contract)
        self.counter += 1
        target = self.tmp / f"m{self.counter}" / self.path.parent.name
        shutil.copytree(self.path.parent, target)
        (target / "inputs" / "contract.json").write_bytes(other.contract)
        self.assertEqual(self.refusal(target / "preview.json"), "CONTRACT_NOT_COMMITTED_AUTHORITY")
        extra = self.tmp / "extra" / self.path.parent.name
        shutil.copytree(self.path.parent, extra)
        (extra / "notes.txt").write_bytes(b"restated")
        self.assertEqual(self.refusal(extra / "preview.json"), "PREVIEW_BUNDLE_MEMBERSHIP_MISMATCH")
        wrong = self.tmp / "wrong" / ("f" * 64)
        shutil.copytree(self.path.parent, wrong)
        self.assertEqual(self.refusal(wrong / "preview.json"), "PREVIEW_IDENTITY_MISMATCH")
        plain = self.tmp / "plain" / "not-an-identity"
        shutil.copytree(self.path.parent, plain)
        self.assertEqual(self.refusal(plain / "preview.json"), "PREVIEW_LOCATION_INVALID")
        nocap = self.tmp / "nocap" / self.path.parent.name
        shutil.copytree(self.path.parent, nocap)
        (nocap / capsule_dir / "raw" / "provider-receipt.json").unlink()
        self.assertEqual(self.refusal(nocap / "preview.json"), "INPUT_BUNDLE_MEMBER_MISSING")
        pretty = self.tmp / "pretty" / self.path.parent.name
        shutil.copytree(self.path.parent, pretty)
        doc = json.loads((pretty / "preview.json").read_text(encoding="utf-8"))
        (pretty / "preview.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.refusal(pretty / "preview.json"), "PREVIEW_CANONICAL_FORM_MISMATCH")
        dup = self.tmp / "dup" / self.path.parent.name
        shutil.copytree(self.path.parent, dup)
        text = (dup / "preview.json").read_bytes()
        (dup / "preview.json").write_bytes(b'{"schema":"x",' + text[1:])
        self.assertEqual(self.refusal(dup / "preview.json"), "PREVIEW_MALFORMED")

    @unittest.skipUnless(os.name == "nt", "Windows location rules")
    def test_network_device_and_non_literal_locations_refuse_before_access(self) -> None:
        for path, refusal in ((r"\\fixture-server\share" + "\\" + "a" * 64 + r"\preview.json",
                               "PREVIEW_LOCATION_UNSUPPORTED"),
                              (r"\\.\PhysicalDrive0", "PREVIEW_LOCATION_UNSUPPORTED"),
                              (r"\\?\GLOBALROOT\Device\x\preview.json", "PREVIEW_LOCATION_UNSUPPORTED"),
                              ("\\\\?\\" + str(self.path.parent) + r"\..\x" + "\\" + "a" * 64 + r"\preview.json",
                               "PREVIEW_LOCATION_NOT_LITERAL")):
            self.assertEqual(self.refusal(path), refusal, path)


class PortableBundleTests(_Workspace):
    def test_rehoused_relative_and_long_path_previews_serve_identically(self) -> None:
        world = self.world()
        _, path = self.build(world)
        argv = ["--grain", "preview-estimate", "--cutoff", CUTOFF, "--all"]
        _, original, _ = self.run_cli(["--prospective-preview", str(path), *argv], world.authority)
        moved = fx.rehouse(path, self.tmp / "elsewhere")
        _, rehoused, _ = self.run_cli(["--prospective-preview", str(moved), *argv], world.authority)
        self.assertEqual(rehoused["rows"], original["rows"])
        self.assertEqual(rehoused["preview_identity"], original["preview_identity"])
        relative = os.path.relpath(moved, Path.cwd()) if moved.drive == Path.cwd().drive else str(moved)
        _, relative_doc, _ = self.run_cli(["--prospective-preview", relative, *argv], world.authority)
        self.assertEqual(relative_doc["rows"], original["rows"])
        _, equals, _ = self.run_cli([f"--prospective-preview={moved}", *argv], world.authority)
        self.assertEqual(equals["rows"], original["rows"])
        if os.name == "nt":
            far = os.path.join(os.path.abspath(self.tmp), "long " + "x" * 110, "deeper " + "y" * 110, "tail " + "z" * 30,
                               path.parent.name)
            target = "\\\\?\\" + far
            self.assertGreater(len(target), 300)
            for name, data in builder.directory_members(path.parent).items():
                member = os.path.join(target, *name.split("/"))
                os.makedirs(os.path.dirname(member), exist_ok=True)
                with open(member, "xb") as handle:
                    handle.write(data)
            _, long_doc, _ = self.run_cli(["--prospective-preview", os.path.join(target, "preview.json"), *argv],
                                          world.authority)
            self.assertEqual(long_doc["rows"], original["rows"])

    @unittest.skipUnless(os.name == "nt", "Windows classic path limit")
    def test_plain_spelling_whose_nested_members_exceed_the_classic_limit(self) -> None:
        world = self.world()
        _, path = self.build(world)
        argv = ["--grain", "preview-estimate", "--cutoff", CUTOFF, "--all"]
        _, original, _ = self.run_cli(["--prospective-preview", str(path), *argv], world.authority)
        # the preview path itself stays below 260 characters while its nested capsule members exceed it
        pad = 230 - len(os.path.abspath(self.tmp)) - len(path.parent.name) - len("preview.json") - 4
        far = os.path.join(os.path.abspath(self.tmp), "n" + "q" * max(pad, 1), path.parent.name)
        plain = os.path.join(far, "preview.json")
        nested = os.path.join(far, "capsule", world.capsule_identity, "raw", "provider-response.json")
        self.assertLess(len(plain), 260)
        self.assertGreater(len(nested), 260)
        for name, data in builder.directory_members(path.parent).items():
            member = "\\\\?\\" + os.path.join(far, *name.split("/"))
            os.makedirs(os.path.dirname(member), exist_ok=True)
            with open(member, "xb") as handle:
                handle.write(data)
        code, doc, refused = self.run_cli(["--prospective-preview", plain, *argv], world.authority)
        self.assertEqual(code, 0, refused)
        self.assertEqual(doc["rows"], original["rows"])
        # a build into a deep output root (nested members beyond the limit) materializes, verifies and re-verifies
        deep = Path(os.path.join(os.path.abspath(self.tmp), "d" + "r" * max(pad - 60, 1)))
        result = builder.build(world.build_args(deep))
        self.assertEqual((result["identity"], result["preview_state"]), (path.parent.name, "MATERIALIZED"))
        self.assertGreater(len(os.path.join(str(deep), "canonical", "sha256", result["identity"], "capsule",
                                            world.capsule_identity, "raw", "provider-response.json")), 260)
        again = builder.build(world.build_args(deep))
        self.assertEqual(again["preview_state"], "ALREADY_PRESENT_IDENTICAL")


class MountedGenuinePreviewTests(unittest.TestCase):
    """The genuine accepted capsule through the committed authority (mounted lanes only)."""

    def capsule(self) -> Path:
        root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        pins = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))["input"]
        if not root:
            self.skipTest("mounted data root required")
        capsule = Path(root) / "canonical" / prospective.POPULATION / "sha256" / pins["capsule_identity"] / \
            prospective.CAPSULE_FILE
        if not capsule.is_file():
            self.skipTest(f"accepted capsule not mounted at {capsule}")
        return capsule

    def test_genuine_capsule_derives_the_complete_preview_population(self) -> None:
        capsule = self.capsule()
        identity, files, iddoc, doc = preview.build_preview(capsule, fx.CONTRACT_PATH.read_bytes())
        self.assertEqual((doc["counts"]["events"], doc["counts"]["features"], doc["counts"]["estimates"],
                          doc["counts"]["games"]), (25, 50, 100, 25))
        verified = prospective.verify_capsule(capsule)
        self.assertEqual(sorted(g["event_key"] for g in doc["games"]),
                         sorted(e["event_key"] for e in verified["document"]["events"]))
        supported = sum(p["support_state"] == "SUPPORTED" for p in verified["document"]["participants"])
        self.assertEqual(doc["counts"]["supported_features"], supported)
        self.assertEqual(iddoc["contract_sha256"], preview.CONTRACT_SHA256)
        gate = REPO_ROOT / "artifacts" / "data_lake" / "provider_record_baseline_preview_20261011_gate.json"
        if gate.is_file():
            binding = json.loads(gate.read_text(encoding="utf-8"))
            self.assertEqual(binding["preview_identity"], identity)
            self.assertEqual(binding["identity_document"], iddoc)
            canonical = Path(os.environ["AGGIE_ANALYTICS_DATA_ROOT"]) / "canonical" / preview.POPULATION / "sha256" / \
                identity / preview.PREVIEW_FILE
            if canonical.is_file():
                self.assertEqual(preview.verify_preview(canonical, expect_identity=identity)["identity_document"],
                                 iddoc)


if __name__ == "__main__":
    unittest.main()
