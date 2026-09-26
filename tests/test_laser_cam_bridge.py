"""Desktop boundary snapshots and previews preserve host geometry and ownership."""

from copy import deepcopy
from threading import Thread
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QMainWindow
from shapely import LineString, Point, box
from shapely.affinity import scale

from mikrocam.bridge.laser_cam import LaserCamHost
from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion


def gerber(name, geometry=None, units='MM', **extra):
    return SimpleNamespace(kind='gerber', obj_options={'name': name}, units=units,
                           solid_geometry=box(0, 0, 10, 10) if geometry is None else geometry,
                           tools={}, follow_geometry=[], source_file='%MOIN*%', **extra)


class Collection:
    def __init__(self, objects):
        self.objects = list(objects)
        self.selected = self.objects[:1]
        self.deleted = []

    def get_list(self):
        return list(self.objects)

    def get_by_name(self, name):
        return next((obj for obj in self.objects if obj.obj_options['name'] == name), None)

    def get_active(self):
        return self.selected[0] if self.selected else None

    def get_selected(self):
        return list(self.selected)

    def set_all_inactive(self):
        self.selected.clear()

    def set_active(self, name):
        obj = self.get_by_name(name)
        if obj not in self.selected:
            self.selected.append(obj)

    def delete_by_name(self, name, select_project=True):
        obj = self.get_by_name(name)
        self.objects.remove(obj)
        self.selected = [item for item in self.selected if item is not obj]
        self.deleted.append((obj, select_project))


class App:
    def __init__(self, parent, objects, units='MM'):
        self.ui = parent
        self.main_thread = QThread.currentThread()
        self.collection = Collection(objects)
        self.options = {'units': units}
        self.app_obj = SimpleNamespace(new_object=self.new_object)
        self.initializations = []
        self.failure = None

    def new_object(self, kind, name, initialize, plot=True, autoselected=True):
        if self.failure:
            self.collection.set_all_inactive()
            return self.failure
        obj = SimpleNamespace(kind=kind, obj_options={'name': name}, units=self.options['units'],
                              tools={}, solid_geometry=[], multigeo=False)
        initialize(obj, self)
        self.initializations.append((obj.units, deepcopy(obj.solid_geometry), plot, autoselected))
        if obj.units.upper() != self.options['units'].upper():
            assert obj.units == 'MM' and self.options['units'] == 'IN'
            obj.solid_geometry = [scale(line, xfact=1 / 25.4, yfact=1 / 25.4, origin=(0, 0))
                                  for line in obj.solid_geometry]
            obj.units = 'IN'
            # Match GeometryObject.convert_units: it rebuilds tool metadata without geometry.
            obj.tools = {uid: {key: value for key, value in tool.items() if key != 'solid_geometry'}
                         for uid, tool in obj.tools.items()}
        base, index = name, 0
        while self.collection.get_by_name(name) is not None:
            index += 1
            name = f'{base}_{index}'
        obj.obj_options['name'] = name
        self.collection.objects.append(obj)
        # Actual on_object_created clears selection even with autoselected=False, plot=True.
        self.collection.set_all_inactive()
        return obj


@pytest.fixture
def app(qtbot):
    parent = QMainWindow()
    qtbot.addWidget(parent)
    return App(parent, [gerber('copper'), gerber('outline')])


@pytest.fixture
def plan():
    from mikrocam.core.laser_paths import LaserPath, LaserPlan, PlanOptions

    recipe = LaserRecipe('synthetic', (LaserPass('pass', 10, 20, 30, 40),))
    job = LaserJob('copper', PlanarRegion.from_geometry(box(0, 0, 100, 100)), recipe)
    return LaserPlan(job, PlanOptions(), (LaserPath(((25.4, 50.8), (76.2, 50.8)), 'contour'),
                                        LaserPath(((0, 0), (0, 25.4)), 'contour')))


def test_source_names_and_active_name_include_only_gerbers(app):
    app.collection.objects.append(SimpleNamespace(kind='geometry', obj_options={'name': 'user geometry'}))
    host = LaserCamHost(app)
    assert host.source_names() == ('copper', 'outline')
    assert host.active_name() == 'copper'
    app.collection.selected = [app.collection.objects[-1]]
    assert host.active_name() is None


def test_panel_helpers_keep_one_panel_on_the_app(app):
    host = LaserCamHost(app)
    assert host.parent_widget() is app.ui
    assert host.existing_panel() is None
    panel = object()
    host.remember_panel(panel)
    assert LaserCamHost(app).existing_panel() is panel


def test_snapshot_uses_current_units_and_clips_semantic_positives(app):
    copper = app.collection.objects[0]
    copper.tools = {10: {'type': 'C', 'geometry': [
        {'solid': box(0, 0, 5, 5), 'follow': Point(2, 2)},
        {'solid': box(4, 0, 15, 2), 'follow': LineString([(4, 1), (15, 1)])},
        {'clear': box(0, 0, 1, 1), 'follow': Point(0, 0)},
    ]}}
    before = deepcopy(vars(copper))
    result = LaserCamHost(app).snapshot('copper')
    assert result.copper.to_geometry().equals(copper.solid_geometry)
    assert result.pads.to_geometry().area == pytest.approx(25)
    assert result.traces.to_geometry().area == pytest.approx(12)
    assert result.board is None
    assert vars(copper) == before


def test_snapshot_normalizes_inch_metadata_once(app):
    copper = app.collection.objects[0]
    copper.units = 'IN'
    copper.solid_geometry = box(0, 0, 1, 1)
    copper.tools = {10: {'type': 'C', 'geometry': [
        {'solid': box(0, 0, 0.5, 0.5), 'follow': Point(0.25, 0.25)}]}}
    result = LaserCamHost(app).snapshot('copper')
    assert result.copper.to_geometry().bounds == pytest.approx((0, 0, 25.4, 25.4))
    assert result.pads.to_geometry().area == pytest.approx(12.7 ** 2)


