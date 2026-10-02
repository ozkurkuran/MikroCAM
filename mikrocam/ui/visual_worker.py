"""File/render tasks use detached arguments and return results through Qt signals."""
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path
import threading
from PyQt6 import QtCore
from mikrocam.core.visual import MAX_SOURCE_BYTES, SourceAsset, build_grid
from mikrocam.core.visual_preview import frame_preview, preview_images
from mikrocam.core.laser_paths import PlanningCancelled, check_cancelled
from mikrocam.importers.visual_source import detect_visual_kind
from mikrocam.bridge.visual_bitmap import inspect_bitmap
from mikrocam.bridge.visual_workflow import prepare_visual_job
from mikrocam.bridge.visual_recipe import load_visual_recipe, save_visual_recipe, job_to_payload, job_from_payload
from mikrocam.bridge.visual_export import export_png_package
from mikrocam.laser.visual_plan import build_plan


class VisualWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(int, str, object)
    failed = QtCore.pyqtSignal(int, str)
    cancelled = QtCore.pyqtSignal(int)

    def __init__(self, operation: str, revision: int, args: tuple, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.operation, self.revision, self.args = operation, revision, args
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def run(self) -> None:
        try:
            check_cancelled(self.is_cancelled)
            result = self._execute()
            check_cancelled(self.is_cancelled)
            self.completed.emit(self.revision, self.operation, result)
        except PlanningCancelled:
            self.cancelled.emit(self.revision)
        except Exception as error:
            if self.is_cancelled(): self.cancelled.emit(self.revision)
            else: self.failed.emit(self.revision, str(error))

    def _inspect(self, data: bytes, page: int = 0):
        kind = detect_visual_kind(data)
        if kind == 'bitmap': return inspect_bitmap(data, page)
        if kind == 'svg':
            from mikrocam.bridge.visual_svg import inspect_svg
            return inspect_svg(data)
        from .visual_pdf import inspect_pdf
        return inspect_pdf(data, page)

    def _execute(self):
        if self.operation == 'open':
            path = Path(self.args[0])
            with path.open('rb') as stream: data = stream.read(MAX_SOURCE_BYTES + 1)
            return SourceAsset(path.name, data, self._inspect(data))
        if self.operation == 'page':
            source, page = self.args
            return replace(source, info=self._inspect(source.data, page), page_index=page)
        if self.operation == 'geometry':
            from mikrocam.bridge.visual_geometry import snapshot_geometry
            geometry, units, roi, name = self.args
            return snapshot_geometry(geometry, units, roi, name), roi
        if self.operation == 'prepare':
            source, preparation, settings, placement, recipe = self.args
            frame, renderer = None, None
            if source.info.kind == 'pdf':
                from .visual_pdf import render_pdf_page
                frame = render_pdf_page(source, preparation, build_grid(preparation))
                renderer = ('QtPdf', version('PyQt6-Qt6'))
            source_preview = []
            job = prepare_visual_job(source, preparation, settings, placement, recipe, self.revision,
                                     cancelled=self.is_cancelled, rendered_frame=frame, renderer=renderer,
                                     frame_ready=lambda value: source_preview.append(frame_preview(value)))
            return self._result(job, source_preview[0])
        if self.operation == 'save':
            save_visual_recipe(*self.args, cancelled=self.is_cancelled); return self.args[1]
        if self.operation == 'load':
            job = replace(load_visual_recipe(*self.args, cancelled=self.is_cancelled), revision=self.revision)
            return self._result(job)
        if self.operation == 'project_load':
            job = replace(job_from_payload(self.args[0]), revision=self.revision)
            return self._result(job)
        if self.operation == 'png':
            export_png_package(*self.args, cancelled=self.is_cancelled); return self.args[2]
        if self.operation == 'project': return job_to_payload(self.args[0])
        raise ValueError('Unknown visual worker operation')

    def _result(self, job, source=None):
        images = preview_images(job.mask, job.interlace.count, cancelled=self.is_cancelled)
        images['source'] = source
        return job, build_plan(job.mask, job.interlace, job.revision), images
