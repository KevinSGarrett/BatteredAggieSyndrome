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
from aggie_analytics.national_source_time import archive as arch  # noqa: E402
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
    # The synthetic world's contract, tranche and acquisition are its issued authority for in-process queries only.
    STATE["stack"] = contextlib.ExitStack()
    STATE["authority"] = STATE["stack"].enter_context(arch.registered_authority(fx.issued_authority(world)))


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["stack"].close()
    STATE["tmp"].cleanup()


def run(*argv: str, sidecar: Path | None = None, archive: bool = True,
        database: Path | None = None) -> tuple[int, dict | None, str]:
    args = ["--database", str(database or STATE["world"]["st_db"]), *argv]
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
        # Echo's page id 99105 differs from its CFBD id 105: mapped by documented names, CFBD role and date.
        self.assertEqual(partial["b_participant"]["archive"]["historically_published_by_cutoff"], "TRUE")
        self.assertEqual(partial["a_points"]["archive"]["historically_published_by_cutoff"],
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
    """``python -m`` runs the query file as __main__; refusals raised by the archive module must still be refusals.
    The real module front serves only the packaged issued authority, so the synthetic world's contract is refused
    there; the bootstrap registers the synthetic authority in its own process, then runs the module as __main__."""

    def module(self, *argv: str, bootstrap: bool = False) -> tuple[int, str, str]:
        import os  # noqa: PLC0415
        import subprocess  # noqa: PLC0415
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(fx.ROOT / "src")] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH")
                                                                     else []))
        front = ["-c", fx.BOOTSTRAP, fx.authority_spec(STATE["world"])] if bootstrap else \
            ["-m", "aggie_analytics.national_source_time.query"]
        proc = subprocess.run([sys.executable, "-B", *front, "--database", str(STATE["world"]["st_db"]), *argv],
                              capture_output=True, text=True, encoding="utf-8", env=env, check=False)
        return proc.returncode, proc.stdout, proc.stderr

    def test_archive_and_cutoff_refusals_exit_two_at_the_module_front(self) -> None:
        for argv, code, boot in ((["--archive-evidence", str(STATE["sidecar"]), "--expect-archive-identity", "0" * 64,
                                   "--grain", "archive-disposition"], "STALE_ARCHIVE_IDENTITY", False),
                                 (["--archive-evidence", str(STATE["sidecar"]), "--grain", "archive-disposition"],
                                  "ARCHIVE_CONTRACT_NOT_ISSUED", False),
                                 (["--archive-evidence", str(STATE["sidecar"]), "--grain", "archive-assertion"],
                                  "CUTOFF_REQUIRED", True),
                                 (["--grain", "archive-request"], "ARCHIVE_EVIDENCE_REQUIRED", False)):
            rc, _out, err = self.module(*argv, bootstrap=boot)
            self.assertEqual((rc, refusal(err)), (2, code), err[-300:])
            self.assertNotIn("Traceback", err)

    def test_module_front_composes_and_keeps_default_output(self) -> None:
        rc, out, err = self.module("--archive-evidence", str(STATE["sidecar"]), "--grain", "archive-disposition",
                                   "--all", bootstrap=True)
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


