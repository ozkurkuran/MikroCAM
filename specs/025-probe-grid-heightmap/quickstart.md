# Quickstart

Open Machine → Probe grid. Enter G54 work-mm grid, clearance/minimum Z, feeds and explicit
machine limits. Connect to the chosen controller, review the current position/offset and plan,
then explicitly Start. For development use FakeGRBL with the authored plane, never an inferred
serial device. Inspect points/heights and completeness; Stop/Disconnect remain available.
Save a map and load it while disconnected. Loading must cause no motion or transport writes.

Run focused tests/test_probe*.py, full pytest, then tests/smoke_app.py with shared repro-a Python.
Physical probe wiring, clearance and emergency-stop validation remain operator responsibilities.
