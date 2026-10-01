from dataclasses import replace
from threading import Event, get_ident
import pytest
from PyQt6 import QtCore
from mikrocam.ui.autolevel_panel import AutoLevelPanel
from mikrocam.core.autolevel_surface import AutoLevelSettings
from mikrocam.bridge.probe_files import save_probe_map
from mikrocam.core.probe_map import ProbeMap
from test_autolevel_core import HEADER, reviewed, settings
from test_autolevel_surface import height_map


def inputs():
    return reviewed(HEADER+'M3S500\nG1Z-.1F60\nG1X2Y2\nG0Z5\nM30')


@pytest.fixture
def panel(qtbot):
    widget=AutoLevelPanel(source=inputs()[0],report=inputs()[1])
    qtbot.addWidget(widget)
    yield widget
    assert widget.shutdown()


def fill(panel):
    panel.set_map(height_map(lambda x,y:.01*x+.02*y))
    for key,value in {'reference_z_mm':'0','max_segment_mm':'.5',
                      'chord_error_mm':'.001','surface_error_mm':'.001'}.items():
        panel.fields[key].setText(value)


def prepare(panel,qtbot):
    fill(panel);panel.prepare()
    qtbot.waitUntil(lambda:not panel.busy,timeout=3000)
    assert panel.result is not None,panel.summary_label.text()
    panel.confirm_checkbox.setChecked(True)
    return panel.result


def test_explicit_blank_inputs_and_confirmation(panel,qtbot,tmp_path):
    assert all(not field.text() for field in panel.fields.values())
    panel.prepare();assert not panel.busy and panel.result is None
    result=prepare(panel,qtbot)
    panel.confirm_checkbox.setChecked(False)
    assert panel.reviewed_binding() is None
    assert not panel.save_button.isEnabled() and not panel.transfer_button.isEnabled()
    panel.confirm_checkbox.setChecked(True)
    path=tmp_path/'derived.nc';panel.save_path(path)
    assert path.read_text(encoding='ascii')==result.prepared_job.source.text
    assert panel.preview_table.rowCount()<=200


def test_load_map_snapshot_invalid_or_incomplete_never_delivers(panel,qtbot,tmp_path):
    path=tmp_path/'map.json';save_probe_map(path,height_map())
    panel.load_map(path);assert panel.map==height_map()
    prepare(panel,qtbot)
    path.write_text('{}',encoding='utf-8');panel.load_map(path)
    assert panel.result is None and not panel.save_button.isEnabled()
    panel.set_map(replace(height_map(),outcome='aborted'))
    panel.prepare();qtbot.waitUntil(lambda:not panel.busy,timeout=3000)
    assert panel.result is None


@pytest.mark.parametrize('changed',['settings','map','source','cancel'])
def test_pending_preparation_cannot_deliver_obsolete_result(panel,qtbot,monkeypatch,changed):
    import mikrocam.ui.autolevel_worker as module
    original=module.prepare_autolevel
    entered,release=Event(),Event()
    def delayed(*args,**kwargs):
        entered.set();assert release.wait(2)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'prepare_autolevel',delayed)
    fill(panel);panel.prepare()
    try:
        qtbot.waitUntil(entered.is_set)
        if changed=='settings':panel.fields['reference_z_mm'].setText('.01')
        elif changed=='map':panel.set_map(height_map(lambda x,y:.03*x))
        elif changed=='source':panel.set_source(*reviewed(HEADER+'G1Z-.2F60\nG1X1'))
        else:panel.cancel()
        expected_message=panel.summary_label.text()
    finally:release.set()
    qtbot.waitUntil(lambda:not panel.busy,timeout=3000)
    assert panel.result is None and panel.reviewed_binding() is None
    if changed=='cancel':assert panel.summary_label.text()=='Compensation cancelled.'
    else:assert panel.summary_label.text()==expected_message


