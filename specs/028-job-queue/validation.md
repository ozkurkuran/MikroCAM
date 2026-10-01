# C2 draft dependency validation

2026-10-02. This is a specification draft, not an implemented job queue.

- Spec Kit allocated 028 automatically after 027. The requirements checklist is 13/16;
  FR-006 still needs the operator's automatic-advance versus per-job Start/Next decision.
  No plan/tasks/runtime queue implementation was generated while that answer is pending.
- The draft branch now includes exact B1 head 730d4bdef4dc07b1c490e0836ab93ad7cda8be57 and
  exact C1 head c549c0feb2dbbb9778f5e9faec43c8de55d0addc via merges, without duplicating
  or rewriting their implementations. Their independent Windows CI runs passed.
- Combined fault-matrix, handoff, job-control/adversarial and manual-control/stop tests:
  252 passed, 3 existing warnings in 17.60 seconds, using the shared CPython 3.13 environment.
  No physical port was opened. No new queue behavior or movement policy was added.
- Whitespace checks passed. Combined final-head Windows CI is required and recorded on
  draft PR #32. The PR includes the C1 prerequisite until PR #31 is merged into its base.
- ROADMAP/main and the untracked MACHINE_CONTROL_ROADMAP remain unchanged.

Implementation readiness remains unproven until FR-006 is resolved through the pending
clarification, then Spec Kit plan/tasks/analyze/implement are completed. H3 requires physical
operator evidence; C3 and D retain their explicit trigger conditions.
