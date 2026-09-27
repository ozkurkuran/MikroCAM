"""Bounded SVG file boundary and authoritative millimetre geometry import."""
from dataclasses import replace
from pathlib import Path

from shapely import affinity, get_num_coordinates
from shapely.geometry.base import BaseGeometry

from mikrocam.core.svg_models import (CURVE_TOLERANCE_MM, MAX_SVG_BYTES, MAX_SVG_POINTS,
                                     SvgDocument, SvgImportResult, SvgNotice, SvgRendered)
from mikrocam.core.svg_paint import render_svg_paths
from mikrocam.core.svg_clip import apply_svg_clips, clip_application_matrix
from mikrocam.core.svg_transform import affine_scale_bound, compose_affine
from mikrocam.importers.svg_document import parse_svg_document
from mikrocam.importers.svg_clips import clip_shape_attributes
from .svg_paths import element_paths


def import_svg_bytes(source: bytes, source_name: str, *, flip: bool = True,
                     object_type: str = 'geometry') -> SvgImportResult:
    """Produce an atomic immutable physical result without touching host objects."""
    if type(flip) is not bool or object_type not in ('geometry', 'gerber'):
        raise ValueError('SVG import requires boolean flip and Geometry/Gerber object type')
    document = parse_svg_document(source, source_name)
    if flip:
        reflection = (1., 0., 0., -1., 0., document.viewport.height_mm)
        clips = {clip.application_id: replace(clip, matrix=compose_affine(reflection, clip.matrix))
                 for element in document.elements for clip in element.clips}
        elements = tuple(replace(element, matrix=compose_affine(reflection, element.matrix),
                                 clips=tuple(clips[c.application_id] for c in element.clips))
                         for element in document.elements)
        viewport = replace(document.viewport, matrix=compose_affine(reflection, document.viewport.matrix))
        notice = SvgNotice('vertical-flip', 'SVG Y axis reflected once about the physical viewport height.')
        document = replace(document, viewport=viewport, elements=elements,
                           notices=document.notices + (notice,))
    rendered, count = [], 0
    for element in document.elements:
        tolerance = min(1e9, CURVE_TOLERANCE_MM / (2 * affine_scale_bound(element.matrix)))
        paths = element_paths(element, tolerance)
        count += sum(len(path.points) for path in paths)
        if count > MAX_SVG_POINTS:
            raise ValueError('SVG document point budget exceeded')
        output = render_svg_paths(paths, element.paint, element.matrix,
                                  retain_centerlines=object_type == 'geometry')
        count += sum(int(get_num_coordinates(geometry)) for geometry in output.geometry_mm)
        if count > MAX_SVG_POINTS:
            raise ValueError('SVG document point budget exceeded')
        rendered.append(output)
    rendered = _clip_material(document, tuple(rendered), count)
    result = SvgImportResult(document, rendered, flipped=flip)
    if not result.geometry_mm:
        raise ValueError('SVG contains no solid material' if object_type == 'gerber'
                         else 'SVG contains no importable geometry')
    return result


def _clip_material(document: SvgDocument, rendered: tuple[SvgRendered, ...],
                   count: int) -> tuple[SvgRendered, ...]:
    applications = {clip.application_id: clip for element in document.elements for clip in element.clips}
    if not applications:
        return rendered
    if len(applications) * len(document.elements) > MAX_SVG_POINTS:
        raise ValueError('SVG clip scope work budget exceeded; simplify the source')
    materials = {}
    for identifier, clip in applications.items():
        matrix = clip_application_matrix(clip, document, rendered)
        shapes = []
        for element in clip.elements:
            effective = compose_affine(matrix, element.matrix)
            tolerance = min(1e9, CURVE_TOLERANCE_MM / (2 * affine_scale_bound(effective)))
            normalized = replace(element, attributes=clip_shape_attributes(element, clip.units))
            paths = element_paths(normalized, tolerance)
            count += sum(len(path.points) for path in paths)
            if count > MAX_SVG_POINTS:
                raise ValueError('SVG clip generated point budget exceeded')
            output = render_svg_paths(paths, element.paint, effective)
            count += sum(int(get_num_coordinates(g)) for g in output.geometry_mm)
            if count > MAX_SVG_POINTS:
                raise ValueError('SVG clip generated point budget exceeded')
            shapes.extend(output.geometry_mm)
        materials[identifier] = tuple(shapes)
    return apply_svg_clips(document, rendered, materials)


def load_svg_file(path: Path | str, *, flip: bool = True,
                  object_type: str = 'geometry') -> SvgImportResult:
    """Read at most the source cap plus one byte, without modifying source data."""
    path = Path(path)
    with path.open('rb') as stream:
        source = stream.read(MAX_SVG_BYTES + 1)
    if len(source) > MAX_SVG_BYTES:
        raise ValueError('SVG source exceeds byte size limit')
    return import_svg_bytes(source, path.name, flip=flip, object_type=object_type)


def host_geometry(result: SvgImportResult, units: str) -> list[BaseGeometry]:
    """Convert authoritative millimetres once at the legacy object's unit boundary."""
    if type(result) is not SvgImportResult or units not in ('MM', 'IN'):
        raise ValueError('SVG host conversion requires a result and MM/IN units')
    if units == 'MM':
        return list(result.geometry_mm)
    return [affinity.scale(geometry, xfact=1 / 25.4, yfact=1 / 25.4, origin=(0., 0.))
            for geometry in result.geometry_mm]
