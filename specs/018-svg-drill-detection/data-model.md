# Data model

Authoritative fields, bounds and APIs: [contract](contracts/svg-drills.md).
SvgElement gains an optional resolved white-fill fact with a conservative unknown default.
DrillCandidate is an immutable mm circle tied to an opening and supporting pad.
DrillReview is immutable source identity/flip plus bounded candidates/notices; it is transient.
DrillTool is an immutable grouped diameter and centres; bridge converts at host boundary.

State: empty -> analysed/unselected -> selected -> created. File/flip changes and load failures
return to empty. Cancel destroys transient state. Geometry ambiguity removes candidates and keeps
notices. No new persisted schema: created Excellon uses its existing project serialization.
No mutable shared caches, live workers, source object edits or device state.
