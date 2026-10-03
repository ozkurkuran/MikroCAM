"""Real device distinctions, explicit bounds and legacy persistence contracts."""
from dataclasses import replace
import json
from pathlib import Path
import zipfile
from types import SimpleNamespace
import pytest
from mikrocam.core.laser_job import LaserPass, LaserRecipe
from mikrocam.core.laser_json import recipe_from_json, recipe_to_json, job_from_json, job_to_json


def profile(kind, **kwargs):
    from mikrocam.core.laser_device import LaserDeviceProfile
    return LaserDeviceProfile(kind, 'MOPA M7 100 W' if kind == 'mopa' else kind, **kwargs)


def recipe(kind):
    values = {'name': 'one', 'power_percent': None if kind == 'uv' else 20, 'speed_mm_s': 100}
    if kind in ('fiber', 'mopa', 'uv'): values['frequency_khz'] = 30
    if kind in ('mopa', 'uv'): values['pulse_width_ns'] = 100
    if kind == 'ruida_rf_co2': values.update(pwm_frequency_khz=20, min_power_percent=10)
    return LaserRecipe('explicit', (LaserPass(**values),), device=profile(kind))


@pytest.mark.parametrize('kind', ['diode', 'co2', 'ruida_rf_co2', 'fiber', 'mopa', 'uv'])
def test_every_device_has_only_applicable_values_and_strict_roundtrip(kind):
    original = recipe(kind); text = recipe_to_json(original)
    assert json.loads(text)['schema_version'] == 2
    assert recipe_from_json(text) == original
    assert recipe_to_json(recipe_from_json(text)) == text
    if kind in ('diode', 'co2', 'ruida_rf_co2'):
        assert original.passes[0].frequency_khz is None and original.passes[0].pulse_width_ns is None


def test_schema_one_is_unspecified_without_inferred_device_or_changed_values():
    data = json.loads((Path(__file__).parent / 'reference/laser_recipe_v1.json').read_text())
    original = recipe_from_json(json.dumps(data))
    assert getattr(original, 'device', None) is None
    assert json.loads(recipe_to_json(original)) == data


@pytest.mark.parametrize('kind,field', [('diode','frequency_khz'), ('co2','pulse_width_ns'),
    ('fiber','pulse_width_ns'), ('mopa','pwm_frequency_khz'), ('uv','power_percent'),
    ('uv','min_power_percent')])
def test_inapplicable_fields_are_rejected_without_silent_loss(kind, field):
    original = recipe(kind)
    with pytest.raises(ValueError, match=field):
        replace(original, passes=(replace(original.passes[0], **{field:10}),))


@pytest.mark.parametrize('kind,field', [('diode','power_percent'), ('co2','power_percent'),
    ('fiber','frequency_khz'), ('mopa','pulse_width_ns'), ('uv','frequency_khz')])
def test_device_required_fields_cannot_be_null(kind,field):
    original = recipe(kind)
    with pytest.raises(ValueError, match=field):
        replace(original, passes=(replace(original.passes[0], **{field:None}),))


def test_frequency_and_pwm_have_independent_units_and_profile_limits():
    original = recipe('mopa')
    bounded = profile('mopa', frequency_range_khz=(20, 100), pulse_width_range_ns=(50, 200),
                      pulse_widths_ns=(50, 100, 200))
    assert replace(original, device=bounded).passes[0].pulse_width_ns == 100
    for values in ({'frequency_khz':19}, {'frequency_khz':101}, {'pulse_width_ns':75}, {'pulse_width_ns':201}):
        with pytest.raises(ValueError): replace(original, device=bounded, passes=(replace(original.passes[0], **values),))
    rf = recipe('ruida_rf_co2')
    with pytest.raises(ValueError, match='pwm_frequency_khz'):
        replace(rf, device=profile('ruida_rf_co2', pwm_frequency_range_khz=(1,10)))
    assert replace(rf, passes=(replace(rf.passes[0], pwm_frequency_khz=None),)).passes[0].pwm_frequency_khz is None


@pytest.mark.parametrize('kwargs', [dict(kind='unknown'), dict(name=''),
    dict(frequency_range_khz=(100,20)), dict(frequency_range_khz=(True,100)),
    dict(pulse_width_range_ns=(0,100)), dict(pulse_widths_ns=(50,50)),
    dict(pulse_widths_ns=[50]), dict(pulse_widths_ns=(float('inf'),)),
    dict(pwm_frequency_range_khz=(1,10))])
