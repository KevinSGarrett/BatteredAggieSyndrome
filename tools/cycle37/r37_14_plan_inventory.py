r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-14-AC01..AC03: consume the manager's plan inventories with their
actual scope, preserve the requirement/domain catalogs exactly, extract
section-level requirement statements from the controlling sources, and
adjudicate the 8111 old heuristic plan links one by one.

What each input is, and what it is not:

* ``SYSTEM_PATH_INVENTORY`` (Cycle 36, 15402 rows) is a census of tracked
  paths across 13 checkout identities. ``PLAN_CANDIDATE_INVENTORY`` (2828
  rows) is a lexical census of files that look like plans. The Cycle 37
  refresh extends the plan census to 4555. None of them says a file
  governs anything; this tool keeps that visible by classifying every
  candidate against the manager's explicit normative-source closure.
* ``PLAN_DISCOVERY_INDEX`` (Cycle 32, 902 files) paired each file with the
  requirement-shaped tokens it contains -- 8111 (file, token) pairs. A
  pair is a lexical co-occurrence. This tool re-derives every pair from
  bytes (the discovery-time bytes where history still holds them), checks
  the token against the registry that defines its family, and records
  where in the file the token sits. That is an adjudication of whether the
  link is real and what kind of link it is. It is NOT a judgement that the
  file governs the requirement, and no row says so: every row carries
  ``semantic_relevance = NOT_ADJUDICATED``.
* Section extraction splits each controlling source into sections and
  lists the statements that carry normative language. A statement found
  that way is a candidate requirement located to a section, not an
  accepted requirement; its key is a content digest, not a new ID.

Reads only. Output goes to the evidence directory named by ``--out-dir``.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
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

#: Token family -> (registry path relative to the repository, ID column).
REGISTRIES = {
    "REQ": ("governance/REQUIREMENTS_INDEX.csv", "requirement_id", "status"),
    "AC": ("governance/ACCEPTANCE_CONTROL_CATALOG.csv", "control_id", "current_status"),
    "THR": ("governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv", "threshold_id", "status"),
    "DOM": ("docs/data_research/w06/DATA_DOMAIN_COVERAGE_MATRIX.csv", "domain_id", "confidence"),
}
CANONICAL_TOKEN = re.compile(r"^(REQ|AC|THR|DOM)-\d{3}$")

#: Normative language that marks a statement as a candidate requirement.
NORMATIVE = re.compile(
    r"\b(must|shall|required|requires|require|never|do not|does not|don't|may not|"
    r"cannot|can't|must not|forbidden|prohibited|reject|rejects|refuse|refuses|"
    r"fail[- ]closed|mandatory|only if|no\s+\w+\s+(?:is|are)\s+(?:allowed|permitted|authori[sz]ed))\b",
    re.IGNORECASE,
)

#: Identifier families worth recording per section. Recorded as found; a
#: match is a reference, never a resolution.
ID_FAMILIES = {
    "R_REQUIREMENT": r"\bR3\d-(?:\d\d|[SNI])(?:-AC\d\d)?\b",
    "TP_SECTION": r"\bTP3\d-(?:\d\d|[SNI])\b",
    "REQ": r"\bREQ-\d{3}\b",
    "AC": r"\bAC-\d{3}\b",
    "THR": r"\bTHR-\d{3}\b",
    "DOM": r"\bDOM-\d{3}\b",
    "REVIEW_DOMAIN": r"\bD(?:[0-4]\d|50|99)\b",
    "JIRA_BAT": r"\bBAT-\d+\b",
    "JIRA_CFIP": r"\bCFIP-\d+\b",
    "FINDING": r"\b(?:MF3\d|W37R|F3\d)-\d\d\b",
    "OBLIGATION": r"\bOBL_[A-Z0-9_]+\b",
    "ADR": r"\bADR-\d+\b",
    "RISK": r"\bRISK-\d+\b",
}
ID_PATTERNS = {name: re.compile(p) for name, p in ID_FAMILIES.items()}

TEXT_KEYS = ("statement", "work", "acceptance", "requirement", "description",
             "original_meaning", "original_statement", "criterion", "title",
             "text", "summary", "meaning", "rule", "positive", "negative")
