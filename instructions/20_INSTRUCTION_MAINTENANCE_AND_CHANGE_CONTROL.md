# Instruction-System Maintenance and Change Control

The instruction pack must remain one coherent control system, not accumulate competing policies.

Machine companion: `policies/instruction_change_policy.json`.

## Canonical rule

- `instructions/START_HERE.md` is the single entrypoint.
- Every major policy has one canonical Markdown home.
- Deterministic enumerations/patterns/state machines may have one machine companion listed in `manifest.json`.
- Root `.codex`, `.github`, `AGENTS.md`, README, and CONTRIBUTING may point/summarize but must not redefine the rule differently.

## Change gate

Before changing an instruction/control policy:

1. Identify the concrete failure, changed external system, or new requirement.
2. Identify affected prompt sections, canonical policy, machine companion, root controls, templates, validators, and workflows.
3. Prefer editing/consolidating an existing canonical file over creating another document.
4. Preserve protected W25/no-W26/security/PIT/evaluation boundaries.
5. Update human and machine forms atomically.
6. Update the manifest/read budget/compliance mapping and affected templates.
7. Add/adjust validation tests.
8. Run instruction/Jira/repository validators and full applicable tests.
9. Regenerate instruction hashes and repository provenance last.
10. Record the change in `CHANGELOG.md` and final validation evidence.

## Versioning

Use semantic versioning:

- **Major:** authority hierarchy, task/Jira/Git operating model, autonomy risk boundary, canonical entry architecture, or incompatible policy change.
- **Minor:** backward-compatible new runbook/policy/tooling capability.
- **Patch:** clarification, typo, link repair, validator bug, or non-behavioral correction.

Do not bump versions without updating manifest/policies/changelog/export names.

## Avoid policy duplication

Before adding a file ask:

- Is this a new distinct decision domain?
- Will an agent know when to read it?
- Does an existing canonical document already own the rule?
- Is machine-readable form materially useful?
- Can a checklist/template express it better?

Do not create 100 tiny files. This pack uses grouped canonical procedures plus functional policies/templates/audits because each has a distinct read trigger or validator role.

## Existing repository controls

When an existing file is stale/contradictory:

- determine whether it is active policy or historical provenance;
- change the smallest active surface necessary;
- use a compatibility pointer for legacy paths where useful;
- do not mass-rewrite historical wave documents;
- record alignment in `audit/existing_control_alignment.csv`.

## Policy contradiction handling

If human and machine policy disagree:

- stop the affected operation;
- apply source precedence and inspect change history;
- repair the canonical pair, manifest/compliance/tests/hashes;
- never let the validator choose a weaker rule silently.

## Validation contract

`tools/validate_autonomous_controls.py` must verify at least:

- all required files and one entrypoint;
- all 56 prompt sections uniquely covered;
- manifest coverage and hashes;
- internal links/paths;
- no Wave 26 enablement;
- branch/worktree/commit/PR consistency;
- autonomy classes/gates;
- state machine/DoD/testing structure;
- Jira unverified-state safety;
- PR/CODEOWNERS/CI alignment;
- no secret/forbidden artifacts.

A validator that merely checks keywords is insufficient.

## Packaging contract

The package tool must:

- validate first;
- scan secrets/forbidden content;
- include only canonical instruction contents for the standalone ZIP;
- exclude `.git`, `.env`, caches, venvs, worktrees, local data, nested ZIPs, and temporary exports;
- create deterministic member ordering/timestamps;
- verify archive paths, CRC, member set, hashes, and extraction;
- write SHA-256 sidecars outside the repository.

## Flexible improvement authority

Evidence-driven improvements are encouraged when materially better. The agent may consolidate, add safeguards, improve runbooks, and propose architecture changes. It may not use “flexibility” to bypass protected rules, create speculative complexity, or silently change authority.
