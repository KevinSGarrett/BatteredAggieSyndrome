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

Every paid operation requires a registered task, Jira identity, source capture SHA-256, strict schema, bounded output tokens, allocation, priority, and candidate destination. The CLI never accepts an API key argument. It discovers only `OPENAI_API_KEY` from the authoritative root `.env` and reports a boolean presence check.

Operational artifacts are under `C:\BatteredAggieSyndrome.data\openai`. Delete reconstructible files in `tmp`; preserve accepted request/response/manifests, ledger events, evaluation evidence, and quarantines according to the project retention contract.
