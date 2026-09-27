# Data model
ConsoleRequest contains an exact supported query; ConsoleObservation separates its lifecycle
from reported machine state. ConsoleControl holds one request, ACK ownership, deadline, provisional
unit evidence and a scheduled completion. No response text accumulates there: raw data lives once
in the bounded wire log. Taint blocks ordinary admission until the next explicit connection.
WireRecord preserves requested/received bytes with an honest write outcome. WireSnapshot shares
immutable records; WireLog bounds entry/payload retention and omitted counters. MachineSnapshot
embeds both console and wire observations. Disconnect keeps final observations; connect resets them.
No persistence schema, alternate transport, raw command framework or response-to-motion conversion.