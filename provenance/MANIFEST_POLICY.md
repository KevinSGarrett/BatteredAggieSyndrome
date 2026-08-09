# Manifest Policy — Executable as of W02

`provenance/PROJECT_FILE_MANIFEST.csv` and `provenance/PROJECT_FILE_HASHES.sha256` do **not** include themselves. Every other canonical repository file is in scope when the manifest is generated.

Generation is implemented by `tools/repo_integrity.py`:
1. generate `CURRENT_TREE.txt`;
2. enumerate canonical files in sorted POSIX-relative-path order;
3. exclude the two self-referential manifest/hash files;
4. record byte size and SHA-256;
5. emit a sorted GNU-style SHA list;
6. compute tree fingerprint as SHA-256 over sorted `sha256 + two spaces + relative path + newline` lines.

The hydration `PACK_BINDING.json` records the cumulative ZIP SHA-256 and repository tree fingerprint separately. ZIP files are produced with sorted members and normalized timestamps/permissions.
