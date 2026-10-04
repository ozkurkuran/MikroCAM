# Implementation plan — Lazer ada ve dama tahtası tarama

2026-10-04; [spec](spec.md), [research](research.md), [data model](data-model.md).
CPython 3.13 / PyQt6 / Shapely 2 / NumPy 2; yeni bağımlılık yok.

## Constitution Check

1. **Evet.** Ayar/geometri `mikrocam.core` (`laser_paths`, yeni `laser_islands`), sıralama
   `mikrocam.laser.planner`, export `mikrocam.laser.export`, kontroller `mikrocam.ui.laser_cam`.
   Core ve alan paketi Qt/legacy import etmez; bridge değişmez.
2. **Evet.** Legacy dosya değişikliği 0 satır; mevcut Laser CAM menü bağlantısı kullanılır.
3. **Evet.** Yeni soyutlama yok: `IslandSettings` ve `IslandTile` düz dataclass'tır; iki sıra
   modu bir enum değeridir, registry/plugin değildir. Yeni bağımlılık yok.
4. **Evet.** Birim mm, transform tek `Placement` (plan sonunda bir kez). Kalıcı değişiklik
   yalnız export manifest'idir: şema 3, `upgrade_manifest` migration'ı ve main kodundan
   üretilmiş v1/v2 fixture'larını açan test. Reçete/job JSON şeması değişmez.
5. **Evet.** Geometri/codec/export testleri Qt'siz ve önce yazılır; UI testi offscreen,
   masaüstü smoke ayrıca.
6. **N/A (gerekçeli).** Makine hareketi/emisyon yok; spec'te tehlike analizi yalnız
   geometri/export riskleri için yazıldı. Durum makinesi/stop yolu kapsam dışı.
7. **Evet.** Özgün uygulama; dış kod yok, `THIRD_PARTY_CHANGES.md` gerekmez.
8. **Evet.** 3 user story, 26 görev.

## Design

- `IslandSettings` ve `PlanOptions.island` (`laser_paths.py`): doğrulama; ada hatch ister
  ve döşeme ≥ aralık.
- `laser_islands.py`: `tile_cells` (orijine sabit hücre aralığı, sınır, sıra),
  `island_hatch_paths` (hücre başına marjlı pencere → döndürülmüş tarama → kapalı hücre
  kırpması → yarı açık üst/sağ kenar filtresi; boş döşemeler atlanır). Mevcut `_lines`
  ve tarama sınırı (`MAX_SCAN_LINES`) yeniden kullanılır.
- `planner.plan_laser`: ada varsa konturlar + döşeme sırasıyla her döşemenin interlace'li
  hatch'i; yoksa önceki yol değişmeden.
- `laser_manifest.py`: v3 doğrulama, `island_to_data`/`island_from_data`,
  `upgrade_manifest`. `export.py`: ada varsa v3 + README ada notu, yoksa önceki byte'lar.
- `ui/laser_cam.py`: “Island tiling” onay kutusu + 4 kontrol; `_inputs` ile mevcut
  geçersiz kılma mekanizmasına katılır.

## Complexity Tracking

| İhlal | Gerekçe | Reddedilen basit alternatif |
| --- | --- | --- |
| — | Anayasa ihlali yok. Manifest v3 yeni sürümdür; 036'nın v1/v2 profil eşlemesi korunur. | Ada ayarlarını v2'ye opsiyonel alan olarak eklemek: strict alan kümesini ve “eski çıktı aynı” garantisini bozar. |

## Verification

RED (yeni testler) → core/codec/planner GREEN → UI offscreen → ilgili laser + mimari →
`pip check` → tam paket (offscreen, arka planda) → gerçek masaüstü `tests/smoke_app.py` ve
`tests/smoke_laser_islands.py` → commit/push → PR final-head Windows CI. Merge koordinatördedir.
Merkezi kayıt: `E:/VSCode/Flatcam/MikroCAM/docs/IS_TAKIP.md`. Fiziksel kupon WAITING.
