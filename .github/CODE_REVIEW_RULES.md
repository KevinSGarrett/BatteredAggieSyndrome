# Code Review Rules

These scientific invariants apply to every pull request. They do not authorize BAS, champion, production, or credibility claims.

`AGENTS.md` is a protected source-reference invariant (`SRCREF-01994`). These rules are the Cycle #25.5 repository-wide code-review contract and are mirrored into `.cursor/BUGBOT.md` and `.github/codex/prompts/scientific-review.md`.

1. **PIT / known-at authority.** Features and labels must be justified by evidence known at the declared cutoff. Missingness is not feature authority. Unproven ranking or mutable venue vintages remain excluded.
2. **Target-game exclusion.** Do not read or fit on a target outcome before the applicable scoring authority permits it. Do not backfill missed checkpoints.
3. **Current-opponent binding.** Week 1 / current-contest rows must resolve the actual opponent from current contest authority. Do not copy terminal historical opponent, conference, FBS, rank, or season-to-date fields into a current target.
4. **Game-grain pair coherence.** Build predictions at game grain, then derive oriented rows. `P(home)+P(away)=1`, `margin_home+margin_away=0`, and favorite directions must agree. Include neutral contests.
5. **Probability / margin / distribution coherence.** Probability, margin, and interval presented together must come from the same declared distribution. Incoherent candidates emit `ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE`.
6. **Immutable forecasts and checkpoints.** Do not rewrite frozen predecessor forecasts. Capture T-24H / T-90M only at actual deadlines. While the scientific-trust gate is closed, fitted outputs are `UNTRUSTED_SHADOW` or `ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED`.
7. **Protected exposure.** 2024/2025 are historically exposed and are not sealed, blind, or protected for model selection. Keep `RETAIN_PROTECTED_LANE_BLOCKED` until explicit user activation of a replacement protocol.
8. **Report / artifact agreement.** Narrative claims must match committed fields, identities, and counts. Unresolved `BAT-XXX` placeholders block the affected artifact.
9. **Producer / validator independence.** A validator that imports producer scientific helpers cannot authorize `SEMANTICALLY_AUDITED` or higher. Independent semantic reconstruction is required for trust recovery.
