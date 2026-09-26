# Tasks: Laser job model

## Setup and foundation
- [X] T001 Complete Gerber representation research in specs/005-laserjob-model/research.md.
- [X] T002 Validate artifact/constitution coverage in specs/005-laserjob-model/validation.md.

## US1: Explicit recipes
Independent check: two-pass recipe value/JSON round-trip and invalid/missing parameter cases.
- [X] T003 [US1] Write recipe/pass tests first in tests/test_laser_job.py and tests/test_laser_json.py.
- [X] T004 [US1] Implement validated immutable LaserPass/LaserRecipe in mikrocam/core/laser_job.py.
- [X] T005 [US1] Implement strict recipe JSON in mikrocam/core/laser_json.py and tests/reference/laser_recipe_v1.json.

## US2: Detached laser jobs
Independent check: source/placed geometry and complete job JSON retain topology and values.
- [X] T006 [US2] Add planar region/job/migration rejection tests in tests/test_laser_job.py and tests/test_laser_json.py before implementation.
- [X] T007 [US2] Implement PlanarRegion/LaserJob with the shared Placement in mikrocam/core/laser_job.py.
- [X] T008 [US2] Implement strict job JSON in mikrocam/core/laser_json.py.

## US3: Gerber bridge
Independent check: equivalent inch/mm geometry, nested shapes, holes, immutable snapshot and a real Gerber fixture.
- [X] T009 [P] [US3] Write bridge tests first in tests/test_gerber_bridge.py.
- [X] T010 [US3] Add the required core polygon-union/unit-boundary helper in mikrocam/core/laser_job.py with regression coverage in tests/test_laser_job.py.
- [X] T011 [US3] Implement thin Gerber adapter in mikrocam/bridge/gerber.py and its package initializer.

## Polish and delivery
- [X] T012 Run full suite/architecture/growth checks in specs/005-laserjob-model/validation.md.
- [X] T013 Review hosted CI and code sizes in specs/005-laserjob-model/validation.md.
- [X] T014 Mark docs/ROADMAP.md completion and deliver the feature PR after prior slices.

## Dependencies and parallel work
T001–T002 gate code. T003 precedes T004–T005; T006 precedes T007–T008. US3 tests and
thin adapter may be prepared separately once the agreed core contract exists, but T011 needs
T010's core helper. Core module edits are owned by one implementer to avoid collisions.
T012–T014 follow all stories. JSON files remain separate from Evo projects.
