# Implementation Plan: Branding and notices

**Branch**: `003-branding-and-notices` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

## Summary

Define identity in `mikrocam/core/identity.py` and small UI presentation helpers in
`mikrocam/ui/identity.py`. Wire existing title/About/property/shell surfaces to those helpers.
Keep App.version and storage namespaces untouched. Disable Evo product update entry points
with thin host wiring. Preserve standalone upstream updater code/tests. Collect exact-version
dependency licenses with hashes and add integrity/completeness checks.

## Technical Context

- Language/platform: pinned standard CPython 3.13 x64, Windows 11 desktop.
- Dependencies: existing pins only; stdlib metadata/hash tools to gather and check notices.
- Storage: no user-data format change; dependency inventory schema_version 1 in THIRD_PARTY_LICENSES/inventory.json.
- Testing: pytest/pytest-qt offscreen, isolated core import, original full suite, GUI/CAM smoke.
- Scope: 3 stories, 17 tasks; no installer, upstream merge, artwork redesign or new updater.
- Performance: unchanged runtime CAM path; at most small strings and existing UI construction.
- Product metadata: pyproject version becomes dynamic and points to the identity constant, avoiding a second version literal.
- License evidence: exact installed wheel metadata and upstream tagged sources where wheels omit notices;
  include bundled binary and vendored notices rather than only top-level license labels.

## Constitution Check

Pre-design and post-design:

| Gate | Result | Evidence |
| --- | --- | --- |
| I: new logic in correct layers | Yes | Identity data in core; presentation and product policy in UI; host thin wiring. |
| II: legacy only wiring/fixes, +50 budget | Yes, verify | Small title/About/update wiring; measure tracked and total changed legacy lines. |
| III/VII: abstractions/dependencies justified | Yes | Plain constants/functions; no new dependency. |
| IV: single sources and versioned data | Yes | One display identity, old host version retained; notice inventory schema 1. |
| V: tests first/hardware-free/headless | No only for desktop smoke | Unit tests headless, real GUI smoke additionally checks rendered identity. |
| VI: hazards where applicable | Yes | No machine/emission behavior. |
| VII: source and license provenance | Yes | Preserve upstream notices, record exact source/version and hashes; no prohibited fork source. |
| <=3 stories / <=40 tasks | Yes | 3 stories, 17 tasks. |

## Project Structure

```text
mikrocam/core/identity.py
mikrocam/ui/__init__.py, mikrocam/ui/identity.py
appGUI/MainGUI.py, appGUI/GUIElements.py, appHandlers/appUIActions.py, appMain.py
pyproject.toml
tests/test_product_identity.py, tests/test_product_update_boundary.py, tests/test_dependency_notices.py
tests/architecture/test_runtime_metadata.py, tests/smoke_app.py
.gitattributes, LICENSE, NOTICE.md, THIRD_PARTY_CHANGES.md, THIRD_PARTY_LICENSES/{inventory.json,README.md,...}
docs/ROADMAP.md, README.md
specs/003-branding-and-notices/
```

## Complexity Tracking

| Exception | Why needed | Simpler alternative rejected |
| --- | --- | --- |
| Desktop smoke alongside headless tests | Verify actual title/About rendering and CAM round-trip | Offscreen helpers alone cannot verify real desktop integration. |

No growth/size exception is needed. Tracked legacy growth: -225 lines; all changed legacy
files combined: -248 lines. Disabled host updater entry-point bodies were replaced with
thin policy calls instead of retaining unreachable code. Standalone updater services remain
tested and unchanged. The facade characterization now explicitly asserts version_check
does not delegate to Evo; affected updater tests assert no queuing/installer invocation.
License bytes are exempt from Git newline conversion so hashes survive Windows checkout.
