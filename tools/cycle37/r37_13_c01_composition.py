r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-13-AC03..AC07, AC10: compose the BAS-local adapter with the ACTUAL
released C01 wheel, and run positive and negative fixtures through both.

AC03 says shape-only owner-wheel probes are insufficient. The Cycle #36 tool
built synthetic documents by hand and handed them to the wheel's validator,
which proves the validator works and says nothing about whether BAS's own
adapter produces documents it accepts. This tool closes that gap: every
fixture is a BAS ``StaffAssertion`` set, it goes through
``project_to_staff_snapshot`` exactly as a caller would, and the document the
adapter emits is then handed to the released wheel's ``validate_document``.

So each fixture has two independent verdicts:

* the **BAS adapter's** -- did it project, or refuse, and why;
* the **released wheel's** -- given what the adapter emitted, does
  ``validate_document("context/StaffSnapshotV1", ...)`` accept it.

A positive fixture passes only if BOTH accept. A negative fixture passes if
EITHER refuses, and the receipt records which one caught it, because a defect
the owner schema happens to catch is still a defect in the BAS adapter.

The wheel is installed in its own interpreter and imported only there. This
tool never imports it into the process that holds BAS code, so the two stay
separable and the wheel is never modified.

Also exercised, because the same requirement names them:

* the membership consumer refusing an empty or foreign mapping (AC04);
* the lossless envelope beside the declared-lossy projection (AC05);
* a source coaching scheme refused as an F10 realized-state contract
  (AC06/AC07), checked against the contract names the wheel actually ships.

Nothing is written outside ``--out``. No owner repository is touched and no
adoption is claimed: a projection qualifying against a released schema is not
the owner accepting BAS's richer envelope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.c01_boundary import (  # noqa: E402
    BOUNDARY_VERSION,
    C01_CONTRACT,
    FIELD_MATRIX,
    LOST,
    PREDECESSOR_BOUNDARY_VERSION,
    ProjectionRefused,
    RoleScope,
    StaffAssertion,
    project_to_staff_snapshot,
    read_only_membership_consumer,
    read_only_role_consumer,
    refuse_source_scheme_as_realized_state,
)
from aggie_analytics import atomic_io as _bas_atomic

#: Runs inside the wheel's own interpreter. Reads documents on stdin, returns
#: one verdict per document on stdout. It imports nothing from BAS.
VALIDATOR = r'''
import json, sys
import cfb_intelligence_contracts as c01
documents = json.loads(sys.stdin.read())
out = []
for name, document in documents:
    try:
        c01.validate_document(name, document)
        out.append({"accepted": True})
    except Exception as error:
        out.append({"accepted": False, "error_type": type(error).__name__,
                    "error": str(error)[:300]})
catalog = c01.load_catalog()
# The catalog keys its contracts under "objects". An earlier version of this
# probe guessed "contracts"/"entries", found nothing, and silently fell back
# to a one-item default, so the F10 separation was tested against one
# contract instead of the nine the wheel ships.
contracts = sorted(str(name) for name in (catalog.get("objects") or {}))
if not contracts:
    raise SystemExit("the released catalog lists no contracts under 'objects'")
print(json.dumps({"verdicts": out, "version": c01.__version__,
                  "catalog_contracts": contracts}))
'''

CUTOFF = "2026-09-09T18:08:43Z"
KNOWN = "2026-09-01T12:00:00Z"


def assertion(**overrides: Any) -> StaffAssertion:
    """Rights-safe synthetic assertions. No real person or program."""

    base: dict[str, Any] = dict(
        assertion_id="fixture-1",
        person_id="synthetic-person-1",
        person_display_name="Synthetic Person One",
        program_id="synthetic-team-1",
        season=2026,
        roles=(RoleScope("head_coach", "TEAM", (), "PRINCIPAL"),),
        source_title="Synthetic Head Coach",
        source_system="SYNTHETIC-FIXTURE",
        evidence_refs=("synthetic://evidence/1",),
        known_at_utc=KNOWN,
        point_in_time_cutoff=CUTOFF,
    )
    base.update(overrides)
    return StaffAssertion(**base)


