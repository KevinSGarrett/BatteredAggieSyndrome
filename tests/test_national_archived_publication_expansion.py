"""BAT-715 archive expansion (Cycle #43 TP43-A01): union scope, retained reuse, the expansion planner, materialization,
the explicit consumer and its refusals. Synthetic worlds only (``national_archived_publication_expansion_fixture``)."""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_archived_publication_expansion_fixture as xfx  # noqa: E402
import national_archived_publication_fixture as apfx  # noqa: E402
from aggie_analytics.national_source_time import archive as arch  # noqa: E402
from aggie_analytics.national_source_time import archive_fields as af  # noqa: E402
from aggie_analytics.national_source_time import query as q  # noqa: E402

STATE: dict = {}


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    world = xfx.build_expansion_world(Path(STATE["tmp"].name) / "x")
    capture = xfx.run_capture(world)
    code, result, err = xfx.run_build(world)
    assert code == 0, err
    STATE.update(world=world, capture=capture, result=result, sidecar=xfx.database_path(result))
    STATE["stack"] = contextlib.ExitStack()
    STATE["stack"].enter_context(arch.registered_authority(xfx.issued_authority(world)))


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["stack"].close()
    STATE["tmp"].cleanup()


def query(*argv: str, sidecar: Path | None = None) -> tuple[int, dict | None, str]:
    args = ["--database", str(STATE["world"]["st_db"]), "--archive-evidence", str(sidecar or STATE["sidecar"]), *argv]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = q.main(args)
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    return code, (json.loads(text) if text.strip() else None), err.getvalue()


def payload(name: str) -> list[dict]:
    return xfx.read_payload(STATE["result"], name)


