"""Optional Gerber/polygon Geometry sources share the general visual pipeline."""
from mikrocam.core.geometry_visual import geometry_svg
from mikrocam.core.laser_job import region_from_polygons
from mikrocam.core.visual import SourceAsset, SourceInfo
from .gerber import gerber_region


def snapshot_geometry(geometry: object, units: str, roi_mm: tuple[float, float, float, float],
                      name: str) -> SourceAsset:
    region = region_from_polygons(geometry, units)
    return _asset(region, roi_mm, name)


def _asset(region, roi_mm, name):
    data = geometry_svg(region, roi_mm)
    width, height = roi_mm[2] - roi_mm[0], roi_mm[3] - roi_mm[1]
    info = SourceInfo('geometry_snapshot', 'image/svg+xml', suggested_size_mm=(width, height), size_origin='user')
    return SourceAsset(name, data, info)


def snapshot_gerber(owner: object, roi_mm: tuple[float, float, float, float], name: str) -> SourceAsset:
    return _asset(gerber_region(owner), roi_mm, name)
