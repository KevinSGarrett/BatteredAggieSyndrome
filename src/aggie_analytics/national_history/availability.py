r"""Archive-supported 2019 prior-game history availability (BAT-714, Cycle #42 TP42-A01): shared derivation core.

Standard library only, plus the accepted readers it composes (``national_history.query``,
``national_population.query``, ``national_source_time.query`` and ``national_source_time.archive``). The producer
(``tools/build_national_history_availability.py``) and the read-only consumer (``availability_query``) both call
:func:`derive`; the independent validator imports neither.

Population and grain. Targets are the 2019 parent contests in the FBS_ESTIMAND_SUBSET that pass every Cycle 39 history
predicate (disposition, reconciliation, status, competitive, date, organization keys, scores). Each target has two
views (A: team = parent a side; B: team = parent b side); the current opponent is the other participant of the target.
A view's expected prior relationships are every 2019 parent contest of the team's organization key, other than the
target, whose contest date is a valid ISO date strictly earlier than the target date -- history-pool members and
parent-excluded contests alike, whatever the opponent's division. Same-date and undated contests are listed as
exclusions; later contests are counted. The derivation is reconciled with the accepted Cycle 39 history database in
both directions before anything is returned. The 28-contest archive tranche is numerator evidence only: it never
defines a target, a relationship or a denominator.

Support. A prior result is archive-supported at a cutoff only when one archived version of that prior contest is
QUALIFIED and qualifies all six witnessable fields (contest date, both participants, completion, both scores) as
agreeing with the parent, and that version's archive upper bound is at or before the cutoff. Versions are never
combined across revisions. Missing (outside the tranche), no capture, every version quarantined, a contradicting
version, partial versions and a too-late bound remain distinct; nothing is ever PIT admitted.
"""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import random
import re
from typing import Any, Iterable, Sequence

from aggie_analytics.national_source_time import query as source_time

