"""R36-15: each adversarial packet mutation must make its own predicate fail.

The list is R36-15's: missing command log, fake exit, stale head, wrong data
root, empty expected population, wrong JSON key, zero-row query,
parser-generated labels, an old release read instead of the delivered
successor, and an unknown converted to a pass.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.packet_guards import (  # noqa: E402
    FAIL,
    OK,
    UNAVAILABLE,
    check_command_receipts,
    check_data_root,
    check_head_binding,
    check_member_digests,
    check_no_parser_generated_labels,
    check_population_not_empty,
    check_query_returns_rows,
    check_selected_release_is_the_successor,
    check_unknown_not_converted,
    check_lane_head_currency,
    evaluate_packet,
    read_required,
)

HEAD = "a" * 40
TREE = "b" * 40
DATA_ROOT = r"C:\BatteredAggieSyndrome.data"


class PacketFixture:
    def __init__(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)
        member = self.root / "evidence.json"
        member.write_text('{"ok": true}', encoding="utf-8")
        self.packet = {
            "source_head": HEAD,
            "source_tree": TREE,
            "data_root": DATA_ROOT,
            "members": [
                {
                    "path": "evidence.json",
                    "sha256": hashlib.sha256(member.read_bytes()).hexdigest(),
                }
            ],
            "lanes": [
                {
                    "lane": "local_strict",
                    "result": "PASS",
                    "command": "python tools/validate_repository.py --strict",
                    "exit_code": 0,
                    "log_path": "logs/local_strict.log",
                },
                {
                    "lane": "canonical_mounted",
                    "result": "FAIL",
                    "reason": "the successor is not activated",
                },
            ],
        }

    def close(self) -> None:
        self.holder.cleanup()


_UNSET = object()


class PacketGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = PacketFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def evaluate(self, packet=None, counts=None, validation=_UNSET):
        return evaluate_packet(
            packet or self.fixture.packet,
            root=self.fixture.root,
            actual_head=HEAD,
            actual_tree=TREE,
            expected_data_root=DATA_ROOT,
            counts=counts or {"program_seasons": 12988, "staff_rows": 16428},
            required_population_keys=("program_seasons", "staff_rows"),
            validation=(
                {"source": {"head": HEAD}} if validation is _UNSET else validation
            ),
        )

    def test_a_packet_with_no_validation_artifact_is_not_clean(self) -> None:
        """Lane currency unknown is UNAVAILABLE, never a quiet pass."""

        self.assertEqual(self.evaluate(validation=None)["overall"], "UNAVAILABLE")

    def test_lanes_from_an_earlier_commit_fail_the_packet(self) -> None:
        self.assertEqual(
            self.evaluate(validation={"source": {"head": "0" * 40}})["overall"],
            "FAIL",
        )

    def test_a_clean_packet_passes(self) -> None:
        self.assertEqual(self.evaluate()["overall"], OK)

    def test_stale_head(self) -> None:
        packet = {**self.fixture.packet, "source_head": "c" * 40}
        result = self.evaluate(packet)
        self.assertEqual(result["overall"], FAIL)
        self.assertEqual(result["findings"][0]["state"], FAIL)

    def test_stale_tree_with_a_current_head(self) -> None:
        packet = {**self.fixture.packet, "source_tree": "d" * 40}
        self.assertEqual(self.evaluate(packet)["overall"], FAIL)

    def test_missing_head_is_unavailable_not_a_pass(self) -> None:
        packet = {**self.fixture.packet}
        packet.pop("source_head")
        result = check_head_binding(packet, HEAD, TREE)
        self.assertEqual(result["state"], UNAVAILABLE)

    def test_wrong_data_root(self) -> None:
        packet = {**self.fixture.packet, "data_root": r"C:\SomewhereElse"}
        self.assertEqual(self.evaluate(packet)["overall"], FAIL)

    def test_missing_member_file(self) -> None:
        (self.fixture.root / "evidence.json").unlink()
        self.assertEqual(self.evaluate()["overall"], FAIL)

    def test_changed_member_bytes(self) -> None:
        (self.fixture.root / "evidence.json").write_text("{}", encoding="utf-8")
        result = check_member_digests(self.fixture.packet, self.fixture.root)
        self.assertEqual(result["state"], FAIL)
        self.assertEqual(result["mismatched_count"], 1)

    def test_empty_member_list_is_not_a_clean_packet(self) -> None:
        packet = {**self.fixture.packet, "members": []}
        self.assertEqual(
            check_member_digests(packet, self.fixture.root)["state"], UNAVAILABLE
        )

    def test_missing_command_log(self) -> None:
        packet = {**self.fixture.packet}
        packet["lanes"] = [
            {**packet["lanes"][0], "log_path": None},
            packet["lanes"][1],
        ]
        result = check_command_receipts(packet)
        self.assertEqual(result["state"], FAIL)

    def test_fake_exit_code(self) -> None:
        packet = {**self.fixture.packet}
        packet["lanes"] = [
            {**packet["lanes"][0], "exit_code": 1},
            packet["lanes"][1],
        ]
        self.assertEqual(check_command_receipts(packet)["state"], FAIL)

    def test_a_pass_with_no_command_at_all(self) -> None:
        packet = {**self.fixture.packet, "lanes": [{"lane": "x", "result": "PASS"}]}
        self.assertEqual(check_command_receipts(packet)["state"], FAIL)

    def test_a_failing_lane_needs_only_a_reason(self) -> None:
        packet = {
            **self.fixture.packet,
            "lanes": [
                {"lane": "canonical_mounted", "result": "FAIL", "reason": "not activated"}
            ],
        }
        self.assertEqual(check_command_receipts(packet)["state"], OK)

    def test_a_failing_lane_with_no_reason_is_unbacked(self) -> None:
        packet = {
            **self.fixture.packet,
            "lanes": [{"lane": "canonical_mounted", "result": "FAIL"}],
        }
        self.assertEqual(check_command_receipts(packet)["state"], FAIL)

    def test_empty_expected_population(self) -> None:
        result = self.evaluate(counts={"program_seasons": 0, "staff_rows": 16428})
        self.assertEqual(result["overall"], FAIL)

    def test_wrong_json_key_is_unavailable_not_zero(self) -> None:
        result = check_population_not_empty(
            {"program_season_keys": 12988}, ("program_seasons",)
        )
        self.assertEqual(result["state"], UNAVAILABLE)
        self.assertEqual(result["missing_keys"], ["program_seasons"])

    def test_read_required_refuses_to_default(self) -> None:
        self.assertEqual(read_required({"a": 1}, "b")["state"], UNAVAILABLE)
        self.assertEqual(read_required({"a": 1}, "a")["value"], 1)

    def test_zero_row_query(self) -> None:
        self.assertEqual(check_query_returns_rows(0, "SELECT 1")["state"], FAIL)
        self.assertEqual(check_query_returns_rows(None, "SELECT 1")["state"], UNAVAILABLE)
        self.assertEqual(check_query_returns_rows(5, "SELECT 1")["state"], OK)

    def test_parser_generated_labels(self) -> None:
        rows = [
            {"producer": "parser-a", "label_source": "parser-a"},
            {"producer": "parser-a", "label_source": "human-review"},
        ]
        result = check_no_parser_generated_labels(rows)
        self.assertEqual(result["state"], FAIL)
        self.assertEqual(result["offender_count"], 1)

    def test_independent_labels_pass(self) -> None:
        rows = [{"producer": "parser-a", "label_source": "human-review"}]
        self.assertEqual(check_no_parser_generated_labels(rows)["state"], OK)

    def test_old_release_selected_instead_of_the_successor(self) -> None:
        result = check_selected_release_is_the_successor(
            "release_r4/db.sqlite",
            "release_c36_r1/db.sqlite",
            ["release_r4/db.sqlite", "release_r3/db.sqlite"],
        )
        self.assertEqual(result["state"], FAIL)

    def test_the_delivered_successor_is_accepted(self) -> None:
        result = check_selected_release_is_the_successor(
            "release_c36_r1/db.sqlite",
            "release_c36_r1/db.sqlite",
            ["release_r4/db.sqlite"],
        )
        self.assertEqual(result["state"], OK)

    def test_unknown_converted_to_pass(self) -> None:
        result = check_unknown_not_converted(
            {"season_unknown_cells": "PASS", "membership_rows": "PASS"}
        )
        self.assertEqual(result["state"], FAIL)

    def test_unknown_left_unknown(self) -> None:
        result = check_unknown_not_converted(
            {"season_unknown_cells": "UNKNOWN", "membership_rows": "PASS"}
        )
        self.assertEqual(result["state"], OK)

    def test_worst_state_wins(self) -> None:
        packet = {**self.fixture.packet, "source_head": "c" * 40}
        result = self.evaluate(packet)
        self.assertEqual(result["overall"], FAIL)
        self.assertTrue(any(f["state"] == OK for f in result["findings"]))



class LaneHeadCurrencyTests(unittest.TestCase):
    """Lanes from an earlier commit must not present as this packet's.

    head_binding proves the packet names the current commit; command_receipts
    proves each lane carries a real command and exit code. Neither asks
    whether those lanes ran at the commit the packet names, so a packet could
    bind head X, carry receipts produced at head Y, and pass everything --
    MR35R-02's defect moved from members onto lanes. It is reached by the
    most ordinary route there is: change one line, re-seal the packet, and
    the old lane results come along.
    """

    def test_matching_heads_pass(self) -> None:
        finding = check_lane_head_currency(
            {"source_head": "abc123"}, {"source": {"head": "abc123"}}
        )
        self.assertEqual(finding["state"], "OK")

    def test_a_stale_lane_head_fails(self) -> None:
        finding = check_lane_head_currency(
            {"source_head": "abc123"}, {"source": {"head": "def456"}}
        )
        self.assertEqual(finding["state"], "FAIL")
        self.assertEqual(finding["lane_head"], "def456")
        self.assertEqual(finding["packet_head"], "abc123")

    def test_a_top_level_head_is_also_read(self) -> None:
        finding = check_lane_head_currency({"source_head": "abc"}, {"head": "abc"})
        self.assertEqual(finding["state"], "OK")

    def test_no_validation_artifact_is_unavailable_not_pass(self) -> None:
        self.assertEqual(
            check_lane_head_currency({"source_head": "abc"}, None)["state"],
            "UNAVAILABLE",
        )

    def test_a_validation_without_a_head_is_unavailable_not_pass(self) -> None:
        self.assertEqual(
            check_lane_head_currency({"source_head": "abc"}, {"lanes": []})["state"],
            "UNAVAILABLE",
        )

    def test_a_packet_without_a_head_is_unavailable_not_pass(self) -> None:
        self.assertEqual(
            check_lane_head_currency({}, {"source": {"head": "abc"}})["state"],
            "UNAVAILABLE",
        )


if __name__ == "__main__":
    unittest.main()
