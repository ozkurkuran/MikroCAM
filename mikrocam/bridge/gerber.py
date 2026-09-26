"""Snapshot current Gerber copper without retaining or modifying host objects."""

from mikrocam.core.laser_job import PlanarRegion, region_from_polygons


def gerber_region(obj: object) -> PlanarRegion:
    """Detach Gerber copper in mm using its current geometry's explicit units.

    Original source-file units and host defaults are not current geometry units.
    Core owns polygon validation, union, conversion and immutable storage.
    """
    if getattr(obj, 'kind', None) != 'gerber':
        raise ValueError('Expected a Gerber object with kind == "gerber"')
    try:
        units = getattr(obj, 'units')
        geometry = getattr(obj, 'solid_geometry')
    except AttributeError as error:
        raise ValueError('Gerber requires explicit units and solid_geometry') from error
    try:
        return region_from_polygons(geometry, units)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid Gerber copper: {error}') from error