class PlannerTests(unittest.TestCase):
    """plan_next_expansion: deterministic, bounded, never re-replays a retained version."""

    def setUp(self) -> None:
        self.b = xfx.builder()
        self.view = {"acquisition": {"limits": {"retry_after_cap_seconds": 120, "replay_requests_per_key": 2}}}
        self.key = {"contest_key": "ncaa:1", "game_id_literal": "901", "candidate_url": apfx.game_url("901"),
                    "expansion_probe_timestamps": ["20190906095959", "20190902000000"]}

    def meta(self, ts: str | None, purpose: str = "PROBE_1", status: int = 200) -> dict:
        body = {"archived_snapshots": {} if ts is None else {"closest": {
            "status": "200", "available": True, "timestamp": ts,
            "url": f"http://web.archive.org/web/{ts}/{apfx.game_url('901')}"}}}
        return {"kind": "METADATA", "purpose": purpose, "http_status": status, "outcome": "RESPONSE",
                "retry_after_seconds": None, "body": json.dumps(body).encode(), "url": "m"}

    def replay(self, ts: str, status: int = 200, location: str | None = None) -> dict:
        return {"kind": "REPLAY", "purpose": "CAPTURE_1", "http_status": status, "outcome": "RESPONSE",
                "retry_after_seconds": None, "location": location,
                "url": f"https://web.archive.org/web/{ts}id_/{apfx.game_url('901')}"}

    def plan(self, history: list[dict], retained: frozenset = frozenset()):
        return self.b.plan_next_expansion(self.key, history, self.view, lambda r: r["body"], retained)

    def test_in_window_version_needs_no_second_probe(self) -> None:
        self.assertEqual(self.plan([])[1], "PROBE_1")
        step = self.plan([self.meta("20190903000000")])
        self.assertEqual(step[:2], ("REPLAY", "CAPTURE_1"))
        self.assertIn("20190903000000id_", step[2])
        self.assertIsNone(self.plan([self.meta("20190903000000"), self.replay("20190903000000")]))

    def test_late_and_early_versions_ask_probe_two_and_capture_a_different_version(self) -> None:
        for first in ("20190920000000", "20190901000000"):
            history = [self.meta(first), self.replay(first)]
            step = self.plan(history)
            self.assertEqual(step[:2], ("METADATA", "PROBE_2"))
            self.assertIn("timestamp=20190902000000", step[2])
            history.append(self.meta("20190903000000", "PROBE_2"))
            self.assertEqual(self.plan(history)[:2], ("REPLAY", "CAPTURE_2"))
            history.append(self.replay("20190903000000"))
            self.assertIsNone(self.plan(history))
            same = [self.meta(first), self.replay(first), self.meta(first, "PROBE_2")]
            self.assertIsNone(self.plan(same), "the same version is never replayed twice")

    def test_retained_versions_cost_no_replay(self) -> None:
        retained = frozenset({"20190903000000"})
        self.assertIsNone(self.plan([self.meta("20190903000000")], retained))
        late = frozenset({"20190920000000"})
        self.assertEqual(self.plan([self.meta("20190920000000")], late)[:2], ("METADATA", "PROBE_2"))
        self.assertIsNone(self.plan([self.meta("20190920000000"), self.meta("20190920000000", "PROBE_2")], late))
        self.assertIsNone(self.plan([self.meta("20190920000000"), self.meta("20190903000000", "PROBE_2")],
                                    frozenset({"20190920000000", "20190903000000"})))

    def test_no_capture_then_probe_two_and_equal_probes_stop(self) -> None:
        self.assertEqual(self.plan([self.meta(None)])[:2], ("METADATA", "PROBE_2"))
        self.assertIsNone(self.plan([self.meta(None), self.meta(None, "PROBE_2")]))
        self.key["expansion_probe_timestamps"] = ["20190906095959", "20190906095959"]
        self.assertIsNone(self.plan([self.meta(None)]), "a capped probe 2 equal to probe 1 is never asked")
        self.assertIsNone(self.plan([self.meta("20190920000000"), self.replay("20190920000000")]))

    def test_transient_retries_and_redirect_hops_stay_inside_the_per_key_budget(self) -> None:
        busy = self.meta(None, status=503)
        busy["outcome"] = "RESPONSE"
        self.assertEqual(self.plan([busy])[:2], ("METADATA", "RETRY"))
        self.assertEqual(self.plan([busy, self.meta("20190920000000", "RETRY")])[:2], ("REPLAY", "CAPTURE_1"))
        self.assertIsNone(self.plan([busy, self.meta("20190920000000", "RETRY"), self.replay("20190920000000")]),
                          "a metadata retry closes probe 2")
        hop = self.replay("20190903000000", 302, f"https://web.archive.org/web/20190903010000id_/"
                                                 f"{apfx.game_url('901')}")
        step = self.plan([self.meta("20190903000000"), hop])
        self.assertEqual(step[:2], ("REPLAY", "REDIRECT_HOP"))
        # a redirect onto a retained version (or off the archive host) is not followed: the replay did not answer 200,
        # so probe 2 may be asked once; the retained version itself is never replayed again
        onto_retained = self.plan([self.meta("20190903000000"), hop], frozenset({"20190903010000"}))
        self.assertEqual(onto_retained[:2], ("METADATA", "PROBE_2"))
        retained_answer = [self.meta("20190903000000"), hop, self.meta("20190903010000", "PROBE_2")]
        self.assertIsNone(self.plan(retained_answer, frozenset({"20190903010000"})))
        away = self.replay("20190903000000", 302, "https://www.espn.com/college-football/game/_/gameId/901")
        self.assertEqual(self.plan([self.meta("20190903000000"), away])[:2], ("METADATA", "PROBE_2"))
        exhausted = [self.meta("20190903000000"), away, self.meta("20190905000000", "PROBE_2")]
        self.assertEqual(self.plan(exhausted)[:2], ("REPLAY", "CAPTURE_2"))
        self.assertIsNone(self.plan(exhausted + [self.replay("20190905000000", 503)]),
                          "a second replay exhausts the per-key replay budget: no retry")

    def test_body_limit_fails_closed_as_a_counted_network_error(self) -> None:
        class Stream(io.BytesIO):
            status, reason, headers = 200, "OK", {}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        class Opener:
            def open(self, request, timeout):
                return Stream(b"x" * 11)
        original = self.b.urllib.request.build_opener
        self.b.urllib.request.build_opener = lambda *a: Opener()
        try:
            over = self.b.urllib_transport("https://archive.org/wayback/available?x", {}, 1.0, max_bytes=10)
            ok = self.b.urllib_transport("https://archive.org/wayback/available?x", {}, 1.0, max_bytes=11)
        finally:
            self.b.urllib.request.build_opener = original
        self.assertIsNone(over.status)
        self.assertTrue(over.error.startswith("BODY_LIMIT_EXCEEDED"))
        self.assertEqual((ok.status, ok.body), (200, b"x" * 11))


