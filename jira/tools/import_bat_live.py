from __future__ import annotations

import argparse
import base64
import copy
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://kevinsgarrett.atlassian.net"
EMAIL = "kevinsgarrett@gmail.com"
PROJECT_KEY = "BAT"
PROJECT_ID = "10133"
BOARD_ID = "134"
BOARD_FILTER_ID = "10134"

ROOT = Path(__file__).resolve().parents[2]
JIRA_ROOT = ROOT / "jira"
LEDGER_PATH = JIRA_ROOT / "reconciliation" / "BAT_LIVE_IMPORT_LEDGER.json"
EXPORT_PATH = JIRA_ROOT / "reconciliation" / "BAT_JIRA_EXPORT.csv"
VERIFY_PATH = JIRA_ROOT / "validation" / "BAT_LIVE_IMPORT_VERIFICATION.json"
COMPLETION_POLICY_PATH = JIRA_ROOT / "project" / "HISTORICAL_COMPLETION_ASSURANCE_POLICY.json"
AUXILIARY_ISSUES_PATH = JIRA_ROOT / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json"

ISSUES_CSV = JIRA_ROOT / "import" / "JIRA_ISSUES_MASTER.csv"
CREATE_PAYLOADS = JIRA_ROOT / "import" / "JIRA_API_CREATE_PAYLOADS.jsonl"
LINKS_CSV = JIRA_ROOT / "import" / "JIRA_LINKS.csv"
LINK_PAYLOADS = JIRA_ROOT / "import" / "JIRA_API_LINK_PAYLOADS.jsonl"
COMPONENTS_CSV = JIRA_ROOT / "project" / "COMPONENTS.csv"

SOURCE_FILES = [
    ISSUES_CSV,
    CREATE_PAYLOADS,
    LINKS_CSV,
    LINK_PAYLOADS,
    COMPONENTS_CSV,
    JIRA_ROOT / "project" / "FIELD_SCHEMA.yaml",
    JIRA_ROOT / "project" / "ISSUE_TYPE_MAPPING.yaml",
    JIRA_ROOT / "project" / "PRIORITY_MAPPING.yaml",
    JIRA_ROOT / "project" / "WORKFLOW_MAPPING.yaml",
    AUXILIARY_ISSUES_PATH,
]

FIELD_SPECS = [
    {
        "name": "Local Issue ID",
        "column": "Local Issue ID",
        "kind": "text",
        "description": "Stable canonical identifier from C:\\BatteredAggieSyndrome\\jira; required for lossless Jira reconciliation.",
    },
    {
        "name": "Source IDs",
        "column": "Source IDs",
        "kind": "text",
        "description": "Compact searchable source, governance, and historical identifiers owned by the canonical local Jira specification.",
    },
    {
        "name": "Phase",
        "column": "Phase",
        "kind": "select",
        "options": ["PHASE-1", "PHASE-2", "PHASE-3", "PHASE-4", "PHASE-5"],
        "description": "Portable project phase metadata; no unsupported hierarchy above Epic is implied.",
    },
    {
        "name": "Logical Workflow State",
        "column": "Logical Workflow State",
        "kind": "select",
        "options": [
            "BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW",
            "VALIDATION", "EVIDENCE_PENDING", "DONE", "DEFERRED", "CANCELLED",
        ],
        "description": "Evidence-aware local workflow state, intentionally separate from Jira's operational status.",
    },
    {
        "name": "Implementation Maturity",
        "column": "Implementation Maturity",
        "kind": "select",
        "options": [
            "DESIGN_ONLY", "CONTRACT_DEFINED", "FUNCTIONAL_STARTER", "IMPLEMENTED",
            "INTEGRATED", "EMPIRICALLY_VALIDATED", "PRODUCTION_READY", "OPERATING",
        ],
        "description": "Implementation maturity kept separate from workflow status and evidence state to prevent fabricated completion.",
    },
    {
        "name": "Evidence State",
        "column": "Evidence State",
        "kind": "select",
        "options": ["PLANNED", "PARTIAL", "BLOCKED", "VERIFIED"],
        "description": "Completion-evidence state; code existence or Jira Done alone does not prove completion.",
    },
    {
        "name": "Owner Historical Wave",
        "column": "Owner Historical Wave",
        "kind": "text",
        "description": "Original wave or POST_W25 provenance for the canonical work item.",
    },
    {
        "name": "Critical Path",
        "column": "Critical Path",
        "kind": "select",
        "options": ["false", "true"],
        "description": "Dependency-critical path flag; it is not a time estimate.",
    },
    {
        "name": "Execution Lane",
        "column": "Execution Lane",
        "kind": "select",
        "options": [
            "DATA_MATERIALIZATION", "OPERATIONS", "PROTECTED_GATE", "RESEARCH_LANE",
            "SCIENTIFIC", "SECURITY", "SHARED_CONTRACT", "SOLO_WORKTREE",
        ],
        "description": "Safe execution and concurrency lane for AI implementation sessions.",
    },
]

SAVED_FILTERS = [
    (
        "BAT — Ready Atomic Work",
        'project = BAT AND cf[{workflow}] = READY AND labels = atomic-execution ORDER BY priority DESC, Rank ASC',
        "Only dependency-satisfied atomic work. Start here; aggregate Epic/Story gates are not direct implementation tasks.",
    ),
    (
        "BAT — Blocked Work",
        'project = BAT AND cf[{workflow}] = BLOCKED ORDER BY priority DESC, Rank ASC',
        "Blocked work with explicit prerequisite or evidence obligations in each description.",
    ),
    (
        "BAT — Deferred or Conditional Work",
        'project = BAT AND cf[{workflow}] IN (DEFERRED, CANCELLED) ORDER BY priority DESC, Rank ASC',
        "Deferred/conditional work kept outside the core release until its admission gate is met.",
    ),
    (
        "BAT — Critical Path",
        'project = BAT AND cf[{critical}] = "true" AND labels = post-wave ORDER BY priority DESC, Rank ASC',
        "Post-W25 dependency-critical work, preserving evidence and protected-governance gates.",
    ),
    (
        "BAT — Historical W01-W25 Reference",
        'project = BAT AND labels = historical ORDER BY key ASC',
        "Scoped W01-W25 planning/design/starter provenance. Historical Done is not a production-performance claim.",
    ),
    (
        "BAT — Historical Completion Not Proven",
        'project = BAT AND labels = completion-not-proven ORDER BY key ASC',
        "Historical records whose original WBS completion is preserved but whose live operational Done claim lacks a completion contract and evidence manifest.",
    ),
]


class JiraError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, body: str):
        super().__init__(f"{method} {path} failed with HTTP {status}: {body[:2000]}")
        self.method = method
        self.path = path
        self.status = status
        self.body = body


class JiraClient:
    def __init__(self, base_url: str, email: str, token: str):
        auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "BAS-Jira-Canonical-Importer/1.0",
        }

    def request(self, method: str, path: str, payload: Any | None = None) -> Any:
        url = self.base_url + path
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        for attempt in range(8):
            req = urllib.request.Request(url, data=data, method=method, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    raw = response.read()
                    if not raw:
                        return None
                    return json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 or 500 <= exc.code < 600:
                    retry_after = exc.headers.get("Retry-After", "")
                    delay = float(retry_after) if retry_after.isdigit() else min(30.0, 1.5 * (2**attempt))
                    time.sleep(delay)
                    continue
                raise JiraError(method, path, exc.code, raw) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 7:
                    raise RuntimeError(f"{method} {path} exhausted retries: {exc}") from exc
                time.sleep(min(30.0, 1.5 * (2**attempt)))
        raise RuntimeError(f"{method} {path} exhausted retries")

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: Any) -> Any:
        return self.request("POST", path, payload)

    def put(self, path: str, payload: Any) -> Any:
        return self.request("PUT", path, payload)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def load_completion_policy() -> dict[str, Any]:
    policy = load_json(COMPLETION_POLICY_PATH, {})
    if not policy:
        return {"local_issue_ids": [], "jira_operational_override": {}}
    ids = policy.get("local_issue_ids", [])
    if len(ids) != len(set(ids)) or int(policy.get("issue_count", -1)) != len(ids):
        raise RuntimeError("Historical completion assurance policy has invalid issue identity cardinality")
    return policy


def load_auxiliary_issues() -> dict[str, dict[str, Any]]:
    registry = load_json(AUXILIARY_ISSUES_PATH, {})
    if registry.get("schema_version") != 1:
        raise RuntimeError("Auxiliary Jira issue registry has an unsupported schema")
    issues = registry.get("issues", [])
    by_key = {item["jira_key"]: item for item in issues}
    local_ids = [item["local_id"] for item in issues]
    if len(by_key) != len(issues) or len(set(local_ids)) != len(local_ids):
        raise RuntimeError("Auxiliary Jira issue identities must be unique")
    for key, item in by_key.items():
        if not re.fullmatch(r"BAT-\d+", key) or not item["local_id"] or not item["summary"]:
            raise RuntimeError(f"Invalid auxiliary Jira issue identity: {key}")
    return by_key


def read_env_token(path: Path) -> str:
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw.startswith("JIRA_API_KEY="):
            value = raw.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("JIRA_API_KEY is missing or blank in .env")


def authoritative_env_path() -> Path:
    run = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if run.returncode != 0:
        raise RuntimeError("Unable to resolve the authoritative Git common directory for .env")
    path = Path(run.stdout.strip()).resolve().parent / ".env"
    if not path.is_file():
        raise RuntimeError("Authoritative project .env is unavailable")
    return path


def canonical_expected_counts() -> dict[str, int]:
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((JIRA_ROOT / "records" / "issues").rglob("*.json"))
    ]
    link_signatures: set[tuple[str, str, str]] = set()
    for record in records:
        local_id = record["local_id"]
        for dependency in record.get("dependencies", []):
            link_signatures.add((dependency, "BLOCKS", local_id))
        for related in record.get("related_to", []):
            link_signatures.add((local_id, "RELATES_TO", related))
    return {
        "issues": len(records),
        "links": len(link_signatures),
        "parents": sum(bool(record.get("parent_id")) for record in records),
        "active_post_wave": sum(record.get("historical_classification") == "ACTIONABLE_POST_WAVE" for record in records),
    }


