# Data model
StreamingMode enum SEND_RESPONSE / CHARACTER_COUNTING; StartJobRequest and StartQueueRequest
carry exact enum with default SEND_RESPONSE. UI selection alone does no I/O.
PendingBlock immutable index, byte_count, deadline. JobStream owns deque, next_index, capacity;
reserve sequential exact canonical bytes if fit, cancel only latest proven-unsent reservation,
ack pops head, expiration checks earliest, extension shifts every pending deadline.
Queue propagates one chosen mode to each job; every job rediscovers capability.
Terminal faults clear authorization and window, retaining accepted source progress/diagnostic.
