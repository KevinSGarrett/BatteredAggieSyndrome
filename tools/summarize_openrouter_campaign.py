from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


IDENTITY_KEYS = (
    "request_id",
    "request_identity",
    "request_identity_sha256",
    "settlement_request_id",
    "source_request_id",
)


def _to_decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid decimal for {field_name}: {value!r}") from exc


def _first_str(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _iter_json_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix == ".json":
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            records.extend(_flatten_payload(payload))
        elif file_path.suffix == ".jsonl":
            for raw_line in file_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.extend(_flatten_payload(payload))
    return records


def _flatten_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = [payload]
        settlements = payload.get("settlements")
        if isinstance(settlements, dict):
            for request_id, cost in settlements.items():
                rows.append({"request_id": request_id, "cost_usd": cost, "source_type": "settlement_map"})
        requests = payload.get("requests")
        if isinstance(requests, list):
            for row in requests:
                if isinstance(row, dict):
                    rows.append(row)
        return rows
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _extract_usage(record: dict[str, Any]) -> tuple[int, int, Decimal]:
    usage = record.get("usage")
    if isinstance(usage, dict):
        input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
        output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
        if "cost" in usage:
            cost = _to_decimal(usage["cost"], "usage.cost")
        elif "cost_usd" in usage:
            cost = _to_decimal(usage["cost_usd"], "usage.cost_usd")
        else:
            cost = Decimal("0")
        return input_tokens, output_tokens, cost
    input_tokens = int(record.get("input_tokens", record.get("prompt_tokens", 0)) or 0)
    output_tokens = int(record.get("output_tokens", record.get("completion_tokens", 0)) or 0)
    if "cost" in record:
        cost = _to_decimal(record["cost"], "cost")
    elif "cost_usd" in record:
        cost = _to_decimal(record["cost_usd"], "cost_usd")
    else:
        cost = Decimal("0")
    return input_tokens, output_tokens, cost


def _normalize_disposition(value: str | None) -> str:
    token = (value or "").strip().upper().replace("-", "_")
    mapping = {
        "CANDIDATE": "accepted",
        "ACCEPTED": "accepted",
        "MODIFIED": "modified",
        "REVIEW_ONLY": "review_only",
        "REVIEW": "review_only",
        "QUARANTINE": "quarantined",
        "QUARANTINED": "quarantined",
        "REJECTED": "rejected",
    }
    return mapping.get(token, "review_only")


@dataclass(frozen=True)
class ReviewDecision:
    request_id: str
    disposition: str
    review_record_id: str
    reviewed_at: str
    review_revision: int
    supersedes: str | None


def _dedupe_reviews(records: list[dict[str, Any]]) -> dict[str, ReviewDecision]:
    grouped: dict[str, list[ReviewDecision]] = defaultdict(list)
    for row in records:
        request_id = _first_str(row, IDENTITY_KEYS)
        if not request_id:
            continue
        grouped[request_id].append(
            ReviewDecision(
                request_id=request_id,
                disposition=_normalize_disposition(_first_str(row, ("disposition", "review_disposition", "verdict"))),
                review_record_id=_first_str(row, ("review_record_id", "id", "review_id")) or f"anon:{request_id}",
                reviewed_at=_first_str(row, ("reviewed_at", "created_at", "timestamp")) or "",
                review_revision=int(row.get("review_revision", 0) or 0),
                supersedes=_first_str(row, ("supersedes_review_record_id", "supersedes_review_id")),
            )
        )

    resolved: dict[str, ReviewDecision] = {}
    for request_id, candidates in grouped.items():
        superseded_ids = {decision.supersedes for decision in candidates if decision.supersedes}
        survivors = [decision for decision in candidates if decision.review_record_id not in superseded_ids]
        if not survivors:
            survivors = candidates
        survivors.sort(
            key=lambda decision: (
                decision.review_revision,
                decision.reviewed_at,
                decision.review_record_id,
            )
        )
        resolved[request_id] = survivors[-1]
    return resolved


def summarize_campaign(
    requests_root: Path,
    responses_root: Path,
    quarantine_root: Path,
    manifests_root: Path,
    settlements_root: Path,
    provider_usage_root: Path,
    reviews_root: Path,
    hard_budget_usd: Decimal,
) -> dict[str, Any]:
    request_records = _iter_json_records(requests_root)
    response_records = _iter_json_records(responses_root)
    quarantine_records = _iter_json_records(quarantine_root)
    manifest_records = _iter_json_records(manifests_root)
    settlement_records = _iter_json_records(settlements_root)
    provider_records = _iter_json_records(provider_usage_root)
    review_records = _iter_json_records(reviews_root)

    request_ids = {
        request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in request_records) if request_id
    }
    if not request_ids:
        raise RuntimeError("no request identities found")

    by_source_ids: dict[str, set[str]] = {
        "responses": {request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in response_records) if request_id},
        "quarantine": {request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in quarantine_records) if request_id},
        "manifests": {request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in manifest_records) if request_id},
        "settlements": {request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in settlement_records) if request_id},
        "provider_usage": {request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in provider_records) if request_id},
        "reviews": {request_id for request_id in (_first_str(row, IDENTITY_KEYS) for row in review_records) if request_id},
    }
    for source_name, identities in by_source_ids.items():
        unknown = sorted(identities - request_ids)
        if unknown:
            raise RuntimeError(f"identity mismatch in {source_name}: unknown request ids {unknown}")

    usage_by_request: dict[str, tuple[int, int, Decimal]] = {}
    model_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    for row in response_records + quarantine_records:
        request_id = _first_str(row, IDENTITY_KEYS)
        if not request_id:
            continue
        usage_tuple = _extract_usage(row)
        existing = usage_by_request.get(request_id)
        if existing is None:
            usage_by_request[request_id] = usage_tuple
        elif existing != usage_tuple:
            raise RuntimeError(f"usage mismatch for request {request_id}")
        model = _first_str(row, ("model_resolved", "model"))
        if model:
            model_counts[model] += 1
        provider = _first_str(row, ("provider", "provider_name"))
        if provider:
            provider_counts[provider] += 1
        category = _first_str(row, ("category", "task_id", "task"))
        if category:
            category_counts[category] += 1

    settlement_by_request: dict[str, Decimal] = {}
    for row in settlement_records:
        request_id = _first_str(row, IDENTITY_KEYS)
        if not request_id:
            continue
        if "actual_usd" in row:
            cost = _to_decimal(row["actual_usd"], "actual_usd")
        elif "cost_usd" in row:
            cost = _to_decimal(row["cost_usd"], "cost_usd")
        elif "cost" in row:
            cost = _to_decimal(row["cost"], "cost")
        else:
            continue
        prior = settlement_by_request.get(request_id)
        if prior is not None and prior != cost:
            raise RuntimeError(f"settlement mismatch for request {request_id}")
        settlement_by_request[request_id] = cost

    provider_by_request: dict[str, Decimal] = {}
    for row in provider_records:
        request_id = _first_str(row, IDENTITY_KEYS)
        if not request_id:
            continue
        if "cost_usd" in row:
            cost = _to_decimal(row["cost_usd"], "provider cost_usd")
        elif "cost" in row:
            cost = _to_decimal(row["cost"], "provider cost")
        elif isinstance(row.get("usage"), dict) and ("cost" in row["usage"] or "cost_usd" in row["usage"]):
            usage = row["usage"]
            cost = _to_decimal(usage.get("cost", usage.get("cost_usd")), "provider usage cost")
        else:
            continue
        prior = provider_by_request.get(request_id)
        if prior is not None and prior != cost:
            raise RuntimeError(f"provider usage mismatch for request {request_id}")
        provider_by_request[request_id] = cost

    for request_id, (_, _, local_cost) in usage_by_request.items():
        settled = settlement_by_request.get(request_id)
        if settled is not None and settled != local_cost:
            raise RuntimeError(f"cost mismatch local vs settlement for request {request_id}")
        provider = provider_by_request.get(request_id)
        if provider is not None and provider != local_cost:
            raise RuntimeError(f"cost mismatch local vs provider for request {request_id}")

    deduped_reviews = _dedupe_reviews(review_records)
    disposition_counts: Counter[str] = Counter()
    for decision in deduped_reviews.values():
        disposition_counts[decision.disposition] += 1

    manifest_dispositions = Counter(
        _normalize_disposition(_first_str(row, ("disposition", "review_disposition", "verdict")))
        for row in manifest_records
        if _first_str(row, IDENTITY_KEYS)
    )
    for key in ("accepted", "modified", "review_only", "quarantined", "rejected"):
        if manifest_dispositions[key] > 0 and disposition_counts[key] > 0 and manifest_dispositions[key] != disposition_counts[key]:
            raise RuntimeError(f"disposition mismatch for {key}: manifests={manifest_dispositions[key]} reviews={disposition_counts[key]}")

    total_input_tokens = sum(tokens[0] for tokens in usage_by_request.values())
    total_output_tokens = sum(tokens[1] for tokens in usage_by_request.values())
    total_cost = sum((tokens[2] for tokens in usage_by_request.values()), Decimal("0"))
    settlement_total = sum(settlement_by_request.values(), Decimal("0"))
    provider_total = sum(provider_by_request.values(), Decimal("0"))
    if settlement_by_request and settlement_total != total_cost:
        raise RuntimeError(f"total cost mismatch local={total_cost} settlement={settlement_total}")
    if provider_by_request and provider_total != total_cost:
        raise RuntimeError(f"total cost mismatch local={total_cost} provider={provider_total}")

    missing_evidence: dict[str, list[str]] = {}
    for request_id in sorted(request_ids):
        missing = []
        if request_id not in by_source_ids["responses"] and request_id not in by_source_ids["quarantine"]:
            missing.append("response_or_quarantine")
        if request_id not in by_source_ids["manifests"]:
            missing.append("manifest")
        if request_id not in by_source_ids["settlements"]:
            missing.append("settlement")
        if request_id not in by_source_ids["provider_usage"]:
            missing.append("provider_usage")
        if request_id not in by_source_ids["reviews"]:
            missing.append("review")
        if missing:
            missing_evidence[request_id] = missing

    remaining_budget = hard_budget_usd - total_cost
    if remaining_budget < Decimal("0"):
        raise RuntimeError(f"budget exceeded total_cost={total_cost} hard_budget={hard_budget_usd}")

    return {
        "request_count": len(request_ids),
        "response_or_quarantine_count": len(by_source_ids["responses"] | by_source_ids["quarantine"]),
        "quarantined_request_count": len(by_source_ids["quarantine"]),
        "counts_by_disposition": {
            "accepted": int(disposition_counts["accepted"]),
            "modified": int(disposition_counts["modified"]),
            "review_only": int(disposition_counts["review_only"]),
            "quarantined": int(disposition_counts["quarantined"]),
            "rejected": int(disposition_counts["rejected"]),
        },
        "counts_by_category": dict(sorted(category_counts.items())),
        "counts_by_model": dict(sorted(model_counts.items())),
        "counts_by_provider": dict(sorted(provider_counts.items())),
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "total_cost_usd": f"{total_cost:.6f}",
        "remaining_budget_usd": f"{remaining_budget:.6f}",
        "missing_evidence": missing_evidence,
        "review_supersession_policy": (
            "drop records explicitly superseded by review_record_id; "
            "then select highest (review_revision, reviewed_at, review_record_id) per request"
        ),
        "operational_admission_guardrail": "counts_only_never_operational_admission",
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize OpenRouter campaign evidence with strict reconciliation")
    parser.add_argument("--requests-root", type=Path, required=True)
    parser.add_argument("--responses-root", type=Path, required=True)
    parser.add_argument("--quarantine-root", type=Path, required=True)
    parser.add_argument("--manifests-root", type=Path, required=True)
    parser.add_argument("--settlements-root", type=Path, required=True)
    parser.add_argument("--provider-usage-root", type=Path, required=True)
    parser.add_argument("--reviews-root", type=Path, required=True)
    parser.add_argument("--hard-budget-usd", required=True)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    summary = summarize_campaign(
        requests_root=args.requests_root,
        responses_root=args.responses_root,
        quarantine_root=args.quarantine_root,
        manifests_root=args.manifests_root,
        settlements_root=args.settlements_root,
        provider_usage_root=args.provider_usage_root,
        reviews_root=args.reviews_root,
        hard_budget_usd=_to_decimal(args.hard_budget_usd, "hard_budget_usd"),
    )
    payload = json.dumps(summary, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
