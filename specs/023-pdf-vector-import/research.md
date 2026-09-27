# Research: selected PDF vectors

## Evaluate existing Evo tool first

`appPlugins/ToolPdf/PdfImport.py` opens filenames without page/crop/flip controls. Its pure reader in
`appParsers/PdfStreamParser.py` scans raw Flate streams and concatenates them without resolving the
page tree; its optional pikepdf path selects only page zero. There are no source/decompressed-size bounds.
`ParsePDF.py` assumes 1/72 inch units and stores only offset/scale, without page boxes/UserUnit/rotation.
Its clip handler resets paths rather than implementing clipping. Fixed-step curves and the legacy
PDF-to-drill heuristic (bounding-box diameter multiplied by 0.974) are unsuitable for physical review.
The existing reader/parser/plugin remain intact; no heuristic drill inference is reused.

A local prototype against the pinned Evo code tested `0 0 10 5 re; f`, then the same path under
`0 1 -1 0 0 0 cm`. Baseline bounds were approximately (0,0,3.527778,1.763889) mm; rotated bounds
collapsed to (-1e-7,-1e-7,1e-7,1e-7), instead of a rotated rectangle. This is direct counterexample
evidence. Existing PDF hole tests remain required.

## Compare permissive alternatives

- [pypdf](https://pypdf.readthedocs.io/en/latest/dev/pypdf-parsing.html) supplies a real page/object/
  content-stream reader in pure Python, under [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE).
  Version 6.19.0 was downloaded as a 395 KB pure wheel for a local prototype without modifying the
  running regression environment. It correctly isolated two ReportLab pages and their distinct paths.
- [pypdfium2](https://pypdfium2.readthedocs.io/en/stable/readme.html) is Apache-2.0/BSD-3-Clause over
  BSD-style PDFium with additional binary notices. Its [page-object API](https://pypdfium2.readthedocs.io/en/stable/python_api.html)
  exposes nested objects/matrices but path/clip extraction needs lower-level calls. A native rendering
  dependency and its notices are unnecessary for the explicitly bounded content subset selected here.
- The optional existing pikepdf path is absent from pinned requirements and only reads the first page;
  adopting it would still require all new vector semantics and bounds.
- [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/faq/index.html) offers drawing extraction under
  AGPL/commercial licensing. It is not added: a permissive object-stream reader is sufficient.

## Decision: pinned pypdf reader at bridge boundary

Pin pypdf 6.19.0 with its BSD-3-Clause license/provenance and dependency checks. Bridge code reads
objects and translates bounded supported operations to pure immutable records; domain/core never
import pypdf. Use strict reading, no password/external resource execution and context-local limits
via the public [apply_configuration API](https://pypdf.readthedocs.io/en/latest/modules/configuration.html).
The downloaded wheel confirms configuration uses ContextVar with reset-on-exit, including bounded
stream decompression, array streams and page-tree entries/depth. This avoids mutable global limits.
The [security documentation](https://pypdf.readthedocs.io/en/latest/user/security.html) describes those
resource controls. Pinning and malformed/expansion fixtures verify the selected behavior.

## Decision: explicit subset with physical paint semantics

Implement full affine path construction, independent subpaths, cubic curves, q/Q graphics state,
opaque fill/stroke, nonzero/evenodd compound fills and basic clip paths. Interpret white as clearing
previous material and other opaque colors as marking; do not infer drills. Reject visible text,
raster images, shading, transparency, patterns and unsupported operators rather than silently omit.
Restrict Form use until bounded resource/transform semantics are implemented and tested; this is
not a general PDF renderer. Empty text setup may be accepted, actual text painting is not.

## Decision: page frame and provenance

Respect inherited boxes, UserUnit and quarter-turn rotation. Start from selected CropBox/MediaBox,
map to oriented physical mm, apply optional rectangular crop, rebase to its lower left, then optional
vertical reflection about cropped height. Store source bytes losslessly using Latin1 in existing
source_file plus a strict optional schema-one PDF report. GeometryObject gets minimal field/UI hooks;
normal project JSON can retain Latin1 strings without a new project format. A malformed stored report
hides stale facts instead of breaking old projects. Recheck the bounded source before publication.
Dependency architecture and existing SVG ImportReport remain unchanged.
