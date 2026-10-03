"""BAT-713 archived-publication evidence producer and independent validator (Cycle #41 TP41-A01).

Everything runs offline on the synthetic world of ``national_archived_publication_fixture`` (fictional records only):
the capture stage is driven by a fake archive transport, so its request plan, limits, retries, redirect refusals and
journal are exercised without any network access.
"""
from __future__ import annotations

import ast
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_archived_publication_fixture as fx  # noqa: E402

STATE: dict = {}
QUAL = "QUALIFIED_AGREES_WITH_PARENT"


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    world = fx.build_world(Path(STATE["tmp"].name) / "g")
    STATE["capture"] = fx.run_capture(world)
    code, result, err = fx.run_build(world)
    assert code == 0, err
    STATE["world"], STATE["result"] = world, result


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def payload(name: str) -> list[dict]:
    return fx.read_payload(STATE["result"], name)


def disposition(key: str) -> dict:
    return next(d for d in payload("dispositions.jsonl") if d["contest_key"] == key)


def fresh_world(name: str, scenarios=None) -> dict:
    return fx.build_world(Path(STATE["tmp"].name) / name, scenarios)


class AcquisitionTests(unittest.TestCase):
    def test_every_key_has_one_explicit_outcome_and_the_control_costs_nothing(self) -> None:
        outcomes = STATE["capture"]["outcomes"]
        self.assertEqual(sorted(outcomes), sorted(k for k, _r, _s in fx.TRANCHE))
        self.assertEqual(outcomes["ncaa:1003"], "CONTROL_REUSED")
        self.assertEqual(outcomes["ncaa:1005"], "NO_ARCHIVE_CAPTURE_REPORTED")
        self.assertEqual(outcomes["ncaa:1007"], "REDIRECT_REFUSED")
        requests = payload("requests.jsonl")
        self.assertFalse([r for r in requests if r["contest_key"] == "ncaa:1003"])
        self.assertEqual([r["seq"] for r in requests], list(range(1, len(requests) + 1)))
        self.assertEqual(len(requests), STATE["capture"]["totals"]["requests"])
        self.assertEqual(sorted(d["contest_key"] for d in payload("dispositions.jsonl")), sorted(outcomes))

    def test_per_key_limits_hold_and_only_archive_hosts_are_requested(self) -> None:
        for key, _role, _stratum in fx.TRANCHE:
            mine = [r for r in payload("requests.jsonl") if r["contest_key"] == key]
            self.assertLessEqual(sum(1 for r in mine if r["kind"] == "METADATA"), 2)
            self.assertLessEqual(sum(1 for r in mine if r["kind"] == "REPLAY"), 2)
        for url in STATE["world"]["archive"].calls:
            self.assertRegex(url, r"^https://(archive\.org/wayback/available\?|web\.archive\.org/web/\d{14}id_/)")

    def test_retry_once_then_redirect_to_live_host_is_refused_and_counted(self) -> None:
        mine = [r for r in payload("requests.jsonl") if r["contest_key"] == "ncaa:1007"]
        self.assertEqual([(r["kind"], r["purpose"], r["http_status"]) for r in mine],
                         [("METADATA", "PROBE_1", 503), ("METADATA", "RETRY", 200), ("REPLAY", "CAPTURE_1", 302)])
        self.assertTrue(mine[-1]["location"].startswith("https://www.espn.com/"))
        self.assertEqual(disposition("ncaa:1007")["disposition"], "REDIRECT_REFUSED")
        self.assertFalse(any("www.espn.com/college" in u and "web.archive.org" not in u
                             for u in STATE["world"]["archive"].calls))

    def test_pregame_version_prompts_one_post_event_probe(self) -> None:
        mine = [(r["kind"], r["purpose"]) for r in payload("requests.jsonl") if r["contest_key"] == "ncaa:1002"]
        self.assertEqual(mine, [("METADATA", "PROBE_1"), ("REPLAY", "CAPTURE_1"), ("METADATA", "PROBE_2"),
                                ("REPLAY", "CAPTURE_2")])
        support = disposition("ncaa:1002")["field_support"]
        self.assertEqual(support["a_participant"], "2019-08-31T12:00:00.999999Z")
        self.assertEqual(support["a_points"], "2019-09-02T10:00:00.999999Z")

    def test_total_limit_stops_requests_and_records_unattempted_keys(self) -> None:
        world = fresh_world("lim")
        contract = copy.deepcopy(world["contract_doc"])
        contract["acquisition"]["limits"]["total_requests"] = 3
        result = fx.run_capture(world, contract=contract)
        self.assertEqual(result["totals"]["requests"], 3)
        self.assertEqual(result["outcomes"]["ncaa:1004"], "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED")
        self.assertEqual(len(world["archive"].calls), 3)

    def test_retry_after_is_honoured_once_then_failure_is_explicit(self) -> None:
        def busy(archive, row):
            archive.meta[(row["cfbd_game_id"]["value"], row["metadata_probe_timestamp"])] = 429
        world = fresh_world("ra", {"ncaa:1001": busy})
        result = fx.run_capture(world)
        self.assertEqual(result["outcomes"]["ncaa:1001"], "METADATA_REQUEST_FAILED")
        self.assertIn(2, result["slept"])
        doc = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        mine = [r for r in doc["requests"] if r["contest_key"] == "ncaa:1001"]
        self.assertEqual([(r["purpose"], r["http_status"], r["retry_after_seconds"]) for r in mine],
                         [("PROBE_1", 429, 2), ("RETRY", 429, 2)])

    def test_in_host_redirect_is_followed_once(self) -> None:
        def hop(archive, row):
            game = row["cfbd_game_id"]["value"]
            archive.meta[(game, row["metadata_probe_timestamp"])] = ("20190901041500", "302")
            target = f"https://web.archive.org/web/20190901041501id_/{fx.game_url(game, 'http')}"
            archive.replay[("20190901041500", game)] = (302, [["Location", target]], b"")
            archive.replay[("20190901041501", game)] = (
                200, fx.replay_headers("20190901041501", fx.game_url(game, "http")), fx.page_for(row))
        world = fresh_world("hop", {"ncaa:1001": hop})
        result = fx.run_capture(world)
        self.assertEqual(result["outcomes"]["ncaa:1001"], "CAPTURED")
        doc = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        purposes = [r["purpose"] for r in doc["requests"] if r["contest_key"] == "ncaa:1001"]
        self.assertEqual(purposes, ["PROBE_1", "CAPTURE_1", "REDIRECT_HOP"])

    def test_metadata_answer_for_another_url_is_not_used(self) -> None:
        build = fx.builder()
        body = json.dumps({"archived_snapshots": {"closest": {
            "available": True, "status": "200", "timestamp": "20190901041500",
            "url": "http://web.archive.org/web/20190901041500/https://www.espn.com/college-football/game/_/gameId/1"}}})
        self.assertEqual(build.metadata_answer(body.encode(), "2")["reason"], "CLOSEST_FOR_ANOTHER_URL")
        self.assertEqual(build.metadata_answer(b"not json", "2")["reason"], "METADATA_ANSWER_NOT_JSON")

    def test_interrupted_capture_counts_the_unknown_request_on_resume(self) -> None:
        world = fresh_world("int")
        real = world["archive"]
        calls = {"n": 0}

        def crashing(url, headers, timeout):
            calls["n"] += 1
            if calls["n"] == 2:
                raise KeyboardInterrupt("simulated interruption")
            return real(url, headers, timeout)
        with self.assertRaises(KeyboardInterrupt):
            fx.run_capture(world, transport=crashing)
        result = fx.run_capture(world)
        doc = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        unknown = [r for r in doc["requests"] if r["outcome"] == "INTERRUPTED_UNKNOWN"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0]["seq"], 2)
        mine = [r for r in doc["requests"] if r["contest_key"] == unknown[0]["contest_key"]]
        self.assertLessEqual(sum(1 for r in mine if r["kind"] == unknown[0]["kind"]), 2)

    def test_request_starts_use_the_high_resolution_counter_with_a_margin(self) -> None:
        import inspect  # noqa: PLC0415
        import time  # noqa: PLC0415
        build = fx.builder()
        self.assertIs(inspect.signature(build.capture).parameters["monotonic"].default, time.perf_counter)
        self.assertGreaterEqual(build.SPACING_MARGIN_SECONDS, 0.05)
        # the fixture's fake counter advances 0.25 s per reading: every wait is 1.0 + margin - 0.25 seconds
        self.assertTrue(all(abs(s - (0.75 + build.SPACING_MARGIN_SECONDS)) < 1e-9 for s in STATE["capture"]["slept"]))

    def test_finalized_acquisition_makes_no_request(self) -> None:
        before = len(STATE["world"]["archive"].calls)
        again = fx.run_capture(STATE["world"])
        self.assertEqual((again["state"], again["new_requests"]), ("ALREADY_FINALIZED", 0))
        self.assertEqual(len(STATE["world"]["archive"].calls), before)

    def test_stale_journal_refuses(self) -> None:
        world = fresh_world("sj")
        build = fx.builder()
        contract = copy.deepcopy(world["contract_doc"])
        pid = build.policy_id(contract)
        journal = world["out"] / "acquisition" / "journal" / pid / "journal.jsonl"
        fx.write(journal, b'{"header": {"policy_id": "other"}, "type": "HEADER"}\n')
        with self.assertRaises(build.BuildRefused) as caught:
            fx.run_capture(world)
        self.assertEqual(caught.exception.code, "REFUSED_STALE_JOURNAL")


