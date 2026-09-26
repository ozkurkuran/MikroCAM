# Laser CAM: Gerber to per-pass geometry

1. Load copper Gerber in MikroCAM and open **Plugins → Laser CAM**. Refresh sources if files
   were added while the dock was open. Select the copper object; choose an explicit closed
   outline Gerber when using Board edge or Board minus copper.
2. Load recipe JSON, or enter a recipe name and add passes. Every row needs a unique name,
   power %, speed mm/s, frequency kHz and pulse width ns. Blank/invalid fields are errors;
   there is no global or material preset fallback. Save recipe JSON to reuse these values.
3. Set origin, translation, rotation and mirror in the shared placement controls. Internal
   units are mm. Mirror local X reflects about local Y before rotation.
4. Choose outer copper, inner holes, trace, pad, board edge or no contour. Trace/pad modes
   need usable aperture metadata and respect final Gerber clear areas. An explicit outline
   must have closed noncrossing rings; nested rings describe cutouts and islands. Touching
   or duplicate ring boundaries are rejected.
5. For hatch, enter spacing and angle; cross hatch adds the perpendicular family. Choose
   Copper or Board minus copper explicitly. The latter requires an outline containing all
   copper. Exposure segments are clipped separately; no connectors cross holes/gaps.
6. Interlace N groups original scan indices by nonnegative modulo N (for example N=3 groups
   rows 0/3/6, then 1/4/7, then 2/5/8). Cross-hatch families remain separate. N=1 preserves
   previous order. This is path ordering, not a calibrated thermal-control claim.
7. Generate and inspect the Geometry preview. It draws common geometry once even for several
   passes; each planned pass retains its own explicit parameters. Cancel/close invalidates
   unfinished results; changing controls requires a new generation before export.
8. Select SVG or DXF and Export ZIP. Extract all files. Each pass has an ordinal filename;
   manifest.json maps that file to its original name, parameters, path count and SHA-256.

## Target application handoff

Import pass files in manifest order using mm, and verify a known board dimension and
orientation. SVG uses physical mm width/height and a common local frame:
`x_svg = x_placed - xmin`, `y_svg = ymax - y_placed`. DXF keeps placed XY and declares
millimetres through `$INSUNITS=4`. A zero-width/height SVG extent gets a 1 mm viewport without
adding a registration/exposure line. All pass files share one frame; do not centre them
independently. SVG viewport localization means the manifest is needed to recover absolute
placed coordinates.

Manually transfer **all four parameters** from recipe.json to each target operation. SVG/DXF
do not automatically configure the laser. Resolve unsupported frequency/pulse-width settings
in the target application's device configuration. External optimization can reorder imported
geometry and defeat interlace; inspect or disable it as appropriate in that application.

The exporter writes a temporary ZIP beside the selected destination, flushes it and replaces
the destination only after success. Cancel before that boundary preserves the previous file.
A cancel after publication reports Saved, because the completed output already exists.
Limits are 1,000 passes, 2 million emitted paths, 10 million vertices and 512 MiB uncompressed
geometry; exceeding a limit produces an error rather than partial output.

## Verification record and limits

Independent XML/SVG rendering and ezdxf readback tests verify 25.4 mm dimensions, path order,
closure, gaps, transformed coordinates and metadata. Real Windows desktop smoke exports
both formats from a two-pass N=3 plan, reopens the archives, then closes MikroCAM normally.
See [slice 008 validation](../specs/008-laser-export-svg-dxf/validation.md).

No LightBurn/EZCAD installation appeared in standard installed-program records or Program
Files during this session. No target-app import or physical PCB manufacture has been claimed.
The next external checks are actual import scale/axis/order/settings verification and a
suitable physical coupon on the user's equipment. Test recipe values are synthetic examples,
not material/device presets. MikroCAM's software export performs no motion or laser emission.
