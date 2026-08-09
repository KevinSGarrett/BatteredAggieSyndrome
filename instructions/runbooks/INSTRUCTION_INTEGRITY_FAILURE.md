# Runbook — Instruction, Manifest, Link, or Package Integrity Failure

## Trigger

Instruction validator, manifest/hash, internal-link, schema, package safety, or compliance coverage check fails.

## Diagnose

Run:

```powershell
python -B tools\validate_instruction_pack.py --repo-root . --strict
python -B tools\package_instruction_pack.py --repo-root . --verify-only
```

Identify:

- missing/unmanifested file;
- broken link/path/ID;
- human/machine policy contradiction;
- missing master-prompt coverage mapping;
- stale hash;
- forbidden/secret package member;
- nondeterministic package;
- obsolete competing instruction file.

## Repair

- edit the canonical policy/procedure;
- update machine-readable companion and manifest together;
- repair inbound/outbound links;
- regenerate hashes deterministically;
- rerun strict validator and tests;
- extract the ZIP into a clean temp directory and revalidate.

Do not disable the failing check or remove coverage merely to package successfully.

## Exit criteria

Strict validation, secret/forbidden scan, deterministic packaging, ZIP integrity, extracted validation, and compliance coverage all pass.