ID_KEYS = ("id", "requirement_id", "control_id", "finding_id", "obligation_id",
           "domain_id", "threshold_id", "item_id", "row_id", "key")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False).encode("utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class GitBlobs:
    """Read blobs from one repository without touching its working tree."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def read(self, spec: str) -> bytes | None:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(spec.encode("utf-8") + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode("utf-8", "replace")
        if header.rstrip().endswith("missing") or not header.strip():
            return None
        size = int(header.split()[2])
        data = self.proc.stdout.read(size)
        self.proc.stdout.read(1)
        return data

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.wait(timeout=60)
        if self.proc.stdout:
            self.proc.stdout.close()


def git_lines(repo: Path, *args: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                         check=True, encoding="utf-8", errors="replace")
    return [line for line in out.stdout.splitlines() if line.strip()]


def decode(data: bytes) -> str:
    return data.decode("utf-8-sig", errors="replace")


# --------------------------------------------------------------------- AC01
def consume_inventories(args: argparse.Namespace, closure_paths: set[str]) -> dict[str, Any]:
    paths = load_json(args.path_inventory)
    plans = load_json(args.plan_inventory)
    refresh = load_json(args.plan_refresh)
    path_refresh = load_json(args.path_refresh)

    by_identity = collections.OrderedDict()
    for row in paths:
        slot = by_identity.setdefault(row["repo"], {"paths": 0, "hashed": 0, "absent": 0})
        slot["paths"] += 1
        slot["hashed"] += 1 if "sha256" in row else 0
        slot["absent"] += 0 if row.get("exists") else 1
    identities = list(by_identity)

    def identity_of(path: str) -> str:
        best = ""
        for ident in identities:
            if path.lower().startswith(ident.lower() + "\\") and len(ident) > len(best):
                best = ident
        return best or "OUTSIDE_INVENTORIED_IDENTITIES"

    plans_by_identity = collections.Counter(identity_of(p["path"]) for p in plans)
    refresh_rows = refresh["plans"]
    prior_paths = {p["path"] for p in plans}
    refresh_paths = {p["path"] for p in refresh_rows}
    comparison = collections.Counter(p.get("comparison") for p in refresh_rows)

    # Re-hash every refreshed candidate now. The manager's refresh is a
    # reading at one instant; this is a second, independent reading.
    drift = collections.Counter()
    drift_rows = []
    for row in refresh_rows:
        path = Path(row["path"])
        if not path.is_file():
            state = "ABSENT_NOW"
        else:
            state = ("MATCHES_REFRESH" if sha256_bytes(path.read_bytes()) == row.get("current_sha256")
                     else "CHANGED_SINCE_REFRESH")
        drift[state] += 1
        if state != "MATCHES_REFRESH":
            drift_rows.append({"path": row["path"], "state": state})

    lowered_closure = {p.lower() for p in closure_paths}
    governing = collections.Counter(
        "IN_NORMATIVE_CLOSURE" if p["path"].lower() in lowered_closure else "LEXICAL_CANDIDATE_ONLY"
        for p in refresh_rows
    )

    refreshed_identities = {r["path"]: r for r in path_refresh["repositories"]}
    refreshed_paths = collections.Counter(r["repository"] for r in path_refresh["paths"])
    identity_deltas = {
        ident: {"inventory": (by_identity.get(ident) or {}).get("paths", 0),
                "refresh_tracked_count": (refreshed_identities.get(ident) or {}).get("tracked_count"),
                "refresh_path_rows": refreshed_paths.get(ident, 0)}
        for ident in sorted(set(by_identity) | set(refreshed_identities))
    }
    return {
        "path_inventory": {
            "source": str(args.path_inventory),
            "sha256": sha256_bytes(args.path_inventory.read_bytes()),
            "rows": len(paths),
            "checkout_identities": len(identities),
            "by_identity": by_identity,
            "scope_note": (
                "Tracked-path census only. Content digests exist for the Cycle 36 "
                "worktree identity alone; the other twelve identities are path "
                "listings. One path is recorded absent."
            ),
        },
        "path_refresh": {
            "source": str(args.path_refresh),
            "observed_at": path_refresh.get("observed_at"),
            "identities": len(refreshed_identities),
            "tracked_count_sum": sum(int(r["tracked_count"]) for r in refreshed_identities.values()),
            "path_rows": len(path_refresh["paths"]),
            "identities_new_since_inventory": sorted(
                k for k in refreshed_identities if k not in by_identity),
            "identities_dropped_since_inventory": sorted(
                k for k in by_identity if k not in refreshed_identities),
            "per_identity": identity_deltas,
            "scope_note": (
                "The 15402 figure is the Cycle 36 census over 13 identities. The "
                "Cycle 37 refresh adds the cycle37-integration worktree as a 14th "
                "identity, so its sum is larger; neither is a count of governing files."
            ),
        },
        "plan_inventory": {
            "source": str(args.plan_inventory),
            "sha256": sha256_bytes(args.plan_inventory.read_bytes()),
            "rows": len(plans),
            "states": dict(collections.Counter(p["state"] for p in plans)),
            "headings_recorded": sum(len(p.get("headings") or []) for p in plans),
            "by_identity": dict(plans_by_identity.most_common()),
            "rows_with_head": sum(1 for p in plans if p.get("head")),
        },
        "plan_refresh": {
            "source": str(args.plan_refresh),
            "rows": len(refresh_rows),
            "comparison": dict(comparison),
            "every_prior_path_retained": prior_paths <= refresh_paths,
            "prior_paths_missing_from_refresh": sorted(prior_paths - refresh_paths)[:50],
            "independent_rehash_now": dict(drift),
            "rehash_differences": drift_rows[:200],
        },
        "governing_classification": {
            "rule": (
                "A candidate is governing only if the manager's explicit normative "
                "source closure names its exact path. Everything else is a lexical "
                "plan candidate: discovered, retained, and not a requirement source."
            ),
            "counts": dict(governing),
        },
    }


# --------------------------------------------------------------------- AC02
def preserve_catalogs(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    refresh = load_json(args.domain_refresh)
    catalogs = refresh["retained_catalogs"]
    exact = refresh["exact_sets"]
    crosswalk = catalogs["technical_crosswalk"]
    domains = catalogs["domains"]
    seeds = catalogs["current_seeds"]
    domain_ids = [d["domain_id"] for d in domains]
    problems = []

    if [r["source_requirement_id"] for r in crosswalk] != exact["crosswalk"]:
        problems.append("crosswalk rows do not equal the exact crosswalk set in order")
    if domain_ids != exact["domains"]:
        problems.append("domain rows do not equal the exact domain set in order")
    if [s["requirement_id"] for s in seeds] != exact["current_seed"]:
        problems.append("seed rows do not equal the exact seed set in order")

    unresolved_domain_refs = []
    for row in crosswalk:
        for ref in [x.strip() for x in str(row.get("review_domain_ids") or "").split(";") if x.strip()]:
            if ref not in domain_ids:
                unresolved_domain_refs.append({"crosswalk": row["source_requirement_id"], "ref": ref})
    unmapped_crosswalk = [r["source_requirement_id"] for r in crosswalk if not r.get("review_domain_ids")]
    covered = {ref for row in crosswalk
               for ref in str(row.get("review_domain_ids") or "").split(";") if ref.strip()}
    domains_without_crosswalk = [d for d in domain_ids if d not in covered]

    matrix_path = repo / REGISTRIES["DOM"][0]
    with matrix_path.open(encoding="utf-8") as handle:
        matrix = {r["domain_id"]: r for r in csv.DictReader(handle)}
    label_mismatch = [
        {"id": r["source_requirement_id"], "crosswalk": r["source_requirement"],
         "matrix": (matrix.get(r["source_requirement_id"]) or {}).get("domain")}
        for r in crosswalk
        if (matrix.get(r["source_requirement_id"]) or {}).get("domain") != r["source_requirement"]
    ]

    prior_accounting = load_json(args.domain_accounting)["domains"]
    prior_mismatch = [
        {"id": p["domain_id"], "prior": p["domain"],
         "current": next((d["domain"] for d in domains if d["domain_id"] == p["domain_id"]), None)}
        for p in prior_accounting
        if next((d["domain"] for d in domains if d["domain_id"] == p["domain_id"]), None) != p["domain"]
    ]

    seed_drift = []
    for seed in seeds:
        source = Path(seed.get("source_path") or "")
        if not source.is_file():
            seed_drift.append({"id": seed["requirement_id"], "state": "SOURCE_ABSENT"})
        elif sha256_bytes(source.read_bytes()) != seed.get("source_sha256"):
            seed_drift.append({"id": seed["requirement_id"], "state": "SOURCE_CHANGED"})

    return {
        "source": str(args.domain_refresh),
        "crosswalk_rows": len(crosswalk),
        "domain_rows": len(domains),
        "seed_rows": len(seeds),
        "row_digests": {
            "crosswalk": {r["source_requirement_id"]: sha256_json(r) for r in crosswalk},
            "domains": {d["domain_id"]: sha256_json(d) for d in domains},
            "seeds": {s["requirement_id"]: sha256_json(s) for s in seeds},
        },
        "set_digests": {
            "crosswalk": sha256_json(crosswalk),
            "domains": sha256_json(domains),
            "seeds": sha256_json(seeds),
        },
        "exact_set_problems": problems,
        "crosswalk_refs_unresolved": unresolved_domain_refs,
        "crosswalk_rows_without_domain": unmapped_crosswalk,
        "domains_without_any_crosswalk_row": domains_without_crosswalk,
        "crosswalk_label_vs_repository_matrix": {
            "matrix": str(matrix_path.relative_to(repo)),
            "mismatches": label_mismatch,
        },
        "domains_vs_cycle36_accounting_mismatches": prior_mismatch,
        "seed_source_drift": seed_drift,
        "preserved": not problems and not unresolved_domain_refs and not prior_mismatch,
    }


# ------------------------------------------------------------ AC03 links
def load_registries(repo: Path) -> dict[str, dict[str, dict[str, str]]]:
    out = {}
    for family, (rel, id_col, _) in REGISTRIES.items():
        with (repo / rel).open(encoding="utf-8") as handle:
            out[family] = {row[id_col]: row for row in csv.DictReader(handle)}
    return out


def token_regex(token: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(token) + r"(?![A-Za-z0-9_])")


def path_kind(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("governance/") or p.startswith("configs/"):
        return "TRACEABILITY_OR_CONFIG_REGISTRY"
    if p.startswith("tests/"):
        return "TEST_REFERENCE"
    if p.startswith("src/") or p.startswith("tools/") or p.endswith(".py"):
        return "IMPLEMENTATION_REFERENCE"
    if p.startswith("artifacts/"):
        return "EVIDENCE_ARTIFACT_REFERENCE"
    if p.startswith("instructions/"):
        return "INSTRUCTION_REFERENCE"
    if p.startswith("docs/"):
        return "PLAN_OR_DOC_NARRATIVE"
    return "OTHER_REFERENCE"


def occurrence_contexts(path: str, text: str, token: str) -> list[str]:
    """Where in the file the token sits, by the file's own structure."""

    rx = token_regex(token)
    contexts: list[str] = []
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        reader = csv.reader(io.StringIO(text))
        header = next(reader, [])
        for row in reader:
            for index, cell in enumerate(row):
                if rx.search(cell):
                    column = header[index] if index < len(header) else f"col{index}"
                    contexts.append("CSV_KEY_COLUMN" if index == 0 else f"CSV_COLUMN:{column}")
    elif suffix == ".json":
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if data is None:
            contexts.extend("JSON_UNPARSED" for _ in rx.finditer(text))
        else:
            def walk(node: Any, key: str) -> None:
                if isinstance(node, dict):
                    for k, v in node.items():
                        if rx.search(str(k)):
                            contexts.append("JSON_OBJECT_KEY")
                        walk(v, str(k))
                elif isinstance(node, list):
                    for v in node:
                        walk(v, key)
                elif isinstance(node, str) and rx.search(node):
                    contexts.append("JSON_ID_FIELD" if key in ID_KEYS or key.endswith("_id")
                                    else f"JSON_VALUE:{key}")
            walk(data, "")
    elif suffix in (".md", ".txt"):
        fenced = False
        for line in text.splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
            if rx.search(line):
                if fenced:
                    contexts.append("MD_CODE_BLOCK")
                elif re.match(r"^\s{0,3}#{1,6}\s", line):
                    contexts.append("MD_HEADING")
                elif line.lstrip().startswith("|"):
                    contexts.append("MD_TABLE_ROW")
                elif re.match(r"^\s*(?:[-*+]|\d+[.)])\s", line):
                    contexts.append("MD_LIST_ITEM")
                else:
                    contexts.append("MD_PROSE")
    else:
        contexts.extend(f"TEXT:{suffix or 'none'}" for _ in rx.finditer(text))
    return contexts


def discovery_bytes(repo: Path, blobs: GitBlobs, path: str, digest: str,
                    head_bytes: bytes | None) -> tuple[bytes | None, str | None]:
    """The bytes the discovery index hashed, recovered from history if needed."""

    if head_bytes is not None and sha256_bytes(head_bytes) == digest:
        return head_bytes, "HEAD"
    for commit in git_lines(repo, "log", "--format=%H", "--", path):
        data = blobs.read(f"{commit}:{path}")
        if data is not None and sha256_bytes(data) == digest:
            return data, commit
    return None, None


def adjudicate_links(args: argparse.Namespace, repo: Path, out_dir: Path) -> dict[str, Any]:
    index = load_json(args.discovery_index)
    registries = load_registries(repo)
    registry_paths = {family: rel for family, (rel, _, _) in REGISTRIES.items()}
    head = git_lines(repo, "rev-parse", "HEAD")[0]
    blobs = GitBlobs(repo)
    counts: collections.Counter[str] = collections.Counter()
    by_kind: collections.Counter[tuple[str, str]] = collections.Counter()
    file_states: collections.Counter[str] = collections.Counter()
    reproduced = collections.Counter()
    pairs = 0
    rows_path = out_dir / "R37_14_LINK_ADJUDICATION.jsonl"
    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as sink:
        for entry in index:
            path = entry["path"]
            head_bytes = blobs.read(f"HEAD:{path}")
            then_bytes, then_source = discovery_bytes(repo, blobs, path, entry["sha256"], head_bytes)
            if head_bytes is None:
                file_state = "ABSENT_AT_HEAD"
            elif then_source == "HEAD":
                file_state = "UNCHANGED_SINCE_DISCOVERY"
            else:
                file_state = "CHANGED_SINCE_DISCOVERY"
            file_states[file_state] += 1
            head_text = decode(head_bytes) if head_bytes is not None else ""
            then_text = decode(then_bytes) if then_bytes is not None else None
            kind = path_kind(path)
            for token in entry["tokens"]:
                pairs += 1
                rx = token_regex(token)
                family = token.split("-", 1)[0]
                present_then = None if then_text is None else bool(rx.search(then_text))
                present_now = bool(rx.search(head_text)) if head_bytes is not None else False
                reproduced["REPRODUCED" if present_then else
                           ("DISCOVERY_BYTES_UNRECOVERABLE" if present_then is None
                            else "NOT_REPRODUCED")] += 1
                registry_row = registries.get(family, {}).get(token)
                contexts = occurrence_contexts(path, head_text, token) if present_now else []
                if not CANONICAL_TOKEN.match(token):
                    verdict = "MALFORMED_TOKEN_EXTRACTION_ARTIFACT"
                elif present_then is False:
                    verdict = "NOT_REPRODUCED_AT_DISCOVERY_BYTES"
                elif head_bytes is None:
                    verdict = "FILE_ABSENT_AT_HEAD"
                elif not present_now:
                    verdict = "TOKEN_REMOVED_AT_HEAD"
                elif registry_row is None:
                    verdict = "UNRESOLVED_ID_NOT_IN_REGISTRY"
                elif path == registry_paths.get(family) and "CSV_KEY_COLUMN" in contexts:
                    verdict = "REGISTRY_DEFINITION"
                elif any(c in ("CSV_KEY_COLUMN", "JSON_ID_FIELD", "JSON_OBJECT_KEY") for c in contexts):
                    verdict = "RESOLVED_KEYED_TRACE_ROW"
                elif any(c.startswith(("CSV_COLUMN", "JSON_VALUE")) for c in contexts):
                    verdict = "RESOLVED_STRUCTURED_CROSS_REFERENCE"
                else:
                    verdict = "RESOLVED_TEXT_REFERENCE"
                counts[verdict] += 1
                by_kind[(kind, verdict)] += 1
                sink.write(json.dumps({
                    "path": path, "token": token, "family": family,
                    "discovery_sha256": entry["sha256"],
                    "discovery_bytes_source": then_source,
                    "file_state": file_state, "path_kind": kind,
                    "present_at_discovery_bytes": present_then,
                    "present_at_head": present_now,
                    "registry": registry_paths.get(family),
                    "registry_status": (registry_row or {}).get(REGISTRIES.get(family, ("", "", ""))[2])
                    if registry_row else None,
                    "head_contexts": dict(collections.Counter(contexts)),
                    "verdict": verdict,
                    "semantic_relevance": "NOT_ADJUDICATED",
                }, sort_keys=True, ensure_ascii=False) + "\n")
    blobs.close()
    return {
        "source": str(args.discovery_index),
        "source_sha256": sha256_bytes(args.discovery_index.read_bytes()),
        "head": head,
        "files": len(index),
        "pairs": pairs,
        "file_states": dict(file_states),
        "reproduction_at_discovery_bytes": dict(reproduced),
        "verdicts": dict(counts.most_common()),
        "verdicts_by_path_kind": {f"{k} | {v}": n for (k, v), n in sorted(by_kind.items())},
        "rows": str(rows_path),
        "rows_sha256": sha256_bytes(rows_path.read_bytes()),
        "boundary": (
            "Every pair was re-derived from bytes and adjudicated as a link. "
            "Whether a file GOVERNS the requirement a token names is not "
            "decided by any verdict here: semantic_relevance is NOT_ADJUDICATED "
            "on all rows, and only a registry definition row is authoritative "
            "for the ID's meaning."
        ),
    }


# --------------------------------------------------------- AC03 sections
def md_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    current = {"heading_path": ["(preamble)"], "level": 0, "start": 1, "lines": []}
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        match = None if fenced else re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if match:
            sections.append(current)
            level = len(match.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, match.group(2).strip()))
            current = {"heading_path": [h for _, h in stack], "level": level,
                       "start": number, "lines": []}
        else:
            current["lines"].append(line)
    sections.append(current)
    return [s for s in sections if s["level"] or any(text.strip() for text in s["lines"])]


