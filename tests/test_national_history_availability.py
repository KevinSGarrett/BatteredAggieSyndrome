"""BAT-714 archive-supported 2019 prior-game history availability: derivation, producer and validator (Cycle #42).

Derivation cases run on a hand-made 2019 population and its accepted BAT-711 history parent with an in-memory archive
view; producer and validator cases run on the synthetic population/history/source-time/archive world of
``national_history_availability_fixture`` (fictional records only). Mounted cases read the delivered projection only
when the private data root is mounted.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_history_availability_fixture as fx  # noqa: E402
from aggie_analytics.national_history import availability as core  # noqa: E402

STATE: dict = {}


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    base = Path(STATE["tmp"].name)
    STATE["unit"] = fx.unit_world(base / "u")
    STATE["world"] = fx.build_world(base / "g")
    code, result, err = fx.run_build(STATE["world"])
    assert code == 0, err
    STATE["result"] = result


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def projection(**kw) -> core.Projection:
    unit = STATE["unit"]
    rows = kw.pop("rows", unit["rows"])
    return core.Projection(rows, kw.pop("subset", unit["subset"]), kw.pop("targets", unit["history_targets"]),
                           kw.pop("views", unit["history_views"]), kw.pop("archive", fx.unit_archive(rows)), **kw)


def rel(p: core.Projection, target: str, view: str, prior: str) -> dict:
    return next(r for r in p.relationships[(target, view)] if r["prior_contest_key"] == prior)


def evidence(p: core.Projection) -> dict:
    return {e["contest_key"]: e for e in p.evidence}


class DerivationTests(unittest.TestCase):
    def test_targets_views_and_complete_expected_relationships(self) -> None:
        p = projection()
        self.assertEqual(p.target_keys, ["ncaa:9002", "ncaa:9003", "ncaa:9004", "ncaa:9006", "ncaa:9008", "ncaa:9010"])
        self.assertEqual(len(p.views), 12)
        # team 2 before ncaa:9008 (09-28): the 20-20 tie, a win/loss and the CONFLICT contest as a parent-excluded prior
        view = p.views[("ncaa:9008", "A")]
        self.assertEqual(view["relationship_contest_keys"], ["ncaa:9002", "ncaa:9003", "ncaa:9007"])
        self.assertEqual((view["expected_prior_relationships"], view["history_pool_priors"],
                          view["parent_excluded_priors"]), (3, 2, 1))
        excluded = rel(p, "ncaa:9008", "A", "ncaa:9007")
        self.assertEqual(excluded["relationship_class"], "PARENT_EXCLUDED_PRIOR")
        self.assertIsNone(excluded["parent_result"])
        self.assertIn("DISPOSITION_NOT_VERIFIED_PRESENT", excluded["parent_exclusion_reasons"])
        tie = rel(p, "ncaa:9008", "A", "ncaa:9002")
        self.assertEqual(tie["parent_result"], {"points_for": 20, "points_against": 20, "result": "T"})
        # Echo's same-date game and the undated contest are exclusions, never relationships; later games are counted
        echo = p.views[("ncaa:9004", "B")]
        self.assertEqual(echo["history_state"], "COLD_START_NO_EXPECTED_PRIORS")
        self.assertEqual([x["contest_key"] for x in echo["same_date_excluded"]], ["ncaa:9005"])
        self.assertEqual(echo["same_date_excluded"][0]["reasons"], ["SAME_DATE_NOT_STRICTLY_EARLIER"])
        self.assertEqual([x["contest_key"] for x in echo["undated_excluded"]], ["ncaa:9009"])
        self.assertIn("DATE_INVALID", echo["undated_excluded"][0]["reasons"])
        self.assertEqual(echo["later_contests_excluded"], 3)
        # an FCS opponent stays in the expected graph with its own division label
        fcs = rel(p, "ncaa:9010", "A", "ncaa:9005")
        self.assertEqual((fcs["prior_opponent_key"], fcs["prior_opponent_division_label"], fcs["prior_side"]),
                         ("org:6", "FCS", "A"))
        # the current opponent is the target's other participant, never a prior row's opponent
        self.assertTrue(all(r["current_opponent_key"] == "org:1" for r in p.relationships[("ncaa:9010", "A")]))
        for rels in p.relationships.values():
            for r in rels:
                self.assertLess(r["prior_contest_date"], r["target_date"])
                self.assertNotEqual(r["prior_contest_key"], r["target_contest_key"])

    def test_history_parent_is_reconciled_both_ways(self) -> None:
        unit = STATE["unit"]
        views = copy.deepcopy(unit["history_views"])
        views[-1]["team_history"]["contributing"] = views[-1]["team_history"]["contributing"][:-1]
        with self.assertRaises(core.AvailabilityError) as ctx:
            projection(views=views)
        self.assertEqual(ctx.exception.code, "HISTORY_PARENT_MISMATCH")
        views = copy.deepcopy(unit["history_views"])
        views[-1]["opponent_history"]["excluded_inputs"] = []
        with self.assertRaises(core.AvailabilityError) as ctx:
            projection(views=views)
        self.assertEqual(ctx.exception.code, "HISTORY_PARENT_MISMATCH")
        with self.assertRaises(core.AvailabilityError) as ctx:
            projection(targets=unit["history_targets"][:-1])
        self.assertEqual(ctx.exception.code, "HISTORY_PARENT_MISMATCH")

    def test_subset_and_duplicate_parent_rows_refuse(self) -> None:
        rows = copy.deepcopy(STATE["unit"]["rows"])
        next(r for r in rows if r["contest_key"] == "ncaa:9003")["b_division_label"] = "FCS"
        with self.assertRaises(core.AvailabilityError) as ctx:
            core.Projection(rows, STATE["unit"]["subset"], [], [], fx.unit_archive(STATE["unit"]["rows"]))
        self.assertEqual(ctx.exception.code, "SUBSET_FIELD_INCONSISTENT")
        rows = STATE["unit"]["rows"] + [STATE["unit"]["rows"][0]]
        with self.assertRaises(core.AvailabilityError) as ctx:
            core.Projection(rows, STATE["unit"]["subset"], [], [], fx.unit_archive(STATE["unit"]["rows"]))
        self.assertEqual(ctx.exception.code, "PARENT_DUPLICATE_KEY")

    def test_evidence_classes_keep_missing_partial_quarantined_contradicted_distinct(self) -> None:
        ev = evidence(projection())
        expected = {"ncaa:9001": "ARCHIVE_COHERENT_VERSION", "ncaa:9002": "ARCHIVE_COHERENT_VERSION",
                    "ncaa:9003": "ARCHIVE_VERSION_CONTRADICTS_PARENT", "ncaa:9004": "ARCHIVE_ALL_VERSIONS_QUARANTINED",
                    "ncaa:9005": "NOT_IN_ARCHIVE_TRANCHE", "ncaa:9006": "ARCHIVE_NO_CAPTURE",
                    "ncaa:9007": "ARCHIVE_COHERENT_VERSION", "ncaa:9008": "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION"}
        for key, cls in expected.items():
            self.assertEqual(ev[key]["archive"]["evidence_class"], cls, key)
        two = ev["ncaa:9002"]["archive"]
        self.assertEqual([v["capture_id"] for v in two["versions"]], ["wb:9002a", "wb:9002b"])
        self.assertEqual(two["coherent_capture_ids"], ["wb:9002b"])
        self.assertEqual(two["coherent_upper_bound_utc"], "2019-09-02T10:00:00.999999Z")
        # per-field earliest bounds are reported, but never combined into support
        self.assertEqual(two["field_earliest_qualified_upper_bound_utc"]["contest_date"], "2019-08-31T12:00:00.999999Z")
        self.assertEqual(ev["ncaa:9003"]["archive"]["contradicting_capture_ids"], ["wb:9003b"])
        self.assertEqual(ev["ncaa:9003"]["archive"]["evidence_reason"], "CONTRADICTING_VERSIONS:wb:9003b[a_points]")
        self.assertEqual(ev["ncaa:9008"]["archive"]["evidence_reason"],
                         "FIELDS_NEVER_QUALIFIED_IN_ANY_VERSION:completion/a_points/b_points")
        self.assertEqual(ev["ncaa:9006"]["archive"]["evidence_reason"], "ARCHIVE_DISPOSITION:NO_ARCHIVE_CAPTURE_REPORTED")
        self.assertTrue(ev["ncaa:9001"]["archive"]["parent_values_agree"])
        self.assertIsNone(ev["ncaa:9007"]["parent_values"])
        self.assertEqual(ev["ncaa:9001"]["earliest_event_instant_utc"], "2019-08-30T10:00:00.000000Z")

    def test_cutoff_equality_microsecond_zone_and_event_boundaries(self) -> None:
        p = projection()
        ev = evidence(p)
        r = rel(p, "ncaa:9003", "A", "ncaa:9001")
        decide = lambda text: core.decide(r, ev["ncaa:9001"], fx.at(text))  # noqa: E731
        self.assertEqual(decide("2019-09-01T04:15:00.999999Z")["support_state"], "SUPPORTED")
        self.assertEqual(decide("2019-09-01T04:15:00.999999Z")["supporting_capture_ids"], ["wb:9001"])
        before = decide("2019-09-01T04:15:00.999998Z")
        self.assertEqual((before["support_state"], before["result_published_by_cutoff"], before["reason_class"]),
                         ("UNSUPPORTED", "UNKNOWN", "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF"))
        self.assertEqual(decide("2019-08-31T23:15:00.999999-05:00")["support_state"], "SUPPORTED")
        self.assertEqual(decide("2019-09-01T04:15:00Z")["support_state"], "UNSUPPORTED")
        early = decide("2019-08-01T00:00:00Z")
        self.assertEqual((early["result_published_by_cutoff"], early["reason_class"]),
                         ("FALSE", "OUTCOME_CANNOT_EXIST_BEFORE_PRIOR_EVENT_DATE"))
        # a pregame version (date and participants only) never supports a result, and versions are not combined
        tie = rel(p, "ncaa:9003", "B", "ncaa:9002")
        mid = core.decide(tie, ev["ncaa:9002"], fx.at("2019-09-01T00:00:00Z"))
        self.assertEqual((mid["support_state"], mid["reason_class"]), ("UNSUPPORTED", "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF"))
        self.assertEqual(core.decide(tie, ev["ncaa:9002"], fx.at("2019-09-02T10:00:00.999999Z"))["support_state"],
                         "SUPPORTED")
        contradicted = core.decide(rel(p, "ncaa:9006", "A", "ncaa:9003"), ev["ncaa:9003"], fx.at("2026-01-01T00:00:00Z"))
        self.assertEqual((contradicted["support_state"], contradicted["result_published_by_cutoff"]),
                         ("UNSUPPORTED", "UNKNOWN"))
        quarantined = core.decide(rel(p, "ncaa:9006", "B", "ncaa:9004"), ev["ncaa:9004"], fx.at("2026-01-01T00:00:00Z"))
        self.assertEqual(quarantined["result_published_by_cutoff"], "NO_QUALIFIED_ARCHIVE_ASSERTION")
        excluded = core.decide(rel(p, "ncaa:9008", "A", "ncaa:9007"), ev["ncaa:9007"], fx.at("2026-01-01T00:00:00Z"))
        self.assertEqual(excluded["support_state"], "EXCLUDED_FROM_HISTORY_POOL")

    def test_supported_subset_totals_and_exact_rates(self) -> None:
        p = projection()
        ev = evidence(p)
        late = fx.at("2026-01-01T00:00:00Z")
        # team 2 before ncaa:9008: tie (supported), ncaa:9003 (contradicted), ncaa:9007 (parent excluded)
        s = core.summarize("org:2", p.relationships[("ncaa:9008", "A")], ev, late)
        self.assertEqual((s["expected_prior_relationships"], s["history_pool_priors"], s["parent_excluded_priors"],
                          s["supported_priors"], s["unsupported_priors"]), (3, 2, 1, 1, 1))
        self.assertEqual(s["unsupported_by_reason_class"]["ARCHIVE_VERSION_CONTRADICTS_PARENT"], 1)
        self.assertEqual(sum(s["unsupported_by_reason_class"].values()), 1)
        sub = s["supported_subset"]
        self.assertEqual((sub["games"], sub["wins"], sub["losses"], sub["ties"], sub["points_for_total"],
                          sub["points_against_total"], sub["margin_total"]), (1, 0, 0, 1, 20, 20, 0))
        self.assertEqual(sub["win_rate"], {"numerator": 0, "denominator": 1})
        self.assertEqual(s["completeness_state"], "PARTIAL_SUPPORTED_SUBSET")
        self.assertFalse(s["supported_subset_is_complete_history"])
        # nothing supported: rates are null, never zero
        none = core.summarize("org:2", p.relationships[("ncaa:9008", "A")], ev, fx.at("2019-08-01T00:00:00Z"))
        self.assertEqual(none["completeness_state"], "NO_SUPPORTED_PRIORS")
        self.assertIsNone(none["supported_subset"]["win_rate"])
        self.assertIsNone(none["supported_subset"]["margin_mean"])
        cold = core.summarize("org:5", p.relationships[("ncaa:9004", "B")], ev, late)
        self.assertEqual(cold["completeness_state"], "COLD_START_NO_EXPECTED_PRIORS")
        self.assertIsNone(cold["supported_subset"]["points_for_mean"])
        # unreduced exact rates: team 1 before ncaa:9006 is 2 supported wins of 2? 9001 coherent, 9003 contradicted
        team1 = core.summarize("org:1", p.relationships[("ncaa:9006", "A")], ev, late)
        self.assertEqual(team1["supported_subset"]["points_for_mean"], {"numerator": 35, "denominator": 1})

    def test_archive_parent_value_contradiction_refuses(self) -> None:
        rows = STATE["unit"]["rows"]
        view = fx.unit_archive(rows)
        view.dispositions["ncaa:9001"]["parent_values"]["a_points"] = 36
        with self.assertRaises(core.AvailabilityError) as ctx:
            projection(archive=view)
        self.assertEqual(ctx.exception.code, "ARCHIVE_PARENT_VALUE_CONTRADICTION")

    def test_input_orders_reproduce_identical_payloads(self) -> None:
        natural = projection().payloads()
        for order in ("reverse", "shuffle:17", "shuffle:3"):
            self.assertEqual(projection(input_order=order).payloads(), natural, order)
        with self.assertRaises(core.AvailabilityError) as ctx:
            projection(input_order="sideways")
        self.assertEqual(ctx.exception.code, "INPUT_ORDER_INVALID")

    def test_closed_schema_refuses_unknown_fields_and_floats(self) -> None:
        p = projection()
        record = copy.deepcopy(p.relationships[("ncaa:9008", "A")][0])
        record["known_at"] = "2019-01-01T00:00:00Z"
        with self.assertRaises(core.AvailabilityError) as ctx:
            core.record_line(record)
        self.assertEqual(ctx.exception.code, "UNKNOWN_FIELD")
        record = copy.deepcopy(p.relationships[("ncaa:9008", "A")][0])
        record["parent_result"]["points_for"] = 20.0
        with self.assertRaises(core.AvailabilityError) as ctx:
            core.record_line(record)
        self.assertEqual(ctx.exception.code, "FLOAT_IN_PAYLOAD")

    def test_mismatch_reaches_its_semantic_class(self) -> None:
        payloads = projection().payloads()
        rels = payloads["relationships.jsonl"].splitlines(keepends=True)
        decoded = [json.loads(x) for x in rels]

        def lines(records):
            return [core.canonical_json_bytes(r) + b"\n" for r in records]

        def code(name, records):
            base = payloads[name].splitlines(keepends=True)
            return core.mismatch(name, base, lines(records))[0]
        self.assertIsNone(core.mismatch("relationships.jsonl", rels, rels))
        self.assertEqual(code("relationships.jsonl", decoded[1:]), "RELATIONSHIP_COLLECTION_MISMATCH")
        later = copy.deepcopy(decoded[0])
        later["prior_contest_key"], later["prior_contest_date"] = "ncaa:9999", later["target_date"]
        self.assertEqual(code("relationships.jsonl", decoded + [later]), "RELATIONSHIP_TEMPORAL_ORDER_VIOLATION")
        swapped = copy.deepcopy(decoded)
        pool = next(r for r in swapped if r["parent_result"] and r["parent_result"]["result"] != "T")
        pool["prior_side"] = "B" if pool["prior_side"] == "A" else "A"
        self.assertEqual(code("relationships.jsonl", swapped), "RELATIONSHIP_ORIENTATION_MISMATCH")
        promoted = copy.deepcopy(decoded)
        ex = next(r for r in promoted if r["relationship_class"] == "PARENT_EXCLUDED_PRIOR")
        ex["relationship_class"], ex["parent_exclusion_reasons"] = "HISTORY_POOL_PRIOR", []
        self.assertEqual(code("relationships.jsonl", promoted), "RELATIONSHIP_CLASS_MISMATCH")
        forged = copy.deepcopy(decoded)
        forged[0]["pit_admission"] = "ADMITTED"
        self.assertEqual(code("relationships.jsonl", forged), "FORGED_AUTHORITY_LABEL")
        self.assertEqual(code("relationships.jsonl", list(reversed(decoded))), "RECORD_ORDER_MISMATCH")
        ev = [json.loads(x) for x in payloads["evidence.jsonl"].splitlines()]
        moved = copy.deepcopy(ev)
        e = next(x for x in moved if x["archive"]["evidence_class"] == "ARCHIVE_COHERENT_VERSION")
        e["archive"]["coherent_upper_bound_utc"] = "2019-01-01T00:00:00.000000Z"
        self.assertEqual(code("evidence.jsonl", moved), "EVIDENCE_SUPPORT_FORGERY")
        dropped = copy.deepcopy(ev)
        e = next(x for x in dropped if len(x["archive"]["versions"]) == 2)
        e["archive"]["versions"] = e["archive"]["versions"][1:]
        self.assertEqual(code("evidence.jsonl", dropped), "EVIDENCE_VERSION_COLLECTION_MISMATCH")
        views = [json.loads(x) for x in payloads["views.jsonl"].splitlines()]
        swapped_views = copy.deepcopy(views)
        swapped_views[0]["team_key"], swapped_views[0]["opponent_key"] = views[0]["opponent_key"], views[0]["team_key"]
        self.assertEqual(code("views.jsonl", swapped_views), "VIEW_ORIENTATION_MISMATCH")
        counted = copy.deepcopy(views)
        counted[0]["history_pool_priors"] += 1
        self.assertEqual(code("views.jsonl", counted), "VIEW_COUNT_MISMATCH")

    def test_cutoff_grammar_and_conservative_boundary(self) -> None:
        for text, code in ((None, "CUTOFF_REQUIRED"), ("2019-09-07", "CUTOFF_TIMEZONE_REQUIRED"),
                           ("2019-09-07T10:00:00", "CUTOFF_TIMEZONE_REQUIRED"), ("yesterday", "CUTOFF_INVALID"),
                           ("2019-09-07T10:00:00+15:00", "CUTOFF_INVALID")):
            with self.assertRaises(core.AvailabilityError) as ctx:
                core.parse_cutoff(text)
            self.assertEqual(ctx.exception.code, code, text)
        self.assertEqual(core.fmt(core.conservative_boundary("2019-09-07")), "2019-09-06T10:00:00.000000Z")
        position = core.cutoff_position("2019-09-07", fx.at("2019-09-06T09:59:59.999999Z"))
        self.assertEqual(position["position"], "BEFORE_CONSERVATIVE_TARGET_DATE_BOUNDARY")
        self.assertFalse(position["pregame_claim"])
        self.assertEqual(core.cutoff_position("2019-09-07", fx.at("2019-09-06T10:00:00Z"))["position"],
                         "AT_OR_AFTER_CONSERVATIVE_TARGET_DATE_BOUNDARY")


class ProducerTests(unittest.TestCase):
    def build(self, *extra: str, **kw):
        return fx.run_build(STATE["world"], *extra, **kw)

    def test_canonical_counts_identities_and_create_only_rerun(self) -> None:
        result = STATE["result"]
        self.assertEqual(result["row_counts"], {"targets.jsonl": 5, "views.jsonl": 10, "relationships.jsonl": 11,
                                                "evidence.jsonl": 5, "witnesses.jsonl": result["row_counts"][
                                                    "witnesses.jsonl"]})
        self.assertGreater(result["row_counts"]["witnesses.jsonl"], 0)
        manifest = json.loads(Path(result["content"]["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(fx.sha(core.canonical_json_bytes(manifest["identity_document"])), result["content_identity"])
        code, again, err = self.build()
        self.assertEqual(code, 0, err)
        self.assertEqual((again["state"], again["database_state"]), ("ALREADY_PRESENT_IDENTICAL",
                                                                     "ALREADY_PRESENT_IDENTICAL"))
        self.assertEqual(again["database_identity"], result["database_identity"])
        targets = fx.read_payload(result, "targets.jsonl")
        self.assertTrue(all(t["pit_admission"] == "NOT_ADMITTED" for t in targets))
        self.assertNotIn("a_points", json.dumps(targets))

    def test_every_variant_reproduces_content_and_physical_identity(self) -> None:
        base = Path(STATE["tmp"].name) / "variants"
        for index, spec in enumerate(STATE["world"]["contract_doc"]["build"]["variants"]):
            run = base / f"v{index}"  # short names keep the deepest output path within MAX_PATH under long temp roots
            out = run / "canonical" / core.POPULATION
            man = run / "manifests" / core.POPULATION
            args = [a.replace("<scratch>", str(run / "ck")) for a in spec["args"]]
            if spec.get("then"):
                # the synthetic world has five targets, so the declared stop (10 chunks of 17) becomes 2 chunks of 1
                interrupted = ["--chunk-size", "1", "--checkpoint-dir", str(run / "ck"),
                               "--stop-after-chunks", "2"]
                code, first, err = self.build(*interrupted, out=out, manifests=man)
                self.assertEqual(code, 3, err)
                self.assertEqual(first["state"], "INTERRUPTED_AT_CHECKPOINT")
                self.assertFalse(out.exists())
                args = ["--chunk-size", "1", "--checkpoint-dir", str(run / "ck"), "--resume"]
            code, got, err = self.build(*args, out=out, manifests=man)
            self.assertEqual(code, 0, f"{spec['id']}: {err}")
            self.assertEqual(got["content_identity"], STATE["result"]["content_identity"], spec["id"])
            self.assertEqual(got["database_identity"], STATE["result"]["database_identity"], spec["id"])

    def test_checkpoint_refusals(self) -> None:
        base = Path(STATE["tmp"].name) / "ck"
        out, man = base / "o", base / "m"
        ck = base / "c"
        code, _r, err = self.build("--chunk-size", "1", "--checkpoint-dir", str(ck), "--stop-after-chunks", "2",
                                   out=out, manifests=man)
        self.assertEqual(code, 3, err)
        code, _r, err = self.build("--chunk-size", "1", "--checkpoint-dir", str(ck), out=out, manifests=man)
        self.assertEqual(fx.refusal(err), "CHECKPOINT_EXISTS")
        code, _r, err = self.build("--chunk-size", "2", "--checkpoint-dir", str(ck), "--resume", out=out, manifests=man)
        self.assertEqual(fx.refusal(err), "REFUSED_STALE_CHECKPOINT")
        chunk = ck / "chunks" / "chunk_000001.jsonl"
        chunk.write_bytes(chunk.read_bytes().replace(b"org:", b"org:9", 1))
        code, _r, err = self.build("--chunk-size", "1", "--checkpoint-dir", str(ck), "--resume", out=out, manifests=man)
        self.assertEqual(fx.refusal(err), "REFUSED_ALTERED_PREFIX")
        self.assertFalse(out.exists())

    def test_wrong_inputs_and_contracts_refuse_before_writing(self) -> None:
        world = STATE["world"]
        base = Path(STATE["tmp"].name) / "wrong"
        out, man = base / "o", base / "m"
        bindings = json.loads(Path(world["bindings"]).read_text(encoding="utf-8"))
        moved = dict(bindings, history_database=dict(bindings["history_database"],
                                                     path=bindings["population_database"]["path"]))
        path = fx.write(base / "b1.json", json.dumps(moved).encode("utf-8"))
        code, _r, err = self.build(bindings=path, out=out, manifests=man)
        self.assertEqual(fx.refusal(err), "PARENT_BINDING_MISMATCH")
        cases = {"FORGED_AUTHORITY_LABEL": lambda c: c["row_labels"].update(pit_admission="ADMITTED"),
                 "CONTRACT_INVALID": lambda c: c["payloads"]["record_fields"]["relationship"].append("known_at"),
                 "CONTRACT_SCHEMA_UNKNOWN": lambda c: c.update(contract_id="BAT-714-SOMETHING-ELSE")}
        for expected, mutate in cases.items():
            contract = copy.deepcopy(world["contract_doc"])
            mutate(contract)
            path = fx.write(base / f"{expected}.json", json.dumps(contract).encode("utf-8"))
            code, _r, err = self.build(contract=path, out=out, manifests=man)
            self.assertEqual(fx.refusal(err), expected)
        contract = copy.deepcopy(world["contract_doc"])
        contract["parent_binding"]["history"]["database_identity"] = "0" * 64
        path = fx.write(base / "stale.json", json.dumps(contract).encode("utf-8"))
        code, _r, err = self.build(contract=path, out=out, manifests=man)
        self.assertEqual(fx.refusal(err), "PARENT_BINDING_MISMATCH")
        self.assertFalse(out.exists())

    def test_existing_different_identity_is_never_overwritten(self) -> None:
        base = Path(STATE["tmp"].name) / "collision"
        out, man = base / "o", base / "m"
        target = out / "sha256" / STATE["result"]["content_identity"]
        target.mkdir(parents=True)
        (target / "targets.jsonl.gz").write_bytes(b"not the payload")
        code, _r, err = self.build(out=out, manifests=man)
        self.assertEqual(fx.refusal(err), "REFUSED_IMMUTABLE_COLLISION")
        self.assertEqual((target / "targets.jsonl.gz").read_bytes(), b"not the payload")


class ValidatorTests(unittest.TestCase):
    def test_independent_validator_passes_and_rejects_every_tamper(self) -> None:
        world, result = STATE["world"], STATE["result"]
        report = Path(STATE["tmp"].name) / "oracle" / "report.json"
        manifest = Path(result["content"]["manifest"])
        code = fx.validator().main(["--contract", str(world["contract"]), "--input-bindings", str(world["bindings"]),
                                    "--manifest", str(manifest), "--report", str(report),
                                    "--consumer-authority", str(world["authority_spec"]),
                                    "--consumer-source-root", str(fx.ROOT / "src")])
        doc = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, doc["failed_checks"])
        self.assertEqual(doc["result"], "PASS")
        self.assertEqual(doc["counts"]["targets"], 5)
        applied = [t for t in doc["tamper_cases"] if t["applied"]]
        self.assertGreaterEqual(len(applied), 15)
        self.assertTrue(all(t["rejected_for_intended_cause"] for t in applied))
        self.assertGreater(doc["decisions"]["supported_at_each_target_conservative_boundary"], 0)
        with self.assertRaises(SystemExit):
            fx.validator().main(["--contract", str(world["contract"]), "--input-bindings", str(world["bindings"]),
                                 "--manifest", str(manifest), "--report", str(report), "--skip-consumer"])

    def test_validator_fails_a_rehashed_semantic_forgery(self) -> None:
        world, result = STATE["world"], STATE["result"]
        base = Path(STATE["tmp"].name) / "forged"
        content = Path(result["content"]["data_dir"])
        manifest = json.loads(Path(result["content"]["manifest"]).read_text(encoding="utf-8"))
        records = fx.read_payload(result, "relationships.jsonl")
        records[0]["prior_side"] = "B" if records[0]["prior_side"] == "A" else "A"
        raw = b"".join(core.canonical_json_bytes(r) + b"\n" for r in records)
        packed = fx.builder().gzip_bytes(raw)
        document = copy.deepcopy(manifest["identity_document"])
        document["semantic_outputs"]["relationships.jsonl"] = fx.sha(raw)
        document["outputs"]["relationships.jsonl.gz"] = fx.sha(packed)
        identity = fx.sha(core.canonical_json_bytes(document))
        target = base / "canonical" / core.POPULATION / "sha256" / identity
        shutil.copytree(content, target)
        (target / "relationships.jsonl.gz").write_bytes(packed)
        mdir = base / "manifests" / core.POPULATION / "sha256" / identity
        mdir.mkdir(parents=True)
        (mdir / "run_manifest.json").write_text(json.dumps({"identity": identity, "identity_document": document,
                                                            "provenance": manifest["provenance"]}), encoding="utf-8")
        db_manifest = Path(result["database"]["manifest"])
        shutil.copytree(db_manifest.parent, mdir.parent / db_manifest.parent.name)
        shutil.copytree(Path(result["database"]["data_dir"]), target.parent / Path(result["database"]["data_dir"]).name)
        report = base / "report.json"
        code = fx.validator().main(["--contract", str(world["contract"]), "--input-bindings", str(world["bindings"]),
                                    "--manifest", str(mdir / "run_manifest.json"), "--report", str(report),
                                    "--skip-consumer"])
        doc = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertIn("every_delivered_record_equals_independent_reconstruction", doc["failed_checks"])
        self.assertEqual(doc["comparison"]["relationships.jsonl"]["field_mismatch_counts"].get("prior_side"), 1)

    def test_validator_fails_a_self_consistent_content_claim(self) -> None:
        """Genuine records under a coordinated alternative content document (payload schema changed, its own hash
        claimed by the content manifest, the database manifest and the meta): only the content binding fails."""
        world, result = STATE["world"], STATE["result"]
        base = Path(STATE["tmp"].name) / "claim"
        manifest = json.loads(Path(result["content"]["manifest"]).read_text(encoding="utf-8"))
        document = dict(manifest["identity_document"], payload_schema="BAS-NATIONAL-HISTORY-AVAILABILITY-PAYLOAD-X")
        identity = fx.sha(core.canonical_json_bytes(document))

        def mutate(conn) -> None:
            for key, value in (("content_identity", identity), ("payload_schema", document["payload_schema"])):
                conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))

        def patch(db_document: dict) -> None:
            db_document["content_identity"] = identity
        db = fx.rehashed_copy(world, result, base, mutate, patch)
        shutil.copytree(result["content"]["data_dir"], base / "canonical" / core.POPULATION / "sha256" / identity)
        mdir = base / "manifests" / core.POPULATION / "sha256" / identity
        mdir.mkdir(parents=True)
        provenance = dict(manifest["provenance"], database_identity=db.parent.name)
        (mdir / "run_manifest.json").write_text(json.dumps({"identity": identity, "identity_document": document,
                                                            "provenance": provenance}), encoding="utf-8")
        report = base / "report.json"
        code = fx.validator().main(["--contract", str(world["contract"]), "--input-bindings", str(world["bindings"]),
                                    "--manifest", str(mdir / "run_manifest.json"), "--report", str(report),
                                    "--skip-consumer"])
        doc = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(sorted(doc["failed_checks"]), ["content_identity_equals_independent_expected_digest",
                                                        "database_meta_restates_the_independent_content_document"])
        self.assertEqual(doc["content_binding"]["expected_identity"], result["content_identity"])


MOUNTED = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or "")
GATE = fx.ROOT / "artifacts" / "data_lake" / "national_history_availability_2019_gate.json"


@unittest.skipUnless(GATE.is_file() and os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") and
                     (MOUNTED / "canonical" / core.POPULATION).is_dir(), "the delivered projection is not mounted")
class MountedDeliveredProjectionTests(unittest.TestCase):
    def test_delivered_projection_matches_the_gate_and_opens_through_the_query(self) -> None:
        from aggie_analytics.national_history import availability_query as aq  # noqa: PLC0415
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        db = MOUNTED / "canonical" / core.POPULATION / "sha256" / gate["database_identity"] / core.DB_FILE
        content_manifest = MOUNTED / "manifests" / core.POPULATION / "sha256" / gate["content_identity"] / \
            "run_manifest.json"
        document = json.loads(content_manifest.read_text(encoding="utf-8"))["identity_document"]
        self.assertEqual(document, gate["content_identity_document"])
        self.assertEqual(fx.sha(core.canonical_json_bytes(document)), gate["content_identity"])
        with aq.HistoryAvailabilityDatabase(db, expect_identity=gate["database_identity"]) as handle:
            result = handle.query("target", cutoff="2026-10-05T00:00:00Z", limit=1)
        self.assertEqual(result["total"], gate["row_counts"]["targets.jsonl"])
        self.assertEqual(result["binding"]["contract_sha256"], gate["contract_sha256"])


if __name__ == "__main__":
    unittest.main()
