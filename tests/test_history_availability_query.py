"""BAT-714 read-only history-availability query (Cycle #42 TP42-A01): ``bas-history-availability-query``.

Runs on the synthetic population/history/source-time/archive world of ``national_history_availability_fixture``
(fictional records only): targets ncaa:1002 (two cold starts, a 20-20 tie), ncaa:1003, ncaa:1004, ncaa:1005 and
ncaa:1007; archive versions for ncaa:1001 (coherent), ncaa:1002 (a pregame partial version, then a coherent one),
ncaa:1003 (the retained control, coherent), ncaa:1004 (pregame only, partial) and ncaa:1005 (no capture).
"""
from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_history_availability_fixture as fx  # noqa: E402
from aggie_analytics.national_history import availability as core  # noqa: E402
from aggie_analytics.national_history import availability_query as aq  # noqa: E402

STATE: dict = {}
LATE = "2026-10-05T00:00:00Z"


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    STATE["world"] = fx.build_world(Path(STATE["tmp"].name) / "g")
    code, result, err = fx.run_build(STATE["world"])
    assert code == 0, err
    STATE["result"] = result
    STATE["db"] = fx.database_path(result)
    STATE["db_sha"] = fx.sha(STATE["db"].read_bytes())


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def q(*argv: str, database: Path | None = None, **kw):
    return fx.query(STATE["world"], database or STATE["db"], *argv, **kw)


def ok(*argv: str, **kw) -> dict:
    code, doc, err = q(*argv, **kw)
    assert code == 0, err
    return doc


def refused(*argv: str, **kw) -> str | None:
    code, _doc, err = q(*argv, **kw)
    assert code == 2, (code, err)
    return fx.refusal(err)


def decision(target: str, view: str, prior: str, cutoff: str) -> dict:
    doc = ok("--grain", "relationship", "--contest", target, "--view", view, "--all", "--cutoff", cutoff)
    return next(r["decision"] for r in doc["rows"] if r["relationship"]["prior_contest_key"] == prior)


def history(target: str, view: str, cutoff: str) -> dict:
    doc = ok("--grain", "history", "--contest", target, "--view", view, "--cutoff", cutoff)
    return doc["rows"][0]


def independent_content_identity(database: Path, base_document: dict) -> str:
    """Expected content identity from the database's exact stored rows, standard library only (no producer, core or
    query helper): the base document's non-payload fields with the semantic and gzip(mtime 0, no file name, level 9)
    payload hashes and row counts recomputed."""
    semantic, packed, counts = {}, {}, {}
    conn = sqlite3.connect(f"file:{Path(database).absolute().as_posix()}?mode=ro", uri=True)
    try:
        for table in ("targets", "views", "relationships", "evidence", "witnesses"):
            rows = conn.execute(f"SELECT record FROM {table} ORDER BY ord")
            raw = b"".join(r[0].encode("utf-8") + b"\n" for r in rows)
            buffer = io.BytesIO()
            with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as stream:
                stream.write(raw)
            semantic[f"{table}.jsonl"] = hashlib.sha256(raw).hexdigest()
            packed[f"{table}.jsonl.gz"] = hashlib.sha256(buffer.getvalue()).hexdigest()
            counts[f"{table}.jsonl"] = raw.count(b"\n")
    finally:
        conn.close()
    document = dict(base_document, semantic_outputs=semantic, outputs=packed, row_counts=counts)
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def content_binding_cases(genuine_meta: dict, other_identity: str, alternative: str, alternative_schema: str) -> dict:
    """Content-binding claims, each a (meta edit, identity-document patch) pair with its intended refusal; the outer
    database hash, table counts and identity are recomputed afterwards by the rehashed copy."""
    def meta(**values):
        def mutate(conn):
            for key, value in values.items():
                conn.execute("DELETE FROM meta WHERE key = ?", (key,))
                if value is not None:
                    conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (key, value))
        return mutate

    def claim(value):
        def patch(document):
            if value is None:
                document.pop("content_identity", None)
            else:
                document["content_identity"] = value
        return patch
    counts = json.dumps(dict(json.loads(genuine_meta["row_counts"]), **{"targets.jsonl": 6}), sort_keys=True)
    return {
        "CONTENT_IDENTITY_MISMATCH/invented": (meta(content_identity="f" * 64), claim("f" * 64)),
        "CONTENT_IDENTITY_MISSING/both": (meta(content_identity=None), claim(None)),
        "CONTENT_IDENTITY_MISSING/meta": (meta(content_identity=None), None),
        "CONTENT_IDENTITY_MISSING/manifest": (lambda conn: None, claim(None)),
        "CONTENT_IDENTITY_MISMATCH/wrong": (meta(content_identity=other_identity), claim(other_identity)),
        "CONTENT_IDENTITY_MISMATCH/self-consistent": (meta(content_identity=alternative,
                                                          payload_schema=alternative_schema), claim(alternative)),
        "CONTENT_DECLARATION_MISMATCH/payload-hashes": (meta(payload_sha256="{}"), None),
        "CONTENT_DECLARATION_MISMATCH/payload-hashes-not-json": (meta(payload_sha256="invented"), None),
        "CONTENT_DECLARATION_MISMATCH/payload-schema": (meta(payload_schema="ADMITTED_FAKE_SCHEMA"), None),
        "CONTENT_DECLARATION_MISMATCH/row-counts": (meta(row_counts=counts), None),
        "DATABASE_IDENTITY_MISMATCH/meta-only": (meta(content_identity="e" * 64), None),
    }


