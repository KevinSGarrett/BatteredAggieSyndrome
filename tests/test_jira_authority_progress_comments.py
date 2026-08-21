from __future__ import annotations

import unittest

from jira.tools import import_bat_live


def _ledger_entry(**overrides: object) -> dict[str, object]:
    entry = {
        "jira_key": "BAT-523",
        "local_issue_id": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
        "comment_id": "14584",
        "comment_body_sha256": import_bat_live.comment_body_sha256(
            "Cycle #15 progress (factual): BAT-619 materialized 43233 rows. This issue stays In Progress."
        ),
        "material_merge_sha": "d77c17bc978247b3189cc2069fa3cd6941a95401",
        "local_evidence_identity": "a" * 64,
        "cycle": 15,
        "kind": "parent_progress",
    }
    entry.update(overrides)
    return entry


def _live_comment(comment_id: str, body: str) -> dict[str, object]:
    return {"id": comment_id, "body": body}


class AuthorityProgressCommentLedgerTests(unittest.TestCase):
    def test_matching_live_comment_passes(self) -> None:
        entry = _ledger_entry()
        live = {
            "BAT-523": [
                _live_comment("14584", "Cycle #15 progress (factual): BAT-619 materialized 43233 rows. This issue stays In Progress.")
            ]
        }
        findings = import_bat_live.collect_authority_progress_comment_findings({"comments": [entry]}, live)
        self.assertEqual([], findings)

    def test_missing_live_progress_comment_fails(self) -> None:
        entry = _ledger_entry()
        findings = import_bat_live.collect_authority_progress_comment_findings({"comments": [entry]}, {"BAT-523": []})
        self.assertTrue(any("missing live progress comment BAT-523/14584" in item for item in findings))

    def test_changed_live_progress_comment_fails(self) -> None:
        entry = _ledger_entry()
        live = {
            "BAT-523": [
                _live_comment("14584", "Cycle #15 progress (factual): TAMPERED BODY. This issue stays In Progress.")
            ]
        }
        findings = import_bat_live.collect_authority_progress_comment_findings({"comments": [entry]}, live)
        self.assertTrue(any("changed progress comment BAT-523/14584" in item for item in findings))

    def test_extra_live_progress_comment_fails(self) -> None:
        entry = _ledger_entry()
        live = {
            "BAT-523": [
                _live_comment(
                    "14584",
                    "Cycle #15 progress (factual): BAT-619 materialized 43233 rows. This issue stays In Progress.",
                ),
                _live_comment(
                    "99999",
                    "Cycle #16 progress (factual): extra unbound parent progress.",
                ),
            ]
        }
        findings = import_bat_live.collect_authority_progress_comment_findings({"comments": [entry]}, live)
        self.assertTrue(any("extra live progress comment BAT-523/99999" in item for item in findings))

    def test_unbound_progress_comment_fails(self) -> None:
        entry = _ledger_entry(material_merge_sha="", local_evidence_identity="")
        live = {
            "BAT-523": [
                _live_comment("14584", "Cycle #15 progress (factual): BAT-619 materialized 43233 rows. This issue stays In Progress.")
            ]
        }
        findings = import_bat_live.collect_authority_progress_comment_findings({"comments": [entry]}, live)
        self.assertTrue(any("unbound progress comment BAT-523/14584" in item for item in findings))

    def test_adf_body_canonicalizes_to_markdown_sha(self) -> None:
        text = "Cycle #15 progress (factual): BAT-619 materialized 43233 rows. This issue stays In Progress."
        adf = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }
        self.assertEqual(import_bat_live.comment_body_sha256(text), import_bat_live.comment_body_sha256(adf))


if __name__ == "__main__":
    unittest.main()
