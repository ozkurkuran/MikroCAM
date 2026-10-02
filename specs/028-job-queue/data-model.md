# Queue data model

QueueEntry: independent bounded ID and immutable PreparedJob snapshot; source name/digest
and reviewed setup are shown before approval. QueueDraft: at most 32 ordered entries, add,
move, remove and clear by validated ID; no I/O. Duplicate sources keep independent IDs.
StartQueueRequest: nonempty tuple of unique entries and explicit whole-queue mechanical approval.
QueueObservation: ordered entry outcomes, one active ID, phase, diagnostic and control flags.
Each result holds original identity and JobObservation progress/terminal state.
Queue phases: ready → running → paused/complete/failed/aborted. A paused boundary may explicitly
resume; failed/aborted/complete never auto-restart. New execution requires explicit approval,
and rerun of terminal work requires explicit new addition. Reconnect retains visible outcomes.
All models use exact types, bounded text/IDs/counts and frozen dataclasses. No Qt imports.