class GrainTests(unittest.TestCase):
    def test_totals_and_exact_paging_in_payload_order(self) -> None:
        totals = {g: ok("--grain", g, "--cutoff", LATE, "--limit", "0")["total"]
                  for g in ("target", "history", "relationship", "prior-evidence")}
        self.assertEqual(totals, {"target": 5, "history": 10, "relationship": 11, "prior-evidence": 5})
        full = ok("--grain", "relationship", "--all", "--cutoff", LATE)
        pages, offset = [], 0
        while True:
            doc = ok("--grain", "relationship", "--limit", "3", "--offset", str(offset), "--cutoff", LATE)
            self.assertEqual(doc["total"], 11)
            pages += doc["rows"]
            if doc["next_offset"] is None:
                break
            self.assertEqual(doc["next_offset"], offset + 3)
            offset = doc["next_offset"]
        self.assertEqual(pages, full["rows"])
        keys = [(r["relationship"]["target_date"], r["relationship"]["target_contest_key"], r["relationship"]["view"],
                 r["relationship"]["prior_contest_date"], r["relationship"]["prior_contest_key"]) for r in full["rows"]]
        self.assertEqual(keys, sorted(keys))
        empty = ok("--grain", "target", "--limit", "0", "--cutoff", LATE)
        self.assertEqual((empty["returned"], empty["rows"], empty["next_offset"]), (0, [], 0))

    def test_filters_by_contest_team_view_and_support_state(self) -> None:
        self.assertEqual(ok("--grain", "history", "--contest", "ncaa:1005", "--cutoff", LATE)["total"], 2)
        self.assertEqual(ok("--grain", "history", "--contest", "1005", "--cutoff", LATE)["total"], 2)
        self.assertEqual(ok("--grain", "relationship", "--team", "org:1", "--all", "--cutoff", LATE)["total"], 6)
        self.assertEqual(ok("--grain", "relationship", "--view", "B", "--all", "--cutoff", LATE)["total"], 4)
        self.assertEqual([r["target"]["contest_key"] for r in ok("--grain", "target", "--team", "5", "--all", "--cutoff",
                                                                 LATE)["rows"]], ["ncaa:1004", "ncaa:1007"])
        supported = ok("--grain", "relationship", "--support-state", "SUPPORTED", "--all", "--cutoff", LATE)
        unsupported = ok("--grain", "relationship", "--support-state", "UNSUPPORTED", "--all", "--cutoff", LATE)
        self.assertEqual(supported["total"] + unsupported["total"], 11)
        self.assertTrue(all(r["decision"]["support_state"] == "SUPPORTED" for r in supported["rows"]))
        self.assertEqual(ok("--grain", "prior-evidence", "--contest", "ncaa:1002", "--cutoff", LATE)["total"], 1)

    def test_refusals(self) -> None:
        cases = [(("--grain", "target", "--view", "A", "--cutoff", LATE), "FILTER_NOT_APPLICABLE"),
                 (("--grain", "history", "--support-state", "SUPPORTED", "--cutoff", LATE), "FILTER_NOT_APPLICABLE"),
                 (("--grain", "history", "--team", "Alpha", "--cutoff", LATE), "TEAM_KEY_INVALID"),
                 (("--grain", "history", "--contest", "espn:1", "--cutoff", LATE), "CONTEST_KEY_INVALID"),
                 (("--grain", "history", "--view", "C", "--cutoff", LATE), "VIEW_INVALID"),
                 (("--grain", "relationship", "--support-state", "MAYBE", "--cutoff", LATE), "SUPPORT_STATE_INVALID"),
                 (("--grain", "history", "--offset", "-1", "--cutoff", LATE), "NEGATIVE_OFFSET"),
                 (("--grain", "history", "--limit", "-1", "--cutoff", LATE), "NEGATIVE_LIMIT"),
                 (("--grain", "history",), "CUTOFF_REQUIRED"),
                 (("--grain", "history", "--cutoff", "2019-09-07"), "CUTOFF_TIMEZONE_REQUIRED"),
                 (("--grain", "history", "--cutoff", "2019-09-07T10:00:00"), "CUTOFF_TIMEZONE_REQUIRED"),
                 (("--grain", "history", "--cutoff", "kickoff"), "CUTOFF_INVALID"),
                 (("--grain", "history", "--cutoff", LATE, "--require-pit"), "PIT_ADMISSION_NOT_ESTABLISHED"),
                 (("--grain", "history", "--cutoff", LATE, "--expect-identity", "0" * 64), "STALE_DATABASE_IDENTITY")]
        for argv, code in cases:
            self.assertEqual(refused(*argv), code, argv)
            # the message names its code once, also when it wraps an accepted reader's error
            _exit, _doc, err = q(*argv)
            self.assertEqual(json.loads(err.strip().splitlines()[-1])["error"].count(code), 1, err)
        wrong = q("--grain", "history", "--cutoff", LATE, "--history-database",
                  str(fx.parent_args(STATE["world"])[fx.parent_args(STATE["world"]).index("--population-database") + 1]))
        self.assertEqual(fx.refusal(wrong[2]), "DATABASE_LOCATION_INVALID")
        self.assertEqual(json.loads(wrong[2].strip().splitlines()[-1])["error"].count("DATABASE_LOCATION_INVALID"), 1)
        for argv in (("--grain", "history", "--cutoff", LATE, "--out", "x.json"), ("--grain", "history", "--cut", LATE),
                     ("--grain", "matrix", "--cutoff", LATE)):
            code, _doc, _err = q(*argv)
            self.assertEqual(code, 2, argv)

    def test_out_of_scope_season_is_not_yet_audited(self) -> None:
        doc = ok("--grain", "history", "--season", "2018", "--cutoff", LATE)
        self.assertEqual((doc["season_scope_state"], doc["total"], doc["rows"]), ("NOT_YET_AUDITED", None, []))
        self.assertEqual(ok("--grain", "history", "--season", "2019", "--cutoff", LATE)["total"], 10)


