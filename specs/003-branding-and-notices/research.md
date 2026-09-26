# Research: Branding and notices

## Separate display identity from compatibility
Decision: new core identity constants and UI presentation helpers; keep App.version='Unstable'
and version_date, QSettings identifiers and storage paths. Rationale: host version selects tool
database filenames, defaults migrations and project metadata. Renaming it would be a data migration.
Alternative rejected: replacing every FlatCAM string would damage attribution and compatibility.

## Existing presentation surfaces
Decision: wire MainGUI initial title and set_ui_title, AppUIActions About/property view and shell
banner. Preserve About author/translator/icon credits and link upstream credit separately from
MikroCAM development/releases/issues. Use the existing translation mechanism for UI sentences.
No new branded artwork is needed in this slice.

## Update boundary
Decision: disable product-facing Evo checks/download/revert controls and short-circuit the host
update entry points through a small UI helper. Rationale: Beta currently suppresses automatic
checks, but forced/manual requests bypass the preference and target Evo. A renamed fork must not
offer that payload. Existing updater services and tests remain available as upstream code.
Alternative rejected: changing one preference does not prevent forced requests; repointing the
updater would introduce a new update system outside the roadmap.

## Notices
Decision: inventory every exact pin across three requirements files; copy upstream full license
and supplied bundled notices with SHA-256 hashes, sources and install groups. Where wheel metadata
omits text, use the exact tagged upstream package/source archive. Include source-vendored packages
separately. Rationale: a single MIT statement cannot describe GPL/LGPL dependencies or bundled
components. New binary distribution and browser bundling remain later work.
Alternative rejected: metadata labels alone omit actual terms and authors. Preserve existing
asset attribution and state any missing per-file provenance without inventing rights.
