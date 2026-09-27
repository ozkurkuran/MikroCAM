# Quickstart validation

Use the existing pinned Python 3.13 environment. Run the dedicated svg_transform/models/paint/curves/
document/import tests, then `python -m pytest -q` and `python tests/smoke_app.py`.

Analytic scenarios: equal physical rectangles in mm/in/px; nonzero viewBox with meet margins; nested
translate/rotate/nonuniform scale and skew; inherited stroke widths with caps/joins; exact matrix
coefficient order; mm vs IN host geometry; malformed transform termination and atomic import failure.
Desktop: import authored SVG into Geometry and Gerber, check physical bounds/solid widths, save and
reopen, then run previous CAM/laser/manual/preflight/streaming/dry/console flows. No machine is needed.

Read contracts/svg-import.md for exact limits/units and explicitly rejected SVG appearance. Source
bytes, existing objects and frozen reference artifacts must remain unchanged. Record evidence in
validation.md; do not mark physical-machine validation performed.
