# Validation — device-aware laser recipes

Base: `921002357d5a5a6eef1c8b0f4811253874e88563`; branch `036-laser-device-recipes`.
Windows desktop; CPython 3.13 pinned MikroCAM main environment. No new dependency
or legacy code change. Native LightBurn and physical process acceptance remain separate.

## Test-first and integration

- Initial new tests: 54 FAIL / 1 PASS (legacy record already worked).
- First implementation: 203 PASS / 40 FAIL from a missing import in an adapted
  legacy test. Import corrected; failure log retained.
- New schema test first failed for absent v2 artifacts; old schema kept unchanged.
- Focused core/codec/export/editor: 244 PASS / 1.42 s.
- Related laser/visual/architecture: 717 PASS / 1 FAIL / 206.38 s. The old UI error
  assertion was updated to require the new explicit device selection.
- Additional integration: 167 PASS / 1 FAIL / 154.39 s. A test incorrectly expected
  preview deletion instead of existing revision invalidation; corrected to assert
  save/PNG/project buttons and current-job rejection. Final UI: 39 PASS / 4.86 s.
- `pip check`: PASS. New/shared editor module/function size and public hints: PASS.

Evidence retained in ignored `.venv/laser-devices-*.log` on the main checkout.
Full regression checkpoint: 894 file hashes,
`7aa1f34c064d09358bac5ee770f65cc1a621cd618180de049dc6008f54748969`.
Full source manifest/log/JUnit: `laser-devices-source.json`, `laser-devices-full.log`
and `laser-devices-full.xml`. Fresh full regression: **5813 PASS, 310 subtests PASS,
3 skipped, 11 existing warnings, 418.12 s, exit 0**. Checkpoint hashes remained
identical after the run. Import boundaries and legacy growth checks passed.

## Actual desktop

`tests/smoke_laser_devices.py`: exit 0 PASS in a private settings/data sandbox.
Actual application menu/dock, MOPA M7 100 W and diode recipes, prepare, JSON
save/reopen, PNG ZIP v2, actual host Geometry carrier, FlatPrj save/reopen with
identical profile and mask hash. The shared native harness also completed legacy
CAM, OpenGL rendering and normal worker/process shutdown.

Markers: `LASER_DEVICE_MOPA_JSON_PNG_PROJECT_ROUNDTRIP_OK`,
`LASER_DEVICE_DIODE_JSON_PNG_PROJECT_ROUNDTRIP_OK`,
`VISUAL_FOCUSED_NATIVE_RENDER_SHUTDOWN_OK`.
Log: main `.venv/laser-devices-native.log`. Worktree screenshots
`.venv/mopa-device-native.png` and `.venv/diode-device-native.png` visually inspected;
narrow dock uses the table's horizontal scrollbar for additional fields.

## Delivery and external acceptance

Local source acceptance: PASS. PR/final-head CI/main merge: pending delivery.
Unknown M7 manufacturer ranges were not supplied or inferred. No laser emission,
motion, firmware setting or physical production was tested. Native `.lbrn2`
requires an actual Image fixture and LightBurn version/device/Open→Save→Preview;
the existing export gate remains closed. Binary installer provenance/packaging
acceptance remains open under its separate roadmap.
