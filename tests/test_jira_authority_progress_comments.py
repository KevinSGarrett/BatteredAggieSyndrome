from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

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
        "immutable_evidence_snapshot_path": "artifacts/jira_evidence/immutable/sha256/"
        + ("a" * 64)
        + "/POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001.json",
        "immutable_evidence_snapshot_sha256": "a" * 64,
        "evolving_evidence_path": "artifacts/jira_evidence/POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001.json",
        "evidence_classification": "IMMUTABLE_CYCLE_SNAPSHOT",
        "parent_progress_kind": "parent_progress",
        "local_evidence_identity": "a" * 64,
        "cycle": 15,
        "kind": "parent_progress",
    }
    entry.update(overrides)
    return entry


def _live_comment(comment_id: str, body: str) -> dict[str, object]:
    return {"id": comment_id, "body": body}


class _OwnedRepository:
    """A minimal Git repository of the test's own, under the system temporary root (W37A04-12).

    The static validator reads snapshot files relative to ``repo_root`` and asks Git whether a merge SHA is an
    ancestor of ``HEAD``. The tests used to create their temporary directory inside the checkout, so a lane that
    watched the working tree saw it change; they now pass this repository explicitly as ``repo_root``. Two commits
    give it both ``HEAD`` and ``HEAD~1``. Every Git command runs inside the repository itself, so none starts in the
    caller's working directory (a guarded lane may run these tests from a protected checkout).
    """

    def __enter__(self) -> "_OwnedRepository":
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._git("init", "-q", str(self.root))
        for key, value in (("user.name", "bas-test"), ("user.email", "bas-test@example.invalid")):
            self._git("-C", str(self.root), "config", key, value)
        for number in (1, 2):
            (self.root / "fixture.txt").write_text(f"fixture {number}\n", encoding="utf-8")
            self._git("-C", str(self.root), "add", "fixture.txt")
            self._git("-C", str(self.root), "commit", "-q", "-m", f"fixture {number}")
        return self

    def _git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def sha(self, revision: str) -> str:
        return self._git("-C", str(self.root), "rev-parse", revision).strip()

    def __exit__(self, *exc: object) -> None:
        self._tmp.cleanup()


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

    def test_static_validator_rejects_mutable_snapshot_path(self) -> None:
        with _OwnedRepository() as repo:
            repo_root = repo.root
            head_sha = repo.sha("HEAD")
            tmp_path = repo_root / "evidence"
            tmp_path.mkdir()
            payload = {
                "jira_key": "BAT-523",
                "decision_unit": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
            }
            immutable = tmp_path / "snapshot.json"
            immutable.write_text(json.dumps(payload), encoding="utf-8")
            sha = hashlib.sha256(immutable.read_bytes()).hexdigest()
            entry = _ledger_entry(
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=str(immutable.relative_to(repo_root)).replace("\\", "/"),
                immutable_evidence_snapshot_sha256=sha,
                evolving_evidence_path=str(immutable.relative_to(repo_root)).replace("\\", "/"),
            )
            findings = import_bat_live.validate_authority_progress_comment_ledger_static(
                repo_root,
                {"schema_version": 2, "comments": [entry]},
            )
            self.assertTrue(any("historical entry points at mutable evidence path" in item for item in findings))

    def test_static_validator_rejects_snapshot_sha_drift(self) -> None:
        with _OwnedRepository() as repo:
            repo_root = repo.root
            head_sha = repo.sha("HEAD")
            tmp_path = repo_root / "evidence"
            tmp_path.mkdir()
            payload = {
                "jira_key": "BAT-523",
                "decision_unit": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
            }
            immutable = tmp_path / "snapshot.json"
            immutable.write_text(json.dumps(payload), encoding="utf-8")
            wrong_sha = "f" * 64
            entry = _ledger_entry(
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=str(immutable.relative_to(repo_root)).replace("\\", "/"),
                immutable_evidence_snapshot_sha256=wrong_sha,
                evolving_evidence_path="artifacts/jira_evidence/POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001.json",
            )
            findings = import_bat_live.validate_authority_progress_comment_ledger_static(
                repo_root,
                {"schema_version": 2, "comments": [entry]},
            )
            self.assertTrue(any("immutable snapshot SHA drift" in item for item in findings))

    def test_static_validator_rejects_duplicate_immutable_snapshot(self) -> None:
        with _OwnedRepository() as repo:
            repo_root = repo.root
            head_sha = repo.sha("HEAD")
            tmp_path = repo_root / "evidence"
            tmp_path.mkdir()
            payload = {
                "jira_key": "BAT-523",
                "decision_unit": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
            }
            immutable = tmp_path / "snapshot.json"
            immutable.write_text(json.dumps(payload), encoding="utf-8")
            sha = hashlib.sha256(immutable.read_bytes()).hexdigest()
            rel = str(immutable.relative_to(repo_root)).replace("\\", "/")
            entry_a = _ledger_entry(
                cycle=15,
                comment_id="14584",
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=rel,
                immutable_evidence_snapshot_sha256=sha,
            )
            entry_b = _ledger_entry(
                cycle=16,
                comment_id="14615",
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=rel,
                immutable_evidence_snapshot_sha256=sha,
            )
            findings = import_bat_live.validate_authority_progress_comment_ledger_static(
                repo_root,
                {"schema_version": 2, "comments": [entry_a, entry_b]},
            )
            self.assertTrue(any("duplicate immutable snapshot" in item for item in findings))

    def test_static_validator_allows_evolving_evidence_to_change(self) -> None:
        with _OwnedRepository() as repo:
            repo_root = repo.root
            head_sha = repo.sha("HEAD")
            tmp_path = repo_root / "evidence"
            tmp_path.mkdir()
            snapshot_contents = json.dumps(
                {
                    "jira_key": "BAT-523",
                    "decision_unit": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
                }
            )
            snapshot_sha = hashlib.sha256(snapshot_contents.encode("utf-8")).hexdigest()
            snapshot = tmp_path / snapshot_sha / "snapshot.json"
            snapshot.parent.mkdir()
            snapshot.write_text(snapshot_contents, encoding="utf-8")
            evolving = tmp_path / "evolving.json"
            evolving.write_text(json.dumps({"revision": 1}), encoding="utf-8")
            entry = _ledger_entry(
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=str(snapshot.relative_to(repo_root)).replace("\\", "/"),
                immutable_evidence_snapshot_sha256=snapshot_sha,
                evolving_evidence_path=str(evolving.relative_to(repo_root)).replace("\\", "/"),
            )
            ledger = {
                "schema_version": 2,
                "v2_evidence_authority": {
                    "historical_snapshot": import_bat_live.V2_HISTORICAL_SNAPSHOT_AUTHORITY,
                    "evolving_evidence_path": import_bat_live.V2_EVOLVING_EVIDENCE_AUTHORITY,
                    "legacy_mutable_fields": import_bat_live.V2_LEGACY_MUTABLE_FIELDS_AUTHORITY,
                },
                "comments": [entry],
            }
            self.assertEqual(
                import_bat_live.validate_authority_progress_comment_ledger_static(repo_root, ledger),
                [],
            )
            evolving.write_text(json.dumps({"revision": 2}), encoding="utf-8")
            self.assertEqual(
                import_bat_live.validate_authority_progress_comment_ledger_static(repo_root, ledger),
                [],
            )

    def test_supersession_record_for_historical_comment_passes(self) -> None:
        with _OwnedRepository() as repo:
            repo_root = repo.root
            head_sha, parent_sha = repo.sha("HEAD"), repo.sha("HEAD~1")
            tmp_path = repo_root / "evidence"
            tmp_path.mkdir()
            snapshot_payload = {
                "jira_key": "BAT-523",
                "decision_unit": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
            }
            snapshot_contents = json.dumps(snapshot_payload)
            snapshot_sha = hashlib.sha256(snapshot_contents.encode("utf-8")).hexdigest()
            snapshot = tmp_path / snapshot_sha / "snapshot.json"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text(snapshot_contents, encoding="utf-8")
            entry = _ledger_entry(
                cycle=21,
                comment_id="14706",
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=str(snapshot.relative_to(repo_root)).replace("\\", "/"),
                immutable_evidence_snapshot_sha256=snapshot_sha,
                comment_body_sha256="49d06f0fec3ea5ea04747cf1e597ce7c2a2803b72e107d2a0d25e2c173cbed0d",
            )
            ledger = {
                "schema_version": 2,
                "supersession_schema_version": 1,
                "v2_evidence_authority": {
                    "historical_snapshot": import_bat_live.V2_HISTORICAL_SNAPSHOT_AUTHORITY,
                    "evolving_evidence_path": import_bat_live.V2_EVOLVING_EVIDENCE_AUTHORITY,
                    "legacy_mutable_fields": import_bat_live.V2_LEGACY_MUTABLE_FIELDS_AUTHORITY,
                },
                "comments": [entry],
                "supersessions": [
                    {
                        "jira_key": "BAT-523",
                        "local_issue_id": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
                        "cycle": 21,
                        "original_comment_id": "14706",
                        "original_comment_body_sha256": "49d06f0fec3ea5ea04747cf1e597ce7c2a2803b72e107d2a0d25e2c173cbed0d",
                        "posted_cycle_end_sha": parent_sha.lower(),
                        "final_cycle_end_sha": head_sha.lower(),
                        "correction_reason": "posted before final closeout commit",
                        "historical_comment_immutable": True,
                        "supersession_kind": "HISTORICAL_COMMENT_END_SHA_CORRECTION",
                    }
                ],
            }
            self.assertEqual(
                import_bat_live.validate_authority_progress_comment_ledger_static(repo_root, ledger),
                [],
            )

    def test_supersession_sha_mismatch_fails(self) -> None:
        with _OwnedRepository() as repo:
            repo_root = repo.root
            head_sha, parent_sha = repo.sha("HEAD"), repo.sha("HEAD~1")
            tmp_path = repo_root / "evidence"
            tmp_path.mkdir()
            snapshot_payload = {
                "jira_key": "BAT-523",
                "decision_unit": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
            }
            snapshot_contents = json.dumps(snapshot_payload)
            snapshot_sha = hashlib.sha256(snapshot_contents.encode("utf-8")).hexdigest()
            snapshot = tmp_path / snapshot_sha / "snapshot.json"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text(snapshot_contents, encoding="utf-8")
            entry = _ledger_entry(
                cycle=21,
                comment_id="14706",
                material_merge_sha=head_sha,
                immutable_evidence_snapshot_path=str(snapshot.relative_to(repo_root)).replace("\\", "/"),
                immutable_evidence_snapshot_sha256=snapshot_sha,
                comment_body_sha256="49d06f0fec3ea5ea04747cf1e597ce7c2a2803b72e107d2a0d25e2c173cbed0d",
            )
            ledger = {
                "schema_version": 2,
                "supersession_schema_version": 1,
                "v2_evidence_authority": {
                    "historical_snapshot": import_bat_live.V2_HISTORICAL_SNAPSHOT_AUTHORITY,
                    "evolving_evidence_path": import_bat_live.V2_EVOLVING_EVIDENCE_AUTHORITY,
                    "legacy_mutable_fields": import_bat_live.V2_LEGACY_MUTABLE_FIELDS_AUTHORITY,
                },
                "comments": [entry],
                "supersessions": [
                    {
                        "jira_key": "BAT-523",
                        "local_issue_id": "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001",
                        "cycle": 21,
                        "original_comment_id": "14706",
                        "original_comment_body_sha256": "0" * 64,
                        "posted_cycle_end_sha": parent_sha.lower(),
                        "final_cycle_end_sha": head_sha.lower(),
                        "correction_reason": "posted before final closeout commit",
                        "historical_comment_immutable": True,
                        "supersession_kind": "HISTORICAL_COMMENT_END_SHA_CORRECTION",
                    }
                ],
            }
            findings = import_bat_live.validate_authority_progress_comment_ledger_static(repo_root, ledger)
            self.assertTrue(any("supersession comment SHA mismatch BAT-523/14706" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
