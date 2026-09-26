# Implementation Plan: Evo Python 3.13 baseline

**Branch**: `001-evo-py313-baseline` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

## Summary

Pin a reproducible Windows environment, make Evo imports safe for test runners, adapt the
eight legacy compatibility behaviors and the real CAM smoke journey, then fix only failures
reproduced by those checks. Preserve Beta_1.0 features, tests, identity and project format.

## Technical Context

- Language: standard CPython 3.13.13 x64; `.python-version` is authoritative.
- Dependencies: PyQt6, VisPy, NumPy 2, Shapely 2 and Evo's existing geometry/import stack.
  Start from versions already exercised by the 8.994 port; resolve and pin the complete
  Windows dependency closure after installation. No new runtime architecture dependency.
- Storage: existing Evo project/defaults files; temporary directories for tests.
- Testing: pytest + pytest-qt, existing unittest tests collected by pytest; real desktop smoke.
- Platform/type: Windows 11 x64 desktop CAM. Linux is secondary and not certified here.
- Performance: no new throughput target; three clean startup/shutdown cycles, two clean
  dependency installations and complete CAM round-trip are the acceptance measurements.
- Scope: three stories; no branding, new manufacturing behavior, CI or core skeleton.
- Known setup failure: pyppeteer and current svgtrace/playwright resolve incompatible pyee
  generations, pulling a greenlet without a Python 3.13 wheel. Image tracing must be optional
  and use its actual current browser backend; core startup cannot depend on it.

## Constitution Check

Evaluated before research and again after design. Final sizes/results go in validation.md.

| Gate | Result | Evidence/design |
| --- | --- | --- |
| I: new feature logic in mikrocam, correct direction | Yes | No new feature logic; compatibility fixes remain with their legacy owner. |
| II: only legacy fixes, net growth <=50 | Yes, budgeted | Target appMain/flatcam/camlib and changed legacy modules; measure at completion, justify any overrun below. |
| III/VII: no unnecessary abstraction; dependencies justified/pinned/licensed | Yes | Existing runtime libraries; pytest (MIT) and pytest-qt (MIT) add test tooling only; notices recorded. |
| IV: existing units/parameters/formats preserved | Yes | No new persistent format or transform. |
| V: hardware-free, tests before fixes, headless checks | No for desktop smoke only | Unit suite offscreen; real rendering deliberately requires desktop/OpenGL per spec. |
| VI: machine/laser safeguards where applicable | Yes | No hardware/emission changes; tests never drive hardware. |
| VII: traceable imports and clean room | Yes | Only MIT 8.994 tests/targeted fixes; original copyright retained and THIRD_PARTY_CHANGES updated. |
| Feature size <=3 stories / <=40 tasks | Yes | 3 stories, 20 tasks. |

Import-boundary/ratchet automation belongs to foundation-guardrails; this slice measures
changed legacy lines directly and does not claim those future checks exist.

## Project Structure

```text
.python-version, requirements*.txt, run-flatcam.ps1, pytest.ini
appMain.py, flatcam.py                 # argument/startup compatibility only
appPlugins/ToolImage.py               # optional raster/trace loading
appParsers/, descartes/, camlib.py     # only reproduced compatibility fixes
tests/test_runtime_compatibility.py
tests/test_optional_image_import.py
tests/conftest.py, tests/qt_settings_sandbox.py, tests/test_settings_isolation.py
tests/test_geometry_edge_cases.py
tests/smoke_app.py
tests/reference/                      # fixed fixtures/expected geometry if parser fixes needed
THIRD_PARTY_CHANGES.md, THIRD_PARTY_LICENSES/
specs/001-evo-py313-baseline/
  plan.md, research.md, data-model.md, quickstart.md, contracts/runtime.md,
  tasks.md, validation.md
```

## Complexity Tracking

| Exception | Why needed | Simpler alternative rejected |
| --- | --- | --- |
| Desktop/OpenGL smoke alongside offscreen unit tests | Must prove actual canvas render and GUI round-trip | Offscreen mocks cannot establish render success. |

Any actual growth-budget or size exception discovered during implementation is recorded
here with the measured amount and concrete reason before completion.

Final source measurement against upstream-evo-beta1-baseline: 112 added / 169 removed,
**-57 net legacy lines** across appMain.py, flatcam.py, ParseSVG.py, ToolImage.py and
descartes/patch.py. No growth exception is needed. New modules are at most 232 lines;
new/changed functions are at most 80 lines (largest new test journey: 64).

Dependency resolution is complete: 43 runtime pins, 5 additional development pins and
10 optional image pins. No new mandatory runtime library was introduced. Test tooling
licenses and optional trace notices are in THIRD_PARTY_LICENSES/; complete release notices
remain the branding-and-notices slice.