def md_units(lines: list[str]) -> list[str]:
    """Paragraphs and list items, each a unit a statement can live in."""

    units: list[str] = []
    buffer: list[str] = []
    fenced = False

    def flush() -> None:
        if buffer:
            units.append(" ".join(part.strip() for part in buffer).strip())
            buffer.clear()

    for line in lines:
        if line.lstrip().startswith("```"):
            flush()
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.strip():
            flush()
        elif re.match(r"^\s*(?:[-*+]|\d+[.)])\s", line) or line.lstrip().startswith("|"):
            flush()
            buffer.append(line)
        else:
            buffer.append(line)
    flush()
    return [u for u in units if u]


def ids_in(text: str) -> dict[str, list[str]]:
    found = {}
    for name, rx in ID_PATTERNS.items():
        hits = sorted(set(rx.findall(text)))
        if hits:
            found[name] = hits
    return found


def json_requirement_rows(data: Any) -> Iterable[tuple[str, str, str]]:
    def walk(node: Any, pointer: str) -> Iterable[tuple[str, str, str]]:
        if isinstance(node, dict):
            ident = next((str(node[k]) for k in ID_KEYS if isinstance(node.get(k), (str, int))), None)
            texts = [f"{k}: {node[k]}" for k in TEXT_KEYS if isinstance(node.get(k), str) and node[k].strip()]
            if ident and texts:
                yield pointer or "/", ident, " | ".join(texts)
            for k, v in node.items():
                yield from walk(v, f"{pointer}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{pointer}/{i}")
    yield from walk(data, "")


