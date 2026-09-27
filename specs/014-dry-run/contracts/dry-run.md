# Dry-run contract
prepare_dry_run(source:SourceSnapshot,report:PreflightReport,dry_z_mm:float,*,cancelled=None)
->DryRunResult. Exact original report reanalysis equality and allowed=True; finite nonbool dryZ
>= original mapped initialZ, >=old safeZ and within Z envelope. Pure-translation Placement required.
No source mutation/I/O. Bound derived bytes/lines by existing caps; check cancellation everyline.

Generated source name identifies DRY RUN and original name within256chars. Header comments include
original digest and chosen machineZ. Generated G21G90G17G94 and M5M9 precede optional G0Z(workdryZ).
workdryZ=dryZ-z_offset; emit bounded nonexponent decimal without material rounding; final derived
preflight/precision guard remains authoritative. Remove all original Z/S words and M3/M4/M7/M8.
Preserve other supported numeric spelling/modes/feed, remove T metadata if desired consistently.
Reject M0/M1/toolchange and unsupported original semantics. Existing M2/M30 retained; generated
preamble output-off is explicit, final sender M5M9/readback remains. Filtered empty lines omitted.
Lineage includes comments and generated lines as None, each retained source executableline as
its original physical line. Preview at most200lines plus total count; no unbounded GUI rendering.

Require positive XY travel (linear XY distance or arc length), not merely Z-only original motion.
Any source G2/G3 must preserve its validated XY endpoint/relativeIJ/signedR spelling; stripping
helixZ gives same planar arc. Original Z-only blocks can retain modal/feed words but create no
derived Z motion. For original motion that relied on a G0/G1 modal word on a removed Z-only line,
retain that mode so later XY semantics stay unchanged.

Derived setup is dataclasses.replace(original.setup,safe_z_mm=dryZ); all other declared values
unchanged. analyze_gcode derived must be allowed, then PreparedJob verifies full exactreport,
line caps, numeric precision, duration/rapid bounds and mechanical execution subset. Newly added
retract contributes to derived time/geometry. Invalid generated source fails before transfer.

UI: existing PreflightPanel adds explicit Dry run action enabled only for current allowedreport.
New DryRunPanel receives original immutable source/report and GUI binding provider, empty dryZ
input, Prepare/Cancel, bounded read-only preview/summary, explicit Load reviewed dry job into Machine.
Worker owns pure prepare_dry_run, generation/cancel/sender checks suppress stale results.
reviewed_binding returns derived(source,report) only while original binding andheight are current;
reviewed_changed emits synchronously oninvalidate/close for pendingStart invalidation. Machine panel
reuses same load_preflight/confirmation/Start API and shows DRY RUN source name with derivedlineIDs.
No auto-start/portopen/alternatewirepath. Active admitted snapshot remainsunchanged afterUIedits.
PreflightPanel owns dry dock shutdown (no newlegacyhook); close cancels/joins<=2s or retainsowner.