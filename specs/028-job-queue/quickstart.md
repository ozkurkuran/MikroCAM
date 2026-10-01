# Queue validation quickstart

Use shared CPython 3.13, FakeGRBL and QT_QPA_PLATFORM=offscreen for pytest; no hardware.
Run: python -m pytest -q tests/test_queue_models.py tests/test_queue_control.py
Then run worker/UI tests, existing job/manual/probe/console groups and architecture checks.
Desktop: python tests/smoke_app.py; inspect queue screenshot and completion/stop markers.
Prepare three contiguous reviewed CNC jobs, seal/reorder snapshots, approve whole queue and
Start. Expect exactly one active job, verified completion per entry and ordered results.
Inject a middle-job alarm: expect no next-source writes, visible failure and no replay on
reconnect. Editing a source after Add must not change queued bytes.
Physical travel/output timing remain H3 operator evidence; no agent opens a serial port.