class SemanticsTests(unittest.TestCase):
    def test_control_bound_equality_microsecond_zone_and_event(self) -> None:
        at = decision("ncaa:1005", "B", "ncaa:1003", fx.CONTROL_BOUND)
        self.assertEqual((at["support_state"], at["result_published_by_cutoff"]), ("SUPPORTED", "TRUE"))
        self.assertEqual(len(at["supporting_versions"]), 1)
        self.assertEqual({w["field"] for w in at["supporting_versions"][0]["witnesses"]}, set(core.FIELDS))
        before = decision("ncaa:1005", "B", "ncaa:1003", "2019-09-08T01:30:00.999998Z")
        self.assertEqual((before["support_state"], before["result_published_by_cutoff"], before["reason_class"]),
                         ("UNSUPPORTED", "UNKNOWN", "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF"))
        zoned = decision("ncaa:1005", "B", "ncaa:1003", "2019-09-07T21:30:00.999999-04:00")
        self.assertEqual(zoned["support_state"], "SUPPORTED")
        early = decision("ncaa:1005", "B", "ncaa:1003", "2019-09-01T00:00:00Z")
        self.assertEqual((early["result_published_by_cutoff"], early["reason_class"]),
                         ("FALSE", "OUTCOME_CANNOT_EXIST_BEFORE_PRIOR_EVENT_DATE"))

    def test_versions_are_never_combined_and_partial_never_supports(self) -> None:
        between = decision("ncaa:1003", "B", "ncaa:1002", "2019-09-01T00:00:00Z")
        self.assertEqual((between["support_state"], between["reason_class"]),
                         ("UNSUPPORTED", "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF"))
        self.assertEqual(decision("ncaa:1003", "B", "ncaa:1002", LATE)["support_state"], "SUPPORTED")
        partial = decision("ncaa:1005", "A", "ncaa:1004", LATE)
        self.assertEqual((partial["support_state"], partial["reason_class"], partial["result_published_by_cutoff"]),
                         ("UNSUPPORTED", "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION",
                          "NO_QUALIFIED_ARCHIVE_ASSERTION"))
        missing = decision("ncaa:1007", "A", "ncaa:1005", LATE)
        self.assertEqual(missing["reason_class"], "ARCHIVE_NO_CAPTURE")

    def test_tie_exact_rates_and_complete_denominators(self) -> None:
        row = history("ncaa:1003", "B", LATE)
        team = row["team_history"]
        self.assertEqual((team["team_key"], team["supported_priors"], team["supported_subset"]["ties"],
                          team["supported_subset"]["margin_total"]), ("org:2", 1, 1, 0))
        self.assertEqual(team["supported_subset"]["win_rate"], {"numerator": 0, "denominator": 1})
        alpha = history("ncaa:1007", "A", LATE)["team_history"]
        self.assertEqual((alpha["expected_prior_relationships"], alpha["history_pool_priors"],
                          alpha["supported_priors"], alpha["unsupported_priors"]), (3, 3, 2, 1))
        self.assertEqual(alpha["unsupported_by_reason_class"]["ARCHIVE_NO_CAPTURE"], 1)
        self.assertEqual(alpha["supported_subset"]["win_rate"], {"numerator": 2, "denominator": 2})
        self.assertEqual(alpha["supported_subset"]["points_for_mean"], {"numerator": 63, "denominator": 2})
        self.assertEqual(alpha["completeness_state"], "PARTIAL_SUPPORTED_SUBSET")
        self.assertFalse(alpha["supported_subset_is_complete_history"])
        self.assertEqual(alpha["supported_subset"]["rate_scope"], "SUPPORTED_SUBSET_ONLY_NOT_FULL_HISTORY")

    def test_cold_starts_and_zero_supported_have_null_rates(self) -> None:
        cold = history("ncaa:1002", "A", LATE)
        for block in (cold["team_history"], cold["opponent_history"]):
            self.assertEqual(block["completeness_state"], "COLD_START_NO_EXPECTED_PRIORS")
            self.assertIsNone(block["supported_subset"]["win_rate"])
        none = history("ncaa:1007", "B", "2019-09-10T00:00:00Z")["team_history"]
        self.assertEqual(none["completeness_state"], "NO_SUPPORTED_PRIORS")
        self.assertIsNone(none["supported_subset"]["points_against_mean"])

    def test_pair_coherence_current_opponent_and_no_target_outcome(self) -> None:
        rows = {(r["view"]["target_contest_key"], r["view"]["view"]): r
                for r in ok("--grain", "history", "--all", "--cutoff", LATE)["rows"]}
        for (target, view), row in rows.items():
            other = rows[(target, "B" if view == "A" else "A")]
            self.assertEqual(row["opponent_history"], other["team_history"])
            self.assertEqual(row["opponent_history"]["team_key"], row["view"]["opponent_key"])
        targets = ok("--grain", "target", "--all", "--cutoff", LATE)["rows"]
        for row in targets:
            self.assertFalse({"a_points", "b_points", "a_result"} & set(row["target"]))
            self.assertEqual(row["histories"]["A"], rows[(row["target"]["contest_key"], "A")]["team_history"])
        rels = ok("--grain", "relationship", "--all", "--cutoff", LATE)["rows"]
        self.assertFalse(any(r["relationship"]["prior_contest_key"] == r["relationship"]["target_contest_key"]
                             for r in rels))

    def test_cutoff_position_is_a_conservative_date_boundary_not_a_kickoff(self) -> None:
        at = history("ncaa:1003", "A", "2019-09-06T10:00:00Z")["cutoff_position"]
        before = history("ncaa:1003", "A", "2019-09-06T09:59:59.999999Z")["cutoff_position"]
        self.assertEqual(at["position"], "AT_OR_AFTER_CONSERVATIVE_TARGET_DATE_BOUNDARY")
        self.assertEqual(before["position"], "BEFORE_CONSERVATIVE_TARGET_DATE_BOUNDARY")
        self.assertEqual(at["conservative_date_boundary_utc"], "2019-09-06T10:00:00.000000Z")
        self.assertIn("NOT_OBSERVED_KICKOFF", at["boundary_basis"])
        self.assertEqual((at["pregame_claim"], at["pit_admission"]), (False, "NOT_ADMITTED"))
        doc = ok("--grain", "target", "--cutoff", LATE, "--limit", "1")
        self.assertEqual((doc["pit_admission"], doc["pit_admission_state"], doc["pregame_claim"]),
                         ("NOT_ADMITTED", "NOT_ADMITTED", False))

    def test_prior_evidence_serves_versions_and_witnesses(self) -> None:
        row = ok("--grain", "prior-evidence", "--contest", "ncaa:1002", "--cutoff", "2019-09-01T00:00:00Z")["rows"][0]
        archive = row["prior_evidence"]["archive"]
        self.assertEqual(len(archive["versions"]), 2)
        self.assertEqual(row["coherent_version_at_or_before_cutoff"], [])
        self.assertTrue(row["witnesses"])
        self.assertEqual(ok("--grain", "prior-evidence", "--contest", "ncaa:1002", "--cutoff", LATE)["rows"][0][
            "coherent_version_at_or_before_cutoff"], archive["coherent_capture_ids"])


