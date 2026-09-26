# Validation: Foundation guardrails

## Pre-implementation analysis

All 16 specification checklist items pass. No extension hooks are configured.
FR-001/002/003 map to US1 T003–T006; FR-004/005 to US2 T007–T009;
FR-006/007 to US3 T010–T011; FR-008 to T012. SC-001/002 have synthetic boundary
tests, SC-003 requires hosted CI and SC-004 is checked through the documented commands.
Three stories and fourteen tasks fit the constitution. No unresolved contradiction or
clarification. No external interfaces, runtime dependencies or source ports.

All fourteen tasks are complete; [feature PR](https://github.com/ozkurkuran/MikroCAM/pull/2).

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

## Final hosted result

[Windows run 36270502616](https://github.com/ozkurkuran/MikroCAM/actions/runs/36270502616),
revision 86d6fe8d, completed successfully: **594 passed, 2 skipped, 310 subtests passed**
in 46.12s, with the same three upstream SWIG deprecation warnings. `pip check` was clean.
Both skips remain the original empty Qt-context placeholders, not new guard exclusions.
The run checked out full history, selected the PR base, installed CPython 3.13.13 x64 and
the pinned development environment, ran all tests and retained the JUnit artifact.

The guard suite includes 46 dependency-boundary cases, 28 growth cases and 9 runtime metadata
cases. New modules are below 600 lines and functions below 80. No application source file
changed, no runtime dependency was added and GUI smoke is not applicable to this slice.
No external code port was performed. Branch work is independently authored developer tooling.
