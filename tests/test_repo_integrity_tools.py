import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.repo_integrity import (  # noqa: E402
    iter_repo_files,
    scan_forbidden,
    validate_safe_archive_member,
)
from tools.packaging import (  # noqa: E402
    deterministic_zip_tree,
    safe_extract,
    safe_zip_names,
)


class IntegrityToolTests(unittest.TestCase):
    def test_archive_member_safety(self):
        self.assertTrue(
            validate_safe_archive_member("Aggie_Analytics_Engine/docs/a.md")
        )
        self.assertFalse(validate_safe_archive_member("../escape.txt"))
        self.assertFalse(validate_safe_archive_member("/absolute.txt"))
        self.assertFalse(validate_safe_archive_member("C:/windows.txt"))
        self.assertFalse(validate_safe_archive_member("..\\escape.txt"))

    def test_deterministic_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir()
            (root / "a.txt").write_text("a\n", encoding="utf-8")
            (root / "b.txt").write_text("b\n", encoding="utf-8")
            z1 = Path(td) / "one.zip"
            z2 = Path(td) / "two.zip"
            deterministic_zip_tree(root, z1, root_name="repo")
            deterministic_zip_tree(root, z2, root_name="repo")
            self.assertEqual(z1.read_bytes(), z2.read_bytes())
            self.assertEqual(safe_zip_names(z1), ["repo/a.txt", "repo/b.txt"])
            out = Path(td) / "out"
            safe_extract(z1, out)
            self.assertEqual((out / "repo/a.txt").read_text(), "a\n")

    def test_intrinsic_git_metadata_is_not_repository_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / ".git").mkdir(parents=True)
            (root / ".git" / "config").write_text(
                "checkout metadata\n", encoding="utf-8"
            )
            (root / ".venv").mkdir()
            (root / ".venv" / "secret.txt").write_text(
                "forbidden payload\n", encoding="utf-8"
            )
            (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")

            files = {
                path.relative_to(root).as_posix() for path in iter_repo_files(root)
            }
            findings = scan_forbidden(
                root,
                {
                    "forbidden_directory_names": [".git", ".venv"],
                    "forbidden_exact_files": [],
                    "forbidden_extensions": [],
                    "max_repository_file_bytes": 1024,
                },
            )

            self.assertNotIn(".git/config", files)
            self.assertIn("tracked.txt", files)
            self.assertTrue(any(finding.path == ".venv" for finding in findings))
            self.assertFalse(
                any(finding.path.startswith(".git") for finding in findings)
            )

    def test_real_git_worktree_excludes_ignored_local_secrets_and_caches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text(
                ".env\n__pycache__/\n",
                encoding="utf-8",
            )
            (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", ".gitignore", "tracked.txt"],
                check=True,
            )
            (root / ".env").write_text("API_KEY=local-only\n", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "module.pyc").write_bytes(b"cache")
            (root / "candidate.pt").write_bytes(b"forbidden")

            files = {
                path.relative_to(root).as_posix() for path in iter_repo_files(root)
            }
            findings = scan_forbidden(
                root,
                {
                    "forbidden_directory_names": [".git", "__pycache__"],
                    "forbidden_exact_files": [".env"],
                    "forbidden_extensions": [".pt"],
                    "max_repository_file_bytes": 1024,
                },
            )

            self.assertEqual({".gitignore", "candidate.pt", "tracked.txt"}, files)
            self.assertFalse(any(finding.path == ".env" for finding in findings))
            self.assertFalse(
                any(finding.path.startswith("__pycache__") for finding in findings)
            )
            self.assertTrue(any(finding.path == "candidate.pt" for finding in findings))

    def test_w06_legacy_state_key_compatibility_is_present(self):
        packaging_source = (ROOT / "tools" / "packaging.py").read_text(encoding="utf-8")
        self.assertIn(
            'state_wave = _simple_yaml_scalar_text(state_text, "wave")',
            packaging_source,
        )


if __name__ == "__main__":
    unittest.main()
