"""Physical clip frames and intersections over unchanged source-path evidence."""
import math

from shapely import get_num_coordinates, union_all, STRtree
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry

from .placement import Affine2D
from .svg_models import MAX_SVG_POINTS, SvgClip, SvgDocument, SvgRendered, SvgNotice, validate_affine
from .svg_transform import apply_svg_point, compose_affine

MAX_CLIP_SEGMENTS = 2048
MAX_CLIP_PAIRS = 32768


def _preflight(geometries: tuple[BaseGeometry, ...]) -> None:
    pending, lines = list(geometries), []
    while pending:
        geometry = pending.pop()
        if geometry.is_empty:
            continue
        if geometry.geom_type.startswith('Multi') or geometry.geom_type == 'GeometryCollection':
            pending.extend(geometry.geoms)
            continue
        if geometry.geom_type == 'Polygon':
            pending.extend((geometry.exterior, *geometry.interiors))
            continue
        if geometry.geom_type not in ('LineString', 'LinearRing'):
            continue
        if int(get_num_coordinates(geometry)) > 2 * MAX_CLIP_SEGMENTS:
            raise ValueError('SVG clip topology segment budget exceeded; simplify the source')
        points = tuple(geometry.coords)
        for first, second in zip(points, points[1:]):
            if first != second:
                if len(lines) >= MAX_CLIP_SEGMENTS:
                    raise ValueError('SVG clip topology segment budget exceeded; simplify the source')
                lines.append(LineString((first, second)))
    tree, pairs = STRtree(lines), 0
    for index, line in enumerate(lines):
        pairs += sum(int(other) > index for other in tree.query(line, predicate='intersects'))
        if pairs > MAX_CLIP_PAIRS:
            raise ValueError('SVG clip intersection budget exceeded; simplify the source')


def _intersection(geometry: BaseGeometry, mask: BaseGeometry) -> tuple[BaseGeometry, ...]:
    if mask.is_empty:
        return ()
    _preflight((geometry, mask))
    pending, retained = [geometry.intersection(mask)], []
    polygon = geometry.area > 0
    while pending:
        item = pending.pop()
        if item.is_empty:
            continue
        if item.geom_type.startswith('Multi') or item.geom_type == 'GeometryCollection':
            pending.extend(item.geoms)
        elif (item.area > 0) if polygon else (item.length > 0):
            retained.append(item)
    return tuple(retained)


def _inverse(matrix: Affine2D) -> Affine2D:
    a,b,d,e,x,y=matrix
    determinant=a*e-b*d
    result=(e/determinant,-b/determinant,-d/determinant,a/determinant,
            (b*y-e*x)/determinant,(d*x-a*y)/determinant)
    validate_affine(result)
    return result


def clip_application_matrix(clip: SvgClip, document: SvgDocument,
                            rendered: tuple[SvgRendered, ...]) -> Affine2D:
    """Resolve an entire affected subtree's unclipped, unstroked bounding box in its own frame."""
    if type(clip) is not SvgClip or type(document) is not SvgDocument or len(rendered)!=len(document.elements):
        raise ValueError('Clip frame requires matching immutable SVG source/results')
    if clip.units=='userSpaceOnUse':
        return clip.matrix
    inverse=_inverse(clip.matrix)
    bounds=None
    count=0
    for element,result in zip(document.elements,rendered):
        if not any(c.application_id==clip.application_id for c in element.clips):
            continue
        for path in result.paths_mm:
            count+=len(path.points)
            if count>MAX_SVG_POINTS:
                raise ValueError('SVG clip bounding-box coordinate budget exceeded')
            for point in path.points:
                x,y=apply_svg_point(inverse,point)
                bounds=(x,y,x,y) if bounds is None else (min(bounds[0],x),min(bounds[1],y),
                                                        max(bounds[2],x),max(bounds[3],y))
    if bounds is None or bounds[0]==bounds[2] or bounds[1]==bounds[3]:
        raise ValueError('SVG objectBoundingBox clipping requires nonzero unclipped width and height')
    bbox=(bounds[2]-bounds[0],0.,0.,bounds[3]-bounds[1],bounds[0],bounds[1])
    return compose_affine(clip.matrix,bbox)


def apply_svg_clips(document: SvgDocument, rendered: tuple[SvgRendered, ...],
                     clip_materials: dict[str, tuple[BaseGeometry, ...]]) -> tuple[SvgRendered, ...]:
    """Intersect physical clip silhouettes without changing original transformed path facts."""
    if type(document) is not SvgDocument or type(rendered) is not tuple or len(rendered)!=len(document.elements):
        raise ValueError('SVG clipping requires matching immutable source/results')
    if any(type(r) is not SvgRendered for r in rendered) or type(clip_materials) is not dict:
        raise ValueError('SVG clipping requires immutable render results and clip material mapping')
    expected={clip.application_id for element in document.elements for clip in element.clips}
    if clip_materials.keys()!=expected:
        raise ValueError('SVG clip materials must match every application exactly')
    masks={}
    count=0
    for identifier,geometries in clip_materials.items():
        if type(geometries) is not tuple or any(not isinstance(g,BaseGeometry) for g in geometries):
            raise ValueError('SVG clip material requires immutable geometry tuples')
        for geometry in geometries:
            count+=int(get_num_coordinates(geometry))
            if count>MAX_SVG_POINTS or not geometry.is_valid or geometry.has_z or geometry.has_m:
                raise ValueError('SVG clip material exceeds validity/coordinate budget')
            if any(not math.isfinite(v) or abs(v)>1e9 for v in geometry.bounds):
                raise ValueError('SVG clip material exceeds finite coordinate bounds')
        _preflight(geometries)
        masks[identifier]=union_all(geometries)
    output=[]
    for element,result in zip(document.elements,rendered):
        geometries=result.geometry_mm
        for clip in element.clips:
            mask=masks[clip.application_id]
            geometries=tuple(fragment for geometry in geometries for fragment in _intersection(geometry,mask))
        notices=result.notices
        if element.clips:
            notices=(notices+(SvgNotice('clipped-material','Local clipping applied; retained paths are original source evidence.',
                                       element.element_id),))[:200]
        clipped=SvgRendered(result.paths_mm,geometries,notices)
        count+=sum(len(p.points) for p in clipped.paths_mm)+sum(int(get_num_coordinates(g)) for g in geometries)
        if count>MAX_SVG_POINTS:
            raise ValueError('SVG clipped result exceeds generated coordinate budget')
        output.append(clipped)
    return tuple(output)
