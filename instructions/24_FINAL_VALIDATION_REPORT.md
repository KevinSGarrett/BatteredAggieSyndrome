# Battered Aggie Syndrome Autonomous Codex Instruction Pack — Final Validation Report

**Instruction-pack version:** `2.0.0`  
**Release date:** `2026-08-08`  
**Status:** `VALIDATED_REPOSITORY_CONTROL_SYSTEM_WITH_EXPLICIT_EXTERNAL_ACTIVATION_BOUNDARIES`  
**Canonical Windows installation target:** `C:\BatteredAggieSyndrome\instructions`  
**Canonical entrypoint:** `instructions/START_HERE.md`

This report records the final state of the autonomous-development control system created for the Battered Aggie Syndrome / Aggie Analytics Engine repository.

The validation standard is the user’s complete 56-section master prompt, decomposed into 464 individually reviewable obligations.

A requirement is not counted as satisfied merely because a heading exists.

Each obligation must map to one or more of the following:

- a canonical human-readable instruction;
- a machine-readable policy or schema;
- an executable tool or runbook;
- an automated validator or unit test;
- an aligned active repository-control file;
- or an explicit external activation boundary that prevents fabricated completion.

The repository control system is validated.

Live local Git, GitHub enforcement, and Jira BAT activation remain external boundaries where the supplied archive or connected services did not provide the necessary authoritative state.

Those boundaries are documented, gated, and supplied with deterministic activation procedures.

They are not silently represented as completed work.

## 1. Instruction Pack Created

The canonical live directory for the user’s machine is:

`C:\BatteredAggieSyndrome\instructions`

The complete instruction system in this release contains 92 files under `instructions/`.

The top-level instruction directory contains:

- `START_HERE.md` as the single canonical entrypoint;
- 24 numbered canonical operating documents;
- `manifest.json` as the machine-readable navigation and authority manifest;
- `FILE_HASHES.sha256` as the instruction-content integrity ledger;
- and `CHANGELOG.md` as the instruction-system change record.

Supporting instruction-system content includes:

- 22 machine-readable policies and schemas;
- 4 generated or curated catalogs;
- 11 audit and compliance artifacts;
- 13 operational recovery runbooks;
- and 14 focused templates and checklists.

The standalone release artifact is named:

`BatteredAggieSyndrome_Autonomous_Instructions_v2.0.0.zip`

The complete updated repository artifact is named:

`BatteredAggieSyndrome_with_Autonomous_Instructions_v2.0.0.zip`

Each ZIP is generated outside the canonical repository.

Each ZIP receives a companion `.sha256` checksum file.

The standalone ZIP is required to contain exactly one root named `instructions/`.

The full repository ZIP is required to contain exactly one root named `BatteredAggieSyndrome/`.

The packaging tools reject `.git`, `.env`, virtual environments, caches, `node_modules`, worktrees, unsafe paths, duplicate members, case-colliding members, and content that differs from the canonical source tree.

The release ZIP digests are intentionally recorded in the companion checksum files and external delivery report rather than embedded inside the ZIP that they hash.

## 2. Repository Findings

The uploaded source archive contained 863 files before this instruction-system rebuild.

The finalized repository tree contains 999 files before packaging.

The rebuild adds 136 files, aligns 34 existing files, removes zero original files, and leaves 829 original files byte-for-byte unchanged.

The 136 additions consist of:

- 92 instruction-system files;
- 21 local Jira control-plane files;
- 13 Python tools;
- 6 PowerShell wrappers;
- and 4 test modules.

The original repository already contained substantial governance and implementation-planning material.

Verified registry counts include:

- 745 requirements;
- 349 ADRs;
- 234 acceptance controls;
- 201 implementation-WBS tasks;
- 33 epics;
- 323 task-dependency edges;
- 33 historical work packets;
- and 14 final post-W25 handoff items.

The final numbered planning wave is W25.

There is no Wave 26.

The project is in a post-W25 implementation-handoff state, not a new wave-generation state.

Protected project invariants remain in force, including point-in-time correctness, target-game exclusion, immutable forecast/source evidence, canonical identity, provenance, empirical promotion, protected evaluation, and no fabricated scientific or performance claims.

