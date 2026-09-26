# FlatCAM Evo — MikroCAM development baseline

FlatCAM Evo (c) 2019 by Marius Stanciu, based on FlatCAM, 2D Computer-Aided PCB
Manufacturing (c) 2014–2018 Juan Pablo Caram. Original copyright and MIT license
notices remain in [LICENSE](LICENSE).

This repository is the MikroCAM fork of FlatCAM Evo. The current compatibility slice
keeps Evo's application name, interface and project format. It prepares PCB jobs from
Gerber and Excellon files and generates CNC G-code.

The selected upstream is Bitbucket `Beta_1.0` at `e046a2a3`, preserved as
`upstream-evo-beta1-baseline`. The original mekatrol fork remains at
`upstream-evo-baseline`. See [preparation history](docs/PREPARATION.md) and
[roadmap](docs/ROADMAP.md).

## Windows 11 setup

Install standard **CPython 3.13 x64 with Tcl/Tk**. The tested patch version is in
`.python-version`; the launcher checks its major/minor version and rejects free-threaded builds.
Run these PowerShell commands from the checkout:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\run-flatcam.ps1
```

The launcher uses this checkout's virtual environment, works from paths containing
spaces, and forwards application options such as `--shellfile=example.tcl`.
For an explicit console invocation, use `.\.venv\Scripts\python.exe flatcam.py`.
Runtime and transitive dependency versions are pinned. A separate GDAL installation
is unnecessary; optional rasterio wheels provide their own GDAL runtime.

## Optional image import and tracing

Core CAM and startup work without rasterio, svgtrace, Playwright or a downloaded browser.
For the existing image import/trace tool:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-image.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pip check
```

Tracing uses svgtrace's Playwright backend. Its compatible version is pinned because
newer svgtrace releases require NumPy 1.x. Missing optional packages/browser are reported
when invoking the tool. Chromium may also be installed by svgtrace on first use; it is
not needed for the baseline smoke test.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe tests/smoke_app.py
```

Unit tests run offscreen with isolated settings. The smoke requires a working Windows
desktop and OpenGL driver. It opens a temporary application window, loads bundled
Gerber/Excellon examples, generates isolation and G-code, saves/reopens the project,
renders the canvas to `.venv/startup-smoke.png`, and verifies normal worker/process shutdown.
It uses temporary app data and explicit INI settings, an isolated IPC pipe, and disables
file associations and update checks in the test process. It does not drive hardware.

Results and remaining validation limits are recorded in
[the feature validation record](specs/001-evo-py313-baseline/validation.md).
Two upstream Qt-context placeholder tests remain explicitly skipped; the desktop smoke
exercises actual application initialization and preference saving on shutdown.

## Scope and other platforms

Windows 11 x64 is the validated target for these pins. Linux remains secondary and has
not been certified by this slice. The upstream `environment.yml`, `setup_ubuntu.sh` and
Makefile remain available as historical platform setup paths; they are not substitutes
for the pinned Windows instructions above. macOS support is outside this slice.

This baseline validates the stated CAM journey, not every tool, editor, controller or
postprocessor. Distribution packaging, complete dependency notices, product branding and
CI guardrails follow their own roadmap slices. Feature rules are in
[CLAUDE.md](CLAUDE.md) and the [constitution](.specify/memory/constitution.md).
