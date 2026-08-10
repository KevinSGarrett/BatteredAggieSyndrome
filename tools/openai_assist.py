from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob  # noqa: E402
from aggie_analytics.openai_assist.contracts import Priority, ProcessingMode  # noqa: E402
from aggie_analytics.openai_assist.evals import evaluate  # noqa: E402


def _job(path: Path) -> AssistiveJob:
    value = json.loads(path.read_text(encoding="utf-8"))
    if any(key.lower() in {"api_key", "openai_api_key", "authorization"} for key in value):
        raise ValueError("job files may not contain credentials")
    value["schema_path"] = (ROOT / value["schema_path"]).resolve()
    value["priority"] = Priority(value.get("priority", "NORMAL"))
    return AssistiveJob(**value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed optional OpenAI assistive controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("usage")
    estimate = sub.add_parser("estimate")
    estimate.add_argument("--job", type=Path, required=True)
    sync = sub.add_parser("sync")
    sync.add_argument("--job", type=Path, required=True)
    batch = sub.add_parser("batch-submit")
    batch.add_argument("--job", type=Path, action="append", required=True)
    collect = sub.add_parser("batch-collect")
    collect.add_argument("--batch-id", required=True)
    collect.add_argument("--keep-remote", action="store_true")
    evaluation = sub.add_parser("eval")
    evaluation.add_argument(
        "--gold", type=Path, default=ROOT / "fixtures" / "openai_assist" / "eval_gold.jsonl"
    )
    evaluation.add_argument("--predictions", type=Path, required=True)
    sub.add_parser("cleanup-tmp")
    args = parser.parse_args()

    controller = AssistiveController(ROOT)
    if args.command == "doctor":
        value = controller.doctor()
    elif args.command == "usage":
        value = controller.ledger.summary()
    elif args.command == "estimate":
        item = controller.prepare(_job(args.job), mode=ProcessingMode.SYNCHRONOUS)
        value = {"request_id": item["request_id"], "estimate": item["estimate"].json_value()}
    elif args.command == "sync":
        value = controller.run_sync(_job(args.job)).__dict__
    elif args.command == "batch-submit":
        value = controller.submit_batch([_job(path) for path in args.job])
    elif args.command == "batch-collect":
        value = controller.collect_batch(args.batch_id, delete_remote=not args.keep_remote)
    elif args.command == "eval":
        schema = json.loads(
            (ROOT / "schemas" / "openai" / "assistive_candidate.schema.json").read_text(encoding="utf-8")
        )
        value = evaluate(args.gold, args.predictions, schema).as_dict()
    elif args.command == "cleanup-tmp":
        value = controller.store.cleanup_tmp()
    else:
        raise AssertionError("unreachable")
    print(json.dumps(value, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
