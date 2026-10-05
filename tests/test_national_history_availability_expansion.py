"""BAT-715 history-availability expansion successor (Cycle #43 TP43-A01): producer, consumer and validator.

One synthetic population/history/source-time world (``national_archived_publication_expansion_fixture``; fictional
records only) carries both archive sidecars: the V1.2 sidecar over the retained acquisition and the expansion sidecar
over the union of the tranche and the cohort. The accepted V1.0 projection is built over the first (before) and the
expansion successor over the second (after), each under its own contract, population and synthetic issued authority.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_archived_publication_expansion_fixture as xfx  # noqa: E402
import national_archived_publication_fixture as apfx  # noqa: E402
import national_history_availability_fixture as fx  # noqa: E402
from aggie_analytics.national_history import availability as core  # noqa: E402
from aggie_analytics.national_history import availability_query as aq  # noqa: E402

EXPANSION_CONTRACT_PATH = fx.ROOT / "configs" / "national_history_availability_2019_expansion_contract.json"
LATE = "2026-10-05T00:00:00Z"
STATE: dict = {}


def _sqlite_sha(path: Path) -> str:
    return fx.sha(Path(path).read_bytes())


def _common_parent(xw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Path]]:
    st_world, st_result = xw["st_world"], xw["st_result"]
    population_db, history_db, st_db = Path(st_world["population_db"]), Path(st_world["history_db"]), \
        Path(xw["st_db"])
    pop_doc = json.loads(aq.manifest_path_for(population_db).read_text(encoding="utf-8"))["identity_document"]
    hist = st_world["history_built"]
    hist_doc = json.loads(aq.manifest_path_for(history_db).read_text(encoding="utf-8"))["identity_document"]
    parent = {
        "population": {"query_db_identity": population_db.parent.name, "sqlite_sha256": _sqlite_sha(population_db),
                       "contract_sha256": pop_doc["contract_sha256"], "contest_identity": pop_doc["upstream"]["contest"],
                       "program_season_identity": pop_doc["upstream"]["program-season"]},
        "history": {"database_identity": hist["database_identity"], "sqlite_sha256": _sqlite_sha(history_db),
                    "content_identity": hist["content_identity"], "contract_sha256": hist_doc["contract_sha256"]},
        "source_time": {"database_identity": st_result["database_identity"], "sqlite_sha256": _sqlite_sha(st_db),
                        "content_identity": st_result["content_identity"],
                        "contract_sha256": st_result["contract_sha256"]}}
    return parent, {"population": population_db, "history": history_db, "source_time": st_db}


def _world(base: Path, name: str, template: Path, parent: dict[str, Any], paths: dict[str, Path],
           bindings: dict[str, Any], archive_authority: Any, archive_spec: dict[str, Any],
           population: str) -> dict[str, Any]:
    prep = base / f"{name}p"
    bindings_path = fx.write(prep / "INPUT_BINDINGS.json", json.dumps(bindings, indent=2).encode("utf-8"))
    contract = json.loads(template.read_text(encoding="utf-8"))
    for key, values in parent.items():
        contract["parent_binding"][key].update(values)
    contract["parent_binding"]["input_bindings"]["sha256"] = fx.sha(bindings_path.read_bytes())
    contract_path = fx.write(prep / "contract.json", (json.dumps(contract, indent=2) + "\n").encode("utf-8"))
    authority = {"contract_id": contract["contract_id"], "contract_sha256": fx.sha(contract_path.read_bytes()),
                 "parent": parent}
    spec_path = fx.write(prep / "authority.json",
                         json.dumps({"availability": authority, "archive": archive_spec}).encode("utf-8"))
    return {"base": base, "parent": parent, "paths": paths, "bindings": bindings_path, "bindings_doc": bindings,
            "contract": contract_path, "contract_doc": contract, "authority": authority,
            "archive_authority": archive_authority, "authority_spec": spec_path,
            "out": base / "o" / "canonical" / population, "manifests": base / "o" / "manifests" / population}


def build_worlds(base: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """The expansion archive world, then the V1.0 (before) and expansion (after) availability worlds over it."""
    xw = xfx.build_expansion_world(base / "a")
    v12 = xw["v12_world"]
    code, v12_built, err = apfx.run_build(v12)
    assert code == 0, err
    capture = xfx.run_capture(xw)
    assert capture["state"] == "FINALIZED", capture
    code, x_built, err = xfx.run_build(xw)
    assert code == 0, err
    parent, paths = _common_parent(xw)
    v12_db, x_db = apfx.database_path(v12_built), xfx.database_path(x_built)
    retained = xw["retained"]["acquisition_identity"]
    common = {"cycle_number": 43, "attempt_number": 1,
              "population_database": {"path": str(paths["population"]),
                                      "sha256": parent["population"]["sqlite_sha256"],
                                      "identity": parent["population"]["query_db_identity"]},
              "history_database": {"path": str(paths["history"]), "sha256": parent["history"]["sqlite_sha256"],
                                   "identity": parent["history"]["database_identity"]},
              "source_time_database": {"path": str(paths["source_time"]),
                                       "sha256": parent["source_time"]["sqlite_sha256"],
                                       "identity": parent["source_time"]["database_identity"]},
              "archive_tranche": {"path": str(xw["tranche"]), "sha256": fx.sha(Path(xw["tranche"]).read_bytes())},
              "control": {"path": str(xw["route"]), "sha256": fx.sha(Path(xw["route"]).read_bytes())}}
    before_parent = {**parent, "archive": {
        "database_identity": v12_built["database_identity"], "sqlite_sha256": _sqlite_sha(v12_db),
        "content_identity": v12_built["content_identity"], "contract_sha256": fx.sha(Path(v12["contract"]).read_bytes()),
        "contract_id": v12["contract_doc"]["contract_id"], "tranche_sha256": v12["contract_doc"]["scope"]["tranche_sha256"],
        "acquisition_identity": retained}}
    before_bindings = {**common,
                       "archive_database": {"path": str(v12_db), "sha256": before_parent["archive"]["sqlite_sha256"],
                                            "identity": v12_built["database_identity"]},
                       "archive_contract": {"path": str(v12["contract"]),
                                            "sha256": before_parent["archive"]["contract_sha256"]}}
    before = _world(base, "b", fx.CONTRACT_PATH, before_parent, {**paths, "archive": v12_db}, before_bindings,
                    apfx.issued_authority(v12), json.loads(apfx.authority_spec(v12)), core.POPULATION)
    xdoc = xw["x_contract_doc"]
    after_parent = {**parent, "archive": {
        "database_identity": x_built["database_identity"], "sqlite_sha256": _sqlite_sha(x_db),
        "content_identity": x_built["content_identity"], "contract_sha256": fx.sha(Path(xw["x_contract"]).read_bytes()),
        "contract_id": xdoc["contract_id"], "tranche_sha256": xdoc["scope"]["tranche_sha256"],
        "acquisition_identity": xfx.expansion_acquisition(xw).parent.name,
        "cohort_sha256": xdoc["scope"]["cohort_sha256"], "retained_acquisition_identity": retained}}
    after_bindings = {**common,
                      "archive_database": {"path": str(x_db), "sha256": after_parent["archive"]["sqlite_sha256"],
                                           "identity": x_built["database_identity"]},
                      "archive_contract": {"path": str(xw["x_contract"]),
                                           "sha256": after_parent["archive"]["contract_sha256"]},
                      "archive_cohort": {"path": str(xw["cohort"]), "sha256": xdoc["scope"]["cohort_sha256"]},
                      "archive_source_bindings": {"path": str(xw["x_bindings"]),
                                                  "sha256": fx.sha(Path(xw["x_bindings"]).read_bytes())},
                      "archive_retained_contract": {"path": str(v12["contract"]),
                                                    "sha256": fx.sha(Path(v12["contract"]).read_bytes())},
                      "archive_retained_root": {"path": str(v12["out"])}}
    after = _world(base, "x", EXPANSION_CONTRACT_PATH, after_parent, {**paths, "archive": x_db}, after_bindings,
                   xfx.issued_authority(xw), json.loads(xfx.authority_spec(xw)), core.EXPANSION_POPULATION)
    return xw, before, after


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    base = Path(STATE["tmp"].name)
    STATE["xw"], STATE["before"], STATE["after"] = build_worlds(base)
    for name in ("before", "after"):
        code, result, err = fx.run_build(STATE[name])
        assert code == 0, err
        STATE[f"{name}_result"] = result


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def payload(name: str, file: str) -> list[dict[str, Any]]:
    return fx.read_payload(STATE[f"{name}_result"], file)


def relationships(name: str, cutoff: str = LATE) -> list[dict[str, Any]]:
    world = STATE[name]
    code, doc, err = fx.query(world, fx.database_path(STATE[f"{name}_result"]), "--grain", "relationship",
                              "--season", "2019", "--cutoff", cutoff, "--all")
    assert code == 0, err
    return doc["rows"]


class ProjectionTests(unittest.TestCase):
    def test_contract_profile_population_and_parent_binding(self) -> None:
        contract = json.loads(EXPANSION_CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual((contract["contract_id"], contract["population_id"]),
                         (core.EXPANSION_CONTRACT_ID, core.EXPANSION_POPULATION))
        self.assertEqual(contract["row_labels"], core.ROW_LABELS)
        self.assertEqual(set(contract["parent_binding"]["archive"]) >= set(core.EXPANSION_PARENT_KEYS["archive"]), True)
        oracle = contract["validator"]["archive_oracle"]
        self.assertEqual(oracle["module"], "tools/validate_national_archived_publication_expansion.py")
        self.assertEqual(fx.sha((fx.ROOT / oracle["module"]).read_bytes()), oracle["sha256"])
        self.assertEqual(fx.sha((fx.ROOT / oracle["accepted_base_oracle"]["module"]).read_bytes()),
                         oracle["accepted_base_oracle"]["sha256"])
        self.assertEqual(core.profile(core.EXPANSION_CONTRACT_ID)["archive_parent"],
                         "national_archived_publication_2019_expansion")
        self.assertEqual(core.parent_files(core.CONTRACT_ID), core.PARENT_FILES)

    def test_expansion_identity_documents_name_their_own_population_and_full_archive_binding(self) -> None:
        result, after = STATE["after_result"], STATE["after"]
        content = json.loads(Path(result["content"]["manifest"]).read_text(encoding="utf-8"))["identity_document"]
        database = json.loads(Path(result["database"]["manifest"]).read_text(encoding="utf-8"))["identity_document"]
        self.assertEqual((content["population"], database["population"]), (core.EXPANSION_POPULATION,) * 2)
        self.assertEqual(content["contract_id"], core.EXPANSION_CONTRACT_ID)
        self.assertEqual(content["parent"], after["parent"])
        self.assertEqual(content["parent"]["archive"]["cohort_sha256"], after["contract_doc"]["scope"].get(
            "cohort_sha256", after["parent"]["archive"]["cohort_sha256"]))
        self.assertIn(core.EXPANSION_POPULATION, Path(result["content"]["data_dir"]).parts)
        self.assertNotEqual(result["content_identity"], STATE["before_result"]["content_identity"])

    def test_targets_views_and_relationships_are_unchanged_only_evidence_differs(self) -> None:
        before, after = STATE["before_result"], STATE["after_result"]
        for name in ("targets.jsonl", "views.jsonl", "relationships.jsonl"):
            self.assertEqual(payload("before", name), payload("after", name), name)
            self.assertEqual(before["row_counts"][name], after["row_counts"][name])
        self.assertEqual(before["row_counts"]["views.jsonl"], 2 * before["row_counts"]["targets.jsonl"])
        evidence_before = {e["contest_key"]: e for e in payload("before", "evidence.jsonl")}
        evidence_after = {e["contest_key"]: e for e in payload("after", "evidence.jsonl")}
        self.assertEqual(set(evidence_before), set(evidence_after))
        union = set(STATE["xw"]["union"])
        for key, e in evidence_after.items():
            self.assertEqual(e["archive"]["in_tranche"], key in union, key)
            if key not in union:
                self.assertEqual(e, evidence_before[key])

    def test_retained_versions_stay_and_support_never_decreases(self) -> None:
        evidence_before = {e["contest_key"]: e for e in payload("before", "evidence.jsonl")}
        evidence_after = {e["contest_key"]: e for e in payload("after", "evidence.jsonl")}
        for key, e in evidence_before.items():
            kept = {v["capture_id"] for v in e["archive"]["versions"]}
            self.assertLessEqual(kept, {v["capture_id"] for v in evidence_after[key]["archive"]["versions"]}, key)
        def states(name: str) -> dict[tuple, str]:
            return {(r["relationship"]["target_contest_key"], r["relationship"]["view"],
                     r["relationship"]["prior_contest_key"]): r["decision"]["support_state"]
                    for r in relationships(name)}
        before, after = states("before"), states("after")
        self.assertEqual(set(before), set(after))
        lost = [k for k in before if before[k] == "SUPPORTED" and after[k] != "SUPPORTED"]
        self.assertEqual(lost, [])
        gained = sorted(k for k in before if before[k] != "SUPPORTED" and after[k] == "SUPPORTED")
        # the cohort-only prior ncaa:1004 gains a coherent version; the overlap key ncaa:1005 stays without capture
        self.assertEqual(gained, [("ncaa:1005", "A", "ncaa:1004"), ("ncaa:1007", "B", "ncaa:1004")])
        self.assertEqual((sum(s == "SUPPORTED" for s in before.values()), sum(s == "SUPPORTED" for s in after.values()),
                          len(after)), (8, 10, 11))
        self.assertEqual(evidence_after["ncaa:1005"]["archive"]["evidence_class"], "ARCHIVE_NO_CAPTURE")

    def test_reverse_input_reproduces_the_expansion_identities(self) -> None:
        base = Path(STATE["tmp"].name) / "rev"
        code, result, err = fx.run_build(STATE["after"], "--input-order", "reverse", "--variant", "REVERSE_INPUT",
                                         out=base / "c" / core.EXPANSION_POPULATION,
                                         manifests=base / "m" / core.EXPANSION_POPULATION)
        self.assertEqual(code, 0, err)
        self.assertEqual((result["content_identity"], result["database_identity"]),
                         (STATE["after_result"]["content_identity"], STATE["after_result"]["database_identity"]))


class RefusalTests(unittest.TestCase):
    def patched(self, name: str, *, contract=None, bindings=None) -> tuple[Path, Path]:
        world = STATE["after"]
        prep = Path(STATE["tmp"].name) / "neg" / name
        bdoc = copy.deepcopy(world["bindings_doc"])
        if bindings:
            bindings(bdoc)
        bpath = fx.write(prep / "INPUT_BINDINGS.json", json.dumps(bdoc, indent=2).encode("utf-8"))
        cdoc = copy.deepcopy(world["contract_doc"])
        cdoc["parent_binding"]["input_bindings"]["sha256"] = fx.sha(bpath.read_bytes())
        if contract:
            contract(cdoc)
        cpath = fx.write(prep / "contract.json", (json.dumps(cdoc, indent=2) + "\n").encode("utf-8"))
        return cpath, bpath

    def refused(self, name: str, **kw) -> str | None:
        cpath, bpath = self.patched(name, **kw)
        out = Path(STATE["tmp"].name) / "neg" / name / "o"
        code, result, err = fx.run_build(STATE["after"], contract=cpath, bindings=bpath, out=out / "c",
                                         manifests=out / "m")
        self.assertEqual(code, 2, err)
        self.assertFalse(out.exists())
        return fx.refusal(err)

    def test_expansion_id_with_the_v10_population_refuses(self) -> None:
        self.assertEqual(self.refused("pop", contract=lambda c: c.update(population_id=core.POPULATION)),
                         "CONTRACT_SCHEMA_UNKNOWN")

    def test_missing_cohort_or_retained_binding_refuses(self) -> None:
        self.assertEqual(self.refused("nocohort", contract=lambda c: c["parent_binding"]["archive"].pop(
            "cohort_sha256")), "CONTRACT_INVALID")
        self.assertEqual(self.refused("noretained", contract=lambda c: c["parent_binding"]["archive"].pop(
            "retained_acquisition_identity")), "CONTRACT_INVALID")

    def test_wrong_cohort_file_refuses(self) -> None:
        tranche = STATE["after"]["bindings_doc"]["archive_tranche"]
        self.assertEqual(self.refused("cohort", bindings=lambda b: b.update(archive_cohort=dict(tranche))),
                         "PARENT_BINDING_MISMATCH")

    def test_the_v12_sidecar_under_the_expansion_contract_refuses(self) -> None:
        v12 = STATE["before"]["bindings_doc"]["archive_database"]
        self.assertEqual(self.refused("v12", bindings=lambda b: b.update(archive_database=dict(v12))),
                         "PARENT_BINDING_MISMATCH")

    def test_wrong_retained_identity_refuses_at_the_archive_parent(self) -> None:
        self.assertEqual(self.refused("retained", contract=lambda c: c["parent_binding"]["archive"].update(
            retained_acquisition_identity="0" * 64)), "PARENT_BINDING_MISMATCH")


class ConsumerTests(unittest.TestCase):
    def query(self, world: str, database: str, *argv: str, parents: dict[str, Path] | None = None):
        w = dict(STATE[world])
        if parents:
            w["paths"] = {**w["paths"], **parents}
        return fx.query(w, fx.database_path(STATE[f"{database}_result"]), *argv)

    def test_each_projection_serves_under_its_own_authority(self) -> None:
        for name in ("before", "after"):
            code, doc, err = self.query(name, name, "--grain", "target", "--cutoff", LATE, "--limit", "1")
            self.assertEqual(code, 0, err)
            self.assertEqual(doc["binding"]["contract_sha256"], STATE[name]["authority"]["contract_sha256"])
            self.assertEqual(doc["total"], STATE[f"{name}_result"]["row_counts"]["targets.jsonl"])

    def test_the_expansion_projection_is_not_served_under_the_v10_authority(self) -> None:
        code, _, err = self.query("before", "after", "--grain", "target", "--cutoff", LATE, "--limit", "1",
                                  parents={"archive": STATE["after"]["paths"]["archive"]})
        self.assertEqual((code, fx.refusal(err)), (2, "PROJECTION_CONTRACT_NOT_ISSUED"))

    def test_the_expansion_projection_refuses_the_v12_sidecar_as_its_archive_parent(self) -> None:
        code, _, err = self.query("after", "after", "--grain", "target", "--cutoff", LATE, "--limit", "1",
                                  parents={"archive": STATE["before"]["paths"]["archive"]})
        self.assertEqual(code, 2, err)
        self.assertIsNotNone(fx.refusal(err))

    def test_require_pit_refuses(self) -> None:
        code, _, err = self.query("after", "after", "--grain", "relationship", "--cutoff", LATE, "--all",
                                  "--require-pit")
        self.assertEqual((code, fx.refusal(err)), (2, "PIT_ADMISSION_NOT_ESTABLISHED"))


class ValidatorTests(unittest.TestCase):
    def test_independent_validator_passes_through_the_bound_expansion_oracle(self) -> None:
        world, result = STATE["after"], STATE["after_result"]
        report = Path(STATE["tmp"].name) / "oracle" / "report.json"
        manifest = Path(result["content"]["manifest"])
        code = fx.validator().main(["--contract", str(world["contract"]), "--input-bindings", str(world["bindings"]),
                                    "--manifest", str(manifest), "--report", str(report),
                                    "--consumer-authority", str(world["authority_spec"]),
                                    "--consumer-source-root", str(fx.ROOT / "src")])
        doc = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, doc["failed_checks"])
        names = {c["check"] for c in doc["checks"] if c["ok"]}
        self.assertIn("archive_expansion_parent_independently_reconstructed_by_the_bound_expansion_oracle", names)
        self.assertEqual(doc["counts"]["archive_keys"], len(STATE["xw"]["union"]))
        applied = [t for t in doc["tamper_cases"] if t["applied"]]
        self.assertGreaterEqual(len(applied), 15)
        self.assertTrue(all(t["rejected_for_intended_cause"] for t in applied))

    def test_validator_refuses_an_unbound_expansion_oracle(self) -> None:
        world, result = STATE["after"], STATE["after_result"]
        doc = copy.deepcopy(world["contract_doc"])
        doc["validator"]["archive_oracle"]["sha256"] = "0" * 64
        contract = fx.write(Path(STATE["tmp"].name) / "badoracle" / "contract.json", json.dumps(doc).encode("utf-8"))
        with self.assertRaises(SystemExit):
            fx.validator().main(["--contract", str(contract), "--input-bindings", str(world["bindings"]),
                                 "--manifest", str(result["content"]["manifest"]),
                                 "--report", str(contract.parent / "report.json"), "--skip-consumer"])


if __name__ == "__main__":
    unittest.main()
