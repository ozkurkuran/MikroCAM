"""Independent authored manufacturing evidence, never geometric plating inference."""
from hashlib import sha256
import pytest

from mikrocam.importers.manufacturing_classify import inspect_manufacturing_bytes


GERBER = b'%FSLAX24Y24*%%MOMM*%%ADD10C,0.2*%D10*X0Y0D03*M02*'
EXCELLON = b'M48\nMETRIC,TZ\nT01C0.8\n%\nT01\nX1.0Y2.0\nM30\n'


def inspect(data=GERBER, name='board.gbr'):
    return inspect_manufacturing_bytes(data, name)


@pytest.mark.parametrize('metadata,role', [
    ('Copper,L1,Top', 'F.Cu'), ('Copper,L8,Bot', 'B.Cu'),
    ('Copper,L2,Inr', 'Other'), ('Copper,L1,Top,Mixed', 'F.Cu'),
    ('Copper,L2,Inr,Plane', 'Other'), ('Copper,L4,Bot,Hatched', 'B.Cu'),
    ('Profile,P', 'Edge.Cuts'), ('Profile,NP', 'Edge.Cuts'),
    ('Plated,1,2,PTH', 'PTH'), ('Plated,4,1,PTH,Drill', 'PTH'),
    ('NonPlated,1,2,NPTH,Rout', 'NPTH'), ('Plated,1,3,Blind', 'Other'),
    ('NonPlated,2,3,Buried,Mixed', 'Other'), ('Soldermask,Top', 'Other'),
    ('Legend,Bot,2', 'Other'), ('Other,Mechanical drawing', 'Other'),
])
def test_standard_metadata_proposes_explicit_roles(metadata, role):
    result = inspect(b'%TF.FileFunction,' + metadata.encode() + b'*%' + GERBER)
    assert (result.format_hint, result.role_hint, result.units_hint) == ('gerber', role, 'MM')
    assert any(item.origin == 'metadata' and item.role_hint == role for item in result.evidence)


@pytest.mark.parametrize('prefix,suffix', [(b'G04 #@! TF.FileFunction,', b'*'),
                                          (b'G04 #@! %TF.FileFunction,', b'*')])
def test_compatible_legacy_comment_metadata(prefix, suffix):
    result = inspect(prefix + b'Copper,L1,Top,Mixed' + suffix + GERBER)
    assert result.role_hint == 'F.Cu'


@pytest.mark.parametrize('kind,role', [('Plated,1,2,PTH', 'PTH'), ('NonPlated,1,2,NPTH', 'NPTH')])
def test_excellon_semicolon_file_function(kind, role):
    result = inspect(b'; #@! TF.FileFunction,' + kind.encode() + b'\n' + EXCELLON, 'drills.drl')
    assert (result.format_hint, result.role_hint, result.units_hint) == ('excellon', role, 'MM')


@pytest.mark.parametrize('metadata', [
    'Copper,L0,Top', 'Copper,L2,Top', 'Copper,L1,Bot', 'Copper,L1,Inr',
    'Copper,L1000001,Bot', 'Copper,L2,Bottom', 'Copper,L1,Top,Unknown',
    'Copper,L1', 'Copper,L1,Top,Mixed,extra', 'copper,L1,Top',
    'Profile', 'Profile,X', 'Profile,P,extra', 'Plated,1,1,PTH',
    'Plated,0,2,PTH', 'Plated,1,2,NPTH', 'NonPlated,1,2,PTH',
    'Plated,1,2,PTH,Route', 'Soldermask,Middle', 'Legend,Top,0', 'Other',
    'UnsupportedFunction,Top', '',
])
def test_malformed_metadata_cannot_be_hidden_by_filename(metadata):
    result = inspect(b'%TF.FileFunction,' + metadata.encode() + b'*%' + GERBER, 'board-F_Cu.gtl')
    assert result.role_hint == 'unknown'
    assert result.issues


@pytest.mark.parametrize('name,role', [
    ('board-F_Cu.gbr', 'F.Cu'), ('Board_f.cu.GBR', 'F.Cu'),
    ('board-B_Cu.gbr', 'B.Cu'), ('board.b.cu.GER', 'B.Cu'),
    ('board-Edge_Cuts.gbr', 'Edge.Cuts'), ('board.Edge.Cuts.GBR', 'Edge.Cuts'),
    ('board.GTL', 'F.Cu'), ('board.GBL', 'B.Cu'), ('board.GKO', 'Edge.Cuts'),
])
def test_case_insensitive_whole_filename_tokens(name, role):
    assert inspect(name=name).role_hint == role


