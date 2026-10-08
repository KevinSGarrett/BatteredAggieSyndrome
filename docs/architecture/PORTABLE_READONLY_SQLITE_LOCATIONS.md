# Portable read-only SQLite locations (BAT-717)

Every installed BAS query family — `bas-national-population-query`, `bas-national-history-query`,
`bas-source-time-query` (with its `--archive-evidence` sidecar), `bas-history-availability-query` and
`bas-staff-query` (with its explicit `--career-successor` attachment and the successor's declared Attempt 4 file) —
opens every database, parent and attachment through one narrow helper, `aggie_analytics.readonly_sqlite`.
Import and write APIs (for example `cycle33.query.connect_for_import`) are separate and unchanged.

The population and history query modules are standard-library only by their accepted contract (BAT-710, BAT-711,
pinned by their `test_query_module_uses_the_standard_library_only` tests). They therefore do not import the helper;
each carries a byte-identical copy of the helper's marked literal-location core
(`# ---- BEGIN/END BAT-717 LITERAL-LOCATION CORE`). `tests/test_readonly_sqlite_location.py` requires the three
copies to stay identical and to answer every spelling exactly as the helper does.

## Contract

A database argument is a filesystem path that names one literal local file. It is never a SQLite URI: the helper
percent-encodes every character that is not unreserved, so `?`, `#`, `%`, `&`, `=`, an apostrophe, spaces and
non-ASCII characters stay part of the file name and cannot become URI parameters, a fragment or an authority. The
only parameters are the helper's own `mode=ro`, plus `immutable=1` where a caller deliberately asks for it (the
career successor attachment and its Attempt 4 file, as before).

| Spelling (Windows) | Behaviour |
| --- | --- |
| Relative, absolute or forward-slash drive path | Made absolute exactly as Win32 resolves it (`GetFullPathNameW`); the URI is the previous `Path.as_uri()` form |
| Native extended-length drive path `\\?\C:\...` (short or beyond 260 characters) | Kept verbatim; the only spelling of a long location on a host without long-path support |
| `\\?\C:\...` that Win32 normalization would change (a trailing dot, a `.` or `..` component, a `/`) | Refused `DATABASE_LOCATION_NOT_LITERAL`: SQLite's Windows VFS normalizes the name it opens, so it would read a different file than the caller's own reads verified |
| Local drive device path `\\.\C:\...` | Normalized to the same file `C:\...` |
| UNC (`\\server\share`, `//server/share`, `\\?\UNC\...`), other `\\.\` devices, volume GUIDs, `GLOBALROOT` | Refused `DATABASE_LOCATION_UNSUPPORTED` before any filesystem access (network and device locations are not supported) |

On POSIX the location is the path's realpath, as before; literal file names keep every character.

Every connection is opened with `mode=ro` (a missing file is never created and there is no read-write fallback), and
before any row is read the helper confirms from `PRAGMA database_list` that SQLite opened the same filesystem object
(device and file identity) as the literal path. Each consumer checks the location lexically before any other file
access and reports a refusal with its own error type and the helper's code; the career successor reports
`REFUSED_CAREER_SUCCESSOR_LOCATION_NOT_SUPPORTED` with that code in its detail.

## Unchanged

Records, totals, identities, profiles, paging, verification and every existing refusal rule are unchanged. Location
metadata a consumer already reports (the staff query's successor and predecessor file names) names the file actually
read. No OS setting, long-path policy, VFS choice or network access is involved.
