r"""Cycle #37 — Attempt #6 — reproduce the assigned findings before any repair (MF37A05-01..03).

    attempt06_before.py --out <new directory> --fixtures <new owned directory> [--reuse-fixtures --prior-run DIR]

MF37A05-01: the manager's ``successor_adversarial.py`` is copied byte for byte into ``--out`` except for the single
fixture-root literal, which is pointed at an owned directory under ``--fixtures`` (the manager's fixture root is
the manager's and is never written); both digests and the adaptation are recorded. It then runs exactly as the
manager ran it: the Attempt 5 installed ``bas-staff-query`` (``C:\BatteredAggieSyndrome.packaging\c37a05\b\5f400707``,
only executed, never written) over one owned full copy of the genuine successor, restored from the delivered file
before each case. Two further challenges of this attempt's own run on the same unfixed consumer: the same
cross-person swap through the Attempt 4 format (the other supported successor entrypoint), and a raw capture
whose payload names another page while the row keeps its own page and revision.

MF37A05-02 is reproduced from Git alone: the candidate's committed manifest rows for the protected paths against
the blobs its committed tree actually carries. MF37A05-03 is reproduced from the sealed Attempt 5 bytes: the
evidence entry that names the live ledger, the ledger's open reservation, and the failed FINAL_PACKET receipt.

``--reuse-fixtures`` restores the owned fixture copies of an earlier, interrupted run in place (every case restores
its copy from the delivered file by SQLite backup, so the earlier bytes never influence a case) instead of making
new ones; ``--prior-run`` names that earlier run's output directory, which is retained unchanged and recorded.
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
ATTEMPT_NUMBER = 6
LABEL = "Cycle #37 — Attempt #6 — IN_PROGRESS_LOCAL_WORK_REMAINS (before-repair reproduction)"
WORKTREE = Path(__file__).resolve().parents[2]
REVIEW = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt05\review-20260925T134703Z")
MANAGER_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a05-134703"
A5_VENV = Path(r"C:\BatteredAggieSyndrome.packaging\c37a05\b\5f400707\venv")
A5_SUCCESSOR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt05\release\successor\CAREER_SUCCESSOR_A05.sqlite")
A5_SUCCESSOR_SHA256 = "10c9a198a4c15595ce11f18f0153c0203b36d16adc2c871187279312d13822ec"
A4_SUCCESSOR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt04\release\successor\CAREER_SUCCESSOR_A04.sqlite")
A4_SUCCESSOR_SHA256 = "f7103f781259ecf13a06dfc59318ab7c735a9ff7c1080b9fd4608f04ae0373c7"
PREDECESSOR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempts\REWORK-20260922T171601Z\release\sha256"
                   r"\67d2ce357dc36d5a13a8edc94d0ffa9fc27115768817b1ee1ac9dff567757671"
                   r"\CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite")
PREDECESSOR_SHA256 = "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331"
A5_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt05")
CANDIDATE_WORKTREE = Path(r"C:\BatteredAggieSyndrome.worktrees\cycle37-integration-review")
CANDIDATE_HEAD = "daba87f012291f5f8d8def001d89b9e47c506a43"
PROTECTED_PATHS = (
    ".github/workflows/codex-scientific-review.yml", ".github/workflows/paid-scientific-review.yml",
    ".github/CODE_REVIEW_RULES.md", ".github/codex/prompts/scientific-review.md",
    "schemas/scientific_review/codex_scientific_review.schema.json", "tools/validate_codex_scientific_review.py",
)
FRED = "Fred Mariani"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path | str) -> str | None:
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def adapt_copy(script: str, target_dir: Path, replacements: dict[str, str]) -> dict[str, Any]:
    source = REVIEW / script
    text = source.read_text(encoding="utf-8")
    applied = []
    for old, new in replacements.items():
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{script}: expected exactly one occurrence of {old!r}, found {count}")
        text = text.replace(old, new)
        applied.append({"old": old, "new": new})
    target_dir.mkdir(parents=True, exist_ok=True)
    copy = target_dir / script
    copy.write_text(text, encoding="utf-8", newline="\n")
    return {"original": str(source), "original_sha256": sha256(source), "copy": str(copy),
            "copy_sha256": sha256(copy), "adaptations": applied}


def run(argv: list[str], cwd: Path, log: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = utc_now()
    completed = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env, check=False, timeout=3 * 3600)
    log.write_text((completed.stdout or "") + "\n" + (completed.stderr or ""), encoding="utf-8", newline="\n")
    return {"argv": [str(a) for a in argv], "cwd": str(cwd), "started_at": started, "finished_at": utc_now(),
            "exit_code": completed.returncode, "log": str(log), "log_sha256": sha256(log)}


def _minimal_env(temp: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "COMSPEC", "PATHEXT"}}
    temp.mkdir(parents=True, exist_ok=True)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", TEMP=str(temp), TMP=str(temp))
    return env


def _query(label: str, successor: Path, out_dir: Path, env: dict[str, str], extra: list[str] = ()) -> dict[str, Any]:
    """The manager's query, verbatim in shape: the installed launcher, the default database, an explicit pin."""

    cmd = [str(A5_VENV / "Scripts" / "bas-staff-query.exe"), "--database", str(PREDECESSOR), "--career",
           "--career-successor", str(successor), "--career-successor-sha256", sha256(successor), "--person", FRED,
           "--compact", *extra]
    completed = subprocess.run(cmd, cwd=str(out_dir), env=env, capture_output=True, text=True, encoding="utf8",
                               errors="replace", timeout=600, check=False)
    output = out_dir / f"{label}.json.gz"
    with gzip.open(output, "wt", encoding="utf8") as handle:
        handle.write(completed.stdout)
    payload = json.loads(completed.stdout) if completed.stdout.lstrip().startswith("{") else {}
    refusal = next(iter(re.findall(r"REFUSED_[A-Z_]+", completed.stderr or "")), None)
    return {"case": label, "command": cmd, "exit": completed.returncode, "refusal": refusal,
            "stderr_tail": (completed.stderr or "")[-600:], "stdout": str(output), "stdout_sha256": sha256(output),
            "row_count": payload.get("row_count")}


