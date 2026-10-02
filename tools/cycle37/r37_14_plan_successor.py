r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-14-AC05: implement the exact changed sections of the BAS-owned TP37 plan
in a PRIVATE successor, and nothing else.

The issued TP37 plan is an issuance input and is never written. This tool
reads it, checks it is the exact issued bytes, and writes a successor copy
under the attempt root in which:

* every section this attempt's evidence changes is replaced by its original
  text followed by an "Actual state" block generated from the evidence
  receipts -- the original words are kept, and every number in the block is
  read from a receipt, not typed;
* one section the requirement-link table found missing (TP37-N, W37R-29) is
  proposed from the issued contract's own text for R37-N, verbatim;
* every other section, and the original line endings, are byte-identical.

A private successor is not adoption. The receipt records the original and
successor digests, each changed section's before/after digest, and a
unified diff, so the manager can adopt, amend or reject each section
separately. External (All-22) plans are not touched here; they get owner
proposals (r37_13_cfip_proposals.py).
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
PLAN = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/TECHNICAL_REPAIR_AND_DATA_RELEASE_PLAN.md")
PLAN_SHA256 = "cb23070333cdd4ec4d1320c5274c2b54e27de9e086b2d4847fd37bc69406c40a"
CONTRACT = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle37/20260922T171601Z/cycle_contract.json")
HEADING = re.compile(r"^## (TP37-[0-9A-Z]+)\b")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_sections(text: str) -> list[tuple[str | None, str]]:
    """Split on level-2 TP37 headings; each piece keeps its own line endings."""

    pieces: list[tuple[str | None, str]] = []
    current_id: str | None = None
    buffer: list[str] = []
    for line in text.splitlines(keepends=True):
        match = HEADING.match(line)
        if match:
            pieces.append((current_id, "".join(buffer)))
            current_id, buffer = match.group(1), [line]
        else:
            buffer.append(line)
    pieces.append((current_id, "".join(buffer)))
    return [p for p in pieces if p[1]]


def apply_changes(text: str, appended: dict[str, str], inserted_after: dict[str, str]) -> str:
    """Append blocks to named sections and insert new sections after named ones.

    Everything not named is copied through unchanged. A named section that
    does not exist is an error, never a silent no-op.
    """

    newline = "\r\n" if "\r\n" in text else "\n"
    pieces = split_sections(text)
    present = {section for section, _ in pieces}
    for name in list(appended) + list(inserted_after):
        if name not in present:
            raise ValueError(f"section {name} is not in the plan")
    out = []
    for section, body in pieces:
        if section in appended:
            stripped = body.rstrip("\r\n")
            trailing = body[len(stripped):] or newline
            block = appended[section].replace("\n", newline)
            body = stripped + newline + newline + block.rstrip(newline) + trailing
        out.append(body)
        if section in inserted_after:
            block = inserted_after[section].replace("\n", newline)
            if not out[-1].endswith(newline * 2):
                out[-1] = out[-1].rstrip("\r\n") + newline + newline
            out.append(block.rstrip(newline) + newline + newline)
    return "".join(out)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def tp37_13_block(composition: dict[str, Any], proposals: dict[str, Any]) -> str:
    markers = ", ".join(f"{k} {v['marker']}" for k, v in sorted(proposals["proposals"].items()))
    lost = composition["lossless_envelope"]["lost_by_projection"]
    return (
        "### Actual state — Cycle #37 Attempt #2 (worker, private successor, not adopted)\n\n"
        f"- Released C01 wheel {composition['vector']['wheel_version']} (sha256 "
        f"{composition['vector']['wheel_sha256']}) composed with the BAS adapter "
        f"{composition['vector']['producer']}: {composition['positives_accepted_by_both']}/"
        f"{composition['positives']} positives accepted by both; {composition['negatives_caught_by_bas_adapter']}/"
        f"{composition['negatives']} negatives refused by BAS first; "
        f"{len(composition['negatives_caught_only_by_released_wheel'])} caught only by the owner schema.\n"
        f"- Lossless envelope retained; the reduced StaffSnapshotV1 projection drops {len(lost)} fields, "
        "each kept in the envelope.\n"
        "- Source schemes refused as F10 state for every intelligence contract in the released catalog.\n"
        f"- Section-bound CFIP proposals prepared with deterministic markers ({markers}). Not posted: "
        "the session's permission layer refused the external write; posting with readback remains "
        "the next step under recovery section 8.\n"
    )


