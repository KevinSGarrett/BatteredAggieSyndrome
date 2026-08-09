# W20 Adaptive Review

## Is the planned objective still correct?
Yes. W20 remains the correct point to turn W16/W17 model science and W19 PIT-safe features into functional starter runtime boundaries.

## Dependency issue discovered
`TASK-087` is a W20 critical gate but depends on W19-owned `TASK-083`–`TASK-086`, which remained PLANNED after the narrower W19 foundation gate. Clearing `TASK-087` without those dependencies would be dishonest.

**Decision:** pull `TASK-083`–`TASK-086` forward into W20, implement a minimal PIT advanced-state aggregation boundary, and then clear `TASK-087`. This changes no wave numbering and does not expand W20 into production modeling.

## Architecture challenges
- Do not install a boosting stack merely to satisfy a task title. Keep a tested optional injected backend until empirical work selects one.
- Preserve the W16 joint-score distribution as the coherent source of derived public outputs.
- Preserve W17 development/protected separation. W20 may implement evaluation/calibration interfaces but may not tune on protected results.
- Preserve W14 no-adjustment A&M baseline and W15 protected BAS anchor.

## Highest-value outcome
A dependency-light, lineage-preserving model/calibration/A&M/BAS starter that W21 can orchestrate without inventing performance or promotion evidence.
