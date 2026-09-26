# Validate placement

With the existing development environment:

```powershell
python -m pytest tests/test_placement.py tests/architecture -q
python -m pytest -q
```

Reference cases live in `tests/reference/placement.json`. For origin (10,20), translation
(100,200), 90-degree CCW rotation and X mirroring, source (12,23) maps to (97,198) mm.
The inverse must recover (12,23). Geometry vertices use the identical affine coefficients.
No GUI or manufacturing machine is involved.
