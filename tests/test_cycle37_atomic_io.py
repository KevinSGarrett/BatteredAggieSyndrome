"""Cycle #37 - Attempt #2 - ACTUAL_STATE: atomic drop-ins for Path writes (U37-11)."""

from __future__ import annotations

import os
import pathlib
import tempfile
import unittest
from unittest import mock

from aggie_analytics import atomic_io


class AtomicIoTests(unittest.TestCase):
    """Same bytes as the plain call; the old content survives a failed write; nothing else changes."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _leftovers(self) -> list[str]:
        return sorted(p.name for p in self.root.rglob("~*"))

    def test_text_bytes_equal_the_plain_call_for_every_newline_and_encoding(self) -> None:
        text = "line one\nlíne two\r\nline three\rend"
        for encoding in ("utf-8", "utf-16", "latin-1"):
            for newline in (None, "", "\n", "\r\n"):
                plain, atomic = self.root / "plain.txt", self.root / "atomic.txt"
                expected = plain.write_text(text, encoding=encoding, newline=newline)
                returned = atomic_io.write_text(atomic, text, encoding=encoding, newline=newline)
                self.assertEqual(atomic.read_bytes(), plain.read_bytes(), (encoding, newline))
                self.assertEqual(returned, expected)
        self.assertEqual(self._leftovers(), [])

    def test_binary_bytes_and_return_value_equal_the_plain_call(self) -> None:
        payload = bytes(range(256)) * 3
        target = self.root / "payload.bin"
        self.assertEqual(atomic_io.write_bytes(target, payload), len(payload))
        self.assertEqual(target.read_bytes(), payload)

    def test_a_failed_write_keeps_the_old_content_and_leaves_no_temporary(self) -> None:
        target = self.root / "keep.txt"
        target.write_text("original", encoding="utf-8")
        with self.assertRaises(UnicodeEncodeError):
            atomic_io.write_text(target, "new content with ü", encoding="ascii")
        self.assertEqual(target.read_text(encoding="utf-8"), "original")
        self.assertEqual(self._leftovers(), [])

    def test_a_missing_parent_raises_and_is_not_created(self) -> None:
        target = self.root / "absent" / "file.txt"
        with self.assertRaises(FileNotFoundError):
            atomic_io.write_text(target, "x", encoding="utf-8")
        self.assertFalse(target.parent.exists())

    def test_an_object_that_is_not_a_path_uses_its_own_method(self) -> None:
        other = mock.Mock()
        other.write_text.return_value = 7
        self.assertEqual(atomic_io.write_text(other, "x", encoding="utf-8"), 7)
        other.write_text.assert_called_once_with("x", encoding="utf-8")

    def test_a_patched_path_write_is_still_intercepted(self) -> None:
        with mock.patch.object(pathlib.Path, "write_text", side_effect=AssertionError("write_text called")):
            with self.assertRaises(AssertionError):
                atomic_io.write_text(self.root / "guarded.txt", "x", encoding="utf-8")
        self.assertFalse((self.root / "guarded.txt").exists())
        self.assertEqual(self._leftovers(), [])

    def test_open_write_commits_on_success_and_discards_on_error(self) -> None:
        target = self.root / "stream.txt"
        target.write_text("old", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            with atomic_io.open_write(target, "w", encoding="utf-8") as stream:
                stream.write("half")
                raise RuntimeError("stop")
        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        with atomic_io.open_write(target, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("new\n")
        self.assertEqual(target.read_bytes(), b"new\n")
        self.assertEqual(self._leftovers(), [])

    def test_open_write_refuses_appending_and_exclusive_modes(self) -> None:
        for mode in ("a", "x", "r+"):
            with self.assertRaises(ValueError):
                with atomic_io.open_write(self.root / "m.txt", mode):
                    pass

    @unittest.skipUnless(hasattr(os, "symlink"), "no symlink support")
    def test_a_symlink_is_written_through_to_its_target(self) -> None:
        target = self.root / "real.txt"
        target.write_text("old", encoding="utf-8")
        link = self.root / "link.txt"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlinks are not permitted here")
        atomic_io.write_text(link, "new", encoding="utf-8")
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_text(encoding="utf-8"), "new")


if __name__ == "__main__":
    unittest.main()
