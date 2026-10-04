# Tasks — 038 laser-island-tile

Test görevleri ilgili uygulama görevlerinden önce gelir (anayasa V).

## Setup
- [x] T001 Merkezi takip, anayasa, roadmap ve 006–008/036 kodunu oku; `038` worktree'sini aç.
- [x] T002 Main kodundan eski manifest fixture'larını üret: `tests/reference/laser_manifest_v1.json`, `laser_manifest_v2.json`.
- [x] T003 spec/research/data-model/plan; uygulama varsayımlarını UV-1…UV-7 olarak kaydet.
- [x] T004 Analiz: 3 story / 12 FR / görev eşlemesi ve 037 çakışma alanı.

## US1 — Ada döşemeli hatch (P1)
- [x] T005 [US1] `tests/test_laser_islands.py`: IslandSettings/PlanOptions doğrulama testleri (RED).
- [x] T006 [US1] Aynı dosyada ızgara/sıra testleri: orijine sabit hücreler, dama tahtası komşuluk, raster, sınır (RED).
- [x] T007 [US1] Kapsama testleri: step 0/overlap 0 ≡ normal hatch, bölge içinde kalma, aralık kapsaması, örtüşme bandı, delikli bölge, cross hatch (RED).
- [x] T008 [US1] Planner testleri: kontur önce, döşeme sırası, döşeme içi interlace, placement bir kez, determinizm, iptal (RED).
- [x] T009 [US1] `IslandSettings` ve `PlanOptions.island` doğrulaması (`mikrocam/core/laser_paths.py`).
- [x] T010 [US1] `mikrocam/core/laser_islands.py`: hücreler, sıra, döşeme kırpması.
- [x] T011 [US1] `mikrocam/laser/planner.py` ada dalı.

## US2 — Export ve kalıcılık (P1)
- [x] T012 [US2] `tests/test_laser_island_export.py`: v3 manifest roundtrip/strict alanlar (RED).
- [x] T013 [US2] Eski v1/v2 fixture'ları byte-kayıpsız açma ve `upgrade_manifest` testleri (RED).
- [x] T014 [US2] SVG/DXF her pass sıra ve sayı korunumu, README ada notu, ada kapalı byte eşitliği (RED).
- [x] T015 [US2] Reçete JSON kaydet/aç sonrası aynı ada planı (RED değil — regresyon koruması).
- [x] T016 [US2] `mikrocam/core/laser_manifest.py` v3 + migration.
- [x] T017 [US2] `mikrocam/laser/export.py` v3 yazımı ve README notu.

## US3 — Laser CAM paneli (P2)
- [x] T018 [US3] `tests/test_laser_island_ui.py`: kontroller, geçersiz kılma, plan seçenekleri, hata (RED).
- [x] T019 [US3] `mikrocam/ui/laser_cam.py` ince kontroller.
- [x] T020 [US3] `tests/smoke_laser_islands.py` gerçek masaüstü yolculuğu.

## Delivery
- [x] T021 Odaklı testler, `tests/architecture`, `pip check`, modül/fonksiyon boyutu.
- [x] T022 Tam paket (offscreen) ve masaüstü smoke (`smoke_app.py`, `smoke_laser_islands.py`).
- [x] T023 `docs/LASER_CAM.md` kullanıcı belgesi ve `validation.md`.
- [ ] T024 Commit, push, PR (merge yok).
- [ ] T025 PR final-head Windows CI; hata varsa düzelt.
- [ ] T026 Merkezi takipte nihai durum; fiziksel kupon WAITING.
