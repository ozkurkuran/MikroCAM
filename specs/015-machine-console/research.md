# Research and decisions
Existing MachineWorker creates and owns exactly one MachineController/Transport. Controller tick
owns reads/framing/polling and all ordinary ACK attribution. Current DEBUG logging prints attempted
TX before knowing delivery; it is not an operator console or bounded structured history.
Evo ToolLevelling has custom serial command helpers (around1831-1885 and3084-3099), coupled to legacy
probing/control. Reusing that separate reader would violate ownership and cannot safely share ACKs.
Reuse the existing Machine dock/worker and add typed read-only queries plus a concrete ring buffer.
Standard GRBL query responses share untagged ok/error replies with job/manual commands; even a read
query must not overlap them. Late replies after timeout cannot be assigned safely to new commands.
? is out-of-band status and should use the current polling scheduler, not a duplicate request stream.
$I is the only additional exact wire permission. Other diagnostic choices already have bounded
manual grammar. Data is logged as raw read chunks, escaped for display, without interpreting control
characters. Partial/error TX is uncertain; no fabricated byte-delivery count or automatic replay.
Primary protocol references (facts only, no source copied):
- https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md
- https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md