# Implementation plan — Fiducial hizalama

2026-10-04; [spec](spec.md), [research](research.md), [data model](data-model.md).
CPython 3.13 / PyQt6 / NumPy 2 / Shapely 2; yeni bağımlılık yok.

## Constitution Check

1. PASS (I): Fit, format, hizalanmış iş `mikrocam.core`; yakalama `mikrocam.machine`
   (yalnız core import eder); nesne noktaları `mikrocam.bridge`; paneller `mikrocam.ui`.
2. PASS (II): Legacy satır değişikliği 0; panel mevcut preflight dock'undan açılır.
3. PASS (III, VII): Yeni soyutlama yok (kamera arayüzü bilinçli olarak eklenmedi). Yeni
   bağımlılık yok; NumPy mevcut core bağımlılığı.
4. PASS (IV): Tek `Placement` genişletildi; preflight, motion bounds, auto-level, hizalanmış iş,
   dry-run (türetilmiş iş üzerinden) ve lazer planlayıcı aynı tipi kullanır. Yeni kalıcı format
   şema 1 taşır, v1 fixture testi var; mevcut formatlar değişmez ve affine'i açıkça reddeder.
5. PASS (V): Core/codec/yakalama testleri Qt'siz ve donanımsız; akış FakeGRBL; testler önce.
6. PASS (VI): Tehlike analizi spec'te; mevcut durum makinesi ve Stop yolu kullanılır,
   hizalanmış iş için FakeGRBL Stop ve G54/G92 uyuşmazlığı testleri eklenir.
7. N/A (VII): Dış kaynaklı kod yok; matematik standart Procrustes/en küçük kareler.
8. PASS: 3 user story, 30 görev.

## Design

- `placement.py`: `affine` alanı, `rigid_data()`; `inverse()` affine tersini döner.
- `gcode_motion.motion_bounds`: tek genel yol, kaynak-açı ekstremumları (research R2); `mirror_x`
  özel durumu kalktı, mevcut rijit/ayna testleri aynen geçer.
- `fiducial.py`: modeller + `fit_alignment` + `default_method`.
- `fiducial_codec.py`: `dumps_fiducial_set` / `loads_fiducial_set`.
- `aligned_job.py`: autolevel/dry-run deseninde türetilmiş iş; kendi 8 haneli koordinat
  biçimlendirmesi, yay kirişleri, sınır ve kimlik denetimi.
- `laser_json.py`, `laser/visual_recipe.py`, `bridge/visual_export.py`: `rigid_data()`.
- `machine/fiducial_capture.py`: anlık görüntüden MPos/WCO okuma.
- `bridge/fiducial_points.py`: Excellon delik / Gerber flash merkezleri (mm).
- UI: `fiducial_panel.py` (çift tablosu, yöntem/politika, hesapla/kabul, kaydet/aç, nesneden
  seç, makineden yakala), `aligned_job_panel.py` + `aligned_job_worker.py` (G54 XY, kiriş,
  hazırla/iptal, Machine'e aktar, dry-run), `preflight_setup.py` hizalama modu,
  `preflight_panel.py` iki düğme ve sağlayıcılar.

## Complexity Tracking

| Durum | Gerekçe | Reddedilen basit alternatif |
| --- | --- | --- |
| Hizalanmış işte yay her zaman kiriş | Affine altında yay elips olur; tek yol | Benzerlikte yay koruma: ikinci kod yolu ve yön çevirme riski |

## Verification

RED → core/codec/akış/UI GREEN → ilgili placement/preflight/dry-run/autolevel/laser/visual
testleri → mimari + pip check → tam suite → masaüstü smoke → commit/push/PR → final-head
Windows CI. Merkezi takip: E:/VSCode/Flatcam/MikroCAM/docs/IS_TAKIP.md.
