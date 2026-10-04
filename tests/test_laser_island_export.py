"""Island plans keep order in per-pass SVG/DXF and persist in a versioned manifest."""
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import ezdxf
import pytest
from shapely.geometry import box

from mikrocam.core.laser_device import LaserDeviceProfile
from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_json import recipe_from_json, recipe_to_json
from mikrocam.core.laser_manifest import manifest_from_json, manifest_to_json
from mikrocam.core.laser_paths import IslandSettings, PlanOptions
from mikrocam.laser.export import export_plan
from mikrocam.laser.planner import plan_laser


REFERENCE = Path(__file__).parent / 'reference'
LEGACY = LaserRecipe('legacy', (LaserPass('mark', 30, 100, 20, 80), LaserPass('finish', 15, 250, 40, 60)))
MOPA = LaserRecipe('mopa', (LaserPass('mark', 30, 100, 30, 100),), LaserDeviceProfile('mopa', 'MOPA M7 100 W'))
ISLAND = IslandSettings(2.5, overlap_mm=0.25, angle_step_deg=90, order='checkerboard')


def plan(recipe=LEGACY, island=ISLAND, interlace=1):
    job = LaserJob('board', PlanarRegion.from_geometry(box(0.1, 0.1, 7.9, 4.9)), recipe)
    options = PlanOptions(contour_mode='outer', hatch=True, spacing_mm=0.5, angle_deg=15,
                          cross_hatch=True, interlace_n=interlace, island=island)
    return plan_laser(job, options)


def manifest_of(path):
    with zipfile.ZipFile(path) as archive:
        return manifest_from_json(archive.read('manifest.json').decode()), archive


@pytest.mark.parametrize('recipe', [LEGACY, MOPA])
@pytest.mark.parametrize('format', ['svg', 'dxf'])
def test_island_export_writes_v3_and_keeps_path_order_for_every_pass(tmp_path, recipe, format):
    source = plan(recipe)
    target = export_plan(source, tmp_path / 'island.zip', format)
    with zipfile.ZipFile(target) as archive:
        data = manifest_from_json(archive.read('manifest.json').decode())
        assert data['schema_version'] == 3
        assert data['island'] == {'tile_size_mm': 2.5, 'overlap_mm': 0.25,
                                  'angle_step_deg': 90.0, 'order': 'checkerboard'}
        assert (data['device'] is None) == (recipe.device is None)
        assert recipe_from_json(archive.read('recipe.json').decode()) == recipe
        assert 'island' in archive.read('README.txt').decode().lower()
        assert len(data['passes']) == len(recipe.passes)
        for record in data['passes']:
            document = archive.read(record['file']).decode()
            if format == 'svg':
                root = ET.fromstring(document)
                polylines = root.findall('{http://www.w3.org/2000/svg}polyline')
                xmin, ymax = data['bounds_mm'][0], data['bounds_mm'][3]
                exported = [tuple((float(x) + xmin, ymax - float(y)) for x, y in
                                  (pair.split(',') for pair in item.get('points').split())) for item in polylines]
            else:
                drawing = ezdxf.read(StringIO(document))
                exported = [tuple((x, y) for x, y, *_ in entity.get_points()) for entity in drawing.modelspace()]
            assert len(exported) == record['path_count'] == len(source.paths)
            for points, path in zip(exported, source.paths):
                expected = path.points[:-1] if format == 'dxf' and path.points[0] == path.points[-1] else path.points
                assert len(points) == len(expected)
                flat = [value for point in points for value in point]
                assert flat == pytest.approx([value for point in expected for value in point], abs=1e-9)


@pytest.mark.parametrize('recipe', [LEGACY, MOPA])
def test_export_without_islands_is_byte_identical_to_previous_versions(tmp_path, recipe):
    options = PlanOptions(hatch=True, spacing_mm=1, interlace_n=2)
    job = LaserJob('board', PlanarRegion.from_geometry(box(0, 0, 4, 3)), LaserRecipe(
        recipe.name, (recipe.passes[0],), recipe.device))
    fixture = 'laser_manifest_v1.json' if recipe.device is None else 'laser_manifest_v2.json'
    target = export_plan(plan_laser(job, options), tmp_path / 'plain.zip', 'svg' if recipe.device is None else 'dxf')
    with zipfile.ZipFile(target) as archive:
        assert archive.read('manifest.json') == (REFERENCE / fixture).read_bytes()
        assert 'island' not in archive.read('README.txt').decode().lower()


