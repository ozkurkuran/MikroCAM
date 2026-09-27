# Quickstart

With pinned Python3.13 run feature pytest files then full `python -m pytest -q` and
`python tests/smoke_app.py`. Import the authored Illustrator-style SVG as Geometry and Gerber;
inspect physical bounds, visible layer/XMP notices and clipped material. Save/reopen preserves
source bytes and report. Schema1 old report must still open; schema2 percentages must roundtrip.
Analytic compound fixtures compare both winding rules; transformed group/object-bbox clipping
must intersect correctly without leaking material. Invalid/external/overbudget inputs fail atomically.
Existing SVG/drill/reference/desktop journeys remain green. Record exact runtime/CI heads and actual
screenshot evidence in validation.md. Authored data is not a genuine Illustrator export.
