"""Cycle #37 — Attempt #6 — MF37A05-02: committed provenance is proved against the committed tree itself.

Attempt 5's candidate kept main's bytes for the protected review controls but committed the repair branch's
provenance, which named the repair branch's blobs for three of them and a paid workflow absent from the tree. Its
checks read files on disk, where those controls are skip-worktree and absent, so the stale rows could not show.
``tools/cycle37/attempt06_candidate.py verify-tree`` reads only committed Git blobs. On a tiny owned repository whose
provenance comes from the canonical generator:

* a commit whose provenance was generated from its own tree is consistent;
* a committed path changed after generation, a committed path removed, provenance generated from a working view
  whose bytes differ from what was then committed, and a stale row whose file is absent from the working tree (as a
  skip-worktree entry leaves it) are each refused -- the last although the working-tree validator sees only an
  absent file;
* a protected entry that differs from main is refused even when the provenance agrees with it.

Every Git write here is ``init``, ``add`` or ``commit`` inside the test's own temporary directory, which the lanes'
canonical write guard admits inside their declared scratch root.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src"), str(REPO / "tools" / "cycle37")]

import attempt06_candidate as ac  # noqa: E402
from tools import repo_integrity  # noqa: E402

PROTECTED = ".github/CODE_REVIEW_RULES.md"
POLICY = '{"manifest_exclude": ["provenance/PROJECT_FILE_MANIFEST.csv", "provenance/PROJECT_FILE_HASHES.sha256"]}\n'


class CommittedProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.env = {**os.environ, "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "GIT_CEILING_DIRECTORIES": self.tmp.name}
        self.git("init", "-q")
        self.write("configs/repository_policy.json", POLICY)
        self.write("a.txt", "alpha\n")
        self.write("tools/x.py", "print('x')\n")
        self.write(PROTECTED, "main rules\n")
        self.main = self.commit_generated("main")
        self.saved = ac.REPO
        ac.REPO = self.root

    def tearDown(self) -> None:
        ac.REPO = self.saved
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        done = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false", "-C", str(self.root),
                               *args], capture_output=True, text=True, env=self.env, check=True)
        return done.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def generate(self) -> None:
        """The canonical generator over the staged working files. It lists the tree before it writes the manifest
        files, so on a repository that has none yet it runs once more, as the repository's own first generation
        did; afterwards the files always exist."""

        self.git("add", "-A")
        if not (self.root / repo_integrity.MANIFEST_NAME).exists():
            repo_integrity.write_manifest(self.root)
            self.git("add", "-A")
        repo_integrity.write_manifest(self.root)

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def commit_generated(self, message: str) -> str:
        self.generate()
        return self.commit(message)

    def verify(self, revision: str) -> dict:
        return ac.verify_tree(revision, main=self.main)

    def test_provenance_generated_from_its_own_tree_is_consistent(self) -> None:
        proof = self.verify(self.main)
        self.assertTrue(proof["consistent"], proof["problems"])
        self.assertEqual(proof["committed_paths"], 7)
        self.assertEqual(proof["manifest_rows"], 5)
        self.assertEqual(proof["current_tree_rows"], 6)
        self.assertTrue(proof["protected_entries_equal_main"])

    def test_changed_committed_path_is_refused(self) -> None:
        self.write("a.txt", "alpha changed after generation\n")
        proof = self.verify(self.commit("changed"))
        self.assertFalse(proof["consistent"])
        self.assertEqual(proof["manifest_rows_differing_from_blobs"], ["a.txt"])

    def test_absent_committed_path_is_refused(self) -> None:
        (self.root / "tools" / "x.py").unlink()
        proof = self.verify(self.commit("removed"))
        self.assertFalse(proof["consistent"])
        self.assertEqual(proof["manifest_absent_from_tree"], ["tools/x.py"])
        self.assertTrue(any("CURRENT_TREE.txt" in problem for problem in proof["problems"]))

    def test_provenance_from_a_stale_generated_view_is_refused(self) -> None:
        # The generator reads a working view whose bytes differ from what is then committed.
        self.write("a.txt", "alpha as the view held it\n")
        self.generate()
        self.write("a.txt", "alpha as committed\n")
        proof = self.verify(self.commit("stale view"))
        self.assertFalse(proof["consistent"])
        self.assertEqual(proof["manifest_rows_differing_from_blobs"], ["a.txt"])

    def test_stale_row_whose_file_is_absent_from_the_working_tree_is_refused_from_blobs(self) -> None:
        # The committed control blob changes after generation, and its file then leaves the working tree, as a
        # skip-worktree entry leaves it: the working-tree validator sees only an absent file (which a skip-worktree
        # candidate expects), never the stale content; the committed blob shows it.
        self.write(PROTECTED, "branch rules\n")
        head = self.commit("masked")
        (self.root / PROTECTED).unlink()
        disk = {finding.kind for finding in repo_integrity.validate_manifest(self.root) if finding.path == PROTECTED}
        self.assertEqual(disk, {"manifest_missing_file", "manifest_extra"})
        proof = self.verify(head)
        self.assertFalse(proof["consistent"])
        self.assertEqual(proof["manifest_rows_differing_from_blobs"], [PROTECTED])
        self.assertFalse(proof["protected_entries_equal_main"])

    def test_protected_entry_differing_from_main_is_refused_even_when_provenance_agrees(self) -> None:
        self.write(PROTECTED, "branch rules\n")
        proof = self.verify(self.commit_generated("controls changed"))
        self.assertFalse(proof["consistent"])
        self.assertFalse(proof["manifest_rows_differing_from_blobs"])
        self.assertFalse(proof["protected_entries_equal_main"])
        self.assertTrue(any("protected entries differ from main" in problem for problem in proof["problems"]))


if __name__ == "__main__":
    unittest.main()