def test_invalid_or_inapplicable_profile_bounds_are_rejected(kwargs):
    values={'kind':'mopa','name':'explicit'}; values.update(kwargs)
    from mikrocam.core.laser_device import LaserDeviceProfile
    with pytest.raises(ValueError): LaserDeviceProfile(**values)


def test_minimum_power_is_optional_finite_and_cannot_exceed_main_power():
    original=recipe('co2')
    assert replace(original, passes=(replace(original.passes[0],min_power_percent=0),)).passes[0].min_power_percent == 0
    for value in (-1,21,101,True,float('nan')):
        with pytest.raises(ValueError): replace(original,passes=(replace(original.passes[0],min_power_percent=value),))


@pytest.mark.parametrize('mutation', [lambda d:d.update(schema_version=3),lambda d:d.update(schema_version=True),
    lambda d:d['device'].update(extra=1),lambda d:d['device'].pop('kind'),
    lambda d:d['device'].update(kind='diode'),lambda d:d['passes'][0].update(extra=1),
    lambda d:d['passes'][0].pop('pwm_frequency_khz'),lambda d:d['device'].update(pulse_widths_ns=[True])])
def test_schema_two_is_strict_and_rejects_profile_mismatch(mutation):
    data=json.loads(recipe_to_json(recipe('mopa'))); mutation(data)
    with pytest.raises(ValueError): recipe_from_json(json.dumps(data))


def test_profiled_job_uses_version_two_and_preserves_source_placement():
    from test_laser_json import make_job
    original=replace(make_job(),recipe=recipe('diode')); text=job_to_json(original)
    assert json.loads(text)['schema_version']==2
    assert job_from_json(text)==original
    data=json.loads(text); data['schema_version']=1
    with pytest.raises(ValueError): job_from_json(json.dumps(data))


@pytest.mark.parametrize('kind',['diode','mopa','uv','ruida_rf_co2'])
def test_visual_project_and_png_package_preserve_profile_without_native_claim(kind,tmp_path):
    from test_visual_recipe import job
    from mikrocam.bridge.visual_recipe import job_to_payload,job_from_payload
    from mikrocam.bridge.visual_project import attach_visual_job,read_visual_job
    from mikrocam.bridge.visual_export import export_png_package
    from mikrocam.laser.visual_plan import build_plan
    original=replace(job(),laser_recipe=recipe(kind))
    payload=job_to_payload(original)
    assert payload['schema_version']==2
    assert job_from_payload(payload).laser_recipe==original.laser_recipe
    owner=SimpleNamespace(obj_options={}); attach_visual_job(owner,original)
    assert read_visual_job(owner).laser_recipe==original.laser_recipe
    target=tmp_path/'passes.zip'
    export_png_package(original,build_plan(original.mask,original.interlace,original.revision),target)
    with zipfile.ZipFile(target) as archive:
        saved=json.loads(archive.read('job.json'))
        assert job_from_payload(saved).laser_recipe==original.laser_recipe
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['native_lightburn_settings_applied'] is False


@pytest.mark.parametrize('kind',['diode','mopa','ruida_rf_co2'])
def test_geometry_transfer_manifest_retains_device_and_null_fields(kind,tmp_path):
    from test_laser_export import plan
    from mikrocam.laser.export import export_plan
    from mikrocam.core.laser_manifest import manifest_from_json
    old=plan(); original=replace(old,job=replace(old.job,recipe=recipe(kind)))
    target=tmp_path/'geometry.zip'; export_plan(original,target,'svg')
    with zipfile.ZipFile(target) as archive:
        data=manifest_from_json(archive.read('manifest.json').decode())
        assert data['schema_version']==2 and data['device']['kind']==kind
        assert recipe_from_json(archive.read('recipe.json').decode())==original.job.recipe
        assert data['passes'][0]['settings']['frequency_khz']==original.job.recipe.passes[0].frequency_khz


def test_new_recipe_and_visual_schema_are_separate_from_legacy_schema():
    root=Path(__file__).parents[1]
    old=json.loads((root/'mikrocam/laser/visual_recipe.schema.json').read_text())
    new=json.loads((root/'mikrocam/laser/visual_recipe_v2.schema.json').read_text())
    recipe_schema=json.loads((root/'mikrocam/core/laser_recipe_v2.schema.json').read_text())
    assert old['properties']['schema_version']=={'const':1}
    assert new['properties']['schema_version']=={'const':2}
    assert recipe_schema['properties']['schema_version']=={'const':2}
    assert 'device' in recipe_schema['required']
