# Target integration — 2026-10-02

Base: MikroCAM main c5a666cf, Python 3.13.13, PyQt6 6.11.0, Pillow 12.3.0.
Worktree: E:/VSCode/Flatcam/MikroCAM-visual-interlace, branch 032-visual-interlace.
Golden reference remains read-only.

Existing core/placement.py is the ONLY placement model. core/laser_job.py LaserRecipe
and core/laser_json.py serializer are reused. Existing LaserJob is polygon-only:
a raster payload gets its own VisualInterlaceJob value, without changing CNCJob or duplicating
recipe/placement. Existing laser/interlace.py remains the vector planner.

Host: flatcam.py / appMain.py menu_plugins (existing Laser CAM entry).
UI: ui/laser_worker.py supplies the QThread cancellation/signal pattern.
Project: Geometry objects serialize obj_options; a non-output Geometry carrier can
hold a versioned visual payload. bridge publishes/reads that payload on the GUI thread.
No new FlatCAM object type. Recipe JSON is independent of host project files.

Architecture scanner tests/architecture/imports.py is stricter than the original
proposal: NumPy computation in core (codec conversion also allowed in bridge),
third-party codecs in bridge, Qt only ui; domain packages are stdlib + core only. Adapted paths:
core/visual.py + visual_normalize.py + visual_interlace.py: pure data/array logic;
laser/visual_plan.py + visual_recipe.py: stdlib scheduling/serialization;
bridge/visual_bitmap.py + visual_svg.py + visual_png.py: optional native codecs;
ui/visual_pdf.py: lazy QtPdf worker renderer;
bridge/visual_workflow.py: detached source orchestration;
ui/visual_interlace_panel.py + visual_worker.py: thin controls and worker lifecycle.
Core and domain packages remain headless. No architecture guard is weakened.

LightBurn G02: no installation found in standard Program Files paths, and no real
saved native fixtures available yet. Version/device question pending. No guessed
.lbrn2 schema will be advertised as verified. V1/V2 continue independently.

Final local software evidence: source/config SHA8fefc0d0 (full digest in implementation.md),
5744 tests/310subtests PASS,3skip/11existingwarning509.30s; actual native menu→3formats→
JSON/PNG/host project/source deletion→OpenGL→normal shutdown PASS. G02/nativeLB remains
WAITING. 75-crate exact source notice coverage is complete; wheel build provenance/final bundle audit remains open. Main/remote/CI NOT_RUN.

## 2026-10-03 — resumed checkpoint

Complete suite PASS exit0: **5746 tests,310subtests,3skips,11existing warnings,306.23s**.
Log: `.venv/visual-resume-final-regression.log`; JUnit: `.venv/visual-resume-final-pytest.xml`.
Source/notice checkpoint: `77899fec9b5b14b87485c5be6c34bc6e6f79af92eee28e7dc815c6e06468334e`,201 SHA-verified files.
`.venv/visual-resume-final-result.json` proves the checkpoint stayed unchanged.
The actual worktree `.venv/Scripts/python.exe` passed pip check; seven SVG-dependent
cases first failed under the older repro-a interpreter, then passed in the correct
environment before this full run. Both results are retained as separate evidence.

The prior native menu/source/project/OpenGL/shutdown evidence remains applicable
to unchanged runtime/config files; it was not rerun or relabelled as a new native test.
Notice inventory and the two added notice tests are covered by this fresh full suite.
Historical5744-test records above remain historical rather than the current full result.

A local source checkpoint preserves V1/V2 and their tests/specs/notice records.
The commit is recorded in the central IS_TAKIP after git verifies it.
Push/PR/hosted CI/main delivery remain NOT_RUN. Two real historical vector-only
projects provide limited format metadata; they are not Image fixtures. Current
LightBurn executable/device/embedded Image evidence and native V3/V4 remain open.
No complete binary-release audit or complete .lbrn2 product delivery is claimed.
