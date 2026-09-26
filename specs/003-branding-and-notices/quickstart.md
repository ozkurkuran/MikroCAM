# Validate branding and notices

Install existing requirements-dev in the checkout environment, then run:

```powershell
python -m pytest tests/test_product_identity.py tests/test_product_update_boundary.py tests/test_dependency_notices.py -q
python -m pytest -q
python -m pip check
python tests/smoke_app.py
```

Use a real desktop/OpenGL environment for smoke. Inspect the title and About screenshot;
MikroCAM and 0.1.0 must agree, FlatCAM/Evo author credits remain visible, and project reopen
must retain the same objects/G-code and host compatibility version. The notice checker runs
without installing optional image packages and covers every pin from the three requirements files.
