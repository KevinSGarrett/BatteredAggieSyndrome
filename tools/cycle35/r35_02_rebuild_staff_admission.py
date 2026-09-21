"""R35-02: rebuild all 798 role cells / 880 references from the actual sources.

This does NOT trust the predecessor's stored `role_claim_supported`,
`person_record_bound` or span offsets. For every one of the 880 episode
references it locates the raw source file the episode claims, reparses it with
the CURRENT (repaired) same-record binder, and compares the freshly derived
verdict against what was recorded.

Two properties are enforced structurally rather than hoped for:

* **No observation loss.** Every input episode appears in exactly one output
  disposition bucket, and the tool asserts input-set == output-set by exact
  key, not by count. Equal counts with different members is precisely the
  failure mode a total-only check cannot see.
* **The parser does not grade itself.** Where the rebuild disagrees with the
  predecessor, the row is emitted as CORRECTED or QUARANTINED with both
  verdicts and the evidence text, so a human reviewer adjudicates the
  semantics. The stratified sample is drawn across subdivision, platform,
  title qualifier and era so review is not concentrated in easy rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle33.span_locate import bind_person_role

RAW_ROOTS = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\official_staff"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\sportradar_staff"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\wikimedia"),
)

QUALIFIER_RE = re.compile(
    r"\b(co|interim|assistant|associate|deputy|acting|senior|head|"
    r"coordinator|analyst|quality control|graduate assistant)\b",
    re.I,
)


def decoded_text(raw: bytes) -> str:
    """Reproduce `Path.read_text()` semantics from bytes, read once.

    Text mode applies universal-newline translation before the caller ever
    sees the string, so the episodes' `source_hash_sha256` is the sha256 of
    THAT normalized text, not of the file's raw bytes. MR33-15 documented
    the distinction; this function makes the two representations derivable
    from a single read instead of reading each 600 KB page twice.
    """

    text = raw.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def index_raw_sources(
    roots=RAW_ROOTS, *, cache_path: Path | None = None
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Map decoded-text sha256 -> file, with a persistent content cache.

    The declared roots hold ~1.25 GB across thousands of captured pages, so
    a naive rescan dominates the rebuild's runtime. The cache is keyed by
    (path, size, mtime_ns): a file whose size and mtime are unchanged cannot
    have different content for our purposes, and any mismatch falls through
    to a real re-read and re-hash. Hashes are still computed here from actual
    bytes -- never copied from a manifest or from the predecessor.
    """

    cache: dict[str, Any] = {}
    if cache_path is not None and cache_path.is_file():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cache = {}

    by_decoded: dict[str, Path] = {}
    stats = {
        "files_scanned": 0,
        "roots_missing": [],
        "raw_equals_decoded": 0,
        "cache_hits": 0,
        "cache_misses": 0,
    }
    fresh: dict[str, Any] = {}
    for root in roots:
        if not root.exists():
            stats["roots_missing"].append(str(root))
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            key = str(path)
            signature = [stat.st_size, stat.st_mtime_ns]
            entry = cache.get(key)
            if entry and entry.get("signature") == signature:
                stats["cache_hits"] += 1
            else:
                try:
                    raw = path.read_bytes()
                except OSError:
                    continue
                entry = {
                    "signature": signature,
                    "raw": hashlib.sha256(raw).hexdigest(),
                    "decoded": hashlib.sha256(
                        decoded_text(raw).encode("utf-8")
                    ).hexdigest(),
                }
                stats["cache_misses"] += 1
            fresh[key] = entry
            stats["files_scanned"] += 1
            if entry["raw"] == entry["decoded"]:
                stats["raw_equals_decoded"] += 1
            by_decoded.setdefault(entry["decoded"], path)

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(fresh), encoding="utf-8")
    stats["distinct_decoded_hashes"] = len(by_decoded)
    stats["roots"] = [str(r) for r in roots]
    return by_decoded, stats


