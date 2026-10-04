# Exact-version dependency notices

[inventory.json](inventory.json), schema version 1, covers every one of the 65 exact
runtime, development, optional image and Windows build-tool pins. Groups include inherited `-r` requirements:
runtime pins also belong to development and optional-image installs. Five baseline source-vendored/bundled components have separate records. Visual
interlace additionally records 75 exact Rust source crates and their source manifest. No optional dependency imports
are needed to check this inventory.

Each dependency record preserves its exact version and supplied license expression,
License field, license classifiers and License-File metadata. Source records identify
the exact PyPI wheel URL, filename and published artifact SHA-256. Copies were gathered
from the matching Windows CPython 3.13 environment and checked against installed RECORD
hashes. Playwright's installed WHEEL declares `py3-none-any`; its platform artifact is
identified using the Windows x64 wheel filename. The distribution's metadata digest and
declared wheel tags are retained as capture evidence.

Notice files are organized as `package/version/wheel/original-distribution-path`. All
supplied files whose basenames identify licenses/notices/copying/copyright/authors,
including vendor distributions and binary/data notices, retain their bytes. A parent
folder named `licenses` does not qualify runtime code or SPDX lookup data as a notice.
Code, bytecode and binaries are excluded. Every file record has
its repository-relative path, exact source URL/member and SHA-256. Git attributes prevent
newline conversion of this directory. The five earlier baseline folders remain historical
records; the versioned inventory is authoritative for the current pin coverage.

PyOpenGL 3.1.10 and pyserial 3.5 wheels omit the main project license. Their exact PyPI
source archives provide the retained full texts under `package/version/sdist/`, with
archive URL, artifact hash and member path. PyQt6's supplied GPLv3 text and Qt6's LGPL text
are retained; these components are not relicensed under the application's MIT license.

`vendored/` records qdarktheme 1.1.1, Material design icons, QDarkStyleSheet and Descartes.
`bundled/` records the complete Unlicense/attribution header from svgtrace's imagetracer.js.
Descartes's exact 1.1.0 source archive omits full license text: its original metadata and
unaltered full downstream conda-forge/Debian notices are clearly distinguished. Material
icons/QDarkStyleSheet license snapshots identify the copied text's immutable revision;
they do not establish the unrecorded original vendored resource revisions.

Run the offline completeness, path-safety and integrity checks with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_dependency_notices.py
```

Package notice coverage and retained hashes do not close a complete binary release audit.
The inventory's `audit_gaps` and [NOTICE.md](../NOTICE.md) explicitly track unknown inherited
artwork provenance, unrecorded theme-resource revisions, Descartes's missing original full
text and Rasterio's missing aggregate native-DLL inventory. Downloaded browser binaries
are not vendored. License terms for any later bundled installer must be audited separately.

Visual interlace adds optional `resvg_py==0.5.0` (MIT wrapper) under the optional-image
group; exact ABI3 Windows artifact, metadata and wrapper license are retained.
`requirements-visual.txt` is included by the image extra and development requirements. The exact Rust source notice graph is retained; wheel build provenance and final bundle
composition remain explicit binary-release audit gaps in inventory.json.

## Visual renderer source notice graph

The exact resvg_py 0.5.0 sdist (SHA256 6d3bf8e866b4e129524d9432a809138b2d100931d8d635bc81294002abcdfd46)
contains the retained Cargo.lock. All 75 registry packages were downloaded from the
primary static.crates.io source and verified against their lockfile checksums.
152 original license/notice files are retained byte-for-byte under resvg-py/0.5.0/rust-crates.
Authors/copyright notices are distinguished from full license texts.
Siphasher's original COPYING contains copyright and references to MIT/Apache-2.0,
not either full text. Its referenced canonical Apache-2.0 text is retained separately
as LICENSE-APACHE with its own official Apache URL and SHA256 provenance.

This is a conservative source-lock superset, including platform and build dependencies.
Both PyPI wheel and sdist build-provenance endpoints returned 404. The exact source graph
is recorded without claiming a proven mapping from every stripped binary component to
that graph. Final bundle composition and binary build provenance remain a release audit.
Offline coverage is checked by tests/test_visual_notices.py and test_dependency_notices.py.

## Windows binary distribution (spec 040)

`requirements-build.txt` pins the build tools in the `build` group: PyInstaller 6.22.3
(GPL-2.0-or-later with the bootloader exception that covers the bootloader embedded in
MikroCAM.exe), pyinstaller-hooks-contrib, altgraph, pefile and pywin32-ctypes. Their exact
wheel license files are retained like every other pin.

Components shipped only by the Windows binary are recorded as inventory components:

- `cpython` 3.13.13: the official Windows build's LICENSE.txt (PSF plus bundled library
  notices and the Microsoft Distributable Code conditions). `release/windows/build.py`
  refuses an interpreter whose LICENSE.txt hash differs.
- `qt-third-party` 6.11.2: the Qt "Third-Party Code Used in Qt" page and the attribution pages
  for the shipped Core, GUI, Image Formats, Network, PDF (PDFium), SVG and Test modules and
  Mesa llvmpipe, kept byte-for-byte as fetched from doc.qt.io.
- `nsis` 3.12: COPYING for the installer stub (zlib compressor only).

`inherited-assets/provenance.json` records the git provenance (SHA-256, adding and last commit,
author, date) of every shipped file under `assets/resources`, `assets/examples` and
`assets/icon.png`. It does not identify original artwork authors or per-icon licenses.

The whole directory ships in the binary as `licenses/`. `audit_gaps` entries carry a
`windows_binary` status; Rasterio, OR-Tools and PyOpenGL's GLUT/GLE DLLs are excluded from the
binary. Regenerate these records with `release/windows/collect_notices.py` from the isolated
build environment and verify them with `tests/test_binary_notices.py`.
