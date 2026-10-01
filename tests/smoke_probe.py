"""Desktop analytic-plane acquisition and offline evidence; never physical hardware."""

from pathlib import Path


def _fill(dialog, nx=3, ny=2):
    values = dict(
        x_min=0,
        x_max=2,
        nx=nx,
        y_min=0,
        y_max=1,
        ny=ny,
        safe_z=5,
        min_z=-1,
        probe_feed=50,
        travel_feed=100,
        timeout=30,
    )
    for axis in "xyz":
        values["machine_min_" + axis] = -10
        values["machine_max_" + axis] = 10
    for key, value in values.items():
        dialog.fields[key].setText(str(value))


def _connect(panel, fake, qapp, errors, pump_until):
    from mikrocam.machine.controller import MachineController

    panel.controller_factory = lambda port: MachineController(fake)
    panel.connect_machine()
    pump_until(
        qapp,
        lambda: panel.last_snapshot.probe.can_start,
        errors,
        "probe fresh Fake admission",
    )
    panel.open_probe_grid()
    dialog = panel._probe_dialog
    assert dialog is not None and dialog.isVisible()
    return dialog


def _complete_evidence(app, dialog, fake, root):
    result = dialog.viewer.map
    assert result.complete and result.origin == "simulated"
    expected = (0.0, 0.01, 0.02, 0.02, 0.03, 0.04)
    assert all(
        abs(actual - target) < 1e-9
        for actual, target in zip(result.heights_mm, expected)
    )
    assert fake.machine_position == (2.0, 1.0, 5.0)
    path = Path(root) / ".venv/probe-map-smoke.json"
    writes = tuple(fake.writes)
    dialog.viewer.save_path(path)
    dialog.viewer.load_path(path)
    assert dialog.viewer.map == result and tuple(fake.writes) == writes
    screenshot = Path(root) / ".venv/probe-grid-smoke.png"
    assert dialog.grab().save(str(screenshot))
    print("PROBE_GRID_SIX_ANALYTIC_OFFLINE_MAP_OK", screenshot, flush=True)
    return path


def probe_journey(app, qapp, errors, pump_until, root):
    from PyQt6 import QtCore
    from mikrocam.bridge.serial_transport import PortInfo
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.machine.probe_models import ProbePhase
    from mikrocam.ui.machine_panel import MachinePanel

    previous = getattr(app, "_mikrocam_machine_panel", None)
    fake = FakeGRBL(machine_position=(0.0, 0.0, 5.0))
    respond = fake._probe.respond
    def decelerated(data):
        respond(data)
        if b'G38.2' in data:
            x, y, z = fake.machine_position
            fake.machine_position = (x, y, z - 0.02)
    fake._probe.respond = decelerated
    panel = MachinePanel(
        app.ui,
        controller_factory=lambda port: MachineController(fake),
        ports_provider=lambda: (PortInfo("FAKE", "Probe smoke simulator"),),
    )
    app.ui.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, panel)
    panel.show()
    try:
        dialog = _connect(panel, fake, qapp, errors, pump_until)
        assert all(not edit.text() for edit in dialog.fields.values())
        assert not fake._probe.fault and not dialog.start_button.isEnabled()
        _fill(dialog)
        dialog.review_button.click()
        assert dialog.plan.grid.count == 6 and dialog.viewer.map is None
        dialog.start_button.click()
        assert not dialog.close()
        pump_until(
            qapp,
            lambda: panel.last_snapshot.probe.phase is ProbePhase.COMPLETE,
            errors,
            "six-point analytic height map",
            timeout=25,
        )
        path = _complete_evidence(app, dialog, fake, root)
        panel.disconnect_machine()
        pump_until(qapp, lambda: not panel.busy, errors, "probe complete session join")
        fake = FakeGRBL(machine_position=(0.0, 0.0, 5.0))
        dialog = _connect(panel, fake, qapp, errors, pump_until)
        _fill(dialog, nx=4, ny=2)
        dialog.review_button.click()
        dialog.start_button.click()
        pump_until(
            qapp,
            lambda: panel.last_snapshot.probe.completed >= 2,
            errors,
            "probe partial measurements",
        )
        assert not dialog.close()
        assert not dialog.viewer.save_button.isEnabled()
        assert not dialog.viewer.load_button.isEnabled()
        assert dialog.stop_button.isEnabled()
        dialog.stop_button.click()
        pump_until(
            qapp,
            lambda: panel.last_snapshot.probe.phase is ProbePhase.ABORTED,
            errors,
            "probe priority stop",
        )
        partial = panel.last_snapshot.probe.map
        assert 2 <= partial.completed < 8 and not partial.complete
        assert panel.last_snapshot.probe.stop_unverified
        dialog.viewer.save_path(path)
        dialog.viewer.load_path(path)
        assert dialog.viewer.map == partial
        print("PROBE_PARTIAL_STOP_UNVERIFIED_MAP_OK", partial.completed, flush=True)
    finally:
        panel.disconnect_machine()
        pump_until(qapp, lambda: not panel.busy, errors, "probe owned worker shutdown")
        assert not fake.is_open
        if panel._probe_dialog is not None:
            assert panel._probe_dialog.close()
        assert panel.close()
        panel.deleteLater()
        qapp.processEvents()
        assert getattr(app, "_mikrocam_machine_panel", None) is previous
