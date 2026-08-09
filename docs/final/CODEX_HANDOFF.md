# Codex Handoff — Aggie Analytics Engine

## Canonical state
This repository is the end of the **exactly 25-wave** architecture/starter-build program. There is no Wave 26. Post-W25 work is implementation against this handoff.

## Before any mutation
1. Verify the W25 cumulative/hydration pair and SHA binding.
2. Run the full test suite.
3. Run final W25 validator and strict repository validator.
4. Read `AGENTS.md`, `docs/final/FINAL_COMPONENT_MATURITY.csv`, `FINAL_KNOWN_GAPS.md`, and `FINAL_IMPLEMENTATION_PRIORITY.md`.
5. Do not reinterpret reconnaissance samples as the historical data lake.

## Windows bootstrap
```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -p "test_*.py"
python tools/validate_w25_final.py --repo-root .
python tools/validate_repository.py --repo-root . --strict
```

Optional product adapter:
```powershell
python -m pip install -r requirements/product.lock
python tools/run_product.py
```

Target benchmark:
```powershell
.\scripts\benchmark_target.ps1
```
Do not assign THR-011/THR-012 until the authoritative target JSON exists.

## Core invariants Codex must not violate
- National historical learning + disproportionately deep Texas A&M specialization.
- PIT/known-at correctness and explicit target-game outcome exclusion.
- Immutable source snapshots and forecast snapshots.
- Canonical identity + source/evidence lineage.
- Empirical feature/model promotion; no intuition-only production adoption.
- Protected W17 split/judging/promotion rules cannot be rewritten by research automation.
- BAS headline definition and cross-fit expectation semantics remain protected.
- Pure-football and market-augmented lanes stay explicit.
- Product request paths read published snapshots only.
- No secrets/restricted bulk raw data in the repository.

## What Codex should implement first
Follow `FINAL_IMPLEMENTATION_PRIORITY.md` and `FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md`. Start with real source materialization and chronological replay, not advanced model complexity.

## Stop conditions
Stop the current implementation task and record evidence when:
- source licensing/access is ambiguous;
- a schema/ID change breaks canonical mapping;
- PIT/leakage validation fails;
- protected evaluation boundaries would be crossed;
- target machine resource use exceeds evidence-backed limits;
- a proposed architecture change would fork a source of truth.

## Final maturity statement
The repository contains substantial contracts, governance, executable reference systems and functional starters. It does **not** contain a validated trained production champion or proven Aggie Excess effect. Those claims require real data and protected chronological evaluation.