def _reseal(conn: sqlite3.Connection, tables: list[tuple[str, str]]) -> None:
    """Re-hash the ledgers exactly as the manager's probe does (a careful forger's reseal)."""

    for table, key in tables:
        digest = hashlib.sha256()
        count = 0
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY {key}"):
            digest.update((json.dumps(list(row), ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
                          .encode())
            count += 1
        for field, value in ((f"ledger::{table}::sha256", digest.hexdigest()), (f"ledger::{table}::rows", str(count))):
            conn.execute("UPDATE successor_identity SET value=? WHERE key=?", (value, field))
    conn.commit()


def mf01(out: Path, fixtures: Path, reuse: bool = False) -> dict[str, Any]:
    """The manager's adversarial probe replayed verbatim, then this attempt's two independent challenges."""

    fixture_root = fixtures / "mr37a05-adversarial"
    fixture_root.mkdir(parents=True, exist_ok=reuse)
    (fixture_root / "temp").mkdir(exist_ok=reuse)
    replay = adapt_copy("successor_adversarial.py", out / "successor_adversarial",
                        {f"F=Path(r'{MANAGER_FIXTURE_LITERAL}')": f"F=Path(r'{fixture_root}')"})
    copy = Path(replay["copy"])
    record = run([sys.executable, "-B", str(copy)], copy.parent, out / "successor_adversarial.log")
    review_path = copy.parent / "SUCCESSOR_ADVERSARIAL_REVIEW.json"
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else {}
    cases = {row["case"]: {"exit": row.get("exit"), "row_count": row.get("row_count"),
                           "refusal": next(iter(re.findall(r"REFUSED_[A-Z_]+", row.get("stderr") or "")), None)}
             for row in review.get("cases") or []}
    manager_forgeries_accepted = all(cases.get(name, {}).get("exit") == 0 and cases.get(name, {}).get("row_count") == 7
                                     for name in ("A5-cross-person-reciprocal-lineage", "A5-other-person-raw-binding"))
    # Independent challenge A: the same cross-person swap through the Attempt 4 format (other entrypoint).
    env = _minimal_env(fixture_root / "temp")
    a4_copy = fixtures / "adversarial_a04.sqlite"
    source = sqlite3.connect(A4_SUCCESSOR.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    target = sqlite3.connect(a4_copy)
    source.backup(target)
    source.close()
    target.row_factory = sqlite3.Row
    victim = dict(target.execute("SELECT * FROM career_episode_a04 WHERE person_display=? AND predecessor_episode_ids "
                                 "!= '[]' LIMIT 1", (FRED,)).fetchone())
    other = None
    for row in target.execute("SELECT * FROM career_episode_a04 WHERE person_display != ? AND predecessor_episode_ids "
                              "!= '[]' ORDER BY episode_id", (FRED,)):
        row = dict(row)
        parents = json.loads(row["predecessor_episode_ids"])
        if len(parents) == 1:
            disposition = dict(target.execute("SELECT * FROM career_a04_disposition WHERE predecessor_episode_id=?",
                                              (parents[0],)).fetchone())
            if json.loads(disposition["successor_episode_ids"]) == [row["episode_id"]]:
                other = row
                break
    assert other is not None
    pa, pb = json.loads(victim["predecessor_episode_ids"])[0], json.loads(other["predecessor_episode_ids"])[0]
    for child, parent in ((victim, pb), (other, pa)):
        target.execute("UPDATE career_episode_a04 SET predecessor_episode_ids=? WHERE episode_id=?",
                       (json.dumps([parent]), child["episode_id"]))
    target.execute("UPDATE career_a04_disposition SET successor_episode_ids=? WHERE predecessor_episode_id=?",
                   (json.dumps([other["episode_id"]]), pa))
    target.execute("UPDATE career_a04_disposition SET successor_episode_ids=? WHERE predecessor_episode_id=?",
                   (json.dumps([victim["episode_id"]]), pb))
    _reseal(target, [("career_episode_a04", "episode_id"), ("career_a04_disposition", "predecessor_episode_id")])
    target.close()
    a4_swap = _query("A4-cross-person-reciprocal-lineage", a4_copy, out, env)
    a4_swap["details"] = {"victim_episode": victim["episode_id"], "other_episode": other["episode_id"],
                          "other_person": other["person_display"], "original_parent": pa, "forged_parent": pb}
    # Independent challenge B: the row keeps its own page and revision, but its raw capture is a valid capture of
    # another page whose revision text carries the row's recorded team text at the recorded span (spans rewritten
    # to that page's text), with the file and text digests re-recorded -- the raw evidence of an unrelated person.
    a5_copy = fixtures / "adversarial.sqlite"
    source = sqlite3.connect(A5_SUCCESSOR.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    target = sqlite3.connect(a5_copy)
    source.backup(target)
    source.close()
    target.row_factory = sqlite3.Row
    fred = dict(target.execute("SELECT * FROM career_episode_a05 WHERE person_display=? AND team_raw LIKE '%DFO%' LIMIT 1",
                               (FRED,)).fetchone())
    donor = dict(target.execute("SELECT * FROM career_episode_a05 WHERE person_display != ? AND team_char_span IS NOT "
                                "NULL ORDER BY episode_id LIMIT 1", (FRED,)).fetchone())
    columns = ("raw_file", "raw_file_sha256", "wikitext_sha256", "team_char_span", "team_byte_span", "team_raw",
               "years_char_span", "years_raw")
    target.execute("UPDATE career_episode_a05 SET " + ",".join(f"{c}=?" for c in columns) + " WHERE episode_id=?",
                   tuple(donor[c] for c in columns) + (fred["episode_id"],))
    # The predecessor row keeps its own capture; the disposition digest is over the predecessor row and stays valid.
    _reseal(target, [("career_episode_a05", "episode_id"), ("career_a05_disposition", "predecessor_episode_id"),
                     ("career_a05_from_a04", "a04_episode_id")])
    target.close()
    unrelated = _query("A5-unrelated-valid-raw-capture", a5_copy, out, env)
    unrelated["details"] = {"victim_episode": fred["episode_id"], "claimed_pageid": fred["pageid"],
                            "claimed_revision": fred["revision"], "donor_episode": donor["episode_id"],
                            "donor_pageid": donor["pageid"], "donor_person": donor["person_display"]}
    reproduced = manager_forgeries_accepted and a4_swap["exit"] == 0 and unrelated["exit"] == 0
    return {"replay": replay, "run": record, "manager_cases": cases,
            "subject_unchanged": review.get("subject_sha256_before") == review.get("subject_sha256_after")
            == A5_SUCCESSOR_SHA256 == sha256(A5_SUCCESSOR),
            "independent_challenges": {"A4-cross-person-reciprocal-lineage": a4_swap,
                                       "A5-unrelated-valid-raw-capture": unrelated},
            "fixtures": {"a05_copy": str(a5_copy), "a04_copy": str(a4_copy)},
            "installed_consumer": {"venv": str(A5_VENV), "launcher": str(A5_VENV / "Scripts" / "bas-staff-query.exe"),
                                   "input_only": True},
            "reproduced": reproduced,
            "meaning": ("Before repair, the installed consumer serves seven Fred Mariani rows from the manager's two "
                        "forged copies and from both independent challenges; the genuine successor is unchanged.")}


def mf02(out: Path) -> dict[str, Any]:
    """The candidate's committed manifest against the blobs its committed tree carries, from Git alone."""

    def git(*args: str) -> str:
        return subprocess.run(["git", "--no-optional-locks", "-C", str(CANDIDATE_WORKTREE), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout

    head = git("rev-parse", "HEAD").strip()
    manifest = git("show", f"{head}:provenance/PROJECT_FILE_MANIFEST.csv")
    rows = {line.split(",")[0]: line.split(",") for line in manifest.splitlines()[1:] if line.strip()}
    checks = []
    for path in PROTECTED_PATHS:
        blob = subprocess.run(["git", "--no-optional-locks", "-C", str(CANDIDATE_WORKTREE), "show", f"{head}:{path}"],
                              capture_output=True, check=False)
        committed = hashlib.sha256(blob.stdout).hexdigest() if blob.returncode == 0 else None
        row = rows.get(path)
        checks.append({"path": path, "committed_blob_exists": blob.returncode == 0, "committed_sha256": committed,
                       "manifest_sha256": row[2] if row else None, "manifest_bytes": row[1] if row else None,
                       "consistent": (row is not None and committed == row[2]) if blob.returncode == 0
                       else row is None})
    stale = [c for c in checks if not c["consistent"]]
    (out / "MF02_COMMITTED_MANIFEST.json").write_text(json.dumps(checks, indent=2), encoding="utf-8", newline="\n")
    return {"candidate_head": head, "expected_head": CANDIDATE_HEAD, "checks": checks, "stale_entries": len(stale),
            "reproduced": head == CANDIDATE_HEAD and len(stale) == 4,
            "meaning": "Four committed manifest entries name blobs the committed tree does not carry (three changed, "
                       "one absent path); reproduced from git show without any worktree file."}


def mf03(out: Path) -> dict[str, Any]:
    """The sealed Attempt 5 packet's live-ledger evidence, its open reservation and its failed lane, read only."""

    submission = json.loads((A5_ROOT / "submission.json").read_text(encoding="utf-8"))
    evidence = {row["id"]: row for row in submission["evidence"]}
    ledger_entry = evidence.get("E-STORAGE-LEDGER") or {}
    ledger_path = Path(ledger_entry.get("path", A5_ROOT / "STORAGE_RESERVATIONS.jsonl"))
    lines = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    open_tokens = {}
    for row in lines:
        if row["kind"] == "RESERVE" and row.get("decision") == "ADMITTED":
            open_tokens[row["token"]] = row.get("operation")
        elif row["kind"] in ("RECONCILE", "ORPHAN_CLOSED"):
            open_tokens.pop(row.get("token"), None)
    lanes = {row["id"]: row for row in submission["lanes"]}
    final_packet = lanes.get("FINAL_PACKET") or {}
    artifacts = {row["id"]: row for row in submission.get("handoff_artifacts") or []}
    return {"sealed_submission_sha256": sha256(A5_ROOT / "submission.json"),
            "live_ledger_evidence": {"id": "E-STORAGE-LEDGER", "path": str(ledger_path),
                                     "sealed_sha256": ledger_entry.get("sha256"), "sha256_now": sha256(ledger_path),
                                     "also_a_handoff_artifact": "STORAGE_RESERVATIONS.jsonl" in artifacts},
            "ledger_records": len(lines), "open_reservations": open_tokens,
            "final_packet_lane": {"status": final_packet.get("status"), "run": final_packet.get("run"),
                                  "reason": final_packet.get("reason")},
            "reproduced": (final_packet.get("status") == "FAIL" and len(open_tokens) == 1
                           and ledger_entry.get("sha256") == sha256(ledger_path)),
            "meaning": ("The sealed packet names the live ledger as hashed evidence and a handoff artifact, the lane "
                        "that appended to it failed, and one reservation stays open so the sealed hash holds; the "
                        "Attempt 5 bytes are read only and unchanged.")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--reuse-fixtures", action="store_true")
    parser.add_argument("--prior-run", type=Path, default=None)
    args = parser.parse_args(argv)
    out, fixtures = args.out.resolve(), args.fixtures.resolve()
    if out.exists() or (fixtures.exists() and not args.reuse_fixtures):
        raise SystemExit("the before-reproduction writes only a new output directory (and new fixtures unless reused)")
    out.mkdir(parents=True)
    fixtures.mkdir(parents=True, exist_ok=args.reuse_fixtures)
    head = subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    document = {"label": LABEL, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "started_at": utc_now(),
                "subject": {"head": head, "a5_successor_sha256": sha256(A5_SUCCESSOR),
                            "a4_successor_sha256": sha256(A4_SUCCESSOR), "predecessor_sha256": sha256(PREDECESSOR),
                            "expected": {"a5": A5_SUCCESSOR_SHA256, "a4": A4_SUCCESSOR_SHA256,
                                         "predecessor": PREDECESSOR_SHA256}},
                "fixtures_reused": args.reuse_fixtures,
                "prior_run": ({"dir": str(args.prior_run),
                               "files": {str(p.relative_to(args.prior_run)): sha256(p)
                                         for p in sorted(args.prior_run.rglob("*")) if p.is_file()},
                               "state": "interrupted by the storage admission bounded stop of BEFORE-01; retained "
                                        "unchanged, never completed or edited"} if args.prior_run else None),
                "findings": {"MF37A05-01": mf01(out, fixtures, args.reuse_fixtures), "MF37A05-02": mf02(out),
                             "MF37A05-03": mf03(out)}}
    document["reproduced"] = {key: value["reproduced"] for key, value in document["findings"].items()}
    document["subject"]["unchanged_after"] = (sha256(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                              and sha256(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256
                                              and sha256(PREDECESSOR) == PREDECESSOR_SHA256)
    document["finished_at"] = utc_now()
    with (out / "BEFORE_REPRODUCTION.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(document["reproduced"]))
    return 0 if all(document["reproduced"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
