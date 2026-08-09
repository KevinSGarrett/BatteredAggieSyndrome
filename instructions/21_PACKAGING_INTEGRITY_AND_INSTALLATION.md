# Packaging, Integrity, Installation, and Hydration Policy

The live canonical instruction system is the `instructions\` directory inside `C:\BatteredAggieSyndrome`. ZIP files are transfer and backup artifacts; they are never a second editable source of truth.

Machine companion: `policies/packaging_policy.json`.

## 1. Required deliverables

A release of this control system produces:

1. a validated live `instructions\` directory inside the repository;
2. a standalone deterministic instruction ZIP named `BatteredAggieSyndrome_Autonomous_Instructions_v<version>.zip`;
3. a complete updated repository ZIP named `BatteredAggieSyndrome_with_Autonomous_Instructions_v<version>.zip` when transfer of the whole repository is required;
4. SHA-256 sidecars for each ZIP;
5. a final validation and activation report outside the repository.

Generated exports belong outside the canonical repository or in an ignored local artifact location. Do not commit them unless an explicit repository policy later establishes a release-artifact lane.

## 2. Forbidden package contents

Do not include:

- `.git` metadata or temporary worktrees;
- `.env`, credentials, tokens, PATs, private keys, cookies, or secret values;
- virtual environments, package caches, `__pycache__`, test caches, IDE state, or OS junk;
- local Jira issue caches containing private content unless explicitly sanitized and approved;
- raw restricted/licensed data, private source payloads, or large local data lakes;
- model checkpoints, experiment stores, databases, logs, screenshots with secrets, or unrelated generated artifacts;
- nested ZIPs or old exports.

References to environment-variable names and expected secret aliases are allowed; values are not.

## 3. Standalone pack contract

The standalone ZIP root must be exactly `instructions/`. Its member set must match the canonical instruction directory after excluding no canonical file. The archive must use safe relative paths, deterministic ordering and timestamps, valid CRCs, and no duplicate or case-colliding names.

Before packaging:

```powershell
python -B tools\validate_autonomous_controls.py --repo-root . --strict
python -B tools\validate_jira_control_plane.py --repo-root . --strict
python -B tools\package_instructions.py --repo-root . --output-dir <outside-repo-path>
```

The package tool must validate before writing, write through a temporary file, verify extraction, compare extracted hashes/member set with the canonical directory, and emit a checksum sidecar. A partial ZIP must never be reported as successful.

## 4. Full-repository export contract

A full transfer ZIP must include every intended versioned/control file needed to recreate the working tree but exclude local Git metadata and nonversioned artifacts. It must be built from a clean, validated staging view—not by recursively zipping the repository while writing the ZIP into itself.

The export process must:

1. validate instruction, Jira control-plane, W25 terminal state, repository integrity, and tests;
2. apply the repository packaging exclusions;
3. scan paths and contents for secrets/forbidden artifacts;
4. produce deterministic member ordering/timestamps;
5. verify CRC, extraction safety, and expected file set;
6. rerun control validators against an extracted copy;
7. write SHA-256 and a final report outside the archive.

## 5. Installation into the Windows repository

Never overwrite an unknown working tree by extracting blindly.

1. Back up or preserve the current directory through Git and approved backup procedures—not by renaming it to a replacement canonical repository.
2. Run the read-only control-plane audit and inspect dirty/unique work.
3. Compare the incoming pack against the current `instructions\`, root controls, `.codex`, `.github`, Jira control files, tools, tests, and governance pointers.
4. Apply changes on a short-lived branch or controlled worktree after repository identity is established.
5. Do not replace `.git`, `.env`, local data, or unknown user files.
6. Run all validators and tests from the actual local checkout.
7. commit/push/PR only under explicit authorization and the Git/GitHub policy.

## 6. Hydration and external activation

After installation:

- reconcile local Git and the GitHub remote;
- hydrate Jira only from the authorized BAT site;
- verify branch protection, merge settings, required checks, secret scanning, and automatic branch deletion before enabling enforcement recommendations;
- verify real environment-variable names and source access without exposing values;
- preserve AC-038 and THR-011/THR-012 as unresolved until the representative hardware benchmark runs;
- update audit records and local mirror metadata with actual evidence.

Hydration may change external-state snapshots but must not weaken canonical technical governance.

## 7. Integrity ledger

`manifest.json` lists every instruction file, purpose, authority, read tier, trigger, dependencies, version, and SHA-256. `FILE_HASHES.sha256` is generated last from the canonical directory and excludes itself. The validator must reject missing, extra, stale, duplicate, unsafe, or unmanifested files.

Do not “fix” integrity by updating hashes while leaving a contradictory or unauthorized policy change unresolved.
