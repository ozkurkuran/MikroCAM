"""Thin fiducial and aligned-job panels: input, core calls and explicit bindings only."""
from pathlib import Path

import pytest
from PyQt6 import QtCore

from mikrocam.core.fiducial import AlignmentPolicy, FiducialPair
from mikrocam.core.fiducial_codec import FiducialSet, dumps_fiducial_set, loads_fiducial_set
from mikrocam.core.gcode_models import PreflightSetup, SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement
from mikrocam.machine.models import ConnectionState, MachineSnapshot, MachineState
from mikrocam.ui.aligned_job_panel import AlignedJobPanel
from mikrocam.ui.fiducial_panel import FiducialPanel
from mikrocam.ui.preflight_panel import PreflightPanel
from mikrocam.ui.preflight_setup import PreflightSetupWidget


TRUTH = Placement(translation=(-100., -50.), rotation_deg=2.)
DESIGN = ((0., 0.), (80., 0.), (80., 60.), (0., 60.))


def snapshot(**changes):
    values = dict(connection=ConnectionState.CONNECTED, state=MachineState.IDLE,
                  machine_position_mm=(-12.5, -7.25, -1.), work_position_mm=(0., 0., 0.),
                  work_offset_mm=(-12.5, -7.25, -1.), report_units='mm', stale=False, last_report_at=1.)
    values.update(changes)
    return MachineSnapshot(**values)


@pytest.fixture
def received():
    return []


@pytest.fixture
def panel(qtbot, received):
    widget = FiducialPanel(alignment_receiver=lambda placement, summary: received.append((placement, summary)),
                           design_points_provider=lambda: (('T1 drill 1', (1., 2.)), ('T1 drill 2', (3., 4.))),
                           snapshot_provider=snapshot)
    qtbot.addWidget(widget)
    return widget


def fill(panel, design=DESIGN, truth=TRUTH):
    panel.set_pairs(tuple(FiducialPair(f'F{i + 1}', point, truth.apply_point(point))
                          for i, point in enumerate(design)))


def test_fit_and_accept_hands_the_placement_to_the_receiver(panel, received):
    fill(panel)
    assert not panel.accept_button.isEnabled()
    panel.fit()
    assert panel.fit_result is not None and panel.fit_result.accepted
    assert panel.method_combo.currentData() == 'affine'
    assert 'F4' in panel.report_label.text()
    assert panel.accept_button.isEnabled()
    panel.accept()
    placement, summary = received[-1]
    assert placement == panel.fit_result.require_placement() and summary


def test_editing_a_cell_invalidates_the_fit(panel):
    fill(panel)
    panel.fit()
    panel.table.item(0, 3).setText('5')
    assert panel.fit_result is None and not panel.accept_button.isEnabled()


def test_rejected_fit_cannot_be_accepted(panel, received):
    fill(panel, truth=Placement(affine=(1.05, 0., 0., 1.05, 0., 0.)))
    panel.fit()
    assert panel.fit_result is not None and not panel.fit_result.accepted
    assert not panel.accept_button.isEnabled()
    panel.accept()
    assert received == []


def test_degenerate_input_shows_error_without_result(panel):
    fill(panel, design=((0., 0.), (50., 0.), (100., 0.)))
    panel.fit()
    assert panel.fit_result is None and panel.report_label.text()


def test_rigid_method_selection_and_policy_values(panel):
    fill(panel, design=DESIGN[:2])
    panel.method_combo.setCurrentIndex(panel.method_combo.findData('similarity'))
    panel.residual_edit.setText('0.1')
    policy = panel.policy()
    assert policy == AlignmentPolicy('similarity', max_residual_mm=.1, max_scale_deviation=.005,
                                     min_separation_mm=10.)
    panel.fit()
    assert panel.fit_result.method == 'similarity'


def test_capture_and_design_candidates_fill_the_selected_row(panel):
    panel.add_row()
    panel.table.setCurrentCell(0, 0)
    panel.capture_machine()
    assert panel.table.item(0, 3).text() == '-12.5' and panel.table.item(0, 4).text() == '-7.25'
    panel.load_candidates()
    assert panel.candidate_combo.count() == 2
    panel.candidate_combo.setCurrentIndex(1)
    panel.use_candidate()
    assert (panel.table.item(0, 1).text(), panel.table.item(0, 2).text()) == ('3', '4')


def test_capture_refuses_stale_machine_state(qtbot, received):
    widget = FiducialPanel(snapshot_provider=lambda: snapshot(stale=True))
    qtbot.addWidget(widget)
    widget.add_row()
    widget.table.setCurrentCell(0, 0)
    widget.capture_machine()
    assert widget.table.item(0, 3).text() == '' and widget.report_label.text()


