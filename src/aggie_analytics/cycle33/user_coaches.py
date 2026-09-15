"""Named-column importer for the user-collected 2000–2026 staff corpus.

CSV column names and research dates are not source truth or PIT evidence.
Every cell is retained. Canonical science identities do not multiply on
rerun, reorder, or duplicate file submission.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33 import USER_IMPORTER_VERSION, USER_SOURCE_CLASS
from aggie_analytics.cycle33.role_taxonomy import (
    QUALIFIER_ACTING,
    QUALIFIER_INTERIM,
    assignments_from_title,
)

DEFAULT_SNAPSHOT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z\source_snapshot"
)
DEFAULT_INDEX = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\USER_COACHES_SOURCE_INDEX.json"
)
DEFAULT_MANIFEST = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z\SOURCE_MANIFEST.json"
)
DEFAULT_COLUMN_MAP = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\USER_COACHES_COLUMN_MAP.csv"
)
QUEUE_NAME = "2026_fbs_fields_needing_review.csv"

MISSINGNESS_EXACT = {
    "",
    "not verified",
    "unknown",
    "n/a",
    "na",
    "none",
    "null",
    "-",
    "—",
}
MISSINGNESS_PREFIXES = (
    "not verified",
    "not captured",
    "blank",
    "tbd",
    "see coverage",
)
NULL_AS_PERSON_FORBIDDEN = frozenset(
    {
        "NOT_VERIFIED",
        "UNKNOWN",
        "BLANK_NOT_CAPTURED",
        "SUPPORT_ONLY_PRIMARY_NOT_VERIFIED",
        "SEPARATE_ROLE_NOT_VERIFIED",
        "CONFLICT",
        "VACANT",
        "NO_SEPARATE_POSITION",
    }
)
PERSON_SPLIT = re.compile(r"\s*\|\s*")
NAME_TITLE_SPLIT = re.compile(r"\s+[—–]{1,2}\s+|\s+-\s+")


class UserCoachesError(ValueError):
    """Raised when a user-corpus file cannot be imported losslessly."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def classify_missingness(text: str) -> str | None:
    folded = re.sub(r"\s+", " ", str(text or "")).strip().casefold()
    if folded in MISSINGNESS_EXACT:
        return "BLANK_NOT_CAPTURED" if folded == "" else "NOT_VERIFIED"
    if any(folded.startswith(prefix) for prefix in MISSINGNESS_PREFIXES):
        return "NOT_VERIFIED"
    if folded in {"vacant", "no separate position", "no oc", "no dc"}:
        return "VACANT_OR_NO_SEPARATE_POSITION_UNVERIFIED"
    return None


def parse_person_segments(cell: str) -> list[dict[str, str]]:
    """Split one role cell. Pipes separate people; em-dash splits name/title."""

    raw = str(cell or "")
    missing = classify_missingness(raw)
    if missing is not None:
        return []
    if raw.lstrip().startswith("="):
        return []
    segments: list[dict[str, str]] = []
    for ordinal, chunk in enumerate(PERSON_SPLIT.split(raw)):
        piece = chunk.strip()
        if not piece:
            continue
        if classify_missingness(piece) is not None:
            continue
        if piece.upper() in NULL_AS_PERSON_FORBIDDEN:
            continue
        parts = NAME_TITLE_SPLIT.split(piece, maxsplit=1)
        if len(parts) == 2:
            name, title = parts[0].strip(), parts[1].strip()
        else:
            name, title = piece.strip(), ""
        if not name or classify_missingness(name) is not None:
            continue
        if name.upper() in NULL_AS_PERSON_FORBIDDEN:
            continue
        segments.append(
            {
                "person_raw": name,
                "title_raw": title or piece,
                "segment_ordinal": str(ordinal),
                "segment_text": piece,
            }
        )
    return segments


def _file_kind(name: str) -> str:
    if name == QUEUE_NAME:
        return "REVIEW_QUEUE"
    subdivision = _subdivision_from_filename(name)
    if subdivision == "FCS":
        return "STAFF_WIDE_OBSERVATIONS_FCS"
    if subdivision == "COMBINED_FBS_FCS":
        return "STAFF_WIDE_OBSERVATIONS_COMBINED"
    return "STAFF_WIDE_OBSERVATIONS_FBS"


