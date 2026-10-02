"""R35-14 regression tests for MR34-12: the live hosted Windows CI failure.

PR #690's exact head errored on `windows-latest` because
`bool(try_resolve_data_root(None, ROOT))` was used to decide whether a
real-data rebuild was possible. A directory exists at the configured data
root on the hosted runner; the private BAT-523 payloads do not. The
condition read True, the rebuild was demanded, and the run died on a
FileNotFoundError for a manifest that was never going to be there -- an
environment fact reported as an artifact defect.

These tests pin all four states apart, and -- crucially -- pin the direction
the repair must NOT move: when the payloads really are mounted, the rebuild
is still mandatory and a caller that demands it still fails loudly.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.experimentation.walk_forward import (  # noqa: E402
    MANIFEST_RELATIVE,
    PAYLOAD_STATE_CORRUPT,
    PAYLOAD_STATE_EMPTY,
    PAYLOAD_STATE_MANIFEST_MISSING,
    PAYLOAD_STATE_MOUNTED,
    PAYLOAD_STATE_NO_ROOT,
    PAYLOAD_STATE_PARTIAL,
    REQUIRED_PAYLOADS,
    private_data_is_mounted,
    private_payload_state,
    resolve_external_path,
    try_resolve_data_root,
    validate_walk_forward_artifact,
)

ARTIFACT = ROOT / "artifacts" / "pit" / "protected_replay_dry_run.json"


def _with_data_root(path: str | None):
    env = dict(os.environ)
    if path is None:
        env.pop("AGGIE_ANALYTICS_DATA_ROOT", None)
    else:
        env["AGGIE_ANALYTICS_DATA_ROOT"] = path
    return mock.patch.dict(os.environ, env, clear=True)


class PayloadStateTests(unittest.TestCase):
    """Directory presence is not data availability."""

    def test_empty_directory_is_not_mounted_data(self) -> None:
        """The hosted-runner shape, reproduced exactly."""
        with tempfile.TemporaryDirectory() as tmp:
            with _with_data_root(tmp):
                state = private_payload_state(None, ROOT)
        self.assertEqual(state["state"], PAYLOAD_STATE_EMPTY)
        self.assertFalse(state["rebuild_possible"])
        self.assertEqual(sorted(state["missing_payloads"]), sorted(REQUIRED_PAYLOADS))

    def test_a_directory_exists_is_still_reported_by_the_old_helper(self) -> None:
        """`try_resolve_data_root` keeps its narrow meaning; the bug was in
        reading it as an availability answer, not in the helper itself."""
        with tempfile.TemporaryDirectory() as tmp:
            with _with_data_root(tmp):
                self.assertIsNotNone(try_resolve_data_root(None, ROOT))
                self.assertFalse(private_data_is_mounted(None, ROOT))

    def test_non_empty_directory_without_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "unrelated.txt").write_text("x", encoding="utf-8")
            with _with_data_root(tmp):
                state = private_payload_state(None, ROOT)
        self.assertEqual(state["state"], PAYLOAD_STATE_MANIFEST_MISSING)
        self.assertFalse(state["rebuild_possible"])

    def test_corrupt_manifest_is_distinguished_from_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / MANIFEST_RELATIVE
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("{not json", encoding="utf-8")
            with _with_data_root(tmp):
                state = private_payload_state(None, ROOT)
        self.assertEqual(state["state"], PAYLOAD_STATE_CORRUPT)
        self.assertFalse(state["rebuild_possible"])

    def test_partial_payloads_are_not_mounted(self) -> None:
        real_manifest = self._real_manifest()
        if real_manifest is None:
            self.skipTest("no real manifest available to copy from")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / MANIFEST_RELATIVE
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(real_manifest, target)
            payload = json.loads(target.read_text(encoding="utf-8"))["payloads"][0]
            one = resolve_external_path(Path(tmp), str(payload["path"]))
            one.parent.mkdir(parents=True, exist_ok=True)
            one.write_bytes(b"not the real payload")
            with _with_data_root(tmp):
                state = private_payload_state(None, ROOT)
        self.assertEqual(state["state"], PAYLOAD_STATE_PARTIAL)
        self.assertFalse(state["rebuild_possible"])
        self.assertEqual(state["present_payloads"], [payload["name"]])
        self.assertIn(payload["name"], REQUIRED_PAYLOADS)

    @staticmethod
    def _real_manifest() -> Path | None:
        with _with_data_root(None):
            root = try_resolve_data_root(None, ROOT)
        if root is None:
            return None
        candidate = root / MANIFEST_RELATIVE
        return candidate if candidate.is_file() else None


class InvariantPreservationTests(unittest.TestCase):
    """The repair must not erase the mounted requirement."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_demanding_a_rebuild_without_data_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with _with_data_root(tmp):
                with self.assertRaises(ValueError) as caught:
                    validate_walk_forward_artifact(
                        self.payload, ROOT, require_payload_rebuild=True
                    )
        message = str(caught.exception)
        self.assertIn("independent payload reconstruction was required", message)
        # The failure names the exact observed state rather than a generic
        # "missing data root", so a real outage is diagnosable from the log.
        self.assertIn(PAYLOAD_STATE_EMPTY, message)

    def test_absent_data_does_not_error_when_a_rebuild_is_not_demanded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with _with_data_root(tmp):
                validate_walk_forward_artifact(
                    self.payload, ROOT, require_payload_rebuild=False
                )

    def test_mounted_payloads_still_require_the_rebuild_to_agree(self) -> None:
        """On a genuinely mounted host the rebuild runs and must match.

        This does not skip on a mounted host -- that is the whole point. It
        skips only where the payloads provably are not present.
        """
        state = private_payload_state(None, ROOT)
        if not state["rebuild_possible"]:
            self.skipTest("private payloads not mounted; state=" + state["state"])
        self.assertEqual(state["state"], PAYLOAD_STATE_MOUNTED)
        validate_walk_forward_artifact(
            self.payload, ROOT, require_payload_rebuild=True
        )

    def test_no_data_root_at_all_is_its_own_state(self) -> None:
        with _with_data_root(str(ROOT / "does" / "not" / "exist")):
            with mock.patch.object(Path, "is_file", return_value=False):
                state = private_payload_state(None, ROOT)
        self.assertEqual(state["state"], PAYLOAD_STATE_NO_ROOT)
        self.assertIsNone(state["data_root"])


if __name__ == "__main__":
    unittest.main()
