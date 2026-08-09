# W22 Adaptive Review

## Planned objective still correct?
Yes. W21 produced immutable forecast publication artifacts, so W22 should create a read-only product boundary rather than additional training/model science.

## Material adaptation
The source conversation proposed `FastAPI` plus `Streamlit initially` and React later. W22 revises the dashboard portion: select an optional FastAPI adapter plus a build-free static dashboard using the same API/service contract. The framework-neutral serving core remains dependency-free.

## Why
- avoids two local application runtimes for one immutable artifact store;
- avoids a React/npm build toolchain before the product requires it;
- prevents UI rerun logic from becoming a hidden inference/feature path;
- preserves a replaceable framework boundary;
- keeps PostgreSQL unnecessary for the current immutable single-host read workload.

## Freshness challenge
`THR-010` remains operationally TBD. W22 will not manufacture a numeric SLA. It exposes exact snapshot age and refuses to label a snapshot current without an explicitly configured threshold; tests demonstrate visible stale behavior when a threshold is supplied.

## Future-plan impact
No wave-count or phase reallocation. W23 should own dependency pinning, CI/security, observability, runtime benchmarks and restore/retention hardening around the W22 product boundary.
