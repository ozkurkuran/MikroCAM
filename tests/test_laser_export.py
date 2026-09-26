"""Strict transfer metadata and atomic geometry package publication."""
from copy import deepcopy
import hashlib
import zipfile

import pytest
from shapely.geometry import box

from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_json import recipe_from_json
from mikrocam.core.laser_manifest import manifest_from_json, manifest_to_json
from mikrocam.core.laser_paths import LaserPath, LaserPlan, PlanOptions, PlanningCancelled
from mikrocam.laser.export import export_plan


def plan():
    recipe = LaserRecipe('transfer', (LaserPass('../α/name', 30, 100, 20, 80),
                                     LaserPass('finish', 15, 250, 40, 60)))
    job = LaserJob('board', PlanarRegion.from_geometry(box(0, 0, 25.4, 10)), recipe)
    paths = (LaserPath(((100, -2), (125.4, -2)), 'hatch', 0, 0),
             LaserPath(((100, 0), (101, 0), (100, 0)), 'contour'))
    return LaserPlan(job, PlanOptions(hatch=True, interlace_n=3), paths)


def manifest():
    settings = {'name': 'one', 'power_percent': 30, 'speed_mm_s': 100,
                'frequency_khz': 20, 'pulse_width_ns': 80}
    return {'kind': 'mikrocam.laser-export', 'schema_version': 1, 'format': 'svg',
            'units': 'mm', 'job_name': 'board', 'bounds_mm': [0, -2, 25.4, 0],
            'interlace_n': 3, 'coordinate_mapping': 'svg-local-y-down',
            'recipe_file': 'recipe.json', 'passes': [
                {'index': 1, 'name': 'one', 'file': 'pass-001.svg', 'sha256': 'a' * 64,
                 'path_count': 2, 'settings': settings}]}


def test_manifest_deterministic_strict_roundtrip():
    data = manifest()
    text = manifest_to_json(data)
    assert manifest_from_json(text) == data
    assert manifest_to_json(dict(reversed(list(data.items())))) == text
    assert manifest_to_json(manifest_from_json(text)) == text


@pytest.mark.parametrize('field, value', [
    ('kind', 'other'), ('schema_version', 2), ('schema_version', True),
    ('format', 'pdf'), ('units', 'in'), ('job_name', ''),
    ('bounds_mm', [0, 0, float('inf'), 1]), ('bounds_mm', [0, 0, 1]),
    ('bounds_mm', [2, 0, 1, 1]), ('bounds_mm', [False, 0, 1, 1]),
    ('bounds_mm', [-1e308, 0, 1e308, 1]),
    ('bounds_mm', [0, 0, 10 ** 400, 1]),
    ('interlace_n', True), ('interlace_n', 0), ('interlace_n', 1_000_001),
    ('coordinate_mapping', 'placed-xy'), ('recipe_file', '../recipe.json'),
    ('passes', []), ('passes', {}),
])
def test_manifest_invalid_envelope_fields(field, value):
    data = manifest()
    data[field] = value
    with pytest.raises(ValueError):
        manifest_to_json(data)


@pytest.mark.parametrize('field, value', [
    ('index', True), ('index', 0), ('index', 2), ('name', 'different'),
    ('file', '../one.svg'), ('file', 'pass-001.dxf'),
    ('sha256', 'A' * 64), ('sha256', 'g' * 64), ('sha256', 'a' * 63),
    ('path_count', True), ('path_count', 0), ('path_count', 1.5),
    ('settings', {}), ('settings', None),
])
def test_manifest_invalid_pass_fields(field, value):
    data = manifest()
    data['passes'][0][field] = value
    with pytest.raises(ValueError):
        manifest_to_json(data)


@pytest.mark.parametrize('location', ['root', 'pass', 'settings'])
@pytest.mark.parametrize('change', ['missing', 'unknown'])
def test_manifest_rejects_missing_and_unknown_fields(location, change):
    data = manifest()
    target = data if location == 'root' else data['passes'][0]
    if location == 'settings':
        target = target['settings']
    if change == 'unknown':
        target['unknown'] = 1
    else:
        target.pop(next(iter(target)))
    with pytest.raises(ValueError):
        manifest_to_json(data)