def load_inputs() -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    with ISSUES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    payloads = [json.loads(line) for line in CREATE_PAYLOADS.read_text(encoding="utf-8").splitlines() if line.strip()]
    with LINKS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        links = list(csv.DictReader(handle))
    link_payloads = [json.loads(line) for line in LINK_PAYLOADS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows, payloads, links, link_payloads


def validate_inputs(
    rows: list[dict[str, str]],
    payloads: list[dict[str, Any]],
    links: list[dict[str, str]],
    link_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    expected = canonical_expected_counts()
    if len(rows) != expected["issues"] or len(payloads) != expected["issues"]:
        errors.append(f"expected {expected['issues']} issues/payloads, got {len(rows)}/{len(payloads)}")
    if len(links) != expected["links"] or len(link_payloads) != expected["links"]:
        errors.append(f"expected {expected['links']} links/payloads, got {len(links)}/{len(link_payloads)}")
    local_ids: set[str] = set()
    import_to_local: dict[str, str] = {}
    for row in rows:
        local_id = row["Local Issue ID"]
        if local_id in local_ids:
            errors.append(f"duplicate Local Issue ID: {local_id}")
        if row["Parent"] and row["Parent"] not in import_to_local:
            errors.append(f"parent is not earlier than child {local_id}: {row['Parent']}")
        local_ids.add(local_id)
        import_to_local[row["Issue ID"]] = local_id
    for row, template in zip(rows, payloads):
        local_id = row["Local Issue ID"]
        fields = template["payload_template"]["fields"]
        if template["local_id"] != local_id:
            errors.append(f"payload order mismatch for {local_id}")
        if fields["summary"] != row["Summary"]:
            errors.append(f"summary mismatch for {local_id}")
        if fields["issuetype"]["name"] != row["Issue type"]:
            errors.append(f"issue type mismatch for {local_id}")
        if fields["description"].get("type") != "doc" or fields["description"].get("version") != 1:
            errors.append(f"invalid ADF description for {local_id}")
        expected_parent = ""
        if row["Parent"]:
            expected_parent = "{{JIRA_KEY:" + import_to_local[row["Parent"]] + "}}"
        actual_parent = fields.get("parent", {}).get("key", "")
        if actual_parent != expected_parent:
            errors.append(f"parent template mismatch for {local_id}")
    for row, template in zip(links, link_payloads):
        if template["source_local_id"] != row["source_local_id"] or template["target_local_id"] != row["target_local_id"]:
            errors.append(f"link template mismatch: {row}")
        if row["source_local_id"] not in local_ids or row["target_local_id"] not in local_ids:
            errors.append(f"link endpoint is not a known Local Issue ID: {row}")
        if row["target_link_type_name"] not in {"Blocks", "Relates"}:
            errors.append(f"unsupported link type: {row}")
    if errors:
        raise RuntimeError("Local import preflight failed: " + "; ".join(errors[:30]))
    return {
        "result": "PASS",
        "issues": len(rows),
        "links": len(links),
        "parents": sum(bool(row["Parent"]) for row in rows),
        "source_hashes": {str(path.relative_to(ROOT)): sha256_file(path) for path in SOURCE_FILES},
    }


def search_issues(client: JiraClient, fields: list[str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    token = ""
    while True:
        query = {
            "jql": f"project = {PROJECT_KEY} ORDER BY key ASC",
            "maxResults": "100",
            "fields": ",".join(fields),
        }
        if token:
            query["nextPageToken"] = token
        result = client.get("/rest/api/3/search/jql?" + urllib.parse.urlencode(query))
        issues.extend(result.get("issues", []))
        token = result.get("nextPageToken", "")
        if result.get("isLast", not token) or not token:
            break
    return issues


def paged_values(client: JiraClient, path: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    start = 0
    separator = "&" if "?" in path else "?"
    while True:
        result = client.get(f"{path}{separator}startAt={start}&maxResults=100")
        batch = result.get("values", [])
        values.extend(batch)
        if result.get("isLast", True) or not batch:
            break
        start += len(batch)
    return values


def make_backup(client: JiraClient, ledger: dict[str, Any], preflight: dict[str, Any]) -> None:
    existing = ledger.get("backup", {})
    if existing:
        path = ROOT / existing["path"]
        if not path.exists() or sha256_file(path) != existing["sha256"]:
            raise RuntimeError("Existing pre-import backup is missing or failed SHA-256 verification")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = JIRA_ROOT / "snapshots" / f"BAT_PRE_IMPORT_{stamp}.json"
    all_fields = paged_values(client, "/rest/api/3/field/search?type=custom")
    field_names = {spec["name"] for spec in FIELD_SPECS}
    snapshot = {
        "schema_version": 1,
        "captured_at": utc_now(),
        "project": client.get(f"/rest/api/3/project/{PROJECT_KEY}?expand=description,lead,issueTypes,projectKeys"),
        "components": client.get(f"/rest/api/3/project/{PROJECT_KEY}/components"),
        "target_named_custom_fields": [field for field in all_fields if field.get("name") in field_names],
        "issue_link_types": client.get("/rest/api/3/issueLinkType"),
        "priorities": client.get("/rest/api/3/priority"),
        "statuses": client.get(f"/rest/api/3/project/{PROJECT_KEY}/statuses"),
        "issues": search_issues(client, ["summary", "status", "issuetype", "parent", "labels"]),
        "board": client.get(f"/rest/agile/1.0/board/{BOARD_ID}/configuration"),
        "board_filter": client.get(f"/rest/api/3/filter/{BOARD_FILTER_ID}"),
        "source_preflight": preflight,
        "rollback": {
            "scope": "BAT project, board filter, project components, created custom fields, saved filters, issues, transitions, and links",
            "note": "The destination was empty at capture. The exact created object IDs/keys are recorded in BAT_LIVE_IMPORT_LEDGER.json.",
        },
    }
    write_json_atomic(path, snapshot)
    digest = sha256_file(path)
    if json.loads(path.read_text(encoding="utf-8")) != snapshot or sha256_file(path) != digest:
        raise RuntimeError("Pre-import backup reread/hash verification failed")
    ledger["backup"] = {"path": str(path.relative_to(ROOT)), "sha256": digest, "verified": True}
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    print(f"BACKUP VERIFIED: {path.relative_to(ROOT)} sha256={digest}", flush=True)


def ensure_components(client: JiraClient, ledger: dict[str, Any]) -> dict[str, str]:
    with COMPONENTS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        specs = list(csv.DictReader(handle))
    existing = {item["name"]: item for item in client.get(f"/rest/api/3/project/{PROJECT_KEY}/components")}
    mapping: dict[str, str] = {}
    for spec in specs:
        name = spec["component_name"]
        item = existing.get(name)
        if item is None:
            item = client.post(
                "/rest/api/3/component",
                {
                    "name": name,
                    "description": spec["description"],
                    "project": PROJECT_KEY,
                    "assigneeType": "PROJECT_DEFAULT",
                },
            )
            existing[name] = item
            print(f"COMPONENT CREATED: {name} ({item['id']})", flush=True)
        mapping[name] = str(item["id"])
    ledger["components"] = mapping
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    return mapping


def ensure_fields(client: JiraClient, ledger: dict[str, Any]) -> dict[str, str]:
    all_fields = paged_values(client, "/rest/api/3/field/search?type=custom")
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in all_fields:
        by_name.setdefault(item.get("name", ""), []).append(item)
    mapping: dict[str, str] = {}
    for spec in FIELD_SPECS:
        matches = by_name.get(spec["name"], [])
        if len(matches) > 1:
            raise RuntimeError(f"Multiple custom fields named {spec['name']!r}; refusing ambiguous mapping")
        expected_type = (
            "com.atlassian.jira.plugin.system.customfieldtypes:textfield"
            if spec["kind"] == "text"
            else "com.atlassian.jira.plugin.system.customfieldtypes:select"
        )
        if matches:
            item = matches[0]
            actual_type = item.get("schema", {}).get("custom", "")
            if actual_type != expected_type:
                raise RuntimeError(f"Custom field {spec['name']} has type {actual_type}, expected {expected_type}")
        else:
            searcher = (
                "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher"
                if spec["kind"] == "text"
                else "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher"
            )
            item = client.post(
                "/rest/api/3/field",
                {
                    "name": spec["name"],
                    "description": spec["description"],
                    "type": expected_type,
                    "searcherKey": searcher,
                },
            )
            print(f"CUSTOM FIELD CREATED: {spec['name']} ({item['id']})", flush=True)
        field_id = str(item["id"])
        mapping[spec["name"]] = field_id
        if spec["kind"] == "select":
            contexts = paged_values(client, f"/rest/api/3/field/{field_id}/context")
            if not contexts:
                raise RuntimeError(f"No custom field context was created for {spec['name']}")
            context = next((value for value in contexts if value.get("isGlobalContext")), contexts[0])
            context_id = str(context["id"])
            options = paged_values(client, f"/rest/api/3/field/{field_id}/context/{context_id}/option")
            current = {option.get("value") for option in options}
            missing = [value for value in spec["options"] if value not in current]
            if missing:
                client.post(
                    f"/rest/api/3/field/{field_id}/context/{context_id}/option",
                    {"options": [{"value": value} for value in missing]},
                )
                print(f"CUSTOM FIELD OPTIONS ADDED: {spec['name']} ({len(missing)})", flush=True)
        try:
            client.post(f"/rest/api/3/screens/addToDefault/{field_id}", {})
            print(f"CUSTOM FIELD ADDED TO DEFAULT SCREEN: {spec['name']}", flush=True)
        except JiraError as exc:
            lower = exc.body.lower()
            if "already" not in lower and "exists" not in lower:
                raise
    screens = paged_values(client, "/rest/api/3/screens?queryString=BAT")
    if not screens:
        raise RuntimeError("No BAT project screens were discoverable for custom-field attachment")
    attached: dict[str, list[str]] = {}
    for screen in screens:
        screen_id = str(screen["id"])
        tabs = client.get(f"/rest/api/3/screens/{screen_id}/tabs")
        if not tabs:
            raise RuntimeError(f"BAT screen {screen_id} has no tabs")
        tab_id = str(tabs[0]["id"])
        current_fields = client.get(
            f"/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields?projectKey={PROJECT_KEY}"
        )
        current_ids = {field["id"] for field in current_fields}
        for field_name, field_id in mapping.items():
            if field_id not in current_ids:
                client.post(
                    f"/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields",
                    {"fieldId": field_id},
                )
            attached.setdefault(field_name, []).append(screen_id)
    ledger["custom_field_screens"] = attached
    print(f"CUSTOM FIELDS ATTACHED TO BAT SCREENS: fields={len(mapping)} screens={len(screens)}", flush=True)
    ledger["custom_fields"] = mapping
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    return mapping


def custom_value(field_name: str, value: str) -> Any:
    spec = next(item for item in FIELD_SPECS if item["name"] == field_name)
    return value if spec["kind"] == "text" else {"value": value}


def map_existing_issues(
    client: JiraClient,
    local_field_id: str,
    allowed_ids: set[str],
    fields: list[str] | None = None,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    wanted = fields or ["summary", "status", "issuetype", "parent", local_field_id]
    issues = search_issues(client, wanted)
    mapping: dict[str, str] = {}
    unknown: list[str] = []
    auxiliary = load_auxiliary_issues()
    for issue in issues:
        raw = issue.get("fields", {}).get(local_field_id)
        local_id = raw.strip() if isinstance(raw, str) else ""
        if not local_id:
            match = re.match(r"^\[([A-Z]+(?:-[A-Z]+)*-\d{3})\]", issue.get("fields", {}).get("summary", ""))
            local_id = match.group(1) if match else ""
        auxiliary_item = auxiliary.get(issue.get("key", ""))
        if auxiliary_item is not None:
            if local_id and local_id != auxiliary_item["local_id"]:
                raise RuntimeError(f"Auxiliary Jira issue {issue['key']} has an unexpected Local Issue ID")
            if issue.get("fields", {}).get("summary") != auxiliary_item["summary"]:
                raise RuntimeError(f"Auxiliary Jira issue {issue['key']} has an unexpected summary")
            continue
        if local_id not in allowed_ids:
            unknown.append(f"{issue.get('key')}:{local_id or 'NO_LOCAL_ID'}")
            continue
        if local_id in mapping and mapping[local_id] != issue["key"]:
            raise RuntimeError(f"Duplicate Jira issues claim Local Issue ID {local_id}")
        mapping[local_id] = issue["key"]
    if unknown:
        raise RuntimeError("BAT contains issues outside the canonical import set: " + ", ".join(unknown[:30]))
    return mapping, issues


def reconcile_auxiliary_issues(
    client: JiraClient,
    ledger: dict[str, Any],
    field_ids: dict[str, str],
) -> None:
    reconciled: list[dict[str, Any]] = []
    for key, item in sorted(load_auxiliary_issues().items()):
        issue = client.get(
            f"/rest/api/3/issue/{key}?fields=summary,status,issuetype,{','.join(field_ids.values())}"
        )
        fields = issue.get("fields", {})
        if fields.get("summary") != item["summary"]:
            raise RuntimeError(f"Auxiliary Jira issue {key} summary drifted")
        if fields.get("issuetype", {}).get("name") != item["issue_type"]:
            raise RuntimeError(f"Auxiliary Jira issue {key} type drifted")
        if fields.get("status", {}).get("name") != item["status"]:
            raise RuntimeError(f"Auxiliary Jira issue {key} status drifted")
        desired = {
            "Local Issue ID": item["local_id"],
            "Logical Workflow State": item["logical_state"],
            "Implementation Maturity": item["maturity"],
            "Evidence State": item["evidence_state"],
            "Owner Historical Wave": item["owner_wave"],
            "Phase": item["phase"],
            "Critical Path": str(item["critical_path"]).lower(),
            "Execution Lane": item["execution_lane"],
        }
        updates: dict[str, Any] = {}
        for name, value in desired.items():
            field_id = field_ids[name]
            if normalize_custom(fields.get(field_id)) != value:
                updates[field_id] = custom_value(name, value)
        if updates:
            client.put(f"/rest/api/3/issue/{key}", {"fields": updates})
        reconciled.append(
            {
                "jira_key": key,
                "local_id": item["local_id"],
                "updated_fields": sorted(updates),
                "verified_at": utc_now(),
            }
        )
    ledger["auxiliary_issue_reconciliation"] = reconciled
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)


def remove_exact_importer_duplicates(
    client: JiraClient,
    ledger: dict[str, Any],
    rows: list[dict[str, str]],
    local_field_id: str,
) -> None:
    backup_path = ROOT / ledger.get("backup", {}).get("path", "")
    if not backup_path.exists():
        raise RuntimeError("Cannot assess duplicate-removal safety without the verified pre-import backup")
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    if backup.get("issues"):
        raise RuntimeError("Pre-import BAT was not empty; automated importer-duplicate removal is not authorized")
    allowed = {row["Local Issue ID"] for row in rows}
    issues = search_issues(
        client,
        [
            "summary", "description", "status", "issuetype", "parent", "components", "priority",
            "labels", "subtasks", "issuelinks", "created", local_field_id,
        ],
    )
    groups: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        local_id = issue.get("fields", {}).get(local_field_id, "")
        if local_id:
            groups.setdefault(local_id, []).append(issue)
    duplicate_groups = {local_id: values for local_id, values in groups.items() if len(values) > 1}
    if not duplicate_groups:
        return
    removals: list[dict[str, str]] = []
    for local_id, values in sorted(duplicate_groups.items()):
        if local_id not in allowed:
            raise RuntimeError(f"Duplicate Local Issue ID is outside canonical set: {local_id}")
        ordered = sorted(values, key=lambda issue: (issue["fields"].get("created", ""), int(issue["id"])))
        keep = ordered[0]
        comparable = [
            "summary", "description", "status", "issuetype", "parent", "components", "priority", "labels",
        ]
        for extra in ordered[1:]:
            if any(extra["fields"].get(name) != keep["fields"].get(name) for name in comparable):
                raise RuntimeError(f"Duplicate candidates for {local_id} are not field-identical; refusing deletion")
            if extra["fields"].get("subtasks") or extra["fields"].get("issuelinks"):
                raise RuntimeError(f"Duplicate candidate {extra['key']} has children or links; refusing deletion")
            removals.append({"local_id": local_id, "kept": keep["key"], "deleted": extra["key"]})
    temporary_grant_id = ensure_temporary_delete_permission(client, ledger)
    deletion_error: Exception | None = None
    try:
        if temporary_grant_id == "quarantine":
            move_exact_duplicates_to_quarantine(client, ledger, removals)
        else:
            for item in removals:
                client.delete(f"/rest/api/3/issue/{item['deleted']}?deleteSubtasks=true")
                print(f"DUPLICATE REMOVED: {item['deleted']} kept={item['kept']} local_id={item['local_id']}", flush=True)
    except Exception as exc:
        deletion_error = exc
        raise
    finally:
        if temporary_grant_id is not None and temporary_grant_id != "quarantine":
            try:
                revoke_temporary_delete_permission(client, ledger, temporary_grant_id)
            except Exception:
                if deletion_error is None:
                    raise
    ledger.setdefault("duplicate_remediation", []).extend(removals)
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    for _ in range(30):
        remaining = search_issues(client, [local_field_id, "summary"])
        counts: dict[str, int] = {}
        for issue in remaining:
            value = issue.get("fields", {}).get(local_field_id, "")
            if value:
                counts[value] = counts.get(value, 0) + 1
        if all(count == 1 for count in counts.values()):
            return
        time.sleep(2)
    raise RuntimeError("Jira search index did not settle after exact duplicate remediation")


def has_delete_permission(client: JiraClient) -> bool:
    result = client.get(
        f"/rest/api/3/mypermissions?projectKey={PROJECT_KEY}&permissions=DELETE_ISSUES"
    )
    return bool(result.get("permissions", {}).get("DELETE_ISSUES", {}).get("havePermission"))


def ensure_temporary_delete_permission(client: JiraClient, ledger: dict[str, Any]) -> str | None:
    if has_delete_permission(client):
        return None
    user = client.get("/rest/api/3/myself")
    scheme = client.get(f"/rest/api/3/project/{PROJECT_KEY}/permissionscheme?expand=permissions")
    account_id = user["accountId"]
    for grant in scheme.get("permissions", []):
        holder = grant.get("holder", {})
        if (
            grant.get("permission") == "DELETE_ISSUES"
            and holder.get("type") == "user"
            and holder.get("parameter") == account_id
        ):
            raise RuntimeError("A direct DELETE_ISSUES grant exists but is ineffective; refusing to alter it")

    projects = client.get("/rest/api/3/project/search?maxResults=100")
    bound_projects = []
    for project in projects.get("values", []):
        try:
            project_scheme = client.get(f"/rest/api/3/project/{project['key']}/permissionscheme")
        except JiraError:
            continue
        if str(project_scheme.get("id")) == str(scheme.get("id")):
            bound_projects.append({"key": project["key"], "name": project["name"]})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = JIRA_ROOT / "snapshots" / f"BAT_PERMISSION_SCHEME_PRE_REMEDIATION_{stamp}.json"
    snapshot = {
        "schema_version": 1,
        "captured_at": utc_now(),
        "reason": "Temporary user-only DELETE_ISSUES grant required to remove verified exact importer duplicates.",
        "authenticated_user": {
            "accountId": account_id,
            "displayName": user.get("displayName"),
            "emailAddress": user.get("emailAddress"),
        },
        "permission_scheme": scheme,
        "projects_using_scheme": bound_projects,
        "preexisting_delete_permission": False,
    }
    write_json_atomic(snapshot_path, snapshot)
    digest = sha256_file(snapshot_path)
    if json.loads(snapshot_path.read_text(encoding="utf-8")) != snapshot or sha256_file(snapshot_path) != digest:
        raise RuntimeError("Permission-scheme backup reread/hash verification failed")
    ledger["permission_remediation"] = {
        "status": "BACKUP_VERIFIED",
        "backup": {"path": str(snapshot_path.relative_to(ROOT)), "sha256": digest},
        "account_id": account_id,
        "scheme_id": str(scheme["id"]),
        "projects_using_scheme": bound_projects,
    }
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)

    try:
        grant = client.post(
            f"/rest/api/3/permissionscheme/{scheme['id']}/permission",
            {
                "holder": {"type": "user", "parameter": account_id},
                "permission": "DELETE_ISSUES",
            },
        )
        grant_id = f"scheme:{grant['id']}"
        remediation_route = "TEMPORARY_USER_PERMISSION_GRANT"
    except JiraError as exc:
        if exc.status != 403 or "free plan" not in exc.body.lower():
            raise
        delete_role_ids = {
            str(grant.get("holder", {}).get("parameter"))
            for grant in scheme.get("permissions", [])
            if grant.get("permission") == "DELETE_ISSUES"
            and grant.get("holder", {}).get("type") == "projectRole"
        }
        roles = client.get(f"/rest/api/3/project/{PROJECT_KEY}/role")
        administrator_url = roles.get("Administrators")
        if not administrator_url:
            raise RuntimeError("BAT has no Administrators project role for scoped duplicate remediation") from exc
        administrator_role = client.get(administrator_url.replace(BASE_URL, ""))
        role_id = str(administrator_role["id"])
        if role_id not in delete_role_ids:
            raise RuntimeError("BAT Administrators role is not an existing DELETE_ISSUES holder") from exc
        if any(
            actor.get("actorUser", {}).get("accountId") == account_id
            for actor in administrator_role.get("actors", [])
        ):
            raise RuntimeError("Authenticated user is already in Administrators role but lacks delete permission") from exc
        role_snapshot_path = (
            JIRA_ROOT / "snapshots" / f"BAT_ADMIN_ROLE_PRE_REMEDIATION_{stamp}.json"
        )
        role_snapshot = {
            "schema_version": 1,
            "captured_at": utc_now(),
            "reason": "Jira Free blocks permission-scheme edits; use BAT-project-scoped role membership only.",
            "project": PROJECT_KEY,
            "role": administrator_role,
            "authenticated_user_account_id": account_id,
        }
        write_json_atomic(role_snapshot_path, role_snapshot)
        role_digest = sha256_file(role_snapshot_path)
        if (
            json.loads(role_snapshot_path.read_text(encoding="utf-8")) != role_snapshot
            or sha256_file(role_snapshot_path) != role_digest
        ):
            raise RuntimeError("Project-role backup reread/hash verification failed")
        ledger["permission_remediation"].update(
            {
                "permission_scheme_route": "BLOCKED_BY_JIRA_FREE_PLAN_NO_CHANGE",
                "project_role_backup": {
                    "path": str(role_snapshot_path.relative_to(ROOT)),
                    "sha256": role_digest,
                },
            }
        )
        ledger["updated_at"] = utc_now()
        write_json_atomic(LEDGER_PATH, ledger)
        try:
            client.post(
                f"/rest/api/3/project/{PROJECT_KEY}/role/{role_id}",
                {"user": [account_id]},
            )
            grant_id = f"role:{role_id}"
            remediation_route = "TEMPORARY_BAT_ADMINISTRATORS_ROLE"
        except JiraError as role_exc:
            if role_exc.status not in {400, 403} or "free plan" not in role_exc.body.lower():
                raise
            ledger["permission_remediation"].update(
                {
                    "status": "JIRA_FREE_PERMISSION_PATHS_BLOCKED",
                    "project_role_route": "BLOCKED_BY_JIRA_FREE_PLAN_NO_CHANGE",
                    "route": "MOVE_EXACT_DUPLICATES_TO_QUARANTINE_PROJECT",
                }
            )
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
            return "quarantine"
    ledger["permission_remediation"].update(
        {
            "status": "TEMPORARY_GRANT_ACTIVE",
            "route": remediation_route,
            "temporary_grant_id": grant_id,
            "granted_at": utc_now(),
        }
    )
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    for _ in range(30):
        if has_delete_permission(client):
            print(f"TEMPORARY DELETE PERMISSION ACTIVE: grant={grant_id}", flush=True)
            return grant_id
        time.sleep(1)
    raise RuntimeError("Temporary DELETE_ISSUES grant did not become effective")


def revoke_temporary_delete_permission(
    client: JiraClient, ledger: dict[str, Any], grant_id: str
) -> None:
    grant_kind, object_id = grant_id.split(":", 1)
    if grant_kind == "scheme":
        scheme_id = ledger["permission_remediation"]["scheme_id"]
        client.delete(f"/rest/api/3/permissionscheme/{scheme_id}/permission/{object_id}")
    elif grant_kind == "role":
        account_id = ledger["permission_remediation"]["account_id"]
        client.delete(
            f"/rest/api/3/project/{PROJECT_KEY}/role/{object_id}?user="
            + urllib.parse.quote(account_id)
        )
    else:
        raise RuntimeError(f"Unknown temporary grant kind: {grant_kind}")
    for _ in range(30):
        if not has_delete_permission(client):
            ledger["permission_remediation"].update(
                {"status": "RESTORED", "revoked_at": utc_now(), "verified_no_delete_permission": True}
            )
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
            print(f"TEMPORARY DELETE PERMISSION REVOKED: grant={grant_id}", flush=True)
            return
        time.sleep(1)
    raise RuntimeError("Temporary DELETE_ISSUES grant was removed but permission restoration could not be verified")


def move_exact_duplicates_to_quarantine(
    client: JiraClient, ledger: dict[str, Any], removals: list[dict[str, str]]
) -> None:
    quarantine_key = "BATQ"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        project = client.get(f"/rest/api/3/project/{quarantine_key}?expand=issueTypes")
    except JiraError as exc:
        if exc.status != 404:
            raise
        projects_before = client.get("/rest/api/3/project/search?maxResults=100")
        project_snapshot_path = (
            JIRA_ROOT / "snapshots" / f"BAT_QUARANTINE_PROJECT_PRE_CREATE_{stamp}.json"
        )
        project_snapshot = {
            "schema_version": 1,
            "captured_at": utc_now(),
            "reason": "Create isolated project for exact importer duplicates because Jira Free blocks deletion grants.",
            "projects_before": projects_before,
            "quarantine_project_key": quarantine_key,
        }
        write_json_atomic(project_snapshot_path, project_snapshot)
        digest = sha256_file(project_snapshot_path)
        if (
            json.loads(project_snapshot_path.read_text(encoding="utf-8")) != project_snapshot
            or sha256_file(project_snapshot_path) != digest
        ):
            raise RuntimeError("Quarantine-project backup reread/hash verification failed")
        user = client.get("/rest/api/3/myself")
        project = client.post(
            "/rest/api/3/project",
            {
                "key": quarantine_key,
                "name": "BAT Import Quarantine",
                "description": (
                    "Non-operational quarantine for exact duplicate issues created by a timed-out "
                    "BAT bulk-import request. Excluded from the BAT board and canonical delivery."
                ),
                "leadAccountId": user["accountId"],
                "projectTypeKey": "software",
                "projectTemplateKey": "com.pyxis.greenhopper.jira:gh-scrum-template",
                "assigneeType": "PROJECT_LEAD",
            },
        )
        ledger.setdefault("duplicate_quarantine", {}).update(
            {
                "project_created": True,
                "project_key": quarantine_key,
                "project_id": str(project["id"]),
                "pre_create_backup": {
                    "path": str(project_snapshot_path.relative_to(ROOT)),
                    "sha256": digest,
                },
            }
        )
        ledger["updated_at"] = utc_now()
        write_json_atomic(LEDGER_PATH, ledger)
        project = client.get(f"/rest/api/3/project/{quarantine_key}?expand=issueTypes")

    task_types = [item for item in project.get("issueTypes", []) if item.get("name") == "Task"]
    if len(task_types) != 1:
        raise RuntimeError(f"Quarantine project Task type is ambiguous: {task_types}")
    move_keys = [item["deleted"] for item in removals]
    target_key = f"{project['id']},{task_types[0]['id']}"
    move_response = client.post(
        "/rest/api/3/bulk/issues/move",
        {
            "sendBulkNotification": False,
            "targetToSourcesMapping": {
                target_key: {
                    "issueIdsOrKeys": move_keys,
                    "inferClassificationDefaults": True,
                    "inferFieldDefaults": True,
                    "inferStatusDefaults": True,
                    "inferSubtaskTypeDefault": True,
                }
            },
        },
    )
    task_id = str(move_response.get("taskId", ""))
    if not task_id:
        raise RuntimeError(f"Bulk move did not return a taskId: {move_response}")
    for _ in range(120):
        task = client.get(f"/rest/api/3/task/{task_id}")
        status = str(task.get("status", "")).upper()
        if status in {"COMPLETE", "SUCCESS", "COMPLETED"}:
            break
        if status in {"FAILED", "CANCELLED"}:
            raise RuntimeError(f"Bulk duplicate-quarantine move failed: {task}")
        time.sleep(2)
    else:
        raise RuntimeError(f"Bulk duplicate-quarantine move did not complete: task={task_id}")

    for _ in range(60):
        bat_keys = {issue["key"] for issue in search_issues(client, ["summary"])}
        if not any(key in bat_keys for key in move_keys):
            ledger.setdefault("duplicate_quarantine", {}).update(
                {
                    "status": "COMPLETE_VERIFIED",
                    "moved_count": len(move_keys),
                    "source_keys": move_keys,
                    "bulk_task_id": task_id,
                    "verified_at": utc_now(),
                }
            )
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
            for item in removals:
                print(
                    f"DUPLICATE QUARANTINED: {item['deleted']} kept={item['kept']} local_id={item['local_id']}",
                    flush=True,
                )
            return
        time.sleep(2)
    raise RuntimeError("Jira search index did not settle after duplicate quarantine move")


def chunks(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def create_issues(
    client: JiraClient,
    ledger: dict[str, Any],
    rows: list[dict[str, str]],
    payloads: list[dict[str, Any]],
    field_ids: dict[str, str],
    component_ids: dict[str, str],
) -> dict[str, str]:
    row_by_id = {row["Local Issue ID"]: row for row in rows}
    payload_by_id = {item["local_id"]: item for item in payloads}
    completion_policy = load_completion_policy()
    completion_override_ids = set(completion_policy.get("local_issue_ids", []))
    completion_override = completion_policy.get("jira_operational_override", {})
    allowed = set(row_by_id)
    key_map, _ = map_existing_issues(client, field_ids["Local Issue ID"], allowed)
    stage_types = [("EPICS", {"Epic"}), ("STORIES_TASKS", {"Story", "Task"}), ("SUBTASKS", {"Sub-task"})]
    for stage_name, issue_types in stage_types:
        pending = [row for row in rows if row["Issue type"] in issue_types and row["Local Issue ID"] not in key_map]
        for batch_number, batch in enumerate(chunks(pending, 50), start=1):
            issue_updates: list[dict[str, Any]] = []
            batch_ids: list[str] = []
            for row in batch:
                local_id = row["Local Issue ID"]
                template = payload_by_id[local_id]
                fields = copy.deepcopy(template["payload_template"]["fields"])
                fields["project"] = {"key": PROJECT_KEY}
                parent = fields.get("parent")
                if parent:
                    parent_local = parent["key"].removeprefix("{{JIRA_KEY:").removesuffix("}}")
                    if parent_local not in key_map:
                        raise RuntimeError(f"Parent {parent_local} for {local_id} has not been created")
                    fields["parent"] = {"key": key_map[parent_local]}
                fields["priority"] = {"name": row["Priority"]}
                fields["components"] = [{"id": component_ids[row["Component"]]}]
                if local_id in completion_override_ids:
                    fields["labels"] = sorted(
                        set(fields.get("labels", [])) | set(completion_override.get("add_labels", []))
                    )
                logical = template["logical_fields_requiring_target_custom_field_ids"]
                for field_name, field_id in field_ids.items():
                    source_name = field_name
                    value = logical.get(source_name, row.get(source_name, ""))
                    if not value and field_name == "Owner Historical Wave":
                        value = row["Owner Historical Wave"]
                    if field_name == "Critical Path":
                        value = row["Critical Path"].lower()
                    if field_name == "Evidence State" and local_id in completion_override_ids:
                        value = completion_override.get("evidence_state", "PARTIAL")
                    fields[field_id] = custom_value(field_name, str(value))
                issue_updates.append(
                    {
                        "fields": fields,
                        "properties": [
                            {
                                "key": "bat.local.identity",
                                "value": {
                                    "local_id": local_id,
                                    "import_id": row["Issue ID"],
                                    "source": "C:\\BatteredAggieSyndrome\\jira",
                                    "schema": "BAS_JIRA_V2",
                                },
                            }
                        ],
                    }
                )
                batch_ids.append(local_id)
            result = client.post("/rest/api/3/issue/bulk", {"issueUpdates": issue_updates}) or {}
            missing = list(batch_ids)
            for _ in range(30):
                key_map, _ = map_existing_issues(client, field_ids["Local Issue ID"], allowed)
                missing = [local_id for local_id in batch_ids if local_id not in key_map]
                if not missing:
                    break
                time.sleep(2)
            if missing:
                raise RuntimeError(
                    f"Bulk create stage {stage_name} batch {batch_number} left issues missing: {missing}; errors={result.get('errors')}"
                )
            ledger["issues"] = key_map
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
            print(
                f"ISSUE BATCH CREATED: stage={stage_name} batch={batch_number} batch_size={len(batch)} total={len(key_map)}/{len(rows)}",
                flush=True,
            )
    if len(key_map) != len(rows):
        raise RuntimeError(f"Expected {len(rows)} mapped Jira issues after creation, got {len(key_map)}")
    return key_map


def synchronize_canonical_spec_fields(
    client: JiraClient,
    ledger: dict[str, Any],
    rows: list[dict[str, str]],
    payloads: list[dict[str, Any]],
    key_map: dict[str, str],
    field_ids: dict[str, str],
    component_ids: dict[str, str],
) -> None:
    completion_policy = load_completion_policy()
    completion_override_ids = set(completion_policy.get("local_issue_ids", []))
    completion_override = completion_policy.get("jira_operational_override", {})
    requested = [
        "summary", "description", "labels", "components", "priority", "updated", *field_ids.values()
    ]
    live = {issue["key"]: issue for issue in search_issues(client, requested)}
    payload_by_id = {item["local_id"]: item for item in payloads}
    pending: list[dict[str, Any]] = []
    backup_issues: list[dict[str, Any]] = []
    for row in rows:
        local_id = row["Local Issue ID"]
        key = key_map[local_id]
        fields = live[key]["fields"]
        template = payload_by_id[local_id]
        expected = template["payload_template"]["fields"]
        updates: dict[str, Any] = {}
        if fields.get("summary") != row["Summary"]:
            updates["summary"] = row["Summary"]
        if fields.get("description") != expected["description"]:
            updates["description"] = expected["description"]
        expected_labels = set(expected.get("labels", []))
        if local_id in completion_override_ids:
            expected_labels |= set(completion_override.get("add_labels", []))
        if set(fields.get("labels", [])) != expected_labels:
            updates["labels"] = sorted(expected_labels)
        if fields.get("priority", {}).get("name") != row["Priority"]:
            updates["priority"] = {"name": row["Priority"]}
        if {item["name"] for item in fields.get("components", [])} != {row["Component"]}:
            updates["components"] = [{"id": component_ids[row["Component"]]}]
        logical = template["logical_fields_requiring_target_custom_field_ids"]
        for field_name, field_id in field_ids.items():
            value = logical.get(field_name, row.get(field_name, ""))
            if not value and field_name == "Owner Historical Wave":
                value = row["Owner Historical Wave"]
            if field_name == "Critical Path":
                value = row["Critical Path"].lower()
            if field_name == "Evidence State" and local_id in completion_override_ids:
                value = completion_override.get("evidence_state", "PARTIAL")
            value = str(value)
            if normalize_custom(fields.get(field_id)) != value:
                updates[field_id] = custom_value(field_name, value)
        if updates:
            pending.append({"key": key, "local_id": local_id, "fields": updates})
            backup_issues.append(
                {
                    "key": key,
                    "local_id": local_id,
                    "updated": fields.get("updated"),
                    "fields": {name: fields.get(name) for name in updates},
                }
            )
    if not pending:
        ledger["canonical_spec_sync"] = {
            "status": "EXACT_NO_UPDATES_REQUIRED",
            "changed_issues": 0,
            "verified_at": utc_now(),
        }
        ledger["updated_at"] = utc_now()
        write_json_atomic(LEDGER_PATH, ledger)
        return
    policy = json.loads((ROOT / "configs" / "external_storage_policy.json").read_text(encoding="utf-8"))
    data_root = Path(policy["current_host_data_root_windows"]).resolve()
    try:
        data_root.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError("Canonical Jira sync backup root must remain outside Git")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = data_root / "reconciliation" / "jira" / "canonical-spec-sync" / stamp / "pre-update.json"
    snapshot = {
        "schema_version": 1,
        "captured_at": utc_now(),
        "reason": "Transactional backup before synchronizing current canonical Jira specification fields to live BAT.",
        "issue_count": len(backup_issues),
        "issues": backup_issues,
    }
    write_json_atomic(backup_path, snapshot)
    digest = sha256_file(backup_path)
    if json.loads(backup_path.read_text(encoding="utf-8")) != snapshot or sha256_file(backup_path) != digest:
        raise RuntimeError("Canonical Jira sync backup reread/hash verification failed")
    progress = {
        "status": "IN_PROGRESS",
        "backup": {
            "path": str(backup_path.relative_to(data_root)).replace("\\", "/"),
            "sha256": digest,
            "bytes": backup_path.stat().st_size,
            "issue_count": len(backup_issues),
            "storage_root": "EXTERNAL_DATA_ROOT",
        },
        "completed_local_ids": [],
        "started_at": utc_now(),
    }
    ledger["canonical_spec_sync"] = progress
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    completed: set[str] = set()
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(client.put, f"/rest/api/3/issue/{item['key']}", {"fields": item["fields"]}): item
            for item in pending
        }
        for index, future in enumerate(as_completed(futures), start=1):
            item = futures[future]
            try:
                future.result()
                completed.add(item["local_id"])
            except Exception as exc:
                errors.append(f"{item['local_id']}: {exc}")
            if index % 25 == 0 or index == len(pending):
                progress["completed_local_ids"] = sorted(completed)
                progress["errors"] = errors
                ledger["updated_at"] = utc_now()
                write_json_atomic(LEDGER_PATH, ledger)
                print(
                    f"CANONICAL SPEC SYNC: processed={index}/{len(pending)} completed={len(completed)} errors={len(errors)}",
                    flush=True,
                )
    if errors:
        raise RuntimeError("Canonical Jira spec synchronization failures: " + "; ".join(errors[:20]))
    progress.update({"status": "COMPLETE", "changed_issues": len(completed), "completed_at": utc_now()})
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)


def transition_declared_active_statuses(
    client: JiraClient,
    rows: list[dict[str, str]],
    key_map: dict[str, str],
) -> None:
    active_rows = [row for row in rows if row["Status"] not in {"To Do", "Done"}]
    for row in active_rows:
        key = key_map[row["Local Issue ID"]]
        issue = client.get(f"/rest/api/3/issue/{key}?fields=status")
        if issue["fields"]["status"]["name"] == row["Status"]:
            continue
        transitions = client.get(f"/rest/api/3/issue/{key}/transitions").get("transitions", [])
        transition = next((item for item in transitions if item.get("to", {}).get("name") == row["Status"]), None)
        if transition is None:
            raise RuntimeError(f"No transition to {row['Status']} is available for {key}")
        client.post(f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": str(transition["id"])}})


def poll_bulk_task(client: JiraClient, task_id: str) -> None:
    for _ in range(240):
        result = client.get(f"/rest/api/3/bulk/queue/{urllib.parse.quote(task_id)}")
        status = str(result.get("status", "")).upper()
        if status in {"COMPLETE", "COMPLETED", "SUCCESS", "SUCCESSFUL"}:
            return
        if status in {"FAILED", "CANCELLED", "CANCELED"}:
            raise RuntimeError(f"Bulk Jira task {task_id} failed: {result}")
        time.sleep(2)
    raise RuntimeError(f"Bulk Jira task {task_id} did not finish within the polling window")


def transition_historical_done(
    client: JiraClient,
    ledger: dict[str, Any],
    rows: list[dict[str, str]],
    key_map: dict[str, str],
    local_field_id: str,
) -> None:
    completion_override_ids = set(load_completion_policy().get("local_issue_ids", []))
    allowed = {row["Local Issue ID"] for row in rows}
    _, issues = map_existing_issues(
        client,
        local_field_id,
        allowed,
        ["summary", "status", "issuetype", local_field_id],
    )
    live_by_key = {issue["key"]: issue for issue in issues}
    done_rows = [
        row
        for row in rows
        if row["Status"] == "Done" and row["Local Issue ID"] not in completion_override_ids
    ]
    groups: dict[str, list[str]] = {}
    representative: dict[str, str] = {}
    for row in done_rows:
        key = key_map[row["Local Issue ID"]]
        if live_by_key[key]["fields"]["status"]["name"] == "Done":
            continue
        representative.setdefault(row["Issue type"], key)
    transition_by_type: dict[str, str] = {}
    for issue_type, key in representative.items():
        result = client.get(f"/rest/api/3/issue/{key}/transitions")
        transition = next((item for item in result.get("transitions", []) if item.get("to", {}).get("name") == "Done"), None)
        if transition is None:
            raise RuntimeError(f"No direct Done transition is available for {issue_type} representative {key}")
        transition_by_type[issue_type] = str(transition["id"])
    for row in done_rows:
        key = key_map[row["Local Issue ID"]]
        if live_by_key[key]["fields"]["status"]["name"] == "Done":
            continue
        transition_id = transition_by_type[row["Issue type"]]
        groups.setdefault(transition_id, []).append(key)
    if groups:
        body = {
            "bulkTransitionInputs": [
                {"selectedIssueIdsOrKeys": keys, "transitionId": transition_id}
                for transition_id, keys in groups.items()
            ],
            "sendBulkNotification": False,
        }
        try:
            result = client.post("/rest/api/3/bulk/issues/transition", body) or {}
            task_id = str(result.get("taskId") or result.get("id") or "")
            if task_id:
                target_keys = {key for keys in groups.values() for key in keys}
                for _ in range(120):
                    current = search_issues(client, ["status", local_field_id])
                    current_status = {
                        issue["key"]: issue.get("fields", {}).get("status", {}).get("name")
                        for issue in current
                    }
                    if all(current_status.get(key) == "Done" for key in target_keys):
                        break
                    time.sleep(2)
                else:
                    raise RuntimeError(
                        f"Bulk transition task {task_id} did not produce the required live Done states"
                    )
        except JiraError:
            print("BULK TRANSITION UNAVAILABLE; using controlled per-issue transitions", flush=True)
            for transition_id, keys in groups.items():
                for key in keys:
                    client.post(f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": transition_id}})
        print(f"HISTORICAL STATUS TRANSITIONS REQUESTED: {sum(len(keys) for keys in groups.values())}", flush=True)
    ledger["historical_done_requested"] = len(done_rows)
    ledger["historical_done_operationally_overridden"] = len(completion_override_ids)
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)


def enforce_completion_assurance_policy(
    client: JiraClient,
    ledger: dict[str, Any],
    key_map: dict[str, str],
    field_ids: dict[str, str],
) -> None:
    policy = load_completion_policy()
    local_ids = set(policy.get("local_issue_ids", []))
    if not local_ids:
        return
    override = policy["jira_operational_override"]
    expected_status = override["status"]
    expected_evidence = override["evidence_state"]
    add_labels = set(override.get("add_labels", []))
    issues = search_issues(
        client,
        ["status", "issuetype", "labels", field_ids["Evidence State"], field_ids["Local Issue ID"]],
    )
    by_local = {
        issue["fields"].get(field_ids["Local Issue ID"]): issue
        for issue in issues
        if issue["fields"].get(field_ids["Local Issue ID"]) in local_ids
    }
    if set(by_local) != local_ids:
        raise RuntimeError("Completion assurance policy does not map exactly to live BAT issues")

    transition_by_type: dict[str, str] = {}
    for issue in by_local.values():
        if issue["fields"]["status"]["name"] == expected_status:
            continue
        issue_type = issue["fields"]["issuetype"]["name"]
        if issue_type in transition_by_type:
            continue
        transitions = client.get(f"/rest/api/3/issue/{issue['key']}/transitions")
        target = next(
            (item for item in transitions.get("transitions", []) if item.get("to", {}).get("name") == expected_status),
            None,
        )
        if target is None:
            raise RuntimeError(f"No transition to {expected_status} for completion-assurance {issue_type}")
        transition_by_type[issue_type] = str(target["id"])

    changed: list[str] = []
    errors: list[str] = []

    def worker(item: tuple[str, dict[str, Any]]) -> tuple[str, bool]:
        local_id, issue = item
        fields = issue["fields"]
        update_fields: dict[str, Any] = {}
        mutated = False
        actual_evidence = normalize_custom(fields.get(field_ids["Evidence State"]))
        if actual_evidence != expected_evidence:
            update_fields[field_ids["Evidence State"]] = {"value": expected_evidence}
        actual_labels = set(fields.get("labels") or [])
        if not add_labels <= actual_labels:
            update_fields["labels"] = sorted(actual_labels | add_labels)
        if update_fields:
            client.put(f"/rest/api/3/issue/{issue['key']}", {"fields": update_fields})
            mutated = True
        if fields["status"]["name"] != expected_status:
            transition_id = transition_by_type[fields["issuetype"]["name"]]
            client.post(
                f"/rest/api/3/issue/{issue['key']}/transitions",
                {"transition": {"id": transition_id}},
            )
            mutated = True
        return local_id, mutated

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(worker, item): item[0] for item in by_local.items()}
        for index, future in enumerate(as_completed(futures), start=1):
            local_id = futures[future]
            try:
                completed_local_id, mutated = future.result()
                if mutated:
                    changed.append(completed_local_id)
            except Exception as exc:
                errors.append(f"{local_id}: {exc}")
            if index % 25 == 0 or index == len(futures):
                ledger["completion_assurance"] = {
                    "policy": str(COMPLETION_POLICY_PATH.relative_to(ROOT)),
                    "processed": len(changed),
                    "errors": errors,
                    "target_status": expected_status,
                    "target_evidence_state": expected_evidence,
                    "updated_at": utc_now(),
                }
                ledger["updated_at"] = utc_now()
                write_json_atomic(LEDGER_PATH, ledger)
                print(
                    f"COMPLETION ASSURANCE: processed={index}/{len(futures)} changed={len(changed)} errors={len(errors)}",
                    flush=True,
                )
    if errors:
        raise RuntimeError("Completion-assurance update failures: " + "; ".join(errors[:20]))
    for _ in range(60):
        current = search_issues(
            client,
            ["status", "labels", field_ids["Evidence State"], field_ids["Local Issue ID"]],
        )
        checked = {
            issue["fields"].get(field_ids["Local Issue ID"]): issue
            for issue in current
            if issue["fields"].get(field_ids["Local Issue ID"]) in local_ids
        }
        if len(checked) == len(local_ids) and all(
            issue["fields"]["status"]["name"] == expected_status
            and normalize_custom(issue["fields"].get(field_ids["Evidence State"])) == expected_evidence
            and add_labels <= set(issue["fields"].get("labels") or [])
            for issue in checked.values()
        ):
            ledger["completion_assurance"].update(
                {"status": "COMPLETE_VERIFIED", "verified_count": len(checked), "verified_at": utc_now()}
            )
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
            return
        time.sleep(2)
    raise RuntimeError("Jira search index did not settle after completion-assurance updates")


def make_completion_assurance_backup(
    client: JiraClient,
    ledger: dict[str, Any],
    field_ids: dict[str, str],
) -> None:
    policy = load_completion_policy()
    local_ids = set(policy.get("local_issue_ids", []))
    if not local_ids:
        return
    existing = ledger.get("completion_assurance_backup", {})
    if existing:
        path = ROOT / existing["path"]
        if not path.exists() or sha256_file(path) != existing["sha256"]:
            raise RuntimeError("Completion-assurance backup is missing or failed SHA-256 verification")
        return
    issues = search_issues(
        client,
        [
            "summary", "status", "issuetype", "labels", "updated",
            field_ids["Local Issue ID"], field_ids["Evidence State"],
            field_ids["Logical Workflow State"],
        ],
    )
    selected = [
        issue
        for issue in issues
        if issue.get("fields", {}).get(field_ids["Local Issue ID"]) in local_ids
    ]
    if len(selected) != len(local_ids):
        raise RuntimeError(
            f"Completion-assurance backup expected {len(local_ids)} live issues, found {len(selected)}"
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = JIRA_ROOT / "snapshots" / f"BAT_HISTORICAL_DONE_PRE_REVIEW_{stamp}.json"
    snapshot = {
        "schema_version": 1,
        "captured_at": utc_now(),
        "reason": "Pre-change rollback snapshot before correcting unproven historical Done statuses.",
        "policy_path": str(COMPLETION_POLICY_PATH.relative_to(ROOT)),
        "policy_sha256": sha256_file(COMPLETION_POLICY_PATH),
        "audit_json_path": "jira\\validation\\HISTORICAL_DONE_EVIDENCE_AUDIT.json",
        "audit_json_sha256": sha256_file(JIRA_ROOT / "validation" / "HISTORICAL_DONE_EVIDENCE_AUDIT.json"),
        "issue_count": len(selected),
        "issues": sorted(selected, key=lambda issue: int(issue["id"])),
        "board_filter": client.get(f"/rest/api/3/filter/{BOARD_FILTER_ID}"),
        "saved_filters_before": ledger.get("saved_filters", {}),
        "rollback": {
            "status": "Use each issue's captured fields.status.name and available Jira transition.",
            "fields": "Restore captured labels and Evidence State value for the exact issue key.",
            "scope": "Only the 221 policy-listed BAT historical-reference issues.",
        },
    }
    write_json_atomic(path, snapshot)
    digest = sha256_file(path)
    if json.loads(path.read_text(encoding="utf-8")) != snapshot or sha256_file(path) != digest:
        raise RuntimeError("Completion-assurance backup reread/hash verification failed")
    ledger["completion_assurance_backup"] = {
        "path": str(path.relative_to(ROOT)),
        "sha256": digest,
        "verified": True,
        "issue_count": len(selected),
    }
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    print(f"COMPLETION ASSURANCE BACKUP VERIFIED: {path.relative_to(ROOT)} sha256={digest}", flush=True)


def existing_link_signatures(issues: list[dict[str, Any]], key_to_local: dict[str, str]) -> set[str]:
    result: set[str] = set()
    for issue in issues:
        current = issue["key"]
        for link in issue.get("fields", {}).get("issuelinks", []) or []:
            link_type = link.get("type", {}).get("name", "")
            if "outwardIssue" in link:
                outward = current
                inward = link["outwardIssue"]["key"]
            elif "inwardIssue" in link:
                outward = link["inwardIssue"]["key"]
                inward = current
            else:
                continue
            if outward in key_to_local and inward in key_to_local:
                result.add(f"{link_type}|{key_to_local[outward]}|{key_to_local[inward]}")
    return result


def remediate_reversed_importer_links(
    client: JiraClient,
    ledger: dict[str, Any],
    link_payloads: list[dict[str, Any]],
    key_map: dict[str, str],
    local_field_id: str,
) -> None:
    issues = search_issues(client, ["issuelinks", local_field_id, "summary"])
    key_to_local = {key: local_id for local_id, key in key_map.items()}
    expected = {
        (
            item["payload_template"]["type"]["name"].removeprefix("{{LINK_TYPE:").removesuffix("}}"),
            item["source_local_id"],
            item["target_local_id"],
        )
        for item in link_payloads
    }
    physical: dict[str, dict[str, str]] = {}
    for issue in issues:
        current = issue["key"]
        for link in issue.get("fields", {}).get("issuelinks", []) or []:
            link_id = str(link["id"])
            link_type = link.get("type", {}).get("name", "")
            if "outwardIssue" in link:
                source_key = current
                target_key = link["outwardIssue"]["key"]
            elif "inwardIssue" in link:
                source_key = link["inwardIssue"]["key"]
                target_key = current
            else:
                continue
            physical[link_id] = {
                "id": link_id,
                "type": link_type,
                "source_key": source_key,
                "target_key": target_key,
                "source_local_id": key_to_local.get(source_key, source_key),
                "target_local_id": key_to_local.get(target_key, target_key),
            }
    canonical_physical = {
        link_id: item
        for link_id, item in physical.items()
        if item["source_key"] in key_to_local and item["target_key"] in key_to_local
    }
    actual = {
        (item["type"], item["source_local_id"], item["target_local_id"])
        for item in canonical_physical.values()
    }
    if actual == expected:
        return
    if actual <= expected:
        ledger["link_direction_remediation"] = {
            "status": "CANONICAL_SUBSET_NO_DELETION_REQUIRED",
            "existing_canonical_links": len(actual),
            "missing_canonical_links": len(expected - actual),
            "preserved_auxiliary_links": len(physical) - len(canonical_physical),
            "verified_at": utc_now(),
        }
        ledger["updated_at"] = utc_now()
        write_json_atomic(LEDGER_PATH, ledger)
        return
    reverse_expected = {(link_type, target, source) for link_type, source, target in expected}
    unexpected = actual - expected
    if unexpected and unexpected <= reverse_expected:
        targeted = ledger.get("targeted_link_direction_remediation", {})
        candidate_links = {
            link_id: item
            for link_id, item in canonical_physical.items()
            if (item["type"], item["source_local_id"], item["target_local_id"]) in unexpected
        }
        if not targeted:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            snapshot_path = JIRA_ROOT / "snapshots" / f"BAT_TARGETED_REVERSED_LINKS_{stamp}.json"
            snapshot = {
                "schema_version": 1,
                "captured_at": utc_now(),
                "reason": "Remove only exact reverse-direction duplicates of canonical generated dependencies; preserve every unrelated or auxiliary relationship.",
                "canonical_expected_count": len(expected),
                "canonical_actual_count": len(actual),
                "preserved_auxiliary_link_count": len(physical) - len(canonical_physical),
                "links": sorted(candidate_links.values(), key=lambda item: int(item["id"])),
            }
            write_json_atomic(snapshot_path, snapshot)
            digest = sha256_file(snapshot_path)
            if json.loads(snapshot_path.read_text(encoding="utf-8")) != snapshot or sha256_file(snapshot_path) != digest:
                raise RuntimeError("Targeted reversed-link snapshot reread/hash verification failed")
            targeted = {
                "status": "DELETE_EXACT_REVERSED_DUPLICATES_IN_PROGRESS",
                "backup": {"path": str(snapshot_path.relative_to(ROOT)), "sha256": digest},
                "candidate_link_ids": sorted(candidate_links, key=int),
                "deleted_link_ids": [],
                "started_at": utc_now(),
            }
            ledger["targeted_link_direction_remediation"] = targeted
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
        candidate_ids = set(targeted["candidate_link_ids"])
        current_ids = set(candidate_links)
        if current_ids - candidate_ids:
            raise RuntimeError("Targeted reversed-link set changed after its immutable snapshot")
        deleted = set(targeted.get("deleted_link_ids", []))
        for link_id in sorted(current_ids - deleted, key=int):
            client.delete(f"/rest/api/3/issueLink/{link_id}")
            deleted.add(link_id)
            targeted["deleted_link_ids"] = sorted(deleted, key=int)
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
        for _ in range(60):
            remaining_issues = search_issues(client, ["issuelinks", local_field_id])
            remaining_ids = {
                str(link["id"])
                for issue in remaining_issues
                for link in issue.get("fields", {}).get("issuelinks", []) or []
            }
            if not (candidate_ids & remaining_ids):
                targeted.update({"status": "EXACT_REVERSED_DUPLICATES_REMOVED_VERIFIED", "removed_at": utc_now()})
                ledger["updated_at"] = utc_now()
                write_json_atomic(LEDGER_PATH, ledger)
                return
            time.sleep(2)
        raise RuntimeError("Jira search index did not settle after targeted reversed-link cleanup")
    remediation = ledger.get("link_direction_remediation", {})
    recoverable_partial = (
        remediation.get("status") == "DELETE_REVERSED_LINKS_IN_PROGRESS"
        and actual
        and actual <= reverse_expected
    )
    if actual != reverse_expected and not recoverable_partial:
        raise RuntimeError(
            "Live Jira links are neither the exact canonical set nor the exact/recoverable reversed importer set; "
            "refusing automated link deletion"
        )
    if not remediation:
        backup = json.loads((ROOT / ledger["backup"]["path"]).read_text(encoding="utf-8"))
        if backup.get("issues"):
            raise RuntimeError("Pre-import BAT was not empty; reversed-link remediation is not authorized")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snapshot_path = JIRA_ROOT / "snapshots" / f"BAT_REVERSED_LINKS_PRE_REMEDIATION_{stamp}.json"
        snapshot = {
            "schema_version": 1,
            "captured_at": utc_now(),
            "reason": "Final quality gate proved all importer-created Jira dependency directions were reversed.",
            "physical_link_count": len(physical),
            "canonical_expected_count": len(expected),
            "links": sorted(physical.values(), key=lambda item: int(item["id"])),
        }
        write_json_atomic(snapshot_path, snapshot)
        digest = sha256_file(snapshot_path)
        if json.loads(snapshot_path.read_text(encoding="utf-8")) != snapshot or sha256_file(snapshot_path) != digest:
            raise RuntimeError("Reversed-link backup reread/hash verification failed")
        remediation = {
            "status": "DELETE_REVERSED_LINKS_IN_PROGRESS",
            "backup": {"path": str(snapshot_path.relative_to(ROOT)), "sha256": digest},
            "original_count": len(physical),
            "deleted_link_ids": [],
            "started_at": utc_now(),
        }
        ledger["link_direction_remediation"] = remediation
        ledger["updated_at"] = utc_now()
        write_json_atomic(LEDGER_PATH, ledger)

    deleted = set(remediation.get("deleted_link_ids", []))
    pending = [link_id for link_id in physical if link_id not in deleted]
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(client.delete, f"/rest/api/3/issueLink/{link_id}"): link_id
            for link_id in pending
        }
        for index, future in enumerate(as_completed(futures), start=1):
            link_id = futures[future]
            try:
                future.result()
                deleted.add(link_id)
            except Exception as exc:
                errors.append(f"{link_id}: {exc}")
            if index % 25 == 0 or index == len(pending):
                remediation["deleted_link_ids"] = sorted(deleted, key=int)
                remediation["errors"] = errors
                ledger["updated_at"] = utc_now()
                write_json_atomic(LEDGER_PATH, ledger)
                print(
                    f"REVERSED LINK CLEANUP: processed={index}/{len(pending)} deleted={len(deleted)} errors={len(errors)}",
                    flush=True,
                )
    if errors:
        raise RuntimeError("Reversed-link deletion failures: " + "; ".join(errors[:20]))
    for _ in range(60):
        remaining = search_issues(client, ["issuelinks", local_field_id])
        if not any(issue.get("fields", {}).get("issuelinks") for issue in remaining):
            remediation.update({"status": "REVERSED_LINKS_REMOVED_VERIFIED", "removed_at": utc_now()})
            ledger["links_completed"] = []
            ledger["link_errors"] = []
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
            return
        time.sleep(2)
    raise RuntimeError("Jira search index did not settle after reversed-link cleanup")


def create_links(
    client: JiraClient,
    ledger: dict[str, Any],
    link_payloads: list[dict[str, Any]],
    key_map: dict[str, str],
    local_field_id: str,
) -> None:
    issues = search_issues(client, ["issuelinks", local_field_id, "summary"])
    key_to_local = {key: local_id for local_id, key in key_map.items()}
    existing = existing_link_signatures(issues, key_to_local)
    expected: dict[str, dict[str, Any]] = {}
    for item in link_payloads:
        raw_type = item["payload_template"]["type"]["name"]
        link_type = raw_type.removeprefix("{{LINK_TYPE:").removesuffix("}}")
        signature = f"{link_type}|{item['source_local_id']}|{item['target_local_id']}"
        expected[signature] = item
    pending = [(signature, item) for signature, item in expected.items() if signature not in existing]
    completed = set(ledger.get("links_completed", [])) | (existing & set(expected))
    lock = threading.Lock()

    def worker(pair: tuple[str, dict[str, Any]]) -> str:
        signature, item = pair
        raw_type = item["payload_template"]["type"]["name"]
        link_type = raw_type.removeprefix("{{LINK_TYPE:").removesuffix("}}")
        client.post(
            "/rest/api/3/issueLink",
            {
                "type": {"name": link_type},
                "outwardIssue": {"key": key_map[item["target_local_id"]]},
                "inwardIssue": {"key": key_map[item["source_local_id"]]},
            },
        )
        return signature

    if pending:
        print(f"LINK CREATION STARTED: pending={len(pending)} existing={len(existing & set(expected))}", flush=True)
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(worker, pair): pair[0] for pair in pending}
            for index, future in enumerate(as_completed(futures), start=1):
                signature = futures[future]
                try:
                    done = future.result()
                    with lock:
                        completed.add(done)
                except Exception as exc:  # exact failures are retained in the ledger
                    errors.append(f"{signature}: {exc}")
                if index % 25 == 0 or index == len(pending):
                    ledger["links_completed"] = sorted(completed)
                    ledger["link_errors"] = errors
                    ledger["updated_at"] = utc_now()
                    write_json_atomic(LEDGER_PATH, ledger)
                    print(f"LINK PROGRESS: processed={index}/{len(pending)} completed={len(completed)}/{len(link_payloads)} errors={len(errors)}", flush=True)
        if errors:
            raise RuntimeError("Link creation failures: " + "; ".join(errors[:20]))
    ledger["links_completed"] = sorted(completed)
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)


def configure_filters(client: JiraClient, ledger: dict[str, Any], field_ids: dict[str, str]) -> None:
    board_filter = client.get(f"/rest/api/3/filter/{BOARD_FILTER_ID}")
    client.put(
        f"/rest/api/3/filter/{BOARD_FILTER_ID}",
        {
            "name": board_filter.get("name", "BAT board filter"),
            "description": (
                "Active post-W25 execution board for the canonical C:\\BatteredAggieSyndrome\\jira backlog. "
                "Historical W01-W25 reference work remains searchable but is intentionally excluded from the active board."
            ),
            "jql": "project = BAT AND labels = post-wave ORDER BY Rank ASC",
            "favourite": True,
        },
    )
    workflow_number = field_ids["Logical Workflow State"].removeprefix("customfield_")
    critical_number = field_ids["Critical Path"].removeprefix("customfield_")
    current = paged_values(client, "/rest/api/3/filter/search?overrideSharePermissions=true")
    by_name = {item.get("name"): item for item in current}
    saved: dict[str, str] = {}
    for name, jql_template, description in SAVED_FILTERS:
        body = {
            "name": name,
            "jql": jql_template.format(workflow=workflow_number, critical=critical_number),
            "description": description,
            "favourite": True,
        }
        item = by_name.get(name)
        if item:
            updated = client.put(f"/rest/api/3/filter/{item['id']}", body) or item
            saved[name] = str(updated.get("id", item["id"]))
        else:
            created = client.post("/rest/api/3/filter", body)
            saved[name] = str(created["id"])
    ledger["board"] = {"id": BOARD_ID, "filter_id": BOARD_FILTER_ID, "active_jql": "project = BAT AND labels = post-wave ORDER BY Rank ASC"}
    ledger["saved_filters"] = saved
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)
    print(f"BOARD/FILTERS CONFIGURED: active board + {len(saved)} saved execution filters", flush=True)


