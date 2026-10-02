"""R36-05: process the whole cached career corpus, not only the 48 declared keys.

R36-05 says to exhaust cached career evidence first, and the Cycle #36 pack's
closeout rule says an unresolved historical project does not authorise
abandoning ordinary row joins or actual ingestion. Cycle #36's first pass
reconciled the 48-key tranche in full and left the other 8,399 cached career
pages unread, recording that as local implementation work it did not reach.
The cache is mounted and costs nothing to read, so it is read here.

Every page and every episode inside it gets a disposition. The interesting
part is how few of them can legitimately be joined, and why:

  * the employer is a free-text string from a Wikimedia infobox. It is
    resolved through the SAME crosswalk R36-04 built -- no second, looser
    matcher -- so "Stamford HS (TX)" and "Abilene Christian" fail for
    different, named reasons rather than both becoming "unresolved";
  * the role is decomposed with the same cycle33 taxonomy the staff ingest
    uses. A page that says "assistant" entails no specific role and is
    refused rather than promoted to a generic position;
  * the interval must be present. "ongoing" without an end year is kept as
    an open interval, not silently closed at the revision date;
  * nothing is admitted. Every episode in this corpus carries
    evidence_class RETROSPECTIVE_CANDIDATE_ONLY and pit_admitted false at
    source, and this tool never raises either.

Two defects in the cached rows are surfaced rather than repaired. The
upstream parser splits a parenthetical out of the employer and into the
title, so a row reads program_raw "Stamford HS" with raw_title "TX"; and the
same display name can belong to more than one person across pages. Both are
recorded as states on the affected rows. Repairing the upstream parse would
change what a predecessor cycle published, which is not this tool's to do.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402
from aggie_analytics.cycle33.role_taxonomy import (  # noqa: E402
    TAXONOMY_VERSION,
    assignments_from_title,
)
from aggie_analytics.cycle36.jsonl_io import write_jsonl_verified  # noqa: E402
from aggie_analytics.cycle36.program_crosswalk import (  # noqa: E402
    CROSSWALK_VERSION,
    RESOLVED,
    build_crosswalk,
    load_payloads,
)

CORPUS_VERSION = "BAS-CAREER-CORPUS-v36.1"

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
OUTPUTS = CYCLE30 / "outputs"
RAW_TEAMS = CYCLE30 / "raw" / "teams"
CAREER_PAGES = OUTPUTS / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"
ACQUISITION_LEDGER = OUTPUTS / "CYCLE30_ACQUISITION_LEDGER.json"
HISTORICAL = OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
DECLARED_SCOPE = (1963, 2026)

# Episode dispositions. Each names the first thing that was missing, checked
# in this order, so a row is never refused for two reasons at once and the
# counts partition the corpus.
NO_EMPLOYER = "REFUSED_EMPLOYER_RESOLVES_TO_NO_DECLARED_PROGRAM"
EMPLOYER_AMBIGUOUS = "REFUSED_EMPLOYER_MATCHES_MORE_THAN_ONE_PROGRAM"
NO_ROLE = "REFUSED_NO_SPECIFIC_ROLE_ENTAILED_BY_THE_SOURCE_TITLE"
NO_INTERVAL = "REFUSED_NO_INTERVAL"
CANDIDATE = "CANDIDATE_CAREER_EPISODE_RETAINED_NOT_JOINED"

PARSE_ARTIFACT = "SOURCE_PARSE_ARTIFACT_TITLE_LOOKS_LIKE_AN_EMPLOYER_QUALIFIER"
HOMONYM = "PERSON_DISPLAY_NAME_IS_SHARED_BY_MORE_THAN_ONE_PAGE"

#: A raw_title that is a bare US state or province code, a bare year, or a
#: bare parenthetical residue is the upstream employer split leaking into the
#: title field. Detecting it is not repairing it.
_QUALIFIER_LIKE = re.compile(
    r"^(?:[A-Z]{2}|\(?[A-Z]{2}\)?|\d{4}|[A-Z][a-z]+\.?)$"
)
_US_STATE = frozenset(
    """AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS
    MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI
    WY DC PR ON QC BC AB""".split()
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def request_identity(endpoint: str, parameters: dict[str, Any]) -> str:
    """The same content-addressed request identity R36-04 uses.

    load_payloads takes the function, not a precomputed map. It also has to
    be THIS function: a hand-rolled json.dumps with different separators
    would hash to a different name, find no cached payload, and quietly
    resolve every employer to nothing while looking like it worked.
    """

    return sha256_json({"endpoint": endpoint, "parameters": parameters})


def looks_like_an_employer_qualifier(raw_title: str) -> bool:
    """Is this title actually a state code the upstream parser split off?

    Two of the abbreviations these pages use are also state codes: GA is
    Graduate Assistant as well as Georgia, and DC is Defensive Coordinator as
    well as the District of Columbia. A detector that only compared against
    the state list flagged every one of those as a parse artifact. So a
    string the role taxonomy resolves to a specific role is a title, whatever
    else it also spells.
    """

    text = str(raw_title or "").strip().strip("()")
    if not text:
        return False
    resolved = [
        a.get("role")
        for a in assignments_from_title(text)
        if a.get("role") not in {None, "", "unmapped_title_review_required"}
    ]
    if resolved:
        return False
    if text.upper() in _US_STATE:
        return True
    return bool(_QUALIFIER_LIKE.match(text)) and len(text) <= 4


def build(out_dir: Path) -> dict[str, Any]:
    pages = read_jsonl(CAREER_PAGES)
    low, high = DECLARED_SCOPE
    payloads = load_payloads(RAW_TEAMS, range(low, high + 1), request_identity)
    crosswalk = build_crosswalk(
        payloads,
        declared_name_rows=read_jsonl(HISTORICAL),
    )

    # Homonyms are a property of the corpus, so they are computed before any
    # episode is dispositioned rather than discovered row by row.
    pages_by_person: dict[str, set[str]] = collections.defaultdict(set)
    for page in pages:
        for episode in page.get("episodes") or []:
            person = str(episode.get("person") or page.get("title") or "")
            if person:
                pages_by_person[person].add(str(page.get("pageid")))
    homonyms = {
        person for person, ids in pages_by_person.items() if len(ids) > 1
    }

    resolutions: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    page_states: collections.Counter = collections.Counter()
    episode_states: collections.Counter = collections.Counter()
    flags: collections.Counter = collections.Counter()
    role_codes: collections.Counter = collections.Counter()
    employers_unresolved: collections.Counter = collections.Counter()

    for page in pages:
        status = str(page.get("status") or "UNKNOWN")
        artifact_class = str(page.get("artifact_class") or "UNKNOWN")
        page_states[f"{artifact_class}/{status}"] += 1
        episodes = page.get("episodes") or []
        for index, episode in enumerate(episodes):
            person = str(episode.get("person") or page.get("title") or "")
            employer_raw = str(episode.get("program_raw") or "")
            source_title = str(
                episode.get("source_title") or episode.get("raw_title") or ""
            )
            start = episode.get("start_year")
            end = episode.get("end_year")
            ongoing = bool(episode.get("ongoing"))

            if employer_raw not in resolutions:
                resolutions[employer_raw] = crosswalk.resolve(employer_raw)
            resolution = resolutions[employer_raw]

            row_flags: list[str] = []
            if looks_like_an_employer_qualifier(source_title):
                row_flags.append(PARSE_ARTIFACT)
            if person in homonyms:
                row_flags.append(HOMONYM)
            for flag in row_flags:
                flags[flag] += 1

            assignments = assignments_from_title(source_title) if source_title else []
            # The cycle33 taxonomy names the field "role", not "role_code".
            # Reading the wrong key made every one of the 27,174 episodes
            # that reached this test look unmapped, which would have reported
            # a whole corpus as roleless when the taxonomy in fact resolves
            # OC/QB, DC, WR, GA and head coach correctly.
            specific = [
                a
                for a in assignments
                if a.get("role")
                not in {None, "", "unmapped_title_review_required"}
            ]

            if resolution["state"] != RESOLVED:
                state = (
                    EMPLOYER_AMBIGUOUS
                    if "MORE_THAN_ONE" in resolution["state"]
                    else NO_EMPLOYER
                )
                employers_unresolved[employer_raw] += 1
            elif not specific:
                state = NO_ROLE
            elif start is None and end is None and not ongoing:
                state = NO_INTERVAL
            else:
                state = CANDIDATE
                for assignment in specific:
                    role_codes[str(assignment.get("role"))] += 1

            episode_states[state] += 1
            rows.append(
                {
                    "span_id": episode.get("span_id"),
                    "pageid": page.get("pageid"),
                    "page_title": page.get("title"),
                    "requested_title": page.get("requested_title"),
                    "wikidata_qid": page.get("wikidata_qid"),
                    "wikimedia_revision": page.get("wikimedia_revision")
                    or episode.get("wikimedia_revision"),
                    "revision_timestamp": page.get("revision_timestamp"),
                    "episode_index": index,
                    "person_display_name": person,
                    "employer_raw": employer_raw,
                    "employer_resolution_state": resolution["state"],
                    "employer_program_id": resolution.get("canonical_program_id"),
                    "source_title": source_title,
                    "role_codes": [a.get("role") for a in specific],
                    "occupancies": [a.get("occupancy") for a in specific],
                    "units": [a.get("unit") for a in specific],
                    "taxonomy_version": TAXONOMY_VERSION,
                    "crosswalk_version": CROSSWALK_VERSION,
                    "start_year": start,
                    "end_year": end,
                    "ongoing": ongoing,
                    "source_year_text": episode.get("source_year_text"),
                    "evidence_class": episode.get("evidence_class"),
                    "pit_admitted": False,
                    "state": state,
                    "flags": row_flags,
                    "joined": False,
                    "why_not_joined": (
                        "Every episode in this corpus is "
                        "RETROSPECTIVE_CANDIDATE_ONLY with pit_admitted false "
                        "at source. Resolving an employer and a role makes an "
                        "episode addressable; it does not make it "
                        "corroborated, so nothing here is joined into a "
                        "delivered assignment."
                    ),
                }
            )

    rows_path = out_dir / "CYCLE36_CAREER_EPISODE_ROWS.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_result = write_jsonl_verified(rows_path, rows)

    artifact = {
        "artifact_type": "CYCLE36_CAREER_CORPUS",
        "corpus_version": CORPUS_VERSION,
        "generated_at_utc": utc_now(),
        "source": {
            "path": str(CAREER_PAGES),
            "pages": len(pages),
            "sha256": (
                hashlib.sha256(CAREER_PAGES.read_bytes()).hexdigest()
                if CAREER_PAGES.is_file()
                else None
            ),
        },
        "pages_read": len(pages),
        "page_states": dict(page_states),
        "episode_rows": len(rows),
        "episode_states": dict(episode_states),
        "every_episode_dispositioned": sum(episode_states.values()) == len(rows),
        "candidate_episodes": episode_states.get(CANDIDATE, 0),
        "joined_episodes": 0,
        "nothing_admitted_as_official": True,
        "no_row_is_pit_admitted": all(not row["pit_admitted"] for row in rows),
        "role_codes_in_candidates": dict(role_codes.most_common()),
        "distinct_role_codes": len(role_codes),
        "distinct_unresolved_employers": len(employers_unresolved),
        "most_frequent_unresolved_employers": employers_unresolved.most_common(25),
        "flags": dict(flags),
        "homonym_display_names": len(homonyms),
        "surfaced_not_repaired": (
            "The upstream parser splits an employer qualifier into the title "
            "field, so rows exist with program_raw 'Stamford HS' and "
            "raw_title 'TX'. Those rows carry "
            f"{PARSE_ARTIFACT}. Repairing the parse would change what a "
            "predecessor cycle published, which is not this tool's to do."
        ),
        "same_crosswalk_as_r36_04": (
            "Employers resolve through the crosswalk R36-04 built, with no "
            "second looser matcher. An employer that is a high school, a "
            "professional club or a school outside the declared FBS/FCS "
            "population therefore fails for a named reason instead of being "
            "fuzzily attached to a similar college."
        ),
        "rows_file": str(rows_path),
        "post_write_verification": write_result,
    }

    _bas_atomic.write_text(out_dir / "CYCLE36_CAREER_CORPUS.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.out_dir)
    print(
        json.dumps(
            {
                key: artifact[key]
                for key in (
                    "pages_read",
                    "episode_rows",
                    "episode_states",
                    "every_episode_dispositioned",
                    "candidate_episodes",
                    "joined_episodes",
                    "nothing_admitted_as_official",
                    "distinct_role_codes",
                    "distinct_unresolved_employers",
                    "flags",
                    "homonym_display_names",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
