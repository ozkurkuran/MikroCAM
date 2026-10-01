import pytest
from mikrocam.core.probe_map import ProbeGrid, ProbeMap
from mikrocam.ui.probe_view import ProbeMapView


def sample(outcome="complete"):
    return ProbeMap(
        ProbeGrid((0.0, 1.0), (0.0, 2.0)),
        (1.0, 2.0, 3.0, 4.0) if outcome == "complete" else (1.0, None, None, None),
        (10.0, 20.0, 0.0),
        outcome,
        "simulated",
    )


def test_table_axes_heights_origin_and_missing(qtbot):
    view = ProbeMapView()
    qtbot.addWidget(view)
    view.set_map(sample("aborted"))
    assert view.table.rowCount() == 2 and view.table.columnCount() == 2
    assert view.table.item(0, 0).text() == "1.000000"
    assert view.table.item(1, 1).text() == "—"
    assert (
        "simulated" in view.status_label.text()
        and "aborted" in view.status_label.text()
    )
    assert "X" in view.table.horizontalHeaderItem(1).text()
    assert "Y" in view.table.verticalHeaderItem(1).text()


def test_offline_save_load_and_failed_load_retains_map(qtbot, tmp_path):
    view = ProbeMapView()
    qtbot.addWidget(view)
    original = sample("aborted")
    view.set_map(original)
    path = tmp_path / "map.json"
    view.save_path(path)
    view.set_map(sample())
    view.load_path(path)
    assert view.map == original
    path.write_text("{}")
    with pytest.raises(ValueError):
        view.load_path(path)
    assert view.map == original
