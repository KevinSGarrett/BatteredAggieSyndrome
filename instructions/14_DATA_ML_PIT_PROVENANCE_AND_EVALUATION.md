# Data, ML, PIT, Provenance, and Protected Evaluation Governance

This document is a navigation and execution contract. The canonical scientific definitions remain in the W25 governance, temporal/entity/feature/model/BAS documents, registries, and protected judging seal.

The machine companion is `policies/protected_scope_policy.json`.

## Point-in-time and target-game exclusion

Historical prediction inputs must be reconstructible as of the declared prediction cutoff.

Required principles:

- Keep knowledge/publication/retrieval time separate from effective/valid/event time.
- Use the protected PIT gateway; features may not query mutable current/provider state directly.
- Unknown eligibility fails closed.
- Missing official reports do not imply healthy/available.
- Later corrections/revisions do not rewrite the evidence visible to an earlier prediction.
- Realized weather is not a substitute for historically issued forecasts.
- Closing lines or postgame outcomes are not pregame features unless a specifically defined forecast lane/cutoff legitimately permits them.
- The target game’s own historical output, same-game snaps, and any future outcome are excluded by identity as defense in depth.
- Eventual NFL draft outcomes or later career facts cannot become earlier historical roster features.

Any PIT/leakage failure blocks promotion/publication. Do not “fix” it by weakening the test.

## Immutable evidence and provenance

For mutable or external sources, preserve:

- source/provider and source record identity;
- retrieval/publication/effective/observed timestamps as applicable;
- content/hash/version/snapshot ID;
- access/license classification;
- parser/schema version;
- transformation lineage;
- canonical-entity resolution state;
- prediction cutoff and eligibility decision;
- data quality/missingness/rejection evidence.

Raw/source snapshots and published forecast snapshots are immutable. Corrections create new versions linked to prior versions; they do not overwrite historical state.

Model/feature/evaluation artifacts must identify code commit, environment/dependency lock, data snapshot, feature registry version, split/protocol, random seeds where relevant, and output hashes.

## Canonical identity

There is one canonical entity truth for teams, games, players, coaches, venues, seasons, sources, and relationships. A&M has higher-resolution evidence, not a separate identity system.

- Unresolved/ambiguous mappings remain explicit.
- Do not enable fuzzy auto-accept without a labeled population benchmark and threshold evidence.
- A source ID mapping must be effective-dated where identity/role changes over time.
- Entity-resolution quality is measured at population scale, not inferred from a few fixtures.

## Feature lifecycle

Raw fields are candidates, not production features. Preserve lifecycle states and evidence history:

- CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED as defined by canonical registries;
- grain and PIT eligibility;
- transformation and missingness semantics;
- redundancy/collinearity and stability;
- incremental ablation under chronological evaluation;
- lane restrictions such as pure-football versus market-augmented;
- rights/resource/operational feasibility.

Do not feed hundreds of raw fields directly into a model or promote based on correlation/importance alone. BANNED leakage/rights fields cannot re-enter because a model likes them.

## Baselines before complexity

Required progression:

1. deterministic/simple strength and score baselines;
2. logistic/linear/statistical baselines;
3. approved boosting challengers;
4. calibration/coherence/uncertainty;
5. only then complex neural/sequence/graph approaches through the advanced admission gate.

A complex candidate must outperform a strong simpler baseline under the same protected chronological protocol with sufficient stability, resource feasibility, and operational benefit. “More sophisticated” is not evidence.

## Protected evaluation and research separation

- Freeze protected periods, metrics, thresholds, promotion rules, and judging code before protected results.
- Development/HPO uses development evidence only.
- Protected results are not iterative tuning feedback.
- Candidate/research agents cannot edit judges, ground truth, historical results, or acceptance thresholds.
- A failed candidate or null result is valid evidence and must be retained.
- Promotion requires the canonical acceptance/promotion state transition and evidence packet.
- No production champion is declared from synthetic starter tests.

## Calibration and coherent outputs

The product requires win probabilities, projected scores/margins/distributions, uncertainty, matchup explanations, availability scenarios, and BAS outputs to be mutually coherent under their contracts.

Evaluate not only discrimination/point error but:

- probabilistic scoring and calibration;
- joint score likelihood/coherence;
- uncertainty/OOD behavior;
- temporal, conference, opponent, venue, season-phase, and A&M slices;
- missingness/source regime sensitivity;
- operational reproducibility and resource cost.

Do not optimize a headline metric while violating probability/score coherence or calibration.

## Texas A&M specialization

A&M receives disproportionately deep state, source resolution, calibration, scenario analysis, and evaluation. The national model still teaches football behavior and remains the comparison baseline.

Required safeguards:

- mandatory national/no-adjustment comparator;
- no hard-coded Kyle Field/fan-narrative bonus;
- no guaranteed residual adapter or nonzero adjustment;
- coaching/roster/regime changes modeled point-in-time;
- old A&M seasons cannot masquerade as current team state;
- specialization must earn incremental lift and calibration under protected slices.

A null or unstable specialization result is acceptable and must not be hidden.

## BAS / Aggie Excess

BAS is not simply loss probability. Preserve the canonical scientific definition, cross-fitted expectation generation, peer/regime comparisons, calibration, component/subtype rules, and null-result policy.

The agent must not:

- use realized target outcomes to construct the pregame expectation;
- hand-weight fan narratives into the target;
- choose thresholds after protected results;
- presume A&M has a persistent excess effect;
- convert theme/branding into a requirement for statistical significance.

If the effect is null, report null. The product can still provide calibrated forecasts and honest BAS probabilities/components under the accepted contract.

## Data/source gaps

Historical injury/depth/availability, private-school resources, officiating, proprietary charting, and lower-division coverage can be asymmetric or incomplete. Represent:

- confidence and source coverage;
- missing/unknown states;
- replacement/usage uncertainty;
- source/regime changes;
- graceful fallback without fabricated values.

Absence of evidence is not negative evidence.

## Resource-aware research

Respect the declared local machines, target host, RAM/GPU/disk/API budgets, and unresolved THR values.

- Benchmark on actual target hardware before claiming thresholds.
- Use staged samples/development slices before full expensive runs.
- Cache immutable intermediates when rights permit.
- Stop unpromising HPO/challengers under precommitted pruning/resource rules.
- Do not assume unlimited cloud/GPU capacity.
- Record runtime, peak memory, artifact size, and reproducibility where relevant.

## Promotion and publication stop conditions

Stop and record evidence when:

- source rights/access are unresolved;
- canonical identity or PIT eligibility fails;
- leakage/replay fails;
- protected judges would be exposed or changed;
- artifact provenance is incomplete;
- model output coherence/calibration is unacceptable;
- target hardware exceeds evidence-backed limits;
- a result would require fabricated or post-hoc claims.
