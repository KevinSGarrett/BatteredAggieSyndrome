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

Every paid operation requires a registered task, Jira identity, source capture SHA-256, strict schema, bounded output tokens, allocation, priority, and candidate destination. The CLI never accepts an API key argument. It uses a nonempty `OPENAI_API_KEY` from the authoritative root `.env` first, or an already-injected inherited process value when the file is unavailable. It reports only the credential channel and boolean presence, never the value, and never writes the process value back to disk.

Layout-heavy source evidence may be attached as a content-addressed PNG stored under the external data root. The controller verifies the MIME type, PNG dimensions, 20 MiB local cap, external-root confinement, detail level, source hash, and conservative image-token cost before admission; the request identity and provenance manifest retain the image hash without putting the image in Git. This route uses a Responses `input_image` block and remains subject to `store:false`, strict Structured Outputs, evidence validation, and candidate-only authority. BAT-538 is the first bounded use: four synchronous GPT-4o Mini calls cost `$0.016589`; the corrected two-case schema passed exactly, no Batch was justified, and 25 official pages remained a validated `STARTING_LINEUP_HISTORY_NOT_DEPTH_CHART` negative finding.

Operational artifacts are under `C:\BatteredAggieSyndrome.data\openai`. Delete reconstructible files in `tmp`; preserve accepted request/response/manifests, ledger events, evaluation evidence, and quarantines according to the project retention contract.

## BAT-522 final scale-out disposition

The assistive plane completed its governed handoff without admitting a Batch
scale-out. This is an empirical no-scale decision, not a provider or budget
failure. Pilot A's gamebook format was not compared with Nano, Pilot C failed
its predeclared promotion gate, and the final bounded Nano/minimal comparison on
Pilot B's exact 12-case entity-review format accepted 10 cases but quarantined
two. Its strict-schema rate was `0.8333`, field precision/recall were `0.9375`,
and evidence-locator accuracy was `0.0`; therefore it did not satisfy the exact
format's required all-pass rules. Do not submit Nano, Luna, Terra, or Sol Batch
work for those formats without a new versioned gold gate and admission record.

The final ledger reconciliation is recorded in
`artifacts/openai_assist/final_handoff.json`. It reports 332 settled synchronous
jobs, 24 released zero-cost provider rejections, zero Batch jobs, zero
outstanding reservations, `$2.751147` settled, and `$97.248853` remaining under
the unchanged `$100` hard stop. No Terra/Sol reserve was released. Operational
payloads remain content-addressed outside Git; `tmp` and `batches` are empty.
The deterministic forecast path, canonical identity, PIT state, protected
evaluation, promotion, forecasts, BAS, Aggie Excess, and publication state were
not modified.

BAT-522 is not the terminal OpenAI work unit. Its exact-format no-Batch result
continues to govern automatic scale-out, while `POST-SUBTASK-168` owns bounded
candidate-only assistance on new dependency-ready evidence. A failed Nano gate
does not prevent a value-backed Luna/Terra/Sol review call. New formats remain
synchronous or bounded until a separately versioned gold/schema/evidence/PIT
gate qualifies them for Batch and any canonical acceptance path.