@pytest.mark.parametrize('name,role', [('Drill_PTH_Through.DRL', 'PTH'),
                                     ('Drill_NPTH_Through.DRL', 'NPTH'),
                                     ('npth.drl', 'NPTH'), ('depth.drl', 'unknown'),
                                     ('xPTHx.drl', 'unknown')])
def test_plating_filename_tokens_are_not_substrings(name, role):
    assert inspect(EXCELLON, name).role_hint == role


@pytest.mark.parametrize('name', ['board-xF_Cux.gbr', 'board-BackCopper.gbr', 'board-In1_Cu.gbr'])
def test_unspecified_filename_purpose_remains_unknown(name):
    assert inspect(name=name).role_hint == 'unknown'


def test_conflicting_roles_and_formats_are_unresolved_with_separate_evidence():
    role = inspect(b'%TF.FileFunction,Copper,L1,Top*%' + GERBER, 'board-B_Cu.gbl')
    assert role.role_hint == 'unknown' and any('conflict' in issue.lower() for issue in role.issues)
    assert {'F.Cu', 'B.Cu'} <= {item.role_hint for item in role.evidence}
    kind = inspect(GERBER, 'board.drl')
    assert kind.format_hint == 'unknown' and kind.issues
    embedded = inspect(b'%TF.FileFunction,Copper,L1,Top*%%TF.FileFunction,Copper,L4,Bot*%' + GERBER)
    assert embedded.role_hint == 'unknown'


def test_same_evidence_is_deduplicated_without_hiding_distinct_sources():
    metadata = b'%TF.FileFunction,Copper,L1,Top*%'
    result = inspect(metadata * 20 + GERBER, 'board-F_Cu.gtl')
    assert result.role_hint == 'F.Cu'
    assert len(result.evidence) == len(set(result.evidence))
    assert len([item for item in result.evidence if item.origin == 'metadata']) == 1


@pytest.mark.parametrize('data,name,kind', [
    (b'%FSLAX24Y24*%', 'unknown.bin', 'gerber'),
    (b'%MOIN*%', 'unknown.bin', 'gerber'),
    (b'%ADD10C,0.4*%', 'unknown.bin', 'gerber'),
    (b'M48\n', 'unknown.bin', 'excellon'),
    (b'T01C0.4\n', 'unknown.bin', 'excellon'),
    (b'METRIC,LZ\n', 'unknown.bin', 'excellon'),
    (b'INCH\n', 'unknown.bin', 'excellon'),
    (b'ordinary text', 'board.gbr', 'gerber'),
    (b'ordinary text', 'board.xln', 'excellon'),
    (b'ordinary text', 'board.tap', 'unknown'),
])
def test_real_content_and_filename_format_proposals(data, name, kind):
    assert inspect(data, name).format_hint == kind


@pytest.mark.parametrize('data', [b'G04 Example %MOMM*% and M48*',
                                b'; M48 METRIC %MOMM*%\n',
                                b'G04 TF.FileFunction,Copper,L1,Top*',
                                b'%AMEXAMPLE*0 Example %MOMM marker*%'])
def test_ordinary_comments_and_macro_text_do_not_forge_evidence(data):
    result = inspect(data, 'unknown.bin')
    assert (result.format_hint, result.role_hint, result.units_hint) == ('unknown', 'unknown', 'unknown')


@pytest.mark.parametrize('data,units', [(b'%MOMM*%', 'MM'), (b'%MOIN*%', 'IN'),
                                      (b'G71*', 'MM'), (b'G70*', 'IN'),
                                      (b'M48\nM71\n', 'MM'), (b'M48\nM72\n', 'IN')])
def test_explicit_unit_markers(data, units):
    assert inspect(data, 'unknown.bin').units_hint == units


def test_missing_and_conflicting_units_reveal_parser_assumption():
    missing = inspect(b'%FSLAX24Y24*%', 'board.gbr')
    conflict = inspect(b'%MOMM*%%MOIN*%', 'board.gbr')
    for result in (missing, conflict):
        assert result.units_hint == 'unknown'
        assert any('parser' in issue.lower() for issue in result.issues)


def test_exact_identity_determinism_and_same_hash_different_name():
    first = inspect(GERBER, 'first.gbr')
    assert first == inspect(GERBER, 'first.gbr')
    assert first.source_sha256 == sha256(GERBER).hexdigest() and first.byte_count == len(GERBER)
    second = inspect(GERBER, 'second.gbr')
    assert first.source_sha256 == second.source_sha256 and first.source_name != second.source_name


