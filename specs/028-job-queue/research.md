# Queue research

Decision: reuse JobControl for each sealed entry, with one QueueControl owner reservation.
Rationale: existing JobControl proves startup/settings/initial frame and final outputs/Idle;
a second sender would duplicate safety gates. Rejected: UI-only next-Start loop (gap races),
new transport/worker, or deleting existing single-job paths.

Decision: queued entries are immutable snapshots sealed explicitly on Add. The single
PreflightPanel._execution_binding / MachinePanel._refresh_binding tracks only the current
candidate and cannot be retained on every entry. Keep live candidate invalidation intact.

Decision: require reviewed initial/final coordinate continuity. Existing source guards and
final endpoint proof reject incompatible jobs. Never synthesize travel or alter reviewed bytes.

Decision: keep authorization across verified final completion, pause/priority inter-job gaps,
and clear it on every fault/Stop/disconnect/reset. Preserve results without auto recovery.

Read-only research agent: /root/queue_research. Sources: JobControl.start/_command/_status_progress/
_end, MachineController.tick/_reset_session/_fail, MachineWorker.submit/_process_intent/_publish,
MachinePanel._refresh_binding, PreflightPanel._execution_binding and existing job test fixtures.
No external code or new dependencies required. No physical device was accessed.
