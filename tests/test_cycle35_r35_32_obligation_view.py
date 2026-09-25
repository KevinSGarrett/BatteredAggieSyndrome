"""Cycle #35 continuation (20260921T055921Z), section 6.

"Finish or demonstrably exhaust the remaining local obligations, including
newly discovered ones. Preserve original ledger entries and provide a
deduplicated current execution view."

A deduplicated view is only worth reading if it cannot lose anything, so
most of these tests are about loss rather than about the numbers. The
mapping must raise on an entry it does not recognise, an entry must be able
to name more than one obligation, and every declared entry must appear in
the output with its text unchanged.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_32_obligation_execution_view import (  # noqa: E402
    BLOCKED,
    DECLARED_MAP,
    DECLARED_PREFIX_MAP,
    DECLARED_UNFINISHED,
    DONE,
    LOCAL_WORK,
    NEWLY_DISCOVERED,
    NEWLY_MAP,
    OBLIGATIONS,
    OPEN,
    MappingError,
    build_view,
    map_declared,
)


class MappingSafetyTests(unittest.TestCase):
    """An unrecognised entry must stop the run, not vanish from it."""

    def test_an_unknown_entry_raises(self) -> None:
        with self.assertRaises(MappingError):
            map_declared({"blocker": "something nobody has declared"})

    def test_an_empty_entry_raises(self) -> None:
        with self.assertRaises(MappingError):
            map_declared({})

    def test_a_reworded_entry_raises_rather_than_binding_to_a_neighbour(self) -> None:
        """Near-miss text is the dangerous case: it would silently attach a
        declared obligation to the wrong execution row."""

        original = next(iter(DECLARED_MAP))
        with self.assertRaises(MappingError):
            map_declared({"blocker": original.replace(".", " approximately.")})

    def test_one_entry_may_name_several_obligations(self) -> None:
        """Entry 2 names scheme AND responsibility. They have different
        causes and different fixes, so collapsing them would rebuild the
        conflation R35-29 had to unpick."""

        both = map_declared(
            {
                "blocker": "responsibility_assertion and scheme_assertion have zero "
                "rows; no source explicitly evidenced either this cycle."
            }
        )
        self.assertEqual(
            set(both), {"OBL_SCHEME_INGEST_CROSSWALK", "OBL_RESPONSIBILITY_UNSTATED"}
        )

    def test_every_mapping_target_is_a_declared_obligation(self) -> None:
        targets = {k for keys in DECLARED_MAP.values() for k in keys}
        targets |= {key for _, key in DECLARED_PREFIX_MAP}
        targets |= set(NEWLY_MAP.values())
        self.assertEqual(targets - set(OBLIGATIONS), set())


class PreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.view = build_view()
        cls.declared = json.loads(DECLARED_UNFINISHED.read_text(encoding="utf-8"))
        cls.newly = json.loads(NEWLY_DISCOVERED.read_text(encoding="utf-8"))

    def test_every_declared_entry_survives_with_its_text_unchanged(self) -> None:
        kept = {
            row["text_preserved_verbatim"]
            for row in self.view["source_entries"]
            if row["source"] == "DECLARED_UNFINISHED_ITEMS"
        }
        for item in self.declared["items"]:
            self.assertIn(item["blocker"], kept)

    def test_every_newly_discovered_entry_survives(self) -> None:
        kept = {
            row["text_preserved_verbatim"]
            for row in self.view["source_entries"]
            if row["source"] == "NEWLY_DISCOVERED_OBLIGATIONS"
        }
        for item in self.newly["items"]:
            self.assertIn(item["finding"], kept)

    def test_the_original_numbering_is_preserved(self) -> None:
        declared_rows = [
            row
            for row in self.view["source_entries"]
            if row["source"] == "DECLARED_UNFINISHED_ITEMS"
        ]
        self.assertEqual(
            [row["source_index"] for row in declared_rows],
            list(range(1, len(self.declared["items"]) + 1)),
        )

    def test_the_counts_reconcile(self) -> None:
        conservation = self.view["conservation"]
        self.assertEqual(conservation["declared_entries"], len(self.declared["items"]))
        self.assertEqual(
            conservation["newly_discovered_entries"], len(self.newly["items"])
        )
        self.assertTrue(conservation["every_source_entry_mapped"])
        self.assertEqual(
            conservation["entry_to_obligation_mappings"],
            sum(len(row["obligations"]) for row in self.view["source_entries"]),
        )

    def test_it_does_not_write_to_the_frozen_ledgers(self) -> None:
        before = DECLARED_UNFINISHED.read_bytes(), NEWLY_DISCOVERED.read_bytes()
        build_view()
        self.assertEqual(
            (DECLARED_UNFINISHED.read_bytes(), NEWLY_DISCOVERED.read_bytes()), before
        )


class DeduplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.view = build_view()

    def test_duplicates_are_collapsed_and_named(self) -> None:
        """Both ledger lines about Family B activation are one owner
        decision, and the view must say so rather than count it twice."""

        row = next(
            r
            for r in self.view["execution_view"]
            if r["obligation"] == "OBL_FAMILY_B_ACTIVATION"
        )
        self.assertGreaterEqual(row["source_entry_count"], 2)
        self.assertEqual(row["category"], "OWNER_OR_RELEASE_AUTHORITY_DECISION")
        self.assertEqual(row["state"], BLOCKED)

    def test_deduplication_never_reduces_the_source_entries(self) -> None:
        self.assertEqual(
            self.view["conservation"]["source_entries_total"],
            len(self.view["source_entries"]),
        )
        self.assertLess(
            self.view["conservation"]["distinct_obligations"],
            self.view["conservation"]["entry_to_obligation_mappings"],
        )

    def test_every_obligation_traces_back_to_at_least_one_entry(self) -> None:
        for row in self.view["execution_view"]:
            self.assertGreaterEqual(row["source_entry_count"], 1, row["obligation"])
            self.assertTrue(row["sources"])


class StateDisciplineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.view = build_view()

    def test_only_local_work_can_be_done(self) -> None:
        """An acquisition, an owner decision or a network call is not
        something that gets finished here, so it can never read DONE."""

        for row in self.view["execution_view"]:
            if row["state"] == DONE:
                self.assertEqual(row["category"], LOCAL_WORK, row["obligation"])

    def test_nothing_outside_local_work_is_reported_as_open_local_work(self) -> None:
        for row in self.view["execution_view"]:
            if row["state"] == OPEN:
                self.assertEqual(row["category"], LOCAL_WORK, row["obligation"])

    def test_every_obligation_states_what_would_settle_it(self) -> None:
        for row in self.view["execution_view"]:
            self.assertTrue(row["acceptance_predicate"].strip(), row["obligation"])
            self.assertTrue(row["measured"].strip(), row["obligation"])

    def test_the_repairs_made_this_session_read_done_with_evidence(self) -> None:
        done = {
            row["obligation"] for row in self.view["execution_view"] if row["state"] == DONE
        }
        for key in (
            "OBL_PARSER_RECALL",
            "OBL_ADJUDICATION_DETERMINISM",
            "OBL_FAMILY_B_SUCCESSOR_QUALIFICATION",
            "OBL_DELIVERED_RELEASE_RECONCILIATION",
        ):
            self.assertIn(key, done)

    def test_the_view_claims_no_authority(self) -> None:
        note = self.view["authority_note"]
        for forbidden in ("merge", "activate canonically", "adopt C01", "paid review"):
            self.assertIn(forbidden.split()[0], note)
        self.assertIn("Cycle #36 is not begun", note)


if __name__ == "__main__":
    unittest.main()
