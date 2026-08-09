# W20 Implementation Inventory

| Area | Maturity | Primary implementation |
|---|---|---|
| Advanced PIT state aggregation | Functional starter | `player_intelligence/advanced_state.py` |
| Common model artifact/runtime | Functional starter | `modeling/runtime.py` |
| Empirical/logistic/Elo baselines | Functional starter | `modeling/baselines.py` |
| Optional boosting boundary | Interface + injected functional path | `modeling/baselines.py` |
| Joint score distribution | Functional starter | `modeling/joint.py` + W16 coherence |
| Calibration | Functional starter | `modeling/calibration.py` |
| Ensemble | Functional starter | `modeling/ensemble.py` |
| Uncertainty carriage | Functional starter | W16 contracts + `modeling/forecast.py` |
| A&M state/specialization adapter | Functional starter | `tamu/runtime.py` |
| BAS probability interface | Functional starter | `bas/runtime.py` |
| Immutable local model registry | Functional starter | `modeling/registry.py` |
| W20 integration test/gate | Functional | `tests/test_w20_model_starter.py`, `tools/validate_w20_starter.py` |

No trained protected performance or production model selection is included.
