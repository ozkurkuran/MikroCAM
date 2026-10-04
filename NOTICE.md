# MikroCAM source and third-party notices

MikroCAM application source is licensed under the [MIT license](LICENSE). Original
copyright notices remain in the source, including:

- Copyright MikroCAM (c) 2026 MikroCAM contributors.
- Copyright FlatCAM Evo (c) 2018-2023 Marius Stanciu.
- Copyright FlatCAM (c) 2014-2018 Juan Pablo Caram.

MikroCAM derives from FlatCAM Evo's `Beta_1.0` baseline at
`e046a2a33926003765f83d6402b96fe6c5c3bcf7`, with earlier FlatCAM authorship preserved.
[THIRD_PARTY_CHANGES.md](THIRD_PARTY_CHANGES.md) records source imports and local adaptations.
Individual source notices continue to apply.

## PCB reference designs

The manufacturing inputs, editable hardware sources and retained notices under
[`tests/reference/boards`](tests/reference/boards/manifest.json) are reference data with
their original terms: MIT, BSD-3-Clause, CC-BY-3.0 or CERN-OHL-W-2.0 as identified per board.
The application MIT license does not relicense these designs or their derived reference
captures. Original bytes and attribution are retained; the manifest records immutable
source revisions, file/member paths and SHA256 values. See
[`tests/reference/README.md`](tests/reference/README.md) for the inventory and reproduction workflow.

## Dependencies retain their own terms

The application MIT license does not relicense dependencies, vendored components, fonts,
icons or other artwork. [The dependency inventory](THIRD_PARTY_LICENSES/inventory.json)
records all 58 exact pins from the runtime, development and optional image requirements,
their installation groups, supplied license metadata, exact distribution sources, and
SHA-256 hashes of copied license/notice bytes. The full supplied texts are retained under
[THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES/README.md). Metadata labels are upstream
declarations; copied component notices remain the licensing evidence.

The pinned **PyQt6 6.11.0 wheel is GPLv3**, specifically `GPL-3.0-only` in its supplied
metadata. Its complete GPLv3 text is included. The **Qt6 6.11.2 wheel supplies LGPL v3**
metadata and an LGPL text; these are also included. This does not assert that every Qt
module or bundled component has identical terms. Commercial licensing available from
upstream is not a license acquired or supplied by this source checkout. Other copyleft
notices include svglib's LGPL-3.0-or-later, certifi's MPL-2.0, Shapely's bundled GEOS
notice and ReportLab's bundled DarkGarden font notices. Their terms are not replaced by MIT.
Recipients distributing combinations must observe the applicable component terms; this
record does not declare a binary distribution cleared for release.

Supplied bundled notices are included, not only each Python package's top-level license:
NumPy's embedded libraries and random implementations; Matplotlib's font notices and
Pillow's supplied license; nested setuptools vendor distributions; Playwright's driver, Node
license and third-party notices; Shapely's GEOS/Windows notices; PyOpenGL's DLL notices;
ReportLab's fonts; and Rasterio's GDAL/PROJ data notices. The source archives for exact
PyOpenGL 3.1.10 and pyserial 3.5 supply their main license texts missing from their wheels.

Playwright's Node driver is part of the pinned wheel and its supplied notices are retained.
Downloaded Chromium or other browser binaries are **not vendored in this source checkout**;
their acquisition and licensing remain separate from this inventory.

## Source-vendored components

- `libs/qdarktheme` identifies PyQtDarkTheme **1.1.1**, by Yunosuke Ohsugi, under MIT.
  Its exact-version source license is retained. `libs/qdarktheme/themes/__init__.py`
  records Google **Material design icons under Apache-2.0** and **QDarkStyleSheet
  stylesheet source under MIT**, crediting Colin Duquesnoy. Evo's vendored resources
  modify icon colors/angles/namespaces and styles. The original resource revisions are
  unrecorded; pinned upstream license-text snapshots and the original provenance file
  are retained without asserting resource-by-resource correspondence. QDarkStyleSheet's
  full notice also contains a separate images section; that section is not represented
  as the license for the Material design icons.
