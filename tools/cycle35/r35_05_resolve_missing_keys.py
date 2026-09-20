"""R35-05 second pass: actually attempt the 33 MISSING career keys.

An unattempted request is not "source unavailable". The first pass resolved
the predeclared 48 keys against the cached career-episode index and left 33
MISSING. This pass attempts each of those from a different, independent
evidence surface -- the season's own team article, whose infobox names the
head coach and coordinators -- cache-first against 27,177 already-acquired
Wikimedia titles, and only then over the network within the counted budget.

The key set is NOT changed. A key that still fails stays MISSING with the
exact routes attempted, so the denominator never shrinks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggie_analytics.cycle35.request_ledger import (  # noqa: E402
    BUDGET_COACHING,
    OUTCOME_CACHE_HIT,
    BudgetExhausted,
    RequestLedger,
)
from r35_05_career_tranche import reconcile_tranche_samples  # noqa: E402

TITLE_INDEX = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\wikimedia_title_index.json"
)
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "BatteredAggieSyndrome-Research/35.1 "
    "(private research; contact via repository owner)"
)

#: Infobox parameters that carry coaching identity on a team-season article.
ROLE_PARAMS = {
    "head_coach": ("head_coach", "hc"),
    "offensive_coordinator": ("off_coach", "offensive_coordinator", "oc"),
    "defensive_coordinator": ("def_coach", "defensive_coordinator", "dc"),
}

_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None



def _population_names() -> frozenset[str]:
    """Canonical display names from the declared national population."""

    base = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
    names: set[str] = set()
    for name in (
        "CURRENT_2026_PROGRAMS.jsonl",
        "HISTORICAL_MEMBERSHIP_2013_2023.jsonl",
        "HISTORICAL_MEMBERSHIP_1963_2012.jsonl",
    ):
        path = base / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            display = (json.loads(line) or {}).get("display_name")
            if display:
                names.add(str(display).strip())
    return frozenset(names)


def candidate_titles(
    display_name: str,
    season: int,
    titles: dict[str, str],
    all_program_names: frozenset[str],
) -> list[str]:
    """Team-season article titles this key could correspond to.

    A plain prefix match is NOT sufficient and was a real defect found by
    spot-checking this tool's own output: `"2011 North Carolina "` is a
    prefix of `"2011 North Carolina A&T Aggies football team"`, so North
    Carolina's key resolved to North Carolina A&T's head coach. That is the
    same class of error as the substring-name bug repaired in R35-02, and it
    is unacceptable here for the same reason.

    The fix is longest-match disambiguation against the canonical
    population: strip the season and the ` football team` suffix, then reject
    the title if ANY other canonical program name is a longer prefix of the
    remainder. A title belongs to the longest program name that matches it.
    """

    name = str(display_name or "").strip()
    prefix = str(season) + " " + name + " "
    suffix = " football team"
    out: list[str] = []
    for title in titles:
        if not (title.startswith(prefix) and title.endswith(suffix)):
            continue
        remainder = title[len(str(season)) + 1 : -len(suffix)]
        longer = [
            other
            for other in all_program_names
            if len(other) > len(name) and remainder.startswith(other)
        ]
        if longer:
            # This article belongs to a different, longer-named program.
            continue
        out.append(title)
    return sorted(out)


def extract_wikitext(payload: Any) -> str:
    pages = ((payload or {}).get("query") or {}).get("pages") or {}
    for page in pages.values():
        revisions = page.get("revisions") or []
        for revision in revisions:
            slots = revision.get("slots") or {}
            main = slots.get("main") or {}
            text = main.get("*") or revision.get("*")
            if text:
                return str(text)
    return ""


def parse_role(wikitext: str, role: str) -> dict[str, Any]:
    """Pull one role's occupant out of the season infobox, verbatim."""

    for param in ROLE_PARAMS[role]:
        # Capture to end of line, NOT to the next `|`. Infobox parameters are
        # one per line, and a wikilink's own pipe (`[[Tom O'Brien (American
        # football)|Tom O'Brien]]`) sits inside the value -- stopping at it
        # truncated the value mid-link and leaked `[[Tom O'Brien (American
        # football)` as the person's name. Found by spot-checking this tool's
        # own output rather than by a test, which is why the spot check
        # happened before the rows were ingested anywhere.
        match = re.search(
            r"\|\s*" + re.escape(param) + r"\s*=\s*([^\n]+)", wikitext, re.I
        )
        if not match:
            continue
        raw = match.group(1).strip()
        if not raw:
            continue
        links = _LINK.findall(raw)
        plain = _LINK.sub(lambda m: m.group(1), raw)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\{\{[^}]*\}\}", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip(" '\"")
        if not plain:
            continue
        return {
            "parameter": param,
            "raw_value": raw,
            "resolved_person": plain,
            "linked_titles": links,
        }
    return {}


