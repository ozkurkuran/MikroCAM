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
One new UI module50 lines; longest function29 lines; legacy net growth10 lines. Existing
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
