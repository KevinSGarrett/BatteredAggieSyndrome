from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


def load_unique_key(path: Path, name: str) -> str:
    matches: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith(f"{name}="):
            matches.append(raw.split("=", 1)[1].strip().strip('"').strip("'"))
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(f"{name}_MUST_EXIST_EXACTLY_ONCE_AND_BE_NONEMPTY")
    return matches[0]


def request_json(url: str, token: str) -> dict[str, Any]:
    auth = base64.b64encode(f"{token}:".encode("ascii")).decode("ascii")
    request = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"CURSOR_CATALOG_HTTP_{response.status}")
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=Path(r"C:\BatteredAggieSyndrome\.env"))
    parser.add_argument("--storage-root", type=Path, default=Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor"))
    args = parser.parse_args()
    token = load_unique_key(args.env, "CURSOR_API_TOKEN")
    models = request_json("https://api.cursor.com/v1/models", token)
    repositories = request_json("https://api.cursor.com/v1/repositories?limit=100", token)
    model_items = list(models.get("items", []))
    exact = [item for item in model_items if item.get("id") == "gpt-5.3-codex"]
    if len(exact) != 1:
        raise RuntimeError("CURSOR_REQUIRED_MODEL_NOT_UNIQUE_IN_LIVE_CATALOG")
    parameters = {item.get("id"): item for item in exact[0].get("parameters", [])}
    reasoning = {item.get("value") for item in parameters.get("reasoning", {}).get("values", [])}
    fast = {item.get("value") for item in parameters.get("fast", {}).get("values", [])}
    if not {"low", "medium"}.issubset(reasoning) or not {"false", "true"}.issubset(fast):
        raise RuntimeError("CURSOR_REQUIRED_MODEL_PARAMETERS_CHANGED")
    payload = {
        "schema_version": 1,
        "api_version": "v1-public-beta",
        "models": models,
        "repositories": repositories,
        "required_model": "gpt-5.3-codex",
        "required_reasoning": ["low", "medium"],
        "fast": False,
        "work_on_current_branch": False,
        "auto_create_pr": False,
        "credential_present": True,
        "credential_recorded": False,
    }
    path, digest = write_content_addressed_json(args.storage_root, "catalogs", payload)
    print(json.dumps({
        "status": "PASS",
        "model_count": len(model_items),
        "repository_count": len(repositories.get("items", [])),
        "required_model_present": True,
        "catalog_sha256": digest,
        "catalog_path": str(path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
