# Quickstart: Transfer to LightBurn/EZCAD
Generate a current interlaced multi-pass plan in Plugins → Laser CAM. Choose SVG or DXF
export and save the ZIP. Extract it, read README.txt and map pass files in manifest order.
Import each geometry file using mm. Verify dimensions/orientation/registration, set every
pass's power %, speed mm/s, frequency kHz and pulse width ns from recipe.json, and inspect
target ordering/optimization before relying on interlace. An unsupported machine parameter
must be resolved in the target application rather than silently ignored.

SVG/DXF carry geometry; they do not arm equipment or automatically configure laser settings.
Physical test coupons and material/device calibration are separate from software export
validation. No real PCB manufacture is claimed by this feature's automated checks.

Tests: `python -m pytest tests/test_laser_export_formats.py tests/test_laser_export.py
tests/test_laser_export_ui.py -q`; real desktop `python tests/smoke_app.py`.
