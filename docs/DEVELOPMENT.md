# Development checks

Use the checkout's `.venv` and the pinned `requirements-dev.txt` environment described
in [README](../README.md). All feature work follows the [constitution](../.specify/memory/constitution.md)
and the [roadmap](ROADMAP.md).

```powershell
.\.venv\Scripts\python.exe -m pytest tests/architecture -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

## Architecture boundaries

New runtime code belongs in `mikrocam/`. Core can use stdlib, NumPy and Shapely;
hardware/process access and desktop libraries are excluded. Domain packages can use core
and their own internal modules plus stdlib, but not each other or external libraries directly.
Geometry dependencies are accessed through core; hardware adapters belong in bridge.
Only bridge can import the legacy host, including vendored `libs` packages.
UI may use lower layers. The package root stays inert and stdlib-only.

The AST check visits initializers, relative imports, imports inside functions or type-checking
blocks, and conventional `importlib.import_module`/`__import__` calls including aliases.
Dynamic names it cannot resolve fail visibly. This is a development guard, not a security
sandbox or a substitute for review of reflection and side effects. Core's isolated import
test additionally checks that importing the skeleton requires neither site packages nor Qt.

## Legacy growth budget

`tests/architecture/legacy-baseline.json` records the ten largest legacy Python application
modules at the merged Python 3.13 baseline. Its schema, selection and counts are verified
against the recorded immutable revision. Do not rewrite it to hide a failing check.

The allowance is **50 net lines combined per feature**, including reductions. The check
tracks renamed modules and compares the current working files with a Git base:

1. `MIKROCAM_BASE_REF`, when explicitly supplied;
2. otherwise the merge-base of `HEAD` and `origin/main`;
3. when already at that merge-base, the first parent of `HEAD` (latest main change).

CI sets the pull request base SHA or the previous main revision. A missing base fails with
guidance; fetch full history instead of disabling the check. To reproduce a particular run:

```powershell
$env:MIKROCAM_BASE_REF = '<base commit from CI>'
.\.venv\Scripts\python.exe -m pytest tests/architecture/test_legacy_growth.py -q
Remove-Item Env:MIKROCAM_BASE_REF
```

An exception requires a concrete explanation and rejected simpler alternative in the
feature plan's Complexity Tracking section, review, and a narrowly scoped guard adjustment.
A plan paragraph alone does not silently switch the check off. Files outside the tracked
ten still obey the constitution's prohibition on new feature logic in legacy code.

## Hosted and desktop validation

The Windows workflow installs the exact version in `.python-version` and pinned development
dependencies, runs `pip check` and the full suite with the offscreen Qt backend, and retains
the JUnit report even on failure. It has read-only repository permissions.

GUI changes also require `python tests/smoke_app.py` on a working desktop/OpenGL environment.
The hosted headless job does not claim to validate real OpenGL or physical machines.

## KiCad desktop validation
Run `python tests/smoke_kicad_app.py` with the same validated CAM interpreter on the native desktop. It checks direct transfer startup, mm alignment, DRC acknowledgement, source/manifest project roundtrip, CAM generation, OpenGL rendering and normal shutdown. Set `MIKROCAM_REAL_KICAD_PACKAGE` to a retained real IPC export to include its four-role import. Settings are isolated; no physical port is opened.

The existing `python tests/smoke_app.py` validates the general desktop journeys separately. Each command retains the shared120s watchdog; KiCad's additional project/export scenarios do not consume the aggregate desktop time budget.
