# Research decisions

Decision: reuse ProbeMap, Placement, ModalInterpreter, PreflightSetup/analyze_gcode and
PreparedJob. Rationale: one physical coordinate authority and existing dialect/precision gates.
Alternative: another parser or serial path would duplicate safety semantics; rejected.

Decision: bilinear interpolation of complete maps in stored G54 work mm. Explicit reference Z
is subtracted from measured work Z. Original placed machine XY minus map G54 XY is the query.
Output uses map G54 as pure translation; original placement is baked into generated XY once.
Alternative: inverse-transform the map is unnecessary and risks double placement.

Decision: rapid endpoints retain original placed Z. Pure vertical feed establishes compensated
cutting Z; diagonal/horizontal feed after uncompensated rapid must not silently jump surfaces.
Feed chords split at cell crossings and adaptive midpoint checks (bilinear along a straight
cell chord is quadratic, so midpoint deviation bounds the chord's maximum surface error).
Arc tessellation bounds sagitta plus permitted radius endpoint disagreement; complete analytic
arc extents must lie inside the map, then each chord follows the same cell subdivision.
Alternative: endpoint-only compensation misses saddle curvature; arbitrary fixed sampling has
no error guarantee. Original sources remain immutable; generated canonical mm/absolute lines
carry exact source ancestry and map digest. No copied code or new dependency.

Decision: dedicated concrete preparation worker/panel, opened from the existing Preflight dock;
map load is offline and explicit fields start blank. Existing Machine receives fresh reviewed
output; no new machine behavior/state or protocol. Export is atomic separate G-code.
An independent read-only design audit is performed per speckit-plan's research phase.

Independent implementation audit found export could overwrite the original source/map.
Failing regression preceded a fix: UI retains resolved loaded-source/map paths and the bridge
rejects identical resolved targets and hardlink aliases before creating a temporary export.
Normal replacement of a separate output remains supported. Nonmodal file choices preserve
access to machine Stop while another session is active. Geometry audit found no remaining blocker.
