# Runtime and validation contract

- `run-flatcam.ps1` resolves paths relative to itself and starts this checkout's .venv,
  validates standard Python 3.13 x64, sets QT_API=pyqt6 and forwards application arguments.
  Missing environment or wrong interpreter produces a clear failure; no global fallback.
- `python -m pytest -q` discovers all upstream and compatibility tests under tests/; importing
  appMain never interprets pytest options. Unit tests require no device/live update service.
- `python tests/smoke_app.py` uses a temporary data/settings sandbox and fixed fixtures,
  prints stage markers, saves a screenshot under .venv, returns zero only after real CAM,
  project round-trip, render and normal thread/process cleanup. It requires a desktop.
- Existing `--shellfile`, `--shellvar`, `--headless` arguments retain their documented meaning.
- Optional image tracing reports the missing package/browser at invocation; its absence
  never prevents the main application from importing or opening.
