# Research and decisions

## Decision: report recorded results, never repeat import
016 already retains source SHA256, element affine/paint, physical viewport, transformed source paths
and valid material. It omits original root unit tokens/viewBox/aspect facts and explicit flip flag.
Add these immutable facts at the existing parse boundary; do not reread source_file or infer scale
from bounding boxes. The report builder consumes the exact import result. Curve tolerance is the
existing core constant; rounded stroke and centreline flattening each reserve half its budget.

Alternative: re-import on selection was rejected because it could be expensive, fail after edits or
produce facts from a different parser version. A generic plugin/report framework is not needed.

## Decision: object Properties section
ObjectCollection selection rebuilds the active object's Properties UI. GeometryObject/GerberObject
set_ui share ObjectUI.custom_box. An owned collapsed section follows this lifecycle without a global
latest-report registry, another dock or an extra worker. Pure widget rendering uses plain text.
Reports are explicitly import-time snapshots; edits/Placement do not silently update their claims.

## Decision: optional versioned project field
Geometry already lacked persisted source_file; actual016desktop exposed and fixed that independent
legacy omission. Retain a separate optional import_report field, whose dictionary has schema_version1.
The inherited FlatCAMObj.from_dict migration leaves constructor defaults for absent fields; old
projects therefore retain None. Unknown/corrupt records yield an unavailable report, while source
and geometry remain usable. Existing project serialization envelope is unchanged. Never persist an
unversioned arbitrary core object or append report metadata into machining tool/default options.

## Scope
Roadmap017 follows016, so first complete reports are SVG. DXF/Gerber-origin objects without a report
show no invented source quality; later import features can add their own recorded evidence. No CAD
source detection, repair, drill extraction, new font/CSS semantics or manufacturing wizard here.
No new package/license/binary. All source inspection is local; no unresolved research question.
