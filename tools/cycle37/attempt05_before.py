r"""Cycle #37 — Attempt #5 — reproduce every assigned finding before any repair (MF37A04-01..05).

    attempt05_before.py --out <new directory> --fixtures <new owned directory>

Each saved manager probe is copied into ``--out`` byte for byte, except for the single occurrence of each
fixture-root literal, which is pointed at an owned directory under ``--fixtures`` (the manager's own fixture
roots belong to the manager and are never written). Both digests and every adaptation are recorded. The probes
then run at the issued base against the Attempt 4 subject they were written for: the v37.4 guard in this
worktree and the Attempt 4 installed wheel (``C:\BatteredAggieSyndrome.packaging\c37a04\b\b9a46658\venv``),
which is only executed, never written.

MF37A04-05 has no probe of the manager's to replay; it is reproduced by reading the Attempt 4 runner's source
for any cumulative reservation and by binding the Attempt 4 measurement that exceeded the budget.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 5
WORKTREE = Path(__file__).resolve().parents[2]
REVIEW = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt04\review-20260925T025537Z")
MANAGER_FIXTURE = r"C:\BatteredAggieSyndrome.validation\mr37a04-025537"
A4_SUCCESSOR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt04\release\successor\CAREER_SUCCESSOR_A04.sqlite")
A4_SUCCESSOR_SHA256 = "f7103f781259ecf13a06dfc59318ab7c735a9ff7c1080b9fd4608f04ae0373c7"
PREDECESSOR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempts\REWORK-20260922T171601Z\release\sha256"
                   r"\67d2ce357dc36d5a13a8edc94d0ffa9fc27115768817b1ee1ac9dff567757671"
                   r"\CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite")
PREDECESSOR_SHA256 = "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331"
A4_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt04")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def adapt_copy(script: str, target_dir: Path, replacements: dict[str, str]) -> dict[str, Any]:
    source = REVIEW / script
    original = source.read_bytes()
    text = original.decode("utf-8")
    changes = []
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise SystemExit(f"{script}: {old!r} occurs {text.count(old)} times, not once")
        text = text.replace(old, new)
        changes.append({"from": old, "to": new})
    target_dir.mkdir(parents=True, exist_ok=False)
    target = target_dir / script
    target.write_bytes(text.encode("utf-8"))
    return {"manager_original": str(source), "manager_original_sha256": hashlib.sha256(original).hexdigest(),
            "copy": str(target), "copy_sha256": sha256(target), "literal_adaptations": changes}


def run(argv: list[str], cwd: Path, log: Path) -> dict[str, Any]:
    started = utc_now()
    completed = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=3600,
                               env={k: v for k, v in os.environ.items()
                                    if not any(m in k.upper() for m in ("TOKEN", "SECRET", "PASSWORD", "API_KEY",
                                                                        "JIRA", "ATLASSIAN", "GITHUB", "GH_"))})
    log.write_text(f"$ {argv}\n--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}\n",
                   encoding="utf-8")
    return {"argv": [str(a) for a in argv], "cwd": str(cwd), "started_at": started, "finished_at": utc_now(),
            "exit": completed.returncode, "log": str(log), "log_sha256": sha256(log)}


def mf01(out: Path, fixtures: Path) -> dict[str, Any]:
    """The manager's attached ``git config -f../p/x`` challenge against the v37.4 guard at the issued base."""

    root = fixtures / "mf01"
    (root / "temp").mkdir(parents=True)
    copy = adapt_copy("git_option_challenge_v2.py", out / "mf01",
                      {f'F=pathlib.Path(r"{MANAGER_FIXTURE}")': f'F=pathlib.Path(r"{root}")'})
    record = run([sys.executable, "-B", copy["copy"]], Path(copy["copy"]).parent, out / "mf01" / "run.log")
    result = json.loads((Path(copy["copy"]).parent / "GIT_OPTION_CHALLENGE_V2.json").read_text(encoding="utf-8"))
    child = json.loads(result.get("stdout") or "[]")
    attached = next((row for row in child if row.get("label") == "protected_attached_file"), {})
    return {"finding": "MF37A04-01", **copy, "run": record, "result": result,
            "reproduced": result.get("protected_bytes_unchanged") is False and attached.get("exit") == 0,
            "observation": ("git config -f../p/x from a repository inside the Git scratch root exits "
                            f"{attached.get('exit')} and the protected fixture reads "
                            f"{result.get('final_fixture_bytes')!r} (before {result.get('before')}, after "
                            f"{result.get('after')})")}


