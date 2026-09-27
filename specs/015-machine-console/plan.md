# Implementation Plan: bounded read-only console
Branch: 015-machine-console. Date: 2026-09-27. Two stories and 28 tasks. Earlier slices must merge
before delivery.

Use Python 3.13 and the existing Qt/serial pins. Add no runtime dependency or persistent format.
Add `machine/console_models.py`, `wire_log.py`, and `console_control.py`; make narrow
controller/model/manual/Fake integrations; and add `ui/console_controls.py` to the existing Machine
panel/worker. Root owns query/ACK integration. Sol may own immutable log/models or the thin UI. Luna
audits protocol facts. Each file has one owner.

## Constitution Check
| Gate | Result |
| --- | --- |
| I layers | Yes: standard-library/domain models and log, Qt only in UI, existing serial bridge |
| II legacy | Yes: existing Machine dock, no legacy feature hook |
| III simplicity | Yes: concrete ring and finite queries, one real/Fake owner |
| IV truth | Yes: raw evidence is distinguished from machine state and delivery |
| V tests first | Yes: bounds/query/fault tests precede implementation |
| VI safety | Yes: read-only set, no ACK overlap, quarantine, existing priority stop |
| VII license | Yes: protocol facts and existing MIT assessment, no code copied |
| VIII slicing | Yes: two stories/28 tasks, modules <=600 lines/functions <=80 lines, public hints |

No complexity exception. Validate exact bytes and partial outcomes, both retention bounds, strict
query admission and late ACK handling, status scheduling, and final log preservation. Then validate
Qt, the full suite/import/growth checks, the actual desktop, and final-head Windows CI. Make no
physical-delivery claim.