def _year_from_filename(name: str) -> int | None:
    match = re.match(r"(19|20)\d{2}", name)
    return int(match.group(0)) if match else None


def _row_source_subdivision(row: Mapping[str, str], filename_subdivision: str) -> str:
    for key in ("Subdivision", "Division", "FBS/FCS", "Level"):
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        folded = value.casefold()
        if "fcs" in folded or "i-aa" in folded:
            return "FCS"
        if "fbs" in folded or "i-a" in folded:
            return "FBS"
    if filename_subdivision == "COMBINED_FBS_FCS":
        return "SUBDIVISION_UNRESOLVED_COMBINED_FILENAME"
    return filename_subdivision or "SUBDIVISION_UNRESOLVED"


def load_source_manifest(path: Path | None = None) -> dict[str, str]:
    target = path or DEFAULT_MANIFEST
    if not target.is_file():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    return {
        str(row.get("relative_path") or ""): str(row.get("sha256") or "")
        for row in payload.get("files") or []
        if row.get("relative_path")
    }


def _subdivision_from_filename(name: str) -> str:
    lowered = name.casefold()
    has_fbs = bool(re.search(r"\bfbs\b|division i-a\b|(?<![a-z])i-a(?!-a)", lowered))
    has_fcs = bool(re.search(r"\bfcs\b|\biaa\b|\bi-aa\b|division i-aa", lowered))
    if "fbs" in lowered and "fcs" in lowered:
        return "COMBINED_FBS_FCS"
    if has_fcs or "fcs" in lowered or "iaa" in lowered:
        return "FCS"
    if has_fbs or "fbs" in lowered:
        return "FBS"
    return "UNKNOWN"


def load_column_map(path: Path | None = None) -> dict[str, dict[str, str]]:
    target = path or DEFAULT_COLUMN_MAP
    mapping: dict[str, dict[str, str]] = {}
    if not target.is_file():
        return mapping
    with target.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mapping[str(row.get("source_column") or "")] = dict(row)
    return mapping


def observation_id(
    *, file_sha256: str, record_ordinal: int, header: str, cell: str
) -> str:
    digest = sha256_json(
        {
            "file_sha256": file_sha256,
            "record_ordinal": record_ordinal,
            "header": header,
            "cell": cell,
        }
    )
    return f"UCS:OBS:{digest}"


def canonical_claim_id(
    *, team_id: str, season: str, role_column: str, person: str, title: str
) -> str:
    digest = sha256_json(
        {
            "team_id": team_id.casefold().strip(),
            "season": str(season).strip(),
            "role_column": role_column,
            "person": person.casefold().strip(),
            "title": title.casefold().strip(),
        }
    )
    return f"UCS:CLAIM:{digest}"


def parse_csv_records(
    path: Path,
) -> tuple[list[str], list[dict[str, str]], bytes, dict[str, Any]]:
    """Strict newline-preserving reader. Duplicate headers and width errors quarantine."""

    payload = path.read_bytes()
    text = payload.decode("utf-8-sig")
    meta: dict[str, Any] = {
        "status": "OK",
        "reasons": [],
        "retained_bytes": len(payload),
        "newline_preserving": True,
        "dictreader_splitlines_forbidden": True,
    }
    reader = csv.reader(io.StringIO(text), strict=True)
    try:
        headers = next(reader)
    except StopIteration:
        return (
            [],
            [],
            payload,
            {**meta, "status": "QUARANTINED", "reasons": ["EMPTY_CSV"]},
        )
    except csv.Error as exc:
        return (
            [],
            [],
            payload,
            {
                **meta,
                "status": "QUARANTINED",
                "reasons": [f"CSV_PARSE_ERROR:{exc}"],
            },
        )
    if len(headers) != len(set(headers)):
        return (
            headers,
            [],
            payload,
            {
                **meta,
                "status": "QUARANTINED",
                "reasons": ["DUPLICATE_HEADER"],
                "headers": headers,
            },
        )
    rows: list[dict[str, str]] = []
    try:
        for ordinal, raw_row in enumerate(reader):
            if len(raw_row) != len(headers):
                return (
                    headers,
                    [],
                    payload,
                    {
                        **meta,
                        "status": "QUARANTINED",
                        "reasons": ["ROW_WIDTH_MISMATCH"],
                        "record_ordinal": ordinal,
                        "header_count": len(headers),
                        "row_width": len(raw_row),
                        "retained_row": raw_row,
                    },
                )
            rows.append(
                dict(
                    zip(
                        headers,
                        [
                            value.replace("\r\n", "\n").replace("\r", "\n")
                            for value in raw_row
                        ],
                        strict=True,
                    )
                )
            )
    except csv.Error as exc:
        return (
            headers,
            [],
            payload,
            {
                **meta,
                "status": "QUARANTINED",
                "reasons": [f"CSV_PARSE_ERROR:{exc}"],
            },
        )
    return headers, rows, payload, meta


