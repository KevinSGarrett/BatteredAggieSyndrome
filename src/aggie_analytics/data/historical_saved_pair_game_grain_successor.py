"""Game-grain successor for immutable C20/C21 saved team-grain predictions.

Predecessor payloads are never rewritten. Pair-normalized probabilities and
antisymmetric ridge margins are emitted as a new content-addressed successor.
Original team-grain metrics are deprecated; they are not authoritative.
Fold-local Normal residual scale is not present in the saved C20/C21 files, so
this successor does not claim a joint probability/margin/interval path. The
Week 1 national successor remains the joint fitted path.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.producer_metric_math import (
    accuracy,
    brier_score,
    log_loss,
)
from aggie_analytics.data.week1_2026_game_grain_national_forecast_successor import (
    normalize_pair_probabilities,
)

SCHEMA_VERSION = "aggie.models.historical_saved_pair_game_grain_successor.v1"
CONTRACT_ID = "CYCLE26-HISTORICAL-SAVED-PAIR-GAME-GRAIN-SUCCESSOR-V1"
JIRA_KEY = "BAT-693"
LOCAL_ISSUE_ID = (
    "POST-TASK-ACTIVE-NATIONAL-FORECAST-SCIENTIFIC-CORRECTNESS-RECOVERY-001"
)
CLASSIFICATION = "HISTORICAL_SAVED_PAIR_GAME_GRAIN_SUCCESSOR"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_HISTORICAL_SAVED_PAIR_GAME_GRAIN_SUCCESSOR"
GATE_RELATIVE = (
    "artifacts/experimentation/historical_saved_pair_game_grain_successor_gate.json"
)
PAYLOAD_SLUG = "historical_saved_pair_game_grain_successor"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"

MARGIN_CAPABLE = "national_margin_ridge"
CONTROL_ONLY = frozenset({"national_base_rate"})
PROBABILITY_ONLY = frozenset(
    {"national_base_rate", "national_elo", "prior_only", "national_logistic_l2"}
)

PREDECESSORS: dict[str, dict[str, str]] = {
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

TAMU_TEAM_ID = "SRC-002:TEAM:245"


class HistoricalPairSuccessorError(ValueError):
    """Raised when a historical pair cannot be converted honestly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    lines = [
        json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for row in rows
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def load_predecessor(
    data_root: Path, cycle: str
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    spec = PREDECESSORS[cycle]
    path = data_root / spec["relative_path"]
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != spec["sha256"]:
        raise HistoricalPairSuccessorError(
            f"predecessor hash drift for cycle {cycle}: {digest} != {spec['sha256']}"
        )
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return rows, spec


def _finite_probability(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        return None
    return number


def _finite_margin(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def succeed_pair(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    spec: Mapping[str, str],
    source_cycle: str,
) -> dict[str, Any]:
    candidate = str(left["candidate_id"])
    if candidate != str(right["candidate_id"]):
        raise HistoricalPairSuccessorError("pair candidate mismatch")
    game_id = str(left[spec["game_key"]])
    if game_id != str(right[spec["game_key"]]):
        raise HistoricalPairSuccessorError("pair game mismatch")
    team_a = str(left["canonical_team_id"] or "")
    team_b = str(right["canonical_team_id"] or "")
    if not team_a or not team_b or team_a == team_b:
        raise HistoricalPairSuccessorError(
            "pair team identities are empty or identical"
        )

    p_a_raw = _finite_probability(left.get(spec["probability_key"]))
    p_b_raw = _finite_probability(right.get(spec["probability_key"]))
    m_a_raw = _finite_margin(left.get(spec["margin_key"]))
    m_b_raw = _finite_margin(right.get(spec["margin_key"]))

    probability_link = "NOT_EMITTED"
    p_a: float | None = None
    p_b: float | None = None
    abstention: str | None = None
    if p_a_raw is None or p_b_raw is None:
        abstention = "ABSTAIN_MISSING_REQUIRED_FEATURES"
    elif candidate in CONTROL_ONLY:
        p_a = 0.5
        p_b = 0.5
        probability_link = "FIXED_CONTROL"
    elif candidate == "national_elo":
        if abs(p_a_raw + p_b_raw - 1.0) <= 1e-8:
            p_a = p_a_raw
            p_b = 1.0 - p_a
            probability_link = "ELO_COMPLEMENT_PRESERVED"
        else:
            normalized = normalize_pair_probabilities(p_a_raw, p_b_raw)
            p_a = float(normalized["p_a_game"])
            p_b = float(normalized["p_b_game"])
            probability_link = "PAIR_NORMALIZED"
    else:
        if p_a_raw == 0.0 or p_b_raw == 0.0:
            abstention = "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        else:
            normalized = normalize_pair_probabilities(p_a_raw, p_b_raw)
            p_a = float(normalized["p_a_game"])
            p_b = float(normalized["p_b_game"])
            probability_link = "PAIR_NORMALIZED"

    m_a: float | None = None
    m_b: float | None = None
    margin_support = "NOT_SUPPORTED_BY_MODEL_FAMILY"
    if candidate == MARGIN_CAPABLE:
        if m_a_raw is None or m_b_raw is None:
            margin_support = "NOT_SUPPORTED_MISSING_SAVED_MARGIN"
        else:
            m_a = (m_a_raw - m_b_raw) / 2.0
            m_b = -m_a
            margin_support = "ANTISYMMETRIC_PROJECTION_OF_SAVED_TEAM_MARGINS"

    pair_ok = p_a is not None and p_b is not None and abs(p_a + p_b - 1.0) <= 1e-12
    if m_a is not None and (m_b is None or abs(m_a + m_b) > 1e-12):
        m_a = None
        m_b = None
        margin_support = "NOT_SUPPORTED_NON_ANTISYMMETRIC_PROJECTION"
    if not pair_ok and abstention is None:
        abstention = "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        p_a = None
        p_b = None
    joint = False

    def _oriented(
        source: Mapping[str, Any],
        *,
        probability: float | None,
        margin: float | None,
        counterpart_team_id: str,
    ) -> dict[str, Any]:
        observed_win = source.get("observed_win")
        observed_label: float | None
        if isinstance(observed_win, bool):
            observed_label = 1.0 if observed_win else 0.0
        else:
            observed_label = None
        row = {
            "candidate_id": candidate,
            "canonical_game_id": game_id,
            "canonical_team_id": source["canonical_team_id"],
            "counterpart_canonical_team_id": counterpart_team_id,
            "source_cycle": source_cycle,
            "grain": "GAME_DERIVED_ORIENTED",
            "predecessor_predicted_win_probability": source.get(
                spec["probability_key"]
            ),
            "predecessor_predicted_margin": source.get(spec["margin_key"]),
            "predicted_win_probability": None
            if probability is None
            else round(probability, 10),
            "predicted_margin": None if margin is None else round(margin, 10),
            "observed_win": observed_win if isinstance(observed_win, bool) else None,
            "observed_label": observed_label,
            "observed_margin": source.get("observed_margin"),
            "probability_link": probability_link,
            "margin_support": margin_support,
            "pair_coherence": pair_ok,
            "joint_probability_margin_interval": joint,
            "control_only": candidate in CONTROL_ONLY,
            "trust_classification": SHADOW_CLASSIFICATION,
            "successor_contract_id": CONTRACT_ID,
            "predecessor_rewritten": False,
            "abstention_reason": abstention,
        }
        for extra in (
            "fold_id",
            "chronological_ordinal",
            "evaluation_season",
            "target",
        ):
            if extra in source:
                row[extra] = source[extra]
        return row

    oriented_a = _oriented(
        left, probability=p_a, margin=m_a, counterpart_team_id=team_b
    )
    oriented_b = _oriented(
        right, probability=p_b, margin=m_b, counterpart_team_id=team_a
    )
    game = {
        "candidate_id": candidate,
        "canonical_game_id": game_id,
        "team_a_canonical_team_id": team_a,
        "team_b_canonical_team_id": team_b,
        "source_cycle": source_cycle,
        "grain": "GAME",
        "probability_a": None if p_a is None else round(p_a, 10),
        "probability_b": None if p_b is None else round(p_b, 10),
        "expected_margin_a": None if m_a is None else round(m_a, 10),
        "expected_margin_b": None if m_b is None else round(m_b, 10),
        "observed_win_a": oriented_a["observed_win"],
        "observed_win_b": oriented_b["observed_win"],
        "pair_coherence": pair_ok,
        "joint_probability_margin_interval": joint,
        "probability_link": probability_link,
        "margin_support": margin_support,
        "control_only": candidate in CONTROL_ONLY,
        "trust_classification": SHADOW_CLASSIFICATION,
        "successor_contract_id": CONTRACT_ID,
        "abstention_reason": abstention,
    }
    return {"game": game, "oriented": [oriented_a, oriented_b]}


def _unique_game_metrics(oriented: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_candidate: dict[str, list[tuple[float, float]]] = defaultdict(list)
    skipped_tie = 0
    skipped_missing = 0
    seen: set[tuple[str, str]] = set()
    for row in oriented:
        candidate = str(row["candidate_id"])
        game_id = str(row["canonical_game_id"])
        key = (candidate, game_id)
        if key in seen:
            continue
        seen.add(key)
        probability = row.get("predicted_win_probability")
        label = row.get("observed_label")
        if probability is None or label is None:
            skipped_missing += 1
            continue
        by_candidate[candidate].append((float(probability), float(label)))
    metrics = []
    for candidate, pairs in sorted(by_candidate.items()):
        predicted = [item[0] for item in pairs]
        observed = [item[1] for item in pairs]
        metrics.append(
            {
                "candidate_id": candidate,
                "unique_games": len(pairs),
                "brier": brier_score(predicted, observed),
                "log_loss": log_loss(predicted, observed),
                "accuracy": accuracy(predicted, observed),
                "mean_predicted": sum(predicted) / len(predicted)
                if predicted
                else None,
                "observed_rate": sum(observed) / len(observed) if observed else None,
            }
        )
    return {
        "by_candidate": metrics,
        "skipped_missing_or_abstained_games": skipped_missing,
        "skipped_tie_games": skipped_tie,
        "denominator": "UNIQUE_GAME_NOT_ORIENTED_ROW",
    }


def build_cycle_successor(
    *,
    data_root: Path,
    cycle: str,
) -> dict[str, Any]:
    rows, spec = load_predecessor(data_root, cycle)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["candidate_id"]), str(row[spec["game_key"]]))].append(row)
    games: list[dict[str, Any]] = []
    oriented: list[dict[str, Any]] = []
    malformed = 0
    failing_pairs = 0
    for (_candidate, _game_id), pair in sorted(groups.items()):
        if len(pair) != 2:
            malformed += 1
            continue
        left, right = sorted(pair, key=lambda item: str(item["canonical_team_id"]))
        built = succeed_pair(left, right, spec=spec, source_cycle=cycle)
        games.append(built["game"])
        oriented.extend(built["oriented"])
        if not built["game"]["pair_coherence"]:
            failing_pairs += 1
    metrics = _unique_game_metrics(oriented)
    tamu_focus = [
        row
        for row in oriented
        if row.get("canonical_team_id") == TAMU_TEAM_ID
        and row.get("candidate_id") == MARGIN_CAPABLE
    ]
    coverage: dict[str, dict[str, int]] = {}
    for game in games:
        bucket = coverage.setdefault(
            str(game["candidate_id"]),
            {"opportunity": 0, "coherent": 0, "abstained": 0, "control_only": 0},
        )
        bucket["opportunity"] += 1
        if game.get("control_only"):
            bucket["control_only"] += 1
        if game.get("pair_coherence"):
            bucket["coherent"] += 1
        else:
            bucket["abstained"] += 1
    return {
        "cycle": cycle,
        "predecessor": {
            "relative_path": spec["relative_path"],
            "sha256": spec["sha256"],
            "rows": len(rows),
            "rewritten": False,
        },
        "game_rows": games,
        "oriented_rows": oriented,
        "malformed_groups": malformed,
        "failing_pairs": failing_pairs,
        "coverage": coverage,
        "metrics": metrics,
        "tamu_ridge_oriented_rows": tamu_focus,
    }


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
    cycles: Sequence[str] = ("20", "21"),
) -> dict[str, Any]:
    cycle_payloads: dict[str, Any] = {}
    files: dict[str, bytes] = {}
    for cycle in cycles:
        built = build_cycle_successor(data_root=data_root, cycle=cycle)
        game_bytes = jsonl_bytes(built["game_rows"])
        oriented_bytes = jsonl_bytes(built["oriented_rows"])
        files[f"cycle_{cycle}_game_rows"] = game_bytes
        files[f"cycle_{cycle}_oriented_rows"] = oriented_bytes
        cycle_payloads[cycle] = {
            "predecessor": built["predecessor"],
            "malformed_groups": built["malformed_groups"],
            "failing_pairs": built["failing_pairs"],
            "coverage": built["coverage"],
            "metrics": built["metrics"],
            "tamu_ridge_oriented_row_count": len(built["tamu_ridge_oriented_rows"]),
            "game_row_count": len(built["game_rows"]),
            "oriented_row_count": len(built["oriented_rows"]),
            "payloads": {
                "game_rows": {
                    "sha256": sha256_bytes(game_bytes),
                    "bytes": len(game_bytes),
                    "row_count": len(built["game_rows"]),
                },
                "oriented_rows": {
                    "sha256": sha256_bytes(oriented_bytes),
                    "bytes": len(oriented_bytes),
                    "row_count": len(built["oriented_rows"]),
                },
            },
        }
        if built["failing_pairs"] != 0 or built["malformed_groups"] != 0:
            raise HistoricalPairSuccessorError(
                f"cycle {cycle} successor is not pair-coherent: "
                f"failing={built['failing_pairs']} malformed={built['malformed_groups']}"
            )

    dataset_seed = {
        "contract_id": CONTRACT_ID,
        "cycles": {cycle: cycle_payloads[cycle]["payloads"] for cycle in cycles},
        "predecessor_hashes": {
            cycle: PREDECESSORS[cycle]["sha256"] for cycle in cycles
        },
    }
    dataset_identity = sha256_bytes(
        json.dumps(dataset_seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    payload_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / dataset_identity
    payload_root.mkdir(parents=True, exist_ok=True)
    relative_payloads: dict[str, dict[str, Any]] = {}
    for cycle in cycles:
        for kind in ("game_rows", "oriented_rows"):
            name = f"cycle_{cycle}_{kind}.jsonl"
            content = files[f"cycle_{cycle}_{kind}"]
            (payload_root / name).write_bytes(content)
            relative = f"canonical/{PAYLOAD_SLUG}/sha256/{dataset_identity}/{name}"
            cycle_payloads[cycle]["payloads"][kind]["relative_path"] = relative
            relative_payloads[f"cycle_{cycle}_{kind}"] = cycle_payloads[cycle][
                "payloads"
            ][kind]

    gate = {
        "artifact_type": "HISTORICAL_SAVED_PAIR_GAME_GRAIN_SUCCESSOR_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "dataset_identity": dataset_identity,
        "predecessor_payloads_rewritten": False,
        "joint_probability_margin_interval": False,
        "joint_path_note": (
            "Saved C20/C21 files do not carry fold-local Normal residual scale; "
            "joint Week 1 successor remains the margin/interval path."
        ),
        "publication_label": SHADOW_CLASSIFICATION,
        "cycles": cycle_payloads,
        "payloads": relative_payloads,
        "scientific_nonclaims": [
            "Does not rewrite historical C20/C21 saved payloads.",
            "Does not restore original team-grain metrics as authoritative.",
            "Does not certify Week 1 prospective skill or production credibility.",
            "Does not open the all-cycle trust gate or operator hold.",
            "Does not claim a joint Normal probability/margin/interval path for C20/C21.",
        ],
    }
    gate["gate_identity"] = sha256_bytes(
        json.dumps(
            {key: value for key, value in gate.items() if key != "gate_identity"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return gate
