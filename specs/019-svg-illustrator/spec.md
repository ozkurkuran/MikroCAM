# Feature Specification: Illustrator SVG appearance

**Feature Branch**: `019-svg-illustrator`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap19: XMP MaxPageSize, katman ve gizli nesne filtresi, compound path, clipping.

## User Scenarios & Testing

### User Story 1 - Retain page size and visible layers (Priority: P1)
A designer imports Illustrator-style SVG artwork with trustworthy physical page dimensions and
only visible layer content. The report explains any page-size metadata used.
**Why this priority**: Incorrect units or hidden construction artwork corrupt the CAM input.
**Independent Test**: A layered source with page metadata imports at known physical bounds.
**Acceptance Scenarios**:
1. Given complete physical root dimensions, import preserves them and reports conflicting XMP metadata.
2. Given missing dimensions or percentage dimensions without an external viewport, valid unambiguous
   page metadata supplies physical page size; absent/invalid essential evidence produces a useful error.
3. Given visible/hidden groups and supported embedded class styles, only visible content contributes;
   a child may override inherited visibility but cannot override an ancestor's display:none.

### User Story 2 - Preserve compound fill intent (Priority: P2)
The designer imports overlapping and self-crossing compound paths with the source winding rule,
so holes and shared regions have the intended material area.
**Why this priority**: Illustrator compound artwork cannot be represented by treating each ring as solid.
**Independent Test**: Known analytic overlap, opposite-winding, touching and bow-tie fixtures match area/bounds.
**Acceptance Scenarios**:
1. Given equal or opposite winding rings, nonzero and evenodd rules produce their respective expected material.
2. Given shared edges or crossings, valid bounded material is produced without guessing a repair.
3. Given input exceeding topology limits, import fails atomically with a simplification message.

### User Story 3 - Apply local clipping (Priority: P3)
The designer imports artwork restricted by local clip paths, including group clipping, without
leaking material outside the source clip or changing drill inference into a guess.
**Why this priority**: Ignoring clipping can manufacture hidden excess material.
**Independent Test**: Transformed shape/group clipping gives analytic intersections before/after vertical flip.
**Acceptance Scenarios**:
1. Given a local clip in user coordinates or an object's bounding box, import keeps exactly its visible material.
2. Given parent and child clips, both apply; multiple clip shapes form a union and each clip uses its own winding rule.
3. Given missing/external/cyclic/unsupported clip content, import fails clearly, leaving existing objects intact.
4. Given clipped circular white artwork, drill detection does not infer an unqualified full drill from source paths.

### Edge Cases
Duplicate/incomplete/unknown-unit XMP; pixel versus physical dimensions; viewBox aspect policy;
percentage root dimensions; inline/class/id style precedence; hidden layers and local use; empty
clips; zero-width bounding boxes; shared edges, repeated rings, opposite winding and singular transforms;
clip reference limits; open source paths retained for reports; unchanged project/source text.

## Requirements
### Functional Requirements
- **FR-001**: Use normal physical root dimensions as primary evidence and a unique valid XMP MaxPageSize
  only as a documented fallback for unavailable dimensions; never average inconsistent scale factors.
- **FR-002**: Retain original source tokens and report page-size provenance, conflicts and visible layer labels.
- **FR-003**: Respect visible layer hierarchy and bounded embedded simple class/id/element styles with
  deterministic precedence; unsupported styles fail explicitly rather than disappearing silently.
- **FR-004**: Interpret nonzero/evenodd compound fills, including bounded touching/crossing contours,
  without modifying original source path facts.
- **FR-005**: Apply local user-coordinate and object-bounding-box clips in the correct transform frame,
  combining clip shapes by union and ancestor/child clips by intersection.
- **FR-006**: Preserve clip-rule independently of fill/stroke appearance; clip paths contribute no standalone material.
- **FR-007**: Reject unsupported/external/missing/nested-inside-definition clipping and excessive expansion/topology
  with actionable messages; import failure publishes no partial host object.
- **FR-008**: Keep import bounds/validity reports accurate after clipping, preserve source text through save/reopen,
  and prevent clipped source circles from silently becoming full drill candidates.
- **FR-009**: Preserve established units, physical flip, defaults and downstream placement behavior.
- **FR-010**: Validate analytic fixtures and existing reference outputs, actual desktop round trips and all prior journeys;
  distinguish authored Illustrator-style fixtures from genuine vendor-export evidence.

### Key Entities
- **Page evidence**: original SVG dimensions, optional XMP dimensions and explicit chosen physical viewport.
- **Layer/style evidence**: visible source group identity and resolved supported presentation.
- **Compound material**: source contours and rule determining bounded filled regions.
- **Clip application**: local source definition, coordinate frame, affected subtree and resulting intersection.

## Success Criteria
### Measurable Outcomes
- **SC-001**: Analytic page/transform fixtures match physical bounds within 0.01 mm without silent scale averaging.
- **SC-002**: Compound analytic area differs by at most 0.001 square mm for linear fixtures; winding cases remain distinct.
- **SC-003**: Clipped material has zero area outside the analytic clip within 0.001 square mm; hidden content contributes none.
- **SC-004**: Unsupported/over-budget fixtures publish no partial objects and preserve source/current project state.
- **SC-005**: Complete regression and real desktop import/report/save/reopen pass, with source/license trace and limitations recorded.

## Assumptions
- Depends on16; delivered after18. Existing SVG coordinate engine remains authoritative.
- Root pixel/unitless dimensions retain ordinary CSS pixel semantics; conflicting XMP is reported,
  not treated as permission to override an explicit source viewport.
- Layer filtering follows source visibility; no separate interactive layer picker is required in this slice.
- Supported styles are offline simple selectors; external CSS, fonts, masks, filters and arbitrary CSS layout remain unsupported.
- Clip definitions contain bounded basic shapes/local use; a clip definition referencing another clip is explicitly unsupported.
- No genuine licensed Illustrator CAM fixture is shipped by Neo; authored analytic fixtures must not be described as vendor exports.
- No new dependency, controller path or project-format redesign.