def import_snapshot(
    snapshot: Path | None = None,
    *,
    column_map_path: Path | None = None,
    import_time_utc: str | None = None,
) -> dict[str, Any]:
    root = Path(snapshot or DEFAULT_SNAPSHOT)
    if not root.is_dir():
        raise UserCoachesError(f"snapshot missing: {root}")
    column_map = load_column_map(column_map_path)
    imported_at = import_time_utc or utc_now()
    files: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    role_cells: list[dict[str, Any]] = []
    queue_rows: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    csv_files = sorted(p for p in root.glob("*.csv") if p.is_file())
    manifest_hashes = load_source_manifest()
    expected_names = set(manifest_hashes)
    found_names = {path.name for path in csv_files}
    extra_files = sorted(found_names - expected_names) if expected_names else []
    missing_files = sorted(expected_names - found_names) if expected_names else []
    physically_present_role_cells = 0
    parsed_person_segments = 0
    for path in csv_files:
        headers, rows, payload, parse_meta = parse_csv_records(path)
        file_sha = sha256_bytes(payload)
        if path.name in manifest_hashes and manifest_hashes[path.name] != file_sha:
            raise UserCoachesError(
                f"manifest hash mismatch for {path.name}: "
                f"expected {manifest_hashes[path.name]} got {file_sha}"
            )
        kind = _file_kind(path.name)
        unclassified_headers = [
            header
            for header in headers
            if header not in column_map and header not in {"", None}
        ]
        file_row = {
            "relative_path": path.name,
            "sha256": file_sha,
            "bytes": len(payload),
            "headers": headers,
            "header_count": len(headers),
            "row_count": len(rows),
            "kind": kind,
            "filename_year": _year_from_filename(path.name),
            "filename_subdivision": _subdivision_from_filename(path.name),
            "source_class": USER_SOURCE_CLASS,
            "importer_version": USER_IMPORTER_VERSION,
            "parse_status": parse_meta.get("status"),
            "unclassified_headers": unclassified_headers,
            "unclassified_preserved": True,
            "versioned_delta": bool(expected_names) and path.name not in expected_names,
        }
        files.append(file_row)
        if kind == "REVIEW_QUEUE":
            for ordinal, row in enumerate(rows):
                queue_rows.append(
                    {
                        "source_file": path.name,
                        "file_sha256": file_sha,
                        "record_ordinal": ordinal,
                        "fields": row,
                        "source_class": USER_SOURCE_CLASS,
                        "queue_not_appointment": True,
                    }
                )
            continue
        if parse_meta.get("status") != "OK":
            quarantined.append(
                {
                    "source_file": path.name,
                    "file_sha256": file_sha,
                    "parse": parse_meta,
                    "source_class": USER_SOURCE_CLASS,
                }
            )
            continue
        for ordinal, row in enumerate(rows):
            season = str(row.get("Season") or file_row["filename_year"] or "")
            team = str(row.get("Team") or "")
            team_id = str(row.get("Team ID") or "")
            source_subdivision = _row_source_subdivision(
                row, str(file_row["filename_subdivision"] or "")
            )
            observations.append(
                {
                    "source_file": path.name,
                    "file_sha256": file_sha,
                    "record_ordinal": ordinal,
                    "team": team,
                    "team_id_source": team_id,
                    "season_cell": season,
                    "filename_year": file_row["filename_year"],
                    "filename_subdivision": file_row["filename_subdivision"],
                    "source_subdivision": source_subdivision,
                    "as_of_date": str(row.get("As Of Date") or ""),
                    "source_urls": str(row.get("Source URLs") or ""),
                    "data_notes": str(row.get("Data Notes") or ""),
                    "fields": row,
                    "header_season_conflict": _header_season_conflict(
                        headers, season, file_row["filename_year"]
                    ),
                    "blank_team_id": not team_id.strip(),
                    "source_class": USER_SOURCE_CLASS,
                    "import_time_utc": imported_at,
                    "research_date_is_not_known_at": True,
                    "pit_admitted": False,
                }
            )
            for header, cell in row.items():
                spec = column_map.get(header, {})
                kind_col = str(spec.get("kind") or "UNCLASSIFIED_METADATA")
                cell_text = "" if cell is None else str(cell)
                obs_id = observation_id(
                    file_sha256=file_sha,
                    record_ordinal=ordinal,
                    header=header,
                    cell=cell_text,
                )
                missing = classify_missingness(cell_text)
                if kind_col != "ROLE_OBSERVATION":
                    continue
                physically_present_role_cells += 1
                segments = parse_person_segments(cell_text)
                parsed_person_segments += len(segments)
                support_column = "assistants / support" in header.casefold()
                if missing is not None:
                    role_cells.append(
                        {
                            "observation_id": obs_id,
                            "source_file": path.name,
                            "record_ordinal": ordinal,
                            "team": team,
                            "team_id_source": team_id,
                            "season": season,
                            "filename_subdivision": file_row["filename_subdivision"],
                            "source_subdivision": source_subdivision,
                            "role_column": header,
                            "cell_text": cell_text,
                            "disposition": missing,
                            "person": None,
                            "source_title": None,
                            "support_column": support_column,
                            "source_class": USER_SOURCE_CLASS,
                            "pit_admitted": False,
                            "column_is_not_role_authority": True,
                        }
                    )
                    continue
                if not segments:
                    role_cells.append(
                        {
                            "observation_id": obs_id,
                            "source_file": path.name,
                            "record_ordinal": ordinal,
                            "team": team,
                            "team_id_source": team_id,
                            "season": season,
                            "filename_subdivision": file_row["filename_subdivision"],
                            "source_subdivision": source_subdivision,
                            "role_column": header,
                            "cell_text": cell_text,
                            "disposition": "UNPARSED_NONEMPTY_CELL",
                            "person": None,
                            "source_title": None,
                            "support_column": support_column,
                            "source_class": USER_SOURCE_CLASS,
                            "pit_admitted": False,
                        }
                    )
                    continue
                seen_people: set[str] = set()
                for segment in segments:
                    person_key = segment["person_raw"].casefold()
                    duplicate = person_key in seen_people
                    seen_people.add(person_key)
                    title = segment["title_raw"] or header
                    mapped = assignments_from_title(title)
                    principal_blocked = support_column or any(
                        item["occupancy"] == "QUALIFIED_NOT_PRINCIPAL"
                        for item in mapped
                    )
                    role_cells.append(
                        {
                            "observation_id": obs_id,
                            "canonical_claim_id": canonical_claim_id(
                                team_id=team_id or team,
                                season=season,
                                role_column=header,
                                person=segment["person_raw"],
                                title=title,
                            ),
                            "source_file": path.name,
                            "record_ordinal": ordinal,
                            "team": team,
                            "team_id_source": team_id,
                            "season": season,
                            "filename_subdivision": file_row["filename_subdivision"],
                            "source_subdivision": source_subdivision,
                            "role_column": header,
                            "cell_text": cell_text,
                            "segment_text": segment["segment_text"],
                            "person": segment["person_raw"],
                            "person_identity_key": re.sub(
                                r"\s+", " ", segment["person_raw"]
                            )
                            .casefold()
                            .strip(),
                            "source_title": title,
                            "assignments": mapped,
                            "disposition": (
                                "REPEATED_MULTI_COLUMN_PERSON"
                                if duplicate
                                else "USER_COMPILED_RESEARCH_OBSERVATION"
                            ),
                            "support_column": support_column,
                            "principal_role_blocked": principal_blocked,
                            "source_class": USER_SOURCE_CLASS,
                            "pit_admitted": False,
                            "column_is_not_role_authority": True,
                            "verified": False,
                        }
                    )
    staff_files = [row for row in files if row["kind"] != "REVIEW_QUEUE"]
    queue_files = [row for row in files if row["kind"] == "REVIEW_QUEUE"]
    return {
        "artifact_type": "CYCLE33_USER_COACHES_IMPORT",
        "artifact_class": "REAL_EVIDENCE",
        "source_class": USER_SOURCE_CLASS,
        "importer_version": USER_IMPORTER_VERSION,
        "snapshot": str(root),
        "import_time_utc": imported_at,
        "file_count": len(files),
        "staff_file_count": len(staff_files),
        "queue_file_count": len(queue_files),
        "staff_observation_count": len(observations),
        "staff_row_count": len(observations),
        "queue_row_count": len(queue_rows),
        "physically_present_role_cells": physically_present_role_cells,
        "parsed_person_segment_count": parsed_person_segments,
        "emitted_role_assignment_records": len(role_cells),
        "role_cell_count": len(role_cells),
        "role_cell_count_is_expanded_assignments": True,
        "distinct_source_role_cell_ids": len(
            {str(row.get("observation_id") or "") for row in role_cells}
        ),
        "records_with_person": sum(1 for row in role_cells if row.get("person")),
        "canonical_people_count": len(
            {
                str(row.get("person_identity_key") or "")
                for row in role_cells
                if row.get("person_identity_key")
            }
        ),
        "quarantined_count": len(quarantined),
        "manifest_file_count": len(expected_names),
        "extra_versioned_files": extra_files,
        "missing_manifest_files": missing_files,
        "grains_are_not_unique_people": True,
        "pit_admitted": False,
        "official_confirmation": False,
        "files": files,
        "observations": observations,
        "role_cells": role_cells,
        "queue_rows": queue_rows,
        "quarantined": quarantined,
        "counts_are_not_verification": True,
    }


