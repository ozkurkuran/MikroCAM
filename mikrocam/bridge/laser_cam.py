"""GUI-thread Gerber snapshots and owned ordinary-Geometry laser previews."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import TYPE_CHECKING

from shapely import LineString

from .gerber import gerber_region

if TYPE_CHECKING:
    from mikrocam.core.laser_paths import CopperFeatures, LaserPlan


def _records(obj: object) -> tuple:
    """Detach positive aperture records; clear-only records are not exposure features."""
    tools = getattr(obj, 'tools', None)
    if tools is None:
        return ()
    if not isinstance(tools, Mapping):
        raise ValueError('Gerber aperture metadata must be a mapping')
    result = []
    for aperture in tools.values():
        if not isinstance(aperture, Mapping):
            raise ValueError('Gerber aperture metadata must contain mappings')
        entries = aperture.get('geometry', ())
        if entries is None:
            entries = ()
        if not isinstance(entries, (list, tuple)):
            raise ValueError('Gerber aperture geometry records must be a sequence')
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError('Gerber aperture geometry record must be a mapping')
            if entry.get('solid') is not None:
                result.append((aperture.get('type'), deepcopy(entry['solid']),
                               deepcopy(entry.get('follow'))))
    return tuple(result)


class LaserCamHost:
    """Concrete adapter for Evo collection/publication, never manufacturing hardware."""

    def __init__(self, app: object) -> None:
        self.app = app

    def _gui_thread(self) -> None:
        if not self.app.main_thread.isCurrentThread():
            raise RuntimeError('Laser CAM host access requires the GUI thread')

    def source_names(self) -> tuple[str, ...]:
        self._gui_thread()
        return tuple(obj.obj_options['name'] for obj in self.app.collection.get_list()
                     if getattr(obj, 'kind', None) == 'gerber')

    def active_name(self) -> str | None:
        self._gui_thread()
        obj = self.app.collection.get_active()
        return obj.obj_options['name'] if getattr(obj, 'kind', None) == 'gerber' else None

    def _gerber(self, name: str) -> object:
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Select a named Gerber object')
        obj = self.app.collection.get_by_name(name)
        if getattr(obj, 'kind', None) != 'gerber':
            raise ValueError(f'Gerber object is unavailable: {name}')
        return obj

    def snapshot(self, source_name: str, outline_name: str | None = None) -> CopperFeatures:
        from mikrocam.core.laser_features import features_from_gerber

        self._gui_thread()
        source = self._gerber(source_name)
        copper = gerber_region(source)
        outline, outline_units = None, None
        if outline_name is not None:
            board = self._gerber(outline_name)
            try:
                outline = deepcopy(board.follow_geometry)
                outline_units = board.units
            except AttributeError as error:
                raise ValueError('Outline requires explicit follow_geometry and units') from error
        return features_from_gerber(copper, _records(source), source.units,
                                    outline=outline, outline_units=outline_units)

    def _restore_selection(self, selected: tuple) -> None:
        collection = self.app.collection
        collection.set_all_inactive()
        for obj in selected:
            name = obj.obj_options['name']
            if collection.get_by_name(name) is obj:
                collection.set_active(name)

    def publish_preview(self, plan: LaserPlan) -> str:
        from mikrocam.core.laser_paths import LaserPlan

        self._gui_thread()
        if not isinstance(plan, LaserPlan):
            raise ValueError('A validated laser plan is required for preview')
        units = self.app.options.get('units')
        if not isinstance(units, str) or units.upper() not in {'MM', 'IN'}:
            raise ValueError('Preview requires explicit MM or IN host units')
        geometry = [LineString(path.points) for path in plan.paths]

        def initialize(obj, app):
            # new_object performs the sole conversion to host units after initialization.
            obj.units = 'MM'
            obj.multigeo = False
            obj.solid_geometry = list(geometry)
            obj.tools = {1: {'tooldia': 0.0, 'data': dict(obj.obj_options),
                             'solid_geometry': list(geometry)}}

        collection = self.app.collection
        selected = tuple(collection.get_selected())
        previous = getattr(self.app, '_mikrocam_laser_cam_preview', None)
        try:
            obj = self.app.app_obj.new_object('geometry', f'{plan.job.name}_laser_preview',
                                              initialize, plot=True, autoselected=False)
            if getattr(obj, 'kind', None) != 'geometry':
                raise ValueError('Geometry preview publication failed')
            # Legacy unit conversion rebuilds tool metadata; retain its converted paths.
            obj.tools[1]['solid_geometry'] = list(obj.solid_geometry)
            self.app._mikrocam_laser_cam_preview = obj
            if previous is not None:
                name = previous.obj_options['name']
                if collection.get_by_name(name) is previous:
                    collection.delete_by_name(name, select_project=False)
            return obj.obj_options['name']
        finally:
            self._restore_selection(selected)

    def parent_widget(self) -> object:
        self._gui_thread()
        return self.app.ui

    def existing_panel(self) -> object | None:
        self._gui_thread()
        return getattr(self.app, '_mikrocam_laser_cam_panel', None)

    def remember_panel(self, panel: object | None) -> None:
        self._gui_thread()
        self.app._mikrocam_laser_cam_panel = panel
