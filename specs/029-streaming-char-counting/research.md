# Research decisions
Read-only stream_research agent checked existing code and primary GRBL protocol documentation.
GRBL serial.h/serial.c define RX_BUFFER_SIZE=128 and a 129-element ring, leaving one slot empty:
128 usable bytes, not 127. $I report.c OPT reports planner and RX compilation capacities.
Planner capacity (15 usable default blocks) is independent from serial byte capacity.
Only complete FIFO ok/error responses release bytes; realtime bytes bypass ordinary ring.
On error already-buffered later blocks may execute. Stop/reset is attempted but physical stop
remains unverified. EEPROM-affecting settings are never windowed.

Sources (facts only, no GPL code copied):
- https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface
- https://github.com/gnea/grbl/blob/master/grbl/serial.h
- https://github.com/gnea/grbl/blob/master/grbl/serial.c
- https://github.com/gnea/grbl/blob/master/grbl/report.c
- https://github.com/gnea/grbl/blob/master/grbl/planner.h

Decision: explicit enum default SEND_RESPONSE; optional CHARACTER_COUNTING starts add serialized
$I, exact VER/OPT validation, max128 budget. FIFO indices/bytes/deadlines live in concrete
JobStream. Each write retains existing JobControl guards and host _send_job priority handoff.
Reserve before send; rollback only proven priority refusal. Uncertain transport fails no retry.
Hold drains pending ACKs without refill; resume extends every deadline. All pending drained
before final M5/M9 and modal/Idle/endpoint. Fake uses pending decoded motion plus bounded raw
source FIFO so later blocks cannot overtake stalled planner parsing.
