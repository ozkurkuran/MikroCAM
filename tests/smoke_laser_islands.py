"""Island tiling in the real Laser CAM dock: recipe JSON reopen, preview and SVG/DXF ZIPs."""
import multiprocessing
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import smoke_app
import smoke_visual_app

_cam_journey = smoke_app.cam_journey


def _export(app, qapp, panel, sandbox, errors, format):
    from io import StringIO
    from unittest.mock import patch
    import xml.etree.ElementTree as ET
    import zipfile
    import ezdxf
    from mikrocam.core.laser_json import recipe_from_json
    from mikrocam.core.laser_manifest import manifest_from_json, manifest_island
    plan, controls = panel.last_plan, panel.export_controls
    target = sandbox / f'island-{format}.zip'
    controls.format_combo.setCurrentIndex(controls.format_combo.findData(format))
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=(str(target), '')):
        controls.export_zip()
    smoke_app.pump_until(qapp, lambda: not panel.busy, errors, f'island {format} export')
    assert target.is_file(), panel.status_label.text()
    with zipfile.ZipFile(target) as archive:
        manifest = manifest_from_json(archive.read('manifest.json').decode('utf-8'))
        assert manifest['schema_version'] == 3 and manifest_island(manifest) == plan.options.island
        assert recipe_from_json(archive.read('recipe.json').decode('utf-8')) == plan.job.recipe
        assert 'island' in archive.read('README.txt').decode('utf-8').lower()
        for record in manifest['passes']:
            document = archive.read(record['file']).decode('utf-8')
            if format == 'svg':
                count = len(ET.fromstring(document).findall('{http://www.w3.org/2000/svg}polyline'))
            else:
                drawing = ezdxf.read(StringIO(document))
                assert drawing.units == 4 and not drawing.audit().has_errors
                count = len(drawing.modelspace())
            assert count == record['path_count'] == len(plan.paths)
    (smoke_app.ROOT / '.venv' / target.name).write_bytes(target.read_bytes())
    print('LASER_ISLAND_' + format.upper() + '_EXPORT_V3_OK', target.stat().st_size, flush=True)


def island_journey(app, qapp, sandbox, errors):
    from unittest.mock import patch
    from mikrocam.core.laser_job import LaserPass, LaserRecipe
    from mikrocam.core.laser_paths import IslandSettings
    from mikrocam.ui.laser_cam import open_laser_cam
    _cam_journey(app, qapp, sandbox, errors)
    action = next(action for action in app.ui.menu_plugins.actions() if action.text() == 'Laser CAM')
    action.trigger()
    panel = open_laser_cam(app)
    app.ui.showMaximized()
    panel.source_combo.setCurrentIndex(panel.source_combo.findData('smoke_gerber'))
    recipe = LaserRecipe('Synthetic island smoke only', (LaserPass('Reference', 20, 100, 20, 80),
                                                         LaserPass('Finish', 10, 150, 30, 60)))
    panel.set_recipe(recipe)
    saved = sandbox / 'island-recipe.json'
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=(str(saved), '')):
        panel._save_recipe()
    panel.recipe_editor.name_edit.clear()
    with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName', return_value=(str(saved), '')):
        panel._load_recipe()
    assert panel.recipe == recipe, panel.status_label.text()
    panel.hatch_enabled.setChecked(True)
    panel.hatch_spacing.setValue(0.25)
    panel.island_enabled.setChecked(True)
    panel.island_tile.setValue(3)
    panel.island_overlap.setValue(0.1)
    panel.island_angle_step.setValue(90)
    panel.island_order.setCurrentIndex(panel.island_order.findData('checkerboard'))
    panel.generate()
    smoke_app.pump_until(qapp, lambda: not panel.busy, errors, 'island preview')
    plan = panel.last_plan
    assert plan is not None, panel.status_label.text()
    assert plan.options.island == IslandSettings(3, 0.1, 90, 'checkerboard')
    assert plan.job.recipe == recipe and len(plan.pass_plans) == 2
    preview = app._mikrocam_laser_cam_preview
    smoke_app.assert_object(app, preview.obj_options['name'], 'geometry')
    smoke_app.pump_until(qapp, lambda: app.workers._pending_count == 0, errors, 'island preview plotting')
    assert len(preview.solid_geometry) == len(plan.paths)
    print('LASER_ISLAND_PREVIEW_OK', len(plan.paths), flush=True)
    for format in ('svg', 'dxf'):
        _export(app, qapp, panel, sandbox, errors, format)
    panel.input_scroll.ensureWidgetVisible(panel.island_order)
    qapp.processEvents()
    assert app.ui.grab().save(str(smoke_app.ROOT / '.venv/laser-island-native.png'))
    print('LASER_ISLAND_RECIPE_JSON_PREVIEW_SVG_DXF_OK', flush=True)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    smoke_visual_app.visual_journey = lambda *args: None
    smoke_app.cam_journey = island_journey
    smoke_app.run_smoke = smoke_visual_app.run_native_smoke
    (smoke_app.ROOT / '.venv').mkdir(exist_ok=True)
    smoke_app.main()