def test_current_handoff_and_changed_original_binding(panel,qtbot):
    binding=list(inputs());calls=[]
    panel.set_source(*binding,binding_provider=lambda:tuple(binding))
    panel.job_receiver=lambda *args:calls.append(args)
    result=prepare(panel,qtbot);panel.transfer()
    assert calls[0][:2]==(result.prepared_job.source,result.prepared_job.report)
    assert calls[0][2]()==calls[0][:2]
    binding[0]=type(binding[0])('edited.nc',binding[0].text)
    panel.transfer()
    assert len(calls)==1 and panel.result is None
    assert calls[0][2]() is None


def test_real_worker_runs_away_from_gui_and_close_joins(panel,qtbot,monkeypatch):
    import mikrocam.ui.autolevel_worker as module
    original=module.prepare_autolevel;threads=[]
    def observed(*args,**kwargs):
        threads.append(get_ident());return original(*args,**kwargs)
    monkeypatch.setattr(module,'prepare_autolevel',observed)
    prepare(panel,qtbot)
    assert threads and threads[0]!=get_ident()
    assert panel.shutdown() and not panel.busy and panel.reviewed_binding() is None



def test_preflight_open_invalidation_and_shutdown(qtbot):
    from mikrocam.ui.preflight_panel import PreflightPanel
    parent=PreflightPanel();qtbot.addWidget(parent)
    source,report=inputs();parent.load_source(source);parent.report=report;parent._sync_controls()
    assert parent.autolevel_button.isEnabled()
    widget=parent.open_autolevel();assert widget is parent._autolevel_panel
    qtbot.addWidget(widget);prepare(widget,qtbot)
    parent.load_source(type(source)('edited.nc',source.text))
    assert widget.result is None and widget.reviewed_binding() is None
    assert parent.shutdown() and not widget._alive


def test_nonmodal_file_choice_keeps_parent_controls_accessible(panel,qtbot):
    prepare(panel,qtbot);panel.choose_save()
    assert len(panel._dialogs)==1
    dialog=panel._dialogs[0]
    assert dialog.windowModality()==QtCore.Qt.WindowModality.NonModal
    assert panel.isEnabled()
    dialog.close()


def test_shutdown_retains_unjoined_worker_and_rejects_late_result(panel,qtbot,monkeypatch):
    import mikrocam.ui.autolevel_worker as module
    original=module.prepare_autolevel;entered,release=Event(),Event()
    def delayed(*args,**kwargs):
        entered.set();assert release.wait(4)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'prepare_autolevel',delayed)
    fill(panel);panel.prepare();qtbot.waitUntil(entered.is_set)
    try:
        assert not panel.shutdown(timeout=0)
        assert panel.busy and panel.reviewed_binding() is None
    finally:release.set()
    qtbot.waitUntil(lambda:not panel.busy,timeout=3000)
    assert panel.result is None and panel.shutdown()



def test_source_and_map_input_paths_are_protected(qtbot,tmp_path):
    from mikrocam.ui.preflight_panel import PreflightPanel
    parent=PreflightPanel();qtbot.addWidget(parent)
    source,report=inputs();path=tmp_path/'original.nc';path.write_text(source.text,encoding='ascii')
    parent.load_file(path)
    parent.report=type(report)(**{**report.__dict__,'source_name':parent.source.name,
                                   'source_sha256':parent.source.sha256})
    parent._sync_controls();widget=parent.open_autolevel();qtbot.addWidget(widget)
    map_path=tmp_path/'map.json';save_probe_map(map_path,height_map(lambda x,y:.01*x+.02*y))
    before_source,before_map=path.read_bytes(),map_path.read_bytes()
    widget.load_map(map_path)
    for key,value in {'reference_z_mm':'0','max_segment_mm':'.5','chord_error_mm':'.001',
                      'surface_error_mm':'.001'}.items():widget.fields[key].setText(value)
    widget.prepare();qtbot.waitUntil(lambda:not widget.busy,timeout=3000)
    assert widget.result is not None,widget.summary_label.text()
    widget.confirm_checkbox.setChecked(True)
    widget.save_path(path);assert path.read_bytes()==before_source
    widget.save_path(map_path);assert map_path.read_bytes()==before_map
    assert 'input' in widget.summary_label.text().lower()
    assert parent.shutdown()
