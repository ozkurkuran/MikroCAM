# Data model

ImportCoordinates records source width/height tokens (or absent), source unit labels, optional
viewBox, resolved aspect policy, positive physical viewport, final source-to-mm affine and flip.
ImportQuality records optional physical material bounds, geometry validity/nonempty counts,
original open/closed path counts and declared physical approximation tolerance.
ImportReport combines source identity with coordinates, quality and bounded SvgNotice records.
All are frozen exact typed records. Nothing exposes a mutable XML or host object.

Schema1 dictionary encoding is the only new persistent format. Records are independently validated
before publication and after loading. Absent old field => None; schema1 => validated report;
unknown/corrupt data => unavailable diagnostic, never fabricated success or parser rerun.
Object selection/deletion changes which owner supplies the section; no global report state exists.
Source or geometry edits leave the historical snapshot intact and the UI labels that limitation.
