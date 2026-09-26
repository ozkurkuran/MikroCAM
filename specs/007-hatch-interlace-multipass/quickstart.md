# Quickstart: Interlaced multi-pass preview
Open Plugins → Laser CAM, select Gerber, load a schema-1 recipe or enter recipe/pass names
and all four parameter values. Add/reorder rows as needed. Save recipe JSON for reuse.
Enable hatch and set Interlace N; N=1 retains prior scan order. Generate and inspect one
Geometry preview; the plan contains one pass for each recipe row with explicit settings.
Changing inputs invalidates the plan. Export is delivered in slice 008. Example values in
tests are synthetic and are not material/device presets.

Tests: `python -m pytest tests/test_laser_interlace.py tests/test_laser_recipe_ui.py
tests/test_laser_cam_ui.py -q`; real desktop `python tests/smoke_app.py`.
