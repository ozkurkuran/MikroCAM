# Data model: Laser contour and hatch

- `CopperFeatures(copper, traces=None, pads=None, board=None)` holds PlanarRegion snapshots.
  None means unavailable/empty semantic area; copper is always required. All are source mm.
- `PlanOptions(contour_mode='outer', hatch=False, spacing_mm=0.1, angle_deg=0.0,
  cross_hatch=False, region_mode='copper')` is frozen and validated; visible geometric inputs.
  Contour modes: none/outer/inner/trace/pad/board. Region modes: copper/clearance.
  At least a contour or hatch must be selected; cross hatch requires hatch.
- `LaserPath(points, role, scan_index=None, hatch_family=None)` has immutable finite XY tuples,
  >=2 distinct points. role is contour or hatch; hatch has integer scan index and family 0/1.
  Each path is one exposure polyline, never an implicit connector between clipped segments.
- `LaserPlan(job, options, paths)` is immutable; paths are already placed mm values, while job
  retains source data. Empty output is rejected. This is ephemeral, not a new file schema.

No device data, Qt types, mutable geometry arrays or host objects are retained. Pass expansion
and editing follow in 007. Recipe/job schema 1 is unchanged; no migration is needed here.