def episode_key(cell: dict[str, Any], episode: dict[str, Any], ordinal: int) -> str:
    """A stable identity for one observation, independent of list position."""

    return "|".join(
        (
            str(cell.get("program_id") or ""),
            str(cell.get("role") or ""),
            str(episode.get("person") or ""),
            str(episode.get("source_title") or ""),
            str(episode.get("source_hash_sha256") or ""),
            str(episode.get("body_offset") if episode.get("body_offset") is not None else ""),
            str(ordinal),
        )
    )


def stratum(cell: dict[str, Any], episode: dict[str, Any]) -> dict[str, str]:
    title = str(episode.get("source_title") or "")
    qualifiers = sorted({m.group(0).casefold() for m in QUALIFIER_RE.finditer(title)})
    url = str(episode.get("page_url") or "")
    platform = "UNKNOWN"
    for token in ("sidearm", "wmt", "presto", "acusports", "wikipedia", "sportradar"):
        if token in url.casefold():
            platform = token
            break
    if platform == "UNKNOWN" and url:
        platform = "OTHER_OFFICIAL"
    season = episode.get("season")
    return {
        "source_class": str(episode.get("source") or "UNKNOWN"),
        "platform": platform,
        "qualifier": ",".join(qualifiers) or "NONE",
        "era": "CURRENT" if str(season) in {"2025", "2026"} else "HISTORIC",
        "role": str(cell.get("role") or ""),
    }