def rehouse(base: Path, mutate_rows=None, mutate_meta=None, mutate_raw=None, mutate_document=None, world=None,
            result=None, mutate_conn=None) -> Path:
    """Copy the archive root, apply a tamper to the sidecar records/meta/raw store and recompute every outer hash so
    that only semantic verification can catch it. ``mutate_rows`` may return "DELETE"; ``mutate_conn`` receives the
    open connection for multi-row edits (reorders, rebuilt tables). Returns the new sidecar path."""
    world, result = world or STATE["world"], result or STATE["result"]
    root = base / "canonical" / "ap"
    shutil.copytree(world["out"], root)
    (base / "manifests").mkdir(parents=True)
    shutil.copytree(world["manifests"], base / "manifests" / "ap")
    db_id = result["database_identity"]
    source = root / "sha256" / db_id / "national_archived_publication.sqlite"
    work = base / "work.sqlite"
    shutil.copyfile(source, work)
    conn = sqlite3.connect(work)
    if mutate_rows:
        for table in ("dispositions", "requests", "captures", "assertions"):
            rows = [(o, json.loads(r)) for o, r in conn.execute(f"SELECT ord, record FROM {table} ORDER BY ord")]
            for ordinal, record in rows:
                changed = mutate_rows(table, record)
                if changed == "DELETE":
                    conn.execute(f"DELETE FROM {table} WHERE ord = ?", (ordinal,))
                elif changed is not None:
                    conn.execute(f"UPDATE {table} SET record = ? WHERE ord = ?",
                                 (json.dumps(changed, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                                  ordinal))
            extra = mutate_rows(table, None)
            for item in ([extra] if isinstance(extra, dict) else extra or []):
                columns = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
                last = conn.execute(f"SELECT * FROM {table} ORDER BY ord DESC LIMIT 1").fetchone()
                values = dict(zip(columns, last))
                values.update({c: item[c] for c in columns if c in item and c not in ("ord", "record")})
                values.update(ord=values["ord"] + 1, record=json.dumps(item, sort_keys=True, separators=(",", ":")))
                if "span_start" in values:
                    values["span_start"] = item["witness_span"][0] if isinstance(extra, list) else -1
                conn.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' * len(columns))})",
                             [values[c] for c in columns])
    if mutate_meta:
        for key, value in mutate_meta.items():
            conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
    if mutate_conn:
        mutate_conn(conn)
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
    if mutate_document:
        mutate_document(document)
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
        self.assertEqual(doc["archive_evidence"]["verification"],
                         "SIDECAR_RAW_RECEIPT_FIELD_GRAIN_AND_PARTICIPANT_MAPPING_REDERIVATION_PASSED")

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

    def test_borrowed_and_same_element_witnesses_refuse(self) -> None:
        """MF41A01-01: a stored span must be an exact occurrence of its own witness, never a borrowed substring."""
        pre = next(c for c in fx.read_payload(STATE["result"], "captures.jsonl")
                   if c["page_status"]["js_status"] == "pre")
        raw = (STATE["world"]["out"] / "raw" / "sha256" / pre["payload_sha256"]).read_bytes()
        template = next(a for a in fx.read_payload(STATE["result"], "assertions.jsonl")
                        if a["capture_id"] == pre["capture_id"])

        def borrowed(table, record):
            if table == "assertions" and record is None:
                start = raw.find(b"Final")
                return [dict(copy.deepcopy(template), field="completion", witness="STATUS_DETAIL", literal="Final",
                             value="Final", witness_span=[start, start + 5], field_role="OUTCOME",
                             corroboration="AGREES_WITH_PARENT", field_state=QUAL, parent_comparator=None)]
            if table == "captures" and record and record["capture_id"] == pre["capture_id"]:
                return dict(record, field_states=dict(record["field_states"], completion=QUAL))
            return None
        self.refuse("ARCHIVE_WITNESS_MISMATCH", rehouse(self.base / "a", borrowed))
        final = next(c for c in fx.read_payload(STATE["result"], "captures.jsonl")
                     if c["contest_key"] == "ncaa:1001")
        fraw = (STATE["world"]["out"] / "raw" / "sha256" / final["payload_sha256"]).read_bytes()
        nav = next(s["span"] for s in final["main_element_spans"] if s["kind"] == "NAV")

        def same_element(table, record):
            if table == "assertions" and record and record["capture_id"] == final["capture_id"] \
                    and record["field"] == "b_points":
                pos = fraw.find(record["literal"].encode(), nav[0])
                while pos == record["witness_span"][0]:
                    pos = fraw.find(record["literal"].encode(), pos + 1)
                self.assertTrue(nav[0] <= pos < nav[1])
                return dict(record, witness_span=[pos, pos + len(record["literal"])])
            return None
        self.refuse("ARCHIVE_WITNESS_MISMATCH", rehouse(self.base / "b", same_element))

    def test_omitted_required_witness_refuses(self) -> None:
        def omit(table, record):
            if table == "assertions" and record and record["contest_key"] == "ncaa:1001" \
                    and record["witness"] == "STATUS_DETAIL":
                return "DELETE"
            return None
        self.refuse("ARCHIVE_WITNESS_SET_MISMATCH", rehouse(self.base / "a", omit))

    def test_participant_mapping_and_orientation_forgeries_refuse(self) -> None:
        """MF41A01-02: the stored map, orientation and participant states must equal the evidenced re-derivation."""
        def rename(table, record):
            if table == "captures" and record and record["contest_key"] == "ncaa:1001":
                mapping = copy.deepcopy(record["participant_mapping"])
                mapping["sides"]["home"]["documented_name"] = "Unrelated College"
                return dict(record, participant_mapping=mapping)
            return None
        self.refuse("ARCHIVE_PARTICIPANT_MAPPING_INVALID", rehouse(self.base / "a", rename))

        def flip(table, record):
            if table == "captures" and record and record["contest_key"] == "ncaa:1001":
                o = record["orientation"]
                return dict(record, orientation=dict(o, a_side=o["b_side"], b_side=o["a_side"]))
            return None
        self.refuse("ARCHIVE_PARTICIPANT_MAPPING_INVALID", rehouse(self.base / "b", flip))

        def demote(table, record):
            if table == "captures" and record and record["contest_key"] == "ncaa:1004":
                return dict(record, field_states=dict(record["field_states"],
                                                      b_participant="CAPTURE_NOT_QUALIFIED"))
            return None
        self.refuse("ARCHIVE_PARTICIPANT_MAPPING_INVALID", rehouse(self.base / "c", demote))

    def test_contradictory_maps_across_the_tranche_refuse(self) -> None:
        from unittest import mock  # noqa: PLC0415

        def alpha_renumbered(archive, row):
            away = fx.side_ids(row["_record"])[1]
            game = row["cfbd_game_id"]["value"]
            archive.meta[(game, row["metadata_probe_timestamp"])] = "20190901041500"
            archive.replay[("20190901041500", game)] = (
                200, fx.replay_headers("20190901041500", fx.game_url(game)), fx.page_for(row, ids=("777", away)))
        world = fx.build_world(self.base / "w", {"ncaa:1001": alpha_renumbered})
        fx.run_capture(world)
        build = fx.builder()
        with mock.patch.object(build.af, "mapping_conflicts", return_value=[]):
            code, result, err = fx.run_build(world)
        self.assertEqual(code, 0, err)
        with arch.registered_authority(fx.issued_authority(world)):
            rc, _doc, err = run("--grain", "archive-disposition", sidecar=fx.database_path(result),
                                database=world["st_db"])
        self.assertEqual((rc, refusal(err)), (2, "ARCHIVE_PARTICIPANT_MAPPING_CONTRADICTORY"), err[-300:])

    def test_unmapped_version_is_quarantined_whole_and_its_promotion_refuses(self) -> None:
        """Contract V1.2 capture_quarantine: real numbers with unrelated main-element names serve no field."""
        def unrelated(archive, row):
            game = row["cfbd_game_id"]["value"]
            archive.meta[(game, row["metadata_probe_timestamp"])] = "20190901041500"
            archive.replay[("20190901041500", game)] = (
                200, fx.replay_headers("20190901041500", fx.game_url(game)),
                fx.page_for(row, home_name="Unrelated College", away_name="Unrelated College"))
        world = fx.build_world(self.base / "w", {"ncaa:1001": unrelated})
        fx.run_capture(world)
        code, result, err = fx.run_build(world)
        self.assertEqual(code, 0, err)
        caps = [c for c in fx.read_payload(result, "captures.jsonl") if c["contest_key"] == "ncaa:1001"]
        self.assertTrue(caps)
        for cap in caps:
            self.assertEqual((cap["state"], cap["quarantine_reasons"]), ("QUARANTINED", ["PARTICIPANT_MAPPING_UNRESOLVED"]))
            self.assertEqual(cap["participant_mapping"]["reason"], "HOME_TEAM_NAME_NOT_DOCUMENTED_FOR_EITHER_PARENT_TEAM")
            self.assertTrue(all(v in ("CAPTURE_NOT_QUALIFIED", "NOT_WITNESSED_IN_VERSION")
                                for v in cap["field_states"].values()), cap["field_states"])
        with arch.registered_authority(fx.issued_authority(world)):
            rc, doc, err = run("--grain", "archive-disposition", "--contest", "ncaa:1001",
                               sidecar=fx.database_path(result), database=world["st_db"])
            self.assertEqual(rc, 0, err)
            self.assertEqual(doc["rows"][0]["disposition"], "ARCHIVED_VERSION_NOT_QUALIFIED")

            def promote(table, record):
                if table == "captures" and record and record["contest_key"] == "ncaa:1001":
                    return dict(record, state="QUALIFIED", quarantine_reasons=[],
                                field_states=dict(record["field_states"], contest_date=QUAL, completion=QUAL))
                return None
            rc, _doc, err = run("--grain", "archive-disposition", database=world["st_db"],
                                sidecar=rehouse(self.base / "p", promote, world=world, result=result))
            self.assertEqual((rc, refusal(err)), (2, "ARCHIVE_SEMANTIC_FORGERY"), err[-400:])
            # MF41A01-06: the quarantined version is part of the expected collection; omitting it refuses.
            quarantined = caps[0]["capture_id"]

            def omit(table, record):
                if record and record.get("capture_id") == quarantined and table in ("captures", "assertions"):
                    return "DELETE"
                if table == "dispositions" and record and record["contest_key"] == "ncaa:1001":
                    return dict(record, capture_ids=[], qualified_capture_ids=[],
                                disposition="ARCHIVED_VERSION_NOT_QUALIFIED", reasons=[])
                return None
            rc, _doc, err = run("--grain", "archive-disposition", database=world["st_db"],
                                sidecar=rehouse(self.base / "q", omit, world=world, result=result))
            self.assertEqual((rc, refusal(err)), (2, "ARCHIVE_CAPTURE_COLLECTION_MISMATCH"), err[-400:])

    def test_v1_1_sidecar_is_checked_then_refused_as_superseded(self) -> None:
        v1_1 = {"contract_id": "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.1"}
        self.refuse("ARCHIVE_SCHEMA_SUPERSEDED", rehouse(self.base / "a", mutate_meta=v1_1))
        final = next(c for c in fx.read_payload(STATE["result"], "captures.jsonl")
                     if c["contest_key"] == "ncaa:1001")

        def borrowed(table, record):
            if table == "assertions" and record and record["capture_id"] == final["capture_id"] \
                    and record["witness"] == "STATUS_DETAIL":
                return dict(record, witness_span=[0, 5], literal="<!DOC")
            return None
        self.refuse("ARCHIVE_WITNESS_MISMATCH", rehouse(self.base / "b", borrowed, mutate_meta=v1_1))

    def test_predecessor_v1_0_sidecar_is_checked_then_refused_as_superseded(self) -> None:
        def legacy_rows(table, record):
            if table == "assertions" and record and record["witness"].endswith("_TEAM_NAME"):
                return "DELETE"
            return None
        legacy_meta = {"schema_version": "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-1",
                       "contract_id": "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.0"}

        def legacy_document(document):
            document.update(schema="BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-1",
                            db_schema_version="BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-1")
        self.refuse("ARCHIVE_SCHEMA_SUPERSEDED", rehouse(self.base / "a", legacy_rows, mutate_meta=legacy_meta,
                                                         mutate_document=legacy_document))
        final = next(c for c in fx.read_payload(STATE["result"], "captures.jsonl")
                     if c["contest_key"] == "ncaa:1001")

        def legacy_borrowed(table, record):
            if table == "assertions" and record and record["capture_id"] == final["capture_id"] \
                    and record["witness"] == "STATUS_DETAIL":
                return dict(record, witness_span=[0, 5], literal="<!DOC")
            return legacy_rows(table, record)
        self.refuse("ARCHIVE_WITNESS_MISMATCH", rehouse(self.base / "b", legacy_borrowed, mutate_meta=legacy_meta,
                                                        mutate_document=legacy_document))

    def test_query_never_writes_the_sidecar(self) -> None:
        before = hashlib.sha256(STATE["sidecar"].read_bytes()).hexdigest()
        run("--grain", "contest", "--season", "2019", "--cutoff", "2026-10-02T00:00:00Z", "--all")
        self.assertEqual(hashlib.sha256(STATE["sidecar"].read_bytes()).hexdigest(), before)


