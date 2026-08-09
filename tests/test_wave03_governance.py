from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Wave03GovernanceTests(unittest.TestCase):
    def test_hydration_template_has_no_stale_wave03_open_architecture_text(self) -> None:
        text = (ROOT / "tools/packaging.py").read_text(encoding="utf-8")
        self.assertNotIn("domain/system architecture remains intentionally open for Wave 03", text)

    def test_w03_hydration_manifest_contains_architecture_recovery_artifacts(self) -> None:
        import json
        config = json.loads((ROOT / "configs/hydration_manifest.json").read_text(encoding="utf-8"))
        sources = {item["source"] for item in config["files"]}
        self.assertIn("docs/01_ARCHITECTURE.md", sources)
        self.assertIn("configs/architecture_registry.json", sources)
        self.assertIn("governance/W03_ADAPTIVE_REVIEW.md", sources)
        self.assertIn("governance/W03_VALIDATION_REPORT.md", sources)


if __name__ == "__main__":
    unittest.main()
