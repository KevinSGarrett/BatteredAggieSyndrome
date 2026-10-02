"""Installed read-only national Division I population consumer (BAT-710, Cycle #38 TP38-A01-07).

The query module uses only the standard library. It opens a content-addressed SQLite database read-only, verifies
its manifest identity before answering, and returns explicit cells (missing, unresolved, conflicting and
single-source rows included) rather than a filtered view.
"""
