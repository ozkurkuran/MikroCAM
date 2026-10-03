"""Real QThreads and thin visual panel lifecycle checks, without a machine."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import pytest
from PyQt6 import QtCore, QtWidgets
from mikrocam.ui.visual_interlace_panel import VisualInterlacePanel
from mikrocam.ui.visual_worker import VisualWorker
from mikrocam.core.visual import PreparationSettings


class Host:
    def __init__(self): self.parent=QtWidgets.QMainWindow(); self.published=[]
    def parent_widget(self): return self.parent
    def source_names(self): return []
    def publish_payload(self,job,payload): self.published.append(job)


def image_file(tmp_path):
    path=tmp_path/'test.png'; image=Image.new('1',(13,10),1); image.putpixel((0,0),0); image.save(path)
    return path


def test_file_prepare_preview_save_and_open(qtbot,tmp_path):
    host=Host(); panel=VisualInterlacePanel(host); qtbot.addWidget(panel)
    panel.open_source(image_file(tmp_path))
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.source is not None and panel.width.value()==pytest.approx(.65)
    panel.prepare()
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job is not None and panel.job.mask.black_pixel_count==1
    assert panel.plan.active_pass_count==1 and len(panel.plan.passes)==3
    assert not panel.lightburn_button.isEnabled()
    destination=tmp_path/'job.json'; panel.save_job(destination)
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert destination.exists()
    before=panel.job.mask.sha256
    panel.load_job(destination)
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job.mask.sha256==before
    panel.save_to_project()
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert len(host.published)==1
    panel.shutdown()


def test_changed_input_cancels_old_worker_and_disables_export(qtbot,tmp_path,monkeypatch):
    import threading
    import mikrocam.ui.visual_worker as module
    host=Host(); panel=VisualInterlacePanel(host); qtbot.addWidget(panel)
    panel.open_source(image_file(tmp_path)); qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    started=threading.Event(); release=threading.Event(); original=module.prepare_visual_job
    def blocked(*args,**kwargs):
        started.set(); release.wait(5); return original(*args,**kwargs)
    monkeypatch.setattr(module,'prepare_visual_job',blocked)
    panel.prepare(); qtbot.waitUntil(started.is_set,timeout=2000)
    counter=[]; timer=QtCore.QTimer(); timer.timeout.connect(lambda:counter.append(True)); timer.start(10)
    qtbot.waitUntil(lambda:len(counter)>=3,timeout=2000)
    panel.threshold.setValue(129); release.set()
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job is None and not panel.save_button.isEnabled()
    timer.stop(); panel.shutdown()


def test_cancelled_decode_keeps_previous_job(qtbot,tmp_path):
    host=Host(); panel=VisualInterlacePanel(host); qtbot.addWidget(panel)
    panel.open_source(image_file(tmp_path)); qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    panel.prepare(); qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    previous=panel.job
    bad=tmp_path/'bad.png'; bad.write_bytes(b'not image')
    panel.open_source(bad); qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job is previous and panel.source is previous.source
    assert 'Desteklenmeyen kaynak biçimi' in panel.status.text()
    assert 'UNSUPPORTED_SOURCE_FORMAT' in panel.status.toolTip()
    panel.shutdown()


def test_project_source_is_decoded_in_worker(qtbot, tmp_path):
    from mikrocam.bridge.visual_recipe import job_to_payload
    from test_visual_recipe import job
    class SavedHost(Host):
        def source_names(self): return ['saved carrier']
        def project_payload(self,name):
            assert name=='saved carrier'
            return job_to_payload(job())
    panel=VisualInterlacePanel(SavedHost()); qtbot.addWidget(panel)
    panel.load_project_source()
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job.mask.black_pixel_count==1 and panel.job.interlace.round_count==3
    panel.shutdown()


def test_preview_fits_narrow_dock(qtbot):
    from test_visual_recipe import job
    from mikrocam.ui.visual_preview import VisualPreview
    widget=VisualPreview(); qtbot.addWidget(widget)
    widget.resize(300,250); widget.show(); widget.set_job(job())
    qtbot.wait(25)
    for index, label in enumerate(widget.labels):
        widget.tabs.setCurrentIndex(index); qtbot.wait(10)
        if label.pixmap() is not None:
            assert label.pixmap().width() <= label.contentsRect().width()
            assert label.pixmap().height() <= label.contentsRect().height()


def test_optional_copper_source_with_explicit_roi(qtbot):
    from shapely.geometry import box
    class CopperHost(Host):
        def geometry_source_names(self): return ['top copper']
        def geometry_source_snapshot(self,name):
            return (box(2,2,8,8).difference(box(4,4,6,6)),),'MM'
    panel=VisualInterlacePanel(CopperHost()); qtbot.addWidget(panel)
    panel.roi[2].setValue(10); panel.roi[3].setValue(10)
    panel.open_geometry_source()
    qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.source.info.kind=='geometry_snapshot'
    panel.prepare(); qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job.mask.burn[60,60] and not panel.job.mask.burn[100,100]
    assert panel.job.placement.translation==(0,0)
    panel.shutdown()


def test_loaded_explicit_recipe_and_direction_survive_reprepare(qtbot,tmp_path):
    from dataclasses import replace
    from test_visual_recipe import job
    from mikrocam.bridge.visual_recipe import save_visual_recipe
    from mikrocam.core.laser_job import LaserRecipe,LaserPass
    from mikrocam.core.placement import Placement
    original=job()
    original=replace(original,interlace=replace(original.interlace,bidirectional=False,direction_policy='source_row_parity'),
        placement=Placement(origin=(1,2),translation=(4,8),rotation_deg=90,mirror_x=True),
        laser_recipe=LaserRecipe('explicit',(LaserPass('one',10,20,30,40),)))
    path=tmp_path/'explicit.json';save_visual_recipe(original,path)
    panel=VisualInterlacePanel(Host());qtbot.addWidget(panel)
    panel.load_job(path);qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    panel.threshold.setValue(127);panel.prepare();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job.laser_recipe==original.laser_recipe
    assert panel.job.placement==original.placement
    assert panel.job.interlace.bidirectional is False
    assert panel.job.interlace.direction_policy=='source_row_parity'
    panel.shutdown()


def test_loaded_precise_grid_survives_threshold_only_edit(qtbot,tmp_path):
    from test_visual_recipe import job
    from mikrocam.bridge.visual_workflow import prepare_visual_job
    from mikrocam.core.visual import PreparationSettings
    from mikrocam.bridge.visual_recipe import save_visual_recipe
    original=job()
    precise=prepare_visual_job(original.source,PreparationSettings(.65000001,.50000001,508.000001),
        original.interlace,original.placement,None,1)
    path=tmp_path/'precise.json';save_visual_recipe(precise,path)
    panel=VisualInterlacePanel(Host());qtbot.addWidget(panel)
    panel.load_job(path);qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    panel.threshold.setValue(129);panel.prepare();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job.mask.grid==precise.mask.grid
    assert panel.job.preparation.requested_dpi==508.000001
    panel.shutdown()


def test_quarter_turn_swaps_physical_dimensions_without_rescaling(qtbot,tmp_path):
    panel=VisualInterlacePanel(Host());qtbot.addWidget(panel)
    panel.open_source(image_file(tmp_path));qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert (panel.width.value(),panel.height.value())==pytest.approx((.65,.5))
    panel.rotation.setCurrentIndex(1)
    assert (panel.width.value(),panel.height.value())==pytest.approx((.5,.65))
    panel.prepare();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert (panel.job.mask.grid.width_px,panel.job.mask.grid.height_px)==(10,13)
    assert panel.job.mask.burn[0,9]
    panel.rotation.setCurrentIndex(2)
    assert (panel.width.value(),panel.height.value())==pytest.approx((.65,.5))
    panel.shutdown()


def test_host_project_failure_is_reported_without_unhandled_qt_exception(qtbot,tmp_path):
    class FailingHost(Host):
        def publish_payload(self,job,payload): raise ValueError('PROJECT_ATTACH_FAILED')
    panel=VisualInterlacePanel(FailingHost());qtbot.addWidget(panel)
    panel.open_source(image_file(tmp_path));qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    panel.prepare();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    before=panel.job.mask.sha256
    panel.save_to_project();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert 'İş projeye eklenemedi' in panel.status.text()
    assert panel.job.mask.sha256==before and panel.save_button.isEnabled()
    panel.shutdown()


def test_preview_zoom_uses_snapshot_without_changing_production_mask(qtbot):
    from test_visual_recipe import job
    from mikrocam.ui.visual_preview import VisualPreview
    original=job();widget=VisualPreview();qtbot.addWidget(widget);widget.set_job(original)
    widget.tabs.setCurrentIndex(2);widget.open_zoom()
    dialog=widget.zoom_window;qtbot.addWidget(dialog)
    assert dialog.image.pixmap().width()==widget.labels[2].original.width()
    dialog.scale.setValue(200)
    assert dialog.image.pixmap().width()==widget.labels[2].original.width()*2
    assert original.mask.sha256==widget.job.mask.sha256
    dialog.close()


@pytest.mark.parametrize('units', ['MM', 'IN'])
def test_project_carrier_keeps_host_units_and_embedded_mm_job(units):
    from test_visual_recipe import job
    from mikrocam.bridge.visual_host import VisualHost
    from mikrocam.bridge.visual_recipe import job_to_payload, job_from_payload
    from mikrocam.bridge.visual_project import PAYLOAD_KEY
    original = job(); payload = job_to_payload(original)
    owner = SimpleNamespace(units=units, obj_options={})
    def create(kind, name, initialize, plot):
        assert kind == 'geometry' and not plot
        initialize(owner, None)
        assert owner.units == units  # The real factory converts mismatches before UI setup.
        return owner
    app = SimpleNamespace(main_thread=SimpleNamespace(isCurrentThread=lambda: True),
                          app_obj=SimpleNamespace(new_object=create))
    VisualHost(app).publish_payload(original, payload)
    restored = job_from_payload(owner.obj_options[PAYLOAD_KEY])
    assert restored.mask.grid == original.mask.grid
    assert restored.placement == original.placement
    assert restored.mask.sha256 == original.mask.sha256
