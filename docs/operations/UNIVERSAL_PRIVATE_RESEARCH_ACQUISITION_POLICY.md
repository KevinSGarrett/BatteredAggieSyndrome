# Universal Private-Research Acquisition Policy

Status: `ACTIVE_SUPERSEDING_POLICY`
Owner authorization: `2026-08-09`
Implementation task: `TASK-202`

## Scope

Aggie Analytics is a private, personal, noncommercial research project. Publicly accessible factual data and data reachable with project credentials supplied by the owner may be downloaded, scraped, rendered, normalized, reconciled, combined, retained locally, analyzed, and used for local model training. This applies to public sites, endpoints, APIs, archives, repositories, release stores, and bulk downloads.

License, terms-of-use, scraping, robots, redistribution, provider-preference, model-training, and upstream-authorization information remains useful metadata. It does not gate private local acquisition, retention, analysis, or training. A failed route triggers autonomous route or source substitution, not a rights-derived project block.

## Enforced boundaries

- Raw and normalized bulk third-party payloads remain outside Git under `AGGIE_ANALYTICS_DATA_ROOT`.
- Raw third-party payloads are not published or redistributed.
- A future proposal for public distribution, repository inclusion of third-party payloads, or commercialization receives a separate review at that time.
- Source URL, request/endpoint identity, acquisition timestamp, immutable hash, schema/version, and lineage are preserved.
- Credentials never enter Git, Jira, saved response bodies, logs, screenshots, or prompts.

Only corrupted or fabricated records, PIT or target leakage, incompatible schemas, malware, exposed credentials, genuinely private personal information, and genuinely inaccessible resources requiring unsupplied credentials may block or quarantine data. Quality failures are scoped to the affected record, partition, domain, grain, season, endpoint, or route.

## Supersession

`SOURCE_BLOCKED`, `RIGHTS_BLOCKED`, rights-only `REFERENCE_ONLY`, and equivalent approval prerequisites are retired for private acquisition and local training. Historical source-rights artifacts remain provenance evidence, but their blocking conclusions are superseded. Current consumers use `configs/source_rights_registry.json` schema `2.0.0`, where rights metadata is nonblocking and raw export is independently denied.