@pytest.mark.parametrize('data,name', [(b'', 'x'), ('text', 'x'), (bytearray(b'x'), 'x'),
                                      (b'x', ''), (b'x', 'é' * 129), (b'x', None)])
def test_invalid_source_arguments_fail(data, name):
    with pytest.raises(ValueError):
        inspect(data, name)


def test_overlong_metadata_is_unresolved_and_bounded():
    result = inspect(b'%TF.FileFunction,Other,' + b'x' * 513 + b'*%' + GERBER, 'board-F_Cu.gtl')
    assert result.role_hint == 'unknown' and result.issues
    assert all(len(item.detail.encode('utf-8')) <= 512 for item in result.evidence)


def test_byte_limit_before_decoding(monkeypatch):
    import mikrocam.importers.manufacturing_classify as module
    monkeypatch.setattr(module, 'MAX_MANUFACTURING_BYTES', 4)
    with pytest.raises(ValueError):
        inspect(GERBER)


@pytest.mark.parametrize('comment', [b'G04 multiline example\nM48\nINCH\nT01C0.8\n*',
                                     b'%AMEXAMPLE*0 multiline example\nM48\nINCH\nT01C0.8\n*%'])
def test_gerber_multiline_comment_or_macro_cannot_forge_excellon_headers(comment):
    result = inspect(comment + GERBER)
    assert (result.format_hint, result.units_hint) == ('gerber', 'MM')
    assert not any(item.format_hint == 'excellon' or item.units_hint == 'IN' for item in result.evidence)


def test_metadata_wrong_case_is_invalid_instead_of_hidden_by_filename():
    result = inspect(b'%tf.FileFunction,Copper,L4,Bot*%' + GERBER, 'board-F_Cu.gtl')
    assert result.role_hint == 'unknown' and result.issues


def test_combined_blocks_bom_and_source_coordinates_are_preserved():
    data = b'\xef\xbb\xbf%FSLAX24Y24*MOMM*TF.FileFunction,Copper,L1,Top*ADD10C,0.2*%X123Y456D03*M02*'
    result = inspect(data, 'board-F_Cu.gbr')
    assert (result.format_hint, result.role_hint, result.units_hint) == ('gerber', 'F.Cu', 'MM')
    assert result.byte_count == len(data) and result.source_sha256 == sha256(data).hexdigest()


def test_conflicting_filename_tokens_and_explicit_units_do_not_silently_win():
    result = inspect(name='board-F_Cu-B_Cu.gbr')
    assert result.role_hint == 'unknown' and result.issues
    drill = inspect(b'M48\nMETRIC\nINCH\n', 'drills.drl')
    assert drill.units_hint == 'unknown' and any('parser' in issue.lower() for issue in drill.issues)


def test_evidence_limit_fails_instead_of_truncating_hidden_conflict():
    data = b''.join(b'%TF.FileFunction,Other,purpose' + str(index).encode() + b'*%'
                    for index in range(40)) + GERBER
    with pytest.raises(ValueError, match='evidence'):
        inspect(data)


@pytest.mark.parametrize('name', ['folder-F_Cu/board.gbr', r'folder-B_Cu\board.gbr',
                                 'éF_Cu.gbr', 'board-F_Cué.gbr'])
def test_filename_hints_are_only_whole_basename_tokens(name):
    assert inspect(name=name).role_hint == 'unknown'


@pytest.mark.parametrize('data', [b'%TF.filefunction,Copper,L4,Bot*%',
                                b'%tf.FileFunction,Copper,L4,Bot*%',
                                b'G04 #@! TF.filefunction,Copper,L4,Bot*'])
def test_malformed_metadata_case_without_other_gerber_signatures_clears_role(data):
    result = inspect(data, 'board-F_Cu.gtl')
    assert result.role_hint == 'unknown' and result.issues


def test_classifier_reads_only_bounded_number_of_excellon_lines(monkeypatch):
    import mikrocam.importers.manufacturing_lines as lines
    calls = []
    original = lines.StringIO

    class ObservedStream(original):
        def readline(self, size=-1):
            calls.append(size)
            return super().readline(size)

    monkeypatch.setattr(lines, 'StringIO', ObservedStream)
    monkeypatch.setattr(lines, 'MAX_LINES', 2)
    with pytest.raises(ValueError, match='line count'):
        inspect(b'M48\n' + b'\n' * 1000, 'many.drl')
    assert len(calls) == 3
