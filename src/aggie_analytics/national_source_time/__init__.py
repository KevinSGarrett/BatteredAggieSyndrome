"""Installed read-only national 2016-2023 source-time evidence and explicit-cutoff consumer (BAT-712, Cycle #40 TP40-A01).

The query module uses only the standard library. It opens a content-addressed SQLite database read-only, verifies its
database identity before answering and serves the exact delivered source-time records together with cutoff decisions
computed from their separately preserved clocks. Nothing is PIT admitted: every decision carries pit_admission
NOT_ADMITTED and a request that requires PIT admission is refused.
"""
