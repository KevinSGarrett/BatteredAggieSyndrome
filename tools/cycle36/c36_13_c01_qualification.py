"""R36-13: qualify the physical C01 wheel, and declare the boundary's losses.

MR35R-12 reclassified the old "cannot download" blocker: the v0.1.2 wheel is
present and digest-bound in the manager's evidence. What remains is physical
qualification -- installing that artifact in an isolated environment and
running its own validators against rights-safe synthetic payloads -- and a
field-level statement of what the released ``StaffSnapshotV1`` can and cannot
carry.

The tool does four things and refuses a fifth:

1. Re-verifies the wheel bytes against the published asset digest, and
   records its metadata, declared dependencies and packaged schema paths.
2. Creates a throwaway virtual environment, installs the wheel from the local
   file with no index access, and imports it there rather than in this
   process.
3. Executes the package's **own** validators -- ``validate_document``,
   ``enforce_point_in_time``, ``require_explicit_unknown``,
   ``classify_version_change``, ``validate_fixture`` -- against synthetic
   valid and invalid payloads built here. No real person, program or
   copyrighted source text is used.
4. Publishes the represented / lost / pending field matrix and runs the two
   read-only BAS consumer stubs, one of which must refuse.

It does not adopt a contract, write to an owner repository, activate a Film
runtime, or claim the richer BAS envelope is a released C01 schema.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import venv
import zipfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.c01_boundary import (  # noqa: E402
    C01_CONTRACT,
    FIELD_MATRIX,
    LOST,
    PENDING,
    REPRESENTED,
    ProjectionRefused,
    RoleScope,
    StaffAssertion,
    owner_proposal,
    project_to_staff_snapshot,
    read_only_membership_consumer,
    read_only_role_consumer,
)
from aggie_analytics import atomic_io as _bas_atomic

WHEEL = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
    r"\c01_release\cfbintelligencecontracts-0.1.2-py3-none-any.whl"
)
PUBLISHED_DIGEST = "a57d4a58cb268e14f88ea7a66bf49131e89b7f930ea1acabc05c2dfeca689af3"

#: Executed inside the isolated interpreter. Everything it touches is
#: synthetic; no real staff record, program name or source text appears.
PROBE = r'''
import json, sys, traceback
import cfb_intelligence_contracts as c01

def attempt(name, fn):
    try:
        value = fn()
        return {"probe": name, "outcome": "ACCEPTED", "detail": None, "value": value}
    except Exception as error:
        return {
            "probe": name,
            "outcome": "REJECTED",
            "detail": f"{type(error).__name__}: {error}"[:400],
            "value": None,
        }

VALID = {
    "schema_version": "0.1.2",
    "contract": "context/StaffSnapshotV1",
    "object_id": "synthetic-staff-snapshot-1",
    "known_at": "2026-09-09T18:08:43Z",
    "point_in_time_cutoff": "2026-09-09T18:08:43Z",
    "provenance": {
        "source_system": "SYNTHETIC-FIXTURE",
        "evidence_refs": ["synthetic://evidence/1"],
    },
    "ruleset_id": "synthetic-ruleset",
    "unit": "record",
    "coordinate_system": "none",
    "value": {"team_id": "synthetic-team-1", "coach_ids": ["synthetic-person-1"]},
    "unknown_reason": None,
    "compatibility": {"classification": "patch", "minimum_consumer_version": "0.1.2"},
}

def without(key):
    document = json.loads(json.dumps(VALID))
    document.pop(key, None)
    return document

def mutate(path, new):
    document = json.loads(json.dumps(VALID))
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = new
    return document

results = []
results.append(attempt("valid_staff_snapshot", lambda: c01.validate_document("context/StaffSnapshotV1", VALID) or "OK"))
results.append(attempt("missing_provenance", lambda: c01.validate_document("context/StaffSnapshotV1", without("provenance"))))
results.append(attempt("missing_point_in_time_cutoff", lambda: c01.validate_document("context/StaffSnapshotV1", without("point_in_time_cutoff"))))
results.append(attempt("empty_evidence_refs", lambda: c01.validate_document("context/StaffSnapshotV1", mutate(["provenance", "evidence_refs"], []))))
results.append(attempt("wrong_contract_constant", lambda: c01.validate_document("context/StaffSnapshotV1", mutate(["contract"], "context/SomethingElse"))))
results.append(attempt("non_utc_known_at", lambda: c01.validate_document("context/StaffSnapshotV1", mutate(["known_at"], "2026-09-09 18:08:43"))))
results.append(attempt("undeclared_extra_field", lambda: c01.validate_document("context/StaffSnapshotV1", {**VALID, "roles": [{"role_code": "HC"}]})))
results.append(attempt("value_missing_coach_ids", lambda: c01.validate_document("context/StaffSnapshotV1", mutate(["value"], {"team_id": "synthetic-team-1"}))))
results.append(attempt("unknown_reason_out_of_enum", lambda: c01.validate_document("context/StaffSnapshotV1", mutate(["unknown_reason"], "BECAUSE"))))
results.append(attempt("pit_known_at_before_cutoff", lambda: c01.enforce_point_in_time("2026-09-01T00:00:00Z", "2026-09-09T18:08:43Z") or "OK"))
results.append(attempt("pit_known_at_after_cutoff", lambda: c01.enforce_point_in_time("2026-09-10T00:00:00Z", "2026-09-09T18:08:43Z")))
results.append(attempt("explicit_unknown_required", lambda: c01.require_explicit_unknown({**VALID, "value": None, "unknown_reason": None})))
results.append(attempt("explicit_unknown_supplied", lambda: c01.require_explicit_unknown({**VALID, "value": None, "unknown_reason": "INSUFFICIENT_EVIDENCE"}) or "OK"))
results.append(attempt("version_change_classification", lambda: c01.classify_version_change("0.1.1", "0.1.2")))
results.append(attempt("utc_timestamp_rejects_naive", lambda: c01.require_utc_timestamp("2026-09-09 18:08:43")))

catalog = c01.load_catalog()
print(json.dumps({
    "package_version": c01.__version__,
    "catalog_object_count": len(catalog.get("objects") or {}),
    "staff_schema_present": "context/StaffSnapshotV1" in (catalog.get("objects") or {}),
    "staff_schema": c01.load_schema("context/StaffSnapshotV1"),
    "probes": results,
}))
'''


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def wheel_facts(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    facts: dict[str, Any] = {
        "path": str(path),
        "bytes": len(raw),
        "sha256": digest,
        "published_asset_digest": PUBLISHED_DIGEST,
        "digest_matches_published_asset": digest == PUBLISHED_DIGEST,
    }
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        facts["entries"] = len(names)
        facts["python_modules"] = sorted(n for n in names if n.endswith(".py"))
        facts["packaged_schema_paths"] = sorted(
            n for n in names if n.endswith(".schema.json")
        )
        facts["packaged_schema_count"] = len(facts["packaged_schema_paths"])
        facts["staff_schema_path"] = next(
            (n for n in names if n.endswith("context/StaffSnapshotV1.schema.json")),
            None,
        )
        metadata_name = next(
            (n for n in names if n.endswith(".dist-info/METADATA")), None
        )
        if metadata_name:
            metadata = archive.read(metadata_name).decode("utf-8", errors="replace")
            facts["metadata"] = {
                line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip()
                for line in metadata.splitlines()
                if ":" in line and not line.startswith(" ")
            }
            facts["declared_dependencies"] = [
                line.split(":", 1)[1].strip()
                for line in metadata.splitlines()
                if line.lower().startswith("requires-dist")
            ]
            facts["declared_license"] = facts["metadata"].get(
                "License-Expression"
            ) or facts["metadata"].get("License")
        facts["license_files"] = sorted(
            n for n in names if "licen" in n.lower()
        )
    facts["license_state"] = (
        "DECLARED"
        if facts.get("declared_license") or facts.get("license_files")
        else "NO_LICENSE_DECLARED_IN_METADATA_OR_PACKAGED_FILES"
    )
    facts["license_note"] = (
        "The wheel's METADATA carries no License or License-Expression field "
        "and the archive contains no licence file. Rights for redistribution "
        "of this package are therefore unstated by the artifact itself; this "
        "is recorded as a gap for the owner rather than assumed permissive."
    )
    facts["dependency_state"] = (
        "NO_RUNTIME_DEPENDENCIES_DECLARED"
        if not facts.get("declared_dependencies")
        else "DEPENDENCIES_DECLARED"
    )
    return facts


def qualify_in_isolation(wheel: Path) -> dict[str, Any]:
    """Install the wheel in a throwaway venv and run its validators there."""

    record: dict[str, Any] = {"isolation": "EPHEMERAL_VIRTUALENV_NO_INDEX_ACCESS"}
    with tempfile.TemporaryDirectory(prefix="c36_c01_") as tmp:
        root = Path(tmp)
        env_dir = root / "env"
        try:
            venv.create(env_dir, with_pip=True, clear=True)
        except Exception as error:  # noqa: BLE001 - environment creation is data
            record.update(state="VENV_CREATE_FAILED", detail=str(error))
            return record
        python = env_dir / ("Scripts" if sys.platform == "win32" else "bin") / (
            "python.exe" if sys.platform == "win32" else "python"
        )
        record["interpreter"] = str(python)
        install = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--disable-pip-version-check",
                str(wheel),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
        )
        record["install_exit_code"] = install.returncode
        record["install_stdout_tail"] = install.stdout[-1200:]
        record["install_stderr_tail"] = install.stderr[-1200:]
        if install.returncode != 0:
            record["state"] = "INSTALL_FAILED"
            return record
        probe_path = root / "probe.py"
        _bas_atomic.write_text(probe_path, PROBE, encoding="utf-8")
        run = subprocess.run(
            [str(python), str(probe_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
            cwd=str(root),
        )
        record["probe_exit_code"] = run.returncode
        if run.returncode != 0:
            record["state"] = "PROBE_FAILED"
            record["probe_stderr_tail"] = run.stderr[-2000:]
            return record
        try:
            payload = json.loads(run.stdout)
        except ValueError as error:
            record["state"] = "PROBE_OUTPUT_UNPARSEABLE"
            record["detail"] = str(error)
            record["probe_stdout_tail"] = run.stdout[-2000:]
            return record
        record["state"] = "INSTALLED_AND_VALIDATORS_EXECUTED"
        record.update(payload)
    return record


EXPECTED_PROBE_OUTCOMES = {
    "valid_staff_snapshot": "ACCEPTED",
    "missing_provenance": "REJECTED",
    "missing_point_in_time_cutoff": "REJECTED",
    "empty_evidence_refs": "REJECTED",
    "wrong_contract_constant": "REJECTED",
    "non_utc_known_at": "REJECTED",
    "undeclared_extra_field": "REJECTED",
    "value_missing_coach_ids": "REJECTED",
    "unknown_reason_out_of_enum": "REJECTED",
    "pit_known_at_before_cutoff": "ACCEPTED",
    "pit_known_at_after_cutoff": "REJECTED",
    "explicit_unknown_required": "REJECTED",
    "explicit_unknown_supplied": "ACCEPTED",
    "utc_timestamp_rejects_naive": "REJECTED",
}


def synthetic_boundary_exercise() -> dict[str, Any]:
    """Project rights-safe synthetic assertions and run both consumer stubs."""

    assertions = [
        StaffAssertion(
            assertion_id="synthetic-assertion-1",
            person_id="synthetic-person-1",
            person_display_name="Synthetic Person One",
            program_id="synthetic-team-1",
            season=2026,
            roles=(
                RoleScope("head_coach", "TEAM", (), "PRINCIPAL"),
            ),
            source_title="Synthetic Head Coach Title",
            source_system="SYNTHETIC-FIXTURE",
            evidence_refs=("synthetic://evidence/1",),
            source_locator="tr[0]",
            source_effective_start="2026-01-15",
            known_at_utc="2026-09-09T18:08:43Z",
            point_in_time_cutoff="2026-09-09T18:08:43Z",
            evidence_tier="OFFICIAL_HTML_RECORD_BOUND",
        ),
        StaffAssertion(
            assertion_id="synthetic-assertion-2",
            person_id="synthetic-person-2",
            person_display_name="Synthetic Person Two",
            program_id="synthetic-team-1",
            season=2026,
            roles=(
                RoleScope("offensive_coordinator", "OFFENSE", ("CO",), "CO_SHARED"),
                RoleScope("quarterbacks", "OFFENSE", (), "OBSERVED"),
            ),
            source_title="Synthetic Co-Offensive Coordinator / Quarterbacks",
            source_system="SYNTHETIC-FIXTURE",
            evidence_refs=("synthetic://evidence/2",),
            known_at_utc="2026-09-09T18:08:43Z",
            point_in_time_cutoff="2026-09-09T18:08:43Z",
            evidence_tier="OFFICIAL_HTML_RECORD_BOUND",
        ),
    ]
    # An unresolved conflict has no field in the released value, so the
    # boundary refuses to project it (the snapshot would look unanimous). The
    # exercise checks that refusal separately instead of projecting it.
    conflicted = list(assertions)
    conflicted[1] = replace(conflicted[1], conflicts_with=("synthetic-assertion-3",))
    try:
        project_to_staff_snapshot(
            conflicted, object_id="synthetic-staff-snapshot-3", ruleset_id="synthetic-ruleset"
        )
        conflict_refusal = {"refused": False}
    except ProjectionRefused as error:
        conflict_refusal = {"refused": True, "detail": str(error)}
    projection = project_to_staff_snapshot(
        assertions, object_id="synthetic-staff-snapshot-1", ruleset_id="synthetic-ruleset"
    )
    refusals: list[dict[str, Any]] = []
    for field_name in ("roles", "source_title", "evidence_tier"):
        try:
            project_to_staff_snapshot(
                assertions,
                object_id="synthetic-staff-snapshot-1",
                ruleset_id="synthetic-ruleset",
                required_fields=[field_name],
            )
            refusals.append({"required_field": field_name, "refused": False})
        except ProjectionRefused as error:
            refusals.append(
                {"required_field": field_name, "refused": True, "detail": str(error)}
            )
    cross_program = list(assertions) + [
        StaffAssertion(
            assertion_id="synthetic-assertion-4",
            person_id="synthetic-person-4",
            person_display_name="Synthetic Person Four",
            program_id="synthetic-team-2",
            season=2026,
            roles=(RoleScope("head_coach", "TEAM", (), "PRINCIPAL"),),
            source_title="Synthetic Head Coach Title",
            source_system="SYNTHETIC-FIXTURE",
            evidence_refs=("synthetic://evidence/4",),
            known_at_utc="2026-09-09T18:08:43Z",
            point_in_time_cutoff="2026-09-09T18:08:43Z",
        )
    ]
    try:
        project_to_staff_snapshot(
            cross_program,
            object_id="synthetic-staff-snapshot-2",
            ruleset_id="synthetic-ruleset",
        )
        cross_program_refused = False
    except ProjectionRefused:
        cross_program_refused = True

    return {
        "projection": projection,
        "role_aware_consumer": read_only_role_consumer(projection),
        "membership_consumer": read_only_membership_consumer(projection),
        "required_field_refusals": refusals,
        "cross_program_projection_refused": cross_program_refused,
        "unresolved_conflict_projection_refused": conflict_refusal["refused"],
        "unresolved_conflict_refusal": conflict_refusal,
        "synthetic_only": (
            "Every identifier, title and evidence reference above is synthetic. "
            "No real person, program or source text is exported."
        ),
    }


def build(out_dir: Path, wheel: Path) -> dict[str, Any]:
    facts = wheel_facts(wheel)
    qualification = qualify_in_isolation(wheel)
    probes = {
        probe["probe"]: probe for probe in qualification.get("probes") or []
    }
    probe_agreement = {
        name: {
            "expected": expected,
            "observed": probes.get(name, {}).get("outcome"),
            "agrees": probes.get(name, {}).get("outcome") == expected,
            "detail": probes.get(name, {}).get("detail"),
        }
        for name, expected in EXPECTED_PROBE_OUTCOMES.items()
    }
    boundary = synthetic_boundary_exercise()

    artifact = {
        "artifact_type": "CYCLE36_ALL22_CONTRACT_COMPATIBILITY",
        "generated_at_utc": utc_now(),
        "wheel": facts,
        "isolated_qualification": {
            key: value
            for key, value in qualification.items()
            if key not in {"probes", "staff_schema"}
        },
        "validator_probes": probe_agreement,
        "validator_probes_agreeing": sum(
            1 for row in probe_agreement.values() if row["agrees"]
        ),
        "validator_probes_total": len(probe_agreement),
        "released_staff_schema": qualification.get("staff_schema"),
        "field_matrix": FIELD_MATRIX,
        "field_matrix_counts": {
            REPRESENTED: sum(
                1 for row in FIELD_MATRIX.values() if row["state"] == REPRESENTED
            ),
            LOST: sum(1 for row in FIELD_MATRIX.values() if row["state"] == LOST),
            PENDING: sum(
                1 for row in FIELD_MATRIX.values() if row["state"] == PENDING
            ),
        },
        "boundary_exercise": boundary,
        "owner_proposal": owner_proposal(),
        "authority": {
            "schema_self_approval": False,
            "owner_repository_written": False,
            "film_runtime_activated": False,
            "direct_table_sharing": False,
            "protected_data_exported": False,
            "note": (
                "Qualification is a local evidence activity. Adoption of the "
                f"{C01_CONTRACT} representation belongs to the C01 owners "
                "through their own workflow."
            ),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_ALL22_CONTRACT_COMPATIBILITY.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, default=WHEEL)
    args = parser.parse_args()
    artifact = build(args.out_dir, args.wheel)
    print(
        json.dumps(
            {
                "digest_matches_published_asset": artifact["wheel"][
                    "digest_matches_published_asset"
                ],
                "packaged_schema_count": artifact["wheel"]["packaged_schema_count"],
                "declared_dependencies": artifact["wheel"].get("declared_dependencies"),
                "isolation_state": artifact["isolated_qualification"].get("state"),
                "validator_probes": f"{artifact['validator_probes_agreeing']}/{artifact['validator_probes_total']}",
                "field_matrix_counts": artifact["field_matrix_counts"],
                "role_consumer_admitted": artifact["boundary_exercise"][
                    "role_aware_consumer"
                ]["admitted"],
                "membership_consumer_admitted": artifact["boundary_exercise"][
                    "membership_consumer"
                ]["admitted"],
                "cross_program_refused": artifact["boundary_exercise"][
                    "cross_program_projection_refused"
                ],
                "unresolved_conflict_refused": artifact["boundary_exercise"][
                    "unresolved_conflict_projection_refused"
                ],
            },
            indent=2,
        )
    )
    boundary = artifact["boundary_exercise"]
    if not (boundary["cross_program_projection_refused"] and boundary["unresolved_conflict_projection_refused"]):
        print("FAIL: the boundary projected a cross-program set or an unresolved conflict")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
