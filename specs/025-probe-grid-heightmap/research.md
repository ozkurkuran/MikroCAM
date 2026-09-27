# Research decisions

Existing MachineController.tick owns bounded reads and shared LineFramer; MachineWorker admits
one typed intent. Extend this path with ProbeControl rather than another worker/serial reader.
Reuse startup/modal/parameter parsers, fresh status query watermarks and existing tainted-session
policy. A normal job cannot collect correlated probe results, so merely streaming generated
G-code would not establish measured heights or safe partial outcomes.

Use G54 work-mm grid positions and store the bound G54 offset. Probe reports carry machine
coordinates, converted using verified report units and then subtracting the reviewed offset.
The map remains a rectangular work-coordinate field;026 will use the shared Placement to query
this field. No second geometric transform is introduced here.

GRBL primary documentation consulted2026-09-27:
- https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface
- https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands

Responses and push reports are separate. An acknowledgement alone does not prove a completed
motion. Probe acquisition therefore retains a successful PRB result and waits for fresh Idle
endpoint evidence; one ordinary transaction owns the acknowledgement. No source code copied.
Author Fake behavior independently, with explicit plane and fault injection; real hardware is
outside the available validation environment. No dependency or license addition required.

Persist a small strict schema1 JSON map with optional missing heights instead of a new project
format or database. Complete is an explicit operation outcome, requiring final retract evidence;
having all sampled values after a failed retract does not manufacture a successful operation.
