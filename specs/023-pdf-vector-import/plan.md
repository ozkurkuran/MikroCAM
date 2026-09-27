# Implementation Plan: Selected PDF vector page import

Branch023-pdf-vector-import | Date2026-09-27 | [Spec](spec.md)

## Summary

Keep the evaluated legacy PDF tool intact. Add a bounded selected-page reader using pinned
pypdf6.19.0 (BSD-3-Clause), an independent physical path interpreter using established SVG
curve/fill/stroke helpers, explicit page box/crop/flip review and normal Geometry publication.

## Technical Context

Pinned Python3.13/PyQt6/NumPy/Shapely. Only new runtime dependency is pure pypdf6.19.0;
retain wheel license/provenance, update runtime inventory and verify both reproducible environments.
Reader and host factory live in bridge. Immutable records, coordinate frames and geometric
painting live in core. Domain interpreter may use core helpers only. No pypdf/legacy/Qt in core.
Source bytes remain immutable and are persisted losslessly via source_file Latin1 text. Optional
schema-one pdf_import report has strict codec and separate historical UI; old objects use None.

Limits:16MiB source,8MiB decoded selected-page contents,128pages,512page-tree entries/depth32,
50000operators,64graphics-state depth,10000subpaths,500000sample/outputcoordinates,
100000points/contour,256compound rings,32768overlay intersection candidates and2000000
cumulative overlay edge-work. Coordinates and physical sizes<=1e9mm. Approximation0.01mm.
Unsupported content rejects the selected page; no raster/text conversion or drill inference.

## Constitution Check

All eight gates YES before and after design:
1. Core records/geometry, domain interpreter, bridge pypdf+host, UI inputs/reports follow dependency direction.
2. Short menu action plus GeometryObject optional field/persistence/UI hooks only; legacy+50budget.
3. Existing curve/fill/stroke helpers gain a second concrete format user; no generic backend registry.
   New dependency is justified by failed legacy page/affine behavior and licensed/pinned explicitly.
4. One page-to-mm frame, explicit host conversion and current factory defaults; optional report schema1.
5. Tests first for reader limits, affine/path/paint/crop semantics, persistence and source guards.
6. No controller or laser behavior. Failed/unsupported/changed sources cannot publish partial objects.
7. Existing MIT helpers plus new BSD reader; no AGPL runtime and no external algorithm copy.
8. Three stories,39tasks. Reader/geometry/UI may run in parallel against frozen records.

## Structure

core/pdf_models.py: strict page/document/options/commands/program/report/result/review records.
core/pdf_report_codec.py: strict optional schema-one JSON report,<=64KiB.
core/pdf_frame.py: effective selected box, rotation, crop and flip into physical mm.
core/pdf_geometry.py: bounded physical subpaths and fill/stroke/clip/paint composition, using
existing core.svg_curves.flatten_cubic, svg_fill.fill_svg_paths and svg_paint.render_svg_paths.
core/pdf_paths.py: bounded current-path construction, separate from saved graphics state.
importers/pdf_program.py: finite operator/state grammar and graphics-state/path lifecycle.
bridge/pdf_reader.py: bounded pypdf context, page facts and selected contents translation.
bridge/pdf_import.py: load/review, source verification, atomic normal Geometry construction/report reads.
ui/pdf_import.py: parent-owned file/page/options/review/create dialog; ui/pdf_report.py historical section.
Tests test_pdf_vector*.py, test_pdf_report*.py, existing test_pdf_hole_detection.py;
smoke_pdf_vectors.py plus all desktop journeys. docs/PDF_VECTOR_IMPORT.md and license inventory.

## Complexity Tracking

No exceptions. Forms, visible text, images, shading, patterns, transparency, annotations and
non-solid dash styles are rejected in this first explicit subset. Empty text setup is accepted
for normal generator headers. Basic path clipping and opaque paint order are supported.
Reports are distinct from SVG-specific ImportReport and CAD producer claims.
