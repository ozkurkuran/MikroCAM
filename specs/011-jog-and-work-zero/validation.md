# Validation: Bounded jog and G54 work zero

Status: specified/planned; implementation not started. No physical hardware claim.
Three stories /33 tasks; all10 specification checklist items reviewed and complete.
No extension hooks are installed. Existing dependencies and layer boundaries remain unchanged.

## Analysis and coverage
| Requirement | Planned evidence |
| --- | --- |
| FR-001/003, SC-001 | protocol/controller jog tests, exact presets/commands and causal endpoint |
| FR-002/004 | all-state gates, startup proof, output-off ACK/modal/fresh-status preparation |
| FR-005 | one transaction, post-batch scheduling, duplicate/late ACK and no replay |
| FR-006/007, SC-002 | selectG54/zero tests, full before/after parameter evidence and work coordinates |
| FR-008/009, SC-003/004 | every-phase cancel/abort/disconnect faults and worker priority/closure |
| FR-010/011 | typed intent-slot tests, singleton/session ownership and previous read-only suite |
| FR-012, SC-005 | full suite, architecture/growth/size, ten Qt cycles and actual desktop fake flow |

The eight constitution gates in plan.md have no planned exception. No application-side
persistent format or new dependency is introduced. Output-on commands cannot pass the shared
strict TX grammar. Startup blocks are inspected only; nonempty/unverified records block manual
actions. Stop fallback explicitly distinguishes verified-empty-startup reset from safety-door
with possible configured parking. Neither claims physical stop on a broken link.

Luna review confirmed standardGRBL G10L20 G92/TLO composition and `$13`-affected parameter units.
It identified the material reset/startup-macro hazard, now addressed in spec/plan/contracts.
Root also verified accessory state can be absent/intermittent, so it is not used as output-off
proof. Tests must demonstrate these outcomes before feature completion.

## Implementation evidence
Pending. Record red/green cases, commands, actual counts/head, desktop/CI and delivery links.
