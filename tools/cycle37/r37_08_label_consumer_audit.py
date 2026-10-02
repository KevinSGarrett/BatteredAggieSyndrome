"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-08 AC04/AC10 and OBL_KERNEL_PRODUCER_RECEIPTS: audit every consumer of
the kernel's producer labels and withdraw the 36 unsupported
``PROVEN_PIT_TRAINING_ROW`` labels by successor, without touching the
predecessor bytes.

Three parts:

1. Discovery. Every tracked Python file (tests aside) that names a PIT label
   token is found with ``git grep``. Each one must carry a declared role
   below, and each declared file must still name a token, so a consumer
   cannot be added or dropped without this audit noticing.
2. Behaviour. The 36 labelled rows are passed, byte for byte, through every
   gate that decides admission, alongside forged controls (a forged label on
   a historical row, a forged receipt, a caller-asserted admission). A gate
   that admits anything fails the audit.
3. Successor. One successor row per label, bound to the SHA-256 of the exact
   predecessor line, states what receipt exists and why the label is
   withdrawn. The kernel file is hashed before and after.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
KERNEL_ROWS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/outputs/PIT_KERNEL_ROWS.jsonl")
FREEZE_ROWS = Path(r"C:/BatteredAggieSyndrome.data/canonical/week1_2026_game_grain_national_forecast_successor/sha256"
                   r"/770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
                   r"/week1_2026_game_grain_forecast_rows.jsonl")
PROVEN = "PROVEN_PIT_TRAINING_ROW"
TOKENS = r"PROVEN_PIT_TRAINING_ROW|PIT_KERNEL_ROWS|proven_pit_training_rows|\brow_verdict\b|\bauthority_class\b"

PRODUCER = "PRODUCER_EMITS_THE_LABEL"
PRIOR_PRODUCER = "EARLIER_CYCLE_PRODUCER_NOT_OF_THESE_ROWS"
GATE = "ADMISSION_GATE_PROBED_WITH_THE_36_ROWS"
REFERENCE_OWN_CLASS = "INDEPENDENT_REFERENCE_EMITS_ITS_OWN_CLASS_FROM_PUBLICATION"
COUNT = "COUNT_OR_REPORT_ONLY_NO_ADMISSION"
FIT_BY_SEASON = "FITS_ROWS_SELECTED_BY_SEASON_LABEL_NOT_READ"
OTHER_ARTIFACT = "SAME_TOKEN_FOR_ANOTHER_ARTIFACT"
VALIDATOR = "VALIDATOR_REQUIRES_ZERO_OR_AUTHORITY"

