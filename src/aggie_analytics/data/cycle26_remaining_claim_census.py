"""Enumerate remaining all-cycle material claims instead of one blob per cycle.

Pass-two COMPLETE still requires independent reconstruction of every remaining
item. Named complete-data checks that already have independent reconstruction
are recorded here without conferring whole-cycle SEMANTICALLY_AUDITED.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aggie.data.cycle26_remaining_claim_census.v1"
CONTRACT_ID = "CYCLE26-REMAINING-CLAIM-CENSUS-V1"
JIRA_KEY = "BAT-691"
LOCAL_ISSUE_ID = "POST-TASK-ALL-CYCLE-REMAINING-CLAIM-CENSUS-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "REMAINING_MATERIAL_CLAIM_CENSUS_NOT_SEMANTICALLY_AUDITED"
PASS_RESULT = "PASS_REMAINING_CLAIM_CENSUS_ENUMERATED"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_REMAINING_CLAIM_CENSUS.json"
)
COVERAGE_AUTHORITY = (
    "C:/BatteredAggieSyndrome.data/ops/cycle26/ALL_CYCLE_RECHECK_COVERAGE.md"
)

NOT_AUDITED_YET = "NOT_AUDITED_YET"
NAMED_CHECK_RECONSTRUCTED = "RECONSTRUCTED_NAMED_CHECK_NOT_WHOLE_CYCLE"
FAIL = "FAIL"

# One remaining material claim per coverage-table row, plus named complete-data
# checks. This is the expected census; it is not a completed reconstruction.
REMAINING_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "claim_id": "C01-CAPTURE-SEMANTIC-REPLAY-AND-OWNERSHIP",
        "cycle_id": "CYCLE-1",
        "status": NOT_AUDITED_YET,
        "remaining": "Capture semantic replay and every ownership/acceptance claim.",
    },
    {
        "claim_id": "C02-INCIDENT-CHRONOLOGY-AND-RESTORE",
        "cycle_id": "CYCLE-2",
        "status": NOT_AUDITED_YET,
        "remaining": "Incident chronology and all restore evidence.",
    },
    {
        "claim_id": "C03-MOUNTED-14-SCENARIO-AND-LEAKAGE",
        "cycle_id": "CYCLE-3",
        "status": NOT_AUDITED_YET,
        "remaining": "Full mounted 14-scenario battery and every early leakage claim.",
    },
    {
        "claim_id": "C04-FEATURE-LABEL-FIT-EXPOSURE",
        "cycle_id": "CYCLE-4",
        "status": NOT_AUDITED_YET,
        "remaining": "All feature/label rows, fitted parameters and historical exposures.",
    },
    {
        "claim_id": "C05-ORIGINAL-OUTPUTS-AND-CLAIMS",
        "cycle_id": "CYCLE-5",
        "status": NOT_AUDITED_YET,
        "remaining": "Original materialized outputs and every scientific claim.",
    },
    {
        "claim_id": "C06-RANKING-METRIC-ROSTER-LINEAGE",
        "cycle_id": "CYCLE-6",
        "status": NOT_AUDITED_YET,
        "remaining": "All ranking/metric/roster populations and lineage.",
    },
    {
        "claim_id": "C07-2010-11-CAPTURE-CENSUS",
        "cycle_id": "CYCLE-7",
        "status": NOT_AUDITED_YET,
        "remaining": "Full 2010-11 capture census and joins.",
    },
    {
        "claim_id": "C08-ALIAS-PAGE-SOURCE-MATCH",
        "cycle_id": "CYCLE-8",
        "status": NOT_AUDITED_YET,
        "remaining": "Every alias, page and source match.",
    },
    {
        "claim_id": "C09-ORIGINAL-UNION-GENERATION",
        "cycle_id": "CYCLE-9",
        "status": NOT_AUDITED_YET,
        "remaining": "Complete original union generation.",
    },
    {
        "claim_id": "C10-METADATA-UNION-DOMAINS",
        "cycle_id": "CYCLE-10",
        "status": NOT_AUDITED_YET,
        "remaining": "Complete metadata/union and all domains.",
    },
    {
        "claim_id": "C11-PLAYER-STAT-DOMAIN-UNION",
        "cycle_id": "CYCLE-11",
        "status": NOT_AUDITED_YET,
        "remaining": "Every player/stat/domain field and enriched union.",
    },
    {
        "claim_id": "C12-2006-NON-PASSING-DOMAINS",
        "cycle_id": "CYCLE-12",
        "status": NOT_AUDITED_YET,
        "remaining": "Every other 2006 domain and admission claim.",
    },
    {
        "claim_id": "C13-2005-HTML-DOMAIN-UNION",
        "cycle_id": "CYCLE-13",
        "status": NOT_AUDITED_YET,
        "remaining": "Complete HTML/domain/union correctness.",
    },
    {
        "claim_id": "C14-2004-DOMAINS-AND-AUTHORITY",
        "cycle_id": "CYCLE-14",
        "status": NOT_AUDITED_YET,
        "remaining": "Other domains and all authority metadata.",
    },
    {
        "claim_id": "C15-2002-03-CORPUS-UNION-REJECTION",
        "cycle_id": "CYCLE-15",
        "status": NOT_AUDITED_YET,
        "remaining": "Complete corpus/union/rejection reconstruction.",
    },
    {
        "claim_id": "C16-2000-01-CORPUS-UNION-REJECTION",
        "cycle_id": "CYCLE-16",
        "status": NOT_AUDITED_YET,
        "remaining": "Complete corpus/union/rejection reconstruction.",
    },
    {
        "claim_id": "C17-1998-99-REJECTION-UNION",
        "cycle_id": "CYCLE-17",
        "status": NOT_AUDITED_YET,
        "remaining": "Original full rejection/union chains.",
    },
    {
        "claim_id": "C18-1996-97-CLAIMS-AND-MUTATION",
        "cycle_id": "CYCLE-18",
        "status": FAIL,
        "remaining": "All original 1996/97 claims, identities and mutation evidence.",
    },
    {
        "claim_id": "C19-PRESERVATION-TO-C20-MAPPING",
        "cycle_id": "CYCLE-19",
        "status": NOT_AUDITED_YET,
        "remaining": "Preservation-to-C20 integration mapping and all dirty-work claims.",
    },
    {
        "claim_id": "C20-NORMALIZED-JOIN-FIT-TRANSFORM",
        "cycle_id": "CYCLE-20",
        "status": FAIL,
        "remaining": "Every normalized/game/feature join, fold-fit/transform and peer inference.",
    },
    {
        "claim_id": "C21-ROW-PUBLICATION-AND-KNOWN-AT",
        "cycle_id": "CYCLE-21",
        "status": FAIL,
        "remaining": "Row-specific completion/publication authority and every prior contribution.",
    },
    {
        "claim_id": "C22-RAW-FINAL-FORECAST-METRIC-REPLAY",
        "cycle_id": "CYCLE-22",
        "status": NOT_AUDITED_YET,
        "remaining": "Full raw-final/forecast/metric replay in this recheck.",
    },
    {
        "claim_id": "C23-ORIGINAL-91-SCHEDULE-CELLS",
        "cycle_id": "CYCLE-23",
        "status": NOT_AUDITED_YET,
        "remaining": "All 91 original schedule/authority receipts and every domain cell.",
    },
    {
        "claim_id": "C24-ORIGINAL-399-ROW-FEATURE-PARAMETER",
        "cycle_id": "CYCLE-24",
        "status": FAIL,
        "remaining": "Every original 399 frozen row's full raw-feature-parameter trace.",
    },
    {
        "claim_id": "C25-ACQUISITION-MARKET-TRAINING-CLAIMS",
        "cycle_id": "CYCLE-25",
        "status": FAIL,
        "remaining": "Original acquisition time authenticity, every market raw join, all training/refit/parameter claims.",
    },
    {
        "claim_id": "C25_5-COMPLETE-INVENTORY-AND-RECONSTRUCTION",
        "cycle_id": "CYCLE-25.5",
        "status": NOT_AUDITED_YET,
        "remaining": "Complete inventory, all independent reconstruction, external admin configuration, original authorization/live comment, materialized scientific recovery.",
    },
    {
        "claim_id": "NAMED-NATIONAL-RAW-BYTES-990",
        "cycle_id": "CYCLE-20",
        "status": NAMED_CHECK_RECONSTRUCTED,
        "remaining": "990 manifest records independently rehashed; does not prove feature eligibility.",
    },
    {
        "claim_id": "NAMED-C20-PREDICTION-PAIR-CENSUS",
        "cycle_id": "CYCLE-20",
        "status": NAMED_CHECK_RECONSTRUCTED,
        "remaining": "9100 saved prediction rows; logistic/ridge/prior-only fail complement on all pairs.",
    },
    {
        "claim_id": "NAMED-C21-PREDICTION-PAIR-CENSUS",
        "cycle_id": "CYCLE-21",
        "status": NAMED_CHECK_RECONSTRUCTED,
        "remaining": "50350 saved prediction rows; same three models fail on every pair.",
    },
    {
        "claim_id": "NAMED-C25-SCORE-ROW-PAIR-CENSUS",
        "cycle_id": "CYCLE-25",
        "status": NAMED_CHECK_RECONSTRUCTED,
        "remaining": "910 saved successor oriented rows; three models fail complement on scorable pairs.",
    },
    {
        "claim_id": "NAMED-PASSING-SECTION-429",
        "cycle_id": "CYCLE-11",
        "status": NAMED_CHECK_RECONSTRUCTED,
        "remaining": "429 confirmed current-corpus errors on 125 raw pages; 45 screen candidates unresolved.",
    },
    {
        "claim_id": "NAMED-C03-LEAKAGE-BATTERY-14",
        "cycle_id": "CYCLE-3",
        "status": NAMED_CHECK_RECONSTRUCTED,
        "remaining": (
            "Mounted 14-scenario leakage battery independently re-executed "
            "2026-09-04T05:14:41Z; artifact_identity "
            "2be6b713722382b2c0ea5e86f89a6e6ed57533bab3adbb0bc3cf3a77b46df13a; "
            "dataset_identity "
            "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7; "
            "status DONE. Does not reconstruct every early leakage claim or "
            "complete CYCLE-3."
        ),
    },
)

ALLOWED_STATUSES = frozenset({NOT_AUDITED_YET, NAMED_CHECK_RECONSTRUCTED, FAIL})
MINIMUM_CLAIM_COUNT = 31


class RemainingClaimCensusError(ValueError):
    """Raised when the remaining-claim census is empty or mislabeled complete."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_census(claims: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> None:
    if len(claims) < MINIMUM_CLAIM_COUNT:
        raise RemainingClaimCensusError(
            "remaining claim census is below the required count"
        )
    seen: set[str] = set()
    for row in claims:
        claim_id = str(row.get("claim_id") or "")
        if not claim_id or claim_id in seen:
            raise RemainingClaimCensusError("claim_id missing or duplicated")
        seen.add(claim_id)
        status = row.get("status")
        if status not in ALLOWED_STATUSES:
            raise RemainingClaimCensusError(f"illegal remaining-claim status: {status}")
        if not row.get("remaining"):
            raise RemainingClaimCensusError(f"empty remaining text: {claim_id}")
        if (
            status == NAMED_CHECK_RECONSTRUCTED
            and str(row.get("claim_id") or "").startswith("C")
            and not str(row.get("claim_id") or "").startswith("NAMED-")
        ):
            raise RemainingClaimCensusError(
                "named-check reconstruction must not use a whole-cycle remaining ID"
            )


