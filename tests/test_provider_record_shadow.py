"""BAT-725 UNTRUSTED_SHADOW snapshot: builder, reader and the explicit query mode (TP53-A01 sections 2-4)."""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
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
from argparse import ArgumentParser, Namespace
from fractions import Fraction
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import provider_record_baseline_preview_fixture as pfx  # noqa: E402
import provider_record_shadow_fixture as fx  # noqa: E402
from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402
from aggie_analytics.retrospective_baseline import preview, query, shadow  # noqa: E402
from tools import build_provider_record_shadow as builder  # noqa: E402

NULL, SMOOTH = preview.MODEL_NULL, preview.MODEL_SMOOTHED
UTC = dt.timezone.utc
#: The fixture anchor (2026-10-12T01:30:00.000-0500) as a UTC instant.
ANCHOR_UTC = dt.datetime(2026, 10, 12, 6, 30, tzinfo=UTC)
CUTOFF = "2026-10-12T07:00:00Z"
GATE = REPO_ROOT / "artifacts" / "data_lake" / "provider_record_shadow_20261017_gate.json"


def micro(moment: dt.datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="bat725-"))
        # snapshot directories nest the preview and capsule beyond MAX_PATH: remove through the extended form
        self.addCleanup(shutil.rmtree, fx.ext(self.tmp))
        self.counter = 0

    def fresh(self, name: str = "o") -> Path:
        self.counter += 1
        return self.tmp / f"{name}{self.counter}"

    def world(self, events=None, *, raw_doc=None) -> fx.ShadowWorld:
        return fx.ShadowWorld(self.fresh("w"), events, raw_doc=raw_doc)

    def run_cli(self, argv: list[str], world: fx.ShadowWorld | None, profile=None) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        kwargs = {} if world is None else {"shadow_contract_sha256": world.authority, "shadow_profile": profile}
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(argv, **kwargs)
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


