"""Audit successor staff cells, adapters, missing margins, and neutrals."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.contracts_v2 import (  # noqa: E402
    ContractV2Error,
    staff_snapshot_v2_from_bas_matrix_cell,
)
from aggie_analytics.cycle30.kernel_model import (  # noqa: E402
    CANDIDATES,
    EVAL_SEASONS,
    TRAIN_SEASONS,
    favorite_direction,
    fold_local_fit,
    swap_participants,
    design_matrix,
    predict_proba,
    fit_logistic,
    RIDGE_LAMBDA,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def staff_audit() -> dict[str, Any]:
    cells = load_jsonl(OUT / "science" / "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl")
    people = load_jsonl(OUT / "science" / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl")
    programs = {str(row.get("program_id")): row for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")}
    duplicate_cells = []
    multi_hc = []
    adapter_ok = 0
    adapter_fail = 0
    by_program_role: dict[tuple[str, str], list[str]] = defaultdict(list)
    for cell in cells:
        names = [
            str(item.get("person") or "")
            for item in (cell.get("episode_refs") or [])
            if isinstance(item, dict)
        ]
        folded = [name.casefold() for name in names if name]
        if len(folded) != len(set(folded)):
            duplicate_cells.append(
                {
                    "program_id": cell.get("program_id"),
                    "role": cell.get("role"),
                    "people": names,
                }
            )
        if cell.get("role") == "head_coach" and len(set(folded)) > 1:
            multi_hc.append(
                {
                    "program_id": cell.get("program_id"),
                    "display_name": (programs.get(str(cell.get("program_id"))) or {}).get(
                        "display_name"
                    ),
                    "people": names,
                    "disposition": cell.get("disposition"),
                }
            )
        try:
            staff_snapshot_v2_from_bas_matrix_cell(cell)
            adapter_ok += 1
        except ContractV2Error:
            adapter_fail += 1
        for name in folded:
            by_program_role[(str(cell.get("program_id")), str(cell.get("role")))].append(name)
    fbs = sum(1 for row in people if (programs.get(str(row.get("program_id"))) or {}).get("classification") == "fbs")
    fcs = sum(1 for row in people if (programs.get(str(row.get("program_id"))) or {}).get("classification") == "fcs")
    return {
        "matrix_cells": len(cells),
        "duplicate_person_string_cells": duplicate_cells,
        "duplicate_person_string_cell_count": len(duplicate_cells),
        "multiple_hc_programs": multi_hc,
        "multiple_hc_program_count": len(multi_hc),
        "adapter_ok": adapter_ok,
        "adapter_fail": adapter_fail,
        "parsed_people_fbs": fbs,
        "parsed_people_fcs": fcs,
        "as_of_utc_values": sorted({str(row.get("as_of_utc")) for row in cells}),
    }


def kernel_audit() -> dict[str, Any]:
    rows = load_jsonl(PRED / "PIT_KERNEL_ROWS.jsonl")
    design = {
        str(row["canonical_game_id"]): row
        for row in load_jsonl(PRED / "KERNEL_DESIGN_MATRIX_SAMPLE.jsonl")
    }
    historical = []
    missing_margin = []
    for row in rows:
        season = int(row.get("season") or 0)
        if season < 2013 or season > 2023:
            continue
        clone = dict(row)
        site = design.get(str(row.get("canonical_game_id"))) or {}
        if clone.get("ordinary_home_exposure") is None:
            clone["ordinary_home_exposure"] = site.get("ordinary_home_exposure")
        clone["site_class"] = site.get("site_class") or clone.get("site_class")
        historical.append(clone)
        home = (clone.get("home_features") or {}).get("pit_prior_margin_mean")
        away = (clone.get("away_features") or {}).get("pit_prior_margin_mean")
        if home is None or away is None:
            missing_margin.append(
                {
                    "canonical_game_id": clone.get("canonical_game_id"),
                    "season": season,
                    "home_margin": home,
                    "away_margin": away,
                    "disposition": "EXCLUDED_MISSING_NUMERIC_PREDICTOR",
                }
            )
    fits = []
    for candidate in CANDIDATES:
        fit = fold_local_fit(historical, candidate=candidate)
        fits.append(
            {
                "candidate": candidate,
                "train_games": fit["train_games"],
                "eval_games": fit["eval_games"],
                "excluded_train": fit["excluded_train"],
                "excluded_eval": fit["excluded_eval"],
                "weights": fit["weights"],
                "feature_version": fit["feature_version"],
                "no_winner_selected": True,
            }
        )
    neutrals = [
        row
        for row in historical
        if int(row["season"]) in set(EVAL_SEASONS)
        and (
            row.get("site_class") == "NEUTRAL"
            or row.get("ordinary_home_exposure") == 0
        )
    ]
    permutation = []
    for candidate in CANDIDATES:
        eligible = []
        for row in neutrals:
            try:
                x, _, _, excluded = design_matrix([row], candidate)
            except Exception:
                continue
            if len(x) == 0:
                continue
            eligible.append(row)
        if not eligible:
            permutation.append(
                {
                    "candidate": candidate,
                    "neutral_eval_rows": 0,
                    "status": "NO_ELIGIBLE_NEUTRAL_ROWS",
                }
            )
            continue
        x_train, y_train, _, _ = design_matrix(
            [row for row in historical if int(row["season"]) in set(TRAIN_SEASONS)],
            candidate,
        )
        ridge = 0.0 if candidate == "intercept_only" else RIDGE_LAMBDA
        weights = fit_logistic(x_train, y_train, ridge=ridge)
        base_x, _, _, _ = design_matrix(eligible, candidate)
        base = predict_proba(base_x, weights)
        swapped = [swap_participants(row) for row in eligible]
        swap_x, _, _, _ = design_matrix(swapped, candidate)
        swap_p = predict_proba(swap_x, weights)
        team_keyed = np.abs((1.0 - swap_p) - base)
        directions = [favorite_direction(float(p)) for p in base]
        permutation.append(
            {
                "candidate": candidate,
                "neutral_eval_rows": len(eligible),
                "participant_swap_max_team_keyed_delta": round(
                    float(np.max(team_keyed)), 8
                ),
                "participant_swap_mean_team_keyed_delta": round(
                    float(np.mean(team_keyed)), 8
                ),
                "tied_probability_no_direction": sum(
                    1 for item in directions if item == "NO_DIRECTION"
                ),
                "ordinary_home_exposure_all_zero": all(
                    float(row.get("ordinary_home_exposure") or 0) == 0.0
                    for row in eligible
                ),
            }
        )
    return {
        "historical_rows_2013_2023": len(historical),
        "missing_margin_games": missing_margin,
        "missing_margin_count": len(missing_margin),
        "fits": fits,
        "neutral_eval_count": len(neutrals),
        "neutral_permutations": permutation,
        "week1_outcomes_not_used_for_selection": True,
        "exposed_seasons_excluded": [2024, 2025],
        "trust_classification": "UNTRUSTED_SHADOW",
    }


def main() -> int:
    staff = staff_audit()
    kernel = kernel_audit()
    write_json(OUT / "science" / "CYCLE32_STAFF_CELL_AUDIT.json", staff)
    write_json(OUT / "science" / "CYCLE32_KERNEL_NEUTRAL_AUDIT.json", kernel)
    print(
        json.dumps(
            {
                "duplicate_cells": staff["duplicate_person_string_cell_count"],
                "multi_hc": staff["multiple_hc_program_count"],
                "adapter_fail": staff["adapter_fail"],
                "missing_margin": kernel["missing_margin_count"],
                "neutral_eval": kernel["neutral_eval_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