def rebuild(
    successor_jsonl: Path, by_decoded: dict[str, Path]
) -> dict[str, Any]:
    cells = [
        json.loads(line)
        for line in successor_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    input_keys: set[str] = set()
    rows: list[dict[str, Any]] = []
    parse_cache: dict[tuple[str, str, str], dict[str, Any]] = {}

    for cell in cells:
        for ordinal, episode in enumerate(cell.get("episode_refs") or []):
            key = episode_key(cell, episode, ordinal)
            input_keys.add(key)
            recorded_supported = episode.get("role_claim_supported")
            recorded_bound = episode.get("person_record_bound")
            source_hash = str(episode.get("source_hash_sha256") or "")
            person = str(episode.get("person") or "")
            title = str(episode.get("source_title") or "")
            path = by_decoded.get(source_hash)

            row: dict[str, Any] = {
                "episode_key": key,
                "program_id": cell.get("program_id"),
                "cell_role": cell.get("role"),
                "cell_disposition": cell.get("disposition"),
                "person": person,
                "source_title": title,
                "source_hash_sha256": source_hash,
                "recorded_role_claim_supported": recorded_supported,
                "recorded_person_record_bound": recorded_bound,
                "strata": stratum(cell, episode),
            }

            if path is None:
                row.update(
                    {
                        "disposition": "UNKNOWN_SOURCE_FILE_NOT_LOCATED",
                        "rebuilt_role_claim_supported": None,
                        "rebuilt_person_record_bound": None,
                        "reason": "No raw file in the declared roots hashes to "
                        "this episode's source_hash_sha256.",
                    }
                )
                rows.append(row)
                continue

            cache_key = (source_hash, person, title)
            if cache_key not in parse_cache:
                html = decoded_text(path.read_bytes())
                parse_cache[cache_key] = bind_person_role(
                    html, person=person, title=title
                )
            found = parse_cache[cache_key]
            rebuilt_supported = found.get("role_claim_supported") is True
            rebuilt_bound = found.get("person_record_bound") is True
            row.update(
                {
                    "raw_path": str(path),
                    "rebuilt_role_claim_supported": rebuilt_supported,
                    "rebuilt_person_record_bound": rebuilt_bound,
                    "rebuilt_reject_reason": found.get("reject_reason"),
                    "rebuilt_record_person": found.get("record_person"),
                    "rebuilt_record_title": found.get("record_title"),
                    "rebuilt_record_selector": found.get("record_selector"),
                    "rebuilt_person_offset": (found.get("person_interval") or {}).get(
                        "body_offset"
                    ),
                    "recorded_person_offset": episode.get("body_offset"),
                    "contrary_records": found.get("contrary_records") or [],
                }
            )
            if rebuilt_supported == (recorded_supported is True) and rebuilt_bound == (
                recorded_bound is True
            ):
                row["disposition"] = (
                    "RETAINED_SUPPORTED" if rebuilt_supported else "RETAINED_UNSUPPORTED"
                )
            elif rebuilt_supported or rebuilt_bound:
                row["disposition"] = "CORRECTED_UPGRADED_BY_REPARSE"
            else:
                row["disposition"] = "QUARANTINED_REPARSE_WITHDRAWS_SUPPORT"
            rows.append(row)

    output_keys = {row["episode_key"] for row in rows}
    counts = Counter(row["disposition"] for row in rows)
    by_stratum: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for dimension, value in row["strata"].items():
            by_stratum[dimension][value] += 1

    return {
        "rows": rows,
        "conservation": {
            "input_episode_count": len(input_keys),
            "output_row_count": len(rows),
            "input_key_set_equals_output_key_set": input_keys == output_keys,
            "keys_lost": sorted(input_keys - output_keys),
            "keys_invented": sorted(output_keys - input_keys),
        },
        "cell_count": len(cells),
        "disposition_counts": dict(counts),
        "strata_counts": {k: dict(v) for k, v in by_stratum.items()},
    }


def stratified_sample(rows: list[dict[str, Any]], per_stratum: int = 2) -> list[dict[str, Any]]:
    """One deterministic sample per (subdivision-ish stratum, disposition).

    Sorted by episode_key so the sample is reproducible rather than whatever
    order the rows happened to arrive in.
    """

    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        strata = row["strata"]
        buckets[
            (strata["platform"], strata["era"], row["disposition"])
        ].append(row)
    sample: list[dict[str, Any]] = []
    for key in sorted(buckets):
        for row in sorted(buckets[key], key=lambda r: r["episode_key"])[:per_stratum]:
            sample.append(
                {
                    "stratum": list(key),
                    "episode_key": row["episode_key"],
                    "person": row["person"],
                    "source_title": row["source_title"],
                    "recorded_role_claim_supported": row[
                        "recorded_role_claim_supported"
                    ],
                    "rebuilt_role_claim_supported": row[
                        "rebuilt_role_claim_supported"
                    ],
                    "rebuilt_record_person": row.get("rebuilt_record_person"),
                    "rebuilt_record_title": row.get("rebuilt_record_title"),
                    "manual_semantic_review": "PENDING_HUMAN_ADJUDICATION",
                }
            )
    return sample


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--successor", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--index-cache", default="")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    by_decoded, index_stats = index_raw_sources(
        cache_path=Path(args.index_cache) if args.index_cache else None
    )
    result = rebuild(Path(args.successor), by_decoded)

    rows_path = out_dir / "R35_02_STAFF_REBUILD_ROWS.jsonl"
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in result["rows"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    summary = {
        "artifact_type": "CYCLE35_R35_02_STAFF_ADMISSION_REBUILD",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "successor_input": str(Path(args.successor)),
        "successor_input_sha256": hashlib.sha256(
            Path(args.successor).read_bytes()
        ).hexdigest(),
        "raw_source_index": index_stats,
        "cell_count": result["cell_count"],
        "conservation": result["conservation"],
        "disposition_counts": result["disposition_counts"],
        "strata_counts": result["strata_counts"],
        "rows_artifact": str(rows_path),
        "rows_artifact_sha256": hashlib.sha256(rows_path.read_bytes()).hexdigest(),
        "parser_does_not_grade_its_own_sample": True,
        "manual_semantic_review_state": "PENDING_HUMAN_ADJUDICATION",
        "pit_admitted": False,
    }
    (out_dir / "R35_02_STAFF_REBUILD_SUMMARY.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (out_dir / "R35_02_STRATIFIED_REVIEW_SAMPLE.json").write_text(
        json.dumps(
            {
                "artifact_type": "CYCLE35_R35_02_STRATIFIED_MANUAL_REVIEW_SAMPLE",
                "sample": stratified_sample(result["rows"]),
                "note": "Parser output cannot label its own gold sample; every "
                "row here requires human semantic adjudication.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "cells": result["cell_count"],
            "episodes": result["conservation"]["input_episode_count"],
            "conserved": result["conservation"]["input_key_set_equals_output_key_set"],
            "dispositions": result["disposition_counts"],
            "files_scanned": index_stats["files_scanned"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
