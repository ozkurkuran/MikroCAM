# Research: SVG/DXF handoff

- [SVG coordinates](https://www.w3.org/TR/SVG/coords.html) define Y down in the initial
  viewport. Emit width/height with mm and viewBox in matching units. Use x'=x-xmin,
  y'=ymax-y; manifest records inverse mapping. All pass files have identical bounds/frame.
  Zero extent gets a 1 mm viewport dimension, never an extra path.
- [LightBurn import settings](https://docs.lightburnsoftware.com/2.2/Reference/SettingsPreferences/)
  expose SVG DPI and DXF unit interpretation. Physical dimensions and explicit unit headers
  help, but users still verify the included 25.4 mm reference/readback instructions on import.
- [DXF LWPOLYLINE](https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-DXF/files/GUID-748FC305-F3F2-4F74-825A-61F04D757A50.htm)
  uses vertex count, XY tags and closed flag. R2000/AC1015 and $INSUNITS=4 convey a mm
  modelspace; see [ezdxf units](https://ezdxf.readthedocs.io/en/stable/concepts/units.html).
  Keep planar zero-elevation polylines, no arcs/splines/blocks/fills. Preserve placed XY.
- [LightBurn color layers](https://docs.lightburnsoftware.com/2.2/Reference/UI/ColorPalette/)
  map colors to process settings but SVG/DXF do not provide a documented portable encoding
  for our complete recipe. [Galvo settings](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/GalvoSpecificCutSettings/)
  include frequency and device-dependent Q-pulse; do not silently drop unsupported fields.
- [JCZ EZCAD2](https://en.bjjcz.cn/product/159.html) lists vector import and separate process
  settings. Detailed installed-target behavior has not been verified. Separate files per pass
  avoid relying on undocumented color/layer-to-parameter mapping. A ZIP includes recipe and
  explicit manifest/README; it is not a machine-ready native target project.
- Geometry ordering is preserved in file entity order. External optimization can reorder;
  instructions require checking/disabling it where needed before relying on interlace order.
- Atomic ZIP replacement provides one publication boundary and avoids a partially updated
  multi-file directory. Runtime uses stdlib encoders; installed ezdxf and XML parser independently
  validate output. No new library or broader serializer abstraction is required.
