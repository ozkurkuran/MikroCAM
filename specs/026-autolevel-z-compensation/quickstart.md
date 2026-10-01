# Quickstart validation

1. Use the shared CPython3.13 development environment, run `python -m pytest tests/test_autolevel*.py`.
   In PowerShell expand actual test filenames first. Run architecture and complete suite afterward.
2. In the desktop Preflight dock, load and review a supported mechanical source with explicit
   setup/rapid rates. Open Auto-level, load a complete map saved by025.
3. Enter reference work Z and segment/chord/surface limits; prepare, inspect provenance/bounds
   and generated line preview. Confirm board/G54 setup before saving or Machine transfer.
4. Exercise Fake job completion and changed-map/source/parameters invalidation; never attach hardware.
5. Run `python tests/smoke_app.py` and inspect `.venv/autolevel-smoke.png`.
