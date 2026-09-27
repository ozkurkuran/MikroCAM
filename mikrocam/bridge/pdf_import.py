"""Bounded PDF source review and atomic normal Geometry publication."""
from hashlib import sha256
from pathlib import Path
from shapely import affinity
from mikrocam.core.pdf_models import (MAX_PDF_BYTES, PdfDocumentInfo, PdfOptions,
                                     PdfImportReview, PdfImportReport)
from mikrocam.core.pdf_report_codec import report_to_dict, report_from_dict
from mikrocam.importers.pdf_program import render_pdf_program
from .pdf_reader import inspect_pdf_bytes, read_pdf_page


def _bytes(path: Path | str) -> bytes:
    try:
        with Path(path).open('rb') as stream:
            data = stream.read(MAX_PDF_BYTES + 1)
    except (OSError, ValueError) as error:
        raise ValueError(f'PDF source could not be read: {error}') from error
    if not 1 <= len(data) <= MAX_PDF_BYTES:
        raise ValueError('PDF source requires 1..16MiB')
    return data


def inspect_pdf_file(path: Path | str) -> PdfDocumentInfo:
    """Inspect page metadata from bounded immutable bytes."""
    return inspect_pdf_bytes(_bytes(path), Path(path).name)


def load_pdf_review(path: Path | str, options: PdfOptions) -> PdfImportReview:
    """Review one physical page without publishing or modifying an object."""
    if type(options) is not PdfOptions:
        raise ValueError('PDF review requires validated import options')
    data = _bytes(path)
    program = read_pdf_page(data, Path(path).name, options.page_index)
    return PdfImportReview(data, render_pdf_program(program, options))


def _fresh(path: Path | str, review: PdfImportReview) -> PdfImportReview:
    try:
        if type(review) is not PdfImportReview:
            raise ValueError('Invalid PDF review')
        fresh = load_pdf_review(path, review.result.report.options)
        if (fresh.source_bytes != review.source_bytes or fresh.result.report != review.result.report
                or tuple(g.wkb for g in fresh.result.geometry_mm) != tuple(g.wkb for g in review.result.geometry_mm)):
            raise ValueError('PDF reviewed source or geometry changed')
        return fresh
    except Exception as error:
        raise ValueError('PDF source changed or is unavailable. Analyse again.') from error


def _guard(path: Path | str, digest: str) -> None:
    try:
        if sha256(_bytes(path)).hexdigest() != digest:
            raise ValueError('PDF source identity changed')
    except Exception as error:
        raise ValueError('PDF source changed or is unavailable. Analyse again.') from error


def _name(name: str) -> None:
    try:
        valid = (type(name) is str and name == name.strip() and name.isprintable()
                 and 1 <= len(name.encode('utf-8')) <= 256)
    except UnicodeError:
        valid = False
    if not valid:
        raise ValueError('PDF Geometry name requires trimmed printable text within 256 UTF8 bytes')


def create_pdf_geometry(app: object, path: Path | str, review: PdfImportReview, name: str) -> object:
    """Use fresh authoritative geometry, normal tool defaults and two source guards."""
    _name(name)
    units = getattr(app, 'app_units', None)
    if type(units) is not str or units not in ('MM', 'IN'):
        raise ValueError('PDF Geometry requires explicit MM or IN host units')
    fresh = _fresh(path, review)
    factor = 1. if units == 'MM' else 1. / 25.4
    initialized, failures = [], []

    def initialize(obj: object, app_obj: object) -> str | None:
        try:
            _guard(path, fresh.result.report.source_sha256)
            if getattr(obj, 'units', None) != units or getattr(app_obj, 'app_units', None) != units:
                raise ValueError('PDF factory units changed')
            if type(obj.tools) is not dict or any(type(tool) is not dict for tool in obj.tools.values()):
                raise ValueError('PDF factory must supply normal Geometry tools')
            obj.solid_geometry = [affinity.scale(g, xfact=factor, yfact=factor, origin=(0., 0.))
                                  for g in fresh.result.geometry_mm]
            obj.multigeo = False
            for tool in obj.tools.values():
                tool['solid_geometry'] = list(obj.solid_geometry)
            obj.source_file = fresh.source_bytes.decode('latin1')
            obj.pdf_import = report_to_dict(fresh.result.report)
            _guard(path, fresh.result.report.source_sha256)
            initialized.append(obj)
            return None
        except Exception as error:
            failures.append(str(error))
            return 'fail'

    try:
        result = app.app_obj.new_object('geometry', name, initialize)
    except Exception as error:
        raise ValueError(f'PDF Geometry factory failed: {error}') from error
    if len(initialized) != 1 or result is not initialized[0]:
        reason = failures[0] if failures else 'factory did not publish the initialized object'
        raise ValueError(f'Could not create PDF Geometry: {reason}')
    return result


def read_pdf_report(owner: object) -> PdfImportReport | None:
    """Read optional historical evidence without accessing the original PDF file."""
    value = getattr(owner, 'pdf_import', None)
    return None if value is None else report_from_dict(value)
