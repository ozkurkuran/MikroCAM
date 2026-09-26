# Baseline research

## Runtime and dependency resolution

Decision: use installed standard CPython 3.13.13 x64 and seed version resolution from the
verified 8.994 port. Pin runtime and development closures for Windows and verify two fresh
environments. Rationale: upstream ranges allow materially different installations.
Alternative: conda environment.yml pins NumPy 1.26 and does not satisfy this slice.

Decision: omit standalone GDAL because repository Python code imports rasterio, not osgeo;
rasterio's Windows wheel supplies its native GDAL runtime. Raster/trace imports must be lazy.
Alternative: requiring external GDAL builds makes the declared clean Windows install fail.

Observed experiment: installing pyppeteer + svgtrace with the reference requirements failed
while building greenlet. Their pyee constraints backtrack to an old Playwright. Use optional
tracing with svgtrace's current Playwright backend, not an unrelated pyppeteer browser check.
No browser download is needed for core startup or CAM tests.

Resolved versions: svgtrace 2023.0.1 retains the same trace API without the NumPy<2 cap
present in 2023.1/2024. Playwright 1.63.0 and install-playwright 1.0.2 resolve with
greenlet 3.5.6 and pyee 13.0.1. requirements-image.txt pins their closure.

## Import and test isolation

Decision: move App command-line parsing from class definition to an explicit method invoked
by flatcam.py. Importing appMain must not consume pytest flags or terminate the interpreter.
Preserve shellfile/shellvar/headless behavior and test it before changing code.

Also retain App.args for positional file-open arguments and existing updater/startup tests.
The original full suite masked the import bug by importing App with a temporarily empty
sys.argv during collection; a fresh-process regression now catches it.

Decision: isolate QSettings, app data, updater calls and IPC in smoke; exercise real parsers,
geometry generation, persistence and rendering. Test scripts must not overwrite registry
associations or launch the real updater. Production defaults are not changed for the smoke.

Observed isolation correction: QSettings(organization, application) always uses NativeFormat;
setDefaultFormat only affects other overloads. Test-only subclassing selects the explicit
IniFormat overload before importing any application modules. This was verified against
[Qt's constructor documentation](https://doc.qt.io/qt-6/qsettings.html#QSettings-1) and a local
format/fileName probe. The final helper uses an explicit INI filename per application,
without changing Qt's global default format or settings search paths. Final isolated tests
preserve an exported HKCU settings snapshot.

## Reference behaviors

Decision: adapt the eight tests from legacy8994 at baseline-8.994-py313 to Evo's APIs;
do not import helper code wholesale if Evo already supports the behavior. Preserve upstream
test collection. Every parser fix gains fixed fixtures/expected geometry under tests/reference.
Alternative: weakening assertions or skipping failures would invalidate the baseline.

## Dependency licenses

Existing runtime dependencies retain their upstream notices. The feature's new development
dependencies are pytest (MIT) and pytest-qt (MIT); their installed metadata/license files are
the source for THIRD_PARTY_LICENSES. Optional svgtrace/Playwright already occur in upstream's
dependency graph; record their installed versions/notices if exposed in an optional lock.
No closed SDK or FlatCAM-Plus code is used. License inventory records package provenance;
it does not relicense third-party libraries under the application's MIT license.
