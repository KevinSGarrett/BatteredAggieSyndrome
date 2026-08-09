# Import Configuration Notes

- Official Atlassian guidance was reviewed on 2026-08-08; recheck destination behavior immediately before a live import.
- Match the destination UI to either the current work-item CSV vocabulary or the legacy External System Import vocabulary; never import both equivalent aliases.
- The ordinary end-user bulk CSV creator is not treated as a reliable multilevel hierarchy reconstruction mechanism; use the authorized administrator import experience or the REST templates.
- Existing-project/space imports require administrator permissions and compatible destination work types, hierarchy, statuses, priorities, fields/options, components, screens, and custom fields.
- Parent-child preservation depends on parent-before-child ordering plus unique `Work item ID`/`Issue ID` and `Parent` mapping.
- Do not use deprecated `Epic Link` behavior unless an explicitly verified non-Cloud/legacy target requires it; the portable Cloud design uses `Parent`.
- Create work items first. Reconcile real keys, discover transitions and link types, then apply workflow transitions and links as separate controlled operations.
- REST v3 payload templates use Atlassian Document Format; all destination IDs and account references remain placeholders until discovered.
- Use a disposable project or test subset before the bulk operation. Never assume bulk imports or links can be rolled back safely.
