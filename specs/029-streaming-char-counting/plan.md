# Implementation Plan: Karakter sayımlı GRBL gönderimi
Branch: 029-streaming-char-counting | 2026-10-02 | [spec](spec.md)

## Summary
Explicit bounded source-only FIFO on the existing JobControl/communication owner.
Default send-response stays unchanged. Readonly $I verifies GRBL 1.1 and min(reported RX,128)
before source. Preparation/final proof remain single transactions. Queue mode is immutable.

## Technical Context
Python 3.13, existing PyQt6/pytest dependencies only; Windows desktop; no persistence change.
FIFO memory bounded by 128 wire bytes; every handoff priority-checked. No physical performance claim.

## Constitution Check
Before/after design PASS: machine/core Qt-free, UI thin; no legacy logic or external source copied,
no dependency, no new communication owner; tests first; module/function size guards preserved.
Real transport and Fake are concrete usages of this protocol window. No generic abstraction.

## Project Structure
machine/job_stream.py: pure FIFO/capability parsing. job_control.py: source-only integration.
job_models.py/queue_models.py: explicit mode; queue_control.py: propagate mode per job.
fake_job.py: bounded pending RX/planner simulation; fake.py: readonly capability fixture.
ui/job_controls.py/queue_controls.py: explicit selector, disabled during admission/execution.
tests/test_job_stream.py, test_char_counting.py, test_char_counting_ui.py, smoke_queue.py.

## Sequence
Merge completed 028 dependency; pure FIFO tests then implementation; coordinator/Fake tests
then implementation; priority/fault/hold/final tests; UI tests then selection; full suite,
actual desktop, final-head Windows CI. Spec quality/analyze gate before runtime writes.

## Complexity Tracking
No exception; original protocol algorithms only. No firmware implementation copied.
