# Security, Secrets, Source Rights, and Dependency Policy

Security is a design and integration requirement, not a final packaging checkbox.

## Secret handling contract

- `.env` is local-only and ignored.
- `.env.example` contains names/placeholders only.
- Read credentials from environment variables or an approved local secret mechanism.
- Never print full secret values, even in debug output.
- Never place secrets in Markdown, JSON/YAML committed to Git, Jira, GitHub Issues/PRs, commit messages, screenshots, fixtures, provenance, model/data artifacts, or ZIPs.
- Redact authorization headers, signed URLs, cookies, tokens, private keys, passwords, database credentials, and provider response fields that expose them.
- Use least-privilege, source-specific credentials; do not share a broad personal token across unrelated tools.
- Rotate/revoke any credential exposed to history or external systems. Deleting the current line is not enough if history/logs/artifacts retain it.

Refer only to names such as `CFBD_API_KEY`; never record its value.

## Before commit, push, PR, and packaging

1. Inspect staged diff and untracked files.
2. Run the repository secret/forbidden-artifact validator.
3. Search for known token/private-key patterns and suspicious assignments.
4. Inspect generated logs/configs/manifests for accidental environment dumps.
5. Confirm `.env`, local data roots, caches, worktrees, virtual environments, model binaries, and exported ZIPs are excluded.
6. For first publication, scan the full proposed Git history, not only the tip.

If a secret is discovered:

- stop propagation;
- preserve evidence without repeating the value;
- revoke/rotate it through the correct owner;
- remove it from all affected current/history/artifact locations using an approved history-remediation plan;
- audit access and document the incident in a secure channel;
- do not paste the secret into Jira/PR while reporting it.

## Source access, licensing, and redistribution

Public accessibility is not permission to redistribute. For every production source, record:

- provider and authoritative terms location/date;
- authentication/access method;
- allowed uses and restrictions;
- rate limits and automation constraints;
- retention and redistribution rules;
- whether raw data may be committed, packaged, shared, or must remain local;
- attribution requirements;
- fallback/disable behavior.

Ambiguous rights are a blocker requiring authoritative review. Do not:

- bypass login, CAPTCHA, robots/access controls, or rate limits;
- scrape a source merely because a browser can display it;
- distribute restricted bulk raw data inside the repository/ZIP;
- invent or substitute provider payloads to bypass access;
- call multiple sibling derivatives independent corroboration when they share one upstream.

Keep stable schemas/contracts/provenance in Git and large/restricted data in configured local storage outside the repository.

## Data protection and privacy

- Minimize copied user/personally identifiable data.
- Redact or tokenize data where identity is not required.
- Do not commit Atlassian user profiles/comments/attachments merely to improve AI context.
- Define retention for local Jira/source caches and logs.
- Avoid raw request/response logging that captures credentials or sensitive source content.
- Restrict artifact access according to source and privacy classification.

## Dependency admission gate

Before adding/upgrading a library, framework, service, database, message queue, or build tool, answer:

1. Which current requirement needs it?
2. Why do existing dependencies or the standard library fail?
3. What measurable benefit is expected?
4. What security/license/supply-chain/resource risk is introduced?
5. What maintenance, upgrade, platform, and packaging burden is introduced?
6. Can a smaller approach satisfy the requirement?

Then:

- verify official package/project identity;
- review license and provenance;
- pin/lock according to repository policy;
- update dependency policy evidence;
- run vulnerability/dependency review and `pip check` where applicable;
- test Windows and Linux if supported;
- document migration/removal fallback.

Do not add dependencies for trivial helpers, style preference, or speculative future use.

## Supply-chain and GitHub controls

Keep and require, where available:

- dependency review on PRs;
- CodeQL/security analysis;
- secret scanning and push protection;
- pinned trusted action versions/major versions under review;
- least-privilege workflow permissions;
- no untrusted script execution with secrets;
- no write tokens in pull-request workflows from untrusted forks.

## Paid services and resource spend

Moderate cost within an approved documented budget may be AUTO WITH GATES. Significant or open-ended cloud/GPU/API spend is HUMAN REQUIRED.

Before spend:

- state the evidence-producing objective;
- estimate/limit budget and duration;
- configure stop/cap/rate controls;
- use least-privilege credentials;
- avoid uploading restricted data;
- record actual cost and result.

Do not use expensive infrastructure to mask inefficient code or skip required local baselines.

## Security-sensitive changes

Changes to authentication, authorization, visibility, secrets storage, workflow permissions, source access, data deletion, production networking, or security controls require explicit threat/risk review and normally human approval when they weaken or irreversibly alter protection.

Use the security sections of the task packet and PR template. Do not create a public GitHub issue containing exploit details or secrets.