@pytest.mark.parametrize('text', [
    '{"schema_version":1,"schema_version":1}',
    '{"passes":[{"name":"a","name":"b"}]}',
    '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}', 'null',
])
def test_manifest_rejects_duplicate_nonfinite_and_nonobject_json(text):
    with pytest.raises(ValueError):
        manifest_from_json(text)


@pytest.mark.parametrize('field', ['power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns'])
def test_manifest_uses_existing_positive_finite_parameter_validation(field):
    data = manifest()
    data['passes'][0]['settings'][field] = float('nan')
    with pytest.raises(ValueError):
        manifest_to_json(data)


def test_manifest_rejects_overflowing_integer_parameter_as_value_error():
    data = manifest()
    data['passes'][0]['settings']['speed_mm_s'] = 10 ** 400
    with pytest.raises(ValueError):
        manifest_to_json(data)


def test_manifest_rejects_duplicate_pass_names():
    data = manifest()
    second = deepcopy(data['passes'][0])
    second.update(index=2, file='pass-002.svg')
    data['passes'].append(second)
    with pytest.raises(ValueError):
        manifest_to_json(data)


@pytest.mark.parametrize('format', ['svg', 'dxf'])
def test_package_complete_hashes_settings_frame_safe_names_and_stable_metadata(tmp_path, format):
    source = plan()
    destination = tmp_path / 'transfer.zip'
    assert export_plan(source, destination, format) == destination
    with zipfile.ZipFile(destination) as archive:
        assert archive.namelist() == [f'pass-001.{format}', f'pass-002.{format}',
                                     'recipe.json', 'manifest.json', 'README.txt']
        data = manifest_from_json(archive.read('manifest.json').decode())
        assert recipe_from_json(archive.read('recipe.json').decode()) == source.job.recipe
        assert data['bounds_mm'] == [100, -2, 125.4, 0]
        assert data['interlace_n'] == 3
        for item, settings in zip(data['passes'], source.job.recipe.passes):
            assert item['sha256'] == hashlib.sha256(archive.read(item['file'])).hexdigest()
            assert item['name'] == settings.name and item['path_count'] == len(source.paths)
            assert all(item['settings'][key] == getattr(settings, key) for key in item['settings'])
        instructions = archive.read('README.txt').decode().lower()
        for required in ['mm', 'scale', 'y', 'power', 'speed', 'frequency', 'pulse',
                         'manual', 'reorder', 'hardware', 'coupon', 'lightburn', 'ezcad']:
            assert required in instructions
        first_manifest = archive.read('manifest.json')
    export_plan(source, destination, format)
    with zipfile.ZipFile(destination) as archive:
        assert archive.read('manifest.json') == first_manifest
    assert source == plan()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['transfer.zip']


@pytest.mark.parametrize('failure', ['write', 'replace', 'encode', 'flush'])
def test_export_error_preserves_existing_file_and_removes_temp(tmp_path, monkeypatch, failure):
    import mikrocam.laser.export as module
    destination = tmp_path / 'existing.zip'
    destination.write_bytes(b'previous')

    def fail(*args, **kwargs):
        raise OSError('simulated failure')

    if failure == 'write':
        monkeypatch.setattr(zipfile.ZipFile, 'writestr', fail)
    elif failure == 'replace':
        monkeypatch.setattr(module.os, 'replace', fail)
    elif failure == 'flush':
        monkeypatch.setattr(module.os, 'fsync', fail)
    else:
        monkeypatch.setattr(module, '_geometry_document', fail)
    with pytest.raises(OSError, match='simulated'):
        export_plan(plan(), destination, 'svg')
    assert destination.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [destination]


def test_callback_exception_cleans_active_temporary_package(tmp_path, monkeypatch):
    import mikrocam.laser.export as module
    encoded = False

    def encode(*args):
        nonlocal encoded
        encoded = True
        return '<svg/>'

    def cancelled():
        if encoded:
            raise RuntimeError('callback failed')
        return False

    monkeypatch.setattr(module, '_geometry_document', encode)
    with pytest.raises(RuntimeError, match='callback failed'):
        export_plan(plan(), tmp_path / 'never.zip', 'svg', cancelled)
    assert not list(tmp_path.iterdir())