The uploaded ZIP did not contain local `.git` metadata.

Consequently, the archive could not prove the real Windows checkout’s current branch, upstream, commit graph, remotes, tags, staged files, unstaged files, untracked files, or active worktrees.

The connected GitHub repository existed and was empty at discovery time.

It returned no branches, commits, pull requests, or issues.

No GitHub write, initialization, force push, history replacement, branch creation, or pull-request creation was performed.

The requested Jira site was `kevinsgarrett.atlassian.net`, project key `BAT`.

The authenticated Atlassian connection exposed a different site and did not expose the requested BAT site.

Therefore the real BAT workflow, issue types, statuses, transitions, fields, board filter, and issue population were not invented.

No Jira write was performed.

## 3. Instruction Architecture

`instructions/START_HERE.md` is the only general entrypoint.

It defines a deterministic startup sequence, context read budget, task-selection gate, execution loop, forbidden actions, and continuation behavior.

The numbered canonical documents divide authority by subject instead of duplicating rules across many competing files.

The architecture is organized into these major control domains:

- project identity and W25 handoff;
- source precedence and conflict resolution;
- repository architecture and task-scoped navigation;
- autonomous permissions and operating contract;
- task selection, dependency sequencing, and progress measurement;
- Jira execution state and local mirror behavior;
- Git repository safety, dirty-worktree recovery, branches, worktrees, commits, pull requests, merge, and cleanup;
- CI, testing tiers, evidence, and Definition of Done;
- security, secrets, data rights, dependencies, PIT, provenance, and ML evaluation;
- architecture change, documentation, release, rollback, context, handoff, parallelism, resources, blockers, loops, and recovery;
- GitHub enforcement recommendations;
- instruction maintenance, packaging, installation, compliance, and first activation.

The manifest tells an agent what each file is for, its authority level, who should read it, when it should be read, its dependencies, and its version.

The read-budget policy separates always-read material, task-start material, and conditional material.

This prevents every Codex cycle from reloading the entire repository or every instruction file.

The source-precedence policy contains eleven explicit levels and a deterministic same-level conflict procedure.

The machine-readable policies and the human-readable documents are cross-validated for critical values such as branch naming, worktree root, merge default, retry limits, Jira state concepts, autonomy permissions, and source precedence.

The master prompt is represented at two levels:

- a 56-section compliance ledger;
- and a 464-obligation atomic catalog with evidence and validation mappings.

Of the 464 obligations, 451 are classified `CONTROL_IMPLEMENTED` and 13 are classified `CONTROL_IMPLEMENTED_EXTERNAL_ACTIVATION_REQUIRED`.

The latter classification means the repository control and activation gate exist, while a live external state could not honestly be asserted from the supplied environment.

## 4. Jira Strategy

Live Jira BAT is the authority for mutable work state.

Repository governance is the authority for technical requirements, architecture, ADRs, acceptance controls, protected rules, schemas, code, tests, and provenance.

The local `jira/` directory is an AI-readable mirror, index, dependency graph, and traceability layer.

It is not a second Jira database.

The local Jira control plane contains 21 files, including:

- project and workflow verification records;
- conceptual status mappings awaiting live IDs;
- field and issue-type maps;
- a 201-task internal catalog;
- a 323-edge dependency graph;
- a 14-item final-handoff catalog;
- issue-to-source traceability schema and index;
- synchronization state;
- hydration schema;
- and mirror validation instructions.

Before implementing a live issue, the agent must inspect the issue, parent, dependencies, internal task and epic IDs, requirements, ADRs, acceptance controls, source documents, architecture, governance, code, tests, schemas, and interfaces relevant to that issue.

The issue source-map contract supports:

`BAT issue → internal task → epic → requirements → ADRs → acceptance controls → source documents → dependencies → branch → PR → evidence`

Status transitions are blocked until the exact live status and transition IDs are verified.

The conceptual states are Backlog, Ready, In Progress, Blocked, Review, Done, and Canceled, but they are not represented as the real Jira status names.

Ticket creation is subject to a granularity and anti-spam gate.

