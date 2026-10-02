"""Canonical lossless mask PNG boundary, shared by job storage and image exports."""
from io import BytesIO
from mikrocam.core.visual import BurnMask, MAX_SOURCE_BYTES, RasterGrid


def encode_mask_png(mask: BurnMask) -> bytes:
    import numpy as np
    from PIL import Image
    image = Image.fromarray(np.where(mask.burn, 0, 255).astype(np.uint8)).convert('1')
    stream = BytesIO()
    image.save(stream, format='PNG', dpi=(mask.grid.requested_dpi, mask.grid.requested_dpi))
    return stream.getvalue()


def decode_mask_png(data: bytes, grid: RasterGrid) -> BurnMask:
    import numpy as np
    from PIL import Image
    if type(data) is not bytes or not 1 <= len(data) <= MAX_SOURCE_BYTES: raise ValueError('RECIPE_CORRUPT: PNG size')
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != 'PNG' or image.size != (grid.width_px, grid.height_px) or image.mode not in ('1', 'L'):
                raise ValueError('RECIPE_CORRUPT: PNG grid, format or mode')
            gray = np.array(image.convert('L'))
            if np.any((gray != 0) & (gray != 255)): raise ValueError('RECIPE_CORRUPT: PNG is not binary')
            return BurnMask(gray == 0, grid)
    except (OSError, SyntaxError) as error:
        raise ValueError(f'RECIPE_CORRUPT: {error}') from error
