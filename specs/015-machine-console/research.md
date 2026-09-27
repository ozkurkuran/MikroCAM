# Research and decisions
The existing `MachineWorker` creates and owns exactly one `MachineController` and `Transport`.
`Controller.tick` owns reads, framing, polling, and all ordinary ACK attribution. Current DEBUG
logging records TX attempts before delivery is known; it is neither an operator console nor a
bounded structured history.

Evo `ToolLevelling` has custom serial command helpers (around lines 1831–1885 and 3084–3099), coupled
to legacy probing and control. Reusing that separate reader would violate ownership and could not
safely share ACKs. Reuse the existing Machine dock/worker and add typed read-only queries plus a
concrete ring buffer.

Standard GRBL query responses share untagged `ok`/`error` replies with job and manual commands, so
even a read query must not overlap them. A late reply after timeout cannot be assigned safely to a
new command. Status `?` is out-of-band and should use the current polling scheduler, not a duplicate
request stream. Because GRBL status replies have no request IDs, a status-poll timeout makes later
replies ambiguous; disable diagnostic console queries until an explicit reconnect restores
attribution.

`$I` is the only additional exact wire permission. Other diagnostic choices already have bounded
manual grammar. Log raw read chunks and escape them for display without interpreting control
characters. Partial or failed TX is uncertain; do not invent a byte-delivery count or retry.
Primary protocol references (facts only; no source copied):
- https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md
- https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md
