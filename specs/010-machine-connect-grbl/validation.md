# Validation: Read-only GRBL connection

Status: implementation and local validation complete; final-head hosted CI and merge pending.
No physical hardware was connected or validated.

## Pre-implementation analysis
Three independently testable stories / 28 tasks. No unresolved placeholder or new dependency.
Implemented domain remains Qt/pyserial-free; serial is a bridge leaf.
Read-only disconnect closes communications; it does not claim to stop externally initiated
motion. Constitution VI active-motion fail-safe obligations apply when active control is added.

| Requirements | Completed tasks / evidence |
| --- | --- |
| FR-001, FR-002 | T004, T007, T010-T012: explicit lifecycle and mocked physical serial |
| FR-003, FR-008 | T013-T017: strict parsing, unknown/invalid state and diagnostics |
| FR-004, FR-005 | T004, T008-T009, T012: exact TX, bounded framing/outstanding requests |
| FR-006, FR-007 | T013-T017: analytic units/offsets and evidence invalidation |
| FR-009, FR-010 | T018-T023: thin panel, one owner, repeated stop/join and stale sessions |
| FR-011, FR-012 | T012, T023-T026: bounded diagnostics, boundaries/full suite/desktop |
| SC-001 | T012, T022: all Fake writes subset of the two read requests |
| SC-002 | T017: analytic mm/inch positions within 1e-9 mm |
| SC-003 | T012, T022: deterministic stale deadline and real worker close timing |
| SC-004 | T022-T023: ten sessions and desktop CAM smoke |
| SC-005 | T025 local full suite passes; T027 hosted Windows CI remains pending |

T026 reviewed all 12 functional requirements, five success criteria and all eight gates.
The following implementation checks passed; coverage review does not claim pending CI passed:
1. Layer direction and hardware-free domain.
2. Legacy menu/shutdown hooks: appMain.py +6 and appHandlers/appLifecycle.py +5 = +11 combined; tracked top-ten legacy growth +6, within +50.
3. One transport Protocol with SerialIO and FakeGRBL; no new dependency, registry or framework.
4. One report-unit-to-mm boundary, session-scoped offsets; no persistence/placement duplication.
5. Tests before domain/adapter/UI behavior; fake clocks, mocked serial and isolated Qt simulation require no hardware, network or user settings.
6. Exact read allowlist, explicit states/units/staleness, owned stop/join and failed-cleanup retention; serial-open reset and disconnect limitations disclosed.
7. Independent protocol implementation; no application source port or FlatCAM Plus code; existing pyserial BSD-3 notice retained.
8. Three stories, 28 tasks; new modules <=600 lines and functions <=80 lines.

## Execution evidence
Read-only Luna review identified reset settings reacquisition and cancellation versus the
three-second settings timeout. The contract now explicitly resolves both with nonblocking
transaction state and a fresh read after a startup banner. All 16 spec checklist items passed;
check-prerequisites returned the complete feature context. No extension hooks are installed.
Tests preceded implementation. Focused machine validation totals **194 passed**:
`tests/test_machine_controller.py` 30, `tests/test_machine_fake.py` 12,
`tests/test_machine_grbl.py` 82, `tests/test_machine_serial.py` 53,
`tests/test_machine_ui.py` 16 and `tests/test_machine_shutdown.py` 1.
The pure subset is 177 and the Qt UI/shutdown subset is 17. Earlier combined
machine/architecture stage counts are not added to this total.

Controller/parser tests cover analytic mm/inch positions within 1e-9 mm, both directly
reported systems, current-session WCO, provisional settings until acknowledgement, reset
reacquisition, stale/late responses, invalid framing and unknown states. Serial/Fake tests
cover inert construction, metadata-only refresh, bounded I/O, exact `b'?'` / `b'$$\n'`
transmissions, short writes and close failures. UI tests cover ten owned sessions, GUI-thread
updates, late old-session snapshots, unknown/stale unavailable positions and stop/join bounds.
Host shutdown tests retain application/worker ownership when cleanup cannot complete.

Reproduce focused and full checks on Windows/CPython 3.13 with the project environment:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$machineTests = (Get-ChildItem tests/test_machine_*.py).FullName
python -m pytest @machineTests -q
python -m pytest tests/architecture -q
python -m pytest -q
```

The initial full run in `.venv/machine-pytest.log` recorded **1562 passed, 1 failed,
2 skipped, 310 subtests passed in 168.36 s**. Its failure,
`test_shutdown_timeout_keeps_live_worker_and_ignores_close`, could inspect a Qt worker
after completed-worker disposal. Test-only correction **db8a4b94** retained the lifecycle
assertion; all 17 UI/shutdown tests then passed.

The final full run at **db8a4b94** recorded **1563 passed, 2 skipped, 11 warnings,
310 subtests passed in 161.20 s** in `.venv/machine-final-pytest.log`.
This completes T025's local full-suite/import/growth/size/desktop checks.

Actual desktop smoke exercised runtime **8e3f6566**, including the fresh-status diagnostic
correction. The later db8a4b94 change is test-only. Use the real desktop backend:

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
python tests/smoke_app.py
```

`.venv/machine-smoke.log` records successful Gerber/Excellon, isolation/CNC, project
round-trip, laser preview/multipass/export and rendering flows, followed by
`MACHINE_READ_ONLY_OK`, `MACHINE_SHUTDOWN_OK` and `SHUTDOWN_OK`. The machine session uses
injected FakeGRBL, never a physical port. `.venv/machine-smoke.png` was visually inspected
by the delivery reviewer. Normal cleanup completed; Qt disconnect/QThreadStorage warnings
are not represented as a warning-free run. Local `.venv` logs/screenshots are ignored
development artifacts; these commands, counts and markers describe their evidence.

## Sources, limitations and delivery

Protocol/API decisions are traced in [research.md](research.md) to the
[GRBL 1.1 interface](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md),
[GRBL settings](https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md),
[pyserial API](https://pyserial.readthedocs.io/en/stable/pyserial_api.html) and
[serial-open/reset discussion](https://github.com/gnea/grbl/issues/731).
No new dependency or copied source requires a new notice.

Physical GRBL 1.1 compatibility, USB/driver behavior and real serial-open reset behavior
have not been hardware-tested. This panel only reads state/settings; disconnect closes
communication and cannot stop externally initiated motion. Motion/emission validation belongs
to later slices.

[PR #11](https://github.com/ozkurkuran/MikroCAM/pull/11) is draft. Final-head Windows
[CI run 36281041456](https://github.com/ozkurkuran/MikroCAM/actions/runs/36281041456)
is pending. T027 stays open until publication/final-head CI evidence is complete; T028 stays
open until the validated head is merged and delivery links are updated. No CI or merge success
is claimed here.
