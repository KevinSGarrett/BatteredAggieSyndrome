from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.cfbd import (
    CFBDTransport,
    acquisition_request,
    load_dotenv_value,
)
from aggie_analytics.data.national_foundation_reconciliation import (
    canonical_json_bytes,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (
    GATE_RELATIVE as FREEZE_GATE_RELATIVE,
    PAYLOAD_SLUG as FREEZE_PAYLOAD_SLUG,
    payload_rows,
    read_json,
    seal_identities,
)
from aggie_analytics.data.week1_2026_authority_enrichment import normalize_name_key
from aggie_analytics.data.week1_2026_ridge_distribution_coherence import (
    audit_cycle24_ridge_forecast_row,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_market_benchmark_and_adequacy.v1"
CONTRACT_ID = "CYCLE25-WEEK1-2026-MARKET-BENCHMARK-AND-ADEQUACY-V1"
JIRA_KEY = "BAT-687"
LOCAL_ISSUE_ID = "POST-TASK-2026-MARKET-BENCHMARK-AND-FORECAST-ADEQUACY-001"
PARENT_JIRA_KEY = "BAT-523"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_EARLY_MARKET_BENCHMARK_AND_ADEQUACY"
CLASSIFICATION = "WEEK1_2026_EARLY_MARKET_BENCHMARK_AND_FORECAST_ADEQUACY"
CONTRACT_RELATIVE = "configs/week1_2026_market_benchmark_and_adequacy_contract.json"
REGISTRY_RELATIVE = "configs/week1_2026_early_market_source_registry.json"
GATE_RELATIVE = "artifacts/forecast/week1_2026_market_benchmark_and_adequacy_gate.json"
PAYLOAD_SLUG = "week1_2026_market_benchmark_and_adequacy"
CANONICAL_DOTENV = Path(r"C:\BatteredAggieSyndrome\.env")
FOCUS_HOME_KEY = "texas a&m"
FOCUS_AWAY_KEY = "missouri st"

ADEQUATE = "ADEQUATE_FOR_SHADOW_COMPARISON"
LIMITED = "LIMITED_STALE_INPUT_SHADOW_ONLY"
REVIEW_DISAGREE = "REVIEW_REQUIRED_MODEL_MARKET_DISAGREEMENT"
REVIEW_SATURATION = "REVIEW_REQUIRED_PROBABILITY_SATURATION"
REVIEW_INCOHERENCE = "REVIEW_REQUIRED_PROBABILITY_DISTRIBUTION_INCOHERENCE"
ABSTAIN_AUTHORITY = "ABSTAIN_FEATURE_AUTHORITY_MISMATCH"
ABSTAIN_FEATURES = "ABSTAIN_MISSING_REQUIRED_FEATURES"
ABSTAIN_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"
MARKET_UNAVAILABLE = "MARKET_REFERENCE_UNAVAILABLE"
QUARANTINED = "QUARANTINED_SOURCE_CONFLICT"


class MarketBenchmarkViolation(ValueError):
    """Raised when the Cycle #25 market benchmark cannot be materialized."""


def canonical_payload_rows(
    data_root: Path, slug: str, dataset_identity: str, name: str
) -> list[dict[str, Any]]:
    path = data_root / "canonical" / slug / "sha256" / dataset_identity / name
    if not path.is_file():
        raise MarketBenchmarkViolation(f"canonical payload missing: {name}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def dotenv_path(repo_root: Path) -> Path:
    for candidate in (
        Path(os.environ.get("AGGIE_ANALYTICS_DOTENV") or ""),
        repo_root / ".env",
        CANONICAL_DOTENV,
    ):
        if str(candidate) and candidate.is_file():
            return candidate
    return CANONICAL_DOTENV


def credential_presence(path: Path, name: str) -> str:
    try:
        value = load_dotenv_value(path, name)
    except FileNotFoundError:
        return "DOTENV_ABSENT"
    except RuntimeError as error:
        text = str(error)
        if "empty" in text:
            return "PRESENT_BUT_EMPTY"
        return "ABSENT"
    if not value:
        return "PRESENT_BUT_EMPTY"
    return "PRESENT"


def american_implied_probability(odds: Any) -> float | None:
    try:
        value = float(odds)
    except (TypeError, ValueError):
        return None
    if value == 0 or math.isnan(value) or math.isinf(value):
        return None
    if value > 0:
        return 100.0 / (value + 100.0)
    return abs(value) / (abs(value) + 100.0)


def multiplicative_devig(
    home_odds: Any,
    away_odds: Any,
    *,
    same_book: bool,
    same_snapshot: bool,
) -> dict[str, Any]:
    if not same_book:
        return {
            "accepted": False,
            "rejection": "CROSS_BOOK_PRICE_PAIRING",
        }
    if not same_snapshot:
        return {
            "accepted": False,
            "rejection": "CROSS_TIMESTAMP_PRICE_PAIRING",
        }
    home_raw = american_implied_probability(home_odds)
    away_raw = american_implied_probability(away_odds)
    if home_raw is None or away_raw is None:
        return {
            "accepted": False,
            "rejection": "ONE_SIDED_OR_MALFORMED_MONEYLINE",
            "raw_implied_home": home_raw,
            "raw_implied_away": away_raw,
        }
    overround = home_raw + away_raw
    if overround <= 0:
        return {
            "accepted": False,
            "rejection": "NEGATIVE_OR_IMPOSSIBLE_OVERROUND",
            "overround": overround,
        }
    if overround < 1.0 - 1e-12:
        return {
            "accepted": False,
            "rejection": "ZERO_OVERROUND_IMPOSSIBLE",
            "overround": overround,
        }
    return {
        "accepted": True,
        "rejection": None,
        "method": "MULTIPLICATIVE_NORMALIZATION",
        "raw_implied_home": round(home_raw, 10),
        "raw_implied_away": round(away_raw, 10),
        "overround": round(overround, 10),
        "devigged_home": round(home_raw / overround, 10),
        "devigged_away": round(away_raw / overround, 10),
    }


def home_expected_margin_from_home_handicap(handicap: Any) -> float | None:
    try:
        value = float(handicap)
    except (TypeError, ValueError):
        return None
    return -value


def consensus_from_books(
    quotes: Sequence[Mapping[str, Any]],
    *,
    minimum_books: int,
) -> dict[str, Any]:
    accepted = [
        quote
        for quote in quotes
        if quote.get("devig", {}).get("accepted") and quote.get("sportsbook")
    ]
    books = sorted({str(quote["sportsbook"]) for quote in accepted})
    probabilities = [float(quote["devig"]["devigged_home"]) for quote in accepted]
    source_count = len(books)
    if source_count == 0:
        label = "INSUFFICIENT_MARKET_COVERAGE"
        median = None
        dispersion = None
    elif source_count < minimum_books:
        label = (
            "SINGLE_SOURCE_MARKET_REFERENCE"
            if source_count == 1
            else "INSUFFICIENT_MARKET_COVERAGE"
        )
        median = round(sorted(probabilities)[len(probabilities) // 2], 10)
        dispersion = round(max(probabilities) - min(probabilities), 10)
    else:
        label = "MARKET_CONSENSUS"
        ordered = sorted(probabilities)
        median = round(ordered[len(ordered) // 2], 10)
        dispersion = round(max(probabilities) - min(probabilities), 10)
    return {
        "label": label,
        "source_count": source_count,
        "independent_books": books,
        "median_devigged_home": median,
        "dispersion": dispersion,
        "aggregation": "MEDIAN_OF_DEVIGGED_HOME_WIN_PROBABILITIES",
        "minimum_independent_books": minimum_books,
        "individual_quotes_hidden": False,
    }


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise MarketBenchmarkViolation("market contract identity drifted")
    if contract["checkpoints"]["t_minus_24h_state"] != "OPEN":
        raise MarketBenchmarkViolation("T-24H is not OPEN")
    if contract["checkpoints"]["t_minus_90m_state"] != "OPEN":
        raise MarketBenchmarkViolation("T-90M is not OPEN")
    if contract["spread_to_exact_win_probability_authorized"] is not False:
        raise MarketBenchmarkViolation(
            "spread-to-probability conversion is not authorized"
        )
    if contract["scientific_nonclaims"]["roughly_40_point_spread_assumed"] is not False:
        raise MarketBenchmarkViolation("40-point spread must not be assumed")
    return contract


def require_freeze(repo_root: Path) -> dict[str, Any]:
    freeze_gate = read_json(repo_root / FREEZE_GATE_RELATIVE)
    freeze = freeze_gate.get("pre_market_model_freeze") or {}
    if freeze.get("freeze_id") != "PRE_MARKET_MODEL_FREEZE":
        raise MarketBenchmarkViolation("PRE_MARKET_MODEL_FREEZE is absent")
    if freeze.get("market_access_occurred") is not False:
        raise MarketBenchmarkViolation(
            "corrective model contract frozen after market access"
        )
    if not freeze.get("issued_at_utc"):
        raise MarketBenchmarkViolation("freeze issuance timestamp is absent")
    return freeze_gate


def redacted_receipt(
    *,
    provider: str,
    uri: str,
    status: int,
    headers: Mapping[str, str],
    body: bytes,
    captured_at_utc: str,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "public_uri": uri,
        "status_code": status,
        "retry_after": headers.get("Retry-After") or headers.get("retry-after"),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "body_preview_redacted": body[:120].decode("utf-8", errors="replace"),
        "captured_at_utc": captured_at_utc,
        "credential_value_recorded": False,
    }


def acquire_cfbd_lines(
    *,
    env_file: Path,
    parameters: Mapping[str, Any],
    captured_at_utc: str,
) -> dict[str, Any]:
    presence = credential_presence(env_file, "CFBD_API_KEY")
    request = acquisition_request(
        endpoint_id="CFBD-GetLines",
        path="/lines",
        parameters=parameters,
        run_id="CYCLE25-EARLY-MARKET",
    )
    if presence != "PRESENT":
        return {
            "route": "CFBD-GetLines",
            "disposition": "CREDENTIAL_ABSENT_OR_UNUSABLE",
            "credential_presence": presence,
            "public_uri": request.source_uri,
            "rows": [],
            "raw_sha256": None,
            "raw_path": None,
        }
    cfbd_auth = load_dotenv_value(env_file, "CFBD_API_KEY")
    transport = CFBDTransport(cfbd_auth, timeout_seconds=90.0)
    response = transport(request)
    receipt = redacted_receipt(
        provider="CollegeFootballData",
        uri=request.source_uri,
        status=int(response.status_code),
        headers=response.headers,
        body=response.body,
        captured_at_utc=captured_at_utc,
    )
    if int(response.status_code) == 429:
        return {
            "route": "CFBD-GetLines",
            "disposition": "QUOTA_EXHAUSTED_429_RECEIPT_PRESERVED",
            "credential_presence": presence,
            "public_uri": request.source_uri,
            "rows": [],
            "raw_sha256": receipt["body_sha256"],
            "receipt": receipt,
            "retry_attempted_after_known_exhaustion": False,
        }
    if int(response.status_code) != 200:
        return {
            "route": "CFBD-GetLines",
            "disposition": f"HTTP_{int(response.status_code)}",
            "credential_presence": presence,
            "public_uri": request.source_uri,
            "rows": [],
            "raw_sha256": receipt["body_sha256"],
            "receipt": receipt,
        }
    payload = json.loads(response.body.decode("utf-8"))
    if not isinstance(payload, list):
        raise MarketBenchmarkViolation("CFBD lines response is not an array")
    return {
        "route": "CFBD-GetLines",
        "disposition": "STRUCTURED_ROWS_CAPTURED",
        "credential_presence": presence,
        "public_uri": request.source_uri,
        "rows": payload,
        "raw_bytes": response.body,
        "raw_sha256": receipt["body_sha256"],
        "receipt": receipt,
    }


def parse_cfbd_quotes(
    events: Sequence[Mapping[str, Any]],
    *,
    captured_at_utc: str,
    raw_sha256: str | None,
) -> list[dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    for event in events:
        event_id = event.get("id")
        home = str(event.get("homeTeam") or "")
        away = str(event.get("awayTeam") or "")
        start = str(event.get("startDate") or "")
        for line in event.get("lines") or []:
            book = str(line.get("provider") or "")
            home_ml = line.get("homeMoneyline")
            away_ml = line.get("awayMoneyline")
            spread = line.get("spread")
            total = line.get("overUnder")
            status = "QUOTED"
            if home_ml is None and away_ml is None and spread is None and total is None:
                status = "MISSING"
            quote = {
                "provider": "CollegeFootballData",
                "sportsbook": book,
                "provider_event_id": event_id,
                "market_type": "CFBD_LINE_BUNDLE",
                "home_source_identity": home,
                "away_source_identity": away,
                "home_normalized_name_key": normalize_name_key(home),
                "away_normalized_name_key": normalize_name_key(away),
                "orientation": "PROVIDER_HOME_AWAY",
                "provider_kickoff_utc": start,
                "capture_timestamp_utc": captured_at_utc,
                "raw_response_sha256": raw_sha256,
                "home_spread": spread,
                "home_spread_price": None,
                "home_moneyline": home_ml,
                "away_moneyline": away_ml,
                "total": total,
                "over_price": None,
                "under_price": None,
                "quote_status": status,
                "source_freshness": "EARLY_MARKET",
                "suspended_closed_missing": status,
            }
            quote["devig"] = multiplicative_devig(
                home_ml,
                away_ml,
                same_book=True,
                same_snapshot=True,
            )
            quote["market_expected_home_margin"] = (
                home_expected_margin_from_home_handicap(spread)
            )
            quote["row_identity"] = stable_hash(quote)
            quotes.append(quote)
    return quotes


def crosswalk_quotes(
    *,
    quotes: Sequence[Mapping[str, Any]],
    contests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    contest_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for contest in contests:
        key = (
            str(contest["home_normalized_name_key"]),
            str(contest["away_normalized_name_key"]),
        )
        contest_index.setdefault(key, []).append(dict(contest))
    matched: list[dict[str, Any]] = []
    unmatched_quotes: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    quarantines: list[dict[str, Any]] = []
    used_events: dict[str, str] = {}
    for quote in quotes:
        if quote.get("quote_status") in {"SUSPENDED", "CLOSED"}:
            quarantines.append(
                {"reason": "STALE_OR_SUSPENDED_QUOTE", "quote": quote["row_identity"]}
            )
            continue
        kickoff = str(quote.get("provider_kickoff_utc") or "")
        capture = str(quote.get("capture_timestamp_utc") or "")
        if kickoff and capture and capture >= kickoff:
            quarantines.append(
                {
                    "reason": "POST_KICKOFF_QUOTE_PRESENTED_AS_PREGAME",
                    "quote": quote["row_identity"],
                }
            )
            continue
        key = (
            str(quote["home_normalized_name_key"]),
            str(quote["away_normalized_name_key"]),
        )
        reversed_key = (key[1], key[0])
        if reversed_key in contest_index and key not in contest_index:
            quarantines.append(
                {
                    "reason": "HOME_AWAY_SWAP_OR_REVERSED_TEAMS",
                    "quote": quote["row_identity"],
                }
            )
            continue
        candidates = contest_index.get(key, [])
        if not candidates:
            unmatched_quotes.append(dict(quote, match_state="UNMATCHED_PROVIDER_EVENT"))
            continue
        date_ok = []
        for contest in candidates:
            official = str(contest.get("official_kickoff_utc") or "")
            if official[:10] == kickoff[:10] or not kickoff or not official:
                date_ok.append(contest)
        if not date_ok:
            quarantines.append(
                {"reason": "KICKOFF_MISMATCH", "quote": quote["row_identity"]}
            )
            continue
        if len(date_ok) != 1:
            conflicts.append(
                {
                    "reason": "DUPLICATE_CONFLICTING_EVENTS",
                    "quote": quote["row_identity"],
                    "contest_identities": [
                        item["contest_identity"] for item in date_ok
                    ],
                }
            )
            continue
        contest = date_ok[0]
        event_key = f"{quote['provider']}:{quote['provider_event_id']}"
        previous = used_events.get(event_key)
        if previous and previous != contest["contest_identity"]:
            conflicts.append(
                {
                    "reason": "ONE_PROVIDER_EVENT_MATCHED_TO_MULTIPLE_CANONICAL_CONTESTS",
                    "provider_event_id": quote["provider_event_id"],
                }
            )
            continue
        used_events[event_key] = contest["contest_identity"]
        bound = {
            **quote,
            "contest_identity": contest["contest_identity"],
            "ncaa_contest_id": contest["ncaa_contest_id"],
            "match_state": "STRONG_IDENTITY",
            "orientation_proof": {
                "home_name_key": key[0],
                "away_name_key": key[1],
                "canonical_home_name_key": contest["home_normalized_name_key"],
                "canonical_away_name_key": contest["away_normalized_name_key"],
                "kickoff_date_home": (
                    kickoff[:10],
                    str(contest.get("official_kickoff_utc") or "")[:10],
                ),
            },
        }
        bound["row_identity"] = stable_hash(bound)
        matched.append(bound)
    matched_contests = {row["contest_identity"] for row in matched}
    missing = [
        contest
        for contest in contests
        if contest["contest_identity"] not in matched_contests
    ]
    return {
        "matched": matched,
        "unmatched_provider_events": unmatched_quotes,
        "week1_contests_with_no_market": missing,
        "conflicts": conflicts,
        "quarantines": quarantines,
    }


def contest_universe(
    *,
    kickoff_rows: Sequence[Mapping[str, Any]],
    early_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_contest: dict[str, dict[str, Any]] = {}
    for row in kickoff_rows:
        by_contest[str(row["contest_identity"])] = {
            "contest_identity": row["contest_identity"],
            "ncaa_contest_id": row["ncaa_contest_id"],
            "home_normalized_name_key": row["home_normalized_name_key"],
            "away_normalized_name_key": row["away_normalized_name_key"],
            "official_kickoff_utc": row.get("official_kickoff_utc"),
            "kickoff_confirmation_state": row.get("kickoff_confirmation_state"),
        }
    for row in early_rows:
        contest = by_contest.setdefault(
            str(row["contest_identity"]),
            {
                "contest_identity": row["contest_identity"],
                "ncaa_contest_id": row["ncaa_contest_id"],
            },
        )
        contest["home_canonical_team_id"] = row.get("home_canonical_team_id")
        contest["away_canonical_team_id"] = row.get("away_canonical_team_id")
        contest["home_source_team_id"] = row.get("home_source_team_id")
        contest["away_source_team_id"] = row.get("away_source_team_id")
    return sorted(by_contest.values(), key=lambda item: str(item["contest_identity"]))


def pair_successor_scores(
    score_rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    paired: dict[tuple[str, str], dict[str, Any]] = {}
    by_contest: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in score_rows:
        by_contest.setdefault(
            (row["candidate_id"], row["contest_identity"]), []
        ).append(row)
    for key, rows in by_contest.items():
        home = next((row for row in rows if row["site_orientation"] == "HOME"), None)
        away = next((row for row in rows if row["site_orientation"] == "AWAY"), None)
        if home is None:
            continue
        paired[key] = {
            "home": home,
            "away": away,
            "probability_home": home.get("probability"),
            "expected_margin_home": home.get("expected_margin"),
            "readiness_state": home.get("readiness_state"),
        }
    return paired


def adequacy_state(
    *,
    model: Mapping[str, Any],
    market: Mapping[str, Any] | None,
    thresholds: Mapping[str, Any],
    cycle24_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    readiness = str(model.get("readiness_state") or "")
    if readiness == ABSTAIN_ENTITY or readiness.endswith("UNSUPPORTED_ENTITY"):
        return {
            "state": ABSTAIN_ENTITY,
            "reasons": ["UNSUPPORTED_ENTITY"],
            "threshold_class": "DESCRIPTIVE_OPERATIONAL_ONLY",
        }
    if readiness.endswith("MISSING_REQUIRED_FEATURES") or readiness == ABSTAIN_FEATURES:
        return {
            "state": ABSTAIN_FEATURES,
            "reasons": ["MISSING_REQUIRED_FEATURES"],
            "threshold_class": "DESCRIPTIVE_OPERATIONAL_ONLY",
        }
    if readiness.endswith("FEATURE_AUTHORITY_MISMATCH"):
        return {
            "state": ABSTAIN_AUTHORITY,
            "reasons": ["FEATURE_AUTHORITY_MISMATCH"],
            "threshold_class": "DESCRIPTIVE_OPERATIONAL_ONLY",
        }
    probability = model.get("probability_home")
    if probability is not None:
        if float(probability) < float(thresholds["saturation_low"]) or float(
            probability
        ) > float(thresholds["saturation_high"]):
            reasons.append("PROBABILITY_SATURATION")
    if (
        cycle24_row
        and cycle24_row.get("staleness_state") == "LIMITED_STALE_INPUT_SHADOW_ONLY"
    ):
        reasons.append("STALE_PRIOR")
    if market is None or market.get("label") == "INSUFFICIENT_MARKET_COVERAGE":
        state = MARKET_UNAVAILABLE if not reasons else LIMITED
        if market is None or market.get("label") == "INSUFFICIENT_MARKET_COVERAGE":
            reasons.append("MISSING_MARKET_BENCHMARK")
        return {
            "state": LIMITED
            if "STALE_PRIOR" in reasons and MARKET_UNAVAILABLE not in [state]
            else (LIMITED if "STALE_PRIOR" in reasons else MARKET_UNAVAILABLE),
            "reasons": reasons,
            "threshold_class": "DESCRIPTIVE_OPERATIONAL_ONLY",
        }
    market_p = market.get("median_devigged_home")
    market_m = market.get("median_home_margin")
    if probability is not None and market_p is not None:
        if (float(probability) - 0.5) * (float(market_p) - 0.5) < 0:
            reasons.append("FAVORITE_DIRECTION_DISAGREEMENT")
        gap = abs(float(probability) - float(market_p))
        if gap >= float(thresholds["probability_gap_review_abs"]):
            reasons.append("MODEL_MARKET_PROBABILITY_GAP")
    margin = model.get("expected_margin_home")
    if margin is not None and market_m is not None:
        if abs(float(margin) - float(market_m)) >= float(
            thresholds["margin_gap_review_abs"]
        ):
            reasons.append("MODEL_MARKET_MARGIN_GAP")
    if (
        "FAVORITE_DIRECTION_DISAGREEMENT" in reasons
        or "MODEL_MARKET_PROBABILITY_GAP" in reasons
        or "MODEL_MARKET_MARGIN_GAP" in reasons
    ):
        state = REVIEW_DISAGREE
    elif "PROBABILITY_SATURATION" in reasons:
        state = REVIEW_SATURATION
    elif "STALE_PRIOR" in reasons:
        state = LIMITED
    else:
        state = ADEQUATE
    return {
        "state": state,
        "reasons": reasons,
        "threshold_class": "DESCRIPTIVE_OPERATIONAL_ONLY",
    }


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
    captured_at_utc: str,
    live_acquire: bool,
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    registry = read_json(repo_root / REGISTRY_RELATIVE)
    freeze_gate = require_freeze(repo_root)
    freeze = freeze_gate["pre_market_model_freeze"]
    if captured_at_utc <= str(freeze["issued_at_utc"]):
        raise MarketBenchmarkViolation(
            "market capture timestamp is not after PRE_MARKET_MODEL_FREEZE"
        )
    env_file = dotenv_path(repo_root)
    credentials = {
        "CFBD_API_KEY": credential_presence(env_file, "CFBD_API_KEY"),
        "ODDS_API_KEY": credential_presence(env_file, "ODDS_API_KEY"),
        "SCRAPFLY_API_TOKEN": credential_presence(env_file, "SCRAPFLY_API_TOKEN"),
        "SCRAPERAPI_API_TOKEN": credential_presence(env_file, "SCRAPERAPI_API_TOKEN"),
        "dotenv_path_exists": env_file.is_file(),
        "dotenv_path_recorded": str(env_file),
        "secret_values_recorded": False,
    }
    early_gate = read_json(
        repo_root / "artifacts/forecast/week1_2026_early_forecast_adequacy_gate.json"
    )
    authority_gate = read_json(
        repo_root / "artifacts/authority/week1_2026_authority_enrichment_gate.json"
    )
    kickoff_rows = payload_rows(
        data_root, authority_gate, "week1_2026_kickoff_authority_rows.jsonl"
    )
    early_rows = payload_rows(
        data_root, early_gate, "week1_2026_early_forecast_rows.jsonl"
    )
    contests = contest_universe(kickoff_rows=kickoff_rows, early_rows=early_rows)
    successor_scores = canonical_payload_rows(
        data_root,
        FREEZE_PAYLOAD_SLUG,
        freeze_gate["dataset_identity"],
        "week1_2026_c25_successor_score_rows.jsonl",
    )
    successor_features = canonical_payload_rows(
        data_root,
        FREEZE_PAYLOAD_SLUG,
        freeze_gate["dataset_identity"],
        "week1_2026_c25_successor_feature_rows.jsonl",
    )
    suite_gate = read_json(
        repo_root / "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
    )
    parameter_rows = payload_rows(
        data_root, suite_gate, "week1_2026_forecast_fitted_parameter_rows.jsonl"
    )
    ridge_params = next(
        row
        for row in parameter_rows
        if row["parameter_set_id"] == "NATIONAL_MARGIN_RIDGE_BETA"
    )
    early_contract = read_json(
        repo_root / "configs/week1_2026_early_forecast_adequacy_contract.json"
    )
    saturation = freeze["diagnostic_thresholds"]
    ridge_coherence_rows = []
    for row in early_rows:
        if row.get("candidate_id") != "national_margin_ridge":
            continue
        if row.get("row_state") != "FORECAST_FROZEN":
            continue
        audit = audit_cycle24_ridge_forecast_row(
            row,
            residual_stdev=float(ridge_params["training_residual_stdev"]),
            logistic_link_scale_divisor=float(
                ridge_params["logistic_link_scale_divisor"]
            ),
            normal_quantile=float(early_contract["uncertainty"]["normal_quantile"]),
            saturation_low=float(saturation["saturation_low"]),
            saturation_high=float(saturation["saturation_high"]),
        )
        audit["row_identity"] = stable_hash(audit)
        ridge_coherence_rows.append(audit)
    ridge_coherence_by_identity = {
        row["forecast_row_identity"]: row for row in ridge_coherence_rows
    }

    capture_dir = data_root / "raw" / "cycle25_early_market" / "cfbd_lines"
    capture_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(capture_dir.glob("sha256_*.json"))
    receipts = sorted(capture_dir.glob("redacted_*.json"))
    cfbd: dict[str, Any]
    if existing:
        raw_path = existing[-1]
        raw = raw_path.read_bytes()
        rows = json.loads(raw.decode("utf-8"))
        cfbd = {
            "route": "CFBD-GetLines",
            "disposition": "STRUCTURED_ROWS_CAPTURED",
            "credential_presence": credentials["CFBD_API_KEY"],
            "public_uri": "https://api.collegefootballdata.com/lines",
            "rows": rows if isinstance(rows, list) else [],
            "raw_bytes": raw,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_path": str(raw_path),
            "replayed": True,
        }
    elif receipts:
        receipt_path = receipts[-1]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        cfbd = {
            "route": "CFBD-GetLines",
            "disposition": "QUOTA_EXHAUSTED_429_RECEIPT_PRESERVED",
            "credential_presence": credentials["CFBD_API_KEY"],
            "public_uri": receipt.get("public_uri"),
            "rows": [],
            "raw_sha256": receipt.get("body_sha256"),
            "raw_path": str(receipt_path),
            "receipt": receipt,
            "retry_attempted_after_known_exhaustion": False,
            "replayed": True,
        }
    elif live_acquire:
        cfbd = acquire_cfbd_lines(
            env_file=env_file,
            parameters=contract["cfbd_lines_parameters"],
            captured_at_utc=captured_at_utc,
        )
        if cfbd.get("raw_bytes"):
            raw_path = capture_dir / f"sha256_{cfbd['raw_sha256']}.json"
            _write_bytes(raw_path, cfbd["raw_bytes"])
            cfbd["raw_path"] = str(raw_path)
        elif cfbd.get("receipt"):
            receipt_path = capture_dir / f"redacted_{cfbd['raw_sha256']}.json"
            _write_bytes(receipt_path, canonical_json_bytes(cfbd["receipt"]) + b"\n")
            cfbd["raw_path"] = str(receipt_path)
    else:
        cfbd = {
            "route": "CFBD-GetLines",
            "disposition": "STRUCTURED_ROUTE_NOT_ACQUIRED_IN_THIS_PASS",
            "credential_presence": credentials["CFBD_API_KEY"],
            "rows": [],
            "raw_sha256": None,
            "raw_path": None,
        }

    odds_presence = credentials["ODDS_API_KEY"]
    odds_disposition = {
        "route": "THE-ODDS-API-ODDS",
        "disposition": "CREDENTIAL_ABSENT_ROUTE_NOT_ATTEMPTED"
        if odds_presence != "PRESENT"
        else "PRESENT_BUT_UNREGISTERED_IN_GLOBAL_SOURCE_ACQUISITION_REGISTRY",
        "credential_presence": odds_presence,
        "fallback_reason": None,
    }
    structured_unavailable = cfbd.get(
        "disposition"
    ) != "STRUCTURED_ROWS_CAPTURED" and not cfbd.get("rows")
    scrapfly = credentials["SCRAPFLY_API_TOKEN"]
    scraperapi = credentials["SCRAPERAPI_API_TOKEN"]
    fallback = {
        "route": "PUBLIC-PAGE-CAPTURE",
        "disposition": "NOT_USED",
        "structured_route_unavailable": structured_unavailable,
        "why_structured_unavailable": cfbd.get("disposition"),
        "credential_presence": {
            "SCRAPFLY_API_TOKEN": scrapfly,
            "SCRAPERAPI_API_TOKEN": scraperapi,
        },
        "used": False,
        "reason": "Structured CFBD route was attempted first; web fallback is not used merely because it is convenient, and no explicit public sportsbook URL is authorized beyond the structured attempt disposition.",
    }
    if structured_unavailable and scrapfly != "PRESENT" and scraperapi != "PRESENT":
        fallback["disposition"] = "WEB_FALLBACK_CREDENTIALS_ABSENT"

    quotes = parse_cfbd_quotes(
        cfbd.get("rows") or [],
        captured_at_utc=captured_at_utc,
        raw_sha256=cfbd.get("raw_sha256"),
    )
    walk = crosswalk_quotes(quotes=quotes, contests=contests)
    by_contest_quotes: dict[str, list[dict[str, Any]]] = {}
    for quote in walk["matched"]:
        by_contest_quotes.setdefault(quote["contest_identity"], []).append(quote)
    consensus_rows = []
    for contest in contests:
        contest_quotes = by_contest_quotes.get(contest["contest_identity"], [])
        consensus = consensus_from_books(
            contest_quotes,
            minimum_books=int(contract["consensus_minimum_independent_books"]),
        )
        margins = [
            quote["market_expected_home_margin"]
            for quote in contest_quotes
            if quote.get("market_expected_home_margin") is not None
        ]
        consensus["median_home_margin"] = (
            round(sorted(margins)[len(margins) // 2], 10) if margins else None
        )
        consensus["contest_identity"] = contest["contest_identity"]
        consensus["ncaa_contest_id"] = contest["ncaa_contest_id"]
        consensus["quote_count"] = len(contest_quotes)
        consensus["row_identity"] = stable_hash(consensus)
        consensus_rows.append(consensus)

    thresholds = freeze["diagnostic_thresholds"]
    paired = pair_successor_scores(successor_scores)
    cycle24_by = {
        (row["candidate_id"], row["contest_identity"]): row for row in early_rows
    }
    market_by = {row["contest_identity"]: row for row in consensus_rows}
    adequacy_rows = []
    for (candidate_id, contest_identity), pair in paired.items():
        predecessor = candidate_id.replace("_c25_input_bound", "")
        cycle24 = cycle24_by.get((predecessor, contest_identity))
        decision = adequacy_state(
            model=pair,
            market=market_by.get(contest_identity),
            thresholds=thresholds,
            cycle24_row=cycle24,
        )
        row = {
            "candidate_id": candidate_id,
            "contest_identity": contest_identity,
            "probability_home": pair.get("probability_home"),
            "expected_margin_home": pair.get("expected_margin_home"),
            "market_label": (market_by.get(contest_identity) or {}).get("label"),
            "market_devigged_home": (market_by.get(contest_identity) or {}).get(
                "median_devigged_home"
            ),
            "market_expected_home_margin": (market_by.get(contest_identity) or {}).get(
                "median_home_margin"
            ),
            "adequacy_state": decision["state"],
            "reasons": decision["reasons"],
            "threshold_class": decision["threshold_class"],
            "independent_probability_replaced_by_market": False,
            "a_and_m_adjustment_applied": False,
        }
        row["row_identity"] = stable_hash(row)
        adequacy_rows.append(row)

    focus = next(
        contest
        for contest in contests
        if contest.get("home_normalized_name_key") == FOCUS_HOME_KEY
        and contest.get("away_normalized_name_key") == FOCUS_AWAY_KEY
    )
    focus_cycle24 = [
        row
        for row in early_rows
        if row["contest_identity"] == focus["contest_identity"]
    ]
    focus_successor = [
        row
        for row in successor_scores
        if row["contest_identity"] == focus["contest_identity"]
        and row["site_orientation"] == "HOME"
    ]
    focus_features = [
        row
        for row in successor_features
        if row["contest_identity"] == focus["contest_identity"]
        and row["site_orientation"] == "HOME"
    ]
    focus_market = market_by[focus["contest_identity"]]
    packet = {
        "contest_identity": focus["contest_identity"],
        "ncaa_contest_id": focus["ncaa_contest_id"],
        "discovered_from_authoritative_universe": True,
        "hardcoded_contest_id": False,
        "home_normalized_name_key": FOCUS_HOME_KEY,
        "away_normalized_name_key": FOCUS_AWAY_KEY,
        "official_kickoff_utc": focus.get("official_kickoff_utc"),
        "immutable_fifty_percent_control": next(
            (
                {
                    "candidate_id": row["candidate_id"],
                    "probability_home": row["probability_home"],
                    "row_state": row["row_state"],
                }
                for row in focus_cycle24
                if row["candidate_id"] == "national_base_rate"
            ),
            None,
        ),
        "immutable_historical_elo_evidence": next(
            (
                {
                    "candidate_id": row["candidate_id"],
                    "probability_home": row["probability_home"],
                    "row_state": row["row_state"],
                }
                for row in focus_cycle24
                if row["candidate_id"] == "national_elo"
            ),
            None,
        ),
        "cycle24_early_forecasts": [
            {
                "candidate_id": row["candidate_id"],
                "probability_home": row["probability_home"],
                "expected_margin_home": row.get("expected_margin_home"),
                "margin_interval_home": row.get("margin_interval_home"),
                "adequacy_verdict": row.get("adequacy_verdict"),
                "row_state": row["row_state"],
                "forecast_row_identity": row["forecast_row_identity"],
                "tamu_specific_adjustment_applied": row.get(
                    "tamu_specific_adjustment_applied"
                ),
                "cycle24_ridge_distribution_state": (
                    ridge_coherence_by_identity.get(row["forecast_row_identity"]) or {}
                ).get("adequacy_state"),
            }
            for row in focus_cycle24
        ],
        "cycle24_national_margin_ridge_coherence": next(
            (
                ridge_coherence_by_identity[row["forecast_row_identity"]]
                for row in focus_cycle24
                if row["candidate_id"] == "national_margin_ridge"
                and row["forecast_row_identity"] in ridge_coherence_by_identity
            ),
            None,
        ),
        "corrective_successors": focus_successor,
        "consumed_features": [
            {
                "source_team_id": row["source_team_id"],
                "ranking_surface_state": row["ranking_surface_state"],
                "effective_ranking_authority": row["effective_ranking_authority"],
                "effective_strength_prior_admission": row[
                    "effective_strength_prior_admission"
                ],
                "historical_prior_outcome_analogue_bound": row[
                    "historical_prior_outcome_analogue_bound"
                ],
                "opening_rating": row.get("opening_rating"),
                "prior_win_rate": (row.get("feature_values") or {}).get(
                    "prior_win_rate"
                ),
                "ap_poll_rank": (row.get("feature_values") or {}).get("ap_poll_rank"),
            }
            for row in focus_features
        ],
        "market": focus_market,
        "roughly_40_point_spread_assumed": False,
        "independent_probability_replaced_by_market": False,
        "a_and_m_adjustment_applied": False,
        "chatgpt_transcript_used_as_source_authority": False,
        "approximate_market_line_from_transcript_used": False,
        "t_minus_24h_state": "OPEN",
        "t_minus_90m_state": "OPEN",
        "bas_claim": False,
        "bas_predicted_score_authorized": False,
        "bas_predicted_score": None,
        "hybrid_visualization": {
            "label": "HYBRID_VISUALIZATION_NOT_A_BAS_SCORE",
            "bas_margin_plus_market_total_computed": False,
            "reason": (
                "No nationally trained total-points or team-score model satisfies "
                "a pre-market-frozen contract, so no BAS predicted score is emitted."
            ),
        },
    }
    packet["packet_identity"] = stable_hash(packet)

    national = {
        "week1_contest_count": len(contests),
        "market_covered_count": sum(
            1 for row in consensus_rows if row["quote_count"] > 0
        ),
        "market_missing_count": sum(
            1 for row in consensus_rows if row["quote_count"] == 0
        ),
        "quote_count": len(quotes),
        "matched_quote_count": len(walk["matched"]),
        "consensus_count": sum(
            1 for row in consensus_rows if row["label"] == "MARKET_CONSENSUS"
        ),
        "single_source_count": sum(
            1
            for row in consensus_rows
            if row["label"] == "SINGLE_SOURCE_MARKET_REFERENCE"
        ),
        "insufficient_coverage_count": sum(
            1
            for row in consensus_rows
            if row["label"] == "INSUFFICIENT_MARKET_COVERAGE"
        ),
        "adequacy_counts": {},
        "cycle24_forecast_coverage": len(early_rows),
        "directional_disagreement_count": sum(
            1
            for row in adequacy_rows
            if "FAVORITE_DIRECTION_DISAGREEMENT" in row["reasons"]
        ),
        "saturation_count": sum(
            1 for row in adequacy_rows if "PROBABILITY_SATURATION" in row["reasons"]
        ),
        "cycle24_ridge_incoherence_count": sum(
            1
            for row in ridge_coherence_rows
            if row["adequacy_state"] == REVIEW_INCOHERENCE
        ),
        "cycle24_ridge_frozen_count": len(ridge_coherence_rows),
        "authority_mismatch_count": sum(
            1 for row in adequacy_rows if row["adequacy_state"] == ABSTAIN_AUTHORITY
        ),
        "t_minus_24h_state": "OPEN",
        "t_minus_90m_state": "OPEN",
    }
    for row in adequacy_rows:
        national["adequacy_counts"][row["adequacy_state"]] = (
            national["adequacy_counts"].get(row["adequacy_state"], 0) + 1
        )

    dataset_identity = stable_hash(
        {
            "quotes": [row["row_identity"] for row in quotes],
            "matched": [row["row_identity"] for row in walk["matched"]],
            "consensus": [row["row_identity"] for row in consensus_rows],
            "adequacy": [row["row_identity"] for row in adequacy_rows],
            "cycle24_ridge_coherence": [
                row["row_identity"] for row in ridge_coherence_rows
            ],
            "packet": packet["packet_identity"],
            "cfbd_disposition": cfbd.get("disposition"),
            "cfbd_raw_sha256": cfbd.get("raw_sha256"),
        }
    )
    return {
        "contract": contract,
        "registry": registry,
        "freeze_gate": freeze_gate,
        "credentials": credentials,
        "cfbd": {
            key: value
            for key, value in cfbd.items()
            if key != "raw_bytes" and key != "rows"
        },
        "odds_disposition": odds_disposition,
        "fallback": fallback,
        "quotes": quotes,
        "crosswalk": walk,
        "consensus_rows": consensus_rows,
        "adequacy_rows": adequacy_rows,
        "ridge_coherence_rows": ridge_coherence_rows,
        "packet": packet,
        "national": national,
        "contests": contests,
        "dataset_identity": dataset_identity,
        "captured_at_utc": captured_at_utc,
        "code_identity": sha256_file(
            repo_root
            / "src/aggie_analytics/data/week1_2026_market_benchmark_and_adequacy.py"
        ),
        "early_rows": early_rows,
        "cfbd_rows": cfbd.get("rows") or [],
    }


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    captured_at_utc: str,
    live_acquire: bool,
) -> dict[str, Any]:
    expected = build_expected(
        repo_root=repo_root,
        data_root=data_root,
        captured_at_utc=captured_at_utc,
        live_acquire=live_acquire,
    )
    identity = expected["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    payloads = []
    for name, role, rows in (
        (
            "week1_2026_early_market_quotes.jsonl",
            "EARLY_MARKET_QUOTES",
            expected["quotes"],
        ),
        (
            "week1_2026_early_market_crosswalk_matched.jsonl",
            "EARLY_MARKET_CROSSWALK_MATCHED",
            expected["crosswalk"]["matched"],
        ),
        (
            "week1_2026_early_market_consensus.jsonl",
            "EARLY_MARKET_CONSENSUS",
            expected["consensus_rows"],
        ),
        (
            "week1_2026_c25_forecast_adequacy_rows.jsonl",
            "CYCLE25_FORECAST_ADEQUACY",
            expected["adequacy_rows"],
        ),
        (
            "week1_2026_cycle24_ridge_distribution_coherence.jsonl",
            "CYCLE24_RIDGE_DISTRIBUTION_COHERENCE",
            expected["ridge_coherence_rows"],
        ),
        (
            "week1_2026_c25_a_and_m_packet.jsonl",
            "CYCLE25_A_AND_M_PACKET",
            [expected["packet"]],
        ),
    ):
        payload = jsonl_bytes(rows)
        _write_bytes(canonical_root / name, payload)
        payloads.append(
            {
                "name": name,
                "role": role,
                "rows": len(rows),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    gate = {
        "artifact_type": "WEEK1_2026_MARKET_BENCHMARK_AND_ADEQUACY_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "decision_unit": LOCAL_ISSUE_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "issued_at_utc": captured_at_utc,
        "snapshot_id": "EARLY_MARKET",
        "dataset_identity": identity,
        "code_identity": expected["code_identity"],
        "pre_market_model_freeze_identity": expected["freeze_gate"][
            "pre_market_model_freeze"
        ]["freeze_identity"],
        "credentials": expected["credentials"],
        "cfbd": expected["cfbd"],
        "odds_disposition": expected["odds_disposition"],
        "web_fallback": expected["fallback"],
        "national": expected["national"],
        "focus_packet_identity": expected["packet"]["packet_identity"],
        "payloads": payloads,
        "scientific_nonclaims": expected["contract"]["scientific_nonclaims"],
        "checkpoints": expected["contract"]["checkpoints"],
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
        },
        "cycle24_preservation": {
            "early_forecast_row_count": len(expected["early_rows"]),
            "rewritten": False,
        },
    }
    seal_identities(gate)
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"gate": gate, "expected": expected}


def validate_artifact(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    gate = read_json(repo_root / GATE_RELATIVE)
    expected = build_expected(
        repo_root=repo_root,
        data_root=data_root,
        captured_at_utc=str(gate["issued_at_utc"]),
        live_acquire=False,
    )
    if gate.get("dataset_identity") != expected["dataset_identity"]:
        raise MarketBenchmarkViolation("market dataset identity drifted")
    if gate["checkpoints"]["t_minus_24h_state"] != "OPEN":
        raise MarketBenchmarkViolation("T-24H is not OPEN")
    if gate["checkpoints"]["t_minus_90m_state"] != "OPEN":
        raise MarketBenchmarkViolation("T-90M is not OPEN")
    if gate["scientific_nonclaims"]["market_enters_model_fitting"]:
        raise MarketBenchmarkViolation("market entered model fitting")
    if gate["scientific_nonclaims"]["roughly_40_point_spread_assumed"]:
        raise MarketBenchmarkViolation("40-point spread was assumed")
    if gate["cycle24_preservation"]["rewritten"]:
        raise MarketBenchmarkViolation("Cycle #24 forecasts were rewritten")
    packet = expected["packet"]
    ridge = packet.get("cycle24_national_margin_ridge_coherence") or {}
    if ridge.get("adequacy_state") != REVIEW_INCOHERENCE:
        raise MarketBenchmarkViolation(
            "Cycle #24 A&M ridge was not classified as probability/interval incoherence"
        )
    if ridge.get("cycle24_row_rewritten"):
        raise MarketBenchmarkViolation("Cycle #24 ridge row was rewritten")
    if packet.get("bas_predicted_score") is not None:
        raise MarketBenchmarkViolation("unauthorized BAS predicted score was emitted")
    if packet.get("chatgpt_transcript_used_as_source_authority"):
        raise MarketBenchmarkViolation("ChatGPT transcript used as market source")
    return {
        "result": "PASS",
        "gate_identity": gate["gate_identity"],
        "dataset_identity": gate["dataset_identity"],
        "national": gate["national"],
        "cfbd_disposition": gate["cfbd"]["disposition"],
    }
