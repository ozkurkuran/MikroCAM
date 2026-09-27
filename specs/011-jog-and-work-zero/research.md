# Research: Bounded jog and G54 work zero

## Decisions
- **Finite jog**: fixed small step/feed choices, explicit mm/incremental jog commands and one
  owned operation. Continuous/key-repeat jogging and a generic command queue were rejected:
  the positioning need is met without accumulating motion.
- **Output-off preparation**: command M5/M9, require ACK and successful modal read-back before
  a fresh Idle gate. An absent accessory field cannot prove outputs inactive because that
  field is intermittent/optional. No emission-start command is added.
- **Verified persistent zero**: explicitly select G54, read its existing offsets plus G92/TLO,
  write only chosen zero axes once, and verify read-back/fresh work position. No silent
  coordinate-system switch, temporary-offset clearing or automatic EEPROM write retry.
- **ACK discipline**: one ordinary transaction; advance phases after the received batch.
  Status verification requires a query issued after the triggering action ACK. A late or
  ambiguous response locks further manual operations until explicit reconnect.
- **Stop**: dedicated jog cancel0x85, bounded verification and abort0x18 fallback. Feed hold
  alone was rejected because it does not turn spindle/coolant off and may race into a hold
  after a completed jog. Abort is an explicit safety operation and can lose position.
- **Startup hazard review**: reset can execute stored `$N` programs. Require two empty,
  uniquely reported startup rows and ACK before a manual action. No startup write is allowed.
  Without current empty-startup proof, generic Abort uses safety-door0x84 and reports unverified
  stop/possible configured parking. Do not infer no-parking from absent/ambiguous build flags.
  A port-induced reset can run startup code before inspection, so Connect's caveat includes it.
- **Architecture**: extend the010 controller/worker with one typed intent slot and a concrete
  manual-operation helper, keeping Qt/serial imports at existing boundaries. No dependency,
  generic event bus, registry, profile or application persistence is introduced.

## Official protocol evidence (checked 2026-09-27)
- [GRBL jogging](https://github.com/gnea/grbl/blob/master/doc/markdown/jogging.md): typed
  incremental/unit overrides, ACK versus motion completion and dedicated cancel semantics.
- [GRBL interface](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md):
  send-response sequencing, asynchronous status, modal/parameter reports and intermittent
  accessory evidence. Polling remains4Hz, below the documented recommendation.
- [GRBL commands](https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md):
  G54/G10 parameter changes, read-back commands, realtime cancel and reset behavior.
- [GRBL settings](https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md):
  report-unit setting and controller settings; no setting assignment is needed for this slice.

These are protocol facts for an independent implementation, not copied application code.
No FlatCAM-Plus source is accessed. The existing pyserial/PyQt6 dependencies/notices suffice.

## Existing integration
010 provides immutable mm snapshots, strict framing, explicit connect, fake clock/transport,
250ms poll/2s freshness, exact serial bounds and Qt worker/panel ownership. Reuse its appMain
menu and AppLifecycle shutdown hook. New tests exercise the previous read-only behavior as
well as manual actions; connect/refresh must retain their original absence of action writes.

## Physical limits
Application step/feed caps do not prove travel/fixture clearance. GRBL acknowledges controller
commands, not measured physical output power or calibration. Cancellation decelerates; reset
may lose position. A broken link cannot carry a stop byte. The UI must keep uncertainty visible
and leave physical E-stop/interlocks to the machine. No real port is opened during development.
