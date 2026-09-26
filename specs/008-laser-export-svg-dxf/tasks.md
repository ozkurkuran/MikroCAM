# Tasks: SVG/DXF pass export
## Foundation
- [X] T001 Review official formats and artifact consistency in research.md/validation.md.
## US1: Geometry transfer
- [X] T002 [US1] Write analytic SVG/DXF readback tests first in tests/test_laser_export_formats.py.
- [X] T003 [US1] Implement core/laser_svg.py using already-placed paths and shared frame.
- [X] T004 [US1] Implement core/laser_dxf.py and verify independently with installed ezdxf.
## US2: Complete handoff
- [X] T005 [US2] Write strict manifest/package/settings/error tests in tests/test_laser_export.py first.
- [X] T006 [US2] Implement core/laser_manifest.py schema-1 codec.
- [X] T007 [US2] Implement laser/export.py per-pass ZIP, README, limits and atomic cancellation.
## US3: Desktop export
- [X] T008 [P] [US3] Write lifecycle/format/stale-plan tests in tests/test_laser_export_ui.py.
- [X] T009 [US3] Implement ui/laser_export.py worker/controls.
- [X] T010 [US3] Integrate export controls, busy/cancel/shutdown into ui/laser_cam.py.
- [X] T011 [US3] Extend tests/smoke_app.py to export/read both formats from two-pass plan.
## Delivery
- [ ] T012 Run full regression/architecture/growth/size checks and hosted CI; record validation.md.
- [X] T013 Document target-app/physical verification evidence and remaining external checks honestly.
- [ ] T014 Update docs/ROADMAP.md/quickstart.md and deliver PR after 007.

T001 gates code; T002 before T003/T004; T005 before T006/T007; T008 before T009/T010.
UI can be prepared separately against contract; integration and smoke wait for core/domain.
No new dependency, legacy modification, external code port or hidden recipe fallback.