def _header_season_conflict(
    headers: Sequence[str], season_cell: str, filename_year: int | None
) -> dict[str, Any]:
    stale = [
        h
        for h in headers
        if re.search(r"20\d{2}", h) and season_cell and str(filename_year) not in h
    ]
    year_in_headers = sorted(
        {
            int(m.group(0))
            for h in headers
            for m in [re.search(r"(?:19|20)\d{2}", h)]
            if m
        }
    )
    return {
        "season_cell": season_cell,
        "filename_year": filename_year,
        "year_labelled_headers": year_in_headers,
        "stale_year_headers": stale,
        "conflict": bool(
            filename_year
            and season_cell
            and str(filename_year) != str(season_cell).strip()
        )
        or any(year != filename_year for year in year_in_headers if filename_year),
    }


NAMED_OVERLAP_KEYS: tuple[dict[str, Any], ...] = (
    {
        "label": "FIU_2004",
        "season": "2004",
        "team_keys": ("fiu", "florida international"),
    },
    {
        "label": "FAU_2004",
        "season": "2004",
        "team_keys": ("florida_atlantic", "florida atlantic", "fau"),
    },
    {
        "label": "WKU_2007",
        "season": "2007",
        "team_keys": ("western_kentucky", "western kentucky", "wku"),
    },
)