def second(**overrides: Any) -> StaffAssertion:
    fields: dict[str, Any] = dict(
        assertion_id="fixture-2",
        person_id="synthetic-person-2",
        roles=(RoleScope("defensive_coordinator", "DEFENSE", (), "PRINCIPAL"),),
        source_title="Synthetic Defensive Coordinator",
        evidence_refs=("synthetic://evidence/2",),
    )
    fields.update(overrides)
    return assertion(**fields)


#: (name, expectation, assertions, projection kwargs). Expectation is
#: ACCEPT (both must accept) or REJECT (either must refuse).
FIXTURES: list[tuple[str, str, list[StaffAssertion], dict[str, Any]]] = [
    ("positive_single_head_coach", "ACCEPT", [assertion()], {}),
    ("positive_two_people_one_program", "ACCEPT", [assertion(), second()], {}),
    ("positive_offset_utc_is_normalised_to_z", "ACCEPT",
     [assertion(known_at_utc="2026-09-01T12:00:00+00:00",
                point_in_time_cutoff="2026-09-09T18:08:43+00:00")], {}),
    ("positive_known_at_equal_to_cutoff", "ACCEPT",
     [assertion(known_at_utc=CUTOFF)], {}),
    ("negative_mixed_cutoffs", "REJECT",
     [assertion(), second(point_in_time_cutoff="2026-09-10T00:00:00Z")], {}),
    ("negative_one_assertion_missing_known_at", "REJECT",
     [assertion(), second(known_at_utc=None)], {}),
    ("negative_known_at_after_cutoff", "REJECT",
     [assertion(known_at_utc="2026-09-10T00:00:00Z")], {}),
    ("negative_missing_cutoff", "REJECT", [assertion(point_in_time_cutoff=None)], {}),
    ("negative_naive_timestamp", "REJECT",
     [assertion(known_at_utc="2026-09-01T12:00:00")], {}),
    ("negative_non_utc_offset", "REJECT",
     [assertion(known_at_utc="2026-09-01T07:00:00-05:00")], {}),
    ("negative_empty_evidence", "REJECT", [assertion(evidence_refs=())], {}),
    ("negative_blank_evidence_string", "REJECT", [assertion(evidence_refs=("  ",))], {}),
    ("negative_one_of_two_without_evidence", "REJECT",
     [assertion(), second(evidence_refs=())], {}),
    ("negative_missing_rights", "REJECT", [assertion(rights="")], {}),
    ("negative_missing_parent_program", "REJECT", [assertion(program_id="")], {}),
    ("negative_missing_person", "REJECT", [assertion(person_id="")], {}),
    ("negative_unresolved_conflict", "REJECT",
     [assertion(conflicts_with=("fixture-9",))], {}),
    ("negative_role_interval_conflict", "REJECT",
     [assertion(source_effective_start="2024-01-01", source_effective_end="2024-12-31"),
      assertion(assertion_id="fixture-1b", evidence_refs=("synthetic://evidence/1b",),
                source_effective_start="2025-01-01", source_effective_end="2025-12-31")], {}),
    ("negative_two_programs", "REJECT",
     [assertion(), second(program_id="synthetic-team-2")], {}),
    ("negative_empty_projection", "REJECT", [], {}),
    ("negative_invalid_object_id", "REJECT", [assertion()], {"object_id": "O"}),
    ("negative_invalid_ruleset_id", "REJECT", [assertion()], {"ruleset_id": "r"}),
    ("negative_unknown_reason_outside_enum", "REJECT",
     [assertion(unknown_reason="MADE_UP")], {}),
    ("negative_required_lost_field_roles", "REJECT", [assertion()],
     {"required_fields": ["roles"]}),
]


