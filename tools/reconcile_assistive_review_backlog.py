from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_report(root: Path, payload: dict[str, object]) -> tuple[Path, str]:
    data = _canonical(payload)
    digest = hashlib.sha256(data).hexdigest()
    destination = root / "sha256" / digest[:2] / f"{digest}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("REVIEW_BACKLOG_REPORT_COLLISION")
    if not destination.exists():
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return destination, digest


def reconcile(
    state: ControllerState,
    *,
    provider: str,
    report_root: Path,
    apply: bool,
    limit: int,
) -> dict[str, object]:
    state.initialize()
    with closing(state.connect()) as connection:
        rows = connection.execute(
            "SELECT a.attempt_id,a.work_unit_id,a.started_at,p.remote_identity,r.evidence_sha256 "
            "FROM reviews r JOIN dispatch_attempts a ON a.attempt_id=r.attempt_id "
            "JOIN provider_runs p ON p.attempt_id=a.attempt_id "
            "WHERE p.provider=? AND r.disposition='REVIEW_ONLY' AND NOT EXISTS ("
            "SELECT 1 FROM downstream_review_dispositions d WHERE d.attempt_id=a.attempt_id) "
            "ORDER BY a.started_at,a.attempt_id LIMIT ?",
            (provider, limit),
        ).fetchall()
    candidates = [dict(row) for row in rows]
    dispositions: list[dict[str, object]] = []
    if apply:
        for row in candidates:
            evidence_sha256 = state.record_downstream_review_disposition(
                attempt_id=str(row["attempt_id"]),
                disposition="UNUSED",
                downstream_consumer="NO_REGISTERED_DOWNSTREAM_CONSUMER_AT_AUDIT_CUTOFF",
                reason=(
                    "REVIEW_ONLY_RESULT_NOT_CONSUMED_BY_A_REAL_BAS_WORKFLOW; "
                    "ZERO_ACCEPTED_OFFLOAD_CREDIT"
                ),
            )
            dispositions.append(
                {
                    "attempt_id": row["attempt_id"],
                    "work_unit_id": row["work_unit_id"],
                    "disposition": "UNUSED",
                    "evidence_sha256": evidence_sha256,
                }
            )
    report: dict[str, object] = {
        "schema_version": 1,
        "artifact_type": "ASSISTIVE_REVIEW_BACKLOG_RECONCILIATION",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "provider": provider,
        "mode": "APPLY" if apply else "READ_ONLY",
        "candidate_count": len(candidates),
        "disposition_counts": {"UNUSED": len(dispositions)},
        "accepted_useful_offload_credit": 0,
        "reason": "NO_VERIFIED_DOWNSTREAM_CONSUMER_OR_PROJECT_ARTIFACT_CHANGE",
        "candidates": candidates,
        "dispositions": dispositions,
    }
    path, digest = _write_report(report_root, report)
    return {"report_path": str(path), "report_sha256": digest, **report}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("REVIEW_BACKLOG_LIMIT_INVALID")
    print(
        json.dumps(
            reconcile(
                ControllerState(args.database),
                provider=args.provider,
                report_root=args.report_root,
                apply=args.apply,
                limit=args.limit,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
