# Validation: Read-only GRBL connection

Status: planning; implementation and delivery evidence pending. No physical hardware claim.

## Pre-implementation analysis
Three independently testable stories / 28 tasks. No unresolved placeholder or new dependency.
Domain remains Qt/pyserial-free; serial is a bridge leaf. No runtime code has been added yet.
Read-only disconnect closes communications; it does not claim to stop externally initiated
motion. Constitution VI active-motion fail-safe obligations apply when active control is added.

| Requirements | Planned tasks / evidence |
| --- | --- |
| FR-001, FR-002 | T004, T007, T010-T012: explicit lifecycle and mocked physical serial |
| FR-003, FR-008 | T013-T017: strict parsing, unknown/invalid state and diagnostics |
| FR-004, FR-005 | T004, T008-T009, T012: exact TX, bounded framing/outstanding requests |
| FR-006, FR-007 | T013-T017: analytic units/offsets and evidence invalidation |
| FR-009, FR-010 | T018-T023: thin panel, one owner, repeated stop/join and stale sessions |
| FR-011, FR-012 | T012, T023-T026: bounded diagnostics, boundaries/full suite/desktop |
| SC-001 | T012, T022: all Fake writes subset of the two read requests |
| SC-002 | T017: analytic mm/inch positions within 1e-9 mm |
| SC-003 | T012, T022: deterministic stale deadline and real worker close timing |
| SC-004 | T022-T023: ten sessions and desktop CAM smoke |
| SC-005 | T025, T027: local full suite and hosted Windows CI |

All eight constitution gates are addressed in plan.md. Implementation review must recheck:
1. Layer direction and hardware-free domain.
2. Legacy menu/shutdown hook only; aggregate growth <=50.
3. Exactly two concrete transports; no new dependency or registry.
4. One mm conversion boundary and no persistence/placement duplication.
5. Tests before domain behavior and hardware-independent simulation.
6. Read-only allowlist, explicit states, disconnect from every state and hazard disclosure.
7. Independent protocol implementation; no third-party source copied.
8. Three stories, 28 tasks.

## Execution evidence
Pending. Record failures before fixes, passing commands, runtime/head, remaining limitations,
real desktop result and hosted CI before marking the feature complete.
