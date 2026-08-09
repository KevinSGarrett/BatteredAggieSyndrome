# GitHub Enforcement Recommendations

This document separates policies written in documentation from controls that should be technically enforced once a trusted `main` branch exists.

At audit time the GitHub repository existed but was empty. These settings were not applied. Initial publication and branch-protection configuration require a trusted local-history reconciliation and human approval.

Machine companion: `policies/github_enforcement.json`.

## P0 controls

### Protect `main`

Recommended:

- require pull requests for routine changes;
- block force pushes and branch deletion;
- require conversation resolution;
- require branches/checks to be up to date where appropriate;
- allow administrators to bypass only through explicit exceptional policy, not routine agent convenience.

Do not require a human review for every trivial file solely to defeat autonomy. Use path/risk-based ownership and automated gates.

### Required checks

After workflow names are observed on trusted `main`, require stable checks equivalent to:

- core validation on Ubuntu;
- core validation on Windows;
- security/secret/dependency policy;
- autonomous instruction/Jira mirror validation.

Do not configure required check names before they exist, or the branch can become unmergeable.

### Merge methods

Recommended ordinary model:

- enable squash merge;
- set concise PR-title-derived squash commit message including Jira key;
- disable ordinary merge commits unless a specific history need exists;
- optionally disable rebase merge unless deliberately adopted.

### Secret scanning and push protection

Enable all available repository secret scanning, push protection, and alerting. This complements, not replaces, local scans.

## P1 controls

### Automatic branch deletion

Enable after merge, while still applying unique-work/active-stack checks before local/worktree cleanup.

### CODEOWNERS for protected scopes

Assign `@KevinSGarrett` to root agent/instruction policies, protected governance/judging, security workflows, and repository policy. Require code-owner review only for genuinely protected paths if desired.

Avoid making every source/test/doc path human-blocked.

### CodeQL and dependency review

Keep the existing security workflow. Ensure least-privilege permissions and dependency review on PRs.

### Ruleset/path protections

Consider stricter review for:

- protected judging/acceptance seals;
- temporal/entity/shared contract registries;
- security workflows/CODEOWNERS;
- instruction autonomy/source-precedence policies;
- destructive migration/release configuration.

## P2 controls

- linear history if squash-only ordinary integration is adopted;
- signed commits/tags only if tooling/operations justify the burden;
- release environments and approvals when a real production deployment exists;
- artifact attestations/provenance after release pipeline maturity.

Do not add controls that create ceremony without reducing a demonstrated risk.

## GitHub Issues configuration

- Jira BAT remains the internal tracker.
- Keep a public bug form for external/repository defects.
- Disable unrestricted blank issues if they cause duplicate/internal work.
- Provide a private security reporting path.
- Do not auto-mirror all Jira issues.

## Application sequence

1. Establish trusted local history and initial `main` under approval.
2. Run CI once and record exact check names.
3. Confirm merge methods and branch/default settings.
4. Apply P0 branch/ruleset controls.
5. Test a Draft PR through all required checks and squash merge.
6. Apply targeted CODEOWNERS/path rules.
7. Enable auto-delete/secret scanning/security features.
8. Record settings and any exceptions in a repository operations artifact.

## Verification cadence

Re-audit GitHub settings when:

- workflows/check names change;
- repository visibility/ownership changes;
- releases/deployments begin;
- security incident occurs;
- bypass behavior is used;
- branch strategy changes.

Documentation is not proof that settings are active. Verify through GitHub metadata/UI/API.
