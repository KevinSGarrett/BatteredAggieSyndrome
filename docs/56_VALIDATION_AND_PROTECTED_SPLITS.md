# W17 Validation and Protected Splits

## Status
Wave 17 freezes **validation science and protected-evaluation protocol**. It does not create or inspect trained protected benchmark results.

## Protected chronology
The canonical split protocol is `SPLIT-W17-001`.

| Lane | Seasons | Allowed use |
|---|---:|---|
| Development history | earliest qualifying through 2022 | chronological model/feature development |
| Development selection/calibration | 2023 | final development-only model/calibration/threshold evidence |
| Primary governance-protected holdout | 2024–2025 | protected test only; no tuning or threshold setting |
| Forward operational shadow | 2026+ | immutable forecast-before-outcome evaluation |

### Honesty note
By W17, 2024–2025 outcomes are public historical facts. “Protected” therefore means **the repository/model-development process is forbidden from using those seasons as tuning feedback after this seal**. It is not a claim that humans are unaware of public outcomes.

## Atomic split unit
The canonical game is the atomic split unit. Mirrored/oriented rows, derivative targets, BAS labels and market-lane representations of the same canonical game remain in the same split.

## Protected-test seal
The protected holdout may not be moved because results are disappointing. If a source/feature cannot be evaluated because of predeclared coverage limitations, the result is `UNEVALUABLE` or requires a documented ADR **before** inspecting the affected protected results. A coverage problem is not permission to search for a friendlier test period.

## Development-only tuning
Hyperparameters, feature promotion, calibration choices, warning thresholds and practical promotion thresholds are derived only from development chronology. Protected results are one-way evaluation evidence, never iterative tuning feedback.

## Future shadow evaluation
2026+ forecasts must be committed immutably before outcomes. Later retraining may create new model versions, but earlier prediction snapshots are never rewritten.
