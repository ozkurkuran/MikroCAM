"""Queued plots must survive deletion and must never read widgets in workers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import logging
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, box


class ForbiddenWidgets:
    def __getattr__(self, name):
        raise RuntimeError(f'Worker accessed QWidget: {name}')


def plot_object(kind):
    from appObjects.AppObjectTemplate import FlatCAMObj
    from appObjects.ExcellonObject import ExcellonObject
    from appObjects.GerberObject import GerberObject
    rendered, clears = [], []
    app = SimpleNamespace(use_3d_engine=True, log=logging.getLogger('plot-lifetime'))
    geometry = box(0, 0, 1, 1)
    obj = SimpleNamespace(app=app, deleted=False, ui=ForbiddenWidgets(),
                          obj_options=dict(plot=True, solid=True, multicolored=False, follow=False),
                          outline_color='#000000ff', fill_color='#ffffffff',
                          solid_geometry=[geometry], follow_geometry=[], shape_indexes_dict={},
                          tools={1: {'solid_geometry': [geometry]}},
                          _app_option=lambda key: True,
                          shapes=SimpleNamespace(redraw=lambda: None, clear=lambda **kwargs: None),
                          clear=lambda: clears.append(True))
    def add_batch(batch, **kwargs):
        rendered.extend((item['shape'], kwargs['visible']) for item in batch)
        return list(range(len(batch)))
    obj.add_shapes_batch = add_batch
    method = GerberObject.plot if kind == 'gerber' else ExcellonObject.plot
    obj.plot = lambda **kwargs: method(obj, **kwargs)
    obj.delete = lambda: FlatCAMObj.delete(obj)
    return obj, rendered, clears


@pytest.mark.parametrize('kind', ['gerber', 'excellon'])
def test_queued_plot_deleted_before_worker_has_no_widget_access(kind):
    from appHandlers.appPlotManager import AppPlotManager
    obj, rendered, clears = plot_object(kind)
    pending = []
    manager = SimpleNamespace(log=obj.app.log, collection=SimpleNamespace(update_view=lambda: None),
                              worker_task=SimpleNamespace(emit=pending.append),
                              proc_container=SimpleNamespace(new=lambda text: nullcontext()))
    AppPlotManager.enable_plots(manager, [obj])
    assert len(pending) == 1
    obj.delete()
    with ThreadPoolExecutor(max_workers=1) as worker:
        worker.submit(pending[0]['fcn'], *pending[0]['params']).result(timeout=5)
    assert obj.deleted and not rendered and not clears


@pytest.mark.parametrize('kind', ['gerber', 'excellon'])
def test_live_plot_uses_stored_options_and_preserves_explicit_hidden_state(kind):
    obj, rendered, _ = plot_object(kind)
    with ThreadPoolExecutor(max_workers=1) as worker:
        worker.submit(obj.plot, visible=False).result(timeout=5)
    assert len(rendered) == 1 and rendered[0][1] is False


def test_delete_is_safe_when_repeated():
    obj, _, _ = plot_object('excellon')
    obj.delete()
    obj.delete()
    assert obj.deleted


@pytest.mark.parametrize('kind', ['gerber', 'excellon'])
def test_deletion_during_plot_setup_stops_before_rendering(kind):
    obj, rendered, _ = plot_object(kind)
    obj.clear = obj.delete
    obj.plot()
    assert obj.deleted and not rendered


def test_delete_releases_real_qt_widget_through_event_loop(qtbot):
    from PyQt6 import QtCore, QtWidgets, sip
    obj, _, _ = plot_object('gerber')
    widget = QtWidgets.QWidget()
    obj.ui = widget
    obj.form_fields = {'field': widget}
    obj.delete()
    assert obj.deleted and obj.ui is None and not obj.form_fields
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    assert sip.isdeleted(widget)


def test_follow_checkbox_updates_plain_plot_state_before_rendering(qtbot):
    from appGUI.GUIElements import FCCheckBox
    from appObjects.AppObjectTemplate import FlatCAMObj
    from appObjects.GerberObject import GerberObject
    obj, rendered, _ = plot_object('gerber')
    checkbox = FCCheckBox()
    qtbot.addWidget(checkbox)
    checkbox.set_value(True)
    obj.muted_ui = False
    obj.form_fields = {'follow': checkbox}
    obj.read_form_item = lambda key: FlatCAMObj.read_form_item(obj, key)
    obj.follow_geometry = [LineString([(0, 0), (2, 0)])]
    GerberObject.on_follow_cb_click(obj)
    assert obj.obj_options['follow'] is True
    assert rendered[0][0].equals(obj.follow_geometry[0])
