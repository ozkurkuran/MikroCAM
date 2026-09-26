"""Order existing hatch exposures without modifying their geometry."""
from mikrocam.core.laser_paths import (CancelCheck, LaserPath, check_cancelled,
                                      check_path_count, validate_interlace_n)


def interlace_paths(paths: tuple[LaserPath, ...], n: int,
                    cancelled: CancelCheck = None) -> tuple[LaserPath, ...]:
    """Keep contours first and sort occupied hatch groups by family and residue."""
    validate_interlace_n(n)
    if not isinstance(paths, tuple):
        raise ValueError('Interlace paths must be a tuple of LaserPath values')
    check_path_count(len(paths))
    check_cancelled(cancelled)
    contours = []
    hatch = []
    for position, path in enumerate(paths):
        check_cancelled(cancelled)
        if not isinstance(path, LaserPath):
            raise ValueError('Interlace paths must be LaserPath values')
        if n == 1:
            continue
        if path.role == 'contour':
            contours.append(path)
        else:
            key = (path.hatch_family, path.scan_index % n, path.scan_index, position)
            hatch.append((key, path))
    if n == 1:
        check_cancelled(cancelled)
        return paths
    hatch.sort(key=lambda entry: entry[0])
    check_cancelled(cancelled)
    return tuple(contours) + tuple(path for _, path in hatch)
