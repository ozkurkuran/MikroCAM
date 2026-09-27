import pytest
from mikrocam.machine.probe_protocol import validate_probe_command, parse_probe_result, probe_move


@pytest.mark.parametrize('data', [b'G21 G90 G94 G1 Z5 F100\n',
    b'G21 G90 G94 G1 X1 Y2 F100\n', b'G21 G90 G94 G38.2 Z-1 F10\n'])
def test_accept_only_generated_bounded_motion(data):
    validate_probe_command(data)


@pytest.mark.parametrize('data', [b'G0 X1\n', b'G38.2 Z-1\n', b'M3\n', b'G21 G90 G94 G1 Z5 F0\n',
    b'G21 G90 G94 G1 Z5 F100\nM3\n', b'G21 G90 G94 G38.2 X1 Y2 F100\n', b'!',
    b'G21 G90 G94 G1 Znan F100\n', b'G21 G90 G94 G1 Z1000001 F100\n'])
def test_reject_non_probe_boundary(data):
    with pytest.raises(ValueError):
        validate_probe_command(data)


def test_probe_wire_units_convert_once():
    assert parse_probe_result('[PRB:1,2,-.1:1]', 'inch') == pytest.approx((25.4, 50.8, -2.54))
    assert parse_probe_result('[PRB:1,2,-.1:1]', 'mm') == (1., 2., -.1)
    assert parse_probe_result('[MSG:hello]', 'mm') is None


@pytest.mark.parametrize('line', ['[PRB:1,2,3:0]', '[PRB:1,2:1]', '[PRB:1,2,nan:1]',
    '[PRB:1,2,3:2]', '[PRB:1,2,3:1]extra', '[PRB:1,2,3:1:1]', '[PRB:1e2,2,3:1]'])
def test_bad_or_failed_probe_rejected(line):
    with pytest.raises(ValueError):
        parse_probe_result(line, 'mm')


def test_generator_exact_and_nonempty_axes():
    assert probe_move(z=2.5, feed=100.) == b'G21 G90 G94 G1 Z2.5 F100\n'
    assert probe_move(x=1., y=2., feed=50.) == b'G21 G90 G94 G1 X1 Y2 F50\n'
    assert probe_move(z=-1., feed=10., probing=True) == b'G21 G90 G94 G38.2 Z-1 F10\n'
    with pytest.raises(ValueError):
        probe_move(x=1., feed=10.)


def test_huge_integer_rejected_as_validation_error():
    with pytest.raises(ValueError):
        probe_move(z=10**1000,feed=100.)
