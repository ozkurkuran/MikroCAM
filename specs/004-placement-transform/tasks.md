# Tasks: Placement transform

## Setup and foundation
- [X] T001 Complete spec/plan consistency review in specs/004-placement-transform/validation.md.
- [X] T002 Record analytic placement examples in tests/reference/placement.json.

## US1: Shared point placement
Independent check: reference point examples and validation failures.
- [X] T003 [US1] Write reference/composition/validation tests first in tests/test_placement.py.
- [X] T004 [US1] Implement immutable Placement and shared coefficients in mikrocam/core/placement.py.
- [X] T005 [US1] Implement apply_point/apply_points and inverse in mikrocam/core/placement.py.

## US2: Consistent whole geometry
Independent check: vertex agreement, holes, multipart/empty, inverse, invalid/Z geometry.
- [X] T006 [US2] Add geometry/reference and randomized round-trip tests in tests/test_placement.py before geometry code.
- [X] T007 [US2] Implement validated apply_geometry in mikrocam/core/placement.py.

## Polish and delivery
- [X] T008 Run full suite/architecture/growth checks and record evidence in specs/004-placement-transform/validation.md.
- [ ] T009 Review hosted feature CI and final code sizes in specs/004-placement-transform/validation.md.
- [ ] T010 Update docs/ROADMAP.md and deliver the feature PR after preceding slices.

## Dependencies and parallel work
T001–T002 precede tests. T003 precedes T004–T005; T006 precedes T007 and uses the US1 API.
All code shares one module, so edits are sequential. T008–T010 follow both stories. This core
slice depends on 002 and can be prepared independently of branding, but delivery follows 003.
