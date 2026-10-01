from dataclasses import replace
import math
import pytest
from mikrocam.core.autolevel import prepare_autolevel
from mikrocam.core.autolevel_surface import AutoLevelSettings, surface_height
from mikrocam.core.gcode_models import PreflightSetup, SourceSnapshot, PreflightCancelled
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.gcode_parser import ModalInterpreter
from mikrocam.core.gcode_lexer import iter_blocks
from mikrocam.core.placement import Placement
from test_autolevel_surface import height_map

HEADER='G21G90G17G94\n'


def reviewed(text, placement=Placement(), offset=0., initial=(0.,0.,5.), **changes):
    setup=PreflightSetup(initial, placement, offset, (-20.,-20.,-20.), (20.,20.,20.),
                         5., (600.,600.,600.))
    setup=replace(setup, **changes)
    source=SourceSnapshot('cut.nc',text)
    report=analyze_gcode(source,setup)
    assert report.allowed,report.findings
    return source,report


def settings(value=None, **changes):
    base=AutoLevelSettings(value or height_map(lambda x,y: .01*x+.02*y),0.,.5,.001,.001)
    return replace(base,**changes)


def motions(result):
    job=result.prepared_job
    parser=ModalInterpreter(job.report.setup.initial_position_mm)
    return [e for b in iter_blocks(job.source.text) if (e:=parser.consume(b)).motion is not None]


def test_plane_cut_depth_metadata_lineage_no_input_mutation():
    source,report=reviewed(HEADER+'M3S500\nG1Z-.1F60\nG1X2Y2\nG0Z5\nM5M30\n')
    original=(source,report,settings())
    result=prepare_autolevel(*original)
    assert (source,report,settings())==original
    job=result.prepared_job
    assert job.report.allowed and job.report.arc_count==0
    assert job.final_machine_mm==pytest.approx((2.,2.,5.))
    cuts=[e for e in motions(result) if e.motion==1]
    for e in cuts:
        assert e.end[2]==pytest.approx(-.1+.01*e.end[0]+.02*e.end[1],abs=1e-5)
    assert 'M3S500' in job.source.text or 'S500M3' in job.source.text
    assert source.sha256 in job.source.text and result.settings.map_sha256 in job.source.text
    assert len(result.lineage)==len(job.source.text.splitlines())
    assert all(e.feed==60 for e in cuts)


@pytest.mark.parametrize('units,mode,text', [
 ('mm','absolute',HEADER+'G1Z-.1F60\nG1X2Y1'),
 ('inch','absolute','G20G90G17G94\nG1Z-.003937007874F2.3622047244\nG1X.07874015748Y.03937007874'),
 ('mm','incremental','G21G91G17G94\nG1Z-5.1F60\nG1X2Y1')])
def test_mm_inch_incremental_canonical_output(units,mode,text):
    result=prepare_autolevel(*reviewed(text),settings())
    end=motions(result)[-1].end
    assert end==pytest.approx((2.,1.,-.06),abs=1e-5)
    assert all(e.feed==pytest.approx(60,abs=1e-5) for e in motions(result))


def test_rotation_mirror_and_map_g54_offset_use_one_placement():
    placement=Placement(translation=(12.,20.),rotation_deg=90,mirror_x=True)
    value=height_map(lambda x,y:.01*x+.02*y,offset=(10.,18.,3.))
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X1Y1',placement=placement,offset=3.,
                            initial=(0.,0.,2.), machine_max_mm=(30.,30.,20.))
    result=prepare_autolevel(source,report,settings(value))
    assert result.prepared_job.g54_offset_mm==(10.,18.,3.)
    assert result.prepared_job.report.setup.placement.matrix[:4]==(1.,0.,0.,1.)
    assert result.prepared_job.final_machine_mm==pytest.approx((11.,19.,2.93),abs=1e-5)


def test_saddle_refines_within_cells_and_respects_surface_tolerance():
    config=settings(height_map(lambda x,y:x*y),surface_error_mm=.001,max_segment_mm=10.)
    result=prepare_autolevel(*reviewed(HEADER+'G1Z-.1F60\nG1X2Y2'),config)
    events=motions(result)[1:]
    assert len(events)>4
    for e in events:
        midpoint=tuple((a+b)/2 for a,b in zip(e.start,e.end))
        assert abs(midpoint[2]-(-.1+surface_height(config.map,*midpoint[:2])))<=.001


@pytest.mark.parametrize('mode,endpoint,center', [('G2','X0Y1','I-1J0'),
    ('G3','X0Y1','I-1J0'), ('G3','X1Y0','I-1J0')])
def test_circle_direction_helix_endpoints_chord_lengths(mode,endpoint,center):
    config=settings(height_map(lambda x,y:.01*x,offset=(-1.,-1.,0.)),max_segment_mm=.2)
    text=HEADER+'G1Z-.1F60\n'+mode+endpoint+'Z-.2'+center+'\nM30'
    source,report=reviewed(text,initial=(1.,0.,5.))
    result=prepare_autolevel(source,report,config)
    cut=motions(result)[1:]
    assert all(e.arc is None and math.dist(e.start[:2],e.end[:2])<=.2 for e in cut)
    expected_x=0. if 'X0' in endpoint else 1.
    assert result.prepared_job.final_machine_mm[0]==pytest.approx(expected_x,abs=1e-5)
    # map work X=machine X+1
    assert result.prepared_job.final_machine_mm[2]==pytest.approx(-.2+.01*(expected_x+1),abs=1e-5)


