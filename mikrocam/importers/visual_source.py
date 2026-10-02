"""Bounded source signature dispatch; independent of native image/PDF libraries."""
from mikrocam.core.visual import MAX_SOURCE_BYTES


def detect_visual_kind(data: bytes) -> str:
    if type(data) is not bytes or not 1 <= len(data) <= MAX_SOURCE_BYTES: raise ValueError('SOURCE_TOO_LARGE')
    head = data[:4096].lstrip(b'\xef\xbb\xbf \t\r\n')
    if head.startswith(b'%PDF-'): return 'pdf'
    if head.startswith(b'<'): return 'svg'  # The SVG validator checks the complete XML root.
    if head.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'BM', b'II*\0', b'MM\0*', b'GIF87a', b'GIF89a')):
        return 'bitmap'
    if head.startswith(b'RIFF') and head[8:12] == b'WEBP': return 'bitmap'
    raise ValueError('UNSUPPORTED_SOURCE_FORMAT')