def run_wheel(interpreter: Path, documents: list[tuple[str, Any]]) -> dict[str, Any]:
    environment = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [str(interpreter), "-B", "-c", VALIDATOR],
        input=json.dumps(documents), capture_output=True, text=True,
        env=environment, timeout=300,
    )
    if completed.returncode != 0:
        raise SystemExit(f"wheel interpreter failed: {completed.stderr[:600]}")
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--wheel-interpreter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    wheel_digest = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
    if wheel_digest != args.wheel_sha256:
        raise SystemExit(
            f"wheel digest {wheel_digest} is not the released {args.wheel_sha256}; "
            "refusing to qualify anything against it"
        )

    cases: list[dict[str, Any]] = []
    to_validate: list[tuple[str, Any]] = []
    for name, expectation, assertions, kwargs in FIXTURES:
        call = {"object_id": "synthetic-snapshot", "ruleset_id": "synthetic-ruleset"}
        call.update(kwargs)
        case: dict[str, Any] = {"fixture": name, "expectation": expectation,
                                "assertions": len(assertions)}
        try:
            projection = project_to_staff_snapshot(assertions, **call)
            case["bas_adapter"] = "PROJECTED"
            case["document"] = projection["document"]
            case["lost_field_count"] = projection["lost_field_count"]
            case["wheel_index"] = len(to_validate)
            to_validate.append((C01_CONTRACT, projection["document"]))
        except ProjectionRefused as error:
            case["bas_adapter"] = "REFUSED"
            case["bas_reason"] = str(error)[:300]
        cases.append(case)

    wheel = run_wheel(args.wheel_interpreter, to_validate)
    for case in cases:
        index = case.pop("wheel_index", None)
        if index is None:
            case["released_wheel"] = "NOT_REACHED_BAS_REFUSED_FIRST"
        else:
            verdict = wheel["verdicts"][index]
            case["released_wheel"] = "ACCEPTED" if verdict["accepted"] else "REJECTED"
            if not verdict["accepted"]:
                case["wheel_reason"] = verdict.get("error")
        accepted_by_both = case["bas_adapter"] == "PROJECTED" and case["released_wheel"] == "ACCEPTED"
        caught_by = (
            "BAS_ADAPTER" if case["bas_adapter"] == "REFUSED"
            else "RELEASED_WHEEL_ONLY" if case["released_wheel"] == "REJECTED"
            else None
        )
        case["caught_by"] = caught_by
        case["honours_expectation"] = (
            accepted_by_both if case["expectation"] == "ACCEPT" else caught_by is not None
        )
        case.pop("document", None)

    # The adapter should catch its own defects. A negative only the owner
    # schema caught is a pass for the fixture and a finding for BAS.
    wheel_only = [c["fixture"] for c in cases if c.get("caught_by") == "RELEASED_WHEEL_ONLY"]

    # -------------------------------------------- consumer and separation
    good = project_to_staff_snapshot(
        [assertion(), second()], object_id="synthetic-snapshot", ruleset_id="synthetic-ruleset"
    )
    consumers = {
        "membership_admits_a_real_projection": read_only_membership_consumer(good)["admitted"],
        "membership_refuses_an_empty_mapping": not read_only_membership_consumer({})["admitted"],
        "membership_refuses_a_foreign_boundary_version": not read_only_membership_consumer(
            {**good, "boundary_version": PREDECESSOR_BOUNDARY_VERSION}
        )["admitted"],
        "membership_refuses_a_document_with_no_people": not read_only_membership_consumer(
            {**good, "document": {**good["document"], "value": {"team_id": "t", "coach_ids": []}}}
        )["admitted"],
        "role_consumer_refuses_the_lossy_projection": not read_only_role_consumer(good)["admitted"],
    }
    shipped = set(wheel.get("catalog_contracts") or [])
    intelligence = sorted(c for c in shipped if c.startswith("intelligence/"))
    if not intelligence:
        raise SystemExit(
            "the released catalog ships no intelligence/* contracts; the F10 "
            "separation cannot be tested against nothing"
        )
    separation = {}
    for target in intelligence:
        try:
            refuse_source_scheme_as_realized_state(
                {"source_text": "runs a spread offense"}, target
            )
            separation[target] = "ALLOWED"
        except ProjectionRefused:
            separation[target] = "REFUSED"
    envelope = assertion().as_dict()
    lossless = {
        "envelope_fields": sorted(envelope),
        "lost_by_projection": sorted(n for n, r in FIELD_MATRIX.items() if r["state"] == LOST),
        "every_lost_field_is_in_the_envelope": all(
            n.split("[")[0] in envelope for n, r in FIELD_MATRIX.items() if r["state"] == LOST
        ),
    }

    positives = [c for c in cases if c["expectation"] == "ACCEPT"]
    negatives = [c for c in cases if c["expectation"] == "REJECT"]
    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-13",
        "acceptance": ["R37-13-AC03", "R37-13-AC04", "R37-13-AC05", "R37-13-AC06",
                       "R37-13-AC07", "R37-13-AC09", "R37-13-AC10"],
        "vector": {
            "producer": f"aggie_analytics.cycle36.c01_boundary {BOUNDARY_VERSION}",
            "predecessor_producer": PREDECESSOR_BOUNDARY_VERSION,
            "consumer": "cfb_intelligence_contracts.validate_document",
            "wheel": str(args.wheel),
            "wheel_sha256": wheel_digest,
            "wheel_matches_released_digest": True,
            "wheel_version": wheel.get("version"),
            "schema": C01_CONTRACT,
            "ruleset_id": "synthetic-ruleset",
            "context": "rights-safe synthetic fixtures; no real person or program",
        },
        "fixtures": cases,
        "positives": len(positives),
        "positives_accepted_by_both": sum(1 for c in positives if c["honours_expectation"]),
        "negatives": len(negatives),
        "negatives_refused": sum(1 for c in negatives if c["honours_expectation"]),
        "negatives_caught_by_bas_adapter": sum(1 for c in negatives if c.get("caught_by") == "BAS_ADAPTER"),
        "negatives_caught_only_by_released_wheel": wheel_only,
        "all_fixtures_honoured": all(c["honours_expectation"] for c in cases),
        "consumers": consumers,
        "all_consumer_checks_hold": all(consumers.values()),
        "source_scheme_vs_f10_state": separation,
        "f10_separation_holds": bool(separation) and all(v == "REFUSED" for v in separation.values()),
        "lossless_envelope": lossless,
        "wheel_catalog_contracts": sorted(shipped),
        "no_film_fallback": (
            "No fixture reaches for a Film-derived value when a BAS fact is "
            "missing: a missing field is a refusal, never a substitution."
        ),
        "submission_is_not_adoption": (
            "Qualifying BAS's projection against the released 0.1.2 schema is "
            "not the owner adopting BAS's envelope, not an owner approval and "
            "not a C01 self-approval. No owner repository or runtime was touched."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
                        encoding="utf-8")

    print("wheel                    :", wheel.get("version"), wheel_digest[:16])
    print("positives accepted by both:", f"{receipt['positives_accepted_by_both']}/{len(positives)}")
    print("negatives refused         :", f"{receipt['negatives_refused']}/{len(negatives)}",
          f"(BAS adapter caught {receipt['negatives_caught_by_bas_adapter']})")
    print("caught only by the wheel  :", wheel_only or "none")
    print("consumer checks           :", consumers)
    print("F10 separation            :", separation)
    print("all honoured              :", receipt["all_fixtures_honoured"])
    for c in cases:
        if not c["honours_expectation"]:
            print("  FAILED:", c["fixture"], c["bas_adapter"], c["released_wheel"],
                  c.get("wheel_reason") or c.get("bas_reason"))
    return 0 if receipt["all_fixtures_honoured"] and receipt["all_consumer_checks_hold"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
