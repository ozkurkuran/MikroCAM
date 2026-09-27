"""Offline bounded file I/O preserves previous files through failed publication."""
from pathlib import Path
import pytest

from mikrocam.core.probe_map import ProbeGrid, ProbeMap
import mikrocam.bridge.probe_files as files


def sample():
    return ProbeMap(ProbeGrid((0., 1.), (0., 1.)), (.1, None, None, None),
                    (1., 2., 3.), 'aborted', 'measured')


def test_save_and_load_partial_map_and_replace_existing_content(tmp_path):
    target = tmp_path / 'harita ölçüm.json'
    target.write_bytes(b'previous')
    files.save_probe_map(target, sample())
    assert files.load_probe_map(str(target)) == sample()
    assert list(tmp_path.iterdir()) == [target]
    assert target.read_bytes().startswith(b'{')


def test_failed_replace_preserves_old_file_and_removes_temporary_file(tmp_path, monkeypatch):
    target = tmp_path / 'map.json'
    target.write_bytes(b'previous exact bytes')
    def fail(source, destination):
        assert Path(source).parent == target.parent
        assert Path(source).is_file() and Path(destination) == target
        raise OSError('publication denied')
    monkeypatch.setattr(files.os, 'replace', fail)
    with pytest.raises(OSError, match='publication denied'):
        files.save_probe_map(target, sample())
    assert target.read_bytes() == b'previous exact bytes'
    assert list(tmp_path.iterdir()) == [target]


def test_write_failure_leaves_no_partial_target_or_temp(tmp_path, monkeypatch):
    target = tmp_path / 'new.json'
    def fail(_):
        raise OSError('flush failed')
    monkeypatch.setattr(files.os, 'fsync', fail)
    with pytest.raises(OSError, match='flush failed'):
        files.save_probe_map(target, sample())
    assert list(tmp_path.iterdir()) == []


def test_invalid_map_cannot_replace_previous_file(tmp_path):
    target = tmp_path / 'map.json'
    target.write_bytes(b'previous')
    with pytest.raises(ValueError):
        files.save_probe_map(target, None)
    assert target.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('contents', [b'', b'not json', b'\xff', b'\xef\xbb\xbf{}',
                                    b'{"schema":1,"schema":1}'])
def test_invalid_file_load_is_read_only(tmp_path, contents):
    target = tmp_path / 'bad.json'
    target.write_bytes(contents)
    with pytest.raises(ValueError):
        files.load_probe_map(target)
    assert target.read_bytes() == contents and list(tmp_path.iterdir()) == [target]


def test_load_reads_only_limit_plus_one_bytes(tmp_path, monkeypatch):
    target = tmp_path / 'large.json'
    target.write_bytes(b' ' * 1000)
    monkeypatch.setattr(files, 'MAX_MAP_BYTES', 32)
    original = Path.open
    reads = []
    class ObservedFile:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def read(self, count):
            reads.append(count)
            return self.stream.read(count)
    monkeypatch.setattr(Path, 'open', lambda self, *args, **kwargs: ObservedFile(original(self, *args, **kwargs)))
    with pytest.raises(ValueError):
        files.load_probe_map(target)
    assert reads == [33]


def test_missing_file_and_directory_errors_are_visible(tmp_path):
    with pytest.raises(OSError):
        files.load_probe_map(tmp_path / 'missing.json')
    with pytest.raises(OSError):
        files.load_probe_map(tmp_path)
    with pytest.raises(OSError):
        files.save_probe_map(tmp_path / 'missing-directory' / 'map.json', sample())
