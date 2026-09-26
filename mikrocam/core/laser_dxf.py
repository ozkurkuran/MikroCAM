"""Narrow ASCII R2000 DXF writer for planar laser exposure polylines only."""
from .laser_paths import CancelCheck, LaserPath, check_cancelled, check_path_count


def _tags(pairs: tuple[tuple[int, object], ...]) -> str:
    return ''.join(f'{code}\n{value}\n' for code, value in pairs)


def _header() -> str:
    return _tags(((0, 'SECTION'), (2, 'HEADER'), (9, '$ACADVER'), (1, 'AC1015'),
                  (9, '$INSUNITS'), (70, 4), (9, '$MEASUREMENT'), (70, 1), (0, 'ENDSEC')))


def _layers(layer: str) -> str:
    parts = [_tags(((0, 'SECTION'), (2, 'TABLES'), (0, 'TABLE'), (2, 'LAYER'),
                    (5, '2'), (100, 'AcDbSymbolTable'), (70, 2)))]
    for name, handle in (('0', '10'), (layer, '11')):
        parts.append(_tags(((0, 'LAYER'), (5, handle), (330, '2'), (100, 'AcDbSymbolTableRecord'),
                             (100, 'AcDbLayerTableRecord'), (2, name), (70, 0), (62, 7), (6, 'CONTINUOUS'))))
    parts.append(_tags(((0, 'ENDTAB'), (0, 'ENDSEC'))))
    return ''.join(parts)


def _polyline(path: LaserPath, layer: str, handle: str) -> str:
    closed = path.points[0] == path.points[-1]
    points = path.points[:-1] if closed else path.points
    parts = [_tags(((0, 'LWPOLYLINE'), (5, handle), (100, 'AcDbEntity'), (8, layer),
                    (100, 'AcDbPolyline'), (90, len(points)), (70, int(closed)), (38, 0)))]
    for x, y in points:
        parts.append(_tags(((10, format(x, '.17g')), (20, format(y, '.17g')))))
    return ''.join(parts)


def dxf_document(paths: tuple[LaserPath, ...], pass_index: int, cancelled: CancelCheck = None) -> str:
    """Preserve placed XY and entity order, with mm metadata and an ordinal layer."""
    if not isinstance(paths, tuple) or not paths:
        raise ValueError('DXF requires a nonempty tuple of laser paths')
    if type(pass_index) is not int or pass_index < 1:
        raise ValueError('DXF pass index must be a positive integer')
    check_path_count(len(paths))
    layer = f'PASS_{pass_index:03d}'
    parts = [_header(), _layers(layer), _tags(((0, 'SECTION'), (2, 'ENTITIES')))]
    for index, path in enumerate(paths):
        check_cancelled(cancelled)
        if not isinstance(path, LaserPath):
            raise ValueError('DXF paths must be LaserPath values')
        parts.append(_polyline(path, layer, format(0x100+index, 'X')))
    parts.append(_tags(((0, 'ENDSEC'), (0, 'EOF'))))
    check_cancelled(cancelled)
    return ''.join(parts)
