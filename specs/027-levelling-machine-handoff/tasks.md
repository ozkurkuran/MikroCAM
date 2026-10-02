# Tasks: Levelling to Machine handoff

## Setup
- [x] T001 Verify base Phase A and create spec/design in specs/027-levelling-machine-handoff/ (FR006/008).
## Foundational
- [x] T002 Research all serial paths and ownership in appPlugins/ToolLevelling.py and mikrocam/ui/machine_panel.py (FR002/003/004).
## US1 - Block legacy GRBL (MVP)
- [x] T003 [US1] Write failing no-open/no-wire/direct-callback tests in tests/test_levelling_machine_handoff.py (FR001/002/003).
- [x] T004 [US1] Add guard and card/visibility helper in mikrocam/ui/levelling_handoff.py (FR001/003).
- [x] T005 [US1] Hook guards/blocked connection/safe metadata into appPlugins/ToolLevelling.py, retaining legacy implementations (FR002/003/006).
- [x] T006 [US1] Target retained mock-only connection implementation in tests/test_levelling_grbl_wire.py and rerun A regressions (FR006/008).
## US2 - Explicit Machine handoff
- [x] T007 [US2] Test reused dock and no implicit connect in tests/test_levelling_machine_handoff.py before its button callback (FR004).
- [x] T008 [US2] Route button to existing dock in mikrocam/ui/levelling_handoff.py (FR004).
## US3 - Offline workflows
- [x] T009 [US3] Test all three offline choices/switching in tests/test_levelling_machine_handoff.py; run unchanged tests/test_levelling_tool.py and tests/test_levelling_journey.py (FR005).
## Polish
- [x] T010 Update docs/PROBING.md, docs/AUTOLEVEL.md and THIRD_PARTY_CHANGES.md (FR007).
- [x] T011 Add tests/smoke_levelling_handoff.py hook in tests/smoke_app.py; actual desktop screenshot inspection (FR001/004/008).
- [x] T012 Complete local suite/architecture and final-head Windows CI; record specs/027-levelling-machine-handoff/validation.md and open dependent PR (FR008).

Dependencies: T001-T002 → red tests T003/T007/T009 → T004-T006/T008 → T010-T012.
US1 is independently verifiable via no-port/no-wire tests. US2 verifies dock reuse alone;
US3 verifies offline controls/journeys independently. Test-writing for different stories can
be read/reviewed in parallel, but shared test/runtime files are edited sequentially.
Implementation is incremental; no new controller/device behavior or persistent entity.
