# Validation quickstart

Requires Windows 11 x64, standard CPython version in `.python-version` with Tcl/Tk, internet
for installation, and a working desktop/OpenGL driver for smoke. Run from repository root.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests/smoke_app.py
.\run-flatcam.ps1
```

Expected: clean dependency check, all tests pass, smoke prints success for each CAM stage,
project reload and rendering, then exits normally. Repeat smoke three times for startup/
shutdown. A second clean environment must install the same pinned package versions.
Actual commands, counts and evidence are recorded in validation.md after execution.