def tp37_14_block(inventory: dict[str, Any], trace: dict[str, Any], jira: dict[str, Any]) -> str:
    ac01 = inventory["ac01_inventories"]
    ac02 = inventory["ac02_catalogs"]
    links = inventory["ac03_link_adjudication"]
    sections = inventory["ac03_section_extraction"]["per_source_class"]
    t = trace["trace"]
    resolved = sum(v for k, v in links["verdicts"].items() if k.startswith(("RESOLVED", "REGISTRY")))
    lines = [
        "### Actual state — Cycle #37 Attempt #2 (worker, private successor, not adopted)",
        "",
        f"- Inventories consumed with scope: {ac01['path_inventory']['rows']} tracked paths over "
        f"{ac01['path_inventory']['checkout_identities']} checkout identities; {ac01['plan_inventory']['rows']} "
        f"plan candidates, refreshed to {ac01['plan_refresh']['rows']}; "
        f"{ac01['governing_classification']['counts'].get('IN_NORMATIVE_CLOSURE', 0)} are in the normative "
        "closure, the rest are lexical candidates only.",
        f"- Catalogs preserved by digest: {ac02['crosswalk_rows']} crosswalk, {ac02['domain_rows']} domain, "
        f"{ac02['seed_rows']} seed rows; {len(ac02['domains_without_any_crosswalk_row'])} review domains "
        "have no crosswalk row.",
        f"- The {links['pairs']} heuristic links were re-derived from discovery-time bytes: {resolved} resolve "
        f"to a registered ID, {links['verdicts'].get('MALFORMED_TOKEN_EXTRACTION_ARTIFACT', 0)} are extraction "
        "artifacts (W37R-28); none is called semantically verified.",
        "- Sections extracted per source class: "
        + "; ".join(f"{k} {v.get('sections', 0)} sections / {v.get('statements', 0)} candidate statements"
                    for k, v in sorted(sections.items())) + ".",
        f"- Domain trace: {t['status_counts']}. Consumers and tests are derived from the import graph; "
        f"{len(t['test_runs'])} derived test files were run.",
        f"- Live/local Jira: {jira.get('canonical_with_live_status')} canonical records with live status, "
        f"mirror status stale {jira.get('mirror_status_stale')}, logical-state differences "
        f"{jira.get('logical_state_disagreements')} (safety-normalised by contract).",
        f"- Cycle 36 domain accounting misattributes {t['predecessor_touch_map']['misattributed']} of "
        f"{len(t['predecessor_touch_map']['rows'])} rows (W37R-25).",
        "",
        "Uncovered and partial domains, next deliverable and existing owner issue:",
        "",
        "| Domain | Status | Missing | Next deliverable | Owner issue |",
        "|---|---|---|---|---|",
    ]
    for row in t["uncovered_or_partial"]:
        lines.append(
            f"| {row['domain_id']} {row['domain']} | {row['status']} | {', '.join(row['missing'])} | "
            f"{row['next_deliverable']} | {row['owner_issue'] or 'none found; audit owner BAT-708'} |"
        )
    return "\n".join(lines) + "\n"


