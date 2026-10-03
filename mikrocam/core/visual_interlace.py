"""Original-index raster partitioning and bounded group statistics."""
import numpy as np
from .visual import BurnMask, integer_range


def partition_rows(height: int, count: int) -> tuple[range, ...]:
    integer_range(height, 0, 2**63 - 1, 'height')
    integer_range(count, 1, 8, 'INVALID_INTERLACE_COUNT')
    return tuple(range(k, height, count) for k in range(count))


def base_order(count: int, mode: str) -> tuple[int, ...]:
    integer_range(count, 1, 8, 'INVALID_INTERLACE_COUNT')
    if mode == 'sequential': return tuple(range(count))
    if mode != 'mixed': raise ValueError('Invalid order_mode')
    bits = (count - 1).bit_length()
    order = [int(format(i, f'0{bits}b')[::-1], 2) if bits else 0 for i in range(1 << bits)]
    return tuple(i for i in order if i < count)


def source_row_direction(row_index: int) -> str:
    integer_range(row_index, 0, 2**63 - 1, 'row_index')
    return 'left_to_right' if row_index % 2 == 0 else 'right_to_left'


def materialize_group(mask: BurnMask, group_index: int, count: int) -> BurnMask:
    integer_range(count, 1, 8, 'INVALID_INTERLACE_COUNT')
    integer_range(group_index, 0, count - 1, 'group_index')
    if count == 1: return mask
    data = np.zeros(mask.burn.shape, dtype=bool)
    data[group_index::count] = mask.burn[group_index::count]
    return BurnMask(data, mask.grid)


def group_statistics(mask: BurnMask, count: int) -> tuple[tuple[int, int], ...]:
    partition_rows(mask.grid.height_px, count)
    black_by_row = np.count_nonzero(mask.burn, axis=1)
    return tuple((int(np.count_nonzero(black_by_row[k::count])), int(black_by_row[k::count].sum()))
                 for k in range(count))
