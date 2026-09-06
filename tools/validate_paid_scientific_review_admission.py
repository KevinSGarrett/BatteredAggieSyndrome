"""Validate paid scientific-review admission, cache, model, and cost ceilings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle28.cost import PaidReviewError, admit_paid_review, review_tuple


def validate_payload(payload: dict) -> list[str]:
    findings: list[str] = []
    try:
        admit_paid_review(
            deterministic_passed=bool(payload.get("deterministic_passed")),
            readiness_label_present=bool(payload.get("readiness_label_present")),
            authorized_head_sha=str(payload.get("authorized_head_sha") or ""),
            current_head_sha=str(payload.get("current_head_sha") or ""),
            model=str(payload.get("model") or "gpt-5.3-codex"),
            effort=str(payload.get("effort") or "low"),
            premium_authorized=bool(payload.get("premium_authorized")),
            cache_hit=bool(payload.get("cache_hit")),
            prior_tuple_paid=bool(payload.get("prior_tuple_paid")),
            estimated_or_actual_cost_usd=payload.get("estimated_or_actual_cost_usd"),
            pr_spend_usd=float(payload.get("pr_spend_usd") or 0.0),
            cycle_spend_usd=float(payload.get("cycle_spend_usd") or 0.0),
            second_run=bool(payload.get("second_run")),
            second_run_reason=payload.get("second_run_reason"),
            retry_loop=bool(payload.get("retry_loop")),
            raw_lake_or_secrets_in_prompt=bool(payload.get("raw_lake_or_secrets_in_prompt")),
        )
        review_tuple(
            repository=str(payload.get("repository") or "KevinSGarrett/BatteredAggieSyndrome"),
            pr_number=int(payload.get("pr_number") or 0),
            base_sha=str(payload.get("base_sha") or ""),
            head_sha=str(payload.get("head_sha") or ""),
            merge_sha=str(payload.get("merge_sha") or ""),
            changed_file_digest=str(payload.get("changed_file_digest") or ""),
            prompt_sha256=str(payload.get("prompt_sha256") or ""),
            rules_sha256=str(payload.get("rules_sha256") or ""),
            model=str(payload.get("model") or "gpt-5.3-codex"),
            effort=str(payload.get("effort") or "low"),
        )
    except (PaidReviewError, TypeError, ValueError) as exc:
        findings.append(str(exc))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    findings = validate_payload(payload)
    print(json.dumps({"result": "PASS" if not findings else "FAIL", "findings": findings}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
