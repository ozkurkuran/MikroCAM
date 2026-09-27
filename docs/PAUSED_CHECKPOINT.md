# Roadmap checkpoint — paused by user

The user explicitly requested on2026-09-27: stop for now, save and push. Do not resume roadmap
implementation until the user asks to continue.

## Delivered

Roadmap001–024 software slices are recorded in ROADMAP.md, including the selected Evo Beta_1.0
base and preparation. Most recent delivery: manufacturing import PR25, merged as
26637e0bd9b3a746a7ad36acdd4421c92d4b6d58, Windows CI36300977639 passed7m31s.
Main delivery checkpoint is4cf03738. Existing physical/vendor validation limitations remain open.

## Saved work in progress:025 probe grid and height map

Branch025-probe-grid-heightmap, worktree E:/VSCode/Flatcam/MikroCAM-probe.
Runtime implementation committed as bedd649deb6d9fa03d5cc61c1a13e732030ca2a3.
Full spec/plan/tasks/contracts/checklist, implementation, tests, usage and validation notes are
committed. Features include bounded immutable maps/atomic JSON, one-owner GRBL acquisition,
Fake plane/faults, probe UI and offline viewer, and desktop helper.

Evidence completed before pausing:221 focused tests passed in16.60s; an earlier combined probe
and existing machine run passed799tests in27.21s. Independent audit fixes were tested first.
Core/codec/files plus architecture/growth earlier passed194tests. Offscreen helper passes; this
does not establish actual desktop success or physical hardware verification.

Full suite at the runtime head was started and then explicitly stopped for the user's pause.
There is no final full-suite result. Actual full desktop, screenshot review, final-head Windows
CI, PR and merge for025 remain pending. Do not mark025 delivered or claim these checks passed.
Continue from tasks.md and validation.md when requested; update completed task boxes against
the saved implementation rather than repeating implementation work.

## Next slice not implemented

An empty026-autolevel-z-compensation branch/worktree was created at the025 runtime commit in
E:/VSCode/Flatcam/MikroCAM-autolevel. No026 spec, implementation or unique commit exists yet.
Only initial read-only investigation began; no026 delivery is claimed. Finish025 verification
and delivery before implementing026, then follow ROADMAP.md in sequence.

## Environment and retained limits

Shared Python: E:/VSCode/Flatcam/MikroCAM/.venv/repro-a/Scripts/python.exe (CPython3.13).
Commands must use their explicit feature workdir. Frozen Evo/8.994 references remain untouched.
Original research source document and physical/vendor checks remain recorded in PREPARATION.md
and feature validations. Local .venv logs/screenshots are ignored, not published artifacts.
All agents and owned background tests were stopped when this checkpoint was saved.
