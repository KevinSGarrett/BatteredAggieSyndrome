"""R34-10 / MR33-16 regression: actual on-disk output-child byte verification.

Isolated temporary roots only -- never touches the real data lake or any
tracked gate file, per the operator hold ("validation must not write to
source lakes or tracked gates"). This exercises `verify_output_children`
directly (the new function `validate_artifact` now calls), which is the
piece MR33-16 found missing: `validate_artifact` compared reconstructed
in-memory hashes to committed JSON but never read the actual output child
files back off disk and hashed those bytes, so deletion or byte-level tamper
of a mounted child was not independently exercised.

This does not attempt the full mounted 1996-2009 reconstruction (that needs
the real external data lake mounted via AGGIE_ANALYTICS_DATA_ROOT, which
tests/test_tamu_official_1996_2009_structured_row_corpus.py already gates
behind `LAKE_READY` and is out of scope for this isolated pass).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.data.tamu_official_1996_2009_structured_row_corpus import (
    AuthorityViolation,
    verify_output_children,
)


def _child_payloads(tmp: Path, rows: dict[str, list[dict]]) -> dict[str, dict]:
    import hashlib

    payloads = {}
    for domain, domain_rows in rows.items():
        filename = f"{domain}.jsonl"
        text = "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in domain_rows
        )
        (tmp / filename).write_text(text, encoding="utf-8", newline="\n")
        payloads[domain] = {
            "filename": filename,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
    return payloads


class OutputChildByteVerificationTests(unittest.TestCase):
    def test_matching_children_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            payloads = _child_payloads(tmp, {"drives": [{"a": 1}, {"a": 2}]})
            result = verify_output_children(out_root=tmp, child_payloads=payloads)
            self.assertEqual(result["result"], "ALL_OUTPUT_CHILDREN_BYTE_VERIFIED")
            self.assertTrue(result["children"]["drives"]["matched"])

    def test_deleted_child_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            payloads = _child_payloads(tmp, {"drives": [{"a": 1}]})
            (tmp / payloads["drives"]["filename"]).unlink()
            with self.assertRaisesRegex(AuthorityViolation, "missing="):
                verify_output_children(out_root=tmp, child_payloads=payloads)

    def test_tampered_child_bytes_are_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            payloads = _child_payloads(tmp, {"drives": [{"a": 1}]})
            path = tmp / payloads["drives"]["filename"]
            path.write_text(
                path.read_text(encoding="utf-8") + '{"a":999}\n',
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaisesRegex(AuthorityViolation, "tampered="):
                verify_output_children(out_root=tmp, child_payloads=payloads)

    def test_undeclared_extra_child_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            payloads = _child_payloads(tmp, {"drives": [{"a": 1}]})
            (tmp / "undeclared_extra.jsonl").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(AuthorityViolation, "undeclared_extra="):
                verify_output_children(out_root=tmp, child_payloads=payloads)

    def test_stale_metadata_hash_mismatch_is_caught(self) -> None:
        """A committed hash that no longer matches regenerated content (e.g.
        after an upstream re-run) must fail, not silently pass as 'metadata
        unchanged'."""

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            payloads = _child_payloads(tmp, {"drives": [{"a": 1}]})
            payloads["drives"]["sha256"] = "0" * 64  # stale/wrong recorded hash
            with self.assertRaisesRegex(AuthorityViolation, "tampered="):
                verify_output_children(out_root=tmp, child_payloads=payloads)


if __name__ == "__main__":
    unittest.main()
