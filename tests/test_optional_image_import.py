"""Image backends are optional; exercise the real tool without a Qt application."""
import builtins
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.fixture
def load_tool():
    def load(optional=None):
        optional = optional or {}
        gui_names = (
            'VerticalScrollArea FCLabel FCButton FCFrame GLay FCComboBox FCCheckBox '
            'FCComboBox2 RadioSet FCDoubleSpinner FCSpinner FCMessageBox'
        ).split()
        stubs = {
            'PyQt6': SimpleNamespace(QtWidgets=SimpleNamespace(), QtGui=SimpleNamespace()),
            'appTool': SimpleNamespace(AppTool=object),
            'appGUI.GUIElements': SimpleNamespace(**dict.fromkeys(gui_names, object)),
            'appTranslation': SimpleNamespace(apply_language=lambda language: None),
            'appParsers.ParseSVG': SimpleNamespace(**dict.fromkeys(
                ['svgparselength', 'svgparse_viewbox', 'getsvggeo', 'getsvgtext'], None)),
            'defaults': SimpleNamespace(AppDefaults=object),
        }
        imported = []

        def tool_import(name, globals=None, locals=None, fromlist=(), level=0):
            imported.append(name)
            if name.split('.')[0] in {'rasterio', 'svgtrace', 'pyppeteer', 'playwright'}:
                if name in optional:
                    return optional[name]
                raise ModuleNotFoundError(f'No module named {name!r}', name=name)
            if name in stubs:
                return stubs[name]
            return builtins.__import__(name, globals, locals, fromlist, level)

        namespace = {'__builtins__': dict(vars(builtins), __import__=tool_import), '_': lambda s: s}
        source = Path(__file__).resolve().parents[1] / 'appPlugins' / 'ToolImage.py'
        exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), namespace)
        tool = namespace['ToolImage'].__new__(namespace['ToolImage'])
        messages, jobs = [], []
        tool.app = SimpleNamespace(
            inform=SimpleNamespace(emit=messages.append),
            worker_task=SimpleNamespace(emit=jobs.append),
            log=SimpleNamespace(debug=lambda *args: None, error=lambda *args: None),
            get_last_folder=lambda: '',
        )
        return tool, namespace, imported, messages, jobs
    return load


def configure_trace(tool, namespace, filename):
    values = {
        'import_mode_radio': 'trace', 'presets_combo': 'detailed', 'control_radio': 'presets',
        'tf_type_obj_combo': 'Geometry', 'dpi_entry': 96, 'image_type': 'color',
        'min_area_entry': 0.3, 'mask_bw_entry': 250, 'mask_r_entry': 251,
        'mask_g_entry': 252, 'mask_b_entry': 253,
    }
    tool.ui = SimpleNamespace(**{
        key: SimpleNamespace(get_value=lambda value=value: value) for key, value in values.items()
    })
    namespace['QtWidgets'].QFileDialog = SimpleNamespace(
        getOpenFileName=lambda **kwargs: (str(filename), ''))


def test_tool_import_does_not_load_optional_backends(load_tool):
    _, _, imported, _, _ = load_tool()
    assert not any(name.split('.')[0] in {'rasterio', 'svgtrace', 'pyppeteer', 'playwright'}
                   for name in imported)


def test_missing_raster_reports_install_command(load_tool):
    tool, _, _, messages, _ = load_tool()
    assert tool.import_image_handler('unused.png') == 'fail'
    assert 'requirements-image.txt' in messages[-1]
    assert messages[-1].startswith('[ERROR_NOTCL]')


def test_missing_trace_reports_install_command(load_tool, tmp_path):
    tool, namespace, _, messages, jobs = load_tool()
    configure_trace(tool, namespace, tmp_path / 'image.png')
    tool.on_file_importimage()
    assert 'requirements-image.txt' in messages[-1]
    assert not jobs


def test_trace_browser_failure_reports_correct_browser_install(load_tool, tmp_path):
    def trace(*args, **kwargs):
        raise RuntimeError("BrowserType.launch: Executable doesn't exist")
    tool, namespace, _, messages, jobs = load_tool({'svgtrace': SimpleNamespace(trace=trace)})
    configure_trace(tool, namespace, tmp_path / 'image.png')
    tool.on_file_importimage()
    assert 'python -m playwright install chromium' in messages[-1]
    assert not jobs


def test_trace_preserves_options_and_schedules_import(load_tool, tmp_path):
    calls = []
    def trace(filename, **kwargs):
        calls.append((filename, kwargs))
        return '<svg/>'
    tool, namespace, imported, messages, jobs = load_tool({'svgtrace': SimpleNamespace(trace=trace)})
    filename = tmp_path / 'image.png'
    configure_trace(tool, namespace, filename)
    tool.on_file_importimage()
    assert calls == [(str(filename), {'blackAndWhite': False, 'mode': 'detailed'})]
    assert jobs[0]['params'] == [str(filename), 'trace', 'Geometry', 96, 'color',
                                 [250, 251, 252, 253], '<svg/>', 0.3]
    assert not messages
    assert not any(name.startswith(('pyppeteer', 'rasterio')) for name in imported)


def test_cancelled_trace_does_not_load_backend(load_tool):
    tool, namespace, imported, messages, jobs = load_tool()
    configure_trace(tool, namespace, '')
    tool.on_file_importimage()
    assert messages == ['Cancelled.']
    assert not jobs
    assert 'svgtrace' not in imported


def test_monochrome_trace_can_import_without_worker(load_tool, tmp_path):
    calls, imports = [], []
    def trace(filename, **kwargs):
        calls.append(kwargs)
        return '<svg/>'
    tool, namespace, _, messages, jobs = load_tool({'svgtrace': SimpleNamespace(trace=trace)})
    filename = tmp_path / 'image.png'
    configure_trace(tool, namespace, filename)
    tool.ui.image_type.get_value = lambda: 'black'
    tool.import_image = lambda *args: imports.append(args)
    tool.on_file_importimage(threaded=False)
    assert calls == [{'blackAndWhite': True, 'mode': 'detailed'}]
    assert imports[0][0] == str(filename)
    assert imports[0][6] == '<svg/>'
    assert not jobs
    assert not messages


def test_optional_dependency_message_uses_translation(load_tool):
    tool, namespace, _, messages, _ = load_tool()
    namespace['_'] = lambda text: 'translated:' + text
    tool.import_image_handler('unused.png')
    assert messages[-1].startswith('[ERROR_NOTCL] translated:')


def test_raster_preserves_mask_scaling_and_flip(load_tool):
    pixels = np.array([[0, 255]], dtype=np.uint8)
    class Raster:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, band):
            if band > 1:
                raise IndexError(band)
            return pixels
    calls = []
    def shapes(total, mask):
        calls.append((total, mask))
        return [({'type': 'Polygon', 'coordinates': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]}, 0)]
    tool, _, imported, messages, _ = load_tool({
        'rasterio': SimpleNamespace(open=lambda filename: Raster()),
        'rasterio.features': SimpleNamespace(shapes=shapes),
    })
    geometry = tool.import_image_handler('image.png', dpi=25.4, mask=[128] * 4)
    np.testing.assert_array_equal(calls[0][1], [[True, False]])
    assert geometry[0].bounds == (0, -1, 1, 0)
    assert geometry[0].area == 1
    assert not messages
    assert 'svgtrace' not in imported
