# Research and decisions

## Existing Evo assessment
The shared seam is camlib.Geometry.import_svg (GUI and both Tcl SVG commands call it). It currently
uses width/viewBox-width alone, derives document units only from height, scales shape coordinates
before unscaled transform translations, passes SVG matrix coefficients in Shapely's different order,
and emits mm coordinates even in an IN object. ParseSVG.parse_svg_transform can log forever without
consuming malformed syntax. Definition recursion draws unused shapes; use cycles are unbounded.
Stroke inheritance and solid stroke conversion are absent. Legacy text uses installed fonts and an
empirical 2.2 size factor; it cannot substantiate correct physical typography. The new path therefore
rejects text explicitly with an outline-in-editor instruction instead of silently mis-sizing it.

Existing helpers retain Move-separated open paths, Close rings and parity topology. Characterization
tests remain; no frozen reference file is changed. Only two small SVG path fixtures currently exist,
so add independently authored physical-unit/transform/stroke document fixtures with analytic output.

## Decisions
Use bounded stdlib XML traversal and immutable records; adapt the already pinned svg.path dependency
at the bridge. Reject unsupported appearance before publishing an object. Do not extend the existing
legacy parser with new feature logic or build a browser/CSS/font renderer. Keep existing host object
population and one final mm-to-host conversion.

Absolute child lengths become CSS-px-equivalent local user units before viewBox/ancestor transforms.
For example child 4in equals 384 local units, not a final physical four inches under an arbitrary
viewBox. Root dimensions anchor physical output. SVG matrix coefficients are remapped explicitly to
Shapely order. Stroke expansion occurs locally before nonuniform transforms. Default fill is black,
stroke none; open subpaths implicitly close for fill while their source centrelines stay available.
Retaining an otherwise unpainted open path for Geometry is an explicit CAM compatibility notice;
Gerber requires solid material. Unsupported clipping, dash, vector-effect, nested viewport, CSS and
font semantics are rejected rather than producing a misleading partial shape.

Source facts only, no external source code copied:
- [SVG 2 coordinate systems and units](https://www.w3.org/TR/SVG2/coords.html#Units)
- [SVG 1.1 transform grammar](https://www.w3.org/TR/SVG11/coords.html#TransformAttribute)
- [SVG 2 fill and stroke](https://www.w3.org/TR/SVG2/painting.html)
- [CSS absolute units](https://www.w3.org/TR/css-values-4/#absolute-lengths)

All runtime packages and their license records already exist. No new binary, font or optional extra.