def test_cancel_mid_encoding_preserves_destination_and_cleans_temp(tmp_path, monkeypatch):
    import mikrocam.laser.export as module
    destination = tmp_path / 'existing.zip'
    destination.write_bytes(b'previous')
    stopped = False

    def encode(*args):
        nonlocal stopped
        stopped = True
        return '<svg/>'

    monkeypatch.setattr(module, '_geometry_document', encode)
    with pytest.raises(PlanningCancelled):
        export_plan(plan(), destination, 'svg', lambda: stopped)
    assert destination.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [destination]


def test_cancel_after_replace_reports_success(tmp_path, monkeypatch):
    import mikrocam.laser.export as module
    destination = tmp_path / 'existing.zip'
    destination.write_bytes(b'previous')
    real_replace = module.os.replace
    published = False

    def publish(source, target):
        nonlocal published
        real_replace(source, target)
        published = True

    monkeypatch.setattr(module.os, 'replace', publish)
    assert export_plan(plan(), destination, 'svg', lambda: published) == destination
    assert published and zipfile.is_zipfile(destination)


def test_cancel_at_final_flush_aborts_before_replace(tmp_path, monkeypatch):
    import mikrocam.laser.export as module
    destination = tmp_path / 'existing.zip'
    destination.write_bytes(b'previous')
    stopped = False

    def flushed(fd):
        nonlocal stopped
        stopped = True

    def forbidden_replace(*args):
        pytest.fail('Cancellation before the commit boundary must prevent replacement')

    monkeypatch.setattr(module.os, 'fsync', flushed)
    monkeypatch.setattr(module.os, 'replace', forbidden_replace)
    with pytest.raises(PlanningCancelled):
        export_plan(plan(), destination, 'svg', lambda: stopped)
    assert destination.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize('limit, value', [('MAX_PASSES', 1), ('MAX_EXPORT_PATHS', 3),
                                         ('MAX_EXPORT_VERTICES', 9),
                                         ('MAX_GEOMETRY_BYTES', 2)])
def test_limits_fail_without_replacing_existing_file(tmp_path, monkeypatch, limit, value):
    import mikrocam.laser.export as module
    destination = tmp_path / 'existing.zip'
    destination.write_bytes(b'previous')
    monkeypatch.setattr(module, limit, value)
    with pytest.raises(ValueError, match='limit|exceed'):
        export_plan(plan(), destination, 'svg')
    assert destination.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [destination]


def test_limits_accept_exact_last_valid_counts_and_bytes(tmp_path, monkeypatch):
    import mikrocam.laser.export as module
    monkeypatch.setattr(module, 'MAX_PASSES', 2)
    monkeypatch.setattr(module, 'MAX_EXPORT_PATHS', 4)
    monkeypatch.setattr(module, 'MAX_EXPORT_VERTICES', 10)
    monkeypatch.setattr(module, 'MAX_GEOMETRY_BYTES', 8)
    monkeypatch.setattr(module, '_geometry_document', lambda *args: '1234')
    destination = tmp_path / 'exact.zip'
    assert export_plan(plan(), destination, 'svg') == destination
    assert zipfile.is_zipfile(destination)


def test_manifest_pass_cap_and_index_boundary(monkeypatch):
    import mikrocam.core.laser_manifest as module
    data = manifest()
    second = deepcopy(data['passes'][0])
    second.update(index=2, name='two', file='pass-002.svg')
    second['settings']['name'] = 'two'
    data['passes'].append(second)
    monkeypatch.setattr(module, 'MAX_PASSES', 2)
    assert manifest_from_json(manifest_to_json(data)) == data
    monkeypatch.setattr(module, 'MAX_PASSES', 1)
    with pytest.raises(ValueError):
        manifest_to_json(data)


def test_export_rejects_overflowed_extent_before_encoding(tmp_path, monkeypatch):
    import mikrocam.laser.export as module
    original = plan()
    extreme = LaserPlan(original.job, original.options,
                        (LaserPath(((-1e308, 0), (1e308, 0)), 'contour'),))

    def forbidden_encode(*args):
        pytest.fail('Invalid extent must fail before serialization')

    monkeypatch.setattr(module, '_geometry_document', forbidden_encode)
    with pytest.raises(ValueError, match='finite|extent'):
        export_plan(extreme, tmp_path / 'bad.zip', 'svg')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('format', ['SVG', 'pdf', '', None])
def test_invalid_format_publishes_nothing(tmp_path, format):
    with pytest.raises(ValueError):
        export_plan(plan(), tmp_path / 'bad.zip', format)
    assert not list(tmp_path.iterdir())
