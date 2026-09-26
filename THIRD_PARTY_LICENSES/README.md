# Exact-version dependency notices

[inventory.json](inventory.json), schema version 1, covers every one of the 58 exact
runtime, development and optional image pins. Groups include inherited `-r` requirements:
runtime pins also belong to development and optional-image installs. Five additional
source-vendored/bundled components have separate records. No optional dependency imports
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
