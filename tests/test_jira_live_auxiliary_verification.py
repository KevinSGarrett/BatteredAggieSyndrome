from __future__ import annotations

import unittest

from jira.tools import import_bat_live


FIELD_IDS = {
    "Local Issue ID": "customfield_10193",
    "Logical Workflow State": "customfield_10196",
    "Implementation Maturity": "customfield_10197",
    "Evidence State": "customfield_10198",
    "Owner Historical Wave": "customfield_10199",
    "Phase": "customfield_10195",
    "Critical Path": "customfield_10200",
    "Execution Lane": "customfield_10201",
}


def _auxiliary_item(
    key: str,
    local_id: str,
    *,
    summary: str | None = None,
    status: str = "In Review",
) -> dict[str, object]:
    return {
        "jira_key": key,
        "local_id": local_id,
        "summary": summary or f"Auxiliary {key}",
        "issue_type": "Task",
        "status": status,
        "logical_state": "REVIEW",
        "maturity": "IMPLEMENTED",
        "evidence_state": "PARTIAL",
        "owner_wave": "POST_W25",
        "phase": "PHASE-1",
        "critical_path": True,
        "execution_lane": "DATA_MATERIALIZATION",
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
    }


def _live_issue(key: str, item: dict[str, object] | None = None, **field_overrides: object) -> dict[str, object]:
    source = item or _auxiliary_item(key, f"LOCAL-{key}")
    fields: dict[str, object] = {
        "summary": source["summary"],
        "issuetype": {"name": source["issue_type"]},
        "status": {"name": source["status"]},
        "issuelinks": [],
        FIELD_IDS["Local Issue ID"]: source["local_id"],
        FIELD_IDS["Logical Workflow State"]: {"value": source["logical_state"]},
        FIELD_IDS["Implementation Maturity"]: {"value": source["maturity"]},
        FIELD_IDS["Evidence State"]: {"value": source["evidence_state"]},
        FIELD_IDS["Owner Historical Wave"]: source["owner_wave"],
        FIELD_IDS["Phase"]: {"value": source["phase"]},
        FIELD_IDS["Critical Path"]: {"value": str(source["critical_path"]).lower()},
        FIELD_IDS["Execution Lane"]: {"value": source["execution_lane"]},
    }
    fields.update(field_overrides)
    return {"key": key, "fields": fields}


def _coverage(
    issues: list[dict[str, object]],
    key_map: dict[str, str],
    auxiliary: dict[str, dict[str, object]],
) -> tuple[list[str], dict[str, object]]:
    return import_bat_live.collect_auxiliary_live_coverage(issues, key_map, auxiliary, FIELD_IDS)