POPULATION = "national_history_availability_2019"
CONTRACT_SCHEMA = "1.0.0"
CONTRACT_ID = "BAT-714-NATIONAL-HISTORY-AVAILABILITY-2019-V1.0"
PAYLOAD_SCHEMA = "BAS-NATIONAL-HISTORY-AVAILABILITY-PAYLOAD-1"
CONTENT_SCHEMA = "BAS-NATIONAL-HISTORY-AVAILABILITY-CONTENT-1"
DATABASE_SCHEMA = "BAS-NATIONAL-HISTORY-AVAILABILITY-DATABASE-1"
DB_SCHEMA = "BAS-NATIONAL-HISTORY-AVAILABILITY-DB-1"
DB_FILE = "national_history_availability.sqlite"
PAYLOAD_ENCODING = "GZIP_MTIME_0_OF_CANONICAL_JSONL"
SEASON = 2019
SUBSET = "FBS_ESTIMAND_SUBSET"
PRIOR_RULE = "SAME_SEASON_VALID_DATE_STRICTLY_BEFORE_TARGET_DATE"
SUPPORT_RULE = "ONE_QUALIFIED_ARCHIVED_VERSION_QUALIFYING_ALL_SIX_FIELDS_WITH_UPPER_BOUND_AT_OR_BEFORE_CUTOFF"
CROSS_VERSION_RULE = "NOT_USED_FIELDS_ARE_NEVER_COMBINED_ACROSS_ARCHIVED_VERSIONS"
BOUNDARY_BASIS = "TARGET_CALENDAR_DATE_00_00_UTC_MINUS_14_HOURS_CONSERVATIVE_DATE_BOUNDARY_NOT_OBSERVED_KICKOFF"
CUTOFF_USE = "HISTORICAL_EVIDENCE_ONLY_NO_PREGAME_OR_PIT_CLAIM"
FIELDS = ("contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
QUALIFIED = "QUALIFIED_AGREES_WITH_PARENT"
CONTRADICTING_STATES = ("CONFLICTS_WITH_PARENT", "CONTRADICTORY_WITHIN_VERSION")
POPULATION_PARENT = "national_di_population_2016_2025"
HISTORY_PARENT = "national_history_prefix_2016_2023"
SOURCE_TIME_PARENT = "national_source_time_2016_2023"
ARCHIVE_PARENT = "national_archived_publication_2019"
PARENT_FILES = {"population": (POPULATION_PARENT, "national_population.sqlite"),
                "history": (HISTORY_PARENT, "national_history.sqlite"),
                "source_time": (SOURCE_TIME_PARENT, "national_source_time.sqlite"),
                "archive": (ARCHIVE_PARENT, "national_archived_publication.sqlite")}
ROW_LABELS = {"evidence_authority": "ARCHIVE_SUPPORTED_HISTORY_EVIDENCE_ONLY",
              "pit_admission": "NOT_ADMITTED",
              "training_eligibility": "NOT_ELIGIBLE_NOT_ADMITTED",
              "temporal_basis": "EXPLICIT_CUTOFF_AGAINST_ARCHIVE_UPPER_BOUNDS_NOT_FIRST_PUBLICATION",
              "scope": "2019_FBS_TARGETS_ARCHIVE_TRANCHE_IS_NUMERATOR_EVIDENCE_NOT_DENOMINATOR"}
#: The issued authority this package serves: the committed contract and the exact accepted parents it binds
#: (configs/national_history_availability_2019_contract.json). A projection naming anything else refuses.
ISSUED = {
    "contract_id": CONTRACT_ID,
    "contract_sha256": "50a7ccd84675b54a53f65dbb16bc8764a3baf69a9e7f529915dfa6b6c355943c",
    "parent": {
        "population": {"query_db_identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
                       "sqlite_sha256": "9c517af94b9e0c7105627397b8a8cd9f9fc0ee806493c126c842c5018c5ba172",
                       "contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
                       "contest_identity": "ab4cdf1b0c1c06f20c9b143b9e0452fa71081670decc13c931830f50d140c4d8",
                       "program_season_identity": "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e"},
        "history": {"database_identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
                    "sqlite_sha256": "e137208cb3e9fec55c9b68e6af5c61e036ea7ea60a8973d9be9c35c358b17060",
                    "content_identity": "58c2bf7d6e9c70c2ba2a9e4dd583a89ace10062cc49aafe00d2f9675c84afe63",
                    "contract_sha256": "2646a5cbe9a1daff7135671b85c98239b250d493c53c4bc066f57805e1e4f76c"},
        "source_time": {"database_identity": "9594e2bf8bba9c697a9bf0f923db77c56a9e680a9fba7daf2085dc1ec7a273ef",
                        "sqlite_sha256": "5259ee091712cf46ce530e815e357ff79d7316097d7d82fe2a938afc4b9d6cb7",
                        "content_identity": "4e1fe127a0799f5a5b6410fe6cdaaf0a876063e3e76fd2aec1fdb2188d85fa85",
                        "contract_sha256": "21ed32b8fac0f5fa2c3f4dd55f29abef80437d339c3db2f1bf75206a1fcaf1bd"},
        "archive": {"database_identity": "768c7c4c8daf5949de3e9cfff5f63ef954ea8d8719678543eef083701361b1da",
                    "sqlite_sha256": "442d908a3fd28f4dde3e52f3e091bb8442cdcd49ccb5321e3ded7a0b8727797e",
                    "content_identity": "e8fe56813c13575cd0ce8f8c56ae1f4763e6c171f109f61c0f08b7fadddd7d81",
                    "contract_sha256": "3be9f08f32d4d40dd805a31b3f402ca171add3afeeeab45256710ed1bbf8fe66",
                    "contract_id": "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.2",
                    "tranche_sha256": "42b96f4238ccb46a2d516332e81ab35efffe22e1fdc717e340749256992e4e79",
                    "acquisition_identity": "c2c0d41c269175cc35f2633ab303868bacd383764a34f2c8c70b17e17b69ccb0"}}}
PARENT_KEYS = {"population": ("query_db_identity", "sqlite_sha256", "contract_sha256", "contest_identity",
                              "program_season_identity"),
               "history": ("database_identity", "sqlite_sha256", "content_identity", "contract_sha256"),
               "source_time": ("database_identity", "sqlite_sha256", "content_identity", "contract_sha256"),
               "archive": ("database_identity", "sqlite_sha256", "content_identity", "contract_sha256", "contract_id",
                           "tranche_sha256", "acquisition_identity")}
#: BAT-715 expansion successor (Cycle #43 TP43-A01): the same projection, record schemas and labels over the explicitly
#: selected 97-key archive expansion sidecar, as its own population and contract. Nothing above changes.
EXPANSION_POPULATION = "national_history_availability_2019_expansion"
EXPANSION_CONTRACT_ID = "BAT-715-NATIONAL-HISTORY-AVAILABILITY-2019-EXPANSION-V1.0"
EXPANSION_ARCHIVE_PARENT = "national_archived_publication_2019_expansion"
EXPANSION_PARENT_KEYS = {**PARENT_KEYS, "archive": PARENT_KEYS["archive"] + ("cohort_sha256",
                                                                             "retained_acquisition_identity")}
#: The issued expansion authority: the committed successor contract and the exact parents its materialized projection
#: binds (configs/national_history_availability_2019_expansion_contract.json; artifacts/data_lake/
#: national_history_availability_2019_expansion_gate.json). Served only for a projection naming exactly this contract.
ISSUED_EXPANSION: dict[str, Any] | None = {
    "contract_id": EXPANSION_CONTRACT_ID,
    "contract_sha256": "1a169c79a67d36a97990cdf76ef0d9c0ca968fe316ce5beee361439431bd9b8c",
    "parent": {
        "population": ISSUED["parent"]["population"], "history": ISSUED["parent"]["history"],
        "source_time": ISSUED["parent"]["source_time"],
        "archive": {"database_identity": "a8c7abcbd8a764eebefaafafc56ebb07bd40342e00bcd3431cb29a3ef58c4a36",
                    "sqlite_sha256": "fe9d4ea97e81139ef5669d5b80349cae2db6665badfe2749613ec3de78b08c56",
                    "content_identity": "4b4e681a1d81c328ebd06b4f7c905cb5dd5d7f61dc870813e87ac7a8aab650fa",
                    "contract_sha256": "8d8edea336dc6691a134d31aa450aa9fe7491b9d2e665cd45b10bc6d878feffc",
                    "contract_id": "BAT-715-NATIONAL-ARCHIVED-PUBLICATION-2019-EXPANSION-V1.0",
                    "tranche_sha256": "42b96f4238ccb46a2d516332e81ab35efffe22e1fdc717e340749256992e4e79",
                    "acquisition_identity": "a0fd2d4f662cfbd5149ac74ae3799f2abbf9f20fe1baa207754a591899ef24df",
                    "cohort_sha256": "9240e5637bf80133d094745baf95898ddd2ef6ed8900fe0d1cf0cd20f397b937",
                    "retained_acquisition_identity":
                        "c2c0d41c269175cc35f2633ab303868bacd383764a34f2c8c70b17e17b69ccb0"}}}
PROFILES = {CONTRACT_ID: {"population": POPULATION, "archive_parent": ARCHIVE_PARENT, "parent_keys": PARENT_KEYS},
            EXPANSION_CONTRACT_ID: {"population": EXPANSION_POPULATION, "archive_parent": EXPANSION_ARCHIVE_PARENT,
                                    "parent_keys": EXPANSION_PARENT_KEYS}}
POPULATION_CONTRACTS = {profile["population"]: cid for cid, profile in PROFILES.items()}
EVIDENCE_CLASSES = ("NOT_IN_ARCHIVE_TRANCHE", "ARCHIVE_NO_CAPTURE", "ARCHIVE_ALL_VERSIONS_QUARANTINED",
                    "ARCHIVE_VERSION_CONTRADICTS_PARENT", "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION",
                    "ARCHIVE_COHERENT_VERSION")
#: Every reason class an unsupported history-pool prior can carry at a cutoff (stable, all reported with zeros).
UNSUPPORTED_REASON_CLASSES = ("NOT_IN_ARCHIVE_TRANCHE", "ARCHIVE_NO_CAPTURE", "ARCHIVE_ALL_VERSIONS_QUARANTINED",
                              "ARCHIVE_VERSION_CONTRADICTS_PARENT", "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION",
                              "OUTCOME_CANNOT_EXIST_BEFORE_PRIOR_EVENT_DATE",
                              "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF")
SUPPORT_STATES = ("SUPPORTED", "UNSUPPORTED", "EXCLUDED_FROM_HISTORY_POOL")
COMPLETENESS_STATES = ("COLD_START_NO_EXPECTED_PRIORS", "ALL_EXPECTED_PRIORS_SUPPORTED", "PARTIAL_SUPPORTED_SUBSET",
                       "NO_SUPPORTED_PRIORS")
TRUE, FALSE, UNKNOWN, NO_ARCHIVE = "TRUE", "FALSE", "UNKNOWN", "NO_QUALIFIED_ARCHIVE_ASSERTION"
PAYLOAD_FILES = ("targets.jsonl", "views.jsonl", "relationships.jsonl", "evidence.jsonl", "witnesses.jsonl")
PAYLOAD_TABLES = {"targets.jsonl": "targets", "views.jsonl": "views", "relationships.jsonl": "relationships",
                  "evidence.jsonl": "evidence", "witnesses.jsonl": "witnesses"}
TABLES = ("meta", "targets", "views", "relationships", "evidence", "witnesses")
POPULATION_COLUMNS = ("contest_key", "ncaa_contest_id", "season", "term", "contest_date", "site", "neutral_site_text",
                      "contest_status", "competitive", "a_org_id", "a_team_name", "a_division_label", "a_points",
                      "b_org_id", "b_team_name", "b_division_label", "b_points", "classification_pair",
                      "reconciliation_state", "disposition", "a_key", "b_key", "contest_dates_observed")
ORG_KEY = re.compile(r"^org:([0-9]+)$")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
INPUT_ORDER = re.compile(r"^(natural|reverse|shuffle:[0-9]{1,9})$")
BOUND_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
LABELS = tuple(ROW_LABELS)

#: Closed record schemas (contract payloads.record_fields).
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "target": ("record_type", "contest_key", "ncaa_contest_id", "season", "term", "contest_date", "a_key", "b_key",
               "a_org_id", "b_org_id", "a_team_name", "b_team_name", "a_division_label", "b_division_label",
               "classification_pair", "parent_site", "neutral_site_text", "conservative_date_boundary_utc", "views",
               *LABELS),
    "view": ("record_type", "target_contest_key", "view", "season", "target_date", "prior_rule", "team_key",
             "team_org_id", "team_name", "team_division_label", "opponent_key", "opponent_org_id", "opponent_name",
             "opponent_division_label", "expected_prior_relationships", "history_pool_priors",
             "parent_excluded_priors", "relationship_contest_keys", "same_date_excluded", "undated_excluded",
             "later_contests_excluded", "history_state", *LABELS),
    "relationship": ("record_type", "target_contest_key", "view", "season", "target_date", "team_key",
                     "current_opponent_key", "prior_contest_key", "prior_contest_date", "prior_side",
                     "prior_opponent_key", "prior_opponent_division_label", "prior_classification_pair",
                     "relationship_class", "parent_exclusion_reasons", "parent_result", *LABELS),
    "prior_evidence": ("record_type", "contest_key", "season", "contest_date", "a_key", "b_key", "classification_pair",
                       "history_pool_member", "parent_exclusion_reasons", "parent_values",
                       "earliest_event_instant_utc", "archive", *LABELS),
    "field_witness": ("record_type", "contest_key", "capture_id", "capture_state", "upper_bound_utc", "field",
                      "witness", "witness_span", "literal", "value", "corroboration", "field_state", *LABELS),
}
NESTED_FIELDS: dict[str, tuple[str, ...]] = {
    "excluded": ("contest_key", "contest_date", "opponent_key", "reasons"),
    "parent_result": ("points_for", "points_against", "result"),
    "parent_values": ("contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points"),
    "archive": ("in_tranche", "archive_disposition", "acquisition_outcome", "parent_values_agree", "versions",
                "coherent_capture_ids", "coherent_upper_bound_utc", "contradicting_capture_ids",
                "field_earliest_qualified_upper_bound_utc", "evidence_class", "evidence_reason"),
    "version": ("capture_id", "state", "quarantine_reasons", "upper_bound_utc", "field_states"),
}


