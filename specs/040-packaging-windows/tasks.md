# Tasks — Windows paketleme (040) + 033 T001/T010

Hikâyeler: **US1** portable çalıştırma, **US2** kullanıcı başına kurulum/kaldırma,
**US3** lisanslar ve tekrarlanabilir yayın hazırlığı.

## Setup
- [x] T001 Merkezi takip, anayasa, roadmap, 003/033 okunur; `MikroCAM-packaging` worktree ve `.venv/build`, `.venv/test` binary-only ortamları kurulur.
- [x] T002 Spike: PyInstaller onedir; vispy veri, OR-Tools, PyOpenGL DLL, PATH sızıntısı, Tcl yarışı ve çıkış asılması bulguları research'e yazılır.
- [x] T003 spec/plan/research/tasks; uygulama varsayımları ve Constitution Check.

## US1 — Portable çalıştırma
- [x] T004 [US1] `tests/test_lifecycle_quit_before_loop.py`: olay döngüsünden önce istenen çıkışın döngü başlayınca kapanması (RED).
- [x] T005 [US1] `appHandlers/appLifecycle.py` en küçük düzeltme (GREEN); ilgili lifecycle testleri.
- [x] T006 [US1] `tests/test_release_windows.py`: kimlikten dosya adları/sürüm demeti, VERSIONINFO, portable config, deterministik ZIP, hariç modül/hedef kuralları (RED).
- [x] T007 [US1] `release/windows/release_layout.py` saf fonksiyonları (GREEN).
- [x] T008 [US1] `release/windows/mikrocam.spec`: tek Analysis, MikroCAM.exe + MikroCAMSmoke.exe, veri dizinleri, hariçler, svglib `.py`.
- [x] T009 [US1] `release/windows/frozen_smoke.py`: dondurulmuş içinde Gerber/CAM/proje + bitmap/SVG/PDF görsel pipeline + opsiyonel bağımlılık yokluğu + normal kapanış.
- [x] T010 [US1] `release/windows/build.py`: ortam/pin denetimi, temiz PATH, PyInstaller, payload, ZIP.
- [x] T011 [US1] `release/windows/smoke_binary.py`: IPC/kayıt defteri korumalı ZIP duman testi (Tcl offscreen + native, duman yürütücüsü).
- [x] T012 [US1] Yerel build + portable offscreen duman PASS.
- [x] T013 [US1] Yerel portable gerçek masaüstü duman PASS, ekran görüntüsü incelenir.

## US2 — Kurulum ve kaldırma
- [x] T014 [US2] `tests/test_release_windows.py`: NSIS tanımları, kaldırma dosya listesi (yalnız kendi dosyaları, derinden sığa dizinler) (RED).
- [x] T015 [US2] `layout.py` NSIS tanım/kaldırma listesi üretimi (GREEN).
- [x] T016 [US2] `release/windows/MikroCAM.nsi`: kullanıcı başına, HKCU kaldırma kaydı, Başlat menüsü, ikon, lisans sayfası, eski sürüm kaldırma, zlib.
- [x] T017 [US2] `build.py` makensis adımı; setup.exe üretimi.
- [x] T018 [US2] `smoke_binary.py` sessiz kurulum → kısayol/kayıt/kurulu exe duman → sessiz kaldırma → kalıntı yok.
- [x] T019 [US2] Yerel kurulum/kaldırma PASS; antivirüs davranışı gözlemlenir ve kaydedilir.

## US3 — Lisanslar ve yayın hazırlığı
- [x] T020 [US3] `tests/test_release_windows.py`: bundle manifest eşlemesi; izinsiz kaynak kökü, eşlenmemiş dosya, lisanssız sahip, hariç dağıtım (ortools/rasterio) reddi (RED).
- [x] T021 [US3] `layout.py` manifest/sahip eşlemesi (GREEN).
- [x] T022 [US3] `tests/test_dependency_notices.py` `build` grubu + yeni bileşenler/kanıt testleri (RED).
- [x] T023 [US3] `release/windows/collect_notices.py`: build araç lisansları, CPython LICENSE, NSIS COPYING, Qt 6.11.2 attribution sayfaları, devralınan artwork provenance; envanter güncellemesi (GREEN).
- [x] T024 [US3] `release/windows/NOTICE-BINARY.txt`, NOTICE.md, THIRD_PARTY_LICENSES/README.md, inventory `audit_gaps` güncellemesi.
- [x] T025 [US3] `.github/workflows/package-windows.yml`: tag/workflow_dispatch/paketleme PR build + offscreen duman + kurulum/kaldırma + artifact; yalnız tag'de taslak Release.
- [x] T026 [US3] `docs/RELEASE_WINDOWS.md` + README: kurulum, SmartScreen/AV, yayın adımları (kullanıcı kararı).

## 033 katılımı
- [x] T027 033 T001: izole binary-only resvg_py kurulum/render, paketleme denemesi (dondurulmuş SVG), lisans kaydı; 033 tasks/validation güncellenir.
- [x] T028 033 T010: SVG/PDF lazy import, Qt PDF lisans/paketleme ve dondurulmuş offscreen bitmap+SVG+PDF kaydet/aç; 033 tasks/validation güncellenir.

## İkili dumanda bulunan legacy hatalar
- [x] T033 [US1] `tests/test_tcl_open_project_headless.py` (RED) → `appIO.restore_project_handler` Tcl/CLI modal düzeltmesi (GREEN).
- [x] T034 [US2] `tests/test_vispy_font_unicode_path.py` (RED) → `VisPyPatches` ASCII-dışı yol FreeType düzeltmesi (GREEN).

## Delivery
- [x] T029 Mimari testler, pip check, tam pytest (offscreen) ve kaynak `tests/smoke_app.py` native.
- [x] T030 validation.md; commit (build çıktısı yok), push, PR.
- [x] T031 PR Windows CI + paketleme iş akışı (yol filtreli PR; `workflow_dispatch` varsayılan dalda); hatalar düzeltilir.
- [x] T032 Merkezi takip son durumu; tag/Release yayını WAITING (kullanıcı kararı), merge koordinatörde.
