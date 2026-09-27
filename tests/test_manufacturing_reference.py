"""Classification of unchanged licensed 009 corpus, not inferred board geometry."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from mikrocam.importers.manufacturing_classify import inspect_manufacturing_bytes


ROOT = Path(__file__).parent / 'reference' / 'boards'
MANIFEST = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
FILES = tuple((board, file) for board in MANIFEST['boards'] for file in board['files']
              if file['role'] in ('copper', 'drill', 'outline', 'drill-map'))
INCH_BOARDS = {'diptrace-fd1-keyboard', 'diptrace-fd1-mainboard', 'fritzing-analog-gyro'}


@pytest.mark.parametrize('board,file', FILES, ids=[file['path'] for _, file in FILES])
def test_licensed_corpus_format_units_identity_and_no_fabricated_plating(board, file):
    path = ROOT / file['path']
    data = path.read_bytes()
    assert sha256(data).hexdigest() == file['sha256'] == file['source_sha256']
    assert board['license']['identifier'] and all((ROOT / name).is_file()
                                                 for name in board['license']['notices'])
    result = inspect_manufacturing_bytes(data, path.name)
    kind = 'excellon' if file['role'] == 'drill' else 'gerber'
    units = 'IN' if (board['id'] in INCH_BOARDS
                     or board['id'] == 'kicad-ivcurve-mux' and file['role'] == 'drill') else 'MM'
    assert (result.format_hint, result.units_hint) == (kind, units)
    assert result.source_name == path.name and result.source_sha256 == file['sha256']
    assert result.byte_count == len(data) and not result.issues
    if board['id'].startswith('diptrace-') or file['role'] == 'drill' and board['id'] in (
            'eagle-newer-gyw', 'altium-limesdr-qpci-e-v1-2'):
        assert result.role_hint == 'unknown'
    elif 'NPTH' in path.name or 'Mechanical 1' in path.name:
        assert result.role_hint == 'NPTH'
    elif file['role'] in ('drill', 'drill-map'):
        assert result.role_hint == 'PTH'
    elif file['role'] == 'outline':
        assert result.role_hint == 'Edge.Cuts'
    else:
        assert result.role_hint == 'F.Cu'
    assert path.read_bytes() == data


def test_existing_corpus_covers_multiple_real_producers_and_both_unit_systems():
    origins = {board['origin'] for board, _ in FILES}
    assert {'KiCad', 'EasyEDA', 'Altium', 'Eagle', 'Proteus', 'DipTrace', 'Fritzing'} <= origins
    assert len({board['id'] for board, _ in FILES}) == 10


def test_proteus_drill_artwork_keeps_gerber_format_despite_plating_role():
    board = next(board for board in MANIFEST['boards'] if board['id'] == 'proteus-sliding-gate')
    for file in board['files']:
        if file['role'] == 'drill-map':
            path = ROOT / file['path']
            result = inspect_manufacturing_bytes(path.read_bytes(), path.name)
            assert result.format_hint == 'gerber' and result.role_hint in ('PTH', 'NPTH')
            assert any(item.origin == 'metadata' and item.role_hint == result.role_hint
                       for item in result.evidence)


def test_eagle_legacy_metadata_and_kicad_comment_and_extended_metadata_are_equivalent():
    names = ('eagle-newer-gyw/copper_top.gbr',
             'kicad-pico2romemu/Pico2ROMEmu_PCB-F_Cu.gtl',
             'kicad-ivcurve-mux/MUX-ADG706-F_Cu.gbr')
    for name in names:
        path = ROOT / name
        result = inspect_manufacturing_bytes(path.read_bytes(), path.name)
        assert result.role_hint == 'F.Cu'
        assert any(item.origin == 'metadata' and item.role_hint == 'F.Cu'
                   for item in result.evidence)