def mf02(out: Path, fixtures: Path) -> dict[str, Any]:
    """The manager's re-sealed successor challenge against the Attempt 4 installed consumer."""

    root = fixtures / "mf02"
    root.mkdir(parents=True)
    copy = adapt_copy("successor_challenge.py", out / "mf02",
                      {f"F=Path(r'{MANAGER_FIXTURE}')": f"F=Path(r'{root}')"})
    record = run([sys.executable, "-B", copy["copy"]], Path(copy["copy"]).parent, out / "mf02" / "run.log")
    result = json.loads((Path(copy["copy"]).parent / "SUCCESSOR_CHALLENGE.json").read_text(encoding="utf-8"))
    cases = {row["label"]: row for row in result["cases"]}
    missing_raw = cases.get("successor-resealed-missing-raw") or {}
    rows = missing_raw.get("rows") or []
    certified = [row.get("episode_id") for row in rows if not row.get("raw_file")
                 and (row.get("successor_binding") or {}).get("raw_file_sha256_verified") is True]
    return {"finding": "MF37A04-02", **copy, "run": record,
            "cases": {label: {k: row.get(k) for k in ("exit", "row_count", "answerable", "stderr")}
                      for label, row in cases.items()},
            "subject_unchanged": result.get("subject_sha_before") == result.get("subject_sha_after") == A4_SUCCESSOR_SHA256,
            "missing_row_accepted": (cases.get("successor-resealed-missing-row") or {}).get("exit") == 0,
            "unsealed_missing_row_refused": (cases.get("successor-unsealed-missing-row") or {}).get("exit") != 0,
            "absent_raw_certified_verified": certified,
            "dangling_disposition": result.get("dangling_disposition"),
            "owned_copy": result.get("owned_copy"), "owned_copy_sha256_after_challenge": sha256(Path(result["owned_copy"])),
            "reproduced": (cases.get("successor-resealed-missing-row") or {}).get("exit") == 0 and bool(certified)}


def mf03_04(out: Path, fixtures: Path) -> dict[str, Any]:
    """The manager's semantic census (template dates, defensive units) and installed season queries."""

    root = fixtures / "mf03_04"
    root.mkdir(parents=True)
    copy = adapt_copy("career_semantic_census.py", out / "mf03_04",
                      {r"F=Path(r'C:\BatteredAggieSyndrome.validation\mr37a04-025537')": f"F=Path(r'{root}')"})
    record = run([sys.executable, "-B", copy["copy"]], Path(copy["copy"]).parent, out / "mf03_04" / "run.log")
    census_path = Path(copy["copy"]).parent / "CAREER_SEMANTIC_CENSUS.json"
    census = json.loads(census_path.read_text(encoding="utf-8"))
    cory = {}
    with gzip.open(Path(copy["copy"]).parent / "cory-2018.consumer.json.gz", "rt", encoding="utf-8") as handle:
        text = handle.read()
        cory = json.loads(text) if text.lstrip().startswith("{") else {}
    conn = sqlite3.connect(f"file:{A4_SUCCESSOR.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        nested = [dict(zip(("episode_id", "person_display", "team_raw", "years_raw", "start", "end"), row)) for row in
                  conn.execute('SELECT episode_id, person_display, team_raw, years_raw, start, "end" FROM '
                               "career_episode_a04 WHERE person_display IN ('Cory Undlin', 'Danny Barrett', "
                               "'Steve Wilks') AND career_field = 'pastcoaching' AND row_index > 1000 ORDER BY "
                               "episode_id")]
    finally:
        conn.close()
    explicit_child = [row for row in nested
                      if re.search(r"(?:nfly|CFL Year)\|\d{4}", str(row["team_raw"] or ""))
                      and str(row["years_raw"] or "") not in str(row["team_raw"] or "")]
    units = census["defensive_pass_game_rows"]
    return {"findings": ["MF37A04-03", "MF37A04-04"], **copy, "run": record, "census": str(census_path),
            "census_sha256": sha256(census_path),
            "template_rows": census["year_template_population"], "collapsed_to_first_year": census["collapsed_to_first_year"],
            "template_types": census["template_types"],
            "cory_undlin_2018_installed_row_count": cory.get("row_count"),
            "nested_child_rows_whose_own_dates_were_replaced_by_the_parent": explicit_child,
            "defensive_pass_game_rows": len(units),
            "defensive_rows_by_unit": {u: sum(1 for r in units if r["assignment"].get("unit") == u)
                                       for u in sorted({r["assignment"].get("unit") for r in units})},
            "reproduced": census["year_template_population"] == 2257 and census["collapsed_to_first_year"] == 2232
            and len(units) == 33 and cory.get("row_count") == 0}


