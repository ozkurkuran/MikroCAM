# Validation: Foundation guardrails

## Pre-implementation analysis

All 16 specification checklist items pass. No extension hooks are configured.
FR-001/002/003 map to US1 T003–T006; FR-004/005 to US2 T007–T009;
FR-006/007 to US3 T010–T011; FR-008 to T012. SC-001/002 have synthetic boundary
tests, SC-003 requires hosted CI and SC-004 is checked through the documented commands.
Three stories and fourteen tasks fit the constitution. No unresolved contradiction or
clarification. No external interfaces, runtime dependencies or source ports.

Implementation and hosted results will be recorded after execution.

## Initial execution and hosted diagnosis

- Clean local core environment: 585 passed, 2 unchanged upstream placeholders skipped,
  310 subtests passed in 72.18s; pip check clean. Follow-up boundary tests: 46 passed;
  growth tests: 28 passed including staged moves, rename-then-large-edit and a two-parent merge.
- Initial hosted run [36270084038](https://github.com/ozkurkuran/MikroCAM/actions/runs/36270084038)
  installed the exact pins successfully. 592 passed, 2 failed, 2 skipped, 310 subtests passed.
  Both failures were existing updater tests comparing short and long Windows paths as text:
  `C:/Users/RUNNER~1/...` versus `C:/Users/runneradmin/...`. The assertions now use samefile
  to verify the intended file identity; runtime updater behavior is unchanged.
- The hosted JUnit artifact uploaded successfully. Review suggestions about a missing JUnit
  parent directory and nonrecursive ls-tree were checked against execution: pytest creates
  the parent, and `git ls-tree -rz` already includes the recursive `-r` flag. No workaround needed.
- Current tracked legacy growth: +0/50 from c388cf4ae58da28049493b47375bb6cdf1e7401f.
