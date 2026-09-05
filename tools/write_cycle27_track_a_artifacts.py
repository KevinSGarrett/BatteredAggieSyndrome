#!/usr/bin/env python3
"""Write Cycle 27 Track A ledger, lease plan, and CONTROL-07 protocol artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.governance.trusted_control_change_protocol import (  # noqa: E402
    build_protocol_artifact,
)
from aggie_analytics.operations.contest_checkpoint_ledger import (  # noqa: E402
    build_cycle27_ledger,
    build_lease_and_restart_plan,
    default_receipt_paths,
    load_c26_ledger,
    load_valid_receipts,
    write_json,
)
from aggie_analytics.operations.cycle27_live_owner_inventory import (  # noqa: E402
    build_live_owner_inventory,
    collect_windows_process_rows,
)

OPS26 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle26")
OPS27 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27")
ART26 = REPO / "artifacts" / "scientific_integrity" / "cycle26"
ART27 = REPO / "artifacts" / "scientific_integrity" / "cycle27"


def main() -> int:
    now = datetime.now(timezone.utc)
    c26 = load_c26_ledger(OPS26, ART26)
    receipts = load_valid_receipts(default_receipt_paths(OPS26, ART26, OPS27))
    processes = collect_windows_process_rows()
    inventory = build_live_owner_inventory(
        processes=processes,
        contests=c26.get("contests") or [],
        t24_arm=OPS27 / "CYCLE27_REMAINING_T24_CLUSTER_ARM.json",
        t90_arm=OPS27 / "CYCLE27_REMAINING_T90_CLUSTER_ARM.json",
        now=now,
    )
    ledger = build_cycle27_ledger(
        c26_ledger=c26,
        receipts=receipts,
        now=now,
        live_owners=inventory["live_owners"],
    )
    plan = build_lease_and_restart_plan(
        ledger=ledger, now=now, live_inventory=inventory
    )
    protocol = build_protocol_artifact(
        repo_root=REPO, issued_at_utc=ledger["issued_at_utc"]
    )
    ART27.mkdir(parents=True, exist_ok=True)
    OPS27.mkdir(parents=True, exist_ok=True)
    write_json(ART27 / "CYCLE27_CONTEST_CHECKPOINT_LEDGER.json", ledger)
    write_json(OPS27 / "CYCLE27_CONTEST_CHECKPOINT_LEDGER.json", ledger)
    write_json(ART27 / "CYCLE27_LEASE_AND_RESTART_PLAN.json", plan)
    write_json(OPS27 / "CYCLE27_LEASE_AND_RESTART_PLAN.json", plan)
    write_json(ART27 / "CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL.json", protocol)
    write_json(OPS27 / "CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL.json", protocol)
    write_json(OPS27 / "CYCLE27_LIVE_OWNER_INVENTORY.json", inventory)
    print(json_summary(ledger, plan, protocol, inventory))
    return 0


def json_summary(ledger, plan, protocol, inventory) -> str:
    return json.dumps(
        {
            "contest_count": ledger["contest_count"],
            "saturday_t24h_completed_count": ledger["saturday_t24h_completed_count"],
            "t24h_state_counts": ledger["t24h_state_counts"],
            "t90m_state_counts": ledger["t90m_state_counts"],
            "saturday_t90_clusters": len(
                plan["saturday_t90_clusters_starting_2026_09_05T14_30Z"]
            ),
            "protocol_status": protocol["bootstrap_status"],
            "live_process_count": inventory["live_process_count"],
            "do_not_kill_pids": inventory["do_not_kill_pids"],
        },
        indent=2,
    )


if __name__ == "__main__":
    raise SystemExit(main())
