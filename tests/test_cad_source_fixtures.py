import hashlib
import json
from pathlib import Path

from mikrocam.importers.cad_source import detect_cad_source


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / 'tests/reference/cad-source/kicad-pico2romemu'


def test_real_kicad_exports_match_retained_exact_hashes_and_license():
    provenance = json.loads((FIXTURE / 'provenance.json').read_text(encoding='utf-8'))
    assert provenance['version'] == '10.0.6'
    assert provenance['license'] == 'MIT'
    assert provenance['upstream_revision'] == 'de3a29370d760e93451975094372e08484cd6777'
    names = {'pico2romemu.svg': 'pico2romemu.svg', 'pico2romemu.dxf': 'pico2romemu.dxf',
             'LICENSE-kicad-pico2romemu.txt': 'LICENSE'}
    for original, local in names.items():
        data = (FIXTURE / local).read_bytes()
        assert len(data) == provenance['files'][original]['bytes']
        assert hashlib.sha256(data).hexdigest() == provenance['files'][original]['sha256']
    native = ROOT / 'tests/reference/boards/kicad-pico2romemu/Pico2ROMEmu_PCB.kicad_pcb'
    assert hashlib.sha256(native.read_bytes()).hexdigest() == provenance['source_sha256']
    assert all(command['exit_code'] == 0 for command in provenance['commands'])
    assert 'Copyright (c) 2025 kyo-ta04(@DragonBallEZ)' in (FIXTURE / 'LICENSE').read_text()


def test_authentic_kicad_svg_identifies_only_explicit_pcbnew_declaration():
    source = (FIXTURE / 'pico2romemu.svg').read_bytes()
    assessment = detect_cad_source(source, 'renamed-inkscape.svg', 'SVG')
    assert assessment.application == 'KiCad' and assessment.status == 'identified'
    assert [(item.field, item.application) for item in assessment.evidence] == [('svg.desc', 'KiCad')]
    assert assessment.source_sha256 == '1c0ed05462cb5b9157bba6285a16f4c94909bcaf2c8c93dd7f2ac52e69d05aec'


def test_authentic_unmarked_kicad_dxf_does_not_guess_from_fonts_or_format():
    source = (FIXTURE / 'pico2romemu.dxf').read_bytes()
    assert b'KICAD' in source and b'$ACADVER' in source and b'$INSUNITS' in source
    assessment = detect_cad_source(source, 'KiCad-10.0.6.dxf', 'DXF')
    assert assessment.application == 'Unknown' and assessment.status == 'unknown'
    assert assessment.evidence == ()
    assert assessment.source_sha256 == 'e9aee26f92577f13cee6149e15563bb3993098bea892d0a00f310ce20713f157'


def test_original_upstream_inkscape_asset_is_metadata_evidence_not_pcb_coverage():
    path = ROOT / 'tests/reference/cad-source/upstream-inkscape-app-small.svg'
    assessment = detect_cad_source(path.read_bytes(), 'app_small.svg', 'SVG')
    assert assessment.application == 'Inkscape' and assessment.status == 'identified'
    assert any(item.field == 'svg.inkscape.version' for item in assessment.evidence)


def test_authored_illustrator_style_fixture_is_not_authentic_producer_evidence():
    path = ROOT / 'tests/reference/svg-illustrator.svg'
    assessment = detect_cad_source(path.read_bytes(), 'Illustrator.svg', 'SVG')
    assert assessment.application == 'Unknown' and assessment.status == 'unknown'
    assert assessment.evidence == ()
