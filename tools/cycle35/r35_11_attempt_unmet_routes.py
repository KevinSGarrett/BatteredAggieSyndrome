"""R35-11 second pass: actually attempt the unmet availability routes.

The prior route ledger contains 14 attempts covering twelve FBS conferences
and the CFP. It contains ZERO FCS conferences and ZERO FBS Independents. So
`POLICY_PUBLISHES_NO_REPORT` for those keys was an inventory assumption, not
an attempted-and-failed finding, and the pack is explicit that an
unattempted request is not "source unavailable".

This attempts one documented public route per unmet key and records the
exact outcome. A 200 that is not an availability surface is recorded as
`ATTEMPTED_NOT_AN_AVAILABILITY_SURFACE`, which is a different and weaker
statement than "the conference publishes reports". Nothing here converts a
failed fetch into a fact, and no key leaves the denominator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle35.request_ledger import (  # noqa: E402
    BUDGET_AVAILABILITY,
    BudgetExhausted,
    RequestLedger,
)

USER_AGENT = (
    "BatteredAggieSyndrome-Research/35.1 "
    "(private research; contact via repository owner)"
)

#: One documented public route per unmet key. Conference sites for the FCS
#: keys (whose conference would publish any report), program sites for the
#: two FBS Independents (which have no conference to publish one).
ROUTES: dict[str, dict[str, Any]] = {
    "Holy Cross": {"conference": "Patriot", "url": "https://patriotleague.org/"},
    "Harvard": {"conference": "Ivy", "url": "https://ivyleague.com/"},
    "West Florida": {"conference": "UAC", "url": "https://theuac.com/"},
    "Towson": {"conference": "Coastal Athletic", "url": "https://caasports.com/"},
    "Cal Poly": {"conference": "Big Sky", "url": "https://bigskyconf.com/"},
    "Notre Dame": {"conference": "FBS Independents", "url": "https://und.com/"},
    "UConn": {"conference": "FBS Independents", "url": "https://uconnhuskies.com/"},
}

#: Tokens that make a page plausibly an availability surface. Their presence
#: is necessary, never sufficient -- a hit still means "worth a human look",
#: not "reports exist".
AVAILABILITY_TOKENS = (
    "availability report",
    "availability-report",
    "injury report",
    "participation report",
    "fbreports",
    "player availability",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--release", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    cache_dir = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\availability_route_cache"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    release = json.loads(Path(args.release).read_text(encoding="utf-8"))
    keys = (release.get("national_report_opportunities") or {}).get("keys") or []
    unmet = [k for k in keys if k["outcome"] != "REPORT_EVIDENCE_PRESENT"]

    ledger = RequestLedger()
    attempts: list[dict[str, Any]] = []
    for key in unmet:
        route = ROUTES.get(key["display_name"])
        if route is None:
            attempts.append(
                {
                    **key,
                    "route_url": None,
                    "new_outcome": "NOT_ATTEMPTED_NO_DOCUMENTED_ROUTE",
                    "detail": "No public route is documented for this key; "
                    "recorded as not attempted, not as unavailable.",
                }
            )
            continue
        url = route["url"]
        cache_path = cache_dir / (
            re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_") + ".html"
        )

        def _do(u: str = url) -> tuple[int, bytes]:
            request = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.status, response.read()

        try:
            outcome = ledger.fetch(
                budget=BUDGET_AVAILABILITY,
                url=url,
                purpose="availability-policy surface for an unmet key",
                fetcher=_do,
                cache_path=cache_path,
            )
        except BudgetExhausted as exc:
            attempts.append(
                {**key, "route_url": url,
                 "new_outcome": "NOT_ATTEMPTED_BUDGET_EXHAUSTED",
                 "detail": str(exc)}
            )
            continue

        if not outcome.get("ok"):
            attempts.append(
                {
                    **key,
                    "route_url": url,
                    "new_outcome": "ATTEMPTED_AND_FAILED",
                    "detail": str(outcome.get("detail") or "fetch failed"),
                    "route_now_attempt_verified": True,
                }
            )
            continue

        text = outcome["body"].decode("utf-8", errors="replace").lower()
        hits = [token for token in AVAILABILITY_TOKENS if token in text]
        attempts.append(
            {
                **key,
                "route_url": url,
                "conference_site": route["conference"],
                "http_ok": True,
                "bytes": len(outcome["body"]),
                "availability_tokens_found": hits,
                "new_outcome": (
                    "ATTEMPTED_AVAILABILITY_SURFACE_INDICATED"
                    if hits
                    else "ATTEMPTED_NOT_AN_AVAILABILITY_SURFACE"
                ),
                "detail": (
                    "Tokens found on the conference/program landing page; a "
                    "human must confirm whether per-game reports are actually "
                    "published. Token presence is necessary, not sufficient."
                    if hits
                    else "The landing page carries no availability-reporting "
                    "language. This is now an ATTEMPTED finding rather than "
                    "an inventory assumption, and still means UNKNOWN for "
                    "every player -- never healthy."
                ),
                "route_now_attempt_verified": True,
                "no_report_means": "UNKNOWN",
            }
        )

    by_outcome: dict[str, int] = {}
    for row in attempts:
        by_outcome[row["new_outcome"]] = by_outcome.get(row["new_outcome"], 0) + 1

    result = {
        "artifact_type": "CYCLE35_R35_11_UNMET_ROUTE_ATTEMPTS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "prior_route_ledger_finding": (
            "The 14 pre-existing route attempts cover twelve FBS conferences "
            "and the CFP. They contain zero FCS conferences and zero FBS "
            "Independents, so POLICY_PUBLISHES_NO_REPORT for those keys was "
            "an inventory assumption rather than an attempted finding."
        ),
        "keys_attempted": len(attempts),
        "attempts": attempts,
        "by_outcome": by_outcome,
        "request_ledger": ledger.as_dict(),
        "denominator_unchanged": True,
        "token_presence_is_not_report_existence": True,
        "absence_still_means_unknown_never_healthy": True,
        "pit_admitted": False,
    }
    (out_dir / "R35_11_UNMET_ROUTE_ATTEMPTS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    ledger.write(out_dir / "CYCLE35_REQUEST_LEDGER_AVAILABILITY.json")
    print(json.dumps(
        {
            "keys_attempted": len(attempts),
            "by_outcome": by_outcome,
            "availability_requests_spent": ledger.spent[BUDGET_AVAILABILITY],
            "availability_remaining": ledger.remaining(BUDGET_AVAILABILITY),
            "outcome_counts": ledger.as_dict()["outcome_counts"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
