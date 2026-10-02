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

## Integrated delivery, 2026-10-02

Delivered to `main` through [PR #34](https://github.com/ozkurkuran/MikroCAM/pull/34),
merge `d173f5fde47008f04de824ea26b6903896a69f16`. PRs #28–#33 are also confirmed merged;
their original commit histories are preserved. Earlier pending/open statements above are historical.

Exact tested source head `405da9519c8ebd3bc73c38517e818eae4c56e53b`:
- Complete local CPython 3.13 suite: 5487 passed, 3 skipped, 11 existing warnings,
  310 subtests, 595.42 s; `.venv/grbl-delivery-full.log`.
- [Windows CI PASS](https://github.com/ozkurkuran/MikroCAM/actions/runs/36989955432):
  same 5487 tests and 310 subtests, 306.13 s.
- Native Qt/OpenGL desktop smoke exit 0; character-counting queue completes three jobs,
  Stop prevents the next source, new MikroCAM logo/About renders and shutdown passes.
  Queue and About screenshots visually inspected; `.venv/grbl-delivery-desktop.log`.

Three skips are the operator-only hardware inventory and two existing full-Qt-context tests.
No physical device was connected. H3 remains open; FluidNC/grblHAL/TCP/SD remain deferred.
The final main documentation head requires its own CI; its exact status is recorded in
central `docs/IS_TAKIP.md`, without transferring this source-head PASS to a newer commit.
