"""Planning conservation and owner edges must survive generic gate mappings."""
from __future__ import annotations

import copy
import ast
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("idea_trace", ROOT / "jira/tools/original_idea_traceability.py")
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class OriginalIdeaTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"local_id": "PRODUCER", "jira_key": "BAT-1", "expected_outputs": ["decision.json"]},
                        {"local_id": "GATE", "jira_key": "BAT-2", "expected_outputs": ["gate.json"]}]
        owner = {"local_id": "PRODUCER", "jira_key": "BAT-1", "role": "evaluate", "scope_basis": "Exact source feasibility", "decision_output": "decision.json"}
        child = {"child_id": "ORI-001-C01", "concept": "Directional rushing", "disposition": "CANDIDATE_TO_EVALUATE",
                 "rationale": "Investigate source availability before empirical use", "planned_decision": "Use/defer/reject from evidence",
                 "checkpoint": "BEFORE_FEATURE_ADOPTION", "owner": "INHERIT_GROUP_PRIMARY_OWNER", "requirement_ids": ["REQ-1"],
                 "decision_location": {"output": "decision.json", "entry_id": "ORI-001-C01"},
                 "implementation_or_scientific_acceptance": "NOT_ASSERTED_BY_THIS_PLAN"}
        self.catalog = {"schema_version": "bas.original-idea-decisions.v1", "counts": {"groups": 1, "children": 1}, "groups": [{
            "idea_id": "ORI-001", "primary_owner": owner, "evaluation_owner": copy.deepcopy(owner), "decision_checkpoint": "before use", "prerequisites": "legal source and source time",
            "source_refs": [{"source_id": "source.txt", "sha256": "a" * 64, "line": 1}], "requirement_ids": ["REQ-1"],
            "expected_child_ids": [child["child_id"]], "expected_child_concept_sha256": {child["child_id"]: hashlib.sha256(child["concept"].encode()).hexdigest()}, "children": [child]}]}
        self.mapping = trace.annotate_requirements([{"requirement_id": "REQ-1", "post_wave_issue_ids": "GATE"},
                                                   {"requirement_id": "REQ-2", "post_wave_issue_ids": "GATE"}], self.catalog)
        self.floor = {"groups": [{"idea_id": "ORI-001", "requirement_ids": ["REQ-1"],
            "source_refs": copy.deepcopy(self.catalog["groups"][0]["source_refs"]),
            "children": [{"child_id": child["child_id"], "concept_sha256": hashlib.sha256(child["concept"].encode()).hexdigest()}]}]}

    def valid(self, catalog, requirements=None):
        return trace.validate_catalog(catalog, self.records, requirements or {"REQ-1", "REQ-2"}, self.floor)

    def test_valid_candidate_and_unreviewed_requirement_are_not_done_claims(self):
        self.assertEqual([], self.valid(self.catalog))
        self.assertEqual([], trace.validate_mapping(self.mapping, self.catalog, self.records, {"REQ-1", "REQ-2"}))
        self.assertEqual(trace.UNREVIEWED, self.mapping[1]["semantic_planning_coverage"])
        self.assertEqual("PLANNED_DECISION_ONLY", trace.decision_rows(self.catalog)[0]["completion_claim"])

    def test_same_generic_gate_cannot_replace_explicit_decision_owner(self):
        # Old native predicate passes this exact counterexample.
        fake = copy.deepcopy(self.mapping)
        for row in fake:
            row["decision_owner_ids"] = "GATE"
            row["original_idea_decision_ids"] = ""
        self.assertTrue(len({r["requirement_id"] for r in fake}) == 2 and all(r["post_wave_issue_ids"] for r in fake))
        errors = trace.validate_mapping(fake, self.catalog, self.records, {"REQ-1", "REQ-2"})
        self.assertTrue(any("decision_owner_ids" in e for e in errors))
        self.assertTrue(any("original_idea_decision_ids" in e for e in errors))

    def test_exact_expected_population_not_only_equal_counts(self):
        for mutation in ("missing", "duplicate", "wrong_id", "wrong_concept", "invalid_disposition", "false_complete", "missing_output"):
            cat = copy.deepcopy(self.catalog); group = cat["groups"][0]; child = group["children"][0]
            if mutation == "missing": group["children"] = []
            if mutation == "duplicate": group["children"].append(copy.deepcopy(child))
            if mutation == "wrong_id": child["child_id"] = "ORI-001-C02"
            if mutation == "wrong_concept": child["concept"] = "Unrelated idea"
            if mutation == "invalid_disposition": child["disposition"] = "DONE"
            if mutation == "false_complete": child["implementation_or_scientific_acceptance"] = "ACCEPTED"
            if mutation == "missing_output": child["decision_location"] = {}
            with self.subTest(mutation=mutation):
                self.assertTrue(self.valid(cat))

    def test_exact_requirement_population_and_existing_owner(self):
        fake = copy.deepcopy(self.mapping); fake[1]["requirement_id"] = "REQ-3"
        self.assertTrue(trace.validate_mapping(fake, self.catalog, self.records, {"REQ-1", "REQ-2"}))
        fake = copy.deepcopy(self.mapping); fake[1]["post_wave_issue_ids"] = "MISSING"
        self.assertTrue(trace.validate_mapping(fake, self.catalog, self.records, {"REQ-1", "REQ-2"}))

    def test_child_owner_override_is_preserved_and_must_own_the_output(self):
        cat = copy.deepcopy(self.catalog); child = cat["groups"][0]["children"][0]
        child["primary_owner_override"] = {"local_id": "GATE", "jira_key": "BAT-2", "role": "specific evaluation", "scope_basis": "Exact bounded evaluation", "decision_output": "gate.json"}
        child["decision_location"]["output"] = "gate.json"
        self.assertEqual([], self.valid(cat))
        self.assertEqual("GATE", trace.decision_rows(cat)[0]["primary_issue_id"])
        child["primary_owner_override"]["jira_key"] = "BAT-999"
        self.assertTrue(self.valid(cat))

    def test_coordinated_catalog_omissions_cannot_rewrite_source_floor(self):
        for mutation in ("child", "group", "concept", "requirements", "source"):
            cat = copy.deepcopy(self.catalog); group = cat["groups"][0]
            if mutation == "child":
                group["children"] = []; group["expected_child_ids"] = []; group["expected_child_concept_sha256"] = {}; cat["counts"]["children"] = 0
            if mutation == "group": cat["groups"] = []; cat["counts"] = {"groups": 0, "children": 0}
            if mutation == "concept":
                group["children"][0]["concept"] = "replacement"
                group["expected_child_concept_sha256"]["ORI-001-C01"] = hashlib.sha256(b"replacement").hexdigest()
            if mutation == "requirements": group["children"][0]["requirement_ids"] = []
            if mutation == "source": group["source_refs"][0]["sha256"] = "b" * 64
            with self.subTest(mutation=mutation):
                self.assertTrue(any("original" in e for e in self.valid(cat)))

    def test_explicit_checkpoint_is_not_replaced_by_group(self):
        self.assertEqual("BEFORE_FEATURE_ADOPTION", trace.decision_rows(self.catalog)[0]["checkpoint"])
        self.catalog["groups"][0]["children"][0]["checkpoint"] = "INHERIT_GROUP_DECISION_CHECKPOINT"
        self.assertEqual("before use", trace.decision_rows(self.catalog)[0]["checkpoint"])

    def test_native_bootstrap_and_future_template_preserve_dependency(self):
        # Inspect and execute only the actual preservation loop, never the
        # destructive historical bootstrap, repository tests or network paths.
        from tempfile import TemporaryDirectory
        source = (ROOT / "jira/tools/build_complete_jira_pack.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_complete_jira_pack")
        loop = next(n for n in fn.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "_name")
        with TemporaryDirectory() as directory:
            jira = Path(directory); (jira / "tools").mkdir()
            (jira / "tools/original_idea_traceability.py").write_text("# owned fixture", encoding="utf-8")
            env = {"jira_root": jira, "preserved_v2_tools": {}}
            exec(compile(ast.Module(body=[loop], type_ignores=[]), "native preservation loop", "exec"), env)
            self.assertEqual("# owned fixture", env["preserved_v2_tools"]["original_idea_traceability.py"])
        hardener = ast.parse((ROOT / "jira/tools/second_pass_hardening.py").read_text(encoding="utf-8"))
        patcher = next(n for n in hardener.body if isinstance(n, ast.FunctionDef) and n.name == "patch_generator_for_reproducibility")
        template = next(n.value.value for n in patcher.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "new" for t in n.targets))
        self.assertIn('"original_idea_traceability.py"', template)

    def test_both_native_packet_writers_preserve_the_governed_consumer_fields(self):
        records = [
            {"local_id": "Z", "historical_classification": "ACTIONABLE_POST_WAVE", "execution_mode": "ATOMIC_EXECUTION", "ready": True},
            {"local_id": "A", "historical_classification": "ACTIONABLE_POST_WAVE", "execution_mode": "AGGREGATE_GATE", "ready": False},
            {"local_id": "B", "historical_classification": "HISTORICAL_REFERENCE", "execution_mode": "HISTORICAL_REFERENCE", "ready": False},
        ]
        for record in records:
            record.update(issue_type="Subtask", workflow_state="READY" if record["ready"] else "BLOCKED",
                          work_packet_path=f"jira/ai/work_packets/{record['local_id']}.md", parent_id="PARENT", governance_traceability_gate="GATE")
        outputs = []
        for filename, function, variable in [("jira_pack_lib.py", "build_indexes", "packets"),
                                              ("second_pass_hardening.py", "regenerate_governance_context", "packet_rows")]:
            tree = ast.parse((ROOT / "jira/tools" / filename).read_text(encoding="utf-8"))
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
            loop = next(n for n in fn.body if isinstance(n, ast.For) and any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name)
                and c.func.value.id == variable and c.func.attr == "append" for c in ast.walk(n)))
            write = next(n for n in fn.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                         and any(isinstance(c, ast.Constant) and c.value == "WORK_PACKET_INDEX.csv" for c in ast.walk(n)))
            captured = []
            # Execute the actual native row-generation and output calls, with
            # only the filesystem sink replaced. Never run destructive bootstrap.
            env = {"records": copy.deepcopy(records), variable: [], "tests": [], "artifacts": [], "JIRA_ROOT": Path("owned"),
                   "write_csv": lambda path, rows: captured.extend(rows), "csv_dump": lambda path, rows: captured.extend(rows)}
            exec(compile(ast.Module(body=[loop, write], type_ignores=[]), filename, "exec"), env)
            outputs.append(captured)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(["Z", "A"], [r["local_id"] for r in outputs[0]])
        self.assertEqual(["local_id", "issue_type", "execution_mode", "workflow_state", "ready", "packet_path",
                          "directly_executable", "aggregate_gate_only", "parent_id", "governance_traceability_gate"], list(outputs[0][0]))
        self.assertEqual("BLOCKED", outputs[0][1]["workflow_state"])
        self.assertTrue(outputs[0][1]["aggregate_gate_only"])
        self.assertFalse(outputs[0][1]["directly_executable"])
        self.assertEqual("PARENT", outputs[0][1]["parent_id"])
        self.assertEqual("GATE", outputs[0][1]["governance_traceability_gate"])

    def test_external_coordination_is_source_bound_and_not_a_bas_owner(self):
        source = {"repository": "GridironCortex/CFBProgramSpecifications", "head": "a" * 40,
                  "relative_path": "50_BAS_INTEGRATION/04_STAFF_PUBLISHER.md", "sha256": "b" * 64}
        binding = trace.dependency_source_binding(source)
        dependency = {"source_refs": [source], "owner_route": [
            {"jira_key": "BAT-708", "role": "BAS bridge decision", "source_bindings": [binding]},
            {"project_key": "CFIP", "dependency_issue_key": "CFIP-8", "role": "Reciprocal coordination", "source_bindings": [binding]}]}
        cat = copy.deepcopy(self.catalog); cat["groups"][0]["cross_project_dependencies"] = dependency
        self.assertEqual([], self.valid(cat))  # The dependency is not a new canonical child owner.
        for mutation in ("mixed", "prefix", "placeholder", "zero", "missing_role", "typed_role", "missing_binding", "unbound", "duplicate", "source_path", "source_head", "source_digest", "typed_project"):
            damaged = copy.deepcopy(cat); block = damaged["groups"][0]["cross_project_dependencies"]; route = block["owner_route"][1]
            if mutation == "mixed": route["jira_key"] = "BAT-708"
            if mutation == "prefix": route["dependency_issue_key"] = "CFI-8"
            if mutation == "placeholder": route["dependency_issue_key"] = "CFIP-XXX"
            if mutation == "zero": route["dependency_issue_key"] = "CFIP-0"
            if mutation == "missing_role": del route["role"]
            if mutation == "typed_role": route["role"] = 12
            if mutation == "missing_binding": del route["source_bindings"]
            if mutation == "unbound": route["source_bindings"] = ["f" * 64]
            if mutation == "duplicate": block["owner_route"].append(copy.deepcopy(route))
            if mutation == "source_path": block["source_refs"][0]["relative_path"] = "different.md"
            if mutation == "source_head": block["source_refs"][0]["head"] = "c" * 40
            if mutation == "source_digest": block["source_refs"][0]["sha256"] = "d" * 64
            if mutation == "typed_project": route["project_key"] = ["CFIP"]
            with self.subTest(mutation=mutation):
                self.assertTrue(any("dependency" in e or "BAS route" in e for e in self.valid(damaged)))


if __name__ == "__main__":
    unittest.main()
