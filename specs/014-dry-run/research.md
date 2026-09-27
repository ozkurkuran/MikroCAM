# Research and decisions
No reusable Evo air-cut engine found. preprocessors/Check_points.py positions/probes/alignment,
including G1 down/M0/toolchange; normal GRBL preprocessors produce machining Z/outputs.
Do not regenerate a legacy CNCJob through those preprocessors. Reuse012 strict interpreter and
013 PreparedJob/sender. A separate source and fresh report avoid passing original checks off as
derived geometry proof. Original source must already have complete allowed preflight.
Policy: fixed operator-selected machineZ at/above initialZ/safeZ. One explicit upward Z-only G0
before original XY sequence; remove sourceZ and spindle/coolant starts/S. Unit/distance modes
remain original so XY semantics are unchanged; helical arcs project onto same circle in XY.
M7 may be removed because its known output semantic is intentionally disabled; it never reaches
013 execution. M0/M1/toolchange/unknown words remain blocking. Drop source T metadata if unused
after validation; no toolchange can enter the accepted source subset.
Derived preamble is mm/absolute/G17/G94, M5M9 and optional vertical retract; original explicit
motion modes still follow. Derived preflight uses original initial position/Placement/envelope/
rapid rates and safeZ=dryZ, with the same G54 translation. No controller writes during preparation.
Existing GRBL planner preserves block order; ACK of retract alone is not physical completion.
Live initial/G54 proof and final endpoint/off verification remain owned by013.
Protocol source: https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md
Existing source assessment: preprocessors/Check_points.py and GRBL_11_no_M6.py (repo MIT code).