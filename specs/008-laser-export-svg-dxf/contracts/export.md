# Export contracts
`core.laser_svg.svg_document(paths, bounds, pass_name, cancelled=None) -> str` emits SVG
with one polyline per exposure path, fill none, explicit mm/viewBox and local Y-down mapping.
`core.laser_dxf.dxf_document(paths, pass_index, cancelled=None) -> str` emits ASCII R2000
planar LWPOLYLINE entities in one ordinal layer, in input order, $INSUNITS=4. Closed paths
drop the duplicate endpoint and set closed flag; open paths remain open.
`core.laser_manifest.manifest_to_json(data: dict) -> str` and `manifest_from_json(text) -> dict`
strictly validate schema 1 as data-model.md, using existing recipe/pass validation.
`laser.export.export_plan(plan: LaserPlan, destination: Path | str, format: str,
cancelled: CancelCheck=None) -> Path` validates limits and atomically writes a complete ZIP.
It raises existing PlanningCancelled before publication, ValueError for bad input/limits and
OSError for file failures. After successful os.replace it returns success even if a late cancel
arrives. Source plan and existing destination remain untouched on prior failure.

UI: `LaserExportControls(QWidget)` owns format selector, export action and one worker;
`set_plan(plan_or_none)`, `cancel()`, `shutdown()`, `busy` and signals `status_changed(str)`,
`busy_changed(bool)`. It snapshots plan on start, asks for destination through standard save
dialog and reports success path. Panel clears it on edits/planning start, supplies completed
plan, integrates busy state and routes cancel/shutdown. No general task-runner abstraction.
