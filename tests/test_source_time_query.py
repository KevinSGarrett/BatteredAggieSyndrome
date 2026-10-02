"""BAT-712 installed read-only source-time query (Cycle #40 TP40-A01): cutoff semantics, paging, filters, refusals.

The database comes from the synthetic national world in ``national_source_time_fixture`` (fictional records only).
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
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
import national_source_time_fixture as fx  # noqa: E402
from aggie_analytics.national_source_time import query as q  # noqa: E402

STATE: dict = {}


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    base = Path(STATE["tmp"].name)
    STATE["world"] = fx.build_world(base / "w")
    code, result, err = fx.run_build(STATE["world"], base / "o")
    assert code == 0, err
    STATE["result"] = result
    STATE["db"] = fx.database_path(result)


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def run(*argv: str) -> tuple[int, dict | None, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = q.main(["--database", str(STATE["db"]), *argv])
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


class CutoffSemanticsTests(unittest.TestCase):
    def test_historical_cutoff_is_not_observed_and_outcomes_cannot_precede_the_event(self) -> None:
        f = fields("ncaa:1003", "2019-09-01T00:00:00Z")
        self.assertEqual(f["season"]["observed_by_cutoff"], "UNKNOWN")
        self.assertEqual(f["season"]["historically_published_by_cutoff"], "UNKNOWN")
        self.assertEqual(f["a_points"]["historically_published_by_cutoff"], "FALSE")
        after = fields("ncaa:1003", "2019-12-31T00:00:00Z")
        self.assertEqual(after["a_points"]["historically_published_by_cutoff"], "UNKNOWN")  # late game date only

    def test_late_retrieval_is_classified_honestly_at_its_own_instant(self) -> None:
        f = fields("ncaa:1003", "2026-10-02T00:00:00Z")
        self.assertEqual({v["observed_by_cutoff"] for v in f.values()}, {"TRUE"})
        self.assertEqual({v["historically_published_by_cutoff"] for v in f.values()}, {"TRUE"})

    def assertion_states(self, contest: str, cutoff: str, kind: str) -> set:
        code, doc, err = run("--grain", "assertion", "--contest", contest, "--cutoff", cutoff, "--source-kind", kind,
                             "--all")
        self.assertEqual(code, 0, err)
        return {(r["decision"]["observed_by_cutoff"], r["decision"]["observed_reason"]) for r in doc["rows"]}

    def test_exact_request_interval_gives_false_unknown_true(self) -> None:
        kind = "CFBD_ROUTE_RESPONSE"
        self.assertEqual(self.assertion_states("ncaa:1003", "2026-08-09T18:59:47Z", kind),
                         {("FALSE", "REQUEST_STARTED_AFTER_CUTOFF")})
        self.assertEqual(self.assertion_states("ncaa:1003", "2026-08-09T18:59:48.500000Z", kind),
                         {("UNKNOWN", "CUTOFF_WITHIN_REQUEST_INTERVAL")})
        self.assertEqual(self.assertion_states("ncaa:1003", "2026-08-09T18:59:49Z", kind),
                         {("TRUE", "RECEIPT_COMPLETED_AT_OR_BEFORE_CUTOFF")})

    def test_cutoff_equality_and_timezone_equivalence(self) -> None:
        kind = "NCAA_TEAM_SEASON_PAGE"
        equal = self.assertion_states("ncaa:1003", fx.NCAA_STAMP, kind)
        offset = self.assertion_states("ncaa:1003", "2026-08-13T05:39:56-05:00", kind)
        self.assertEqual(equal, {("TRUE", "POSSESSION_RECORDED_AT_OR_BEFORE_CUTOFF")})
        self.assertEqual(equal, offset)
        before = self.assertion_states("ncaa:1003", "2026-08-13T10:39:55.999999Z", kind)
        self.assertEqual(before, {("UNKNOWN", "RECORDED_AFTER_CUTOFF_EARLIER_POSSESSION_NOT_EXCLUDED")})

    def test_cache_hit_is_an_upper_bound_never_false(self) -> None:
        early = self.assertion_states("ncaa:1001", "2016-01-01T00:00:00Z", "CFBD_ROUTE_RESPONSE")
        self.assertIn(("UNKNOWN", "CACHE_HIT_AFTER_CUTOFF_ORIGINAL_RETRIEVAL_UNRECORDED"), early)
        self.assertNotIn("FALSE", {s for s, _r in early if _r.startswith("CACHE")})

    def test_absent_and_contradictory_receipts_never_decide(self) -> None:
        late = "2026-10-02T00:00:00Z"
        absent = self.assertion_states("ncaa:1007", late, "NCAA_TEAM_SEASON_PAGE")
        self.assertIn(("UNKNOWN", "RECEIPT_ABSENT"), absent)
        contradictory = self.assertion_states("ncaa:2001", late, "NCAA_TEAM_SEASON_PAGE")
        self.assertIn(("UNKNOWN", "RECEIPT_TIMES_CONTRADICTORY"), contradictory)

    def test_asserted_commit_is_compared_as_an_assertion_only(self) -> None:
        code, doc, err = run("--grain", "assertion", "--contest", "ncaa:1001", "--source-kind", "REPOSITORY_VERSION",
                             "--cutoff", "2024-01-01T00:00:00Z", "--all")
        decision = doc["rows"][0]["decision"]
        self.assertEqual((decision["asserted_commit_time_by_cutoff"], decision["asserted_commit_label"]),
                         ("TRUE", "SOURCE_ASSERTED_ONLY_NOT_PUBLICATION_EVIDENCE"))
        self.assertEqual(decision["observed_by_cutoff"], "UNKNOWN")
        self.assertEqual(decision["historically_published_by_cutoff"], "UNKNOWN")
        self.assertEqual(decision["pit_admission"]["state"], "NOT_ADMITTED")
        code, doc, err = run("--grain", "assertion", "--contest", "ncaa:1001", "--source-kind", "REPOSITORY_VERSION",
                             "--cutoff", "2020-01-01T00:00:00Z", "--limit", "1")
        self.assertEqual(doc["rows"][0]["decision"]["asserted_commit_time_by_cutoff"], "FALSE")

    def test_precision_interval_crossing_and_synthetic_qualified_publication(self) -> None:
        capture = {"clocks": {"retrieval": {"state": "PRESENT", "role": "EXACT_REQUEST_INTERVAL",
                                            "earliest_utc": "2026-01-01T00:00:00.000000Z",
                                            "latest_utc": "2026-01-01T00:00:59.999999Z"},
                              "supported_publication": {"state": "ABSENT"},
                              "asserted_commit_committer": {"state": "NOT_APPLICABLE"}},
                   "time_evidence_class": "SYNTHETIC_FIXTURE_ONLY"}
        cut = q.parse_cutoff("2026-01-01T00:00:30Z")
        self.assertEqual(q.observed_by_cutoff(capture, cut)[0], "UNKNOWN")
        synthetic = copy.deepcopy(capture)
        synthetic["clocks"]["supported_publication"] = {"state": "PRESENT", "role": q.SYNTHETIC_PUBLICATION_ROLE,
                                                        "earliest_utc": "2016-01-01T00:00:00.000000Z",
                                                        "latest_utc": "2016-01-01T00:00:59.999999Z"}
        decide = q.published_by_cutoff
        self.assertEqual(decide(synthetic, "UNKNOWN", "a_points", "2015-09-01", q.parse_cutoff("2016-01-01T00:01:00Z")),
                         ("TRUE", "SYNTHETIC_FIXTURE_PUBLICATION_AT_OR_BEFORE_CUTOFF"))
        self.assertEqual(decide(synthetic, "UNKNOWN", "season", "2015-09-01", q.parse_cutoff("2015-12-31T23:59:59Z"))[0],
                         "FALSE")
        self.assertEqual(decide(synthetic, "UNKNOWN", "season", "2015-09-01", q.parse_cutoff("2016-01-01T00:00:30Z"))[0],
                         "UNKNOWN")
        unqualified = copy.deepcopy(synthetic)
        unqualified["clocks"]["supported_publication"]["role"] = "GIT_COMMITTER_DATE"
        self.assertEqual(decide(unqualified, "UNKNOWN", "a_points", "2015-09-01", cut),
                         ("UNKNOWN", "PUBLICATION_CLAIM_UNQUALIFIED"))

    def test_target_relation_excludes_outcome_fields(self) -> None:
        code, doc, err = run("--grain", "contribution", "--contest", "ncaa:1005", "--cutoff", "2026-10-02T00:00:00Z",
                             "--relation-type", "TARGET_CONTEST", "--all")
        self.assertEqual(code, 0, err)
        for row in doc["rows"]:
            self.assertTrue(row["target_outcome_fields_excluded"])
            self.assertEqual(sorted(row["required_field_decisions"]),
                             ["a_participant", "b_participant", "contest_date", "season"])
        code, doc, err = run("--grain", "contribution", "--contest", "ncaa:1005", "--cutoff", "2019-09-01T00:00:00Z",
                             "--relation-type", "CONTRIBUTOR", "--all")
        self.assertTrue(doc["rows"])
        self.assertEqual({r["inputs_observed_by_cutoff"] for r in doc["rows"]}, {"UNKNOWN"})
        self.assertEqual({r["pit_admission"]["state"] for r in doc["rows"]}, {"NOT_ADMITTED"})


class PagingAndFilterTests(unittest.TestCase):
    def test_paging_is_exact_in_payload_order(self) -> None:
        for grain, payload, key in (("assertion", "assertions.jsonl", "assertion"),
                                    ("contribution", "relations.jsonl", "relation")):
            expected = fx.read_payload(STATE["result"], payload)
            seen, offset = [], 0
            while True:
                code, doc, err = run("--grain", grain, "--cutoff", "2026-10-02T00:00:00Z", "--limit", "7",
                                     "--offset", str(offset))
                self.assertEqual(code, 0, err)
                if not doc["rows"]:
                    break
                self.assertEqual(doc["total"], len(expected))
                seen += [r[key] for r in doc["rows"]]
                offset += 7
            self.assertEqual(seen, expected, grain)
        for grain, payload in (("partition", "partition.jsonl"), ("repository-row", "repository_rows.jsonl"),
                               ("capture", "captures.jsonl"), ("lineage-row", "lineage_rows.jsonl")):
            code, doc, err = run("--grain", grain, "--all")
            self.assertEqual(doc["rows"], fx.read_payload(STATE["result"], payload), grain)

    def test_filters_and_out_of_scope_seasons(self) -> None:
        code, doc, err = run("--grain", "contest", "--team", "org:3", "--season", "2019", "--cutoff",
                             "2026-10-02T00:00:00Z", "--all")
        self.assertEqual(sorted(r["contest"]["contest_key"] for r in doc["rows"]), ["ncaa:1002", "ncaa:1004",
                                                                                   "ncaa:1005"])
        code, doc, err = run("--grain", "assertion", "--field", "a_points", "--evidence-class",
                             "EXACT_REQUEST_RECEIPT_ONLY", "--cutoff", "2026-10-02T00:00:00Z", "--all")
        self.assertTrue(doc["rows"] and all(r["assertion"]["field"] == "a_points" and
                                            r["decision"]["time_evidence_class"] == "EXACT_REQUEST_RECEIPT_ONLY"
                                            for r in doc["rows"]))
        code, doc, err = run("--grain", "repository-row", "--join-state", "CONFLICTING", "--all")
        self.assertEqual(doc["total"], 4)
        for season in ("2015", "2024", "2026"):
            code, doc, err = run("--grain", "contribution", "--season", season, "--cutoff", "2026-10-02T00:00:00Z")
            self.assertEqual((doc["season_scope_state"], doc["total"], doc["rows"]), ("NOT_YET_AUDITED", 0, []))
        code, doc, err = run("--grain", "partition", "--season", "2024", "--all")
        self.assertEqual((doc["season_scope_state"], [r["source_time_scope"] for r in doc["rows"]]),
                         ("NOT_YET_AUDITED", ["KEY_ONLY_PROTECTED_EXPOSED"]))


class RefusalTests(unittest.TestCase):
    def refuse(self, code_expected: str, *argv: str, database: Path | None = None) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = q.main(["--database", str(database or STATE["db"]), *argv])
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, 2, out.getvalue())
        text = err.getvalue()
        self.assertIn(code_expected, text)

    def test_input_refusals(self) -> None:
        cut = ("--cutoff", "2026-10-02T00:00:00Z")
        self.refuse("PIT_ADMISSION_AUTHORITY_ABSENT", "--grain", "contest", *cut, "--require-pit")
        self.refuse("CUTOFF_REQUIRED", "--grain", "assertion")
        self.refuse("CUTOFF_TIMEZONE_REQUIRED", "--grain", "assertion", "--cutoff", "2026-10-02T00:00:00")
        self.refuse("CUTOFF_TIMEZONE_REQUIRED", "--grain", "assertion", "--cutoff", "2026-10-02")
        self.refuse("CUTOFF_INVALID", "--grain", "assertion", "--cutoff", "yesterday")
        self.refuse("CUTOFF_INVALID", "--grain", "assertion", "--cutoff", "2026-02-30T00:00:00Z")
        self.refuse("TEAM_KEY_INVALID", "--grain", "contest", *cut, "--team", "Texas A&M")
        self.refuse("CONTEST_KEY_INVALID", "--grain", "contest", *cut, "--contest", "game 7")
        self.refuse("FIELD_INVALID", "--grain", "assertion", *cut, "--field", "rank")
        self.refuse("EVIDENCE_CLASS_INVALID", "--grain", "assertion", *cut, "--evidence-class", "PUBLISHED")
        self.refuse("FILTER_NOT_APPLICABLE", "--grain", "contest", *cut, "--field", "season")
        self.refuse("NEGATIVE_OFFSET", "--grain", "partition", "--offset", "-1")
        self.refuse("STALE_DATABASE_IDENTITY", "--grain", "partition", "--expect-identity", "0" * 64)
        self.refuse("STALE_CONTRACT", "--grain", "partition", "--expect-contract", "0" * 64)
        self.refuse("unrecognized arguments", "--grain", "partition", "--no-such-flag")
        self.refuse("invalid choice", "--grain", "labels")

    def copy_db(self, tmp: Path) -> tuple[Path, Path]:
        result = STATE["result"]
        ident = result["database_identity"]
        db = tmp / "canonical" / "st" / "sha256" / ident / "national_source_time.sqlite"
        man = tmp / "manifests" / "st" / "sha256" / ident / "run_manifest.json"
        db.parent.mkdir(parents=True)
        man.parent.mkdir(parents=True)
        shutil.copyfile(STATE["db"], db)
        shutil.copyfile(result["database"]["manifest"], man)
        return db, man

    def test_altered_database_manifest_schema_and_location_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            db, man = self.copy_db(tmp / "a")
            conn = sqlite3.connect(db)
            changed = conn.execute("UPDATE partition SET record = replace(record, 'IN_SCOPE', 'IN_SCOPF') "
                                   "WHERE ord = 1 AND instr(record, 'IN_SCOPE') > 0").rowcount
            conn.commit()
            conn.close()
            self.assertEqual(changed, 1)
            self.refuse("DATABASE_TAMPERED", "--grain", "partition", database=db)
            doc = json.loads(man.read_text(encoding="utf-8"))
            doc["identity_document"]["outputs"]["national_source_time.sqlite"] = hashlib.sha256(db.read_bytes()).hexdigest()
            man.write_text(json.dumps(doc), encoding="utf-8")
            self.refuse("DATABASE_IDENTITY_MISMATCH", "--grain", "partition", database=db)
            # an unknown schema in a consistently rehoused copy (identity recomputed for its own directory)
            db2, man2 = self.copy_db(tmp / "b")
            conn = sqlite3.connect(db2)
            conn.execute("UPDATE meta SET value = 'BAS-NATIONAL-SOURCE-TIME-DB-9' WHERE key = 'schema_version'")
            conn.commit()
            conn.close()
            doc = json.loads(man2.read_text(encoding="utf-8"))
            doc["identity_document"]["outputs"]["national_source_time.sqlite"] = hashlib.sha256(db2.read_bytes()).hexdigest()
            ident = hashlib.sha256(json.dumps(doc["identity_document"], sort_keys=True, separators=(",", ":"),
                                              ensure_ascii=False).encode("utf-8")).hexdigest()
            doc["identity"] = ident
            db3 = tmp / "b" / "canonical" / "st" / "sha256" / ident / "national_source_time.sqlite"
            man3 = tmp / "b" / "manifests" / "st" / "sha256" / ident / "run_manifest.json"
            db3.parent.mkdir(parents=True)
            man3.parent.mkdir(parents=True)
            shutil.copyfile(db2, db3)
            man3.write_text(json.dumps(doc), encoding="utf-8")
            self.refuse("DATABASE_SCHEMA_UNSUPPORTED", "--grain", "partition", database=db3)
            moved = tmp / "c" / "elsewhere" / "national_source_time.sqlite"
            moved.parent.mkdir(parents=True)
            shutil.copyfile(STATE["db"], moved)
            self.refuse("DATABASE_LOCATION_INVALID", "--grain", "partition", database=moved)
            self.refuse("DATABASE_MISSING", "--grain", "partition", database=tmp / "none.sqlite")

    def test_connection_refuses_writes(self) -> None:
        with q.SourceTimeDatabase(STATE["db"]) as handle:
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("DELETE FROM partition")
        self.assertEqual(fx.sha(STATE["db"].read_bytes()), STATE["result"]["database_sha256"])


if __name__ == "__main__":
    unittest.main()
