# Jira Import Pack

## Choose one hierarchy import mode

After completing `../project/JIRA_TARGET_PROFILE.yaml` and inspecting the destination administrator import screen, choose **one** of these equivalent ordered files:

- **Current Jira Cloud terminology:** `JIRA_CLOUD_CURRENT_IMPORT.csv` (alias: `JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv`) using `Work type`, `Work item ID`, and `Parent`.
- **Legacy administrator External System Import terminology:** `JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv` (alias: `JIRA_EXTERNAL_SYSTEM_IMPORT.csv`) using `Issue type`, `Issue ID`, and `Parent`.

Do not import both aliases. Each file contains the complete 463-record hierarchy in parent-before-child order: Epics, then Stories/Tasks, then Sub-tasks.

## Required execution sequence

1. Discover the actual Jira Cloud project/space configuration and populate `../project/JIRA_TARGET_PROFILE.yaml`.
2. Create or map only the controlled work types, statuses, priorities, components, fields/options, hierarchy levels, and link types required by the pack.
3. Select the matching current or legacy CSV shape above. The ordinary end-user bulk CSV creator is not treated as a reliable multilevel hierarchy reconstruction path.
4. Run a representative subset in a disposable project and verify UTF-8 content, descriptions, custom fields, parent mapping, and status/priority mappings.
5. Import the full ordered hierarchy with `Work item ID`/`Issue ID` and `Parent` mapped exactly.
6. Export the created work items with `Local Issue ID`, real Jira key, Jira numeric ID, status, assignee, sprint, and update timestamp. Run `../tools/reconcile_jira_export.py <export.csv> --dry-run` first, resolve reported conflicts, then run it without `--dry-run`.
7. `POST_IMPORT_KEY_MAP_TEMPLATE.csv` must remain blank and reusable. Successful reconciliation writes actual assigned values to `POST_IMPORT_KEY_MAP.csv`, stores raw Jira operational fields in canonical records, rejects `Done` without complete/verified local evidence, and rolls back if strict validation fails.
8. Apply desired workflow states only after discovering valid destination transitions, using the inert `JIRA_API_STATUS_TRANSITION_PLAN.jsonl` as a plan—not as a pre-authorized executable script.
9. Create dependency and related links only after real keys and actual link-type names are known, using `JIRA_LINKS.csv` and `JIRA_API_LINK_PAYLOADS.jsonl`.
10. Complete `POST_IMPORT_VALIDATION_CHECKLIST.md`, rebuild all derivatives, and run `python -B jira/tools/validate_second_pass.py`.

## Portability and safety boundaries

- No Jira-generated issue key/ID, field ID, project ID, work-type ID, user/account ID, workflow/transition ID, component ID, or link-type ID is fabricated.
- Logical workflow state, implementation maturity, evidence state, and execution mode remain separate fields.
- API payloads target Jira Cloud REST API v3 and use Atlassian Document Format, but remain inert templates until the target profile and post-import key map are complete.
- Stage CSVs are inspection/recovery views. Independently importing them requires replacing local parent references with real Jira keys; the single ordered file is preferred.
- Live import, credentials, administrator authorization, and destination-specific mapping are unavoidable external steps, not evidence that the local pack is incomplete.

See `ATLASSIAN_2026_COMPATIBILITY.md`, `IMPORT_CONFIGURATION_NOTES.md`, `FIELD_MAPPING_GUIDE.md`, and `POST_IMPORT_VALIDATION_CHECKLIST.md`.
