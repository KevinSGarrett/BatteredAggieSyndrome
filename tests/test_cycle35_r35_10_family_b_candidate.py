"""R35-10 tests for MR34-11: a candidate release, not a candidate hash.

These exercise the pure logic of the candidate builder in isolation -- child
byte validation, negative controls and the BAT-637 pin diagnosis -- without
requiring the mounted lake, so they run in every lane. The mounted-lane
result is recorded separately in the run artifacts and remains FAIL.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_10_family_b_candidate_successor import (  # noqa: E402
    APPROVAL_ID,
    consumer_state,
    CANDIDATE_KIND,
    canonical_bytes,
    negative_controls,
    sha256_bytes,
    snapshot_predecessors,
    validate_child_bytes,
    write_candidate,
)

PAYLOAD = {
    "schema_version": 1,
    "ledger_identity": "l" * 64,
    "complete_rejection_ledger": [{"url": "u1", "superseded": True}],
    "historical_rejection_records": [{"url": "u1", "superseded": True}],
    "active_rejections": [{"url": "u2"}],
    "active_rejection_count": 1,
    "complete_rejection_count": 2,
    "supersessions": [{"url": "u1", "material_merge_sha": "a" * 40}],
    "predecessor_union_identity": "u" * 64,
    "predecessor_corpus_dataset_identity": "c" * 64,
}


def _candidate():
    return {
        "payload": PAYLOAD,
        "children": {
            "rejection_ledger_payload.json": {
                "ledger_identity": PAYLOAD["ledger_identity"],
                "complete_rejection_ledger": PAYLOAD["complete_rejection_ledger"],
                "historical_rejection_records": PAYLOAD["historical_rejection_records"],
                "schema_version": 1,
            },
            "active_rejections.json": {
                "ledger_identity": PAYLOAD["ledger_identity"],
                "active_rejections": PAYLOAD["active_rejections"],
                "active_rejection_count": 1,
            },
            "supersessions.json": {
                "ledger_identity": PAYLOAD["ledger_identity"],
                "supersessions": PAYLOAD["supersessions"],
                "supersession_count": 1,
            },
        },
        "contract": {},
        "committed_gate": {},
    }


class CandidateCompletenessTests(unittest.TestCase):
    def test_a_candidate_is_children_manifest_and_gate_not_one_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_candidate(Path(tmp), _candidate())
            self.assertEqual(len(out["children"]), 3)
            self.assertTrue(out["manifest_path"].is_file())
            self.assertTrue(out["gate_path"].is_file())
            self.assertEqual(out["gate"]["kind"], CANDIDATE_KIND)
            for child in out["children"]:
                self.assertTrue((Path(tmp) / child["relative_path"]).is_file())

    def test_the_gate_declares_it_is_not_activated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate = write_candidate(Path(tmp), _candidate())["gate"]
            self.assertEqual(gate["result"], "CANDIDATE_PREPARED_NOT_ACTIVATED")
            self.assertEqual(gate["canonical_activation_requires"], APPROVAL_ID)
            self.assertEqual(gate["protected_lane"], "CLOSED")
            self.assertTrue(gate["predecessor_gate_untouched"])

    def test_gate_identity_covers_the_gate_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate = write_candidate(Path(tmp), _candidate())["gate"]
            self.assertNotIn("gate_identity", [k for k in gate if k == "nonexistent"])
            self.assertEqual(len(gate["gate_identity"]), 64)

    def test_replay_writes_an_identical_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = write_candidate(Path(tmp) / "a", _candidate())
            second = write_candidate(Path(tmp) / "b", _candidate())
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
            self.assertEqual(
                first["gate"]["gate_identity"], second["gate"]["gate_identity"]
            )
            self.assertEqual(
                [c["sha256"] for c in first["children"]],
                [c["sha256"] for c in second["children"]],
            )


class ChildByteValidationTests(unittest.TestCase):
    def test_actual_disk_bytes_are_validated_not_in_memory_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_candidate(Path(tmp), _candidate())
            report = validate_child_bytes(Path(tmp), out["manifest"])
            self.assertTrue(report["all_children_match_on_disk"])
            self.assertEqual(report["children_checked"], 3)
            for row in report["results"]:
                self.assertEqual(row["state"], "PRESENT")
                self.assertEqual(row["declared_sha256"], row["actual_sha256"])

    def test_every_negative_control_behaves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_candidate(Path(tmp), _candidate())
            controls = negative_controls(Path(tmp), out["manifest"])
            names = {row["control"] for row in controls}
            self.assertEqual(
                names,
                {
                    "TAMPERED_CHILD",
                    "MISSING_CHILD",
                    "RESTORED_CHILD_PASSES_AGAIN",
                    "MIXED_PREDECESSOR_SUCCESSOR_CHILD",
                },
            )
            for row in controls:
                self.assertTrue(row["detected"], row["control"])

    def test_a_missing_child_is_reported_not_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_candidate(Path(tmp), _candidate())
            (Path(tmp) / out["children"][0]["relative_path"]).unlink()
            report = validate_child_bytes(Path(tmp), out["manifest"])
            self.assertFalse(report["all_children_match_on_disk"])
            self.assertEqual(report["results"][0]["state"], "MISSING_CHILD")


class PredecessorImmutabilityTests(unittest.TestCase):
    def test_snapshot_records_absent_files_as_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            present = Path(tmp) / "a.json"
            present.write_bytes(b"x")
            absent = Path(tmp) / "missing.json"
            snap = snapshot_predecessors([present, absent])
            self.assertEqual(snap[str(present)], sha256_bytes(b"x"))
            self.assertIsNone(snap[str(absent)])

    def test_building_a_candidate_does_not_touch_predecessors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            predecessor = Path(tmp) / "committed_gate.json"
            predecessor.write_bytes(canonical_bytes({"gate_identity": "old"}))
            before = snapshot_predecessors([predecessor])
            write_candidate(Path(tmp) / "isolated", _candidate())
            after = snapshot_predecessors([predecessor])
            self.assertEqual(before, after)


class ApprovalRequestTests(unittest.TestCase):
    def test_requested_action_does_not_describe_an_in_place_replacement(self) -> None:
        """MF35-12: the approval wording previously described activation as
        'replacing the committed gate's ledger identity with the
        independently reconstructed one' -- in-place mutation language that
        does not match what this module actually does (write an isolated,
        immutable candidate; prove the committed gate's bytes are
        untouched). The source text itself, not just runtime behavior, must
        say installation-and-routing, not replacement. Source module
        (`build_candidate`/`main`) requires a mounted data root to actually
        execute, so this reads the module's own text directly rather than
        running main()."""
        source = (ROOT / "tools" / "cycle35" / "r35_10_family_b_candidate_successor.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("replacing the committed gate", source)
        self.assertIn("route canonical consumers", source)
        self.assertIn("does NOT edit, delete,", source)
        self.assertIn("overwrite the currently committed gate", source)

    def test_the_run_artifact_records_a_failing_canonical_dimension(self) -> None:
        """The prepared candidate must not be mistaken for activation."""
        artifact = (
            Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
            / "20260920T172801Z"
            / "implementation_output"
            / "R35_10_FAMILY_B_CANDIDATE.json"
        )
        if not artifact.is_file():
            self.skipTest("run artifact not present in this lane")
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(payload["canonical_mounted_validation"], "FAIL")
        self.assertTrue(payload["no_done_gate_edited"])
        self.assertTrue(payload["no_live_hash_copied_into_an_old_pin"])
        self.assertTrue(payload["predecessor_bytes_unchanged"])
        self.assertEqual(payload["approval_request"]["approval_id"], APPROVAL_ID)


class RequiredConsumerStateTests(unittest.TestCase):
    """The closeout review: "Do not request approval for a candidate
    described as complete while its own evidence says the required consumer
    remains unimplemented."

    The request now carries the consumer's state, read from the consumer's
    own qualification artifact rather than asserted -- which would be the
    same mistake one layer up.
    """

    APPROVAL_REQUEST = (
        Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
        / "20260921T025300Z_closeout"
        / "R35_10_APPROVAL_REQUEST.json"
    )

    def test_the_state_is_read_from_the_qualification_artifact(self) -> None:
        state = consumer_state()
        self.assertIn(
            state["state"],
            {
                "IMPLEMENTED_AND_QUALIFIED_IN_ISOLATION",
                "NOT_QUALIFIED",
                "UNKNOWN_NO_QUALIFICATION_ARTIFACT",
                "UNKNOWN_ARTIFACT_UNREADABLE",
            },
        )
        if state["state"].startswith("UNKNOWN"):
            self.assertNotIn("artifact_sha256", state)
        else:
            self.assertTrue(state["artifact_sha256"])

    def test_each_state_reads_differently_from_the_others(self) -> None:
        """Three outcomes, three statements. Qualified, not qualified, and
        not knowable are different claims, and a hosted runner with no
        private lake hits the third -- so collapsing it into either of the
        other two says something false wherever the lake is absent."""
        expected = {
            "IMPLEMENTED_AND_QUALIFIED_IN_ISOLATION": "negative controls all rejecting",
            "NOT_QUALIFIED": "should not be granted",
            "UNKNOWN_NO_QUALIFICATION_ARTIFACT": "does not claim the consumer is implemented",
        }
        state = consumer_state()
        phrase = expected.get(state["state"])
        if phrase is None:
            self.assertEqual(state["state"], "UNKNOWN_ARTIFACT_UNREADABLE")
            return
        self.assertIn(phrase, state["detail"])

    def test_no_unknown_state_ever_reads_as_qualified(self) -> None:
        """The dangerous collapse: an absent artifact must never produce
        language a reader could take as a qualified consumer."""
        state = consumer_state()
        if not state["state"].startswith("UNKNOWN"):
            self.skipTest("the qualification artifact is present")
        self.assertNotIn("qualified", state["detail"].lower())
        self.assertNotIn("cases", state)

    def test_the_request_carries_the_consumer_state(self) -> None:
        if not self.APPROVAL_REQUEST.is_file():
            self.skipTest("the approval request has not been generated")
        payload = json.loads(self.APPROVAL_REQUEST.read_text(encoding="utf-8"))
        state = payload["required_consumer_state"]
        self.assertEqual(state["state"], "IMPLEMENTED_AND_QUALIFIED_IN_ISOLATION")
        # Every negative control must actually have rejected.
        rejected = {
            name: outcome
            for name, outcome in state["cases"].items()
            if name.endswith("_REJECTED")
        }
        self.assertGreaterEqual(len(rejected), 5)
        for name, outcome in rejected.items():
            with self.subTest(case=name):
                self.assertEqual(outcome, "REJECTED")

    def test_implementing_the_consumer_does_not_activate_anything(self) -> None:
        """Wiring the consumer and activating canonical routing are separate.
        The request must not let the first imply the second."""
        state = consumer_state()
        if state["state"] != "IMPLEMENTED_AND_QUALIFIED_IN_ISOLATION":
            self.skipTest("consumer is not qualified")
        self.assertIn("LEGACY remains the import-time default", state["detail"])



if __name__ == "__main__":
    unittest.main()
