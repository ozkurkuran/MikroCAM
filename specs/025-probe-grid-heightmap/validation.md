# Validation: probe grid and height map

## Requirements and constitution

| Requirements | Evidence |
| --- | --- |
| FR001–003 | Strict Grid/Plan bounds, full route envelope, upward-first Z, live binding and edited-review UI tests |
| FR004–005 | Sole owner/factory/transport thread; typed intent; mechanical/setup gates; correlated PRB+ACK+fresh Idle, final retract |
| FR006–007 | Fault matrix, priority stop/close, late response deadline and unsolicited evidence quarantine; incomplete prefix retained |
| FR008–009 | Strict1MiB schema1 codec, atomic replacement/failure cleanup; numeric/heat-map view, offline historical-map retention |
| FR010 | Analytic mm/inch/G54-offset Fake, failure/worker/serial boundary and complete desktop below |

SC001–003 use independent analytic heights, final safe coordinates and exact complete/incomplete
persistence. SC004–005 require desktop/full/CI below. All eight constitution gates remain YES;
no new dependency, copied source, generic framework, new project format or legacy feature logic.
Probe wire commands have a distinct validated boundary on the existing real/Fake transports.
Largest modified production module472lines; all functions<=80lines at implementation audit.

## Test-first and audit evidence

Core/codec/files initially failed with missing modules, then120tests passed. The additional
incomplete outcome and strict codec cases brought this group to131tests. Protocol initially
failed missing-module collection; controller18cases failed missing request_probe before its
implementation. Worker tests initially rejected the new typed request. Production implementation
then passed799 combined probe and prior-machine tests in27.21s before final audit additions.

Meaningful red regressions preceded fixes for large integer validation, late ACK bypassing an
expired deadline, idle unsolicited PRB admission, and unchanged live results overwriting a loaded
historical map. Cached PRB from legitimate parameter queries remains separate and harmless.
Partial maps now carry incomplete until a terminal outcome; all measurements alone do not prove
the final retract succeeded. Luna independently audited protocol/controller/Fake and found no
remaining concrete safety blocker after the deadline fix; defensive idle quarantine was also added.

Final focused results, exact runtime head, full suite, desktop and CI/merge follow below.
