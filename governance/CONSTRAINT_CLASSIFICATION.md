# Constraint Classification — Hardened through W05

Constraint class describes **authority/revisability**, not whether evidence has passed.

- **Level A — protected/mandatory:** changing it would violate a protected mission, correctness, governance, provenance, security, temporal-safety or accepted required behavior unless the user or permitted governance authority explicitly changes it.
- **Level B — strong default:** current preferred design/representation/tooling. It remains active until evidence-backed ADR/review replaces it.
- **Level C — hypothesis/research candidate:** cannot become production truth merely because it is documented; empirical evidence and promotion are required.

W04 separately tracks lifecycle status and acceptance evidence state. A future Level-A requirement may be `CONTRACT_DEFINED_OWNER_PENDING`; that is not a failure and not a PASS.

## W04 classification corrections
Stable IDs were preserved. W04 revised classifications/statuses for `REQ-070`, `REQ-071`, `REQ-077`, `REQ-086`, `REQ-093`, `REQ-104`, `REQ-115`, `REQ-133`, `REQ-154`, `REQ-160`, and `REQ-173`. The detailed before/after record is `CONSTRAINT_CLASSIFICATION_AUDIT.csv`.

The largest correction was removing exact modeling-method assumptions from Level A where the master architecture explicitly permits empirical alternatives. Conversely, core LLM independence (`REQ-154`) and the explicit national→A&M interface (`REQ-160`) are treated as protected boundaries while their internal implementations remain flexible.


## W05 additions
W05 introduced `REQ-216` through `REQ-240` already classified at creation: 24 Level-A planning/governance requirements and one Level-B adaptive-priority default (`REQ-240`). No prior IDs were renumbered. Current cumulative counts are **192 Level A / 41 Level B / 7 Level C**.
