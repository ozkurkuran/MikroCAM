# Validation — lazer ada ve dama tahtası tarama

Base: `70800e5b`; branch `038-laser-island-tile`. Windows 11 masaüstü; paylaşılan
CPython 3.13 ortamı (`MikroCAM/.venv/repro-a`). Yeni bağımlılık yok; legacy dosya
değişikliği 0 satır. Fiziksel kupon ölçümü ve hedef uygulama (LightBurn/EZCAD) içe
aktarma doğrulaması bu dilimde yapılmadı (WAITING).

## Test-first

- Eski format kanıtı: `tests/reference/laser_manifest_v1.json` ve `laser_manifest_v2.json`
  değiştirilmemiş main (`70800e5b`) kodunun gerçek export'undan, uygulamadan önce üretildi.
- RED: `test_laser_islands.py` ve `test_laser_island_export.py` koleksiyonda
  `ImportError: IslandSettings`; `test_laser_island_ui.py` 3 FAIL. Log: worktree
  `.venv/island-red.log`.
- İlk uygulama koşusu iki test kaynaklı düzeltme gerektirdi: (1) normal hatch bir köşe
  teğetinde 1e-14 mm'lik kayan nokta artığı üretiyor; ada kırpması bunu (≤1e-9 mm) atıyor,
  eşdeğerlik testi bu artığı yok sayacak şekilde belgelendi; (2) iç içe `pytest.approx`
  kullanımı düzleştirildi. Ürün davranışı bu düzeltmelerle değişmedi.

## Sonuçlar

- Odaklı ada testleri: 64 PASS.
- İlgili `tests/test_laser_*.py` + `tests/architecture`: 584 PASS / 125.86 s
  (import sınırları ve legacy büyüme dahil). `pip check`: PASS.
- Modül/fonksiyon boyutu: `laser_islands.py` 146 satır, en uzun yeni fonksiyon 19 satır;
  `laser_cam.py` 357 satır.
- Tam paket (offscreen, paylaşılan `repro-a`): **5865 PASS, 310 subtest PASS, 3 skip,
  11 mevcut uyarı, 12 FAIL, 543.79 s**. 12 FAIL'in tamamı `SVG_UNAVAILABLE` (görsel SVG
  testleri): paylaşılan `repro-a` yorumlayıcısında `requirements-visual.txt` içindeki
  `resvg_py` kurulu değil; bu dilim görsel koda dokunmadı. Aynı 5 görsel test modülü
  (12 başarısız testi içeren 46 test) tam bağımlılıklı main `.venv` ile **46 PASS /
  176.78 s**. Log/JUnit: `.venv/island-full.log`, `.venv/island-full.xml`,
  `.venv/island-visual-mainvenv.log`. CI `requirements-dev.txt` ile `requirements-visual`
  kurar; nihai kanıt PR final-head Windows CI'dır.

## Gerçek masaüstü

- `tests/smoke_laser_islands.py`: exit 0. Gerçek menü/dock, reçete JSON kaydet → aç
  (aynı reçete), Gerber ada önizlemesi (3 mm döşeme, 0.1 mm örtüşme, 90° adım, dama
  tahtası; 264 yol, gerçek Geometry önizlemesi), SVG ve DXF ZIP (manifest şema 3,
  `manifest_island` eşit, her pass yol sayısı eşit, ezdxf denetimi temiz), OpenGL
  render ve normal kapanış. İşaretler: `LASER_ISLAND_PREVIEW_OK`,
  `LASER_ISLAND_SVG_EXPORT_V3_OK`, `LASER_ISLAND_DXF_EXPORT_V3_OK`,
  `LASER_ISLAND_RECIPE_JSON_PREVIEW_SVG_DXF_OK`, `VISUAL_FOCUSED_NATIVE_RENDER_SHUTDOWN_OK`.
  Log `.venv/island-native.log`; ekran görüntüsü `.venv/laser-island-native.png` gözle
  incelendi (komşu döşemelerde dik hatch; çapraz soluk çizgiler mevcut CNC iş hareketleri).
- `tests/smoke_app.py`: exit 0 (`SHUTDOWN_OK`), log `.venv/island-smoke-app.log`.

## Açık / WAITING

- Fiziksel kupon ölçümü (ısı dağılımı, dikiş, örtüşme etkisi): WAITING; gerçek lazer yok.
- LightBurn/EZCAD içe aktarmada ada sırasının korunması: WAITING (hedef uygulama yok).
- Bu doğrulama yalnız yazılım yol üretimi/export'udur; emisyon, hareket veya ısıl sonuç
  iddiası yoktur.
