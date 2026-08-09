# Schema Discovery and Reconciliation — Wave 09

The scanner records observed structure; it does not execute source-provided code or infer temporal safety from values. CSV, JSON and JSONL are supported with the standard library. Parquet is optional when `pyarrow` is already available; Wave 09 does not make it a mandatory dependency.

Scanner output separates **documented type** from **observed type**, records scan depth, non-null/missing counts and nested JSON paths, and is deterministic for the same input and scan limit.

Precedence: verified temporal classification > explicit source contract > observed scanner metadata > heuristic review. A scanner cannot convert `REVIEW_REQUIRED` or banned fields into safe candidates.

Schema drift is detected by comparing field-path/type signatures between scans. Additions/removals/type changes create evidence for review rather than silently mutating historical schemas.
