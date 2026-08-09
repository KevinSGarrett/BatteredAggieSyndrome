from __future__ import annotations

"""Render bounded canonical context paths for one local Jira issue ID."""

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_id")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    matches = []
    for path in (repo / "jira/records/issues").rglob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if record.get("local_id") == args.local_id:
            matches.append((path, record))
    if len(matches) != 1:
        raise SystemExit(f"Expected one record for {args.local_id}; found {len(matches)}")
    path, record = matches[0]
    context = {
        "local_id": args.local_id,
        "jira_key": record.get("jira_key", ""),
        "workflow_state": record.get("workflow_state", ""),
        "objective": record.get("objective", ""),
        "record_path": path.relative_to(repo).as_posix(),
        "work_packet_path": record.get("work_packet_path", ""),
        "source_manifest_path": f"jira/sources/issue_source_manifests/{args.local_id}.json",
        "parent_id": record.get("parent_id", ""),
        "dependencies": record.get("dependencies", []),
        "allowed_modification_paths": record.get("allowed_modification_paths", []),
        "files_expected_to_be_read": record.get("files_expected_to_be_read", []),
        "acceptance_criteria": record.get("acceptance_criteria", []),
        "required_tests": record.get("required_tests", []),
    }
    if args.format == "json":
        print(json.dumps(context, indent=2, sort_keys=True))
    else:
        print(f"# {context['jira_key']} / {context['local_id']}\n")
        print(context["objective"])
        for name in ("record_path", "work_packet_path", "source_manifest_path"):
            print(f"- {name}: `{context[name]}`")
        print("\n## Acceptance criteria")
        for value in context["acceptance_criteria"]:
            print(f"- {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
