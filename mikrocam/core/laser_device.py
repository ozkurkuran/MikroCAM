"""Explicit laser-family capabilities and user-supplied manufacturer limits."""
from dataclasses import dataclass
from .placement import _finite_real

DEVICE_KINDS = ('diode', 'co2', 'ruida_rf_co2', 'fiber', 'mopa', 'uv')
PARAMETER_FIELDS = frozenset(('power_percent', 'speed_mm_s', 'frequency_khz',
                             'pulse_width_ns', 'min_power_percent', 'pwm_frequency_khz'))


@dataclass(frozen=True)
class LaserDeviceProfile:
    """A capability family, not a calibrated controller or machine configuration."""
    kind: str
    name: str
    frequency_range_khz: tuple[float, float] | None = None
    pulse_width_range_ns: tuple[float, float] | None = None
    pulse_widths_ns: tuple[float, ...] = ()
    pwm_frequency_range_khz: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in DEVICE_KINDS:
            raise ValueError('device.kind is unsupported')
        if type(self.name) is not str or not self.name.strip() or len(self.name) > 256:
            raise ValueError('device.name requires nonempty text of at most 256 characters')
        for field, parameter in (('frequency_range_khz', 'frequency_khz'),
                                 ('pulse_width_range_ns', 'pulse_width_ns'),
                                 ('pwm_frequency_range_khz', 'pwm_frequency_khz')):
            pair = getattr(self, field)
            if pair is None: continue
            if parameter not in self.fields: raise ValueError(f'{field} is unsupported for {self.kind}')
            if type(pair) is not tuple or len(pair) != 2: raise ValueError(f'{field} requires a pair')
            low, high = (_finite_real(value, field) for value in pair)
            if not 0 < low <= high: raise ValueError(f'{field} requires positive ordered bounds')
            object.__setattr__(self, field, (low, high))
        widths = self.pulse_widths_ns
        if type(widths) is not tuple or len(widths) > 1000: raise ValueError('pulse_widths_ns requires a bounded tuple')
        if widths and 'pulse_width_ns' not in self.fields: raise ValueError('pulse_widths_ns is unsupported')
        widths = tuple(_finite_real(value, 'pulse_widths_ns') for value in widths)
        if any(value <= 0 for value in widths) or len(set(widths)) != len(widths):
            raise ValueError('pulse_widths_ns requires unique positive values')
        if self.pulse_width_range_ns and any(not self.pulse_width_range_ns[0] <= value <= self.pulse_width_range_ns[1]
                                             for value in widths):
            raise ValueError('pulse_widths_ns must lie within pulse_width_range_ns')
        object.__setattr__(self, 'pulse_widths_ns', widths)

    @property
    def fields(self) -> frozenset[str]:
        """Supported job parameters, with pulse repetition distinct from PWM."""
        fields = {'speed_mm_s'}
        if self.kind != 'uv': fields.update(('power_percent', 'min_power_percent'))
        if self.kind in ('fiber', 'mopa', 'uv'): fields.add('frequency_khz')
        if self.kind in ('mopa', 'uv'): fields.add('pulse_width_ns')
        if self.kind == 'ruida_rf_co2': fields.add('pwm_frequency_khz')
        return frozenset(fields)

    @property
    def required_fields(self) -> frozenset[str]:
        """Values that must be explicit for every pass of this family."""
        return self.fields - {'min_power_percent', 'pwm_frequency_khz'}

    def validate_pass(self, value: object) -> None:
        """Reject missing, unsupported and out-of-range values without substitution."""
        for field in PARAMETER_FIELDS:
            parameter = getattr(value, field)
            if parameter is None and field in self.required_fields:
                raise ValueError(f'{field} is required for {self.kind}')
            if parameter is not None and field not in self.fields:
                raise ValueError(f'{field} is unsupported for {self.kind}')
        for field, bounds in (('frequency_khz', self.frequency_range_khz),
                              ('pulse_width_ns', self.pulse_width_range_ns),
                              ('pwm_frequency_khz', self.pwm_frequency_range_khz)):
            parameter = getattr(value, field)
            if bounds and parameter is not None and not bounds[0] <= parameter <= bounds[1]:
                raise ValueError(f'{field} is outside device bounds {bounds}')
        if self.pulse_widths_ns and value.pulse_width_ns not in self.pulse_widths_ns:
            raise ValueError('pulse_width_ns is not a supported device pulse width')
