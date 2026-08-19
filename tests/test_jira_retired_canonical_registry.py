from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from jira.tools.validate_jira_live_convergence import (
    load_canonical_records,
    load_retired_local_ids,
    validate_retired_canonical_registry,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "jira" / "reconciliation" / "BAT_RETIRED_CANONICAL_ISSUE_REGISTRY.json"
LEDGER_PATH = ROOT / "jira" / "reconciliation" / "BAT_LIVE_IMPORT_LEDGER.json"
LINKS_PATH = ROOT / "jira" / "import" / "JIRA_LINKS.csv"

REQUIRED_RETIRED_IDS = {
    "POST-EPIC-018",
    "POST-STORY-054",
    "POST-STORY-055",
    "POST-STORY-056",
    "POST-STORY-057",
    "POST-STORY-058",
    "POST-SUBTASK-160",
    "POST-SUBTASK-161",
    "POST-SUBTASK-162",
    "POST-SUBTASK-163",
    "POST-SUBTASK-164",
    "POST-SUBTASK-166",
    "POST-SUBTASK-168",
    "POST-SUBTASK-198",
    "POST-SUBTASK-199",
    "POST-SUBTASK-200",
    "POST-SUBTASK-201",
    "POST-SUBTASK-202",
    "POST-SUBTASK-203",
    "POST-SUBTASK-204",
    "POST-SUBTASK-205",
}


class JiraRetiredCanonicalRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        self.records = load_canonical_records(ROOT)
        with LINKS_PATH.open(encoding="utf-8-sig", newline="") as handle:
            self.links = list(csv.DictReader(handle))

    def test_retired_ids_are_registered_and_not_treated_as_missing(self) -> None:
        retired = load_retired_local_ids(self.registry)
        self.assertEqual(REQUIRED_RETIRED_IDS, retired)
        active = {record["local_id"] for record in self.records}
        self.assertFalse(retired & active)
        self.assertEqual(494, len(self.records))

    def test_retired_ids_must_not_remain_in_active_bat_key_map(self) -> None:
        retired = load_retired_local_ids(self.registry)
        self.assertFalse(retired & set(self.ledger.get("issues") or {}))
        self.assertEqual(494, len(self.ledger.get("issues") or {}))

    def test_surviving_issues_cannot_retain_retired_parents_or_expected_links(self) -> None:
        findings = validate_retired_canonical_registry(
            registry=self.registry,
            records=self.records,
            ledger=self.ledger,
            links=self.links,
        )
        self.assertEqual([], findings)

    def test_violation_fixtures_fail_closed(self) -> None:
        retired = next(iter(REQUIRED_RETIRED_IDS))
        records = list(self.records)
        records.append({"local_id": retired, "parent_id": "POST-STORY-027", "dependencies": []})
        leaked = validate_retired_canonical_registry(
            registry=self.registry,
            records=records,
            ledger=self.ledger,
            links=self.links,
        )
        self.assertTrue(any("remain in the active BAT corpus" in item for item in leaked))

        parented = [dict(records[0]), *records[1:]]
        parented[0] = {**parented[0], "parent_id": retired}
        parent_findings = validate_retired_canonical_registry(
            registry=self.registry,
            records=parented,
            ledger=self.ledger,
            links=self.links,
        )
        self.assertTrue(any("retains retired parent" in item for item in parent_findings))

        link_findings = validate_retired_canonical_registry(
            registry=self.registry,
            records=self.records,
            ledger=self.ledger,
            links=[*self.links, {"source_local_id": "POST-SUBTASK-040", "target_local_id": retired}],
        )
        self.assertTrue(any("expected BAT board link still names retired node" in item for item in link_findings))

        mapped = validate_retired_canonical_registry(
            registry=self.registry,
            records=self.records,
            ledger={**self.ledger, "issues": {**self.ledger["issues"], retired: "BAT-512"}},
            links=self.links,
        )
        self.assertTrue(any("remain in the active BAT key map" in item for item in mapped))


if __name__ == "__main__":
    unittest.main()
