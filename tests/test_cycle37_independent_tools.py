"""Cycle #37 - Attempt #2 - ACTUAL_STATE: W37R-69, independent tools stay independent of aggie_analytics.

The atomic-write sweep (U37-11) gave every swept tool ``from aggie_analytics import atomic_io``. For the three-pass
pass-2 verifiers, the independent references and the tools whose evidence states that they import nothing from
aggie_analytics, that import broke the independence they exist to provide. They now carry a self-contained atomic
writer; these tests keep it that way and check the writer behaves like ``aggie_analytics.atomic_io``.
"""

from __future__ import annotations

import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SWEEP = REPO / "tools" / "cycle37" / "r37_s_atomic_write_sweep.py"


def _sweep():
    spec = importlib.util.spec_from_file_location("r37_s_atomic_write_sweep_under_test", SWEEP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _writer():
    namespace: dict = {}
    exec(compile(_sweep().INDEPENDENT_SHIM, "<independent shim>", "exec"), namespace)  # noqa: S102
    return namespace["_bas_atomic"]


class IndependentToolsImportNothingFromThePackage(unittest.TestCase):
    def test_every_independent_tool_imports_nothing_from_aggie_analytics(self) -> None:
        independent = sorted(_sweep().INDEPENDENT)
        self.assertGreaterEqual(len(independent), 14)
        for rel in independent:
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
            imported = [node for node in ast.walk(tree)
                        if (isinstance(node, ast.Import) and any(a.name.split(".")[0] == "aggie_analytics" for a in node.names))
                        or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "aggie_analytics")]
            with self.subTest(tool=rel):
                self.assertEqual(imported, [], f"{rel} imports aggie_analytics")


class SelfContainedAtomicWriter(unittest.TestCase):
    def test_the_bytes_are_the_plain_calls_and_no_temporary_remains(self) -> None:
        writer = _writer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain, atomic = root / "plain.txt", root / "atomic.txt"
            plain.write_text("a\nb\n", encoding="utf-8", newline="\r\n")
            writer.write_text(atomic, "a\nb\n", encoding="utf-8", newline="\r\n")
            self.assertEqual(atomic.read_bytes(), plain.read_bytes())
            writer.write_bytes(atomic, b"\x00\x01")
            self.assertEqual(atomic.read_bytes(), b"\x00\x01")
            with writer.open_write(atomic, "w", encoding="utf-8") as stream:
                stream.write("streamed")
            self.assertEqual(atomic.read_text(encoding="utf-8"), "streamed")
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["atomic.txt", "plain.txt"])

    def test_a_failed_write_leaves_the_previous_bytes(self) -> None:
        writer = _writer()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload.json"
            target.write_bytes(b'{"original": true}')
            with self.assertRaises(RuntimeError):
                with writer.open_write(target, "w", encoding="utf-8") as stream:
                    stream.write('{"partial"')
                    raise RuntimeError("interrupted")
            self.assertEqual(target.read_bytes(), b'{"original": true}')
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["payload.json"])

    def test_a_missing_parent_still_raises_and_creates_nothing(self) -> None:
        writer = _writer()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                writer.write_text(Path(tmp) / "absent" / "x.json", "{}", encoding="utf-8")
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
