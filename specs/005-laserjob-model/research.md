# Research: Laser job model

Decision: frozen dataclasses, required pass parameters and tuple pass order. Rationale: no
CNC tool database coupling, mutable shared defaults or fallback parameters. Device-specific
validation belongs to a future backend; positive scalar units are checked here.

Decision: a PlanarRegion stores canonical WKB hex and converts through Shapely only inside core.
Rationale: job fields remain plain serializable data while polygon holes and multipart geometry
are preserved. Alternatives: storing live legacy/Shapely objects breaks the plain-data boundary;
hand-written coordinate topology serializers duplicate the existing geometry library.

Decision: strict schema-1 JSON envelopes for recipe and job, explicit kind and units fields,
duplicate/unknown keys rejected. Nested job recipe retains its own envelope. Rationale: future
schema changes must be migrated deliberately. No historical format exists in this first schema.

Decision: Gerber bridge reads the object's declared units and current solid_geometry, recursively
accepts polygon/multipolygon collections, unions overlapping copper, converts inch to mm once,
then creates a PlanarRegion. Empty or unsupported input fails. No mutation or repair is performed.
Source-aperture classification for pad/trace modes belongs to the later contour/hatch feature.
