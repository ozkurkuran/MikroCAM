# Export data model
Archive contains `pass-001.svg` (or dxf), sequential pass files, `recipe.json`,
`manifest.json`, `README.txt`. Filenames depend only on index, never user-supplied names.
SVG frame records original bounds xmin,ymin,xmax,ymax; x'=x-xmin, y'=ymax-y. Viewport width
and height are extent or 1 mm if exactly zero. DXF preserves placed XY, units mm.

Manifest schema 1 exact fields: `kind='mikrocam.laser-export'`, `schema_version=1`,
`format` ('svg'/'dxf'), `units='mm'`, `job_name`, `bounds_mm` (four finite numbers),
`interlace_n`, `coordinate_mapping` ('svg-local-y-down'/'placed-xy'), `recipe_file='recipe.json'`,
`passes` (nonempty ordered list). Each entry exact fields: `index` (1-based), `name`, `file`,
`sha256` (64 lowercase hex), `path_count` (positive integer), `settings` (existing exact pass
name/power_percent/speed_mm_s/frequency_khz/pulse_width_ns values).
Strict codec rejects missing/unknown/duplicate/nonfinite/future schema fields. JSON remains
deterministic. No importer executes instructions or accesses a machine.
