# Research — Lazer reçete veritabanı

## Depolama biçimi (UA1)

| Seçenek | Artı | Eksi | Karar |
| --- | --- | --- | --- |
| Tek strict JSON dosyası (stdlib `json`) | Mevcut strict codec yardımcıları (`_load`, `_fields`, `device_from_data`) yeniden kullanılır; deterministik, diff'lenebilir, yedeklenebilir; atomik `os.replace` | Tüm dosya her kayıtta yeniden yazılır | **Seçildi** |
| SQLite (stdlib `sqlite3`) | Kısmi güncelleme, sorgu | İkinci şema/migration sistemi, ORM'e kayma riski (anayasa III), dosya kilidi ve WAL davranışı, ikili dosya diff'i | Reddedildi |
| Her reçete ayrı JSON + klasör | 0.2 dosyalarına benzer | Malzeme/makine/lens referans bütünlüğü ve atomiklik yok | Reddedildi |

Beklenen boyut kişisel kullanımda onlar–yüzler kayıttır; 16 MiB okuma sınırı konur.
Yeni runtime bağımlılığı yoktur.

## Eşzamanlı yazma

İki MikroCAM süreci aynı dosyayı açabilir. Okuma anındaki SHA-256 revizyonu saklanır;
yazmadan önce dosya yeniden okunur ve revizyon farklıysa yazma reddedilir (iyimser
eşzamanlılık). Kontrol ile `os.replace` arasındaki küçük pencere belgelenmiş sınırdır;
kilit dosyası Windows'ta bayat kilit sorunu getirdiği için seçilmedi.

## Cihaz profilinin tek kaynağı

036 profili her reçetede gömülüdür. Veritabanında profil makine kaydında bir kez saklanır,
reçete satırı yalnız geçişleri taşır. Bellekte `RecipeEntry.recipe` tam `LaserRecipe`
olup profil eşitliği yapıcıda doğrulanır; makine profili güncellenince bağlı reçeteler
`LaserRecipe(..., yeni_profil)` ile yeniden kurulur ve mevcut 036 doğrulaması aynen çalışır.

## Kayıpsızlık

Tekli reçete dışa aktarımı mevcut `recipe_to_json` ile yapılır. MikroCAM'in yazdığı
kanonik schema1/schema2 dosyası içe→dışa aktarımda bayt bayt korunur. Elle biçimlenmiş
(boşluk/anahtar sırası farklı) dosyada anlamsal eşitlik korunur, metin kanonikleşir.

## İş/proje anlık görüntüsü (FR011)

İşler veritabanı kimliği yerine tam reçeteyi saklamaya devam eder. Böylece sonradan
yapılan bir veritabanı düzenlemesi kaydedilmiş bir işi veya export paketini sessizce
değiştirmez. Veritabanı kimliğini işte izlemek ileride gerçek bir ihtiyaçla eklenebilir.

## Kimlikler

Kayıt kimlikleri `uuid4().hex` ile alan katmanında üretilir; çekirdek kimlik üretmez,
yalnız biçimi (`[a-z0-9][a-z0-9_-]{0,63}`) ve benzersizliği denetler. Testler açık kimlik
verir.
