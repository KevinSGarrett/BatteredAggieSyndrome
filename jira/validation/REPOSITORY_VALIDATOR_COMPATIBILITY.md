# Original Repository Validator Compatibility

- Pre-generation W25 strict repository validator: **PASS** (recorded in `BASELINE_REPOSITORY_VALIDATION.json`).
- Post-generation original strict validator exit code: **1**.
- Manifest-coverage findings observed in captured output: **1740**.
- Non-manifest findings in captured output: **0**.
- Non-Jira scope hash comparison: **PASS** (863 files; missing=0, added=0, changed=0).

The original W25 global provenance manifest predates this Jira generation and therefore does not list newly created `jira/` files. The task explicitly confined new Jira-system changes to `jira/` and prohibited rewriting unrelated existing governance/provenance merely to make the old manifest accept new files. The original global strict validator is therefore expected to report Jira-local files as unrepresented until a later, explicitly authorized whole-repository provenance refresh.

`NON_JIRA_SCOPE_DIFF.json` independently proves whether any original non-Jira repository file changed. The Jira subtree has its own complete release boundary:

- `validation/JIRA_FILE_MANIFEST.csv`
- `validation/JIRA_FILE_HASHES.sha256`
- `validation/NON_JIRA_SCOPE_DIFF.json`
- `tools/validate_jira_manifest.py`
- `tools/validate_jira_pack.py`
- `tools/run_second_pass_audit.py`

This is a transparent manifest-authority boundary, not a hidden product or Jira-pack validation failure. A future controlled whole-repository release may regenerate the global project manifest after reviewing the Jira addition.
