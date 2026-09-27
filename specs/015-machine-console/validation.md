# Validation: read-only console and wire diagnostics

Status: implementation, full local suite and actual desktop passed; final-head Windows CI and merge pending.
Two stories, 28 tasks. No new dependency or legacy host hook.

## Requirements and constitution
FR001–004: the sole Controller boundary records requested TX only after its result and raw RX before
framing. Exact integer byte counts mean complete; short/invalid counts and exceptions remain uncertain.
The immutable ring retains at most 512 records, 256 KiB payload and 4096 bytes per record, with exact
omission/eviction counters. Disconnect and even nested owner/close failures retain final evidence.
FR005–010: six exact typed queries, single ACK owner, fresh verified Idle admission, full-batch
completion, 3-second deadline, matching unique $13 and explicit quarantine. Status ? uses existing
polling; a poll timeout disables diagnostic queries until reconnect because replies lack IDs.
Priority intent cancels before writing and leaves a terminal query outcome. UI uses the existing
worker, escapes bytes in plain text, offers only finite choices and hides old rows locally on Clear.
FR011 and all five SCs are covered by the focused/full/desktop checks below.

All eight gates pass: domain/core boundaries, zero legacy growth, concrete ring/query coordinator,
existing coordinate authority, tests before behavior, bounded fault/priority paths, independent
implementation/no copied external code, and two stories/28 tasks. No dependency or complexity
exception. Largest changed module is 414 lines; largest function is 55 lines (limits 600/80).

## Tests first and audit fixes
Initial tests failed on missing model/log modules. Root and Sol then added regressions before fixes
for nonprintable query records, duplicate/missing/changed units, stale status attribution, immediate
eligibility closure, priority cancellation before admission, and final worker/close evidence loss.
Luna identified status-poll attribution ambiguity and independently reviewed ownership and scope.

157 new focused tests passed in 5.74 seconds:
- 60 immutable model/ring tests: strict types, limits, omission counting, eviction and reset snapshots.
- 36 query/control tests: six commands, concurrency, full-batch ACK, units, deadline, priority and logs.
- 38 adversarial tests: 13 job boundaries, manual phases, partial/invalid/error writes, invalid/oversized
  reads, worker intent cancellation and retained evidence through generic owner/final close failures.
- 23 Qt tests: finite choices, escaped bytes, Clear/reconnect, pending/rejected intents, final evidence
  and all six queries over ten actual QThread/Fake sessions.

Full suite at `0776ace9b291fd9e76ee3039e52dddb13a3259dc`:
`python -m pytest -q --junitxml=.venv/console-pytest.xml`
**2721 passed, 2 skipped, 11 warnings, 310 subtests in 227.35 seconds.**
Architecture/import/growth checks are included. Ignored local evidence: .venv/console-pytest.log/.xml.
The two upstream empty Qt drafts and existing SWIG/Shapely warnings remain unchanged.

## Actual desktop
At the same runtime head, `python tests/smoke_app.py` exited 0. The visible MikroCAM desktop queried
?, $$, $G, $#, $N and $I through the existing Machine worker. HTML/ESC/NUL bytes stayed escaped;
Clear hid older records without clearing the owner; later records appeared. Disconnect during an
unacknowledged $I retained FAILED identity/log and closed FakeGRBL without an invented motion command.
Markers: CONSOLE_READ_ONLY_CLEAR_OK; CONSOLE_DISCONNECT_EVIDENCE_OK. All prior CAM/project/laser,
manual, preflight, streaming and dry-run journeys passed in the same run, including
JOB_ACTIVE_SHUTDOWN_OK; PREFLIGHT_SHUTDOWN_OK; MACHINE_SHUTDOWN_OK; SHUTDOWN_OK.
Root inspected the 3840x2089 .venv/console-smoke.png: collapsed-section toggle, finite query controls,
completion result and plain wire entries are visible in the Machine dock. Local log: .venv/console-smoke.log.
Existing editor/QThreadStorage warnings and the already-closing arg-thread pipe (WinError 232) were
followed by successful owned shutdown markers.

## Limits and delivery
[Operator guide](../../docs/MACHINE_CONSOLE.md), [contract](contracts/console.md).
No physical controller was exercised. TX complete means the transport accepted bytes, not controller
acceptance or physical execution. This bounded local view is not a complete retained transcript and
has no export/persistence. Untagged delayed replies cannot prove causal ownership after timeout.
PR, final-head CI and merge links will be added as delivery completes.
