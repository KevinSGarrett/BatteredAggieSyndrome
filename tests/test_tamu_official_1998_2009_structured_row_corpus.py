from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_2009_structured_row_corpus import (  # noqa: E402  # pylint: disable=import-error
    GATE_RELATIVE,
    PINNED_BAT637_UNION_IDENTITY,
    PINNED_PREDECESSOR_DATASET_IDENTITY,
    validate_artifact,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
PREDECESSOR_MANIFEST = (
    DATA_ROOT
    / "features/tamu_official_2000_2009_structured_row_corpus/sha256"
    / PINNED_PREDECESSOR_DATASET_IDENTITY
    / "corpus_manifest.json"
)


class Official1998to2009CorpusTests(unittest.TestCase):
    def test_gate_binds_predecessor_and_union(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["predecessor_dataset_identity"], PINNED_PREDECESSOR_DATASET_IDENTITY)
        self.assertEqual(gate["union_identity"], PINNED_BAT637_UNION_IDENTITY)

    @unittest.skipUnless(PREDECESSOR_MANIFEST.is_file(), "external predecessor corpus is not mounted")
    def test_validate_artifact_passes(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(result["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
