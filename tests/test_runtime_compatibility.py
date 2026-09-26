"""Behavioral regressions adapted from the MIT FlatCAM 8.994 Python 3.13 port."""

import json
import os
from pathlib import Path
import subprocess
import sys

import ezdxf
import numpy as np
import pytest
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon
from svg.path import parse_path

from appParsers.ParseDXF import getdxfgeo
from appParsers.ParseSVG import path2shapely
from descartes.patch import PolygonPath

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = json.loads((Path(__file__).parent / 'reference/svg_paths.json').read_text())


def test_multipart_iteration_preserves_components():
    from camlib import Geometry
    parts = [Polygon([(0, 0), (1, 0), (1, 1)]), Polygon([(3, 0), (4, 0), (4, 1)])]
    geometry = Geometry.__new__(Geometry)
    assert geometry.flatten(MultiPolygon(parts)) == parts
    assert geometry.flatten(parts) == parts
    assert geometry.flatten(parts[0]) == [parts[0]]


def test_flatten_nested_multipart_geometry():
    from camlib import Geometry
    geometry = Geometry.__new__(Geometry)
    lines = [LineString([(0, 0), (1, 1)]), LineString([(2, 2), (3, 3)])]
    assert geometry.flatten([MultiLineString(lines)], pathonly=True) == lines


def test_svg_preserves_open_subpaths_and_scale():
    case = REFERENCES['open_subpaths']
    result = path2shapely(parse_path(case['path']), 'geometry', factor=case['factor'])
    assert len(result) == 2
    for actual, expected in zip(result, case['coordinates']):
        assert actual.geom_type == 'LineString'
        np.testing.assert_allclose(actual.coords, expected, atol=1e-9, rtol=0)


def test_svg_preserves_holes_and_disconnected_contours():
    case = REFERENCES['holes_and_contours']
    result = path2shapely(parse_path(case['path']), 'geometry')
    assert sorted(p.area for p in result) == pytest.approx(case['areas'], abs=1e-9)
    assert sum(len(p.interiors) for p in result) == case['holes']


def test_matplotlib_polygon_patch_and_empty_geometry():
    polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(2, 2), (4, 2), (4, 4), (2, 4)]])
    path = PolygonPath(polygon)
    assert path.vertices.shape == (10, 2)
    assert np.isfinite(path.vertices).all()
    assert PolygonPath(Polygon()).vertices.shape == (0, 2)


def test_current_ezdxf_import():
    drawing = ezdxf.new()
    drawing.modelspace().add_line((1, 2), (3, 4))
    shapes = getdxfgeo(drawing)
    assert len(shapes) == 1
    assert list(shapes[0].coords) == [(1, 2), (3, 4)]


def test_qt6_double_slider_and_text_editor(qtbot):
    from appGUI.GUIElements import FCSliderWithDoubleSpinner, FCTextAreaExtended
    widget = FCSliderWithDoubleSpinner(min=0, max=10.5, step=0.1)
    qtbot.addWidget(widget)
    widget.slider.set_value(1.25)
    assert widget.slider.value() == pytest.approx(1.25)
    assert widget.spinner.value() == pytest.approx(1.25)
    editor = FCTextAreaExtended()
    qtbot.addWidget(editor)
    editor.setPlainText('G00 X0 Y0\nG01 X10 Y10')
    editor.show()
    assert editor.toPlainText().startswith('G00')


def test_cli_arguments_are_explicit():
    from appMain import App
    original = (App.cmd_line_headless, App.cmd_line_shellfile, App.cmd_line_shellvar, App.args)
    try:
        App.configure_command_line(['--headless=1', '--shellfile=example.tcl', '--shellvar=42', 'board.gbr'])
        assert App.cmd_line_headless == 1
        assert App.cmd_line_shellfile == 'example.tcl'
        assert App.cmd_line_shellvar == '42'
        assert App.args == ['board.gbr']
        App.configure_command_line([])
        assert App.cmd_line_headless is None
        assert App.cmd_line_shellfile == ''
        assert App.args == []
    finally:
        App.cmd_line_headless, App.cmd_line_shellfile, App.cmd_line_shellvar, App.args = original


def test_import_does_not_consume_test_runner_arguments(tmp_path):
    env = dict(os.environ, APPDATA=str(tmp_path), QT_QPA_PLATFORM='offscreen')
    result = subprocess.run(
        [sys.executable, '-c', 'import sys; sys.argv=["pytest", "-q"]; import appMain; print("IMPORT_OK")'],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'IMPORT_OK' in result.stdout
