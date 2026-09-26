"""Concrete minimal headless host plumbing for unchanged reference applications."""
from copy import deepcopy
import importlib
import importlib.util
import inspect
import logging
import os
from pathlib import Path
import sys
from types import SimpleNamespace


class Config(dict):
    """Factory host configuration with the usage-report service expected by legacy code."""
    def report_usage(self, *args) -> None:
        pass


def sandbox_settings(directory: Path) -> None:
    """Install the established named-QSettings sandbox before application imports."""
    os.environ['APPDATA'] = str(directory)
    path = Path(__file__).resolve().parents[1] / 'qt_settings_sandbox.py'
    spec = importlib.util.spec_from_file_location('_capture_settings_sandbox', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.install_settings_sandbox(directory)


def verify_module_paths(modules: list, source: Path) -> list[Path]:
    """Refuse an application module imported from a different checkout or fallback."""
    source = source.resolve(strict=True)
    paths = []
    for module in modules:
        filename = getattr(module, '__file__', None)
        if not filename:
            raise ValueError('Application module has no verifiable source file')
        path = Path(filename).resolve(strict=True)
        if not path.is_relative_to(source):
            raise ValueError(f'Application module is outside declared source: {path.name}')
        paths.append(path)
    return paths


def load_engine(source: Path, parameters: dict) -> SimpleNamespace:
    """Load real source classes and its real default preprocessor, without a GUI."""
    sys.path.insert(0, str(source.resolve(strict=True)))
    names = ('defaults', 'camlib', 'appParsers.ParseGerber', 'appParsers.ParseExcellon',
             'preprocessors.default', 'appPreProcessor')
    modules = [importlib.import_module(name) for name in names]
    verify_module_paths(modules, source)
    defaults, camlib, gerber, excellon, preprocessor, _ = modules
    cls = getattr(defaults, 'AppDefaults', getattr(defaults, 'FlatCAMDefaults', None))
    cfg = Config(deepcopy(cls.factory_defaults))
    cfg.update(parameters['parser']['gerber'])
    cnc = parameters['cnc']
    cfg.update(tools_mill_optimization_type='N', geometry_optimization_type='N',
               cncjob_coords_type=cnc['coords_type'], cncjob_coords_decimals=cnc['coords_decimals'],
               cncjob_fr_decimals=cnc['fr_decimals'], cncjob_steps_per_circle=cnc['steps_per_circle'],
               tools_mill_endxy=cnc['endxy'], geometry_endxy=cnc['endxy'],
               tools_mill_toolchangexy='0,0', geometry_toolchangexy='0,0',
               tools_drill_toolchangexy='0,0', excellon_toolchangexy='0,0')
    app = SimpleNamespace(options=cfg, defaults=cfg, decimals=cnc['coords_decimals'],
                          abort_flag=False, app_units='MM', use_3d_engine=True, is_legacy=False,
                          log=logging.getLogger('reference'), preprocessors={'default': preprocessor.default()},
                          inform=SimpleNamespace(emit=lambda *args: None),
                          proc_container=SimpleNamespace(update_view_text=lambda *args: None),
                          plotcanvas=SimpleNamespace(new_shape_collection=lambda **kwargs: None),
                          exc_areas=SimpleNamespace(exclusion_areas_storage=[],
                              travel_coordinates=lambda **kwargs: [[None, kwargs['end_point']]]))
    return SimpleNamespace(app=app, Gerber=gerber.Gerber, Excellon=excellon.Excellon,
                           Geometry=camlib.Geometry, CNCjob=camlib.CNCjob)


def construct(engine: SimpleNamespace, cls: type, **kwargs) -> object:
    """Match the actual class's constructor signature, including legacy class app."""
    cls.app = engine.app
    return cls(app=engine.app, **kwargs) if 'app' in inspect.signature(cls).parameters else cls(**kwargs)