class QualificationTests(unittest.TestCase):
    """Receipt and page rules applied to single archived versions of the synthetic ncaa:1001 contest."""

    def setUp(self) -> None:
        self.build = fx.builder()
        self.row = STATE["world"]["by_key"]["ncaa:1001"]
        self.game = self.row["cfbd_game_id"]["value"]
        control = self.build.verify_control(STATE["world"]["contract_doc"], STATE["world"]["route"])
        self.parent = self.build.read_parent(STATE["world"]["st_db"], [
            {k: v for k, v in self.row.items() if not k.startswith("_")}])["ncaa:1001"]
        self.assertTrue(control)

    def judge(self, page: bytes, *, ts: str = "20190901041500", headers=None, status: int = 200):
        url = f"https://web.archive.org/web/{ts}id_/{fx.game_url(self.game)}"
        headers = headers if headers is not None else fx.replay_headers(ts, fx.game_url(self.game))
        checks, reasons, derived = self.build.receipt_checks(url, status, headers, page, self.game)
        result = self.build.qualify("ncaa:1001", self.parent, self.game, page, derived["bound"], reasons)
        return result, derived

    def test_genuine_version_qualifies_every_witnessable_field_with_end_of_second_bound(self) -> None:
        result, derived = self.judge(fx.page_for(self.row))
        self.assertEqual(result["reasons"], [])
        self.assertEqual(derived["bound"], "2019-09-01T04:15:00.999999Z")
        self.assertEqual({f: s for f, s in result["states"].items() if s != QUAL}, {"season": "NOT_WITNESSED_IN_VERSION"})

    def test_wrong_game_node_and_matching_scoreboard_are_quarantined(self) -> None:
        page = fx.page_for(self.row, nav_game="990001", js_game="990001")
        result, _ = self.judge(page)
        self.assertIn("WRONG_GAME_NODE", result["reasons"])
        self.assertIn("GAME_IDENTITY_MISMATCH", result["reasons"])
        self.assertNotIn(QUAL, result["states"].values())
        board = page.find(b"global-scoreboard")
        self.assertTrue(all(a["witness_span"][0] > page.find(b'id="custom-nav"') for a in result["assertions"]
                            if a["witness"].endswith("SCORE")))
        self.assertGreater(board, 0)

    def test_error_pages_and_json_bodies_are_never_qualified(self) -> None:
        result, _ = self.judge(b"<html><body><h1>Page not found</h1></body></html>")
        self.assertIn("MAIN_GAME_ELEMENT_ABSENT", result["reasons"])
        headers = fx.replay_headers("20190901041500", fx.game_url(self.game), content_type="application/json")
        result, _ = self.judge(b'{"error": "not found"}', headers=headers)
        self.assertIn("NOT_AN_ARCHIVED_HTML_200", result["reasons"])

    def test_malformed_absent_and_contradictory_timestamps_quarantine(self) -> None:
        original = fx.game_url(self.game)
        cases = {"MEMENTO_DATETIME_MALFORMED": fx.replay_headers("20190901041500", original,
                                                                 memento="2019-09-01 04:15:00"),
                 "MEMENTO_DATETIME_ABSENT": fx.replay_headers("20190901041500", original, memento=None),
                 "ARCHIVE_TIMESTAMPS_CONTRADICTORY": fx.replay_headers("20190901041500", original,
                                                                       memento=fx.http_date("20190901041501")),
                 "ORIGIN_DATE_CONTRADICTORY": fx.replay_headers("20190901041500", original,
                                                                origin_date=fx.http_date("20190901041500", 301))}
        for code, headers in cases.items():
            result, _ = self.judge(fx.page_for(self.row), headers=headers)
            self.assertIn(code, result["reasons"], code)
            self.assertNotIn(QUAL, result["states"].values(), code)

    def test_later_origin_date_within_tolerance_moves_the_bound_later(self) -> None:
        headers = fx.replay_headers("20190901041500", fx.game_url(self.game),
                                    origin_date=fx.http_date("20190901041500", 7))
        _result, derived = self.judge(fx.page_for(self.row), headers=headers)
        self.assertEqual(derived["bound"], "2019-09-01T04:15:07.999999Z")

    def test_memento_for_another_url_is_quarantined(self) -> None:
        headers = fx.replay_headers("20190901041500", fx.game_url(self.game),
                                    link_original=fx.game_url("990001"))
        result, _ = self.judge(fx.page_for(self.row), headers=headers)
        self.assertIn("MEMENTO_FOR_ANOTHER_URL", result["reasons"])

    def test_orientation_comes_from_identity_and_swapped_scores_conflict(self) -> None:
        result, _ = self.judge(fx.page_for(self.row, swap_scores=True))
        self.assertEqual(result["states"]["a_points"], "CONFLICTS_WITH_PARENT")
        self.assertEqual(result["states"]["a_participant"], QUAL)

    def test_equal_number_in_another_namespace_never_joins(self) -> None:
        caps = [c for c in payload("captures.jsonl") if c["contest_key"] == "ncaa:1004"]
        self.assertEqual(caps[0]["orientation"]["a_side"], None)
        self.assertEqual(caps[0]["field_states"]["a_participant"], "ORIENTATION_UNRESOLVED")
        self.assertEqual(caps[0]["field_states"]["b_points"], "ORIENTATION_UNRESOLVED")
        self.assertEqual(disposition("ncaa:1004")["disposition"], "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS")

    def test_absent_score_is_never_filled_from_the_parent(self) -> None:
        record = self.row["_record"]
        home, away = fx.side_ids(record)
        page = fx.espn_page(self.game, home, away, None, None, kickoff="2019-08-31T23:30Z")
        result, _ = self.judge(page)
        self.assertEqual(result["states"]["a_points"], "NOT_WITNESSED_IN_VERSION")
        self.assertFalse([a for a in result["assertions"] if a["field"] in ("a_points", "b_points")])

    def test_contradictory_date_witnesses_and_in_progress_status(self) -> None:
        result, _ = self.judge(fx.page_for(self.row, info_date="2019-09-07T23:30Z"))
        self.assertEqual(result["states"]["contest_date"], "CONTRADICTORY_WITHIN_VERSION")
        result, _ = self.judge(fx.page_for(self.row, status="in", detail="3rd Quarter"))
        self.assertEqual(result["states"]["completion"], "NOT_SUPPORTED_BY_VERSION_STATUS")
        self.assertEqual(result["states"]["a_points"], "NOT_SUPPORTED_BY_VERSION_STATUS")

    def test_final_status_before_the_event_date_is_impossible(self) -> None:
        result, _ = self.judge(fx.page_for(self.row), ts="20190820000000")
        self.assertIn("IMPOSSIBLE_CHRONOLOGY", result["reasons"])

    def test_witness_spans_reread_exactly_from_raw(self) -> None:
        page = fx.page_for(self.row)
        result, _ = self.judge(page)
        for item in result["assertions"]:
            start, end = item["witness_span"]
            self.assertEqual(page[start:end].decode("utf-8"), item["literal"])


class RefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))

    def refused(self, *, mutate=None, **kwargs) -> str | None:
        world = STATE["world"]
        if mutate is not None:
            kwargs["contract"] = fx.patched_contract(world, self.dir / "c.json", mutate)
        code, _result, err = fx.run_build(world, out=self.dir / "o" / "canonical" / "ap",
                                          manifests=self.dir / "o" / "manifests" / "ap", **kwargs)
        self.assertNotEqual(code, 0)
        return fx.refusal(err)

    def test_materialization_before_any_finalized_acquisition_refuses(self) -> None:
        self.assertEqual(self.refused(), "ACQUISITION_MISSING")

    def test_wrong_or_tampered_parent_refuses(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c["parent_binding"]["source_time"].update(
            database_identity="0" * 64)), "WRONG_PARENT")
        st = STATE["world"]["st_db"]
        copy_dir = self.dir / "st" / "canonical" / "st" / "sha256" / st.parent.name
        copy_dir.mkdir(parents=True)
        shutil.copyfile(st, copy_dir / st.name)
        manifest = STATE["world"]["st_result"]["database"]["manifest"]
        target = self.dir / "st" / "manifests" / "st" / "sha256" / st.parent.name / "run_manifest.json"
        target.parent.mkdir(parents=True)
        shutil.copyfile(manifest, target)
        conn = sqlite3.connect(copy_dir / st.name)
        conn.execute("UPDATE meta SET value = value || ' ' WHERE key = 'contract_id'")
        conn.commit()
        conn.close()
        self.assertEqual(self.refused(database=copy_dir / st.name), "PARENT_TAMPERED")

    def test_unknown_schema_and_forged_authority_refuse(self) -> None:
        self.assertEqual(self.refused(mutate=lambda c: c.update(schema_version="9.9.9")), "CONTRACT_SCHEMA_UNKNOWN")
        self.assertEqual(self.refused(mutate=lambda c: c["authority"].update(pit_admission="ADMITTED")),
                         "FORGED_PIT_AUTHORITY")
        self.assertEqual(self.refused(mutate=lambda c: c["acquisition"]["limits"].update(
            replay_requests_per_key=5)), "ACQUISITION_POLICY_INVALID")

    def test_duplicate_omitted_or_out_of_tranche_keys_refuse(self) -> None:
        tranche = json.loads(STATE["world"]["tranche"].read_text(encoding="utf-8"))
        tranche["selected"][1] = copy.deepcopy(tranche["selected"][0])
        path = fx.write(self.dir / "t.json", json.dumps(tranche).encode())
        self.assertEqual(self.refused(tranche=path, mutate=lambda c: c["scope"].update(
            tranche_sha256=fx.sha(path.read_bytes()))), "TRANCHE_KEYS_INVALID")
        self.assertEqual(self.refused(mutate=lambda c: c["scope"].update(tranche_count=7)), "TRANCHE_KEYS_INVALID")

    def test_tranche_row_disagreeing_with_the_parent_refuses(self) -> None:
        tranche = json.loads(STATE["world"]["tranche"].read_text(encoding="utf-8"))
        tranche["selected"][0]["a_points"] = 99
        path = fx.write(self.dir / "t2.json", json.dumps(tranche).encode())
        bindings = json.loads(STATE["world"]["bindings"].read_text(encoding="utf-8"))
        bindings["tranche"].update(path=str(path), sha256=fx.sha(path.read_bytes()))
        bpath = fx.write(self.dir / "b.json", json.dumps(bindings).encode())

        def mutate(c):
            c["scope"]["tranche_sha256"] = fx.sha(path.read_bytes())
            c["parent_binding"]["source_bindings"]["sha256"] = fx.sha(bpath.read_bytes())
        self.assertEqual(self.refused(tranche=path, bindings=bpath, mutate=mutate), "TRANCHE_PARENT_MISMATCH")

    def test_bindings_naming_another_database_refuse(self) -> None:
        bindings = json.loads(STATE["world"]["bindings"].read_text(encoding="utf-8"))
        bindings["source_time_database"]["identity"] = "f" * 64
        bpath = fx.write(self.dir / "b2.json", json.dumps(bindings).encode())
        self.assertEqual(self.refused(bindings=bpath, mutate=lambda c: c["parent_binding"]["source_bindings"].update(
            sha256=fx.sha(bpath.read_bytes()))), "SOURCE_BINDINGS_MISMATCH")

    def test_changed_raw_bytes_under_the_same_receipt_refuse(self) -> None:
        world = fresh_world("raw")
        fx.run_capture(world)
        doc = json.loads(Path(next((world["out"] / "acquisition" / "sha256").glob("*/acquisition.json")))
                         .read_text(encoding="utf-8"))
        body = next(r["body_sha256"] for r in doc["requests"] if r["kind"] == "REPLAY" and r["http_status"] == 200)
        raw = world["out"] / "raw" / "sha256" / body
        raw.write_bytes(raw.read_bytes().replace(b"Final", b"Fina1", 1))
        code, _result, err = fx.run_build(world)
        self.assertEqual((code, fx.refusal(err)), (2, "RAW_ALTERED"))

    def test_out_of_tranche_request_in_the_acquisition_refuses(self) -> None:
        world = fresh_world("oot")
        fx.run_capture(world)
        acq_path = next((world["out"] / "acquisition" / "sha256").glob("*/acquisition.json"))
        doc = json.loads(acq_path.read_text(encoding="utf-8"))
        forged = copy.deepcopy(doc)
        forged["requests"][0]["url"] = "https://www.espn.com/college-football/game/_/gameId/1"
        data = json.dumps(forged, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        target = world["out"] / "acquisition" / "sha256" / fx.sha(data) / "acquisition.json"
        fx.write(target, data)
        code, _result, err = fx.run_build(world, "--acquisition", str(target))
        self.assertEqual((code, fx.refusal(err)), (2, "ACQUISITION_HOST_REFUSED"))


class DeterminismAndResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))

    def build(self, name: str, *extra: str):
        return fx.run_build(STATE["world"], "--evidence-root", str(STATE["world"]["out"]), *extra,
                            out=self.dir / name / "canonical" / "ap", manifests=self.dir / name / "manifests" / "ap")

    def test_input_order_and_chunking_reproduce_the_identities(self) -> None:
        reference = STATE["result"]
        for name, extra in (("r", ["--input-order", "reverse"]), ("s", ["--input-order", "shuffle:17"]),
                            ("c1", ["--chunk-size", "1", "--checkpoint-dir", str(self.dir / "k1")]),
                            ("c17", ["--chunk-size", "17", "--checkpoint-dir", str(self.dir / "k17")])):
            code, result, err = self.build(name, "--acquisition", str(self.acquisition()), *extra)
            self.assertEqual(code, 0, err)
            self.assertEqual((result["content_identity"], result["database_identity"], result["database_sha256"]),
                             (reference["content_identity"], reference["database_identity"],
                              reference["database_sha256"]), name)

    def acquisition(self) -> Path:
        return next((STATE["world"]["out"] / "acquisition" / "sha256").glob("*/acquisition.json"))

    def test_interrupted_then_resumed_build_is_identical(self) -> None:
        ck = str(self.dir / "ir")
        code, result, _err = self.build("i", "--acquisition", str(self.acquisition()), "--chunk-size", "1",
                                        "--checkpoint-dir", ck, "--stop-after-chunks", "2")
        self.assertEqual((code, result["state"], result["completed_chunks"]), (3, "INTERRUPTED_AT_CHECKPOINT", 2))
        code, result, err = self.build("i", "--acquisition", str(self.acquisition()), "--chunk-size", "1",
                                       "--checkpoint-dir", ck, "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual(result["content_identity"], STATE["result"]["content_identity"])

    def test_stale_altered_and_existing_checkpoints_refuse(self) -> None:
        ck = self.dir / "st"
        acq = str(self.acquisition())
        self.build("a", "--acquisition", acq, "--chunk-size", "1", "--checkpoint-dir", str(ck), "--stop-after-chunks",
                   "2")
        code, _r, err = self.build("a", "--acquisition", acq, "--chunk-size", "2", "--checkpoint-dir", str(ck),
                                   "--resume")
        self.assertEqual(fx.refusal(err), "REFUSED_STALE_CHECKPOINT")
        code, _r, err = self.build("a", "--acquisition", acq, "--chunk-size", "1", "--checkpoint-dir", str(ck))
        self.assertEqual(fx.refusal(err), "CHECKPOINT_EXISTS")
        chunk = ck / "chunks" / "chunk_000001.jsonl.gz"
        chunk.write_bytes(gzip.compress(gzip.decompress(chunk.read_bytes()).replace(b"ncaa", b"ncab", 1), mtime=0))
        code, _r, err = self.build("a", "--acquisition", acq, "--chunk-size", "1", "--checkpoint-dir", str(ck),
                                   "--resume")
        self.assertEqual(fx.refusal(err), "REFUSED_ALTERED_PREFIX")

    def test_rebuild_is_already_present_and_collision_refuses(self) -> None:
        code, result, err = self.build("p", "--acquisition", str(self.acquisition()))
        self.assertEqual(code, 0, err)
        code, again, err = self.build("p", "--acquisition", str(self.acquisition()))
        self.assertEqual((code, again["state"]), (0, "ALREADY_PRESENT_IDENTICAL"))
        db = Path(result["database"]["data_dir"]) / "national_archived_publication.sqlite"
        os.chmod(db, 0o666)
        with db.open("ab") as handle:
            handle.write(b"x")
        code, _again, err = self.build("p", "--acquisition", str(self.acquisition()))
        self.assertEqual(fx.refusal(err), "REFUSED_IMMUTABLE_COLLISION")


class IndependentValidatorTests(unittest.TestCase):
    def test_validator_imports_no_producer_query_or_project_code(self) -> None:
        tree = ast.parse(fx.VALIDATOR_PATH.read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names}
        names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                  and node.module}
        self.assertFalse(names & {"aggie_analytics", "build_national_archived_publication", "tools", "polars",
                                  "duckdb"}, names)
        self.assertLessEqual(names, set(sys.stdlib_module_names) | {"__future__"})

    def validate(self, manifest: Path, name: str) -> dict:
        report = Path(STATE["tmp"].name) / f"{name}.json"
        world = STATE["world"]
        with contextlib.redirect_stdout(io.StringIO()):
            fx.validator().main(["--contract", str(world["contract"]), "--source-database", str(world["st_db"]),
                                 "--source-bindings", str(world["bindings"]), "--tranche", str(world["tranche"]),
                                 "--manifest", str(manifest), "--report", str(report), "--skip-consumer"])
        return json.loads(report.read_text(encoding="utf-8"))

    def test_validator_passes_the_genuine_delivery_and_rejects_rehashed_semantic_tamper(self) -> None:
        manifest = Path(STATE["result"]["content"]["manifest"])
        doc = self.validate(manifest, "genuine")
        self.assertEqual(doc["result"], "PASS", doc["failed_checks"])
        spacing = doc["grant_conditions"]["request_start_spacing"]
        self.assertEqual((spacing["state"], spacing["intervals_below_declared"]), ("HELD", []))
        self.assertEqual(doc["grant_conditions"]["total_requests"]["state"], "HELD")
        self.assertTrue(all(t["rejected"] for t in doc["tamper_cases"] if t["applied"]))
        # Coordinated tamper: swap a/b points in the payload, recompute every outer hash and identity.
        root = Path(STATE["tmp"].name) / "tam"
        shutil.copytree(STATE["world"]["out"].parent.parent, root)
        content = json.loads(manifest.read_text(encoding="utf-8"))
        old_dir = root / "canonical" / "ap" / "sha256" / STATE["result"]["content_identity"]
        lines = gzip.decompress((old_dir / "assertions.jsonl.gz").read_bytes()).decode("utf-8").splitlines()
        rows = [json.loads(x) for x in lines]
        for row in rows:
            if row["field"] == "a_points":
                row["value"] += 1
                break
        raw = "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
                      for r in rows).encode("utf-8")
        ident = content["identity_document"]
        ident["semantic_outputs"]["assertions.jsonl"] = hashlib.sha256(raw).hexdigest()
        packed = gzip.compress(raw, compresslevel=9, mtime=0)
        ident["outputs"]["assertions.jsonl.gz"] = hashlib.sha256(packed).hexdigest()
        new_id = hashlib.sha256(json.dumps(ident, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                                .encode("utf-8")).hexdigest()
        new_dir = old_dir.parent / new_id
        shutil.copytree(old_dir, new_dir)
        (new_dir / "assertions.jsonl.gz").write_bytes(packed)
        new_manifest = root / "manifests" / "ap" / "sha256" / new_id / "run_manifest.json"
        fx.write(new_manifest, json.dumps({"identity": new_id, "identity_document": ident,
                                           "provenance": content["provenance"]}).encode("utf-8"))
        doc = self.validate(new_manifest, "tampered")
        self.assertEqual(doc["result"], "FAIL")
        self.assertIn("every_record_reconstructed_independently", doc["failed_checks"])


if __name__ == "__main__":
    unittest.main()
