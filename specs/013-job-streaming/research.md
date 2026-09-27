# Protocol decisions
Simple send/response ACK means acceptance, not physical completion; planner may hold16 moves.
Dwell/planner capacity can delay ACK while status and priority processing must remain available.
Canonicalization preserves numeric spelling; realtime bytes cannot hide in comments.
Hold:1 decelerates; Hold:0 stopped. Feed hold can leave spindle/coolant on. Cycle-start must be
restricted to explicit same-job resume. Reset can lose position and execute startup; empty N proof
required. Door fallback may park. M2/M30 is not physical output-off proof; final M5M9/readback/Idle.
$32=0 does not identify physical spindle wiring; require mechanical confirmation and reject lasers.
Offline rotation/mirror is not applied by GRBL. Match actual G54 and zero G92/TLO.
Source watchdog is conservative; no physical duration guarantee and no ambiguous retry.
Primary protocol facts only; no implementation copied:
- https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md
- https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md
- https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md
- https://github.com/gnea/grbl/blob/master/grbl/gcode.c
- https://github.com/gnea/grbl/blob/master/grbl/protocol.c
- https://github.com/gnea/grbl/blob/master/grbl/motion_control.c
- https://github.com/gnea/grbl/blob/master/grbl/config.h