# Validation — lazer reçete veritabanı

Base: `70800e5b` (origin/main, 036 birleştirilmiş); branch `037-laser-recipe-db`.
Windows 11 masaüstü; CPython 3.13.13. Yeni bağımlılık ve legacy dosya değişikliği yok.
Fiziksel lazer işlemi, emisyon veya gerçek cihaz bağlantısı yapılmadı.

## Test-first

- RED: 4 yeni test modülü (model, v1 codec/migration/0.2 JSON içe aktarma, atomik depo,
  arayüz) **95 FAIL / 0 PASS** — modüller yoktu. Log: main `.venv/laser-recipe-db-red.log`.
- İlk uygulamada `put_machine` makineyi reçetelerden önce değiştirdiği için ara değer
  doğrulaması başarısız oldu; makine ve reçete tabloları tek adımda değiştirildi.
- Mevcut `test_laser_recipe_ui.py` atomik kayıt hata testi, yazıcı ortak
  `mikrocam/laser/recipe_db_store.py` modülüne taşındığı için aynı davranışı yeni modülde
  yamalayacak biçimde güncellendi; `FakeHost` yalnız veritabanı yolunu sağlar.
- Yeni/ilgili odak: 152 PASS (`test_laser_recipe_db*`, `test_laser_cam_ui`,
  `test_laser_recipe_ui`, `test_laser_device_ui`).
- `tests/architecture`: 83 PASS (import sınırı, legacy büyüme 0 satır). `pip check`: PASS.
- Modül/fonksiyon boyutu: en büyük yeni modül 377 satır (UI), en uzun fonksiyon 33 satır.

## Tam regresyon

Ortak `.venv/repro-a` yorumlayıcısında `resvg_py` kurulu değil (`requirements-visual.txt`
eksik; `pip check` bunu yakalamaz). Bu yüzden bu ortamda SVG render gerektiren 12 görsel
test `SVG_UNAVAILABLE` ile başarısız olur; değişiklikle ilgisizdir. Aynı 12 test ve
ilgili modüller, eksiksiz `requirements-dev.txt` kurulu ana `.venv` yorumlayıcısıyla
(3.13.13) PASS'tir.

Kaynak commit sonuçları ve CI bağlantısı merkezi takip dosyasında
(`docs/IS_TAKIP.md`, “Lazer reçete veritabanı (28)”) ve PR üzerinde kayıtlıdır.

## Gerçek masaüstü

`tests/smoke_app.py` (ana `.venv`, OpenGL masaüstü): **EXIT 0, 106 s**. Laser CAM
yolculuğuna eklenen adım, sandbox veri dizinindeki
`appdata\FlatCAM\mikrocam\laser_recipe_db.json` dosyasına editör reçetesini kaydetti,
dosyadan yeniden okudu, tabloda seçip editöre yükledi:
`LASER_RECIPE_DB_SAVE_RELOAD_OK`. Ardından mevcut önizleme, çok geçiş ve SVG/DXF dışa
aktarma işaretleri de geçti. Smoke kendi sürecinden artık worker bırakmadı.

## Bekleyen (cihaza bağlı)

- Veritabanındaki reçetelerin fiziksel kabulü (MOPA M7 100 W dahil): **WAITING**.
- Gerçek M7 üretici frekans/atım aralıkları sağlanmadı ve tahmin edilmedi.
- LightBurn native `.lbrn2` (G02) bu dilimin kapsamı dışında; mevcut kapı korunur.
