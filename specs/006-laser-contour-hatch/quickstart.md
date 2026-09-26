# Quickstart: Laser CAM preview

1. Start MikroCAM using the documented Python 3.13 environment and load a copper Gerber.
2. Open Tools → Laser CAM. Refresh/select the copper source and optionally a closed outline Gerber.
3. Load an explicit recipe JSON created by slice 005. Set placement in mm/degrees if required.
4. Choose contour mode and optionally hatch, spacing, angle and cross hatch. Select copper
   or clearance (board minus copper); clearance needs an explicit containing outline.
5. Generate. Inspect the ordinary Geometry preview on the existing canvas. Generate again
   to replace the panel's owned preview. Cancel/close prevents an unfinished result appearing.

This slice produces paths only. Pass editing/interlace and SVG/DXF export follow in 007/008.
Test recipes are synthetic examples, not validated material/device settings.

Headless checks: `python -m pytest tests/test_laser_paths.py tests/test_laser_geometry.py
tests/test_laser_planner.py tests/test_laser_cam_bridge.py tests/test_laser_cam_ui.py -q`.
Run `tests/smoke_app.py` on the Windows desktop for real host preview/shutdown evidence.
