"""Independently reconstruct C20/C21 game-grain successor pair coherence.

This validator does not import producer scientific helpers. Predecessor identity
pins are duplicated as hashes here. Pair reconstruction uses the declared
complement rule: probabilities outside (0, 1] are invalid and are not
renormalized into a coherent pair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.scientific_reference.coherence import pair_normalize  # noqa: E402
from aggie_analytics.scientific_reference.metrics import brier_score, log_loss  # noqa: E402

PREDECESSOR_PINS: dict[str, dict[str, str]] = {
    "20": {
        "cycle": "CYCLE-20",
        "relative_path": (
            "canonical/national_expectation_baselines_and_peers/sha256/"
            "773cf850bb8351497643506dd2ddcb4efbad26e3cd95a4dc78039b6e8ef3a1b0/"
            "national_baseline_predictions.jsonl"
        ),
        "sha256": "a4671745e7c89a65ed87f2c2c5bd0a90a6adb38fedd162240cace1f30ee0088e",
        "game_key": "canonical_game_id",
        "probability_key": "predicted_win_probability",
        "margin_key": "predicted_margin",
    },
    "21": {
        "cycle": "CYCLE-21",
        "relative_path": (
            "canonical/national_multi_year_walk_forward/sha256/"
            "1112becc65f78a25b0843588fd5eba5ddcec6009b0ec58f0cb299c343188bcda/"
            "national_multi_year_walk_forward_predictions.jsonl"
        ),
        "sha256": "c380eb08ee42c7b4eeed32436ccfc4f035f88e43048f327ea9c0d5d28fb4e6d6",
        "game_key": "canonical_game_id",
        "probability_key": "predicted_win_probability",
        "margin_key": "predicted_margin",
    },
}
CONTROL_ONLY = frozenset({"national_base_rate"})
MARGIN_CAPABLE = "national_margin_ridge"
GATE_RELATIVE = (
    "artifacts/experimentation/historical_saved_pair_game_grain_successor_gate.json"
)


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _probability_in_unit_interval(value: Any) -> float | None:
    if not _finite(value):
        return None
    number = float(value)
    if number <= 0.0 or number > 1.0:
        return None
    return number


def _declared_pair_complement(p_a_raw: float, p_b_raw: float) -> dict[str, Any]:
    """Independent reconstruction of the declared in-range pair-sum rule.

    Values outside (0, 1] are invalid. They are not inputs for renormalization
    into a complementary pair.
    """
    left = _probability_in_unit_interval(p_a_raw)
    right = _probability_in_unit_interval(p_b_raw)
    if left is None or right is None:
        return {
            "ok": False,
            "reason": "INVALID_PROBABILITY_DOMAIN",
            "p_a": None,
            "p_b": None,
        }
    total = left + right
    p_a = left / total
    p_b = 1.0 - p_a
    check = pair_normalize(p_a, p_b, 0.0, 0.0)
    return {
        "ok": bool(check["probability_complementary"]),
        "reason": ""
        if check["probability_complementary"]
        else str(check["abstain_reason"]),
        "p_a": p_a,
        "p_b": p_b,
    }


def _reconstruct_pair(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    spec: Mapping[str, str],
) -> dict[str, Any]:
    candidate = str(left.get("candidate_id") or "")
    p_a_raw = left.get(spec["probability_key"])
    p_b_raw = right.get(spec["probability_key"])
    if candidate in CONTROL_ONLY:
        return {"probability_a": 0.5, "probability_b": 0.5, "ok": True, "reason": ""}
    left_p = _probability_in_unit_interval(p_a_raw)
    right_p = _probability_in_unit_interval(p_b_raw)
    if left_p is None or right_p is None:
        return {
            "probability_a": None,
            "probability_b": None,
            "ok": True,
            "reason": "ABSTAIN_MISSING_OR_INVALID_PROBABILITY",
        }
    if candidate == "national_elo" and abs(left_p + right_p - 1.0) <= 1e-8:
        return {
            "probability_a": left_p,
            "probability_b": 1.0 - left_p,
            "ok": True,
            "reason": "",
        }
    rebuilt = _declared_pair_complement(left_p, right_p)
    return {
        "probability_a": rebuilt["p_a"],
        "probability_b": rebuilt["p_b"],
        "ok": rebuilt["ok"],
        "reason": rebuilt["reason"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root)
    data = Path(args.data_root)
    gate_path = repo / GATE_RELATIVE
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    fail = 0
    for cycle, spec in PREDECESSOR_PINS.items():
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
        rows = [
            json.loads(line)
            for line in predecessor_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
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
            key = (str(row["candidate_id"]), str(row[spec["game_key"]]))
            groups.setdefault(key, []).append(row)
        reconstructed_fail = 0
        predicted: list[float] = []
        observed: list[float] = []
        for game in games:
            pair = groups[(game["candidate_id"], game["canonical_game_id"])]
            left, right = sorted(pair, key=lambda item: str(item["canonical_team_id"]))
            rebuilt = _reconstruct_pair(left, right, spec=spec)
            if rebuilt["probability_a"] != game["probability_a"]:
                reconstructed_fail += 1
            if rebuilt["probability_b"] != game["probability_b"]:
                reconstructed_fail += 1
            if game["probability_a"] is None:
                continue
            check = pair_normalize(
                float(game["probability_a"]),
                float(game["probability_b"]),
                0.0,
                0.0,
            )
            if not check["probability_complementary"]:
                reconstructed_fail += 1
            if game["candidate_id"] not in {"national_base_rate", "national_elo"}:
                expected = _declared_pair_complement(
                    float(left[spec["probability_key"]]),
                    float(right[spec["probability_key"]]),
                )
                if not expected["ok"]:
                    reconstructed_fail += 1
                elif abs(float(game["probability_a"]) - float(expected["p_a"])) > 1e-10:
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
            "producer_helpers_imported": False,
        }
        if payload["failing_pairs"] != 0:
            fail += 1
    result = {
        "result": "PASS" if fail == 0 else "FAIL",
        "independent_fail_count": fail,
        "gate_identity": gate["gate_identity"],
        "predecessor_rewritten": False,
        "joint_probability_margin_interval": gate["joint_probability_margin_interval"],
        "producer_helpers_imported": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