@pytest.mark.parametrize('fixture,version', [('laser_manifest_v1.json', 1), ('laser_manifest_v2.json', 2)])
def test_old_manifest_files_open_losslessly_and_upgrade_to_v3(fixture, version):
    from mikrocam.core.laser_manifest import manifest_island, upgrade_manifest
    text = (REFERENCE / fixture).read_text(encoding='utf-8')
    data = manifest_from_json(text)
    assert data['schema_version'] == version and manifest_to_json(data) == text
    assert manifest_island(data) is None
    upgraded = upgrade_manifest(data)
    assert upgraded['schema_version'] == 3 and upgraded['island'] is None
    assert upgraded['device'] == data.get('device')
    assert {key: value for key, value in upgraded.items() if key not in ('schema_version', 'island', 'device')} == {
        key: value for key, value in data.items() if key not in ('schema_version', 'device')}
    assert manifest_from_json(manifest_to_json(upgraded)) == upgraded
    assert manifest_from_json(text) == data


def test_v3_roundtrip_is_deterministic_and_island_is_recoverable(tmp_path):
    from mikrocam.core.laser_manifest import manifest_island, upgrade_manifest
    first = export_plan(plan(), tmp_path / 'a.zip', 'svg')
    second = export_plan(plan(), tmp_path / 'b.zip', 'svg')
    assert first.read_bytes() == second.read_bytes()
    data, _ = manifest_of(first)
    assert manifest_island(data) == ISLAND
    assert upgrade_manifest(data) == data and upgrade_manifest(data) is not data
    assert manifest_to_json(manifest_from_json(manifest_to_json(data))) == manifest_to_json(data)


def valid_v3():
    text = (REFERENCE / 'laser_manifest_v1.json').read_text(encoding='utf-8')
    data = json.loads(text)
    data.update(schema_version=3, device=None, island={'tile_size_mm': 5.0, 'overlap_mm': 0.0,
                                                       'angle_step_deg': 90.0, 'order': 'raster'})
    return data


@pytest.mark.parametrize('change', [
    lambda d: d.pop('island'), lambda d: d.pop('device'), lambda d: d.update(schema_version=4),
    lambda d: d['island'].update(extra=1), lambda d: d['island'].pop('order'),
    lambda d: d['island'].update(tile_size_mm=0), lambda d: d['island'].update(overlap_mm=5),
    lambda d: d['island'].update(order='spiral'), lambda d: d['island'].update(angle_step_deg=True),
    lambda d: d.update(island=[]),
    lambda d: d['passes'][0]['settings'].update(min_power_percent=None),
    lambda d: d.update(device={'kind': 'mopa'}),
])
def test_v3_manifest_is_strict(change):
    data = valid_v3()
    assert manifest_from_json(manifest_to_json(data)) == data
    change(data)
    with pytest.raises(ValueError):
        manifest_to_json(data)


def test_v3_profiled_settings_require_device_fields():
    text = (REFERENCE / 'laser_manifest_v2.json').read_text(encoding='utf-8')
    data = json.loads(text)
    data.update(schema_version=3, island=None)
    assert manifest_from_json(manifest_to_json(data)) == data
    broken = deepcopy(data)
    broken['device'] = None
    with pytest.raises(ValueError):
        manifest_to_json(broken)


def test_recipe_json_save_reopen_regenerates_identical_island_plan(tmp_path):
    for recipe in (LEGACY, MOPA):
        saved = tmp_path / 'recipe.json'
        saved.write_text(recipe_to_json(recipe), encoding='utf-8')
        reopened = recipe_from_json(saved.read_text(encoding='utf-8'))
        assert reopened == recipe
        assert json.loads(recipe_to_json(reopened))['schema_version'] == (2 if recipe.device else 1)
        assert plan(reopened).paths == plan(recipe).paths
