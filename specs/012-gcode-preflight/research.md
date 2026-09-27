# Research: G-code preflight

## Decisions
- Interpret a bounded GRBL-oriented subset independently in pure core. Existing
  `reference_gcode.compare_gcode` is a lexical regression comparator, not a modal/safety oracle.
  `camlib.CNCjob.gcode_parse` is visualization-oriented and mutates legacy state; neither is reused
  as a safety parser. Reuse its general bounded-input approach, not its implementation.
- Support G0/G1 and G17 XY G2/G3 including helices and signed-R/relative-IJ centers. Reject G93,
  non-XY planes, machine/temporary offset changes, probing, tool changes and macros explicitly.
  G94 feed persists in physical mm/min through unit changes until another F word.
- Use existing Placement for XY and explicit Z translation. Initial G92 and TLO must be zero
  assumptions, not inherited unknown controller state; G49 only restates zero tool-length offset.
  This offline feature does not prove a connected machine satisfies those assumptions.
- Compute analytic arc extrema after actual Placement; chord sampling can understate travel.
  Use complete path including initial position and Z endpoints; no geometry approximation needed.
- Machine bounds/initial position/safe Z are required explicit inputs. No limits are guessed
  from a CNCJob bounding box. A successful report is conditional on this declared setup.
- Duration is nominal path/feed plus per-axis rapid-limited time and dwell. Missing rapid rates,
  pauses or incomplete interpretation make total unavailable. Acceleration/overrides/physical
  spindle delays are outside this estimate; never substitute a cutting feed for unknown G0 rates.
- Bridge snapshots complete source_file only; gcode bodies may omit exported headers. No call to
  legacy export or mutation is allowed. Files use bounded strict UTF-8 decoding; executable analysis
  rejects non-ASCII/control/realtime bytes even in comments because GRBL receives realtime bytes
  outside line parsing. Percent wrappers are unsupported and blocked.
- A new lightweight dock uses immutable worker inputs and cooperative cancellation. Reuse the
  existing app menu/shutdown connection pattern; do not introduce a generic task framework.

## Primary references checked 2026-09-27
- [GRBL1.1 commands](https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md): supported
  modal groups, coordinate/TLO semantics and realtime handling.
- [GRBL1.1 interface](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md): source
  stream and realtime handling; analysis cannot treat comments as a realtime-byte shield.
- [GRBL G-code parser](https://github.com/gnea/grbl/blob/master/grbl/gcode.c): factual verification
  of physical G94 feed retention, relative arc centers, signed-R major arcs and G49 semantics.
- [GRBL protocol](https://github.com/gnea/grbl/blob/master/grbl/protocol.c): comment/line behavior.
Luna inspected protocol facts only; no GPL implementation text was copied or ported. All new
algorithms/tests are independently written. No FlatCAM-Plus source is used.

## Alternatives rejected
- Guess modal defaults or silently skip unsupported lines: can approve the wrong physical path.
- Use geometry bounding boxes/endpoints alone: misses arcs and initial/rapid travel.
- Add machine profiles/settings persistence now: roadmap requires preflight, not a profile system.
- Synchronous GUI analysis or unconstrained diagnostic/path storage: avoidable resource/UI risk.
