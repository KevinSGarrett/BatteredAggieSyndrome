from __future__ import annotations

import json
import sys
import urllib.request
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.openrouter_backend import load_openrouter_key  # noqa: E402
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json  # noqa: E402
from aggie_analytics.assistive_plane.budget import BudgetLedger  # noqa: E402


def main() -> int:
    authorization_value = load_openrouter_key(Path(r"C:\BatteredAggieSyndrome\.env"))
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {authorization_value}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    data = body.get("data", {})
    payload = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "usage_usd": str(data.get("usage", "")),
        "usage_daily_usd": str(data.get("usage_daily", "")),
        "usage_weekly_usd": str(data.get("usage_weekly", "")),
        "usage_monthly_usd": str(data.get("usage_monthly", "")),
        "limit_usd": str(data.get("limit", "")),
        "limit_remaining_usd": str(data.get("limit_remaining", "")),
        "is_free_tier": bool(data.get("is_free_tier", False)),
        "label_recorded": False,
        "credential_recorded": False,
    }
    path, digest = write_content_addressed_json(
        Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter"), "usage/provider_snapshots", payload
    )
    policy = json.loads((ROOT / "configs" / "openrouter_assist_policy.json").read_text(encoding="utf-8"))
    ledger = BudgetLedger(
        Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter\usage\ledger.json"),
        Decimal(policy["budget"]["paid_hard_limit_usd"]),
        Decimal(policy["budget"]["released_stage_usd"]),
    )
    ledger.reconcile_provider_total(Decimal(payload["usage_usd"]), evidence_sha256=digest)
    print(json.dumps({"status": "PASS", "usage_usd": payload["usage_usd"], "limit_usd": payload["limit_usd"], "limit_remaining_usd": payload["limit_remaining_usd"], "path": str(path), "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
