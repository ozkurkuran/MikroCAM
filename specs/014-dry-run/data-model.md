# Data model
core.dry_run.DryRunResult is frozen and contains original SourceSnapshot/PreflightReport,
dry_z_mm, derived PreparedJob, and lineage tuple[int|None,...] indexed by physical derived line.
None marks generated preamble/retract/end lines; positive values identify original source lines.
Construct through prepare_dry_run(source,report,dry_z_mm,*,cancelled=None), which recomputes exact
original report, interprets source, builds bounded derived bytes, re-analyzes and constructs
PreparedJob. Derived setup changes only safe_z_mm to dry_z_mm; current initial and mapping remain.
No persistent schema; no duplicate job sender/model hierarchy. DryRunWorker owns immutable inputs
and cancellation. DryRunPanel exposes reviewed_binding/reviewed_changed for the existing explicit
MachinePanel.load_preflight binding seam.