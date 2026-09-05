"""Independently reconstruct C20/C21 game-grain successor pair coherence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.historical_saved_pair_game_grain_successor import (  # noqa: E402
    PREDECESSORS,
    load_predecessor,
    succeed_pair,
)
from aggie_analytics.data.week1_2026_game_grain_national_forecast_successor import (  # noqa: E402
    normalize_pair_probabilities,
)
from aggie_analytics.scientific_reference.metrics import brier_score, log_loss  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root)
    data = Path(args.data_root)
    gate = json.loads(
        (
            repo
            / "artifacts/experimentation/historical_saved_pair_game_grain_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    fail = 0
    for cycle, spec in PREDECESSORS.items():
        predecessor_path = data / spec["relative_path"]
        predecessor_digest = hashlib.sha256(predecessor_path.read_bytes()).hexdigest()
        if predecessor_digest != spec["sha256"]:
            print(
                json.dumps(
                    {
                        "result": "FAIL",
                        "reason": "predecessor_rewritten",
                        "cycle": cycle,
                    }
                )
            )
            return 1
        rows, loaded_spec = load_predecessor(data, cycle)
        payload = gate["cycles"][cycle]
        game_path = data / payload["payloads"]["game_rows"]["relative_path"]
        games = [
            json.loads(line)
            for line in game_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(games) != payload["game_row_count"]:
            fail += 1
        groups: dict[tuple[str, str], list] = {}
        for row in rows:
            key = (str(row["candidate_id"]), str(row[loaded_spec["game_key"]]))
            groups.setdefault(key, []).append(row)
        reconstructed_fail = 0
        predicted: list[float] = []
        observed: list[float] = []
        for game in games:
            pair = groups[(game["candidate_id"], game["canonical_game_id"])]
            left, right = sorted(pair, key=lambda item: str(item["canonical_team_id"]))
            rebuilt = succeed_pair(left, right, spec=loaded_spec, source_cycle=cycle)
            if rebuilt["game"]["probability_a"] != game["probability_a"]:
                reconstructed_fail += 1
            if rebuilt["game"]["probability_b"] != game["probability_b"]:
                reconstructed_fail += 1
            if game["probability_a"] is None:
                continue
            if (
                abs(float(game["probability_a"]) + float(game["probability_b"]) - 1.0)
                > 1e-12
            ):
                reconstructed_fail += 1
            if game["candidate_id"] not in {"national_base_rate", "national_elo"}:
                raw_a = float(left[loaded_spec["probability_key"]])
                raw_b = float(right[loaded_spec["probability_key"]])
                expected = normalize_pair_probabilities(raw_a, raw_b)
                if (
                    abs(float(game["probability_a"]) - float(expected["p_a_game"]))
                    > 1e-10
                ):
                    reconstructed_fail += 1
            if (
                game.get("observed_win_a") is True
                or game.get("observed_win_a") is False
            ):
                predicted.append(float(game["probability_a"]))
                observed.append(1.0 if game["observed_win_a"] else 0.0)
        if reconstructed_fail:
            fail += reconstructed_fail
        independent_brier = brier_score(predicted, observed) if predicted else None
        independent_log_loss = log_loss(predicted, observed) if predicted else None
        payload["_independent_check"] = {
            "reconstructed_fail": reconstructed_fail,
            "independent_brier_all_candidates_pooled": independent_brier,
            "independent_log_loss_all_candidates_pooled": independent_log_loss,
        }
        if payload["failing_pairs"] != 0:
            fail += 1
    result = {
        "result": "PASS" if fail == 0 else "FAIL",
        "independent_fail_count": fail,
        "gate_identity": gate["gate_identity"],
        "predecessor_rewritten": False,
        "joint_probability_margin_interval": gate["joint_probability_margin_interval"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
