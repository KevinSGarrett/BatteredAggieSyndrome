"""Installed read-only national 2016-2023 FBS retrospective history-prefix consumer (BAT-711, Cycle #39 TP39-A01).

The query module uses only the standard library. It opens a content-addressed SQLite database read-only, verifies
its database identity before answering and serves the exact delivered payload records. Every record is
RETROSPECTIVE_OBSERVATION_ONLY and PIT_ELIGIBILITY_NOT_ESTABLISHED; a request that requires PIT eligibility is
refused.
"""