def extract_source(source_id: str, source_class: str, path: Path, text: str,
                   sections_sink: Any, statements_sink: Any) -> dict[str, int]:
    tally = collections.Counter()
    suffix = path.suffix.lower()
    if suffix == ".md":
        for order, section in enumerate(md_sections(text)):
            body = "\n".join(section["lines"])
            units = md_units(section["lines"])
            normative = [u for u in units if NORMATIVE.search(u)]
            section_key = sha256_json([source_id, section["heading_path"], body])[:24]
            sections_sink.write(json.dumps({
                "source_id": source_id, "source_class": source_class, "path": str(path),
                "section_key": section_key, "order": order,
                "heading_path": section["heading_path"], "start_line": section["start"],
                "section_sha256": sha256_bytes(body.encode("utf-8")),
                "units": len(units), "normative_statements": len(normative),
                "ids": ids_in(section["heading_path"][-1] + "\n" + body),
                "extraction": "SECTION_EXTRACTED",
            }, sort_keys=True, ensure_ascii=False) + "\n")
            tally["sections"] += 1
            for statement in normative:
                statements_sink.write(json.dumps({
                    "source_id": source_id, "source_class": source_class,
                    "section_key": section_key, "heading_path": section["heading_path"],
                    "statement_key": sha256_json([section_key, statement])[:24],
                    "statement": statement, "ids": ids_in(statement),
                    "state": "CANDIDATE_REQUIREMENT_NOT_ADJUDICATED",
                }, sort_keys=True, ensure_ascii=False) + "\n")
                tally["statements"] += 1
    elif suffix == ".json":
        try:
            data = json.loads(text)
        except ValueError:
            tally["unparsed"] += 1
            return dict(tally)
        for pointer, ident, body in json_requirement_rows(data):
            section_key = sha256_json([source_id, pointer, body])[:24]
            sections_sink.write(json.dumps({
                "source_id": source_id, "source_class": source_class, "path": str(path),
                "section_key": section_key, "json_pointer": pointer, "row_id": ident,
                "section_sha256": sha256_bytes(body.encode("utf-8")),
                "ids": ids_in(body), "extraction": "STRUCTURED_ROW_EXTRACTED",
            }, sort_keys=True, ensure_ascii=False) + "\n")
            tally["sections"] += 1
            if NORMATIVE.search(body):
                statements_sink.write(json.dumps({
                    "source_id": source_id, "source_class": source_class,
                    "section_key": section_key, "row_id": ident, "json_pointer": pointer,
                    "statement_key": sha256_json([section_key, body])[:24],
                    "statement": body, "ids": ids_in(body),
                    "state": "CANDIDATE_REQUIREMENT_NOT_ADJUDICATED",
                }, sort_keys=True, ensure_ascii=False) + "\n")
                tally["statements"] += 1
    elif suffix == ".csv":
        reader = csv.DictReader(io.StringIO(text))
        header = reader.fieldnames or []
        id_col = next((h for h in header if h == "id" or h.endswith("_id")), header[0] if header else None)
        for number, row in enumerate(reader, 2):
            body = " | ".join(f"{k}: {v}" for k, v in row.items() if k and v)
            section_key = sha256_json([source_id, number, body])[:24]
            sections_sink.write(json.dumps({
                "source_id": source_id, "source_class": source_class, "path": str(path),
                "section_key": section_key, "csv_line": number,
                "row_id": row.get(id_col) if id_col else None,
                "section_sha256": sha256_bytes(body.encode("utf-8")),
                "ids": ids_in(body), "extraction": "STRUCTURED_ROW_EXTRACTED",
            }, sort_keys=True, ensure_ascii=False) + "\n")
            tally["sections"] += 1
            if NORMATIVE.search(body):
                statements_sink.write(json.dumps({
                    "source_id": source_id, "source_class": source_class,
                    "section_key": section_key, "row_id": row.get(id_col) if id_col else None,
                    "statement_key": sha256_json([section_key, body])[:24],
                    "statement": body, "ids": ids_in(body),
                    "state": "CANDIDATE_REQUIREMENT_NOT_ADJUDICATED",
                }, sort_keys=True, ensure_ascii=False) + "\n")
                tally["statements"] += 1
    else:
        tally["not_sectioned"] += 1
    return dict(tally)