@pytest.mark.parametrize('text', [HEADER+'G1Z-.1F60\nG1X3',
 HEADER+'G1Z-.1F60\nG2X0Y1I-1J0', HEADER+'G1Z-.1F60\nM0',
 HEADER+'G1Z-.1F60\nM7'])
def test_out_of_map_or_unsupported_streaming_fails(text):
    with pytest.raises(ValueError):
        prepare_autolevel(*reviewed(text,initial=(1.,0.,5.)),settings())


def test_no_silent_feed_entry_jump_after_rapid():
    source,report=reviewed(HEADER+'G0X1Y1\nG1X2Z-.1F60')
    with pytest.raises(ValueError,match='vertical'):
        prepare_autolevel(source,report,settings())


def test_derived_warped_z_rechecked_against_travel_envelope():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X2Y2',machine_max_mm=(20.,20.,6.))
    with pytest.raises(ValueError):
        prepare_autolevel(source,report,settings(height_map(lambda x,y:4*x*y)))


def test_stale_report_resource_bound_and_cancellation(monkeypatch):
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X2Y2')
    with pytest.raises(ValueError):
        prepare_autolevel(SourceSnapshot('changed.nc',source.text),report,settings())
    with pytest.raises(PreflightCancelled):
        prepare_autolevel(source,report,settings(),cancelled=lambda:True)
    import mikrocam.core.autolevel as module
    monkeypatch.setattr(module,'MAX_OUTPUT_LINES',5)
    with pytest.raises(ValueError,match='limit'):
        prepare_autolevel(source,report,settings())



def test_rotated_arc_transform_and_complete_source_ancestry():
    value=height_map(lambda x,y:.01*x+.02*y,offset=(-1.,-1.,0.))
    source,report=reviewed(HEADER+'G1Z-.1F60\nG3X0Y1I-1J0',
                           placement=Placement(rotation_deg=90,mirror_x=True),initial=(1.,0.,5.))
    result=prepare_autolevel(source,report,settings(value))
    assert result.prepared_job.final_machine_mm==pytest.approx((-1.,0.,-.08),abs=1e-5)
    assert set(n for n in result.lineage if n is not None)=={2,3}


def test_tiny_dwell_and_once_only_output_end_semantics():
    source,report=reviewed(HEADER+'S500M3G1Z-.1F60\nG4P.000001M8\nG1X1M5M30')
    result=prepare_autolevel(source,report,settings())
    blocks=tuple(iter_blocks(result.prepared_job.source.text))
    words=[item for block in blocks for item in block.words]
    assert words.count(('S',500.))==1 and words.count(('M',3.))==1
    assert words.count(('M',8.))==1 and words.count(('M',5.))==1 and words.count(('M',30.))==1
    assert ('P',.000001) in words
    assert blocks[-1].canonical=='M30'
    assert blocks.index(next(b for b in blocks if ('M',3.) in b.words)) < blocks.index(
        next(b for b in blocks if ('Z',-.1) in b.words))


def test_rounded_radius_arc_rejected_despite_original_preflight_allowance():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG3X0Y1.001I-1J0',initial=(1.,0.,5.))
    config=settings(height_map(lambda x,y:0.,offset=(-.5,-.5,0.)))
    with pytest.raises(ValueError,match='radii'):
        prepare_autolevel(source,report,config)


def test_arc_interior_outside_map_is_rejected_with_endpoints_inside():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG2X1Y0I-1J0',initial=(1.,0.,5.))
    with pytest.raises(ValueError,match='outside'):
        prepare_autolevel(source,report,settings())


def test_late_cancellation_inside_subdivision_never_returns_prefix():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X2Y2')
    calls=0
    def cancel():
        nonlocal calls
        calls+=1
        return calls>30
    with pytest.raises(PreflightCancelled):
        prepare_autolevel(source,report,settings(max_segment_mm=.01),cancelled=cancel)
    assert calls==31


def test_unsafe_derived_rapid_after_surface_following_retract_is_blocked():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X1\nG1Z5\nG0X2')
    with pytest.raises(ValueError,match='preflight'):
        prepare_autolevel(source,report,settings(height_map(lambda x,y:-.02*x)))



def test_float32_machine_translation_cannot_consume_tight_chord_budget():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X.12345',
                           placement=Placement(translation=(10000.,0.)),
                           machine_max_mm=(20000.,20.,20.))
    config=settings(height_map(lambda x,y:0.,offset=(10000.,0.,0.)),chord_error_mm=.0001)
    with pytest.raises(ValueError,match='precision'):
        prepare_autolevel(source,report,config)


def test_historical_same_heights_without_complete_final_retract_rejected():
    source,report=reviewed(HEADER+'G1Z-.1F60\nG1X1')
    incomplete=replace(height_map(),outcome='incomplete')
    with pytest.raises(ValueError,match='complete'):
        prepare_autolevel(source,report,settings(incomplete))


@pytest.mark.parametrize('noop', ['G1X1F60', 'G1Z5F60'])
def test_axis_noop_cannot_establish_compensated_feed_entry(noop):
    source,report=reviewed(HEADER+'G0X1Y1\n'+noop+'\nG1X2Z-.1')
    with pytest.raises(ValueError,match='vertical'):
        prepare_autolevel(source,report,settings())


def test_axis_noop_preserves_outputs_without_manufacturing_motion():
    source,report=reviewed(HEADER+'G0X1Y1\nM3S500G1Z5F60\nG1Z-.1\nG1X2')
    result=prepare_autolevel(source,report,settings())
    assert not any(e.motion==1 and e.end[2]>0 for e in motions(result))
    assert 'M3S500' in result.prepared_job.source.text
