# Karakter sayımlı GRBL doğrulaması
2026-10-02; test-first spec/plan/tasks/analyze gates PASS; no physical port.

- FIFO absent-module red →18 green; real GRBL build-date/OPT flags2 red →green.
- Coordinator19 red/1 default pass →green; mode UI/queue3 red →green.
- 50 feature checks pass: byte budgets/FIFO, capacity rejection, partial/coalesced ACK,
  source attribution, fresh-status late ACK, hold across deadline, per-handoff priority,
  default send-response, >15-motion bounded raw RX/planner, final modal/Idle gate,
  queue per-job rediscovery, faults/reconnect and4 uncertain-write cases.
- Related job/queue/UI/worker/architecture group317 passed in77.95 s before the final
  queue review regressions and4 extra uncertainty checks; those targeted checks also passed.
- Full CPython3.13 suite on merged badf760e:5394 passed,2 skipped,11 existing warnings,
  310 subtests,250.05 s. The4 subsequently appended uncertainty tests passed separately;
  final-head Windows CI collects them with the whole suite.
- Actual Qt/OpenGL smoke_app exit0: CHAR_COUNTING_QUEUE_COMPLETE_OK,
  QUEUE_THREE_COMPLETE_OK, QUEUE_STOP_REMAINDER_NOT_SENT_OK and all existing journeys/
  shutdown markers. .venv/queue-smoke.png visually inspected: mode selector, source IDs,
  accepted counts and verified endpoint/output results visible.
- git diff --check PASS. Size checks: JobControl411 lines/max function43, JobStream69,
  Controller509/max47, MachinePanel457/max60, QueueControls226/max45; no new dependencies.
- Last C2 correction33517547 merged; separate PR based on028-job-queue. Final-head Windows
  CI pending push; result belongs in central docs/IS_TAKIP.md and PR body, not inherited.
- H3 physical GRBL throughput/stopping/compatibility still open. Main/reference/user roadmap
  untouched. FluidNC/grblHAL/TCP/SD deferred. No firmware implementation copied.
