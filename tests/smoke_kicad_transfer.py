"""Native aligned KiCad transfer import, DRC gate and saved-project provenance."""
from pathlib import Path
import os


def _settle(app,qapp,dialog,errors,pump_until):
    pump_until(qapp,lambda:not dialog.busy and len(dialog.imported_indices)==len(dialog.files) and bool(dialog.files) and app.workers._pending_count==0,errors,'KiCad production worker import')


def kicad_transfer_journey(app,qapp,sandbox,errors,pump_until,root):
    from test_kicad_package import sample
    from mikrocam.kicad.package import write_package,read_package
    from mikrocam.bridge.kicad_transfer import read_transfer_metadata
    from smoke_manufacturing_import import _reopen
    from shapely import union_all
    import pytest
    assert not app.collection.get_names()
    value=sample();path=sandbox/'exit-save board.mcam-transfer';write_package(path,value)
    app.on_startup_args([str(path)])
    dialog=app._kicad_transfer_dialog
    assert dialog is not None
    _settle(app,qapp,dialog,errors,pump_until)
    names=tuple(Path(f.name).stem for f in value.manifest.files)
    for name in names:
        owner=app.collection.get_by_name(name)
        assert owner is not None and read_transfer_metadata(owner)==value.manifest
        material=union_all(owner.solid_geometry);factor=1.0 if app.app_units=='MM' else 25.4
        print('KICAD_NATIVE_OBJECT_UNITS_BOUNDS',name,app.app_units,material.bounds,flush=True)
        assert tuple(v*factor for v in material.bounds)==pytest.approx((0.5,0.5,1.5,1.5),abs=0.001),'Copper/drill millimetre dimensions changed'
        assert (material.centroid.x*factor,material.centroid.y*factor)==pytest.approx((1.0,1.0),abs=1e-9),'Copper/drill origins diverged'
    screenshot=root/'.venv/kicad-transfer-smoke.png';qapp.processEvents();assert dialog.grab().save(str(screenshot))
    dialog.reject();qapp.processEvents();assert app._kicad_transfer_dialog is None
    previous=app.collection.get_by_name(names[0]);project=sandbox/'kicad-transfer.FlatPrj'
    app.f_handlers.save_project(str(project),silent=True);assert project.is_file();path.unlink()
    _reopen(app,qapp,project,previous,names[0],errors,pump_until)
    for name in names:assert read_transfer_metadata(app.collection.get_by_name(name))==value.manifest
    app.collection.delete_all();pump_until(qapp,lambda:not app.collection.get_names() and app.workers._pending_count==0,errors,'KiCad source cleanup')
    print('KICAD_STARTUP_DIRECT_MM_ALIGNMENT_SOURCE_PROJECT_ROUNDTRIP_OK',screenshot,flush=True)
    real=os.environ.get('MIKROCAM_REAL_KICAD_PACKAGE')
    if not real:return
    package=read_package(Path(real));assert package.manifest.needs_acknowledgement
    app.on_startup_args([real]);dialog=app._kicad_transfer_dialog
    pump_until(qapp,lambda:dialog.package is not None,errors,'real KiCad package load')
    assert not dialog.busy and not app.collection.get_names() and not dialog.import_button.isEnabled()
    dialog.acknowledge.setChecked(True);dialog.review_selected();dialog.import_selected()
    _settle(app,qapp,dialog,errors,pump_until)
    owners=[app.collection.get_by_name(Path(f.name).stem) for f in package.manifest.files]
    assert len(owners)==4 and all(o is not None for o in owners)
    roles={f.role:o for f,o in zip(package.manifest.files,owners)}
    outline=union_all(roles['Edge.Cuts'].solid_geometry).envelope.buffer(0.01)
    from shapely.geometry import Point
    for tool in roles['PTH'].tools.values():
        for point in tool.get('drills',[]):assert outline.covers(Point(point)), 'Real drill/outline coordinates diverged'
    assert all(read_transfer_metadata(o)==package.manifest for o in owners)
    screenshot=root/'.venv/kicad-real-import-smoke.png';qapp.processEvents();assert dialog.grab().save(str(screenshot))
    dialog.reject();app.collection.delete_all()
    pump_until(qapp,lambda:not app.collection.get_names() and app.workers._pending_count==0,errors,'real KiCad owned cleanup')
    print('KICAD_REAL_IPC_PACKAGE_FOUR_ROLES_DRC_ACK_ALIGNMENT_OK',screenshot,flush=True)
