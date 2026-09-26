# Identity and notice records

Product identity is immutable plain data: name MikroCAM, semantic display version 0.1.0,
release date, description, repository/releases/issues URLs, own and upstream copyright lines.
The host's compatibility version is deliberately separate and never derived from display version.

Dependency inventory schema 1 contains a list of normalized package names, exact versions,
groups (runtime/development/optional-image), upstream license metadata, source URLs and files.
Each file record contains repository-relative path, source location and SHA-256 digest of the
unaltered bytes. Paths cannot escape THIRD_PARTY_LICENSES; names are unique after normalization.
The inventory is developer release metadata, not a user file; future schema changes require
an explicit checker update and regression fixture for the previous schema.
