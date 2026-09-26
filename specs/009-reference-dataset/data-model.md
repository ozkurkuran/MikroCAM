# Reference data model (schema 1)

All persistent envelopes have exact `kind`, integer `schema_version=1` and declared fields.
Unknown/missing/duplicate keys, nonfinite numbers, malformed hashes and unsupported versions
are invalid. Artifact paths are relative, stay inside the declared root after resolution,
and cannot escape through traversal or symlinks. SHA256 is 64 lowercase hexadecimal characters.

## Dataset manifest
`kind='mikrocam.reference-dataset'`, `schema_version`, `boards`.
Each board: `id` (unique stable slug), `name`, `origin` (nonempty evidenced tool name;
all five named origins must occur, and additional origins such as DipTrace/Fritzing/gEDA are allowed),
`design_identity` (original project/design identity, unique independently of filenames),
`source` (`url`, `revision`, `origin_evidence`), `license` (`identifier`, `evidence`, `notices`),
`files` (nonempty list). Immutable source references and redistribution evidence are mandatory.
Each file: `path`, `source_path`, `sha256`, `source_sha256`, `role`
(copper/drill/outline/drill-map/native/notice/archive). Original ZIP archives are retained.
`source_path` is an immutable source-relative file path, or `archivepath!member` for a verbatim
extracted entry; archive/member paths must be safe. `source_sha256` is the original file/entry
hash, equal to admitted bytes' `sha256`; the archive has its own role/hash record. No rewritten entries.
License notices link to retained original notice files; file-specific terms must be represented
in the evidence, not assumed from the repository's top-level license.
10–20 distinct admitted boards and every origin category are required. A board needs actual
copper; missing optional drill/outline is declared by its role inventory, not synthesized.

## Capture configuration
`kind='mikrocam.reference-config'`, `schema_version`, `parameters`, `stages`.
`parameters` is an exact, reviewed configuration of Gerber/Excellon parsing, isolation and CNC
numeric/boolean/string settings. Factory defaults may initialize baseline host plumbing,
but every actual parser/CAM parameter is explicitly overridden; no silent machining fallback.
`stages` explicitly declares outputs
requested for each role. Probe-selected keys/values must be frozen in capture-config.json
before capture, tested and recorded in research.md. Probe feasibility/configuration evidence is resolved;
formal strict config/codec schema is frozen before harness implementation.
Common requested machining parameters have one hash across engines. Engine-specific effective
optimization is recorded separately: Evo `N`, legacy hardcoded RTree, an expected source distinction.

## Capture artifact
Deterministic gzip JSON: `kind='mikrocam.reference-capture'`, `schema_version`, `board_id`,
`engine`, `source`, `runtime`, `inputs`, `configuration`, `stages`.
`engine` is legacy8994/evo/current. `source` has exact `revision` and `files` (ordered
`{path,sha256}` records for tracked application Python sources). `runtime` has exact
`python`, `architecture`, `dependencies` (distribution-to-version map) and `harness_sha256`
(combined capture/codec/settings-helper byte hash). `inputs` is an ordered list of
`{path,sha256}` for every admitted board file. `configuration` has exact `sha256`,
`requested` (full configuration envelope) and `effective_optimization`. No machine-local
absolute paths are required for portability. Comparison requires equal runtime/harness
evidence and common requested configuration; differing source revisions are expected.
Each requested stage has `input_path`, `stage` (gerber/excellon/isolation/cnc), `status`
(ok/error/unsupported), `units='mm'`, `source_units` (MM/IN or null if unavailable),
`tools` (list, empty for non-Excellon stages), `geometry_wkb` (ordered strings), `paths` (ordered
`{kind:[str,...],wkb_hex:str}`), `gcode` (string or null), `diagnostic` (string or null).
Success retains actual available outputs; error/unsupported records have a contextual
diagnostic and no fabricated geometry/path/G-code. Empty requested output cannot become
a synthetic successful geometry. Absent requested stages make the artifact incomplete.
Each tool has exact `id` (string), `diameter_mm` (positive finite), `drills` (ordered XY pairs,
including duplicates) and `slots` (ordered start/end XY-pair pairs). Tools have stable ID order.
Union geometry cannot replace diameters, duplicates or drill/slot multiplicity.
Geometry is valid finite XY ISO little-endian normalized WKB hex, preserving original source
geometry. CNC path Point/LineString coordinates preserve order/direction/repeated vertices;
their WKB is plain 2D encoding without geometric normalization that would reverse paths.
Actual parser `units` is authoritative; source-file and `units_found` labels are not conversion inputs.
Raw G-code retains returned header+body, without executing it or using lexical equality as the CAM gate.

## Pure comparison values
Frozen `GeometryComparison(matches, topology_equal, hausdorff_mm,
symmetric_difference_mm2, bounds_delta_mm)`. Bounds delta is a tuple of four absolute coordinate deltas.
Topology compares structural geometry type, component count and ring/hole counts;
orientation/component order do not change geometric equality. Distance is GEOS's discrete
vertex Hausdorff metric, not a claimed continuous maximum-distance proof.
Frozen `ReferencePath(kind:tuple[str,...], wkb_hex:str)` accepts valid finite 2D Point/LineString
only. Frozen `PathComparison(matches, differing_indices, expected_count, actual_count)`
records explicit tuple indices, including unmatched tail paths. Corresponding paths require
exact kind, equal vertex count and each corresponding XY pair within Euclidean `distance_mm`.
This preserves direction, repeated vertices and order. A separate narrow executable-word
comparison detects emitted Z/feed/spindle/dwell/mode changes; it does not interpret modal state.
Tool comparison requires equal IDs and tool/drill/slot counts/order; diameter and corresponding
drill/slot endpoint differences use distance_mm. Reusable numeric/path comparison stays core-only.
Tolerances are explicit finite nonboolean real numbers >=0; zero is valid. Malformed/nonplanar
WKB and oversized input raise ValueError. Limits: 64 MiB decoded WKB per geometry,
200,000 ordered paths and 2,000,000 aggregate vertices in core; 128 MiB decoded JSON per
gzip artifact in developer codecs. Fail explicitly before expensive allocation; never truncate.

## Comparison report
`kind='mikrocam.reference-report'`, `schema_version`, `baseline`, `candidate_source`,
`tolerances` (`distance_mm`,`area_mm2`), `results`, `outcome`.
Results identify board/input/stage, outcome match/difference/indeterminate, diagnostic and
available metric values. Only matching comparable stages yield aggregate match. Any invalid
or indeterminate stage yields aggregate indeterminate; otherwise any difference yields difference.
Repeated baseline errors/unsupported stages remain indeterminate even when candidate errors match.
