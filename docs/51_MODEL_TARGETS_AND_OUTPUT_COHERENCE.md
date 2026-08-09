
# W16 Model Targets and Output Coherence

Wave 16 freezes **semantics**, not empirical winners.

## Source-of-truth output
The preferred forecasting contract is a coherent predictive distribution over the two teams' scores. Margin, total, win/loss probabilities, and other compatible probabilities must derive from that distribution or be reconciled to it.

The system must never publish mutually contradictory values such as:
- a 58% A&M win probability while the claimed joint score distribution implies 44%;
- an expected margin that does not equal expected A&M score minus expected opponent score;
- score point estimates that are labeled as distribution expectations but disagree with the stored distribution.

## Targets
Final team and opponent scores are nonnegative integer labels including overtime. Margin and total are deterministic derivations. Final win/loss labels derive from final margin.

If a statistical architecture models **regulation** scores and therefore permits tie mass, overtime resolution must be explicit. Tie mass cannot simply be discarded or silently split 50/50.

## BAS
W15 label semantics remain frozen:
`performance_residual = actual_A&M_margin - BAS_independent_expected_A&M_margin`.

The 3/7/14/21 thresholds are unchanged. W16 may define coherent BAS probability interfaces, but it does not establish BAS significance or calibration. Any BAS probability output must remain nested:
`P(>=21) <= P(>=14) <= P(>=7) <= P(>=3)`.

## No W16 empirical claim
No target architecture is declared superior from synthetic/reference tests. W17 defines protected evaluation protocol; materialized implementation/results remain later evidence.
