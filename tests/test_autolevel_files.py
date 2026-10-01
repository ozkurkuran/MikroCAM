import pytest
from mikrocam.bridge.autolevel_files import save_autolevel_gcode
from mikrocam.core.autolevel import prepare_autolevel
from test_autolevel_core import HEADER, reviewed, settings


def result():
    return prepare_autolevel(*reviewed(HEADER+'G1Z-.1F60\nG1X1'),settings())


def test_separate_exact_file_export(tmp_path):
    value=result()
    path=tmp_path/'compensated.nc'
    save_autolevel_gcode(path,value)
    assert path.read_text(encoding='ascii')==value.prepared_job.source.text
    assert value.original_source.text!=path.read_text(encoding='ascii')
    assert not list(tmp_path.glob('.autolevel-*.tmp'))


def test_atomic_replace_failure_preserves_previous_and_cleans_temp(tmp_path,monkeypatch):
    import mikrocam.bridge.autolevel_files as module
    path=tmp_path/'cut.nc';path.write_bytes(b'original')
    def fail(*args):
        raise OSError('locked destination')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(OSError):
        save_autolevel_gcode(path,result())
    assert path.read_bytes()==b'original'
    assert not list(tmp_path.glob('.autolevel-*.tmp'))



@pytest.mark.parametrize('kind',['same','relative','hardlink'])
def test_input_destinations_cannot_be_overwritten(tmp_path,kind):
    import os
    original=tmp_path/'original.nc';original.write_bytes(b'original-source')
    destination=original
    if kind=='relative':destination=tmp_path/'sub'/'..'/'original.nc';(tmp_path/'sub').mkdir()
    elif kind=='hardlink':destination=tmp_path/'alias.nc';os.link(original,destination)
    with pytest.raises(ValueError,match='input'):
        save_autolevel_gcode(destination,result(),protected_paths=(original,))
    assert original.read_bytes()==b'original-source' and destination.read_bytes()==b'original-source'
