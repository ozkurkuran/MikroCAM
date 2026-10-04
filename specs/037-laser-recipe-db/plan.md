# Implementation plan — Lazer reçete veritabanı

2026-10-04; [spec](spec.md), [research](research.md), [data model](data-model.md).
CPython 3.13 / PyQt6; yeni bağımlılık yok (stdlib `json`, `hashlib`, `os`, `tempfile`, `uuid`).

## Constitution Check

1. **Evet** (I): Model/işlemler `mikrocam/core/laser_recipe_db.py`, codec
   `mikrocam/core/laser_recipe_db_json.py`, dosya deposu `mikrocam/laser/recipe_db_store.py`,
   veri yolu `mikrocam/bridge/laser_cam.py`, arayüz `mikrocam/ui/laser_recipe_db.py`.
   Core ve alan Qt/legacy import etmez.
2. **Evet** (II): Legacy dosya değişikliği 0 satır.
3. **Evet** (III, VII): Yeni soyutlama/registry/ORM yok; dört düz dataclass ve saf
   fonksiyonlar. Atomik yazım tek yardımcıya taşınır ve iki gerçek kullanıcısı vardır
   (reçete JSON kaydı, veritabanı kaydı). Yeni bağımlılık yok.
4. **Evet** (IV): Cihaz profili makinede tek kaynak; reçete parametreleri mevcut
   `LaserPass`/`LaserRecipe` doğrulamasıyla; veritabanı dosyası `schema_version=1`, migration
   giriş noktası, v1 altın dosyası ve schema1/schema2 reçete içe aktarma testleri.
5. **Evet** (V): Core/codec/depo testleri Qt'siz ve önce yazılır; UI testleri offscreen
   qtbot; masaüstü smoke.
6. **N/A** (VI): Makine hareketi/emisyon yok; veri riski tehlike analizi spec'te.
7. **N/A** (VII): Dış kaynaklı kod yok.
8. **Evet**: 3 user story, 26 görev.

## Complexity Tracking

| Konu | Gerekçe | Reddedilen basit alternatif |
| --- | --- | --- |
| Özel modül önekli yardımcıların (`_fields`, `_load`, `_dump`) laser_json'dan import edilmesi | Aynı strict JSON kurallarının tek kaynağı; `visual_recipe.py` aynı deseni kullanır | Kodu kopyalamak (iki strict okuyucu ayrışır) |

## Design

`LaserRecipeDatabase.__post_init__` bütün değişmezleri (kimlik, ad, referans, profil
eşitliği, reçete anahtarı) doğrular; işlemler (`put_*`, `remove_*`, `store_recipe`,
`matching_recipes`) yeni değer döndürür, hata durumunda eski değer korunur. `put_machine`
bağlı reçeteleri yeni profille yeniden kurar. `store_recipe` cihaz profiline eşit makineyi
bulur, yoksa yeni makine ekler; aynı adlı farklı profil çakışmadır. Aynı anahtarlı farklı
reçete yalnız `replace=True` ile değişir; birebir aynısı değişiklik üretmez.

Codec mevcut laser_json yardımcılarıyla strict okur/yazar. Depo `load_database(path)`
→ (veritabanı, revizyon) ve `save_database(path, db, expected_revision)` → yeni revizyon
sağlar; `write_text_atomic` hem bu depo hem `save_recipe_file` tarafından kullanılır.

UI: `LaserRecipeLibrary` (QGroupBox) Laser CAM panelinde reçete editörünün altında yer
alır. Malzeme/lens/makine combobox + yönetim düğmeleri, arama, tablo, yükle/kaydet/sil,
JSON içe/dışa aktar. İş mantığı core fonksiyonlarında; widget yalnız girdiyi toplar ve
sonucu gösterir. Diyaloglar ve onaylar test için ayrı metotlardır.

## Verification

RED (yeni test modülleri) → core/codec/depo GREEN → UI GREEN → ilgili laser/visual testleri
→ `tests/architecture` + `pip check` → tam suite (offscreen) → `tests/smoke_app.py`
(laser yolculuğuna veritabanı kaydet/yeniden aç adımı) → commit/push/PR → final-head
Windows CI. Fiziksel reçete kabulü WAITING.
