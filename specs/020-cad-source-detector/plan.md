# Implementation Plan: CAD source detection

Branch020-cad-source-detector | Date2026-09-27 | [Spec](spec.md)

## Summary
Report bounded explicit SVG/DXF producer claims independently of geometry import. Add immutable
source assessment and strict schema1 codec; attach an optional historical record to imported
Geometry/Gerber objects and display it in Properties. Missing/conflicting metadata is Unknown.

## Technical Context
Python3.13, stdlib-only core/importers detector, existing PyQt6 UI and host adapters. No dependency.
Windows11 primary. Existing source text is retained by appIO; assess the exact UTF-8 text bytes after
successful import, preserving newline/BOM. A separate optional `cad_source` record avoids inventing
SVG page/curve fields for DXF and leaves ImportReport schema2 unchanged. Old objects defaultNone.
Detection input<=16MiB, XML<=10000nodes/depth64, DXF<=250000pairs/8192chars per line, evidence<=32
with field<=80/value<=512chars. Serialized assessment<=65536UTF8bytes. Unknown/unavailable for
input/metadata limits; no partial positive answer. Every production module<=600/function<=80lines.
Complete pytest/reference/architecture suite and actual desktop source/save/reopen journeys.

## Constitution Check
All eight gates YES before research and after design:
1. Immutable records/codec core; parsing in importers; owner boundary in bridge; plain-text Qt in UI.
2. Host additions limited to optional persisted attr and two short import hooks (<50legacy lines).
3. Concrete functions/records, no registry/scoring/plugin abstraction, no dependency/process I/O.
4. No coordinate transform or default changes. Independent source schema1, missing-old tests;
   existing physical ImportReport2 stays intact rather than inventing a DXF viewport.
5. Tests first for records, parsing, malformed/limit/conflict, host preservation and persistence.
6. No machine connection or emission. Source claims never imply geometry or manufacturing validity.
7. Independent finite evidence rules, existing MIT Neo trace retained, actual fixture licenses/hashes.
8. Three stories, <=40tasks.

## Project Structure
core/cad_source.py and cad_source_codec.py; importers/cad_source.py, cad_svg_source.py,
cad_dxf_source.py; bridge/cad_source.py; ui/cad_source.py; both legacy object UIs call a short hook beside the existing physical report
to attach the second optional historical section. appIO SVG/DXF source boundary hooks and Geometry/Gerber
optional field only. Tests/test_cad_source*.py, reference/cad-source/, smoke_cad_source.py.

## Complexity Tracking
No exceptions. Detection does not require successful SVG geometry parsing: a fixed external SVG1.1
DOCTYPE may be ignored by evidence inspection without fetching it; current physical importer still
rejects DTDs. Genuine KiCad export is source-detector evidence, not a new geometry-compatibility claim.
