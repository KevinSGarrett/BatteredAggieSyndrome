# Data Context — through W06

Accepted flow remains immutable source evidence → validation/quarantine → canonical effective-dated observations → PIT/as-of state → PIT-safe features → immutable model/forecast artifacts.

W06 current source baseline is `docs/data_research/w06/DATA_UNIVERSE_MASTER.csv`. SportsDataverse and CFBD remain practical national foundations; official NCAA/conference/school sources provide governing truth, validation, recent availability reports and lower-division/regulatory evidence.

New protected semantics: mutable report publication/version history, weather provider/model/run/lead/valid-time history, explicit availability policy scope/noncoverage, effective-dated roster/eligibility/transfer regulatory environment, and upstream provenance for derived providers.

Early local analytical default remains native raw + Parquet + DuckDB; PostgreSQL is conditional pending W07 transaction requirements.

## W08 PIT update
W08 freezes a bitemporal data contract. Every future materialized field/observation must distinguish public/system knowledge time from real-world validity/event time where applicable. Unknown temporal semantics are ineligible/review-required, not silently imputed into PIT features.
