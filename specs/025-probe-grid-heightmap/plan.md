# Plan: probe grid and height map

CPython3.13, PyQt6 UI, stdlib core/machine, existing single-owner serial/Fake boundary. No new
dependency. Extend existing controller observations and ownership, do not add a serial reader.

## Constitution Check (pre/post design)
1. YES — immutable core models/codec, machine protocol/coordinator, bridge file I/O, thin UI.
2. YES — only short existing machine-panel composition; no added legacy feature logic.
3. YES — concrete probe coordinator and SerialIO/Fake implementations; no generic abstraction.
4. YES — mm and G54 authority, schema1 map; future026 queries this same coordinate frame.
5. YES — tests precede each core/protocol/coordinator implementation and run without hardware.
6. YES — spec hazard analysis, priority abort, incomplete/uncertain states and Fake fault matrix.
7. YES — independent implementation from GRBL documented protocol; no external source copy.
8. YES — three stories,39tasks. All gates remain YES after design.

## Structure
core/probe_map.py: Grid/Plan/Map records and deterministic row-major positions.
core/probe_codec.py: bounded strict versioned serialization.
machine/probe_models.py and probe_protocol.py: typed request/observation, narrow wire grammar,
probe report parsing and absolute-mm moves. machine/probe_control.py: one transaction owner,
preparation, each move/result/Idle confirmation and final retract. Split concrete preparation
helper if required to keep600/80 limits. machine/fake_probe.py: deterministic plane and fault seam.
bridge/probe_files.py: atomic save/bounded load. ui/probe_controls.py and probe_view.py: review,
explicit start/stop, file controls, table/heat visualization, standalone dialog from machine panel.
Short integration in controller/models/manual+console admission, worker, panel, Fake and SerialIO.

Limits: axes2..64/total1024; finite abs coordinates<=1e6mm; feeds.01..10000mm/min; probe travel
<=100mm; deadline3..300s; JSON<=1MiB. Grid strict increasing; map heights row-major optional;
only complete outcome requires every point. Strict JSON rejects duplicate/unknown keys and NaN.
Protocol carries at most one ordinary command and fresh status watermark for every movement.

## Validation
Analytic plane and exact coordinates, schema corruption/limits, per-write admission, preparation
and ACK/result ordering, all failure modes, save/load atomicity/no transport, Qt queued worker
and old behavior, actual desktop plus final-head Windows CI. Physical probing remains unverified.

## Complexity Tracking
No exception. Concrete coordinator uses existing preparation record parsers and status evidence.
