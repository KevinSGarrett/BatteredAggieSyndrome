# OpenRouter Assistive Plane Architecture

The provider-neutral dispatcher owns task admission, request identity, strict-schema validation, redaction, budget reservation, external manifests, disposition, and final deterministic validation. Exactly one backend owns OpenRouter HTTP behavior and credential loading. The existing direct OpenAI controller remains unchanged and separately governed.

```text
bounded task packet
  -> provider-neutral dispatcher
  -> authority + secret + schema + budget gates
  -> one selected backend
  -> strict candidate response
  -> deterministic evidence/path/test validation
  -> candidate | review | quarantine | rejected
```

The production OpenRouter policy has a USD 0.00 hard limit, so its backend cannot be reached by a billable request. Fake-client tests exercise the dispatcher boundary without a provider call. Public catalog capture is a separate non-billable read-only operation.

Operational data is content-addressed outside Git. Repository code contains only policy, schemas, adapter/controller code, tests, and documentation. Batch Beta is disabled pending its separate gate.