def conservation_checks(imported: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct summary grains from row-level records. None is unique people."""

    observations = list(imported.get("observations") or [])
    role_cells = list(imported.get("role_cells") or [])
    queue_rows = list(imported.get("queue_rows") or [])
    files = list(imported.get("files") or [])
    reconstructed = {
        "source_files": len(files),
        "staff_rows": len(observations),
        "queue_rows": len(queue_rows),
        "physically_present_role_cells": len(
            {str(row.get("observation_id") or "") for row in role_cells}
        ),
        "parsed_person_segments": sum(1 for row in role_cells if row.get("person")),
        "emitted_role_assignment_records": len(role_cells),
        "distinct_source_role_cell_ids": len(
            {str(row.get("observation_id") or "") for row in role_cells}
        ),
        "canonical_people_keys": len(
            {
                str(row.get("person_identity_key") or "")
                for row in role_cells
                if row.get("person_identity_key")
            }
        ),
    }
    declared = {
        "source_files": imported.get("file_count"),
        "staff_rows": imported.get("staff_row_count")
        or imported.get("staff_observation_count"),
        "queue_rows": imported.get("queue_row_count"),
        "physically_present_role_cells": imported.get("physically_present_role_cells"),
        "parsed_person_segments": imported.get("parsed_person_segment_count"),
        "emitted_role_assignment_records": imported.get(
            "emitted_role_assignment_records"
        )
        or imported.get("role_cell_count"),
        "distinct_source_role_cell_ids": imported.get("distinct_source_role_cell_ids"),
        "canonical_people_keys": imported.get("canonical_people_count"),
    }
    mismatches = {
        key: {"declared": declared[key], "reconstructed": reconstructed[key]}
        for key in reconstructed
        if declared.get(key) not in {None, reconstructed[key]}
    }
    return {
        "reconstructed": reconstructed,
        "declared": declared,
        "mismatches": mismatches,
        "conserved": not mismatches,
        "grains_are_not_unique_people": True,
        "hardcoded_counters_forbidden": True,
    }


def _team_key(row: Mapping[str, Any]) -> str:
    team_id = str(row.get("team_id_source") or "").strip().casefold()
    if team_id:
        return team_id
    return re.sub(r"\s+", " ", str(row.get("team") or "")).strip().casefold()


def overlap_program_seasons(
    imported: Mapping[str, Any],
) -> dict[str, Any]:
    """Same program-season listed under both FBS and FCS source files."""

    buckets: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
    for row in imported.get("observations") or []:
        season = str(row.get("season_cell") or row.get("filename_year") or "")
        key = (season, _team_key(row))
        sub = str(
            row.get("filename_subdivision") or row.get("source_subdivision") or ""
        )
        bucket = buckets.setdefault(key, {"FBS": [], "FCS": [], "OTHER": []})
        if "FCS" in sub.upper() or "I-AA" in sub.upper() or "IAA" in sub.upper():
            bucket["FCS"].append(row)
        elif "FBS" in sub.upper() and "FCS" not in sub.upper():
            bucket["FBS"].append(row)
        else:
            bucket["OTHER"].append(row)
    overlaps = []
    for (season, team_key), bucket in sorted(buckets.items()):
        if bucket["FBS"] and bucket["FCS"]:
            overlaps.append(
                {
                    "season": season,
                    "team_key": team_key,
                    "team": (
                        bucket["FBS"][0].get("team") or bucket["FCS"][0].get("team")
                    ),
                    "fbs_files": sorted(
                        {str(row.get("source_file")) for row in bucket["FBS"]}
                    ),
                    "fcs_files": sorted(
                        {str(row.get("source_file")) for row in bucket["FCS"]}
                    ),
                    "disposition": "TRANSITION_OVERLAP_BOTH_SOURCE_ROWS_RETAINED",
                    "silent_fbs_promotion_forbidden": True,
                    "review_queue_is_not_repair": True,
                    "pit_admitted": False,
                }
            )
    named = []
    for spec in NAMED_OVERLAP_KEYS:
        match = [
            row
            for row in overlaps
            if row["season"] == spec["season"]
            and any(
                token == row["team_key"] or token in row["team_key"]
                for token in spec["team_keys"]
            )
        ]
        named.append(
            {
                **spec,
                "found": bool(match),
                "matches": match,
                "adjudication": (
                    "BOTH_SOURCE_SUBDIVISION_ROWS_RETAINED_NO_AUTO_FBS"
                    if match
                    else "NAMED_OVERLAP_KEY_NOT_FOUND"
                ),
            }
        )
    return {
        "overlap_count": len(overlaps),
        "overlaps": overlaps,
        "named_keys": named,
        "all_named_found": all(row["found"] for row in named),
        "filename_subdivision_is_not_historical_membership": True,
        "pit_admitted": False,
    }


def adjudicate_risk_fragment(
    fragment: Mapping[str, Any],
) -> dict[str, Any]:
    """Title-taxonomy adjudication. Not official confirmation or PIT."""

    text = str(fragment.get("fragment") or "")
    column = str(fragment.get("column") or "")
    segments = parse_person_segments(text)
    title = segments[0]["title_raw"] if segments else text
    person = segments[0]["person_raw"] if segments else None
    mapped = assignments_from_title(title or text)
    qualifiers = tuple(
        item for assignment in mapped for item in assignment.get("qualifiers") or []
    )
    occupancies = {str(item.get("occupancy")) for item in mapped}
    roles = {str(item.get("role")) for item in mapped}
    interim = any(
        token in {QUALIFIER_INTERIM, QUALIFIER_ACTING} for token in qualifiers
    ) or bool(re.search(r"\b(interim|acting)\b", text, re.I))
    column_folded = column.casefold()
    if interim and (
        "head_coach" in roles
        or re.search(r"\b(interim|acting)\s+head(?:\s+football)?\s+coach\b", text, re.I)
    ):
        disposition = "POSITIVE_CONTROL_INTERIM_OR_ACTING"
    elif (
        re.search(r"\bassoc(?:iate|\.)?\s+hc\b", text, re.I)
        and "head coach" in column_folded
    ):
        disposition = "REJECTED_NOT_PRINCIPAL_FOR_HC_COLUMN"
    elif (
        "head coach" in column_folded
        and occupancies & {"QUALIFIED_NOT_PRINCIPAL"}
        and "PRINCIPAL" not in occupancies
    ):
        disposition = "REJECTED_NOT_PRINCIPAL_FOR_HC_COLUMN"
    elif (
        "head coach" in column_folded
        and "head_coach" in roles
        and "PRINCIPAL"
        in {
            str(item.get("occupancy"))
            for item in mapped
            if item.get("role") == "head_coach"
        }
    ):
        disposition = "PRINCIPAL_HC_FROM_USER_TITLE_NOT_OFFICIAL"
    elif "head coach" in column_folded:
        disposition = "REJECTED_NOT_PRINCIPAL_FOR_HC_COLUMN"
    elif "formal title not established" in text.casefold():
        disposition = "FORMAL_TITLE_NOT_ESTABLISHED_NOT_PRINCIPAL"
    elif any(token in column_folded for token in ("coordinator",)) and not any(
        item.get("occupancy") == "PRINCIPAL"
        and item.get("role") in {"offensive_coordinator", "defensive_coordinator"}
        for item in mapped
    ):
        disposition = "QUALIFIED_NOT_PRINCIPAL_COORDINATOR"
    else:
        disposition = "OWNER_EPISODE_REVIEW_RETAINED"
    return {
        **dict(fragment),
        "person": person,
        "parsed_title": title,
        "taxonomy_assignments": mapped,
        "adjudication": disposition,
        "review_queue_is_not_repair": disposition == "OWNER_EPISODE_REVIEW_RETAINED",
        "fact_verified": False,
        "identity_accepted": False,
        "official_confirmation": False,
        "pit_admitted": False,
    }


def adjudicate_risk_fragments(
    fragments: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [adjudicate_risk_fragment(item) for item in fragments]
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("adjudication") or "")
        counts[key] = counts.get(key, 0) + 1
    return {
        "count": len(rows),
        "by_adjudication": counts,
        "rows": rows,
        "fact_verified": False,
        "pit_admitted": False,
    }


def coverage_by_year(imported: Mapping[str, Any]) -> dict[str, Any]:
    rows: dict[tuple[str, str], dict[str, int]] = {}
    for row in imported.get("observations") or []:
        key = (
            str(row.get("filename_year") or ""),
            str(row.get("filename_subdivision") or ""),
        )
        bucket = rows.setdefault(key, {"observations": 0, "blank_team_id": 0})
        bucket["observations"] += 1
        if row.get("blank_team_id"):
            bucket["blank_team_id"] += 1
    return {
        "by_year_subdivision": [
            {
                "year": year,
                "subdivision": subdivision,
                **counts,
            }
            for (year, subdivision), counts in sorted(rows.items())
        ]
    }
