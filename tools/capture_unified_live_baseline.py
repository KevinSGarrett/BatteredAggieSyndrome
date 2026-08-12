from __future__ import annotations

import base64
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


AUTHORITATIVE_ENV = Path(r"C:\BatteredAggieSyndrome\.env")
OUTPUT_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3")
WORKER = "comfy-v4-cpu-01.tail9b05ab.ts.net"
WORKER_USER = "Windows 11"
KEYS = (
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "CURSOR_API_TOKEN",
    "JIRA_EMAIL",
    "JIRA_API_KEY",
    "SCRAPFLY_API_TOKEN",
    "SCRAPFLY_MCP_URL",
    "SCRAPERAPI_API_TOKEN",
    "CFBD_API_KEY",
)


def load_env_presence(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    values: dict[str, list[str]] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values.setdefault(key.strip(), []).append(value.strip())
    presence = {
        key: {"count": len(values.get(key, [])), "nonempty_exactly_once": len(values.get(key, [])) == 1 and bool(values[key][0])}
        for key in KEYS
    }
    secrets = {key: values[key][0] for key in KEYS if presence[key]["nonempty_exactly_once"]}
    return presence, secrets


def run(arguments: list[str], timeout: int = 20) -> dict[str, Any]:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
    return {"exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr_present": bool(result.stderr.strip())}


def tailscale_self(arguments: list[str]) -> dict[str, Any]:
    result = run(arguments)
    if result["exit_code"] != 0:
        return {"reachable": False, "exit_code": result["exit_code"], "stderr_present": result["stderr_present"]}
    payload = json.loads(result["stdout"])
    self_state = payload.get("Self", {})
    return {
        "reachable": True,
        "hostname": self_state.get("HostName"),
        "dns_name": self_state.get("DNSName"),
        "online": self_state.get("Online"),
        "os": self_state.get("OS"),
        "tailscale_ip_count": len(self_state.get("TailscaleIPs", [])),
        "node_id_present": bool(self_state.get("ID")),
    }


def ollama_catalog() -> dict[str, Any]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - baseline records type only
        return {"reachable": False, "error_type": type(exc).__name__}
    models = [
        {"name": item.get("name"), "digest": item.get("digest"), "bytes": item.get("size")}
        for item in payload.get("models", [])
    ]
    return {"reachable": True, "models": models, "model_count": len(models)}


def openai_usage() -> dict[str, Any]:
    path = Path(r"C:\BatteredAggieSyndrome.data\openai\usage\usage-ledger.jsonl")
    calls = 0
    spend = Decimal("0")
    by_model: Counter[str] = Counter()
    last_success = None
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("event") == "SETTLED" or item.get("status") in {"SETTLED", "COMPLETED", "SUCCESS"}:
                calls += 1
                by_model[str(item.get("model") or item.get("resolved_model") or "UNKNOWN")] += 1
                spend += Decimal(str(item.get("actual_usd") or item.get("actual_cost_usd") or item.get("cost_usd") or item.get("settled_usd") or "0"))
                stamp = item.get("recorded_at") or item.get("settled_at") or item.get("timestamp") or item.get("completed_at")
                if stamp and (last_success is None or stamp > last_success):
                    last_success = stamp
    return {"settled_calls": calls, "settled_usd": format(spend, "f"), "calls_by_model": dict(sorted(by_model.items())), "last_successful_at": last_success}


def provider_artifact_summary(root: Path, identity_field: str) -> dict[str, Any]:
    files = list(root.rglob("*.json")) if root.is_dir() else []
    identities: set[str] = set()
    dispositions: Counter[str] = Counter()
    for path in files:
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(item, dict):
            if item.get(identity_field):
                identities.add(str(item[identity_field]))
            if item.get("disposition"):
                dispositions[str(item["disposition"])] += 1
    return {"json_artifacts": len(files), "real_identity_count": len(identities), "dispositions": dict(sorted(dispositions.items()))}


def jira_preflight(secrets: dict[str, str]) -> dict[str, Any]:
    if not {"JIRA_EMAIL", "JIRA_API_KEY"}.issubset(secrets):
        return {"authenticated": False, "reason": "CREDENTIAL_PRESENCE_GATE_FAILED"}
    auth_header = base64.b64encode(f"{secrets['JIRA_EMAIL']}:{secrets['JIRA_API_KEY']}".encode()).decode()
    request = urllib.request.Request(
        "https://kevinsgarrett.atlassian.net/rest/api/3/myself",
        headers={"Authorization": f"Basic {auth_header}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
        return {"authenticated": response.status == 200, "http_status": response.status, "account_id_present": bool(payload.get("accountId"))}
    except Exception as exc:  # noqa: BLE001
        return {"authenticated": False, "error_type": type(exc).__name__}


def main() -> int:
    presence, secrets = load_env_presence(AUTHORITATIVE_ENV)
    git_head = run(["git", "rev-parse", "HEAD"])
    git_main = run(["git", "rev-parse", "origin/main"])
    git_status = run(["git", "status", "--porcelain"])
    local_ts = tailscale_self(["tailscale", "status", "--json"])
    remote_ts = tailscale_self(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", f"{WORKER_USER}@{WORKER}", "tailscale", "status", "--json"])
    remote_hostname = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", f"{WORKER_USER}@{WORKER}", "hostname"])
    remote_serve = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", f"{WORKER_USER}@{WORKER}", "tailscale", "serve", "status"])
    payload = {
        "schema_version": 1,
        "capture_id": "unified-assistive-live-baseline-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "credentials": presence,
        "git": {
            "head": git_head["stdout"],
            "origin_main": git_main["stdout"],
            "clean": git_status["exit_code"] == 0 and not git_status["stdout"],
        },
        "jira": jira_preflight(secrets),
        "tailscale": {"coordinator": local_ts, "worker": remote_ts},
        "cpu_worker": {
            "ssh_passwordless": remote_hostname["exit_code"] == 0,
            "hostname": remote_hostname["stdout"],
            "serve_private_https_configured": remote_serve["exit_code"] == 0 and "tailnet only" in remote_serve["stdout"].lower(),
            "serve_loopback_target_8765": "127.0.0.1:8765" in remote_serve["stdout"],
            "funnel_public_claimed": False,
            "corrected_service_qualification": "BLOCKED_PARTIAL_CORRECTED_DEPLOYMENT_PENDING",
        },
        "ollama": ollama_catalog(),
        "openai": openai_usage(),
        "openrouter": provider_artifact_summary(Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter"), "request_id"),
        "cursor": provider_artifact_summary(Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor"), "agent_id"),
        "operational_completeness": "INCOMPLETE",
        "secrets_recorded": False,
    }
    path, digest = write_content_addressed_json(OUTPUT_ROOT, "baselines", payload)
    print(json.dumps({"status": "PASS", "path": str(path), "sha256": digest, "operational_completeness": "INCOMPLETE"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