class AvailabilityError(ValueError):
    """A refused build or query; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------------------------- serialization

def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fields(kind: str, value: Any, expected: Sequence[str]) -> None:
    if not isinstance(value, dict) or set(value) != set(expected):
        got = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise AvailabilityError("UNKNOWN_FIELD", f"{kind} fields {got} differ from {sorted(expected)}")


def _no_float(value: Any) -> None:
    if isinstance(value, float):
        raise AvailabilityError("FLOAT_IN_PAYLOAD", repr(value))
    if isinstance(value, dict):
        for item in value.values():
            _no_float(item)
    elif isinstance(value, list):
        for item in value:
            _no_float(item)


def check_record(record: dict[str, Any]) -> None:
    """Closed-schema check of one payload record and its nested objects."""
    kind = record.get("record_type") if isinstance(record, dict) else None
    if kind not in RECORD_FIELDS:
        raise AvailabilityError("UNKNOWN_FIELD", f"record type {kind!r}")
    _fields(kind, record, RECORD_FIELDS[kind])
    if kind == "view":
        for item in record["same_date_excluded"] + record["undated_excluded"]:
            _fields("excluded", item, NESTED_FIELDS["excluded"])
    elif kind == "relationship" and record["parent_result"] is not None:
        _fields("parent_result", record["parent_result"], NESTED_FIELDS["parent_result"])
    elif kind == "prior_evidence":
        if record["parent_values"] is not None:
            _fields("parent_values", record["parent_values"], NESTED_FIELDS["parent_values"])
        _fields("archive", record["archive"], NESTED_FIELDS["archive"])
        for version in record["archive"]["versions"]:
            _fields("version", version, NESTED_FIELDS["version"])
            _fields("field_states", version["field_states"], FIELDS)
        _fields("field_earliest_qualified_upper_bound_utc",
                record["archive"]["field_earliest_qualified_upper_bound_utc"], FIELDS)
    _no_float(record)


def record_line(record: dict[str, Any]) -> bytes:
    check_record(record)
    return canonical_json_bytes(record) + b"\n"


# --------------------------------------------------------------------------------------------- time

def valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not ISO_DATE.match(value):
        return False
    try:
        return _dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def fmt(value: _dt.datetime) -> str:
    return value.astimezone(_dt.timezone.utc).strftime(BOUND_FORMAT)


def parse_bound(text: str) -> _dt.datetime:
    return _dt.datetime.strptime(text, BOUND_FORMAT).replace(tzinfo=_dt.timezone.utc)


def conservative_boundary(contest_date: str) -> _dt.datetime:
    """The earliest instant compatible with a calendar date anywhere (00:00 at UTC+14 = 00:00 UTC minus 14 hours).
    A conservative date boundary, not an observed kickoff."""
    instant = source_time.earliest_event_instant(contest_date)
    if instant is None:
        raise AvailabilityError("DATE_INVALID", f"{contest_date!r} is not a calendar date")
    return instant


def wrapped_message(exc: Exception) -> str:
    """A wrapped reader error's message without its own leading ``CODE: `` (AvailabilityError adds the code once)."""
    text, prefix = str(exc), f"{getattr(exc, 'code', '')}: "
    return text[len(prefix):] if text.startswith(prefix) else text


def parse_cutoff(value: str | None) -> _dt.datetime:
    """The accepted source-time cutoff grammar: an ISO-8601 instant with seconds and an explicit zone."""
    try:
        return source_time.parse_cutoff(value)
    except source_time.SourceTimeQueryError as exc:
        raise AvailabilityError(exc.code, wrapped_message(exc)) from exc


# --------------------------------------------------------------------------------------------- predicates

def pool_reasons(row: dict[str, Any]) -> list[str]:
    """Every failing Cycle 39 history predicate for one parent contest, in contract order."""
    reasons: list[str] = []
    if row["disposition"] != "VERIFIED_PRESENT":
        reasons.append("DISPOSITION_NOT_VERIFIED_PRESENT")
    if row["reconciliation_state"] != "RECONCILED_2016_2023":
        reasons.append("RECONCILIATION_NOT_RECONCILED_2016_2023")
    if row["contest_status"] != "COMPLETED":
        reasons.append("STATUS_NOT_COMPLETED")
    if not (type(row["competitive"]) is int and row["competitive"] == 1):
        reasons.append("NOT_COMPETITIVE")
    if not valid_date(row["contest_date"]):
        reasons.append("DATE_INVALID")
    else:
        observed = row.get("contest_dates_observed")
        if observed is not None:
            try:
                dates = json.loads(observed) if isinstance(observed, str) else observed
            except ValueError:
                dates = None
            if not isinstance(dates, list) or set(dates) != {row["contest_date"]}:
                reasons.append("DATE_NOT_SINGLE")
    stable = True
    for side in ("a", "b"):
        key = row[f"{side}_key"]
        match = ORG_KEY.match(key) if isinstance(key, str) else None
        if not match or match.group(1) != str(row[f"{side}_org_id"]):
            stable = False
    if not stable:
        reasons.append("ORG_KEY_NOT_STABLE")
    if row["a_key"] == row["b_key"]:
        reasons.append("ORG_KEYS_NOT_DISTINCT")
    points = (row["a_points"], row["b_points"])
    if any(p is None for p in points):
        reasons.append("SCORE_MISSING")
    if any(p is not None and not (type(p) is int and p >= 0) for p in points):
        reasons.append("SCORE_NOT_NONNEGATIVE_INTEGER")
    return reasons


