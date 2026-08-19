from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jira.tools.validate_jira_live_convergence import (
    validate_committed_jira_live_convergence,
    validate_count_contracts,
)


def _verification(*, auxiliary: int, canonical: int, total: int, schema: int = 2, result: str = "PASS") -> dict[str, object]:
    return {
        "schema_version": schema,
        "result": result,
        "discrepancies": [],
        "auxiliary_expected_count": auxiliary,
        "auxiliary_actual_count": auxiliary,
        "canonical_expected_count": canonical,
        "canonical_actual_count": canonical,
        "total_expected_issue_count": total,
        "total_actual_issue_count": total,
        "issue_count": total,
        "actual_expected_link_count": 1151,
        "expected_link_count": 1151,
    }


def _profile(*, issues: int, links: int = 1151) -> dict[str, object]:
    return {
        "live_counts": {"issues": issues, "links": links},
        "local_sync": {"state": "LIVE_SYNCHRONIZED"},
    }


class JiraLiveConvergenceContractTests(unittest.TestCase):
    def test_stale_36_auxiliary_registry_31_verification_551_profile_fails(self) -> None:
        findings = validate_count_contracts(
            auxiliary_registry_count=36,
            canonical_record_count=515,
            current_link_count=1191,
            verification=_verification(auxiliary=31, canonical=515, total=546, schema=1),
            profile=_profile(issues=551, links=1191),
        )
        joined = " ".join(findings)
        self.assertTrue(findings)
        self.assertIn("auxiliary registry count 36 != verification auxiliary_expected_count 31", findings)
        self.assertIn("profile issue count 551 != verification total_expected_issue_count 546", joined)
        self.assertIn("schema-v1 verification artifact after schema v2 adoption", joined)
        self.assertIn("PASS artifact retains stale 31-auxiliary semantics", findings)
        self.assertIn("LIVE_SYNCHRONIZED while the committed verification artifact is internally inconsistent", findings)

    def test_matching_counts_pass(self) -> None:
        findings = validate_count_contracts(
            auxiliary_registry_count=37,
            canonical_record_count=494,
            current_link_count=1151,
            verification=_verification(auxiliary=37, canonical=494, total=531),
            profile=_profile(issues=531),
        )
        self.assertEqual([], findings)

    def test_committed_stale_tree_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "jira/reconciliation").mkdir(parents=True)
            (root / "jira/validation").mkdir(parents=True)
            (root / "jira/project").mkdir(parents=True)
            (root / "jira/import").mkdir(parents=True)
            (root / "jira/records/issues").mkdir(parents=True)
            (root / "jira/reconciliation/BAT_AUXILIARY_ISSUE_REGISTRY.json").write_text(
                json.dumps({"schema_version": 1, "issues": [{"jira_key": f"BAT-{n}"} for n in range(36)]}) + "\n",
                encoding="utf-8",
            )
            (root / "jira/validation/BAT_LIVE_IMPORT_VERIFICATION.json").write_text(
                json.dumps(_verification(auxiliary=31, canonical=515, total=546, schema=1), indent=2) + "\n",
                encoding="utf-8",
            )
            (root / "jira/project/JIRA_TARGET_PROFILE.yaml").write_text(
                json.dumps(_profile(issues=551, links=1191), indent=2) + "\n",
                encoding="utf-8",
            )
            (root / "jira/reconciliation/BAT_LIVE_IMPORT_LEDGER.json").write_text(
                json.dumps({"issues": {"CANON-1": "BAT-1"}}, indent=2) + "\n",
                encoding="utf-8",
            )
            (root / "jira/reconciliation/BAT_RETIRED_CANONICAL_ISSUE_REGISTRY.json").write_text(
                json.dumps({"schema_version": 1, "retired_count": 0, "issues": []}, indent=2) + "\n",
                encoding="utf-8",
            )
            (root / "jira/import/JIRA_LINKS.csv").write_text(
                "source_local_id,relationship,target_local_id\n",
                encoding="utf-8",
            )
            findings = validate_committed_jira_live_convergence(root)
        self.assertTrue(any("auxiliary registry count 36" in item for item in findings))
        self.assertTrue(any("profile issue count 551" in item for item in findings))
        self.assertTrue(any("stale 31-auxiliary" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
