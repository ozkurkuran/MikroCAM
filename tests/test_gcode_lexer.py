"""Bounded GRBL-oriented lexical recognition with physical source line identity."""
import pytest

from mikrocam.core.gcode_lexer import GcodeError, iter_blocks
from mikrocam.core.gcode_models import PreflightCancelled


def words(text):
    return [block.words for block in iter_blocks(text)]


def test_comments_case_adjacent_words_and_line_numbers():
    blocks = list(iter_blocks('(header)\r\n\n g21\rG90 ; mode\nN12g1x-.5 Y+2. F100 (end)'))
    assert [item.line for item in blocks] == [3, 4, 5]
    assert blocks[-1].words == (('N', 12.), ('G', 1.), ('X', -.5), ('Y', 2.), ('F', 100.))
    assert words('; G0X999\n(comment G2)') == []


@pytest.mark.parametrize('text', ['G1 Xnan', 'G1 Xinf', 'G1 X', 'G1 .', '%', '#1=2',
                                  'G1 X1*3', '(unclosed', 'unmatched)', '(nested(x))',
                                  'G1 X' + '1'*65, 'G1 X1000000001'])
def test_malformed_input_never_silently_disappears(text):
    with pytest.raises(GcodeError) as caught:
        list(iter_blocks('\n' + text))
    assert caught.value.line == 2 and caught.value.code


@pytest.mark.parametrize('character', ['!', '?', '~', '\x18', '\x85', '\x00', '\x7f', 'ğ'])
@pytest.mark.parametrize('wrapper', ['G1 X1{}', '(comment{})', ';comment{}'])
def test_realtime_control_and_nonascii_are_not_shielded_by_comments(character, wrapper):
    with pytest.raises(GcodeError):
        list(iter_blocks(wrapper.format(character)))


def test_limits_apply_to_comments_and_blank_lines(monkeypatch):
    import mikrocam.core.gcode_lexer as lexer
    monkeypatch.setattr(lexer, 'MAX_LINES', 3)
    with pytest.raises(GcodeError, match='line count'):
        list(lexer.iter_blocks('\n\n\n\n'))
    with pytest.raises(GcodeError, match='line length'):
        list(lexer.iter_blocks(';' + 'a'*4096))


def test_cancellation_checked_on_empty_lines():
    with pytest.raises(PreflightCancelled):
        list(iter_blocks('\n\nG21', lambda: True))


def test_cancellation_between_yielded_blocks():
    cancelled = False
    blocks = iter_blocks('G21\nG90\n', lambda: cancelled)
    assert next(blocks).words == (('G', 21.),)
    cancelled = True
    with pytest.raises(PreflightCancelled):
        next(blocks)
