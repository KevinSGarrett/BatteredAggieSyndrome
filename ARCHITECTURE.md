# Research architecture

Battered Aggie Syndrome combines a national college-football research foundation with Texas A&M-specific questions. This page describes responsibilities, not a claim that every component is scientifically validated.

## From evidence to a research result

1. **Capture:** preserve source responses, request identity, and actual retrieval time. Provider credentials and bulk data stay outside the repository.
2. **Resolve:** connect teams, players, coaches, venues, and games through authoritative identifiers. Ambiguous records remain unresolved.
3. **Construct pregame state:** admit only information with defensible availability before the target cutoff. Publication, event, retrieval, and forecast times are different concepts.
4. **Build national expectations:** use chronological model development, explicit feature requirements, and independent evaluation.
5. **Compare A&M with peers:** measure residuals, shortfall severity, sensitivity, and repeated patterns. An A&M adjustment is not assumed.
6. **Freeze and inspect:** retain immutable snapshot identities, uncertainty, coverage, and abstention reasons.
7. **Serve approved snapshots:** the optional local API reads existing snapshots; it does not train a model or acquire live data on request.

## Implemented software boundaries

| Package | Responsibility |
|---|---|
| `aggie_analytics.data` | Source-specific acquisition and normalization research |
| `aggie_analytics.temporal` | Temporal and cutoff-related utilities |
| `aggie_analytics.features` | Feature construction and domain-specific research |
| `aggie_analytics.modeling` | National model, evaluation, and forecast experiments |
| `aggie_analytics.scientific_reference` | Separate numerical reference implementations |
| `aggie_analytics.orchestration` | Snapshot publication and related research workflow primitives |
| `aggie_analytics.product` | Snapshot contracts, read-only repository, service, and dashboard view models |
| `aggie_analytics.api` | Optional FastAPI adapter |

These are code locations, not independent certifications of correctness. See [research status](docs/public/STATUS.md).

## Data and output boundaries

- A snapshot directory is not a raw data lake; the serving interface expects published forecast JSON files.
- A provider's API response is not automatically point-in-time feature authority.
- A passed reconstruction check is not proof that the underlying scientific specification is correct.
- A UI can display a stored number without validating the model that produced it.
- Market benchmarks must be labeled separately from an independent model.
- Coaching, availability, weather, travel, and recruiting require source-specific admission; see [data domains](docs/public/DATA_DOMAINS.md).

The artwork on the [project overview](README.md) depicts the wider research vision, including scenario analysis and reports still under development.
