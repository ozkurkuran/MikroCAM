# Quickstart: reviewed Excellon merge

Use the pinned Python3.13 environment. Focused tests cover merge, physical tools and existing shared
factory callers; run the complete `python -m pytest -q` and actual desktop `python tests/smoke_app.py`.

Select at least two Excellon objects. Plugins → Review Excellon merge opens a fixed-source dialog.
Analyse and inspect physical tools, source-tool mapping, duplicate removals and overlap conflicts.
Resolve conflicts in the original objects and analyse again. Enter a new object name and create the
separate result. Export/reparse and project reopen must preserve drills/slots at configured precision,
while every source remains unchanged. Editing/replacing sources after analysis requires reanalysis.

Test fixtures include mixed units, duplicate holes and reversed duplicate slots. No drilling or
controller connection is required. Exact equality is deliberate; there is no implicit tolerance.
