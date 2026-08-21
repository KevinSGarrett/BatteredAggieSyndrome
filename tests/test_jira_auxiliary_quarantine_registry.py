from __future__ import annotations

import json
import unittest
from pathlib import Path

from jira.tools import import_bat_live


ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_PATH = ROOT / "jira" / "reconciliation" / "BAT_AUXILIARY_QUARANTINE_REGISTRY.json"
RETIRED_PATH = ROOT / "jira" / "reconciliation" / "BAT_RETIRED_CANONICAL_ISSUE_REGISTRY.json"


class AuxiliaryQuarantineRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(QUARANTINE_PATH.read_text(encoding="utf-8"))
        self.retired = json.loads(RETIRED_PATH.read_text(encoding="utf-8"))

    def test_batq_68_and_69_are_quarantined_and_not_retired_canonical(self) -> None:
        keys = {item["current_batq_key"] for item in self.registry["issues"]}
        self.assertEqual({"BATQ-68", "BATQ-69"}, keys)
        retired_keys = {item["current_batq_key"] for item in self.retired["issues"]}
        retired_keys.update(item["former_bat_key"] for item in self.retired["issues"])
        self.assertNotIn("BATQ-68", retired_keys)
        self.assertNotIn("BATQ-69", retired_keys)
        self.assertNotIn("BAT-614", retired_keys)
        self.assertNotIn("BAT-616", retired_keys)
        for item in self.registry["issues"]:
            self.assertTrue(item["never_canonical_owner"])
            self.assertFalse(item["restore_to_bat"])
            self.assertEqual("BATQ", item["current_project"])

    def test_live_batq_membership_is_required(self) -> None:
        live = {
            "BATQ-68": {
                "key": "BATQ-68",
                "fields": {
                    "summary": "DUPLICATE VOID of BAT-613 official 2002 season index",
                    "project": {"key": "BATQ"},
                    "status": {"name": "In Progress"},
                },
            },
            "BATQ-69": {
                "key": "BATQ-69",
                "fields": {
                    "summary": "DUPLICATE VOID of BAT-615 official 2002 box-score acquisition",
                    "project": {"key": "BATQ"},
                    "status": {"name": "In Progress"},
                },
            },
        }
        findings = import_bat_live.collect_auxiliary_quarantine_findings(self.registry, self.retired, live)
        self.assertEqual([], findings)

    def test_restored_to_bat_fails(self) -> None:
        live = {
            "BATQ-68": {
                "key": "BAT-614",
                "fields": {
                    "summary": "DUPLICATE VOID of BAT-613 official 2002 season index",
                    "project": {"key": "BAT"},
                    "status": {"name": "In Progress"},
                },
            }
        }
        findings = import_bat_live.collect_auxiliary_quarantine_findings(self.registry, self.retired, live)
        self.assertTrue(any("BATQ-68 restored off BATQ" in item for item in findings))
        self.assertTrue(any("missing quarantined auxiliary issue BATQ-69" in item for item in findings))

    def test_retired_canonical_leak_fails(self) -> None:
        retired = json.loads(json.dumps(self.retired))
        retired["issues"].append(
            {
                "current_batq_key": "BATQ-68",
                "former_bat_key": "BAT-614",
            }
        )
        live = {
            "BATQ-68": {
                "fields": {
                    "summary": "DUPLICATE VOID of BAT-613 official 2002 season index",
                    "project": {"key": "BATQ"},
                }
            },
            "BATQ-69": {
                "fields": {
                    "summary": "DUPLICATE VOID of BAT-615 official 2002 box-score acquisition",
                    "project": {"key": "BATQ"},
                }
            },
        }
        findings = import_bat_live.collect_auxiliary_quarantine_findings(self.registry, retired, live)
        self.assertTrue(any("retired canonical registry" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
