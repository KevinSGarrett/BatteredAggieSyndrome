r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-12-AC06: bind ONE actionable approval request for the Family B lake
successor (CYCLE33-APPROVAL-LAKE-SUCCESSOR-001) to the exact source head,
predecessor and successor identities, the affected consumers, the rollback
and the evidence.

Every value in the request is read, not typed:

* identities come from the FAMILY_B_COMPOSED lane receipt and the isolated
  qualification artifact it names;
* the predecessor digests are the canonical bytes that qualification
  hashed before and after (and found unchanged);
* the affected consumers are every tracked module or test that imports one
  of the Family B modules, taken from the import graph;
* the source head is the repository HEAD this is generated at.

Requesting is all this does. It performs no activation, writes nothing to
the canonical lake or the repository, and the request states that only the
named approval, given explicitly by the owner, authorizes the change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from r37_14_domain_trace import import_graph, importers_of
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ROOT = Path(__file__).resolve().parents[2]
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
APPROVAL_ID = "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001"
FAMILY_B_MODULES = (
    "src/aggie_analytics/data/tamu_official_1998_2009_rejection_integrity.py",
    "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py",
    "src/aggie_analytics/data/tamu_official_1998_2009_structured_row_corpus.py",
)


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def build(lane_path: Path) -> dict[str, Any]:
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    if lane.get("result") != "PASS":
        raise SystemExit(f"the Family B lane is {lane.get('result')}, not PASS; no request is bound to it")
    qualification_path = Path(lane["qualification_artifact"])
    q = json.loads(qualification_path.read_text(encoding="utf-8"))
    binding = q["identity_binding"]
    cases = {c["case"]: c for c in q["cases"]}
    successor = cases["SUCCESSOR_VALIDATES_IN_ISOLATION"]["value"]
    if q.get("canonical_predecessor_bytes_unchanged") is not True:
        raise SystemExit("the qualification did not prove the predecessor bytes unchanged")
    if q.get("negative_controls_that_did_not_reject"):
        raise SystemExit("a negative control did not reject; no request is bound to this qualification")
    # R36-12: the unit is the composition, so the request binds the composed
    # upstream+downstream qualification too, and refuses without it.
    composed_path = Path(lane.get("composed_qualification_artifact") or "")
    if not composed_path.is_file():
        raise SystemExit("the lane carries no composed Family B qualification; no request is bound to it")
    cq = json.loads(composed_path.read_text(encoding="utf-8"))
    if cq.get("qualified_in_isolation") is not True:
        raise SystemExit("the composed qualification did not qualify in isolation")
    agreement = cq["identity_agreement"]
    rehearsal = cq["rollback_rehearsal"]

    tracked = git("ls-files").splitlines()
    imports, refs = import_graph(tracked)
    consumers: set[str] = set()
    tests: set[str] = set()
    for module in FAMILY_B_MODULES:
        c, t = importers_of(module, imports, refs)
        consumers.update(c)
        tests.update(t)

    predecessor = {path: digest for path, digest in q["canonical_bytes_before"].items()
                   if not path.startswith("MOUNTED_")}
    return {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-12-AC06",
        "approval_id": APPROVAL_ID,
        "requested_action": (
            "Activate the qualified, composed Family B successor in the canonical lake: materialize the "
            f"rejection ledger {binding['requested_for_activation']} as the mounted successor child and "
            f"re-pin the rejection-integrity contract and gate from the predecessor ledger "
            f"{binding['committed_gate_pins']} to it; materialize the downstream rejection-complete union "
            f"{agreement['downstream_union_identity']['published_by_manager']} with gate "
            f"{agreement['downstream_gate_identity']['published_by_manager']} under the declared-contract pin "
            "authority, changing the consumer default from LEGACY for these two artifacts only."
        ),
        "source": {"repository": str(ROOT), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                   "head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}")},
        "predecessor": {
            "ledger_identity": binding["committed_gate_pins"],
            "canonical_file_digests": predecessor,
            "mounted_successor_child_exists": False,
        },
        "successor": {
            "ledger_identity": successor["ledger_identity"],
            "gate_identity": successor["gate_identity"],
            "qualified_twice": cases.get("SUCCESSOR_VALIDATES_ON_REPLAY", {}).get("outcome") == "ACCEPTED",
            "negative_controls": {"declared": q["negative_controls_declared"],
                                  "rejected": q["negative_controls_that_rejected"]},
            "composed_downstream": {
                "union_identity": agreement["downstream_union_identity"]["validator_returned"],
                "gate_identity": agreement["downstream_gate_identity"]["validator_returned"],
                "identities_published_returned_and_independently_recomputed_agree": all(
                    v["all_three_agree"] for v in agreement.values()),
                "negative_controls": {"declared": cq["negative_controls_total"],
                                      "rejected": cq["negative_controls_rejected"],
                                      "rejected_by_an_incidental_exception":
                                          cq["controls_rejected_by_an_incidental_exception"]},
                "rollback_rehearsal_complete": rehearsal["complete"],
                "rolled_back_copy_behaves_like_the_mounted_configuration":
                    rehearsal["rolled_back_copy_behaves_like_the_mounted_configuration"],
            },
        },
        "canonical_main_note": rehearsal.get("canonical_main_note"),
        "affected_consumers": sorted(consumers),
        "affected_tests": sorted(tests),
        "rollback": [
            "Re-pin the rejection-integrity contract and gate to the predecessor ledger "
            f"{binding['committed_gate_pins']}; each predecessor file digest above is the exact target.",
            "Leave the content-addressed successor child unreferenced rather than deleting it; an "
            "unreferenced content-addressed directory changes no consumer's input.",
            "The consumer's default pin authority stays LEGACY until activation, so reverting the pins "
            "restores the predecessor behaviour without a code change.",
            "Re-pin the downstream rejection-complete gate to its branch-head predecessor bytes and restore the "
            "LEGACY pin authority; the downstream successor union child stays, unreferenced.",
            "Re-run the mounted Family B lane; it must return to its pre-activation state. The composed "
            "qualification rehearsed exactly this in isolation: after rollback both validators behaved as they do "
            "on the branch head against the canonical lake, and re-activation returned the same identities.",
        ],
        "evidence": [
            {"path": str(lane_path), "sha256": sha256_file(lane_path)},
            {"path": str(qualification_path), "sha256": sha256_file(qualification_path)},
            {"path": str(composed_path), "sha256": sha256_file(composed_path)},
        ],
        "preconditions_not_changed_by_this_request": [
            "No canonical byte is written by preparing this request.",
            "Protected lane stays RETAIN_PROTECTED_LANE_BLOCKED; activation is not scientific acceptance.",
            "The mounted Family B lane stays FAIL until the owner activates or rejects.",
        ],
        "authority": f"Only an explicit {APPROVAL_ID} from the owner authorizes this change.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def render(request: dict[str, Any]) -> str:
    lines = [
        f"# {LABEL} — Family B activation approval request",
        "",
        f"cycle_number=37 · attempt_number=2 · requirement R37-12-AC06 · approval `{request['approval_id']}`",
        "",
        "## Requested action",
        "",
        request["requested_action"],
        "",
        "## Exact source",
        "",
        f"- Branch `{request['source']['branch']}`, head `{request['source']['head']}`, "
        f"tree `{request['source']['tree']}`",
        "",
        "## Predecessor (what is canonical now)",
        "",
        f"- Ledger `{request['predecessor']['ledger_identity']}`; mounted successor child exists: "
        f"{request['predecessor']['mounted_successor_child_exists']}",
    ]
    lines += [f"- `{path}` sha256 `{digest}`" for path, digest in sorted(request["predecessor"]["canonical_file_digests"].items())]
    s = request["successor"]
    lines += [
        "",
        "## Successor (what activation would install)",
        "",
        f"- Ledger `{s['ledger_identity']}`, gate `{s['gate_identity']}`",
        f"- Accepted by the real validator in isolation and on replay: {s['qualified_twice']}",
        f"- Negative controls: {s['negative_controls']['rejected']} of {s['negative_controls']['declared']} rejected",
        f"- Composed downstream: union `{s['composed_downstream']['union_identity']}`, gate "
        f"`{s['composed_downstream']['gate_identity']}`; published, returned and independently recomputed "
        f"identities agree: {s['composed_downstream']['identities_published_returned_and_independently_recomputed_agree']}",
        f"- Composed negative controls: {s['composed_downstream']['negative_controls']['rejected']} of "
        f"{s['composed_downstream']['negative_controls']['declared']} rejected (by an incidental exception, "
        f"not an AuthorityViolation: {', '.join(s['composed_downstream']['negative_controls']['rejected_by_an_incidental_exception']) or 'none'})",
        f"- Rollback rehearsed in isolation: {s['composed_downstream']['rollback_rehearsal_complete']}",
        "",
        f"Note: {request.get('canonical_main_note')}",
        "",
        "## Affected consumers (from the import graph)",
        "",
    ]
    lines += [f"- `{c}`" for c in request["affected_consumers"]] or ["- none outside the modules themselves"]
    lines += ["", "Tests that exercise them:", ""] + [f"- `{t}`" for t in request["affected_tests"]]
    lines += ["", "## Rollback", ""] + [f"{i}. {step}" for i, step in enumerate(request["rollback"], 1)]
    lines += ["", "## Evidence", ""] + [f"- `{e['path']}` sha256 `{e['sha256']}`" for e in request["evidence"]]
    lines += ["", "## Not changed by this request", ""] + [f"- {p}" for p in request["preconditions_not_changed_by_this_request"]]
    lines += ["", f"**Authority:** {request['authority']}", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", type=Path, default=ATTEMPT / "evidence/lanes/family-b.json")
    parser.add_argument("--out-dir", type=Path, default=ATTEMPT)
    args = parser.parse_args(argv)
    request = build(args.lane)
    stem = "R37_12_FAMILY_B_ACTIVATION_APPROVAL_REQUEST"
    _bas_atomic.write_text(args.out_dir / f"{stem}.json", json.dumps(request, indent=2) + "\n", encoding="utf-8")
    _bas_atomic.write_text(args.out_dir / f"{stem}.md", render(request), encoding="utf-8")
    print("consumers:", len(request["affected_consumers"]), "tests:", len(request["affected_tests"]),
          "| successor ledger", request["successor"]["ledger_identity"][:12],
          "| predecessor", request["predecessor"]["ledger_identity"][:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
