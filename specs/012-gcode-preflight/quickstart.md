# Preflight quickstart
Use the pinned Windows CPython3.13 environment from repo root. No device is required.

```powershell
python -m pytest tests/test_gcode_models.py tests/test_gcode_lexer.py tests/test_gcode_motion.py tests/test_gcode_preflight.py -q
python -m pytest tests/test_gcode_source.py tests/test_gcode_ui.py -q
python -m pytest tests/architecture -q
python -m pytest -q
python tests/smoke_app.py
```
The desktop command uses the existing sandboxed CAM/project/laser/manual smoke plus a read-only
preflight journey. Record actual results/timing/heads in validation.md; commands are not evidence.

In Plugins > G-code preflight load a file or selected CNC job, supply initial program position,
Placement/Z offset, machine min/max and safe rapid Z. Optional XYZ rapid rates enable a nominal
complete time estimate. Analyze and inspect exact snapshot digest, extents and line findings.
Unknown syntax or missing setup blocks success. Cancel/replace input to confirm old results do
not reappear. Source is never changed or transmitted. A passed report assumes the declared setup
and does not establish physical clearance or authorize machine operation.
