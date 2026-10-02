"""Host adapter for the visual dock and existing Geometry payload carriers."""
from copy import deepcopy
from mikrocam.core.interlace_job import VisualInterlaceJob
from .visual_project import PAYLOAD_KEY


class VisualHost:
    def __init__(self, app: object) -> None: self.app = app

    def _gui_thread(self) -> None:
        if not self.app.main_thread.isCurrentThread(): raise RuntimeError('Host access requires GUI thread')

    def parent_widget(self) -> object:
        self._gui_thread(); return self.app.ui

    def existing_panel(self) -> object | None:
        self._gui_thread(); return getattr(self.app, '_mikrocam_visual_panel', None)

    def remember_panel(self, panel: object) -> None:
        self._gui_thread(); self.app._mikrocam_visual_panel = panel

    def source_names(self) -> list[str]:
        self._gui_thread()
        return [o.obj_options['name'] for o in self.app.collection.get_list()
                if o.obj_options.get(PAYLOAD_KEY) is not None]

    def publish_payload(self, job: VisualInterlaceJob, payload: dict) -> None:
        self._gui_thread()
        # Encoding has already completed in the worker, never in this Qt callback.
        name = job.source.name + '_visual_interlace'
        def initialize(owner: object, _app: object) -> None:
            owner.units = 'MM'
            owner.solid_geometry = None
            owner.multigeo = False
            owner.tools = {}
            owner.obj_options['plot'] = False
            owner.obj_options[PAYLOAD_KEY] = payload
        result = self.app.app_obj.new_object('geometry', name, initialize, plot=False)
        if result == 'fail': raise ValueError('Cannot create visual project carrier')

    def project_payload(self, name: str) -> dict:
        self._gui_thread()
        owner = self.app.collection.get_by_name(name)
        if owner is None or owner.obj_options.get(PAYLOAD_KEY) is None:
            raise ValueError('Visual project carrier not found')
        return deepcopy(owner.obj_options[PAYLOAD_KEY])

    def geometry_source_names(self) -> list[str]:
        self._gui_thread()
        return [o.obj_options['name'] for o in self.app.collection.get_list()
                if o.kind in ('gerber', 'geometry') and PAYLOAD_KEY not in o.obj_options]

    def geometry_source_snapshot(self, name: str) -> tuple[object, str]:
        self._gui_thread()
        owner = self.app.collection.get_by_name(name)
        if owner is None or owner.kind not in ('gerber', 'geometry') or PAYLOAD_KEY in owner.obj_options:
            raise ValueError('Choose an existing copper/polygon geometry source')
        def freeze(value: object, depth: int = 0) -> object:
            if depth > 64: raise ValueError('Geometry nesting exceeds limit')
            if isinstance(value, (list, tuple)): return tuple(freeze(item, depth + 1) for item in value)
            return value  # Shapely2 geometries are immutable values, not live host objects.
        return freeze(owner.solid_geometry), owner.units
