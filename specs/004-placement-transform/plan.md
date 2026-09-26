# Implementation Plan: Placement transform

**Branch**: `004-placement-transform` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

## Summary

Implement a frozen `Placement` dataclass in core. Derive Shapely-compatible six affine
coefficients once; all point/geometry operations use those coefficients. Inverse maps retain
the same dataclass representation instead of adding an unrelated matrix type.

## Technical Context

- Language/platform: CPython 3.13 x64, Windows primary; platform-independent core math.
- Dependencies: stdlib math/dataclasses/numbers plus already pinned Shapely 2.1.2. No new dependency.
- Storage: none; plain immutable values, no new persistent file format.
- Tests: pytest analytic examples, deterministic randomized round-trips, geometry fixtures.
- Performance: linear in point/vertex count using Shapely affine transforms; no speculative optimization.
- Scope: two stories, ten tasks, one new runtime module; no GUI/legacy edits or hardware.

## Constitution Check

Pre-design and post-design checks all pass:

| Gate | Result | Evidence |
| --- | --- | --- |
| I: correct core boundary | Yes | Only stdlib/Shapely; no UI/host imports. |
| II: legacy limited, <=50 | Yes | Zero legacy edits. |
| III/VII: justified abstractions/dependencies | Yes | One concrete value dataclass needed by preview and laser; existing Shapely. |
| IV: one unit/transform/parameter source | Yes | Millimetres throughout, one coefficient source; no file format. |
| V: headless/hardware-free/test first | Yes | Tests precede implementation and require no Qt context. |
| VI: hazard analysis if motion/emission | Yes | Pure geometry only, no control behavior. |
| VII: provenance/clean room | Yes | Independent implementation from mathematical definitions. |
| <=3 stories/<=40 tasks | Yes | Two stories, ten tasks. |

## Project Structure

```text
mikrocam/core/placement.py
tests/test_placement.py
tests/reference/placement.json
specs/004-placement-transform/{spec,plan,research,data-model,quickstart,tasks,validation}.md
specs/004-placement-transform/contracts/placement.md
docs/ROADMAP.md
```

## Complexity Tracking

No exceptions. Module <=600 lines, each function <=80, public APIs type hinted.
