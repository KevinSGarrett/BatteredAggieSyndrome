# Jira Cloud Import Compatibility — Verified August 2026

The pack supplies two equivalent hierarchy shapes and explicit aliases so the administrator can match the terminology exposed by the destination Jira Cloud import experience:

1. `JIRA_CLOUD_CURRENT_IMPORT.csv` and its identical alias `JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv` use current Cloud terminology: `Work type`, `Work item ID`, and `Parent`.
2. `JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv` and its identical alias `JIRA_EXTERNAL_SYSTEM_IMPORT.csv` use the legacy administrator External System Import terminology: `Issue type`, `Issue ID`, and `Parent`.

Choose exactly one shape after inspecting the destination mapping screen; do not import both. Current official Atlassian guidance reviewed for this pass states that hierarchy reconstruction requires a unique work/issue ID plus the parent ID, that the ordinary non-admin bulk CSV creator is not an equivalent multilevel hierarchy importer, and that importing into an existing Jira Cloud project/space requires the administrator import workflow and compatible destination configuration. Work types, statuses, priorities, fields/options, components, hierarchy levels, users, and link types must be discovered or created/mapped by an authorized administrator; the pack does not invent their IDs.

The REST templates use Jira Cloud REST API v3 and Atlassian Document Format for descriptions. Issue creation, status transitions, and issue links are deliberately separate: create the hierarchy first, reconcile `Local Issue ID → Jira key`, discover real transition/link identifiers, and only then execute the inert transition/link plans.

Always use a disposable project or representative test subset first and complete `POST_IMPORT_VALIDATION_CHECKLIST.md`, because the available mappings and UI terminology can vary by Jira project/space type and site configuration.