def _swap_ords(conn: sqlite3.Connection, table: str, first: int, second: int) -> None:
    conn.execute(f"UPDATE {table} SET ord = -1 WHERE ord = ?", (first,))
    conn.execute(f"UPDATE {table} SET ord = ? WHERE ord = ?", (first, second))
    conn.execute(f"UPDATE {table} SET ord = ? WHERE ord = -1", (second,))


class RecordAuthorityTests(unittest.TestCase):
    """MF41A01-06: every served disposition and request field and the complete capture collection are bound to the
    issued tranche, the parent contest, the acquisition receipts and the retained raw bodies. Each rehashed,
    self-consistent sidecar below keeps every raw, receipt and parent byte and refuses for its own semantic cause."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(dir=STATE["tmp"].name))
        self.dispositions = {d["contest_key"]: d for d in fx.read_payload(STATE["result"], "dispositions.jsonl")}
        self.captures = fx.read_payload(STATE["result"], "captures.jsonl")
        self.requests = fx.read_payload(STATE["result"], "requests.jsonl")

    def refuse(self, code: str, sidecar: Path) -> None:
        rc, _doc, err = run("--grain", "archive-disposition", sidecar=sidecar)
        self.assertEqual((rc, refusal(err)), (2, code), err[-400:])

    @staticmethod
    def edit(table: str, pick, **fields):
        def mutate(name, record):
            if name == table and record and pick(record):
                return dict(record, **fields)
            return None
        return mutate

    def omit_captures(self, ids: set[str], key: str):
        """Delete versions and their assertions and make the key's disposition summary agree with what remains."""
        remaining = [c["capture_id"] for c in self.captures if c["contest_key"] == key and c["capture_id"] not in ids]

        def mutate(table, record):
            if record and table in ("captures", "assertions") and record["capture_id"] in ids:
                return "DELETE"
            if table == "dispositions" and record and record["contest_key"] == key:
                return dict(record, capture_ids=remaining, qualified_capture_ids=remaining)
            return None
        return mutate

    def test_genuine_rehoused_copy_reconstructs_every_record(self) -> None:
        sidecar = rehouse(self.base / "g")
        for grain, payload in (("archive-disposition", "dispositions.jsonl"), ("archive-request", "requests.jsonl"),
                               ("archive-capture", "captures.jsonl")):
            rc, doc, err = run("--grain", grain, "--all", sidecar=sidecar)
            self.assertEqual(rc, 0, err)
            self.assertEqual(doc["rows"], fx.read_payload(STATE["result"], payload), grain)

    def test_disposition_parent_fields_refuse(self) -> None:
        d = self.dispositions["ncaa:1001"]
        pick = lambda r: r["contest_key"] == "ncaa:1001"  # noqa: E731
        for name, fields in (("date", {"contest_date": "2025" + d["contest_date"][4:]}),
                             ("teams", {"a_key": d["b_key"], "b_key": d["a_key"]}), ("season", {"season": 2020}),
                             ("values", {"parent_values": dict(d["parent_values"],
                                                               a_points=d["parent_values"]["a_points"] + 1)})):
            self.refuse("ARCHIVE_DISPOSITION_PARENT_MISMATCH",
                        rehouse(self.base / name, self.edit("dispositions", pick, **fields)))

    def test_disposition_tranche_fields_refuse(self) -> None:
        pick = lambda r: r["contest_key"] == "ncaa:1001"  # noqa: E731
        for name, fields in (("classification", {"classification_pair": "FCS-FCS"}),
                             ("stratum", {"stratum": "FBS-FBS-LATE"}),
                             ("selection", {"selection_role": "SEPARATE_PREQUALIFIED_ROUTE_CONTROL"}),
                             ("locator", {"candidate_url": fx.game_url("990001")}),
                             ("game", {"game_id_literal": "990001"}), ("position", {"ord": 4})):
            self.refuse("ARCHIVE_DISPOSITION_TRANCHE_MISMATCH",
                        rehouse(self.base / name, self.edit("dispositions", pick, **fields)))

    def test_disposition_receipt_and_collection_summaries_refuse(self) -> None:
        pick = lambda r: r["contest_key"] == "ncaa:1001"  # noqa: E731
        self.refuse("ARCHIVE_RECEIPT_ALTERED", rehouse(self.base / "outcome", self.edit(
            "dispositions", pick, acquisition_outcome="NO_ARCHIVE_CAPTURE_REPORTED")))
        self.refuse("ARCHIVE_RECEIPT_ALTERED", rehouse(self.base / "count", self.edit(
            "dispositions", pick, request_count=self.dispositions["ncaa:1001"]["request_count"] + 1)))
        partial = next(k for k, d in self.dispositions.items() if d["disposition"] ==
                       "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS")
        self.refuse("ARCHIVE_SEMANTIC_FORGERY", rehouse(self.base / "overstated", self.edit(
            "dispositions", lambda r: r["contest_key"] == partial,
            disposition="ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS")))

    def test_missing_extra_duplicate_and_reordered_captures_refuse(self) -> None:
        by_key: dict[str, list[dict]] = {}
        for cap in self.captures:
            by_key.setdefault(cap["contest_key"], []).append(cap)
        self.assertEqual(len(by_key["ncaa:1002"]), 2)
        code = "ARCHIVE_CAPTURE_COLLECTION_MISMATCH"
        self.refuse(code, rehouse(self.base / "receipted", self.omit_captures(
            {by_key["ncaa:1001"][0]["capture_id"]}, "ncaa:1001")))
        self.refuse(code, rehouse(self.base / "later_version", self.omit_captures(
            {by_key["ncaa:1002"][1]["capture_id"]}, "ncaa:1002")))
        self.refuse(code, rehouse(self.base / "control", self.omit_captures(
            {by_key["ncaa:1003"][0]["capture_id"]}, "ncaa:1003")))
        later = by_key["ncaa:1002"][1]

        def extra(table, record):
            if table == "captures" and record is None:
                return dict(copy.deepcopy(later), capture_id="wayback:20190902100001:" + later["payload_sha256"])
            return None
        self.refuse(code, rehouse(self.base / "extra", extra))

        def duplicate(conn):
            conn.execute("CREATE TABLE captures_copy AS SELECT * FROM captures")
            conn.execute("DROP TABLE captures")
            conn.execute("ALTER TABLE captures_copy RENAME TO captures")
            last = conn.execute("SELECT MAX(ord) FROM captures").fetchone()[0]
            conn.execute("INSERT INTO captures SELECT ? + 1, capture_id, contest_key, state, record FROM captures "
                         "WHERE ord = (SELECT MIN(ord) FROM captures)", (last,))
        self.refuse(code, rehouse(self.base / "duplicate", mutate_conn=duplicate))

        def reorder(conn):
            ords = [o for (o,) in conn.execute("SELECT ord FROM captures WHERE contest_key = 'ncaa:1002' ORDER BY ord")]
            _swap_ords(conn, "captures", ords[0], ords[1])
        self.refuse("ARCHIVE_RECORD_ORDER_MISMATCH", rehouse(self.base / "reorder", mutate_conn=reorder))

    def test_reordered_assertions_requests_and_dispositions_refuse(self) -> None:
        first, second = [c["capture_id"] for c in self.captures if c["contest_key"] == "ncaa:1002"]

        def assertions(conn):
            last = conn.execute("SELECT MAX(ord) FROM assertions WHERE capture_id = ?", (first,)).fetchone()[0]
            head = conn.execute("SELECT MIN(ord) FROM assertions WHERE capture_id = ?", (second,)).fetchone()[0]
            self.assertEqual(head, last + 1)
            _swap_ords(conn, "assertions", last, head)
        self.refuse("ARCHIVE_RECORD_ORDER_MISMATCH", rehouse(self.base / "assertions", mutate_conn=assertions))

        def requests(conn):
            ords = [o for (o,) in conn.execute("SELECT ord FROM requests WHERE contest_key = 'ncaa:1002' ORDER BY ord")]
            _swap_ords(conn, "requests", ords[0], ords[1])
        self.refuse("ARCHIVE_RECORD_ORDER_MISMATCH", rehouse(self.base / "requests", mutate_conn=requests))
        self.refuse("ARCHIVE_RECORD_ORDER_MISMATCH", rehouse(self.base / "dispositions", mutate_conn=lambda conn: _swap_ords(
            conn, "dispositions", *[o for (o,) in conn.execute("SELECT ord FROM dispositions ORDER BY ord LIMIT 2")])))
        self.refuse("ARCHIVE_DISPOSITION_COLLECTION_MISMATCH", rehouse(self.base / "dropped", lambda t, r: (
            "DELETE" if t == "dispositions" and r and r["contest_key"] == "ncaa:1005" else None)))

    def test_derived_request_fields_refuse(self) -> None:
        answered = next(r for r in self.requests if r["kind"] == "METADATA" and r["metadata_answer"]
                        and r["metadata_answer"]["usable"])
        other = next(r for r in self.requests if r["body_sha256"] and r["seq"] != answered["seq"])
        pick = lambda r: r["seq"] == answered["seq"]  # noqa: E731
        code = "ARCHIVE_REQUEST_DERIVATION_MISMATCH"
        self.refuse(code, rehouse(self.base / "answer", self.edit("requests", pick, metadata_answer=dict(
            answered["metadata_answer"], timestamp="19000101000000"))))
        self.refuse(code, rehouse(self.base / "path", self.edit("requests", pick, body_path=other["body_path"])))
        self.refuse(code, rehouse(self.base / "type", self.edit("requests", pick, record_type="archive_capture")))
        self.refuse("ARCHIVE_RECEIPT_ALTERED", rehouse(self.base / "receipt", self.edit("requests", pick,
                                                                                     purpose="RETRY")))

    def test_issued_contract_tranche_acquisition_and_control_bind(self) -> None:
        def contract(document):
            document["contract_sha256"] = "f" * 64
        self.refuse("ARCHIVE_CONTRACT_NOT_ISSUED", rehouse(self.base / "contract", mutate_meta={
            "contract_sha256": "f" * 64}, mutate_document=contract))
        self.refuse("ARCHIVE_TRANCHE_NOT_ISSUED", rehouse(self.base / "tranche", mutate_meta={
            "tranche_sha256": "e" * 64}))
        control = json.loads(sqlite3.connect(STATE["sidecar"]).execute(
            "SELECT value FROM meta WHERE key = 'control'").fetchone()[0])
        self.refuse("ARCHIVE_RECEIPT_ALTERED", rehouse(self.base / "control", mutate_meta={
            "control": json.dumps(dict(control, contest_key="ncaa:1001"), sort_keys=True)}))
        old = next(STATE["world"]["out"].glob("acquisition/sha256/*/acquisition.json"))
        doc = json.loads(old.read_text(encoding="utf-8"))
        doc["requests"] = [r for r in doc["requests"] if not (r["contest_key"] == "ncaa:1001" and r["kind"] == "REPLAY")]
        data = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        forged = hashlib.sha256(data).hexdigest()

        def write_acquisition(root):
            fx.write(root / "acquisition" / "sha256" / forged / "acquisition.json", data)
        self.refuse("ARCHIVE_ACQUISITION_NOT_ISSUED", rehouse(self.base / "acquisition", self.omit_captures(
            {c["capture_id"] for c in self.captures if c["contest_key"] == "ncaa:1001"}, "ncaa:1001"),
            mutate_meta={"acquisition_identity": forged}, mutate_raw=write_acquisition))


