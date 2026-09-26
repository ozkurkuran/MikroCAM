# Implementation Plan: Interlace and multiple passes
**Branch**: `007-hatch-interlace-multipass` | **Date**: 2026-09-27

Extend PlanOptions with interlace_n=1. A domain ordering function groups existing paths
without generating coordinates or iterating empty residue groups. LaserPlan.pass_plans
exposes frozen LaserPassPlan values sharing its immutable path tuple. A focused recipe editor
widget collects explicit text fields and uses the existing core models/codecs. Atomic recipe
file replacement uses a same-directory temporary file; no new serialization schema.

## Technical Context
CPython 3.13, stdlib and existing Qt. No new dependency, legacy edit or source port. Three
stories, twelve tasks. Domain sorting costs O(paths log paths), with cancellation checks
while collecting/sorting keys and after sort; no allocation proportional to N or pass*paths.
Native sort is a bounded non-interruptible step under existing 200,000-path limit.

## Constitution Check
| Gate | Result | Evidence |
| --- | --- | --- |
| I layers | Yes | Plain values core, ordering laser, recipe controls UI. |
| II legacy/+50 | Yes | Existing dock hook reused; no legacy changes. |
| III/VII simplicity/dependencies | Yes | One function and concrete widget; existing deps only. |
| IV single source | Yes | Existing mm/Placement/recipe JSON1; ephemeral interlace option. |
| V tests first | Yes | Ordering/models first, UI smoke and atomic-write failure coverage. |
| VI hazards/stop | Yes | Geometry only; validation/invalidation/cancellation in spec. |
| VII provenance | Yes | Independent implementation; no imported external code. |
| size | Yes | Three stories, twelve tasks. |

## Structure and complexity
`core/laser_paths.py` extends existing values; `laser/interlace.py` orders paths;
`laser/planner.py` integrates order. `ui/laser_recipe.py` owns editor and atomic recipe save;
`ui/laser_cam.py` integrates editor, N and status. Focused tests plus existing desktop smoke.
Every module <=600 and function <=80 lines. No abstractions, new settings or format exceptions.