#: Declared role of every file that names a token, with the basis read from it.
DECLARED: dict[str, tuple[str, str]] = {
    "src/aggie_analytics/cycle30/pit_kernel.py": (PRODUCER, "build_game_grain_kernel emits the label; since ff7859fa a freeze receipt yields RETROSPECTIVE, not PROVEN"),
    "tools/materialize_cycle30.py": (PRODUCER, "wrote PIT_KERNEL_ROWS.jsonl on 2026-09-09 with the pre-ff7859fa rule that read a freeze time as source publication"),
    "src/aggie_analytics/cycle29/pit_kernel.py": (PRIOR_PRODUCER, "Cycle 29 kernel builder; not the producer of the current file"),
    "tools/materialize_cycle29.py": (PRIOR_PRODUCER, "wrote a Cycle 29 kernel to its own output directory"),
    "tools/materialize_cycle28.py": (PRIOR_PRODUCER, "writes proven_pit_training_rows = 0"),
    "src/aggie_analytics/cycle36/kernel_reference.py": (GATE, "classify_pit and admit_to_pit_consumer: the single consumer gate, repaired for MF36-03"),
    "src/aggie_analytics/cycle33/pit_recompute.py": (GATE, "independently_admit_row refuses a producer label without a receipt"),
    "src/aggie_analytics/scientific_reference/cycle33_pit.py": (GATE, "independent_row_class refuses without publication or on a 2026 season"),
    "tools/trace_cycle32_pit_lineage.py": (GATE, "independent_verdict re-derives a class from row authority"),
    "src/aggie_analytics/scientific_reference/cycle30/pit.py": (REFERENCE_OWN_CLASS, "reconstructs features and names a row PROVEN only when a source_publication_utc is supplied; kernel rows carry none"),
    "src/aggie_analytics/cycle28/assurance.py": (COUNT, "blocks when the proven count is zero; reads no row label"),
    "src/aggie_analytics/cycle29/claims.py": (COUNT, "claim field names"),
    "src/aggie_analytics/cycle30/claims.py": (COUNT, "treats the token as an overclaim word in narrative checks"),
    "src/aggie_analytics/cycle30/audit_register.py": (COUNT, "lists the file path in the audit register"),
    "src/aggie_analytics/data/week1_2026_fitted_path_temporal_authority.py": (COUNT, "derives a proven count from authority domains and forces zero without them"),
    "tools/audit_cycle32_national_game_core.py": (COUNT, "counts kernel lines"),
    "tools/continue_cycle33_availability_pit.py": (COUNT, "reports recompute_pit_population counts"),
    "tools/exhaust_cycle33_forecast_pit_search.py": (COUNT, "reports producer_proven_without_receipt and searches receipt mentions"),
    "tools/cycle35/r35_05_national_coverage_census.py": (COUNT, "counts kernel coverage"),
    "tools/cycle35/r35_09_independent_kernel_reference.py": (COUNT, "reports the producer labels as unsupported"),
    "tools/cycle35/r35_09_pit_feasibility.py": (COUNT, "reports the producer labels in the feasibility table"),
    "tools/cycle36/c36_08_kernel_reconciliation.py": (COUNT, "supersedes the labels through classify_pit and admit_to_pit_consumer"),
    "tools/cycle37/mf36_admission_probe.py": (COUNT, "negative and positive controls for the repaired gate"),
    "tools/cycle37/r37_08_kernel_reconciliation.py": (COUNT, "records the stored label beside each reconstructed row"),
    "tools/cycle37/r37_08_label_consumer_audit.py": (COUNT, "this audit"),
    "tools/audit_cycle32_staff_kernel_adapters.py": (FIT_BY_SEASON, "fold_local_fit over seasons 2013-2023; the 2026 rows are in no fold"),
    "tools/exhaust_cycle33_remaining.py": (FIT_BY_SEASON, "fold_local_fit over seasons 2013-2023"),
    "tools/cycle34_r34_09_population_reconciliation.py": (FIT_BY_SEASON, "fold_local_fit with train 2013-2019, eval 2020-2023; reports the 36 labels separately"),
    "src/aggie_analytics/data/national_pit_eligible_slice.py": (OTHER_ARTIFACT, "row_verdict of the 90,198-row eligible slice (ELIGIBLE/ELIGIBLE_NO_PRIOR)"),
    "tools/validate_national_pit_eligible_slice.py": (OTHER_ARTIFACT, "row_verdict of the eligible slice"),
    "src/aggie_analytics/data/cycle26_bound_authority_pair_audit.py": (OTHER_ARTIFACT, "authority_class of known-at domains"),
    "src/aggie_analytics/data/historical_known_at_authority.py": (OTHER_ARTIFACT, "authority_class of known-at domains"),
    "tools/validate_historical_known_at_authority_audit.py": (OTHER_ARTIFACT, "authority_class of known-at domains"),
    "tools/validate_cycle28_gates.py": (VALIDATOR, "requires proven_pit_training_rows == 0"),
    "tools/validate_cycle30_gates.py": (VALIDATOR, "reads the kernel file to check gate claims"),
    "tools/validate_week1_2026_fitted_path_temporal_authority.py": (VALIDATOR, "flags proven rows claimed without authority"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def discover(root: Path = ROOT) -> dict[str, list[str]]:
    listing = subprocess.run(["git", "grep", "--untracked", "-n", "-E", TOKENS, "--", "*.py", ":!tests/*"], cwd=root,
                             capture_output=True, text=True, encoding="utf-8", check=False)
    if listing.returncode not in (0, 1):
        raise RuntimeError(listing.stderr)
    hits: dict[str, list[str]] = {}
    for line in listing.stdout.splitlines():
        path, number, text = line.split(":", 2)
        if re.search(TOKENS, text):
            hits.setdefault(path, []).append(f"{number}: {text.strip()[:160]}")
    return hits


def reconcile_declarations(hits: dict[str, list[str]]) -> dict[str, Any]:
    undeclared = sorted(set(hits) - set(DECLARED))
    stale = sorted(set(DECLARED) - set(hits))
    return {"files_naming_a_token": len(hits), "declared": len(DECLARED),
            "undeclared_consumers": undeclared, "declared_but_no_longer_naming_a_token": stale,
            "complete": not undeclared and not stale}


def _load_tool(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gates() -> dict[str, Any]:
    from aggie_analytics.cycle33 import pit_recompute
    from aggie_analytics.cycle36 import kernel_reference
    from aggie_analytics.scientific_reference import cycle33_pit

    lineage = _load_tool("tools/trace_cycle32_pit_lineage.py", "trace_cycle32_pit_lineage")

    def cycle36_gate(row: dict[str, Any], receipts: dict[str, Any] | None = None, authority: Any = None) -> bool:
        # MF37A02-03: the gate now resolves receipts to verified bytes through an authority, and the priors
        # they attest must be exactly those the row declares it consumed.
        classification = kernel_reference.classify_pit(row, receipts, authority=authority)
        return bool(classification.get("admissible_to_a_pit_consumer")) and kernel_reference.admit_to_pit_consumer(
            classification, row=row, receipts_by_game=receipts, authority=authority)

    return {
        "cycle36.kernel_reference.admit_to_pit_consumer": cycle36_gate,
        "cycle33.pit_recompute.independently_admit_row": (
            lambda row, receipts=None: bool(pit_recompute.independently_admit_row(row)["independently_proven"])),
        "scientific_reference.cycle33_pit.independent_row_class": (
            lambda row, receipts=None: bool(cycle33_pit.independent_row_class(row)["independently_proven"])),
        "tools.trace_cycle32_pit_lineage.independent_verdict": (
            lambda row, receipts=None: lineage.independent_verdict(row) == PROVEN and not lineage.limiting_keys(row)),
    }


def forged_controls(historical: dict[str, Any]) -> list[tuple[str, dict[str, Any], dict[str, Any] | None]]:
    gid = historical["canonical_game_id"]
    forged_label = {**historical, "authority_class": PROVEN, "row_verdict": PROVEN}
    asserted = {**forged_label, "successor_state": "PIT_PROVEN", "admissible_to_a_pit_consumer": True,
                "independently_proven": True}
    forged_receipt_fields = {**forged_label, "source_id": "SRC-002", "effective_utc": "2013-08-01T00:00:00Z",
                             "known_at_utc": "2013-08-01T00:00:00Z", "receipt_sha256": "0" * 64,
                             "classification": "OBSERVED_PUBLICATION", "evidence_class": "SOURCE_PUBLICATION",
                             "source_publication_utc": "2099-01-01T00:00:00Z"}
    published_late = {**forged_receipt_fields, "target_cutoff_utc": "2013-08-31T16:00:00Z",
                      "source_publication_utc": "2014-01-15T12:00:00Z", "known_at_utc": "2014-01-15T12:00:00Z",
                      "effective_utc": "2013-08-01T00:00:00Z"}
    return [
        ("forged PROVEN label on a historical row", forged_label, None),
        ("caller-asserted admission fields", asserted, None),
        ("forged authority with a future publication instant", forged_receipt_fields, None),
        ("authority published after the row's own cutoff", published_late, None),
        ("unrelated truthy receipt object", forged_label, {gid: {"unrelated": True}}),
    ]


def positive_control(historical: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """A synthetic row whose authority is well formed and in time.

    Not evidence about any real contest: the structure of a real 2013 row
    with an invented authority, so a gate which refuses the labelled rows is
    shown to refuse them for a reason, not to refuse everything.
    """

    gid = historical["canonical_game_id"]
    digest = hashlib.sha256(b"synthetic positive control").hexdigest()
    row = {**historical, "canonical_game_id": gid, "season": 2013, "source_id": "SRC-TEST",
           "effective_utc": "2013-08-30T12:00:00Z", "known_at_utc": "2013-08-30T13:00:00Z",
           "receipt_sha256": digest, "classification": "OBSERVED_PUBLICATION",
           "evidence_class": "SOURCE_PUBLICATION", "source_publication_utc": "2013-08-30T12:30:00Z",
           "target_cutoff_utc": "2013-08-31T16:00:00Z", "cutoff_utc": "2013-08-31T16:00:00Z",
           "frozen_input_identity": digest, "contributing_event_ids": [gid]}
    receipts = {gid: {"source_id": "SRC-TEST", "prior_game_id": gid, "payload_sha256": digest,
                      "published_at_utc": "2013-08-30T12:30:00+00:00", "known_at_utc": "2013-08-30T13:00:00+00:00"}}
    return row, receipts


CYCLE36_GATE = "cycle36.kernel_reference.admit_to_pit_consumer"


def cycle36_positive_control(historical: dict[str, Any], fixture_root: Path) -> tuple[dict[str, Any], dict[str, Any], Any]:
    """The Cycle 36 gate's positive control, with real bytes behind its receipt (MF37A02-03).

    The shared positive control's receipt is a caller-built dictionary naming the row's own contest as its
    prior and an invented digest -- the exact shape MF37A02-03 showed the gate used to admit. For this gate
    the control therefore declares the prior the row consumed and offers a receipt written to a test-only
    fixture store, resolved by digest. It is a fixture, labelled as one, and proves nothing about a contest.
    """

    from aggie_analytics.cycle37.receipt_fixtures import fixture_authority, prior_receipt

    row, _ = positive_control(historical)
    prior = f"{row['canonical_game_id']}:SYNTHETIC-PRIOR"
    row = {**row, "prior_observation_ids": [prior]}
    authority = fixture_authority(fixture_root, "r37-08-label-audit-fixture")
    receipt_digest, stored = prior_receipt(fixture_root, priors=[prior],
                                           published_at=datetime(2013, 8, 30, 12, 30, tzinfo=timezone.utc),
                                           known_at=datetime(2013, 8, 30, 13, 0, tzinfo=timezone.utc))
    return row, {row["canonical_game_id"]: {**stored, "receipt_digest": receipt_digest}}, authority


def probe(rows: list[dict[str, Any]], historical: dict[str, Any]) -> dict[str, Any]:
    import shutil
    import tempfile

    fixture_root = Path(tempfile.mkdtemp(prefix="r37_08_fixture_"))
    try:
        return _probe(rows, historical, fixture_root)
    finally:
        shutil.rmtree(fixture_root, ignore_errors=True)


def _probe(rows: list[dict[str, Any]], historical: dict[str, Any], fixture_root: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    cycle36_row, cycle36_receipts, cycle36_authority = cycle36_positive_control(historical, fixture_root)
    for name, gate in gates().items():
        # The Cycle 36 gate is probed with a fixture authority present, so its refusals below are refusals of
        # the evidence, not merely of an absent authority.
        authority = {"authority": cycle36_authority} if name == CYCLE36_GATE else {}
        admitted = []
        errors = []
        for row in rows:
            try:
                if gate(dict(row), None, **authority):
                    admitted.append(row["canonical_game_id"])
            except Exception as exc:  # a gate that raises has not admitted; the error is recorded
                errors.append(f"{row['canonical_game_id']}: {type(exc).__name__}: {exc}")
        controls = []
        for label, control, receipts in forged_controls(historical):
            try:
                outcome = "ADMITTED" if gate(dict(control), receipts, **authority) else "REFUSED"
            except Exception as exc:
                outcome = f"REFUSED_BY_ERROR: {type(exc).__name__}"
            controls.append({"control": label, "outcome": outcome})
        positive, receipts = ((cycle36_row, cycle36_receipts) if name == CYCLE36_GATE
                              else positive_control(historical))
        try:
            positive_outcome = "ADMITTED" if gate(dict(positive), receipts, **authority) else "REFUSED"
        except Exception as exc:
            positive_outcome = f"REFUSED_BY_ERROR: {type(exc).__name__}"
        results[name] = {"labelled_rows_probed": len(rows), "labelled_rows_admitted": admitted,
                         "errors": errors, "forged_controls": controls,
                         "synthetic_positive_control": positive_outcome,
                         "passes": not admitted and all(c["outcome"] != "ADMITTED" for c in controls)}
    return results


BASE_COMMIT = "2202b2b2d48217ecfcf52df4464c21abd077ef06"
REFERENCE_PATH = "src/aggie_analytics/scientific_reference/cycle33_pit.py"


def reference_before_after(historical: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """The Cycle 33 reference at the prepared base against the repaired one."""

    import types
    from aggie_analytics.scientific_reference import cycle33_pit as repaired

    source = subprocess.run(["git", "show", f"{BASE_COMMIT}:{REFERENCE_PATH}"], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", check=True).stdout
    base = types.ModuleType("cycle33_pit_at_base")
    exec(compile(source, f"{BASE_COMMIT}:{REFERENCE_PATH}", "exec"), base.__dict__)
    cases = [(label, row) for label, row, receipts in forged_controls(historical) if receipts is None]
    cases.append(("synthetic positive control", positive_control(historical)[0]))
    out = []
    for label, row in cases:
        out.append({"control": label,
                    "at_base": "ADMITTED" if base.independent_row_class(dict(row))["independently_proven"] else "REFUSED",
                    "repaired": "ADMITTED" if repaired.independent_row_class(dict(row))["independently_proven"] else "REFUSED"})
    return {"base_commit": BASE_COMMIT, "path": REFERENCE_PATH, "cases": out}


def producer_rule_now() -> dict[str, Any]:
    """The current producer's verdict on the authority that produced the labels."""

    from aggie_analytics.cycle30 import pit_kernel

    freeze = [json.loads(line) for line in FREEZE_ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    issued = next(str(row.get("snapshot_timestamp_utc") or row.get("issued_at_utc")) for row in freeze
                  if row.get("snapshot_timestamp_utc") or row.get("issued_at_utc"))
    old_form = {"source_id": "WEEK1_2026_FORECAST_SUCCESSOR", "effective_utc": issued, "known_at_utc": issued,
                "receipt_sha256": sha256_file(FREEZE_ROWS), "classification": "FEATURE_TIME_AUTHORITY",
                "evidence_class": "FORECAST_FREEZE_RECEIPT", "source_publication_utc": issued}
    return {"authority_form_at_build": "forecast freeze issued time carried as source_publication_utc",
            "issued_utc": issued,
            "current_producer_verdict": pit_kernel.validate_row_authority(old_form, target_cutoff="2027-01-01T00:00:00Z"),
            "current_freeze_authority_carries_publication": "source_publication_utc" in pit_kernel.forecast_freeze_authority(
                {"snapshot_timestamp_utc": issued}, receipt_sha256=sha256_file(FREEZE_ROWS))}


def successor_rows(lines: list[bytes], freeze_sha: str) -> list[dict[str, Any]]:
    out = []
    for raw in lines:
        row = json.loads(raw)
        if row.get("authority_class") != PROVEN and row.get("row_verdict") != PROVEN:
            continue
        out.append({
            "label": LABEL, "cycle_number": 37, "attempt_number": 2,
            "canonical_game_id": row["canonical_game_id"], "season": row.get("season"),
            "predecessor_label": row.get("authority_class"), "predecessor_row_verdict": row.get("row_verdict"),
            "predecessor_line_sha256": sha256_bytes(raw.rstrip(b"\r\n")),
            "receipts_found": {
                "per_contest_forecast_freeze_receipt": {"path": str(FREEZE_ROWS), "sha256": freeze_sha,
                                                        "what_it_shows": "a forecast was frozen before kickoff"},
                "per_prior_publication_receipt": None,
            },
            "successor_state": "WITHDRAWN_NO_PER_PRIOR_PUBLICATION_RECEIPT",
            "reason": ("The label came from the producer rule before ff7859fa, which carried the forecast-freeze "
                       "issued time as the source publication time. A freeze receipt shows when a forecast was "
                       "frozen; it does not show when any of the row's prior results were published. No per-prior "
                       "publication receipt exists, so the label is withdrawn. The current producer returns "
                       "RETROSPECTIVE for the same authority."),
            "pit_admissible": False,
        })
    return out


def build(out_dir: Path) -> dict[str, Any]:
    before = sha256_file(KERNEL_ROWS)
    lines = [line for line in KERNEL_ROWS.read_bytes().splitlines(keepends=True) if line.strip()]
    rows = [json.loads(line) for line in lines]
    labelled = [row for row in rows if row.get("authority_class") == PROVEN or row.get("row_verdict") == PROVEN]
    historical = next(row for row in rows if row.get("season") == 2013)
    hits = discover()
    declarations = reconcile_declarations(hits)
    behaviour = probe(labelled, historical)
    freeze_sha = sha256_file(FREEZE_ROWS)
    successors = successor_rows(lines, freeze_sha)
    out_dir.mkdir(parents=True, exist_ok=True)
    successor_path = out_dir / "R37_08_PRODUCER_LABEL_SUCCESSOR.jsonl"
    _bas_atomic.write_text(successor_path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in successors), encoding="utf-8")
    after = sha256_file(KERNEL_ROWS)
    roles: dict[str, list[str]] = {}
    for path, (role, _) in DECLARED.items():
        roles.setdefault(role, []).append(path)
    summary = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirement": "R37-08", "rows": ["R37-08-AC04", "R37-08-AC10", "R37-08-CF-OBL-KERNEL-PRODUCER-RECEIPTS"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "predecessor": {"path": str(KERNEL_ROWS), "sha256_before": before, "sha256_after": after,
                        "bytes_preserved": before == after, "rows": len(rows), "labelled_rows": len(labelled)},
        "declarations": declarations,
        "consumers": {path: {"role": DECLARED[path][0], "basis": DECLARED[path][1], "lines": hits.get(path, [])[:6]}
                      for path in sorted(DECLARED)},
        "roles": {role: sorted(paths) for role, paths in sorted(roles.items())},
        "behavioural_probes": behaviour,
        "gates_pass": all(item["passes"] for item in behaviour.values()),
        "fit_consumers": {"train_seasons": "2013-2019", "eval_seasons": "2020-2023",
                          "labelled_rows_seasons": sorted({row.get("season") for row in labelled}),
                          "label_read_by_a_fit": False},
        "producer_rule_now": producer_rule_now(),
        "cycle33_reference_repair": reference_before_after(historical),
        "successor": {"path": str(successor_path), "rows": len(successors),
                      "states": sorted({row["successor_state"] for row in successors})},
        "independently_proven_pit_rows": 0,
    }
    _bas_atomic.write_text(out_dir / "R37_08_LABEL_CONSUMER_AUDIT.json", json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs")
    args = parser.parse_args(argv)
    summary = build(args.out)
    print(json.dumps({k: summary[k] for k in ("predecessor", "declarations", "gates_pass", "producer_rule_now",
                                               "successor")}, indent=1))
    for name, item in summary["behavioural_probes"].items():
        print(name, "admitted", len(item["labelled_rows_admitted"]), "errors", len(item["errors"]),
              [c["outcome"] for c in item["forged_controls"]], "positive", item["synthetic_positive_control"])
    return 0 if summary["gates_pass"] and summary["declarations"]["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
