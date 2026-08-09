# Runbook — Secret or Sensitive Data Incident

## Trigger

Credential, private key, token, restricted raw data, or sensitive personal information appears in repository, logs, Jira, GitHub, artifacts, screenshots, or ZIPs.

## Immediate containment

- stop copying/publishing the value;
- avoid quoting it in comments or reports;
- identify exact locations and exposure scope;
- prevent further pushes/uploads where safe;
- preserve unrelated work.

## Remediation

1. remove/redact from current working state;
2. notify credential/data owner through approved private channel;
3. revoke/rotate credential if exposed;
4. determine whether commit/history/cache/artifact/Jira/PR remediation is required;
5. use Human Required authority for shared-history rewrite or destructive cleanup;
6. rerun scans across repository and packages;
7. record incident metadata without the value.

## Evidence

Record type, affected locations, first/last exposure, committed/pushed/shared status, owner action, remediation, scan results, and residual risk.

## Exit criteria

Sensitive material is no longer exposed in active surfaces, credential/data owner has handled required rotation/remediation, and scans pass.
