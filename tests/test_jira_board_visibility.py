from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import patch

from jira.tools import import_bat_live as live


def auxiliary(key: str, status: str = "In Review") -> dict[str, str]:
    return {"jira_key": key, "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT", "status": status}


class FilterClient:
    def __init__(self, jql: str = "old filter", filter_id: str = "10134") -> None:
        self.jql, self.filter_id = jql, filter_id
        self.gets: list[str] = []
        self.puts: list[tuple[str, dict[str, object]]] = []

    def get(self, path: str) -> dict[str, object]:
        self.gets.append(path)
        if path == "/rest/api/3/filter/10134":
            return {"id": "10134", "name": "BAS", "jql": self.jql}
        if path == "/rest/agile/1.0/board/134/configuration":
            return {"name": "BAS", "filter": {"id": self.filter_id}}
        raise AssertionError(path)

    def put(self, path: str, body: dict[str, object]) -> None:
        self.puts.append((path, deepcopy(body)))


class JiraBoardVisibilityTests(unittest.TestCase):
    def test_actual_configuration_retains_post_wave_and_adopted_auxiliary_any_status(self) -> None:
        registry = {key: auxiliary(key, status) for key, status in
                    (("BAT-702", "In Review"), ("BAT-510", "Done"), ("BAT-523", "In Progress"))}
        original = deepcopy(registry)
        client, ledger = FilterClient(), {}
        expected = "project = BAT AND (labels = post-wave OR key in (BAT-510, BAT-523, BAT-702)) ORDER BY Rank ASC"
        with (patch.object(live, "load_auxiliary_issues", return_value=registry),
              patch.object(live, "paged_values", return_value=[]),
              patch.object(live, "SAVED_FILTERS", ()),
              patch.object(live, "write_json_atomic") as write):
            live.configure_filters(client, ledger, {"Logical Workflow State": "customfield_1", "Critical Path": "customfield_2"})
        self.assertEqual(client.puts[0][0], "/rest/api/3/filter/10134")
        self.assertEqual(client.puts[0][1]["jql"], expected)
        self.assertEqual(ledger["board"]["active_jql"], expected)
        self.assertEqual(registry, original)
        write.assert_called_once()
        # No issue update, transition, comment or other board mutation is made.
        self.assertEqual(len(client.puts), 1)
        self.assertNotIn("status", expected)

    def test_new_authorized_issue_is_included_without_fixed_population_list(self) -> None:
        registry = {"BAT-800": auxiliary("BAT-800")}
        self.assertEqual(live.active_board_jql(registry),
                         "project = BAT AND (labels = post-wave OR key in (BAT-800)) ORDER BY Rank ASC")
        registry["BAT-1000"] = auxiliary("BAT-1000", "Done")
        self.assertIn("BAT-800, BAT-1000", live.active_board_jql(registry))

    def test_unregistered_fixture_foreign_project_and_historical_to_do_are_not_added(self) -> None:
        query = live.active_board_jql({"BAT-702": auxiliary("BAT-702")})
        self.assertNotIn("BAT-709", query)
        self.assertNotIn("BATQ-68", query)
        self.assertNotIn("statusCategory", query)
        self.assertNotIn("To Do", query)
        self.assertTrue(query.startswith("project = BAT AND (labels = post-wave OR key in (BAT-702))"))
        self.assertEqual(live.active_board_jql({}), "project = BAT AND labels = post-wave ORDER BY Rank ASC")

    def test_unadopted_foreign_mismatched_or_injected_identity_refuses_before_requests(self) -> None:
        for key, item in (("BATQ-68", auxiliary("BATQ-68")),
                          ("BAT-702", auxiliary("BAT-703")),
                          ("BAT-702", {"jira_key": "BAT-702", "classification": "FIXTURE"}),
                          ("BAT-1) OR project=BATQ", auxiliary("BAT-1) OR project=BATQ"))):
            with self.subTest(key=key, item=item):
                client = FilterClient()
                with patch.object(live, "load_auxiliary_issues", return_value={key: item}):
                    with self.assertRaisesRegex(RuntimeError, "Invalid authorized auxiliary"):
                        live.configure_filters(client, {}, {})
                self.assertEqual(client.gets, [])
                self.assertEqual(client.puts, [])

    def verify_empty(self, client: FilterClient) -> dict[str, object]:
        # Exercise the real verification entrypoint; only unrelated platform
        # census/authority providers are isolated. No network or file write.
        providers = {"load_completion_policy": {}, "search_issues": [],
                     "load_authority_progress_comment_ledger": {}, "fetch_live_comments_by_key": {},
                     "collect_authority_progress_comment_findings": [], "load_auxiliary_quarantine_registry": {},
                     "load_retired_canonical_registry": {}, "fetch_live_issues_by_key": [],
                     "collect_auxiliary_quarantine_findings": []}
        with ExitStack() as stack:
            for name, value in providers.items():
                stack.enter_context(patch.object(live, name, return_value=value))
            return live.verify_live(client, [], [], [], {}, {}, {}, {}, {}, persist=False)[0]

    def test_native_readback_rejects_visibility_drift(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "board filter does not match"):
            self.verify_empty(FilterClient("project = BAT ORDER BY Rank ASC"))

    def test_native_readback_rejects_different_board_filter(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "board is bound to a different filter"):
            self.verify_empty(FilterClient(live.active_board_jql({}), "99999"))

    def test_native_readback_accepts_exact_policy(self) -> None:
        report = self.verify_empty(FilterClient(live.active_board_jql({})))
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["board"]["expected_jql"], live.active_board_jql({}))


if __name__ == "__main__":
    unittest.main()
