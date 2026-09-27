# Data model: Bounded jog and G54 work zero

All public values are frozen dataclasses/enums with bounded strings and finite numbers.
No transport, Qt object, mutable dict or live worker crosses a snapshot.

## Typed intents
- `JogRequest(axis: str, distance_mm: float, feed_mm_min: float)` accepts uppercase X/Y/Z,
  signed distance from +/-0.1, +/-1 or +/-10 mm and feed100/300/600 mm/min. Reject booleans,
  nonfinite values and every unsupported value at construction/encoding. One intent is one move.
- `ZeroRequest(axes: tuple[str, ...])` accepts exactly ('X','Y'), ('Z',) or ('X','Y','Z').
  Unselected axes must remain unchanged; no free-form command or coordinate input.
- `SelectG54Request` is an explicit zero-field intent. It selects a system without zeroing.
- Priority cancel/abort/disconnect signals are distinct from the single pending action slot.

## Operation observation
`ManualPhase`: READY, PREPARING, MOVING, VERIFYING, CANCELLING, COMPLETE, FAILED, ABORTED.
`ManualObservation`: phase, action kind, diagnostic, command eligibility and stop uncertainty.
Published state distinguishes an active manual operation from GRBL's actual reported machine
state. The controller owns a monotonically increasing status-query/report sequence; timestamps
alone cannot distinguish two reports received during the same injected-clock instant.

Existing `MachineSnapshot` retains its fields and adds an immutable manual observation with
safe defaults. Unknown unit/position/state, stale reports, a pending ordinary transaction,
another operation or a tainted session always disables new actions. A completed operation is
not a new physical coordinate authority; DRO still comes from valid reports.

## Modal and parameter evidence
`ModalState`: active work system G54-G59, unit mode G20/G21, distance mode G90/G91, spindle
mode M3/M4/M5 and coolant modes M7/M8 or M9. Query evidence is provisional until its `ok`;
missing/duplicate/conflicting required groups fail the transaction. M5/M9 proves reported
controller modes only, not measured physical power. Unknown/malformed required groups fail.

`ParameterRecord(name, value)`: finite mm XYZ for G54-G59/G92, or finite mm scalar TLO.
Convert `$#` wire values using verified `$13` once at the parser boundary. A completed
parameter query needs all six WCS rows plus G92 and TLO, each exactly once. Extra unrelated
parameter records do not satisfy missing required rows. Preserve before/after immutable
inventories; no cached row from an earlier query fills a missing one.

`StartupRecord(index, block)`: bounded `$N0`/`$N1` query evidence, provisional until ACK.
Nonempty or unverified startup blocks cannot authorize a reset fallback for owned motion.
Exact stop policy is specified in contracts/manual-grbl.md; never silently modify startup data.

## Zero verification
For selected axes, expected new G54 = fresh MPos - G92 - tool-length contribution (Z only).
For omitted axes, expected G54 is the old G54. Require G55-G59/G92/TLO unchanged, then new
fresh WCO and work coordinates: selected work axes0, omitted work axes unchanged. Explicit
0.005mm tolerance covers inch-report quantization; no tolerance widening based on outcomes.
Default GRBL tool-length axis Z is the supported target; nonstandard firmware is outside scope.

## Lifetimes
One settings/ordinary command transaction at a time, with bounded provisional query rows,
ACK deadline and purpose. Only the response belonging to that phase can advance it; a fresh
status verification must use a query issued after the triggering event. Reset, malformed
frames, ambiguous ACK, timeout, disconnect and abort invalidate relevant evidence and queued
intent. No failed motion/persistent action is replayed. A new explicit connection creates a
new session; late GUI snapshots/requests cannot revive the old one.
