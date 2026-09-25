"""An artifact that does not read back intact must not be returned.

The failure this guards against actually happened in this cycle: a written
JSONL whose newline count matched while eleven records were truncated
mid-value. The row count alone could not see it; parsing every line back
from disk can.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.jsonl_io import (  # noqa: E402
    JsonlWriteError,
    read_jsonl_strict,
    verify_jsonl,
    write_jsonl_verified,
)

ROWS = [{"id": index, "text": f"row {index}"} for index in range(5)]


class WriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)

    def tearDown(self) -> None:
        self.holder.cleanup()

    def test_a_clean_write_verifies(self) -> None:
        path = self.root / "rows.jsonl"
        result = write_jsonl_verified(path, ROWS)
        self.assertTrue(result["verified"])
        self.assertEqual(result["parsed_rows"], 5)
        self.assertEqual(read_jsonl_strict(path), ROWS)

    def test_no_partial_file_is_left_behind(self) -> None:
        path = self.root / "rows.jsonl"
        write_jsonl_verified(path, ROWS)
        self.assertFalse((self.root / "rows.jsonl.partial").exists())

    def test_a_truncated_record_is_caught_even_when_the_count_matches(self) -> None:
        """The exact shape of the real failure: lost bytes take their newline."""

        path = self.root / "rows.jsonl"
        write_jsonl_verified(path, ROWS)
        lines = path.read_text(encoding="utf-8").split("\n")
        # Truncate row 2 mid-value and let row 3 start on the same line, which
        # keeps the newline count unchanged.
        lines[2] = lines[2][:20] + lines[3]
        del lines[3]
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        result = verify_jsonl(path, 5)
        self.assertFalse(result["verified"])
        self.assertEqual(result["broken_lines"], 1)

    def test_a_missing_row_is_caught(self) -> None:
        path = self.root / "rows.jsonl"
        write_jsonl_verified(path, ROWS)
        lines = [line for line in path.read_text(encoding="utf-8").split("\n") if line]
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8", newline="\n")
        result = verify_jsonl(path, 5)
        self.assertFalse(result["verified"])
        self.assertEqual(result["parsed_rows"], 4)

    def test_a_raw_line_separator_inside_a_record_is_caught(self) -> None:
        path = self.root / "rows.jsonl"
        write_jsonl_verified(path, ROWS)
        text = path.read_text(encoding="utf-8")
        #   is a line separator to str.splitlines and not to split("\n").
        path.write_text(text.replace("row 1", "row 1"), encoding="utf-8", newline="\n")
        result = verify_jsonl(path, 5)
        self.assertNotEqual(result["separator_disagreement"], 0)
        self.assertFalse(result["verified"])

    def test_a_strict_reader_refuses_a_bad_line_rather_than_skipping_it(self) -> None:
        path = self.root / "rows.jsonl"
        write_jsonl_verified(path, ROWS)
        path.write_text(
            path.read_text(encoding="utf-8") + '{"broken": \n', encoding="utf-8"
        )
        with self.assertRaises(JsonlWriteError):
            read_jsonl_strict(path)

    def test_an_absent_file_reads_as_empty_not_as_an_error(self) -> None:
        self.assertEqual(read_jsonl_strict(self.root / "nothing.jsonl"), [])

    def test_rows_round_trip_with_sorted_keys(self) -> None:
        path = self.root / "rows.jsonl"
        write_jsonl_verified(path, [{"b": 1, "a": 2}])
        line = path.read_text(encoding="utf-8").strip()
        self.assertEqual(line, json.dumps({"a": 2, "b": 1}, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
