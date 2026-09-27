"""Do not stream a reviewed path with material float32 coordinate drift."""
import pytest

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.gcode_models import SourceSnapshot, PreflightSetup
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement


def job(text, initial=(0.,0.,0.), maximum=100001., placement=None):
    setup = PreflightSetup(initial, placement or Placement(), 0., (-10.,-10.,-10.),
                           (maximum,maximum,10.), 0., (100000.,100000.,600.))
    source = SourceSnapshot('precision.nc', text)
    report = analyze_gcode(source, setup)
    assert report.allowed
    return PreparedJob(source, report)


def test_large_absolute_coordinate_rounding_is_rejected():
    with pytest.raises(ValueError, match='precision'):
        job('G21G90G17G94\nG1X99999.99F100000\n')


def test_incremental_float32_drift_is_accumulated_not_checked_per_word_only():
    with pytest.raises(ValueError, match='precision'):
        job('G21G91G17G94\nG1X.01F60\n' + 'X.01\n'*20, initial=(9999.,0.,0.))


def test_float32_endpoint_outside_declared_envelope_is_rejected():
    with pytest.raises(ValueError, match='precision'):
        job('G21G90G17G94\nG1X1.1F60\n', maximum=1.1)


def test_normal_mm_inch_and_exact_incremental_paths_remain_supported():
    for text in ('G21G90G17G94\nG1X1F60\n', 'G20G90G17G94\nG1X1F60\n',
                 'G21G91G17G94\nG1X.125F60\n'+'X.125\n'*20):
        assert job(text).blocks


def test_quantized_arc_interior_cannot_escape_declared_bounds():
    with pytest.raises(ValueError, match='precision'):
        job('G21G90G17G94\nG3X1.1Y1.1I0J1.1F60\n', maximum=1.1)
