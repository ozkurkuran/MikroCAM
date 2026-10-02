# Levelling Machine handoff validation

2026-10-02; base Phase A `c2d6e427314b831f02364a3477d7729cfec2843b` (PR28 remains open).

## Spec Kit sequence and analysis
Specify allocated027; clarify used the user's prior explicit Machine-handoff proposal.
Plan/research/data/UI contract/quickstart and12 tasks were generated with local Spec Kit
scripts. Requirements checklist9/9 passes; analysis found0 critical/high inconsistencies,
8 requirements mapped to12 tasks (100% coverage), no unmapped tasks or new dependencies.
No extensions.yml/hooks exist. The research agent independently enumerated all I/O callbacks.

## Failing-before evidence
20 handoff cases failed before implementation: public connection/search, fourteen GRBL read/
write/scheduled callbacks, offline switch restoration and inert dock reuse. Desktop found a
card parent-disabled by missing CNC eligibility; another regression failed before relocating
the card to the root tool layout. Final feature group21 passes. Related Levelling group144
passed plus41 subtests before the added parent-disabled case; original tool/journey tests
were unchanged. Phase A's mock connection test now targets the retained private implementation;
no runtime test bypass flag was added. Other Phase A wire contracts remain protected.

## Implementation and invariants
Metadata enumeration uses existing bridge list_ports and never opens devices. Public Connect
always refuses. GRBL callbacks reject before serial/UI/worker side effects, including injected
stale handles and low-level helper calls. Legacy source is retained behind guards/private
helpers. Machine's dock/owner is reused explicitly, without auto-connect/probe/transfer/start.
Offline controller export/edit/import controls restore across repeated switches.
One new UI module50 lines; longest function26 lines; legacy net growth10 lines. Existing
architecture/growth rules pass. No external implementation was copied; Evo attribution recorded.

## Final local evidence
- Full shared CPython3.13 suite:5168 passed,2 existing Qt-context skips,11 existing warnings,
  310 subtests passed in305.25s; `.venv/handoff-full.log`, exit0. Architecture checks included,
  growth baseline is Phase A head.
- Actual desktop:exit0 `.venv/handoff-desktop.log`; controller switching/reset/direct blocked
  connection, visible card and reused inert Machine dock pass while physical serial constructors
  are patched to raise. Entire existing CAM/probe/job/console/autolevel journeys also pass;
  RENDER_OK and SHUTDOWN_OK emitted.
- Visually inspected `.venv/levelling-machine-handoff.png`: visible Levelling tab, GRBL selection,
  explanation and Open Machine button together with the disconnected Machine dock. Separate
  `.venv/levelling-handoff-card.png` text/button are readable. No physical device was connected.
- Final-head Windows CI is required and its result is recorded in the PR after this commit.
- Delivery is a stacked PR on Phase A. ROADMAP delivery status is unchanged before merge.

## Final CI smoke race correction
The first final-head Windows run (36927765821) passed 5167 cases but failed the existing
probe desktop helper's offline wire-invariance assertion. Its owner was still polling while
save/load performed disk I/O. Injecting a 700 ms save delay reproduced the same failure
locally before the correction. The helper now disconnects and joins the owner before the
offline save/load assertion, preserving the exact no-write assertion without filtering bytes.
The same injected-delay case then passed. No production machine behavior changed.
The related Levelling/probe groups passed: 153 tests and 41 subtests in 19.16s.
Final-head Windows CI is rerun and its result recorded in the PR.

## Recorded original final CI and delivery review
Original final head `730d4bdef4dc07b1c490e0836ab93ad7cda8be57` passed Windows validation:
https://github.com/ozkurkuran/MikroCAM/actions/runs/36929106301 (5168 passed, 2 skipped,
310 subtests). This is historical evidence for that exact head, not for subsequent changes.
The 2026-10-02 delivery review reproduced stale/direct GRBL calls under all three offline
selections. Runtime guards now reject unconditionally; mock-only retained wire tests use
explicit wrapped-body access. All existing offline Levelling journeys remain covered.
Final integration results belong to central `docs/IS_TAKIP.md` and the delivery PR.

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
