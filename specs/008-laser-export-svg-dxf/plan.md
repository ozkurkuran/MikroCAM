# Implementation Plan: SVG/DXF pass export
**Branch**: `008-laser-export-svg-dxf` | **Date**: 2026-09-27

## Summary and technical context
Pure core serializers emit narrow geometry-only SVG and ASCII DXF R2000 LWPOLYLINE files
from already-placed LaserPath tuples. Core uses stdlib only for encoding. Laser domain writes
a ZIP with per-pass files, recipe, manifest and instructions to a same-directory temporary
file, then atomically replaces the selected destination. Existing pinned ezdxf is an independent
test reader, not a forbidden core dependency. PyQt export worker/controls integrate the panel.

Resource limits: at most 1,000 passes (1,003 archive entries), 2,000,000 total emitted paths, 10,000,000 total vertices and 512 MiB
uncompressed geometry bytes across all passes; fail explicitly, never truncate. Files are
serialized/written per pass rather than materializing all pass copies. Cancellation checks
between paths and archive entries; atomic replace is the completion boundary.

## Constitution Check
| Gate | Result | Evidence |
| --- | --- | --- |
| I layers | Yes | Core serializers stdlib, laser file orchestration stdlib/core, Qt UI worker. |
| II legacy | Yes | Existing dock hook reused, no legacy edit. |
| III/VII dependencies | Yes | No new dependency; small narrow format writers, no general framework. |
| IV single source | Yes | Existing placed mm paths/recipe; manifest schema1 with no prior migration. |
| V tests first | Yes | Serializer/package tests before code; independent parser readback. |
| VI hazards/stop | Yes | No motion/emission; transfer risks and cancellation states in spec. |
| VII provenance | Yes | Independent implementation using official format docs; no external code port. |
| size | Yes | Three stories, fourteen tasks. |

## Structure / complexity
`core/laser_svg.py`, `core/laser_dxf.py`: narrow serializers;
`core/laser_manifest.py`: manifest schema validation/codec;
`laser/export.py`: package assembly/atomic write and import README;
`ui/laser_export.py`: concrete export worker/widget;
existing `ui/laser_cam.py` integrates busy/invalidation/close state.
Tests: `test_laser_export_formats.py`, `test_laser_export.py`, `test_laser_export_ui.py` and
desktop smoke extension. Modules <=600/functions <=80, no abstract export plugin/backend.
