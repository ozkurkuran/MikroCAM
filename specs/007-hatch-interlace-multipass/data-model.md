# Data model: Interlace and multiple passes
- Append `interlace_n: int = 1` to frozen PlanOptions; strict non-bool integer 1..1,000,000.
- Add frozen `LaserPassPlan(settings: LaserPass, paths: tuple[LaserPath,...])`; require valid
  settings and nonempty typed paths. No coordinates are copied or transformed here.
- `LaserPlan.pass_plans` property returns one LaserPassPlan per recipe pass in original order,
  each referencing exactly `plan.paths`.
- `interlace_paths(paths, n, cancelled=None)` returns ordered tuple. Contours stay first/in
  original order. Hatch key=(family, scan_index % n, scan_index, original_position); N=1 returns
  original tuple/order. Invalid N fails; cancellation raises existing PlanningCancelled.
- Recipe editor drafts are UI text until `.get_recipe()` validates all fields through
  LaserPass/LaserRecipe. Name/order and numeric values round-trip via existing JSON schema1.
