"""R36-05: reconcile the 48-key career tranche against delivered rows.

The predecessor produced two lists of forty-eight: ``keys``, predeclared
before any evidence was looked at, and ``final_keys``, the dispositions.
Reading the wrong one is the ``keys``/``final_keys`` defect: a consumer that
counts ``keys`` sees forty-eight resolved candidates, because every
predeclared key is present whether or not evidence was found for it.

This tool keeps them apart and checks four things:

1. **Conservation.** The two key sets must be identical as sets. A key that
   appears in one and not the other is a finding, not a rounding.
2. **Disposition truth.** ``ACCEPTED_SINGLE_SOURCE`` must actually carry
   exactly one resolved person; ``CONFLICT`` must carry more than one;
   ``MISSING_NO_EVIDENCE`` must carry none. A disposition that disagrees with
   its own row is the shape that makes a summary count meaningless.
3. **Entailment before joining.** A candidate is joinable only when the
   evidence entails person, employer, role AND season together. Every key
   here is a retrospective Wikimedia candidate with
   ``official_corroboration: NOT_ACQUIRED_THIS_CYCLE``, so none is admitted
   as official and none is PIT-admitted.
4. **Delivered-row support.** Each key is looked up against the delivered
   national release: is its program-season in the membership denominator, and
   does any delivered staff observation support that program-season-role?
   Absence is reported, never filled in.

A team-season occurrence is not a career-page join, so the two evidence
classes are counted separately rather than summed.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

CYCLE35_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output"
)
PREDECLARED = CYCLE35_OUT / "R35_05_PREDECLARED_48_KEYS.json"
FINAL = CYCLE35_OUT / "R35_05_CAREER_TRANCHE_FINAL.json"

EXPECTED_PERSON_COUNT = {
    "ACCEPTED_SINGLE_SOURCE": lambda n: n == 1,
    "CONFLICT": lambda n: n > 1,
    "MISSING_NO_EVIDENCE": lambda n: n == 0,
}

JOINABLE = "JOINABLE_ENTAILS_PERSON_EMPLOYER_ROLE_AND_SEASON"
NOT_JOINABLE_CONFLICT = "NOT_JOINABLE_COMPETING_PEOPLE_RETAINED"
NOT_JOINABLE_NO_PERSON = "NOT_JOINABLE_NO_PERSON_IN_THE_EVIDENCE"
NOT_JOINABLE_NO_CORROBORATION = "NOT_JOINABLE_CANDIDATE_TIER_ONLY"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def key_tuple(row: dict[str, Any]) -> tuple:
    return (
        str(row.get("key_id")),
        str(row.get("program_id")),
        int(row.get("season") or 0),
        str(row.get("role")),
    )


def delivered_support(database: Path) -> dict[str, Any]:
    """Membership and staff support from the delivered release, read-only."""

    if not database.is_file():
        return {"state": "RELEASE_NOT_BUILT", "membership": set(), "roles": {}}
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        membership = {
            (row[0], int(row[1]))
            for row in connection.execute(
                "SELECT program_id, season FROM program_season_membership"
            )
        }
        roles: dict[tuple, int] = {}
        for program, season, role, count in connection.execute(
            "SELECT o.program_id, o.season, a.role_code, COUNT(*) "
            "FROM staff_observation AS o "
            "JOIN staff_role_assignment AS a "
            "  ON a.observation_id = o.observation_id "
            "WHERE o.program_id IS NOT NULL AND o.season IS NOT NULL "
            "GROUP BY o.program_id, o.season, a.role_code"
        ):
            roles[(program, int(season), role)] = int(count)
        return {"state": "RELEASE_READ", "membership": membership, "roles": roles}
    finally:
        connection.close()


def build(out_dir: Path, database: Path) -> dict[str, Any]:
    predeclared = read_json(PREDECLARED) or {}
    final = read_json(FINAL) or {}
    declared_keys = predeclared.get("keys") or []
    final_keys = final.get("final_keys") or []

    declared_set = {key_tuple(row) for row in declared_keys}
    final_set = {key_tuple(row) for row in final_keys}
    support = delivered_support(database)

    rows: list[dict[str, Any]] = []
    dispositions: collections.Counter = collections.Counter()
    joinability: collections.Counter = collections.Counter()
    disposition_mismatches: list[dict[str, Any]] = []
    membership_missing: list[str] = []

    for row in final_keys:
        disposition = str(row.get("disposition"))
        dispositions[disposition] += 1
        people = row.get("resolved_people") or []
        predicate = EXPECTED_PERSON_COUNT.get(disposition)
        consistent = predicate(len(people)) if predicate else None
        if consistent is False:
            disposition_mismatches.append(
                {
                    "key_id": row.get("key_id"),
                    "disposition": disposition,
                    "resolved_people": people,
                }
            )
        program = str(row.get("program_id"))
        season = int(row.get("season") or 0)
        role = str(row.get("role"))
        in_membership = (program, season) in support["membership"]
        if not in_membership:
            membership_missing.append(f"{program}|{season}")
        delivered_rows = support["roles"].get((program, season, role), 0)

        if disposition == "CONFLICT":
            state = NOT_JOINABLE_CONFLICT
        elif not people:
            state = NOT_JOINABLE_NO_PERSON
        elif str(row.get("official_corroboration")) != "OFFICIAL_CORROBORATED":
            state = NOT_JOINABLE_NO_CORROBORATION
        else:
            state = JOINABLE
        joinability[state] += 1

        rows.append(
            {
                "key_id": row.get("key_id"),
                "program_id": program,
                "display_name": row.get("display_name"),
                "classification": row.get("classification"),
                "season": season,
                "role": role,
                "era_band": row.get("era_band"),
                "predeclared_before_evidence": row.get("predeclared_before_evidence"),
                "disposition": disposition,
                "resolved_people": people,
                "person_count_declared": row.get("person_count"),
                "person_count_observed": len(people),
                "disposition_consistent_with_its_own_row": consistent,
                "evidence_class": row.get("evidence_class"),
                "official_corroboration": row.get("official_corroboration"),
                "wikimedia_revisions": row.get("source_revisions") or [],
                "employer_season_episode_count": row.get(
                    "employer_season_episode_count"
                ),
                "supporting_episode_count": row.get("supporting_episode_count"),
                "joinability": state,
                "program_season_in_delivered_membership": in_membership,
                "delivered_staff_rows_for_this_role": delivered_rows,
                "pit_admitted": False,
            }
        )

    artifact = {
        "artifact_type": "CYCLE36_CAREER_TRANCHE_RECONCILIATION",
        "generated_at_utc": utc_now(),
        "sources": {
            "predeclared": {
                "path": str(PREDECLARED),
                "sha256": sha256_file(PREDECLARED),
                "key_count": len(declared_keys),
            },
            "final": {
                "path": str(FINAL),
                "sha256": sha256_file(FINAL),
                "key_count": len(final_keys),
            },
        },
        "keys_versus_final_keys": {
            "declared_count": len(declared_keys),
            "final_count": len(final_keys),
            "sets_identical": declared_set == final_set,
            "only_in_predeclared": sorted(
                "|".join(map(str, key)) for key in declared_set - final_set
            ),
            "only_in_final": sorted(
                "|".join(map(str, key)) for key in final_set - declared_set
            ),
            "why_this_matters": (
                "Counting the predeclared list reports forty-eight candidates "
                "regardless of what evidence was found. Only the final list "
                "carries dispositions, and only its ACCEPTED rows name a "
                "person."
            ),
        },
        "dispositions": dict(dispositions),
        "disposition_self_consistency": {
            "mismatches": disposition_mismatches,
            "mismatch_count": len(disposition_mismatches),
            "all_consistent": not disposition_mismatches,
        },
        "joinability": dict(joinability),
        "joinable_keys": joinability.get(JOINABLE, 0),
        "delivered_release": {
            "path": str(database),
            "state": support["state"],
            "program_seasons_missing_from_membership": sorted(set(membership_missing)),
            "program_seasons_missing_count": len(set(membership_missing)),
        },
        "rows": rows,
        "evidence_classes": dict(
            collections.Counter(str(row.get("evidence_class")) for row in final_keys)
        ),
        "team_season_occurrence_is_not_a_career_page_join": (
            "Keys resolved from a team-season infobox and keys resolved from a "
            "career page are different evidence and are counted by "
            "evidence_class rather than summed."
        ),
        "nothing_admitted_as_official": all(
            str(row.get("official_corroboration")) != "OFFICIAL_CORROBORATED"
            for row in final_keys
        ),
        "no_key_dropped": len(final_keys) == 48,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_CAREER_TRANCHE_RECONCILIATION.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.out_dir, args.database)
    print(
        json.dumps(
            {
                "keys_versus_final_keys": artifact["keys_versus_final_keys"][
                    "sets_identical"
                ],
                "dispositions": artifact["dispositions"],
                "disposition_mismatches": artifact["disposition_self_consistency"][
                    "mismatch_count"
                ],
                "joinability": artifact["joinability"],
                "release_state": artifact["delivered_release"]["state"],
                "program_seasons_missing": artifact["delivered_release"][
                    "program_seasons_missing_count"
                ],
                "nothing_admitted_as_official": artifact["nothing_admitted_as_official"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