A new ticket must represent a meaningful independently trackable outcome, not a file, function, command, small test, retry, or bookkeeping action.

Meaningful Jira updates are required at claim, material blocker, review readiness, integration, and completion boundaries.

Command-by-command narration is prohibited.

Jira Done requires the applicable canonical Definition of Done and integration evidence; code existence alone is insufficient.

Live Jira writes remain disabled until the correct BAT site is authenticated and hydrated.

## 5. GitHub Strategy

The canonical local repository is `C:\BatteredAggieSyndrome`.

Replacement directories such as `-clean`, `-fixed`, `-new`, or `-final2` are prohibited as recovery mechanisms.

Protected `main` with short-lived Jira-linked task branches is the default model.

The active branch convention is:

`codex/BAT-123-short-description`

The active sibling worktree root is:

`C:\BatteredAggieSyndrome.data\worktrees`

A permanent `dev` branch is not introduced without a documented integration need.

Dirty repository recovery begins with read-only inspection of status, staged changes, unstaged changes, untracked files, ownership, and user intent.

Automatic hard resets, destructive cleans, force checkouts, deletion of unknown files, and replacement clones are prohibited.

Commits must be coherent engineering units and should include the Jira key where practical.

The default pull-request model is one coherent PR per meaningful Jira implementation unit or reviewable vertical slice.

Micro-PRs for files, functions, tests, retries, or Codex cycles are prohibited.

An existing matching PR must be reused rather than duplicated.

Draft PRs are used once coherent work exists; empty activity PRs are prohibited.

The ordinary merge default is squash merge, subject to verification of actual GitHub repository settings after publication.

Force pushing protected or shared branches is prohibited.

Safe force-with-lease may be used only on the owning agent’s unmerged task branch when policy conditions are met.

Merged branch and worktree cleanup requires proof that no unique commits, uncommitted work, active PR, or active owner remain.

Jira is the primary work tracker.

GitHub Issues are not allowed to mirror every Jira issue.

GitHub enforcement recommendations distinguish documentation-only controls from settings that should be technically enforced, including branch protection, required CI, secret scanning, dependency review, CodeQL, merge-method configuration, and automatic deletion of merged branches.

Because the remote was empty at discovery and the archive lacked trusted local history, first publication remains human-required.

## 6. Autonomy Strategy

The canonical operating cycle is:

**UNDERSTAND → SELECT → IMPLEMENT → TEST → REVIEW → INTEGRATE → RECORD → CONTINUE**

The agent first verifies repository identity and active state.

It then resumes valid unfinished work before selecting a new task.

Task selection is priority- and dependency-driven rather than interest-driven.

The sequence preserves P0 empirical foundations before P1 forecasting, P2 operation, and P3 complexity.

The current repository-evidenced boundary records `HANDOFF-001` as hardware-blocked and identifies `HANDOFF-002` as the independent P0 fallback only when real access, rights, and live Jira mapping are verified.

Every work cycle must move toward an observable project outcome.

Repeated rereading, plan regeneration, status checking, unchanged command retries, document reshuffling, and bookkeeping do not count as meaningful progress by themselves.

The retry policy permits one unchanged retry for a plausibly transient failure.

After that, diagnosis and a changed hypothesis are required.

After three materially different approaches without progress in one session, the item must be classified or escalated as blocked rather than retried indefinitely.

The blocker taxonomy covers dependency, data/source, credential/access, rights/license, shared contract, protected governance, CI/environment, ambiguity, external service, resource, and human-approval blockers.

Blocked work records evidence, attempted resolutions, the exact unblocking condition, and the next independent Ready lane.

The anti-overengineering gate requires a current requirement, evidence that a simpler approach is insufficient, expected measurable benefit, maintenance-cost assessment, and a smaller-alternative analysis before significant complexity is added.

Baselines, chronological evaluation, calibration, and protected evidence precede advanced ML challengers.

Null results are valid.

No BAS effect, Aggie Excess effect, A&M specialization lift, model performance, data availability, or hardware threshold may be fabricated.

The autonomy permission matrix separates AUTO, AUTO WITH GATES, and HUMAN REQUIRED operations.

