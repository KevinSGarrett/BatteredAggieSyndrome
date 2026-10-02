"""Adversarial predicates for a completion packet.

R36-02/15. A packet whose member digests all verify can still be false: it
can be sealed at an earlier head, point at the wrong data root, count an
empty population as complete, read a key that does not exist, or carry a
"PASS" that no command produced. Each of those is a separate predicate here,
and each has a mutation in the regression suite that must make it fail.

The rule every predicate obeys: a missing input is an explicit unavailable
state, never a default zero and never a pass.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PACKET_GUARD_VERSION = "BAS-PACKET-GUARD-v36.1"

OK = "OK"
FAIL = "FAIL"
UNAVAILABLE = "UNAVAILABLE"

#: Lane results that are NOT a pass. Kept as data so no consumer can quietly
#: treat one of them as success.
NON_PASSING_STATES = frozenset({"FAIL", "ERROR", "NOT_RUN", "BLOCKED", "SKIPPED", "STALE"})


def _finding(check: str, state: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {
        "guard_version": PACKET_GUARD_VERSION,
        "check": check,
        "state": state,
        "detail": detail,
        **extra,
    }


def check_head_binding(
    packet: Mapping[str, Any], actual_head: str, actual_tree: str
) -> dict[str, Any]:
    """A packet sealed at an earlier commit must not present as current.

    MR35R-02: every member digest matched while the packet's head was two
    commits behind the reviewed source. Digest completeness is not head
    currency, so both are checked and the head is checked first.
    """

    declared_head = packet.get("source_head")
    declared_tree = packet.get("source_tree")
    if not declared_head or not declared_tree:
        return _finding(
            "head_binding",
            UNAVAILABLE,
            "the packet declares no source head or tree, so its currency "
            "cannot be established",
            declared_head=declared_head,
            declared_tree=declared_tree,
        )
    if declared_head != actual_head:
        return _finding(
            "head_binding",
            FAIL,
            "the packet is sealed at a different commit than the source it "
            "claims to describe",
            declared_head=declared_head,
            actual_head=actual_head,
        )
    if declared_tree != actual_tree:
        return _finding(
            "head_binding",
            FAIL,
            "the packet's tree digest does not match the working tree it "
            "claims to describe",
            declared_tree=declared_tree,
            actual_tree=actual_tree,
        )
    return _finding(
        "head_binding", OK, "the packet is bound to the exact source head and tree"
    )


def check_member_digests(
    packet: Mapping[str, Any], root: Path
) -> dict[str, Any]:
    """Every declared member must exist and hash to its declared digest."""

    members = packet.get("members") or []
    if not members:
        return _finding(
            "member_digests",
            UNAVAILABLE,
            "the packet declares no members, so there is nothing to verify; "
            "an empty member list is not a clean packet",
        )
    missing: list[str] = []
    mismatched: list[dict[str, str]] = []
    for member in members:
        relative = str(member.get("path") or "")
        declared = str(member.get("sha256") or "")
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != declared:
            mismatched.append(
                {"path": relative, "declared": declared, "actual": actual}
            )
    if missing or mismatched:
        return _finding(
            "member_digests",
            FAIL,
            "declared members are missing or do not match their digests",
            missing=missing[:20],
            missing_count=len(missing),
            mismatched=mismatched[:20],
            mismatched_count=len(mismatched),
        )
    return _finding(
        "member_digests",
        OK,
        f"all {len(members)} declared members exist and match their digests",
        members=len(members),
    )


def check_data_root(packet: Mapping[str, Any], expected_root: str) -> dict[str, Any]:
    """A packet produced against a different data root is not this packet."""

    declared = packet.get("data_root")
    if not declared:
        return _finding(
            "data_root",
            UNAVAILABLE,
            "the packet does not declare the data root it was produced against",
        )
    if str(declared).rstrip("\\/").casefold() != expected_root.rstrip("\\/").casefold():
        return _finding(
            "data_root",
            FAIL,
            "the packet was produced against a different data root",
            declared=declared,
            expected=expected_root,
        )
    return _finding("data_root", OK, "the packet declares the expected data root")


def check_command_receipts(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Every claimed lane result must be backed by a real command receipt.

    A lane that reports PASS with no command, no exit code or no output is a
    claim, not a result. A fabricated exit code with no command line is the
    same thing with more punctuation.
    """

    lanes = packet.get("lanes") or []
    if not lanes:
        return _finding(
            "command_receipts",
            UNAVAILABLE,
            "the packet declares no validation lanes",
        )
    unbacked: list[dict[str, Any]] = []
    for lane in lanes:
        name = str(lane.get("lane") or "UNNAMED")
        result = str(lane.get("result") or "").upper()
        command = lane.get("command")
        exit_code = lane.get("exit_code")
        log = lane.get("log_path") or lane.get("output_tail")
        if result in NON_PASSING_STATES:
            # A non-passing lane needs a reason, not a receipt.
            if not lane.get("reason") and not command:
                unbacked.append(
                    {"lane": name, "result": result, "why": "no reason and no command"}
                )
            continue
        if not command or exit_code is None or not log:
            unbacked.append(
                {
                    "lane": name,
                    "result": result,
                    "why": "a passing lane needs a command, an exit code and output",
                    "has_command": bool(command),
                    "has_exit_code": exit_code is not None,
                    "has_log": bool(log),
                }
            )
            continue
        if int(exit_code) != 0:
            unbacked.append(
                {
                    "lane": name,
                    "result": result,
                    "why": f"claims a pass with exit code {exit_code}",
                }
            )
    if unbacked:
        return _finding(
            "command_receipts",
            FAIL,
            "one or more lanes claim a result no command produced",
            unbacked=unbacked[:20],
            unbacked_count=len(unbacked),
        )
    return _finding(
        "command_receipts",
        OK,
        f"all {len(lanes)} lanes carry a command, an exit code and output or a "
        "stated reason",
        lanes=len(lanes),
    )


