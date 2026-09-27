"""Finite selected-page PDF vector interpreter; no reader, UI or host dependencies."""
from copy import copy
from mikrocam.core.pdf_models import (MAX_PDF_POINTS, PdfProgram, PdfOptions, PdfImportReport, PdfGeometryResult,
                                     geometry_facts, geometry_sha256)
from mikrocam.core.pdf_frame import pdf_page_frame
from mikrocam.core.pdf_geometry import PdfCanvas, PdfGraphicsState, polygon_parts
from mikrocam.core.pdf_paths import PdfPaths
from mikrocam.core.svg_transform import compose_affine, apply_svg_point

_NUMERIC = {'cm': 6, 'w': 1, 'J': 1, 'j': 1, 'M': 1, 'm': 2, 'l': 2,
            'c': 6, 'v': 4, 'y': 4, 're': 4, 'g': 1, 'G': 1, 'rg': 3,
            'RG': 3, 'k': 4, 'K': 4, 'TL': 1, 'Tc': 1, 'Tw': 1, 'Tz': 1,
            'Tr': 1, 'Ts': 1, 'Td': 2, 'TD': 2, 'Tm': 6, 'i': 1}
_EMPTY = {'q', 'Q', 'h', 'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n',
          'W', 'W*', 'BT', 'ET', 'T*'}
_PATH = {'m', 'l', 'c', 'v', 'y', 'h', 're', 'S', 's', 'f', 'F', 'f*',
         'B', 'B*', 'b', 'b*', 'n', 'W', 'W*'}
_TEXT_POSITION = {'Td', 'TD', 'Tm', 'T*'}
_TEXT_STATE = {'Tf', 'TL', 'Tc', 'Tw', 'Tz', 'Tr', 'Ts'}


def _grammar(operator: str, values: tuple) -> None:
    if operator in _NUMERIC:
        if len(values) != _NUMERIC[operator] or any(type(v) not in (int, float) for v in values):
            raise ValueError(f'PDF {operator} requires {_NUMERIC[operator]} numeric operands')
    elif operator in _EMPTY:
        if values:
            raise ValueError(f'PDF {operator} does not take operands')
    elif operator == 'd':
        if len(values) != 2 or values[0] != () or type(values[1]) not in (int, float) or values[1] != 0:
            raise ValueError('PDF supports only solid strokes (empty dash and zero phase)')
    elif operator == 'Tf':
        if (len(values) != 2 or type(values[0]) is not str or not values[0].startswith('/')
                or type(values[1]) not in (int, float) or values[1] <= 0):
            raise ValueError('PDF Tf requires a font name and positive size')
    elif operator == 'ri':
        if len(values) != 1 or values[0] not in ('/AbsoluteColorimetric', '/RelativeColorimetric',
                                               '/Saturation', '/Perceptual'):
            raise ValueError('PDF rendering intent is unsupported')
    else:
        raise ValueError(f'PDF operator {operator!r} is unsupported; convert artwork to simple opaque paths')


def _setting(state: PdfGraphicsState, operator: str, values: tuple) -> None:
    if operator == 'cm':
        a, b, c, d, e, f = values
        state.matrix = compose_affine(state.matrix, (a, c, b, d, e, f))
    elif operator in ('J', 'j'):
        if values[0] not in (0, 1, 2) or values[0] != int(values[0]):
            raise ValueError('PDF line cap/join must be 0, 1 or 2')
        setattr(state, 'cap' if operator == 'J' else 'join', int(values[0]))
    elif operator in ('w', 'M'):
        if values[0] <= 0 or (operator == 'M' and not 1 <= values[0] <= 1000):
            raise ValueError('PDF line width must be positive; miter limit must be within 1..1000')
        setattr(state, 'width' if operator == 'w' else 'miter', values[0])
    elif operator in ('g', 'G', 'rg', 'RG', 'k', 'K'):
        if any(not 0 <= value <= 1 for value in values):
            raise ValueError('PDF opaque colour components must be within 0..1')
        white = all(value == (0 if operator in ('k', 'K') else 1) for value in values)
        setattr(state, 'stroke_white' if operator.isupper() else 'fill_white', white)
    elif operator == 'Tr' and (values[0] not in range(8) or values[0] != int(values[0])):
        raise ValueError('PDF text rendering mode must be 0..7')
    elif operator == 'i' and not 0 <= values[0] <= 100:
        raise ValueError('PDF flatness must be within 0..100')