def source_class_of(ref: dict[str, Any]) -> str:
    ident = ref["id"].upper()
    path = ref["path"].upper()
    if "USER_" in path or ident.startswith("USER") or ident == "RECOVERY37":
        return "USER_ADDITION"
    for prefix, name in (("HIST-", "HISTORICAL_PRESERVED"), ("ANCESTRAL-", "ANCESTRAL_NORMATIVE"),
                         ("SCHEMA-", "SCHEMA"), ("PRIOR-", "PRIOR_MANAGER_INPUT")):
        if ident.startswith(prefix):
            return name
    if "MANAGER_REVIEWS" in path:
        return "MANAGER_REVIEW_INPUT"
    return "CONTROLLING_BAS"


def extract_sections(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    closure = load_json(args.normative_closure)["explicit_source_refs"]
    snapshots = load_json(args.owner_snapshots)
    sections_path = out_dir / "R37_14_SECTION_EXTRACTION.jsonl"
    statements_path = out_dir / "R37_14_REQUIREMENT_STATEMENTS.jsonl"
    per_class: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    drift = []
    snapshot_checks = collections.Counter()
    snapshot_problems = []
    per_source: list[dict[str, Any]] = []
    with _bas_atomic.open_write(sections_path, "w", encoding="utf-8", newline="\n") as sections_sink, \
            _bas_atomic.open_write(statements_path, "w", encoding="utf-8", newline="\n") as statements_sink:
        for ref in closure:
            path = Path(ref["path"])
            cls = source_class_of(ref)
            per_class[cls]["sources"] += 1
            if not path.is_file():
                drift.append({"id": ref["id"], "state": "ABSENT"})
                per_class[cls]["absent"] += 1
                continue
            data = path.read_bytes()
            if sha256_bytes(data) != ref["sha256"]:
                drift.append({"id": ref["id"], "state": "CHANGED_SINCE_CLOSURE",
                              "recorded": ref["sha256"], "current": sha256_bytes(data)})
                per_class[cls]["changed_since_closure"] += 1
            tally = extract_source(ref["id"], cls, path, decode(data), sections_sink, statements_sink)
            per_source.append({"id": ref["id"], "class": cls, **tally})
            for key, value in tally.items():
                per_class[cls][key] += value

        origin_blobs: dict[str, GitBlobs] = {}
        for snap in snapshots:
            path = Path(snap["snapshot"])
            cls = "ALL22_COUNTERPART"
            per_class[cls]["sources"] += 1
            if not path.is_file():
                snapshot_problems.append({"source_path": snap["source_path"], "state": "SNAPSHOT_ABSENT"})
                continue
            data = path.read_bytes()
            blobs = origin_blobs.setdefault(snap["origin"], GitBlobs(Path(snap["origin"])))
            origin = blobs.read(f"{snap['revision']}:{snap['source_path']}")
            if origin is None:
                state = "ORIGIN_OBJECT_UNREADABLE"
            elif origin == data or origin.replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n"):
                state = "SNAPSHOT_EQUALS_ORIGIN_REVISION"
            else:
                state = "SNAPSHOT_DIFFERS_FROM_ORIGIN_REVISION"
            snapshot_checks[state] += 1
            if state != "SNAPSHOT_EQUALS_ORIGIN_REVISION":
                snapshot_problems.append({"source_path": snap["source_path"], "state": state})
            source_id = f"ALL22:{snap['revision'][:12]}:{snap['source_path']}"
            tally = extract_source(source_id, cls, path, decode(data), sections_sink, statements_sink)
            per_source.append({"id": source_id, "class": cls, **tally})
            for key, value in tally.items():
                per_class[cls][key] += value
        for blobs in origin_blobs.values():
            blobs.close()

    return {
        "closure_source": str(args.normative_closure),
        "closure_refs": len(closure),
        "owner_snapshots": len(snapshots),
        "owner_snapshot_origin_checks": dict(snapshot_checks),
        "owner_snapshot_problems": snapshot_problems,
        "closure_drift": drift,
        "per_source_class": {k: dict(v) for k, v in sorted(per_class.items())},
        "per_source": per_source,
        "sources_with_no_extracted_section": [
            {"id": r["id"], "class": r["class"],
             "reason": ("non-text source" if r.get("not_sectioned") else
                        "unparseable" if r.get("unparsed") else
                        "no heading, keyed row or id+text object found")}
            for r in per_source if not r.get("sections")
        ],
        "user_addition_rule": (
            "USER_ADDITION = closure refs whose path or ID names a user source "
            "(the Cycle 33 user coaching intake files) plus RECOVERY37, the "
            "controlling message the user reaffirmed verbatim. User additions "
            "that never reached the closure are not visible to this tool."
        ),
        "sections": str(sections_path),
        "sections_sha256": sha256_bytes(sections_path.read_bytes()),
        "statements": str(statements_path),
        "statements_sha256": sha256_bytes(statements_path.read_bytes()),
        "boundary": (
            "Sections are located and hashed; statements with normative "
            "language are listed per section as CANDIDATE_REQUIREMENT_NOT_ADJUDICATED. "
            "Keys are content digests, not new requirement IDs. Non-text "
            "sources (.py/.toml/.whl/.txt) are counted as not_sectioned."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    manager36 = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle36/20260922T022500Z")
    manager37 = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle37/20260922T171601Z")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--path-inventory", type=Path, default=manager36 / "SYSTEM_PATH_INVENTORY.json")
    parser.add_argument("--plan-inventory", type=Path, default=manager36 / "PLAN_CANDIDATE_INVENTORY.json")
    parser.add_argument("--domain-accounting", type=Path, default=manager36 / "DOMAIN_EXECUTION_ACCOUNTING.json")
    parser.add_argument("--plan-refresh", type=Path, default=manager37 / "WHOLE_SYSTEM_PLAN_REFRESH.json")
    parser.add_argument("--path-refresh", type=Path, default=manager37 / "WHOLE_SYSTEM_PATH_REFRESH.json")
    parser.add_argument("--domain-refresh", type=Path,
                        default=manager37 / "WHOLE_SYSTEM_REQUIREMENT_DOMAIN_REFRESH.json")
    parser.add_argument("--normative-closure", type=Path, default=manager37 / "NORMATIVE_SOURCE_CLOSURE.json")
    parser.add_argument("--owner-snapshots", type=Path, default=manager37 / "OWNER_SOURCE_SNAPSHOTS.json")
    parser.add_argument("--discovery-index", type=Path, default=Path(
        r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle32/20260911T214000Z/PLAN_DISCOVERY_INDEX.json"))
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    repo = args.repo.resolve()

    closure_paths = {r["path"] for r in load_json(args.normative_closure)["explicit_source_refs"]}
    receipt = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirement": "R37-14-AC01/AC02/AC03",
        "generated_at_utc": now(),
        "repository_head": git_lines(repo, "rev-parse", "HEAD")[0],
        "tool": "tools/cycle37/r37_14_plan_inventory.py",
        "ac01_inventories": consume_inventories(args, closure_paths),
        "ac02_catalogs": preserve_catalogs(args, repo),
        "ac03_link_adjudication": adjudicate_links(args, repo, args.out_dir),
        "ac03_section_extraction": extract_sections(args, args.out_dir),
        "not_claimed": [
            "No plan candidate is called governing unless the normative closure names it.",
            "No link or statement is called semantically verified.",
            "No new requirement, domain or Jira ID is minted; row keys are content digests.",
        ],
    }
    out = args.out_dir / "R37_14_PLAN_INVENTORY.json"
    _bas_atomic.write_text(out, json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    ac01 = receipt["ac01_inventories"]
    ac02 = receipt["ac02_catalogs"]
    ac03 = receipt["ac03_link_adjudication"]
    sec = receipt["ac03_section_extraction"]
    print("paths", ac01["path_inventory"]["rows"], "identities", ac01["path_inventory"]["checkout_identities"],
          "| plans", ac01["plan_inventory"]["rows"], "-> refresh", ac01["plan_refresh"]["rows"],
          ac01["plan_refresh"]["independent_rehash_now"])
    print("governing:", ac01["governing_classification"]["counts"])
    print("catalogs preserved:", ac02["preserved"], "| label mismatches:",
          len(ac02["crosswalk_label_vs_repository_matrix"]["mismatches"]),
          "| domains without crosswalk:", len(ac02["domains_without_any_crosswalk_row"]))
    print("links:", ac03["pairs"], ac03["file_states"], ac03["reproduction_at_discovery_bytes"])
    print("verdicts:", ac03["verdicts"])
    print("sections:", {k: v for k, v in sec["per_source_class"].items()})
    print("closure drift:", len(sec["closure_drift"]), "| snapshot checks:", sec["owner_snapshot_origin_checks"])
    print("receipt:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
