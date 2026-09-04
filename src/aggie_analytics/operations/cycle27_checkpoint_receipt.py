"""Content-addressed Cycle 27 checkpoint receipt binder.

Generic T-24H / T-90M windows derive from the bound contest cutoff, never from
A&M or a hardcoded September 3 / 19:45Z constant. Raw collection does not
claim FORECAST_FROZEN. Receipt versions are content-addressed; a separately
labeled latest pointer updates only after the versioned write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.operations.contest_checkpoint_ledger import (
    CAPTURE_WINDOW,
    T24H,
    T90M,
)

OPS26 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle26")
OPS27 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27")
DATA = Path(r"C:\BatteredAggieSyndrome.data")
C27_LEDGER = Path(
    r"C:\BatteredAggieSyndrome.data\worktrees\BAT-690-c27-scr"
    r"\artifacts\scientific_integrity\cycle27\CYCLE27_CONTEST_CHECKPOINT_LEDGER.json"
)
REQUIRED_STAGES = ("schedule", "authority", "rankings", "weather", "eligibility_ledger")
# Incident evidence: the retired C26 binder used this as "earliest T-90M".
C26_SEP3_T90M_CONSTANT = datetime(2026, 9, 3, 20, 30, tzinfo=timezone.utc)
HARDCODED_FRI_WINDOW_CONSTANT = datetime(2026, 9, 4, 19, 45, tzinfo=timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_capture_window_open(
    cutoff: datetime,
    explicit: datetime | None = None,
) -> datetime:
    """Window opens CAPTURE_WINDOW before the bound cutoff unless explicitly supplied.

    An explicit 19:45Z constant is rejected when it is not exactly cutoff-60m for
    this contest. Callers must not reuse an A&M/Friday-21:00 window for a later
    cluster.
    """
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("cutoff must be timezone-aware")
    cutoff = cutoff.astimezone(timezone.utc)
    derived = cutoff - CAPTURE_WINDOW
    if explicit is None:
        return derived
    if explicit.tzinfo is None or explicit.utcoffset() is None:
        raise ValueError("capture_window_open must be timezone-aware")
    explicit = explicit.astimezone(timezone.utc)
    if explicit >= cutoff:
        raise ValueError("capture_window_open must precede cutoff")
    if explicit == HARDCODED_FRI_WINDOW_CONSTANT and explicit != derived:
        raise ValueError(
            "HARDCODED_CAPTURE_WINDOW_NOT_FROM_BOUND_CUTOFF: 19:45Z is not "
            "this contest's cutoff minus 60 minutes"
        )
    return explicit


def classify_checkpoint_label(
    *,
    phase: str,
    now: datetime,
    window_open: datetime,
    cutoff: datetime,
    missing_stages: Sequence[str],
    cohort_contest: str,
) -> dict[str, Any]:
    """Classify a capture. Completion after cutoff is never a backfilled T90/T24 label."""
    if phase not in {T90M, T24H}:
        raise ValueError(f"unsupported phase {phase}")
    on_time = window_open <= now <= cutoff
    if now > cutoff:
        return {
            "checkpoint_label": "LATE_RAW_CAPTURE_ONLY",
            "label_authority": "MISSED_CUTOFF_NO_BACKFILL",
            "state": "MISSED_CUTOFF_NO_BACKFILL",
            "on_time": False,
            "forecast_frozen": False,
        }
    if missing_stages:
        return {
            "checkpoint_label": "PARTIAL_RAW_EVIDENCE",
            "label_authority": "REQUIRED_STAGE_MISSING",
            "state": "EVIDENCE_CAPTURED",
            "on_time": False,
            "forecast_frozen": False,
        }
    if on_time:
        pretty = "T-90M" if phase == T90M else "T-24H"
        return {
            "checkpoint_label": pretty,
            "label_authority": f"{phase}_LABEL_PERMITTED_FOR_BOUND_CONTEST_{cohort_contest}",
            "state": "EVIDENCE_CAPTURED",
            "on_time": True,
            "forecast_frozen": False,
        }
    return {
        "checkpoint_label": "RAW_CAPTURE_OUTSIDE_WINDOW",
        "label_authority": "NOT_IN_DECLARED_CAPTURE_WINDOW",
        "state": "EVIDENCE_CAPTURED",
        "on_time": False,
        "forecast_frozen": False,
    }


def parse_named_stages(log_text: str) -> dict[str, dict[str, str]]:
    stages: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in log_text.splitlines():
        start = re.search(r"\[([^\]]+)\] START ([A-Za-z0-9_]+):", line)
        if start:
            current = start.group(2)
            stage = stages.setdefault(current, {"start_line": line})
            stage["start_utc"] = format_utc(parse_dt(start.group(1)))
            continue
        ok = re.search(r"\[([^\]]+)\] OK ([A-Za-z0-9_]+)$", line)
        if ok:
            stage = stages.setdefault(ok.group(2), {})
            stage["ok"] = "true"
            stage["ok_utc"] = format_utc(parse_dt(ok.group(1)))
            continue
        if current:
            ident = re.search(r"capture_identity:\s*([a-f0-9]{64})", line)
            if ident:
                stages[current]["capture_identity"] = ident.group(1)
    return stages


def bound_cutoff_for_phase(contest: Mapping[str, Any], phase: str) -> datetime:
    key = "t90m_cutoff_utc" if phase == T90M else "t24h_cutoff_utc"
    raw = contest.get(key)
    if not raw:
        raise ValueError("BOUND_CUTOFF_MISSING_FROM_CONTEST_ROW")
    return parse_dt(str(raw))


def require_cutoff_matches_contest(
    cutoff: datetime, contest: Mapping[str, Any], phase: str
) -> datetime:
    bound = bound_cutoff_for_phase(contest, phase)
    if format_utc(cutoff) != format_utc(bound):
        raise ValueError("CUTOFF_NOT_BOUND_TO_CONTEST_PHASE")
    return bound


def stage_completion_authority(
    *,
    stages: Mapping[str, Mapping[str, str]],
    required: Sequence[str],
    window_open: datetime,
    cutoff: datetime,
) -> dict[str, Any]:
    missing_ok: list[str] = []
    missing_timestamps: list[str] = []
    stale: list[str] = []
    late: list[str] = []
    completions: list[datetime] = []
    for name in required:
        stage = stages.get(name) or {}
        if stage.get("ok") != "true":
            missing_ok.append(name)
            continue
        raw = stage.get("ok_utc")
        if not raw:
            missing_timestamps.append(name)
            continue
        completed = parse_dt(raw)
        completions.append(completed)
        if completed < window_open:
            stale.append(name)
        elif completed > cutoff:
            late.append(name)
    authority = None
    if completions and not missing_ok and not missing_timestamps:
        authority = max(completions)
    return {
        "missing_ok": missing_ok,
        "missing_timestamps": missing_timestamps,
        "stale_before_window": stale,
        "completed_after_cutoff": late,
        "acquisition_completed_at": authority,
    }


def lookup_identity(identity: str, data_root: Path) -> dict[str, Any]:
    root = data_root / "manifests" / "shadow"
    hits: list[dict[str, Any]] = []
    if root.exists() and identity:
        for path in root.glob(f"**/sha256/{identity}/*"):
            hits.append(
                {
                    "path": str(path).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
            if len(hits) >= 3:
                break
    return {"identity": identity, "found": bool(hits), "manifests": hits}


def load_contest_row(
    contest_id: str,
    ledger_paths: Sequence[Path],
) -> dict[str, Any] | None:
    for path in ledger_paths:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("contests") or payload.get("rows") or []
        for row in rows:
            if str(row.get("ncaa_contest_id")) == str(contest_id):
                return dict(row)
    return None


def bind_checkpoint_receipt(
    *,
    checkpoint: str,
    phase: str,
    run_id: str,
    log_path: Path,
    cutoff: datetime,
    cohort_contest: str,
    now: datetime,
    output_root: Path,
    data_root: Path,
    ledger_paths: Sequence[Path],
    capture_window_open: datetime | None = None,
    clock_note: str = "Host OS clock; not cryptographic global-time proof",
) -> dict[str, Any]:
    if not log_path.is_file():
        raise FileNotFoundError("LOG_MISSING")
    window_open = derive_capture_window_open(cutoff, capture_window_open)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    stages = parse_named_stages(log_text)
    capture_run_logs = re.findall(
        r"C:\\BatteredAggieSyndrome\.data\\ops\\cycle26\\CYCLE26_CAPTURE_RUN_\d{8}T\d{6}Z\.log",
        log_text,
    )
    bound_capture_log = capture_run_logs[-1] if capture_run_logs else None
    if bound_capture_log and Path(bound_capture_log).is_file():
        stages.update(
            parse_named_stages(
                Path(bound_capture_log).read_text(encoding="utf-8", errors="replace")
            )
        )
    identities = {
        name: lookup_identity(
            stages.get(name, {}).get("capture_identity") or "", data_root
        )
        for name in ("schedule", "rankings", "weather")
    }
    contest = load_contest_row(cohort_contest, ledger_paths)
    if contest is None:
        raise ValueError("COHORT_CONTEST_MISSING")
    require_cutoff_matches_contest(cutoff, contest, phase)
    authority = stage_completion_authority(
        stages=stages,
        required=REQUIRED_STAGES,
        window_open=window_open,
        cutoff=cutoff,
    )
    missing = list(authority["missing_ok"]) + list(authority["missing_timestamps"])
    if authority["completed_after_cutoff"]:
        classification_now = cutoff + timedelta(seconds=1)
    elif authority["acquisition_completed_at"] is not None:
        classification_now = authority["acquisition_completed_at"]
    else:
        classification_now = now
    if authority["stale_before_window"] and not authority["completed_after_cutoff"]:
        classification_now = window_open - timedelta(seconds=1)
    classification = classify_checkpoint_label(
        phase=phase,
        now=classification_now,
        window_open=window_open,
        cutoff=cutoff,
        missing_stages=missing,
        cohort_contest=str(cohort_contest),
    )
    if authority["stale_before_window"] and classification["checkpoint_label"] == (
        "RAW_CAPTURE_OUTSIDE_WINDOW"
    ):
        classification["label_authority"] = "STALE_STAGE_NOT_THIS_WINDOW"
    identities_found = all(
        identities[name]["found"] for name in ("schedule", "rankings", "weather")
    )
    receipt_verified = (
        not missing
        and not authority["stale_before_window"]
        and not authority["completed_after_cutoff"]
        and bool(classification["on_time"])
        and identities_found
        and authority["acquisition_completed_at"] is not None
    )
    issued_at = authority["acquisition_completed_at"] or now
    receipt: dict[str, Any] = {
        "artifact_type": "CYCLE27_CHECKPOINT_CAPTURE_RECEIPT",
        "run_id": run_id,
        "checkpoint": checkpoint,
        "phase": phase,
        "cohort_contest": str(cohort_contest),
        "issued_at_utc": format_utc(issued_at),
        "completed_at_utc": format_utc(issued_at),
        "receipt_bound_at_utc": format_utc(now),
        "cutoff_utc": format_utc(cutoff),
        "earliest_cutoff_utc": format_utc(cutoff),
        "coverage": "EXACT_EARLIEST_CLUSTER",
        "capture_window_open_utc": format_utc(window_open),
        "scheduler_log": str(log_path).replace("\\", "/"),
        "scheduler_log_sha256": sha256_file(log_path),
        "capture_run_log": bound_capture_log,
        "required_stages": list(REQUIRED_STAGES),
        "stage_results": stages,
        "missing_required_stages": list(missing),
        "stage_authority": {
            "missing_ok": authority["missing_ok"],
            "missing_timestamps": authority["missing_timestamps"],
            "stale_before_window": authority["stale_before_window"],
            "completed_after_cutoff": authority["completed_after_cutoff"],
            "acquisition_completed_at_utc": (
                format_utc(issued_at)
                if authority["acquisition_completed_at"] is not None
                else None
            ),
        },
        "capture_identities": identities,
        "eligibility_contest_row": contest,
        "clock_note": clock_note,
        "state": classification["state"],
        "checkpoint_label": classification["checkpoint_label"],
        "label_authority": classification["label_authority"],
        "forecast_frozen": False,
        "receipt_verified": receipt_verified,
        "git_publication": "NOT_IN_THIS_RUN",
        "window_derivation": "cutoff_minus_capture_window_unless_explicit",
        "c26_sep3_t90m_constant_not_used": format_utc(C26_SEP3_T90M_CONSTANT),
    }
    payload = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    receipt["receipt_sha256"] = digest
    out_dir = output_root / "receipts" / checkpoint
    out_dir.mkdir(parents=True, exist_ok=True)
    versioned = out_dir / f"{digest}.json"
    versioned.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pointer = {
        "artifact_type": "CYCLE27_LATEST_RECEIPT_POINTER",
        "checkpoint": checkpoint,
        "receipt_path": str(versioned).replace("\\", "/"),
        "receipt_sha256": digest,
        "updated_at_utc": format_utc(now),
        "note": "Pointer updated only after versioned write. Predecessor versions remain.",
    }
    (out_dir / "LATEST.json").write_text(
        json.dumps(pointer, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "ok": True,
        "receipt": str(versioned),
        "verified": receipt_verified,
        "state": classification["state"],
        "checkpoint_label": classification["checkpoint_label"],
        "receipt_sha256": digest,
    }


def default_ledger_paths() -> list[Path]:
    return [
        C27_LEDGER,
        OPS26 / "CYCLE26_CHECKPOINT_ELIGIBILITY_LEDGER.json",
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--phase", required=True, choices=(T90M, T24H))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--cohort-contest", required=True)
    parser.add_argument("--capture-window-open", default=None)
    parser.add_argument("--output-root", default=str(OPS27))
    parser.add_argument("--data-root", default=str(DATA))
    parser.add_argument("--ledger", action="append", default=None)
    parser.add_argument(
        "--now-utc",
        default=None,
        help="Replay metadata only. Live acquisition uses the host clock.",
    )
    args = parser.parse_args(argv)

    now = parse_dt(args.now_utc) if args.now_utc else utc_now()
    cutoff = parse_dt(args.cutoff)
    explicit = parse_dt(args.capture_window_open) if args.capture_window_open else None
    ledger_paths = (
        [Path(path) for path in args.ledger] if args.ledger else default_ledger_paths()
    )
    clock_note = (
        "REPLAY_METADATA_NOT_ACQUISITION_CLOCK"
        if args.now_utc
        else "Host OS clock; not cryptographic global-time proof"
    )
    try:
        result = bind_checkpoint_receipt(
            checkpoint=args.checkpoint,
            phase=args.phase,
            run_id=args.run_id,
            log_path=Path(args.log),
            cutoff=cutoff,
            cohort_contest=args.cohort_contest,
            now=now,
            output_root=Path(args.output_root),
            data_root=Path(args.data_root),
            ledger_paths=ledger_paths,
            capture_window_open=explicit,
            clock_note=clock_note,
        )
    except FileNotFoundError:
        print(json.dumps({"ok": False, "reason": "LOG_MISSING"}))
        return 2
    except ValueError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    state = result["state"]
    return 0 if result["verified"] or state != "MISSED_CUTOFF_NO_BACKFILL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
