# Data model

LaserDeviceProfile: kind in diode/co2/ruida_rf_co2/fiber/mopa/uv; name text;
frequency_range_khz, pulse_width_range_ns, pwm_frequency_range_khz optional finite
positive ordered pairs; pulse_widths_ns immutable unique positive tuple.

LaserPass: existing name/power_percent/speed_mm_s/frequency_khz/pulse_width_ns;
new min_power_percent and pwm_frequency_khz optional. None means inapplicable or
not overriding optional settings, never a fabricated numeric default.

LaserRecipe: name, ordered unique passes, optional device. None explicitly
represents unspecified legacy schema1. Profiled schema2 has device and complete
seven-field passes with null for inapplicable fields. Unit conversion is absent.

Schema1 wire output stays identical for legacy values. Profiled nested job,
visual and geometry transfer envelopes use2; readers reject mismatched nested
versions, unknown keys, bool numbers, nonfinite values and unsupported profiles.