def _path(paths: PdfPaths, state: PdfGraphicsState, operator: str, values: tuple) -> None:
    if operator in ('m', 'l'):
        point = apply_svg_point(state.matrix, values)
        paths.move(point) if operator == 'm' else paths.line(point)
    elif operator == 're':
        paths.rectangle(values, state.matrix)
    elif operator == 'h':
        paths.close()
    else:
        points = tuple(apply_svg_point(state.matrix, values[i:i + 2]) for i in range(0, len(values), 2))
        if operator == 'v':
            points = (paths.current(), *points)
        elif operator == 'y':
            points = (*points, points[-1])
        paths.curve(points)


class _Interpreter:
    def __init__(self, program: PdfProgram, options: PdfOptions) -> None:
        self.program, self.options = program, options
        self.page = program.document.pages[program.page_index]
        self.matrix, self.viewport = pdf_page_frame(self.page, options)
        self.canvas, self.paths = PdfCanvas(self.viewport), PdfPaths()
        self.state = PdfGraphicsState(self.matrix, self.canvas.page_clip)
        self.stack: list[PdfGraphicsState] = []
        self.pending_clip: str | None = None
        self.in_text = False

    def execute(self, operator: str, values: tuple) -> None:
        _grammar(operator, values)
        if self.in_text and operator in _PATH:
            raise ValueError('PDF path operators are not permitted inside text objects')
        if operator in ('BT', 'ET'):
            if self.in_text == (operator == 'BT'):
                raise ValueError('PDF text object nesting is unbalanced')
            self.in_text = operator == 'BT'
        elif operator in _TEXT_POSITION and not self.in_text:
            raise ValueError('PDF text positioning requires a text object')
        elif operator == 'q':
            if len(self.stack) >= 64:
                raise ValueError('PDF graphics state depth exceeded')
            self.stack.append(copy(self.state))
        elif operator == 'Q':
            if not self.stack:
                raise ValueError('PDF graphics state restore underflow')
            self.state = self.stack.pop()
        elif operator in ('W', 'W*'):
            if self.pending_clip is not None:
                raise ValueError('PDF clipping operator repeated before path end')
            self.pending_clip = 'evenodd' if operator == 'W*' else 'nonzero'
        elif operator in ('S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'):
            if operator in ('s', 'b', 'b*'):
                self.paths.close()
            self.canvas.finish_path(self.paths.take(), self.state, operator, self.pending_clip)
            self.pending_clip = None
        elif operator in ('m', 'l', 'c', 'v', 'y', 'h', 're'):
            _path(self.paths, self.state, operator, values)
        else:
            _setting(self.state, operator, values)

    def result(self) -> PdfGeometryResult:
        if self.stack or self.in_text or self.pending_clip is not None or self.paths.unfinished():
            raise ValueError('PDF has unfinished path, clipping, text or graphics state')
        geometry = polygon_parts(self.canvas.material)
        if not geometry:
            raise ValueError('PDF selected page/crop contains empty supported material')
        bounds, points = geometry_facts(geometry)
        if self.paths.point_count + points > MAX_PDF_POINTS:
            raise ValueError('PDF combined sample/output point budget exceeded')
        document = self.program.document
        report = PdfImportReport(document.source_name, document.source_sha256, len(document.pages),
                                 self.page, self.options, self.viewport, self.matrix, bounds,
                                 len(geometry), self.paths.path_count, points, geometry_sha256(geometry))
        return PdfGeometryResult(report, geometry)


def render_pdf_program(program: PdfProgram, options: PdfOptions) -> PdfGeometryResult:
    """Render one bounded supported page atomically into physical polygon material."""
    if type(program) is not PdfProgram or type(options) is not PdfOptions:
        raise ValueError('PDF rendering requires a validated program and options')
    try:
        interpreter = _Interpreter(program, options)
        for command in program.commands:
            interpreter.execute(command.operator, command.operands)
        return interpreter.result()
    except (ValueError, ArithmeticError) as error:
        raise ValueError(f'PDF vector import: {error}') from error
