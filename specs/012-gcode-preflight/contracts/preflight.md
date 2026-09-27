# Public contracts and supported dialect

## Core API
`mikrocam.core.gcode_preflight.analyze_gcode(source: SourceSnapshot, setup: PreflightSetup,
cancelled: Callable[[], bool]|None=None) -> PreflightReport` performs no I/O or mutation.
Models/constants are in `mikrocam.core.gcode_models`; use existing `core.placement.Placement`.
Source/setup construction raises ValueError for bad values; program syntax/semantic issues
return blocked findings. Cancellation raises PreflightCancelled. No suppressed unknown tokens.
Check cancellation every source line and before returning; max250000 lines,4096 chars/line,
64 chars/numeric token, absolute coordinate/feed magnitude<=1e9,200 retained findings.
Text source max16MiB; bounds/time are partial/None on interpretation failure. Analytic validation
runs independently of controllers, serial settings, GUI or legacy parser state.

## Dialect
ASCII executable words, case-insensitive, decimal non-exponent numbers; adjacent words allowed.
Spaces/tabs, blank lines, same-line nonnested parenthesis comments and semicolon-to-EOL comments
are supported. CRLF/LF/CR normalize line boundaries. Reject control/realtime characters even in
comments, multiline/unclosed/nested parentheses, percent wrappers, checksums, macros and any
unknown word. Non-ASCII source is blocked even in comments: UTF-8 bytes may be realtime commands.

Supported groups: motionG0/G1/G2/G3; unitsG20/G21; distanceG90/G91; planeG17; arc-distanceG91.1;
feedG94; coordinateG54; cancelled cutter/tool compensationG40/G49. Units/distance must be explicit
before motion, G94 before feed movement, G17 before arcs. No implicit machine modal defaults.
G54/G40/G49 are declarations consistent with the fixed setup: initial G92/TLO/compensation are
assumed zero. This offline report does not verify that a controller meets those assumptions.
G4P seconds (required nonnegative P) is dwell, no axis/motion words. M3/M4/M5, M7/M8/M9,
M0/M1/M2/M30, S>=0 and T integer>=0 are recognized metadata only; output-start is reported as
program content, never transmitted. M0/M1 mean unknown operator-wait total. M2/M30 end the program;
subsequent executable words are blocked. T does not perform a tool change; M6 is unsupported.
N integer0..9999999 is optional line metadata. Duplicate non-G/M words and conflicts within G/M
modal groups are errors. Unused axis/center/radius/dwell words and combinations are errors.

XYZ endpoints follow active distance mode, units convert once to mm. F>0 is stored in physical
mm/min when supplied, and persists through a unit change without another F. Unsupported G93,
G18/G19, G90.1, G53/G55..59/G10/G28/G30/G92/G43.1, canned cycles/probing/variables are blocked.
A feed move missing F may still contribute known geometry but adds an error and unknown duration.
A nonpositive F is an error even if the block does not move. Numeric overflow/magnitude fails.

XY G2/G3: I/J are incremental center offsets regardless of G90/G91; omitted I or J means0 but
at least one must be present. Every arc also requires an explicit X or Y endpoint word, including
full circles/helices; an omitted or Z-only endpoint is rejected as GRBL would reject it.
R form permits signed radius: positive minor, negative major.
Do not combine R with I/J. No K/P arc turns. Equal XY endpoints with I/J mean a full circle,
including optional helical Z. R full-circle/zero-radius/impossible chord and radius inconsistency
>0.005mm are rejected. Arc bounds include analytic interior extrema after actual Placement,
not chord or polygon approximation. Helical Z extrema are endpoints. Arc length is
hypot(radius*abs(sweep), deltaZ), invariant under the rigid/mirrored Placement.

## Checks and timing
Initial position plus all path extrema must fit inclusive machine bounds (numeric tolerance1e-9mm).
Any G0 horizontal travel with min(startZ,endZ)<safeZ is unsafe; downward Z-only rapid ending below
safeZ is unsafe. Z-only upward retreat is allowed subject to bounds. Cutting moves require feed.
Nominal feed time=60*length/feed; rapid=60*max(abs(machineDelta_i)/axisRapid_i); dwell adds P seconds.
No acceleration, cornering, overrides/spindle spinup or operator time is claimed. Missing rapid
rates for nonzero rapid movement or pauses => total None. Interpretation failure => total None.
A zero-motion program is blocked. Successful output says declared-setup geometry checks only.

## Bridge/UI
`bridge.gcode_source.snapshot_cncjob(obj)` copies only complete `source_file` text and name from
an object whose kind is cncjob. Reject absent/empty/nontext source; never fall back to incomplete
body `gcode`, call export/edit methods or infer travel limits from object options.
`load_gcode_file(path)` uses a bounded binary read and strict UTF-8(-BOM) decode into SourceSnapshot.
It must not write the file. Filename and digest label the loaded snapshot; external file edits do
not mutate this snapshot or authorize later execution (later streaming must rebind exact bytes).

Preflight dock has Load file / Use selected CNC job, explicit setup fields, Analyze and Cancel.
No setting defaults silently authorize analysis; required numeric inputs start empty. Optional
rapid fields may remain empty (unknown duration); rotation/mirroring and work-origin transform
are represented with the existing Placement UI/value authority. Source/setup changes invalidate
results. A selected-job provider is rechecked before showing its result and on periodic UI refresh;
changes/deletion/selection replacement invalidate it. File results explicitly identify the loaded
snapshot, not a live file. Worker owns only immutable values, never a legacy object or widget.
On close cancel+join2000ms; timeout retains liveworker/window. Host shutdown honors that result.
No new dependencies or controller/transport command APIs are used.
