"""Device-aware recipes in the real visual dock and host project lifecycle."""
import multiprocessing
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import smoke_app
import smoke_visual_app


def device_journey(app, qapp, sandbox, errors):
    from PIL import Image
    from mikrocam.ui.visual_interlace_panel import open_visual_interlace
    from mikrocam.bridge.visual_project import read_visual_job
    from smoke_manufacturing_import import _reopen
    from test_laser_devices import recipe
    import json
    import zipfile
    action = next(action for action in app.ui.menu_plugins.actions() if action.text() == 'Görsel satır serpiştirme')
    action.trigger(); panel = open_visual_interlace(app); app.ui.showMaximized()
    path = sandbox / 'device-source.png'
    image = Image.new('1', (13, 10), 1); image.putpixel((0, 0), 0); image.save(path)
    panel.open_source(path)
    smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'device source')
    panel.recipe_group.setChecked(True)
    for kind in ('mopa', 'diode'):
        expected = recipe(kind); panel.recipe_editor.set_recipe(expected); panel.prepare()
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, kind + ' device prepare')
        assert panel.job is not None and panel.job.laser_recipe == expected, panel.status.text()
        job_hash = panel.job.mask.sha256
        destination = sandbox / (kind + '.json'); panel.save_job(destination)
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, kind + ' JSON save')
        panel.load_job(destination)
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, kind + ' JSON reopen')
        assert panel.job.laser_recipe == expected and panel.job.mask.sha256 == job_hash
        assert panel.recipe_editor.get_recipe() == expected
        package = sandbox / (kind + '-groups.zip'); panel._start('png', (panel.job, panel.plan, package))
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, kind + ' PNG export')
        with zipfile.ZipFile(package) as archive:
            data = json.loads(archive.read('job.json'))
            assert data['schema_version'] == 2 and data['laser_recipe']['device']['kind'] == kind
        panel.save_to_project()
        smoke_app.pump_until(qapp, lambda: panel.worker is None and bool(app.collection.get_names()), errors, kind + ' carrier')
        names = app.collection.get_names(); assert len(names) == 1, names
        owner = app.collection.get_by_name(names[0]); assert read_visual_job(owner).laser_recipe == expected
        project = sandbox / (kind + '.FlatPrj'); app.f_handlers.save_project(str(project), silent=True)
        assert project.is_file(); _reopen(app, qapp, project, owner, names[0], errors, smoke_app.pump_until)
        restored = read_visual_job(app.collection.get_by_name(names[0]))
        assert restored.laser_recipe == expected and restored.mask.sha256 == job_hash
        panel.widget().ensureWidgetVisible(panel.recipe_editor); qapp.processEvents()
        assert panel.grab().save(str(smoke_app.ROOT / '.venv' / (kind + '-device-native.png')))
        app.collection.delete_all()
        smoke_app.pump_until(qapp, lambda: not app.collection.get_names(), errors, 'device carrier cleanup')
        print('LASER_DEVICE_' + kind.upper() + '_JSON_PNG_PROJECT_ROUNDTRIP_OK', flush=True)
    panel.shutdown(); panel.close()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    smoke_visual_app.visual_journey = device_journey
    smoke_app.run_smoke = smoke_visual_app.run_native_smoke
    (smoke_app.ROOT / '.venv').mkdir(exist_ok=True)
    smoke_app.main()
