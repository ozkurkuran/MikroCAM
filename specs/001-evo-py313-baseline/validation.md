# Evo Python 3.13 baseline — validation

Date: 2026-09-26. Branch: `001-evo-py313-baseline`.
Selected upstream: `upstream-evo-beta1-baseline` (`e046a2a3`).
Implemented source commits: `d30cc6c8` (reference adaptations), `1786e70f` (runtime/setup).

## Environment and reproducibility

- Windows 11 Pro x64, build `10.0.26200`.
- Standard CPython `3.13.13`, 64-bit, recorded in `.python-version`.
- PyQt6 6.11.0 / Qt 6.11.2, NumPy 2.5.3, Shapely 2.1.2, VisPy 0.17.0.
- `requirements.txt`: 43 pinned runtime distributions, including transitive dependencies.
- `requirements-dev.txt`: five additional distributions; each clean development environment
  has 49 distributions including the venv's pip 26.0.1.
- Two newly created environments, `.venv/repro-a` and `.venv/repro-b`, installed
  `requirements-dev.txt` independently. Their normalized name/version lists matched exactly.
  Both `python -m pip check` runs returned `No broken requirements found.`
- Repro-a contains no rasterio, svgtrace, scipy or win32api. Importing appMain, the full
  unit suite and all three final desktop smoke cycles passed in that environment.
- After comparing the two clean installs, repro-b also installed requirements-image.txt
  successfully. Its dependency check remained clean, and the real pinned svgtrace export
  has signature `trace(filename: str, blackAndWhite: bool = False, mode: str = 'default') -> str`.
  No Chromium download or live browser trace was needed or performed for acceptance.

## Test-first evidence and final unit result

Unmodified Evo application/test sources produced **484 passed, 2 skipped, 310 subtests
passed**, with three SWIG deprecation warnings. The full suite masked import-time option
parsing by importing App with temporarily empty argv during collection.

Before the corresponding fixes, the adapted compatibility file produced **5 failed,
4 passed**: open SVG subpaths, holes/disconnected contours, empty polygon rendering,
explicit CLI parsing and fresh-process import safety failed. Optional image tests initially
failed on eager imports; those failures were corrected without suppressing the assertions.

Final command (fresh core-only environment):

```powershell
.\.venv\repro-a\Scripts\python.exe -m pytest -q -rs
```

**511 passed, 2 skipped, 310 subtests passed in 14.42 seconds.** Three existing SWIG
`__module__` deprecation warnings remain. No upstream test file was modified or excluded.
The 27 additional tests cover runtime behavior, geometry edges, optional dependencies and
settings isolation.

The two skips already existed upstream in tests/test_lifecycle_initialization.py:

| Test | Upstream condition / contents | Coverage here |
| --- | --- | --- |
| test_quit_application_can_save_preferences | Explicit unittest.skip; body is pass | Desktop smoke executes normal quit and preference save |
| test_full_app_instantiation_sequence | Explicit unittest.skip; actual constructor commented out | Desktop smoke constructs the real App |

These are empty Qt-context placeholders, not newly skipped failures or platform failures.

## Eight legacy behavior mappings

Source: legacy8994 baseline-8.994-py313, tests/test_runtime_compatibility.py.

| Legacy behavior | Evo verification |
| --- | --- |
| Multipart component preservation | Existing Geometry.flatten on MultiPolygon, list and single Polygon |
| Nested multipart flatten | Existing Geometry.flatten with MultiLineString, pathonly=True |
| SVG open subpaths and scale | Fixed reference JSON, separate LineStrings, absolute tolerance 1e-9 |
| SVG holes/disconnected contours | Fixed reference areas 4 and 96, exactly one hole |
| Polygon plotting and empty geometry | Finite 10x2 vertices; empty 0x2 path; added GeoJSON/3D cases |
| Current ezdxf import | Generated DXF line retains its two endpoints |
| Qt6 slider/text editor | qtbot validates fractional values and editable text |
| Explicit CLI arguments | shell/headless/positional arguments and reset; fresh subprocess import regression |

## Three final desktop smoke cycles

```powershell
1..3 | ForEach-Object { .\.venv\repro-a\Scripts\python.exe -u tests/smoke_app.py }
```

All three returned **exit 0** with STARTUP_OK, GERBER_OK, EXCELLON_OK, ISOLATE_OK, CNC_OK,
PROJECT_SAVE_OK, PROJECT_ROUNDTRIP_OK, RENDER_OK and SHUTDOWN_OK.

- Same bundled Gerber/Excellon examples as the legacy smoke.
- Gerber bounds: approximately `(13.794, 13.667, 32.844, 28.907)`.
- Nonempty isolation geometry and parsed CNC toolpath; G-code length **26,367 characters**.
- Reopened objects: smoke_gerber (gerber), smoke_drill (excellon), smoke_iso (geometry),
  smoke_cnc (cncjob). Names/kinds and G-code remained identical after reload.
- The expected Import Settings dialog is explicitly accepted. Unexpected dialogs or
  asynchronous Python exceptions fail the smoke.
- Real VisPy/OpenGL pixel rendering and a non-null screenshot were checked. Screenshot
  was visually inspected: PCB traces, pads, drills, toolpaths and all four objects visible.
- Normal app.quit_application executed. All worker/listener threads stopped, all pool
  processes were dead and multiprocessing.active_children was empty before process exit.
- User/app settings use explicit temporary INI files; data uses temporary APPDATA. The
  named QSettings overload trap was found during harness development and fixed. The final
  helper leaves Qt's global format/search paths unchanged. Exported user registry snapshots
  matched across the final isolated suite and smoke cycles.
- First-run file associations and automatic updater are disabled only inside the harness;
  IPC uses a unique pipe. The watchdog can terminate only its own process children on failure.

Local ignored evidence: `.venv/final-suite.log`, `repro-*-install.log`,
`repro-*-packages.json`, `smoke-cycle-1.log` through `smoke-cycle-3.log`, their PNGs and
`startup-smoke.png`. Logs/screenshots contain local paths and are not published as source.

The fixture's obsolete Gerber/comment notices and upstream QObject disconnect/QThreadStorage
shutdown warnings remain visible. They are not Python exceptions and did not leave running
threads/processes. The smoke follows the upstream entry point's os._exit pattern only
after normal shutdown and successful assertions, avoiding native Qt/VisPy GC order issues.

## Scope, review and remaining limits

- PowerShell launcher syntax, missing-env behavior and `-h` forwarding were verified.
  The launcher supports the pinned major/minor and reports the tested patch separately.
- Changed legacy Python files: 112 added / 169 removed = **-57 net lines**; within +50.
  Added modules <=232 lines and new functions <=80 lines. No new feature logic, product
  renaming, persistent schema, machine connection or updater functionality was added.
- All 12 functional requirements and five success criteria map to the 20 tasks. No
  unresolved spec clarification or registered before/after hook remains.
- Optional tracing's dependency/API contract is checked; real browser tracing is outside
  the CAM acceptance journey. Linux/macOS, every editor/plugin and hardware are not certified.
- SVG fill-rule/winding semantics remain a broader existing importer limitation; this
  slice preserves the tested containment behavior and fixes the reference regressions.
- CI/import-boundary/ratchet automation and complete distribution notices belong to the
  following roadmap slices. The original research document is still awaiting its source.

Acceptance outcome: **evo-py313-baseline complete**. Next slice: foundation-guardrails.
