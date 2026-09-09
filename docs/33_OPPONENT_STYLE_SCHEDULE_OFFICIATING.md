# Opponent Adjustment, Style, Schedule and Officiating — W13

## Opponent adjustment
Opponent-adjusted performance must use strict-prior opponent states. Same-game/future opponent outcomes are prohibited. Candidate methods include iterative residual adjustment, hierarchical partial pooling and schedule-strength context.

## Style similarity
Offense/defense style vectors and opponent analogs are experiment candidates only. They may not become manual matchup bonuses.

## Schedule stress
Candidate stress includes prior opponent strength, workload, overtime, short rest, travel and road streaks. Look-ahead may use future opponent identity/schedule only if known; future opponent performance is never eligible.

## Officiating
Historical crew data may be retained. Crew-specific upcoming-game features are allowed only when the assignment is demonstrably public before forecast cutoff.

Prohibited:
- referee X hates/favors team Y;
- raw team win rate under referee as causal evidence.

Crew tendencies remain experimental and require shrinkage plus team/opponent/style controls. When pregame assignment is unavailable, the crew-specific feature fails closed.

## Cycle #30 neutral, relocated and per-team travel schedule context

Neutral-site, international, relocated and shared-venue contests remain in the national schedule denominator. Site class is not inferred from a single famous venue. Ordinary home-field advantage is masked (`ordinary_home_exposure=0`) for verified neutrals in every actual fitted path, while orientation is retained for joins and reporting.

Per-team travel and rest are contest × participant facts. Rest (DOM-026 / CURRENT-REST) and travel (DOM-027 / CURRENT-TRAVEL) stay distinct. A designation swap on a verified neutral must not change team-keyed strength, travel, or ordinary-home exposure. Venue-change successors may correct later context; they never create an earlier known-at or repair a missed checkpoint. Unsupported cross-subdivision strength continues to abstain.