High-risk irreversible actions such as protected-branch force push, destructive history rewrite, deletion of unknown work, weakening protected evaluation/security, destructive migrations, costly cloud commitments, or irreversible production changes require explicit human authorization.

Parallel sessions require separate Jira claims, branches, worktrees, scopes, and shared-contract ownership.

Single-writer resources and unfrozen shared contracts are not parallelized.

Session handoff records remain lightweight and contain only the active issue, branch/worktree, completed and pending changes, validation, failures, blocker, and next action.

## 7. Existing Files Updated

The rebuild adds **136 new files**, aligns **34 existing files**, removes **zero original files**, and leaves **829 original files byte-for-byte unchanged** relative to the supplied 863-file archive.

Every changed pre-existing path is enumerated below. The machine-readable authority is `instructions/audit/existing_control_alignment.csv`.

| Existing path | Action | Why it changed |
|---|---|---|
| `.codex/README.md` | Update | Make instructions/START_HERE.md the single canonical post-W25 operating entry and prevent a competing .codex instruction system. |
| `.codex/TASK_PACKET_TEMPLATE.md` | Update | Replace the duplicate packet body with a pointer to the canonical instructions/templates/TASK_EXECUTION_PACKET.md. |
| `.codex/WORKTREE_POLICY.md` | Update | Align the branch/worktree convention, protected shared-contract boundaries, and cleanup safety with the canonical Git policies. |
| `.github/CODEOWNERS` | Update | Assign the repository owner to governance, instruction, Jira-control, CI, and policy surfaces so GitHub can enforce review after remote activation. |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Update | Reserve GitHub Issues for repository/external defects, require sanitized evidence, and prevent duplication of planned Jira BAT work. |
| `.github/ISSUE_TEMPLATE/config.yml` | Update | Disable unstructured blank issues and route planned internal implementation work to Jira BAT. |
| `.github/pull_request_template.md` | Update | Require Jira/internal IDs, requirements, ADRs, acceptance controls, source documents, PIT/security implications, tests, limitations, rollback, and maturity evidence. |
| `.github/workflows/ci.yml` | Update | Add autonomous-control, Jira-control-plane, terminal-W25, warning-strict, and repository validations while preventing Python bytecode artifacts. |
| `.gitignore` | Update | Exclude secrets, caches, synchronized Jira issue payloads, worktree roots, control-plane audit outputs, and generated instruction/repository ZIP exports. |
| `AGENTS.md` | Update | Declare terminal W25/no-Wave-26 state, route all agents through START_HERE, and preserve protected governance and repository-safety boundaries. |
| `CHANGELOG.md` | Update | Record the v2 autonomous instruction/control-plane addition and the aligned repository controls without rewriting historical wave entries. |
| `CONTRIBUTING.md` | Update | Align task claims, Jira-linked branches, worktrees, commits, PR scope, progressive testing, and instruction validation with the canonical policies. |
| `README.md` | Update | State the post-W25 implementation-handoff maturity honestly, identify START_HERE, and remove stale active-wave/production-completeness implications. |
| `configs/backlog_policy.json` | Update | Make W25 terminal, prohibit Wave 26, represent HANDOFF-001 as blocked, and identify HANDOFF-002 only as the conditional independent P0 lane. |
| `configs/repository_policy.json` | Update | Require instructions and Jira control-plane content, exclude only root runtime .git metadata, and continue forbidding nested repositories and unsafe artifacts. |
| `docs/06_GITHUB_CODEX_WORKFLOW.md` | Update | Supersede historical execution details with the canonical Jira-linked branch, worktree, PR, CI, and reconciliation contracts. |
| `docs/11_CODEX_EXECUTION_STRATEGY.md` | Update | Route post-W25 implementation through the new selection, execution, evidence, blocker, and continuation control system. |
| `docs/85_WORKTREE_ISOLATION.md` | Update | Align historical worktree guidance with the canonical Windows worktree root, branch naming, single-writer rules, and safe cleanup gates. |
| `docs/final/CODEX_HANDOFF.md` | Update | Add the canonical instruction entrypoint, no-Wave-26 boundary, and mandatory local Git/GitHub/Jira reconciliation before mutation. |
| `docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md` | Update | Correct the active sequence so blocked hardware evidence does not hide the conditional independent source-access/rights lane. |
| `governance/CURRENT_BACKLOG.yaml` | Update | Represent real handoff blockers/readiness without inventing empirical completion, Jira state, access, rights, or hardware evidence. |
| `governance/NEXT_WAVE.md` | Update | Replace obsolete wave-generation behavior with post-W25 implementation continuation and explicitly forbid Wave 26. |
| `governance/SOURCE_OF_TRUTH_MAP.md` | Update | Add the instruction system, live Jira, local Jira mirror, Git/PR state, precedence hierarchy, and same-level conflict procedure. |
| `provenance/CURRENT_TREE.txt` | Regenerate | Record the complete finalized repository tree after adding the instruction, Jira, tool, test, and alignment artifacts. |
| `provenance/PROJECT_FILE_HASHES.sha256` | Regenerate | Recompute SHA-256 evidence for the finalized repository while excluding permitted root runtime .git metadata. |
| `provenance/PROJECT_FILE_MANIFEST.csv` | Regenerate | Recompute path, size, and hash rows for the finalized repository after all control-plane changes. |
| `scripts/new_worktree.ps1` | Update | Require a BAT key and safe slug, verify canonical Git identity and branch uniqueness, use the approved external worktree root, and refuse unsafe creation. |
| `tests/test_repo_integrity_tools.py` | Update | Prove root .git metadata is excluded from packages/manifests while nested .git repositories remain forbidden. |
| `tests/test_w23_operations.py` | Update | Suppress the expected duplicate-member warning only inside the intentional ZIP-tampering test so warning-strict validation remains meaningful. |
| `tools/packaging.py` | Update | Use the policy-aware repository iterator so generated archives and file counts exclude root runtime .git metadata without excluding nested repository violations. |
| `tools/repo_integrity.py` | Update | Support real Git checkouts by excluding only root .git metadata, continue detecting nested .git, and make manifests/packages deterministic and policy-aware. |
| `tools/validate_repository.py` | Update | Integrate autonomous instruction/Jira validation, use the policy-aware file iterator, and preserve external-activation warnings without treating them as fabricated success. |
| `tools/validate_w20_starter.py` | Update | Context-manage the WBS CSV handle to eliminate ResourceWarning leakage during warning-strict release tests. |
| `tools/validate_w21_mlops.py` | Update | Context-manage WBS and ADR CSV handles to eliminate ResourceWarning leakage during warning-strict release tests. |

