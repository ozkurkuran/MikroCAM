# Capture, comparison and CLI contracts

## Pure core API
`compare_geometry(expected_wkb: str, actual_wkb: str, *, distance_mm: float,
area_mm2: float) -> GeometryComparison` validates finite valid 2D canonical ISO WKB;
normalizes ring/component ordering for set comparison, requires structural topology equality,
discrete vertex Hausdorff <= distance_mm and symmetric-difference area <= area_mm2.
Identical valid geometry has a zero-metric fast path. Bounds deltas are report evidence,
not an extra implicit tolerance. Invalid/oversized/nonplanar inputs or tolerances raise ValueError.

`compare_paths(expected: Sequence[ReferencePath], actual: Sequence[ReferencePath], *,
distance_mm: float) -> PathComparison` compares path order/count, exact kind tuples and
ordered XY coordinate counts/positions, including direction and repeated vertices.
Only Point/LineString paths are accepted. Invalid values raise ValueError.
Core limits: 64 MiB decoded WKB/geometry, 200,000 paths and 2,000,000 aggregate vertices.
Developer gzip codecs reject decoded JSON beyond 128 MiB/artifact.
Excellon comparison retains source_units metadata and explicit tools (ID, diameter_mm,
ordered drills/slots), using distance tolerance for diameters/coordinates and exact IDs/counts.
Every stage uses the same exact keys with tools=[] and source_units=null where unavailable.
Core imports stdlib/Shapely/NumPy only; file/provenance/JSON/engine loading belongs to developer tooling.

`ReferenceTool(id, diameter_mm, drills, slots)` is frozen; coordinates are immutable XY
tuples, including ordered duplicate drill hits and oriented slot endpoint pairs. Unused
declared tools may have no hits; their metadata remains present. `compare_tools(expected,
actual, *, distance_mm) -> ToolComparison(matches, differing_indices, expected_count,
actual_count)` requires unique IDs within each nonempty sequence and preserves tool order,
diameters, hit/slot counts and corresponding coordinates. Diameter and point differences
use the explicit distance tolerance. Empty overall successful Excellon output is rejected
by the capture/codec boundary. Tool sequences share the path/aggregate vertex limits.

## Capture CLI
`python tests/reference/capture.py --engine legacy8994|evo|current --source PATH
--python PATH --manifest PATH --config PATH --output NEW_DIRECTORY [--revision SHA]
[--timeout-seconds 120]`.
Baseline expected revisions are fixed: legacy8994 `6ba378bca139aa306f8c94f09461a98f95d3c75b`,
evo `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff`. Current requires explicit revision.
Reject dirty source, wrong SHA, invalid corpus/config or existing output directories. Each board
runs in an isolated subprocess with bounded positive timeout. Freeze/record parser/CAM APIs
and explicit settings after probes; never patch baseline source/functions or invent outputs.
Factory defaults may provide host plumbing; actual parser/CAM parameters must be overridden
explicitly and recorded, rather than claiming factory configs were never loaded.
Qt settings/AppData are sandboxed before imports; no QApplication GUI, OpenGL, network or hardware.
On timeout/failure retain stage context and clean only owned child processes. Capture cannot
claim comparable success for failed stages. Report capture completeness separately from CAM success.
Output is normalized deterministic JSON1 gzip (`mtime=0`); wall-clock timing/logs are auxiliary
evidence and not a source of false result changes. Repeat capture compares normalized content.

## Compare CLI
`python tests/reference/compare.py --baseline legacy8994|evo --goldens DIRECTORY
--candidate DIRECTORY --manifest PATH --config PATH --distance-mm NUMBER
--area-mm2 NUMBER --report PATH`.
Both tolerances are required, finite nonboolean/nonnegative; no relative/default widening.
Validate strict schemas, hashes, source identity and common requested configuration before
comparing outputs. Expected engine-specific optimization is evidence, not a false common-config mismatch.
Never overwrite corpus/goldens or capture a missing expected result from current code.

Exit codes: **0** = every requested comparable stage matches; **1** = valid measured difference
with no indeterminate stages; **2** = invalid input/provenance/config or any indeterminate stage.
Error versus success may be reported as a difference in status, but an unavailable/error baseline
still makes the overall result indeterminate. Missing stages and repeated failures cannot be green.
Always identify board/input/stage and preserve diagnostics/available metrics. Reports stay outside
goldens. Deliberate replacement of expected records is a separate reviewed data change, no update flag.

Raw G-code is retained for audit; ordered engine-parsed paths and explicit machining config are
the comparison surface. This contract adds no lexical G-code interpreter or machine preflight.
