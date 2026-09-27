# Jog and G54 validation quickstart

Use the pinned CPython3.13 environment from the repository root; no real port is required.

1. Run tests/test_machine_manual_protocol.py and tests/test_machine_manual_fake.py.
2. Run manual-controller/work-zero/stop tests with deterministic clocks and scripted FakeGRBL.
3. Run Qt manual UI and existing machine UI/shutdown tests; verify10cycles and exact transcript.
4. Run the full pytest suite and architecture/growth checks.
5. Run tests/smoke_app.py on a real Windows desktop with FakeGRBL injection. Keep real CAM,
   project round-trip/laser export/render checks and normal application cleanup.
6. Record actual evidence in validation.md and require final-head hosted Windows CI.

Never point an automated test at a physical device. For eventual real use, explicit port open
can reset a controller and execute stored startup blocks. Manual actions require two verified
empty startup blocks; the application never erases them. G54 zero is persistent and selected
axes must be verified. Cancel decelerates, reset can lose position, and safety-door fallback may
execute configured parking. A broken link cannot confirm a physical stop: use machine E-stop.
No homing, unlock, resume, output-start or arbitrary G-code is provided by this slice.
