"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-02 / W37R-24: compare the baseline and final full-suite lanes by failure
CAUSE, not only by failing test identity.

A set difference over failing identities says how many failures a head
introduced. It cannot see a test that fails on both sides for different
reasons: W37R-24 found one, where the baseline failed because an export has no
.git and the head failed because of this attempt's own commit subjects. So
"0 introduced" was true as measured and not the whole truth.

This reads each lane's own unittest log. For every ERROR/FAIL block it keeps
the identity, the kind and the final exception block, normalized so that paths,
digests, addresses and timings do not count as a different cause. Each identity
is then FIXED, INTRODUCED, INHERITED_SAME_CAUSE or INHERITED_DIFFERENT_CAUSE,
with both causes shown for the last. The file imports nothing from
aggie_analytics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
class _bas_atomic:  # U37-11: atomic writes, self-contained -- this tool stays independent of aggie_analytics
    @staticmethod
    def _begin(path):
        import os as _bas_os
        import pathlib as _bas_pathlib
        import tempfile as _bas_tempfile

        target = path.resolve() if path.is_symlink() else path
        handle, name = _bas_tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")
        _bas_os.close(handle)
        return target, _bas_pathlib.Path(name)

    @staticmethod
    def _finish(temporary, target):
        import os as _bas_os
        import stat as _bas_stat
        import time as _bas_time

        with open(temporary, "rb+") as stream:
            _bas_os.fsync(stream.fileno())
        try:
            mode = _bas_stat.S_IMODE(_bas_os.stat(target).st_mode)
        except FileNotFoundError:
            umask = _bas_os.umask(0)
            _bas_os.umask(umask)
            mode = 0o666 & ~umask
        _bas_os.chmod(temporary, mode)
        for attempt in range(6):
            try:
                _bas_os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                _bas_time.sleep(0.05 * (attempt + 1))

    @classmethod
    def _call(cls, method, path, *args, **kwargs):
        import pathlib as _bas_pathlib

        if not isinstance(path, _bas_pathlib.Path):
            return getattr(path, method)(*args, **kwargs)
        target, temporary = cls._begin(path)
        try:
            written = getattr(temporary, method)(*args, **kwargs)
            cls._finish(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return written

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        return cls._call("write_text", path, *args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        return cls._call("write_bytes", path, *args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        import contextlib as _bas_contextlib
        import pathlib as _bas_pathlib

        @_bas_contextlib.contextmanager
        def _stream():
            if not isinstance(path, _bas_pathlib.Path):
                with path.open(*args, **kwargs) as stream:
                    yield stream
                return
            target, temporary = cls._begin(path)
            try:
                with temporary.open(*args, **kwargs) as stream:
                    yield stream
                cls._finish(temporary, target)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise

        return _stream()

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
SEPARATOR = "=" * 70
RULE = "-" * 70
HEADER = re.compile(r"^(ERROR|FAIL): (\S+) \(([^)]+)\)(?: \((.*)\))?\s*$")

#: A different cause is not a verdict; it needs an explanation from the two
#: exception blocks. Each entry below was read from both blocks. A different
#: cause that is not listed here is reported as UNADJUDICATED.
ADJUDICATIONS = {
    "test_execution_focus.ExecutionFocusPolicyTests.test_repository_policy_is_valid_before_new_commit": (
        "Baseline: EXECUTION_FOCUS_HISTORY_UNAVAILABLE, because the exact-hash export has no .git. Final: "
        "COMMIT_CLASSIFICATION_INVALID for this attempt's own commit subjects (W37R-23), which the attempt "
        "introduced, and corrected in 70784486 through the policy's SHA-scoped correction list. A rerun at or after "
        "that commit should no longer fail this way."),
    "test_tamu_official_1998_2009_rejection_integrity.RejectionIntegrityGateTests."
    "test_reconstruction_does_not_read_the_working_checkout_commit": (
        "Baseline stops at `git rev-parse HEAD` because the export has no .git. Final gets past it and fails on "
        "the ledger-identity assertion: the unactivated Family B successor. The reconstruction names d48698ab and "
        "the committed gate pins 1b79f1ba. The sibling test_gate_reconstructs fails with that same mismatch on BOTH "
        "sides, so this is the export's shape and not a regression."),
    **{f"test_tamu_official_historical_coverage_inventory.InventoryPayloadMutationTests.{name}": (
        "Both sides fail because the canonical inventory payload is 0 bytes (R37-N zero-byte scope). At baseline "
        "the mutation test crashed with JSONDecodeError while copying it. This attempt's e768d8bd made the test "
        "refuse with a named assertion instead, and stopped the suite from writing the canonical payload in place. "
        "The root cause is the same; the message changed on purpose.")
       for name in ("test_guessed_year_url_fails", "test_missing_official_discovery_provenance_fails",
                    "test_third_party_discovery_url_fails", "test_union_season_falsely_missing_fails")},
}

_NORMALIZE = (
    (re.compile(r"[A-Za-z]:[\\/][^\s'\"(),:;]*"), "<PATH>"),
    (re.compile(r"(?<![\w.])/(?:c|tmp|home|Users|mnt)/[^\s'\"(),:;]*"), "<PATH>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<ADDR>"),
    (re.compile(r"\b[0-9a-f]{12,}\b"), "<HEX>"),
    (re.compile(r"\b\d+\.\d+s\b"), "<SECONDS>"),
)


def normalize(text: str) -> str:
    for pattern, token in _NORMALIZE:
        text = pattern.sub(token, text)
    return re.sub(r"[ \t]+", " ", text).strip()


def failure_blocks(log: str) -> dict[str, dict[str, Any]]:
    """Every ERROR/FAIL block in a unittest -v log, keyed by identity."""

    blocks: dict[str, dict[str, Any]] = {}
    lines = log.splitlines()
    index = 0
    while index < len(lines):
        match = HEADER.match(lines[index])
        if not match or index == 0 or lines[index - 1] != SEPARATOR:
            index += 1
            continue
        kind, _name, identity, subtest = match.groups()
        body: list[str] = []
        index += 1
        if index < len(lines) and lines[index] == RULE:
            index += 1
        while index < len(lines) and lines[index] != SEPARATOR and not (
                lines[index] == RULE and index + 1 < len(lines) and lines[index + 1].startswith("Ran ")):
            body.append(lines[index])
            index += 1
        # The exception block is what follows the last indented traceback line.
        last_frame = max((i for i, line in enumerate(body) if line.startswith("  ")), default=-1)
        exception = [line for line in body[last_frame + 1:] if line.strip()]
        key = identity if not subtest else f"{identity} ({subtest})"
        signature = normalize(exception[0]) if exception else "<NO_EXCEPTION_LINE>"
        entry = {"kind": kind, "signature": signature,
                 "exception_block": normalize("\n".join(exception))[:1500],
                 "exception_type": signature.split(":", 1)[0] if ":" in signature else signature}
        if key in blocks:
            blocks[key].setdefault("repeats", []).append(entry)
        else:
            blocks[key] = entry
    return blocks


def compare(baseline_log: str, final_log: str) -> dict[str, Any]:
    before, after = failure_blocks(baseline_log), failure_blocks(final_log)
    rows = []
    for identity in sorted(set(before) | set(after)):
        b, a = before.get(identity), after.get(identity)
        if b and not a:
            state = "FIXED"
        elif a and not b:
            state = "INTRODUCED"
        elif (b["kind"], b["exception_block"]) == (a["kind"], a["exception_block"]):
            state = "INHERITED_SAME_CAUSE"
        else:
            state = "INHERITED_DIFFERENT_CAUSE"
        row = {"identity": identity, "state": state, "baseline": b, "final": a}
        if state == "INHERITED_DIFFERENT_CAUSE":
            row["adjudication"] = ADJUDICATIONS.get(identity, "UNADJUDICATED")
        rows.append(row)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return {"baseline_failure_blocks": len(before), "final_failure_blocks": len(after), "states": counts,
            "introduced": [r["identity"] for r in rows if r["state"] == "INTRODUCED"],
            "inherited_different_cause": [r["identity"] for r in rows if r["state"] == "INHERITED_DIFFERENT_CAUSE"],
            "unadjudicated_different_cause": [r["identity"] for r in rows if r.get("adjudication") == "UNADJUDICATED"],
            "rows": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline-receipt", type=Path, default=ATTEMPT / "evidence/lanes/full-baseline-mounted.json")
    parser.add_argument("--final-receipt", type=Path, default=ATTEMPT / "evidence/lanes/full-final-mounted.json")
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence/repairs/R37_02_CAUSE_COMPARISON.json")
    args = parser.parse_args(argv)
    receipts, logs = {}, {}
    for side, path in (("baseline", args.baseline_receipt), ("final", args.final_receipt)):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        log_path = next(Path(receipt["log_dir"]).glob("*.log"))
        receipts[side] = {"receipt": str(path), "log": str(log_path), "observed_at": receipt.get("observed_at"),
                          "source_binding": receipt.get("source_binding"),
                          "failed_or_errored_identities": receipt.get("failed_or_errored_identities") or []}
        logs[side] = log_path.read_text(encoding="utf-8", errors="replace")
    result = compare(logs["baseline"], logs["final"])
    # The log parse must agree with the lane's own identity parse, or the
    # comparison is of something else.
    parsed = {side: set(failure_blocks(logs[side])) for side in logs}
    agreement = {side: sorted(set(receipts[side]["failed_or_errored_identities"]) ^ parsed[side]) for side in logs}
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-02-AC03",
              "finding": "W37R-24", "inputs": receipts,
              "log_parse_disagrees_with_lane_parse": agreement,
              "log_parse_agrees_with_lane_parse": not any(agreement.values()),
              **result,
              "normalization": "paths, 0x addresses, hex runs of 12+ characters and N.NNs timings are masked; "
                               "everything else in the exception block must match for SAME_CAUSE",
              "independence": "Imports nothing from aggie_analytics."}
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("baseline_failure_blocks", "final_failure_blocks", "states", "introduced",
                                             "inherited_different_cause", "unadjudicated_different_cause",
                                             "log_parse_agrees_with_lane_parse")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
