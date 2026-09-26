# Implementation Plan: Laser job model

**Branch**: `005-laserjob-model` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary

Frozen core dataclasses hold explicit laser values and a planar polygon region encoded as
canonical WKB hex (plain string data). Strict JSON codecs preserve recipe/job schema 1.
A thin Gerber bridge collects polygon solids, normalizes declared MM/IN units and snapshots
them into core. Job preview uses Placement.apply_geometry once.

## Technical Context

- CPython 3.13 x64; existing Shapely, stdlib dataclasses/json/math. No new dependencies.
- Data: core laser_job.py values; laser_json.py strict codecs; bridge/gerber.py host adaptation.
- Persistence: recipe/job JSON schema 1; existing project/CNC formats untouched.
- Tests: pure data/codec examples, malicious/malformed parameter records, real Gerber fixture
  plus small detached fake host objects for units/nesting/topology. No manufacturing hardware.
- Scope: 3 stories, 14 tasks; no UI or generated laser paths. Input geometry must be planar
  nonempty valid polygons; no automatic repair or guessed conversion of strokes into copper.
- Limits: no device-specific capability bounds; supplied values are model data, not certified
  device settings. Serializers reject non-finite JSON and ambiguous duplicate keys.

## Constitution Check

Pre/post-design gates:

| Gate | Result | Evidence |
| --- | --- | --- |
| I: layered new code | Yes | Models/codecs in core, only bridge references Gerber host. |
| II: legacy minimal/+50 | Yes | No legacy edits. |
| III/VII: justified simplicity/dependencies | Yes | Plain frozen dataclasses and functions; existing Shapely. |
| IV: one unit/placement/parameters/versioned format | Yes | mm, existing Placement, explicit passes, JSON schema 1; no prior schema needs migration. |
| V: test first/no hardware/display | Yes | Model/codec/bridge tests precede code and require no Qt context. |
| VI: hazards for motion/emission | Yes | Data-only, no emission/transport commands. |
| VII: provenance/clean room | Yes | Independently implemented, no fork source imported. |
| <=3 stories/<=40 tasks | Yes | Three stories, fourteen tasks. |

## Project Structure

```text
mikrocam/core/laser_job.py, mikrocam/core/laser_json.py
mikrocam/bridge/__init__.py, mikrocam/bridge/gerber.py
tests/test_laser_job.py, tests/test_laser_json.py, tests/test_gerber_bridge.py
tests/reference/laser_recipe_v1.json
specs/005-laserjob-model/{spec,plan,research,data-model,quickstart,tasks,validation}.md
specs/005-laserjob-model/contracts/laser-json.md
```

## Complexity Tracking
No exceptions. Keep modules <=600 and functions <=80 lines; split data and serialization
because they have separate responsibilities and independent test suites.
