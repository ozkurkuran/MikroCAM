# Core values

- `LaserPass(name, power_percent, speed_mm_s, frequency_khz, pulse_width_ns)`: frozen;
  names nonempty strings; finite nonboolean real parameters, all >0, power <=100.
- `LaserRecipe(name, passes)`: frozen; nonempty name, nonempty tuple of LaserPass, unique pass names.
- `PlanarRegion(wkb_hex)`: frozen plain string; canonical 2D WKB hex of a valid nonempty
  Polygon/MultiPolygon, coordinates finite and in mm; Z/M rejected. `from_geometry()` and
  `to_geometry()` perform conversion; no host reference is retained.
- `LaserJob(name, region, recipe, placement=Placement())`: frozen; typed nested values;
  `placed_geometry()` applies that one Placement to detached source geometry exactly once.

JSON serializes only plain string/float/bool/list/object data. Recipe/job versions start at 1;
future migration must preserve old examples and add explicit migration tests. A job file is not
an Evo project file or a manufacturing command stream. Device capability limits remain external.