def normalize_custom(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("value", ""))
    return "" if value is None else str(value)


def verify_live(
    client: JiraClient,
    rows: list[dict[str, str]],
    payloads: list[dict[str, Any]],
    link_payloads: list[dict[str, Any]],
    field_ids: dict[str, str],
    component_ids: dict[str, str],
    key_map: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    completion_policy = load_completion_policy()
    completion_override_ids = set(completion_policy.get("local_issue_ids", []))
    completion_override = completion_policy.get("jira_operational_override", {})
    requested_fields = [
        "summary", "description", "status", "issuetype", "parent", "labels", "components",
        "priority", "issuelinks", "updated", "assignee", *field_ids.values(),
    ]
    issues = search_issues(client, requested_fields)
    by_key = {issue["key"]: issue for issue in issues}
    payload_by_id = {item["local_id"]: item for item in payloads}
    discrepancies: list[str] = []
    canonical_live_count = sum(key in by_key for key in key_map.values())
    if canonical_live_count != len(rows):
        discrepancies.append(f"canonical issue count {canonical_live_count} != {len(rows)}")
    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in rows:
        local_id = row["Local Issue ID"]
        key = key_map.get(local_id, "")
        issue = by_key.get(key)
        if not issue:
            discrepancies.append(f"missing Jira issue for {local_id}")
            continue
        fields = issue["fields"]
        expected = payload_by_id[local_id]["payload_template"]["fields"]
        actual_type = fields["issuetype"]["name"]
        type_counts[actual_type] = type_counts.get(actual_type, 0) + 1
        actual_status = fields["status"]["name"]
        status_counts[actual_status] = status_counts.get(actual_status, 0) + 1
        if fields["summary"] != row["Summary"]:
            discrepancies.append(f"{local_id}: summary mismatch")
        if fields["description"] != expected["description"]:
            discrepancies.append(f"{local_id}: ADF description mismatch")
        if actual_type != row["Issue type"]:
            discrepancies.append(f"{local_id}: issue type {actual_type} != {row['Issue type']}")
        expected_status = (
            completion_override.get("status", "To Do")
            if local_id in completion_override_ids
            else row["Status"]
        )
        if actual_status != expected_status:
            discrepancies.append(f"{local_id}: status {actual_status} != {expected_status}")
        expected_parent = ""
        parent_template = expected.get("parent", {}).get("key", "")
        if parent_template:
            parent_local = parent_template.removeprefix("{{JIRA_KEY:").removesuffix("}}")
            expected_parent = key_map[parent_local]
        actual_parent = (fields.get("parent") or {}).get("key", "")
        if actual_parent != expected_parent:
            discrepancies.append(f"{local_id}: parent {actual_parent} != {expected_parent}")
        if fields["priority"]["name"] != row["Priority"]:
            discrepancies.append(f"{local_id}: priority mismatch")
        actual_components = {item["name"] for item in fields.get("components", [])}
        if actual_components != {row["Component"]}:
            discrepancies.append(f"{local_id}: component mismatch")
        expected_labels = set(expected.get("labels", []))
        if local_id in completion_override_ids:
            expected_labels |= set(completion_override.get("add_labels", []))
        if set(fields.get("labels", [])) != expected_labels:
            discrepancies.append(f"{local_id}: label mismatch")
        logical = payload_by_id[local_id]["logical_fields_requiring_target_custom_field_ids"]
        for field_name, field_id in field_ids.items():
            expected_value = str(logical.get(field_name, row.get(field_name, "")))
            if field_name == "Critical Path":
                expected_value = row["Critical Path"].lower()
            if field_name == "Evidence State" and local_id in completion_override_ids:
                expected_value = completion_override.get("evidence_state", "PARTIAL")
            actual_value = normalize_custom(fields.get(field_id))
            if actual_value != expected_value:
                discrepancies.append(f"{local_id}: {field_name} {actual_value!r} != {expected_value!r}")
    key_to_local = {key: local_id for local_id, key in key_map.items()}
    actual_links = existing_link_signatures(issues, key_to_local)
    expected_links: set[str] = set()
    for item in link_payloads:
        link_type = item["payload_template"]["type"]["name"].removeprefix("{{LINK_TYPE:").removesuffix("}}")
        expected_links.add(f"{link_type}|{item['source_local_id']}|{item['target_local_id']}")
    missing_links = sorted(expected_links - actual_links)
    unexpected_links = sorted(actual_links - expected_links)
    if missing_links:
        discrepancies.append(f"missing links: {len(missing_links)}; sample={missing_links[:10]}")
    if unexpected_links:
        discrepancies.append(f"unexpected links: {len(unexpected_links)}; sample={unexpected_links[:10]}")
    board = client.get(f"/rest/agile/1.0/board/{BOARD_ID}/configuration")
    board_filter = client.get(f"/rest/api/3/filter/{BOARD_FILTER_ID}")
    verification = {
        "schema_version": 1,
        "verified_at": utc_now(),
        "result": "PASS" if not discrepancies else "FAIL",
        "project": {"key": PROJECT_KEY, "id": PROJECT_ID, "base_url": BASE_URL},
        "board": {"id": BOARD_ID, "name": board.get("name"), "filter_id": BOARD_FILTER_ID, "jql": board_filter.get("jql")},
        "issue_count": len(issues),
        "issue_type_counts": type_counts,
        "status_counts": status_counts,
        "parent_count": sum(bool(row["Parent"]) for row in rows),
        "expected_link_count": len(expected_links),
        "actual_expected_link_count": len(actual_links & expected_links),
        "link_direction_semantics": "source_local_id performs the Jira outward action toward target_local_id",
        "missing_link_count": len(missing_links),
        "unexpected_link_count": len(unexpected_links),
        "custom_fields": field_ids,
        "components": component_ids,
        "completion_assurance_policy_count": len(completion_override_ids),
        "discrepancies": discrepancies,
    }
    write_json_atomic(VERIFY_PATH, verification)
    if discrepancies:
        raise RuntimeError("Live Jira verification failed: " + "; ".join(discrepancies[:30]))
    return verification, issues


def write_export(rows: list[dict[str, str]], key_map: dict[str, str], issues: list[dict[str, Any]]) -> None:
    by_key = {issue["key"]: issue for issue in issues}
    fields = [
        "Local Issue ID", "Issue key", "Issue ID", "Status", "Logical Workflow State",
        "Assignee", "Sprint", "Updated",
    ]
    with EXPORT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            key = key_map[row["Local Issue ID"]]
            issue = by_key[key]
            assignee = issue["fields"].get("assignee") or {}
            writer.writerow(
                {
                    "Local Issue ID": row["Local Issue ID"],
                    "Issue key": key,
                    "Issue ID": issue["id"],
                    "Status": issue["fields"]["status"]["name"],
                    "Logical Workflow State": row["Logical Workflow State"],
                    "Assignee": assignee.get("emailAddress") or assignee.get("displayName", ""),
                    "Sprint": "",
                    "Updated": issue["fields"].get("updated", ""),
                }
            )


def write_target_configuration(
    verification: dict[str, Any],
    field_ids: dict[str, str],
    component_ids: dict[str, str],
    saved_filters: dict[str, str],
) -> None:
    profile_path = JIRA_ROOT / "project" / "JIRA_TARGET_PROFILE.yaml"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "platform": "Jira Cloud",
            "profile_status": "LIVE_TARGET_CONFIGURED_AND_VERIFIED",
            "discovery_required_before_api_execution": False,
            "jira_base_url": BASE_URL,
            "project_key": PROJECT_KEY,
            "project_id": PROJECT_ID,
            "project_name": "BatteredAggieSyndrome",
            "project_type": "software",
            "company_or_team_managed": "COMPANY_MANAGED",
            "board_id": BOARD_ID,
            "board_filter_id": BOARD_FILTER_ID,
            "saved_filters": saved_filters,
            "custom_field_mapping": field_ids,
            "available_components": [
                {"name": name, "id": component_id} for name, component_id in sorted(component_ids.items())
            ],
            "available_issue_types": [
                {"name": "Epic", "id": "10000"},
                {"name": "Story", "id": "10008"},
                {"name": "Task", "id": "10126"},
                {"name": "Sub-task", "id": "10125"},
            ],
            "available_link_types": ["Blocks", "Relates"],
            "available_priorities": ["Highest", "High", "Medium", "Low", "Lowest"],
            "available_statuses": ["To Do", "In Progress", "In Review", "Done"],
            "last_live_verification": verification["verified_at"],
            "live_counts": {
                "issues": verification["issue_count"],
                "parents": verification["parent_count"],
                "links": verification["actual_expected_link_count"],
            },
            "notes": [
                "BAT was discovered and configured through Jira Cloud REST v3 using returned IDs only.",
                "The active board is post-W25 execution only; historical W01-W25 reference remains searchable.",
                "Local canonical JSON owns specification; Jira owns operational status, assignee, sprint, rank, and comments.",
                "There is no Wave 26. Historical Done does not claim production or empirical completion.",
            ],
        }
    )
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    field_schema_path = JIRA_ROOT / "project" / "FIELD_SCHEMA.yaml"
    field_schema = json.loads(field_schema_path.read_text(encoding="utf-8"))
    for entry in field_schema["minimum_recommended_custom_fields"]:
        logical = entry["logical_name"]
        if logical in field_ids:
            entry["jira_id"] = field_ids[logical]
    field_schema_path.write_text(json.dumps(field_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with COMPONENTS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        component_rows = list(csv.DictReader(handle))
        component_fields = list(component_rows[0].keys())
    with COMPONENTS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=component_fields, lineterminator="\n")
        writer.writeheader()
        for row in component_rows:
            row["jira_component_id"] = component_ids[row["component_name"]]
            row["target_status"] = "MAPPED_LIVE_VERIFIED"
            writer.writerow(row)

    issue_map_path = JIRA_ROOT / "project" / "ISSUE_TYPE_MAPPING.yaml"
    issue_map = json.loads(issue_map_path.read_text(encoding="utf-8"))
    issue_map["target_mapping_status"] = "VERIFIED_IN_BAT"
    issue_map["target_issue_type_ids"] = {"Epic": "10000", "Story": "10008", "Task": "10126", "Subtask": "10125"}
    issue_map_path.write_text(json.dumps(issue_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for filename in ("PRIORITY_MAPPING.yaml", "WORKFLOW_MAPPING.yaml"):
        path = JIRA_ROOT / "project" / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        data["target_mapping_status"] = "VERIFIED_IN_BAT"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_reconciliation() -> dict[str, Any]:
    script = JIRA_ROOT / "tools" / "reconcile_jira_export.py"
    base = [sys.executable, "-B", str(script), str(EXPORT_PATH), "--repo-root", str(ROOT)]
    dry = subprocess.run([*base, "--dry-run"], cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
    if dry.returncode != 0:
        raise RuntimeError(f"Reconciliation dry-run failed:\n{dry.stdout}\n{dry.stderr}")
    dry_result = json.loads(dry.stdout)
    if dry_result.get("conflicts"):
        raise RuntimeError(f"Reconciliation dry-run reported conflicts: {dry_result['conflicts'][:20]}")
    live = subprocess.run(base, cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
    if live.returncode != 0:
        raise RuntimeError(f"Live reconciliation failed:\n{live.stdout}\n{live.stderr}")
    result = json.loads(live.stdout)
    print(f"LOCAL RECONCILIATION: {result}", flush=True)
    return {"dry_run": dry_result, "live": result}


def final_local_validation() -> dict[str, Any]:
    commands = [
        [sys.executable, "-B", str(JIRA_ROOT / "tools" / "validate_jira_pack.py"), "--repo-root", str(ROOT)],
        [sys.executable, "-B", str(JIRA_ROOT / "tools" / "validate_source_refs.py"), "--repo-root", str(ROOT)],
        [sys.executable, "-B", str(JIRA_ROOT / "tools" / "validate_dependencies.py")],
        [sys.executable, "-B", str(JIRA_ROOT / "tools" / "validate_import_files.py"), "--repo-root", str(ROOT)],
        [sys.executable, "-B", str(JIRA_ROOT / "tools" / "validate_second_pass.py"), "--repo-root", str(ROOT)],
    ]
    results: list[dict[str, Any]] = []
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
        results.append({"command": command, "returncode": run.returncode, "stdout": run.stdout[-8000:], "stderr": run.stderr[-4000:]})
        if run.returncode != 0:
            raise RuntimeError(f"Local validation failed: {command}\n{run.stdout}\n{run.stderr}")
    return {"result": "PASS", "commands": results}


def rebuild_manifest() -> None:
    sys.path.insert(0, str(JIRA_ROOT / "tools"))
    from jira_pack_lib import rebuild_file_manifest  # type: ignore

    rebuild_file_manifest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Idempotently import the canonical BAS Jira pack into live BAT Jira Cloud.")
    parser.add_argument("--execute", action="store_true", help="Perform the authorized production writes.")
    args = parser.parse_args()
    auxiliary = load_auxiliary_issues()
    rows, payloads, links, link_payloads = load_inputs()
    preflight = validate_inputs(rows, payloads, links, link_payloads)
    print(
        f"LOCAL PREFLIGHT: {preflight['result']} issues={preflight['issues']} "
        f"links={preflight['links']} auxiliary={len(auxiliary)}",
        flush=True,
    )
    if not args.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 0

    token = read_env_token(authoritative_env_path())
    client = JiraClient(BASE_URL, EMAIL, token)
    user = client.get("/rest/api/3/myself")
    if user.get("emailAddress") != EMAIL or not user.get("active"):
        raise RuntimeError(f"Unexpected Jira authenticated identity: {user}")
    project = client.get(f"/rest/api/3/project/{PROJECT_KEY}?expand=issueTypes")
    if str(project.get("id")) != PROJECT_ID or project.get("key") != PROJECT_KEY:
        raise RuntimeError(f"Destination identity mismatch: {project}")

    ledger = load_json(
        LEDGER_PATH,
        {
            "schema_version": 1,
            "status": "IN_PROGRESS",
            "started_at": utc_now(),
            "project": {"base_url": BASE_URL, "key": PROJECT_KEY, "id": PROJECT_ID, "board_id": BOARD_ID},
            "source_preflight": preflight,
            "approval": "Explicit user approval received in Codex task before production execution.",
        },
    )
    ledger["status"] = "IN_PROGRESS"
    if ledger.get("last_error"):
        ledger.setdefault("negative_findings", []).append(
            {"recorded_at": ledger.get("updated_at", utc_now()), "finding": ledger["last_error"]}
        )
    ledger.pop("last_error", None)
    ledger["updated_at"] = utc_now()
    write_json_atomic(LEDGER_PATH, ledger)

    make_backup(client, ledger, preflight)
    components = ensure_components(client, ledger)
    fields = ensure_fields(client, ledger)
    reconcile_auxiliary_issues(client, ledger, fields)
    remove_exact_importer_duplicates(client, ledger, rows, fields["Local Issue ID"])
    key_map = create_issues(client, ledger, rows, payloads, fields, components)
    synchronize_canonical_spec_fields(client, ledger, rows, payloads, key_map, fields, components)
    make_completion_assurance_backup(client, ledger, fields)
    transition_historical_done(client, ledger, rows, key_map, fields["Local Issue ID"])
    transition_declared_active_statuses(client, rows, key_map)
    enforce_completion_assurance_policy(client, ledger, key_map, fields)
    remediate_reversed_importer_links(client, ledger, link_payloads, key_map, fields["Local Issue ID"])
    create_links(client, ledger, link_payloads, key_map, fields["Local Issue ID"])
    configure_filters(client, ledger, fields)
    verification, live_issues = verify_live(client, rows, payloads, link_payloads, fields, components, key_map)
    if ledger.get("link_direction_remediation"):
        ledger["link_direction_remediation"].update(
            {
                "status": "CORRECT_DIRECTION_RECREATED_VERIFIED",
                "corrected_link_count": verification["actual_expected_link_count"],
                "verified_at": verification["verified_at"],
            }
        )
    write_export(rows, key_map, live_issues)
    write_target_configuration(verification, fields, components, ledger.get("saved_filters", {}))
    reconciliation = run_reconciliation()
    local_validation = final_local_validation()

    ledger["status"] = "COMPLETE_VERIFIED"
    ledger["completed_at"] = utc_now()
    ledger["verification"] = verification
    ledger["reconciliation"] = reconciliation
    ledger["local_validation"] = local_validation
    ledger["updated_at"] = ledger["completed_at"]
    write_json_atomic(LEDGER_PATH, ledger)
    rebuild_manifest()
    expected = canonical_expected_counts()
    print(
        "BAT LIVE IMPORT COMPLETE: "
        f"issues={expected['issues']} parents={expected['parents']} links={expected['links']} "
        f"operational_done={verification['status_counts'].get('Done', 0)} "
        f"active_post_wave={expected['active_post_wave']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            ledger = load_json(LEDGER_PATH, {})
            ledger["status"] = "FAILED_RESUMABLE"
            ledger["last_error"] = str(exc)
            ledger["updated_at"] = utc_now()
            write_json_atomic(LEDGER_PATH, ledger)
        except Exception:
            pass
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