def check_lane_head_currency(
    packet: Mapping[str, Any], validation: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Lanes sealed at an earlier commit must not present as this packet's.

    check_head_binding proves the packet names the current commit and
    check_command_receipts proves each lane carries a real command and exit
    code. Neither asks the question in between: did those lanes actually run
    at the commit the packet names? A packet could bind head X, carry lane
    receipts produced at head Y, and pass every other predicate -- which is
    MR35R-02's defect displaced from members onto lanes. It is easy to reach
    honestly: change one line, re-seal the packet, and the old lane results
    come along.
    """

    if not validation:
        return _finding(
            "lane_head_currency",
            UNAVAILABLE,
            "no validation artifact was supplied, so the commit its lanes ran "
            "at is unknown",
        )
    lane_head = (validation.get("source") or {}).get("head") or validation.get("head")
    packet_head = packet.get("source_head")
    if not lane_head:
        return _finding(
            "lane_head_currency",
            UNAVAILABLE,
            "the validation artifact records no head, so its lanes cannot be "
            "tied to any commit",
            packet_head=packet_head,
        )
    if not packet_head:
        return _finding(
            "lane_head_currency",
            UNAVAILABLE,
            "the packet declares no head to compare the lanes against",
            lane_head=lane_head,
        )
    if lane_head != packet_head:
        return _finding(
            "lane_head_currency",
            FAIL,
            "the validation lanes ran at a different commit than the packet "
            "describes, so their results are not evidence about this packet",
            packet_head=packet_head,
            lane_head=lane_head,
        )
    return _finding(
        "lane_head_currency",
        OK,
        "every lane receipt was produced at the commit this packet names",
        head=packet_head,
    )


def check_population_not_empty(
    counts: Mapping[str, Any], required_keys: Sequence[str]
) -> dict[str, Any]:
    """An expected population of zero is never evidence of completeness."""

    missing = [key for key in required_keys if key not in counts]
    if missing:
        return _finding(
            "expected_population",
            UNAVAILABLE,
            "required population keys are absent from the delivered counts; a "
            "missing key is a schema error, not a zero",
            missing_keys=missing,
        )
    empty = [key for key in required_keys if not int(counts[key] or 0)]
    if empty:
        return _finding(
            "expected_population",
            FAIL,
            "a required population is empty, which cannot be read as complete "
            "coverage",
            empty_keys=empty,
        )
    return _finding(
        "expected_population",
        OK,
        "every required population has rows behind it",
        checked=list(required_keys),
    )


def read_required(counts: Mapping[str, Any], key: str) -> dict[str, Any]:
    """Read a count by key, failing loudly when the key does not exist.

    ``counts.get(key, 0)`` is the shape that turns a renamed field into a
    quiet zero. This returns an explicit unavailable state instead.
    """

    if key not in counts:
        return _finding(
            "required_key",
            UNAVAILABLE,
            f"the delivered counts have no key {key!r}; the reader must not "
            "default it to zero",
            key=key,
            available_keys=sorted(counts)[:40],
        )
    return _finding("required_key", OK, f"read {key!r}", key=key, value=counts[key])


def check_query_returns_rows(row_count: int | None, query: str) -> dict[str, Any]:
    """A zero-row query is a result to report, never a silent success."""

    if row_count is None:
        return _finding(
            "query_rows",
            UNAVAILABLE,
            "the query did not execute, so it has no row count",
            query=query,
        )
    if row_count == 0:
        return _finding(
            "query_rows",
            FAIL,
            "the query returned no rows; an empty result cannot stand in for a "
            "delivered table",
            query=query,
            rows=0,
        )
    return _finding("query_rows", OK, "the query returned rows", query=query, rows=row_count)


def check_no_parser_generated_labels(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """The producer must not also supply the labels it is being checked against.

    A row whose ``label_source`` is the same parser that produced the row is
    self-certifying. It is rejected here rather than counted as agreement.
    """

    offenders = [
        {
            "row": index,
            "producer": row.get("producer"),
            "label_source": row.get("label_source"),
        }
        for index, row in enumerate(rows)
        if row.get("label_source") and row.get("label_source") == row.get("producer")
    ]
    if offenders:
        return _finding(
            "independent_labels",
            FAIL,
            "rows carry labels generated by their own producer",
            offenders=offenders[:20],
            offender_count=len(offenders),
        )
    return _finding(
        "independent_labels", OK, "no row's label came from its own producer"
    )


def check_selected_release_is_the_successor(
    selected: str | None, delivered: str, predecessors: Sequence[str]
) -> dict[str, Any]:
    """A report must read the release it delivered, not an older snapshot."""

    if not selected:
        return _finding(
            "release_selection",
            UNAVAILABLE,
            "no release path was recorded, so which artifact was read is unknown",
        )
    if str(selected) in {str(item) for item in predecessors}:
        return _finding(
            "release_selection",
            FAIL,
            "the report read a predecessor release instead of the delivered "
            "successor",
            selected=selected,
            delivered=delivered,
        )
    if str(selected) != str(delivered):
        return _finding(
            "release_selection",
            FAIL,
            "the report read a release other than the one this run delivered",
            selected=selected,
            delivered=delivered,
        )
    return _finding(
        "release_selection", OK, "the report read the delivered successor release"
    )


def check_unknown_not_converted(states: Mapping[str, str]) -> dict[str, Any]:
    """An unknown must stay unknown; converting it to a pass is a defect."""

    converted = [
        name
        for name, value in states.items()
        if str(value).upper() in {"PASS", "OK", "CONFIRMED", "TRUE"}
        and "UNKNOWN" in name.upper()
    ]
    if converted:
        return _finding(
            "unknown_preserved",
            FAIL,
            "an unknown state was reported as a pass",
            converted=converted,
        )
    return _finding("unknown_preserved", OK, "unknown states were preserved")


def evaluate_packet(
    packet: Mapping[str, Any],
    *,
    root: Path,
    actual_head: str,
    actual_tree: str,
    expected_data_root: str,
    counts: Mapping[str, Any],
    required_population_keys: Sequence[str],
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run every predicate and report the worst state, never an average."""

    findings = [
        check_head_binding(packet, actual_head, actual_tree),
        check_member_digests(packet, root),
        check_data_root(packet, expected_data_root),
        check_command_receipts(packet),
        check_lane_head_currency(packet, validation),
        check_population_not_empty(counts, required_population_keys),
    ]
    states = {finding["state"] for finding in findings}
    overall = FAIL if FAIL in states else (UNAVAILABLE if UNAVAILABLE in states else OK)
    return {
        "guard_version": PACKET_GUARD_VERSION,
        "overall": overall,
        "findings": findings,
        "worst_state_wins": (
            "The packet's state is the worst of its predicates. A failing "
            "predicate is never averaged away by passing ones."
        ),
    }
