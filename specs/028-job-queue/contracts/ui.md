# Queue UI and owner contract

Existing prepared candidate has Add to queue. It seals reviewed bytes/setup/name/hash into
the ordered list without I/O; subsequent candidate changes never mutate added snapshots.
Move up/down, remove and clear operate only when not active. Rows show identity/source,
state/progress and diagnostic. Duplicate source rows remain independently identifiable.
Start requires an explicit checkbox confirming all jobs can run on the same setup without
tool/fixture intervention, with wording that following jobs advance automatically.
MachineWorker accepts one typed StartQueueRequest; priority Stop/abort/disconnect wins before
admission. Existing job Hold/Resume/Stop manage the active queue; a paused boundary also holds.
Every queued job repeats live admission/preflight evidence. No new worker, transport or raw
G-code shortcut. Closing preserves terminal outcomes, joins the owner and never auto reconnects.
