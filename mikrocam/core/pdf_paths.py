"""Bounded current PDF path; coordinates are frozen when each command executes."""
from .placement import Affine2D, Point2D
from .pdf_models import MAX_PDF_POINTS
from .svg_models import SvgPath
from .svg_curves import flatten_cubic
from .svg_transform import apply_svg_point


class PdfPaths:
    """Current path is independent of the graphics-state save/restore stack."""

    def __init__(self) -> None:
        self.paths: list[SvgPath] = []
        self.points: list[Point2D] = []
        self.closed = False
        self.path_count = 0
        self.point_count = 0

    def _append(self, values: list[Point2D]) -> None:
        self.point_count += len(values)
        if self.point_count > MAX_PDF_POINTS or len(self.points) + len(values) > 100000:
            raise ValueError('PDF path point budget exceeded')
        self.points.extend(values)

    def _flush(self) -> None:
        if len(self.points) >= 2:
            self.paths.append(SvgPath(tuple(self.points), self.closed))
        self.points = []
        self.closed = False

    def move(self, point: Point2D) -> None:
        self._flush()
        self.path_count += 1
        if self.path_count > 10000:
            raise ValueError('PDF subpath budget exceeded')
        self._append([point])

    def current(self) -> Point2D:
        if not self.points:
            raise ValueError('PDF path command requires a current point')
        return self.points[-1]

    def _continue(self) -> None:
        point = self.current()
        if self.closed:
            self.move(point)

    def line(self, point: Point2D) -> None:
        self._continue()
        self._append([point])

    def curve(self, controls: tuple[Point2D, Point2D, Point2D]) -> None:
        self._continue()
        points = flatten_cubic(self.current(), *controls, 0.005)
        self._append(list(points[1:]))

    def close(self) -> None:
        self.current()
        if not self.closed:
            self._append([self.points[0]])
            while len(self.points) < 4:
                self._append([self.points[0]])
            self.closed = True

    def rectangle(self, values: tuple[float, ...], matrix: Affine2D) -> None:
        x, y, width, height = values
        self.move(apply_svg_point(matrix, (x, y)))
        for point in ((x + width, y), (x + width, y + height), (x, y + height)):
            self.line(apply_svg_point(matrix, point))
        self.close()

    def take(self) -> tuple[SvgPath, ...]:
        self._flush()
        paths = tuple(self.paths)
        self.paths.clear()
        return paths

    def unfinished(self) -> bool:
        return bool(self.paths or self.points)
