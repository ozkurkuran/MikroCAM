# Validate the laser data boundary

Using the existing Python 3.13 development environment:

```powershell
python -m pytest tests/test_laser_job.py tests/test_laser_json.py tests/test_gerber_bridge.py -q
python -m pytest -q
```

`tests/reference/laser_recipe_v1.json` supplies explicit synthetic test values, not settings
recommended for any material or machine. Load it with recipe_from_json, then write the result
of recipe_to_json to a UTF-8 file and load again. Fields and order must agree exactly.
Bridge tests compare equivalent MM/IN source geometry and ensure source values are unchanged.
This slice emits no laser/CNC commands and connects to no device.