def test_outline_is_explicit_follow_geometry_with_its_own_units(app):
    source, outline = app.collection.objects
    source.follow_geometry = [LineString([(0, 0), (100, 0)])]
    outline.units = 'IN'
    outline.solid_geometry = box(0, 0, 99, 99)
    outline.follow_geometry = [LineString([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])]
    host = LaserCamHost(app)
    assert host.snapshot('copper').board is None
    result = host.snapshot('copper', 'outline')
    assert result.board.to_geometry().area == pytest.approx(25.4 ** 2)


def test_snapshot_copies_metadata_containers_before_delegating(app, monkeypatch):
    import mikrocam.core.laser_features as features

    copper = app.collection.objects[0]
    solid = [box(0, 0, 1, 1)]
    copper.tools = {10: {'type': 'REG', 'geometry': [{'solid': solid, 'follow': None}]}}
    calls = []

    def capture(region, records, units, outline=None, outline_units=None):
        calls.append((region, records, units, outline, outline_units))
        return region

    monkeypatch.setattr(features, 'features_from_gerber', capture)
    LaserCamHost(app).snapshot('copper')
    assert len(calls) == 1 and calls[0][2] == 'MM'
    assert calls[0][1][0][0] == 'REG'
    assert calls[0][1][0][1] is not solid
    solid.clear()
    assert len(calls[0][1][0][1]) == 1


@pytest.mark.parametrize('name', [None, '', 'missing', 'user geometry'])
def test_snapshot_rejects_missing_or_wrong_source(app, name):
    app.collection.objects.append(SimpleNamespace(kind='geometry', obj_options={'name': 'user geometry'}))
    with pytest.raises(ValueError):
        LaserCamHost(app).snapshot(name)


@pytest.mark.parametrize('tools', ['bad', {10: 'bad'}, {10: {'geometry': 'bad'}},
                                   {10: {'geometry': [None]}}])
def test_malformed_aperture_records_are_not_silently_guessed(app, tools):
    app.collection.objects[0].tools = tools
    with pytest.raises(ValueError, match='metadata|record'):
        LaserCamHost(app).snapshot('copper')


def test_preview_uses_existing_geometry_and_keeps_selection_and_source(app, plan):
    app.collection.selected = list(app.collection.objects)
    selected = tuple(app.collection.selected)
    source_wkb = selected[0].solid_geometry.wkb
    name = LaserCamHost(app).publish_preview(plan)
    obj = app.collection.get_by_name(name)
    assert obj.kind == 'geometry' and obj.units == 'MM' and not obj.multigeo
    assert len(obj.solid_geometry) == 2
    assert list(obj.solid_geometry[0].coords) == list(plan.paths[0].points)
    assert obj.tools[1]['solid_geometry'] == obj.solid_geometry
    assert obj.tools[1]['tooldia'] == 0
    assert tuple(app.collection.selected) == selected
    assert selected[0].solid_geometry.wkb == source_wkb
    assert app.initializations[0][2:] == (True, False)


def test_preview_mm_to_inch_conversion_is_host_owned_and_applied_once(app, plan):
    app.options['units'] = 'IN'
    name = LaserCamHost(app).publish_preview(plan)
    obj = app.collection.get_by_name(name)
    assert app.initializations[0][0] == 'MM'
    assert list(app.initializations[0][1][0].coords) == list(plan.paths[0].points)
    assert obj.units == 'IN'
    assert obj.solid_geometry[0].coords[0] == pytest.approx((1, 2))
    assert obj.solid_geometry[0].coords[1] == pytest.approx((3, 2))
    assert obj.tools[1]['solid_geometry'] == obj.solid_geometry


def test_replacement_deletes_only_owned_object_reference(app, plan):
    host = LaserCamHost(app)
    first = app.collection.get_by_name(host.publish_preview(plan))
    app.collection.objects.remove(first)
    unrelated = SimpleNamespace(kind='geometry', obj_options=dict(first.obj_options))
    app.collection.objects.append(unrelated)
    second = app.collection.get_by_name(host.publish_preview(plan))
    assert unrelated in app.collection.objects and not app.collection.deleted
    third = app.collection.get_by_name(host.publish_preview(plan))
    assert second not in app.collection.objects and third in app.collection.objects
    assert app.collection.deleted == [(second, False)]


def test_failed_publication_keeps_prior_owned_preview_and_selection(app, plan):
    host = LaserCamHost(app)
    previous = app.collection.get_by_name(host.publish_preview(plan))
    selected = tuple(app.collection.selected)
    app.failure = 'fail'
    with pytest.raises(ValueError, match='preview|Geometry'):
        host.publish_preview(plan)
    assert previous in app.collection.objects and not app.collection.deleted
    assert tuple(app.collection.selected) == selected


@pytest.mark.parametrize('units', [None, 'CM', '', 1])
def test_unsupported_host_units_fail_before_publication(app, plan, units):
    app.options['units'] = units
    with pytest.raises(ValueError, match='units'):
        LaserCamHost(app).publish_preview(plan)
    assert not app.initializations


def test_invalid_plan_publishes_nothing(app):
    with pytest.raises(ValueError, match='plan'):
        LaserCamHost(app).publish_preview(None)
    assert not app.initializations


def test_host_access_from_worker_thread_is_rejected(app):
    host = LaserCamHost(app)
    errors = []

    def worker():
        try:
            host.source_names()
        except RuntimeError as error:
            errors.append(str(error))

    thread = Thread(target=worker)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive() and errors and 'GUI thread' in errors[0]
