"""Thin device-family selection and explicit optional manufacturer-bound inputs."""
import builtins
from contextlib import ExitStack
import gettext
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.laser_device import DEVICE_KINDS, LaserDeviceProfile

_ = getattr(builtins, '_', gettext.gettext)
LABELS = ('Diyot / G-code', 'CO₂', 'Ruida RF CO₂ — PWM', 'Fiber galvo', 'MOPA galvo', 'UV galvo')


def _pair(text: str, field: str) -> tuple[float, float] | None:
    if not text.strip(): return None
    try:
        parts = tuple(float(value.strip()) for value in text.split(':'))
        if len(parts) != 2: raise ValueError()
        return parts
    except ValueError as error: raise ValueError(f'{field}: min:max biçiminde iki sayı girin') from error


class LaserDeviceEditor(QtWidgets.QWidget):
    """Keep manufacturer data separate from per-pass values and firmware settings."""
    changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._legacy = False
        layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        form = QtWidgets.QFormLayout()
        self.kind = QtWidgets.QComboBox(); self.kind.addItem(_('Cihaz türü seçin…'), None)
        for kind, label in zip(DEVICE_KINDS, LABELS): self.kind.addItem(_(label), kind)
        self.name = QtWidgets.QLineEdit(); self.name.setPlaceholderText(_('Örn. MOPA M7 100 W'))
        form.addRow(_('Lazer türü'), self.kind); form.addRow(_('Model / profil adı'), self.name)
        layout.addLayout(form)
        hint = QtWidgets.QLabel(_('Yalnız seçilen lazer türünün alanları kaydedilir. Sayısal ayarları siz girersiniz.'))
        hint.setWordWrap(True); layout.addWidget(hint)
        self.limits = QtWidgets.QGroupBox(_('Üretici sınırlarını kullan (isteğe bağlı)'))
        self.limits.setCheckable(True); self.limits.setChecked(False)
        outer = QtWidgets.QVBoxLayout(self.limits); self.bounds = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.bounds)
        self.frequency = QtWidgets.QLineEdit(); self.pulse_range = QtWidgets.QLineEdit()
        self.pulses = QtWidgets.QLineEdit(); self.pwm = QtWidgets.QLineEdit()
        for label, widget in ((_('Frekans kHz — min:max'), self.frequency),
                              (_('Atım süresi ns — min:max'), self.pulse_range),
                              (_('İzin verilen ns — virgülle'), self.pulses),
                              (_('PWM kHz — min:max'), self.pwm)):
            self.form.addRow(label, widget); widget.textChanged.connect(self.changed)
        outer.addWidget(self.bounds); self.bounds.setVisible(False); layout.addWidget(self.limits)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self.name.textChanged.connect(self.changed)
        self.limits.toggled.connect(self.bounds.setVisible); self.limits.toggled.connect(self.changed)
        self._sync_bounds()

    @property
    def active_fields(self) -> frozenset[str]:
        """Fields shown by the parent, independent of incomplete bound drafts."""
        kind = self.kind.currentData()
        if kind is None: return frozenset(('power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns'))
        return LaserDeviceProfile(kind, kind).fields

    def _kind_changed(self) -> None:
        self._legacy = False; self.kind.setItemText(0, _('Cihaz türü seçin…'))
        self._sync_bounds(); self.changed.emit()

    def _sync_bounds(self) -> None:
        fields = self.active_fields
        for widget, field in ((self.frequency, 'frequency_khz'), (self.pulse_range, 'pulse_width_ns'),
                              (self.pulses, 'pulse_width_ns'), (self.pwm, 'pwm_frequency_khz')):
            visible = self.kind.currentData() is not None and field in fields
            widget.setVisible(visible); self.form.labelForField(widget).setVisible(visible)
        self.limits.setVisible(self.kind.currentData() is not None and bool(
            fields & {'frequency_khz', 'pulse_width_ns', 'pwm_frequency_khz'}))

    def get_profile(self) -> LaserDeviceProfile | None:
        """Validate typed manufacturer metadata; never infer a laser from old numbers."""
        kind = self.kind.currentData()
        if kind is None:
            if self._legacy: return None
            raise ValueError(_('Cihaz türü seçin.'))
        values = {}
        if self.limits.isChecked():
            for field, parameter, widget in (('frequency_range_khz', 'frequency_khz', self.frequency),
                                            ('pulse_width_range_ns', 'pulse_width_ns', self.pulse_range),
                                            ('pwm_frequency_range_khz', 'pwm_frequency_khz', self.pwm)):
                if parameter in self.active_fields: values[field] = _pair(widget.text(), field)
            if 'pulse_width_ns' in self.active_fields and self.pulses.text().strip():
                try: values['pulse_widths_ns'] = tuple(float(value.strip()) for value in self.pulses.text().split(','))
                except ValueError as error: raise ValueError(_('Atım seçeneklerini virgülle ayrılmış sayılar olarak girin.')) from error
        return LaserDeviceProfile(kind, self.name.text().strip() or self.kind.currentText(), **values)

    def set_profile(self, profile: LaserDeviceProfile | None) -> None:
        """Load exact metadata, keeping unspecified legacy recipes visibly separate."""
        with ExitStack() as stack:
            for widget in (self.kind, self.name, self.limits, self.frequency, self.pulse_range, self.pulses, self.pwm):
                stack.enter_context(QtCore.QSignalBlocker(widget))
            self._legacy = profile is None
            self.kind.setItemText(0, _('Eski reçete — cihaz türü belirtilmemiş') if self._legacy else _('Cihaz türü seçin…'))
            self.kind.setCurrentIndex(0 if profile is None else self.kind.findData(profile.kind))
            self.name.setText('' if profile is None else profile.name)
            for field, widget in (('frequency_range_khz', self.frequency), ('pulse_width_range_ns', self.pulse_range),
                                  ('pwm_frequency_range_khz', self.pwm)):
                pair = getattr(profile, field) if profile else None
                widget.setText('' if pair is None else ':'.join(repr(value) for value in pair))
            self.pulses.setText(', '.join(repr(value) for value in profile.pulse_widths_ns) if profile else '')
            self.limits.setChecked(bool(profile and (profile.frequency_range_khz or profile.pulse_width_range_ns or
                                                    profile.pulse_widths_ns or profile.pwm_frequency_range_khz)))
        self.bounds.setVisible(self.limits.isChecked()); self._sync_bounds(); self.changed.emit()
