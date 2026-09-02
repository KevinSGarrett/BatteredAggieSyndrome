# Bugbot scientific-review rules

These rules apply to every pull request. They do not authorize BAS, champion, production, or credibility claims.

## Scientific invariants

- PIT / known-at authority only. Missingness is not evidence. Rankings and mutable venue attributes remain excluded until publication/vintage evidence exists.
- Never read a target outcome before scoring authority permits it. Never backfill a missed T-24H or T-90M checkpoint.
- Bind current contest opponents from current Week 1 authority. Reject historical opponent, conference, FBS, rank, or season-to-date transplants.
- Game-grain pair coherence: P(home)+P(away)=1, margin_home+margin_away=0, favorite directions agree, neutral contests included.
- Probability, margin, and interval must come from one declared distribution. Otherwise ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE.
- Do not rewrite frozen predecessor forecasts. While the trust gate is closed, fitted outputs are UNTRUSTED_SHADOW or ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED.
- 2024/2025 are exposed, not sealed/blind/protected. Keep RETAIN_PROTECTED_LANE_BLOCKED.
- Report text must match committed artifacts. Unresolved BAT-XXX placeholders are blocking.
- Validators that import producer scientific helpers cannot authorize SEMANTICALLY_AUDITED or higher.

## Windows / path / provenance

- Use pathlib. Preserve POSIX relative paths in Git artifacts. Do not write tracked gates from tests; use temporary data roots.
- Do not commit secrets, .env contents, or restricted bulk raw payloads.
- Bind identities with canonical JSON hashes. Do not use supplied CLI time as acquisition authority.

## Review posture

Fail closed on P0/P1 scientific defects. Do not treat green unit tests as semantic correctness.
