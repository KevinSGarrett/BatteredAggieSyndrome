# Master Prompt Compliance Ledger
This is the human-readable section-level view of the canonical machine mapping in `policies/prompt_compliance.json`. The atomic catalog in `catalogs/master_prompt_atomic_requirements.json` decomposes all 56 sections into individually testable obligations; the CSV audit is generated from that catalog.
A status beginning with `IMPLEMENTED` means the **repository control** exists. Suffixes preserve honest activation boundaries: they do not claim that the inaccessible Windows checkout, empty-at-discovery GitHub remote, or unavailable BAT Jira workflow has been live-configured.
| Section | Requirement | Status | Canonical evidence | Validation |
|---:|---|---|---|---|
| 1 | PRIMARY MISSION | `IMPLEMENTED` | `instructions/START_HERE.md`<br>`instructions/04_AUTONOMOUS_OPERATING_CONTRACT.md`<br>`instructions/06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md` | `VAL-COMPLIANCE`<br>`VAL-LINKS` |
| 2 | OUTPUT LOCATION | `IMPLEMENTED_WITH_INSTALLATION_BOUNDARY` | `instructions/21_PACKAGING_INTEGRITY_AND_INSTALLATION.md`<br>`tools/package_instructions.py` | `VAL-PACKAGE`<br>`VAL-SECRET` |
| 3 | PROJECT LOCATIONS | `IMPLEMENTED_WITH_EXTERNAL_DISCOVERY_GAPS` | `instructions/01_PROJECT_IDENTITY_AND_HANDOFF.md`<br>`instructions/23_ACTIVATION_AND_NEXT_SESSION.md`<br>`instructions/audit/EXTERNAL_INTEGRATION_AUDIT.md` | `VAL-CONTROL-PLANE`<br>`VAL-JIRA` |
| 4 | FIRST ACTION — COMPLETE REPOSITORY DISCOVERY | `IMPLEMENTED_WITH_EXTERNAL_DISCOVERY_GAPS` | `instructions/audit/REPOSITORY_DISCOVERY_REPORT.md`<br>`instructions/audit/repository_inventory.json`<br>`instructions/audit/external_access_audit.json`<br>`tools/audit_control_plane.py` | `VAL-CONTROL-PLANE`<br>`VAL-AUDIT` |
| 5 | EXISTING PROJECT STATE YOU MUST PRESERVE | `IMPLEMENTED` | `instructions/01_PROJECT_IDENTITY_AND_HANDOFF.md`<br>`instructions/14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md`<br>`instructions/policies/protected_scope_policy.json` | `VAL-NO-W26`<br>`VAL-PROTECTED` |
| 6 | SOURCE-OF-TRUTH PRECEDENCE | `IMPLEMENTED` | `instructions/02_SOURCE_OF_TRUTH_AND_CONFLICT_RESOLUTION.md`<br>`instructions/policies/source_precedence.json` | `VAL-SOURCE-PRECEDENCE` |
| 7 | SINGLE CANONICAL INSTRUCTION SYSTEM | `IMPLEMENTED` | `instructions/START_HERE.md`<br>`instructions/20_INSTRUCTION_MAINTENANCE_AND_CHANGE_CONTROL.md` | `VAL-ENTRYPOINT`<br>`VAL-DUPLICATION` |
| 8 | REQUIRED INSTRUCTION-PACK COVERAGE | `IMPLEMENTED` | `instructions/START_HERE.md`<br>`instructions/manifest.json`<br>`instructions/22_MASTER_PROMPT_COMPLIANCE_LEDGER.md` | `VAL-MANIFEST`<br>`VAL-COMPLIANCE` |
| 9 | JIRA OPERATING MODEL | `IMPLEMENTED_PENDING_LIVE_ACTIVATION` | `instructions/07_JIRA_OPERATING_CONTRACT.md`<br>`instructions/policies/jira_operating_policy.json` | `VAL-JIRA` |
| 10 | LOCAL JIRA DIRECTORY | `IMPLEMENTED_PENDING_LIVE_ACTIVATION` | `instructions/08_LOCAL_JIRA_MIRROR_AND_SYNC.md`<br>`jira/README.md`<br>`jira/schemas/issue_source_map.schema.json` | `VAL-JIRA` |
| 11 | JIRA STATUS HYGIENE | `IMPLEMENTED_PENDING_LIVE_ACTIVATION` | `instructions/07_JIRA_OPERATING_CONTRACT.md`<br>`instructions/policies/task_state_machine.json`<br>`jira/status_map.json` | `VAL-JIRA` |
| 12 | JIRA TICKET GRANULARITY — PREVENT AI TICKET EXPLOSION | `IMPLEMENTED` | `instructions/07_JIRA_OPERATING_CONTRACT.md`<br>`instructions/templates/NEW_ISSUE_DECISION.md` | `VAL-JIRA-POLICY` |
| 13 | TASK SELECTION AND BUILD SEQUENCE | `IMPLEMENTED` | `instructions/05_TASK_SELECTION_AND_SEQUENCING.md`<br>`instructions/policies/task_selection_policy.json`<br>`tools/select_next_work.py` | `VAL-TASK-SELECTION` |
| 14 | GIT/GITHUB OPERATING CONTRACT | `IMPLEMENTED_PENDING_LIVE_RECONCILIATION` | `instructions/09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md`<br>`instructions/10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md`<br>`instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`instructions/policies/git_policy.json` | `VAL-GIT-POLICY` |
| 15 | CANONICAL REPOSITORY RULE | `IMPLEMENTED` | `instructions/09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md`<br>`instructions/policies/git_policy.json` | `VAL-CANONICAL-REPO` |
| 16 | DIRTY REPOSITORY DECISION TREE | `IMPLEMENTED` | `instructions/09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md`<br>`instructions/runbooks/DIRTY_WORKTREE_RECOVERY.md` | `VAL-GIT-POLICY` |
| 17 | BRANCH STRATEGY | `IMPLEMENTED_PENDING_LIVE_RECONCILIATION` | `instructions/10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md`<br>`instructions/policies/git_policy.json` | `VAL-BRANCH-POLICY` |
| 18 | WORKTREE STRATEGY | `IMPLEMENTED_PENDING_LIVE_RECONCILIATION` | `instructions/10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md`<br>`.codex/WORKTREE_POLICY.md`<br>`scripts/new_worktree.ps1` | `VAL-WORKTREE-POLICY` |
| 19 | COMMIT POLICY | `IMPLEMENTED` | `instructions/10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md`<br>`instructions/policies/git_policy.json` | `VAL-COMMIT-POLICY` |
| 20 | PULL REQUEST POLICY — CRITICAL | `IMPLEMENTED_PENDING_REMOTE_INITIALIZATION` | `instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`.github/pull_request_template.md` | `VAL-PR-TEMPLATE` |
| 21 | PR LIFECYCLE | `IMPLEMENTED_PENDING_REMOTE_INITIALIZATION` | `instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`instructions/templates/PR_READY_CHECKLIST.md`<br>`instructions/templates/MERGE_AND_CLEANUP_CHECKLIST.md` | `VAL-PR-LIFECYCLE` |
| 22 | PULL REQUEST TEMPLATE | `IMPLEMENTED` | `.github/pull_request_template.md`<br>`instructions/templates/PR_READY_CHECKLIST.md` | `VAL-PR-TEMPLATE` |
| 23 | MERGE STRATEGY | `IMPLEMENTED_PENDING_GITHUB_SETTING_VERIFICATION` | `instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`instructions/policies/git_policy.json`<br>`instructions/19_GITHUB_ENFORCEMENT_RECOMMENDATIONS.md` | `VAL-MERGE-POLICY` |
| 24 | BRANCH CLEANUP | `IMPLEMENTED` | `instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`instructions/runbooks/STALE_BRANCH_AND_WORKTREE.md` | `VAL-CLEANUP-POLICY` |
| 25 | GITHUB ISSUE VS JIRA AUTHORITY | `IMPLEMENTED` | `instructions/07_JIRA_OPERATING_CONTRACT.md`<br>`instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`.github/ISSUE_TEMPLATE/config.yml` | `VAL-ISSUE-AUTHORITY` |
| 26 | GITHUB CI/CD | `IMPLEMENTED_PENDING_REMOTE_INITIALIZATION` | `instructions/11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md`<br>`instructions/12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md`<br>`.github/workflows/ci.yml` | `VAL-CI-CONFIG` |
| 27 | TESTING STRATEGY — PREVENT OVERTESTING | `IMPLEMENTED` | `instructions/12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md`<br>`instructions/policies/test_tiers.json` | `VAL-TESTING-POLICY` |
| 28 | DEFINITION OF DONE | `IMPLEMENTED` | `instructions/12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md`<br>`instructions/policies/definition_of_done.json` | `VAL-DOD` |
| 29 | AUTONOMOUS DEVELOPMENT EXECUTION LOOP | `IMPLEMENTED` | `instructions/04_AUTONOMOUS_OPERATING_CONTRACT.md`<br>`instructions/06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md`<br>`instructions/START_HERE.md` | `VAL-EXECUTION-LOOP` |
| 30 | MEANINGFUL PROGRESS RULE | `IMPLEMENTED` | `instructions/06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md`<br>`instructions/templates/TASK_EXECUTION_PACKET.md` | `VAL-MEANINGFUL-PROGRESS` |
| 31 | ANTI-LOOP POLICY | `IMPLEMENTED` | `instructions/17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md`<br>`instructions/policies/loop_and_retry_policy.json`<br>`instructions/runbooks/AGENT_LOOP_RECOVERY.md` | `VAL-LOOP-POLICY` |
| 32 | ANTI-OVERENGINEERING POLICY | `IMPLEMENTED` | `instructions/17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md`<br>`instructions/04_AUTONOMOUS_OPERATING_CONTRACT.md` | `VAL-OVERENGINEERING` |
| 33 | BASELINES BEFORE COMPLEXITY | `IMPLEMENTED` | `instructions/05_TASK_SELECTION_AND_SEQUENCING.md`<br>`instructions/14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md` | `VAL-ML-GOVERNANCE` |
| 34 | BLOCKER MANAGEMENT | `IMPLEMENTED` | `instructions/17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md`<br>`instructions/policies/blocker_taxonomy.json`<br>`instructions/templates/BLOCKER_RECORD.md` | `VAL-BLOCKER-POLICY` |
| 35 | AUTONOMY PERMISSION MATRIX | `IMPLEMENTED` | `instructions/04_AUTONOMOUS_OPERATING_CONTRACT.md`<br>`instructions/policies/autonomy_permissions.json` | `VAL-AUTONOMY` |
| 36 | PARALLELISM AND MULTIPLE CODEX SESSIONS | `IMPLEMENTED` | `instructions/16_PARALLELISM_RESOURCES_CONTEXT_AND_HANDOFF.md`<br>`instructions/policies/parallelism_policy.json`<br>`instructions/policies/shared_contract_policy.json` | `VAL-PARALLELISM` |
| 37 | SESSION STARTUP PROCEDURE | `IMPLEMENTED` | `instructions/START_HERE.md`<br>`tools/audit_control_plane.py` | `VAL-ENTRYPOINT`<br>`VAL-CONTROL-PLANE` |
| 38 | CONTEXT MANAGEMENT | `IMPLEMENTED` | `instructions/16_PARALLELISM_RESOURCES_CONTEXT_AND_HANDOFF.md`<br>`instructions/policies/read_budget.json` | `VAL-READ-BUDGET` |
| 39 | HANDOFF AND CONTINUATION | `IMPLEMENTED` | `instructions/16_PARALLELISM_RESOURCES_CONTEXT_AND_HANDOFF.md`<br>`instructions/templates/HANDOFF_RECORD.md` | `VAL-HANDOFF` |
| 40 | ARCHITECTURE CHANGE POLICY | `IMPLEMENTED` | `instructions/15_ARCHITECTURE_DOCUMENTATION_RELEASE_AND_ROLLBACK.md`<br>`instructions/templates/ARCHITECTURE_CHANGE_PROPOSAL.md` | `VAL-ARCHITECTURE-CHANGE` |
| 41 | DOCUMENTATION POLICY | `IMPLEMENTED` | `instructions/15_ARCHITECTURE_DOCUMENTATION_RELEASE_AND_ROLLBACK.md` | `VAL-DOCUMENTATION-POLICY` |
| 42 | SECURITY AND SECRET HANDLING | `IMPLEMENTED` | `instructions/13_SECURITY_SECRETS_DATA_RIGHTS_AND_DEPENDENCIES.md`<br>`instructions/policies/security_policy.json` | `VAL-SECRET`<br>`VAL-SECURITY-POLICY` |
| 43 | DATA/ML GOVERNANCE | `IMPLEMENTED` | `instructions/14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md`<br>`instructions/policies/protected_scope_policy.json` | `VAL-PROTECTED`<br>`VAL-ML-GOVERNANCE` |
| 44 | RESOURCE-AWARE DEVELOPMENT | `IMPLEMENTED` | `instructions/16_PARALLELISM_RESOURCES_CONTEXT_AND_HANDOFF.md`<br>`instructions/14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md` | `VAL-RESOURCE-POLICY` |
| 45 | ERROR AND RECOVERY RUNBOOKS | `IMPLEMENTED` | `instructions/18_OPERATIONAL_RUNBOOKS.md`<br>`instructions/runbooks/DIRTY_WORKTREE_RECOVERY.md`<br>`instructions/runbooks/FAILED_CI_DIAGNOSIS.md`<br>`instructions/runbooks/JIRA_GITHUB_DESYNCHRONIZATION.md`<br>`instructions/runbooks/INTERRUPTED_SESSION_RECOVERY.md`<br>`instructions/runbooks/SOURCE_API_OUTAGE_AND_ACCESS_FAILURE.md` | `VAL-RUNBOOKS` |
| 46 | MACHINE-READABLE POLICIES | `IMPLEMENTED` | `instructions/policies/`<br>`tools/validate_autonomous_controls.py` | `VAL-POLICIES` |
| 47 | INSTRUCTION-PACK MANIFEST | `IMPLEMENTED` | `instructions/manifest.json`<br>`instructions/policies/instruction_manifest.schema.json` | `VAL-MANIFEST`<br>`VAL-HASHES` |
| 48 | INSTRUCTION NAVIGATION / READ BUDGET | `IMPLEMENTED` | `instructions/START_HERE.md`<br>`instructions/policies/read_budget.json`<br>`instructions/03_REPOSITORY_ARCHITECTURE_AND_NAVIGATION.md` | `VAL-READ-BUDGET` |
| 49 | DO NOT OVERENGINEER THE INSTRUCTION PACK ITSELF | `IMPLEMENTED` | `instructions/20_INSTRUCTION_MAINTENANCE_AND_CHANGE_CONTROL.md`<br>`instructions/22_MASTER_PROMPT_COMPLIANCE_LEDGER.md` | `VAL-DUPLICATION` |
| 50 | EXISTING FILE INTEGRATION | `IMPLEMENTED` | `instructions/20_INSTRUCTION_MAINTENANCE_AND_CHANGE_CONTROL.md`<br>`instructions/audit/existing_control_alignment.csv` | `VAL-ACTIVE-CONTROLS` |
| 51 | GITHUB ENFORCEMENT RECOMMENDATIONS | `IMPLEMENTED_PENDING_REMOTE_INITIALIZATION` | `instructions/19_GITHUB_ENFORCEMENT_RECOMMENDATIONS.md`<br>`instructions/policies/github_enforcement.json`<br>`instructions/templates/GITHUB_ENFORCEMENT_ACTIVATION_CHECKLIST.md` | `VAL-GITHUB-ENFORCEMENT` |
| 52 | PROFESSIONAL ENGINEERING STANDARD | `IMPLEMENTED` | `instructions/01_PROJECT_IDENTITY_AND_HANDOFF.md`<br>`instructions/04_AUTONOMOUS_OPERATING_CONTRACT.md`<br>`instructions/06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md` | `VAL-OPERATING-STANDARD` |
| 53 | FLEXIBILITY AND IMPROVEMENT AUTHORITY | `IMPLEMENTED` | `instructions/15_ARCHITECTURE_DOCUMENTATION_RELEASE_AND_ROLLBACK.md`<br>`instructions/20_INSTRUCTION_MAINTENANCE_AND_CHANGE_CONTROL.md` | `VAL-CHANGE-CONTROL` |
| 54 | REQUIRED FINAL VALIDATION | `IMPLEMENTED_WITH_EXTERNAL_DISCOVERY_GAPS` | `instructions/24_FINAL_VALIDATION_REPORT.md`<br>`tools/validate_autonomous_controls.py`<br>`tests/test_autonomous_controls.py`<br>`tests/test_jira_control_plane.py`<br>`tests/test_instructions_pack.py` | `VAL-FINAL` |
| 55 | REQUIRED FINAL REPORT | `IMPLEMENTED_WITH_EXTERNAL_DISCOVERY_GAPS` | `instructions/24_FINAL_VALIDATION_REPORT.md` | `VAL-FINAL-REPORT` |
| 56 | IMPORTANT FINAL OPERATING PRINCIPLE | `IMPLEMENTED` | `instructions/START_HERE.md`<br>`instructions/04_AUTONOMOUS_OPERATING_CONTRACT.md`<br>`instructions/06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md` | `VAL-OPERATING-CYCLE` |

## Atomic proof
- Atomic obligations: **464**
- Sections represented: **1–56 exactly once at section level and at least once atomically**
- Machine catalog: `catalogs/master_prompt_atomic_requirements.json`
- Reviewable CSV: `audit/MASTER_PROMPT_ATOMIC_COMPLIANCE.csv`
- Enforcer: `tools/validate_autonomous_controls.py`

The final release report must cite executed results rather than treating this mapping as proof that external activation or empirical model outcomes occurred.
