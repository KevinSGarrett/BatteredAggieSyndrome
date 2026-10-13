"""Natural-grain regression probes for the independent system audit findings."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from aggie_analytics.orchestration import (
    ImmutableForecastPublisher, LocalCheckpointStore, LocalWeeklyOrchestrator,
    WeeklyRunIdentity, StepResult, result,
)
from aggie_analytics.orchestration.contracts import stable_hash
from aggie_analytics.product import PublishedSnapshotRepository, ForecastProductService, SnapshotNotFound
from aggie_analytics.experimentation.store import ExperimentStore
from aggie_analytics.experimentation.queue import make_event
from aggie_analytics.experimentation.lineage import content_hash
from aggie_analytics.experimentation.hpo_engine import DiscreteParameter, enumerate_trials, run_trials
from aggie_analytics.operations.drift_alerts import (
    AlertLedger, DriftRule, DriftObservation, evaluate_drift, validate_alert_snapshot, canonical_sha256,
)

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


class OwnedFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)


class PublicationBoundaryTests(OwnedFixture):
    def publish(self, **changes):
        kw = dict(snapshot_id="s1", game_id="g1", forecast_cutoff=NOW-timedelta(days=1),
                  model_artifact_sha256="synthetic-model", feature_snapshot_id="synthetic-feature",
                  public_summary={"win_probability": .5}, lineage_refs=("synthetic",))
        return Path(ImmutableForecastPublisher(self.root / "published").publish(**(kw | changes)))

    def repository(self, **options):
        return PublishedSnapshotRepository(self.root / "published", **options)

    def test_publication_rejects_identifiers_before_any_game_write(self):
        # Literal drive/UNC spellings must never reach the filesystem, including
        # when this regression is deliberately run against the unfixed publisher.
        publisher = ImmutableForecastPublisher(self.root / "published")
        for field in ("game_id", "snapshot_id"):
            for value in ("../outside", "..\\outside", "C:\\outside", "\\\\host\\share", "/outside", "a/b", "a\\b", "a*", "a?", ".", "..", "CON", "a."):
                with self.subTest(field=field, value=value), patch.object(Path, "mkdir", side_effect=AssertionError("unexpected filesystem create")) as create, self.assertRaises(ValueError):
                    publisher.publish(snapshot_id=value if field == "snapshot_id" else "s1", game_id=value if field == "game_id" else "g1",
                                      forecast_cutoff=NOW, model_artifact_sha256="m", feature_snapshot_id="f", public_summary={}, lineage_refs=("synthetic",))
                self.assertEqual(0, create.call_count)
                self.assertEqual([], list((self.root / "published").iterdir()))

    def test_owned_traversal_is_refused(self):
        # The unfixed producer can create only inside this test's own root.
        with self.assertRaises(ValueError):
            self.publish(game_id="../owned-escape")
        self.assertFalse((self.root / "owned-escape").exists())

    def test_game_binding_applies_to_all_serving_selections(self):
        path = self.publish()
        other = path.parent.parent / "g2"
        other.mkdir()
        (other / path.name).write_bytes(path.read_bytes())
        repo = self.repository()
        for select in (lambda: repo.get("g2", "s1"), lambda: repo.latest("g2", as_of=NOW+timedelta(days=2)),
                       lambda: repo.list_snapshots("g2"), repo.list_games,
                       lambda: ForecastProductService(repo).forecast("g2", now=NOW+timedelta(days=2))):
            with self.assertRaisesRegex(ValueError, "game identity mismatch"):
                select()

    def test_hash_name_and_idempotent_publish_refuse_changed_content(self):
        path = self.publish()
        self.assertEqual(path, self.publish())
        payload = json.loads(path.read_bytes())
        payload["public_summary"]["win_probability"] = .9
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "content identity mismatch"):
            self.repository().get("g1", "s1")
        with self.assertRaisesRegex(RuntimeError, "content identity mismatch"):
            self.publish()
        pins = {path.relative_to(path.parent.parent).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(ValueError, "content identity mismatch"):
            self.repository(legacy_artifact_sha256=pins).get("g1", "s1")

    def test_idempotence_retains_original_publication_time(self):
        with patch("aggie_analytics.orchestration.publication.datetime") as clock:
            clock.now.return_value = NOW
            path = self.publish()
            original = path.read_bytes()
            clock.now.return_value = NOW+timedelta(days=1)
            self.assertEqual(path, self.publish())
        self.assertEqual(original, path.read_bytes())
        self.assertEqual(NOW, self.repository().get("g1", "s1").published_at)

    def test_simultaneous_owners_cannot_publish_two_timestamp_identities(self):
        original_glob = Path.glob
        local = threading.local()
        barrier = threading.Barrier(2)
        def interleaved_glob(path, pattern):
            values = list(original_glob(path, pattern))
            if path.name == "g1" and pattern == "s1-*.json" and not getattr(local, "scanned", False):
                local.scanned = True
                barrier.wait(timeout=5)
            return iter(values)
        class Clock:
            @classmethod
            def now(cls, tz):
                return NOW + timedelta(seconds=local.second)
        def writer(second):
            local.second = second
            try:
                return self.publish()
            except RuntimeError as exc:
                return exc
        with patch.object(Path, "glob", interleaved_glob), patch("aggie_analytics.orchestration.publication.datetime", Clock):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(writer, second) for second in (1, 2)]
                outcomes = [future.result(timeout=10) for future in futures]
        successes = [item for item in outcomes if isinstance(item, Path)]
        self.assertGreaterEqual(len(successes), 1)
        self.assertEqual(1, len(set(successes)))
        for item in outcomes:
            if isinstance(item, Exception):
                self.assertIn("publication already in progress", str(item))
        self.assertEqual(1, len(self.repository().list_snapshots("g1")))
        self.assertEqual("s1", self.repository().get("g1", "s1").snapshot_id)
        first = successes[0].read_bytes()
        self.assertEqual(successes[0], self.publish())
        self.assertEqual(first, successes[0].read_bytes())
        self.assertFalse((successes[0].parent / ".s1.publish-claim").exists())

    def test_existing_publication_claim_is_not_broken_or_reused(self):
        directory = self.root / "published" / "g1"
        directory.mkdir(parents=True)
        claim = directory / ".s1.publish-claim"
        claim.write_bytes(b"retained other owner")
        with self.assertRaisesRegex(RuntimeError, "publication already in progress"):
            self.publish()
        self.assertEqual(b"retained other owner", claim.read_bytes())
        self.assertEqual([], list(directory.glob("s1-*.json")))
        # Another snapshot has a distinct claim and remains available.
        self.publish(snapshot_id="s2")

    def test_owned_publication_failure_releases_claim_without_overwrite(self):
        with patch("aggie_analytics.orchestration.publication.os.link", side_effect=OSError("injected local write failure")):
            with self.assertRaisesRegex(OSError, "injected local write failure"):
                self.publish()
        directory = self.root / "published" / "g1"
        self.assertEqual([], list(directory.iterdir()))
        first = self.publish()
        original = first.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "different content"):
            self.publish(public_summary={"win_probability": .9})
        self.assertEqual(original, first.read_bytes())

    def test_legacy_is_exact_pinned_not_a_filename_downgrade(self):
        path = self.publish(schema_version="aggie.forecast.snapshot.v1")
        payload = json.loads(path.read_bytes()); payload.pop("publication_format")
        path.write_text(json.dumps(payload), encoding="utf-8")
        legacy = path.with_name("s1-PURE_FOOTBALL.json")
        path.rename(legacy)
        with self.assertRaisesRegex(ValueError, "exact artifact pin"):
            self.repository().get("g1", "s1")
        relative = legacy.relative_to(legacy.parent.parent).as_posix()
        repo = self.repository(legacy_artifact_sha256={relative: hashlib.sha256(legacy.read_bytes()).hexdigest()})
        self.assertEqual("aggie.forecast.snapshot.v1", repo.get("g1", "s1").schema_version)
        legacy.write_bytes(legacy.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "exact artifact pin"):
            repo.get("g1", "s1")

    def test_publication_time_is_bound_and_old_format_needs_exact_bytes(self):
        path = self.publish()
        original = path.read_bytes()
        payload = json.loads(original); payload["published_at"] = (NOW-timedelta(hours=2)).isoformat()
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "content identity mismatch"):
            self.repository().latest("g1", as_of=NOW)
        payload.pop("publication_format")
        path.write_text(json.dumps(payload), encoding="utf-8")
        legacy = path.with_name("s1-"+stable_hash({k:v for k,v in payload.items() if k != "published_at"})+".json")
        path.rename(legacy)
        with self.assertRaisesRegex(ValueError, "exact artifact pin"):
            self.repository().latest("g1", as_of=NOW)
        pins = {legacy.relative_to(legacy.parent.parent).as_posix(): hashlib.sha256(legacy.read_bytes()).hexdigest()}
        self.assertEqual("s1", self.repository(legacy_artifact_sha256=pins).latest("g1", as_of=NOW).snapshot_id)
        payload["published_at"] = (NOW-timedelta(hours=1)).isoformat()
        legacy.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exact artifact pin"):
            self.repository(legacy_artifact_sha256=pins).latest("g1", as_of=NOW)

    def test_publisher_refuses_linked_game_and_snapshot(self):
        pub = self.root / "published"
        outside = self.root / "outside"
        pub.mkdir(); outside.mkdir()
        link = pub / "g1"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "escapes root"):
            self.publish()
        self.assertEqual([], list(outside.iterdir()))

    def test_multiple_snapshots_lane_and_missing_game_remain_supported(self):
        self.publish()
        self.publish(snapshot_id="s2", market_lane="MARKET_AUGMENTED")
        repo = self.repository()
        self.assertEqual(2, len(repo.list_snapshots("g1")))
        self.assertEqual("s2", repo.get("g1", "s2", market_lane="MARKET_AUGMENTED").snapshot_id)
        self.assertEqual((), repo.list_snapshots("missing"))
        with self.assertRaises(SnapshotNotFound):
            repo.latest("missing", as_of=NOW)


class CheckpointBoundaryTests(OwnedFixture):
    def setup_run(self, output=None):
        store = LocalCheckpointStore(self.root)
        identity = WeeklyRunIdentity("test-run", "week", NOW)
        calls = []
        def step(identity, prior):
            calls.append("INGEST")
            return output or result("INGEST", {"valid": True})
        orchestrator = LocalWeeklyOrchestrator(store, {"INGEST": step}, ("INGEST",))
        self.assertEqual("SUCCEEDED", orchestrator.run(identity).status)
        return store, identity, calls, orchestrator

    def test_corrupt_success_never_skips_execution_as_success(self):
        store, identity, calls, orch = self.setup_run()
        path = self.root / "test-run/steps/INGEST.json"
        original = path.read_bytes()
        for field, value in (("step_id", "UNRELATED"), ("output_ref", ""), ("output_hash", ""),
                             ("output_hash", "z"*64), ("output_ref", "memory:OTHER:"+"a"*16), ("detail", "changed")):
            for rehash in (False, True):
                item = json.loads(original); item[field] = value
                if rehash:
                    item["result_sha256"] = stable_hash({k: v for k, v in item.items() if k not in {"checkpoint_schema", "result_sha256"}})
                # Detail may legitimately be different when independently reidentified.
                if field == "detail" and rehash:
                    continue
                path.write_text(json.dumps(item), encoding="utf-8")
                with self.subTest(field=field, rehash=rehash), self.assertRaises((ValueError, RuntimeError)):
                    orch.run(identity)
        path.write_bytes(original)
        self.assertTrue(orch.run(identity).resumed)
        self.assertEqual(["INGEST"], calls)

    def test_local_artifact_content_is_verified_on_resume(self):
        artifact = self.root / "output.bin"
        artifact.write_bytes(b"first")
        output = StepResult("INGEST", "SUCCEEDED", artifact.as_uri(), hashlib.sha256(b"first").hexdigest())
        store, identity, calls, orch = self.setup_run(output)
        self.assertEqual("SUCCEEDED", orch.run(identity).status)
        artifact.write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "artifact identity mismatch"):
            orch.run(identity)
        self.assertEqual(["INGEST"], calls)

    def test_legacy_requires_pin_and_opaque_artifact_keeps_claim_semantics(self):
        store, identity, calls, orch = self.setup_run(result("INGEST", {"ok": True}, output_ref="artifact:INGEST"))
        path = self.root / "test-run/steps/INGEST.json"
        item = json.loads(path.read_bytes()); item.pop("checkpoint_schema"); item.pop("result_sha256")
        item.pop("run_id"); item.pop("run_fingerprint")
        path.write_text(json.dumps(item), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "legacy checkpoint requires"):
            store.get(identity.run_id, "INGEST")
        pinned = LocalCheckpointStore(self.root, legacy_step_sha256={"test-run/steps/INGEST.json": hashlib.sha256(path.read_bytes()).hexdigest()})
        self.assertEqual("artifact:INGEST", pinned.get(identity.run_id, "INGEST").output_ref)
        path.write_bytes(path.read_bytes()+b"\n")
        with self.assertRaisesRegex(RuntimeError, "legacy checkpoint requires"):
            pinned.get(identity.run_id, "INGEST")

    def test_wrong_run_payload_and_unsafe_step_rejected(self):
        store, identity, calls, orch = self.setup_run()
        path = self.root / "test-run/run.json"
        payload = json.loads(path.read_bytes()); payload["forecast_week"] = "other"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "different immutable identity"):
            orch.run(identity)
        with self.assertRaisesRegex(ValueError, "unsafe checkpoint"):
            store.get(identity.run_id, "../outside")

    def test_checkpoint_cannot_replay_under_another_run_identity(self):
        store, identity, calls, orch = self.setup_run()
        second = WeeklyRunIdentity("second", "other-week", NOW, ("other-source",))
        store.initialize(second)
        target = self.root / "second/steps/INGEST.json"
        target.parent.mkdir()
        target.write_bytes((self.root / "test-run/steps/INGEST.json").read_bytes())
        with self.assertRaisesRegex(RuntimeError, "run identity mismatch"):
            orch.run(second)
        self.assertEqual(["INGEST"], calls)


class ExperimentBoundaryTests(OwnedFixture):
    def create_store(self, name="store.sqlite"):
        store = ExperimentStore(self.root / name)
        store.initialize()
        eid = store.add_experiment({"target": "margin", "split": "development", "config": {"n": 3}})
        e0 = make_event(experiment_id=eid, state="PROPOSED", actor_role="research_agent", reason="proposed", event_index=0)
        e1 = make_event(experiment_id=eid, state="APPROVED", actor_role="research_governor", reason="reviewed", event_index=1, previous_event_hash=e0["event_hash"])
        store.append_queue_event(e0); store.append_queue_event(e1)
        rid = store.add_result({"experiment_id": eid, "attempt": 1, "metrics": {"mae": 7.1}})
        store.add_artifact(experiment_id=eid, attempt=1, class_name="report", uri="artifact:report", sha256="a"*64, size_bytes=7)
        return store, eid, rid

    def test_every_stored_payload_and_chain_checked_before_read(self):
        mutations = (
            "UPDATE experiment_specs SET payload_json='{}'",
            "UPDATE experiment_specs SET spec_sha256='wrong'",
            "UPDATE queue_events SET reason='changed' WHERE event_index=0",
            "UPDATE queue_events SET event_hash='wrong' WHERE event_index=1",
            "UPDATE queue_events SET previous_event_hash='wrong' WHERE event_index=1",
            "DELETE FROM queue_events WHERE event_index=0",
            "UPDATE queue_events SET event_index=5 WHERE event_index=1",
            "UPDATE result_packets SET payload_json='{}'",
            "UPDATE result_packets SET result_sha256='wrong'",
            "UPDATE artifact_records SET uri='artifact:changed'",
            "UPDATE result_packets SET experiment_id='missing'",
        )
        for n, mutation in enumerate(mutations):
            store, eid, rid = self.create_store(f"store{n}.sqlite")
            self.assertEqual([], store.integrity_check())
            with closing(sqlite3.connect(store.path)) as conn:
                conn.execute(mutation)
                conn.commit()
            with self.subTest(mutation=mutation):
                self.assertTrue(store.integrity_check())
                for read in (lambda: store.get_experiment(eid), store.list_experiments, lambda: store.queue_history(eid)):
                    with self.assertRaisesRegex(ValueError, "store integrity failure"):
                        read()

    def test_append_rejects_forged_event_and_preserves_genuine_chain(self):
        store, eid, rid = self.create_store()
        previous = store.queue_history(eid)[-1]["event_hash"]
        event = make_event(experiment_id=eid, state="QUEUED", actor_role="scheduler", reason="queued", event_index=2, previous_event_hash=previous)
        bad = {**event, "reason": "forged"}
        with self.assertRaisesRegex(ValueError, "content identity mismatch"):
            store.append_queue_event(bad)
        store.append_queue_event(event)
        self.assertEqual([], store.integrity_check())
        self.assertEqual(3, len(store.queue_history(eid)))
        self.assertEqual(eid, store.add_experiment(store.get_experiment(eid).payload))

    def test_replay_payload_and_cross_experiment_reference_checked(self):
        store, eid, rid = self.create_store()
        payload = {"experiment_id": eid, "source_result_id": rid, "checks": {"same": True}}
        with store.connect() as conn:
            conn.execute("INSERT INTO replay_reports VALUES (?,?,?,?,?,?,?)", ("rep-1", eid, rid, json.dumps(payload), content_hash(payload), "VERIFIED", "now"))
        self.assertEqual([], store.integrity_check())
        with store.connect() as conn:
            conn.execute("UPDATE replay_reports SET payload_json='{}'")
        self.assertTrue(store.integrity_check())

    def test_replay_status_derived_from_checks_and_failure_code(self):
        for n, payload_delta in enumerate(({"checks": {"same": False}}, {"failure_code": "HASH_MISMATCH"}, {"checks": {}}, {"checks": {"same": "true"}})):
            store, eid, rid = self.create_store(f"replay{n}.sqlite")
            payload = {"experiment_id": eid, "attempt_id": "attempt-1", "checks": {"same": True}, "failure_code": None} | payload_delta
            with store.connect() as conn:
                conn.execute("INSERT INTO replay_reports VALUES (?,?,?,?,?,?,?)", ("rep-1", eid, rid, json.dumps(payload), content_hash(payload), "VERIFIED", "now"))
            with self.subTest(delta=payload_delta):
                self.assertTrue(store.integrity_check())


class HPOBoundaryTests(unittest.TestCase):
    def test_nonfinite_objectives_are_failed_not_complete(self):
        trials = enumerate_trials("study", [DiscreteParameter("x", [0, 1, 2])], 3)
        for value in (math.nan, math.inf, -math.inf):
            for failure_value in (None, -99):
                with self.subTest(value=value, failure_value=failure_value):
                    results = run_trials(trials, lambda _: value, failure_value=failure_value)
                    self.assertEqual(3, len(results))
                    self.assertEqual(["FAILED"]*3, [r.state for r in results])
                    self.assertEqual(["InvalidObjectiveError"]*3, [r.reason for r in results])
        genuine = run_trials(trials, lambda p: p["x"]-1)
        self.assertEqual([-1., 0., 1.], [r.objective for r in genuine])
        self.assertEqual(["COMPLETE"]*3, [r.state for r in genuine])

    def test_exception_and_finite_failure_value_remain_distinct(self):
        trial = enumerate_trials("study", [], 1)
        def failed(_):
            raise LookupError("no source")
        out = run_trials(trial, failed, failure_value=0)
        self.assertEqual(("FAILED", "LookupError", 0.), (out[0].state, out[0].reason, out[0].objective))
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaisesRegex(ValueError, "failure_value must be finite"):
                run_trials(trial, failed, failure_value=value)


class AlertBoundaryTests(unittest.TestCase):
    def evaluation(self, *, clear=False, minute=0, terms=False):
        rule = DriftRule("rule", "TERMS_METADATA" if terms else "SCHEMA", "source/original", "EXACT_IDENTITY", "a"*64, "b"*64,
                         "WARNING" if terms else "HIGH", "METADATA_ONLY_NONBLOCKING" if terms else "QUARANTINE_AFFECTED_SCOPE")
        stamp = f"2026-10-13T06:{minute:02d}:00Z"
        return evaluate_drift(rule, DriftObservation("a"*64 if clear else "c"*64, "d"*64, stamp), evaluated_at_utc=stamp)

    @staticmethod
    def rehash(snapshot):
        for record in snapshot["records"]:
            previous = None
            for transition in record["transitions"]:
                transition["previous_transition_identity"] = previous
                transition["transition_identity"] = canonical_sha256({k: v for k, v in transition.items() if k != "transition_identity"})
                previous = transition["transition_identity"]
        snapshot["snapshot_identity"] = canonical_sha256({k: v for k, v in snapshot.items() if k != "snapshot_identity"})

    def test_record_and_transition_forgeries_refused_after_rehash(self):
        ledger = AlertLedger(); aid = ledger.ingest(self.evaluation())
        original = ledger.snapshot()
        for field, value in (("scope_id", "source/unrelated"), ("rule_identity", "f"*64), ("current_severity", "INFO"), ("status", "ACKNOWLEDGED")):
            bad = copy.deepcopy(original); bad["records"][0][field] = value; self.rehash(bad)
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_alert_snapshot(bad)
        for change in ("wrong-first", "wrong-details", "wrong-evidence", "unknown-type", "no-opening"):
            bad = copy.deepcopy(original)
            transition = bad["records"][0]["transitions"][0]
            if change == "wrong-first": transition["transition_type"] = "ACKNOWLEDGED"
            elif change == "wrong-details": transition["details"]["evaluation_identity"] = "f"*64
            elif change == "wrong-evidence": transition["evidence_sha256"] = "f"*64
            elif change == "unknown-type": transition["transition_type"] = "UNKNOWN"
            else: bad["records"][0]["transitions"] = []
            self.rehash(bad)
            with self.subTest(change=change), self.assertRaises(ValueError): validate_alert_snapshot(bad)

    def test_genuine_lifecycle_and_rehashed_invalid_escalation(self):
        ledger = AlertLedger(); aid = ledger.ingest(self.evaluation())
        ledger.acknowledge(aid, actor_id="operator", evidence_sha256="e"*64, occurred_at_utc="2026-10-13T06:01:00Z")
        ledger.escalate(aid, to_severity="CRITICAL", escalation_rule_id="rule-2", actor_id="operator", evidence_sha256="e"*64, occurred_at_utc="2026-10-13T06:02:00Z")
        ledger.ingest(self.evaluation(minute=3))
        genuine = ledger.snapshot(); validate_alert_snapshot(genuine)
        for value in ("WARNING", "INFO"):
            bad = copy.deepcopy(genuine); bad["records"][0]["transitions"][2]["details"]["to_severity"] = value
            bad["records"][0]["current_severity"] = value; self.rehash(bad)
            with self.assertRaisesRegex(ValueError, "increase derived severity"): validate_alert_snapshot(bad)
        ledger.resolve(aid, clearing_evaluation=self.evaluation(clear=True, minute=4), actor_id="operator", evidence_sha256="e"*64, occurred_at_utc="2026-10-13T06:05:00Z")
        validate_alert_snapshot(ledger.snapshot())

    def test_terms_metadata_remains_nonblocking_through_lifecycle(self):
        ledger = AlertLedger(); aid = ledger.ingest(self.evaluation(terms=True))
        with self.assertRaisesRegex(ValueError, "cannot exceed WARNING"):
            ledger.escalate(aid, to_severity="HIGH", escalation_rule_id="rule-2", actor_id="operator", evidence_sha256="e"*64, occurred_at_utc="2026-10-13T06:01:00Z")
        validate_alert_snapshot(ledger.snapshot())


if __name__ == "__main__":
    unittest.main()
