"""Equal XY geometry must not hide changed emitted machining instructions."""
import pytest

from mikrocam.core import reference_gcode as reference


PROGRAM = 'G21\nG90\nG94\nG0 Z2\nM3 S10000\nG4 P1\nG1 X1 Y2 Z-0.1 F120\nM5\nM2\n'


@pytest.mark.parametrize(('original', 'replacement'), [('Z-0.1', 'Z-0.2'), ('F120', 'F121'),
    ('S10000', 'S9000'), ('P1', 'P0'), ('G21', 'G20'), ('G90', 'G91'), ('M3', 'M4'), ('M5', 'M3')])
def test_every_emitted_machining_value_remains_significant(original, replacement):
    result = reference.compare_gcode(PROGRAM, PROGRAM.replace(original, replacement), distance_mm=100)
    assert not result.matches and result.differing_blocks


def test_comments_whitespace_case_and_numeric_spelling_are_presentation_only():
    expected = '(source version 1)\nG21\nG1X1.000Y2F120\nM2\n'
    actual = '(source version 2)\ng21 ; comment\n g1 x1 y2.000 f120.0 (nested (comment))\n\nm2\n'
    result = reference.compare_gcode(expected, actual, distance_mm=0)
    assert result.matches and not result.differing_blocks
    assert result.expected_count == result.actual_count == 3


def test_xy_tolerance_is_explicit_and_other_coordinates_are_exact():
    assert reference.compare_gcode(PROGRAM, PROGRAM.replace('X1', 'X1.001'), distance_mm=.002).matches
    assert not reference.compare_gcode(PROGRAM, PROGRAM.replace('X1', 'X1.001'), distance_mm=.0005).matches
    assert not reference.compare_gcode(PROGRAM, PROGRAM.replace('Z2', 'Z2.001'), distance_mm=.002).matches


@pytest.mark.parametrize('changed', ['G90\nG21\nM2', 'G21\nG90\nG90\nM2', 'G21 G90\nM2'])
def test_block_and_word_order_duplicate_words_and_tail_commands_are_retained(changed):
    assert not reference.compare_gcode('G21\nG90\nM2', changed, distance_mm=0).matches


@pytest.mark.parametrize('text', ['', '(header only)', 'G1 XNaN', 'G1 X1;comment\n(unclosed',
                                  'G1 X1)', 'G1 X[1+2]', '/G1 X2', 'G1 X1e-3', 'G1 X1*42',
                                  'G1 X' + '1'*65, '('*65 + ')'*65 + '\nG21'])
def test_unsupported_or_incomplete_gcode_is_indeterminate_not_ignored(text):
    with pytest.raises(ValueError):
        reference.compare_gcode(text, PROGRAM, distance_mm=0)


@pytest.mark.parametrize('value', [True, -1, float('inf'), float('nan'), '0'])
def test_invalid_tolerance_is_rejected(value):
    with pytest.raises(ValueError):
        reference.compare_gcode(PROGRAM, PROGRAM, distance_mm=value)


def test_input_and_block_limits_are_explicit(monkeypatch):
    monkeypatch.setattr(reference, 'MAX_GCODE_BYTES', 5)
    with pytest.raises(ValueError, match='limit'):
        reference.compare_gcode(PROGRAM, PROGRAM, distance_mm=0)
    monkeypatch.setattr(reference, 'MAX_GCODE_BYTES', 1000)
    monkeypatch.setattr(reference, 'MAX_BLOCKS', 1)
    with pytest.raises(ValueError, match='limit'):
        reference.compare_gcode(PROGRAM, PROGRAM, distance_mm=0)
