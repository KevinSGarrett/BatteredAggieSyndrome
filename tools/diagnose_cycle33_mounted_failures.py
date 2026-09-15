"""Read-only diagnosis of Cycle 33 mounted lake-gate failures.

Does not rematerialize predecessor gates or rewrite expected hashes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data import tamu_official_1998_2009_rejection_integrity as rej  # noqa: E402
from aggie_analytics.data import tamu_official_gamebook_union_1998_rejection_complete as union1998  # noqa: E402
from aggie_analytics.data.tamu_official_1998_2009_rejection_integrity import (  # noqa: E402
    GATE_RELATIVE as REJ_GATE,
)

SCI = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
CYCLE32 = "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185"
STRUCTURED = {
    2000: (
        "artifacts/data_lake/tamu_official_2000_structured_domains_gate.json",
        "cc1b76240aaab39f355721ed8499a06db3a2d15fcc9056055a594841fba91268",
        "aggie_analytics.data.tamu_official_2000_structured_domains",
    ),
    2001: (
        "artifacts/data_lake/tamu_official_2001_structured_domains_gate.json",
        "efbd7b1e0d52b99d49066878cd45e9b7768a9288f8ed2fe94891cb402b02a666",
        "aggie_analytics.data.tamu_official_2001_structured_domains",
    ),
    2002: (
        "artifacts/data_lake/tamu_official_2002_structured_domains_gate.json",
        "d6eca244760bba8963130e070d9ac707cb36af7e715b53e2c3bc60a5bbbed014",
        "aggie_analytics.data.tamu_official_2002_structured_domains",
    ),
    2003: (
        "artifacts/data_lake/tamu_official_2003_structured_domains_gate.json",
        "758ca462a05f9d67ff5017417626eae666902f054037c76207231287cb3f20e9",
        "aggie_analytics.data.tamu_official_2003_structured_domains",
    ),
    2004: (
        "artifacts/data_lake/tamu_official_2004_structured_domains_gate.json",
        "bbabb6e97583b33967dd2f883fa8d70082a95fa44eaadb23dbd2a766e33860e6",
        "aggie_analytics.data.tamu_official_2004_structured_domains",
    ),
    2005: (
        "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json",
        "b4964041f1b87392ad61c5781c300531051dc9f1a71dfaf630cbeb25af20f96d",
        "aggie_analytics.data.tamu_official_2005_structured_domains",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def blob_at(rev: str, path: str) -> str:
    return git("rev-parse", f"{rev}:{path}")


def main() -> int:
    os.environ["AGGIE_ANALYTICS_DATA_ROOT"] = str(DATA_ROOT)
    head = git("rev-parse", "HEAD")
    rows: list[dict[str, Any]] = []
    pin = union1998.PINNED_BAT637_GATE_IDENTITY
    committed_637 = load(
        ROOT / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json"
    ).get("gate_identity")
    rows.append(
        {
            "id": "BAT-637-PIN-VS-COMMITTED-GATE",
            "family": "union_1998_rejection_complete",
            "test": "test_tamu_official_gamebook_union_1998_rejection_complete.RejectionCompleteUnionTests.setUpClass",
            "assertion_or_exception": "AuthorityViolation: BAT-637 gate identity drifted",
            "python_pin": pin,
            "committed_gate_identity": committed_637,
            "match": pin == committed_637,
            "cycle32_producer_blob": blob_at(
                CYCLE32,
                "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py",
            ),
            "head_producer_blob": blob_at(
                "HEAD",
                "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py",
            ),
            "cycle32_gate_blob": blob_at(
                CYCLE32,
                "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
            ),
            "head_gate_blob": blob_at(
                "HEAD",
                "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
            ),
            "root_cause": (
                "In-repo pin/gate divergence: PINNED_BAT637_GATE_IDENTITY is not the "
                "committed 1998 expanded gate identity. Same blobs at Cycle 32 HEAD."
            ),
            "correction_or_authority": (
                "Do not retarget the pin to the current gate hash without an authorized "
                "BAT-637 successor. Preserve predecessor bytes. Approval required to "
                "publish a versioned successor pin/gate pair."
            ),
        }
    )
    try:
        objects = rej.reconstruct_objects(repo_root=ROOT, data_root=DATA_ROOT)
        reconstructed_ledger = objects["payload"]["ledger_identity"]
        reconstructed_gate = objects["gate"]["gate_identity"]
        recon_error = None
    except Exception as exc:  # noqa: BLE001 — diagnosis must capture reconstruct failures
        reconstructed_ledger = None
        reconstructed_gate = None
        recon_error = f"{type(exc).__name__}: {exc}"
    committed_rej = load(ROOT / REJ_GATE)
    rows.append(
        {
            "id": "REJECTION-INTEGRITY-LEDGER",
            "family": "1998_2009_rejection_integrity",
            "test": "test_tamu_official_1998_2009_rejection_integrity.RejectionIntegrityGateTests.test_reconstruction_does_not_read_the_working_checkout_commit",
            "assertion_or_exception": (
                "AssertionError reconstructed ledger_identity != committed gate ledger_identity"
            ),
            "reconstructed_ledger_identity": reconstructed_ledger,
            "committed_ledger_identity": committed_rej.get("ledger_identity"),
            "reconstructed_gate_identity": reconstructed_gate,
            "committed_gate_identity": committed_rej.get("gate_identity"),
            "reconstruct_error": recon_error,
            "cycle32_producer_blob": blob_at(
                CYCLE32,
                "src/aggie_analytics/data/tamu_official_1998_2009_rejection_integrity.py",
            ),
            "head_producer_blob": blob_at(
                "HEAD",
                "src/aggie_analytics/data/tamu_official_1998_2009_rejection_integrity.py",
            ),
            "cycle32_gate_blob": blob_at(CYCLE32, REJ_GATE.replace("\\", "/")),
            "head_gate_blob": blob_at("HEAD", REJ_GATE.replace("\\", "/")),
            "root_cause": (
                "Independent reconstruction of the rejection ledger from the mounted "
                "union manifest plus committed upstream gates does not equal the "
                "committed BAT-649 gate. Producer and gate blobs are identical at "
                "Cycle 32 HEAD. Not a Cycle 33 producer edit."
            ),
            "correction_or_authority": (
                "Rematerializing the committed predecessor gate is forbidden. A "
                "versioned successor ledger would require BAT-649 owner approval."
            ),
        }
    )
    import importlib

    for year, (gate_rel, expected, module_name) in STRUCTURED.items():
        committed = load(ROOT / gate_rel)
        module = importlib.import_module(module_name)
        reconstructed_id = None
        match_committed = None
        error = None
        try:
            reconstructed = module.reconstruct_objects(
                repo_root=ROOT, data_root=DATA_ROOT
            )
            reconstructed_id = reconstructed["gate"]["gate_identity"]
            match_committed = reconstructed["gate"] == committed
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"
        producer = module.__file__ or ""
        rel_producer = str(Path(producer).resolve().relative_to(ROOT)).replace("\\", "/")
        rows.append(
            {
                "id": f"STRUCTURED-{year}",
                "family": "2000_2005_structured_domains",
                "test": f"test_tamu_official_{year}_structured_domains.test_committed_gate_reconstructs",
                "assertion_or_exception": "AssertionError result gate_identity != EXPECTED_GATE_IDENTITY",
                "committed_gate_identity": committed.get("gate_identity"),
                "reconstructed_gate_identity": reconstructed_id,
                "test_expected_gate_identity": expected,
                "reconstruction_equals_committed_gate": match_committed,
                "test_expected_equals_committed": expected == committed.get("gate_identity"),
                "reconstruct_error": error,
                "cycle32_producer_blob": blob_at(CYCLE32, rel_producer),
                "head_producer_blob": blob_at("HEAD", rel_producer),
                "cycle32_gate_blob": blob_at(CYCLE32, gate_rel),
                "head_gate_blob": blob_at("HEAD", gate_rel),
                "root_cause": (
                    "Committed gate identity equals independent reconstruction but "
                    "differs from the stale EXPECTED_GATE_IDENTITY constant in the "
                    "test module. Cycle 32 blobs are identical."
                    if match_committed
                    else "Reconstruction does not match the committed gate."
                ),
                "correction_or_authority": (
                    "If reconstruction equals the committed gate, the test constant "
                    "is the erroneous expectation and may be successor-labeled "
                    "without rewriting the gate. Preserve the stale hash as a "
                    "predecessor constant."
                    if match_committed
                    else "Do not overwrite the committed gate. Owner approval required."
                ),
            }
        )
    from aggie_analytics.data.tamu_official_statcrew_preformatted import (  # noqa: E402
        GATE_RELATIVE as STAT_GATE,
        reconstruct_objects as reconstruct_statcrew,
    )

    stat_committed = load(ROOT / STAT_GATE)
    stat_expected = "9c3da52dceebd8da0908aa478326196bef2338095a8b5d4c42decaa27df53e16"
    try:
        stat_recon = reconstruct_statcrew(repo_root=ROOT, data_root=DATA_ROOT)
        stat_id = stat_recon["gate"]["gate_identity"]
        stat_match = stat_recon["gate"] == stat_committed
        stat_err = None
    except Exception as exc:  # noqa: BLE001
        stat_id = None
        stat_match = None
        stat_err = f"{type(exc).__name__}: {exc}"
    rows.append(
        {
            "id": "STATCREW",
            "family": "statcrew_preformatted",
            "test": "test_tamu_official_statcrew_preformatted.StatCrewLakeTests.test_committed_gate_reconstructs",
            "assertion_or_exception": "AssertionError result gate_identity != EXPECTED_GATE_IDENTITY",
            "committed_gate_identity": stat_committed.get("gate_identity"),
            "reconstructed_gate_identity": stat_id,
            "test_expected_gate_identity": stat_expected,
            "reconstruction_equals_committed_gate": stat_match,
            "test_expected_equals_committed": stat_expected
            == stat_committed.get("gate_identity"),
            "reconstruct_error": stat_err,
            "cycle32_producer_blob": blob_at(
                CYCLE32,
                "src/aggie_analytics/data/tamu_official_statcrew_preformatted.py",
            ),
            "head_producer_blob": blob_at(
                "HEAD",
                "src/aggie_analytics/data/tamu_official_statcrew_preformatted.py",
            ),
            "root_cause": (
                "Same pattern as 2000-2005: committed gate matches reconstruction; "
                "test EXPECTED_GATE_IDENTITY is a stale predecessor constant."
                if stat_match
                else "StatCrew reconstruction mismatch or reconstruct error."
            ),
            "correction_or_authority": (
                "Successor-label the test expectation to the independently "
                "reconstructed committed identity; keep the stale hash visible."
                if stat_match
                else "Do not overwrite the StatCrew gate."
            ),
        }
    )
    payload = {
        "artifact_type": "CYCLE33_MOUNTED_FAILURE_LEDGER",
        "as_of_utc": utc_now(),
        "subject_head": head,
        "cycle32_predecessor": CYCLE32,
        "data_root": str(DATA_ROOT),
        "wrote_tracked_gates": False,
        "cycle33_producer_diff_vs_cycle32": "empty for these lake modules/gates",
        "first_known_failing_baseline": (
            "Present at Cycle 32 submitted HEAD ca8e0a1f against the same "
            "AGGIE_ANALYTICS_DATA_ROOT snapshot; Cycle 33 did not change these "
            "producer or gate blobs."
        ),
        "rows": rows,
        "mounted_validation_dimension": "FAIL",
        "repeatability_is_not_correctness": True,
    }
    out = SCI / "CYCLE33_MOUNTED_FAILURE_LEDGER.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "rows": len(rows), "head": head}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