def test_save_and_load_roundtrip(panel, tmp_path):
    fill(panel)
    path = tmp_path / 'set.json'
    panel.save_to(path)
    value = loads_fiducial_set(path.read_text(encoding='utf-8'))
    assert [pair.name for pair in value.pairs] == ['F1', 'F2', 'F3', 'F4']
    other = FiducialSet('x', AlignmentPolicy('rigid', min_separation_mm=5.),
                        (FiducialPair('A', (0., 0.), None), FiducialPair('B', (20., 0.), (1., 1.), enabled=False)))
    path.write_text(dumps_fiducial_set(other), encoding='utf-8')
    panel.load_from(path)
    assert panel.pairs() == other.pairs
    assert panel.policy() == other.policy
    assert panel.method_combo.currentData() == 'rigid'


def test_setup_widget_alignment_mode_replaces_rigid_fields(qtbot):
    widget = PreflightSetupWidget()
    qtbot.addWidget(widget)
    values = dict(initial_x='0', initial_y='0', initial_z='5', min_x='-200', min_y='-200', min_z='-10',
                  max_x='200', max_y='200', max_z='30', safe_z='2', z_offset='0', origin_x='0',
                  origin_y='0', translation_x='0', translation_y='0', rotation='0')
    for key, text in values.items():
        widget.fields[key].setText(text)
    changes = []
    widget.changed.connect(lambda: changes.append(1))
    affine = Placement(affine=(1., .01, -.01, 1., -60., -40.))
    widget.set_alignment(affine, 'test')
    assert changes and widget.value().placement == affine
    assert not widget.fields['rotation'].isEnabled() and not widget.mirror_checkbox.isEnabled()
    widget.clear_alignment()
    assert widget.value().placement == Placement()
    assert widget.fields['rotation'].isEnabled()


TEXT = 'G21G90G17G94\nG0Z2\nG1Z-.1F60\nG1X10Y0\nG2X10Y10I0J5\nG0Z5\nM2\n'


def aligned_review():
    setup = PreflightSetup((0., 0., 5.), Placement(affine=(.9995, -.0262, .0259, 1.0003, -60., -40.)), 0.,
                           (-200., -200., -10.), (200., 200., 30.), 2., (600., 600., 600.))
    source = SourceSnapshot('board.nc', TEXT)
    return source, analyze_gcode(source, setup)


@pytest.fixture
def aligned(qtbot):
    source, report = aligned_review()
    transfers = []
    widget = AlignedJobPanel(source=source, report=report,
                             job_receiver=lambda *args: transfers.append(args),
                             snapshot_provider=lambda: snapshot(work_offset_mm=(-50., -30., 0.)))
    widget.transfers = transfers
    qtbot.addWidget(widget)
    yield widget
    assert widget.shutdown()


def test_aligned_job_requires_explicit_g54_then_prepares_and_transfers(aligned, qtbot):
    assert aligned.g54_x_edit.text() == '' and not aligned.transfer_button.isEnabled()
    aligned.prepare()
    assert aligned.result is None and aligned.summary_label.text()
    aligned.use_machine_g54()
    assert (aligned.g54_x_edit.text(), aligned.g54_y_edit.text()) == ('-50', '-30')
    aligned.prepare()
    qtbot.waitUntil(lambda: aligned._worker is None, timeout=5000)
    assert aligned.result is not None, aligned.summary_label.text()
    assert aligned.result.g54_offset_mm == (-50., -30., 0.)
    assert aligned.preview_table.rowCount() > 0
    assert aligned.transfer_button.isEnabled() and aligned.dry_run_button.isEnabled()
    aligned.transfer()
    source, report, binding = aligned.transfers[-1]
    assert source is aligned.result.prepared_job.source and binding() == (source, report)
    aligned.g54_x_edit.setText('-49')
    assert aligned.result is None and binding() is None


def test_aligned_job_opens_dry_run_bound_to_the_derived_job(aligned, qtbot):
    aligned.g54_x_edit.setText('-50')
    aligned.g54_y_edit.setText('-30')
    aligned.prepare()
    qtbot.waitUntil(lambda: aligned._worker is None, timeout=5000)
    dry = aligned.open_dry_run()
    assert dry is not None and dry.source is aligned.result.prepared_job.source
    assert dry.shutdown()


def test_preflight_panel_offers_fiducial_and_aligned_actions(qtbot):
    panel = PreflightPanel()
    qtbot.addWidget(panel)
    assert panel.fiducial_button.isEnabled() and not panel.aligned_button.isEnabled()
    fiducial = panel.open_fiducial()
    assert fiducial is not None
    affine = Placement(affine=(1., .01, -.01, 1., -60., -40.))
    fiducial.alignment_receiver(affine, 'x')
    assert panel.setup_widget._alignment == affine
    source, report = aligned_review()
    panel.source, panel.report = source, report
    panel._sync_controls()
    assert panel.aligned_button.isEnabled()
    assert panel.shutdown()
