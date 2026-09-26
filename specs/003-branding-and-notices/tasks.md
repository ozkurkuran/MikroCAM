# Tasks: Branding and notices

## Setup and foundation
- [ ] T001 Complete research and constitution checks in specs/003-branding-and-notices/research.md and plan.md.
- [ ] T002 Validate spec/plan/task coverage in specs/003-branding-and-notices/validation.md.

## US1: Consistent product identity
Independent test: identity helpers and actual title/About on desktop.
- [ ] T003 [US1] Write product identity/presentation tests first in tests/test_product_identity.py.
- [ ] T004 [US1] Define immutable product data in mikrocam/core/identity.py.
- [ ] T005 [US1] Add thin presentation helpers in mikrocam/ui/identity.py and wire appGUI/MainGUI.py, appGUI/GUIElements.py and appHandlers/appUIActions.py.
- [ ] T006 [US1] Point pyproject.toml dynamic version to the identity definition; adapt tests/architecture/test_runtime_metadata.py.

## US2: Complete source/dependency notices
Independent test: pin coverage, path safety and hashes without optional packages installed.
- [ ] T007 [P] [US2] Write inventory completeness/integrity tests first in tests/test_dependency_notices.py.
- [ ] T008 [US2] Gather exact-version license texts and bundled notices in THIRD_PARTY_LICENSES/ with schema_version 1 inventory.json.
- [ ] T009 [US2] Preserve upstream MIT holders in LICENSE; add NOTICE.md and update THIRD_PARTY_LICENSES/README.md and THIRD_PARTY_CHANGES.md.

## US3: Compatibility and update boundaries
Independent test: no updater/network calls through product entry points, same legacy storage/project versions.
- [ ] T010 [P] [US3] Write update/compatibility regressions first in tests/test_product_update_boundary.py.
- [ ] T011 [US3] Add product update-unavailable behavior in mikrocam/ui/identity.py and thin appMain.py/UI control wiring.
- [ ] T012 [US3] Extend tests/smoke_app.py to assert title/About and preserved project compatibility; save About screenshot.

## Polish and delivery
- [ ] T013 Update README.md with MikroCAM identity, notices and update behavior.
- [ ] T014 Run full tests, import/growth guards and pip check; record results in specs/003-branding-and-notices/validation.md.
- [ ] T015 Run desktop smoke and visually inspect screenshots; record evidence in specs/003-branding-and-notices/validation.md.
- [ ] T016 Review actual hosted CI for the feature PR and source/notice changes; update specs/003-branding-and-notices/validation.md.
- [ ] T017 Mark verified completion in docs/ROADMAP.md and deliver the feature PR.

## Dependencies and parallel work
T001–T002 gate implementation. Tests precede corresponding code. US2 can run independently
of US1/US3. US3 T010 may run with US1 tests, but T011 shares identity.py and must follow T005.
T006 depends on T004; T012 follows US1/US3 wiring. T013–T017 integrate all stories. MVP is US1,
but this feature is delivered with all three stories complete.
