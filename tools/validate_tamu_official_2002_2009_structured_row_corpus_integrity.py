from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus_integrity import (  # noqa: E402
    CHILD_DOMAINS,
    CHILD_FILENAMES,
    FORBIDDEN_URLS,
    MANIFEST_NAME,
    AuthorityViolation,
    consume_corpus,
    reconstruct_objects,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AuthorityViolation, FileNotFoundError, AssertionError) as exc:
        return {"name": name, "rejected": True, "detail": str(exc)}
    return {"name": name, "rejected": False, "detail": ""}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently consume and validate the integrity-complete 2002-2009 structured row corpus."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    reconstructed = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    validated = validate_artifact(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    consumed = consume_corpus(data_root=data_root, dataset_identity=validated["dataset_identity"])
    mutations = [
        expect_rejection(
            "consumer_skips_scoring_summary",
            lambda: consume_corpus(
                data_root=data_root,
                dataset_identity=validated["dataset_identity"],
                skip_children=("scoring_summary",),
            ),
        )
    ]
    print(
        json.dumps(
            {
                "dataset_identity": validated["dataset_identity"],
                "gate_identity": reconstructed["gate"]["gate_identity"],
                "code_identity": reconstructed["gate"]["validator_code_identity"],
                "consumed_row_counts": {domain: len(consumed[domain]) for domain in CHILD_DOMAINS},
                "child_filenames": CHILD_FILENAMES,
                "forbidden_url_count": len(FORBIDDEN_URLS),
                "manifest_name": MANIFEST_NAME,
                "mutations": mutations,
            },
            indent=2,
            sort_keys=True,
        )
    )
    if any(not item["rejected"] for item in mutations):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
