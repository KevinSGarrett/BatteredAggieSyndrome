# Runbook — Failed CI Diagnosis

## Trigger

A GitHub check/workflow fails, hangs, is canceled, or does not appear on the expected head SHA.

## Verify identity

- repository and PR number;
- base/head branches;
- current head SHA;
- workflow/job/step;
- whether failure belongs to the latest commit.

## Read evidence

Inspect logs, annotations, runner OS/Python, dependency install output, artifacts, and check conclusion. Do not infer from a red badge alone.

## Classify

- code/test regression;
- stale/inaccurate test;
- dependency/lock issue;
- OS/path/line-ending issue;
- permission/secret issue;
- deterministic configuration;
- flaky/transient runner/network/service;
- external provider unavailable;
- workflow definition defect;
- required check missing/misconfigured.

## Act

- reproduce locally when practical;
- make the smallest diagnosis-backed change;
- run relevant local gates;
- push to the same branch/PR;
- retry one plausible transient failure once;
- if external, record blocker and avoid code churn.

## Do not

- rerun unchanged deterministic failure repeatedly;
- weaken tests/protected rules to pass;
- create a new PR;
- mark evidence passed when job was skipped/canceled;
- expose secrets in logs/comments.

## Exit criteria

The current head SHA has required passing checks, or the exact external/misconfiguration blocker is recorded with owner/unblock action.
