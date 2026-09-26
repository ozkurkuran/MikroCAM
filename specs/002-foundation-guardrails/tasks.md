# Tasks: Foundation guardrails

## Setup and foundation
- [X] T001 Review constitution and source inventory; document decisions in specs/002-foundation-guardrails/research.md.
- [X] T002 Complete specification/plan consistency review in specs/002-foundation-guardrails/validation.md.

## US1: Independent new code
Independent check: synthetic allowed/forbidden imports and an isolated core import.
- [X] T003 [US1] Write boundary regression cases first in tests/architecture/test_import_boundaries.py.
- [X] T004 [US1] Create minimal mikrocam/__init__.py and mikrocam/core/__init__.py.
- [X] T005 [US1] Implement AST dependency diagnostics in tests/architecture/imports.py.
- [X] T006 [US1] Validate the real package and isolated import in tests/architecture/test_import_boundaries.py.

## US2: Per-feature legacy budget
Independent check: temporary repositories exercise 50/51, deletion, rename and missing base.
- [X] T007 [P] [US2] Write growth cases first in tests/architecture/test_legacy_growth.py.
- [X] T008 [US2] Record top ten legacy module counts in tests/architecture/legacy-baseline.json with schema_version 1 and budget 50.
- [X] T009 [US2] Implement baseline validation and feature deltas in tests/architecture/growth.py.

## US3: Reproducible hosted checks
Independent check: supported runtime metadata and a successful hosted PR run.
- [X] T010 [P] [US3] Write runtime declaration checks in tests/architecture/test_runtime_metadata.py.
- [X] T011 [US3] Add pyproject.toml and Windows headless checks in .github/workflows/ci.yml.

## Polish and delivery
- [X] T012 Document baseline selection and local checks in docs/DEVELOPMENT.md.
- [X] T013 Run complete suite and pip check, review hosted CI, record actual evidence in specs/002-foundation-guardrails/validation.md.
- [X] T014 Update docs/ROADMAP.md with verified completion and deliver the feature PR.

## Dependencies and parallel execution

T001–T002 precede implementation. US1 tests precede its code. US2 and US3 may run in parallel
with US1 after T002, each writing only its listed files. T007 precedes T008–T009;
T010 precedes T011. T012–T014 follow all three stories. MVP is US1; delivery includes all stories.
No external interface contract is needed: this slice only adds internal developer checks.