- `descartes` derives from Sean Gillies' **Descartes 1.1.0**, whose exact source metadata
  declares BSD. The published source archive and wheels omit a full license file and the
  original repository is unavailable. The inventory preserves exact source metadata and
  full **BSD-3-Clause downstream notices** from conda-forge and Debian 1.1.0-4, with their
  provenance explicitly distinguished from upstream archive contents. Local adaptations
  support Shapely 2, GeoJSON, empty polygons and XY rendering; no MIT relicensing is asserted.
- Optional svgtrace **2023.0.1** bundles **imagetracer.js 1.2.5** by Andras Jankovics,
  with FredHappyface tracing tweaks. Its header explicitly exempts the file from svgtrace's
  MIT license and supplies **The Unlicense / PUBLIC DOMAIN**. The complete unchanged
  attribution/license header is retained as a separate component notice.

## Inherited artwork and release audit gaps

Evo's About credits name these artwork providers; the credits remain attributed here:

- [Freepik](https://www.flaticon.com/authors/freepik), through Flaticon.
- [Icons8](https://icons8.com).
- [oNline Web Fonts](http://www.onlinewebfonts.com).
- [Pixel perfect](https://www.flaticon.com/authors/pixel-perfect), through Flaticon.
- [Anggara](https://www.flaticon.com/authors/anggara), through Flaticon.
- [Kharisma](https://www.flaticon.com/authors/kharisma), through Flaticon.

Evo did not record **per-file provenance** linking each inherited image to its original
author, applicable license version and required notices. Since the Windows packaging slice,
[a git provenance record](THIRD_PARTY_LICENSES/inherited-assets/provenance.json) lists every
shipped file under `assets/resources`, `assets/examples` and `assets/icon.png` with its SHA-256,
adding and last commit, author and date (722 unchanged FlatCAM/Evo files, 46 replaced by
MikroCAM branding). Git history names who committed a file, not who drew it; these credits do
not establish a blanket MIT license or permission for every asset. Per-icon license
verification remains an open audit item.

**Rasterio native-library audit gap:** all notices supplied by the pinned Windows wheel
are preserved, including its package, GDAL data and PROJ data notices. That wheel does not
provide an aggregate license inventory for every DLL in `rasterio.libs`; native library
versions, sources and their full license/notice obligations require a distribution audit.
This gap applies to optional source installations only: the Windows binary excludes Rasterio.

## Windows binary distribution

The Windows portable ZIP and installer (built by `release/windows/build.py`, spec 040) ship
`LICENSE.txt`, this file, `NOTICE-BINARY.txt`, the complete `THIRD_PARTY_LICENSES` folder as
`licenses/`, and `bundle-manifest.json`, which maps every packaged file to the component that
supplied it. The build fails if a file comes from outside the pinned interpreter, the pinned
wheels (verified against their installed RECORD hashes) or this repository, or if its owner
has no retained license text.

- Because the package includes **PyQt6 (GPLv3)**, the binary package as a whole is conveyed
  under GPLv3 terms; MikroCAM's own source remains MIT. `NOTICE-BINARY.txt` names the
  corresponding source locations. Qt DLLs stay replaceable files (LGPLv3) and svglib
  (LGPL-3.0-or-later) is shipped as plain `.py` source.
- Third-party code inside the Qt 6.11.2 modules (PDFium, FreeType, HarfBuzz, PCRE2, libpng,
  libjpeg, zlib, Mesa llvmpipe and others) is covered by Qt's retained attribution pages.
- The CPython 3.13.13 Windows `LICENSE.txt`, including bundled library notices and the
  Microsoft Distributable Code conditions for the Visual C++ runtime DLLs, is retained.
- The PyInstaller bootloader is embedded under its bootloader exception; the NSIS 3.12
  installer stub uses only zlib/libpng-licensed modules. Build tools are pinned in
  `requirements-build.txt` and inventoried in the `build` group.
- **Not shipped:** the optional image stack (Rasterio/GDAL, svgtrace, Playwright), PyOpenGL's
  GLUT/GLE DLLs and **Google OR-Tools**. OR-Tools statically links EPL-2.0 COIN-OR code that
  cannot be conveyed together with GPLv3 PyQt6 as one work; the binary uses the built-in RTree
  path ordering instead. Source installations are unchanged.
- The resvg_py extension ships unchanged with all 152 retained crate notices; its wheel build
  provenance remains unavailable upstream. The inventory's `audit_gaps` records each item's
  `windows_binary` status. Executables are not code-signed.
