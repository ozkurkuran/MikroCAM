# Research and clarified scope

User device: MOPA M7 100 W. Üretici adı bilinmediğinden JPT varsayılmadı;
tek generic MOPA profili, explicit model etiketi ve optional manufacturer bounds.

Primary references checked 2026-10-03:
- [Galvo settings](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/GalvoSpecificCutSettings/):
  frequency kHz; MOPA/UV Q-pulse ns; UV power via frequency/pulse.
- [Shared settings](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/SharedSettings/):
  power/speed and conditional min-power; device family matters.
- [Ruida RF PWM](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/LineMode/#override-pwm-frequency):
  PWM frequency override is not universal CO₂ capability.
- [Galvo device source settings](https://docs.lightburnsoftware.com/latest/Reference/DeviceSettings/GalvoPorts/):
  device enable-PWM/source/ports are distinct from per-layer job values.

Alternatives rejected: compulsory fake frequency/ns for diode; infer MOPA from
schema1; assign an unverified M7 numeric range; treat PWM and pulse frequency as
synonyms; save a metadata field and report native LightBurn application.

The earlier read-only search found only vector `.lbrn2` samples and no LightBurn
executable/Image fixture. User has not yet supplied version/path. G02 remains open.
