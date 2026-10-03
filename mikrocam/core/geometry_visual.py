"""Polygon appearance snapshots in an explicit mm viewport, using shared Placement."""
import math
from .laser_job import PlanarRegion
from .placement import Placement


def geometry_svg(region: PlanarRegion, roi_mm: tuple[float, float, float, float]) -> bytes:
    if type(roi_mm) is not tuple or len(roi_mm) != 4 or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in roi_mm
    ) or roi_mm[2] <= roi_mm[0] or roi_mm[3] <= roi_mm[1]:
        raise ValueError('Explicit finite ROI in mm required')
    xmin, ymin, xmax, ymax = roi_mm
    # Map original Y-up geometry to this SVG's local Y-down viewport once.
    placement = Placement(origin=(xmin, ymax), rotation_deg=180, mirror_x=True)
    geometry = placement.apply_geometry(region.to_geometry())
    polygons = (geometry,) if geometry.geom_type == 'Polygon' else geometry.geoms
    paths, vertices = [], 0
    for polygon in polygons:
        parts = []
        for ring in (polygon.exterior, *polygon.interiors):
            vertices += len(ring.coords)
            if vertices > 500000: raise ValueError('SOURCE_TOO_LARGE: geometry vertex limit')
            points = [f'{x:.15g},{y:.15g}' for x, y in ring.coords]
            parts.append('M' + 'L'.join(points) + 'Z')
        paths.append('<path fill="black" fill-rule="evenodd" d="' + ' '.join(parts) + '"/>')
    width, height = xmax - xmin, ymax - ymin
    text = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.15g}mm" height="{height:.15g}mm" viewBox="0 0 {width:.15g} {height:.15g}">' + ''.join(paths) + '</svg>'
    return text.encode('utf-8')
