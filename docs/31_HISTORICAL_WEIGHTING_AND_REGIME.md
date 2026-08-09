# Historical Weighting and Regime Intelligence — Wave 11

## Separate two questions
An old game can remain useful to the **national football model** while becoming weak evidence for the **current identity of one team**. National statistical usefulness and current-team relevance are therefore separate weights/roles.

## Candidate weighting families
- uniform-history baseline;
- exponential recency;
- regime similarity;
- recency × regime similarity;
- change-point shrinkage;
- similarity-weighted history;
- hierarchical partial pooling.

None is declared champion in Wave 11.

## Regime similarity
Candidate evidence includes effective-dated head coach, coordinators/play caller, QB, roster continuity, scheme continuity, unit continuity and regulatory environment. Weights are not hard-coded.

## Change points
Staff/QB/scheme/roster changes can create regime breaks, but the system must not automatically erase history. A detected change may instead:
- reduce pre-change relevance;
- increase epistemic uncertainty;
- increase shrinkage toward broader priors.

Statistical performance shifts are also candidates, but data-coverage/schema breaks must be distinguished from true football changes.

## A&M
The source conversation's idea that an old A&M game can remain nationally useful while having low current-A&M relevance is preserved. Exact A&M-specific weighting belongs to W14/W17.