def permute(rows: list[dict[str, Any]], order: str) -> list[dict[str, Any]]:
    if not INPUT_ORDER.match(str(order)):
        raise AvailabilityError("INPUT_ORDER_INVALID", str(order))
    rows = list(rows)
    if order == "reverse":
        rows.reverse()
    elif order.startswith("shuffle:"):
        random.Random(int(order.split(":", 1)[1])).shuffle(rows)
    return rows


# --------------------------------------------------------------------------------------------- archive view

class ArchiveView:
    """The archive facts the projection uses, from a verified sidecar: per tranche key its disposition record and
    its complete ordered capture collection, and per capture its assertion rows."""

    def __init__(self, dispositions: Iterable[dict[str, Any]], captures: Iterable[dict[str, Any]],
                 assertions: Iterable[dict[str, Any]]) -> None:
        self.dispositions = {d["contest_key"]: d for d in dispositions}
        self.captures: dict[str, list[dict[str, Any]]] = {}
        for cap in captures:
            self.captures.setdefault(cap["contest_key"], []).append(cap)
        self.assertions: dict[str, list[dict[str, Any]]] = {}
        for item in assertions:
            self.assertions.setdefault(item["capture_id"], []).append(item)

    @classmethod
    def from_evidence(cls, evidence: Any) -> "ArchiveView":
        """From an accepted, already verified ``national_source_time.archive.ArchiveEvidence``."""
        return cls(evidence.dispositions, evidence.captures, evidence.assertions)


def _bound(capture: dict[str, Any]) -> str | None:
    clock = (capture.get("clocks") or {}).get("archive_capture") or {}
    return clock.get("latest_utc") if clock.get("state") == "PRESENT" else None


def evidence_archive(key: str, archive: ArchiveView) -> dict[str, Any]:
    disposition = archive.dispositions.get(key)
    if disposition is None:
        return {"in_tranche": False, "archive_disposition": None, "acquisition_outcome": None,
                "parent_values_agree": None, "versions": [], "coherent_capture_ids": [],
                "coherent_upper_bound_utc": None, "contradicting_capture_ids": [],
                "field_earliest_qualified_upper_bound_utc": {f: None for f in FIELDS},
                "evidence_class": "NOT_IN_ARCHIVE_TRANCHE", "evidence_reason": "CONTEST_OUTSIDE_THE_ARCHIVE_TRANCHE"}
    captures = archive.captures.get(key, [])
    versions = [{"capture_id": c["capture_id"], "state": c["state"],
                 "quarantine_reasons": list(c.get("quarantine_reasons") or []), "upper_bound_utc": _bound(c),
                 "field_states": {f: c["field_states"][f] for f in FIELDS}} for c in captures]
    qualified = [v for v in versions if v["state"] == "QUALIFIED"]
    contradicting = [v for v in qualified if any(v["field_states"][f] in CONTRADICTING_STATES for f in FIELDS)]
    coherent = [v for v in qualified if all(v["field_states"][f] == QUALIFIED for f in FIELDS)
                and v["upper_bound_utc"] is not None]
    earliest = {}
    for field in FIELDS:
        bounds = sorted(v["upper_bound_utc"] for v in qualified
                        if v["field_states"][field] == QUALIFIED and v["upper_bound_utc"] is not None)
        earliest[field] = bounds[0] if bounds else None
    if not versions:
        cls, reason = "ARCHIVE_NO_CAPTURE", f"ARCHIVE_DISPOSITION:{disposition['disposition']}"
    elif not qualified:
        cls, reason = "ARCHIVE_ALL_VERSIONS_QUARANTINED", "QUARANTINED:" + ",".join(
            sorted({r for v in versions for r in v["quarantine_reasons"]}))
    elif contradicting:
        cls, reason = "ARCHIVE_VERSION_CONTRADICTS_PARENT", "CONTRADICTING_VERSIONS:" + ",".join(
            f"{v['capture_id']}[{'/'.join(f for f in FIELDS if v['field_states'][f] in CONTRADICTING_STATES)}]"
            for v in contradicting)
    elif coherent:
        cls, reason = "ARCHIVE_COHERENT_VERSION", "ONE_VERSION_QUALIFIES_ALL_SIX_FIELDS"
    else:
        missing = [f for f in FIELDS if earliest[f] is None]
        cls = "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION"
        reason = ("FIELDS_NEVER_QUALIFIED_IN_ANY_VERSION:" + "/".join(missing)) if missing else \
            "EVERY_FIELD_QUALIFIED_ONLY_IN_DIFFERENT_VERSIONS_NOT_COMBINED"
    coherent_bounds = sorted(v["upper_bound_utc"] for v in coherent)
    return {"in_tranche": True, "archive_disposition": disposition["disposition"],
            "acquisition_outcome": disposition.get("acquisition_outcome"), "parent_values_agree": None,
            "versions": versions,
            "coherent_capture_ids": [v["capture_id"] for v in coherent] if cls == "ARCHIVE_COHERENT_VERSION" else [],
            "coherent_upper_bound_utc": coherent_bounds[0] if cls == "ARCHIVE_COHERENT_VERSION" else None,
            "contradicting_capture_ids": [v["capture_id"] for v in contradicting],
            "field_earliest_qualified_upper_bound_utc": earliest, "evidence_class": cls, "evidence_reason": reason}


# --------------------------------------------------------------------------------------------- derivation

def _result(points_for: int, points_against: int) -> str:
    return "W" if points_for > points_against else ("L" if points_for < points_against else "T")


