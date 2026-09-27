# Validation: G-code preflight
Status: specified/planned; implementation not started. Three stories/37 tasks.
Spec checklist10/10 reviewed. No extension hooks installed. All eight constitution gates pass
pre/post design; no dependency, persistent schema or external source port is planned.

Coverage map: FR001/source bridge;002/parser;003/motion/Placement;004/setup;005/hazards;
006/report counters;007/timing;008/worker cancellation;009/stale input;010/resource/performance;
011/full suite/desktop. SC001 analytic fixtures,002 forbidden/hazard fixtures,003 read-only/stale,
004 measured performance/cancel,005 complete Windows/desktop evidence.

Initial modal assumptions are explicit: G94 only, fixed declared G54, no inherited G92/TLO.
Luna verified unit/feed and arc/compensation behavior against official GRBL protocol/source facts.
No actual machine is involved; output-start in source is metadata, not execution permission.

Implementation, red/green evidence, actual performance, final-head CI and delivery: pending.
