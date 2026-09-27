# Data model: G-code preflight

All values are immutable; core uses stdlib and existing Placement. No machine/Qt imports.

- `SourceSnapshot(name: str, text: str)`: nonempty name<=256, nonempty text<=16MiB UTF-8,
  `sha256` computed from exact text. Numeric/line restrictions belong to the lexer.
- `PreflightSetup(initial_position_mm: XYZ, placement: Placement, z_offset_mm: float,
  machine_min_mm: XYZ, machine_max_mm: XYZ, safe_z_mm: float,
  rapid_rates_mm_min: XYZ|None=None)`: exactly three finite non-bool coordinates, magnitude<=1e9;
  min<max for each machine axis; safe Z within declared Z limits; optional rates all positive.
  Initial position is in program/work coordinates; Placement maps XY to machine, Z adds offset.
  Initial position outside limits is a report error, not silently clamped.
- `Finding(line: int, code: str, message: str, severity: str='error')`: line is1-based,0 for
  setup/program-level findings. severity error/warning, message<=256; stable code for tests/UI.
- `PreflightReport(source_name, source_sha256, setup, complete, bounds_mm, executable_blocks,
  rapid_count, linear_count, arc_count, distance_mm, duration_seconds, units_seen,
  distance_modes_seen, findings, finding_count, error_count)`: bounds is(minXYZ,maxXYZ)|None;
  findings holds first200 with total counters retained; duration None when unknown/incomplete.
  `allowed` property is complete and error_count==0. This means geometric checks passed only.
- `PreflightCancelled`: cooperative cancellation exception, never a successful report.

Core motion representation is internal and concrete: source line, G0/G1/G2/G3 kind, start/end
program XYZ, physical feed, and optional XY arc(center, radius, start angle, signed sweep).
Do not retain an entire toolpath in the report. Accumulate analytic bounds/distance/time online.

UI state: empty -> source/setup ready -> analyzing -> report/error/cancelled. Input changes
increment a generation token and clear the report; cancelled/obsolete worker outputs are ignored.
Snapshot label/digest identify immutable text, never a live hardware state or execution approval.
No serialization schema or persistent profile is introduced.
