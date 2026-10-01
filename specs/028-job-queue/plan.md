# Implementation Plan: İş kuyruğu

Branch: 028-job-queue | Date: 2026-10-02 | Spec: [spec.md](spec.md)

## Summary
Ordered immutable prepared CNC snapshots are sealed on Add, edited offline and submitted
once after whole-queue mechanical confirmation. A domain coordinator reserves the sole
MachineController across jobs and reuses JobControl's full per-job preparation/completion.
Automatic advance is the disclosed implementation assumption under the new completion request.

## Technical Context
Language: pinned CPython 3.13. Dependencies: existing stdlib, PyQt6, pytest only.
Storage: session-only bounded queue of 32 entries; no persistent format or migrations.
Platform: Windows 11 desktop; no physical ports in agent tests. Performance: bounded owner
cycle and one active job, no busy wait; immutable observations delivered by existing QThread.
Scope: GRBL CNC, existing approved PreparedJob and serialized sender; C3 separate spec.

## Constitution Check
PASS before/after design: domain contains no Qt/legacy; UI only collects/renders; sole owner
and existing priority stop maintained; test tasks precede implementation; no new dependency,
protocol abstraction or legacy business code. Modules <600 lines/functions <80. Hazard analysis
is in spec. Original implementation; no outside code copying. Physical H3 remains open.

## Phase 0 Research
Research agent inspected controller/job/worker/preflight/Fake and existing tests. See
[research.md](research.md). No unresolved technical or scope clarifications remain; the user
completion request and explicit implementation assumption are recorded in spec.

## Project Structure
- mikrocam/machine/queue_models.py: frozen entry/request/result types and pure QueueDraft edits.
- mikrocam/machine/queue_control.py: concrete owner reservation, per-job state and advancement.
- mikrocam/machine/models.py: queue observation in MachineSnapshot.
- mikrocam/machine/controller.py: typed queue admission/tick/priority/session lifecycle hooks.
- mikrocam/ui/queue_controls.py: sealed snapshot list, move/remove/clear/start and rendering.
- mikrocam/ui/machine_worker.py and machine_panel.py: typed intent and panel hookup.
- tests/test_queue_models.py, test_queue_control.py, test_queue_worker.py, test_queue_ui.py:
  test-first models, owner boundaries/faults, worker priority and snapshot UI tests.
- tests/smoke_queue.py plus smoke_app.py: actual desktop completion/stop and screenshot.

## Design and Integration
Queue admission never releases ownership between jobs. Public manual/probe/console/single
Start are rejected while the queue runs; advertised capabilities agree. Internal JobControl
start is narrowly permitted for the queue owner without opening external admission.
All startup/settings/modal/G54/endpoint/outputs-off queries repeat per job. Contiguous reviewed
initial/final endpoints are required; no generated repositioning or re-analysis of snapshots.
Add detaches immutable PreparedJob from the single current UI binding. Editing the source does
not mutate an added snapshot; preparing another candidate does not invalidate earlier entries.
Stop/abort/disconnect/reset clears queue authorization. Fault results survive reconnect; pending
entries never auto-restart. Pause at an inter-job boundary holds queue advancement.

## Validation Strategy
Models and domain tests first red; use existing Clock/Fake and typed PreparedJob fixtures.
Cover two/three contiguous jobs; every final completion boundary; all C1 faults; competing
owner admission and reconnect/late-ACK; worker stop-before-admission and GUI snapshot sealing.
Run related tests, architecture, actual desktop smoke, full suite, final-head Windows CI.
Update docs/IS_TAKIP.md per stage; update PR #32 from draft only once ready.

## Complexity Tracking
No exception requested. Queue coordinator is concrete, not a generic scheduler. Existing
legacy remains untouched. C3 adds a separate source mode later, preserving queue contracts.
