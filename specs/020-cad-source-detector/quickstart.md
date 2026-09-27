# Quickstart: CAD source evidence

Use pinned Python3.13 environment and requirements-dev.txt. From this checkout:
`python -m pytest -q tests/test_cad_source_models.py tests/test_cad_source_codec.py tests/test_cad_source_svg.py tests/test_cad_source_dxf.py tests/test_cad_source_bridge.py tests/test_cad_source_ui.py`
Then fullsuite `python -m pytest -q` and actualdesktop `python tests/smoke_app.py`.

Import an SVG with explicit producer metadata: Properties shows application, exact field/value,
sourceidentity and historicalnotice. A filenameorlayermention alone staysUnknown. Conflicting
applications stayUnknown withbothclaims. Import unmarked KiCad DXF: Unknown iscorrect.
Saveandreopen SVG/DXF Geometry/Gerber objects withsourceinputs removed: assessmentmustremain.
Oldobjectswithoutdata openwithoutinventedidentity. ThisdoesnotvalidateCAMgeometryorhardware.
See contracts/cad-source.md and research.md for exactmarkers, boundsandvendorcoverage.
