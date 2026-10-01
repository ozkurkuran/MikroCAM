# Data model

All records frozen and validated, finite numeric values reject bool, tuple collections only.
ProbeGrid(x_mm,y_mm): each strict-increasing tuple2..64 values, product<=1024, abs<=1e6;
points row-major (Y outer/X inner). uniform_grid(x_min,x_max,nx,y_min,y_max,ny) constructs it.
ProbePlan(grid,safe_z_mm,min_z_mm,probe_feed_mm_min,travel_feed_mm_min,machine_min_mm,
machine_max_mm,initial_machine_mm,g54_offset_mm,timeout_seconds=30): validate full machine-frame
endpoints, initial inside bounds, safe machine Z>=initial Z,0<safe-min<=100, feeds.01..10000,
deadline3..300. G54 frame positions plus offset must stay within bounds. Upward-first route.
ProbeMap(grid,heights_mm,g54_offset_mm,outcome,origin): heights exact grid count with float|None,
row-major prefix of measurements; outcome incomplete/complete/failed/aborted, origin measured/simulated.
Incomplete is a preterminal acquisition snapshot, including all measured values while final retract
is pending; it never implies complete. Complete requires all values and represents verified final
retract. Failure may contain all values if final retract failed.
StartProbeGridRequest(plan): exact ProbePlan. ProbePhase ready/preparing/probing/complete/failed/aborted.
ProbeObservation(phase,completed,total,map,diagnostic,can_start,can_stop,stop_unverified):
immutable progress and optional latest map, never hardware authority on its own.

Map JSON exact keys schema=1, units=mm, grid{x_mm,y_mm}, heights_mm, g54_offset_mm, outcome, origin.
No silent coercion, unknown schema migration or implicit defaults. Old host projects unaffected.
