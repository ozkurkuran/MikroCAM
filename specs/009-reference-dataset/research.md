# Research: PCB reference dataset

## Decisions and evidence
- **Decision**: Admit only immutable-source, hash-verified designs with original license notices.
  **Rationale**: Public availability alone is not redistribution permission or tool-origin evidence.
  **Alternative**: Arbitrary downloaded Gerbers or synthetic renamed layers would not satisfy authenticity.
  **Pending evidence**: Candidate source/license audit and final corpus inventory. Twelve candidates
  were researched; admission may be eleven. Neither number is claimed as completed; scope remains 10–20/all five origins.
- **Decision**: Keep both unchanged baselines separately. Fixed source revisions are legacy8994
  `6ba378bca139aa306f8c94f09461a98f95d3c75b` and evo `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff`.
  **Rationale**: Actual independent behavior must survive baseline disagreement.
  **Evidence supplied by probe**: Existing test.gbr copper areas differ (about 62.5507 Evo versus
  62.5225 legacy); these approximate values illustrate divergence, not substitute goldens.
  **Alternative**: Selecting the closer result automatically or manufacturing expectations from current code is rejected.
- **Decision**: Capture through real headless Gerber -> isolation_geometry -> Geometry boundary
  -> CNC generation and the engine's own G-code parse.
  **Evidence supplied by probe**: This chain runs on both unchanged revisions without GUI/hardware.
  Evo supports optimization `N`; legacy hardcodes RTree. Record effective optimization per engine
  while holding common requested parameters fixed. Raw CNC generation returns body/header;
  preserve header+body. Actual parser.units is authoritative; Excellon units_found may remain MM for IN data.
  **Resolved probe evidence**: `.venv/probe-cam-baselines.py` and `probe-cam-repeat.py` ran
  eight isolated processes (two references x MM/IN x two repeats). Raw G-code and ordered
  parsed-path SHA256 repeated identically for each pair; native IN-to-MM conversion factor
  is 25.4 on both. Constructor app argument and spindle direction/circle-step argument names
  are selected from actual signatures. Root will retain exact command/output evidence in validation.
  **Verified explicit operation settings**: circle steps64; Gerber simplification off,
  simplification tolerance0.001, full buffering/extra0, clean apertures and union buffering;
  isolation distance0.1mm; tool diameter0.2mm, offset/tolerance0, cutZ-0.1mm, travel/start/endZ2mm,
  feeds120/60/300mm/min, spindle10000CW, dwell/multidepth/toolchange/extracut off,
  depthpercut0.1mm, endXY0,0, default preprocessor, tool1, coordinate/feed decimals4/2,
  G90; Excellon zerosL, MM format3:3 and IN format2:4. Factory config supplies plumbing;
  actual parser/CAM controls are explicitly overridden, not silently inherited machining choices.
  **Remaining admission evidence**: Corpus license/origin audit, formal strict schema/config
  freeze, runtime/source hash records and actual per-board golden/failure inventory.
- **Decision**: Compare geometry sets and ordered parsed paths in pure core.
  **Rationale**: Hausdorff/area alone lose topology and CNC direction; coordinatewise path
  comparison preserves those meanings without a future lexical G-code preflight feature.
  **Alternative**: Byte-equal WKB/G-code would falsely fail orientation/header changes; only area
  equality could falsely pass lost holes/shifted paths. GEOS discrete Hausdorff is explicitly named.
- **Decision**: Explicit tolerances and indeterminate failures, no auto-update.
  **Rationale**: A repeated baseline exception is evidence of unavailable comparison, not equality.
  **Alternative**: Silent skips/default tolerance inflation would make the regression gate untrustworthy.

## Implementation evidence gates
Integration review found that equal engine-parsed 2D paths and requested configuration
cannot detect wrong emitted Z, feed, spindle or dwell. Therefore raw default-preprocessor
executable words are also compared, ignoring presentation-only comments/whitespace and
using numeric equality for non-XY words. This is a narrow saved-output comparison, not
the future modal preflight/streaming feature. Tests must demonstrate each emitted-value
regression before implementing this addition.

Source/notice admission and exact capture config must be reviewed before corpus/golden creation.
Capture adapters must match unchanged source APIs; isolation wrappers may provide only explicit
test context, never altered parser/CAM algorithms. Reproduction and IN probes are implementation
tasks with retained evidence. Core geometry/path comparison is sufficiently specified to test first
independently while the dataset audit/capture probes proceed.
