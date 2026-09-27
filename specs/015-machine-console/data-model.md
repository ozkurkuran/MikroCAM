# Data model
`ConsoleRequest` contains one exact supported query. `ConsoleObservation` separates its lifecycle
from reported machine state. `ConsoleControl` holds one request, ACK ownership, a deadline,
provisional unit evidence, and a scheduled completion. It does not accumulate response text; raw
data lives only in the bounded wire log. Taint blocks ordinary admission until the next explicit
connection.

`WireRecord` preserves requested or received bytes with an honest write outcome. `WireSnapshot`
shares immutable records; `WireLog` bounds entry and payload retention and tracks omitted data.
`MachineSnapshot` embeds both console and wire observations. Disconnect keeps final observations;
connect resets them.

There is no persistence schema, alternate transport, raw-command framework, or response-to-motion
conversion.