def fetch_title(
    title: str, ledger: RequestLedger, cache_dir: Path
) -> tuple[str, dict[str, Any]]:
    """Fetch one article's wikitext, counted against the coaching budget."""

    cache_path = cache_dir / (
        hashlib.sha256(title.encode("utf-8")).hexdigest() + ".json"
    )
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content|ids|timestamp",
            "rvslots": "main",
            "titles": title,
            "format": "json",
            "formatversion": "1",
        }
    )
    url = API + "?" + params

    def _do() -> tuple[int, bytes]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read()

    outcome = ledger.fetch(
        budget=BUDGET_COACHING,
        url=url,
        purpose="team-season infobox for a MISSING predeclared key",
        fetcher=_do,
        cache_path=cache_path,
    )
    if not outcome.get("ok"):
        return "", {"state": "FETCH_FAILED", "detail": outcome.get("detail", "")}
    payload = json.loads(outcome["body"].decode("utf-8", errors="replace"))
    return extract_wikitext(payload), {
        "state": "FETCHED" if not outcome.get("from_cache") else "CACHE_HIT",
        "cache_path": str(cache_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tranche", required=True)
    ap.add_argument(
        "--reconcile-with", default="",
        help="Path to a predecessor R35_05_CAREER_TRANCHE_FINAL.json (a "
        "resolved second-pass artifact) to reconcile this run's resolved "
        "sample against, by stable (program_id, season, role) semantic "
        "key rather than mutable key_id. Optional; performs no acquisition.",
    )
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    cache_dir = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\wikimedia_teamseason_cache"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    tranche = read_json(Path(args.tranche)) or {}
    titles = read_json(TITLE_INDEX) or {}
    # Every canonical program display name, for longest-match disambiguation.
    all_program_names = frozenset(
        str(row["display_name"]).strip()
        for row in (tranche.get("keys") or [])
        if row.get("display_name")
    ) | _population_names()
    ledger = RequestLedger()

    keys = tranche.get("keys") or []
    missing = [row for row in keys if row["disposition"] == "MISSING_NO_EVIDENCE"]

    resolved: list[dict[str, Any]] = []
    for key in missing:
        options = candidate_titles(
            key["display_name"], int(key["season"]), titles, all_program_names
        )
        attempt: dict[str, Any] = {
            "key_id": key["key_id"],
            "display_name": key["display_name"],
            "season": key["season"],
            "role": key["role"],
            "candidate_titles": options,
        }
        if not options:
            # Construct the conventional title and attempt it over the network
            # rather than declaring the source unavailable without trying.
            options = [
                str(key["season"]) + " " + str(key["display_name"]) + " football team"
            ]
            attempt["candidate_titles_constructed"] = options

        found = None
        for title in options[:2]:
            cached_path = titles.get(title)
            if cached_path and Path(cached_path).is_file():
                ledger.record(
                    budget=BUDGET_COACHING,
                    url="cache:" + title,
                    purpose="team-season infobox",
                    outcome=OUTCOME_CACHE_HIT,
                    detail=cached_path,
                )
                wikitext = extract_wikitext(
                    json.loads(
                        Path(cached_path).read_text(encoding="utf-8", errors="replace")
                    )
                )
                state = {"state": "CACHE_HIT", "cache_path": cached_path}
            else:
                try:
                    wikitext, state = fetch_title(title, ledger, cache_dir)
                except BudgetExhausted as exc:
                    attempt["new_disposition"] = "NOT_ATTEMPTED_BUDGET_EXHAUSTED"
                    attempt["detail"] = str(exc)
                    resolved.append(attempt)
                    wikitext = ""
                    state = {"state": "BUDGET_EXHAUSTED"}
                    break
            if not wikitext:
                continue
            parsed = parse_role(wikitext, key["role"])
            attempt["source_title"] = title
            attempt["source_state"] = state
            if parsed:
                found = parsed
                break
        if attempt.get("new_disposition"):
            continue
        if found:
            attempt["new_disposition"] = "ACCEPTED_SINGLE_SOURCE"
            attempt["resolved_people"] = [found["resolved_person"]]
            attempt["infobox_parameter"] = found["parameter"]
            attempt["raw_value"] = found["raw_value"]
            attempt["linked_titles"] = found["linked_titles"]
            attempt["evidence_class"] = (
                "WIKIMEDIA_TEAM_SEASON_INFOBOX_RETROSPECTIVE_CANDIDATE"
            )
        else:
            attempt["new_disposition"] = "MISSING_NO_EVIDENCE"
            attempt["detail"] = (
                "Attempted the season's own team article; the article either "
                "does not exist, was not retrievable, or its infobox carries "
                "no value for this role. The key stays in the denominator."
            )
        attempt["pit_admitted"] = False
        resolved.append(attempt)

    upgraded = {
        row["key_id"]: row
        for row in resolved
        if row.get("new_disposition") == "ACCEPTED_SINGLE_SOURCE"
    }
    final_keys = []
    for key in keys:
        row = dict(key)
        if key["key_id"] in upgraded:
            hit = upgraded[key["key_id"]]
            row.update(
                {
                    "disposition": "ACCEPTED_SINGLE_SOURCE",
                    "resolved_people": hit["resolved_people"],
                    "person_count": 1,
                    "second_pass_source_title": hit.get("source_title"),
                    "second_pass_parameter": hit.get("infobox_parameter"),
                    "evidence_class": hit["evidence_class"],
                    "detail": "Resolved on the second pass from the season's "
                    "own team article infobox.",
                }
            )
        final_keys.append(row)

    dispositions = Counter(row["disposition"] for row in final_keys)
    by_division = Counter(
        row["classification"]
        for row in final_keys
        if row["disposition"] != "MISSING_NO_EVIDENCE"
    )
    result = {
        "artifact_type": "CYCLE35_R35_05_CAREER_TRANCHE_SECOND_PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "keys_attempted": len(missing),
        "attempts": resolved,
        "final_dispositions": dict(dispositions),
        "resolved_by_division": dict(by_division),
        "final_keys": final_keys,
        "key_count": len(final_keys),
        "request_ledger": ledger.as_dict(),
        "key_set_unchanged": len(final_keys) == len(keys),
        "denominator_never_shrank": True,
        "unattempted_is_not_unavailable": True,
        "pit_admitted": False,
    }
    (out_dir / "R35_05_CAREER_TRANCHE_FINAL.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    ledger.write(out_dir / "CYCLE35_REQUEST_LEDGER_CAREER.json")

    reconciliation_summary: dict[str, Any] | None = None
    if args.reconcile_with:
        predecessor = read_json(Path(args.reconcile_with)) or {}
        reconciliation = reconcile_tranche_samples(
            predecessor.get("final_keys") or [], final_keys
        )
        (out_dir / "R35_05_SAMPLE_RECONCILIATION.json").write_text(
            json.dumps(reconciliation, indent=2, sort_keys=True), encoding="utf-8"
        )
        reconciliation_summary = {
            "old_sample_path": args.reconcile_with,
            "status_counts": reconciliation["status_counts"],
            "union_distinct_semantic_key_count": reconciliation[
                "union_distinct_semantic_key_count"
            ],
        }

    print(json.dumps(
        {
            "attempted": len(missing),
            "final_dispositions": dict(dispositions),
            "resolved_by_division": dict(by_division),
            "coaching_requests_spent": ledger.spent[BUDGET_COACHING],
            "coaching_remaining": ledger.remaining(BUDGET_COACHING),
            "outcome_counts": ledger.as_dict()["outcome_counts"],
            "sample_reconciliation": reconciliation_summary,
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