class CommittedContractTests(unittest.TestCase):
    def test_reader_anchor_is_the_committed_contract_and_equals_the_code(self) -> None:
        data = fx.CONTRACT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), shadow.CONTRACT_SHA256)
        c = json.loads(data.decode("utf-8"))
        self.assertEqual((c["contract_id"], c["population_id"], c["designation"]),
                         (shadow.CONTRACT_ID, shadow.POPULATION, "UNTRUSTED_SHADOW"))
        self.assertEqual(c["models"], shadow._models_document())
        self.assertEqual(c["labels"], shadow.LABELS)
        self.assertEqual(c["record_labels"], shadow.RECORD_LABELS)
        self.assertEqual(c["numeric_contract"], shadow.NUMERIC_CONTRACT)
        self.assertEqual(c["timing_reasons"], shadow.TIMING_REASONS)
        self.assertEqual(c["payload"]["fields"], shadow.field_families())
        self.assertEqual(c["payload"]["top_level_members"], list(shadow.PAYLOAD_TOP))
        self.assertEqual(c["snapshot"]["top_level_members"], list(shadow.SNAPSHOT_TOP))
        self.assertEqual({k: c["anchor"][k] for k in shadow.ANCHOR_SPEC}, shadow.ANCHOR_SPEC)
        self.assertEqual(c["query_rules"]["grains"], list(shadow.GRAINS))
        self.assertEqual(c["query_rules"]["applicable_filters"], {k: list(v) for k, v in shadow.APPLICABLE.items()})
        self.assertEqual(c["families"], {"payload": list(shadow.PAYLOAD_FAMILIES),
                                         "snapshot": list(shadow.SNAPSHOT_FAMILIES)})
        self.assertEqual(c["snapshot"]["identity"]["members"], list(shadow.identity_document(
            {"contract": {"sha256": "0" * 64}, "bundle": {}})))

    def test_committed_inputs_are_the_accepted_preview_and_capsule(self) -> None:
        pins = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))["input"]
        self.assertEqual(pins["preview_identity"], "09597970622178fbde21925866a04491657b6134d4a9524513cc88a027a68c88")
        self.assertEqual(pins["preview_sha256"], "d8d2c7c6ffc8c1533f73bac328d7cfb68d34fa19cfd34712a22c81bbf60caf7c")
        self.assertEqual(pins["preview_contract_sha256"], preview.CONTRACT_SHA256)
        self.assertEqual(pins["capsule_identity"], "7c108ac8d003350b9a03d8106fa3f08aa3ef5651360cbd575ee9ae3fc18a51f4")
        self.assertEqual((pins["expected_events"], pins["expected_participants"], pins["expected_predictions"]),
                         (25, 50, 100))

    def test_labels_bind_the_shadow_role_and_the_preview_provenance_role(self) -> None:
        for key, value in (("designation", "UNTRUSTED_SHADOW"), ("input_authority", "PROVIDER_CLAIM_INPUTS"),
                           ("pit_admission", "PIT_NOT_ADMITTED"), ("calibration", "NOT_CALIBRATED"),
                           ("predictive_skill", "PREDICTIVE_SKILL_NOT_ESTABLISHED"), ("national_coverage", "UNKNOWN")):
            self.assertEqual(shadow.LABELS[key], value)
            self.assertEqual(shadow.RECORD_LABELS[key], value)
        self.assertEqual(shadow.RECORD_LABELS["source_preview_label"], preview.LABELS["preview_status"])
        self.assertNotIn("OFFICIAL_KICKOFF_CONFIRMED", json.dumps(shadow.LABELS).replace(
            "NOT_OFFICIAL_KICKOFF_CONFIRMED", ""))
        self.assertFalse(set(shadow.MODEL_IDS) & set(bm.MODEL_IDS))

    def test_packaged_profile_matches_the_committed_gate(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(shadow.ANCHOR_PROFILE, gate["anchor_profile"])
        self.assertEqual(set(shadow.ANCHOR_PROFILE), set(shadow.PROFILE_FIELDS))
        self.assertEqual(gate["anchor_profile"]["snapshot_identity"], gate["snapshot_identity"])
        self.assertEqual((gate["contract_id"], gate["contract_sha256"]), (shadow.CONTRACT_ID, shadow.CONTRACT_SHA256))
        anchor = gate["anchor"]
        self.assertEqual((anchor["issue_key"], anchor["issue_id"], anchor["marker"]),
                         (shadow.ANCHOR_SPEC["issue_key"], shadow.ANCHOR_SPEC["issue_id"], shadow.ANCHOR_SPEC["marker"]))
        self.assertEqual(anchor["created"], anchor["updated"])
        self.assertIs(anchor["edited"], False)
        self.assertEqual(anchor["comment_id"], shadow.ANCHOR_PROFILE["comment_id"])
        self.assertEqual(shadow.iso_micro(shadow.parse_service_time(anchor["created"])), anchor["created_utc"])
        self.assertLess(anchor["created_utc"], gate["timing"]["earliest_provider_reported_start"].replace("Z", ".000000Z"))
        self.assertLessEqual(gate["timing"]["observation_end_utc"], anchor["created_utc"])
        self.assertEqual((gate["counts"]["events"], gate["counts"]["participants"], gate["counts"]["predictions"]),
                         (25, 50, 100))
        self.assertEqual(gate["payload"]["sha256"], shadow.ANCHOR_PROFILE["payload_sha256"])
        self.assertEqual(gate["identity_document"]["schema"], shadow.IDENTITY_SCHEMA)

    def test_default_authority_refuses_a_fixture_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bat725c-") as tmp:
            world = fx.ShadowWorld(Path(tmp))
            with self.assertRaises(shadow.ShadowError) as caught:
                shadow.payload_files(world.contract, world.preview)
            self.assertEqual(caught.exception.code, "CONTRACT_NOT_COMMITTED_AUTHORITY")
            shutil.rmtree(fx.ext(tmp), ignore_errors=True)


class PayloadTests(_Workspace):
    def payload(self, world: fx.ShadowWorld, out: Path | None = None, **overrides) -> tuple[dict, dict]:
        result = builder.build(world.payload_args(out or self.fresh(), **overrides))
        return result, json.loads(Path(fx.ext(result["payload"])).read_text(encoding="utf-8"))

    def test_payload_freezes_every_preview_estimate_with_bound_roles(self) -> None:
        world = self.world()
        result, doc = self.payload(world)
        self.assertEqual(result["payload_state"], "MATERIALIZED")
        self.assertEqual((doc["counts"]["events"], doc["counts"]["participants"], doc["counts"]["predictions"]),
                         (3, 6, 12))
        estimates = json.loads(world.preview.read_text(encoding="utf-8"))["estimates"]
        self.assertEqual(len(doc["predictions"]), len(estimates))
        for x, e in zip(doc["predictions"], estimates):
            self.assertEqual(x["preview_estimate_sha256"], hashlib.sha256(preview.canonical_bytes(e)).hexdigest())
            for field in ("event_key", "model_id", "orientation", "team_key", "opponent_team_key", "probability",
                          "probability_decimal", "opponent_probability", "support_state", "abstention_reasons"):
                self.assertEqual(x[field], e[field], field)
            self.assertEqual({k: x[k] for k in shadow.RECORD_LABELS}, shadow.RECORD_LABELS)
            self.assertEqual(x["source_preview_label"], "PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST")
            if x["probability"]:
                p, q = (Fraction(x[k]["numerator"], x[k]["denominator"]) for k in ("probability",
                                                                                    "opponent_probability"))
                self.assertEqual(p + q, 1)
        self.assertEqual(doc["source"]["preview_identity"], world.preview_identity)
        self.assertEqual(doc["source"]["preview_role"], shadow.LABELS["source_preview_role"])
        self.assertEqual(doc["designation"], "UNTRUSTED_SHADOW")
        for e in doc["events"]:
            game = next(g for g in world.games if g["event_key"] == e["event_key"])
            self.assertEqual(e["provider_scheduled_utc"], game["scheduled_utc"])

    def test_smoothed_values_equal_independent_reconstruction_from_raw_records(self) -> None:
        world = self.world()
        _, doc = self.payload(world)
        raw = json.loads(world.preview_world.world.raw.decode("utf-8"))
        records = {}
        for event in raw["events"]:
            for c in event["competitions"][0]["competitors"]:
                parts = [int(x) for x in c["records"][0]["summary"].split("-")]
                w, l, t = parts[0], parts[1], parts[2] if len(parts) == 3 else 0
                records[(f"espn:event:{event['id']}", c["homeAway"])] = pfx.oracle_q(w, l, t)
        for x in doc["predictions"]:
            if x["model_id"] != SMOOTH:
                continue
            q_home, q_away = records[(x["event_key"], "home")], records[(x["event_key"], "away")]
            p_home = pfx.oracle_p(q_home, q_away)
            p = p_home if x["orientation"] == "home" else 1 - p_home
            self.assertEqual(Fraction(x["probability"]["numerator"], x["probability"]["denominator"]), p)
            self.assertEqual(x["probability_decimal"], pfx.half_even(p))

    def test_missing_record_keeps_an_explicit_abstention_and_cold_start_stays_labelled(self) -> None:
        def mutate(events):
            pfx.competitor_of(events, "900000001", "home")["records"] = [
                r for r in pfx.competitor_of(events, "900000001", "home")["records"] if r["name"] != "overall"]
            pfx.competitor_of(events, "900000003", "away")["records"][0]["summary"] = "0-0"
        world = self.world(fx.copy_events(mutate))
        _, doc = self.payload(world)
        rows = {(x["event_key"], x["model_id"], x["orientation"]): x for x in doc["predictions"]}
        abstained = rows[("espn:event:900000001", SMOOTH, "home")]
        self.assertEqual((abstained["support_state"], abstained["probability"], abstained["probability_decimal"]),
                         ("ABSTAINED", None, None))
        self.assertEqual([r["reason"] for r in abstained["abstention_reasons"]], ["RECORD_UNSUPPORTED"])
        self.assertEqual(rows[("espn:event:900000001", NULL, "home")]["support_state"], "SUPPORTED")
        cold = rows[("espn:event:900000003", SMOOTH, "away")]
        self.assertTrue(cold["team_cold_start"])
        self.assertEqual(cold["team_strength_q"], {"numerator": 1, "denominator": 2})
        self.assertEqual(doc["counts"]["abstained_predictions"], 2)
        part = next(p for p in doc["participants"] if p["event_key"] == "espn:event:900000001" and p["side"] == "home")
        self.assertEqual((part["support_state"], part["wins"], part["games"]), ("UNSUPPORTED", None, None))

    def test_order_chunk_interrupt_resume_and_frozen_root_rules(self) -> None:
        world = self.world()
        out = self.fresh()
        first, doc = self.payload(world, out)
        for order, chunk in (("reversed", "1"), ("shuffled:53", "17")):
            other, _ = self.payload(world, processing_order=order, chunk_size=chunk)
            self.assertEqual(other["payload_sha256"], first["payload_sha256"])
        again, _ = self.payload(world, out)
        self.assertEqual(again["payload_state"], "ALREADY_PRESENT_IDENTICAL")
        crash = self.fresh()
        with self.assertRaises(builder.BuildInterrupted):
            builder.build(world.payload_args(crash, stop_after_members=1))
        self.assertFalse((crash / "c" / "payload" / "sha256" / first["payload_sha256"]).exists())
        self.assertTrue(any((crash / "c" / ".staging").iterdir()))
        resumed = builder.build(world.payload_args(crash))
        self.assertEqual((resumed["payload_sha256"], resumed["payload_state"]),
                         (first["payload_sha256"], "MATERIALIZED"))
        # a second, different payload in the same root is refused unless it names its frozen predecessor
        other_world = self.world(fx.copy_events(lambda ev: pfx.competitor_of(ev, "900000001", "home")["records"][0]
                                                .update(summary="5-0")))
        with self.assertRaises(builder.BuildRefused) as caught:
            builder.build(other_world.payload_args(out))
        self.assertEqual(caught.exception.code, "PAYLOAD_ALREADY_FROZEN")
        successor = builder.build(other_world.payload_args(out, successor_of=first["payload_sha256"]))
        self.assertEqual(successor["payload_state"], "MATERIALIZED")
        self.assertEqual(hashlib.sha256(Path(fx.ext(first["payload"])).read_bytes()).hexdigest(),
                         first["payload_sha256"])

    def test_anchor_body_is_hash_only_and_deterministic(self) -> None:
        world = self.world()
        result, doc = self.payload(world)
        data = Path(fx.ext(result["payload"])).read_bytes()
        body = shadow.anchor_body(doc, result["payload_sha256"], len(data))
        self.assertEqual(body, shadow.anchor_body(copy.deepcopy(doc), result["payload_sha256"], len(data)))
        self.assertTrue(body.startswith("C53-A01-M2 "))
        self.assertIn(f"payload_sha256: {result['payload_sha256']}", body)
        self.assertNotIn("\n\n", body)
        for x in doc["predictions"]:
            if x["probability_decimal"]:
                self.assertNotIn(x["probability_decimal"], body)
        for p in doc["participants"]:
            self.assertNotIn(p["source_name"], body)
        out = self.fresh() / "body.txt"
        rendered = builder.build(Namespace(stage="anchor-body", contract=world.contract_path, preview=world.preview,
                                           payload=Path(result["payload"]), out=out, chunk_size=str(1 << 20),
                                           contract_authority=world.authority))
        self.assertEqual(out.read_text(encoding="utf-8"), body)
        self.assertEqual(rendered["payload_sha256"], result["payload_sha256"])
        with self.assertRaises(FileExistsError):  # the rendered body is written once, never replaced
            builder.build(Namespace(stage="anchor-body", contract=world.contract_path, preview=world.preview,
                                    payload=Path(result["payload"]), out=out, chunk_size=str(1 << 20),
                                    contract_authority=world.authority))


class AnchorAndTimingTests(_Workspace):
    def built(self, world: fx.ShadowWorld | None = None, **receipt_kwargs) -> tuple[fx.ShadowWorld, dict]:
        world = world or self.world()
        return world, world.build(self.fresh(), **receipt_kwargs)

    def verify(self, world: fx.ShadowWorld, path: Path, profile) -> dict:
        return shadow.verify_snapshot(path, contract_sha256=world.authority, profile=profile)

    def refused(self, world: fx.ShadowWorld, path: Path, profile) -> str:
        with self.assertRaises(shadow.ShadowError) as caught:
            self.verify(world, path, profile)
        return caught.exception.code

    def test_genuine_fixture_snapshot_anchors_every_event_and_binds_the_receipt(self) -> None:
        world, b = self.built()
        binding = self.verify(world, b["path"], b["profile"])
        snap = binding["snapshot"]
        self.assertEqual(snap["anchor"]["created_utc"], micro(ANCHOR_UTC))
        self.assertEqual(snap["anchor"]["comment_id"], fx.FIXTURE_COMMENT_ID)
        self.assertFalse(snap["anchor"]["edited"])
        self.assertEqual({t["decision"] for t in snap["timing"]["events"]}, {shadow.ANCHORED})
        self.assertEqual(snap["timing"]["basis"], "PRE_PROVIDER_REPORTED_START")
        self.assertEqual(snap["counts"]["anchored_predictions"], 12)
        self.assertEqual(snap["anchor"]["receipt_sha256"], hashlib.sha256(b["receipt"].read_bytes()).hexdigest())
        self.assertEqual(snap["payload"]["sha256"], b["payload"]["payload_sha256"])
        self.assertTrue(binding["profile_pinned"])
        self.assertEqual(self.refused(world, b["path"], fx.deep(None)), "SHADOW_PROFILE_NOT_PINNED")
        self.assertFalse(b["snapshot"]["profile_pinned"])
        # the default packaged profile never authorizes a fixture snapshot
        with self.assertRaises(shadow.ShadowError) as caught:
            shadow.verify_snapshot(b["path"], contract_sha256=world.authority)
        self.assertIn(caught.exception.code, ("SHADOW_PROFILE_NOT_PINNED", "SHADOW_ANCHOR_NOT_PINNED_PROFILE"))

    def test_anchor_just_before_equal_to_and_after_a_provider_start(self) -> None:
        start = dt.datetime(2026, 10, 17, 16, 0, tzinfo=UTC)
        for label, moment, ineligible in (("before", start - dt.timedelta(milliseconds=1), set()),
                                          ("equal", start, {"espn:event:900000001"}),
                                          ("after_all", dt.datetime(2026, 10, 17, 20, 0, tzinfo=UTC),
                                           {"espn:event:900000001", "espn:event:900000002", "espn:event:900000003"})):
            world, b = self.built(created=fx.service_time(moment))
            snap = self.verify(world, b["path"], b["profile"])["snapshot"]
            got = {t["event_key"] for t in snap["timing"]["events"] if t["decision"] == shadow.INELIGIBLE}
            self.assertEqual(got, ineligible, label)
            for t in snap["timing"]["events"]:
                if t["event_key"] in ineligible:
                    self.assertEqual(t["reasons"], ["ANCHOR_AT_OR_AFTER_PROVIDER_REPORTED_START"])
            # an ineligible key is retained and served with its reason, never dropped
            self.assertEqual(snap["counts"]["predictions"], 12)
            self.assertEqual(snap["counts"]["ineligible_predictions"], 4 * len(ineligible))
            code, doc, err = self.run_cli(["--prospective-shadow", str(b["path"]), "--grain", "shadow-prediction",
                                           "--cutoff", "2026-10-18T00:00:00Z", "--all"], world, b["profile"])
            self.assertEqual((code, doc["total"]), (0, 12), err)
            flagged = {r["prediction"]["event_key"] for r in doc["rows"] if r["timing"]["decision"] == shadow.INELIGIBLE}
            self.assertEqual(flagged, ineligible)

    def test_anchor_before_inside_and_after_the_observation_interval(self) -> None:
        start = dt.datetime(2026, 10, 11, 18, 15, 55, 264959, tzinfo=UTC)
        end = dt.datetime(2026, 10, 11, 18, 15, 55, 744674, tzinfo=UTC)
        cases = (("before_start", start - dt.timedelta(seconds=5), True),
                 ("inside", start + (end - start) / 2, True),
                 ("last_millisecond_before_end", dt.datetime(2026, 10, 11, 18, 15, 55, 744000, tzinfo=UTC), True),
                 ("first_millisecond_after_end", dt.datetime(2026, 10, 11, 18, 15, 55, 745000, tzinfo=UTC), False))
        for label, moment, before_end in cases:
            world, b = self.built(created=fx.service_time(moment.replace(microsecond=moment.microsecond // 1000 * 1000)))
            snap = self.verify(world, b["path"], b["profile"])["snapshot"]
            decisions = {t["decision"] for t in snap["timing"]["events"]}
            if before_end:
                self.assertEqual(decisions, {shadow.INELIGIBLE}, label)
                self.assertTrue(all("ANCHOR_BEFORE_OBSERVATION_END" in t["reasons"] for t in snap["timing"]["events"]))
            else:
                self.assertEqual(decisions, {shadow.ANCHORED}, label)

    def test_receipt_semantic_rules_refuse_at_the_builder(self) -> None:
        world = self.world()
        out = self.fresh()
        payload = builder.build(world.payload_args(out))
        cases = {
            "edited": ({"updated": "2026-10-12T01:31:00.000-0500"}, "SHADOW_ANCHOR_EDITED"),
            "other_issue": ({"issue_id": "25891"}, "SHADOW_ANCHOR_ISSUE_MISMATCH"),
            "integer_id": ({"comment_id": 700001}, "SHADOW_ANCHOR_IDENTITY_INVALID"),
            "zulu_time": ({"created": "2026-10-12T06:30:00.000Z"}, "SHADOW_ANCHOR_TIME_INVALID"),
            "no_millis": ({"created": "2026-10-12T01:30:00-0500"}, "SHADOW_ANCHOR_TIME_INVALID"),
            "overflow_time": ({"created": "9999-12-31T23:59:59.999-1400"}, "SHADOW_ANCHOR_TIME_INVALID"),
            "wrong_marker": ({"text": lambda b: b.replace("C53-A01-M2 ", "C53-A01-M1 ", 1)},
                             "SHADOW_ANCHOR_MARKER_MISMATCH"),
            "wrong_digest": ({"text": lambda b: b.replace(payload["payload_sha256"], "0" * 64)},
                             "SHADOW_ANCHOR_BODY_MISMATCH"),
            "values_appended": ({"text": lambda b: b + "probability: 0.5\n"}, "SHADOW_ANCHOR_BODY_MISMATCH"),
        }
        for name, (kwargs, code) in cases.items():
            receipt = world.write_receipt(Path(payload["payload"]), self.fresh() / "r.json", **kwargs)
            with self.assertRaises(builder.BuildRefused) as caught:
                builder.build(world.snapshot_args(out, Path(payload["payload"]), receipt))
            self.assertEqual(caught.exception.code, code, name)
        broken = self.fresh() / "r.json"
        broken.parent.mkdir(parents=True)
        broken.write_bytes(b'{"id":"1","id":"2"}')
        with self.assertRaises(builder.BuildRefused) as caught:
            builder.build(world.snapshot_args(out, Path(payload["payload"]), broken))
        self.assertEqual(caught.exception.code, "SHADOW_ANCHOR_RECEIPT_MALFORMED")
        self.assertFalse((out / "c" / "sha256").exists())

    def test_coordinated_anchor_forgeries_refuse_for_their_own_rule(self) -> None:
        world, b = self.built()
        profile = b["profile"]
        cases = {
            "earlier_created_time": (dict(receipt_edit=lambda r: r.update(created="2026-10-12T00:10:00.000-0500",
                                                                          updated="2026-10-12T00:10:00.000-0500")),
                                     "SHADOW_ANCHOR_NOT_PINNED_PROFILE"),
            "other_comment_id": (dict(receipt_edit=lambda r: r.update(
                id="700002", self=r["self"].replace("700001", "700002"))), "SHADOW_ANCHOR_NOT_PINNED_PROFILE"),
            "edited_comment": (dict(receipt_edit=lambda r: r.update(updated="2026-10-12T02:00:00.000-0500")),
                               "SHADOW_ANCHOR_EDITED"),
            "body_names_old_payload": (dict(payload_edit=lambda d: d["labels"].update(use="X"), rerender_body=False),
                                       "SHADOW_PAYLOAD_LABELS_MISMATCH"),
            "receipt_other_issue": (dict(receipt_edit=lambda r: r.update(self=r["self"].replace("/25892/",
                                                                                                 "/25000/"))),
                                    "SHADOW_ANCHOR_ISSUE_MISMATCH"),
            "receipt_id_as_int": (dict(receipt_edit=lambda r: r.update(id=700001)), "SHADOW_ANCHOR_IDENTITY_INVALID"),
            "receipt_body_digest": (dict(receipt_edit=lambda r: r["body"]["content"][1]["content"][0].update(
                text="payload_sha256: " + "1" * 64)), "SHADOW_ANCHOR_BODY_MISMATCH"),
            "snapshot_comment_id_int": (dict(snapshot_edit=lambda s: s["anchor"].update(comment_id=700001)),
                                        "SHADOW_SNAPSHOT_ANCHOR_MISMATCH"),
            "snapshot_created_backdated": (dict(snapshot_edit=lambda s: s["anchor"].update(
                created_utc="2026-10-11T00:00:00.000000Z")), "SHADOW_SNAPSHOT_ANCHOR_MISMATCH"),
            "snapshot_edited_flag": (dict(snapshot_edit=lambda s: s["anchor"].update(edited=0)),
                                     "SHADOW_SNAPSHOT_ANCHOR_MISMATCH"),
            "snapshot_receipt_digest": (dict(snapshot_edit=lambda s: s["anchor"].update(receipt_sha256="2" * 64)),
                                        "SHADOW_SNAPSHOT_ANCHOR_MISMATCH"),
            "snapshot_payload_digest": (dict(snapshot_edit=lambda s: s["payload"].update(sha256="3" * 64)),
                                        "SHADOW_SNAPSHOT_PAYLOAD_MISMATCH"),
            "official_kickoff_claim": (dict(snapshot_edit=lambda s: s["timing"].update(
                basis="OFFICIAL_KICKOFF_CONFIRMED")), "SHADOW_SNAPSHOT_TIMING_MISMATCH"),
            "anchored_key_marked_ineligible": (dict(snapshot_edit=lambda s: s["timing"]["events"][0].update(
                reasons=["ANCHOR_AT_OR_AFTER_PROVIDER_REPORTED_START"], decision=shadow.INELIGIBLE)),
                "SHADOW_SNAPSHOT_TIMING_MISMATCH"),
            "dropped_timing_key": (dict(snapshot_edit=lambda s: s["timing"]["events"].pop()),
                                   "SHADOW_SNAPSHOT_TIMING_MISMATCH"),
        }
        for name, (kwargs, code) in cases.items():
            forged = fx.forge(b["path"], self.fresh("f"), **kwargs)
            self.assertEqual(self.refused(world, forged, profile), code, name)
        other = dict(profile, snapshot_identity="4" * 64)
        self.assertEqual(self.refused(world, b["path"], other), "SHADOW_NOT_PINNED_SNAPSHOT")
        self.assertEqual(self.refused(world, b["path"], dict(profile, payload_sha256="5" * 64)),
                         "SHADOW_NOT_PINNED_SNAPSHOT")

    def test_snapshot_determinism_interruption_and_frozen_successor_rules(self) -> None:
        world = self.world()
        out = self.fresh()
        payload = builder.build(world.payload_args(out))
        receipt = world.write_receipt(Path(payload["payload"]), out / "receipt.json")
        first = builder.build(world.snapshot_args(out, Path(payload["payload"]), receipt))
        self.assertEqual(first["snapshot_state"], "MATERIALIZED")
        again = builder.build(world.snapshot_args(out, Path(payload["payload"]), receipt))
        self.assertEqual((again["identity"], again["snapshot_state"]), (first["identity"],
                                                                       "ALREADY_PRESENT_IDENTICAL"))
        for order, chunk in (("reversed", "1"), ("shuffled:725", "17")):
            v = builder.build(world.snapshot_args(self.fresh(), Path(payload["payload"]), receipt,
                                                  processing_order=order, chunk_size=chunk))
            self.assertEqual(v["identity"], first["identity"])
            self.assertEqual(fx.read_tree(Path(v["snapshot"]).parent), fx.read_tree(Path(first["snapshot"]).parent))
        crash = self.fresh()
        with self.assertRaises(builder.BuildInterrupted):
            builder.build(world.snapshot_args(crash, Path(payload["payload"]), receipt, stop_after_members=3))
        self.assertFalse((crash / "c" / "sha256" / first["identity"]).exists())
        resumed = builder.build(world.snapshot_args(crash, Path(payload["payload"]), receipt))
        self.assertEqual(resumed["identity"], first["identity"])
        # a different receipt for the same payload is another snapshot: refused unless a named successor
        other = world.write_receipt(Path(payload["payload"]), self.fresh() / "r2.json",
                                    created="2026-10-12T01:45:00.000-0500", comment_id="700009")
        with self.assertRaises(builder.BuildRefused) as caught:
            builder.build(world.snapshot_args(out, Path(payload["payload"]), other))
        self.assertEqual(caught.exception.code, "SNAPSHOT_ALREADY_FROZEN")
        before = fx.read_tree(Path(first["snapshot"]).parent)
        successor = builder.build(world.snapshot_args(out, Path(payload["payload"]), other,
                                                      successor_of=first["identity"]))
        self.assertNotEqual(successor["identity"], first["identity"])
        self.assertEqual(fx.read_tree(Path(first["snapshot"]).parent), before)


class QueryTests(_Workspace):
    def setUp(self) -> None:
        super().setUp()
        self.w = self.world()
        b = self.w.build(self.fresh())
        self.path, self.profile = b["path"], b["profile"]
        self.payload = json.loads(Path(fx.ext(b["payload"]["payload"])).read_text(encoding="utf-8"))

    def cli(self, *argv: str) -> tuple[int, dict | None, str]:
        return self.run_cli(["--prospective-shadow", str(self.path), *argv], self.w, self.profile)

    def test_cutoff_boundaries_equivalent_zones_overflow_and_no_refresh(self) -> None:
        base = ["--grain", "shadow-prediction", "--all"]
        code, _, refused = self.cli(*base, "--cutoff", micro(ANCHOR_UTC - dt.timedelta(microseconds=1)))
        self.assertEqual((code, refused), (2, "SHADOW_UNAVAILABLE_BEFORE_ANCHOR"))
        answers = []
        for cutoff in (micro(ANCHOR_UTC), "2026-10-12T08:30:00+02:00", "2026-10-12T01:30:00-05:00",
                       "2026-10-17T16:00:00Z", "2027-06-01T00:00:00Z"):
            code, doc, refused = self.cli(*base, "--cutoff", cutoff)
            self.assertEqual(code, 0, refused)
            answers.append(doc)
        self.assertEqual(len({json.dumps(d["rows"], sort_keys=True) for d in answers}), 1)
        self.assertEqual(answers[1]["cutoff"]["utc"], answers[2]["cutoff"]["utc"])
        for cutoff, code_name in (("2026-10-12T07:00:00", "CUTOFF_TIMEZONE_REQUIRED"),
                                  ("2026-10-12", "CUTOFF_TIMEZONE_REQUIRED"), ("tomorrow", "CUTOFF_INVALID"),
                                  (CUTOFF + "\n", "CUTOFF_INVALID"), ("2026-02-30T00:00:00Z", "CUTOFF_INVALID"),
                                  ("2026-10-12T07:00:00+15:00", "CUTOFF_INVALID"),
                                  ("0001-01-01T00:00:00+14:00", "CUTOFF_OUT_OF_RANGE"),
                                  ("9999-12-31T23:59:59-14:00", "CUTOFF_OUT_OF_RANGE")):
            code, doc, refused = self.cli(*base, "--cutoff", cutoff)
            self.assertEqual((code, doc, refused), (2, None, code_name), cutoff)
        code, _, refused = self.cli("--grain", "shadow-prediction")
        self.assertEqual((code, refused), (2, "CUTOFF_REQUIRED"))

    def test_modes_filters_and_selectors_refuse_for_their_own_reason(self) -> None:
        sel = ["--grain", "shadow-prediction", "--cutoff", CUTOFF]
        cases = [(["--require-pit"], "SHADOW_PIT_NOT_ADMITTED"), (["--database", "x"], "SHADOW_MODE_CONFLICT"),
                 (["--history-database", "x"], "SHADOW_MODE_CONFLICT"), (["--manifest", "x"], "SHADOW_MODE_CONFLICT"),
                 (["--prospective-preview", "x"], "SHADOW_MODE_CONFLICT"),
                 (["--contest", "ncaa:1"], "FILTER_NOT_APPLICABLE"), (["--partition", "P"], "FILTER_NOT_APPLICABLE"),
                 (["--event", "900000001"], "EVENT_KEY_INVALID"), (["--event", "espn:event:1\n"], "EVENT_KEY_INVALID"),
                 (["--team", "Fixture Alpha Owls"], "TEAM_KEY_INVALID"), (["--team", "org:1"], "TEAM_KEY_INVALID"),
                 (["--model", "SMOOTHED_HISTORY_ODDS_V1"], "SHADOW_MODEL_UNKNOWN"),
                 (["--orientation", "neutral"], "ORIENTATION_INVALID"), (["--offset", "-1"], "NEGATIVE_OFFSET"),
                 (["--limit", "-1"], "NEGATIVE_LIMIT"), (["--expect-identity", "0" * 64], "STALE_SHADOW_IDENTITY"),
                 (["--expect-identity", "nothex"], "STALE_SHADOW_IDENTITY")]
        for extra, expected in cases:
            code, doc, refused = self.cli(*sel, *extra)
            self.assertEqual((code, doc, refused), (2, None, expected), extra)
        for grain in ("estimate", "summary", "preview-estimate"):
            code, _, refused = self.cli("--grain", grain, "--cutoff", CUTOFF)
            self.assertEqual((code, refused), (2, "SHADOW_GRAIN_REQUIRED"), grain)
        code, _, refused = self.cli("--grain", "shadow-summary", "--cutoff", CUTOFF, "--orientation", "home")
        self.assertEqual((code, refused), (2, "FILTER_NOT_APPLICABLE"))
        code, _, text = self.cli(*sel, "--season", "abc")
        self.assertEqual(code, 2)
        self.assertIn("invalid int value", text)
        missing = self.tmp / "nothing" / ("b" * 64) / "snapshot.json"
        code, _, refused = self.run_cli(["--prospective-shadow", str(missing), *sel], self.w, self.profile)
        self.assertEqual((code, refused), (2, "SHADOW_MISSING"))
        self.assertFalse(missing.parent.exists())

    def expected(self, grain: str, **f) -> list:
        teams = {}
        for p in self.payload["participants"]:
            teams.setdefault(p["event_key"], set()).add(p["team_key"])
        if f.get("season") not in (None, 2026):
            return []
        if grain == "shadow-prediction":
            return [x for x in self.payload["predictions"]
                    if f.get("event") in (None, x["event_key"]) and f.get("team") in (None, x["team_key"]) and
                    f.get("model") in (None, x["model_id"]) and f.get("orientation") in (None, x["orientation"])]
        chosen = [e["event_key"] for e in self.payload["events"] if f.get("event") in (None, e["event_key"]) and
                  (f.get("team") is None or f["team"] in teams[e["event_key"]])]
        if not chosen:
            return []
        rows = []
        for m in ([f["model"]] if f.get("model") else [NULL, SMOOTH]):
            preds = [x for x in self.payload["predictions"] if x["event_key"] in chosen and x["model_id"] == m]
            parts = [p for p in self.payload["participants"] if p["event_key"] in chosen]
            rows.append({"model_id": m, "distinct_events": len(chosen), "predictions": len(preds),
                         "participants": len(parts), "anchored_pre_provider_start_games": len(chosen),
                         "ineligible_games": 0})
        return rows

    def test_conjunctive_filter_and_paging_matrix_at_both_grains(self) -> None:
        events = [e["event_key"] for e in self.payload["events"]]
        teams = sorted({p["team_key"] for p in self.payload["participants"]})
        choices = {"event": [None, events[0], "espn:event:123456789"], "team": [None, teams[0], teams[3],
                                                                             "espn:team:987654"],
                   "model": [None, NULL, SMOOTH], "season": [None, 2026, 2025]}
        for event, team, model, season in itertools.product(*choices.values()):
            for grain in ("shadow-prediction", "shadow-summary"):
                for orient in ([None, "home", "away"] if grain == "shadow-prediction" else [None]):
                    f = {"event": event, "team": team, "model": model, "season": season, "orientation": orient}
                    argv = ["--grain", grain, "--cutoff", CUTOFF, "--all"]
                    for k, v in f.items():
                        if v is not None:
                            argv += [f"--{k}", str(v)]
                    code, doc, refused = self.cli(*argv)
                    self.assertEqual(code, 0, (f, refused))
                    want = self.expected(grain, **f)
                    if grain == "shadow-prediction":
                        self.assertEqual([r["prediction"] for r in doc["rows"]], want, f)
                    else:
                        got = [{k: r["summary"][k] for k in ("model_id", "distinct_events", "predictions",
                                                             "participants", "anchored_pre_provider_start_games",
                                                             "ineligible_games")} for r in doc["rows"]]
                        self.assertEqual(got, want, f)
                    self.assertEqual((doc["total"], doc["returned"], doc["next_offset"]), (len(want), len(want), None))
                    self.assertEqual(doc["season_scope_state"], "NOT_YET_AUDITED" if season == 2025 else
                                     shadow.IN_SCOPE_STATE)
        everything = self.cli("--grain", "shadow-prediction", "--cutoff", CUTOFF, "--all")[1]["rows"]
        for limit in (0, 1, 5, 7, 12, 13):
            pages, offset = [], 0
            while True:
                doc = self.cli("--grain", "shadow-prediction", "--cutoff", CUTOFF, "--limit", str(limit), "--offset",
                               str(offset))[1]
                self.assertEqual(doc["total"], 12)
                pages += doc["rows"]
                if doc["next_offset"] is None or limit == 0:
                    break
                self.assertEqual(doc["next_offset"], offset + limit)
                offset = doc["next_offset"]
            if limit:
                self.assertEqual(pages, everything)
        beyond = self.cli("--grain", "shadow-prediction", "--cutoff", CUTOFF, "--offset", "50")[1]
        self.assertEqual((beyond["rows"], beyond["returned"], beyond["next_offset"], beyond["total"]), ([], 0, None, 12))

    def test_empty_valid_selections_serve_no_rows_at_both_grains(self) -> None:
        events = [e["event_key"] for e in self.payload["events"]]
        home_other = next(e["home_team_key"] for e in self.payload["events"] if e["event_key"] == events[1])
        for grain in ("shadow-prediction", "shadow-summary"):
            for selection in (["--event", "espn:event:123456789"], ["--team", "espn:team:987654"],
                              ["--event", events[0], "--team", home_other]):
                for extra in ([], ["--model", SMOOTH], ["--limit", "1"], ["--limit", "0"], ["--offset", "3"]):
                    code, doc, refused = self.cli("--grain", grain, "--cutoff", CUTOFF, *selection, *extra)
                    self.assertEqual(code, 0, refused)
                    self.assertEqual((doc["rows"], doc["total"], doc["returned"], doc["next_offset"]),
                                     ([], 0, 0, None), (grain, selection, extra))

    def test_summary_counts_games_once_and_every_row_carries_labels_and_timing(self) -> None:
        code, doc, _ = self.cli("--grain", "shadow-summary", "--cutoff", CUTOFF, "--all")
        self.assertEqual([r["summary"]["distinct_events"] for r in doc["rows"]], [3, 3])
        self.assertEqual([r["summary"]["predictions"] for r in doc["rows"]], [6, 6])
        self.assertEqual([r["summary"]["participants"] for r in doc["rows"]], [6, 6])
        for r in doc["rows"]:
            self.assertEqual({k: r["summary"][k] for k in shadow.RECORD_LABELS}, shadow.RECORD_LABELS)
        one = self.cli("--grain", "shadow-summary", "--cutoff", CUTOFF, "--event", "espn:event:900000002",
                       "--model", SMOOTH)[1]["rows"]
        self.assertEqual([(r["summary"]["distinct_events"], r["summary"]["predictions"]) for r in one], [(1, 2)])
        code, doc, _ = self.cli("--grain", "shadow-prediction", "--cutoff", CUTOFF, "--all")
        for r in doc["rows"]:
            self.assertEqual({k: r["prediction"][k] for k in shadow.RECORD_LABELS}, shadow.RECORD_LABELS)
            self.assertEqual((r["timing"]["decision"], r["timing"]["basis"]), (shadow.ANCHORED,
                                                                               "PRE_PROVIDER_REPORTED_START"))
            self.assertEqual(r["shadow_identity"], self.path.parent.name)
        self.assertEqual(doc["designation"], "UNTRUSTED_SHADOW")
        self.assertEqual(doc["labels"], shadow.LABELS)
        self.assertEqual(doc["anchor"]["created_utc"], micro(ANCHOR_UTC))

    def test_other_invocations_are_unchanged_and_never_import_the_shadow_reader(self) -> None:
        code = (f"import sys; sys.path[:0] = [{str(REPO_ROOT / 'src')!r}]; "
                "from aggie_analytics.retrospective_baseline import query; "
                "rc = query.main(['--database', 'missing.sqlite', '--history-database', 'm.sqlite', '--grain', "
                "'summary']); rc2 = query.main(['--prospective-preview', 'missing.json', '--grain', "
                "'preview-estimate', '--cutoff', '2026-10-12T00:00:00Z']); print(rc, rc2, "
                "'aggie_analytics.retrospective_baseline.shadow' in sys.modules)")
        proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(proc.stdout.strip(), "2 2 False")
        parser = query.build_parser()
        self.assertNotIn("prospective-shadow", parser.format_usage())
        help_text = parser.format_help()
        # the original help (the same parser formatted by the plain ArgumentParser) is an unchanged prefix; the only
        # addition is one paragraph naming the shadow mode
        plain = ArgumentParser.format_help(parser)
        self.assertNotIn("prospective-shadow", plain)
        self.assertTrue(help_text.startswith(plain))
        added = help_text[len(plain):]
        self.assertTrue(added.startswith("\n") and added.endswith("\n"))
        # Cycle 61 (BAT-732, TP61) authorizes exactly one more paragraph, naming the personnel association mode, after
        # the unchanged shadow paragraph
        shadow_paragraph, association_paragraph, boosting_paragraph = added.strip("\n").split("\n\n")
        self.assertEqual(" ".join(shadow_paragraph.split()), " ".join(query.SHADOW_EPILOG.split()))
        association_formatter = parser._get_formatter()
        association_formatter.add_text(query.ASSOCIATION_EPILOG)
        self.assertEqual(association_paragraph, association_formatter.format_help().strip("\n"))
        self.assertEqual(boosting_paragraph, query.BOOSTING_HELP_PARAGRAPH)
        self.assertNotIn("prospective-shadow", query.build_preview_parser().format_help())


class ForgeryTests(_Workspace):
    """Coordinated forgeries (every outer identity recomputed) must refuse for their own semantic rule."""

    def setUp(self) -> None:
        super().setUp()
        self.w = self.world()
        b = self.w.build(self.fresh())
        self.path, self.profile = b["path"], b["profile"]

    def refusal(self, path) -> str:
        code, out, refused = self.run_cli(["--prospective-shadow", str(path), "--grain", "shadow-prediction",
                                           "--cutoff", CUTOFF, "--all"], self.w, self.profile)
        self.assertEqual((code, out), (2, None), refused)
        return refused

    def test_payload_field_forgeries_refuse_for_their_own_family(self) -> None:
        def pred(d, i=0):
            return d["predictions"][i]

        def smoothed(d):
            return next(x for x in d["predictions"] if x["model_id"] == SMOOTH)
        cases = {
            "wrong_numerator": (lambda d: smoothed(d)["probability"].update(
                numerator=smoothed(d)["probability"]["numerator"] + 1), "PREDICTION_VALUE"),
            "complement_mistake": (lambda d: smoothed(d).update(opponent_probability=smoothed(d)["probability"]),
                                   "PREDICTION_VALUE"),
            "wrong_decimal": (lambda d: smoothed(d).update(probability_decimal="0.5"), "PREDICTION_VALUE"),
            "probability_as_float": (lambda d: smoothed(d).update(probability=0.5), "PREDICTION_VALUE"),
            "role_swap": (lambda d: pred(d).update(team_key=pred(d)["opponent_team_key"],
                                                   opponent_team_key=pred(d)["team_key"]), "PREDICTION_IDENTITY"),
            "borrowed_model": (lambda d: pred(d).update(model_sha256=pred(d, 2)["model_sha256"]),
                               "PREDICTION_IDENTITY"),
            "season_as_string": (lambda d: pred(d).update(season="2026"), "PREDICTION_IDENTITY"),
            "season_as_float": (lambda d: pred(d).update(season=2026.0), "PREDICTION_IDENTITY"),
            "start_backdated": (lambda d: pred(d).update(provider_scheduled_utc="2026-10-12T00:00:00Z"),
                                "PREDICTION_IDENTITY"),
            "model_relabelled": (lambda d: pred(d).update(model_id=SMOOTH), "PREDICTION_MEMBERSHIP"),
            "dropped_prediction": (lambda d: d["predictions"].pop(), "PREDICTION_MEMBERSHIP"),
            "duplicate_prediction": (lambda d: d["predictions"].insert(1, copy.deepcopy(pred(d))),
                                     "PREDICTION_MEMBERSHIP"),
            "fabricated_abstention": (lambda d: pred(d).update(support_state="ABSTAINED"), "PREDICTION_SUPPORT"),
            "lineage_borrowed": (lambda d: smoothed(d).update(team_feature_sha256=pred(d, 3)["team_feature_sha256"]),
                                 "PREDICTION_LINEAGE"),
            "preview_role_dropped": (lambda d: pred(d).update(preview_estimate_sha256="6" * 64), "PREDICTION_LINEAGE"),
            "skill_label": (lambda d: pred(d).update(predictive_skill="ESTABLISHED"), "PREDICTION_LABELS"),
            "trust_label": (lambda d: pred(d).update(designation="TRUSTED"), "PREDICTION_LABELS"),
            "pit_label": (lambda d: pred(d).update(pit_admission="PIT_ADMITTED"), "PREDICTION_LABELS"),
            "preview_label_as_role": (lambda d: pred(d).update(source_preview_label="UNTRUSTED_SHADOW"),
                                      "PREDICTION_LABELS"),
            "borrowed_record": (lambda d: d["participants"][0].update(wins=d["participants"][1]["wins"] + 7),
                                "PARTICIPANT_RECORD"),
            "cold_start_as_int": (lambda d: d["participants"][0].update(cold_start=0), "PARTICIPANT_RECORD"),
            "games_as_bool": (lambda d: d["participants"][0].update(games=True), "PARTICIPANT_RECORD"),
            "participant_dropped": (lambda d: d["participants"].pop(), "PARTICIPANT_MEMBERSHIP"),
            "participant_side_swap": (lambda d: d["participants"][0].update(side="away"), "PARTICIPANT_MEMBERSHIP"),
            "event_dropped": (lambda d: d["events"].pop(), "EVENT_MEMBERSHIP"),
            "event_duplicated": (lambda d: d["events"].append(copy.deepcopy(d["events"][0])), "EVENT_MEMBERSHIP"),
            "event_start_moved": (lambda d: d["events"][0].update(provider_scheduled_utc="2026-10-18T16:00:00Z"),
                                  "EVENT_IDENTITY"),
            "event_role_swap": (lambda d: d["events"][0].update(home_team_key=d["events"][0]["away_team_key"]),
                                "EVENT_IDENTITY"),
            "summary_orientations_as_games": (lambda d: d["summary"][0].update(distinct_events=6), "SUMMARY"),
            "count_as_float": (lambda d: d["counts"].update(events=3.0), "COUNTS"),
            "count_as_bool": (lambda d: d["counts"].update(abstained_predictions=False), "COUNTS"),
            "designation_trusted": (lambda d: d.update(designation="TRUSTED_FORECAST"), "DESIGNATION"),
            "pit_admitted": (lambda d: d["labels"].update(pit_admission="PIT_ADMITTED"), "LABELS"),
            "calibrated": (lambda d: d["labels"].update(calibration="CALIBRATED"), "LABELS"),
            "national_complete": (lambda d: d["labels"].update(national_coverage="COMPLETE"), "LABELS"),
            "fake_preview_pin": (lambda d: d["source"].update(preview_identity="7" * 64), "SOURCE"),
            "observation_backdated": (lambda d: d["source"]["observation"].update(
                request_end_utc="2026-10-01T00:00:00.000000Z"), "SOURCE"),
            "fake_contract": (lambda d: d["contract"].update(sha256="8" * 64), "CONTRACT"),
            "home_advantage": (lambda d: d["models"][SMOOTH]["definition"].update(home_advantage=0.03), "MODELS"),
            "numeric_contract": (lambda d: d["numeric_contract"].update(probability="floats"), "NUMERIC_CONTRACT"),
            "extra_top_member": (lambda d: d.update(issued_at="2026-10-12T00:00:00Z"), "SCHEMA"),
        }
        for name, (edit, family) in cases.items():
            forged = fx.forge(self.path, self.fresh("f"), payload_edit=edit)
            self.assertEqual(self.refusal(forged), f"SHADOW_PAYLOAD_{family}_MISMATCH", name)

    def test_snapshot_bundle_and_location_forgeries(self) -> None:
        snapshot_cases = {
            "designation": (lambda s: s.update(designation="TRUSTED"), "SHADOW_SNAPSHOT_DESIGNATION_MISMATCH"),
            "skill_label": (lambda s: s["labels"].update(predictive_skill="ESTABLISHED"),
                            "SHADOW_SNAPSHOT_LABELS_MISMATCH"),
            "count_as_bool": (lambda s: s["counts"].update(ineligible_events=False), "SHADOW_SNAPSHOT_COUNTS_MISMATCH"),
            "count_as_float": (lambda s: s["counts"].update(events=3.0), "SHADOW_SNAPSHOT_COUNTS_MISMATCH"),
            "payload_bytes": (lambda s: s["payload"].update(bytes=s["payload"]["bytes"] + 1),
                              "SHADOW_SNAPSHOT_PAYLOAD_MISMATCH"),
            "contract": (lambda s: s["contract"].update(sha256="9" * 64), "SHADOW_SNAPSHOT_CONTRACT_MISMATCH"),
            "extra_member": (lambda s: s.update(published=True), "SHADOW_SNAPSHOT_SCHEMA_MISMATCH"),
        }
        for name, (edit, code) in snapshot_cases.items():
            self.assertEqual(self.refusal(fx.forge(self.path, self.fresh("s"), snapshot_edit=edit)), code, name)
        pid = self.w.preview_identity
        cases = {
            "extra_file": (lambda f: f.update({"notes.txt": b"x"}), "SHADOW_BUNDLE_MEMBERSHIP_MISMATCH"),
            "missing_receipt": (lambda f: f.pop(shadow.ANCHOR_MEMBER), "SHADOW_BUNDLE_MEMBERSHIP_MISMATCH"),
            "preview_bytes": (lambda f: f.update({f"preview/{pid}/preview.json": f[f"preview/{pid}/preview.json"]
                                                  .replace(b'"schema"', b'"schema" ')}),
                              "SHADOW_INPUT_PREVIEW_CANONICAL_FORM_MISMATCH"),
            "capsule_raw": (lambda f: f.update({k: v + b" " for k, v in f.items() if k.endswith("provider-response.json")}),
                            "SHADOW_INPUT_INPUT_RAW_NOT_PINNED_ORIGINAL"),
            "payload_pretty": (lambda f: f.update({shadow.PAYLOAD_FILE: json.dumps(json.loads(
                f[shadow.PAYLOAD_FILE].decode("utf-8")), indent=1, sort_keys=True).encode("utf-8") + b"\n"}),
                "SHADOW_PAYLOAD_CANONICAL_FORM_MISMATCH"),
            "receipt_duplicate_member": (lambda f: f.update({shadow.ANCHOR_MEMBER: b'{"id":"1",' +
                                                             f[shadow.ANCHOR_MEMBER][1:]}),
                                         "SHADOW_ANCHOR_RECEIPT_MALFORMED"),
        }
        for name, (edit, code) in cases.items():
            self.assertEqual(self.refusal(fx.forge(self.path, self.fresh("b"), file_edit=edit)), code, name)
        files = fx.read_tree(self.path.parent)
        pretty = self.fresh("p") / self.path.parent.name
        snap = json.loads(files.pop(shadow.SNAPSHOT_FILE).decode("utf-8"))
        fx.write_tree(pretty, {**files, shadow.SNAPSHOT_FILE: (json.dumps(snap, indent=1) + "\n").encode("utf-8")})
        self.assertEqual(self.refusal(pretty / shadow.SNAPSHOT_FILE), "SHADOW_SNAPSHOT_CANONICAL_FORM_MISMATCH")
        wrong = self.fresh("x") / ("f" * 64)
        fx.write_tree(wrong, fx.read_tree(self.path.parent))
        self.assertEqual(self.refusal(wrong / shadow.SNAPSHOT_FILE), "SHADOW_IDENTITY_MISMATCH")
        plain = self.fresh("x") / "not-an-identity"
        fx.write_tree(plain, fx.read_tree(self.path.parent))
        self.assertEqual(self.refusal(plain / shadow.SNAPSHOT_FILE), "SHADOW_LOCATION_INVALID")
        other = fx.ShadowWorld(self.fresh("w"), fx.copy_events(lambda ev: ev.pop()))
        swapped = self.fresh("c") / self.path.parent.name
        fx.write_tree(swapped, {**fx.read_tree(self.path.parent), })
        Path(fx.ext(swapped / "inputs" / "contract.json")).write_bytes(other.contract)
        self.assertEqual(self.refusal(swapped / shadow.SNAPSHOT_FILE), "CONTRACT_NOT_COMMITTED_AUTHORITY")

    @unittest.skipUnless(os.name == "nt", "Windows location rules")
    def test_network_device_and_non_literal_locations_refuse_before_access(self) -> None:
        for path, refusal in ((r"\\fixture-server\share" + "\\" + "a" * 64 + r"\snapshot.json",
                               "SHADOW_LOCATION_UNSUPPORTED"),
                              (r"\\.\PhysicalDrive0", "SHADOW_LOCATION_UNSUPPORTED"),
                              (r"\\?\GLOBALROOT\Device\x\snapshot.json", "SHADOW_LOCATION_UNSUPPORTED"),
                              ("\\\\?\\" + str(self.path.parent) + r"\..\x" + "\\" + "a" * 64 + r"\snapshot.json",
                               "SHADOW_LOCATION_NOT_LITERAL")):
            self.assertEqual(self.refusal(path), refusal, path)


class PortableSnapshotTests(_Workspace):
    def test_rehoused_relative_equals_form_long_and_junction_spellings_serve_identically(self) -> None:
        world = self.world()
        b = world.build(self.fresh())
        argv = ["--grain", "shadow-prediction", "--cutoff", CUTOFF, "--all"]
        _, original, err = self.run_cli(["--prospective-shadow", str(b["path"]), *argv], world, b["profile"])
        self.assertIsNotNone(original, err)
        moved = fx.rehouse(b["path"], self.fresh("elsewhere"))
        _, rehoused, err = self.run_cli(["--prospective-shadow", str(moved), *argv], world, b["profile"])
        self.assertEqual(rehoused["rows"], original["rows"], err)
        relative = os.path.relpath(moved, Path.cwd()) if moved.drive == Path.cwd().drive else str(moved)
        _, rel_doc, err = self.run_cli(["--prospective-shadow", relative, *argv], world, b["profile"])
        self.assertEqual(rel_doc["rows"], original["rows"], err)
        _, eq_doc, err = self.run_cli([f"--prospective-shadow={moved}", *argv], world, b["profile"])
        self.assertEqual(eq_doc["rows"], original["rows"], err)
        if os.name == "nt":
            far = os.path.join(os.path.abspath(self.tmp), "long " + "x" * 110, "deeper " + "y" * 110, "tail",
                               b["path"].parent.name)
            target = "\\\\?\\" + far
            self.assertGreater(len(target), 300)
            fx.write_tree(target, fx.read_tree(b["path"].parent))
            _, long_doc, err = self.run_cli(["--prospective-shadow", os.path.join(target, "snapshot.json"), *argv],
                                            world, b["profile"])
            self.assertEqual(long_doc["rows"], original["rows"], err)
            import _winapi  # noqa: PLC0415
            link = self.tmp / "jx"
            _winapi.CreateJunction(str(moved.parent.parent), str(link))
            self.addCleanup(os.rmdir, str(link))
            _, junction_doc, err = self.run_cli(["--prospective-shadow", str(link / moved.parent.name /
                                                                              "snapshot.json"), *argv],
                                                world, b["profile"])
            self.assertEqual(junction_doc["rows"], original["rows"], err)


class MountedGenuineShadowTests(unittest.TestCase):
    """The genuine accepted preview and, once frozen, the genuine snapshot through the committed authority (mounted
    lanes only)."""

    def data_root(self) -> Path:
        root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        if not root:
            self.skipTest("mounted data root required")
        return Path(root)

    def test_genuine_preview_derives_the_complete_payload_population(self) -> None:
        pins = json.loads(fx.CONTRACT_PATH.read_text(encoding="utf-8"))["input"]
        path = self.data_root() / "canonical" / preview.POPULATION / "sha256" / pins["preview_identity"] / \
            preview.PREVIEW_FILE
        if not path.is_file():
            self.skipTest(f"accepted preview not mounted at {path}")
        _spec, data, doc = shadow.payload_files(fx.CONTRACT_PATH.read_bytes(), path)
        self.assertEqual((doc["counts"]["events"], doc["counts"]["participants"], doc["counts"]["predictions"]),
                         (25, 50, 100))
        self.assertEqual(len({x["event_key"] for x in doc["predictions"]}), 25)
        frozen = self.data_root() / "canonical" / shadow.POPULATION / "payload" / "sha256" / \
            hashlib.sha256(data).hexdigest() / shadow.PAYLOAD_FILE
        if frozen.is_file():
            self.assertEqual(frozen.read_bytes(), data)

    def test_genuine_snapshot_verifies_against_the_packaged_gate(self) -> None:
        if shadow.ANCHOR_PROFILE is None:
            self.skipTest("no actual anchor profile is packaged yet")
        snapshot = self.data_root() / "canonical" / shadow.POPULATION / "sha256" / \
            shadow.ANCHOR_PROFILE["snapshot_identity"] / shadow.SNAPSHOT_FILE
        if not snapshot.is_file():
            self.skipTest(f"genuine snapshot not mounted at {snapshot}")
        binding = shadow.verify_snapshot(snapshot, expect_identity=shadow.ANCHOR_PROFILE["snapshot_identity"])
        snap = binding["snapshot"]
        self.assertEqual((snap["counts"]["events"], snap["counts"]["participants"], snap["counts"]["predictions"]),
                         (25, 50, 100))
        self.assertEqual(snap["anchor"]["created"], snap["anchor"]["updated"])
        self.assertTrue(binding["profile_pinned"])
        self.assertEqual(snap["counts"]["anchored_events"] + snap["counts"]["ineligible_events"], 25)


if __name__ == "__main__":
    unittest.main()
