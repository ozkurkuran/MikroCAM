# Compensation contract

`surface_height(map, x_mm, y_mm)` returns bilinear height of a complete map, rejects exterior.
`prepare_autolevel(source, report, settings, cancelled=None)` returns an immutable current
AutoLevelResult or rejects the whole operation. Fresh original/derived review and PreparedJob
are required; no file/transport access. All feed points use placed machine XY minus map G54;
corrected machine Z = original placed Z + map height - explicit reference height.
G0 remains uncompensated. Output is explicit G21/G90/G17/G94/G54 with G0/G1 XYZ; Feed F is mm/min.
UI prepare is cooperative; changed inputs invalidate preview/save/transfer immediately. Derived
handoff is `(source, report, binding_provider)` through the existing Machine admission path.
No transfer without current board/G54 confirmation. Map origin stays visible and in G-code comments.
