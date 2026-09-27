# Data model

Frozen SvgViewport maps local user units to physical mm. SvgPaint records inherited geometry-relevant
paint policy. SvgElement carries source ID/kind/immutable attributes plus accumulated matrix/paint.
SvgDocument binds exact source SHA256 and viewport to bounded resolved elements and notices.

SvgPath keeps immutable sampled local points and explicit Close state. SvgRendered retains mapped
paths and valid manufactured geometry separately: implicit fill closure must not overwrite source
centreline metadata. SvgImportResult binds one rendered result to each element, exposes flattened
geometry and bounded notices, and enforces the document coordinate budget. Shapely 2 values are
immutable and remain in core/bridge; the stdlib-only importer domain uses no Shapely imports.

No model is persisted and no schema migration is required. Existing object persistence receives only
host-unit geometry through its normal serializer. Placement consumes authoritative mm geometry in
later CAM steps; SVG source mapping does not change the established machine transform.