class CaptureAndBuildTests(unittest.TestCase):
    def test_retained_import_is_byte_identical_and_costs_zero_requests(self) -> None:
        world, capture = STATE["world"], STATE["capture"]
        self.assertEqual(capture["retained_import"]["new_requests"], 0)
        for path in Path(world["out"]).rglob("*"):
            rel = path.relative_to(world["out"])
            if path.is_file() and rel.parts[0] in ("raw", "acquisition") and "network_audit" not in path.name:
                twin = Path(world["x_out"]) / rel
                if twin.exists():
                    self.assertEqual(twin.read_bytes(), path.read_bytes(), rel)
        retained = Path(world["x_out"]) / "acquisition" / "sha256" / world["retained"]["acquisition_identity"]
        self.assertTrue((retained / "acquisition.json").is_file())

    def test_expansion_acquisition_requests_are_exactly_the_planned_ones(self) -> None:
        capture = STATE["capture"]
        self.assertEqual(capture["state"], "FINALIZED")
        self.assertEqual(capture["outcomes"], {"ncaa:1002": "RETAINED_VERSION_REUSED", "ncaa:1004": "CAPTURED",
                                               "ncaa:1005": "NO_ARCHIVE_CAPTURE_REPORTED", "ncaa:1007": "CAPTURED"})
        self.assertEqual(capture["totals"]["requests"], 9)
        self.assertEqual(capture["totals"]["limit"], 320)
        doc = json.loads(xfx.expansion_acquisition(STATE["world"]).read_text(encoding="utf-8"))
        starts = [dt.datetime.strptime(r["started_utc"], "%Y-%m-%dT%H:%M:%S.%fZ") for r in doc["requests"]]
        gaps = [(b - a).total_seconds() for a, b in zip(starts, starts[1:])]
        self.assertTrue(gaps and all(g >= 1.05 for g in gaps), gaps)
        self.assertEqual([(r["contest_key"], r["purpose"]) for r in doc["requests"]],
                         [("ncaa:1002", "PROBE_1"), ("ncaa:1004", "PROBE_1"), ("ncaa:1004", "CAPTURE_1"),
                          ("ncaa:1005", "PROBE_1"), ("ncaa:1005", "PROBE_2"), ("ncaa:1007", "PROBE_1"),
                          ("ncaa:1007", "CAPTURE_1"), ("ncaa:1007", "PROBE_2"), ("ncaa:1007", "CAPTURE_2")])
        rerun = xfx.run_capture(STATE["world"])
        self.assertEqual((rerun["state"], rerun["new_requests"]), ("ALREADY_FINALIZED", 0))

    def test_union_payloads_keep_every_key_request_and_version(self) -> None:
        world = STATE["world"]
        dispositions = payload("dispositions.jsonl")
        self.assertEqual([d["contest_key"] for d in dispositions], world["union"])
        by = {d["contest_key"]: d for d in dispositions}
        self.assertEqual(by["ncaa:1002"]["selection_sources"], ["TRANCHE_28", "COHORT_70"])
        self.assertEqual([o["acquisition_outcome"] for o in by["ncaa:1002"]["acquisition_outcomes"]],
                         ["CAPTURED", "RETAINED_VERSION_REUSED"])
        self.assertEqual(by["ncaa:1004"]["selection_role"], af.COHORT_ROLE)
        self.assertIsNone(by["ncaa:1004"]["classification_pair"])
        self.assertEqual(by["ncaa:1004"]["season"], 2019)
        self.assertEqual(by["ncaa:1005"]["disposition"], "NO_ARCHIVE_CAPTURE_REPORTED")
        self.assertEqual([o["acquisition_outcome"] for o in by["ncaa:1005"]["acquisition_outcomes"]],
                         ["NO_ARCHIVE_CAPTURE_REPORTED", "NO_ARCHIVE_CAPTURE_REPORTED"])
        self.assertEqual(by["ncaa:1007"]["disposition"], "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS")
        self.assertEqual(len(by["ncaa:1007"]["capture_ids"]), 2)
        requests = payload("requests.jsonl")
        self.assertEqual(len(requests), len(world["retained_doc"]["requests"]) + 9)
        self.assertEqual(len({(r["acquisition_identity"], r["seq"]) for r in requests}), len(requests))
        overlap = [r for r in requests if r["contest_key"] == "ncaa:1002"]
        self.assertEqual([r["acquisition_identity"] for r in overlap][-1],
                         xfx.expansion_acquisition(world).parent.name)
        retained_caps = [c for c in payload("captures.jsonl") if c["contest_key"] == "ncaa:1002"]
        self.assertEqual(len(retained_caps), 2, "the retained versions stay; none is duplicated")
        self.assertTrue(all(d["duplicate_versions"] == [] for d in dispositions))

    def test_variants_reproduce_the_canonical_identities(self) -> None:
        world, ref = STATE["world"], STATE["result"]
        base = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))
        acq = xfx.expansion_acquisition(world)
        common = ["--evidence-root", str(world["x_out"]), "--acquisition", str(acq)]
        for i, extra in enumerate((["--input-order", "reverse"], ["--input-order", "shuffle:17"],
                                   ["--chunk-size", "3", "--checkpoint-dir", str(base / "c3")])):
            code, got, err = xfx.run_build(world, *common, *extra, out=base / f"o{i}", manifests=base / f"m{i}")
            self.assertEqual(code, 0, err)
            self.assertEqual((got["content_identity"], got["database_identity"]),
                             (ref["content_identity"], ref["database_identity"]))
        code, got, err = xfx.run_build(world, *common, "--chunk-size", "1", "--checkpoint-dir", str(base / "ir"),
                                       "--stop-after-chunks", "4", out=base / "oi", manifests=base / "mi")
        self.assertEqual((code, got["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"), err)
        code, got, err = xfx.run_build(world, *common, "--chunk-size", "1", "--checkpoint-dir", str(base / "ir"),
                                       "--resume", out=base / "oi", manifests=base / "mi")
        self.assertEqual(code, 0, err)
        self.assertEqual(got["database_identity"], ref["database_identity"])

    def test_scope_binding_and_policy_refusals(self) -> None:
        world = STATE["world"]
        base = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))

        def patched(name: str, mutate) -> Path:
            doc = copy.deepcopy(world["x_contract_doc"])
            mutate(doc)
            return apfx.write(base / name, (json.dumps(doc, indent=1) + "\n").encode("utf-8"))
        cases = {
            "ACQUISITION_POLICY_INVALID": patched("a.json", lambda d: d["acquisition"]["limits"].update(
                total_requests=321)),
            "SCOPE_KEYS_INVALID": patched("b.json", lambda d: d["scope"]["keys"][-1].update(
                expansion_probe_timestamps=["20190101000000", "20190101000000"])),
            "AUTHORITY_LABELS_INVALID": patched("c.json", lambda d: d["row_labels"].update(scope="NATIONAL")),
            "FORGED_PIT_AUTHORITY": patched("d.json", lambda d: d["authority"].update(pit_admission="ADMITTED")),
        }
        spacing = patched("e.json", lambda d: d["acquisition"]["limits"].update(min_seconds_between_request_starts=1.0))
        cases_list = list(cases.items()) + [("ACQUISITION_POLICY_INVALID", spacing)]
        for code_expected, contract in cases_list:
            code, _got, err = xfx.run_build(world, contract=contract, out=base / "z", manifests=base / "zm")
            self.assertEqual((code, apfx.refusal(err)), (2, code_expected), err[-300:])
        other = apfx.write(base / "cohort.json", Path(world["cohort"]).read_bytes() + b" ")
        code, _got, err = xfx.run_build(world, cohort=other, out=base / "z", manifests=base / "zm")
        self.assertEqual((code, apfx.refusal(err)), (2, "COHORT_MISMATCH"))
        code, _got, err = xfx.run_build(world, bindings=world["bindings"], out=base / "z", manifests=base / "zm")
        self.assertEqual((code, apfx.refusal(err)), (2, "SOURCE_BINDINGS_MISMATCH"))

    def test_altered_retained_acquisition_refuses_before_any_request(self) -> None:
        world = STATE["world"]
        base = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))
        fake_root = base / "v12"
        shutil.copytree(world["out"], fake_root)
        doc = next(fake_root.glob("acquisition/sha256/*/acquisition.json"))
        doc.write_bytes(doc.read_bytes().replace(b'"CAPTURED"', b'"CAPTURED "', 1))
        build = xfx.builder()
        contract, _ = build.load_expansion_contract(world["x_contract"])
        with self.assertRaises(build.BuildRefused) as caught:
            build.import_retained(contract, fake_root, base / "out")
        self.assertEqual(caught.exception.code, "RETAINED_ACQUISITION_ALTERED")
        self.assertFalse((base / "out").exists())


