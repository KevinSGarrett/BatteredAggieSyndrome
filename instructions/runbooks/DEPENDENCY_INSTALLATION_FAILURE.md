# Runbook — Dependency or Environment Installation Failure

## Trigger

Package install, editable install, lock resolution, import, compiler, CUDA/driver, or environment bootstrap fails.

## Capture

- OS/architecture;
- Python and pip versions;
- active interpreter/environment path;
- command and exact error;
- lock/requirements file identity;
- network/package index state;
- GPU/driver stack when relevant.

Do not capture secret values.

## Diagnose layers

1. wrong interpreter/environment;
2. unsupported Python/platform;
3. lock/pin conflict;
4. missing build tool/system library;
5. unavailable/incorrect wheel;
6. network/index/rate-limit issue;
7. permissions/path length;
8. corrupted cache;
9. optional dependency installed in wrong profile;
10. dependency policy/license/security conflict.

## Recovery order

- verify interpreter and documented install command;
- use existing lock/profile;
- reproduce in a clean approved temporary environment without deleting the current one;
- inspect dependency resolver output;
- clear only proven disposable caches if needed;
- change version/dependency only with requirement, license, compatibility, and test review.

Do not repeatedly recreate environments or upgrade everything blindly.

## Exit criteria

Install succeeds reproducibly under approved profile, or a precise environment/dependency blocker and safe alternative is documented.
