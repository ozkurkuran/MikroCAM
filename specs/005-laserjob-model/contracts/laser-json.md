# Core and bridge contracts

Core exports LaserPass, LaserRecipe, PlanarRegion and LaserJob from `core.laser_job`.
`core.laser_json` exposes `recipe_to_json`, `recipe_from_json`, `job_to_json`, `job_from_json`.
Output is deterministic UTF-8-compatible JSON text; callers own file I/O. No global defaults.

Recipe envelope has exactly `kind: "mikrocam.laser-recipe"`, `schema_version: 1`, `name`,
`passes`. Each pass has exactly `name`, `power_percent`, `speed_mm_s`, `frequency_khz`,
`pulse_width_ns`. Pass order is significant. No omitted parameter is inferred.

Job envelope has exactly `kind: "mikrocam.laser-job"`, `schema_version: 1`, `units: "mm"`,
`name`, `region_wkb_hex`, `recipe` (complete recipe envelope), and `placement`.
Placement has exactly `origin`, `translation`, `rotation_deg`, `mirror_x`; pairs are 2-element arrays.

Malformed/unknown/duplicate fields, invalid values or unsupported versions raise ValueError
with the offending context. Invalid geometry objects passed to from_geometry raise TypeError.

`bridge.gerber.gerber_region(obj)` accepts a Gerber host object (`kind == "gerber"`) with
declared `units` MM or IN and `solid_geometry`; returns detached mm PlanarRegion. No global
settings/defaults lookup. Unsupported objects/units/geometry raise ValueError. The bridge may
use core geometry conversion helpers; all polygon/union/unit math stays in core so domain
consumers can share it later without importing Shapely directly.
