# Jog and G54 validation quickstart

Use the pinned CPython3.13 environment from the repository root; no real port is required.

Run pure protocol/simulator/adapter tests, then controller/zero/stop behavior:

```powershell
python -m pytest tests/test_machine_manual_protocol.py tests/test_machine_manual_fake.py tests/test_machine_serial.py -q
python -m pytest tests/test_machine_manual_controller.py tests/test_machine_work_zero.py tests/test_machine_manual_stop.py -q
```

Run the Qt worker/control tests and the existing machine UI/shutdown regressions with an
offscreen backend. Tests inject FakeGRBL; no device port is opened. Check ten simulated cycles,
intent priority, GUI ownership and exact command transcripts through the tests:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python -m pytest tests/test_machine_manual_worker.py tests/test_machine_manual_ui.py tests/test_machine_ui.py tests/test_machine_shutdown.py -q
python -m pytest tests/architecture -q
python -m pytest -q
```

For the actual desktop smoke, remove the offscreen override and use the project's Python
environment on a Windows desktop. The smoke uses simulated machine injection; preserve its
real CAM/project round-trip/laser export/render flows and normal application cleanup:

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
python tests/smoke_app.py
```

Record actual results, revisions and limitations in [validation.md](validation.md); these
commands are instructions, not evidence that a run passed. Require final-head Windows CI.
Operator controls and caveats: [MACHINE_CONTROL.md](../../docs/MACHINE_CONTROL.md).

Never point an automated test at a physical device. For eventual real use, explicit port open
can reset a controller and execute stored startup blocks. Manual actions require two verified
empty startup blocks; the application never erases them. G54 zero is persistent and selected
axes must be verified. Cancel needs a fresh causal Idle report; Door may execute configured
parking and cannot verify cancellation. Missing Idle leads to failure/abort after the bounded
deadline, never a successful stop claim. Reset can lose position, and safety-door fallback may
execute configured parking. A broken link cannot confirm a physical stop: use machine E-stop.
No homing, unlock, resume, output-start or arbitrary G-code is provided by this slice.