GATE_V1_2 = fx.ROOT / "artifacts" / "data_lake" / "national_archived_publication_2019_v1_2_gate.json"


class IssuedAuthorityPackagingTests(unittest.TestCase):
    """The packaged V1.2 authority is exactly the committed contract, its issued tranche bytes and the retained
    acquisition of the committed gate (unmounted)."""

    def test_packaged_authority_equals_the_committed_contract_and_gate(self) -> None:
        contract = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))
        gate = json.loads(GATE_V1_2.read_text(encoding="utf-8"))
        issued = arch.ISSUED_V1_2
        self.assertEqual((issued["contract_id"], issued["contract_sha256"]),
                         (contract["contract_id"], hashlib.sha256(fx.CONTRACT_PATH.read_bytes()).hexdigest()))
        self.assertEqual(issued["tranche_sha256"], contract["scope"]["tranche_sha256"])
        parent = contract["parent_binding"]["source_time"]
        self.assertEqual(issued["parent"], {"source_time": {k: parent[k] for k in (
            "content_identity", "contract_sha256", "database_identity", "sqlite_sha256")}})
        route = contract["parent_binding"]["route_control"]
        self.assertEqual(issued["control"], {"contest_key": route["contest_key"],
                                             "payload_sha256": route["raw_payload_sha256"],
                                             "raw_receipt_sha256": route["raw_receipt_sha256"],
                                             "route_qualification_sha256": route["sha256"]})
        self.assertEqual(issued["acquisition_identity"], gate["acquisition_identity"])
        self.assertEqual(issued["acquisition_identity"],
                         contract["predecessor"]["predecessor_outputs"]["acquisition_identity"])
        self.assertEqual(gate["contract_sha256"], issued["contract_sha256"])
        packaged = Path(arch.__file__).with_name(arch.ISSUED_TRANCHE_FILE)
        self.assertEqual(hashlib.sha256(packaged.read_bytes()).hexdigest(), issued["tranche_sha256"])
        authority = arch.packaged_authority()
        specs = contract["scope"]["keys"]
        self.assertEqual(authority.keys, [s["contest_key"] for s in specs])
        for spec in specs:
            key = spec["contest_key"]
            row = authority.rows[key]
            self.assertEqual((row["selection_role"], row["stratum"], authority.candidate_urls[key],
                              authority.game_ids[key]),
                             (spec["selection_role"], spec["stratum"], spec["candidate_url"], spec["game_id_literal"]))
        # The issued tranche file is declared package data (BAT-715 adds the expansion cohort file to the same list, so
        # the parsed list is checked rather than the literal one-element line).
        import tomllib  # noqa: PLC0415
        package_data = tomllib.loads((fx.ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"][
            "package-data"]["aggie_analytics.national_source_time"]
        self.assertIn(arch.ISSUED_TRANCHE_FILE, package_data)

    def test_an_unissued_authority_is_refused_before_any_record_is_read(self) -> None:
        with self.assertRaises(arch.ArchiveEvidenceError) as caught:
            arch.issued_authority("0" * 64, arch.ISSUED_V1_2["acquisition_identity"])
        self.assertEqual(caught.exception.code, "ARCHIVE_CONTRACT_NOT_ISSUED")
        with self.assertRaises(arch.ArchiveEvidenceError) as caught:
            arch.issued_authority(arch.ISSUED_V1_2["contract_sha256"], "0" * 64)
        self.assertEqual(caught.exception.code, "ARCHIVE_ACQUISITION_NOT_ISSUED")
        tranche = Path(arch.__file__).with_name(arch.ISSUED_TRANCHE_FILE).read_bytes()
        with self.assertRaises(arch.ArchiveEvidenceError) as caught:
            arch.IssuedAuthority(tranche_bytes=tranche + b" ", **arch.ISSUED_V1_2)
        self.assertEqual(caught.exception.code, "ARCHIVE_AUTHORITY_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
