# Operating the OpenAI assistive plane

Install the optional, hash-locked adapter dependencies:

```powershell
python -m pip install --require-hashes -r requirements/openai-assist.lock
python -m pip install --no-deps -e .
```

Initialize and validate without spending credits:

```powershell
python -B tools/openai_assist.py doctor
python -B tools/openai_assist.py usage
python -B tools/openai_assist.py eval --predictions fixtures/openai_assist/eval_predictions.jsonl
```

Paid model comparisons use the versioned prompt and predeclared thresholds in
`configs/openai_evaluation_policy.json`. For the strict evaluation corpus, pass
`--schema schemas/openai/assistive_evaluation.schema.json`; `--model` produces a
single-route scorecard. Repeat `--predictions` to score independently
content-addressed primary and repeat artifacts together. A missing repeat or cross-model comparison group is
reported as `null`, never as an invented perfect score.

Budget stages are append-only ledger events. Release them only with the exact evidence reason required by policy, for example after the already-verified BAT-518/BAT-519 pilots:

```powershell
python -B tools/openai_assist.py budget-release --stage-usd 30.00 --evidence-id BAT-518,BAT-519 --reason PASSING_PILOT
```

The router starts validated bulk work on GPT-5 Nano Batch, uses 4o Mini only for a measured task-specific A/B win, sends Nano failures to Luna, complex ambiguity to Terra, and only the hardest/high-risk residue to Sol. Terra and Sol remain mandatory representative comparison routes; their base caps are $15 and $10, and measured value-gated reserve release can raise their absolute caps only to $25 and $17. Never hand-edit or rewrite settled ledger events when a policy revision remaps their historical allocation.

Pilot C is deliberately non-promoting: Nano/minimal passed 0/8 exact cases, Terra/low passed 3/4, and Sol/medium passed 2/2, while the overall strict gate failed. Keep this format synchronous/shadow only, preserve deterministic triage, submit no Nano Batch scale-out, and release no Terra/Sol reserve until a new versioned prompt/schema and independent evidence pass a fresh predeclared gate.

Every paid operation requires a registered task, Jira identity, source capture SHA-256, strict schema, bounded output tokens, allocation, priority, and candidate destination. The CLI never accepts an API key argument. It discovers only `OPENAI_API_KEY` from the authoritative root `.env` and reports a boolean presence check.

Operational artifacts are under `C:\BatteredAggieSyndrome.data\openai`. Delete reconstructible files in `tmp`; preserve accepted request/response/manifests, ledger events, evaluation evidence, and quarantines according to the project retention contract.
