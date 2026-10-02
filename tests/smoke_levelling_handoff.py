"""Actual desktop Levelling→Machine journey; forbid physical serial constructors."""
from unittest.mock import patch


def levelling_handoff_journey(app, qapp, errors, pump_until, root):
    with patch("serial.serial_for_url", side_effect=AssertionError("Legacy port opened")), \
            patch("serial.Serial", side_effect=AssertionError("Physical port opened")):
        tool = app.levelling_tool
        tool.run(toggle=True)
        for _ in range(2):
            tool.ui.al_controller_combo.set_value("GRBL")
            qapp.processEvents()
            assert tool.ui.grbl_frame.isHidden() and not tool.ui.grbl_frame.isEnabled()
            assert tool.ui.machine_handoff.isVisible()
            tool.on_grbl_connect()
            tool.set_tool_ui()
        for offline in ("MACH3", "MACH4", "LinuxCNC"):
            tool.ui.al_controller_combo.set_value(offline)
            qapp.processEvents()
            assert not tool.ui.import_heights_button.isHidden()
            assert not tool.ui.h_gcode_button.isHidden()
            assert tool.ui.machine_handoff.isHidden()
        tool.ui.al_controller_combo.set_value("GRBL")
        qapp.processEvents()
        tool.ui.machine_handoff_button.click()
        panel = app._mikrocam_machine_panel
        assert panel.isVisible() and not panel.busy and panel._worker is None
        tool.ui.machine_handoff_button.click()
        assert app._mikrocam_machine_panel is panel
        app.ui.plugin_scroll_area.ensureWidgetVisible(tool.ui.machine_handoff)
        qapp.processEvents()
        assert not errors
        screenshot = root / ".venv/levelling-machine-handoff.png"
        assert app.ui.grab().save(str(screenshot))
        card = root / ".venv/levelling-handoff-card.png"
        assert tool.ui.machine_handoff.grab().save(str(card))
        print("LEVELLING_GRBL_NO_PORT_MACHINE_HANDOFF_OK", screenshot, flush=True)
