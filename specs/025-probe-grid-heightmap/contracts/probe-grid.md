# Probe grid contracts

Review constructs a validated core ProbePlan from explicit controls plus current live snapshot.
StartProbeGridRequest reserves one existing worker slot; controller rechecks all live bindings.
Manual/job/console and probe admission are mutually exclusive, including pending/tainted states.

Preparation: empty startup inventory, mechanical settings/report units, M5/M9 acknowledgement,
modal G54/output-off, complete coordinate inventory with G92/TLO zero, fresh initial Idle binding.
Each ordinary command receives exactly one ACK. Movement waits for a query issued after ACK
and matching fresh Idle position before advancing. Vertical G38.2 additionally requires one
successful PRB record received before its ACK, bounded XY/Z and machine/work offset agreement.
Position tolerance.005mm (existing controller reporting tolerance). Returned heights are work Z.

Sequence: upward Z to safe plane; XY to grid point; G38.2 to minimum Z; safe retract; next XY.
Only successful PRB+ACK+Idle commits a sample. Final safe retract establishes COMPLETE.
Any malformed/extra/stale evidence stops the operation, keeps data and taints session. Stop,
abort and disconnect use the existing priority owner path, best-effort reset only after verified
empty startup blocks, otherwise safety-door semantics with parking caveat. No restart/resume.

No unbounded strings or arbitrary G-code interface: separate validated write_probe transport
boundary implemented by real SerialIO and Fake, called only by controller. Trace records use
the existing bounded TX/RX log. ProbeMap save/load never touches transport or starts acquisition.
