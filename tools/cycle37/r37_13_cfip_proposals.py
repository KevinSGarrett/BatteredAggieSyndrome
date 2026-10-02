r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-13-AC08: send section-bound proposal corrections through the existing
CFIP owner issues, and read each one back.

Authority: recovery section 8 permits evidence/proposal comments on the
existing owner issues with readback, and the assignment retains that
permission with two conditions this tool implements literally:

* **A deterministic event marker.** Each proposal ends with a marker built
  from the issue key and the digest of the proposal body. The same evidence
  produces the same marker.
* **Check for an existing effect before any retry.** Before posting, the
  issue's comments are read; if a comment already carries this proposal's
  marker prefix, nothing is posted. If a POST fails, the comments are read
  again before the second and last try, so a POST that landed but whose
  response was lost is never duplicated.

The client can GET and POST a comment. It has no method for transitions,
field edits, issue creation or deletion. Every attempt counts against the
attempt's metadata ceiling.

Every proposal is bound to exact owner sections at the owner revision, with
the section body digest from the R37-14 extraction, and every number in it
is read from the BAS composition receipt or the delivered release. A
proposal is a proposal: it asks the owner to decide, adopts nothing, and
changes no owner repository, catalog or runtime.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from r37_14_jira_live_read import (  # noqa: E402
    BASE_URL,
    EMAIL,
    MAX_TRIES_PER_ROUTE,
    authoritative_env,
    read_token,
)
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
MARKER_PREFIX = "BAS-C37A2-R37-13-AC08"
OWNER_REVISION = "886e277dd9f34eb0ea1de78f98ee516bcc0c33cb"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")

#: Owner sections each proposal is bound to: (owner path, heading as written).
BINDINGS = {
    "CFIP-19": [
        ("50_BAS_INTEGRATION/00_BAS_FILM_INTEGRATION_MASTER.md", "3. Authority and release composition"),
        ("50_BAS_INTEGRATION/00_BAS_FILM_INTEGRATION_MASTER.md", "4. Failure, invalidation, rollback and recovery"),
    ],
    "CFIP-22": [
        ("50_BAS_INTEGRATION/04_STAFF_PUBLISHER.md", "2. Source assertion grain and identity"),
        ("50_BAS_INTEGRATION/04_STAFF_PUBLISHER.md", "4. PIT, conflicts and corrections"),
        ("50_BAS_INTEGRATION/12_COACH_STATE_IMPORT.md", "2. Vector, conflicts and PIT"),
        ("50_BAS_INTEGRATION/13_TEAM_SCHEME_IMPORT.md", "1. Authority and grain"),
    ],
    "CFIP-24": [
        ("50_BAS_INTEGRATION/08_FILM_PIT_IMPORT.md", "2. Time coordinates and eligibility"),
        ("50_BAS_INTEGRATION/08_FILM_PIT_IMPORT.md", "5. Correction, rollback and recovery"),
        ("50_BAS_INTEGRATION/09_FILM_PROVENANCE_IMPORT.md", "4. Rights, correction and recovery"),
    ],
    "CFIP-27": [
        ("50_BAS_INTEGRATION/21_BAS_FILM_ACCEPTANCE.md", "4. Mandatory end-to-end walkthroughs"),
        ("50_BAS_INTEGRATION/21_BAS_FILM_ACCEPTANCE.md", "7. Acceptance evidence record"),
        ("50_BAS_INTEGRATION/03_ROSTER_PUBLISHER.md", "11. Qualification and acceptance"),
    ],
}

