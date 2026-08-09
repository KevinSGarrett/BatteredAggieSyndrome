# Runbook — Agent Loop Recovery

## Trigger

Repeated command/failure/edit/review/planning cycle occurs without new evidence or meaningful state change.

## Stop and record

```text
Repeated action:
Equivalent attempts:
Expected state:
Actual state:
Evidence unchanged:
Likely failing layer:
```

## Recover

1. stop the repeated command;
2. reduce to smallest reproducer;
3. inspect authoritative docs/logs/code rather than repeating;
4. form a materially different hypothesis;
5. try a different layer or tool once;
6. verify whether a prior write already succeeded;
7. after up to three distinct approaches, block if unresolved;
8. switch to independent Ready work;
9. if none exists, produce concise global blocker.

## Loop examples

- unchanged CI reruns;
- repeated dependency installs;
- status checking without action;
- same edit reverted by same test;
- creating more plans/templates instead of implementation;
- repeated Git cleanup attempts;
- duplicate Jira/PR writes.

## Exit criteria

New evidence/progress exists, or the task is accurately blocked and the agent has moved to valid work/stopped globally.
