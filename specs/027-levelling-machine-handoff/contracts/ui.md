# UI contract

Selecting GRBL does not enumerate/open ports. Legacy serial frame is hidden and disabled.
A localized notice names Machine, probe grid, auto-level and sending; button opens/reuses
Machine without implicit connection/transfer. Switching to each offline controller restores
probe export/edit/import. Reset/reopen repeats the same policy.
Public Connect cannot open any controller port. Static search uses OS metadata only.
GRBL callbacks reject before reads/writes/wake/reset or worker scheduling, including injected
stale handles. The existing Machine owner is never closed or replaced by handoff.
