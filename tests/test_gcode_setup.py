"""Explicit blank setup inputs; no hardware state or silent numeric defaults."""
import pytest
from PyQt6 import QtWidgets

from mikrocam.core.gcode_models import PreflightSetup
from mikrocam.core.placement import Placement
from mikrocam.ui.preflight_setup import PreflightSetupWidget


VALUES = {'initial_x':'1','initial_y':'2','initial_z':'3',
          'min_x':'-10','min_y':'-20','min_z':'-5',
          'max_x':'100','max_y':'200','max_z':'50',
          'safe_z':'2','z_offset':'1','origin_x':'4','origin_y':'5',
          'translation_x':'6','translation_y':'7','rotation':'30'}
KEYS = tuple(VALUES) + ('rapid_x','rapid_y','rapid_z')


@pytest.fixture
def widget(qtbot):
    widget=PreflightSetupWidget()
    qtbot.addWidget(widget)
    return widget


def fill(widget):
    for key,value in VALUES.items():
        widget.fields[key].setText(value)


def test_all_required_and_optional_numeric_fields_start_empty(widget):
    assert set(widget.fields) == set(KEYS)
    assert all(isinstance(edit,QtWidgets.QLineEdit) and edit.text()=='' for edit in widget.fields.values())
    assert not widget.mirror_checkbox.isChecked()
    with pytest.raises(ValueError,match='[Ii]nitial'):
        widget.value()


def test_value_uses_existing_placement_and_explicit_setup_values(widget):
    fill(widget)
    widget.mirror_checkbox.setChecked(True)
    value=widget.value()
    assert isinstance(value,PreflightSetup)
    assert value.initial_position_mm == (1.,2.,3.)
    assert value.machine_min_mm == (-10.,-20.,-5.)
    assert value.machine_max_mm == (100.,200.,50.)
    assert value.safe_z_mm == 2. and value.z_offset_mm == 1.
    assert value.placement == Placement(origin=(4.,5.),translation=(6.,7.),rotation_deg=30.,mirror_x=True)
    assert value.rapid_rates_mm_min is None


@pytest.mark.parametrize('key',tuple(VALUES))
def test_each_missing_required_field_never_falls_back_to_zero(widget,key):
    fill(widget)
    widget.fields[key].clear()
    with pytest.raises(ValueError,match='[Ee]nter|[Rr]equired|[Mm]issing'):
        widget.value()


@pytest.mark.parametrize('key,value', [('initial_x','text'), ('initial_y','NaN'), ('safe_z','inf'),
                                     ('z_offset','1e99'), ('max_z','-10'), ('safe_z','51'),
                                     ('rotation','nan'), ('origin_x','1000000001')])
def test_invalid_setup_is_reported_instead_of_clamped_or_defaulted(widget,key,value):
    fill(widget)
    widget.fields[key].setText(value)
    with pytest.raises(ValueError):
        widget.value()


def test_optional_rapid_rates_require_all_three_positive_values(widget):
    fill(widget)
    widget.fields['rapid_x'].setText('100')
    with pytest.raises(ValueError,match='[Rr]apid'):
        widget.value()
    widget.fields['rapid_y'].setText('200')
    widget.fields['rapid_z'].setText('300')
    assert widget.value().rapid_rates_mm_min == (100.,200.,300.)
    for text in ('0','-1','inf','text'):
        widget.fields['rapid_z'].setText(text)
        with pytest.raises(ValueError):
            widget.value()


def test_every_edit_and_mirror_change_emits_invalidation_signal(widget):
    changes=[]
    widget.changed.connect(lambda: changes.append(True))
    for key in KEYS:
        widget.fields[key].setText('1')
    widget.mirror_checkbox.setChecked(True)
    assert len(changes) == len(KEYS)+1


def test_values_are_detached_from_later_widget_edits(widget):
    fill(widget)
    before=widget.value()
    widget.fields['initial_x'].setText('9')
    widget.fields['translation_x'].setText('0')
    assert before.initial_position_mm == (1.,2.,3.)
    assert before.placement.translation == (6.,7.)
    assert widget.value().initial_position_mm == (9.,2.,3.)


def test_human_readable_number_error_names_the_field(widget):
    fill(widget)
    widget.fields['initial_x'].setText('bad')
    with pytest.raises(ValueError,match='Initial X.*number'):
        widget.value()


def test_placement_validation_error_uses_visible_axis_label(widget):
    fill(widget)
    widget.fields['origin_x'].setText('nan')
    with pytest.raises(ValueError,match='Origin X.*finite'):
        widget.value()