class FrontAndIntegrityTests(unittest.TestCase):
    def module(self, *argv: str) -> subprocess.CompletedProcess:
        spec = Path(STATE["world"]["authority_spec"]).read_text(encoding="utf-8")
        return subprocess.run([sys.executable, "-B", "-c", fx.BOOTSTRAP, spec, "--database", str(STATE["db"]),
                               *fx.parent_args(STATE["world"]), *argv], capture_output=True, text=True,
                              encoding="utf-8", env=fx.child_env(), check=False)

    @unittest.skipUnless(sys.platform == "win32", "Windows extended-length paths")
    def test_readonly_uri_keeps_the_extended_prefix_of_the_literal_file(self) -> None:
        # BAT-717 (Cycle #45) supersedes the Cycle #42 expectation that the prefix is stripped: the stripped spelling
        # cannot be opened beyond 260 characters on a host without long-path support and, for a verbatim name that
        # Win32 normalization changes (a trailing-dot directory), it names a different file than the verbatim one.
        self.assertEqual(aq.readonly_uri(aq.EXTENDED_PREFIX + "C:\\data\\x y\\db.sqlite"),
                         "file:%5C%5C%3F%5CC%3A%5Cdata%5Cx%20y%5Cdb.sqlite?mode=ro")
        self.assertEqual(aq.readonly_uri(STATE["db"]), Path(STATE["db"]).absolute().as_uri() + "?mode=ro")

    def test_module_front_equals_console_entry_and_refuses_cleanly(self) -> None:
        argv = ("--grain", "history", "--contest", "ncaa:1005", "--cutoff", fx.CONTROL_BOUND)
        proc = self.module(*argv)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), ok(*argv))
        proc = self.module("--grain", "history", "--cutoff", LATE, "--require-pit")
        self.assertEqual((proc.returncode, fx.refusal(proc.stderr)), (2, "PIT_ADMISSION_NOT_ESTABLISHED"))
        self.assertNotIn("Traceback", proc.stderr)
        proc = self.module("--grain", "history", "--cutoff", LATE, "--history-database",
                           str(STATE["world"]["paths"]["population"]))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_unissued_authority_wrong_parent_and_tampered_bytes_refuse(self) -> None:
        self.assertEqual(refused("--grain", "history", "--cutoff", LATE, register=False),
                         "PROJECTION_CONTRACT_NOT_ISSUED")
        self.assertEqual(refused("--grain", "history", "--cutoff", LATE, "--history-database",
                                 str(STATE["world"]["paths"]["population"])), "DATABASE_LOCATION_INVALID")
        base = Path(STATE["tmp"].name) / "bytes"
        root = STATE["db"].parents[3]
        shutil.copytree(root, base / "canonical")
        shutil.copytree(root.parent / "manifests", base / "manifests")
        copied = base / "canonical" / STATE["db"].relative_to(root)
        data = bytearray(copied.read_bytes())
        data[-100] ^= 1
        copied.write_bytes(bytes(data))
        self.assertEqual(refused("--grain", "history", "--cutoff", LATE, database=copied), "DATABASE_TAMPERED")

    def test_rehashed_semantic_forgeries_refuse_for_their_own_rule(self) -> None:
        world, result = STATE["world"], STATE["result"]
        pool = lambda r: r.get("relationship_class") == "HISTORY_POOL_PRIOR"  # noqa: E731

        def swap(r):
            pr = r["parent_result"]
            return dict(r, prior_side="B" if r["prior_side"] == "A" else "A",
                        parent_result=dict(pr, points_for=pr["points_against"], points_against=pr["points_for"],
                                           result={"W": "L", "L": "W", "T": "T"}[pr["result"]]))

        def drop_relationship(conn):
            conn.execute("DELETE FROM relationships WHERE ord = (SELECT MAX(ord) FROM relationships)")

        def reintroduce_same_day(conn):
            row = json.loads(conn.execute("SELECT record FROM relationships ORDER BY ord LIMIT 1").fetchone()[0])
            row.update(prior_contest_key=row["target_contest_key"], prior_contest_date=row["target_date"])
            conn.execute("INSERT INTO relationships VALUES ((SELECT MAX(ord) + 1 FROM relationships), ?, ?, ?, ?, ?)",
                         (row["target_contest_key"], row["view"], row["team_key"], row["prior_contest_key"],
                          core.canonical_json_bytes(row).decode("utf-8")))

        def reorder(conn):
            conn.execute("UPDATE relationships SET ord = -1 WHERE ord = 0")
            conn.execute("UPDATE relationships SET ord = 0 WHERE ord = 1")
            conn.execute("UPDATE relationships SET ord = 1 WHERE ord = -1")

        def drop_version(e):
            archive = copy.deepcopy(e["archive"])
            archive["versions"] = archive["versions"][1:]
            return dict(e, archive=archive)

        def move_bound(e):
            archive = dict(e["archive"], coherent_upper_bound_utc="2019-09-08T01:30:00.999998Z")
            return dict(e, archive=archive)

        def promote_partial(e):
            archive = dict(e["archive"], evidence_class="ARCHIVE_COHERENT_VERSION",
                           evidence_reason="ONE_VERSION_QUALIFIES_ALL_SIX_FIELDS",
                           coherent_capture_ids=[e["archive"]["versions"][0]["capture_id"]],
                           coherent_upper_bound_utc=e["archive"]["versions"][0]["upper_bound_utc"])
            return dict(e, archive=archive)

        def stale_parent(document):
            document["parent"]["history"]["database_identity"] = "0" * 64

        def unissued_contract(document):
            document["contract_sha256"] = "f" * 64

        cases = {
            "RELATIONSHIP_COLLECTION_MISMATCH": (drop_relationship, None),
            "RELATIONSHIP_TEMPORAL_ORDER_VIOLATION": (reintroduce_same_day, None),
            "RECORD_ORDER_MISMATCH": (reorder, None),
            "RELATIONSHIP_ORIENTATION_MISMATCH": (fx.edit_record("relationships", lambda r: pool(r) and
                                                                 r["parent_result"]["result"] != "T", swap), None),
            "EVIDENCE_VERSION_COLLECTION_MISMATCH": (fx.edit_record("evidence", lambda e: len(
                e["archive"]["versions"]) == 2, drop_version), None),
            "EVIDENCE_SUPPORT_FORGERY": (fx.edit_record("evidence", lambda e: e["contest_key"] == fx.CONTROL_KEY,
                                                        move_bound), None),
            "EVIDENCE_SUPPORT_FORGERY/partial": (fx.edit_record("evidence", lambda e: e["archive"]["evidence_class"] ==
                                                                "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION",
                                                                promote_partial), None),
            "EVIDENCE_PARENT_VALUE_MISMATCH": (fx.edit_record("evidence", lambda e: e["parent_values"] is not None,
                                                              lambda e: dict(e, parent_values=dict(
                                                                  e["parent_values"], a_points=99))), None),
            "WITNESS_MISMATCH": (fx.edit_record("witnesses", lambda w: True, lambda w: dict(w, literal="99")), None),
            "VIEW_COUNT_MISMATCH": (fx.edit_record("views", lambda v: v["expected_prior_relationships"] > 0,
                                                   lambda v: dict(v, history_pool_priors=v["history_pool_priors"] + 1)),
                                    None),
            "VIEW_ORIENTATION_MISMATCH": (fx.edit_record("views", lambda v: True, lambda v: dict(
                v, team_key=v["opponent_key"], opponent_key=v["team_key"])), None),
            "TARGET_RECORD_MISMATCH": (fx.edit_record("targets", lambda t: True,
                                                      lambda t: dict(t, contest_date="2019-08-30")), None),
            "FORGED_AUTHORITY_LABEL": (fx.edit_record("relationships", lambda r: True,
                                                      lambda r: dict(r, pit_admission="ADMITTED")), None),
            "FORGED_AUTHORITY_LABEL/meta": (fx.edit_meta("row_labels", json.dumps(dict(
                core.ROW_LABELS, training_eligibility="ELIGIBLE"), sort_keys=True)), None),
            "FORGED_AUTHORITY_LABEL/rule": (fx.edit_meta("support_rule", "ANY_FIELD_FROM_ANY_VERSION"), None),
            "PARENT_NOT_ISSUED": (lambda conn: conn.execute("UPDATE meta SET value = ? WHERE key = 'parent'", (
                json.dumps(dict(world["parent"], history=dict(world["parent"]["history"],
                                                              database_identity="0" * 64)), sort_keys=True),)),
                                  stale_parent),
            "PROJECTION_CONTRACT_NOT_ISSUED": (fx.edit_meta("contract_sha256", "f" * 64), unissued_contract),
        }
        for index, (name, (mutate, patch)) in enumerate(cases.items()):
            expected = name.split("/")[0]
            # short directory names keep the rehashed database path within MAX_PATH under long temp roots
            db = fx.rehashed_copy(world, result, Path(STATE["tmp"].name) / f"f{index:02d}", mutate, patch)
            self.assertEqual(refused("--grain", "history", "--cutoff", LATE, database=db), expected, name)

    def test_displayed_content_identity_is_recomputed_from_the_verified_payloads(self) -> None:
        result = STATE["result"]
        content = json.loads(Path(result["content"]["manifest"]).read_text(encoding="utf-8"))["identity_document"]
        expected = independent_content_identity(STATE["db"], content)
        self.assertEqual(expected, result["content_identity"])
        self.assertEqual(ok("--grain", "target", "--cutoff", LATE, "--limit", "1")["binding"]["content_identity"],
                         expected)
        # the consumer's stored-payload encoding is the producer's (gzip, mtime 0, no file name)
        data = b'{"a":1}\n' * 50
        self.assertEqual(aq.gzip_mtime0(data), fx.builder().gzip_bytes(data))

    def test_content_binding_claims_refuse_for_their_own_rule(self) -> None:
        world, result = STATE["world"], STATE["result"]
        conn = sqlite3.connect(f"file:{STATE['db'].absolute().as_posix()}?mode=ro", uri=True)
        genuine_meta = dict(conn.execute("SELECT key, value FROM meta"))
        conn.close()
        content_manifest = Path(result["content"]["manifest"])
        content = json.loads(content_manifest.read_text(encoding="utf-8"))
        # a coordinated, self-consistent alternative: its own content document and artifact, its own identity claimed
        # by the meta and the manifest, and the meta's restated payload schema changed to match it
        alternative_schema = "BAS-NATIONAL-HISTORY-AVAILABILITY-PAYLOAD-ADMITTED-1"
        document = dict(content["identity_document"], payload_schema=alternative_schema)
        alternative = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"),
                                                ensure_ascii=False).encode("utf-8")).hexdigest()
        base = Path(STATE["tmp"].name) / "cb"
        shutil.copytree(result["content"]["data_dir"], base / "canonical" / core.POPULATION / "sha256" / alternative)
        mdir = base / "manifests" / core.POPULATION / "sha256" / alternative
        mdir.mkdir(parents=True)
        (mdir / "run_manifest.json").write_text(json.dumps({"identity": alternative, "identity_document": document}),
                                                encoding="utf-8")
        cases = content_binding_cases(genuine_meta, world["parent"]["archive"]["content_identity"], alternative,
                                      alternative_schema)
        databases = {}
        for index, (name, (mutate, patch)) in enumerate(cases.items()):
            db = fx.rehashed_copy(world, result, Path(STATE["tmp"].name) / f"c{index:02d}", mutate, patch)
            databases[name] = db
            self.assertEqual(refused("--grain", "history", "--cutoff", LATE, database=db), name.split("/")[0], name)
        # the python -m module front reaches the same rule
        spec = Path(world["authority_spec"]).read_text(encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", "-c", fx.BOOTSTRAP, spec, "--database",
                               str(databases["CONTENT_IDENTITY_MISMATCH/invented"]), *fx.parent_args(world),
                               "--grain", "target", "--cutoff", LATE], capture_output=True, text=True,
                              encoding="utf-8", env=fx.child_env(), check=False)
        self.assertEqual((proc.returncode, fx.refusal(proc.stderr)), (2, "CONTENT_IDENTITY_MISMATCH"))
        self.assertNotIn("Traceback", proc.stderr)

    def test_queries_never_write(self) -> None:
        for grain in ("target", "history", "relationship", "prior-evidence"):
            ok("--grain", grain, "--all", "--cutoff", LATE)
        self.assertEqual(fx.sha(STATE["db"].read_bytes()), STATE["db_sha"])

    @unittest.skipUnless(sys.platform == "win32", "Windows native extended-length spelling")
    def test_a_long_extended_location_serves_the_same_answers(self) -> None:
        # BAT-717: a byte-identical copy of the whole synthetic world (projection, manifests, parents and the archive
        # sidecar's raw store) beyond 260 characters, read through the native extended-length spelling.
        base = str(STATE["world"]["base"])
        top = aq.EXTENDED_PREFIX + os.path.join(str(Path(STATE["tmp"].name).resolve()), "long " + "x" * 120)
        far = os.path.join(top, "deeper # % é ' " + "y" * 120)
        self.addCleanup(shutil.rmtree, top)  # removable only through the verbatim spelling
        self.assertTrue(str(STATE["db"]).startswith(base))
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                source = os.path.join(dirpath, name)
                target = far + source[len(base):]
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(source, target)
        moved = {k: far + str(v)[len(base):] for k, v in STATE["world"]["paths"].items()}
        database = far + str(STATE["db"])[len(base):]
        self.assertGreater(len(database), 300)
        parents = ["--population-database", moved["population"], "--history-database", moved["history"],
                   "--source-time-database", moved["source_time"], "--archive-database", moved["archive"]]
        for grain in ("target", "history", "relationship", "prior-evidence"):
            code, doc, err = self.far_query(database, parents, grain)
            self.assertEqual(code, 0, err)
            self.assertEqual(doc, ok("--grain", grain, "--all", "--cutoff", LATE), grain)
        self.assertEqual(fx.sha(Path(database).read_bytes()), STATE["db_sha"])

    @staticmethod
    def far_query(database: str, parents: list[str], grain: str) -> tuple[int, dict | None, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with fx.authorities(STATE["world"]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = aq.main(["--database", database, *parents, "--grain", grain, "--all", "--cutoff", LATE])
            except SystemExit as exc:
                code = exc.code
        text = stdout.getvalue()
        return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


MOUNTED = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or "")
GATE = fx.ROOT / "artifacts" / "data_lake" / "national_history_availability_2019_gate.json"


@unittest.skipUnless(GATE.is_file() and os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") and
                     (MOUNTED / "canonical" / core.POPULATION).is_dir(), "the delivered projection is not mounted")
class MountedContentBindingTests(unittest.TestCase):
    """The delivered projection's displayed content identity (MF42A01-01): genuine equals the independent digest;
    invented, missing, wrong and coordinated self-consistent claims on rehashed owned copies refuse for their rule."""

    def test_delivered_content_identity_and_rehashed_claims(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        db = MOUNTED / "canonical" / core.POPULATION / "sha256" / gate["database_identity"] / core.DB_FILE
        manifest = MOUNTED / "manifests" / core.POPULATION / "sha256" / gate["database_identity"] / "run_manifest.json"
        parents = []
        for name, (population, filename) in core.PARENT_FILES.items():
            ident = gate["parent"][name]["query_db_identity" if name == "population" else "database_identity"]
            parents += [f"--{name.replace('_', '-')}-database",
                        str(MOUNTED / "canonical" / population / "sha256" / ident / filename)]
        expected = independent_content_identity(db, gate["content_identity_document"])
        self.assertEqual(expected, gate["content_identity"])

        def serve(database: Path) -> tuple[int, dict | None, str]:
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = aq.main(["--database", str(database), *parents, "--grain", "target", "--cutoff", LATE,
                                "--limit", "1"])
            text = stdout.getvalue()
            return code, (json.loads(text) if text.strip() else None), stderr.getvalue()
        code, doc, err = serve(db)
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["binding"]["content_identity"], expected)
        conn = sqlite3.connect(f"file:{db.absolute().as_posix()}?mode=ro", uri=True)
        genuine_meta = dict(conn.execute("SELECT key, value FROM meta"))
        conn.close()
        alternative_schema = "BAS-NATIONAL-HISTORY-AVAILABILITY-PAYLOAD-ADMITTED-1"
        alternative_document = dict(gate["content_identity_document"], payload_schema=alternative_schema)
        alternative = hashlib.sha256(json.dumps(alternative_document, sort_keys=True, separators=(",", ":"),
                                                ensure_ascii=False).encode("utf-8")).hexdigest()
        cases = content_binding_cases(genuine_meta, gate["parent"]["archive"]["content_identity"], alternative,
                                      alternative_schema)
        chosen = ("CONTENT_IDENTITY_MISMATCH/invented", "CONTENT_IDENTITY_MISSING/both",
                  "CONTENT_IDENTITY_MISMATCH/wrong", "CONTENT_IDENTITY_MISMATCH/self-consistent",
                  "CONTENT_DECLARATION_MISMATCH/payload-hashes")
        source = json.loads(manifest.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, name in enumerate(chosen):
                mutate, patch = cases[name]
                work = Path(tmp) / f"w{index}.sqlite"
                shutil.copyfile(db, work)
                conn = sqlite3.connect(work)
                mutate(conn)
                conn.commit()
                counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in core.TABLES}
                conn.close()
                document = copy.deepcopy(source["identity_document"])
                if patch is not None:
                    patch(document)
                document["outputs"][core.DB_FILE] = fx.sha(work.read_bytes())
                document["table_counts"] = counts
                ident = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"),
                                                  ensure_ascii=False).encode("utf-8")).hexdigest()
                target = Path(tmp) / f"m{index}" / "canonical" / core.POPULATION / "sha256" / ident / core.DB_FILE
                target.parent.mkdir(parents=True)
                os.replace(work, target)
                mdir = Path(tmp) / f"m{index}" / "manifests" / core.POPULATION / "sha256" / ident
                mdir.mkdir(parents=True)
                (mdir / "run_manifest.json").write_text(json.dumps({"identity": ident, "identity_document": document}),
                                                        encoding="utf-8")
                code, _doc, err = serve(target)
                self.assertEqual((code, fx.refusal(err)), (2, name.split("/")[0]), name)


if __name__ == "__main__":
    unittest.main()
