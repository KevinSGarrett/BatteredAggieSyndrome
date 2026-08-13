# OpenRouter Assistive Plane Operations

## Foundation validation

Run:

```powershell
python -B tools/validate_openrouter_assist.py --repo-root .
python -B -m unittest tests.test_openrouter_assist
```

The validator must confirm the authorized USD 25 hard stop, the lower USD 5 released stage, no budget transfer from direct OpenAI, strict schemas, privacy/provider defaults, disabled Batch Beta, and a single OpenRouter backend endpoint.

## Non-billable catalog refresh

`python -B tools/refresh_openrouter_model_catalog.py` captures the public model catalog and official documentation under `C:\BatteredAggieSyndrome.data\assistive\openrouter\runtime`, then writes a content-addressed manifest. This is capability evidence, not route approval. It makes no paid inference call.

## Paid dispatch state

`tools/openrouter_assist.py` is intentionally fail-closed. The separately authorized USD 25 hard limit and USD 5 released stage now permit bounded candidate-only work after exact schema, privacy, provider, evidence, and reservation admission. As of 2026-08-13, two strict-schema `qwen/qwen3-coder-next` independent-review candidates validated; the conservative local all-key ledger records USD 0.00209168 while provider totals lag local settlement. No exact route is operationally admitted, and continuing scale remains gated on the required empirical campaign.

Never provide the key in a command argument. The backend loads it only from `C:\BatteredAggieSyndrome\.env`. Never copy `.env` into a worktree.

## Cleanup and handoff

Remove verified reconstructible files only from the external `tmp` directory. Preserve content-addressed requests, responses, manifests, evaluations, usage, worker packets/results, quarantines, and catalog evidence as required by their evidence contracts.

Report separate OpenRouter and direct OpenAI call counts and ledgers. OpenRouter handoff must include requested/resolved models and providers, calls, spend, remaining authorized budget, last successful use, active tasks, dispositions, Batch decisions, artifacts/hashes, cleanup, blockers, and next eligible workload.
