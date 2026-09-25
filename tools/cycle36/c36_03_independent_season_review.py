"""R36-03: an independent reader checks every admitted season-support tuple.

The producer (``aggie_analytics.cycle36.source_scoped_season``) builds a DOM
with ``html.parser``, classifies each region, and scopes a heading to the
records it governs. This checker deliberately does **none** of that. It scans
the raw bytes with its own regular expressions, finds ``<hN>`` elements
directly, computes their governed span from the next same-or-higher-rank
heading, and asks whether the producer's recorded season for a record agrees.

Two implementations that share no code can still both be wrong, so this is
evidence and not proof. What it does exclude is a producer that agrees with
itself: no function from the producer's module is imported here, and the
labels this checker emits are its own.

It also emits a deterministic stratified sample for a human to read: at least
sixty distinct official records spread across subdivision, role class, site
platform, season state and the specific capture shapes the manager's negative
controls were drawn from. Each sampled row carries a quoted excerpt of the
heading and of the record so a reviewer can check it without running
anything.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html as html_lib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
class _bas_atomic:  # U37-11: atomic writes, self-contained -- this tool stays independent of aggie_analytics
    @staticmethod
    def _begin(path):
        import os as _bas_os
        import pathlib as _bas_pathlib
        import tempfile as _bas_tempfile

        target = path.resolve() if path.is_symlink() else path
        handle, name = _bas_tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")
        _bas_os.close(handle)
        return target, _bas_pathlib.Path(name)

    @staticmethod
    def _finish(temporary, target):
        import os as _bas_os
        import stat as _bas_stat
        import time as _bas_time

        with open(temporary, "rb+") as stream:
            _bas_os.fsync(stream.fileno())
        try:
            mode = _bas_stat.S_IMODE(_bas_os.stat(target).st_mode)
        except FileNotFoundError:
            umask = _bas_os.umask(0)
            _bas_os.umask(umask)
            mode = 0o666 & ~umask
        _bas_os.chmod(temporary, mode)
        for attempt in range(6):
            try:
                _bas_os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                _bas_time.sleep(0.05 * (attempt + 1))

    @classmethod
    def _call(cls, method, path, *args, **kwargs):
        import pathlib as _bas_pathlib

        if not isinstance(path, _bas_pathlib.Path):
            return getattr(path, method)(*args, **kwargs)
        target, temporary = cls._begin(path)
        try:
            written = getattr(temporary, method)(*args, **kwargs)
            cls._finish(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return written

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        return cls._call("write_text", path, *args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        return cls._call("write_bytes", path, *args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        import contextlib as _bas_contextlib
        import pathlib as _bas_pathlib

        @_bas_contextlib.contextmanager
        def _stream():
            if not isinstance(path, _bas_pathlib.Path):
                with path.open(*args, **kwargs) as stream:
                    yield stream
                return
            target, temporary = cls._begin(path)
            try:
                with temporary.open(*args, **kwargs) as stream:
                    yield stream
                cls._finish(temporary, target)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise

        return _stream()

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]

#: This checker's own patterns. They are intentionally written from the
#: contract, not imported, so a change to the producer's regexes cannot
#: silently move this checker with them.
_HEADING = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.I | re.S)
_SEASON_IN_HEADING = re.compile(
    r"\b(20[0-3]\d)\s+(?:football\s+coaching\s+staff|football\s+staff\s+directory"
    r"|football\s+staff|coaching\s+staff|staff\s+directory|football\s+coaches"
    r"|football\s+roster|football\s+season|football\s+schedule)\b",
    re.I,
)
_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"(?is)<(script|style|noscript|template)\b.*?</\1>")
_COMMENT = re.compile(r"(?s)<!--.*?-->")

AGREES = "INDEPENDENT_READER_AGREES"
DISAGREES_SEASON = "INDEPENDENT_READER_READS_A_DIFFERENT_SEASON"
DISAGREES_UNBOUND = "INDEPENDENT_READER_FINDS_NO_GOVERNING_HEADING"
PRODUCER_UNBOUND_READER_FINDS = "PRODUCER_LEFT_UNBOUND_BUT_READER_FINDS_A_HEADING"
BOTH_UNBOUND = "BOTH_UNBOUND"
NOT_CHECKABLE = "NOT_CHECKABLE_NO_RECORD_OFFSET"
CAPTURE_MISSING = "CAPTURE_MISSING"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(_TAG.sub(" ", fragment))).strip()


def masked(text: str) -> str:
    """Blank out scripts and comments so a year inside them cannot be read.

    Replacing with spaces of equal length keeps every offset aligned with the
    original document, which is what lets the producer's recorded offsets be
    compared against this reader's spans.
    """

    def blank(match: "re.Match[str]") -> str:
        return " " * (match.end() - match.start())

    return _COMMENT.sub(blank, _SCRIPT.sub(blank, text))


def governing_headings(text: str) -> list[dict[str, Any]]:
    """Every ``hN`` heading with a season, and the span it governs."""

    body = masked(text)
    headings = []
    for match in _HEADING.finditer(body):
        rank = int(match.group(1)[1])
        headings.append(
            {
                "rank": rank,
                "start": match.start(),
                "end": match.end(),
                "text": plain(match.group(2))[:200],
            }
        )
    for index, heading in enumerate(headings):
        scope_end = len(body)
        for later in headings[index + 1 :]:
            if later["rank"] <= heading["rank"]:
                scope_end = later["start"]
                break
        heading["scope_end"] = scope_end
        seasons = sorted(
            {int(found.group(1)) for found in _SEASON_IN_HEADING.finditer(heading["text"])}
        )
        heading["seasons"] = seasons
    return [heading for heading in headings if heading["seasons"]]


def check_record(text: str, offset: int | None, recorded_season: Any) -> dict[str, Any]:
    if offset is None:
        return {"state": NOT_CHECKABLE, "reader_season": None}
    headings = governing_headings(text)
    governing = [
        heading
        for heading in headings
        if heading["start"] <= offset < heading["scope_end"]
    ]
    if not governing:
        return {
            "state": (
                BOTH_UNBOUND if recorded_season is None else DISAGREES_UNBOUND
            ),
            "reader_season": None,
            "headings_with_a_season": len(headings),
        }
    governing.sort(key=lambda heading: (heading["scope_end"] - heading["start"], -heading["start"]))
    tightest = governing[0]
    seasons = tightest["seasons"]
    reader_season = seasons[0] if len(seasons) == 1 else None
    if recorded_season is None:
        return {
            "state": (
                BOTH_UNBOUND if reader_season is None else PRODUCER_UNBOUND_READER_FINDS
            ),
            "reader_season": reader_season,
            "governing_heading_text": tightest["text"],
        }
    if reader_season == int(recorded_season):
        return {
            "state": AGREES,
            "reader_season": reader_season,
            "governing_heading_text": tightest["text"],
            "governing_span": [tightest["start"], tightest["scope_end"]],
        }
    return {
        "state": DISAGREES_SEASON,
        "reader_season": reader_season,
        "recorded_season": recorded_season,
        "governing_heading_text": tightest["text"],
    }


def stratum(row: dict[str, Any]) -> tuple[str, str, str, str]:
    classification = str(row.get("classification") or "UNKNOWN").upper()
    roles = row.get("role_codes") or []
    if any(
        role in {"head_coach", "offensive_coordinator", "defensive_coordinator"}
        for role in roles
    ):
        role_class = "CORE"
    elif "unmapped_title_review_required" in roles:
        role_class = "UNMAPPED"
    elif roles:
        role_class = "NON_CORE"
    else:
        role_class = "NONE"
    url = str(row.get("page_url") or row.get("capture_page_url") or "")
    if url.startswith("cache://") or not url:
        # A capture that matched no declared acquisition attempt has no
        # recorded request URL, so its site platform is genuinely unknown.
        # Calling that "cache:" would invent a platform that does not exist.
        platform = "CAPTURE_WITHOUT_A_RECORDED_URL"
    else:
        host = re.sub(r"^https?://", "", url).split("/", 1)[0] or "unknown-host"
        platform = host.split(".")[-2] if host.count(".") >= 1 else host
    # The checked record carries the producer's state under its own name; a
    # first version read "season_state" and collapsed every row into UNKNOWN,
    # which defeated two of the four declared strata.
    season_state = str(
        row.get("producer_season_state") or row.get("season_state") or "UNKNOWN"
    )
    return (classification, role_class, platform, season_state)


#: The five season cases the Cycle #35 manager review reported under
#: MR35R-04. They are synthetic probe files, not corpus records, so no
#: sampling strategy over the corpus can reach them. They are read here, by
#: this checker, so the previously reported corruptions appear in the same
#: human-readable review as the sampled records.
MANAGER_SEASON_PROBES = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35"
    r"\20260921T131038Z\synthetic_source_probes"
)
MANAGER_EXPECTATION = {
    "positive.html": "BOUND",
    "comment_only.html": "UNBOUND",
    "script_only.html": "UNBOUND",
    "archive_navigation.html": "UNBOUND",
    "biography.html": "UNBOUND",
}
#: What the Cycle #35 producer actually returned for each, quoted from
#: ADVERSARIAL_PROBE_RESULTS.json. All five were bound to 2026; four of them
#: should not have been. That is the defect R36-03 exists to repair.
CYCLE35_PRODUCER_VERDICT = {
    "positive.html": ("SEASON_BOUND_BY_UNANIMOUS_STAFF_LABEL", 2026),
    "comment_only.html": ("SEASON_BOUND_BY_UNANIMOUS_STAFF_LABEL", 2026),
    "script_only.html": ("SEASON_BOUND_BY_UNANIMOUS_STAFF_LABEL", 2026),
    "archive_navigation.html": ("SEASON_BOUND_BY_UNANIMOUS_STAFF_LABEL", 2026),
    "biography.html": ("SEASON_BOUND_BY_UNANIMOUS_STAFF_LABEL", 2026),
}


def manager_season_cases() -> dict[str, Any]:
    """Read the manager's five probe captures with this checker's own logic."""
    cases: list[dict[str, Any]] = []
    for name in sorted(MANAGER_EXPECTATION):
        path = MANAGER_SEASON_PROBES / name
        if not path.is_file():
            cases.append(
                {
                    "case": name,
                    "state": "FIXTURE_MISSING",
                    "path": str(path),
                }
            )
            continue
        blob = path.read_bytes()
        text_ = blob.decode("utf-8", errors="replace")
        headings = governing_headings(text_)
        # A record placed immediately after the last heading is the most
        # favourable position a binder could ask for. If no season governs
        # even there, no record in the capture can inherit one.
        offset = max((heading["start"] for heading in headings), default=0)
        probe = check_record(text_, len(text_) - 1 if headings else offset, None)
        reader_season = probe.get("reader_season")
        reader_verdict = "BOUND" if reader_season is not None else "UNBOUND"
        expected = MANAGER_EXPECTATION[name]
        producer35_state, producer35_season = CYCLE35_PRODUCER_VERDICT[name]
        cases.append(
            {
                "case": name,
                "path": str(path),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "manager_expected": expected,
                "cycle35_producer_state": producer35_state,
                "cycle35_producer_season": producer35_season,
                "cycle35_producer_was_wrong": expected == "UNBOUND",
                "independent_reader_verdict": reader_verdict,
                "independent_reader_season": reader_season,
                "independent_reader_agrees_with_the_manager": (
                    reader_verdict == expected
                ),
                "headings_carrying_a_season": [
                    heading["text"] for heading in headings
                ],
                "capture_text": text_,
            }
        )
    return {
        "what_this_is": (
            "The five season cases MR35R-04 reported, re-read by this "
            "checker. They are synthetic files rather than corpus records, "
            "so the stratified sample over the delivered rows cannot reach "
            "them; they are carried here so the previously reported "
            "corruptions are in the same human-readable review."
        ),
        "producer_verdicts_are_pinned_elsewhere": (
            "This artifact does not ask the Cycle #36 producer what it "
            "thinks, because this checker must not import it. "
            "tests/test_cycle36_source_scoped_season.py pins the Cycle #36 "
            "producer's verdict on these same five shapes."
        ),
        "cases": cases,
        "case_count": len(cases),
        "independent_reader_agrees_with_every_manager_expectation": all(
            case.get("independent_reader_agrees_with_the_manager") for case in cases
        ),
    }


def build(out_dir: Path, observations: Path, sample_target: int) -> dict[str, Any]:
    rows = read_jsonl(observations)
    # Every row the producer's season binder labelled -- not only the rows
    # whose CAPTURE also matched a declared acquisition receipt. The evidence
    # tier records whether the capture is bound to a receipt; it says nothing
    # about where the season came from. A first version of this checker
    # filtered on OFFICIAL_HTML_RECORD_BOUND and therefore read 5,123 of the
    # 16,074 labelled rows, leaving 5,987 bound seasons -- two thirds of every
    # season this cycle asserts -- with no independent reading at all, while
    # the artifact still said "every admitted season-support tuple".
    labelled = [row for row in rows if row.get("season_parser_version")]
    by_capture: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in labelled:
        by_capture[str(row.get("capture_path"))].append(row)

    states: collections.Counter = collections.Counter()
    disagreements: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    cache: dict[str, str | None] = {}

    for capture in sorted(by_capture):
        if capture not in cache:
            path = Path(capture)
            # Decode from BYTES, not through read_text. On Windows, read_text
            # applies universal-newline translation and silently removes every
            # CR, shifting all offsets: one capture here carries 3,390 of them.
            # The producer's recorded offsets are in the untranslated text, so
            # a reader that translates is comparing against a different
            # document and reports disagreements that are its own.
            cache[capture] = (
                path.read_bytes().decode("utf-8", errors="replace")
                if path.is_file()
                else None
            )
        text = cache[capture]
        for row in by_capture[capture]:
            if text is None:
                states[CAPTURE_MISSING] += 1
                continue
            result = check_record(
                text, row.get("person_body_offset"), row.get("season")
            )
            states[result["state"]] += 1
            record = {
                "capture_path": capture,
                "evidence_tier": row.get("evidence_tier"),
                "page_url": row.get("page_url"),
                "program_id": row.get("program_id"),
                "display_name": row.get("display_name"),
                "classification": row.get("classification"),
                "person": row.get("person"),
                "source_title": row.get("source_title"),
                "role_codes": row.get("role_codes"),
                "producer_season": row.get("season"),
                "producer_season_state": row.get("season_state"),
                "record_offset": row.get("person_body_offset"),
                "record_selector": row.get("record_selector"),
                **result,
            }
            checked.append(record)
            if result["state"] in {DISAGREES_SEASON, DISAGREES_UNBOUND}:
                disagreements.append(record)

    # Deterministic stratified sample. The declared dimensions are
    # subdivision, role class, season state and site platform. Stratifying on
    # all four at once produces hundreds of one-row cells and a round-robin
    # over them returns sixty rows that are all FBS/CORE -- which a first
    # version of this tool did. So the primary strata are the three
    # *semantic* dimensions, and platform diversity is obtained by cycling
    # platforms WITHIN each stratum. No random number participates.
    def primary(row: dict[str, Any]) -> tuple[str, str, str]:
        key = stratum(row)
        return (key[0], key[1], key[3])

    def platform_of(row: dict[str, Any]) -> str:
        return stratum(row)[2]

    # A row with no record offset, or whose capture is gone, cannot carry a
    # quoted excerpt, so it is counted but never sampled.
    sampleable = [
        row
        for row in checked
        if row.get("state") not in {NOT_CHECKABLE, CAPTURE_MISSING}
    ]
    strata: dict[tuple, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in sampleable:
        strata[primary(row)].append(row)

    def interleave_by_platform(bucket: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_platform: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for row in bucket:
            by_platform[platform_of(row)].append(row)
        for rows_ in by_platform.values():
            rows_.sort(
                key=lambda item: (item["capture_path"], item["record_offset"] or 0)
            )
        ordered: list[dict[str, Any]] = []
        platforms = sorted(by_platform)
        depth = 0
        while len(ordered) < len(bucket):
            for platform in platforms:
                rows_ = by_platform[platform]
                if depth < len(rows_):
                    ordered.append(rows_[depth])
            depth += 1
        return ordered

    for key in strata:
        strata[key] = interleave_by_platform(strata[key])

    sample: list[dict[str, Any]] = []
    ordered_keys = sorted(strata)
    index = 0
    while len(sample) < sample_target and ordered_keys:
        progressed = False
        for key in ordered_keys:
            bucket = strata[key]
            if index < len(bucket):
                row = bucket[index]
                text = cache.get(row["capture_path"])
                excerpt = ""
                if text and row["record_offset"] is not None:
                    start_at = max(0, int(row["record_offset"]) - 120)
                    excerpt = plain(
                        text[start_at : int(row["record_offset"]) + 220]
                    )
                sample.append(
                    {
                        **row,
                        "stratum": list(stratum(row)),
                        "primary_stratum": list(key),
                        "record_excerpt": excerpt[:320],
                        "human_check": (
                            "Does the quoted heading govern the quoted record, "
                            "and does the person and title appear there?"
                        ),
                    }
                )
                progressed = True
                if len(sample) >= sample_target:
                    break
        if not progressed:
            break
        index += 1

    not_checkable = states.get(NOT_CHECKABLE, 0) + states.get(CAPTURE_MISSING, 0)
    comparable = len(checked) - not_checkable
    by_tier: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for row in checked:
        by_tier[str(row.get("evidence_tier"))][str(row.get("state"))] += 1

    artifact = {
        "artifact_type": "CYCLE36_INDEPENDENT_SEASON_REVIEW",
        "generated_at_utc": utc_now(),
        "manager_season_cases": manager_season_cases(),
        "implementation": (
            "Separate read-only reader. It imports nothing from "
            "aggie_analytics.cycle36.source_scoped_season and writes its own "
            "labels."
        ),
        "observations_source": {
            "path": str(observations),
            "sha256": hashlib.sha256(observations.read_bytes()).hexdigest()
            if observations.is_file()
            else None,
            "rows": len(rows),
        },
        "rows_the_binder_labelled": len(labelled),
        "rows_examined": len(checked),
        "every_labelled_row_examined": len(checked) == len(labelled),
        "rows_not_comparable": not_checkable,
        "rows_compared": comparable,
        "official_tier_rows_checked": sum(
            1
            for row in checked
            if row.get("evidence_tier") == "OFFICIAL_HTML_RECORD_BOUND"
        ),
        "states_by_evidence_tier": {
            tier: dict(counter) for tier, counter in sorted(by_tier.items())
        },
        "evidence_tier_is_about_the_capture_not_the_season": (
            "OFFICIAL_HTML_RECORD_BOUND means the capture matched a declared "
            "acquisition receipt. CANDIDATE_FROM_UNBOUND_CAPTURE means it did "
            "not. Both tiers get their season from the same record-scoped "
            "binder, so both are read here; the tier is reported separately "
            "rather than used to narrow the check."
        ),
        "distinct_captures": len(by_capture),
        "states": dict(states),
        "concordant_rows": states.get(AGREES, 0) + states.get(BOTH_UNBOUND, 0),
        "concordance_rate": (
            round(
                (states.get(AGREES, 0) + states.get(BOTH_UNBOUND, 0)) / comparable,
                6,
            )
            if comparable
            else None
        ),
        "concordance_includes_agreed_absence": (
            "Both readers leaving a record unbound is agreement about the "
            "absence of evidence, so it counts as concordant. Reporting only "
            "the bound agreements would understate concordance by treating "
            "every honest unknown as a disagreement."
        ),
        "bound_agreement_rate": (
            round(
                states.get(AGREES, 0)
                / max(states.get(AGREES, 0) + states.get(DISAGREES_SEASON, 0), 1),
                6,
            )
        ),
        "decoding_contract": (
            "Both readers decode the capture from raw bytes. Universal-newline "
            "translation would shift every offset and make the comparison "
            "meaningless."
        ),
        "disagreements": disagreements[:60],
        "disagreement_count": len(disagreements),
        "stratified_sample": sample,
        "sample_size": len(sample),
        "sample_target": sample_target,
        "sample_meets_target": len(sample) >= sample_target,
        "distinct_strata_in_sample": len({tuple(row["stratum"]) for row in sample}),
        "distinct_primary_strata_in_sample": len(
            {tuple(row["primary_stratum"]) for row in sample}
        ),
        "primary_strata_available": len(strata),
        "distinct_platforms_in_sample": len(
            {row["stratum"][2] for row in sample}
        ),
        "distinct_subdivisions_in_sample": len(
            {row["stratum"][0] for row in sample}
        ),
        "distinct_role_classes_in_sample": len(
            {row["stratum"][1] for row in sample}
        ),
        "distinct_season_states_in_sample": len(
            {row["stratum"][3] for row in sample}
        ),
        "distinct_captures_in_sample": len({row["capture_path"] for row in sample}),
        "sample_is_deterministic": (
            "Strata are ordered by key and rows within a stratum by capture "
            "path and offset. No random number participates, so the same "
            "inputs give the same sample."
        ),
        "producer_did_not_label_its_own_check": True,
        "what_this_is_not": (
            "Two implementations agreeing is evidence, not proof. It excludes "
            "a producer certifying itself; it does not establish that the "
            "shared contract is the right one."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_INDEPENDENT_SEASON_REVIEW.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--sample-target", type=int, default=60)
    args = parser.parse_args()
    artifact = build(args.out_dir, args.observations, args.sample_target)
    print(
        json.dumps(
            {
                key: artifact[key]
                for key in (
                    "rows_the_binder_labelled",
                    "rows_examined",
                    "every_labelled_row_examined",
                    "rows_compared",
                    "rows_not_comparable",
                    "official_tier_rows_checked",
                    "distinct_captures",
                    "states",
                    "concordant_rows",
                    "concordance_rate",
                    "bound_agreement_rate",
                    "disagreement_count",
                    "sample_size",
                    "sample_meets_target",
                    "distinct_primary_strata_in_sample",
                    "primary_strata_available",
                    "distinct_platforms_in_sample",
                    "distinct_subdivisions_in_sample",
                    "distinct_role_classes_in_sample",
                    "distinct_season_states_in_sample",
                    "distinct_captures_in_sample",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
