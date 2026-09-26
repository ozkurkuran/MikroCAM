# Validation: Interlace and multiple passes
## Pre-implementation analysis
Three stories/twelve tasks, all eight constitution gates pass. FR-001/002/006 and SC-001
map to T002–T004; FR-003/004/006 and SC-002 to T005–T007; FR-005 to T008/T009;
SC-003 and FR-007 to T010/T011. No new dependency, persistent schema, legacy logic or
manufacturing behavior. Existing worker cancellation states are reused. Execution pending.

## Implementation evidence
Interlace/pass tests first failed on the absent API; 28 cases now cover N=1/2/3, negative and
sparse row indices, clipped segments, cross families, cancellation, one placement and shared
immutable pass geometry. Recipe/panel tests first failed on missing editor/controls; 39 UI
cases pass. Atomic-save write/fsync/replace failures preserve old bytes and clean temp files.

Full integration: **995 tests and 310 subtests pass** in 60.99s, with two original placeholders
skipped and three inherited SWIG warnings. Architecture/growth checks pass; no legacy edit,
new dependency or format change. Modules remain under 600 lines/functions under 80 (UI326/24,
editor137/25; core/domain largest144/27). New pass numeric fields start blank and current draft
validation never falls back to an older recipe.

Real desktop smoke passed all existing CAM/project/render/shutdown stages, generated/replaced
110 paths with interlace N=3 and two distinct recipe passes, and verified both pass settings
and shared path identity. Screenshot inspected; controls remain scrollable in the small host
window. Source copper and selection are preserved. Hosted validation remains the delivery gate.
