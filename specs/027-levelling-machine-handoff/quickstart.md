# Validation guide

Use shared `E:\VSCode\Flatcam\MikroCAM\.venv\repro-a\Scripts\python.exe`.
Run `-m pytest tests/test_levelling_machine_handoff.py tests/test_levelling_grbl_wire.py
 tests/test_levelling_tool.py tests/test_levelling_journey.py -q` from this checkout.
Expected: mock-only tests pass; no physical serial backend is accessed.
Run `tests/smoke_app.py` with QT_QPA_PLATFORM unset for the actual desktop, using the
existing temporary settings sandbox and Fake journeys. Inspect handoff screenshot and log.
Run complete `-m pytest -q -rs`; require architecture checks and final-head Windows CI.
