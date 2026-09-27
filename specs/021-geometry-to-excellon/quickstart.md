# Quickstart: Geometry circles to Excellon

Use the pinned Python3.13 environment. Run `python -m pytest -q` and actual desktop
`python tests/smoke_app.py` after focused geometry-drill and existing SVG-drill tests.

Select a Geometry object containing closed circles. Plugins → Geometry circles to Excellon opens
review. Analyse, inspect physical diameters and boundary roles, then select only intended holes.
Nothing starts selected. Confirm the proposed tool groups and create a named separate Excellon.
Source geometry and machining settings must remain unchanged. Export/reparse and project reopen
retain selected centres/diameters at configured output precision. Changing source geometry/units,
renaming or replacing the object after analysis requires a new analysis.

The review does not prove drilling intent or operate equipment. See contracts/geometry-drills.md
for exact tolerances, bounds, authoritative multi-tool source and source guard behavior.
