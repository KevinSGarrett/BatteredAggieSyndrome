"""Cycle #37 — Attempt #3 — IN_PROGRESS_LOCAL_WORK_REMAINS

W37R-71 / R37A03-06: the versioned Cycle 29 claim-inventory successor and
its explicit-selection validator.

The committed ``CYCLE29_CLAIM_INVENTORY.json`` is a historical receipt: it
stays unchanged and the default validator keeps reporting its 35 omissions.
Only an explicitly selected successor can close the gate, and it must fail
closed on an undeclared artifact, a renamed field, tampered artifact or
successor bytes, a missing claim, an altered original inventory and a
contradicted or unrecomputed claim.

Everything runs on a temporary copy of the committed artifacts; nothing here
reads the data lake, so the suite runs unmounted.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "scientific_integrity" / "cycle29"
SUCCESSOR = ROOT / "artifacts" / "scientific_integrity" / "cycle29_successor" / (
    "CYCLE29_CLAIM_INVENTORY_SUCCESSOR.v1.json")
VALIDATOR = ROOT / "tools" / "validate_cycle29_gates.py"
CENSUS = ROOT / "tools" / "cycle37" / "c29_numeric_census.py"
PRODUCER = ROOT / "tools" / "cycle37" / "c29_claim_successor.py"


def rehash(document: dict[str, Any]) -> dict[str, Any]:
    """Re-sign a deliberately edited successor, isolating the check under test."""

    body = {key: value for key, value in document.items() if key != "body_sha256"}
    document["body_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return document


def recount(document: dict[str, Any]) -> dict[str, Any]:
    counts = {name: 0 for name in ("EVIDENCE_BACKED", "RECONSTRUCTED", "UNSUPPORTED", "CONTRADICTED")}
    for row in document["claims"]:
        counts[row["classification"]] += 1
    document["classification_counts"] = counts
    document["claim_count"] = len(document["claims"])
    return rehash(document)


class Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.art = self.root / "artifacts" / "scientific_integrity" / "cycle29"
        shutil.copytree(ART, self.art)
        for package in ("cycle29", "scientific_reference/cycle29"):
            shutil.copytree(ROOT / "src" / "aggie_analytics" / package,
                            self.root / "src" / "aggie_analytics" / package,
                            ignore=shutil.ignore_patterns("__pycache__"))
        self.successor = self.root / "successor.json"
        shutil.copy2(SUCCESSOR, self.successor)

    def run_validator(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(VALIDATOR), "--repo-root", str(self.root), *extra],
            capture_output=True, text=True, timeout=300,
        )

    def selected(self) -> subprocess.CompletedProcess[str]:
        return self.run_validator("--claim-inventory-successor", str(self.successor))

    def load(self) -> dict[str, Any]:
        return json.loads(self.successor.read_text(encoding="utf-8"))

    def save(self, document: dict[str, Any]) -> None:
        self.successor.write_text(json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False),
                                  encoding="utf-8")

    def edit_artifact(self, name: str, change) -> None:
        path = self.art / name
        document = json.loads(path.read_text(encoding="utf-8"))
        change(document)
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def assertFailsWith(self, result: subprocess.CompletedProcess[str], *fragments: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL claim inventory successor", result.stdout)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout)


class DefaultRoutingIsUnchanged(Workspace):
    def test_the_committed_inventory_alone_still_fails_with_its_35_omissions(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL claim inventory", result.stdout)
        self.assertIn("35 numeric claims absent from the inventory", result.stdout)
        self.assertNotIn("successor", result.stdout)

    def test_the_explicitly_selected_successor_passes(self) -> None:
        result = self.selected()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NOTE claim inventory successor selected explicitly", result.stdout)
        self.assertIn("35 numeric claims absent", result.stdout)
        self.assertTrue(result.stdout.strip().endswith("PASS cycle29 gates"))

    def test_the_committed_original_inventory_is_the_one_the_successor_names(self) -> None:
        document = self.load()
        digest = hashlib.sha256((ART / "CYCLE29_CLAIM_INVENTORY.json").read_bytes()).hexdigest()
        self.assertEqual(document["predecessor_inventory"]["sha256"], digest)
        self.assertTrue(document["predecessor_inventory"]["left_unchanged"])


class TheSuccessorFailsClosed(Workspace):
    def test_an_undeclared_artifact_without_numbers(self) -> None:
        (self.art / "NEW_UNDECLARED_GATE.json").write_text('{"state": "x"}', encoding="utf-8")
        self.assertFailsWith(self.selected(), "neither the manifest nor the successor declares",
                             "NEW_UNDECLARED_GATE.json")

    def test_an_undeclared_artifact_with_a_number(self) -> None:
        (self.art / "NEW_UNDECLARED_GATE.json").write_text('{"hidden_count": 7}', encoding="utf-8")
        self.assertFailsWith(self.selected(), "NEW_UNDECLARED_GATE.json",
                             "numeric values absent from the inventory and its successor")

    def test_a_renamed_field(self) -> None:
        def rename(document: dict[str, Any]) -> None:
            document["mapping_total"] = document.pop("mapping_count")
        self.edit_artifact("BAS_DOMAIN_CATALOG_CROSSWALK.json", rename)
        result = self.selected()
        self.assertFailsWith(result, "no longer holds a number", "mapping_total")

    def test_a_tampered_artifact_value(self) -> None:
        self.edit_artifact("COACHING_COVERAGE_AND_RIGHTS_GATE.json", lambda d: d.__setitem__("W", 183))
        self.assertFailsWith(self.selected(), "bytes differ from the successor's recorded digest",
                             "holds 183")

    def test_an_extra_pointer_under_a_claimed_field(self) -> None:
        def add(document: dict[str, Any]) -> None:
            document["contests"][2]["box_header"]["away_points"] = 7
        self.edit_artifact("CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json", add)
        self.assertFailsWith(self.selected(), "/contests/2/box_header/away_points")

    def test_a_tampered_successor_without_resigning(self) -> None:
        document = self.load()
        document["claims"][0]["pointers"][0]["value"] = 999
        self.save(document)
        self.assertFailsWith(self.selected(), "does not match its body_sha256")

    def test_a_tampered_successor_value_even_when_resigned(self) -> None:
        document = self.load()
        document["claims"][0]["pointers"][0]["value"] = 999
        self.save(rehash(document))
        self.assertFailsWith(self.selected(), "the successor records 999")

    def test_a_missing_claim(self) -> None:
        document = self.load()
        removed = document["claims"].pop()
        self.save(recount(document))
        self.assertFailsWith(self.selected(), "numeric values absent from the inventory and its successor",
                             removed["artifact"])

    def test_a_missing_array_number(self) -> None:
        document = self.load()
        document["array_element_numbers"].pop()
        self.save(rehash(document))
        self.assertFailsWith(self.selected(), "numeric values absent from the inventory and its successor")

    def test_an_altered_original_inventory(self) -> None:
        path = self.art / "CYCLE29_CLAIM_INVENTORY.json"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertFailsWith(self.selected(), "committed claim inventory differs")

    def test_an_altered_manifest(self) -> None:
        path = self.art / "CYCLE29_MATERIALIZATION_MANIFEST.json"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertFailsWith(self.selected(), "materialization manifest differs")

    def test_a_contradicted_claim(self) -> None:
        document = self.load()
        document["claims"][0]["classification"] = "CONTRADICTED"
        self.save(recount(document))
        self.assertFailsWith(self.selected(), "contradicts the recorded value")

    def test_evidence_backed_without_a_matching_recomputation(self) -> None:
        document = self.load()
        target = next(row for row in document["claims"] if row["classification"] == "EVIDENCE_BACKED")
        target["pointers"][0]["matches"] = False
        self.save(rehash(document))
        self.assertFailsWith(self.selected(), "without a matching recomputation")

    def test_an_unknown_classification(self) -> None:
        document = self.load()
        document["claims"][0]["classification"] = "TRUSTED"
        self.save(rehash(document))
        self.assertFailsWith(self.selected(), "is not in the vocabulary")

    def test_an_unsupported_version(self) -> None:
        document = self.load()
        document["successor_version"] = "BAS-C29-CLAIM-INVENTORY-SUCCESSOR-v99"
        self.save(rehash(document))
        self.assertFailsWith(self.selected(), "is not supported")


class TheCommittedSuccessorIsComplete(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(SUCCESSOR.read_text(encoding="utf-8"))

    def test_the_35_validator_omissions_and_3_hidden_pairs_are_claimed(self) -> None:
        discovery = [row["discovery"] for row in self.document["claims"]]
        self.assertEqual(discovery.count("VALIDATOR_OMISSION"), 35)
        self.assertEqual(discovery.count("PAIR_LEVEL_OMISSION_HIDDEN_BY_FIELD_NAME_MATCHING"), 3)
        self.assertEqual(self.document["claim_count"], 38)

    def test_every_census_value_is_accounted_for_exactly_once(self) -> None:
        accounting = self.document["numeric_value_accounting"]
        self.assertEqual(accounting["accounted"], accounting["census_numeric_values"])
        self.assertEqual(sum(accounting["by_disposition"].values()), accounting["census_numeric_values"])
        self.assertNotIn("UNACCOUNTED", accounting["by_disposition"])

    def test_unsupported_claims_are_explicit_and_carry_no_recomputation(self) -> None:
        unsupported = [row for row in self.document["claims"] if row["classification"] == "UNSUPPORTED"]
        self.assertTrue(unsupported)
        for row in unsupported:
            with self.subTest(claim=row["claim_id"]):
                self.assertTrue(all(entry["matches"] is None for entry in row["pointers"]))
                self.assertTrue(row["classification_basis"])

    def test_no_claim_says_it_is_scientific_truth(self) -> None:
        for row in self.document["claims"]:
            self.assertEqual(row["trust"], "INVENTORIED_NOT_SCIENTIFICALLY_ACCEPTED")
        self.assertIn("not evidence that the numbers are scientifically true",
                      " ".join(self.document["not_claimed"]))

    def test_the_label_carries_the_actual_state(self) -> None:
        self.assertTrue(self.document["label"].startswith("Cycle #37 — Attempt #3 — "))
        self.assertNotIn("ACTUAL_STATE", self.document["label"])


class Independence(unittest.TestCase):
    def imports(self, path: Path) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        return names

    def test_the_validator_imports_no_producer_or_census_code(self) -> None:
        names = self.imports(VALIDATOR)
        self.assertFalse(any("c29_claim_successor" in name or "c29_numeric_census" in name for name in names))
        self.assertFalse(any(name.startswith("aggie_analytics.cycle29") for name in names))

    def test_the_census_imports_nothing_from_the_producer_or_the_validator(self) -> None:
        names = self.imports(CENSUS)
        self.assertFalse(any(name.startswith(("aggie_analytics", "tools")) or "validate" in name
                             or "c29_claim_successor" in name for name in names))


class TheCensusItself(unittest.TestCase):
    def load_census_module(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("c29_numeric_census", CENSUS)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_numbers_are_found_at_every_depth_and_booleans_are_not_numbers(self) -> None:
        census = self.load_census_module()
        found = list(census.numeric_values({"a": 1, "b": True, "c": [2, {"d~/e": 3.5}], "f": None}))
        self.assertEqual(found, [("/a", "a", 1), ("/c/0", None, 2), ("/c/1/d~0~1e", "d~/e", 3.5)])

    def test_an_undeclared_file_and_a_renamed_field_are_both_visible(self) -> None:
        census = self.load_census_module()
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "scientific_integrity" / "cycle29"
            shutil.copytree(ART, art)
            (art / "NEW_UNDECLARED_GATE.json").write_text('{"hidden_count": 7}', encoding="utf-8")
            crosswalk = json.loads((art / "BAS_DOMAIN_CATALOG_CROSSWALK.json").read_text(encoding="utf-8"))
            crosswalk["mapping_total"] = crosswalk.pop("mapping_count")
            (art / "BAS_DOMAIN_CATALOG_CROSSWALK.json").write_text(json.dumps(crosswalk), encoding="utf-8")
            body = census.census(art, None)
        records = {row["artifact"]: row for row in body["artifacts"]}
        self.assertFalse(records["NEW_UNDECLARED_GATE.json"]["declared_in_manifest"])
        pairs = {(row["artifact"], row["field"]) for row in body["numeric_field_pairs"]}
        self.assertIn(("NEW_UNDECLARED_GATE.json", "hidden_count"), pairs)
        self.assertIn(("BAS_DOMAIN_CATALOG_CROSSWALK.json", "mapping_total"), pairs)
        self.assertNotIn(("BAS_DOMAIN_CATALOG_CROSSWALK.json", "mapping_count"), pairs)
        self.assertFalse(records["BAS_DOMAIN_CATALOG_CROSSWALK.json"]["manifest_hash_matches"])

    def test_the_census_refuses_to_write_into_the_artifact_directory(self) -> None:
        result = subprocess.run([sys.executable, "-B", str(CENSUS), "--artifact-dir", str(ART), "--no-external",
                                 "--out", str(ART / "x.json")], capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((ART / "x.json").exists())


class TheProducerReadsRawHtmlIndependently(unittest.TestCase):
    def load_producer(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("c29_claim_successor", PRODUCER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_both_header_colours_are_read(self) -> None:
        producer = self.load_producer()
        html = ('<td valign="center" style="font-size:36px; color: grey">\n 13\n </td>'
                '<td valign="center" style="font-size:36px; color: black">\n 41\n </td>')
        self.assertEqual(producer._box_header_scores(html), [13, 41])

    def test_a_scoreboard_score_is_bound_to_its_own_team_row(self) -> None:
        producer = self.load_producer()
        html = ('<a href="/teams/1"> A</a><td><div id="score_9" class="p-1"> 13 </div></td>'
                '<a href="/teams/2"> B</a><td class="totalcol"><div id="score_8" class="p-1"> 41 </div>')
        self.assertEqual(producer._team_scores_from_scoreboard(html, ["1", "2", "3"]),
                         {"1": 13, "2": 41, "3": None})


if __name__ == "__main__":
    unittest.main()
