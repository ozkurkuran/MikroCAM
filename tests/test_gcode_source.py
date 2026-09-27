"""Complete immutable G-code source acquisition without edits or export side effects."""
import hashlib
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from mikrocam.bridge.gcode_source import load_gcode_file, snapshot_cncjob


PROGRAM = 'G21 G90 G94\r\nG0 Z5\r\nG1 X2 F100\r\nM30\r\n'


class ReadOnlyJob:
    kind = 'cncjob'

    def __init__(self, text=PROGRAM):
        self.source_file = text
        self.obj_options = {'name': 'complete-job', 'units': 'IN', 'xmin': -999}

    @property
    def gcode(self):
        raise AssertionError('Incomplete body must never be inspected')

    def export_gcode(self, *args, **kwargs):
        raise AssertionError('Snapshot must never export or edit')


def test_snapshot_preserves_complete_source_line_endings_and_hash_without_mutation():
    job = ReadOnlyJob()
    before = (job.source_file, dict(job.obj_options))
    source = snapshot_cncjob(job)
    assert source.name == 'complete-job' and source.text == PROGRAM
    assert source.sha256 == hashlib.sha256(PROGRAM.encode('utf-8')).hexdigest()
    assert (job.source_file, job.obj_options) == before
    job.source_file = 'G0 X999\n'
    job.obj_options['name'] = 'changed'
    assert source.name == 'complete-job' and source.text == PROGRAM


@pytest.mark.parametrize('source', [None, '', b'G0 X1\n', ['G0 X1'], 123])
def test_absent_empty_or_nontext_source_is_rejected_without_body_fallback(source):
    job = ReadOnlyJob(source)
    with pytest.raises(ValueError):
        snapshot_cncjob(job)
    assert job.source_file is source


@pytest.mark.parametrize('job', [None, SimpleNamespace(kind='geometry', source_file=PROGRAM),
                                SimpleNamespace(kind='cncjob', obj_options={'name': 'missing'}),
                                SimpleNamespace(kind='cncjob', source_file=PROGRAM),
                                SimpleNamespace(kind='cncjob', source_file=PROGRAM, obj_options={}),
                                SimpleNamespace(kind='cncjob', source_file=PROGRAM, obj_options='job'),
                                SimpleNamespace(kind='cncjob', source_file=PROGRAM,
                                                obj_options={'name': None})])
def test_invalid_object_or_name_is_rejected(job):
    with pytest.raises(ValueError):
        snapshot_cncjob(job)


def test_oversized_utf8_job_source_is_rejected_without_mutating_object():
    from mikrocam.core.gcode_models import MAX_SOURCE_BYTES
    text = 'é' * (MAX_SOURCE_BYTES // 2 + 1)
    job = ReadOnlyJob(text)
    with pytest.raises(ValueError):
        snapshot_cncjob(job)
    assert job.source_file is text


@pytest.mark.parametrize('bom', [b'', b'\xef\xbb\xbf'])
def test_file_load_preserves_utf8_text_and_lines_and_never_changes_file(tmp_path, bom):
    path = tmp_path / 'program.nc'
    raw = bom + PROGRAM.encode('utf-8')
    path.write_bytes(raw)
    before_stat = path.stat()
    source = load_gcode_file(path)
    assert source.name == path.name and source.text == PROGRAM
    assert source.sha256 == hashlib.sha256(PROGRAM.encode()).hexdigest()
    assert path.read_bytes() == raw and path.stat().st_mtime_ns == before_stat.st_mtime_ns
    path.write_text('changed', encoding='utf-8')
    assert source.text == PROGRAM


def test_valid_unicode_is_decoded_without_loss_for_later_lexer_rejection(tmp_path):
    path = tmp_path / 'program.nc'
    path.write_bytes('G21\n(comment é)\n'.encode('utf-8'))
    assert load_gcode_file(path).text == 'G21\n(comment é)\n'


@pytest.mark.parametrize('raw', [b'', b'\xef\xbb\xbf', b'G21\n\xff', b'\xff\xfeG\x002\x001\x00'])
def test_empty_or_invalid_utf8_file_is_rejected_and_preserved(tmp_path, raw):
    path = tmp_path / 'bad.nc'
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        load_gcode_file(path)
    assert path.read_bytes() == raw


def test_file_read_is_bounded_binary_and_closed_on_oversize(monkeypatch):
    from mikrocam.bridge import gcode_source
    monkeypatch.setattr(gcode_source, 'MAX_SOURCE_BYTES', 64)
    calls = []

    class TrackedBytes(io.BytesIO):
        def read(self, size=-1):
            calls.append(size)
            return super().read(size)

    handle = TrackedBytes(b'G' * 100)
    def open_file(path, mode, *args, **kwargs):
        assert mode == 'rb'
        return handle
    monkeypatch.setattr(Path, 'open', open_file)
    with pytest.raises(ValueError):
        load_gcode_file('oversized.nc')
    assert calls == [65] and handle.closed


def test_exact_file_byte_limit_is_allowed_but_next_byte_is_rejected(tmp_path, monkeypatch):
    from mikrocam.bridge import gcode_source
    monkeypatch.setattr(gcode_source, 'MAX_SOURCE_BYTES', 64)
    path = tmp_path / 'limit.nc'
    path.write_bytes(b'G' * 64)
    assert load_gcode_file(path).text == 'G' * 64
    path.write_bytes(b'G' * 65)
    with pytest.raises(ValueError):
        load_gcode_file(path)
    assert path.read_bytes() == b'G' * 65


def test_missing_path_and_directory_errors_do_not_modify_existing_data(tmp_path):
    path = tmp_path / 'kept.nc'
    path.write_text(PROGRAM, encoding='utf-8', newline='')
    for invalid in (tmp_path / 'absent.nc', tmp_path):
        with pytest.raises(OSError):
            load_gcode_file(invalid)
    assert path.read_bytes() == PROGRAM.encode('utf-8')