class JiraLiveAuxiliaryVerificationTests(unittest.TestCase):
    def test_current_541_local_544_live_situation_fails(self) -> None:
        key_map = {f"CANON-{index:03d}": f"BAT-{index}" for index in range(1, 516)}
        auxiliary = {
            f"BAT-{index}": _auxiliary_item(f"BAT-{index}", f"AUX-{index:03d}")
            for index in range(516, 542)
        }
        issues = [_live_issue(key, _auxiliary_item(key, local_id)) for local_id, key in key_map.items()]
        issues.extend(_live_issue(key, item) for key, item in auxiliary.items())
        extras = {
            "BAT-588": _auxiliary_item(
                "BAT-588",
                "POST-TASK-SRC014-2007-OFFICIAL-INDEX-001",
                summary="Capture the official SRC-014 2007 Texas A&M season index and discover box URLs from that page",
            ),
            "BAT-589": _auxiliary_item(
                "BAT-589",
                "POST-TASK-SRC014-2007-OFFICIAL-ACQUISITION-001",
                summary="Acquire and normalize official SRC-014 2007 Texas A&M box scores from the BAT-588 captured index",
            ),
            "BAT-590": _auxiliary_item(
                "BAT-590",
                "POST-TASK-SRC014-2007-OFFICIAL-UNION-001",
                summary="Expand the immutable SRC-014 gamebook union with independently matched 2007 official games",
            ),
        }
        issues.extend(_live_issue(key, item) for key, item in extras.items())

        findings, coverage = _coverage(issues, key_map, auxiliary)

        self.assertEqual(515, coverage["canonical_expected_count"])
        self.assertEqual(515, coverage["canonical_actual_count"])
        self.assertEqual(26, coverage["auxiliary_expected_count"])
        self.assertEqual(26, coverage["auxiliary_actual_count"])
        self.assertEqual(541, coverage["total_expected_issue_count"])
        self.assertEqual(544, coverage["total_actual_issue_count"])
        self.assertEqual(["BAT-588", "BAT-589", "BAT-590"], coverage["unexpected_issue_keys"])
        self.assertEqual([], coverage["missing_auxiliary_keys"])
        self.assertTrue(any("unknown extra BAT issues" in item for item in findings))
        self.assertTrue(any("live total count 544 != 541" in item for item in findings))

    def test_missing_auxiliary_issue_fails(self) -> None:
        item = _auxiliary_item("BAT-588", "POST-TASK-SRC014-2007-OFFICIAL-INDEX-001")
        findings, coverage = _coverage([], {}, {"BAT-588": item})
        self.assertEqual(["BAT-588"], coverage["missing_auxiliary_keys"])
        self.assertEqual(1, coverage["auxiliary_expected_count"])
        self.assertEqual(0, coverage["auxiliary_actual_count"])
        self.assertTrue(any("missing auxiliary issues" in item for item in findings))

    def test_unknown_extra_bat_issue_fails(self) -> None:
        extra = _live_issue("BAT-999", _auxiliary_item("BAT-999", "UNEXPECTED-001"))
        findings, coverage = _coverage([extra], {}, {})
        self.assertEqual(["BAT-999"], coverage["unexpected_issue_keys"])
        self.assertTrue(any("unknown extra BAT issues" in item for item in findings))

    def test_auxiliary_summary_and_status_drift_fail(self) -> None:
        item = _auxiliary_item("BAT-588", "POST-TASK-SRC014-2007-OFFICIAL-INDEX-001")
        live = _live_issue(
            "BAT-588",
            item,
            summary="Drifted summary",
            **{"status": {"name": "Done"}},
        )
        findings, _coverage_counts = _coverage([live], {}, {"BAT-588": item})
        self.assertTrue(any("auxiliary summary drift" in item for item in findings))
        self.assertTrue(any("auxiliary status drift" in item for item in findings))

    def test_auxiliary_custom_field_drift_fails(self) -> None:
        item = _auxiliary_item("BAT-588", "POST-TASK-SRC014-2007-OFFICIAL-INDEX-001")
        live = _live_issue(
            "BAT-588",
            item,
            **{
                FIELD_IDS["Local Issue ID"]: None,
                FIELD_IDS["Logical Workflow State"]: None,
                FIELD_IDS["Evidence State"]: None,
            },
        )
        findings, _coverage_counts = _coverage([live], {}, {"BAT-588": item})
        self.assertTrue(any("auxiliary Local Issue ID" in item for item in findings))
        self.assertTrue(any("auxiliary Logical Workflow State" in item for item in findings))
        self.assertTrue(any("auxiliary Evidence State" in item for item in findings))

    def test_duplicate_auxiliary_local_ids_fail(self) -> None:
        first = _auxiliary_item("BAT-588", "SHARED-LOCAL-ID")
        second = _auxiliary_item("BAT-589", "SHARED-LOCAL-ID")
        issues = [_live_issue("BAT-588", first), _live_issue("BAT-589", second)]
        findings, _coverage_counts = _coverage(
            issues,
            {},
            {"BAT-588": first, "BAT-589": second},
        )
        self.assertTrue(any("duplicate auxiliary Local Issue IDs" in item for item in findings))
        self.assertTrue(any("duplicate Local Issue ID SHARED-LOCAL-ID" in item for item in findings))

    def test_matching_auxiliary_coverage_passes(self) -> None:
        item = _auxiliary_item("BAT-523", "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001")
        findings, coverage = _coverage([_live_issue("BAT-523", item)], {}, {"BAT-523": item})
        self.assertEqual([], findings)
        self.assertEqual(1, coverage["auxiliary_expected_count"])
        self.assertEqual(1, coverage["auxiliary_actual_count"])
        self.assertEqual(1, coverage["total_expected_issue_count"])
        self.assertEqual(1, coverage["total_actual_issue_count"])
        self.assertEqual([], coverage["unexpected_issue_keys"])
        self.assertEqual([], coverage["missing_auxiliary_keys"])


if __name__ == "__main__":
    unittest.main()
