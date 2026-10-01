# C1 validation

2026-10-02; baseline main `8680a09d`.

Existing failure tests were inspected before adding cases. The matrix records source test
names and scenario parameters for ten scenarios across seven transaction owners. Function
references were checked against AST definitions; parameter values were reviewed against the
existing parametrizations. Inapplicable cells have ownership-based explanations.

The first deadline group demonstrated three failures: jog, work zero and job accepted late
ACKs when fresh status reports prevented the separate status timeout. Fifteen cases already
passed. Two small consume guards now enforce the existing ACK deadline before processing
late evidence. The existing verified-hold deadline extension is preserved.

83 added parametrized cases cover only audited gaps. No automatic reconnect, replay, restart
or new controller behavior was introduced. All transport tests use FakeGRBL, including
injected SerialException. No physical port was opened.

Validation:
- Related controller/manual/job groups: 208 passed after the deadline fix.
- Full CPython 3.13 suite: 5183 passed, 2 existing Qt-context skips, 11 existing warnings,
  310 subtests passed in 288.97 seconds; `.venv/fault-matrix-full.log`, exit 0.
- Architecture checks included in the full suite; git diff whitespace check passed.
- Final-head Windows CI is required; the result is recorded on the separate C1 PR.

Physical validation remains open under phase H. ROADMAP delivery status remains unchanged
until merge.
