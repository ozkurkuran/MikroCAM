# Implementation Plan: bounded read-only console
Branch015-machine-console,2026-09-27. Two stories,28 tasks. Earlier slices merge before delivery.
Python3.13 and existing Qt/serial pins. No new runtime dependency or persistent format.
Add machine/console_models.py,wire_log.py,console_control.py, narrow controller/model/manual/Fake
integration and ui/console_controls.py in the existing Machine panel/worker. Root owns query/ACK
integration; Sol may own immutable log/models or thin UI; Luna audits protocol facts. One file owner.

## Constitution Check
| Gate | Result |
| --- | --- |
| I layers | Yes: stdlib/domain models/log, Qt only in UI, existing bridge serial |
| II legacy | Yes: existing Machine dock, no legacy feature hook |
| III simplicity | Yes: concrete ring and finite queries, one real/Fake owner |
| IV truth | Yes: raw evidence distinguished from machine state and delivery |
| V tests first | Yes: bounds/query/fault tests precede implementation |
| VI safety | Yes: read-only set, no ACK overlap, quarantine, existing priority stop |
| VII license | Yes: protocol facts and existing MIT assessment, no code copied |
| VIII slicing | Yes: two stories/28 tasks, modules<=600/functions<=80/public hints |

No complexity exception. Validate exact bytes/partial outcomes, both retention bounds, strict query
admission/late ACK, status scheduling and final log preservation. Then Qt, full suite/import/growth,
actual desktop and final-head Windows CI. No physical delivery claim.