"""The qualified audit identity of the complete per-row qualification collection (BAT-733, TP62-A01 section 4).

``None`` until the first real qualification of the fixed profile: the rules, profile and reader are frozen and
committed before any substantive real qualification output exists. A later commit pins here exactly the identity the
qualification lane observed ({rules_sha256, database_sha256, rows, lines_sha256, summary}) without changing any rule;
from then on the reader refuses a builtin-profile qualification collection that differs
(``QUALIFICATION_AUDIT_MISMATCH``).

Pinned from QUALIFY_SOURCE_ASSERTIONS run 20261020T154352516976Z at 5a86bf4b (the first real
qualification, after the contract commit; rules unchanged).
"""
from __future__ import annotations

from typing import Any

QUALIFIED_AUDIT: dict[str, Any] | None = {
    "rules_sha256": "4a99cfc76f76c45b219f47cef4dd688aa179b0911adaa2b03927746174efb96a",
    "database_sha256": "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331",
    "rows": 5079,
    "lines_sha256": "cf8975ae98f5b5a009b1ad825f86139631b7973f3f24032cd93cbdaf5ffef7d2",
    "summary": {
        "source_cells": {
            "VERIFIED_RETAINED_SOURCE_CELL": 1592,
        },
        "source_cell_fields_compared": 27940,
        "publication": {
            "PUBLICATION_TIME_UNKNOWN": 1573,
            "SOURCE_POSTING_CLAIM_WITNESSED_IN_LATER_CAPTURE": 19,
        },
        "opportunity_occurrence": {
            "EXACT_DUPLICATE_ASSERTION_OF_THE_SAME_BUSINESS_KEY": 508,
            "SINGLETON_BUSINESS_KEY": 2966,
        },
        "statements_ingested_reconciled": 3474,
        "opportunity_policy_foreign_keys_present": 1751,
        "quarantine_flag_agrees_with_identity_claim": 1592,
    },
}
