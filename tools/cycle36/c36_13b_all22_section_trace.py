"""R36-13: section-level extraction and capability reconciliation for all 34
current All-22 owner documents.

MR35R-11 says the controlling AREA-24 authority is the 22-document owner
hierarchy, not the stale 12-file local aggregation, and the Cycle #36 pack
requires that each exact capability be resolved *from document metadata* --
never inferred from a filename, and never collapsed into a single-value
controlling field. Cycle #36's first pass did not do that. It qualified the
released C01 wheel and implemented one boundary, and recorded the remaining
trace as not done.

It is doable here and costs nothing. The manager already pinned all 34
remote documents at CFBProgramSpecifications head 886e277d and recorded each
one's remote digest, so this tool reads bytes that are already on disk:

  * every local copy is rehashed against the manager's recorded remote digest
    before a single field is believed;
  * the YAML front matter is parsed in both forms the documents actually use
    (a block list and an inline list), so ``capabilities`` stays a list;
  * every ``##`` section of every document is extracted with its heading and
    its span, which is what "section-level" means;
  * the current 0574-0595 series and the retained historical 0070-0081
    series are reconciled against each other and against each document's own
    supersession state.

What this tool must not do is as important. It does not claim BAS implements
any of these capabilities. Exactly one owner boundary -- 04_STAFF_PUBLISHER,
CAP-...-0578 -- has a BAS-local projection in this cycle, and the field
matrix already records that it is lossy and unadopted. Every other capability
is reported NOT_IMPLEMENTED_BY_BAS with the reason. Reading a plan is not
implementing it, and a trace that blurred the two would be the "table naming
them is not evidence that requirements are implemented" defect the pack names
directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
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

MANAGER_REVIEW = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
)
PINNED_DOCS = MANAGER_REVIEW / "all22_remote_plans"
REHASH = MANAGER_REVIEW / "ALL22_REMOTE_PLAN_REHASH_CURRENT.json"

TRACE_VERSION = "BAS-ALL22-SECTION-TRACE-v36.1"

#: The one capability BAS implemented a local boundary against this cycle.
#: It is named by its capability identifier, not by its filename, because the
#: pack forbids inferring a capability from a filename.
IMPLEMENTED_BOUNDARY = "CAP-BAS-INTEGRAT-04-STAFF-PUBLISHER-0578"

CURRENT_SERIES = range(574, 596)
HISTORICAL_SERIES = range(70, 82)

#: Phrases that contradict an ACCEPTED_PHASE_2_PLAN front matter when they
#: appear in the body. The pack asks for such contradictions to be surfaced
#: for owner adjudication, not resolved here.
#: These documents are hard-wrapped, so a phrase regex written with literal
#: spaces silently misses every occurrence that straddles a line break -- and
#: the one genuine contradiction in the corpus, "remains an incomplete Phase 2
#: draft", straddles one. Every inter-word gap is therefore \s+.
_DRAFT_PHRASES = (
    "to be decided",
    "to be determined",
    "TBD",
    "not yet decided",
    "not yet specified",
    r"remains? (?:an? )?incomplete",
    r"remains? (?:a )?draft",
    "draft only",
    "placeholder",
    "open question",
)
_DRAFT_LANGUAGE = re.compile(
    r"\b(?:"
    + "|".join(phrase.replace(" ", r"\s+") for phrase in _DRAFT_PHRASES)
    + r")\b",
    re.I,
)

#: A bare "incomplete" is not evidence of a contradiction. These documents use
#: INCOMPLETE as a RESULT STATE -- "Results are `VALID_FOR_PIT_IMPORT`,
#: `PARTIAL_ALLOWED`, `INCOMPLETE`, ..." -- and as a domain condition, as in
#: "incomplete roster" and "incomplete denominators". A first version of this
#: scan matched the word anywhere and reported six contradictions of which
#: five were enum values and domain vocabulary. The phrase now has to be
#: about the document's own planning state, and anything inside backticks is
#: removed before the scan so a state name can never match.
_CODE_SPAN = re.compile(r"`[^`]*`")
_ABOUT_THE_PLAN = re.compile(
    r"\b(plan|planning|draft|hierarchy|phase\s*2|document|specification|"
    r"this\s+(?:doc|section|area))\b",
    re.I,
)

_SECTION = re.compile(r"^(#{1,6})\s+(.*)$")
_CAP_SUFFIX = re.compile(r"-(\d{4})$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    return text[3:end], text[end + 4 :]


def _scalar(raw: str) -> Any:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",")]
    return value.strip("'\"")


def parse_front_matter(block: str) -> dict[str, Any]:
    """Parse the small YAML dialect these documents actually use.

    Two forms carry ``capabilities``: an inline ``[...]`` list and a block
    list of ``- `` items. A parser that handled only one of them would drop
    CAP-...-0074 silently, which is exactly the kind of quiet omission that
    makes a reconciliation look complete when it is not.
    """

    fields: dict[str, Any] = {}
    key: str | None = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and key:
            fields.setdefault(key, [])
            if isinstance(fields[key], list):
                fields[key].append(_scalar(item.group(1)))
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1)
        remainder = match.group(2)
        if remainder.strip() == "":
            fields[key] = []
        else:
            fields[key] = _scalar(remainder)
    return fields


def extract_sections(body: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    lines = body.splitlines()
    offset = 0
    for index, line in enumerate(lines):
        match = _SECTION.match(line)
        if match:
            heading = match.group(2).strip()
            number = None
            numbered = re.match(r"^(\d+)\.\s*(.*)$", heading)
            if numbered:
                number = int(numbered.group(1))
                heading = numbered.group(2).strip()
            sections.append(
                {
                    "level": len(match.group(1)),
                    "number": number,
                    "heading": heading,
                    "line": index + 1,
                    "char_offset": offset,
                }
            )
        offset += len(line) + 1
    for position, section in enumerate(sections):
        end = (
            sections[position + 1]["char_offset"]
            if position + 1 < len(sections)
            else len(body)
        )
        section["char_end"] = end
        section["body_chars"] = end - section["char_offset"]
    return sections


def draft_contradictions(body: str, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for section in sections:
        raw_chunk = body[section["char_offset"] : section["char_end"]]
        # Blank out code spans, preserving offsets so the quoted context still
        # lines up with the document a reader will open.
        chunk = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), raw_chunk)
        for match in _DRAFT_LANGUAGE.finditer(chunk):
            sentence_start = max(
                chunk.rfind(".", 0, match.start()) + 1,
                chunk.rfind("\n\n", 0, match.start()) + 1,
                0,
            )
            sentence_end = chunk.find(".", match.end())
            sentence_end = len(chunk) if sentence_end == -1 else sentence_end + 1
            sentence = chunk[sentence_start:sentence_end]
            if not _ABOUT_THE_PLAN.search(sentence):
                continue
            found.append(
                {
                    "section_number": section["number"],
                    "section_heading": section["heading"],
                    "phrase": match.group(0),
                    "quoted_sentence": " ".join(sentence.split()),
                }
            )
    return found


def capability_suffix(capability: str) -> int | None:
    match = _CAP_SUFFIX.search(str(capability))
    return int(match.group(1)) if match else None


def build(out_dir: Path) -> dict[str, Any]:
    rehash_rows = json.loads(REHASH.read_text(encoding="utf-8"))
    expected = {
        row["path"]: row["remote_sha256"] for row in rehash_rows
    }
    had_local_counterpart = {
        row["path"] for row in rehash_rows if row.get("local_sha256")
    }

    documents: list[dict[str, Any]] = []
    digest_failures: list[dict[str, Any]] = []
    for relative, remote_digest in sorted(expected.items()):
        path = PINNED_DOCS / Path(relative)
        if not path.is_file():
            digest_failures.append(
                {"path": relative, "state": "PINNED_COPY_MISSING"}
            )
            continue
        blob = path.read_bytes()
        actual = hashlib.sha256(blob).hexdigest()
        if actual != remote_digest:
            digest_failures.append(
                {
                    "path": relative,
                    "state": "PINNED_COPY_DOES_NOT_MATCH_THE_RECORDED_REMOTE_DIGEST",
                    "recorded": remote_digest,
                    "actual": actual,
                }
            )
            continue
        text = blob.decode("utf-8", errors="replace")
        front_raw, body = split_front_matter(text)
        front = parse_front_matter(front_raw)
        capabilities = front.get("capabilities")
        if isinstance(capabilities, str):
            capabilities = [capabilities]
        capabilities = list(capabilities or [])
        sections = extract_sections(body)
        suffixes = [capability_suffix(c) for c in capabilities]
        series = None
        if any(s in CURRENT_SERIES for s in suffixes if s is not None):
            series = "CURRENT_22_OWNER_HIERARCHY"
        elif any(s in HISTORICAL_SERIES for s in suffixes if s is not None):
            series = "RETAINED_HISTORICAL_AGGREGATION"
        documents.append(
            {
                "path": relative,
                "sha256": actual,
                "matches_recorded_remote_digest": True,
                "doc_id": front.get("doc_id"),
                "title": front.get("title"),
                "document_class": front.get("document_class"),
                "authority": front.get("authority"),
                "authority_state": front.get("authority_state"),
                "status": front.get("status"),
                "implementation_state": front.get("implementation_state"),
                "supersession_state": front.get("supersession_state"),
                "security_classification": front.get("security_classification"),
                "owner": front.get("owner"),
                "reviewers": front.get("reviewers"),
                "phase_relevance": front.get("phase_relevance"),
                "source_authority_ref": front.get("source_authority_ref"),
                "source_authority_commit": front.get("source_authority_commit"),
                "source_decisions": front.get("source_decisions"),
                "engineering_decisions": front.get("engineering_decisions"),
                # A list, always. The pack forbids collapsing several
                # capabilities into one controlling value, so this field is
                # never reduced to a scalar even when it holds one item.
                "capabilities": capabilities,
                "capability_suffixes": suffixes,
                "series": series,
                "capability_slug_equals_filename_stem": [
                    Path(relative).stem.upper().replace("_", "-") in str(c).upper()
                    for c in capabilities
                ],
                "section_count": len(sections),
                "sections": sections,
                "draft_language_contradicting_accepted_state": (
                    draft_contradictions(body, sections)
                    if str(front.get("authority_state")) == "ACCEPTED_PHASE_2_PLAN"
                    else []
                ),
                "had_a_stale_local_counterpart": relative in had_local_counterpart,
                "bas_implementation_state": (
                    "BAS_LOCAL_BOUNDARY_IMPLEMENTED_LOSSY_AND_UNADOPTED"
                    if IMPLEMENTED_BOUNDARY in capabilities
                    else "NOT_IMPLEMENTED_BY_BAS"
                ),
                "bas_implementation_reason": (
                    "The staff boundary is projected to the released C01 "
                    "StaffSnapshotV1 with a declared field matrix; the "
                    "projection is lossy and the owner has not adopted the "
                    "richer envelope."
                    if IMPLEMENTED_BOUNDARY in capabilities
                    else "Read and traced only. No BAS code implements this "
                    "capability, and reading a plan is not implementing it."
                ),
            }
        )

    current = [d for d in documents if d["series"] == "CURRENT_22_OWNER_HIERARCHY"]
    historical = [
        d for d in documents if d["series"] == "RETAINED_HISTORICAL_AGGREGATION"
    ]
    current_suffixes = sorted(
        {s for d in current for s in d["capability_suffixes"] if s is not None}
    )
    historical_suffixes = sorted(
        {s for d in historical for s in d["capability_suffixes"] if s is not None}
    )

    superseded_targets: list[dict[str, Any]] = []
    current_by_number: dict[int, str] = {}
    for doc in current:
        stem = Path(doc["path"]).stem
        lead = re.match(r"^(\d+)_", stem)
        if lead:
            current_by_number[int(lead.group(1))] = doc["path"]
    for doc in historical:
        state = str(doc.get("supersession_state") or "")
        target = (
            state[len("SUPERSEDED_BY_") :]
            if state.startswith("SUPERSEDED_BY_")
            else None
        )
        resolved: list[str] = []
        unresolved: list[str] = []
        if target:
            # The successor is written as a document number, a range
            # ("06_THROUGH_09_SOURCE_NAMED_OWNERS") or a conjunction
            # ("12_AND_13_SOURCE_NAMED_OWNERS"). A first version compared the
            # whole string to a filename stem and reported five of the twelve
            # historical documents as naming no successor, when every one of
            # them names several.
            # Not \b: "_" is a word character, so \b never fires between a
            # digit and the underscore in "06_THROUGH_09_SOURCE_NAMED_OWNERS"
            # and a first version resolved none of the twelve.
            numbers = [
                int(n) for n in re.findall(r"(?<![0-9])(\d{2})(?![0-9])", target)
            ]
            if "THROUGH" in target and len(numbers) >= 2:
                numbers = list(range(min(numbers[:2]), max(numbers[:2]) + 1))
            for number in numbers:
                if number in current_by_number:
                    resolved.append(current_by_number[number])
                else:
                    unresolved.append(f"{number:02d}")
        superseded_targets.append(
            {
                "path": doc["path"],
                "capability": (doc["capabilities"] or [None])[0],
                "supersession_state": state or None,
                "declared_successor": target,
                "resolved_successor_documents": resolved,
                "unresolved_successor_numbers": unresolved,
                "successor_is_a_current_document": bool(resolved and not unresolved),
                "declares_a_supersession_at_all": bool(target),
            }
        )

    contradictions = [
        {
            "path": doc["path"],
            "capability": (doc["capabilities"] or [None])[0],
            "findings": doc["draft_language_contradicting_accepted_state"],
        }
        for doc in documents
        if doc["draft_language_contradicting_accepted_state"]
    ]

    artifact = {
        "artifact_type": "CYCLE36_ALL22_SECTION_TRACE",
        "trace_version": TRACE_VERSION,
        "generated_at_utc": utc_now(),
        "source": {
            "pinned_copies": str(PINNED_DOCS),
            "digest_ledger": str(REHASH),
            "remote_head": sorted({row["remote_head"] for row in rehash_rows}),
            "repository": "CFBProgramSpecifications",
            "access": (
                "Read from the manager's already-pinned local copies. No "
                "network request, no owner checkout and no owner write."
            ),
        },
        "documents_declared": len(expected),
        "documents_read": len(documents),
        "every_document_matched_its_recorded_remote_digest": not digest_failures,
        "digest_failures": digest_failures,
        "current_hierarchy_count": len(current),
        "retained_historical_count": len(historical),
        "current_capability_series": current_suffixes,
        "current_series_is_exactly_0574_to_0595": current_suffixes
        == list(CURRENT_SERIES),
        "historical_capability_series": historical_suffixes,
        "historical_series_is_exactly_0070_to_0081": historical_suffixes
        == list(HISTORICAL_SERIES),
        "sections_extracted": sum(d["section_count"] for d in documents),
        "documents_with_no_capability": [
            d["path"] for d in documents if not d["capabilities"]
        ],
        "documents_with_more_than_one_capability": [
            d["path"] for d in documents if len(d["capabilities"]) > 1
        ],
        "capabilities_are_never_collapsed_into_one_field": (
            "Every document's capabilities value is carried as a list, even "
            "where it holds a single identifier, because a single-value "
            "controlling field cannot represent a document that later "
            "declares two."
        ),
        "capability_resolved_from_metadata_not_filename": (
            "Each capability is read from the document's own front matter. "
            "The per-document flag capability_slug_equals_filename_stem "
            "records where the slug happens to agree with the filename; "
            "agreement is an observation, not the basis of the resolution."
        ),
        "supersession": superseded_targets,
        "every_historical_document_that_declares_a_supersession_resolves_it": all(
            row["successor_is_a_current_document"]
            for row in superseded_targets
            if row["declares_a_supersession_at_all"]
        ),
        "historical_documents_declaring_no_supersession": [
            row["path"]
            for row in superseded_targets
            if not row["declares_a_supersession_at_all"]
        ],
        "authority_states": sorted(
            {str(d["authority_state"]) for d in documents}
        ),
        "implementation_states": sorted(
            {str(d["implementation_state"]) for d in documents}
        ),
        "bas_implementation": {
            "capabilities_with_a_bas_local_boundary": [
                c
                for d in documents
                for c in d["capabilities"]
                if d["bas_implementation_state"].startswith("BAS_LOCAL")
            ],
            "capabilities_not_implemented_by_bas": len(
                [d for d in documents if d["bas_implementation_state"] == "NOT_IMPLEMENTED_BY_BAS"]
            ),
            "reading_is_not_implementing": (
                "This trace establishes that every current owner document was "
                "read at section level and that its capability is bound to "
                "its metadata. It establishes nothing about whether BAS "
                "implements the capability, and 33 of 34 are explicitly not "
                "implemented."
            ),
        },
        "owner_adjudication_required": contradictions,
        "owner_adjudication_count": sum(
            len(entry["findings"]) for entry in contradictions
        ),
        "what_this_is_not": (
            "Not owner adoption, not schema approval, not activation, and "
            "not a claim that the technical-program requirement union is "
            "complete. Contradictions between an accepted front matter and a "
            "narrower paragraph are surfaced for the owner, not resolved."
        ),
        "documents": documents,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_ALL22_SECTION_TRACE.json", 
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
                    "documents_declared",
                    "documents_read",
                    "every_document_matched_its_recorded_remote_digest",
                    "current_hierarchy_count",
                    "retained_historical_count",
                    "current_series_is_exactly_0574_to_0595",
                    "historical_series_is_exactly_0070_to_0081",
                    "sections_extracted",
                    "every_historical_document_that_declares_a_supersession_resolves_it",
                    "owner_adjudication_count",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
