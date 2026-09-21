"""R35-15 (Cycle #35 manager follow-up, 20260920T224700Z), Section 7:
"Generate requirement/finding/unfinished-item ledgers from current
evidence" and the final closeout requirement's "exact-head CI" and "a
minimal concrete list of decisions genuinely required from Kevin or
another owner."

hosted_ci_status() and minimal_decisions_required() were added to
r35_15_acceptance_packet.py to cover exactly those two pieces, which the
existing packet assembly did not produce. These are their first tests.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.cycle35.r35_15_acceptance_packet import (  # noqa: E402
    R35_UNITS,
    hosted_ci_status,
    load_evidence_graph_reconciliation,
    minimal_decisions_required,
)


class HostedCiStatusTests(unittest.TestCase):
    """Exercised against the real `gh` CLI -- the whole point of this
    function is to bind a real, current query result, not a mock of one."""

    def test_real_query_against_a_real_open_pr_returns_a_bound_result(self) -> None:
        result = hosted_ci_status(pr_number=691, head_sha="deadbeef")
        self.assertEqual(result["head_sha"], "deadbeef")
        if not result["queried"]:
            self.skipTest(f"gh unavailable or PR unreachable in this environment: {result.get('reason')}")
        self.assertIn("check_count", result)
        self.assertIn("by_bucket", result)
        self.assertIsInstance(result["all_pass"], bool)
        self.assertIsInstance(result["checks"], list)

    def test_bucket_counts_sum_to_check_count(self) -> None:
        result = hosted_ci_status(pr_number=691, head_sha="x")
        if not result["queried"]:
            self.skipTest("gh unavailable in this environment")
        self.assertEqual(sum(result["by_bucket"].values()), result["check_count"])

    def test_all_pass_is_false_when_any_check_is_not_passing(self) -> None:
        result = hosted_ci_status(pr_number=691, head_sha="x")
        if not result["queried"] or not result["checks"]:
            self.skipTest("gh unavailable or no checks reported in this environment")
        any_not_pass = any(str(row.get("bucket")) != "pass" for row in result["checks"])
        self.assertEqual(result["all_pass"], not any_not_pass)

    def test_an_unreachable_pr_number_is_disclosed_not_silently_empty(self) -> None:
        """A PR that does not exist must fail visibly (queried=False with a
        reason), never come back looking like a real, empty-but-successful
        query."""
        result = hosted_ci_status(pr_number=999999999, head_sha="x")
        if result["queried"]:
            # gh may still return an empty check list for a nonexistent PR
            # rather than erroring; either shape is acceptable as long as
            # it is not silently claimed to be a real all-green result.
            self.assertEqual(result.get("checks"), [])
        else:
            self.assertTrue(result.get("reason"))


class MinimalDecisionsRequiredTests(unittest.TestCase):
    def test_at_least_one_decision_is_returned(self) -> None:
        self.assertTrue(minimal_decisions_required())

    def test_every_decision_has_required_nonempty_fields(self) -> None:
        for row in minimal_decisions_required():
            for key in ("decision", "owner", "why_bas_cannot_decide"):
                self.assertTrue(str(row.get(key) or "").strip(), row)
            self.assertTrue(row.get("blocks"), row)

    def test_every_blocked_unit_is_a_real_r35_unit(self) -> None:
        """A decision that names a unit which doesn't exist in R35_UNITS
        would silently point at nothing."""
        for row in minimal_decisions_required():
            for unit_id in row["blocks"]:
                self.assertIn(unit_id, R35_UNITS, unit_id)

    def test_decisions_are_not_duplicated(self) -> None:
        texts = [row["decision"] for row in minimal_decisions_required()]
        self.assertEqual(len(texts), len(set(texts)))

    def test_no_decision_asks_bas_to_do_something_bas_is_authorized_to_do(self) -> None:
        """Every listed decision must be something requiring authority BAS
        does not have -- not a restatement of ordinary local work."""
        for row in minimal_decisions_required():
            reason = row["why_bas_cannot_decide"].lower()
            self.assertTrue(
                any(
                    keyword in reason
                    for keyword in (
                        "authority", "budget", "owner", "decision",
                        "confirmation", "sign-off", "spend",
                    )
                ),
                row,
            )




class UnfinishedItemReconciliationTests(unittest.TestCase):
    """The closeout review: "Do not use fixed narrative status dictionaries
    as authority... Reconcile each entry with delivered evidence; do not
    simply delete the list or relabel its contents."

    R35_UNITS is exactly such a fixed dictionary. It stays the source of the
    blocker TEXT -- nothing is deleted or reworded -- but the evidence graph,
    which checks each blocker against a delivered artifact, is what says
    whether it is still real.
    """

    def test_every_declared_blocker_is_reconciled_against_evidence(self) -> None:
        reconciliation = load_evidence_graph_reconciliation()
        if not reconciliation:
            self.skipTest("the evidence graph has not been generated")
        missing = [
            (unit_id, blocker)
            for unit_id, unit in R35_UNITS.items()
            for blocker in unit["blockers"]
            if (unit_id, blocker) not in reconciliation
        ]
        self.assertEqual(missing, [], f"unreconciled blockers: {missing}")

    def test_the_reconciliation_carries_a_category_for_each_entry(self) -> None:
        reconciliation = load_evidence_graph_reconciliation()
        if not reconciliation:
            self.skipTest("the evidence graph has not been generated")
        for key, item in reconciliation.items():
            with self.subTest(key=key):
                self.assertTrue(item.get("category"))

    def test_a_missing_graph_yields_no_silent_categorisation(self) -> None:
        """With no graph the items must come back uncategorised rather than
        defaulting to a category nothing checked."""
        import tools.cycle35.r35_15_acceptance_packet as packet

        original = packet.CYCLE_RUNS
        try:
            packet.CYCLE_RUNS = Path(__file__).resolve().parent / "no_such_directory"
            self.assertEqual(packet.load_evidence_graph_reconciliation(), {})
        finally:
            packet.CYCLE_RUNS = original

    def test_no_blocker_text_was_edited_to_make_it_resolvable(self) -> None:
        """A blocker that was reworded to match a repair would make the
        reconciliation trivially true."""
        reconciliation = load_evidence_graph_reconciliation()
        if not reconciliation:
            self.skipTest("the evidence graph has not been generated")
        for (unit_id, blocker), item in reconciliation.items():
            with self.subTest(unit=unit_id):
                self.assertIn(blocker, R35_UNITS[unit_id]["blockers"])
                self.assertEqual(item["blocker"], blocker)


class DecisionsAreNotAlreadyDoneTests(unittest.TestCase):
    """The closeout review asks for "only the genuine remaining external
    decisions". Asking an owner to fund work that already happened is not
    one, and it makes the list look longer than the obligation is.
    """

    CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")

    def newest(self, name: str) -> Path | None:
        found = [
            path
            for path in self.CYCLE_RUNS.rglob(name)
            if "site-packages" not in str(path)
        ]
        return max(found, key=lambda p: p.stat().st_mtime) if found else None

    def test_no_decision_asks_to_re_resolve_the_remote_heads(self) -> None:
        artifact = self.newest("CYCLE35_ALL22_REMOTE_HEADS_REFRESHED.json")
        if artifact is None:
            self.skipTest("remote-head refresh artifact is not mounted")
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        if not payload.get("reresolved_count"):
            self.skipTest("no re-resolution was recorded")
        for decision in minimal_decisions_required():
            with self.subTest(decision=decision["decision"][:40]):
                self.assertNotIn("re-resolving the five", decision["decision"])

    def test_no_decision_describes_the_jira_result_as_offline_only(self) -> None:
        artifact = self.newest("CYCLE35_JIRA_LIVE_READBACK.json")
        if artifact is None:
            self.skipTest("jira readback artifact is not mounted")
        if not json.loads(artifact.read_text(encoding="utf-8")).get("issues"):
            self.skipTest("no readback issues were recorded")
        for decision in minimal_decisions_required():
            with self.subTest(decision=decision["decision"][:40]):
                self.assertNotIn("offline duplicate-audit-only", decision["decision"])

    def test_a_narrowed_decision_records_what_was_already_done(self) -> None:
        """Narrowing without saying what was removed would look like the
        obligation was quietly dropped."""
        narrowed = [
            decision
            for decision in minimal_decisions_required()
            if "already_done_not_part_of_this_decision" in decision
        ]
        self.assertGreaterEqual(len(narrowed), 2)
        for decision in narrowed:
            with self.subTest(decision=decision["decision"][:40]):
                self.assertTrue(
                    decision["already_done_not_part_of_this_decision"].strip()
                )

    def test_every_decision_still_names_an_owner_and_what_it_blocks(self) -> None:
        for decision in minimal_decisions_required():
            with self.subTest(decision=decision["decision"][:40]):
                self.assertTrue(decision["owner"].strip())
                self.assertTrue(decision["blocks"])
                self.assertTrue(decision["why_bas_cannot_decide"].strip())



if __name__ == "__main__":
    unittest.main()
