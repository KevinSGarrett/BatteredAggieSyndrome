# Superseded Decisions

Historical ideas are preserved so later sessions do not resurrect them accidentally.

## SUP-001 — Downloadable pretrained gmalbert `.joblib` as project foundation
- **Status:** SUPERSEDED
- **Current resolution:** Unverified in later source research; train our own final models and use currently verified external models only as benchmarks/reference.
- **History:** Initial_Chat_Log_002 → Initial_Chat_Log_007
- **Governing ADR:** ADR-026

## SUP-002 — PFF as high-priority/core source
- **Status:** SUPERSEDED/DEFERRED
- **Current resolution:** PFF is deferred optional enrichment and cannot block v1/core architecture.
- **History:** Initial_Chat_Log_005 → 007; recon FINAL
- **Governing ADR:** ADR-004

## SUP-003 — Sports Info Solutions as potential advanced charting dependency
- **Status:** REJECTED
- **Current resolution:** Difficult/enterprise source removed; no core dependency.
- **History:** Initial_Chat_Log_005
- **Governing ADR:** ADR-003/004

## SUP-004 — A&M-only training dataset
- **Status:** REJECTED
- **Current resolution:** National FBS/FCS foundation provides statistical power; A&M dominates specialization/evaluation, not historical sample.
- **History:** Initial_Chat_Log_001/015
- **Governing ADR:** ADR-001

## SUP-005 — Manual feature inclusion from football intuition
- **Status:** REJECTED
- **Current resolution:** Feature usefulness is empirical with PIT walk-forward/ablation/stability.
- **History:** Initial_Chat_Log_009/012
- **Governing ADR:** ADR-008

## SUP-006 — Raw ~900 columns directly into model
- **Status:** REJECTED
- **Current resolution:** Raw fields are registry/evidence inputs transformed into target-specific PIT features.
- **History:** Initial_Chat_Log_009/012
- **Governing ADR:** ADR-008

## SUP-007 — Manual/fan BAS formula
- **Status:** REJECTED
- **Current resolution:** BAS is leakage-safe underperformance probability with scientific significance/stability tests.
- **History:** Initial_Chat_Log_006/010/011
- **Governing ADR:** ADR-002

## SUP-008 — Old A&M games directly represent current A&M
- **Status:** REJECTED
- **Current resolution:** Old games primarily teach national structure; current-team evidence is continuity/regime/roster weighted.
- **History:** Initial_Chat_Log_013
- **Governing ADR:** ADR-010

## SUP-009 — Infinite recursive lower-division strength modeling
- **Status:** REJECTED
- **Current resolution:** Terminate with increasingly coarse hierarchical priors + uncertainty.
- **History:** Initial_Chat_Log_014
- **Governing ADR:** ADR-009

## SUP-010 — Static team rating unaffected by injuries/replacements
- **Status:** REJECTED
- **Current resolution:** Current available strength incorporates player-specific availability/replacement impact.
- **History:** Initial_Chat_Log_010
- **Governing ADR:** ADR-011

## SUP-011 — Single static generic coach rating
- **Status:** REJECTED
- **Current resolution:** Use effective-dated role episodes and role-conditioned hierarchical residuals.
- **History:** Initial_Chat_Log_003/004; recon v1.1
- **Governing ADR:** ADR-012

## SUP-012 — Raw home win percentage / hard-coded 12th Man bonus
- **Status:** REJECTED
- **Current resolution:** Learn context-adjusted partial-pooled home/venue residuals.
- **History:** recon v1.1
- **Governing ADR:** ADR-027

## SUP-013 — Fixed conference transfer penalty
- **Status:** REJECTED
- **Current resolution:** Learn continuous-strength/contextual transfer translation.
- **History:** recon v1.1
- **Governing ADR:** ADR-028

## SUP-014 — Observed weather as replacement for historical forecast
- **Status:** REJECTED
- **Current resolution:** Forecast snapshots and observed/reanalysis weather are separate temporal products.
- **History:** recon v1/v1.1
- **Governing ADR:** ADR-005/006

## SUP-015 — Closing line safe for earlier-week forecast
- **Status:** REJECTED
- **Current resolution:** Only market observations known by forecast timestamp are eligible.
- **History:** recon v1.2
- **Governing ADR:** ADR-030

## SUP-016 — Large LLM/GPU as central path to accuracy
- **Status:** REJECTED
- **Current resolution:** Core problem is structured probabilistic ML/data engineering; advanced compute is later challenger research only.
- **History:** Initial_Chat_Log_018/019
- **Governing ADR:** ADR-018

## SUP-017 — Autonomous agent may rewrite validation/promotion rules
- **Status:** REJECTED
- **Current resolution:** Research agent cannot alter protected judging rules/ground truth.
- **History:** Initial_Chat_Log_017
- **Governing ADR:** ADR-017

## SUP-018 — One giant permanent CSV as canonical storage
- **Status:** REJECTED
- **Current resolution:** Use immutable raw → normalized → PIT state → features → training matrices → prediction snapshots; technologies remain defaults.
- **History:** master §43; source log 005
- **Governing ADR:** ADR-006