def build_gate(*, issued_at_utc: str) -> dict[str, Any]:
    validate_census(REMAINING_CLAIMS)
    counts: dict[str, int] = {}
    for row in REMAINING_CLAIMS:
        status = str(row["status"])
        counts[status] = counts.get(status, 0) + 1
    unreviewed = counts.get(NOT_AUDITED_YET, 0)
    failed = counts.get(FAIL, 0)
    named = counts.get(NAMED_CHECK_RECONSTRUCTED, 0)
    gate = {
        "ALL_CYCLE_SCIENTIFIC_TRUST_GATE": False,
        "artifact_type": "CYCLE26_REMAINING_CLAIM_CENSUS",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "authority_document": COVERAGE_AUTHORITY,
        "semantically_audited": False,
        "three_pass_status": "INCOMPLETE",
        "claim_count": len(REMAINING_CLAIMS),
        "status_counts": counts,
        "unreviewed_remaining_claim_count": unreviewed,
        "failed_remaining_claim_count": failed,
        "named_check_reconstructed_count": named,
        "claims": [dict(row) for row in REMAINING_CLAIMS],
        "scientific_nonclaims": [
            "Does not stamp SEMANTICALLY_AUDITED.",
            "Does not convert NOT_AUDITED_YET into PASS.",
            "Does not claim all 25 cycles audited because 25 JSON files exist.",
            "Named complete-data checks do not complete their parent cycles.",
        ],
    }
    gate["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in gate.items() if key != "gate_identity"}
        )
    )
    return gate


def materialize(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    gate = build_gate(issued_at_utc=issued_at_utc)
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(gate, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return gate
