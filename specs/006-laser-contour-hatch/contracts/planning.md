# Planning and desktop contracts

`core.laser_paths`: CopperFeatures, PlanOptions, LaserPath, LaserPlan as in data-model.md.
`core.laser_features.features_from_gerber(copper, records, units, outline=None, outline_units=None)`
returns CopperFeatures. `records` is a detached sequence of `(aperture_type, solid, follow)`
values copied by bridge; missing metadata is an empty tuple. `outline` is explicit selected
host follow_geometry; core validates/normalizes units and builds board area from closed paths.
`core.laser_geometry.contour_paths(features, mode, cancelled=None)` returns source-mm paths.
`core.laser_geometry.hatch_paths(region, spacing_mm, angle_deg, cross_hatch=False, cancelled=None)`
returns source-mm paths. `selected_area(features, region_mode)` returns PlanarRegion.
`laser.planner.plan_laser(job, options, features=None, cancelled=None)` returns LaserPlan.
`cancelled` is an optional zero-argument callable returning bool. Cancellation raises
`PlanningCancelled` (defined in core.laser_paths); invalid/empty/too-complex requests ValueError.
Input feature copper must match the job's source copper; source geometry is never modified.

`bridge.laser_cam.LaserCamHost(app)` wraps host access. Methods:
- `source_names() -> tuple[str,...]`: current Gerbers; `active_name() -> str | None`.
- `snapshot(source_name, outline_name=None) -> CopperFeatures`: GUI-thread snapshot.
- `publish_preview(plan) -> str`: GUI-thread Geometry publication; replaces only owned preview.
- `parent_widget()`: main window; `existing_panel()` / `remember_panel(panel)` preserve one dock.

`ui.laser_cam.open_laser_cam(app) -> LaserCamPanel` creates/reuses a right-side QDockWidget.
`LaserCamPanel(host)` offers source/outline, load-recipe, placement, contour/polarity/hatch
controls, generate/cancel/status. It retains the last successful plan for slice 008 export.
Public `set_recipe(recipe)` permits file loading and smoke setup without dialog automation.
`generate()` snapshots current inputs then starts one worker; cancellation invalidates result.
`shutdown()` cancels and waits for worker without touching widgets from its thread.
All user-facing strings use the existing `_()` translation callable via builtins/gettext.
