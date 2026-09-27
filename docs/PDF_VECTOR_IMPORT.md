# Import a PDF vector page

Choose **File → Import → PDF vector page...**. Browse to a PDF and select **Inspect pages**.
Select one page and its CropBox or MediaBox. Optionally enable a rectangular crop in millimetres
and a vertical flip. Select **Analyse selected page**, review the physical bounds and source
details, enter a Geometry name and select **Create reviewed Geometry**.

Changing the file, page, box, crop or flip clears the review. Creation checks the source again;
if it changed, analyse again. The original file and existing project objects are preserved.
The resulting Geometry uses the application's current MM/IN units and normal machining defaults.
The original PDF bytes and a versioned import report survive project save/reopen even when the
original file is unavailable. The optional, collapsed report describes the geometry at import time.

## Coordinates and supported artwork

The selected page's box origin is removed, then PDF UserUnit and points are converted to mm.
The page's clockwise rotation is applied before the optional physical crop. Crop coordinates are
in this oriented page frame. The crop's lower-left corner becomes the new origin. Vertical flip
reflects once about the cropped height. Material is clipped to the final viewport.

Independent subpaths remain independent. The supported subset includes affine transforms,
graphics-state save/restore, straight paths, rectangles, cubic curves, nonzero/even-odd compound
fills, solid strokes and basic path clipping. Opaque white paint clears earlier material; other
opaque gray/RGB/CMYK colors mark material. Fill occurs before stroke for combined painting.
Curves and rounded strokes use a 0.01 mm physical approximation budget.

Supported drawing operators: `q Q cm w J j M d m l c v y h re S s f F f* B B* b b* n W W*`
and `g G rg RG k K`. Empty text setup from normal generators is accepted; actual text painting,
images, Forms, patterns, shading, transparency and annotations require conversion to supported
paths before import. Hairline width zero, dashed strokes and self-overlapping strokes fail
explicitly. Miter limits are restricted to 1–1000. This workflow produces Geometry, without drill
inference or raster vectorization. Evo's existing PDF tool remains separately available.

## Complexity and reading boundary

Input is limited to 16 MiB, 128 pages and 8 MiB of jointly decoded selected-page content. Page
trees are checked for type, parent/count agreement, duplicate children and cycles, with 512
entries and depth 32. A page permits 50,000 commands, graphics-state depth 64, 10,000 subpaths,
100,000 points per contour, and 500,000 combined sampled/final coordinates. Intermediate material
and accumulated stroke outputs are also bounded. Coordinates and physical page sizes are limited
to 1e9 mm. Existing compound-fill guards apply, including 256 rings and bounded complex faces.
Overlays check at most 32,768 edge intersection candidates and two million cumulative edge visits
before geometric operations. Empty final material and exceeded bounds produce an error.

The pinned, lazily imported BSD-3-Clause `pypdf==6.19.0` reads page/object streams. Configuration
limits are context-local and restored after each read. No actions, scripts or external resources
are executed. Three pinned instance-level parser hooks bound operator accumulation, reject inline
images before decoding, and detect unconsumed trailing operands; they do not patch global classes.
Changing pypdf requires revalidating these hooks and malformed-input fixtures. These are explicit
input/algorithm limits, not an operating-system memory or time sandbox.

## Verification and provenance

The legacy Evo reader was evaluated first: it did not provide page isolation and collapsed a
quarter-turn matrix in a local analytic prototype. The selected implementation reuses MikroCAM's
existing curve, compound-fill and affine-stroke helpers. No outside parser or rendering algorithm
was copied. pypdf's original wheel license and hashes are retained under `THIRD_PARTY_LICENSES`.

Fixtures are authored analytic PDFs, including two distinct pages, compressed contents, physical
crop/flip, paint/clipping topology and malformed limits. Actual Geometry tests cover MM and IN,
DXF export/reparse, lossless PDF source and report persistence, and unchanged defaults. Desktop
validation exercises the complete dialog and project reopening. This is software validation;
no vendor PDF compatibility or physical machining accuracy is inferred from authored examples.
