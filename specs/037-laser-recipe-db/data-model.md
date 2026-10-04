# Data model

Material: id, name, thickness_mm (None veya pozitif sonlu mm), notes (≤4000 karakter).
Lens: id, name, focal_length_mm (None veya pozitif sonlu mm), notes.
Machine: id, device (`LaserDeviceProfile`, 036), notes; ad = `device.name`.
RecipeEntry: id, recipe (`LaserRecipe`), machine_id | None, material_id | None,
lens_id | None, notes. `machine_id is None` ⇔ `recipe.device is None`; aksi hâlde
`recipe.device == machine.device`.
LaserRecipeDatabase: materials, lenses, machines, recipes (tuple, sıra korunur; tablo
başına ≤10000). Kimlik biçimi `[a-z0-9][a-z0-9_-]{0,63}`, tablo içinde benzersiz.
Ad benzersizliği `strip().casefold()`; reçete anahtarı
(material_id, machine_id, lens_id, ad) benzersiz.

## Dosya şeması v1

```json
{"kind": "mikrocam.laser-recipe-db", "schema_version": 1,
 "materials": [{"id": "…", "name": "…", "thickness_mm": null, "notes": ""}],
 "lenses":    [{"id": "…", "name": "…", "focal_length_mm": null, "notes": ""}],
 "machines":  [{"id": "…", "device": {036 profil alanları}, "notes": ""}],
 "recipes":   [{"id": "…", "name": "…", "machine_id": null, "material_id": null,
                "lens_id": null, "notes": "", "passes": [{…}]}]}
```

`machine_id` null olan reçetenin geçişleri schema1 alanlarını (ad, güç, hız, frekans,
atım), makineli reçetenin geçişleri schema2'nin yedi alanını taşır. Yazım
`sort_keys`, ayırıcısız, `ensure_ascii=False`, `allow_nan=False`. Okuma: duplicate anahtar,
eksik/bilinmeyen alan, NaN/Inf, bool sayı, yanlış `kind`, desteklenmeyen sürüm,
16 MiB üstü dosya reddedilir. `migrate_database_data` sürüm 1'i olduğu gibi döndürür;
gelecekteki sürümler yeni migration adımıyla eklenir.

## Durum geçişleri (arayüz)

Yükleme başarılı → yazılabilir. Yükleme başarısız (bozuk/gelecek sürüm/okuma hatası) →
salt okunur, dosyaya dokunulmaz. Yazma: beklenen revizyon = diskteki revizyon ise atomik
yaz ve revizyonu güncelle; değilse reddet ve “yeniden yükle” iste.
