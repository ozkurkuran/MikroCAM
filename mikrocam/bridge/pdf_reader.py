"""Strict offline PDF page reader, bounded against the pinned pypdf 6.19.0 API."""
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import re

from mikrocam.core.pdf_models import (
    MAX_PDF_BYTES, MAX_PDF_STREAM_BYTES, MAX_PDF_PAGES, MAX_PDF_OPERATORS,
    PdfCommand, PdfDocumentInfo, PdfPageInfo, PdfProgram,
)

MAX_PAGE_TREE_ENTRIES = 512
MAX_PAGE_TREE_DEPTH = 32
_OPERATORS = frozenset(
    'q Q cm w J j M d m l c v y h re S s f F f* B B* b b* n W W* '
    'g G rg RG k K BT ET Tf TL Tc Tw Tz Tr Ts Td TD Tm T* ri i'.split()
)


def _libraries():
    try:
        import pypdf
        from pypdf import generic
    except ImportError as error:
        raise ValueError('PDF reading requires pypdf==6.19.0') from error
    if pypdf.__version__ != '6.19.0':
        raise ValueError('PDF reading requires the bounded pypdf==6.19.0 implementation')
    return pypdf, generic


def _source(data, name):
    if type(data) is not bytes or not 1 <= len(data) <= MAX_PDF_BYTES:
        raise ValueError('PDF source requires 1..16MiB of bytes')
    if re.match(rb'%PDF-1\.[0-7](?:\s|$)|%PDF-2\.0(?:\s|$)', data) is None:
        raise ValueError('PDF source requires a valid PDF header')
    # Validate the name before parsing any PDF objects.
    if type(name) is not str or not name or len(name.encode('utf-8')) > 256:
        raise ValueError('PDF source name requires 1..256 UTF-8 bytes')


def _tree(reader, generic):
    root = reader.root_object['/Pages'].get_object()
    pending = [(root, None, 0, False)]
    seen, counts = set(), {}
    while pending:
        node, parent, depth, exiting = pending.pop()
        identity = id(node)
        if exiting:
            count = sum(counts[id(child.get_object())] for child in node['/Kids'])
            if type(node.get('/Count')) is not generic.NumberObject or node['/Count'] != count:
                raise ValueError('PDF page tree Count disagrees with actual pages')
            counts[identity] = count
            continue
        if identity in seen or depth > MAX_PAGE_TREE_DEPTH:
            raise ValueError('PDF page tree cycle, shared child or excessive depth')
        seen.add(identity)
        if len(seen) > MAX_PAGE_TREE_ENTRIES or not isinstance(node, generic.DictionaryObject):
            raise ValueError('PDF page tree exceeds bounds or contains invalid nodes')
        if parent is not None and node.get('/Parent', generic.NullObject()).get_object() is not parent:
            raise ValueError('PDF page tree has an invalid Parent reference')
        kind = node.get('/Type')
        if kind == '/Page':
            counts[identity] = 1
        elif kind == '/Pages':
            children = node.get('/Kids')
            if not isinstance(children, generic.ArrayObject) or len(children) > MAX_PAGE_TREE_ENTRIES:
                raise ValueError('PDF page tree requires bounded Kids')
            pending.append((node, parent, depth, True))
            pending.extend((child.get_object(), node, depth + 1, False) for child in reversed(children))
        else:
            raise ValueError('PDF page tree contains an invalid node type')
    if not 1 <= counts[id(root)] <= MAX_PDF_PAGES:
        raise ValueError('PDF requires 1..128 pages')


@contextmanager
def _reader(data, name):
    _source(data, name)
    pypdf, generic = _libraries()
    limits = {
        key: MAX_PDF_STREAM_BYTES for key in (
            'maximum_declared_stream_length', 'array_based_stream_maximum_output_length',
            'zlib_maximum_output_length', 'lzw_maximum_output_length',
            'run_length_maximum_output_length', 'image_maximum_buffer_size',
        )
    }
    limits.update(page_tree_maximum_entries=MAX_PAGE_TREE_ENTRIES,
                  page_tree_maximum_depth=MAX_PAGE_TREE_DEPTH,
                  disable_legacy_handling=True, jbig2dec_binary=None)
    try:
        with pypdf.apply_configuration(**limits), BytesIO(data) as stream:
            parsed = pypdf.PdfReader(stream, strict=True)
            try:
                if parsed.is_encrypted:
                    raise ValueError('Encrypted PDF input is unsupported')
                _tree(parsed, generic)
                yield parsed, generic
            finally:
                parsed.close()
    except Exception as error:
        raise ValueError(f'PDF reading failed: {error}') from error


def _numeric(value, generic):
    if type(value) is generic.NumberObject:
        return int(value)
    if type(value) is generic.FloatObject:
        return float(value)
    raise ValueError('PDF numeric value has an unsupported type')


def _box(value, generic):
    value = value.get_object()
    if not isinstance(value, generic.ArrayObject) or len(value) != 4:
        raise ValueError('PDF page box requires four numbers')
    return tuple(_numeric(item.get_object(), generic) for item in value)


