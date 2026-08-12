from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.contracts import AssistiveRequest, Authority  # noqa: E402
from aggie_analytics.assistive_plane.dispatcher import AssistiveDispatcher  # noqa: E402
from aggie_analytics.assistive_plane.openrouter_backend import OpenRouterBackend  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed candidate-only OpenRouter dispatcher")
    parser.add_argument("request", type=Path)
    parser.add_argument("schema", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.request.read_text(encoding="utf-8"))
    payload["authority"] = Authority(payload["authority"])
    request = AssistiveRequest(**payload)
    backend = OpenRouterBackend(Path(r"C:\BatteredAggieSyndrome\.env"))
    dispatcher = AssistiveDispatcher(ROOT, backend, ROOT / "configs/openrouter_assist_policy.json")
    result = dispatcher.dispatch(request, json.loads(args.schema.read_text(encoding="utf-8")))
    print(json.dumps({"request_id": result.request_id, "disposition": result.disposition.value, "reason": result.reason, "manifest_path": result.manifest_path}, sort_keys=True))
    return 0 if result.disposition.value == "CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
