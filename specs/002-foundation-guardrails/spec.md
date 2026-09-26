# Feature Specification: Foundation guardrails

**Feature Branch**: `002-foundation-guardrails`
**Created**: 2026-09-26
**Status**: Specified
**Input**: Roadmap slice 2: enforce the constitution before adding product features.

## User Scenarios & Testing

### User Story 1 - Keep new work independent (Priority: P1)

As a contributor, I want forbidden dependencies detected before merge so that core CAM
work remains usable without the desktop host or hardware.

**Why this priority**: Every subsequent feature depends on a reliable architectural boundary.
**Independent Test**: Check allowed and forbidden dependencies in small temporary examples.
**Acceptance Scenarios**:
1. Given a permitted inward dependency, when checked, then it passes.
2. Given a forbidden host, display, outward or cross-domain dependency, when checked,
   then the report identifies its source location and target.
3. Given indirect or relative dependency notation, when checked, then equivalent boundaries apply.

### User Story 2 - Limit legacy growth (Priority: P1)

As a maintainer, I want each feature's combined growth in the largest legacy modules
measured against its starting revision so upstream updates remain manageable.

**Why this priority**: A lifetime allowance would punish unrelated future features.
**Independent Test**: Evaluate examples at +50, +51, with deletions, and with a missing base.
**Acceptance Scenarios**:
1. Given combined net growth of 50 lines, when checked, then it passes; 51 fails.
2. Given deletions and additions in tracked modules, when checked, then their signed sum is used.
3. Given unavailable baseline history, when checked, then it fails with recovery guidance.

### User Story 3 - Repeat checks on every change (Priority: P2)

As a contributor, I want an automated clean Windows validation run for proposed changes,
using the supported runtime, without a physical display or machine.

**Why this priority**: Locally passing checks must be independently reproducible.
**Independent Test**: Open this feature's pull request and inspect its completed validation run.
**Acceptance Scenarios**:
1. Given a new change, when automated validation runs, then dependencies are checked and the
   full test suite, dependency boundaries and growth budget are checked.
2. Given a failed check, when the run finishes, then its failure and test report are available.

### Edge Cases

- Relative imports through package initializers, import aliases and literal dynamic imports.
- Unresolvable dynamic dependencies must fail visibly rather than evade the boundary rule.
- Deleted tracked files count as reductions; renamed files must not evade the tracked budget.
- Missing history, invalid baseline records and fork pull requests need explicit handling.
- Core import must work in an isolated process without loading display or legacy modules.

## Requirements

### Functional Requirements

- **FR-001**: Establish the minimal new-code package and core location without speculative features.
- **FR-002**: Enforce constitutional dependency direction, core external-library restrictions,
  display separation, cross-domain isolation and host access only through the bridge.
- **FR-003**: Report violations with file, line and dependency; reject unresolved dynamic imports.
- **FR-004**: Record the ten largest tracked legacy application modules, their revision and line counts.
- **FR-005**: Enforce combined net growth of at most 50 lines per feature relative to its base;
  missing history or malformed records must fail, not disable the check.
- **FR-006**: Declare the supported runtime range from the roadmap and retain the existing pinned setup.
- **FR-007**: Run the complete existing suite and guardrails automatically for pull requests and main changes.
- **FR-008**: Document local reproduction, baseline selection and the constitutional exception process.

### Key Entities

- Dependency violation: source location, target and violated boundary.
- Legacy baseline: versioned list of tracked modules, recorded revision and original line counts.
- Feature growth: selected base revision, current file counts and combined signed delta.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All allowed/forbidden boundary examples are classified correctly with actionable diagnostics.
- **SC-002**: The growth check accepts 50 and rejects 51 added net lines, including deletion/rename examples.
- **SC-003**: A clean hosted validation run completes successfully with the full suite and both guardrails.
- **SC-004**: Contributors can reproduce the same checks using the documented commands.

## Assumptions

- Slice 001 is merged. This slice adds developer protections and changes no CAM or GUI behavior.
- The constitution defines dependency policy; its allowed libraries remain unchanged.
- Standard runtime tooling and existing test dependencies suffice; no new dependency is introduced.
- Exceptions above the legacy allowance require explicit plan justification and review; the guard
  deliberately remains failing until that reviewed exception is implemented.
