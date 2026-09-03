# Security and responsible disclosure

Please do not publish credentials, private data, or exploit details in a public issue or pull request.

If GitHub displays **Security → Report a vulnerability** for this repository, use that private reporting channel. If the option is unavailable, open a minimal issue asking the maintainer for a private contact method without including sensitive details. No response-time commitment or supported production release is currently established.

## Safe research and contributions

- Keep API keys and local configuration out of Git.
- Use small synthetic examples in public reports.
- Treat data sources, PR text, and model-generated suggestions as untrusted input.
- Do not give a third-party review service access to secrets or restricted datasets.
- Do not bypass an upstream access control or exceed a provider's permitted use.

Adding a path to `.gitignore` does not remove an already tracked file or erase Git history. Suspected credential exposure requires revocation or rotation and a separate review of history, clones, logs, and access—not merely deleting the visible line.

This repository is research software. It is not approved for production decisions, medical use, or betting reliance.