class ConsumerTests(unittest.TestCase):
    def test_explicit_successor_serves_the_union_and_v12_default_is_unchanged(self) -> None:
        code, doc, err = query("--grain", "archive-disposition", "--all")
        self.assertEqual(code, 0, err)
        self.assertEqual([r["contest_key"] for r in doc["rows"]], STATE["world"]["union"])
        self.assertEqual(doc["scope"], arch.EXPANSION_ROW_LABELS["scope"])
        self.assertEqual(doc["archive_evidence"]["union_keys"], len(STATE["world"]["union"]))
        self.assertIsNone(arch.ISSUED_EXPANSION, "nothing is packaged before the real acquisition is issued")
        code, doc, err = query("--grain", "contest", "--contest", "ncaa:1004", "--cutoff", "2019-09-13T09:59:59Z")
        self.assertEqual(code, 0, err)
        fields = doc["rows"][0]["fields"]
        self.assertEqual(fields["a_points"]["archive"]["historically_published_by_cutoff"], "TRUE")
        code, doc, err = query("--grain", "contest", "--contest", "ncaa:1004", "--cutoff", "2019-09-10T02:00:00Z")
        self.assertEqual(doc["rows"][0]["fields"]["a_points"]["archive"]["historically_published_by_cutoff"],
                         "UNKNOWN", "a cutoff before the version's upper bound is not supported")
        code, _doc, err = query("--grain", "archive-disposition", "--require-pit")
        self.assertEqual((code, apfx.refusal(err)), (2, "PIT_ADMISSION_AUTHORITY_ABSENT"))

    def test_unregistered_successor_is_not_served(self) -> None:
        STATE["stack"].close()
        try:
            code, _doc, err = query("--grain", "archive-disposition")
            self.assertEqual((code, apfx.refusal(err)), (2, "ARCHIVE_CONTRACT_NOT_ISSUED"))
        finally:
            STATE["stack"] = contextlib.ExitStack()
            STATE["stack"].enter_context(arch.registered_authority(xfx.issued_authority(STATE["world"])))

    def rehoused(self, **kwargs) -> Path:
        return xfx.rehouse(STATE["world"], STATE["result"], Path(tempfile.mkdtemp(dir=STATE["tmp"].name)), **kwargs)

    def refuse(self, code: str, sidecar: Path) -> None:
        rc, _doc, err = query("--grain", "archive-disposition", sidecar=sidecar)
        self.assertEqual((rc, apfx.refusal(err)), (2, code), err[-500:])

    def test_genuine_rehoused_copy_opens(self) -> None:
        rc, _doc, err = query("--grain", "archive-disposition", sidecar=self.rehoused())
        self.assertEqual(rc, 0, err)

    def test_rehashed_union_forgeries_reach_their_rule(self) -> None:
        def disposition(key: str, **fields):
            return lambda t, r: ({**r, **fields} if t == "dispositions" and r and r["contest_key"] == key else None)
        expansion_id = xfx.expansion_acquisition(STATE["world"]).parent.name
        retained_id = STATE["world"]["retained"]["acquisition_identity"]
        cases = {
            "ARCHIVE_DISPOSITION_TRANCHE_MISMATCH": disposition("ncaa:1004", selection_sources=["TRANCHE_28"]),
            "ARCHIVE_RECEIPT_ALTERED": disposition("ncaa:1002", acquisition_outcomes=[
                {"acquisition_identity": retained_id, "acquisition_outcome": "CAPTURED"}]),
            "ARCHIVE_DISPOSITION_PARENT_MISMATCH": disposition("ncaa:1004", season=2018),
        }
        for code, mutate in cases.items():
            self.refuse(code, self.rehoused(mutate_rows=mutate))
        swap = (lambda t, r: {**r, "acquisition_identity": retained_id}
                if t == "requests" and r and r["acquisition_identity"] == expansion_id and r["seq"] == 1 else None)
        self.refuse("ARCHIVE_RECEIPT_ALTERED", self.rehoused(mutate_rows=swap))
        drop = (lambda t, r: "DELETE" if t == "captures" and r and r["contest_key"] == "ncaa:1007" else None)
        self.refuse("ARCHIVE_CAPTURE_COLLECTION_MISMATCH", self.rehoused(mutate_rows=drop))
        omit = (lambda t, r: "DELETE" if t == "requests" and r and r["contest_key"] == "ncaa:1005" else None)
        self.refuse("ARCHIVE_RECEIPT_ALTERED", self.rehoused(mutate_rows=omit))
        self.refuse("ARCHIVE_TRANCHE_NOT_ISSUED", self.rehoused(mutate_meta={"cohort_sha256": "0" * 64}))
        acqs = json.dumps([{"acquisition_identity": expansion_id, "policy_id": "x", "origin": "EXPANSION"}])
        self.refuse("ARCHIVE_ACQUISITION_NOT_ISSUED", self.rehoused(mutate_meta={"acquisitions": acqs}))

    def test_altered_retained_copy_and_raw_refuse(self) -> None:
        retained_id = STATE["world"]["retained"]["acquisition_identity"]

        def alter_doc(root: Path) -> None:
            path = root / "acquisition" / "sha256" / retained_id / "acquisition.json"
            path.write_bytes(path.read_bytes() + b" ")
        self.refuse("ARCHIVE_RECEIPT_ALTERED", self.rehoused(mutate_raw=alter_doc))
        body = next(r["body_sha256"] for r in STATE["world"]["retained_doc"]["requests"] if r["body_sha256"])

        def alter_raw(root: Path) -> None:
            path = root / "raw" / "sha256" / body
            path.write_bytes(path.read_bytes() + b" ")
        self.refuse("ARCHIVE_RAW_ALTERED", self.rehoused(mutate_raw=alter_raw))


