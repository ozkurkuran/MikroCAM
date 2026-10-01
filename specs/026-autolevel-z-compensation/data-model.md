# Data model

AutoLevelSettings: exact complete ProbeMap, reference_z_mm finite abs<=1e6;
max_segment_mm .01..10, chord_error_mm .0001...1, surface_error_mm .0001...1.
Map digest is SHA256 of existing deterministic schema1 map serialization; no format change.
AutoLevelResult: original SourceSnapshot/PreflightReport, settings, generated PreparedJob,
immutable lineage matching every generated physical line (original source line or None).
Feed path coordinates and surface queries are work-mm in map G54. Derived PreflightSetup has
pure translation=map G54 XY, Z translation=map G54 Z and the unchanged machine envelope/safe Z.
Initial position is original placed machine position minus map G54. Resource bounds reuse
16MiB/250000lines; segmentation checks cancellation on each bounded generated piece.
