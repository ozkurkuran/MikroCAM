"""Command boundaries preserve compact artwork and aperture macro bodies."""
import pytest
from mikrocam.importers.gerber_statements import gerber_statements


def test_compact_attributes_never_discard_adjacent_artwork():
    data = b'%TF.FileFunction,Copper,L1,Top*%%FSLAX24Y24*%%MOMM*%D10*X100Y200D03*M02*'
    assert gerber_statements(data) == ('%FSLAX24Y24*%', '%MOMM*%', 'D10*', 'X100Y200D03*', 'M02*')
    assert gerber_statements(data, retain_attributes=True)[0] == '%TF.FileFunction,Copper,L1,Top*%'


def test_combined_extended_commands_split_preserving_macro_body():
    assert gerber_statements(b'%FSLAX24Y24*MOMM*ADD10C,1.0*%') == (
        '%FSLAX24Y24*%', '%MOMM*%', '%ADD10C,1.0*%')
    macro = '%AMDONUT*\n$1=1*\n1,1,$1,0,0*\n1,0,0.5,0,0*%'
    assert gerber_statements(macro.encode() + b'%ADD10DONUT*%') == (macro.replace('\n', ''), '%ADD10DONUT*%')


def test_ordinary_and_legacy_metadata_comments_preserve_next_draw():
    data = b'G04 tool %TF not an attribute*D10*G04 #@! %TF.FileFunction,Copper,L1,Top,Mixed*X10Y20D03*'
    result = gerber_statements(data)
    assert result == ('G04 tool %TF not an attribute*', 'D10*',
                      'G04 #@! %TF.FileFunction,Copper,L1,Top,Mixed*', 'X10Y20D03*')


@pytest.mark.parametrize('attribute', ['TF.FileFunction,Copper,L1,Top', 'TA.AperFunction,ViaPad',
                                      'TO.N,GND', 'TD', 'TD.N'])
def test_only_attribute_statements_are_removed(attribute):
    assert gerber_statements(f'%{attribute}*%D10*'.encode()) == ('D10*',)


@pytest.mark.parametrize('source', [b'', b'   ', b'%MOMM*', b'%MOMM%', b'D10', b'D10%X1*',
                                  b'%%', b'%AM*%', b'%FSLAX24Y24**%', b'X1\x00Y1D03*'])
def test_incomplete_or_malformed_delimiters_reject(source):
    with pytest.raises(ValueError, match='Gerber'):
        gerber_statements(source)


def test_bom_is_only_removed_from_parsing_input():
    data = b'\xef\xbb\xbf%MOMM*%M02*'
    assert gerber_statements(data) == ('%MOMM*%', 'M02*')
    assert data.startswith(b'\xef\xbb\xbf')


def test_statement_and_source_limits(monkeypatch):
    from mikrocam.importers import gerber_statements as module
    monkeypatch.setattr(module, 'MAX_STATEMENTS', 2)
    assert len(gerber_statements(b'D10*X1Y1D03*')) == 2
    with pytest.raises(ValueError, match='Gerber.*command'):
        gerber_statements(b'D10*X1Y1D03*M02*')
    monkeypatch.setattr(module, 'MAX_STATEMENT_BYTES', 8)
    with pytest.raises(ValueError, match='Gerber.*statement'):
        gerber_statements(b'G04 too long*')


@pytest.mark.parametrize('source,flag', [('D10*', False), (b'D10*', 1), (bytearray(b'D10*'), False)])
def test_exact_source_and_flag_types(source, flag):
    with pytest.raises(ValueError):
        gerber_statements(source, retain_attributes=flag)


def test_extended_command_cap_rejects_before_mass_split_allocation(monkeypatch):
    import tracemalloc
    from mikrocam.importers import gerber_statements as module
    monkeypatch.setattr(module, 'MAX_STATEMENTS', 3)
    source = b'%' + b'G01*' * 200000 + b'%'
    tracemalloc.start()
    try:
        with pytest.raises(ValueError, match='command count'):
            gerber_statements(source)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 5000000, f'Unexpected eager allocation before bounded command rejection: {peak}'
