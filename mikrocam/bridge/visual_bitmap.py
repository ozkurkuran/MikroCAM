"""Optional Pillow boundary: offline bitmap inspection and physical viewport sampling."""
from contextlib import contextmanager
from collections.abc import Iterator
from io import BytesIO
import math
import warnings
from mikrocam.core.visual import MAX_PIXELS, MAX_SOURCE_BYTES, PreparationSettings, RasterFrame, RasterGrid, SourceAsset, SourceInfo

FORMATS = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'BMP': 'image/bmp',
           'TIFF': 'image/tiff', 'WEBP': 'image/webp', 'GIF': 'image/gif'}


@contextmanager
def bitmap_reader(data: bytes) -> Iterator[object]:
    if type(data) is not bytes or not 1 <= len(data) <= MAX_SOURCE_BYTES:
        raise ValueError('SOURCE_TOO_LARGE')
    try:
        from PIL import Image
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in FORMATS: raise ValueError('UNSUPPORTED_SOURCE_FORMAT')
                if image.width * image.height > MAX_PIXELS: raise ValueError('RASTER_LIMIT_EXCEEDED')
                yield image
    except ImportError as error:
        raise ValueError('BITMAP_UNAVAILABLE: install requirements-visual.txt') from error
    except (OSError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise ValueError(f'SOURCE_DECODE_FAILED: {error}') from error


def inspect_bitmap(data: bytes, page_index: int = 0) -> SourceInfo:
    with bitmap_reader(data) as image:
        from PIL import ImageOps
        count = getattr(image, 'n_frames', 1)
        if type(page_index) is not int or not 0 <= page_index < count: raise ValueError('PAGE_OUT_OF_RANGE')
        image.seek(page_index)
        oriented = ImageOps.exif_transpose(image)
        native = oriented.size
        dpi = image.info.get('dpi')
        size = (native[0] * .05, native[1] * .05)
        origin = 'default_508dpi'
        if isinstance(dpi, (tuple, list)) and len(dpi) == 2 and all(
            type(v) in (int, float) and math.isfinite(v) and v > 0 for v in dpi
        ):
            size = (native[0] * 25.4 / dpi[0], native[1] * 25.4 / dpi[1])
            origin = 'metadata'
        notes = () if image.info.get('icc_profile') else ('SOURCE_ASSUMED_SRGB',)
        return SourceInfo('bitmap', FORMATS[image.format], count, native, size, origin, notes)


def _srgb(image):
    from PIL import Image
    profile = image.info.get('icc_profile')
    if image.mode.startswith('I;16'):
        import numpy as np
        gray = np.asarray(image, dtype=np.uint32)
        image = Image.fromarray(((gray * 255 + 32767) // 65535).astype('uint8'))
    elif image.mode in ('I', 'F'):
        raise ValueError('SOURCE_DECODE_FAILED: unsupported grayscale sample range')
    if not profile: return image.convert('RGBA')
    from PIL import ImageCms
    try:
        input_profile = ImageCms.ImageCmsProfile(BytesIO(profile))
        output_profile = ImageCms.createProfile('sRGB')
        alpha = image.convert('RGBA').getchannel('A')
        color = image if image.mode in ('RGB', 'CMYK', 'LAB', 'L') else image.convert('RGB')
        converted = ImageCms.profileToProfile(color, input_profile, output_profile, outputMode='RGB')
        converted.putalpha(alpha)
        return converted
    except (OSError, ValueError, ImageCms.PyCMSError) as error:
        raise ValueError('SOURCE_DECODE_FAILED: invalid or unsupported color profile') from error


def sample_image(image: object, preparation: PreparationSettings, grid: RasterGrid,
                 one_bit: bool = False) -> RasterFrame:
    """Sample the requested viewport without stretching fractional padding into content."""
    import numpy as np
    from PIL import Image
    image = image.convert('RGBA')
    if preparation.crop_rect is not None:
        x0, y0, x1, y1 = preparation.crop_rect
        if x1 > image.width or y1 > image.height: raise ValueError('crop_rect exceeds source bounds')
        image = image.crop((x0, y0, x1, y1))
    if preparation.quarter_turns:
        image = image.transpose((Image.Transpose.ROTATE_270, Image.Transpose.ROTATE_180,
                                 Image.Transpose.ROTATE_90)[preparation.quarter_turns - 1])
    if preparation.mirror_x: image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if preparation.mirror_y: image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    valid = grid.valid_area()
    if not valid.any():
        return RasterFrame(np.full((grid.height_px, grid.width_px, 4), 255, dtype=np.uint8), grid, valid)
    extent_w = image.width * grid.canvas_width_mm / grid.requested_width_mm
    extent_h = image.height * grid.canvas_height_mm / grid.requested_height_mm
    # Pad the source before resize so floating viewport extents remain meaningful.
    pad_size = (math.ceil(extent_w), math.ceil(extent_h))
    estimate = (pad_size[0] * pad_size[1] + image.width * image.height) * 8 + grid.width_px * grid.height_px * 16
    if estimate > 1024**3: raise ValueError('RASTER_LIMIT_EXCEEDED: working memory exceeds 1GiB')
    if pad_size != image.size:
        padded = Image.new('RGBA', pad_size, 'white'); padded.paste(image, (0, 0)); image = padded
    target = (grid.width_px, grid.height_px)
    if image.size != target or (extent_w, extent_h) != target:
        method = Image.Resampling.NEAREST if one_bit else Image.Resampling.LANCZOS
        image = image.resize(target, method, box=(0, 0, extent_w, extent_h))
    return RasterFrame(np.array(image, dtype=np.uint8), grid, valid)


def render_bitmap(source: SourceAsset, preparation: PreparationSettings, grid: RasterGrid) -> RasterFrame:
    from PIL import ImageOps
    with bitmap_reader(source.data) as image:
        if source.info.media_type != FORMATS[image.format]: raise ValueError('SOURCE_DECODE_FAILED: media type mismatch')
        if source.page_index >= getattr(image, 'n_frames', 1): raise ValueError('PAGE_OUT_OF_RANGE')
        image.seek(source.page_index)
        if image.width * image.height > MAX_PIXELS: raise ValueError('RASTER_LIMIT_EXCEEDED')
        one_bit = image.mode == '1'
        image = ImageOps.exif_transpose(image)
        return sample_image(_srgb(image), preparation, grid, one_bit)
