"""Excellon input is bounded before accumulating lines or oversize statements."""
import pytest
from mikrocam.importers.manufacturing_lines import excellon_lines


def test_universal_line_endings_and_parser_only_bom_removal():
    data = b'\xef\xbb\xbfM48\r\nMETRIC,TZ\rT1C1\n%\n'
    assert excellon_lines(data) == ('M48\r\n', 'METRIC,TZ\r', 'T1C1\n', '%\n')
    assert data.startswith(b'\xef\xbb\xbf')


def test_line_limit_stops_reading_immediately(monkeypatch):
    from mikrocam.importers import manufacturing_lines as module
    from io import StringIO
    reads = []
    class Counted(StringIO):
        def readline(self, size=-1):
            reads.append(size)
            return super().readline(size)
    monkeypatch.setattr(module, 'StringIO', Counted)
    monkeypatch.setattr(module, 'MAX_LINES', 3)
    with pytest.raises(ValueError, match='line count'):
        excellon_lines(b'\n' * 10000)
    assert len(reads) == 4


def test_line_size_bounded_read_and_valid_limit(monkeypatch):
    from mikrocam.importers import manufacturing_lines as module
    monkeypatch.setattr(module, 'MAX_LINE_BYTES', 8)
    assert excellon_lines(b'1234567\n') == ('1234567\n',)
    with pytest.raises(ValueError, match='line size'):
        excellon_lines(b'12345678\n')


@pytest.mark.parametrize('data', [b'', 'M48', bytearray(b'M48'), b'M48\x00', b'M48\x0b'])
def test_source_types_and_controls_reject(data):
    with pytest.raises(ValueError):
        excellon_lines(data)