def mf05(out: Path) -> dict[str, Any]:
    """The Attempt 4 runner's storage handling, read from its source, and the measurement that exceeded the budget."""

    (out / "mf05").mkdir(parents=True)
    sources = {}
    for name in ("tools/cycle37/attempt04_lanes.py", "tools/cycle37/attempt03_lanes.py", "tools/cycle37/rework_lanes.py"):
        path = WORKTREE / name
        text = path.read_text(encoding="utf-8")
        lines = list(enumerate(text.splitlines(), 1))
        sources[name] = {
            "sha256": sha256(path),
            "disk_usage_lines": [f"{n}: {line.strip()}" for n, line in lines if "disk_usage" in line],
            # v2 detector: the peak budget is gated only if a line that names it compares it; a reservation is an
            # actual call into an admission API. (v1 matched the substring "reserv", which also matches
            # "preserved"; its result is retained in the first BEFORE_REPRODUCTION.json.)
            "peak_budget_lines": [f"{n}: {line.strip()}" for n, line in lines
                                  if re.search(r"storage_peak_extra_bytes|peak_extra", line)],
            "peak_budget_comparisons": [f"{n}: {line.strip()}" for n, line in lines
                                        if re.search(r"storage_peak_extra_bytes|peak_extra", line)
                                        and re.search(r"(?<![=!<>])(?:<=?|>=?)(?!=)|\bif\b|\bwhile\b", line)],
            "admission_api_calls": [f"{n}: {line.strip()}" for n, line in lines
                                    if re.search(r"\breserve\(|storage_admission|\bLedger\(|run_bounded\(", line)],
        }
    measurements = sorted((A4_ROOT / "evidence").glob("STORAGE_MEASUREMENT_*.json"))
    measured = json.loads(measurements[-1].read_text(encoding="utf-8")) if measurements else {}
    compared = [line for row in sources.values() for line in row["peak_budget_comparisons"]]
    admission = [line for row in sources.values() for line in row["admission_api_calls"]]
    return {"finding": "MF37A04-05", "runner_sources": sources, "attempt4_measurement": str(measurements[-1]) if measurements else None,
            "attempt4_measurement_sha256": sha256(measurements[-1]) if measurements else None,
            "attempt4_added_bytes": measured.get("added_bytes_now"), "budget": measured.get("budget"),
            "peak_budget_exceeded": measured.get("peak_budget_exceeded"),
            "detector_version": "v2 (peak-budget comparisons and admission API calls)",
            "reproduced": bool(measured.get("peak_budget_exceeded")) and not compared and not admission,
            "observation": ("the Attempt 4 runners check free space against the reserve (disk_usage) and never "
                            "reserve or gate the cumulative added bytes; Attempt 4 measured "
                            f"{measured.get('added_bytes_now')} added bytes against {measured.get('budget')}")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--only-mf05", action="store_true",
                        help="Rerun only the MF37A04-05 source reading (after its detector was corrected).")
    args = parser.parse_args(argv)
    if args.only_mf05:
        args.out.mkdir(parents=True, exist_ok=False)
        result = mf05(args.out)
        (args.out / "BEFORE_MF05_RERUN.json").write_text(json.dumps({
            "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS (MF37A04-05 before-repair "
                     "reading, detector v2)", "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
            "observed_at": utc_now(), "result": result,
            "supersedes_detector_of": "BEFORE_REPRODUCTION.json (retained unchanged)"}, indent=2, default=str)
            + "\n", encoding="utf-8")
        print(json.dumps({"MF37A04-05": result["reproduced"]}))
        return 0
    args.out.mkdir(parents=True, exist_ok=False)
    args.fixtures.mkdir(parents=True, exist_ok=False)
    head = subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    subject = {"head": head, "guard_sha256": sha256(WORKTREE / "tools/cycle37/canonical_write_guard/bas_canonical_write_guard.py"),
               "a4_successor_sha256": sha256(A4_SUCCESSOR), "predecessor_sha256": sha256(PREDECESSOR),
               "interpreter": sys.executable}
    results = {"MF37A04-01": mf01(args.out, args.fixtures), "MF37A04-02": mf02(args.out, args.fixtures),
               "MF37A04-03/04": mf03_04(args.out, args.fixtures), "MF37A04-05": mf05(args.out)}
    subject["a4_successor_sha256_after"] = sha256(A4_SUCCESSOR)
    subject["predecessor_sha256_after"] = sha256(PREDECESSOR)
    summary = {"label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS (before-repair reproduction)",
               "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "observed_at": utc_now(),
               "subject": subject,
               "subject_bytes_unchanged": subject["a4_successor_sha256"] == subject["a4_successor_sha256_after"]
               == A4_SUCCESSOR_SHA256 and subject["predecessor_sha256"] == subject["predecessor_sha256_after"]
               == PREDECESSOR_SHA256,
               "results": results,
               "reproduced": {key: value.get("reproduced") for key, value in results.items()}}
    target = args.out / "BEFORE_REPRODUCTION.json"
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary["reproduced"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