def tp37_n_section(contract: dict[str, Any]) -> str:
    requirement = next(r for r in contract["requirements"] if r["id"] == "R37-N")
    return (
        f"## TP37-N — {requirement['title']}\n\n"
        f"Implementation unit: R37-N. Existing Jira owner: {requirement.get('jira_key')}. Proposed by the "
        "worker because no controlling plan carries a TP37-N section (W37R-29); the text below is the "
        "issued contract's own, verbatim.\n\n"
        f"{requirement['original_meaning']}\n\n"
        f"Inherited: {', '.join(requirement.get('inherited_ids') or [])}.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=ATTEMPT / "private" / "plans")
    args = parser.parse_args(argv)

    raw = PLAN.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise SystemExit("the TP37 plan is not the issued bytes; refusing to derive a successor")
    original = raw.decode("utf-8")
    repairs = ATTEMPT / "evidence" / "repairs"
    composition = load(repairs / "R37_13_C01_COMPOSITION.json")
    proposals = load(ATTEMPT / "private" / "jira" / "CFIP_PROPOSALS.json")
    inventory = load(repairs / "R37_14_PLAN_INVENTORY.json")
    trace = load(repairs / "R37_14_DOMAIN_TRACE.json")
    jira = load(ATTEMPT / "private" / "jira" / "R37_14_JIRA_CONVERGENCE.json")
    contract = load(CONTRACT)

    appended = {"TP37-13": tp37_13_block(composition, proposals),
                "TP37-14": tp37_14_block(inventory, trace, jira)}
    inserted = {"TP37-16": tp37_n_section(contract)}
    successor = apply_changes(original, appended, inserted)

    before = dict(split_sections(original))
    after = dict(split_sections(successor))
    changed = []
    for name in sorted(set(before) | set(after), key=lambda s: str(s)):
        if before.get(name) != after.get(name):
            kind = ("ADDED" if name not in before else
                    "SEPARATOR_ONLY" if before[name].rstrip() == after[name].rstrip() else "CONTENT")
            changed.append({"section": name, "change": kind,
                            "original_sha256": sha256_text(before[name]) if name in before else None,
                            "successor_sha256": sha256_text(after[name]) if name in after else None})
    unchanged = [n for n in before if n not in {c["section"] for c in changed}]
    if any(before[n] != after.get(n) for n in unchanged):
        raise SystemExit("an unchanged section differs; refusing to write")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    successor_path = args.out_dir / "TP37_PRIVATE_SUCCESSOR.md"
    _bas_atomic.write_bytes(successor_path, successor.encode("utf-8"))
    diff = "".join(difflib.unified_diff(original.splitlines(keepends=True), successor.splitlines(keepends=True),
                                        fromfile="TECHNICAL_REPAIR_AND_DATA_RELEASE_PLAN.md (issued)",
                                        tofile="TP37_PRIVATE_SUCCESSOR.md"))
    _bas_atomic.write_bytes(args.out_dir / "TP37_PRIVATE_SUCCESSOR.diff", diff.encode("utf-8"))
    receipt = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-14-AC05",
        "original": {"path": str(PLAN), "sha256": PLAN_SHA256},
        "successor": {"path": str(successor_path), "sha256": hashlib.sha256(successor.encode("utf-8")).hexdigest()},
        "changed_sections": changed,
        "unchanged_sections_byte_identical": len(unchanged),
        "inputs": {name: {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for name, p in {
            "composition": repairs / "R37_13_C01_COMPOSITION.json",
            "proposals": ATTEMPT / "private/jira/CFIP_PROPOSALS.json",
            "inventory": repairs / "R37_14_PLAN_INVENTORY.json",
            "trace": repairs / "R37_14_DOMAIN_TRACE.json",
            "jira": ATTEMPT / "private/jira/R37_14_JIRA_CONVERGENCE.json",
            "contract": CONTRACT}.items()},
        "not_adoption": "A private successor under the attempt root. The issued plan is unchanged and "
                        "nothing here is adopted until the manager accepts a section.",
    }
    _bas_atomic.write_text(args.out_dir / "TP37_PRIVATE_SUCCESSOR_RECEIPT.json", json.dumps(receipt, indent=2) + "\n",
                                                                      encoding="utf-8")
    print("changed:", [(c["section"], c["change"]) for c in changed], "| unchanged byte-identical:", len(unchanged))
    print("successor:", successor_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