class Projection:
    """Every projection record for one set of verified parents; built once, served chunk by chunk."""

    def __init__(self, population_rows: list[dict[str, Any]], subset_keys: Iterable[str],
                 history_targets: list[dict[str, Any]], history_views: list[dict[str, Any]], archive: ArchiveView,
                 *, input_order: str = "natural") -> None:
        rows = permute(population_rows, input_order)
        subset = set(subset_keys)
        keys = [r["contest_key"] for r in rows]
        if len(set(keys)) != len(keys):
            raise AvailabilityError("PARENT_DUPLICATE_KEY", f"{len(keys) - len(set(keys))} duplicate 2019 parent keys")
        bad = [r["contest_key"] for r in rows if r["season"] != SEASON or type(r["season"]) is not int]
        if bad:
            raise AvailabilityError("PARENT_SCHEMA_INVALID", f"non-2019 rows supplied: {sorted(bad)[:5]}")
        inconsistent = sorted(r["contest_key"] for r in rows if (r["contest_key"] in subset) != (
            r["a_division_label"] == "FBS" and r["b_division_label"] == "FBS"))
        if inconsistent:
            raise AvailabilityError("SUBSET_FIELD_INCONSISTENT", f"{len(inconsistent)} contests: {inconsistent[:5]}")
        self.archive = archive
        self.reasons = {r["contest_key"]: pool_reasons(r) for r in rows}
        self.by_key = {r["contest_key"]: r for r in rows}
        self.by_team: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            for side in ("a", "b"):
                if isinstance(row[f"{side}_key"], str):
                    self.by_team.setdefault(row[f"{side}_key"], []).append(row)
        for entries in self.by_team.values():
            entries.sort(key=lambda r: (r["contest_date"] if valid_date(r["contest_date"]) else "", r["contest_key"]))
        self.targets = sorted((r for r in rows if r["contest_key"] in subset and not self.reasons[r["contest_key"]]),
                              key=lambda r: (r["contest_date"], r["contest_key"]))
        self.target_keys = [r["contest_key"] for r in self.targets]
        self.views: dict[tuple[str, str], dict[str, Any]] = {}
        self.relationships: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for target in self.targets:
            for view, side, other in (("A", "a", "b"), ("B", "b", "a")):
                self.views[(target["contest_key"], view)], self.relationships[(target["contest_key"], view)] = \
                    self._view(target, view, side, other)
        self._reconcile_history(history_targets, history_views)
        referenced = {rel["prior_contest_key"] for rels in self.relationships.values() for rel in rels}
        self.evidence = [self._evidence(self.by_key[key]) for key in sorted(
            referenced, key=lambda k: (self.by_key[k]["contest_date"], k))]
        self.witnesses = [w for record in self.evidence for w in self._witnesses(record)]

    # ------------------------------------------------------------------ views and relationships
    def _view(self, target: dict[str, Any], view: str, side: str, other: str) -> tuple[dict, list]:
        team, opponent, date, key = target[f"{side}_key"], target[f"{other}_key"], target["contest_date"], \
            target["contest_key"]
        relationships, same_date, undated, later = [], [], [], 0
        for row in self.by_team.get(team, []):
            if row["contest_key"] == key:
                continue
            reasons = self.reasons[row["contest_key"]]
            mine = "a" if row["a_key"] == team else "b"
            theirs = "b" if mine == "a" else "a"
            if not valid_date(row["contest_date"]):
                undated.append({"contest_key": row["contest_key"], "contest_date": row["contest_date"],
                                "opponent_key": row[f"{theirs}_key"], "reasons": list(reasons)})
                continue
            if row["contest_date"] > date:
                later += 1
                continue
            if row["contest_date"] == date:
                same_date.append({"contest_key": row["contest_key"], "contest_date": row["contest_date"],
                                  "opponent_key": row[f"{theirs}_key"],
                                  "reasons": list(reasons) + ["SAME_DATE_NOT_STRICTLY_EARLIER"]})
                continue
            pool = not reasons
            result = None
            if pool:
                pf, pa = row[f"{mine}_points"], row[f"{theirs}_points"]
                result = {"points_for": pf, "points_against": pa, "result": _result(pf, pa)}
            relationships.append({
                "record_type": "relationship", "target_contest_key": key, "view": view, "season": SEASON,
                "target_date": date, "team_key": team, "current_opponent_key": opponent,
                "prior_contest_key": row["contest_key"], "prior_contest_date": row["contest_date"],
                "prior_side": mine.upper(), "prior_opponent_key": row[f"{theirs}_key"],
                "prior_opponent_division_label": row[f"{theirs}_division_label"],
                "prior_classification_pair": row["classification_pair"],
                "relationship_class": "HISTORY_POOL_PRIOR" if pool else "PARENT_EXCLUDED_PRIOR",
                "parent_exclusion_reasons": list(reasons), "parent_result": result, **ROW_LABELS})
        pool_count = sum(1 for r in relationships if r["relationship_class"] == "HISTORY_POOL_PRIOR")
        record = {"record_type": "view", "target_contest_key": key, "view": view, "season": SEASON,
                  "target_date": date, "prior_rule": PRIOR_RULE, "team_key": team,
                  "team_org_id": target[f"{side}_org_id"], "team_name": target[f"{side}_team_name"],
                  "team_division_label": target[f"{side}_division_label"], "opponent_key": opponent,
                  "opponent_org_id": target[f"{other}_org_id"], "opponent_name": target[f"{other}_team_name"],
                  "opponent_division_label": target[f"{other}_division_label"],
                  "expected_prior_relationships": len(relationships), "history_pool_priors": pool_count,
                  "parent_excluded_priors": len(relationships) - pool_count,
                  "relationship_contest_keys": [r["prior_contest_key"] for r in relationships],
                  "same_date_excluded": sorted(same_date, key=lambda x: x["contest_key"]),
                  "undated_excluded": sorted(undated, key=lambda x: x["contest_key"]),
                  "later_contests_excluded": later,
                  "history_state": "HAS_EXPECTED_PRIORS" if relationships else "COLD_START_NO_EXPECTED_PRIORS",
                  **ROW_LABELS}
        return record, relationships

    def _reconcile_history(self, history_targets: list[dict[str, Any]], history_views: list[dict[str, Any]]) -> None:
        """Both directions against the accepted Cycle 39 history: the same 2019 targets and, per view, the same
        contributing contests (lineage and parent result) and the same excluded inputs with their reasons."""
        mine = {r["contest_key"]: (r["contest_date"], r["a_key"], r["b_key"]) for r in self.targets}
        theirs = {r["contest_key"]: (r["contest_date"], r["a_key"], r["b_key"]) for r in history_targets}
        if mine != theirs or len(theirs) != len(history_targets):
            raise AvailabilityError("HISTORY_PARENT_MISMATCH", f"targets differ: missing {sorted(set(theirs) - set(mine))[:5]}"
                                    f" extra {sorted(set(mine) - set(theirs))[:5]}")
        views = {(v["target_contest_key"], v["view"]): v for v in history_views}
        if set(views) != set(self.views) or len(views) != len(history_views):
            raise AvailabilityError("HISTORY_PARENT_MISMATCH", "history views are not exactly two per target")
        for vkey, record in self.views.items():
            other = (vkey[0], "B" if vkey[1] == "A" else "A")
            for block, rels, own in ((views[vkey]["team_history"], self.relationships[vkey], record),
                                     (views[other]["opponent_history"], self.relationships[vkey], record)):
                pool = [r for r in rels if r["relationship_class"] == "HISTORY_POOL_PRIOR"]
                contributing = [{"contest_key": r["prior_contest_key"], "contest_date": r["prior_contest_date"],
                                 "side": r["prior_side"], "opponent_key": r["prior_opponent_key"],
                                 "opponent_division_label": r["prior_opponent_division_label"],
                                 "points_for": r["parent_result"]["points_for"],
                                 "points_against": r["parent_result"]["points_against"],
                                 "result": r["parent_result"]["result"]} for r in pool]
                excluded = [{"contest_key": r["prior_contest_key"], "contest_date": r["prior_contest_date"],
                             "opponent_key": r["prior_opponent_key"], "reasons": r["parent_exclusion_reasons"]}
                            for r in rels if r["relationship_class"] == "PARENT_EXCLUDED_PRIOR"]
                excluded = sorted(excluded + own["same_date_excluded"] + own["undated_excluded"],
                                  key=lambda x: (x["contest_date"] if valid_date(x["contest_date"]) else "",
                                                 x["contest_key"]))
                if block.get("team_key") != own["team_key"] or block.get("contributing") != contributing or \
                        block.get("excluded_inputs") != excluded or block.get("games") != len(pool):
                    raise AvailabilityError("HISTORY_PARENT_MISMATCH",
                                            f"{vkey} {own['team_key']}: the history parent's contributing or excluded "
                                            f"contests differ from the population derivation")

    # ------------------------------------------------------------------ evidence
    def _evidence(self, row: dict[str, Any]) -> dict[str, Any]:
        reasons = self.reasons[row["contest_key"]]
        pool = not reasons
        values = {"contest_date": row["contest_date"], "a_participant": row["a_key"], "b_participant": row["b_key"],
                  "completion": row["contest_status"], "a_points": row["a_points"],
                  "b_points": row["b_points"]} if pool else None
        archive = evidence_archive(row["contest_key"], self.archive)
        if archive["in_tranche"]:
            stated = self.archive.dispositions[row["contest_key"]].get("parent_values") or {}
            agree = pool and all(stated.get(f) == values[f] for f in FIELDS) and stated.get("season") == SEASON
            if pool and not agree:
                raise AvailabilityError("ARCHIVE_PARENT_VALUE_CONTRADICTION",
                                        f"{row['contest_key']}: the archive's parent values differ from the population")
            archive["parent_values_agree"] = agree if pool else None
        return {"record_type": "prior_evidence", "contest_key": row["contest_key"], "season": SEASON,
                "contest_date": row["contest_date"], "a_key": row["a_key"], "b_key": row["b_key"],
                "classification_pair": row["classification_pair"], "history_pool_member": pool,
                "parent_exclusion_reasons": list(reasons), "parent_values": values,
                "earliest_event_instant_utc": fmt(conservative_boundary(row["contest_date"])), "archive": archive,
                **ROW_LABELS}

    def _witnesses(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for version in record["archive"]["versions"]:
            for item in self.archive.assertions.get(version["capture_id"], []):
                if item["field"] not in FIELDS:
                    continue
                out.append({"record_type": "field_witness", "contest_key": record["contest_key"],
                            "capture_id": version["capture_id"], "capture_state": version["state"],
                            "upper_bound_utc": version["upper_bound_utc"], "field": item["field"],
                            "witness": item["witness"], "witness_span": list(item["witness_span"]),
                            "literal": item["literal"], "value": item["value"],
                            "corroboration": item["corroboration"], "field_state": item["field_state"],
                            **ROW_LABELS})
        return out

    # ------------------------------------------------------------------ serialization
    def target_record(self, row: dict[str, Any]) -> dict[str, Any]:
        return {"record_type": "target", "contest_key": row["contest_key"], "ncaa_contest_id": row["ncaa_contest_id"],
                "season": SEASON, "term": row["term"], "contest_date": row["contest_date"], "a_key": row["a_key"],
                "b_key": row["b_key"], "a_org_id": row["a_org_id"], "b_org_id": row["b_org_id"],
                "a_team_name": row["a_team_name"], "b_team_name": row["b_team_name"],
                "a_division_label": row["a_division_label"], "b_division_label": row["b_division_label"],
                "classification_pair": row["classification_pair"], "parent_site": row["site"],
                "neutral_site_text": row["neutral_site_text"],
                "conservative_date_boundary_utc": fmt(conservative_boundary(row["contest_date"])),
                "views": ["A", "B"], **ROW_LABELS}

    def bundle(self, row: dict[str, Any]) -> bytes:
        """The canonical lines for one target: target, view A, view B, the A relationships, the B relationships."""
        key = row["contest_key"]
        lines = [record_line(self.target_record(row)), record_line(self.views[(key, "A")]),
                 record_line(self.views[(key, "B")])]
        lines += [record_line(r) for r in self.relationships[(key, "A")]]
        lines += [record_line(r) for r in self.relationships[(key, "B")]]
        return b"".join(lines)

    def census_bytes(self) -> tuple[bytes, bytes]:
        return (b"".join(record_line(r) for r in self.evidence), b"".join(record_line(w) for w in self.witnesses))

    def payloads(self) -> dict[str, bytes]:
        return payloads_from(b"".join(self.bundle(row) for row in self.targets), *self.census_bytes())


def payloads_from(bundles: bytes, evidence: bytes, witnesses: bytes) -> dict[str, bytes]:
    """Split a bundle stream by record type, keeping its order, and add the evidence and witness payloads."""
    groups: dict[str, list[bytes]] = {"target": [], "view": [], "relationship": []}
    for line in bundles.splitlines(keepends=True):
        kind = json.loads(line)["record_type"]
        if kind not in groups:
            raise AvailabilityError("REFUSED_ALTERED_PREFIX", f"unexpected record type {kind!r} in the bundle stream")
        groups[kind].append(line)
    return {"targets.jsonl": b"".join(groups["target"]), "views.jsonl": b"".join(groups["view"]),
            "relationships.jsonl": b"".join(groups["relationship"]), "evidence.jsonl": evidence,
            "witnesses.jsonl": witnesses}


# --------------------------------------------------------------------------------------------- parents

def read_population(conn: Any) -> tuple[list[dict[str, Any]], set[str]]:
    """The 2019 parent contests (only 2019 rows are read) and the FBS_ESTIMAND_SUBSET keys, from an open read-only
    population connection."""
    columns = ", ".join(POPULATION_COLUMNS)
    cursor = conn.execute(f"SELECT {columns} FROM contest WHERE season = ? ORDER BY rowid", (SEASON,))
    names = [d[0] for d in cursor.description]
    rows = [dict(zip(names, row)) for row in cursor.fetchall()]
    subset = {row[0] for row in conn.execute(
        "SELECT s.contest_key FROM subset_membership s JOIN contest c ON c.contest_key = s.contest_key "
        "WHERE s.subset = ? AND c.season = ?", (SUBSET, SEASON))}
    return rows, subset


def read_history(conn: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    targets = [json.loads(r[0]) for r in conn.execute("SELECT record FROM targets WHERE season = ? ORDER BY ord",
                                                      (SEASON,))]
    views = [json.loads(r[0]) for r in conn.execute("SELECT record FROM history WHERE season = ? ORDER BY ord",
                                                    (SEASON,))]
    return targets, views


def profile(contract_id: Any) -> dict[str, Any]:
    """The population, archive parent and parent keys of an issued projection contract (V1.0 or the BAT-715
    expansion)."""
    if contract_id not in PROFILES:
        raise AvailabilityError("CONTRACT_SCHEMA_UNKNOWN", f"contract id {contract_id!r}")
    return PROFILES[contract_id]


def parent_files(contract_id: Any) -> dict[str, tuple[str, str]]:
    """PARENT_FILES with the archive parent population of the contract's profile."""
    return {**PARENT_FILES, "archive": (profile(contract_id)["archive_parent"], PARENT_FILES["archive"][1])}


def _check(name: str, observed: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """The bound identity fields of one verified parent must equal the expected binding exactly (an archive binding
    that names a cohort is the BAT-715 expansion's and binds its cohort and retained acquisition too)."""
    keys = EXPANSION_PARENT_KEYS[name] if name == "archive" and "cohort_sha256" in expected else PARENT_KEYS[name]
    wanted = {k: expected.get(k) for k in keys}
    got = {k: observed.get(k) for k in keys}
    if got != wanted:
        differing = sorted(k for k in wanted if got[k] != wanted[k])
        raise AvailabilityError("PARENT_BINDING_MISMATCH", f"{name} parent {differing} differ from the binding")
    return got


def open_parents(paths: dict[str, Any], expected: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Verify every parent with its accepted reader at its expected identity, read the 2019 rows and the verified
    archive view, and return them with the exact bound parent identities. Every reader refusal keeps its own code."""
    from pathlib import Path  # noqa: PLC0415

    from aggie_analytics.national_history import query as history_query  # noqa: PLC0415
    from aggie_analytics.national_population import query as population_query  # noqa: PLC0415
    from aggie_analytics.national_source_time import archive as archive_module  # noqa: PLC0415

    bound: dict[str, dict[str, Any]] = {}
    readers = (population_query.NationalQueryError, history_query.HistoryQueryError,
               source_time.SourceTimeQueryError)
    try:
        exp = expected["population"]
        population = population_query.NationalPopulationDatabase(Path(paths["population"]),
                                                                  expect_identity=exp.get("query_db_identity"))
        try:
            upstream = population.binding.get("upstream") or {}
            bound["population"] = _check("population", {
                "query_db_identity": population.binding["database_identity"],
                "sqlite_sha256": population.binding["database_sha256"],
                "contract_sha256": population.binding["contract_sha256"],
                "contest_identity": upstream.get("contest"), "program_season_identity": upstream.get("program-season")},
                exp)
            if (population.meta.get("contest_identity"), population.meta.get("program_season_identity")) != (
                    exp.get("contest_identity"), exp.get("program_season_identity")):
                raise AvailabilityError("PARENT_BINDING_MISMATCH", "population meta identities differ from the binding")
            population_rows, subset = read_population(population.conn)
        finally:
            population.close()
        exp = expected["history"]
        with history_query.NationalHistoryDatabase(Path(paths["history"]),
                                                   expect_identity=exp.get("database_identity")) as history:
            bound["history"] = _check("history", {
                "database_identity": history.binding["database_identity"],
                "sqlite_sha256": history.binding["database_sha256"],
                "content_identity": history.binding["content_identity"],
                "contract_sha256": history.binding["contract_sha256"]}, exp)
            history_targets, history_views = read_history(history.conn)
        exp = expected["source_time"]
        source = source_time.SourceTimeDatabase(Path(paths["source_time"]), expect_identity=exp.get("database_identity"))
        try:
            bound["source_time"] = _check("source_time", {
                "database_identity": source.binding["database_identity"],
                "sqlite_sha256": source.binding["database_sha256"],
                "content_identity": source.binding["content_identity"],
                "contract_sha256": source.binding["contract_sha256"]}, expected["source_time"])
            exp = expected["archive"]
            evidence = archive_module.ArchiveEvidence(Path(paths["archive"]), source,
                                                      expect_identity=exp.get("database_identity"))
            bound["archive"] = _check("archive", {
                "database_identity": evidence.binding["archive_identity"],
                "sqlite_sha256": evidence.binding["archive_sha256"],
                "content_identity": evidence.binding["content_identity"],
                "contract_sha256": evidence.binding["contract_sha256"],
                "contract_id": evidence.meta.get("contract_id"), "tranche_sha256": evidence.meta.get("tranche_sha256"),
                "acquisition_identity": evidence.meta.get("acquisition_identity"),
                "cohort_sha256": evidence.meta.get("cohort_sha256"),
                "retained_acquisition_identity": getattr(evidence.authority, "retained_acquisition_identity", None)},
                exp)
            view = ArchiveView.from_evidence(evidence)
        finally:
            source.close()
    except readers as exc:
        raise AvailabilityError(exc.code, wrapped_message(exc)) from exc
    return {"population_rows": population_rows, "subset": subset, "history_targets": history_targets,
            "history_views": history_views, "archive": view, "parent": bound}


# --------------------------------------------------------------------------------------------- decisions

def decide(relationship: dict[str, Any], evidence: dict[str, Any], cutoff: _dt.datetime) -> dict[str, Any]:
    """The support decision for one relationship at one explicit cutoff."""
    if relationship["relationship_class"] != "HISTORY_POOL_PRIOR":
        return {"support_state": "EXCLUDED_FROM_HISTORY_POOL", "result_published_by_cutoff": None,
                "reason_class": "PARENT_EXCLUDED_PRIOR",
                "reason": "PARENT_EXCLUDED:" + ",".join(relationship["parent_exclusion_reasons"]),
                "supporting_capture_ids": []}
    archive = evidence["archive"]
    cls = archive["evidence_class"]
    if cls != "ARCHIVE_COHERENT_VERSION":
        published = UNKNOWN if cls == "ARCHIVE_VERSION_CONTRADICTS_PARENT" else NO_ARCHIVE
        return {"support_state": "UNSUPPORTED", "result_published_by_cutoff": published, "reason_class": cls,
                "reason": archive["evidence_reason"], "supporting_capture_ids": []}
    supporting = [v["capture_id"] for v in archive["versions"] if v["capture_id"] in archive["coherent_capture_ids"]
                  and parse_bound(v["upper_bound_utc"]) <= cutoff]
    if supporting:
        return {"support_state": "SUPPORTED", "result_published_by_cutoff": TRUE,
                "reason_class": "ARCHIVE_COHERENT_VERSION_AT_OR_BEFORE_CUTOFF",
                "reason": "ARCHIVED_COHERENT_VERSION_CAPTURED_AT_OR_BEFORE_CUTOFF", "supporting_capture_ids": supporting}
    if cutoff < conservative_boundary(relationship["prior_contest_date"]):
        return {"support_state": "UNSUPPORTED", "result_published_by_cutoff": FALSE,
                "reason_class": "OUTCOME_CANNOT_EXIST_BEFORE_PRIOR_EVENT_DATE",
                "reason": "CUTOFF_BEFORE_THE_PRIOR_CONTEST_DATE_EARLIEST_INSTANT", "supporting_capture_ids": []}
    return {"support_state": "UNSUPPORTED", "result_published_by_cutoff": UNKNOWN,
            "reason_class": "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF",
            "reason": "BEFORE_ARCHIVE_UPPER_BOUND_EARLIER_PUBLICATION_NOT_EXCLUDED", "supporting_capture_ids": []}


def rate(numerator: int, denominator: int) -> dict[str, int] | None:
    return {"numerator": numerator, "denominator": denominator} if denominator else None


def summarize(team_key: str, relationships: list[dict[str, Any]], evidence: dict[str, dict[str, Any]],
              cutoff: _dt.datetime) -> dict[str, Any]:
    """One team's history at a cutoff: the complete expected denominator, the supported subset with integer totals and
    exact unreduced rates (null over zero supported games) and every unsupported reason class."""
    pool = [r for r in relationships if r["relationship_class"] == "HISTORY_POOL_PRIOR"]
    decisions = [(r, decide(r, evidence[r["prior_contest_key"]], cutoff)) for r in relationships]
    supported = [r for r, d in decisions if d["support_state"] == "SUPPORTED"]
    reasons = {name: 0 for name in UNSUPPORTED_REASON_CLASSES}
    for _r, d in decisions:
        if d["support_state"] == "UNSUPPORTED":
            reasons[d["reason_class"]] += 1
    wins = sum(1 for r in supported if r["parent_result"]["result"] == "W")
    losses = sum(1 for r in supported if r["parent_result"]["result"] == "L")
    ties = sum(1 for r in supported if r["parent_result"]["result"] == "T")
    pf = sum(r["parent_result"]["points_for"] for r in supported)
    pa = sum(r["parent_result"]["points_against"] for r in supported)
    n = len(supported)
    expected = len(relationships)
    if expected == 0:
        state = "COLD_START_NO_EXPECTED_PRIORS"
    elif n == expected:
        state = "ALL_EXPECTED_PRIORS_SUPPORTED"
    elif n == 0:
        state = "NO_SUPPORTED_PRIORS"
    else:
        state = "PARTIAL_SUPPORTED_SUBSET"
    return {"team_key": team_key, "expected_prior_relationships": expected, "history_pool_priors": len(pool),
            "parent_excluded_priors": expected - len(pool), "supported_priors": n,
            "unsupported_priors": len(pool) - n, "unsupported_by_reason_class": reasons,
            "completeness_state": state, "supported_subset_is_complete_history": n == expected,
            "supported_subset": {"games": n, "wins": wins, "losses": losses, "ties": ties, "points_for_total": pf,
                                 "points_against_total": pa, "margin_total": pf - pa,
                                 "win_rate": rate(wins, n), "points_for_mean": rate(pf, n),
                                 "points_against_mean": rate(pa, n), "margin_mean": rate(pf - pa, n),
                                 "contributing_contest_keys": [r["prior_contest_key"] for r in supported],
                                 "rate_scope": "SUPPORTED_SUBSET_ONLY_NOT_FULL_HISTORY", "imputation": "NONE"}}


def cutoff_position(target_date: str, cutoff: _dt.datetime) -> dict[str, Any]:
    boundary = conservative_boundary(target_date)
    return {"conservative_date_boundary_utc": fmt(boundary),
            "position": "BEFORE_CONSERVATIVE_TARGET_DATE_BOUNDARY" if cutoff < boundary else
            "AT_OR_AFTER_CONSERVATIVE_TARGET_DATE_BOUNDARY", "boundary_basis": BOUNDARY_BASIS, "use": CUTOFF_USE,
            "pregame_claim": False, "pit_admission": "NOT_ADMITTED"}


# --------------------------------------------------------------------------------------------- comparison

_NATURAL = {
    "targets.jsonl": lambda r: (r.get("contest_key"),),
    "views.jsonl": lambda r: (r.get("target_contest_key"), r.get("view")),
    "relationships.jsonl": lambda r: (r.get("target_contest_key"), r.get("view"), r.get("prior_contest_key")),
    "evidence.jsonl": lambda r: (r.get("contest_key"),),
    "witnesses.jsonl": lambda r: (r.get("capture_id"), r.get("field"), r.get("witness"),
                                  tuple(r.get("witness_span") or ())),
}
_COLLECTION = {"targets.jsonl": "TARGET_COLLECTION_MISMATCH", "views.jsonl": "VIEW_COLLECTION_MISMATCH",
               "relationships.jsonl": "RELATIONSHIP_COLLECTION_MISMATCH",
               "evidence.jsonl": "EVIDENCE_COLLECTION_MISMATCH", "witnesses.jsonl": "WITNESS_COLLECTION_MISMATCH"}
ORIENTATION_FIELDS = {"team_key", "current_opponent_key", "prior_side", "prior_opponent_key", "parent_result",
                      "prior_opponent_division_label", "opponent_key", "team_org_id", "team_name",
                      "team_division_label", "opponent_org_id", "opponent_name", "opponent_division_label"}
COUNT_FIELDS = {"expected_prior_relationships", "history_pool_priors", "parent_excluded_priors",
                "relationship_contest_keys", "later_contests_excluded", "history_state"}


def mismatch(name: str, expected: list[bytes], stored: list[bytes]) -> tuple[str, str] | None:
    """None when the stored lines equal the derived lines; otherwise the refusal code for the first semantic class a
    difference reaches (checked in this order: forged labels, temporal order, collection, order, fields)."""
    if expected == stored:
        return None
    try:
        got = [json.loads(line) for line in stored]
    except ValueError:
        return "PAYLOAD_MALFORMED", f"{name} holds a line that is not JSON"
    want = [json.loads(line) for line in expected]
    for record in got:
        if isinstance(record, dict) and any(record.get(k) != v for k, v in ROW_LABELS.items()):
            return "FORGED_AUTHORITY_LABEL", f"{name} {_NATURAL[name](record)} carries a changed authority label"
    if name == "relationships.jsonl":
        for record in got:
            date, target = record.get("prior_contest_date"), record.get("target_date")
            if not (valid_date(date) and valid_date(target) and date < target):
                return "RELATIONSHIP_TEMPORAL_ORDER_VIOLATION", \
                    f"{_NATURAL[name](record)} is not strictly earlier than its target"
    key = _NATURAL[name]
    have, wanted = collections.Counter(key(r) for r in got), collections.Counter(key(r) for r in want)
    if have != wanted:
        return _COLLECTION[name], (f"missing {sorted((wanted - have).elements())[:3]} extra "
                                   f"{sorted((have - wanted).elements())[:3]} duplicated "
                                   f"{sorted(k for k, n in have.items() if n > 1)[:3]}")
    if [key(r) for r in got] != [key(r) for r in want]:
        return "RECORD_ORDER_MISMATCH", f"{name} records are not in the payload order"
    for a, b in zip(want, got):
        if a == b:
            continue
        differs = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        where = f"{key(a)} {differs[:6]}"
        if name == "relationships.jsonl":
            if any(k in ORIENTATION_FIELDS for k in differs):
                return "RELATIONSHIP_ORIENTATION_MISMATCH", where
            if any(k in ("relationship_class", "parent_exclusion_reasons") for k in differs):
                return "RELATIONSHIP_CLASS_MISMATCH", where
            return "RELATIONSHIP_RECORD_MISMATCH", where
        if name == "views.jsonl":
            if any(k in ("team_key", "opponent_key") for k in differs) and a.get("team_key") == b.get("opponent_key"):
                return "VIEW_ORIENTATION_MISMATCH", where
            if any(k in COUNT_FIELDS for k in differs):
                return "VIEW_COUNT_MISMATCH", where
            return "VIEW_RECORD_MISMATCH", where
        if name == "evidence.jsonl":
            if "archive" in differs:
                ida = [v.get("capture_id") for v in (a.get("archive") or {}).get("versions", [])]
                idb = [v.get("capture_id") for v in ((b.get("archive") or {}).get("versions") or [])
                       if isinstance(v, dict)]
                if ida != idb:
                    return "EVIDENCE_VERSION_COLLECTION_MISMATCH", where
                return "EVIDENCE_SUPPORT_FORGERY", where
            if "parent_values" in differs:
                return "EVIDENCE_PARENT_VALUE_MISMATCH", where
            return "EVIDENCE_RECORD_MISMATCH", where
        if name == "witnesses.jsonl":
            return "WITNESS_MISMATCH", where
        return "TARGET_RECORD_MISMATCH", where
    return "PAYLOAD_BYTES_MISMATCH", f"{name} bytes differ from the canonical serialization"