def _document(parsed, generic, data, name):
    facts = []
    for index, page in enumerate(parsed.pages):
        media = _box(page['/MediaBox'], generic)
        crop = _box(page.get('/CropBox', page['/MediaBox']), generic)
        crop = (max(media[0], crop[0]), max(media[1], crop[1]),
                min(media[2], crop[2]), min(media[3], crop[3]))
        rotation = page.get('/Rotate', generic.NumberObject(0)).get_object()
        if type(rotation) is not generic.NumberObject or int(rotation) % 90:
            raise ValueError('PDF page rotation requires an integer quarter turn')
        unit = _numeric(page.get('/UserUnit', generic.NumberObject(1)).get_object(), generic)
        facts.append(PdfPageInfo(index, media, crop, int(rotation) % 360, unit))
    return PdfDocumentInfo(name, sha256(data).hexdigest(), tuple(facts))


def _content(page, generic):
    annotations = page.get('/Annots', generic.NullObject()).get_object()
    if not isinstance(annotations, generic.NullObject):
        if not isinstance(annotations, generic.ArrayObject) or annotations:
            raise ValueError('PDF page annotations require an empty array; visible annotations are unsupported')
    if page.get('/Group') is not None:
        raise ValueError('PDF page transparency groups are unsupported')
    value = page.get('/Contents')
    if value is None or isinstance(value.get_object(), generic.NullObject):
        return b''
    value = value.get_object()
    streams = value if isinstance(value, generic.ArrayObject) else (value,)
    parts, size = [], 0
    for reference in streams:
        stream = reference.get_object()
        if not isinstance(stream, generic.StreamObject) or any(key in stream for key in ('/F', '/FFilter', '/FDecodeParms')):
            raise ValueError('PDF content requires internal streams')
        filters = stream.get('/Filter', [])
        filters = filters.get_object() if hasattr(filters, 'get_object') else filters
        filters = filters if isinstance(filters, (list, generic.ArrayObject)) else [filters]
        if any(item not in ('/FlateDecode', '/ASCIIHexDecode', '/ASCII85Decode', '/LZWDecode', '/RunLengthDecode') for item in filters):
            raise ValueError('PDF content uses an unsupported stream filter')
        chunk = stream.get_data()
        if chunk and not chunk.endswith(b'\n'):
            chunk += b'\n'
        size += len(chunk)
        if size > MAX_PDF_STREAM_BYTES:
            raise ValueError('PDF decoded content exceeds the 8MiB stream limit')
        parts.append(chunk)
    return b''.join(parts)


def _operand(value, generic):
    if type(value) in (generic.NumberObject, generic.FloatObject):
        return _numeric(value, generic)
    if type(value) in (generic.NameObject, generic.TextStringObject):
        return str(value)
    if type(value) is generic.ArrayObject and len(value) <= 64:
        return tuple(_numeric(item, generic) for item in value)
    raise ValueError('PDF command has an unsupported or oversized operand')


class _OperationList(list):
    """6.19.0 ContentStream._parse_content_stream appends directly to this list.

    Install AFTER construction/set_data (which replace _operations). Guard before
    each append; never mutate pypdf classes or process configuration globally.
    """
    def __init__(self, generic):
        super().__init__()
        self.generic = generic
        self.stream = None
        self.last_end = 0

    def append(self, operation):
        if len(self) >= MAX_PDF_OPERATORS:
            raise ValueError('PDF operator count exceeds the bounded limit')
        operands, operator = operation
        name = operator.decode('ascii')
        if name not in _OPERATORS:
            raise ValueError(f'Unsupported PDF operator: {name}')
        if len(operands) > 8:
            raise ValueError('PDF command has too many operands')
        command = PdfCommand(name, tuple(_operand(value, self.generic) for value in operands))
        super().append(command)
        self.last_end = self.stream.tell()


def _commands(data, parsed, generic):
    class BoundedContentStream(generic.ContentStream):
        # Pinned private hook: refuse BI before parsing/allocating inline image data.
        def _read_inline_image(self, stream):
            raise ValueError('Unsupported PDF inline image')

        def _parse_content_stream(self, stream):
            # 6.19.0 silently drops a final operand stack. Check bytes after the
            # last appended operator without duplicating its tokenizer.
            self._operations.stream = stream
            super()._parse_content_stream(stream)
            tail = stream.getvalue()[self._operations.last_end:]
            if re.sub(rb'%[^\r\n]*', b'', tail).strip():
                raise ValueError('PDF content has trailing operands without an operator')

    stream = generic.DecodedStreamObject()
    stream.set_data(data)
    content = BoundedContentStream(stream, parsed)
    content._operations = _OperationList(generic)
    return tuple(content.operations)


def inspect_pdf_bytes(data: bytes, name: str) -> PdfDocumentInfo:
    with _reader(data, name) as (parsed, generic):
        return _document(parsed, generic, data, name)


def read_pdf_page(data: bytes, name: str, page_index: int) -> PdfProgram:
    if type(page_index) is not int or not 0 <= page_index < MAX_PDF_PAGES:
        raise ValueError('PDF page index requires an integer from 0 to 127')
    with _reader(data, name) as (parsed, generic):
        document = _document(parsed, generic, data, name)
        if page_index >= len(document.pages):
            raise ValueError('PDF selected page does not exist')
        commands = _commands(_content(parsed.pages[page_index], generic), parsed, generic)
        return PdfProgram(document, page_index, commands)
