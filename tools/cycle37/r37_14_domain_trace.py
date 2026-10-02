r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-14-AC04, AC08 and AC09: trace every review domain from expected
population through source, data, producer, consumer, tests and owner, keep
the named domains visible, duplicate-audit before any new issue, and link
each R37 requirement to its TP37 section, owner issue and evidence.

What is declared and what is derived:

* **Declared** (``r37_14_domain_trace_declaration.json``): each domain's
  producer modules, the delivered release tables and national admission
  domains that hold its data, and its owner issue. A declaration can be
  wrong, so each part is checked here: producers must be tracked at HEAD,
  release tables must exist and be non-empty, admission domains must exist
  in the materialized matrix, and every issue key must be live.
* **Derived** (never declared): consumers are the tracked non-test modules
  that import a producer; tests are the tracked test modules that import a
  producer or name a producer script. A domain cannot be given a consumer
  that does not exist by writing one down.
* **Executed** (``--run-tests``): each derived test file is run in its own
  interpreter and its counts recorded. A domain whose tests were only
  found, not run, says so.

A domain is ``TRACED_LOCAL`` only when every element is present and its
tests ran with no failure. Nothing here is a scientific acceptance of a
domain: population completeness against the national universe is a
separate audit, and the status names what exists, not whether it is right.
"""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
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
ROOT = Path(__file__).resolve().parents[2]
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
MANAGER37 = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle37/20260922T171601Z")
ADMISSION = Path(r"C:/BatteredAggieSyndrome.data/canonical/national_pit_domain_admission_matrix/sha256")
VALIDATION_ROOT = Path(r"C:/BatteredAggieSyndrome.validation/c37r-171601")
WATCHED_DATA = (Path(r"C:/BatteredAggieSyndrome.data/canonical"),
                Path(r"C:/BatteredAggieSyndrome.data/pit_state"),
                Path(r"C:/BatteredAggieSyndrome.data/lake"))

DATA_PRESENT_DECISIONS = {"ADMITTED", "CANDIDATE", "QUARANTINED"}

#: Duplicate-audit patterns: an existing issue whose summary or labels
#: match is a candidate owner before any new issue could be proposed.
DUPLICATE_PATTERNS = {
    "D01": r"program (identity|population)|canonical (team|program)|sponsorship",
    "D02": r"membership|conference|subdivision|classification",
    "D03": r"schedule|kickoff|contest identity|game spine",
    "D04": r"outcome|final score|official final",
    "D05": r"strength|opponent",
    "D06": r"ranking|poll",
    "D07": r"roster",
    "D08": r"player identity|eligib|experience",
    "D09": r"recruit|prospect",
    "D10": r"transfer|portal",
    "D11": r"head coach|coaching|coach\b",
    "D12": r"coordinator|play-?caller",
    "D13": r"position coach|staff",
    "D14": r"career|coach/staff role",
    "D15": r"play[- ]?call|responsibilit",
    "D16": r"injur|availability",
    "D17": r"depth|starter|snap|participation|substitut",
    "D18": r"suspen|absence",
    "D19": r"venue|stadium|surface|altitude|elevation",
    "D20": r"travel|\brest\b|time[- ]?zone|distance",
    "D21": r"weather",
    "D22": r"box ?score|team stat|gamebook",
    "D23": r"player stat|player box|individual stat",
    "D24": r"play[- ]by[- ]play|\bdrives?\b|possession",
    "D25": r"officiat|penalt|referee",
    "D26": r"market|odds|spread|betting",
    "D27": r"film|all-?22",
    "D28": r"scheme|formation",
    "D29": r"feature",
    "D30": r"probabilit|margin|uncertaint|score-distribution",
    "D31": r"total|joint score|team score",
    "D32": r"calibrat|evaluation",
    "D33": r"residual|peer|aggie excess",
    "D34": r"licens|rights|provenance",
    "D35": r"resource|finance|revenue",
    "D36": r"\bnil\b|revenue[- ]shar|name,? image",
    "D37": r"rule[- ]era|playing rule|regulatory",
    "D38": r"eligibility|regulat",
    "D39": r"stakes|standing|playoff",
    "D40": r"rivalry|homecoming|senior",
    "D41": r"draft",
    "D42": r"rating|\belo\b",
    "D43": r"lower[- ]division|\bdii\b|diii|division ii",
    "D44": r"naia",
    "D45": r"juco|junior college",
    "D46": r"\blive\b|in-game",
    "D47": r"efficiency|tempo|field position|special teams",
    "D48": r"fourth[- ]down|clock|halftime decision",
    "D49": r"personnel|tracking|formation",
    "D50": r"honor|watch list|preseason|high[- ]school",
    "D99": r"technical plan|cross-system",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_lines(*args: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                         check=True, encoding="utf-8", errors="replace")
    return [line for line in out.stdout.splitlines() if line.strip()]


# ------------------------------------------------------------- import graph
def module_name(path: str) -> str | None:
    if path.startswith("src/") and path.endswith(".py"):
        dotted = path[len("src/"):-3].replace("/", ".")
        return dotted[:-len(".__init__")] if dotted.endswith(".__init__") else dotted
    return None


def import_graph(tracked: list[str]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Per tracked .py file: modules it imports, and string constants naming .py files."""

    imports: dict[str, set[str]] = {}
    script_refs: dict[str, set[str]] = {}
    for path in tracked:
        if not path.endswith(".py") or not path.startswith(("src/", "tools/", "tests/")):
            continue
        try:
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        found: set[str] = set()
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module)
                for alias in node.names:
                    found.add(f"{node.module}.{alias.name}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for token in re.findall(r"[A-Za-z0-9_]+\.py", node.value):
                    names.add(token)
        imports[path] = found
        script_refs[path] = names
    return imports, script_refs


def importers_of(producer: str, imports: dict[str, set[str]],
                 script_refs: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    target = module_name(producer)
    basename = Path(producer).name
    consumers, tests = [], []
    for path, found in imports.items():
        if path == producer:
            continue
        hit = bool(target and target in found)
        if not hit and producer.startswith("tools/"):
            hit = basename in script_refs.get(path, set())
        if not hit:
            continue
        if path.startswith("tests/"):
            # A helper module under tests/ (a fixture builder, a frozen
            # predecessor) is not a test: running it collects nothing, and
            # counting it would report a domain's tests as failing to run.
            if Path(path).name.startswith("test_"):
                tests.append(path)
        else:
            consumers.append(path)
    return sorted(consumers), sorted(tests)


# ------------------------------------------------------------------ tests
SUMMARY = re.compile(r"^Ran (\d+) tests? in", re.MULTILINE)
RESULT = re.compile(r"^(OK|FAILED)(?: \((.*)\))?\s*$", re.MULTILINE)


def run_test_file(path: str, python: str, timeout: int) -> dict[str, Any]:
    module = Path(path).stem
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    # The repository root is on the path as well as src/: several suites
    # import ``tools.<validator>`` the way the full-suite lane runs them,
    # and running them without it would manufacture a failure.
    env.update({"PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)]),
                "PYTHONDONTWRITEBYTECODE": "1",
                "BAS_VALIDATION_ROOT": str(VALIDATION_ROOT)})
    tmp_root = VALIDATION_ROOT / "r37_14_domain_tests_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    # Some suites leave their temporary directories behind (about 150 MB a
    # trace). Each file gets its own directory under the validation root,
    # removed when the file finishes, so repeated traces do not accumulate them.
    with tempfile.TemporaryDirectory(prefix=f"{module}-", dir=tmp_root, ignore_cleanup_errors=True) as tmp:
        env.update({"TMP": tmp, "TEMP": tmp, "TMPDIR": tmp})
        try:
            proc = subprocess.run([python, "-B", "-m", "unittest", "-q", module],
                                  cwd=str(ROOT / "tests"), env=env, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"file": path, "state": "TIMEOUT", "seconds": timeout}
    text = proc.stdout + "\n" + proc.stderr
    outcome = classify_unittest(text, proc.returncode)
    return {"file": path, **outcome, "exit_code": proc.returncode,
            "seconds": round(time.monotonic() - started, 1),
            "tail": text.strip().splitlines()[-6:] if outcome["state"] != "PASSED" else []}


def classify_unittest(text: str, returncode: int) -> dict[str, Any]:
    """Read unittest's own summary. No summary line means nothing ran.

    A file whose every test skipped is not a pass: it proves the tests exist,
    not that the domain works.
    """

    ran = SUMMARY.search(text)
    result = RESULT.search(text)
    detail = dict(part.split("=") for part in (result.group(2) or "").split(", ") if "=" in part) \
        if result else {}
    tests_run = int(ran.group(1)) if ran else 0
    skipped = int(detail.get("skipped", 0))
    failures = int(detail.get("failures", 0)) + int(detail.get("errors", 0))
    if not ran:
        state = "DID_NOT_RUN"
    elif failures:
        state = "FAILED"
    elif tests_run == 0:
        state = "DID_NOT_RUN"
    elif skipped == tests_run:
        state = "ALL_SKIPPED"
    elif returncode == 0 and result and result.group(1) == "OK":
        state = "PASSED"
    else:
        state = "NONZERO_EXIT"
    return {"state": state, "ran": tests_run, "skipped": skipped,
            "failures_and_errors": failures,
            "expected_failures": int(detail.get("expected failures", 0))}


def data_fingerprint() -> str:
    digest = hashlib.sha256()
    for root in WATCHED_DATA:
        for dirpath, _, filenames in os.walk(root):
            for name in sorted(filenames):
                full = Path(dirpath) / name
                try:
                    stat = full.stat()
                except OSError:
                    continue
                digest.update(f"{full}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
    return digest.hexdigest()


# ------------------------------------------------------------------ inputs
def admission_matrix() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    versions = sorted(ADMISSION.iterdir(), key=lambda p: (p / "national_domain_admission_matrix.jsonl").stat().st_mtime)
    chosen = versions[-1] / "national_domain_admission_matrix.jsonl"
    rows = {}
    for line in chosen.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["domain_id"]] = row
    meta = {"chosen": str(chosen), "sha256": sha256_bytes(chosen.read_bytes()),
            "versions": [{"dir": v.name, "matrix_sha256": sha256_bytes(
                (v / "national_domain_admission_matrix.jsonl").read_bytes())} for v in versions],
            "rule": "the most recently written content-addressed version is used; both are listed"}
    return rows, meta


def release_tables(path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        names = [r[0] for r in conn.execute("select name from sqlite_master where type='table'")]
        return {n: conn.execute(f'select count(*) from "{n}"').fetchone()[0] for n in names}
    finally:
        conn.close()


def live_issues(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    out = {}
    for issue in data["bat_issues"] + data["cfip_owner_issues"]:
        fields = issue.get("fields") or {}
        out[issue["key"]] = {"status": (fields.get("status") or {}).get("name"),
                             "summary": fields.get("summary") or "",
                             "labels": fields.get("labels") or []}
    return out


def dom_sources(repo: Path, crosswalk: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    with (repo / "docs/data_research/w06/DATA_DOMAIN_COVERAGE_MATRIX.csv").open(encoding="utf-8") as handle:
        matrix = {r["domain_id"]: r for r in csv.DictReader(handle)}
    by_domain: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for row in crosswalk:
        dom = matrix.get(row["source_requirement_id"]) or {}
        for ref in str(row.get("review_domain_ids") or "").split(";"):
            if ref.strip():
                by_domain[ref.strip()].append({
                    "dom": row["source_requirement_id"], "label": row["source_requirement"],
                    "available": dom.get("available_source"), "primary": dom.get("primary_source"),
                    "fallback": dom.get("fallback_source"), "depth": dom.get("historical_depth"),
                    "pit_quality": dom.get("point_in_time_quality"), "gap": dom.get("remaining_gap"),
                })
    return by_domain


# -------------------------------------------------------------- the trace
def trace(args: argparse.Namespace) -> dict[str, Any]:
    declaration = load_json(args.declaration)
    refresh = load_json(args.domain_refresh)
    domains = refresh["retained_catalogs"]["domains"]
    crosswalk = refresh["retained_catalogs"]["technical_crosswalk"]
    tracked = git_lines("ls-files")
    tracked_set = set(tracked)
    imports, script_refs = import_graph(tracked)
    admissions, admission_meta = admission_matrix()
    tables = release_tables(args.release)
    issues = live_issues(args.jira_read)
    sources = dom_sources(ROOT, crosswalk)
    declared = declaration["domains"]
    reverse_admission = collections.defaultdict(list)
    for name, dom in declaration["admission_matrix_domains"].items():
        reverse_admission[dom].append(name)

    problems: list[str] = []
    for name in declaration["admission_matrix_domains"]:
        if name not in admissions:
            problems.append(f"declared admission domain {name} is not in the materialized matrix")
    for name in admissions:
        if name not in declaration["admission_matrix_domains"]:
            problems.append(f"materialized admission domain {name} is mapped to no review domain")
    missing_declarations = [d["domain_id"] for d in domains if d["domain_id"] not in declared]
    extra_declarations = [k for k in declared if k not in {d["domain_id"] for d in domains}]
    if missing_declarations:
        problems.append(f"domains without a declaration: {missing_declarations}")
    if extra_declarations:
        problems.append(f"declarations for unknown domains: {extra_declarations}")

    all_tests: set[str] = set()
    rows = []
    for domain in domains:
        did = domain["domain_id"]
        spec = declared.get(did, {})
        producers = []
        consumers: set[str] = set()
        tests: set[str] = set()
        for producer in spec.get("producers", []):
            present = producer in tracked_set
            c, t = importers_of(producer, imports, script_refs) if present else ([], [])
            consumers.update(c)
            tests.update(t)
            producers.append({"path": producer, "tracked_at_head": present,
                              "consumers": len(c), "tests": len(t)})
            if not present:
                problems.append(f"{did}: declared producer {producer} is not tracked at HEAD")
        all_tests.update(tests)
        data = []
        for table in spec.get("release_tables", []):
            count = tables.get(table)
            data.append({"kind": "RELEASE_TABLE", "name": table, "rows": count,
                         "present": bool(count)})
            if count is None:
                problems.append(f"{did}: declared release table {table} does not exist")
        for name in spec.get("admission_domains", []):
            row = admissions.get(name) or {}
            data.append({"kind": "NATIONAL_ADMISSION_DOMAIN", "name": name,
                         "decision": row.get("decision"), "known_at_basis": row.get("known_at_basis"),
                         "domain_scope_games": row.get("domain_scope_games"),
                         "domain_scope_seasons": row.get("domain_scope_seasons"),
                         "present": row.get("decision") in DATA_PRESENT_DECISIONS})
        for rel in spec.get("config_evidence", []):
            data.append({"kind": "CONFIG_REGISTRY", "name": rel, "present": rel in tracked_set})
        mapped_back = sorted(reverse_admission.get(did, []))
        owner = spec.get("owner_issue")
        owner_live = issues.get(owner) if owner else None
        if owner and not owner_live:
            problems.append(f"{did}: owner issue {owner} is not in the live read")
        related = [{"key": k, "status": (issues.get(k) or {}).get("status"), "live": k in issues}
                   for k in spec.get("related_issues", [])]
        for r in related:
            if not r["live"]:
                problems.append(f"{did}: related issue {r['key']} is not in the live read")
        derived_from = spec.get("derived_from", [])
        catalog_ids = {d["domain_id"] for d in domains}
        derived_unknown = [d for d in derived_from if d not in catalog_ids]
        if derived_unknown:
            problems.append(f"{did}: derived_from names unknown domains {derived_unknown}")
        rx = re.compile(DUPLICATE_PATTERNS.get(did, r"$^"), re.IGNORECASE)
        duplicates = sorted(k for k, v in issues.items()
                            if rx.search(v["summary"]) or any(rx.search(label) for label in v["labels"]))

        has = {
            "expected_population": bool(domain.get("mandatory_review")),
            "source": (any(s.get("available") == "YES" for s in sources.get(did, []))
                       or bool(derived_from and not derived_unknown)),
            "data": any(d["present"] for d in data),
            "producer": any(p["tracked_at_head"] for p in producers),
            "consumer": bool(consumers),
            "tests": bool(tests),
            "owner": bool(owner_live),
        }
        rows.append({
            "domain_id": did, "domain": domain["domain"], "natural_grain": domain["natural_grain"],
            "expected_population": domain.get("mandatory_review"),
            "conditional": bool(spec.get("conditional")),
            "sources": sources.get(did, []),
            "derived_from": derived_from,
            "source_basis": ("CROSSWALK_DOM_SOURCE" if any(s.get("available") == "YES" for s in sources.get(did, []))
                             else "DERIVED_FROM_UPSTREAM_DOMAINS" if derived_from else "NO_SOURCE"),
            "data": data, "admission_domains_mapped_here": mapped_back,
            "producers": producers,
            "consumers": sorted(consumers), "tests": sorted(tests),
            "owner_issue": owner, "owner_status": (owner_live or {}).get("status"),
            "related_issues": related,
            "duplicate_audit": {"pattern": DUPLICATE_PATTERNS.get(did), "existing_matches": len(duplicates),
                                "sample": duplicates[:12],
                                "decision": ("EXISTING_ISSUES_FOUND_NO_NEW_ISSUE" if duplicates
                                             else "NO_EXISTING_ISSUE_FOUND_NO_ISSUE_CREATED_OWNER_REQUEST_ONLY")},
            "has": has, "next_deliverable": spec.get("next_deliverable"),
        })

    executed: dict[str, dict[str, Any]] = {}
    fingerprint_before = fingerprint_after = None
    if args.run_tests:
        fingerprint_before = data_fingerprint()
        for path in sorted(all_tests):
            executed[path] = run_test_file(path, args.python, args.test_timeout)
            print(f"  {executed[path]['state']:<13} {executed[path].get('ran', 0):>4} {path}", flush=True)
        fingerprint_after = data_fingerprint()

    status_counts = collections.Counter()
    for row in rows:
        results = [executed[t] for t in row["tests"] if t in executed]
        row["test_execution"] = {
            "files": len(row["tests"]), "executed": len(results),
            "passed_files": sum(1 for r in results if r["state"] == "PASSED"),
            "failed_files": [r["file"] for r in results if r["state"] in ("FAILED", "NONZERO_EXIT", "TIMEOUT", "DID_NOT_RUN")],
            "all_skipped_files": [r["file"] for r in results if r["state"] == "ALL_SKIPPED"],
            "tests_ran": sum(r.get("ran", 0) for r in results),
            "tests_skipped": sum(r.get("skipped", 0) for r in results),
        }
        missing = [k for k, v in row["has"].items() if not v]
        tests_ok = bool(results) and not row["test_execution"]["failed_files"] and \
            row["test_execution"]["passed_files"] > 0
        if not missing and tests_ok:
            status = "TRACED_LOCAL"
        elif not row["has"]["producer"] and not row["has"]["data"]:
            status = "UNCOVERED"
        else:
            status = "PARTIAL"
        if row["has"]["tests"] and not results:
            missing.append("tests_not_executed")
        elif row["has"]["tests"] and not tests_ok:
            missing.append("tests_not_passing")
        row["missing"] = missing
        row["status"] = status
        status_counts[status] += 1

    named = {}
    for tag, dids in declaration["named_requirement_tags"].items():
        named[tag] = [{"domain_id": d, "status": next((r["status"] for r in rows if r["domain_id"] == d), "ABSENT"),
                       "missing": next((r["missing"] for r in rows if r["domain_id"] == d), None)}
                      for d in dids]
        if any(x["status"] == "ABSENT" for x in named[tag]):
            problems.append(f"named requirement {tag} maps to a domain that is not in the catalog")

    predecessor = declaration["predecessor_touch_map_adjudication"]
    predecessor_rows = []
    for did, item in predecessor["rows"].items():
        label = next((d["domain"] for d in domains if d["domain_id"] == did), None)
        predecessor_rows.append({"domain_id": did, "catalog_label": label, **item})

    return {
        "domains": rows,
        "status_counts": dict(status_counts),
        "named_requirements": named,
        "uncovered_or_partial": [
            {"domain_id": r["domain_id"], "domain": r["domain"], "status": r["status"],
             "missing": r["missing"], "next_deliverable": r["next_deliverable"],
             "owner_issue": r["owner_issue"], "owner_status": r["owner_status"],
             "audit_owner": "BAT-708"}
            for r in rows if r["status"] != "TRACED_LOCAL"
        ],
        "test_runs": list(executed.values()),
        "data_fingerprint": {"before": fingerprint_before, "after": fingerprint_after,
                             "unchanged": fingerprint_before == fingerprint_after,
                             "watched": [str(p) for p in WATCHED_DATA]} if args.run_tests else None,
        "admission_matrix": admission_meta,
        "release": {"path": str(args.release), "sha256": sha256_bytes(args.release.read_bytes()),
                    "tables": tables},
        "jira_read": {"path": str(args.jira_read), "issues": len(issues)},
        "predecessor_touch_map": {
            "source": predecessor["source"],
            "rows": predecessor_rows,
            "misattributed": sum(1 for r in predecessor_rows if r["verdict"] == "MISATTRIBUTED"),
        },
        "problems": problems,
    }


# ------------------------------------------------------------ AC09 links
def requirement_links(args: argparse.Namespace, issues_path: Path) -> dict[str, Any]:
    original = {r["id"]: r for r in load_json(args.requirements)["requirements"]}
    contract = load_json(MANAGER37 / "cycle_contract.json")["requirements"]
    reqs = []
    for item in contract:
        base = dict(original.get(item["id"], {}))
        base.setdefault("id", item["id"])
        base.setdefault("title", item.get("title"))
        base.setdefault("owner", item.get("owner"))
        base["jira_key"] = item.get("jira_key")
        if not base.get("plan_section"):
            base["plan_section"] = "TP37-" + item["id"].split("-", 1)[1]
        deliverables = item.get("deliverables") or []
        if isinstance(deliverables, str):
            deliverables = ast.literal_eval(deliverables)
        base["deliverables"] = deliverables
        reqs.append(base)
    closure = load_json(MANAGER37 / "NORMATIVE_SOURCE_CLOSURE.json")["explicit_source_refs"]
    headings: dict[str, list[str]] = collections.defaultdict(list)
    for ref in closure:
        path = Path(ref["path"])
        if path.suffix.lower() != ".md" or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"^\s{0,3}#{1,6}\s+(TP37-(?:\d\d|[SNI]))(?![0-9A-Za-z])", line)
            if match:
                headings[match.group(1)].append(ref["id"])
    claims = load_json(ATTEMPT / "evidence" / "EVIDENCE_CLAIMS.json")
    issues = live_issues(issues_path)
    rows = []
    for req in reqs:
        rid = req.get("id")
        if not rid:
            continue
        section = req.get("plan_section")
        owners = sorted(set(re.findall(r"\b(?:BAT|CFIP)-\d+\b",
                                       f"{req.get('owner') or ''} {req.get('jira_key') or ''}")))
        req_claims = [c for c in claims if c.get("requirement") == rid]
        evidence = []
        for claim in req_claims:
            for rel in claim.get("evidence") or []:
                evidence.append({"claim_rows": claim.get("rows"), "state": claim.get("state"),
                                 "path": rel, "exists": (ATTEMPT / rel).exists()})
        rows.append({
            "requirement": rid, "title": req.get("title"),
            "tp37_section": section,
            "section_heading_found_in": sorted(set(headings.get(section or "", []))),
            "owner_issues": [{"key": k, "status": (issues.get(k) or {}).get("status"),
                              "live": k in issues} for k in owners],
            "claims": len(req_claims),
            "claim_states": dict(collections.Counter(c.get("state") for c in req_claims)),
            "evidence": evidence,
            "evidence_missing": [e["path"] for e in evidence if not e["exists"]],
            "named_deliverables": [{"path": d, "exists": Path(d).exists()}
                                   for d in req.get("deliverables", []) if re.match(r"^[A-Za-z]:[\\/]", d)],
            "semantic_verification": "NOT_PERFORMED_BY_THIS_TOOL",
        })
    return {"rows": rows,
            "requirements": len(rows),
            "sections_without_heading": [r["requirement"] for r in rows if not r["section_heading_found_in"]],
            "requirements_without_claims": [r["requirement"] for r in rows if not r["claims"]],
            "evidence_paths_missing": sum(len(r["evidence_missing"]) for r in rows),
            "named_deliverables_missing": [d["path"] for r in rows for d in r["named_deliverables"] if not d["exists"]],
            "boundary": ("Links are issue <-> TP37 heading <-> requirement <-> claimed "
                         "evidence path. A link says the pieces exist and name each other; "
                         "it does not say the evidence satisfies the requirement.")}


def named_states(issues_path: Path) -> dict[str, Any]:
    issues = live_issues(issues_path)
    gaps_path = ROOT / "docs/final/FINAL_KNOWN_GAPS.csv"
    with gaps_path.open(encoding="utf-8") as handle:
        gaps = {r[next(iter(r))]: r for r in csv.DictReader(handle)}
    gap = gaps.get("GAP-005")
    expected = {"BAT-523": "In Progress", "BAT-429": "To Do"}
    out = {k: {"live_status": (issues.get(k) or {}).get("status"), "expected": v,
               "holds": (issues.get(k) or {}).get("status") == v} for k, v in expected.items()}
    out["BAT-401"] = {
        "live_status": (issues.get("BAT-401") or {}).get("status"),
        "expected": "protected lane retained blocked (RETAIN_PROTECTED_LANE_BLOCKED)",
        "note": ("Jira shows the retain-blocked decision issue itself as Done: the decision to "
                 "retain the lane blocked is complete, and the lane stays blocked. No protected "
                 "evaluation runs here."),
    }
    out["BAT-429"]["meaning"] = "dependency-blocked: A&M acquisition waits on its declared dependencies"
    out["GAP-005"] = {"present_in": str(gaps_path.relative_to(ROOT)), "row": gap,
                      "holds": gap is not None,
                      "meaning": "no production champion is claimed; the gap stays listed open"}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--declaration", type=Path,
                        default=ROOT / "tools/cycle37/r37_14_domain_trace_declaration.json")
    parser.add_argument("--domain-refresh", type=Path,
                        default=MANAGER37 / "WHOLE_SYSTEM_REQUIREMENT_DOMAIN_REFRESH.json")
    parser.add_argument("--requirements", type=Path,
                        default=Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/REQUIREMENTS.json"))
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--jira-read", type=Path, required=True)
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--test-timeout", type=int, default=900)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    result = trace(args)
    receipt = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirement": "R37-14-AC04/AC08/AC09",
        "generated_at_utc": now(),
        "repository_head": git_lines("rev-parse", "HEAD")[0],
        "tool": "tools/cycle37/r37_14_domain_trace.py",
        "declaration": {"path": str(args.declaration.relative_to(ROOT)) if args.declaration.is_relative_to(ROOT)
                        else str(args.declaration),
                        "sha256": sha256_bytes(args.declaration.read_bytes())},
        "trace": result,
        "requirement_links": requirement_links(args, args.jira_read),
        "named_states": named_states(args.jira_read),
        "not_claimed": [
            "No domain is scientifically accepted; TRACED_LOCAL means every element exists and its tests ran.",
            "No new Jira issue is created or proposed as created; the duplicate audit names existing issues.",
            "No link is called semantically verified.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    t = result
    print("status:", t["status_counts"], "| problems:", len(t["problems"]))
    for p in t["problems"][:20]:
        print("  problem:", p)
    print("predecessor misattributed:", t["predecessor_touch_map"]["misattributed"], "of",
          len(t["predecessor_touch_map"]["rows"]))
    if t["data_fingerprint"]:
        print("data unchanged by tests:", t["data_fingerprint"]["unchanged"])
    links = receipt["requirement_links"]
    print("requirements:", links["requirements"], "| without heading:", links["sections_without_heading"],
          "| without claims:", links["requirements_without_claims"],
          "| missing evidence paths:", links["evidence_paths_missing"])
    print("named deliverables missing:", len(links["named_deliverables_missing"]))
    print("named:", {k: v.get("holds") for k, v in receipt["named_states"].items()})
    print("receipt:", args.out)
    return 1 if t["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
