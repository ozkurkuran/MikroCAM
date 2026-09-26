# Research: Laser contour and hatch

- Final Gerber `solid_geometry` has clear polarity subtracted. Aperture `tools` entries contain
  `geometry` records with `solid`, `follow`, `clear`; Point follow denotes flash/pad, non-REG
  LineString follow denotes trace. REG regions must not be relabelled as traces. Intersect
  selected positive solids with final copper; missing semantic metadata remains unavailable.
- Current `obj.units` reflects host conversion; original MOIN/MOMM source can disagree. Reuse
  the 005 bridge boundary. Geometry math and conversion stay in core helpers.
- An explicitly selected board Gerber may expose closed `follow_geometry` rings; polygonize
  closed planar paths with even/odd nesting for cutouts. Reject open paths, crossings,
  ambiguous touching rings, nonplanar or invalid data. Do not use stroked outline copper width
  or invent a bounding box as board area. Existing `region_test.gbr` provides a closed fixture.
- Hatch: rotate selected area into hatch coordinates using existing Placement, intersect
  integer-indexed horizontal lines at spacing, retain separate clipped segments, rotate back.
  This local basis change is separate from the one final job placement. Index zero is anchored
  at source origin; perpendicular family keeps its own indices for future interlace.
- Evo `install_tools()` rebuilds its plugin menu after layout changes. A small action there
  can lazily open the UI dock. Concrete bridge wraps collection lookup and `new_object`.
- Preview uses ordinary geometry, detached LineStrings and mm converted at the host boundary
  if app units are IN. Existing Geometry initialization uses one tool with solid_geometry,
  tooldia and data. A unique owned object reference avoids deleting a similarly named user
  object. Publish on GUI thread and preserve source selection.
- Existing plugin tab is recreated by legacy layout logic; a QDockWidget is simpler and
  reusable. Cancellation Event is checked in core callbacks; worker results return by Qt
  signals. Hide/close cancels, shutdown waits; stale results cannot publish.
- No external source code or new dependency is needed; analytic fixtures are independently
  authored test data, not claims of a measured manufacturing board.