class PackagingTests(unittest.TestCase):
    def test_the_exact_issued_cohort_bytes_are_packaged_and_declared(self) -> None:
        import hashlib  # noqa: PLC0415
        import tomllib  # noqa: PLC0415
        contract = json.loads(xfx.EXPANSION_CONTRACT_PATH.read_text(encoding="utf-8"))
        packaged = Path(arch.__file__).with_name(arch.ISSUED_COHORT_FILE)
        self.assertEqual(hashlib.sha256(packaged.read_bytes()).hexdigest(), contract["scope"]["cohort_sha256"])
        package_data = tomllib.loads((xfx.ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"][
            "package-data"]["aggie_analytics.national_source_time"]
        self.assertIn(arch.ISSUED_COHORT_FILE, package_data)
        self.assertIn(arch.ISSUED_TRANCHE_FILE, package_data)
        self.assertEqual(contract["row_labels"], arch.EXPANSION_ROW_LABELS)
        self.assertEqual(contract["contract_id"], arch.EXPANSION_CONTRACT_IDS[0])
        self.assertEqual(contract["scope"]["union_count"], 97)
        self.assertEqual(len(contract["scope"]["keys"]), 97)


class DuplicateRuleTests(unittest.TestCase):
    def test_a_second_receipt_of_the_same_version_is_listed_not_duplicated(self) -> None:
        url = f"https://web.archive.org/web/20190903000000id_/{apfx.game_url('901')}"
        request = {"seq": 1, "contest_key": "k", "kind": "REPLAY", "http_status": 200, "url": url,
                   "headers": [], "started_utc": "a", "ended_utc": "b", "body_sha256": "s"}
        docs = [("A" * 64, {"requests": [request]}), ("B" * 64, {"requests": [dict(request, seq=4)]})]
        entries, dups = af.expansion_versions("k", None, docs, lambda sha: b"page")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"]["receipt_document_sha256"], "A" * 64)
        self.assertEqual([(d["receipt_document_sha256"], d["request_seq"]) for d in dups], [("B" * 64, 4)])


if __name__ == "__main__":
    unittest.main()
