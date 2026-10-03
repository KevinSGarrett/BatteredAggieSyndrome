"""BAT-713 explicit archive evidence in the installed source-time query (Cycle #41 TP41-A01).

The source-time database and the archive sidecar come from the synthetic worlds of ``national_source_time_fixture``
and ``national_archived_publication_fixture`` (fictional records only).
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_archived_publication_fixture as fx  # noqa: E402
from aggie_analytics.national_source_time import query as q  # noqa: E402

STATE: dict = {}
QUAL = "QUALIFIED_AGREES_WITH_PARENT"


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    world = fx.build_world(Path(STATE["tmp"].name) / "g")
    fx.run_capture(world)
    code, result, err = fx.run_build(world)
    assert code == 0, err
    STATE.update(world=world, result=result, sidecar=fx.database_path(result))


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def run(*argv: str, sidecar: Path | None = None, archive: bool = True) -> tuple[int, dict | None, str]:
    args = ["--database", str(STATE["world"]["st_db"]), *argv]
    if archive:
        args += ["--archive-evidence", str(sidecar or STATE["sidecar"])]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = q.main(args)
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    return code, (json.loads(text) if text.strip() else None), err.getvalue()


def refusal(err: str) -> str | None:
    return fx.refusal(err)


def fields(contest: str, cutoff: str) -> dict:
    code, doc, err = run("--grain", "contest", "--contest", contest, "--cutoff", cutoff)
    assert code == 0, err
    return doc["rows"][0]["fields"]


class CompositionTests(unittest.TestCase):
    def test_precision_boundary_and_zone_equivalent_cutoffs(self) -> None:
        bound = "2019-09-01T04:15:00.999999Z"
        before = fields("ncaa:1001", "2019-09-01T04:15:00.999998Z")
        at = fields("ncaa:1001", bound)
        zoned = fields("ncaa:1001", "2019-08-31T23:15:00.999999-05:00")
        whole_second = fields("ncaa:1001", "2019-09-01T04:15:00Z")
        for field in ("contest_date", "a_participant", "completion", "b_points"):
            self.assertEqual(before[field]["archive"]["historically_published_by_cutoff"], "UNKNOWN", field)
            self.assertEqual(whole_second[field]["archive"]["historically_published_by_cutoff"], "UNKNOWN", field)
            self.assertEqual(at[field]["archive"]["historically_published_by_cutoff"], "TRUE", field)
            self.assertEqual(zoned[field]["archive"], at[field]["archive"], field)
            self.assertEqual(at[field]["historically_published_by_cutoff_with_archive"], "TRUE", field)
            self.assertEqual(at[field]["archive"]["earliest_qualified_upper_bound_utc"], bound)

    def test_original_decisions_and_2026_clocks_are_kept_untouched(self) -> None:
        cutoff = "2019-09-02T00:00:00Z"
        code, plain, err = run("--grain", "contest", "--contest", "ncaa:1001", "--cutoff", cutoff, archive=False)
        self.assertEqual(code, 0, err)
        archived = fields("ncaa:1001", cutoff)
        for field, value in plain["rows"][0]["fields"].items():
            self.assertEqual({k: v for k, v in archived[field].items()
                              if k not in ("archive", "historically_published_by_cutoff_with_archive")}, value)
            self.assertEqual(value["observed_by_cutoff"], "UNKNOWN")
            self.assertEqual(archived[field]["historically_published_by_cutoff_with_archive"],
                             "UNKNOWN" if field == "season" else "TRUE")

    def test_outcomes_before_the_event_stay_false_and_identity_unknown(self) -> None:
        early = fields("ncaa:1001", "2019-08-01T00:00:00Z")
        for field in ("completion", "a_points", "b_points"):
            self.assertEqual(early[field]["archive"]["historically_published_by_cutoff"], "FALSE")
            self.assertEqual(early[field]["historically_published_by_cutoff_with_archive"], "FALSE")
        for field in ("contest_date", "a_participant"):
            self.assertEqual(early[field]["historically_published_by_cutoff_with_archive"], "UNKNOWN")

    def test_each_version_supports_only_what_it_witnesses(self) -> None:
        between = fields("ncaa:1002", "2019-09-01T00:00:00Z")
        self.assertEqual(between["a_participant"]["archive"]["historically_published_by_cutoff"], "TRUE")
        self.assertEqual(between["a_points"]["archive"]["historically_published_by_cutoff"], "UNKNOWN")
        later = fields("ncaa:1002", "2019-09-02T10:00:00.999999Z")
        self.assertEqual(later["a_points"]["archive"]["historically_published_by_cutoff"], "TRUE")

    def test_partial_and_missing_routes_stay_honest(self) -> None:
        partial = fields("ncaa:1004", "2026-10-02T00:00:00Z")
        self.assertEqual(partial["contest_date"]["archive"]["historically_published_by_cutoff"], "TRUE")
        self.assertEqual(partial["a_participant"]["archive"]["historically_published_by_cutoff"],
                         "NO_QUALIFIED_ARCHIVE_ASSERTION")
        missing = fields("ncaa:1005", "2026-10-02T00:00:00Z")
        self.assertTrue(all(v["archive"]["historically_published_by_cutoff"] == "NO_QUALIFIED_ARCHIVE_ASSERTION"
                            for v in missing.values()))
        code, doc, _err = run("--grain", "contest", "--contest", "ncaa:1005", "--cutoff", "2026-10-02T00:00:00Z")
        self.assertEqual(doc["rows"][0]["archive_disposition"], "NO_ARCHIVE_CAPTURE_REPORTED")
        outside = fields("ncaa:2001", "2026-10-02T00:00:00Z")
        self.assertTrue(all(not v["archive"]["in_archive_tranche"] for v in outside.values()))

    def test_contribution_composes_contributor_fields_only_with_the_option(self) -> None:
        code, doc, err = run("--grain", "contribution", "--season", "2019", "--cutoff", "2026-10-02T00:00:00Z",
                             "--all")
        self.assertEqual(code, 0, err)
        rows = [r for r in doc["rows"] if r["relation"]["contributor_contest_key"] == "ncaa:1001"]
        self.assertTrue(rows)
        for row in rows:
            for field, value in row["required_field_decisions"].items():
                self.assertIn(value["archive_published_by_cutoff"], ("TRUE", "NO_QUALIFIED_ARCHIVE_ASSERTION"))
            self.assertEqual(row["pit_admission"]["state"], "NOT_ADMITTED")
        code, plain, err = run("--grain", "contribution", "--season", "2019", "--cutoff", "2026-10-02T00:00:00Z",
                               "--all", archive=False)
        self.assertNotIn("archive_evidence", plain)
        self.assertNotIn("inputs_published_by_cutoff_with_archive", plain["rows"][0])

    def test_default_output_is_exactly_the_source_time_consumer(self) -> None:
        db = q.SourceTimeDatabase(STATE["world"]["st_db"])
        try:
            for grain in q.GRAINS:
                extra = ["--cutoff", "2019-09-20T00:00:00Z"] if grain in q.DECISION_GRAINS else []
                code, doc, err = run("--grain", grain, "--all", *extra, archive=False)
                self.assertEqual(code, 0, err)
                expected = db.query(grain, cutoff=extra[1] if extra else None, all_rows=True)
                self.assertEqual(json.dumps(doc, sort_keys=True), json.dumps(expected, sort_keys=True), grain)
                code, composed, err = run("--grain", grain, "--all", *extra)
                self.assertEqual(code, 0, err)
                self.assertEqual(composed["total"], doc["total"], grain)
                if grain not in ("contest", "contribution"):
                    self.assertEqual(composed["rows"], doc["rows"], grain)
        finally:
            db.close()

    def test_require_pit_and_archive_grains_without_the_option_refuse(self) -> None:
        code, _doc, err = run("--grain", "contest", "--cutoff", "2026-10-02T00:00:00Z", "--require-pit")
        self.assertEqual((code, refusal(err)), (2, "PIT_ADMISSION_AUTHORITY_ABSENT"))
        for grain in q.ARCHIVE_GRAINS:
            code, _doc, err = run("--grain", grain, "--cutoff", "2026-10-02T00:00:00Z", archive=False)
            self.assertEqual((code, refusal(err)), (2, "ARCHIVE_EVIDENCE_REQUIRED"), grain)
        code, _doc, err = run("--grain", "partition", "--expect-archive-identity", "0" * 64, archive=False)
        self.assertEqual(refusal(err), "ARCHIVE_EVIDENCE_REQUIRED")


class ModuleFrontTests(unittest.TestCase):
    """``python -m`` runs the query file as __main__; refusals raised by the archive module must still be refusals."""

    def module(self, *argv: str) -> tuple[int, str, str]:
        import os  # noqa: PLC0415
        import subprocess  # noqa: PLC0415
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(fx.ROOT / "src")] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH")
                                                                     else []))
        proc = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.national_source_time.query", "--database",
                               str(STATE["world"]["st_db"]), *argv], capture_output=True, text=True,
                              encoding="utf-8", env=env, check=False)
        return proc.returncode, proc.stdout, proc.stderr

    def test_archive_and_cutoff_refusals_exit_two_at_the_module_front(self) -> None:
        for argv, code in ((["--archive-evidence", str(STATE["sidecar"]), "--expect-archive-identity", "0" * 64,
                             "--grain", "archive-disposition"], "STALE_ARCHIVE_IDENTITY"),
                           (["--archive-evidence", str(STATE["sidecar"]), "--grain", "archive-assertion"],
                            "CUTOFF_REQUIRED"),
                           (["--grain", "archive-request"], "ARCHIVE_EVIDENCE_REQUIRED")):
            rc, _out, err = self.module(*argv)
            self.assertEqual((rc, refusal(err)), (2, code), err[-300:])
            self.assertNotIn("Traceback", err)

    def test_module_front_composes_and_keeps_default_output(self) -> None:
        rc, out, err = self.module("--archive-evidence", str(STATE["sidecar"]), "--grain", "archive-disposition",
                                   "--all")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["total"], len(fx.TRANCHE))
        rc, out, err = self.module("--grain", "partition", "--all")
        code, doc, _err = run("--grain", "partition", "--all", archive=False)
        self.assertEqual((rc, json.loads(out)), (code, doc))


class ArchiveGrainTests(unittest.TestCase):
    def test_dispositions_requests_captures_and_assertions_page_exactly(self) -> None:
        for grain, payload in (("archive-disposition", "dispositions.jsonl"), ("archive-request", "requests.jsonl"),
                               ("archive-capture", "captures.jsonl"), ("archive-assertion", "assertions.jsonl")):
            expected = fx.read_payload(STATE["result"], payload)
            seen, offset = [], 0
            while True:
                code, doc, err = run("--grain", grain, "--limit", "4", "--offset", str(offset), "--cutoff",
                                     "2026-10-02T00:00:00Z")
                self.assertEqual(code, 0, err)
                self.assertEqual(doc["total"], len(expected), grain)
                if not doc["rows"]:
                    break
                seen += [r["assertion"] if grain == "archive-assertion" else r for r in doc["rows"]]
                offset += 4
            self.assertEqual(seen, expected, grain)

    def test_filters_and_assertion_decisions(self) -> None:
        code, doc, err = run("--grain", "archive-assertion", "--contest", "ncaa:1001", "--field", "a_points",
                             "--cutoff", "2019-09-01T04:15:00.999999Z")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(doc["rows"]), 1)
        decision = doc["rows"][0]["decision"]
        self.assertEqual((decision["historically_published_by_cutoff"], decision["observed_by_cutoff"],
                          decision["pit_admission"]["state"]), ("TRUE", "FALSE", "NOT_ADMITTED"))
        code, doc, err = run("--grain", "archive-disposition", "--team", "org:3")
        self.assertEqual({r["contest_key"] for r in doc["rows"]}, {"ncaa:1002", "ncaa:1004", "ncaa:1005"})
        code, _doc, err = run("--grain", "archive-assertion", "--contest", "ncaa:1001")
        self.assertEqual(refusal(err), "CUTOFF_REQUIRED")
        code, _doc, err = run("--grain", "archive-capture", "--field", "a_points")
        self.assertEqual(refusal(err), "FILTER_NOT_APPLICABLE")
        code, _doc, err = run("--grain", "archive-request", "--offset", "-1")
        self.assertEqual(refusal(err), "NEGATIVE_OFFSET")


def rehouse(base: Path, mutate_rows=None, mutate_meta=None, mutate_raw=None) -> Path:
    """Copy the archive root, apply a tamper to the sidecar records/meta/raw store and recompute every outer hash so
    that only semantic verification can catch it. Returns the new sidecar path."""
    root = base / "canonical" / "ap"
    shutil.copytree(STATE["world"]["out"], root)
    (base / "manifests").mkdir(parents=True)
    shutil.copytree(STATE["world"]["manifests"], base / "manifests" / "ap")
    db_id = STATE["result"]["database_identity"]
    source = root / "sha256" / db_id / "national_archived_publication.sqlite"
    work = base / "work.sqlite"
    shutil.copyfile(source, work)
    conn = sqlite3.connect(work)
    if mutate_rows:
        for table in ("dispositions", "requests", "captures", "assertions"):
            rows = [(o, json.loads(r)) for o, r in conn.execute(f"SELECT ord, record FROM {table} ORDER BY ord")]
            for ordinal, record in rows:
                changed = mutate_rows(table, record)
                if changed is not None:
                    conn.execute(f"UPDATE {table} SET record = ? WHERE ord = ?",
                                 (json.dumps(changed, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                                  ordinal))
            extra = mutate_rows(table, None)
            if extra is not None:
                columns = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
                last = conn.execute(f"SELECT * FROM {table} ORDER BY ord DESC LIMIT 1").fetchone()
                values = dict(zip(columns, last))
                values.update({c: extra[c] for c in columns if c in extra and c not in ("ord", "record")})
                values.update(ord=values["ord"] + 1, record=json.dumps(extra, sort_keys=True, separators=(",", ":")))
                if "span_start" in values:
                    values["span_start"] = -1
                conn.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' * len(columns))})",
                             [values[c] for c in columns])
    if mutate_meta:
        for key, value in mutate_meta.items():
            conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("meta", "dispositions", "requests", "captures", "assertions")}
    conn.close()
    if mutate_raw:
        mutate_raw(root)
    manifest = json.loads((base / "manifests" / "ap" / "sha256" / db_id / "run_manifest.json").read_text(
        encoding="utf-8"))
    document = manifest["identity_document"]
    document["outputs"]["national_archived_publication.sqlite"] = hashlib.sha256(work.read_bytes()).hexdigest()
    document["table_counts"] = counts
    document["record_counts"] = {name: counts[name.split(".")[0]] for name in document["record_counts"]}
    identity = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                              .encode("utf-8")).hexdigest()
    target = root / "sha256" / identity / "national_archived_publication.sqlite"
    if target.is_file():
        return target
    target.parent.mkdir(parents=True)
    shutil.move(str(work), target)
    fx.write(base / "manifests" / "ap" / "sha256" / identity / "run_manifest.json",
             json.dumps({"identity": identity, "identity_document": document}).encode("utf-8"))
    return target


class SidecarRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))

    def refuse(self, code: str, sidecar: Path, *extra: str) -> None:
        rc, _doc, err = run("--grain", "archive-disposition", *extra, sidecar=sidecar)
        self.assertEqual((rc, refusal(err)), (2, code), err[-400:])

    def test_genuine_rehoused_copy_opens(self) -> None:
        sidecar = rehouse(self.base)
        rc, doc, err = run("--grain", "archive-disposition", sidecar=sidecar)
        self.assertEqual(rc, 0, err)
        self.assertEqual(doc["archive_evidence"]["verification"], "SIDECAR_RAW_RECEIPT_AND_SEMANTIC_REDERIVATION_PASSED")

    def test_rehashed_semantic_forgeries_refuse(self) -> None:
        def points(table, record):
            if table == "assertions" and record and record["field"] == "b_points":
                return dict(record, value=record["value"] + 1, literal=str(record["value"] + 1))
            return None
        self.refuse("ARCHIVE_WITNESS_MISMATCH", rehouse(self.base / "a", points))

        def swap(table, record):
            if table == "assertions" and record and record["field"] in ("a_points", "b_points"):
                return dict(record, field="b_points" if record["field"] == "a_points" else "a_points")
            return None
        self.refuse("ARCHIVE_SEMANTIC_FORGERY", rehouse(self.base / "b", swap))

        def promote(table, record):
            if table == "captures" and record and "NOT_SUPPORTED_BY_VERSION_STATUS" in record["field_states"].values():
                states = {f: (QUAL if s == "NOT_SUPPORTED_BY_VERSION_STATUS" else s)
                          for f, s in record["field_states"].items()}
                return dict(record, field_states=states)
            return None
        self.refuse("ARCHIVE_SEMANTIC_FORGERY", rehouse(self.base / "c", promote))

    def test_forged_clock_and_backdated_probe_refuse(self) -> None:
        def backdate(table, record):
            if table == "captures" and record and record["state"] == "QUALIFIED":
                clocks = copy.deepcopy(record["clocks"])
                clocks["archive_capture"]["latest_utc"] = "2019-08-31T23:59:59.999999Z"
                return dict(record, clocks=clocks)
            return None
        self.refuse("ARCHIVE_CLOCK_FORGED", rehouse(self.base / "a", backdate))

        def relabel(table, record):
            if table == "captures" and record and record["origin"] == "WORKER_ARCHIVE_REPLAY":
                clocks = copy.deepcopy(record["clocks"])
                clocks["retrieval"]["latest_utc"] = "2019-09-02T00:00:00.000000Z"
                return dict(record, clocks=clocks)
            return None
        self.refuse("ARCHIVE_CLOCK_FORGED", rehouse(self.base / "b", relabel))

    def test_wrong_field_duplicate_and_out_of_tranche_rows_refuse(self) -> None:
        def season(table, record):
            if table == "assertions" and record and record["field"] == "contest_date":
                return dict(record, field="season")
            return None
        self.refuse("ARCHIVE_SOURCE_INVALID", rehouse(self.base / "a", season))
        first = fx.read_payload(STATE["result"], "assertions.jsonl")[0]

        def duplicate(table, record):
            return copy.deepcopy(first) if table == "assertions" and record is None else None
        self.refuse("ARCHIVE_DUPLICATE_ASSERTION", rehouse(self.base / "b", duplicate))
        capture = fx.read_payload(STATE["result"], "captures.jsonl")[0]

        def outside(table, record):
            if table == "captures" and record is None:
                return dict(copy.deepcopy(capture), contest_key="ncaa:9999", capture_id="wayback:x")
            return None
        self.refuse("ARCHIVE_SOURCE_INVALID", rehouse(self.base / "c", outside))

    def test_altered_raw_payload_and_receipt_refuse(self) -> None:
        sha = fx.read_payload(STATE["result"], "captures.jsonl")[0]["payload_sha256"]

        def alter(root):
            path = root / "raw" / "sha256" / sha
            path.write_bytes(path.read_bytes() + b" ")
        self.refuse("ARCHIVE_RAW_ALTERED", rehouse(self.base / "a", mutate_raw=alter))
        acquisition = next(STATE["world"]["out"].glob("acquisition/sha256/*/acquisition.json")).parent.name

        def alter_receipt(root):
            path = root / "acquisition" / "sha256" / acquisition / "acquisition.json"
            path.write_bytes(path.read_bytes().replace(b"PROBE_1", b"PROBE_2", 1))
        self.refuse("ARCHIVE_RECEIPT_ALTERED", rehouse(self.base / "b", mutate_raw=alter_receipt))

    def test_another_parent_unknown_schema_and_stale_identity_refuse(self) -> None:
        parent = json.loads(sqlite3.connect(STATE["sidecar"]).execute(
            "SELECT value FROM meta WHERE key = 'parent'").fetchone()[0])
        parent["source_time"]["database_identity"] = "e" * 64
        sidecar = rehouse(self.base / "a", mutate_meta={"parent": json.dumps(parent, sort_keys=True)})
        self.refuse("ARCHIVE_IDENTITY_MISMATCH", sidecar)
        self.refuse("ARCHIVE_SCHEMA_UNSUPPORTED", rehouse(self.base / "b", mutate_meta={
            "schema_version": "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-9"}))
        self.refuse("STALE_ARCHIVE_IDENTITY", STATE["sidecar"], "--expect-archive-identity", "0" * 64)

    def test_sidecar_over_another_parent_refuses(self) -> None:
        sidecar = rehouse(self.base / "a")
        manifest_path = next((self.base / "a" / "manifests" / "ap" / "sha256" / sidecar.parent.name).glob("*.json"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        document = manifest["identity_document"]
        document["parent"]["source_time"]["database_identity"] = "e" * 64
        conn = sqlite3.connect(sidecar)
        conn.execute("UPDATE meta SET value = ? WHERE key = 'parent'", (json.dumps(document["parent"],
                                                                                    sort_keys=True),))
        conn.commit()
        conn.close()
        document["outputs"]["national_archived_publication.sqlite"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
        identity = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                                  .encode("utf-8")).hexdigest()
        target = sidecar.parent.parent / identity / sidecar.name
        target.parent.mkdir()
        shutil.copyfile(sidecar, target)
        fx.write(manifest_path.parent.parent / identity / "run_manifest.json",
                 json.dumps({"identity": identity, "identity_document": document}).encode("utf-8"))
        self.refuse("ARCHIVE_PARENT_MISMATCH", target)

    def test_tampered_bytes_location_and_missing_manifest_refuse(self) -> None:
        sidecar = rehouse(self.base / "a")
        with sidecar.open("ab") as handle:
            handle.write(b"x")
        self.refuse("ARCHIVE_DATABASE_TAMPERED", sidecar)
        moved = self.base / "loose" / "national_archived_publication.sqlite"
        moved.parent.mkdir()
        shutil.copyfile(STATE["sidecar"], moved)
        self.refuse("ARCHIVE_LOCATION_INVALID", moved)
        orphan = self.base / "o" / "canonical" / "ap" / "sha256" / STATE["result"]["database_identity"] / moved.name
        orphan.parent.mkdir(parents=True)
        shutil.copyfile(STATE["sidecar"], orphan)
        self.refuse("ARCHIVE_MANIFEST_MISSING", orphan)

    def test_query_never_writes_the_sidecar(self) -> None:
        before = hashlib.sha256(STATE["sidecar"].read_bytes()).hexdigest()
        run("--grain", "contest", "--season", "2019", "--cutoff", "2026-10-02T00:00:00Z", "--all")
        self.assertEqual(hashlib.sha256(STATE["sidecar"].read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
