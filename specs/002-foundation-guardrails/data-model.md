# Developer records

`legacy-baseline.json` schema 1 contains `schema_version`, immutable `revision`,
`budget` (50) and `files` (path-to-nonnegative-line-count mapping of ten largest legacy modules).
Paths must be repository-relative Python application paths, never parent traversals or tests.
Counts and selection must match that revision. Unsupported versions fail with an actionable error.
Changing this developer record is reviewed in Git; no user data needs migration.

Dependency violations contain source path, 1-based line, target name and reason.
Growth results contain base revision and per-path before/after counts; total is their signed sum.
Renames preserve the original record's identity. There is no mutable runtime state.