NONCLAIMS = (
    "Submitted for owner review, not adoption. BAS changed no owner repository, "
    "catalog, schema or runtime; this is not a C01 self-approval, not a scientific "
    "acceptance and not a request to transition this issue. Operator hold unchanged."
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_sections(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_class") != "ALL22_COUNTERPART":
            continue
        owner_path = row["source_id"].split(":", 2)[2]
        out[(owner_path, row["heading_path"][-1])] = row
    return out


def bound(issue: str, sections: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for owner_path, heading in BINDINGS[issue]:
        row = sections.get((owner_path, heading))
        if row is None:
            raise SystemExit(f"{issue}: no extracted owner section {owner_path} / {heading}")
        rows.append({"owner_path": owner_path, "heading": heading,
                     "section_sha256": row["section_sha256"]})
    return rows


def section_lines(rows: list[dict[str, str]]) -> str:
    return "\n".join(f"- {r['owner_path']} § {r['heading']} (section body sha256 {r['section_sha256']})"
                     for r in rows)


def release_counts(release: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{release}?mode=ro", uri=True)
    try:
        return {t: conn.execute(f'select count(*) from "{t}"').fetchone()[0]
                for t in ("scheme_assertion", "responsibility_assertion")}
    finally:
        conn.close()


def build_proposals(composition: dict[str, Any], sections: dict[tuple[str, str], dict[str, Any]],
                    counts: dict[str, int]) -> dict[str, dict[str, Any]]:
    vector = composition["vector"]
    lost = composition["lossless_envelope"]["lost_by_projection"]
    fixtures = composition["fixtures"]
    negatives = [f["fixture"] for f in fixtures if f["fixture"].startswith("negative_")]
    positives = [f["fixture"] for f in fixtures if f["fixture"].startswith("positive_")]
    f10 = composition["source_scheme_vs_f10_state"]
    head = (
        f"BAS Cycle #37 Attempt #2 | R37-13-AC08 section-bound proposal\n"
        f"Owner source: CFBProgramSpecifications at {OWNER_REVISION} (each section was "
        f"read from a snapshot checked against the owner's git object at that revision).\n"
    )
    composed = (
        f"BAS evidence: the BAS staff adapter ({vector['producer']}) was composed with the "
        f"released C01 wheel {vector['wheel_version']} (sha256 {vector['wheel_sha256']}, equal to "
        f"the release asset digest). {len(fixtures)} fixtures: {composition['positives_accepted_by_both']} "
        f"of {composition['positives']} positive projections accepted by both the adapter and "
        f"{vector['consumer']}; {composition['negatives_caught_by_bas_adapter']} of "
        f"{composition['negatives']} negatives refused by the adapter before reaching the wheel; "
        f"{len(composition['negatives_caught_only_by_released_wheel'])} negatives that only the owner "
        f"schema caught. Fixtures are rights-safe synthetic data."
    )
    bodies: dict[str, str] = {}
    rows = {issue: bound(issue, sections) for issue in BINDINGS}

    bodies["CFIP-19"] = "\n\n".join([
        head + "Sections:\n" + section_lines(rows["CFIP-19"]),
        composed,
        "Proposed correction 1 (§ 3): state that the released context/StaffSnapshotV1 "
        f"{vector['wheel_version']} value (team_id, coach_ids) is a reduced compatibility "
        "projection of a staff assertion, and name what the projection drops. In the BAS "
        f"composition it drops {len(lost)} fields: {', '.join(lost)}. BAS keeps every one "
        "of them in its lossless assertion envelope, so nothing is lost on the BAS side, but "
        "a consumer holding only the released object cannot see them.",
        "Proposed correction 2 (§ 4): record the wheel asset digest as a composition input, "
        "so that a digest change invalidates a qualified composition. BAS already refuses to "
        "qualify against any bytes other than the released digest.",
        NONCLAIMS,
    ])
    bodies["CFIP-22"] = "\n\n".join([
        head + "Sections:\n" + section_lines(rows["CFIP-22"]),
        "Observed mismatch: 04 § 2 defines one StaffSnapshotV1 row as one source assertion "
        "(person, program/team, role and scope, assignment kind including PLAYCALLER, "
        "half-open interval, known_at, provenance, rights, conflicts). The released "
        f"{vector['wheel_version']} StaffSnapshotV1 value carries team_id and coach_ids only, so "
        "a released document cannot carry that grain. BAS's projection loses roles, "
        "occupancy, qualifiers, unit, play_calling_stated, rights, conflicts_with and the "
        "source interval (full list on CFIP-19).",
        "Proposed correction (owner decision, BAS takes no position): either amend 04 § 2 to "
        "say the assertion grain belongs to a successor contract version and the released "
        "value is a team-level projection, or version StaffSnapshotV1.",
        "BAS-side behaviour now matching 04 § 4 and 12 § 2 (evidence about the BAS adapter, "
        "not the owner schema): it refuses mixed cutoffs, a missing or post-cutoff known_at, "
        "naive or non-UTC timestamps, empty or blank evidence per assertion (one good "
        "assertion no longer hides a bad one), missing rights, program or person, an "
        "unresolved conflict, and one role over two different intervals; two assertions of "
        "the same role over the same interval are kept.",
        "Separation (13 § 1, 12 § 2): BAS refuses any source-stated scheme as an F10 "
        f"intelligence state regardless of evidence tier, tested against {len(f10)} "
        f"intelligence contracts in the released catalog ({', '.join(f10)}). BAS's "
        f"{counts['scheme_assertion']:,} source scheme assertions and "
        f"{counts['responsibility_assertion']:,} responsibility assertions stay source "
        "assertions; a title is not play-calling.",
        NONCLAIMS,
    ])
    bodies["CFIP-24"] = "\n\n".join([
        head + "Sections:\n" + section_lines(rows["CFIP-24"]),
        "Response to the MR36 reproduction on this issue (comment 15023): the BAS-local "
        "acceptance of mixed cutoffs, unknown or future known_at and empty evidence is "
        "repaired in BAS. " + composed,
        "Proposed BOM/compatibility content (08 § 2 requires exact compatible vectors): the "
        "release BOM could carry, per contract, the schema digest and the exact string "
        "patterns a producer must emit. Two of them cost BAS a defect. (1) The UTC instant "
        "pattern accepts only the Z suffix: an RFC 3339 instant written +00:00 is rejected "
        "by validate_document although it is the same instant. (2) Identifiers must match "
        "^[a-z0-9][a-z0-9._-]+$, so a one-character or upper-case identifier is rejected. "
        "BAS now normalises +00:00 to Z, refuses every other offset and refuses invalid "
        "identifiers before projection; a BOM that stated both would let other producers "
        "avoid the same failure.",
        "08 § 5 and 09 § 4: BAS refuses missing rights, but it has no C01 correction-impact "
        "object to emit and cannot express an ambiguous correction scope as a typed release "
        "state. Request: name the correction/withdrawal contract a producer should use, or "
        f"confirm that {vector['wheel_version']} has none, in which case BAS keeps refusing "
        "rather than guessing.",
        NONCLAIMS,
    ])
    covered = {
        "empty snapshot": "negative_empty_projection",
        "mixed cutoff": "negative_mixed_cutoffs",
        "missing evidence": "negative_empty_evidence, negative_blank_evidence_string, "
                            "negative_one_of_two_without_evidence",
        "future knowledge": "negative_known_at_after_cutoff",
        "wrong program": "negative_two_programs",
    }
    for label, names in covered.items():
        for name in names.split(", "):
            if name not in negatives:
                raise SystemExit(f"CFIP-27: claimed fixture {name} is not in the composition")
    bodies["CFIP-27"] = "\n\n".join([
        head + "Sections:\n" + section_lines(rows["CFIP-27"]),
        composed,
        "Offer for 21 § 4 walkthroughs 2 (context conflict/missing) and 5 (future-known): "
        "BAS's composition fixtures as independent producer-side fixtures. Positives: "
        f"{', '.join(positives)}. Negatives: {', '.join(negatives)}.",
        "Coverage of the negatives requested on this issue (comment 15024): "
        + "; ".join(f"{label} - covered by {names}" for label, names in covered.items())
        + ". Wrong-season roster - NOT covered: BAS has no RosterSnapshotV1 producer or "
          "roster composition yet, so the 03 § 11 item 2 roster cases are not exercised "
          "by BAS.",
        f"Exact vector (21 § 7): wheel {vector['wheel_version']} sha256 {vector['wheel_sha256']}; "
        f"schema {vector['schema']}; ruleset {vector['ruleset_id']}; consumer {vector['consumer']}; "
        f"producer {vector['producer']}; predecessor {vector['predecessor_producer']}.",
        "Schema-fixture success establishes interface behaviour only: not a scientific fact, "
        "not roster or staff accuracy, not production readiness (03 § 11, last paragraph).",
        NONCLAIMS,
    ])

    proposals = {}
    for issue, body in bodies.items():
        digest = sha256_text(body)
        marker = f"[{MARKER_PREFIX} {issue} {digest[:16]}]"
        proposals[issue] = {"issue": issue, "sections": rows[issue], "body_sha256": digest,
                            "marker": marker, "text": body + "\n\n" + marker}
    return proposals


class OwnerCommentClient:
    """GET, and POST a comment. Nothing else exists on this client."""

    def __init__(self, token: str, ceiling_remaining: int) -> None:
        auth = base64.b64encode(f"{EMAIL}:{token}".encode("utf-8")).decode("ascii")
        self._headers = {"Authorization": f"Basic {auth}", "Accept": "application/json",
                         "Content-Type": "application/json",
                         "User-Agent": "BAS-Cycle37-ProposalComment/1.0"}
        self.attempts: list[dict[str, Any]] = []
        self.ceiling_remaining = ceiling_remaining

    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if len(self.attempts) >= self.ceiling_remaining:
            raise RuntimeError("the metadata request ceiling would be exceeded; stopping")
        started = datetime.now(timezone.utc).isoformat()
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(BASE_URL + path, method=method, headers=self._headers, data=data)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
                self.attempts.append({"method": method, "path": path.split("?")[0],
                                      "status": response.status, "at": started})
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as error:
            self.attempts.append({"method": method, "path": path.split("?")[0],
                                  "status": error.code, "at": started})
            raise
        except (urllib.error.URLError, TimeoutError):
            self.attempts.append({"method": method, "path": path.split("?")[0],
                                  "status": None, "at": started})
            raise

    def comments(self, issue: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        start = 0
        while True:
            page = self._call("GET", f"/rest/api/2/issue/{issue}/comment?startAt={start}&maxResults=100")
            out.extend(page.get("comments") or [])
            start += len(page.get("comments") or [])
            if start >= int(page.get("total") or 0) or not page.get("comments"):
                return out

    def post_comment(self, issue: str, text: str) -> dict[str, Any]:
        return self._call("POST", f"/rest/api/2/issue/{issue}/comment", {"body": text})

    def comment(self, issue: str, comment_id: str) -> dict[str, Any]:
        return self._call("GET", f"/rest/api/2/issue/{issue}/comment/{comment_id}")


def existing_effect(comments: list[dict[str, Any]], issue: str) -> dict[str, Any] | None:
    prefix = f"[{MARKER_PREFIX} {issue} "
    for comment in comments:
        if prefix in str(comment.get("body") or ""):
            return comment
    return None


def normalise(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def post_with_readback(client: OwnerCommentClient, proposal: dict[str, Any]) -> dict[str, Any]:
    issue = proposal["issue"]
    for attempt in range(1, MAX_TRIES_PER_ROUTE + 1):
        prior = existing_effect(client.comments(issue), issue)
        if prior is not None:
            same = proposal["marker"] in str(prior.get("body") or "")
            return {"issue": issue, "action": "NOT_POSTED_EXISTING_EFFECT" if attempt == 1
                    else "LANDED_ON_EARLIER_TRY", "comment_id": prior.get("id"),
                    "same_marker": same, "attempts": attempt}
        try:
            created = client.post_comment(issue, proposal["text"])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            last = f"{type(error).__name__} {getattr(error, 'code', '')}".strip()
            if isinstance(error, urllib.error.HTTPError) and error.code not in (429, 500, 502, 503, 504):
                return {"issue": issue, "action": "POST_REFUSED", "error": last, "attempts": attempt}
            time.sleep(3.0 * attempt)
            continue
        readback = client.comment(issue, created["id"])
        return {"issue": issue, "action": "POSTED", "comment_id": created["id"],
                "created": readback.get("created"), "attempts": attempt,
                "readback_marker_present": proposal["marker"] in str(readback.get("body") or ""),
                "readback_text_equal": normalise(str(readback.get("body") or "")) == normalise(proposal["text"])}
    return {"issue": issue, "action": "STOPPED_AFTER_TWO_TRIES", "attempts": MAX_TRIES_PER_ROUTE}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--composition", type=Path,
                        default=ATTEMPT / "evidence/repairs/R37_13_C01_COMPOSITION.json")
    parser.add_argument("--sections", type=Path,
                        default=ATTEMPT / "evidence/repairs/R37_14_SECTION_EXTRACTION.jsonl")
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=ATTEMPT / "private/jira")
    parser.add_argument("--post", action="store_true",
                        help="post the proposals; without it nothing leaves this machine")
    parser.add_argument("--ceiling-remaining", type=int, default=0)
    args = parser.parse_args(argv)

    composition = json.loads(args.composition.read_text(encoding="utf-8"))
    proposals = build_proposals(composition, load_sections(args.sections), release_counts(args.release))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    draft = args.out_dir / "CFIP_PROPOSALS.json"
    _bas_atomic.write_text(draft, json.dumps({"label": LABEL, "cycle_number": 37, "attempt_number": 2,
                                 "owner_revision": OWNER_REVISION, "proposals": proposals},
                                indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for issue, p in proposals.items():
        print(issue, p["marker"], len(p["text"]), "chars")
    if not args.post:
        print("dry run: nothing posted; proposals at", draft)
        return 0
    if args.ceiling_remaining <= 0:
        raise SystemExit("--ceiling-remaining must state the metadata requests still available")

    client = OwnerCommentClient(read_token(authoritative_env(Path(__file__).resolve().parents[2])),
                                args.ceiling_remaining)
    results = []
    for issue in BINDINGS:
        try:
            results.append(post_with_readback(client, proposals[issue]))
        except RuntimeError as error:
            results.append({"issue": issue, "action": "STOPPED", "error": str(error)})
            break
        print(results[-1])
    receipt = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-13-AC08",
        "posted_at_utc": stamp, "owner_revision": OWNER_REVISION,
        "authority": "Recovery section 8 evidence/proposal comments on existing owner issues, "
                     "retained by the Cycle 37 Attempt 2 assignment; no transition, field edit "
                     "or new issue.",
        "client_capabilities": ["GET", "POST comment"],
        "results": results, "request_count": len(client.attempts), "requests": client.attempts,
        "proposals": str(draft), "proposals_sha256": hashlib.sha256(draft.read_bytes()).hexdigest(),
        "credential": "Read from the authoritative .env into memory only; not printed, logged or written.",
    }
    _bas_atomic.write_text(args.out_dir / f"CFIP_PROPOSAL_RECEIPT_{stamp}.json", 
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("requests:", len(client.attempts))
    return 0 if all(r.get("action") in ("POSTED", "NOT_POSTED_EXISTING_EFFECT", "LANDED_ON_EARLIER_TRY")
                    and r.get("readback_marker_present", True) for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