The three provenance files are regenerated evidence rather than policy rewrites. The two historical validator files and the W23 tamper test received only warning/resource hygiene changes needed for a clean warning-strict release run.

Historical wave records remain preserved as provenance. They were not rewritten merely because newer W25 controls supersede their operational status.
## 8. Validation Results

The final validation suite checks structure, content, consistency, traceability, secrets, packaging, and extracted artifacts.

The autonomous-control validator requires all canonical files, valid JSON, valid internal Markdown links, manifest coverage, instruction hash coverage, 56-section compliance, 464 atomic obligations, policy invariants, human/machine consistency, root-control alignment, no-Wave-26 behavior, honest external audits, final-report completeness, semantic safety, and minimum instruction depth.

The Jira validator checks schemas, generated counts, dependency integrity, traceability structures, unverified-live-state honesty, and write gating.

The repository validator checks required structure, project manifests, governance IDs, dangling requirement/ADR references, secrets, forbidden artifacts, and instruction-system integration.

The W25 validator checks terminal handoff integrity and prevents a Wave 26 restart.

The dependency-policy validator checks task dependencies and execution-policy consistency.

The unit-test suite contains 255 tests after the rebuild.

The finalized source tree is required to pass all 255 tests.

The standalone packager regenerates the instruction manifest, runs strict instruction validation, creates a deterministic ZIP, checks safe paths and unique members, performs ZIP CRC validation, extracts the archive, verifies every instruction hash, and compares every extracted file with the canonical directory.

