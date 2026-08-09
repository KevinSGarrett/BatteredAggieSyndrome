# Cumulative + Hydration Packaging Integrity

## Goals
- verify the prior wave before mutation;
- package one canonical cumulative repository, never deltas;
- generate a compact allowlisted hydration pack;
- prevent self-referential manifests;
- reject unsafe ZIP paths, secrets and forbidden artifacts;
- make ZIP output reproducible for identical file content.

## Prior-wave verification
`tools/verify_prior_wave.py` reads `PACK_BINDING.json` from the hydration ZIP, checks cumulative SHA-256 and expected next wave, rejects traversal/absolute ZIP members, and can safely extract the verified cumulative repository.

## Repository manifest
`tools/repo_integrity.py` generates `CURRENT_TREE.txt`, then hashes every canonical file except:
- `provenance/PROJECT_FILE_MANIFEST.csv`
- `provenance/PROJECT_FILE_HASHES.sha256`

The tree fingerprint is SHA-256 over sorted lines of `file_sha256 + two spaces + POSIX relative path + newline` for manifest-covered files.

## Deterministic ZIP policy
Members are sorted. ZIP timestamps are fixed to the ZIP epoch and permissions are normalized. This prevents packaging time/order from changing the ZIP when repository bytes are identical.

## Hydration allowlist
`configs/hydration_manifest.json` explicitly maps canonical repository files to hydration archive names. Generated `HYDRATE_FIRST.md`, `PACK_BINDING.json` and `HYDRATION_FILE_HASHES.sha256` are added during packaging.

## Commands
Build:
`python tools/package_wave.py --repo-root . --wave W02 --output-dir <dir> --previous-cumulative <W01.zip>`

Validate completed pair:
`python tools/validate_wave_pair.py --cumulative <W02 cumulative> --hydration <W02 hydration> --expected-wave W02`