The full-repository packager regenerates project and instruction manifests, runs control, Jira, W25, dependency, repository, secret, and forbidden-artifact checks, runs both the complete and warning-strict unit-test suites, regenerates post-test provenance, creates a deterministic ZIP, validates CRC and member safety, extracts it, compares every file with the canonical tree, and reruns the release validations and both test modes from the extracted copy.

The executed release validation results are:

- autonomous control validation: PASS, with one explicit Jira external-activation warning;
- Jira control-plane structural validation: PASS, with live BAT activation still unverified;
- W25 terminal validation: PASS;
- dependency policy validation: PASS;
- strict repository validation: PASS;
- secret scan: PASS;
- forbidden-artifact scan: PASS;
- internal instruction links: PASS;
- manifest and hash-ledger validation: PASS;
- 464-obligation compliance validation: PASS;
- unit tests: 255 of 255 PASS;
- warning-strict unit tests (`PYTHONWARNINGS=error`): 255 of 255 PASS;
- standalone ZIP CRC, extraction, member, and hash comparison: PASS;
- full repository ZIP CRC, extraction, member, source comparison, validator rerun, and test rerun: PASS.

No `.env`, secret value, PAT, password, private token, raw restricted data, cache, virtual environment, temporary worktree, nested repository, or unrelated ZIP is permitted in either release artifact.

## 9. Unresolved Questions and Risks

The real local `.git` state on `C:\BatteredAggieSyndrome` remains unverified because it was not present in the supplied archive.

The incoming full-repository ZIP must not be blindly extracted over the existing Windows checkout.

The actual local branch, history, remotes, dirty files, tags, and worktrees must be audited read-only before installation or publication.

The discovery-time GitHub repository was empty, but it must be rechecked because remote state can change.

Initial publication or history reconciliation remains human-required.

GitHub branch protection, required checks, merge methods, secret scanning, dependency review, CodeQL, and branch auto-deletion remain recommendations until the real remote is initialized and inspected.

The requested Jira BAT site was not accessible through the authenticated Atlassian session.

Live workflow names, transitions, required fields, issue hierarchy, board filter, and issue mappings remain intentionally unhydrated.

Jira writes remain disabled until the correct site is connected and read-only discovery succeeds.

`HANDOFF-001` remains blocked until representative target hardware can produce measured evidence.

`HANDOFF-002` remains conditional on actual credentials, access, source terms, licensing, and redistribution rights.

Real national historical data materialization, canonical entities, PIT state, leakage replay, defensible model performance, calibration, A&M specialization, and BAS/Aggie Excess scientific findings remain product implementation work.

This instruction-pack task deliberately does not fabricate those outcomes or arbitrarily implement the remaining product backlog.

## 10. Recommended Next Action

Place the complete updated repository artifact beside—not over—the actual Windows checkout.

Open the trusted `C:\BatteredAggieSyndrome` checkout.

Read `AGENTS.md` and `instructions\START_HERE.md` first.

Run the read-only control-plane audit:

```powershell
Set-Location C:\BatteredAggieSyndrome
python -B tools\audit_control_plane.py --repo-root . --output artifacts\control-plane-audit.json
git status --short --branch
git remote -v
git branch --all --verbose --no-abbrev
git worktree list --porcelain
git log --graph --decorate --oneline --all -n 100
```

Compare the incoming v2 files with the actual checkout while preserving every unexplained user or agent change.

Reconcile trusted local history with GitHub without force push, reset, or replacement cloning.

Connect an authorized identity to the requested BAT Jira site and hydrate the local mirror read-only before enabling writes.

Resume valid unfinished work before creating a new branch or issue.

Select the highest-priority dependency-ready Jira item that maps to the internal task, requirements, ADRs, acceptance controls, source documents, code, tests, and schemas.

Create one short-lived branch and one worktree using the documented Jira-linked convention.

Execute the canonical cycle:

**UNDERSTAND → SELECT → IMPLEMENT → TEST → REVIEW → INTEGRATE → RECORD → CONTINUE**

Continue through meaningful Ready work until a genuine human-required or global blocker is reached.

Never create Wave 26, duplicate the canonical repository, discard unknown work, weaken protected rules, invent evidence, leak secrets, create ticket/branch/PR spam, or repeat unchanged failures indefinitely.
